from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import Job, JobStep, JobStepArtifact
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
    if persisted_status == JobStatus.CANCELLED.value:
        raise JobCancelled("任务已取消")


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


def recover_stale_jobs(db: Session, attempt_timeout_seconds: int) -> int:
    now = utc_now()
    timed_out = 0
    for job in db.scalars(select(Job).where(Job.status == JobStatus.RUNNING.value)).all():
        last_activity = job.heartbeat_at or job.started_at or job.created_at
        inactive_seconds = max(0, round((now - as_utc(last_activity)).total_seconds()))
        if inactive_seconds < attempt_timeout_seconds:
            continue
        step = db.scalar(
            select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == job.current_step)
        )
        started_at = (step.started_at if step and step.started_at else job.started_at) or job.created_at
        reason = (
            f"本次“{job.current_step}”自 {as_utc(started_at).astimezone().strftime('%Y-%m-%d %H:%M')} 开始，"
            f"已 {max(1, inactive_seconds // 60)} 分钟未收到该任务进度更新，已停止本次尝试。"
        )
        job.status = JobStatus.FAILED.value
        job.error_code = "ATTEMPT_TIMEOUT"
        job.error = reason
        job.finished_at = now
        job.lease_owner = None
        job.lease_expire_at = None
        if step:
            step.status = "FAILED"
            step.error = reason
            step.finished_at = now
        record_event(
            db,
            "job.attempt.timeout",
            reason,
            component="worker",
            level="ERROR",
            entity_type="job",
            entity_id=job.id,
            detail={
                "step": job.current_step,
                "error_code": "ATTEMPT_TIMEOUT",
                "last_activity_at": as_utc(last_activity).isoformat(),
                "inactive_seconds": inactive_seconds,
            },
            commit=False,
        )
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
