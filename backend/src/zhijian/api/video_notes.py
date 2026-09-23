from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.ai.job_config import SNAPSHOT_KEY, capture_ai_config
from zhijian.core.config import Settings, get_settings
from zhijian.core.time import utc_now
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    ContentItem,
    Destination,
    GroundedMapArtifact,
    Job,
    Place,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    Segment,
    Source,
    Transcript,
    VideoAsset,
    VideoCoverAsset,
    VideoScreenshot,
)
from zhijian.db.session import get_db
from zhijian.domain.enums import JobStatus, JobType
from zhijian.domain.schemas import BulkDeleteRequest
from zhijian.services.audit import record_event
from zhijian.services.auth import require_session
from zhijian.services.source_retention import prune_source_if_orphan
from zhijian.services.video_note_search import remove_video_note_search_index, search_video_note_ids
from zhijian.services.video_support import note_render_profile

router = APIRouter(tags=["video-notes"])
Protected = Annotated[object | None, Depends(require_session)]


def _cover_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("http://"):
        return "https://" + value.removeprefix("http://")
    return value


def _asset_for_note(db: Session, note_id: str) -> tuple[AINote, VideoAsset]:
    note = db.get(AINote, note_id)
    if note is None and note_id.startswith("ntv_"):
        version = db.get(AINoteVersion, note_id)
        note = db.get(AINote, version.ai_note_id) if version else None
    if note is None:
        raise HTTPException(404, "视频笔记不存在")
    asset = db.get(VideoAsset, note.video_asset_id)
    if asset is None:
        raise HTTPException(404, "视频资产不存在")
    return note, asset


def _transcript_for_note(db: Session, note: AINote, asset: VideoAsset) -> Transcript | None:
    version = db.get(AINoteVersion, note.current_version_id) if note.current_version_id else None
    statement = select(Transcript).where(Transcript.video_asset_id == asset.id)
    if version:
        statement = statement.where(Transcript.version == version.transcript_version)
    return db.scalar(statement.order_by(Transcript.version.desc()))


def _mentions_for_note(db: Session, note: AINote) -> list[PlaceMention]:
    rows = (
        db.scalars(
            select(PlaceMention)
            .where(PlaceMention.ai_note_version_id == note.current_version_id)
            .order_by(PlaceMention.created_at)
        ).all()
        if note.current_version_id
        else []
    )
    if rows:
        return rows
    if note.submission_job_id:
        return db.scalars(
            select(PlaceMention)
            .where(PlaceMention.submission_job_id == note.submission_job_id)
            .order_by(PlaceMention.created_at)
        ).all()
    return db.scalars(
        select(PlaceMention)
        .where(
            PlaceMention.video_asset_id == note.video_asset_id,
            PlaceMention.submission_job_id.is_(None),
        )
        .order_by(PlaceMention.created_at)
    ).all()


def _note_view(db: Session, note: AINote, asset: VideoAsset) -> dict:
    current = db.get(AINoteVersion, note.current_version_id) if note.current_version_id else None
    mentions = _mentions_for_note(db, note)
    cover = db.query(VideoCoverAsset).filter_by(video_asset_id=asset.id).one_or_none()
    return {
        "id": note.id,
        "status": note.status,
        "title": asset.title,
        "platform": asset.platform,
        "canonical_url": asset.canonical_url,
        "cover_url": _cover_url(asset.cover_url),
        "cover_status": cover.status if cover else "PENDING",
        "cover_image_url": (
            f"/api/video-covers/{cover.id}/image" if cover and cover.status == "READY" else None
        ),
        "cover_width": cover.width if cover else None,
        "cover_height": cover.height if cover else None,
        "cover_error": cover.error_code if cover else None,
        "uploader": asset.uploader,
        "duration_ms": asset.duration_ms,
        "current_version_id": note.current_version_id,
        "render_profile_id": current.render_profile_id if current else "CURRENT_DEFAULT",
        "render_profile_version": current.render_profile_version if current else "1",
        "overview": current.overview if current else "",
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "place_summary": {
            "total": len(mentions),
            "confirmed": sum(item.resolution_status == "CONFIRMED" for item in mentions),
        },
    }


@router.get("/api/video-notes")
def list_video_notes(_: Protected, query: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    statement = (
        select(AINote, VideoAsset)
        .join(VideoAsset, VideoAsset.id == AINote.video_asset_id)
        .order_by(AINote.updated_at.desc())
    )
    if not query or not query.strip():
        return [_note_view(db, note, asset) for note, asset in db.execute(statement).all()]
    matches = search_video_note_ids(db, query)
    if not matches:
        return []
    rows = {
        note.id: (note, asset)
        for note, asset in db.execute(
            statement.where(AINote.id.in_([item["note_id"] for item in matches]))
        ).all()
    }
    result = []
    for match in matches:
        row = rows.get(match["note_id"])
        if row is None:
            continue
        item = _note_view(db, *row)
        item["search_match"] = match["match_type"]
        item["search_snippet"] = match["snippet"]
        result.append(item)
    return result


@router.get("/api/video-notes/{note_id}")
def video_note_detail(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    note, asset = _asset_for_note(db, note_id)
    data = _note_view(db, note, asset)
    version = db.get(AINoteVersion, note.current_version_id) if note.current_version_id else None
    data["markdown"] = version.markdown if version else ""
    data["warnings"] = version.warnings_json if version else []
    section_rows = db.scalars(
        select(AINoteSection)
        .where(AINoteSection.ai_note_version_id == (version.id if version else ""))
        .order_by(AINoteSection.ordinal)
    ).all()
    data["sections"] = [
        {
            "id": section.id,
            "heading": section.heading,
            "section_kind": section.section_kind,
            "thesis": section.thesis,
            "summary": section.summary,
            "bullets": section.bullets_json,
            "anchor_id": section.anchor_id or f"section-{section.id}",
            "body_markdown": section.body_markdown,
            "segment_ids": section.segment_ids_json,
            "place_mention_ids": section.place_mention_ids_json,
            "evidence_quotes": section.evidence_quotes_json,
            "start_ms": section.start_ms,
            "end_ms": section.end_ms,
        }
        for section in section_rows
    ]
    data["needs_regeneration"] = bool(
        section_rows and any(not section.summary and not section.bullets_json for section in section_rows)
    )
    transcript = _transcript_for_note(db, note, asset)
    artifact = (
        db.scalar(
            select(GroundedMapArtifact)
            .where(
                GroundedMapArtifact.transcript_id == transcript.id,
                GroundedMapArtifact.transcript_version == transcript.version,
            )
            .order_by(GroundedMapArtifact.created_at.desc())
        )
        if transcript
        else None
    )
    screenshot_total = (
        db.scalar(
            select(func.count(VideoScreenshot.id)).where(
                VideoScreenshot.video_asset_id == asset.id,
                VideoScreenshot.ai_note_version_id == note.current_version_id,
            )
        )
        or 0
    )
    screenshot_ready = (
        db.scalar(
            select(func.count(VideoScreenshot.id)).where(
                VideoScreenshot.video_asset_id == asset.id,
                VideoScreenshot.ai_note_version_id == note.current_version_id,
                VideoScreenshot.status == "READY",
            )
        )
        or 0
    )
    transcript_status = "NOT_READY"
    if transcript:
        transcript_status = "EXPIRED" if transcript.purged_at else "AVAILABLE"
    data.update(
        {
            "transcript_status": transcript_status,
            "transcript_segment_count": transcript.segment_count if transcript else 0,
            "transcript_retention_until": transcript.retention_until if transcript else None,
            "screenshot_status": (
                "READY" if screenshot_ready else "PLANNING" if screenshot_total else "UNAVAILABLE"
            ),
            "semantic_map": {
                "prompt_version": artifact.prompt_version,
                "content_units": artifact.content_units_json,
                "entities": artifact.entities_json,
                "relations": artifact.relations_json,
                "claims": artifact.claims_json,
            }
            if artifact
            else None,
        }
    )
    return data


@router.get("/api/video-notes/{note_id}/transcript")
def video_note_transcript(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    note, asset = _asset_for_note(db, note_id)
    transcript = _transcript_for_note(db, note, asset)
    if transcript is None:
        raise HTTPException(404, "转写尚未生成")
    if transcript.purged_at:
        raise HTTPException(status_code=410, detail="完整转写已按 180 天策略删除")
    snapshot_id = transcript.metadata_json.get("snapshot_id")
    segments = db.scalars(
        select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)
    ).all()
    return {
        "id": transcript.id,
        "version": transcript.version,
        "source_kind": transcript.source_kind,
        "language": transcript.language,
        "text": transcript.text,
        "correction_status": transcript.metadata_json.get("correction_status", "UNCORRECTED"),
        "correction_coverage": transcript.metadata_json.get("correction_coverage", 0),
        "segments": [
            {
                "id": item.id,
                "text": item.corrected_text or item.text,
                "raw_text": item.raw_text or item.text,
                "corrected_text": item.corrected_text or item.text,
                "correction_status": item.correction_status,
                "start_ms": item.locator_json.get("start_ms"),
                "end_ms": item.locator_json.get("end_ms"),
                "confidence": item.confidence,
            }
            for item in segments
        ],
    }


@router.get("/api/video-notes/{note_id}/transcript/export")
def export_video_note_transcript(
    note_id: str,
    _: Protected,
    version: str = "corrected",
    db: Session = Depends(get_db),
) -> Response:
    note, asset = _asset_for_note(db, note_id)
    transcript = _transcript_for_note(db, note, asset)
    if transcript is None:
        raise HTTPException(404, "转写尚未生成")
    if transcript.purged_at:
        raise HTTPException(status_code=410, detail="完整转写已按 180 天策略删除")
    segments = db.scalars(
        select(Segment)
        .where(Segment.snapshot_id == transcript.metadata_json.get("snapshot_id"))
        .order_by(Segment.ordinal)
    ).all()
    if version not in {"raw", "corrected"}:
        raise HTTPException(status_code=422, detail="version 仅支持 raw 或 corrected")
    version_label = "AI 校对稿" if version == "corrected" else "原始识别稿"
    lines = [
        f"# {asset.title}",
        f"来源：{asset.canonical_url}",
        f"转写版本：{transcript.version} · {version_label}",
        "",
    ]
    for segment in segments:
        start = int(segment.locator_json.get("start_ms") or 0)
        end = int(segment.locator_json.get("end_ms") or start)
        value = (
            segment.corrected_text or segment.text
            if version == "corrected"
            else segment.raw_text or segment.text
        )
        lines.append(f"[{_timecode(start)} - {_timecode(end)}] {value}")
    filename = f"zhijian-transcript-{asset.bvid or asset.id}.txt"
    return Response(
        "\ufeff" + "\n".join(lines) + "\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _timecode(value: int) -> str:
    seconds = value // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


@router.get("/api/video-notes/{note_id}/screenshots")
def video_note_screenshots(note_id: str, _: Protected, db: Session = Depends(get_db)) -> list[dict]:
    note, asset = _asset_for_note(db, note_id)
    return [
        {
            "id": item.id,
            "section_id": item.ai_note_section_id,
            "place_mention_id": item.place_mention_id,
            "segment_id": item.segment_id,
            "planned_timestamp_ms": item.planned_timestamp_ms,
            "actual_timestamp_ms": item.actual_timestamp_ms,
            "image_url": f"/api/video-screenshots/{item.id}/image" if item.status == "READY" else None,
            "selection_reason": item.selection_reason,
            "caption": item.caption,
            "content_role": item.content_role,
            "status": item.status,
        }
        for item in db.scalars(
            select(VideoScreenshot)
            .where(
                VideoScreenshot.video_asset_id == asset.id,
                VideoScreenshot.ai_note_version_id == note.current_version_id,
            )
            .order_by(VideoScreenshot.planned_timestamp_ms)
        ).all()
    ]


@router.get("/api/video-screenshots/{screenshot_id}/image")
def video_screenshot_image(screenshot_id: str, _: Protected, db: Session = Depends(get_db)) -> FileResponse:
    screenshot = db.get(VideoScreenshot, screenshot_id)
    path = Path(screenshot.image_path) if screenshot and screenshot.image_path else None
    if screenshot is None or screenshot.status != "READY" or path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="截图尚不可用")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/api/video-screenshots/{screenshot_id}/visual-facts")
def queue_visual_fact_extraction(
    screenshot_id: str,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    screenshot = db.get(VideoScreenshot, screenshot_id)
    if screenshot is None or screenshot.status != "READY" or not screenshot.image_path:
        raise HTTPException(status_code=409, detail="截图尚不可用")
    active = db.scalar(
        select(Job).where(
            Job.payload_json["visual_fact_screenshot_id"].as_string() == screenshot_id,
            Job.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
        )
    )
    if active:
        return {"job_id": active.id, "status": active.status}
    job = Job(
        job_type=JobType.TRAVEL.value,
        status=JobStatus.QUEUED.value,
        payload_json={
            "visual_fact_screenshot_id": screenshot_id,
            SNAPSHOT_KEY: capture_ai_config(db, settings),
        },
    )
    db.add(job)
    record_event(
        db,
        "visual_fact.queued",
        "已排入截图视觉事实提取任务",
        component="vision-fact",
        entity_type="job",
        entity_id=job.id,
        commit=False,
    )
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.get("/api/video-covers/{cover_id}/image")
def video_cover_image(cover_id: str, _: Protected, db: Session = Depends(get_db)) -> FileResponse:
    cover = db.get(VideoCoverAsset, cover_id)
    path = Path(cover.derivative_path) if cover and cover.derivative_path else None
    if cover is None or cover.status != "READY" or path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="封面尚不可用")
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable", "ETag": cover.content_hash or ""},
    )


@router.get("/api/video-notes/{note_id}/places")
def video_note_places(note_id: str, _: Protected, db: Session = Depends(get_db)) -> list[dict]:
    note, asset = _asset_for_note(db, note_id)
    transcript = _transcript_for_note(db, note, asset)
    segment_rows = (
        db.scalars(
            select(Segment).where(Segment.snapshot_id == transcript.metadata_json.get("snapshot_id"))
        ).all()
        if transcript
        else []
    )
    segment_by_id = {segment.id: segment for segment in segment_rows}
    sections = db.scalars(
        select(AINoteSection).where(AINoteSection.ai_note_version_id == (note.current_version_id or ""))
    ).all()
    result = []
    for mention in _mentions_for_note(db, note):
        place = db.get(Place, mention.place_id) if mention.place_id else None
        destination = db.get(Destination, mention.destination_id) if mention.destination_id else None
        evidence_segments = [
            segment_by_id[segment_id]
            for segment_id in mention.segment_ids_json
            if segment_id in segment_by_id
        ]
        target_section = next(
            (
                section
                for section in sections
                if set(section.segment_ids_json) & set(mention.segment_ids_json)
            ),
            None,
        )
        insights = db.scalars(
            select(PlaceInsightItem)
            .where(PlaceInsightItem.place_mention_id == mention.id, PlaceInsightItem.status == "ACTIVE")
            .order_by(PlaceInsightItem.created_at)
        ).all()
        result.append(
            {
                "id": mention.id,
                "name": mention.name,
                "place_type": mention.place_type,
                "content_unit_id": mention.content_unit_id,
                "subject_role": mention.subject_role,
                "visit_intent": mention.visit_intent,
                "poi_policy": mention.poi_policy,
                "quote": mention.quote,
                "segment_ids": mention.segment_ids_json,
                "start_ms": (
                    evidence_segments[0].locator_json.get("start_ms") if evidence_segments else None
                ),
                "target_section_id": target_section.id if target_section else None,
                "confidence": mention.confidence,
                "insights": [
                    {
                        "insight_type": item.insight_type,
                        "value_text": item.value_text,
                        "segment_ids": item.segment_ids_json,
                        "source_quote": item.source_quote,
                        "target_section_id": next(
                            (
                                section.id
                                for section in sections
                                if set(section.segment_ids_json) & set(item.segment_ids_json)
                            ),
                            None,
                        ),
                    }
                    for item in insights
                ],
                "resolution_status": mention.resolution_status,
                "place_id": mention.place_id,
                "place": {
                    "name": place.name,
                    "address": place.address,
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "coordinate_system": place.coordinate_system,
                }
                if place
                else None,
                "destination": {
                    "id": destination.id,
                    "name": destination.canonical_name,
                    "scope_type": destination.scope_type,
                }
                if destination
                else None,
            }
        )
    return result


@router.post("/api/video-notes/{note_id}/regenerate")
def regenerate_video_note(
    note_id: str,
    _: Protected,
    profile_id: str = "CURRENT_DEFAULT",
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    note, asset = _asset_for_note(db, note_id)
    try:
        note_render_profile(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_NOTE_RENDER_PROFILE"}) from exc
    job = Job(
        job_type=JobType.TRAVEL.value,
        status=JobStatus.QUEUED.value,
        payload_json={
            "source_id": asset.source_id,
            "locator": str(asset.metadata_json.get("local_path") or asset.canonical_url),
            "title": asset.title,
            "video_platform": asset.platform,
            "video_asset_id": asset.id,
            "note_id": note.id,
            "note_render_profile": profile_id,
            "replay_from_step": "GENERATE_AI_NOTE",
            "reuse_reason": "NOTE_RENDER_PROFILE_CHANGED",
            "ai_automation_version": "v2",
            SNAPSHOT_KEY: capture_ai_config(db, settings),
        },
        created_at=utc_now(),
    )
    db.add(job)
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.delete("/api/video-notes/bulk")
def bulk_delete_video_notes(payload: BulkDeleteRequest, _: Protected, db: Session = Depends(get_db)) -> dict:
    notes_assets = [_asset_for_note(db, note_id) for note_id in dict.fromkeys(payload.ids)]
    source_ids = {asset.source_id for _, asset in notes_assets}
    active = db.scalar(
        select(Job).where(
            Job.payload_json["source_id"].as_string().in_(source_ids),
            Job.status.in_(["QUEUED", "RUNNING"]),
        )
    )
    if active:
        raise HTTPException(status_code=409, detail="请先取消或等待关联活跃任务结束")
    for note, asset in notes_assets:
        for content in _note_contents(db, note, asset):
            db.delete(content)
        remove_video_note_search_index(db, note.id)
        db.delete(note)
    db.flush()
    source_deleted_ids = [source_id for source_id in source_ids if prune_source_if_orphan(db, source_id)]
    record_event(
        db,
        "video.note.bulk_deleted",
        f"已删除 {len(notes_assets)} 条视频笔记",
        actor="user",
        detail={"ids": payload.ids, "source_deleted_ids": source_deleted_ids},
        commit=False,
    )
    db.commit()
    return {
        "requested": len(payload.ids),
        "deleted": len(notes_assets),
        "source_deleted_ids": source_deleted_ids,
    }


@router.delete("/api/video-notes/{note_id}")
def delete_video_note(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    note, asset = _asset_for_note(db, note_id)
    active = db.scalar(
        select(Job).where(
            Job.payload_json["source_id"].as_string() == asset.source_id,
            Job.status.in_(["QUEUED", "RUNNING"]),
        )
    )
    if active:
        raise HTTPException(status_code=409, detail="该视频仍有活跃任务，请先取消或等待结束")
    title, canonical_id, source_id = asset.title, note.id, asset.source_id
    for content in _note_contents(db, note, asset):
        db.delete(content)
    remove_video_note_search_index(db, note.id)
    db.delete(note)
    db.flush()
    source_deleted = prune_source_if_orphan(db, source_id)
    preserved = ["places"] if source_deleted else ["source", "video_asset", "transcript", "places"]
    record_event(
        db,
        "video.note.deleted",
        f"已删除视频笔记：{title}",
        actor="user",
        entity_type="video_note",
        entity_id=canonical_id,
        detail={"preserved": preserved, "source_deleted": source_deleted},
        commit=False,
    )
    db.commit()
    return {
        "status": "DELETED",
        "note_id": canonical_id,
        "preserved": preserved,
        "source_deleted": source_deleted,
    }


def _note_contents(db: Session, note: AINote, asset: VideoAsset) -> list[ContentItem]:
    contents = db.scalars(
        select(ContentItem).where(
            ContentItem.source_id == asset.source_id,
            ContentItem.content_type == "VIDEO_NOTE",
        )
    ).all()
    return [
        content
        for content in contents
        if (content.structured_json or {}).get("note_id") == note.id
        or (note.submission_job_id is None and not (content.structured_json or {}).get("note_id"))
    ]


@router.get("/api/travel/places/{place_id}/note")
def place_note(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(404, "地点不存在")
    note = db.scalar(
        select(PlaceNoteVersion)
        .where(PlaceNoteVersion.place_id == place_id)
        .order_by(PlaceNoteVersion.version.desc())
    )
    if note is None:
        raise HTTPException(404, "地点笔记尚未生成")
    return {
        "place_id": place_id,
        "version": note.version,
        "markdown": note.markdown,
        "evidence_count": note.evidence_count,
        "updated_at": note.updated_at,
    }


@router.get("/api/travel/places/{place_id}/sources")
def place_sources(place_id: str, _: Protected, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Place, place_id) is None:
        raise HTTPException(404, "地点不存在")
    result = []
    for mention in db.scalars(select(PlaceMention).where(PlaceMention.place_id == place_id)).all():
        asset = db.get(VideoAsset, mention.video_asset_id)
        source = db.get(Source, asset.source_id) if asset else None
        result.append(
            {
                "mention_id": mention.id,
                "source_id": source.id if source else None,
                "title": asset.title if asset else "",
                "url": asset.canonical_url if asset else "",
                "quote": mention.quote,
                "segment_ids": mention.segment_ids_json,
            }
        )
    return result
