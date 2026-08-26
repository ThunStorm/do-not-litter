from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from zhijian.db.models import AINote, ContentItem, Job, Source, VideoAsset


def source_deletion_state(db: Session, source_id: str) -> dict[str, int | bool]:
    content_count = db.scalar(
        select(func.count(ContentItem.id)).where(ContentItem.source_id == source_id)
    ) or 0
    note_count = db.scalar(
        select(func.count(AINote.id))
        .join(VideoAsset, VideoAsset.id == AINote.video_asset_id)
        .where(VideoAsset.source_id == source_id)
    ) or 0
    active_job_count = db.scalar(
        select(func.count(Job.id)).where(
            Job.payload_json["source_id"].as_string() == source_id,
            or_(Job.status.in_(["QUEUED", "RUNNING"]), Job.lease_owner.is_not(None)),
        )
    ) or 0
    return {
        "allowed": not (content_count or note_count or active_job_count),
        "content_count": content_count,
        "video_note_count": note_count,
        "active_job_count": active_job_count,
    }


def prune_source_if_orphan(db: Session, source_id: str | None) -> bool:
    if not source_id:
        return False
    source = db.get(Source, source_id)
    if source is None or not source_deletion_state(db, source_id)["allowed"]:
        return False
    db.delete(source)
    return True
