from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import ExternalCallAudit, Job, JobStep, JobStepArtifact
from zhijian.domain.enums import JobStatus
from zhijian.services.audit import record_event


class JobCancelled(RuntimeError):
    pass


def purge_expired_step_artifacts(db: Session) -> int:
    expired = db.scalars(
        select(JobStepArtifact).where(
            JobStepArtifact.status == "AVAILABLE",
            JobStepArtifact.replayable_until <= utc_now(),
        )
    ).all()
    for artifact in expired:
        cache_path = artifact.artifact_ref_json.get("cache_path")
        if cache_path:
            Path(str(cache_path)).unlink(missing_ok=True)
        artifact.status = "EXPIRED"
    if expired:
        db.commit()
    return len(expired)


def ensure_job_active(db: Session, job: Job) -> None:
    persisted_status = db.execute(
        select(Job.status).where(Job.id == job.id), execution_options={"autoflush": False}
    ).scalar_one_or_none()
    if persisted_status == JobStatus.CANCELLED.value or (
        job.lease_owner and persisted_status != JobStatus.RUNNING.value
    ):
        raise JobCancelled("任务已取消或本次执行权已失效")


def job_run_fence(job: Job) -> dict[str, object]:
    return {
        "lease_owner": job.lease_owner,
        "retry_count": job.retry_count,
        "started_at": as_utc(job.started_at).isoformat() if job.started_at else None,
    }


def job_matches_fence(job: Job, fence: dict[str, object]) -> bool:
    started_at = as_utc(job.started_at).isoformat() if job.started_at else None
    return (
        job.status == JobStatus.RUNNING.value
        and job.lease_owner == fence.get("lease_owner")
        and job.retry_count == int(fence.get("retry_count") or 0)
        and started_at == fence.get("started_at")
    )


def renew_job_lease(
    db: Session,
    job_id: str,
    fence: dict[str, object],
    lease_seconds: int,
) -> bool:
    job = db.get(Job, job_id)
    if job is None or not job_matches_fence(job, fence):
        return False
    job.lease_expire_at = utc_now() + timedelta(seconds=lease_seconds)
    db.commit()
    return True


def release_expired_cancelled_jobs(db: Session) -> int:
    now = utc_now()
    result = db.execute(
        update(Job)
        .where(
            Job.status == JobStatus.CANCELLED.value,
            Job.lease_owner.is_not(None),
            Job.lease_expire_at < now,
        )
        .values(lease_owner=None, lease_expire_at=None)
    )
    db.commit()
    return result.rowcount or 0


def _fail_active_job(db: Session, job: Job, code: str, reason: str, event_type: str) -> None:
    now = utc_now()
    job.status = JobStatus.FAILED.value
    job.error_code = code
    job.error = reason
    job.finished_at = now
    job.lease_owner = None
    job.lease_expire_at = None
    step = db.scalar(
        select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == job.current_step)
    )
    if step and step.status == "RUNNING":
        step.status = "FAILED"
        step.error = reason
        step.finished_at = now
    record_event(
        db,
        event_type,
        reason,
        component="worker",
        level="ERROR",
        entity_type="job",
        entity_id=job.id,
        detail={"step": job.current_step, "error_code": code},
        commit=False,
    )


def recover_stale_jobs(
    db: Session,
    attempt_timeout_seconds: int,
    attempt_timeout_grace_seconds: int = 5,
) -> int:
    now = utc_now()
    timed_out = 0
    for attempt in db.scalars(
        select(ExternalCallAudit).where(ExternalCallAudit.status == "RUNNING")
    ).all():
        metadata = attempt.request_meta_json or {}
        job = db.get(Job, attempt.job_id) if attempt.job_id else None
        fence = metadata.get("run_fence") if isinstance(metadata.get("run_fence"), dict) else {}
        if job is None or not job_matches_fence(job, fence):
            attempt.status = "CANCELLED" if job and job.status == JobStatus.CANCELLED.value else "DISCARDED"
            attempt.error_code = "JOB_RUN_FENCED"
            attempt.error_message = "本次模型调用所属的任务执行权已失效"
            continue
        raw_deadline = metadata.get("deadline_at")
        if not raw_deadline:
            continue
        try:
            deadline = as_utc(datetime.fromisoformat(str(raw_deadline)))
        except ValueError:
            continue
        if now <= deadline + timedelta(seconds=attempt_timeout_grace_seconds):
            continue
        attempt.status = "TIMED_OUT"
        attempt.duration_ms = max(0, round((now - as_utc(attempt.created_at)).total_seconds() * 1000))
        attempt.error_code = "AI_PROVIDER_TIMEOUT"
        attempt.error_message = "模型调用超过已配置的 deadline"
        reason = f"本次“{job.current_step}”模型调用超过 deadline，已停止本次任务执行。"
        _fail_active_job(db, job, "AI_PROVIDER_TIMEOUT", reason, "model.attempt.deadline_exceeded")
        timed_out += 1
    for job in db.scalars(select(Job).where(Job.status == JobStatus.RUNNING.value)).all():
        last_activity = job.heartbeat_at or job.started_at or job.created_at
        inactive_seconds = max(0, round((now - as_utc(last_activity)).total_seconds()))
        if inactive_seconds < attempt_timeout_seconds:
            continue
        if job.status != JobStatus.RUNNING.value:
            continue
        step = db.scalar(
            select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == job.current_step)
        )
        started_at = (step.started_at if step and step.started_at else job.started_at) or job.created_at
        reason = (
            f"本次“{job.current_step}”自 {as_utc(started_at).astimezone().strftime('%Y-%m-%d %H:%M')} 开始，"
            f"已 {max(1, inactive_seconds // 60)} 分钟未收到该任务进度更新，已停止本次尝试。"
        )
        _fail_active_job(db, job, "ATTEMPT_TIMEOUT", reason, "job.attempt.timeout")
        timed_out += 1
    db.commit()
    return timed_out


def lease_next_job(db: Session, owner: str, lease_seconds: int) -> Job | None:
    now = utc_now()
    candidate_id = db.scalar(
        select(Job.id)
        .where(Job.status == JobStatus.QUEUED.value)
        .order_by(Job.priority.asc(), Job.created_at.asc())
        .limit(1)
    )
    if not candidate_id:
        return None
    result = db.execute(
        update(Job)
        .where(Job.id == candidate_id, Job.status == JobStatus.QUEUED.value)
        .values(
            status=JobStatus.RUNNING.value,
            lease_owner=owner,
            lease_expire_at=now + timedelta(seconds=lease_seconds),
            heartbeat_at=now,
            started_at=now,
        )
    )
    db.commit()
    if not result.rowcount:
        return None
    return db.get(Job, candidate_id)
