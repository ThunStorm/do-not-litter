"""Read-only provenance assembly using the existing Snapshot/Segment identity."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.db.models import PlaceMention, Segment, Snapshot, VideoAsset


def evidence_trace(segments: list[Segment], ids: list[str], quote: str, snapshot_id: str) -> dict:
    by_id = {segment.id: segment for segment in segments}
    references = [by_id[item] for item in ids if item in by_id]
    # Transcript segments are consecutive pieces of one utterance. Inserting a
    # newline changes the evidence and rejects quotations spanning a boundary.
    source_text = "".join(segment.corrected_text or segment.text for segment in references)
    ordinals = [segment.ordinal for segment in references]
    contiguous = all(right == left + 1 for left, right in zip(ordinals, ordinals[1:], strict=False))
    valid = bool(
        ids
        and len(ids) == len(set(ids))
        and len(references) == len(ids)
        and all(segment.snapshot_id == snapshot_id for segment in references)
        and contiguous
        and quote
        and quote in source_text
    )
    return {
        "valid": valid,
        "snapshot_id": snapshot_id,
        "segment_ids": list(ids),
        "quote": quote,
        "version": "evidence-trace-v2",
        "start_ms": min((segment.locator_json.get("start_ms", 0) for segment in references), default=None),
        "end_ms": max((segment.locator_json.get("end_ms", 0) for segment in references), default=None),
    }


def verified_place_mention_trace(db: Session, mention: PlaceMention) -> dict:
    refs = db.scalars(select(Segment).where(Segment.id.in_(mention.segment_ids_json))).all()
    snapshot_id = refs[0].snapshot_id if refs else ""
    trace = evidence_trace(refs, mention.segment_ids_json, mention.quote, snapshot_id)
    snapshot = db.get(Snapshot, snapshot_id) if snapshot_id else None
    asset = db.get(VideoAsset, mention.video_asset_id)
    trace["valid"] = bool(
        trace["valid"]
        and snapshot
        and asset
        and snapshot.source_id == asset.source_id
        and snapshot.metadata_json.get("video_asset_id") == asset.id
    )
    trace["source_id"] = asset.source_id if trace["valid"] else None
    return trace
