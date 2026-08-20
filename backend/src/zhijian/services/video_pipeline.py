from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import ContentItem, Job, JobStep, Source, Transcript, VideoAsset
from zhijian.domain.enums import ContentType, JobStatus
from zhijian.providers.asr import WhisperCppProvider
from zhijian.providers.media import MediaDownloadError, YtDlpMediaProvider
from zhijian.resolvers.video import BilibiliResolver
from zhijian.resolvers.video.bilibili import VideoResolveError
from zhijian.services.audit import record_event
from zhijian.services.external_audit import audited_call
from zhijian.services.video_support import (
    ProviderUnavailable,
    build_place_notes,
    extract_place_mentions,
    generate_note,
    materialize_transcript,
    resolve_mentions_with_amap,
)

VIDEO_STEPS = (
    "VALIDATE_LINK",
    "FETCH_METADATA",
    "FETCH_SUBTITLE",
    "DOWNLOAD_AUDIO",
    "ASR",
    "NORMALIZE_TRANSCRIPT",
    "GENERATE_AI_NOTE",
    "EXTRACT_TRAVEL_FACTS",
    "RESOLVE_POI",
    "BUILD_PLACE_NOTES",
    "MATERIALIZE",
    "CLEAN_CACHE",
)


class NeedsUser(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


def _step(db: Session, job: Job, name: str, progress: int, input_value: dict[str, Any]) -> JobStep:
    digest = _hash(input_value)
    step = db.scalar(select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == name))
    if step is None:
        step = JobStep(
            job_id=job.id,
            step_name=name,
            status="RUNNING",
            progress=progress,
            input_json=input_value,
            input_hash=digest,
            version="video-v1",
            started_at=utc_now(),
        )
        db.add(step)
    else:
        step.status, step.progress, step.input_json, step.input_hash = (
            "RUNNING",
            progress,
            input_value,
            digest,
        )
        step.error = None
        step.started_at = step.started_at or utc_now()
    job.current_step, job.progress, job.heartbeat_at = name, progress, utc_now()
    db.commit()
    return step


def _done(db: Session, job: Job, step: JobStep, progress: int, output: dict[str, Any]) -> None:
    step.status, step.progress, step.output_json, step.finished_at = "COMPLETED", progress, output, utc_now()
    job.progress, job.heartbeat_at = progress, utc_now()
    db.commit()


def _fail_step(db: Session, step: JobStep, error: Exception) -> None:
    step.status, step.error, step.finished_at = "FAILED", str(error)[:4000], utc_now()
    db.commit()


def process_video_job(db: Session, job: Job, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    job.status = JobStatus.RUNNING.value
    job.started_at = job.started_at or utc_now()
    db.commit()
    audio_path: Path | None = None
    cookie_path: Path | None = None
    try:
        source = db.get(Source, str(job.payload_json["source_id"]))
        if source is None:
            raise RuntimeError("视频来源不存在")
        raw_url = str(job.payload_json.get("locator") or "")
        validate = _step(db, job, "VALIDATE_LINK", 5, {"url": raw_url})
        resolver = BilibiliResolver(
            timeout=settings.video_network_timeout_seconds,
            max_redirects=settings.video_max_redirects,
            proxy_url=settings.video_proxy_url,
        )
        store = build_secret_store(settings.secret_store, settings.data_dir)
        cookie = store.get(settings.video_cookie_secret_key)
        if cookie:
            cookie_path = _temporary_cookie_file(settings, job.id, cookie)
        resolved = audited_call(
            db,
            job_id=job.id,
            capability="VIDEO_RESOLVE",
            provider="bilibili",
            operation="metadata",
            request_meta={"url_host": "bilibili"},
            call=lambda: resolver.resolve(raw_url, cookie),
        )
        _done(db, job, validate, 12, {"bvid": resolved.bvid, "page": resolved.page_number})

        meta = _step(db, job, "FETCH_METADATA", 15, {"bvid": resolved.bvid, "cid": resolved.cid})
        asset = db.scalar(select(VideoAsset).where(VideoAsset.source_id == source.id))
        if asset is None:
            asset = VideoAsset(
                source_id=source.id,
                canonical_url=resolved.canonical_url,
                bvid=resolved.bvid,
                aid=resolved.aid,
                cid=resolved.cid,
                page_number=resolved.page_number,
                title=resolved.title,
                uploader=resolved.uploader,
                duration_ms=resolved.duration_ms,
                cover_url=resolved.cover_url,
                metadata_json=resolved.metadata,
            )
            db.add(asset)
        else:
            asset.canonical_url, asset.bvid, asset.aid, asset.cid = (
                resolved.canonical_url,
                resolved.bvid,
                resolved.aid,
                resolved.cid,
            )
            asset.title, asset.uploader, asset.duration_ms, asset.cover_url, asset.metadata_json = (
                resolved.title,
                resolved.uploader,
                resolved.duration_ms,
                resolved.cover_url,
                resolved.metadata,
            )
        source.title = resolved.title
        source.authority = "PLATFORM"
        db.commit()
        _done(
            db,
            job,
            meta,
            22,
            {"video_asset_id": asset.id, "title": asset.title, "duration_ms": asset.duration_ms},
        )

        transcript: Transcript | None = None
        segments = []
        subtitle = _step(
            db, job, "FETCH_SUBTITLE", 25, {"asset": asset.id, "subtitle_tracks": len(resolved.subtitles)}
        )
        if resolved.subtitles:
            raw_segments = audited_call(
                db,
                job_id=job.id,
                capability="VIDEO_SUBTITLE",
                provider="bilibili",
                operation="subtitle",
                request_meta={"track": resolved.subtitles[0].language},
                call=lambda: resolver.fetch_subtitle_segments(resolved.subtitles[0]),
            )
            transcript, segments = materialize_transcript(
                db,
                source,
                asset,
                raw_segments,
                source_kind=resolved.subtitles[0].source,
                language=resolved.subtitles[0].language or "zh-CN",
            )
            _done(
                db,
                job,
                subtitle,
                42,
                {"source": "subtitle", "segments": len(segments), "transcript_id": transcript.id},
            )
            skipped = _step(db, job, "DOWNLOAD_AUDIO", 43, {"reason": "subtitle_available"})
            _done(db, job, skipped, 43, {"skipped": True})
            skipped = _step(db, job, "ASR", 44, {"reason": "subtitle_available"})
            _done(db, job, skipped, 44, {"skipped": True})
        else:
            _done(db, job, subtitle, 28, {"source": "none", "segments": 0})
            download = _step(
                db,
                job,
                "DOWNLOAD_AUDIO",
                30,
                {"url": resolved.canonical_url, "max_mb": settings.video_max_media_mb},
            )
            media = YtDlpMediaProvider(
                settings.cache_dir / "audio",
                max_bytes=settings.video_max_media_mb * 1024 * 1024,
                timeout=settings.video_network_timeout_seconds,
                proxy_url=settings.video_proxy_url,
            )
            try:
                audio_path = audited_call(
                    db,
                    job_id=job.id,
                    capability="VIDEO_MEDIA",
                    provider="yt-dlp",
                    operation="audio-only",
                    request_meta={"bvid": resolved.bvid},
                    call=lambda: media.download_audio(resolved.canonical_url, cookie_path),
                )
            except MediaDownloadError as exc:
                raise NeedsUser("VIDEO_MEDIA_UNAVAILABLE", str(exc)) from exc
            _done(db, job, download, 45, {"audio_cached": True, "bytes": audio_path.stat().st_size})
            asr_step = _step(
                db, job, "ASR", 48, {"audio": audio_path.name, "model": str(settings.whisper_model)}
            )
            try:
                text, raw_segments = audited_call(
                    db,
                    job_id=job.id,
                    capability="ASR",
                    provider="whisper.cpp",
                    operation="transcribe",
                    request_meta={"audio": audio_path.name},
                    call=lambda: WhisperCppProvider(
                        settings.whisper_binary, settings.whisper_model
                    ).transcribe(audio_path),
                )
            except RuntimeError as exc:
                raise NeedsUser("ASR_UNAVAILABLE", str(exc)) from exc
            if not text or not raw_segments:
                raise NeedsUser("ASR_EMPTY", "本地转写没有产生带时间码的结果")
            _done(db, job, asr_step, 62, {"segments": len(raw_segments)})
            transcript, segments = materialize_transcript(db, source, asset, raw_segments, source_kind="ASR")

        normalize = _step(
            db, job, "NORMALIZE_TRANSCRIPT", 64, {"transcript_id": transcript.id if transcript else ""}
        )
        if transcript is None or not segments:
            raise NeedsUser("TRANSCRIPT_MISSING", "未获得可用于笔记生成的时间码转写")
        _done(db, job, normalize, 68, {"segments": len(segments), "source": transcript.source_kind})

        note_step = _step(
            db, job, "GENERATE_AI_NOTE", 70, {"transcript": transcript.id, "version": transcript.version}
        )
        try:
            note = generate_note(db, settings, asset, transcript, segments)
        except ProviderUnavailable as exc:
            raise NeedsUser(exc.code, str(exc)) from exc
        _done(db, job, note_step, 80, {"note_version_id": note.id, "version": note.version})

        extract = _step(db, job, "EXTRACT_TRAVEL_FACTS", 82, {"note_version": note.id})
        try:
            mentions = extract_place_mentions(db, settings, asset, note, segments)
        except ProviderUnavailable as exc:
            # The video note is usable without travel POI enrichment.
            mentions = []
            _done(db, job, extract, 84, {"skipped": True, "reason": exc.code})
        else:
            _done(db, job, extract, 87, {"mentions": len(mentions)})

        poi = _step(db, job, "RESOLVE_POI", 88, {"mentions": len(mentions), "provider": "AMap"})
        confirmed, unresolved = resolve_mentions_with_amap(db, settings, mentions)
        _done(
            db,
            job,
            poi,
            92,
            {
                "confirmed": confirmed,
                "unresolved": unresolved,
                "amap_configured": bool(settings.amap_api_key),
            },
        )
        place_notes = _step(db, job, "BUILD_PLACE_NOTES", 93, {"confirmed": confirmed})
        built = build_place_notes(db, asset, mentions)
        _done(db, job, place_notes, 95, {"built": built})

        materialize = _step(db, job, "MATERIALIZE", 96, {"note": note.id})
        content = db.scalar(
            select(ContentItem).where(
                ContentItem.source_id == source.id, ContentItem.content_type == ContentType.VIDEO_NOTE.value
            )
        )
        if content is None:
            content = ContentItem(
                content_type=ContentType.VIDEO_NOTE.value,
                title=asset.title,
                summary=note.overview,
                source_id=source.id,
                structured_json={},
            )
            db.add(content)
        content.summary = note.overview
        content.status = "COMPLETED"
        content.structured_json = {
            "video_asset_id": asset.id,
            "note_id": note.id,
            "place_mentions": len(mentions),
            "confirmed_places": confirmed,
            "unresolved_places": unresolved,
        }
        db.flush()
        job.result_content_id = content.id
        _done(db, job, materialize, 98, {"content_id": content.id})
        clean = _step(db, job, "CLEAN_CACHE", 99, {"audio": audio_path.name if audio_path else None})
        if audio_path:
            audio_path.unlink(missing_ok=True)
        if cookie_path:
            cookie_path.unlink(missing_ok=True)
        _done(db, job, clean, 100, {"audio_deleted": bool(audio_path)})
        job.status = (
            JobStatus.PARTIAL_SUCCESS.value
            if unresolved or not settings.amap_api_key
            else JobStatus.COMPLETED.value
        )
        job.current_step, job.progress, job.finished_at = "CLEAN_CACHE", 100, utc_now()
        job.lease_owner, job.lease_expire_at, job.error, job.error_code = None, None, None, None
        record_event(
            db,
            "video.note.completed",
            f"视频笔记已生成：{asset.title}",
            component="video-pipeline",
            entity_type="job",
            entity_id=job.id,
            detail={"note_id": note.id, "partial": job.status == JobStatus.PARTIAL_SUCCESS.value},
            commit=False,
        )
        db.commit()
    except NeedsUser as exc:
        job.status, job.error_code, job.error, job.finished_at = (
            JobStatus.NEEDS_USER.value,
            exc.code,
            str(exc)[:4000],
            utc_now(),
        )
        job.lease_owner = job.lease_expire_at = None
        record_event(
            db,
            "video.note.needs_user",
            str(exc),
            component="video-pipeline",
            level="WARNING",
            entity_type="job",
            entity_id=job.id,
            detail={"code": exc.code},
            commit=False,
        )
        db.commit()
    except Exception as exc:
        if isinstance(exc, VideoResolveError):
            job.error_code = exc.code
        job.status, job.error, job.finished_at = JobStatus.FAILED.value, str(exc)[:4000], utc_now()
        job.lease_owner = job.lease_expire_at = None
        record_event(
            db,
            "video.note.failed",
            str(exc),
            component="video-pipeline",
            level="ERROR",
            entity_type="job",
            entity_id=job.id,
            detail={"code": job.error_code},
            commit=False,
        )
        db.commit()
        raise
    finally:
        if audio_path:
            audio_path.unlink(missing_ok=True)
        if cookie_path:
            cookie_path.unlink(missing_ok=True)


def _temporary_cookie_file(settings: Settings, job_id: str, value: str) -> Path:
    """Convert a locally stored Cookie header to a short-lived Netscape file for yt-dlp."""
    path = settings.cache_dir / "temp" / f"{job_id}.cookies.txt"
    rows = ["# Netscape HTTP Cookie File"]
    for pair in value.split(";"):
        name, separator, cookie_value = pair.strip().partition("=")
        if separator and name:
            rows.append(f".bilibili.com\tTRUE\t/\tTRUE\t0\t{name}\t{cookie_value}")
    if len(rows) == 1:
        raise NeedsUser("VIDEO_COOKIE_INVALID", "保存的 Bilibili Cookie 格式无效")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path
