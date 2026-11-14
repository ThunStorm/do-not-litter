"""Read-only review contract. Actions are hints; write endpoints recheck all guards."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.db.models import Job, Place, PlaceDeletionTombstone, PlaceMention
from zhijian.services.evidence_trace import verified_place_mention_trace

REASON_CATEGORIES = {
    "POI_SEARCH_FAILED": "SEARCH_ERROR",
    "POI_SEARCH_EMPTY": "NO_RESULTS",
    "NAME_MATCH_WEAK": "NAME_UNCERTAIN",
    "CANDIDATE_GAP_SMALL": "AMBIGUOUS",
    "SCENIC_CHILD_ONLY": "OBJECT_CATEGORY",
    "SCENIC_RELATION_UNKNOWN": "OBJECT_CATEGORY",
    "CATEGORY_UNMAPPED": "OBJECT_CATEGORY",
    "CATEGORY_WEAK_ONLY": "OBJECT_CATEGORY",
    "CATEGORY_CONFLICT": "OBJECT_CATEGORY",
    "QUERY_INCOMPLETE": "INCOMPLETE_CANDIDATES",
    "DETAIL_VERIFICATION_FAILED": "DETAIL_MISMATCH",
    "GEO_CONTEXT_MISSING": "INSUFFICIENT_EVIDENCE",
    "SOURCE_EVIDENCE_INVALID": "INSUFFICIENT_EVIDENCE",
    "AUTHOR_NOT_RECOMMENDED": "INSUFFICIENT_EVIDENCE",
    "DUPLICATE_PROVIDER_ID": "AMBIGUOUS",
    "PLACE_DELETED": "USER_DELETED",
}


def poi_review_contract(db: Session, mention: PlaceMention) -> dict:
    metadata = mention.metadata_json or {}
    context = metadata.get("resolver_context") or {}
    manual = metadata.get("poi_candidates_source") == "MANUAL"
    trace = metadata.get("manual_search_trace" if manual else "poi_search_trace") or {}
    codes = list(metadata.get("reason_codes") or [])
    feedback = metadata.get("resolver_feedback") or {}
    job = db.get(Job, mention.submission_job_id) if mention.submission_job_id else None
    active = bool(job and (job.status in {"QUEUED", "RUNNING"} or job.lease_owner is not None))
    blockers = []
    if active:
        blockers.append("PLACE_JOB_ACTIVE")
    if mention.extraction_status == "SUPERSEDED":
        blockers.append("MENTION_SUPERSEDED")
    if metadata.get("deleted_by_user"):
        blockers.append("PLACE_DELETED")
    rejected = mention.extraction_status == "USER_REJECTED"
    eligible = mention.poi_policy in {"RESOLVE", "LEGACY"} and mention.extraction_status == "EXTRACTED"
    actions = []
    if not blockers:
        if rejected:
            actions = ["RESTORE"]
        elif eligible:
            actions = ["SEARCH", "REJECT"]
    candidate_actions = []
    for candidate in metadata.get("poi_candidates") or []:
        poi_id = candidate.get("provider_id")
        blocked = list(blockers)
        if not eligible:
            blocked.append("MENTION_NOT_POI_ELIGIBLE")
        if db.scalar(
            select(PlaceDeletionTombstone.id).where(
                func.upper(PlaceDeletionTombstone.external_provider) == "AMAP",
                PlaceDeletionTombstone.external_poi_id == poi_id,
            )
        ):
            blocked.append("PLACE_DELETED")
        places = db.scalars(
            select(Place).where(
                func.upper(Place.external_provider) == "AMAP",
                Place.external_poi_id == poi_id,
            )
        ).all()
        if len(places) > 1:
            blocked.append("DUPLICATE_PROVIDER_ID")
        if any(place.deleted_at is not None for place in places):
            blocked.append("PLACE_DELETED")
        try:
            valid = bool(
                poi_id
                and str(candidate.get("name") or "").strip()
                and 73.5 <= float(candidate["longitude"]) <= 135.1
                and 18 <= float(candidate["latitude"]) <= 53.6
            )
        except (KeyError, ValueError, TypeError):
            valid = False
        if not valid:
            blocked.append("INVALID_POI")
        candidate_actions.append(
            {
                "provider_id": poi_id,
                "allowed_actions": [] if blocked else ["CONFIRM"],
                "blocked_by": list(dict.fromkeys(blocked)),
            }
        )
    category = (
        "MANUAL_REJECTED"
        if rejected
        else "AREA_ONLY"
        if mention.resolution_status == "AREA_RESOLVED"
        else "UNIQUE_CONFIRMED"
        if mention.resolution_status == "CONFIRMED"
        else next(
            (REASON_CATEGORIES[code] for code in codes if code in REASON_CATEGORIES), "INSUFFICIENT_EVIDENCE"
        )
    )
    return {
        "version": "poi-review-v1",
        "authority": {
            "mention_id": mention.id,
            "revision": mention.revision,
            "video_asset_id": mention.video_asset_id,
            "submission_job_id": mention.submission_job_id,
            "ai_note_version_id": mention.ai_note_version_id,
            "place_id": mention.place_id,
            "destination_id": mention.destination_id,
        },
        "classification": (
            "MANUAL_RESULTS"
            if manual and trace.get("status") in {"RESULTS", "PARTIAL"}
            else "NO_RESULTS"
            if manual and trace.get("status") == "EMPTY"
            else category
        ),
        "automatic_classification": category,
        "reason_codes": codes,
        "resolver_version": metadata.get("resolver_version")
        or (metadata.get("resolver_v3") or {}).get("version"),
        "candidate_source": metadata.get("poi_candidates_source", "HISTORICAL"),
        "search": {
            **trace,
            "completeness": "PARTIAL"
            if trace.get("status") in {"FAILED", "PARTIAL"} or trace.get("truncated")
            else "UNKNOWN",
        },
        "effective_context": {
            "city": mention.city_hint or context.get("unit_city") or context.get("geo_session_city"),
            "province": mention.province_hint or context.get("geo_session_province"),
            "content_unit_id": mention.content_unit_id,
        },
        "evidence": verified_place_mention_trace(db, mention),
        "allowed_actions": actions,
        "blocked_by": blockers,
        "candidate_actions": candidate_actions,
        "detail_verification": {
            "status": "FAILED"
            if "DETAIL_VERIFICATION_FAILED" in codes
            else "AUTO_VERIFIED"
            if metadata.get("confirmation_origin") == "AUTO_STRONG"
            else "MANUAL_SELECTED"
            if metadata.get("confirmation_origin") == "MANUAL_CONFIRMED"
            else "CONTEXTUAL_FETCHED"
            if metadata.get("contextual_verification")
            else "NOT_RECORDED",
            "contextual_candidate": metadata.get("contextual_verification"),
        },
        "manual_decision": metadata.get("manual_confirmation") or feedback or None,
    }
