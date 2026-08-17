from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import Job
from zhijian.domain.enums import JobStatus


def recover_stale_jobs(db: Session) -> int:
    now = utc_now()
    result = db.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING.value, Job.lease_expire_at < now)
        .values(
            status=JobStatus.QUEUED.value,
            lease_owner=None,
            lease_expire_at=None,
            heartbeat_at=None,
        )
    )
    db.commit()
    return result.rowcount or 0


def lease_next_job(db: Session, owner: str, lease_seconds: int) -> Job | None:
    now = utc_now()
    candidate_id = db.scalar(
        select(Job.id)
        .where(
            or_(
                Job.status == JobStatus.QUEUED.value,
                (Job.status == JobStatus.RUNNING.value) & (Job.lease_expire_at < now),
            )
        )
        .order_by(Job.priority.asc(), Job.created_at.asc())
        .limit(1)
    )
    if not candidate_id:
        return None
    result = db.execute(
        update(Job)
        .where(
            Job.id == candidate_id,
            or_(
                Job.status == JobStatus.QUEUED.value,
                (Job.status == JobStatus.RUNNING.value) & (Job.lease_expire_at < now),
            ),
        )
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
