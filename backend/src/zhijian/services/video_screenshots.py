from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat
from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    PlaceMention,
    Segment,
    Transcript,
    VideoAsset,
    VideoScreenshot,
)
from zhijian.providers.media import YtDlpMediaProvider


def plan_screenshots(db: Session, asset: VideoAsset, note_version: AINoteVersion) -> list[VideoScreenshot]:
    """Persist evidence-bound screenshot plans before any media download is attempted."""
    existing = db.scalars(
        select(VideoScreenshot).where(
            VideoScreenshot.video_asset_id == asset.id,
            VideoScreenshot.ai_note_version_id == note_version.id,
        )
    ).all()
    if existing:
        return existing
    sections = db.scalars(
        select(AINoteSection)
        .where(AINoteSection.ai_note_version_id == note_version.id)
        .order_by(AINoteSection.ordinal)
    ).all()
    if not sections:
        transcript = db.scalar(
            select(Transcript)
            .where(Transcript.video_asset_id == asset.id)
            .order_by(Transcript.version.desc())
        )
        snapshot_id = transcript.metadata_json.get("snapshot_id") if transcript else ""
        segments = db.scalars(
            select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)
        ).all()
        if not segments:
            return []
        count = min(6, max(3, len(segments) // 40 + 2))
        plans = []
        for index in range(count):
            segment = segments[min(len(segments) - 1, round(index * (len(segments) - 1) / max(1, count - 1)))]
            shot = VideoScreenshot(
                video_asset_id=asset.id,
                ai_note_version_id=note_version.id,
                segment_id=segment.id,
                planned_timestamp_ms=int(segment.locator_json.get("start_ms") or 0),
                selection_reason="无章节时按时间线抽取的关键画面",
                caption="视频时间线关键画面",
                status="PLANNED",
            )
            db.add(shot)
            plans.append(shot)
        db.commit()
        return plans
    plans: list[VideoScreenshot] = []
    # A video note should ordinarily carry 3–12 visual anchors.  When the
    # model only yields one or two broad chapters, derive evenly-spaced
    # representatives within their known time span instead of silently
    # emitting a visually empty note.
    mentions = db.scalars(
        select(PlaceMention)
        .where(
            PlaceMention.video_asset_id == asset.id,
            PlaceMention.ai_note_version_id == note_version.id,
            PlaceMention.place_id.is_not(None),
        )
        .order_by(PlaceMention.confidence.desc())
    ).all()
    candidates: list[tuple[AINoteSection | None, int, str, PlaceMention | None]] = []
    for mention in mentions:
        section = next(
            (
                item for item in sections
                if set(item.segment_ids_json or []).intersection(mention.segment_ids_json or [])
            ),
            None,
        )
        if section and not any(existing[3] and existing[3].id == mention.id for existing in candidates):
            evidence_segment = next(
                (db.get(Segment, segment_id) for segment_id in mention.segment_ids_json),
                None,
            )
            timestamp = (
                int(evidence_segment.locator_json.get("start_ms") or 0)
                if evidence_segment
                else max(0, section.start_ms or 0)
            )
            candidates.append((section, timestamp, "地点讲解关键画面", mention))
    for section in sections:
        if len(candidates) >= 12:
            break
        if not any(item[0] and item[0].id == section.id for item in candidates):
            start_ms = max(0, section.start_ms or 0)
            end_ms = max(start_ms, section.end_ms or start_ms)
            candidates.append((section, (start_ms + end_ms) // 2, "章节主旨关键画面", None))
    if 0 < len(candidates) < 3:
        last_end = max((section.end_ms or section.start_ms or 0) for section in sections)
        for ordinal, timestamp in enumerate((last_end // 3, last_end * 2 // 3), start=1):
            if len(candidates) >= 3:
                break
            if not any(abs(timestamp - item[1]) < 4_000 for item in candidates):
                candidates.append((None, max(0, timestamp), f"全文代表帧 {ordinal}", None))
    for section, timestamp, reason, mention in candidates[:12]:
        segment_id = next(iter(section.segment_ids_json or []), None) if section else None
        segment = db.get(Segment, segment_id) if segment_id else None
        shot = VideoScreenshot(
            video_asset_id=asset.id,
            ai_note_version_id=note_version.id,
            ai_note_section_id=section.id if section else None,
            place_mention_id=mention.id if mention else None,
            segment_id=segment.id if segment else None,
            planned_timestamp_ms=timestamp,
            selection_reason=reason,
            caption=(f"{mention.name}相关画面" if mention else section.heading if section else reason),
            status="PLANNED",
        )
        db.add(shot)
        plans.append(shot)
    db.commit()
    return plans


def ensure_missing_screenshot_plans(db: Session) -> int:
    """Backfill plans for completed historical notes; downloading remains an explicit job step."""
    created = 0
    for note in db.scalars(select(AINote).where(AINote.current_version_id.is_not(None))).all():
        version = db.get(AINoteVersion, note.current_version_id)
        asset = db.get(VideoAsset, note.video_asset_id)
        if version is None or asset is None:
            continue
        if db.scalar(
            select(VideoScreenshot.id).where(
                VideoScreenshot.video_asset_id == asset.id,
                VideoScreenshot.ai_note_version_id == version.id,
            )
        ):
            continue
        created += len(plan_screenshots(db, asset, version))
    return created


def download_screenshot_video(
    settings: Settings, url: str, cookie_path: Path | None
) -> Path:
    """Fetch a bounded cache copy only; callers decide whether enhancement failure is partial."""
    media = YtDlpMediaProvider(
        settings.cache_dir / "video",
        max_bytes=settings.video_max_media_mb * 1024 * 1024,
        timeout=settings.video_network_timeout_seconds,
        proxy_url=settings.video_proxy_url,
    )
    return media.download_video(url, cookie_path)


def extract_screenshots(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    plans: list[VideoScreenshot],
    video_path: Path,
) -> tuple[int, str | None]:
    if not plans:
        return 0, None
    output_dir = settings.permanent_dir / "screenshots" / asset.id
    output_dir.mkdir(parents=True, exist_ok=True)
    perceptual_hashes: set[str] = set()
    ready = 0
    for plan in plans[:12]:
        target = output_dir / f"{plan.id}.jpg"
        planned_seconds = max(0, plan.planned_timestamp_ms) / 1000
        best: tuple[float, tuple[str, float, int, int]] | None = None
        # A short local search avoids chapter cuts, pure-black transition frames
        # and subtitle fades while keeping every final image tied to its plan.
        for offset in (-1.25, 0.0, 1.25):
            seconds = max(0, planned_seconds + offset)
            candidate = output_dir / f"{plan.id}-{int(offset * 1000):+05d}.jpg"
            command = [
                "ffmpeg", "-y", "-ss", str(seconds), "-i", str(video_path), "-frames:v", "1",
                "-vf", "scale=min(960\\,iw):-2", "-q:v", "3", str(candidate),
            ]
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=90)
            except subprocess.TimeoutExpired:
                continue
            quality = _quality(candidate) if result.returncode == 0 and candidate.is_file() else None
            if quality and (best is None or quality[1] > best[1][1]):
                best = (seconds, quality)
                if candidate != target:
                    target.unlink(missing_ok=True)
                    candidate.replace(target)
            else:
                candidate.unlink(missing_ok=True)
        if best is None or not target.is_file():
            plan.status = "REJECTED"
            plan.selection_reason = "FFmpeg 未能在计划时间码抽帧"
            continue
        actual_seconds, (perceptual, score, width, height) = best
        if perceptual in perceptual_hashes:
            target.unlink(missing_ok=True)
            plan.status = "REJECTED"
            plan.selection_reason = "与已选代表帧重复"
            continue
        perceptual_hashes.add(perceptual)
        plan.actual_timestamp_ms = round(actual_seconds * 1000)
        plan.image_path = str(target)
        plan.content_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        plan.perceptual_hash = perceptual
        plan.width, plan.height, plan.quality_score, plan.status = width, height, score, "READY"
        ready += 1
    db.commit()
    return ready, None


def _quality(path: Path) -> tuple[str, float, int, int] | None:
    with Image.open(path) as image:
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        mean = stat.mean[0]
        variance = stat.var[0]
        if mean < 12 or mean > 245 or variance < 45:
            return None
        edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).var[0]
        if edges < 80:
            return None
        thumb = gray.resize((8, 8))
        pixels = list(thumb.get_flattened_data())
        average = sum(pixels) / len(pixels)
        perceptual = "".join("1" if pixel >= average else "0" for pixel in pixels)
        return perceptual, min(1.0, variance / 1800), image.width, image.height
