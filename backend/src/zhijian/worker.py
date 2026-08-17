from __future__ import annotations

import logging
import platform
import socket
import time

from zhijian.core.config import get_settings
from zhijian.db.session import SessionLocal, init_database
from zhijian.services.jobs import lease_next_job, recover_stale_jobs
from zhijian.services.pipeline import process_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("zhijian.worker")


def worker_loop(once: bool = False) -> None:
    settings = get_settings()
    init_database()
    owner = f"{socket.gethostname()}:{platform.node()}"
    logger.info("Worker started: %s", owner)
    while True:
        with SessionLocal() as db:
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
