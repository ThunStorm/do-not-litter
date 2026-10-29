"""Remove source-owned projections without erasing shared or personal places."""

from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from zhijian.db.models import (
    AINote,
    AINoteVersion,
    ContentItem,
    DestinationPlaceLink,
    MapMarkerState,
    Place,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    PlaceObservation,
    PlaceUserNote,
    PlaceUserOverlay,
    PlaceVisitWindow,
    PreferenceEvent,
    RouteDraftItem,
    VideoAsset,
    VideoScreenshot,
    VisualFact,
)


def prune_place_candidates(db: Session, candidates: set[str]) -> list[str]:
    db.flush()
    deleted = []
    for place_id in sorted(candidates):
        place = db.get(Place, place_id)
        if place is None:
            continue
        personal = (
            place.origin != "AI_EXTRACTED"
            or place.user_state != "DISCOVERED"
            or place.poi_binding_status == "USER_CONFIRMED"
            or bool(place.metadata_json.get("user_edited"))
        )
        linked = bool(place.content_item_id and db.get(ContentItem, place.content_item_id))
        for model in (
            PlaceMention,
            PlaceObservation,
            PlaceInsightItem,
            PlaceVisitWindow,
            DestinationPlaceLink,
            VisualFact,
            PlaceUserNote,
            PlaceUserOverlay,
            PreferenceEvent,
            RouteDraftItem,
        ):
            linked = (
                linked or db.scalar(select(model.id).where(model.place_id == place_id).limit(1)) is not None
            )
        personal = (
            personal
            or db.scalar(
                select(PlaceNoteVersion.id)
                .where(
                    PlaceNoteVersion.place_id == place_id,
                    or_(
                        PlaceNoteVersion.model_provider != "deterministic",
                        PlaceNoteVersion.model_name != "evidence-template",
                    ),
                )
                .limit(1)
            )
            is not None
        )
        marker = db.scalar(select(MapMarkerState).where(MapMarkerState.place_id == place_id))
        personal = personal or bool(
            marker
            and (marker.origin != "AI_EXTRACTED" or marker.updated_by != "system" or marker.custom_label)
        )
        if not personal and not linked:
            db.delete(place)
            deleted.append(place_id)
            continue
        # These are disposable summaries, not independent observations. Never leave a
        # latest generated note quoting evidence that was just removed.
        db.execute(
            delete(PlaceNoteVersion).where(
                PlaceNoteVersion.place_id == place_id,
                PlaceNoteVersion.model_provider == "deterministic",
                PlaceNoteVersion.model_name == "evidence-template",
            )
        )
        from zhijian.services.video_support import build_place_notes

        mentions = db.scalars(select(PlaceMention).where(PlaceMention.place_id == place_id)).all()
        if place.origin == "AI_EXTRACTED":
            place.summary = next((m.reason for m in mentions if m.reason), "")
        if mentions:
            build_place_notes(db, None, mentions, commit=False)
    db.flush()
    return deleted


def remove_note_places(db: Session, note: AINote) -> list[str]:
    versions = select(AINoteVersion.id).where(AINoteVersion.ai_note_id == note.id)
    ownership = [PlaceMention.ai_note_version_id.in_(versions)]
    if note.submission_job_id:
        ownership.append(PlaceMention.submission_job_id == note.submission_job_id)
    other_note = db.scalar(
        select(AINote.id)
        .where(
            AINote.video_asset_id == note.video_asset_id,
            AINote.id != note.id,
        )
        .limit(1)
    )
    if not other_note:
        ownership.append(PlaceMention.ai_note_version_id.is_(None) & PlaceMention.submission_job_id.is_(None))
    mentions = db.scalars(
        select(PlaceMention).where(
            PlaceMention.video_asset_id == note.video_asset_id,
            or_(*ownership),
        )
    ).all()
    ids = [m.id for m in mentions]
    candidates = {m.place_id for m in mentions if m.place_id}
    screenshots = select(VideoScreenshot.id).where(VideoScreenshot.ai_note_version_id.in_(versions))
    visual_facts = db.scalars(select(VisualFact).where(VisualFact.screenshot_id.in_(screenshots))).all()
    for fact in visual_facts:
        if fact.place_id:
            candidates.add(fact.place_id)
        db.delete(fact)
    for model in (PlaceInsightItem, PlaceVisitWindow, DestinationPlaceLink):
        for row in db.scalars(select(model).where(model.place_mention_id.in_(ids))).all():
            if getattr(row, "provenance", "") in {"USER_ADDED", "PERSONAL_INFERENCE"}:
                row.place_mention_id, row.source_id = None, None
            else:
                db.delete(row)
    db.flush()
    db.execute(delete(PlaceMention).where(PlaceMention.id.in_(ids)))
    return prune_place_candidates(db, candidates)


def remove_source_places(db: Session, source_id: str) -> list[str]:
    asset_ids = select(VideoAsset.id).where(VideoAsset.source_id == source_id)
    mentions = db.scalars(select(PlaceMention).where(PlaceMention.video_asset_id.in_(asset_ids))).all()
    candidates = {m.place_id for m in mentions if m.place_id}
    mention_ids = [m.id for m in mentions]
    screenshots = select(VideoScreenshot.id).where(VideoScreenshot.video_asset_id.in_(asset_ids))
    for model in (PlaceInsightItem, PlaceVisitWindow, PlaceObservation, DestinationPlaceLink, VisualFact):
        ownership = [model.source_id == source_id]
        if hasattr(model, "place_mention_id"):
            ownership.append(model.place_mention_id.in_(mention_ids))
        if model is VisualFact:
            ownership.append(VisualFact.screenshot_id.in_(screenshots))
        rows = db.scalars(select(model).where(or_(*ownership))).all()
        for row in rows:
            if row.place_id:
                candidates.add(row.place_id)
            if getattr(row, "provenance", "") in {"USER_ADDED", "PERSONAL_INFERENCE"}:
                row.source_id = None
                if hasattr(row, "place_mention_id"):
                    row.place_mention_id = None
            else:
                db.delete(row)
    db.flush()
    db.execute(delete(PlaceMention).where(PlaceMention.video_asset_id.in_(asset_ids)))
    return prune_place_candidates(db, candidates)
