from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import Evidence, Job, Segment, Transcript, VideoAsset
from zhijian.services.audit import record_event

TRANSCRIPT_RETENTION_DAYS = 180


def retention_deadline():
    return utc_now() + timedelta(days=TRANSCRIPT_RETENTION_DAYS)


def purge_expired_transcripts(db: Session) -> int:
    expired = db.scalars(
        select(Transcript).where(Transcript.retention_until <= utc_now(), Transcript.purged_at.is_(None))
    ).all()
    purged = 0
    for transcript in expired:
        asset = db.get(VideoAsset, transcript.video_asset_id)
        if db.scalar(
            select(Job.id)
            .where(
                Job.status.in_(["QUEUED", "RUNNING"]),
                or_(
                    Job.payload_json["video_asset_id"].as_string() == transcript.video_asset_id,
                    Job.payload_json["transcript_id"].as_string() == transcript.id,
                    Job.payload_json["source_id"].as_string() == (asset.source_id if asset else ""),
                ),
            )
            .limit(1)
        ):
            continue
        purged += 1
        snapshot_id = transcript.metadata_json.get("snapshot_id")
        segments = db.scalars(select(Segment).where(Segment.snapshot_id == snapshot_id)).all()
        segment_ids = [segment.id for segment in segments]
        if segment_ids:
            for evidence in db.scalars(select(Evidence).where(Evidence.segment_id.in_(segment_ids))).all():
                evidence.quote = None
            for segment in segments:
                segment.text = ""
                segment.raw_text = ""
                segment.corrected_text = ""
        transcript.text = ""
        transcript.metadata_json = {
            key: value
            for key, value in transcript.metadata_json.items()
            if key not in {"fingerprint", "full_text_fingerprint"}
        }
        transcript.purged_at = utc_now()
        record_event(
            db,
            "transcript.retention.purged",
            "完整转写已按 180 天策略删除",
            component="worker",
            entity_type="transcript",
            entity_id=transcript.id,
            detail={"segment_count": transcript.segment_count},
            commit=False,
        )
    if purged:
        db.commit()
    return purged
