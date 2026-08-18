from __future__ import annotations

import logging
import os
import socket
import time

from zhijian.core.config import get_settings
from zhijian.core.logging import configure_logging
from zhijian.core.time import utc_now
from zhijian.db.models import Setting
from zhijian.db.session import SessionLocal, init_database
from zhijian.services.audit import record_event
from zhijian.services.jobs import lease_next_job, recover_stale_jobs
from zhijian.services.pipeline import process_job

logger = logging.getLogger("zhijian.worker")


def worker_loop(once: bool = False) -> None:
    settings = get_settings()
    configure_logging(settings, "worker")
    init_database()
    owner = f"{socket.gethostname()}:{os.getpid()}"
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
    while True:
        with SessionLocal() as db:
            heartbeat = db.get(Setting, "runtime:worker-heartbeat")
            value = {"owner": owner, "pid": os.getpid(), "at": utc_now().isoformat()}
            if heartbeat is None:
                heartbeat = Setting(key="runtime:worker-heartbeat", value_json=value)
                db.add(heartbeat)
            else:
                heartbeat.value_json = value
                heartbeat.updated_at = utc_now()
            db.commit()
            recover_stale_jobs(db)
            job = lease_next_job(db, owner, settings.worker_lease_seconds)
            if job:
                logger.info("Processing %s (%s)", job.id, job.job_type)
                try:
                    process_job(db, job)
                except Exception:
                    logger.exception("Job failed: %s", job.id)
        if once:
            return
        time.sleep(settings.worker_poll_seconds)


def run() -> None:
    worker_loop()


if __name__ == "__main__":
    run()
