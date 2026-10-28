"""Additive, local-only travel route and export API; legacy exports remain unchanged."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.db.models import (
    AINote,
    AINoteVersion,
    MapMarkerState,
    Place,
    PlaceInsightItem,
    PlaceMention,
    PlaceUserNote,
    PlaceUserOverlay,
    PlaceVisitWindow,
    RouteDraft,
    RouteDraftItem,
    VideoAsset,
)
from zhijian.db.session import get_db
from zhijian.services.auth import require_session
from zhijian.services.route_guides import list_route_guides
from zhijian.services.travel_semantics import temporal_semantics

router = APIRouter(prefix="/api/travel", dependencies=[Depends(require_session)])
Database = Annotated[Session, Depends(get_db)]


class GuideCopy(BaseModel):
    note_id: str = Field(min_length=1, max_length=64)
    guide_id: str = Field(min_length=1, max_length=64)
    version_id: str = Field(min_length=1, max_length=64)


@router.get("/route-guides")
def guides(db: Database, note_id: str | None = Query(default=None, max_length=64)):
    return list_route_guides(db, note_id=note_id)


@router.post("/route-guides/copy")
def copy_guide(payload: GuideCopy, db: Database):
    guide = next(
        (
            g
            for g in list_route_guides(db, note_id=payload.note_id)
            if g["guide_id"] == payload.guide_id and g["version_id"] == payload.version_id
        ),
        None,
    )
    if not guide:
        raise HTTPException(409, detail={"code": "ROUTE_SOURCE_CHANGED"})
    if not guide["stops"] or any(not stop["place_id"] for stop in guide["stops"]):
        raise HTTPException(
            409,
            detail={
                "code": "ROUTE_STOPS_NEED_REVIEW",
                "message": "请先确认来源路线的全部地点；原词仍保留在作者路线。",
            },
        )
    route = RouteDraft(name=guide["name"], city="")
    db.add(route)
    db.flush()
    for index, pid in enumerate(dict.fromkeys(s["place_id"] for s in guide["stops"])):
        db.add(RouteDraftItem(route_draft_id=route.id, place_id=pid, sort_order=index))
    db.commit()
    return {"id": route.id, "source_version_id": payload.version_id, "synchronized": False}


@router.get("/history-audit")
def history_audit(db: Database):
    # Report missing structures only. No apply mode is exposed; approval cannot be implied by GET.
    rows = db.scalars(
        select(PlaceMention)
        .where(PlaceMention.extraction_status.not_in(["USER_REJECTED", "SUPERSEDED"]))
        .order_by(PlaceMention.id)
    ).all()
    return {
        "dry_run": True,
        "writes": 0,
        "provider_calls": 0,
        "items": [
            {
                "mention_id": m.id,
                "version_id": m.ai_note_version_id,
                "reasons": [
                    name
                    for name, missing in (
                        ("MISSING_SCOPED_TIME", not (m.metadata_json or {}).get("visit_windows")),
                        ("MISSING_TRAVEL_FACTS", not (m.metadata_json or {}).get("travel_facts")),
                        ("MISSING_EVIDENCE", not m.quote or not m.segment_ids_json),
                    )
                    if missing
                ],
                "confirmed_binding_preserved": bool(m.place_id or m.destination_id),
            }
            for m in rows
        ],
    }


def export_bundle(db):
    places = db.scalars(select(Place).where(Place.deleted_at.is_(None)).order_by(Place.id)).all()
    hidden = set(db.scalars(select(MapMarkerState.place_id).where(MapMarkerState.visibility != "VISIBLE")))
    places = [p for p in places if p.id not in hidden]
    ids = [p.id for p in places]
    windows = db.scalars(
        select(PlaceVisitWindow).where(
            PlaceVisitWindow.place_id.in_(ids), PlaceVisitWindow.status == "ACTIVE"
        )
    ).all()
    insights = db.scalars(
        select(PlaceInsightItem).where(
            PlaceInsightItem.place_id.in_(ids), PlaceInsightItem.status == "ACTIVE"
        )
    ).all()
    overlays = {
        o.place_id: o for o in db.scalars(select(PlaceUserOverlay).where(PlaceUserOverlay.place_id.in_(ids)))
    }
    notes = {
        n.place_id: n.markdown
        for n in db.scalars(select(PlaceUserNote).where(PlaceUserNote.place_id.in_(ids)))
    }
    rows = []
    for p in places:
        o = overlays.get(p.id)
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "user_state": p.user_state,
                "poi": {"provider": p.external_provider, "id": p.external_poi_id},
                "user_note": notes.get(p.id, ""),
                "user_overlay": {"name": o.display_name, "tags": o.custom_tags_json} if o else {},
                "visit_windows": [
                    {
                        "id": w.id,
                        "season": w.season,
                        "month": w.month,
                        "month_segment": w.month_segment,
                        "day_time_slot": w.day_time_slot,
                        "period_type": w.period_type,
                        "suitability": w.suitability,
                        "semantics": temporal_semantics(w.source_text, period_type=w.period_type),
                        "source_id": w.source_id,
                        "quote": w.source_text,
                        "segment_ids": w.segment_ids_json,
                        "provenance": w.provenance,
                    }
                    for w in windows
                    if w.place_id == p.id
                ],
                "facts": [
                    {
                        "type": i.insight_type,
                        "text": i.value_text,
                        "qualifiers": i.value_json,
                        "source_id": i.source_id,
                        "segment_ids": i.segment_ids_json,
                        "quote": i.source_quote,
                        "provenance": i.provenance,
                    }
                    for i in insights
                    if i.place_id == p.id
                ],
            }
        )
    candidate_rows = db.execute(
        select(PlaceMention, AINoteVersion, VideoAsset)
        .join(AINoteVersion, PlaceMention.ai_note_version_id == AINoteVersion.id)
        .join(AINote, AINote.current_version_id == AINoteVersion.id)
        .join(VideoAsset, AINote.video_asset_id == VideoAsset.id)
        .where(
            PlaceMention.video_asset_id == VideoAsset.id,
            PlaceMention.extraction_status.not_in(["USER_REJECTED", "SUPERSEDED"]),
        )
        .order_by(PlaceMention.id)
    ).all()
    source_candidates = [
        {
            "id": m.id,
            "raw_name": m.raw_name,
            "name": m.name,
            "place_id": m.place_id,
            "destination_id": m.destination_id,
            "source_id": asset.source_id,
            "note_id": version.ai_note_id,
            "version_id": version.id,
            "scope": "AREA" if m.poi_policy == "AREA_RESOLVE" or m.destination_id else "PLACE",
            "resolution_status": m.resolution_status,
            "subject_role": m.subject_role,
            "visit_intent": m.visit_intent,
            "quote": m.quote,
            "segment_ids": m.segment_ids_json,
            "visit_windows": (m.metadata_json or {}).get("visit_windows", []),
            "travel_facts": (m.metadata_json or {}).get("travel_facts", []),
        }
        for m, version, asset in candidate_rows
        if not m.place_id or m.place_id in ids
    ]
    guides = list_route_guides(db)
    drafts = db.scalars(select(RouteDraft).order_by(RouteDraft.id)).all()
    items = db.scalars(select(RouteDraftItem).order_by(RouteDraftItem.sort_order)).all()
    return {
        "schema_version": "travel_export_v2",
        "places": rows,
        "source_candidates": source_candidates,
        "route_guides": guides,
        "route_drafts": [
            {"id": d.id, "name": d.name, "place_ids": [i.place_id for i in items if i.route_draft_id == d.id]}
            for d in drafts
        ],
        "notice": "来源视频观点，非实时通行信息；无路线服务验证的道路几何。",
    }


@router.get("/export-v2")
def export_v2(db: Database):
    bundle = export_bundle(db)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, value in (
            (
                "manifest.json",
                {
                    k: v
                    for k, v in bundle.items()
                    if k not in {"places", "source_candidates", "route_guides", "route_drafts"}
                },
            ),
            ("places.json", {"places": bundle["places"], "source_candidates": bundle["source_candidates"]}),
            ("routes.json", {"author_guides": bundle["route_guides"], "user_drafts": bundle["route_drafts"]}),
        ):
            archive.writestr(filename, json.dumps(value, ensure_ascii=False, indent=2))
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="zhijian-travel-v2.zip"'},
    )
