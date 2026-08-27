from __future__ import annotations

import logging
import os
import socket
import time
from datetime import timedelta
from threading import Event, Thread

from sqlalchemy import select

from zhijian.core.config import get_settings
from zhijian.core.logging import configure_logging
from zhijian.core.time import utc_now
from zhijian.db.models import Job, JobStep, Setting, VideoAsset, VideoCoverAsset
from zhijian.db.session import SessionLocal, init_database
from zhijian.domain.enums import JobStatus
from zhijian.services.audit import record_event
from zhijian.services.jobs import (
    lease_next_job,
    purge_expired_step_artifacts,
    recover_stale_jobs,
    release_expired_cancelled_jobs,
)
from zhijian.services.pipeline import process_job
from zhijian.services.transcript_retention import purge_expired_transcripts
from zhijian.services.video_cover import materialize_cover
from zhijian.services.video_screenshots import ensure_missing_screenshot_plans
from zhijian.services.video_support import repair_legacy_transcript_timing

logger = logging.getLogger("zhijian.worker")


def _preflight_video_pipeline() -> None:
    """Fail before leasing work when launchd cannot read deferred video modules."""
    from zhijian.services.video_pipeline import process_video_job  # noqa: F401


def _fail_unhandled_job(db, job_id: str, exc: Exception) -> None:
    job = db.get(Job, job_id)
    if job is None or job.status != JobStatus.RUNNING.value:
        return
    now = utc_now()
    reason = f"Worker 未处理异常：{type(exc).__name__}: {str(exc)[:360]}"
    job.status = JobStatus.FAILED.value
    job.error_code = "WORKER_UNHANDLED_EXCEPTION"
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
        "job.worker.unhandled_exception",
        reason,
        component="worker",
        level="ERROR",
        entity_type="job",
        entity_id=job.id,
        detail={"step": job.current_step, "error_code": job.error_code},
        commit=False,
    )
    db.commit()


def _persist_worker_heartbeat(owner: str) -> None:
    with SessionLocal() as db:
        heartbeat = db.get(Setting, "runtime:worker-heartbeat")
        now = utc_now()
        value = {"owner": owner, "pid": os.getpid(), "at": now.isoformat()}
        if heartbeat is None:
            db.add(Setting(key="runtime:worker-heartbeat", value_json=value))
        else:
            heartbeat.value_json = value
            heartbeat.updated_at = now
        db.commit()


def _heartbeat_loop(owner: str, interval_seconds: float, stopped: Event) -> None:
    while not stopped.is_set():
        try:
            _persist_worker_heartbeat(owner)
        except Exception:
            logger.exception("Worker heartbeat update failed")
        stopped.wait(interval_seconds)


def worker_loop(once: bool = False) -> None:
    settings = get_settings()
    configure_logging(settings, "worker")
    init_database()
    try:
        _preflight_video_pipeline()
    except Exception:
        logger.exception("Worker startup preflight failed")
        raise
    owner = f"{socket.gethostname()}:{os.getpid()}"
    last_transcript_cleanup = utc_now() - timedelta(days=1)
    repaired_legacy_timing = False
    planned_legacy_screenshots = False
    backfilled_covers = False
    heartbeat_stopped = Event()
    heartbeat_thread = Thread(
        target=_heartbeat_loop,
        args=(owner, settings.worker_heartbeat_seconds, heartbeat_stopped),
        name="zhijian-worker-heartbeat",
        daemon=True,
    )
    logger.info("Worker started: %s", owner)
    with SessionLocal() as db:
        record_event(
            db,
            "service.worker.started",
            "至简 Worker 已启动",
            component="worker",
            actor="system",
            detail={"owner": owner},
        )
    heartbeat_thread.start()
    try:
        while True:
            with SessionLocal() as db:
                release_expired_cancelled_jobs(db)
                recover_stale_jobs(db, settings.job_attempt_timeout_seconds)
                if utc_now() - last_transcript_cleanup >= timedelta(days=1):
                    purge_expired_transcripts(db)
                    purge_expired_step_artifacts(db)
                    last_transcript_cleanup = utc_now()
                if not repaired_legacy_timing:
                    repair_legacy_transcript_timing(db)
                    repaired_legacy_timing = True
                if not planned_legacy_screenshots:
                    ensure_missing_screenshot_plans(db)
                    planned_legacy_screenshots = True
                if not backfilled_covers:
                    for asset in db.scalars(select(VideoAsset)).all():
                        if db.query(VideoCoverAsset).filter_by(video_asset_id=asset.id).one_or_none() is None:
                            materialize_cover(db, settings, asset)
                    backfilled_covers = True
                job = lease_next_job(db, owner, settings.worker_lease_seconds)
                if job:
                    job_id = job.id
                    logger.info("Processing %s (%s)", job_id, job.job_type)
                    try:
                        process_job(db, job)
                    except Exception as exc:
                        db.rollback()
                        _fail_unhandled_job(db, job_id, exc)
                        logger.exception("Job failed: %s", job_id)
            if once:
                return
            time.sleep(settings.worker_poll_seconds)
    finally:
        heartbeat_stopped.set()
        heartbeat_thread.join(timeout=1)


def run() -> None:
    worker_loop()


if __name__ == "__main__":
    run()
