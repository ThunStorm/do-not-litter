from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    Job,
    Place,
    PlaceMention,
    PlaceNoteVersion,
    Segment,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.db.session import get_db
from zhijian.domain.enums import JobStatus, JobType
from zhijian.services.auth import require_session

router = APIRouter(tags=["video-notes"])
Protected = Annotated[object | None, Depends(require_session)]


def _asset_for_note(db: Session, note_id: str) -> tuple[AINote, VideoAsset]:
    note = db.get(AINote, note_id)
    if note is None:
        raise HTTPException(404, "视频笔记不存在")
    asset = db.get(VideoAsset, note.video_asset_id)
    if asset is None:
        raise HTTPException(404, "视频资产不存在")
    return note, asset


def _note_view(db: Session, note: AINote, asset: VideoAsset) -> dict:
    current = db.get(AINoteVersion, note.current_version_id) if note.current_version_id else None
    mentions = db.scalars(select(PlaceMention).where(PlaceMention.video_asset_id == asset.id)).all()
    return {
        "id": note.id,
        "status": note.status,
        "title": asset.title,
        "canonical_url": asset.canonical_url,
        "cover_url": asset.cover_url,
        "uploader": asset.uploader,
        "duration_ms": asset.duration_ms,
        "current_version_id": note.current_version_id,
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
    if query:
        statement = statement.where(VideoAsset.title.contains(query))
    return [_note_view(db, note, asset) for note, asset in db.execute(statement).all()]


@router.get("/api/video-notes/{note_id}")
def video_note_detail(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    note, asset = _asset_for_note(db, note_id)
    data = _note_view(db, note, asset)
    version = db.get(AINoteVersion, note.current_version_id) if note.current_version_id else None
    data["markdown"] = version.markdown if version else ""
    data["warnings"] = version.warnings_json if version else []
    data["sections"] = [
        {
            "id": section.id,
            "heading": section.heading,
            "body_markdown": section.body_markdown,
            "segment_ids": section.segment_ids_json,
            "start_ms": section.start_ms,
            "end_ms": section.end_ms,
        }
        for section in db.scalars(
            select(AINoteSection)
            .where(AINoteSection.ai_note_version_id == (version.id if version else ""))
            .order_by(AINoteSection.ordinal)
        ).all()
    ]
    return data


@router.get("/api/video-notes/{note_id}/transcript")
def video_note_transcript(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    _, asset = _asset_for_note(db, note_id)
    transcript = db.scalar(
        select(Transcript).where(Transcript.video_asset_id == asset.id).order_by(Transcript.version.desc())
    )
    if transcript is None:
        raise HTTPException(404, "转写尚未生成")
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
        "segments": [
            {
                "id": item.id,
                "text": item.text,
                "start_ms": item.locator_json.get("start_ms"),
                "end_ms": item.locator_json.get("end_ms"),
                "confidence": item.confidence,
            }
            for item in segments
        ],
    }


@router.get("/api/video-notes/{note_id}/places")
def video_note_places(note_id: str, _: Protected, db: Session = Depends(get_db)) -> list[dict]:
    _, asset = _asset_for_note(db, note_id)
    result = []
    for mention in db.scalars(
        select(PlaceMention).where(PlaceMention.video_asset_id == asset.id).order_by(PlaceMention.created_at)
    ).all():
        place = db.get(Place, mention.place_id) if mention.place_id else None
        result.append(
            {
                "id": mention.id,
                "name": mention.name,
                "place_type": mention.place_type,
                "quote": mention.quote,
                "segment_ids": mention.segment_ids_json,
                "confidence": mention.confidence,
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
            }
        )
    return result


@router.post("/api/video-notes/{note_id}/regenerate")
def regenerate_video_note(note_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    _, asset = _asset_for_note(db, note_id)
    job = Job(
        job_type=JobType.TRAVEL.value,
        status=JobStatus.QUEUED.value,
        payload_json={
            "source_id": asset.source_id,
            "locator": asset.canonical_url,
            "title": asset.title,
            "video_platform": "BILIBILI",
            "regenerate": True,
        },
        created_at=utc_now(),
    )
    db.add(job)
    db.commit()
    return {"job_id": job.id, "status": job.status}


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
