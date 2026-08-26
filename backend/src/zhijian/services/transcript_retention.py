from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import Evidence, Segment, Transcript
from zhijian.services.audit import record_event

TRANSCRIPT_RETENTION_DAYS = 180


def retention_deadline():
    return utc_now() + timedelta(days=TRANSCRIPT_RETENTION_DAYS)


def purge_expired_transcripts(db: Session) -> int:
    expired = db.scalars(
        select(Transcript).where(Transcript.retention_until <= utc_now(), Transcript.purged_at.is_(None))
    ).all()
    for transcript in expired:
        snapshot_id = transcript.metadata_json.get("snapshot_id")
        segments = db.scalars(select(Segment).where(Segment.snapshot_id == snapshot_id)).all()
        segment_ids = [segment.id for segment in segments]
        if segment_ids:
            for evidence in db.scalars(select(Evidence).where(Evidence.segment_id.in_(segment_ids))).all():
                evidence.quote = None
            for segment in segments:
                segment.text = ""
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
    if expired:
        db.commit()
    return len(expired)
