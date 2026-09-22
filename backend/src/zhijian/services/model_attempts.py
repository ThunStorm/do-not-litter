from __future__ import annotations

from datetime import datetime, timedelta
from threading import Event, Lock, Thread
from typing import Any

from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import ExternalCallAudit, Job
from zhijian.db.session import SessionLocal
from zhijian.services.audit import record_event
from zhijian.services.jobs import job_matches_fence, job_run_fence

_heartbeats: dict[str, tuple[Event, Thread]] = {}
_heartbeats_lock = Lock()


def begin_model_attempt(
    db: Session,
    settings: Settings,
    job: Job | None,
    *,
    provider: str,
    operation: str,
    request_meta: dict[str, Any],
) -> str:
    timeout_seconds = float(request_meta.get("timeout_seconds") or 300)
    started_at = utc_now()
    metadata = {
        **request_meta,
        "deadline_at": (started_at + timedelta(seconds=timeout_seconds)).isoformat(),
        "run_fence": job_run_fence(job) if job else None,
    }
    attempt = ExternalCallAudit(
        job_id=job.id if job else None,
        capability="LLM",
        provider=provider,
        operation=operation,
        status="RUNNING",
        request_meta_json=metadata,
        response_meta_json={},
    )
    db.add(attempt)
    db.flush()
    if job:
        record_event(
            db,
            "model.attempt.started",
            f"开始调用 {provider} / {metadata.get('model') or provider}",
            component="ai-gateway",
            entity_type="job",
            entity_id=job.id,
            detail={
                "attempt_id": attempt.id,
                "stage": metadata.get("stage"),
                "step": metadata.get("step"),
                "route": metadata.get("route"),
                "model": metadata.get("model"),
                "chunk_index": metadata.get("chunk_index"),
                "chunk_count": metadata.get("chunk_count"),
                "deadline_at": metadata["deadline_at"],
            },
            commit=False,
        )
    db.commit()
    if job:
        _start_heartbeat(attempt.id, job.id, metadata, settings)
    return attempt.id


def finish_model_attempt(
    db: Session,
    job: Job | None,
    attempt_id: str,
    *,
    status: str,
    duration_ms: int,
    response_meta: dict[str, Any],
    request_meta_updates: dict[str, Any],
    error_code: str | None,
    error_message: str | None,
) -> bool:
    _stop_heartbeat(attempt_id)
    db.expire_all()
    attempt = db.get(ExternalCallAudit, attempt_id)
    if attempt is None:
        return False
    metadata = attempt.request_meta_json or {}
    fence = metadata.get("run_fence") if isinstance(metadata.get("run_fence"), dict) else {}
    active = attempt.status == "RUNNING"
    if job:
        persisted = db.get(Job, job.id)
        active = active and persisted is not None and job_matches_fence(persisted, fence)
    if not active:
        if attempt.status == "RUNNING":
            persisted_job = db.get(Job, job.id) if job else None
            persisted_status = persisted_job.status if persisted_job else None
            attempt.status = "CANCELLED" if persisted_status == "CANCELLED" else "DISCARDED"
            attempt.error_code = "JOB_RUN_FENCED"
            attempt.error_message = "本次模型调用所属的任务执行权已失效"
        if job:
            record_event(
                db,
                "job.run.late_result_discarded",
                "模型调用返回时本次任务执行权已失效，结果已丢弃",
                component="ai-gateway",
                level="WARNING",
                entity_type="job",
                entity_id=job.id,
                detail={"attempt_id": attempt.id, "attempt_status": attempt.status},
                commit=False,
            )
        db.commit()
        return False
    attempt.status = status
    attempt.duration_ms = duration_ms
    attempt.request_meta_json = {**metadata, **request_meta_updates}
    attempt.response_meta_json = response_meta
    attempt.error_code = error_code
    attempt.error_message = error_message
    db.commit()
    return True


def _start_heartbeat(
    attempt_id: str,
    job_id: str,
    metadata: dict[str, Any],
    settings: Settings,
) -> None:
    stopped = Event()
    interval = max(1.0, min(float(settings.worker_heartbeat_seconds), settings.worker_lease_seconds / 3))
    thread = Thread(
        target=_heartbeat_loop,
        args=(attempt_id, job_id, metadata, settings, stopped, interval),
        name=f"zhijian-attempt-{attempt_id[-8:]}",
        daemon=True,
    )
    with _heartbeats_lock:
        _heartbeats[attempt_id] = (stopped, thread)
    thread.start()


def _stop_heartbeat(attempt_id: str) -> None:
    with _heartbeats_lock:
        handle = _heartbeats.pop(attempt_id, None)
    if not handle:
        return
    stopped, thread = handle
    stopped.set()
    thread.join(timeout=1)


def _heartbeat_loop(
    attempt_id: str,
    job_id: str,
    metadata: dict[str, Any],
    settings: Settings,
    stopped: Event,
    interval: float,
) -> None:
    fence = metadata.get("run_fence") if isinstance(metadata.get("run_fence"), dict) else {}
    try:
        deadline = as_utc(datetime.fromisoformat(str(metadata["deadline_at"])))
    except (KeyError, ValueError):
        return
    while not stopped.wait(interval):
        now = utc_now()
        if now >= deadline:
            return
        with SessionLocal() as db:
            attempt = db.get(ExternalCallAudit, attempt_id)
            job = db.get(Job, job_id)
            if (
                attempt is None
                or attempt.status != "RUNNING"
                or job is None
                or not job_matches_fence(job, fence)
            ):
                return
            attempt.updated_at = now
            job.heartbeat_at = now
            job.lease_expire_at = now + timedelta(seconds=settings.worker_lease_seconds)
            db.commit()
