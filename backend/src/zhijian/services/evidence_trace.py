"""Read-only provenance assembly using the existing Snapshot/Segment identity."""

from zhijian.db.models import Segment


def evidence_trace(segments: list[Segment], ids: list[str], quote: str, snapshot_id: str) -> dict:
    by_id = {segment.id: segment for segment in segments}
    references = [by_id[item] for item in ids if item in by_id]
    source_text = "\n".join(segment.corrected_text or segment.text for segment in references)
    valid = bool(
        ids
        and len(ids) == len(set(ids))
        and len(references) == len(ids)
        and all(segment.snapshot_id == snapshot_id for segment in references)
        and quote
        and quote in source_text
    )
    return {
        "valid": valid,
        "snapshot_id": snapshot_id,
        "segment_ids": list(ids),
        "quote": quote,
        "version": "evidence-trace-v1",
        "start_ms": min((segment.locator_json.get("start_ms", 0) for segment in references), default=None),
        "end_ms": max((segment.locator_json.get("end_ms", 0) for segment in references), default=None),
    }
