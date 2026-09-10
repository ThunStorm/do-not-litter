from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zhijian.ai.resource_manager import local_ai_resource_manager
from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import (
    AINote,
    AINoteVersion,
    ContentItem,
    Job,
    JobStep,
    JobStepArtifact,
    PlaceMention,
    Segment,
    Snapshot,
    Source,
    Transcript,
    VideoAsset,
    VideoScreenshot,
)
from zhijian.domain.enums import ContentType, JobStatus
from zhijian.providers.asr import WhisperCppProvider
from zhijian.providers.media import MediaDownloadError, YtDlpMediaProvider
from zhijian.resolvers.video import BilibiliResolver
from zhijian.resolvers.video.bilibili import (
    SubtitleTrack,
    VideoResolveError,
    first_usable_subtitle,
)
from zhijian.services.audit import record_event
from zhijian.services.external_audit import audited_call
from zhijian.services.jobs import JobCancelled, ensure_job_active
from zhijian.services.transcript_validation import assess_transcript_quality
from zhijian.services.video_cover import materialize_cover
from zhijian.services.video_screenshots import (
    download_screenshot_video,
    extract_screenshots,
    plan_screenshots,
)
from zhijian.services.video_support import (
    ProviderUnavailable,
    build_place_notes,
    correct_transcript,
    extract_place_mentions,
    generate_note,
    materialize_transcript,
    prompt_supplement_hash,
    resolve_mentions_with_amap,
)

VIDEO_STEPS = (
    "VALIDATE_LINK",
    "FETCH_METADATA",
    "FETCH_SUBTITLE",
    "DOWNLOAD_AUDIO",
    "ASR",
    "NORMALIZE_TRANSCRIPT",
    "CORRECT_TRANSCRIPT",
    "EXTRACT_TRAVEL_FACTS",
    "GENERATE_AI_NOTE",
    "RESOLVE_POI",
    "BUILD_PLACE_NOTES",
    "PLAN_SCREENSHOTS",
    "DOWNLOAD_VIDEO_FOR_FRAMES",
    "EXTRACT_SCREENSHOTS",
    "MATERIALIZE",
    "CLEAN_CACHE",
)

TRUSTED_TRANSCRIPT_STATUSES = frozenset({"TRUSTED_PLATFORM", "VERIFIED_GENERATED", "LOCAL_ASR"})
SUBTITLE_VALIDATION_VERSION = "subtitle-alignment-v1"


class NeedsUser(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


def _subtitle_decision(
    asset: VideoAsset, track: SubtitleTrack, raw_segments: list[dict[str, Any]]
) -> dict[str, Any]:
    assessment = assess_transcript_quality(
        raw_segments,
        duration_ms=asset.duration_ms,
        generated=track.generated,
        language=track.language,
    )
    metrics = assessment["metrics"]
    return {
        "accepted": assessment["status"] == "PASS",
        "validation_status": assessment["validation_status"],
        "validation_reasons": assessment["reasons"],
        "validation_version": SUBTITLE_VALIDATION_VERSION,
        "track_id": track.track_id,
        "language": track.language,
        "generated": track.generated,
        "endpoint": track.endpoint,
        "url_sha256": hashlib.sha256(track.url.encode()).hexdigest(),
        "body_sha256": _hash(raw_segments),
        "segments": len(raw_segments),
        "metrics": metrics,
        "timeline_ratio": metrics["timeline_ratio"],
    }


def _trusted_transcript_or_raise(
    db: Session, source: Source, asset: VideoAsset, transcript: Transcript, segments: list[Segment]
) -> None:
    metadata = transcript.metadata_json or {}
    status = str(metadata.get("validation_status") or "")
    if status not in TRUSTED_TRANSCRIPT_STATUSES:
        raise NeedsUser("TRANSCRIPT_SOURCE_MISMATCH", "转写未通过来源一致性验证，请从字幕步骤重新处理")
    snapshot_id = str(metadata.get("snapshot_id") or "")
    snapshot = db.get(Snapshot, snapshot_id)
    if transcript.video_asset_id != asset.id or snapshot is None or snapshot.source_id != source.id:
        raise NeedsUser("TRANSCRIPT_SOURCE_MISMATCH", "转写来源与当前视频不一致，请从字幕步骤重新处理")
    if asset.bvid and metadata.get("requested_bvid") != asset.bvid:
        raise NeedsUser("TRANSCRIPT_SOURCE_MISMATCH", "转写 BV 身份不一致，请从字幕步骤重新处理")
    if asset.cid and metadata.get("requested_cid") != asset.cid:
        raise NeedsUser("TRANSCRIPT_SOURCE_MISMATCH", "转写 CID 身份不一致，请从字幕步骤重新处理")
    assessment = assess_transcript_quality(segments, duration_ms=asset.duration_ms)
    if assessment["status"] != "PASS":
        raise NeedsUser("TRANSCRIPT_TIMELINE_INVALID", "转写时间轴异常，请从字幕步骤重新处理")


def _step(db: Session, job: Job, name: str, progress: int, input_value: dict[str, Any]) -> JobStep:
    ensure_job_active(db, job)
    digest = _hash(input_value)
    step = db.scalar(select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == name))
    if step is None:
        step = JobStep(
            job_id=job.id,
            step_name=name,
            status="RUNNING",
            progress=0,
            input_json=input_value,
            input_hash=digest,
            version="video-v1",
            started_at=utc_now(),
        )
        db.add(step)
    else:
        step.status, step.progress, step.input_json, step.input_hash = (
            "RUNNING",
            0,
            input_value,
            digest,
        )
        step.error = None
        step.started_at = utc_now()
        step.finished_at = None
    job.current_step, job.progress, job.heartbeat_at = name, progress, utc_now()
    record_event(
        db,
        "job.step.started",
        f"开始执行 {name}",
        component="video-pipeline",
        entity_type="job",
        entity_id=job.id,
        detail={"step": name, "step_status": "RUNNING", "job_progress": progress, "step_progress": 0},
        commit=False,
    )
    db.commit()
    return step


def _done(db: Session, job: Job, step: JobStep, progress: int, output: dict[str, Any]) -> None:
    ensure_job_active(db, job)
    step.status, step.progress, step.output_json, step.finished_at = "COMPLETED", 100, output, utc_now()
    job.progress, job.heartbeat_at = progress, utc_now()
    artifact = db.scalar(
        select(JobStepArtifact).where(
            JobStepArtifact.job_id == job.id,
            JobStepArtifact.step_name == step.step_name,
            JobStepArtifact.artifact_type == "STEP_OUTPUT",
        )
    )
    if artifact is None:
        artifact = JobStepArtifact(job_id=job.id, step_name=step.step_name)
        db.add(artifact)
    artifact.artifact_ref_json = output
    artifact.input_hash = step.input_hash
    artifact.content_hash = _hash(output)
    artifact.producer_version = step.version
    artifact.status = "AVAILABLE"
    artifact.replayable_until = utc_now() + timedelta(hours=get_settings().video_cache_ttl_hours)
    artifact.invalidated_at = None
    record_event(
        db,
        "job.step.completed",
        f"{step.step_name} 已完成",
        component="video-pipeline",
        entity_type="job",
        entity_id=job.id,
        detail={
            "step": step.step_name,
            "step_status": "COMPLETED",
            "job_progress": progress,
            "step_progress": 100,
            **output,
        },
        commit=False,
    )
    db.commit()


def _fail_step(db: Session, step: JobStep, error: Exception) -> None:
    step.status, step.error, step.finished_at = "FAILED", str(error)[:4000], utc_now()
    db.commit()


def _skip_step(db: Session, job: Job, step: JobStep, progress: int, reason: str) -> None:
    step.status, step.progress, step.output_json, step.finished_at = (
        "SKIPPED",
        100,
        {"reason": reason},
        utc_now(),
    )
    job.progress, job.heartbeat_at = progress, utc_now()
    record_event(
        db,
        "job.step.skipped",
        f"{step.step_name} 已跳过：{reason}",
        component="video-pipeline",
        entity_type="job",
        entity_id=job.id,
        detail={"step": step.step_name, "step_status": "SKIPPED", "reason": reason},
        commit=False,
    )
    db.commit()


def _stage_event(db: Session, job: Job, phase: str, message: str, **detail: Any) -> None:
    """Record a human-readable checkpoint and renew this job's own activity heartbeat."""
    ensure_job_active(db, job)
    job.heartbeat_at = utc_now()
    record_event(
        db,
        "video.stage.progress",
        message,
        component="video-pipeline",
        entity_type="job",
        entity_id=job.id,
        detail={"step": job.current_step, "phase": phase, **detail},
        commit=False,
    )
    db.commit()


def _download_and_transcribe_audio(
    db: Session,
    job: Job,
    settings: Settings,
    source: Source,
    asset: VideoAsset,
    canonical_url: str,
    bvid: str,
    cookie_path: Path | None,
    validation_reasons: list[str] | None = None,
) -> tuple[Path, Transcript, list[Segment]]:
    download = _step(
        db,
        job,
        "DOWNLOAD_AUDIO",
        30,
        {"url": canonical_url, "max_mb": settings.video_max_media_mb},
    )
    _stage_event(
        db,
        job,
        "audio.download.requested",
        "未找到平台字幕，正在下载音频用于转写",
        bvid=bvid,
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
            request_meta={"bvid": bvid},
            call=lambda: media.download_audio(canonical_url, cookie_path),
        )
    except MediaDownloadError as exc:
        raise NeedsUser(exc.code, str(exc)) from exc
    _stage_event(
        db,
        job,
        "audio.download.completed",
        "音频已下载，准备本地转写",
        bytes=audio_path.stat().st_size,
    )
    _done(
        db,
        job,
        download,
        45,
        {"audio_cached": True, "bytes": audio_path.stat().st_size, "cache_path": str(audio_path)},
    )
    asr_step = _step(db, job, "ASR", 48, {"audio": audio_path.name, "model": str(settings.whisper_model)})
    _stage_event(db, job, "asr.requested", "正在调用本机 Whisper.cpp 转写")
    try:
        text, raw_segments = audited_call(
            db,
            job_id=job.id,
            capability="ASR",
            provider="whisper.cpp",
            operation="transcribe",
            request_meta={"audio": audio_path.name},
            call=lambda: local_ai_resource_manager.run(
                "ASR",
                lambda: WhisperCppProvider(settings.whisper_binary, settings.whisper_model).transcribe(
                    audio_path
                ),
            ),
        )
    except RuntimeError as exc:
        raise NeedsUser("ASR_UNAVAILABLE", str(exc)) from exc
    if not text or not raw_segments:
        raise NeedsUser("ASR_EMPTY", "本地转写没有产生带时间码的结果")
    last_ms = max(int(item.get("end_ms") or item.get("start_ms") or 0) for item in raw_segments)
    _stage_event(db, job, "asr.completed", "本机转写已完成", segments=len(raw_segments))
    _done(db, job, asr_step, 62, {"segments": len(raw_segments)})
    transcript, segments = materialize_transcript(
        db,
        source,
        asset,
        raw_segments,
        source_kind="WHISPER_CPP_ASR",
        metadata={
            "requested_bvid": bvid,
            "requested_cid": asset.cid or "",
            "validation_status": "LOCAL_ASR",
            "validation_reasons": validation_reasons or [],
            "validation_version": SUBTITLE_VALIDATION_VERSION,
            "timeline_ratio": round(last_ms / asset.duration_ms, 4) if asset.duration_ms else None,
        },
    )
    return audio_path, transcript, segments


def process_video_job(db: Session, job: Job, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if job.payload_json.get("replay_from_step"):
        job_id = job.id
        try:
            _process_video_replay(db, job, settings, str(job.payload_json["replay_from_step"]))
        except NeedsUser as exc:
            db.rollback()
            replay_job = db.get(Job, job_id)
            if replay_job:
                replay_step = db.scalar(
                    select(JobStep).where(
                        JobStep.job_id == replay_job.id,
                        JobStep.step_name == replay_job.current_step,
                    )
                )
                if replay_step and replay_step.status in {"PENDING", "RUNNING"}:
                    replay_step.status = "FAILED"
                    replay_step.error = str(exc)[:4000]
                    replay_step.finished_at = utc_now()
                replay_job.status = JobStatus.NEEDS_USER.value
                replay_job.error_code = exc.code
                replay_job.error = str(exc)[:4000]
                replay_job.finished_at = utc_now()
                replay_job.lease_owner = replay_job.lease_expire_at = None
                db.commit()
        except Exception as exc:
            db.rollback()
            replay_job = db.get(Job, job_id)
            if replay_job:
                replay_step = db.scalar(
                    select(JobStep).where(
                        JobStep.job_id == replay_job.id,
                        JobStep.step_name == replay_job.current_step,
                    )
                )
                if replay_step and replay_step.status in {"PENDING", "RUNNING"}:
                    replay_step.status = "FAILED"
                    replay_step.error = str(exc)[:4000]
                    replay_step.finished_at = utc_now()
                replay_job.status = JobStatus.FAILED.value
                replay_job.error = str(exc)[:4000]
                replay_job.finished_at = utc_now()
                replay_job.lease_owner = replay_job.lease_expire_at = None
                record_event(
                    db,
                    "job.step_replay.failed",
                    str(exc),
                    component="video-pipeline",
                    level="ERROR",
                    entity_type="job",
                    entity_id=replay_job.id,
                    detail={"step": replay_job.current_step},
                    commit=False,
                )
                db.commit()
            raise
        return
    job_id = job.id
    ensure_job_active(db, job)
    job.status = JobStatus.RUNNING.value
    job.started_at = job.started_at or utc_now()
    db.commit()
    audio_path: Path | None = None
    cookie_path: Path | None = None
    screenshot_error: str | None = None
    screenshot_count = 0
    try:
        source = db.get(Source, str(job.payload_json["source_id"]))
        if source is None:
            raise RuntimeError("视频来源不存在")
        source_id = source.id
        raw_url = str(job.payload_json.get("locator") or "")
        validate = _step(db, job, "VALIDATE_LINK", 5, {"url": raw_url})
        _stage_event(
            db,
            job,
            "metadata.requested",
            "正在请求 Bilibili 视频元数据",
            url_host="bilibili",
        )
        resolver = BilibiliResolver(
            timeout=settings.video_network_timeout_seconds,
            max_redirects=settings.video_max_redirects,
            proxy_url=settings.video_proxy_url,
        )
        store = build_secret_store(settings.secret_store, settings.data_dir)
        cookie = store.get(settings.video_cookie_secret_key)
        if cookie:
            cookie_path = _temporary_cookie_file(settings, job.id, cookie)
        try:
            resolved = audited_call(
                db,
                job_id=job.id,
                capability="VIDEO_RESOLVE",
                provider="bilibili",
                operation="metadata",
                request_meta={"url_host": "bilibili"},
                call=lambda: resolver.resolve(raw_url, cookie),
                response_meta=lambda item: {
                    "bvid": item.bvid,
                    "cid": item.cid,
                    "page_number": item.page_number,
                    "subtitle_tracks": len(item.subtitles),
                    "subtitle_endpoints": sorted({track.endpoint for track in item.subtitles}),
                },
            )
        except VideoResolveError as exc:
            if exc.code == "VIDEO_LOGIN_REQUIRED":
                raise NeedsUser(
                    "VIDEO_LOGIN_REQUIRED",
                    "Bilibili 登录已失效或访问被平台拦截，请扫码登录后继续",
                ) from exc
            raise
        _stage_event(
            db,
            job,
            "metadata.resolved",
            "已解析 BV 与分 P，准备保存元数据",
            bvid=resolved.bvid,
            cid=resolved.cid,
            page=resolved.page_number,
            subtitle_tracks=len(resolved.subtitles),
        )
        _done(db, job, validate, 12, {"bvid": resolved.bvid, "page": resolved.page_number})

        meta = _step(db, job, "FETCH_METADATA", 15, {"bvid": resolved.bvid, "cid": resolved.cid})
        _stage_event(
            db,
            job,
            "asset.lookup",
            "正在查询是否已有同一视频资产",
            canonical_url=resolved.canonical_url,
        )
        asset = db.scalar(select(VideoAsset).where(VideoAsset.canonical_url == resolved.canonical_url))
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
            asset_action = "created"
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
            asset_action = "reused"
        source.title = resolved.title
        source.authority = "PLATFORM"
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            source = db.get(Source, source_id)
            asset = db.scalar(select(VideoAsset).where(VideoAsset.canonical_url == resolved.canonical_url))
            if source is None or asset is None:
                raise
            source.title = resolved.title
            source.authority = "PLATFORM"
            asset_action = "reused_after_conflict"
            db.commit()
        _stage_event(
            db,
            job,
            f"asset.{asset_action}",
            "视频资产已复用" if asset_action.startswith("reused") else "已创建视频资产",
            asset_id=asset.id,
            bvid=resolved.bvid,
        )
        _done(
            db,
            job,
            meta,
            22,
            {"video_asset_id": asset.id, "title": asset.title, "duration_ms": asset.duration_ms},
        )
        job.payload_json = {**job.payload_json, "video_asset_id": asset.id}
        db.commit()
        try:
            materialize_cover(db, settings, asset)
            _stage_event(db, job, "cover.materialized", "视频封面已缓存到本机")
        except Exception:
            _stage_event(db, job, "cover.unavailable", "视频封面不可用，不影响笔记处理")

        transcript: Transcript | None = None
        segments = []
        subtitle = _step(
            db, job, "FETCH_SUBTITLE", 25, {"asset": asset.id, "subtitle_tracks": len(resolved.subtitles)}
        )
        selected_track = None
        raw_segments = []
        subtitle_failures: list[tuple[str, str]] = []

        def fetch_track(track: SubtitleTrack) -> list[dict[str, Any]]:
            _stage_event(
                db,
                job,
                "subtitle.requested",
                "正在获取平台字幕",
                language=track.language,
                available_tracks=len(resolved.subtitles),
            )
            return audited_call(
                db,
                job_id=job.id,
                capability="VIDEO_SUBTITLE",
                provider="bilibili",
                operation="subtitle",
                request_meta={
                    "bvid": resolved.bvid,
                    "cid": resolved.cid,
                    "track_id": track.track_id,
                    "language": track.language,
                    "generated": track.generated,
                    "endpoint": track.endpoint,
                    "url_sha256": hashlib.sha256(track.url.encode()).hexdigest(),
                },
                call=lambda: resolver.fetch_subtitle_segments(track),
                response_meta=lambda items: _subtitle_decision(asset, track, items),
            )

        try:
            selected_track, raw_segments, subtitle_failures = first_usable_subtitle(
                resolved.subtitles, fetch_track
            )
        except VideoResolveError as exc:
            if exc.code == "VIDEO_LOGIN_REQUIRED":
                raise NeedsUser("VIDEO_LOGIN_REQUIRED", str(exc)) from exc
            raise
        for language, reason in subtitle_failures:
            _stage_event(
                db,
                job,
                "subtitle.track.unavailable",
                "字幕轨不可用，已尝试其他轨道或准备音频回退",
                language=language,
                reason=reason,
            )

        subtitle_decision = (
            _subtitle_decision(asset, selected_track, raw_segments) if selected_track else None
        )
        if selected_track and subtitle_decision and subtitle_decision["accepted"]:
            transcript, segments = materialize_transcript(
                db,
                source,
                asset,
                raw_segments,
                source_kind=selected_track.source_kind,
                language=selected_track.language or "zh-CN",
                metadata={
                    "requested_bvid": resolved.bvid,
                    "requested_cid": resolved.cid,
                    "subtitle_endpoint": selected_track.endpoint,
                    "subtitle_track_id": selected_track.track_id,
                    "subtitle_language": selected_track.language,
                    "subtitle_generated": selected_track.generated,
                    "subtitle_url_sha256": subtitle_decision["url_sha256"],
                    "subtitle_body_sha256": subtitle_decision["body_sha256"],
                    "timeline_ratio": subtitle_decision["timeline_ratio"],
                    "validation_status": subtitle_decision["validation_status"],
                    "validation_reasons": subtitle_decision["validation_reasons"],
                    "validation_version": SUBTITLE_VALIDATION_VERSION,
                },
            )
            _stage_event(
                db,
                job,
                "subtitle.materialized",
                "平台字幕已转换为时间码片段",
                segments=len(segments),
            )
            _done(
                db,
                job,
                subtitle,
                42,
                {
                    "source": "subtitle",
                    "accepted": True,
                    "subtitle": subtitle_decision,
                    "transcript_id": transcript.id,
                    "failed_tracks": subtitle_failures,
                },
            )
            skipped = _step(db, job, "DOWNLOAD_AUDIO", 43, {"reason": "subtitle_available"})
            _done(db, job, skipped, 43, {"skipped": True})
            skipped = _step(db, job, "ASR", 44, {"reason": "subtitle_available"})
            _done(db, job, skipped, 44, {"skipped": True})
        else:
            reasons = (
                subtitle_decision["validation_reasons"]
                if subtitle_decision
                else ["PLATFORM_SUBTITLE_UNAVAILABLE"]
            )
            _done(
                db,
                job,
                subtitle,
                28,
                {
                    "source": "subtitle_rejected" if subtitle_decision else "none",
                    "accepted": False,
                    "subtitle": subtitle_decision,
                    "validation_reasons": reasons,
                    "failed_tracks": subtitle_failures,
                },
            )
            audio_path, transcript, segments = _download_and_transcribe_audio(
                db,
                job,
                settings,
                source,
                asset,
                resolved.canonical_url,
                resolved.bvid,
                cookie_path,
                reasons,
            )

        normalize = _step(
            db, job, "NORMALIZE_TRANSCRIPT", 64, {"transcript_id": transcript.id if transcript else ""}
        )
        if transcript is None or not segments:
            raise NeedsUser("TRANSCRIPT_MISSING", "未获得可用于笔记生成的时间码转写")
        _trusted_transcript_or_raise(db, source, asset, transcript, segments)
        _done(
            db,
            job,
            normalize,
            68,
            {
                "segments": len(segments),
                "source": transcript.source_kind,
                "validation_status": transcript.metadata_json.get("validation_status"),
                "timeline_ratio": transcript.metadata_json.get("timeline_ratio"),
            },
        )

        correction = _step(
            db,
            job,
            "CORRECT_TRANSCRIPT",
            69,
            {
                "transcript_id": transcript.id,
                "segments": len(segments),
                "prompt_supplement_hash": prompt_supplement_hash(db, "transcript_correction"),
            },
        )
        _stage_event(db, job, "transcript.correction.requested", "正在使用 AI 校对完整转写")
        try:
            segments = correct_transcript(db, settings, asset, transcript, segments, job)
        except Exception as exc:
            raise NeedsUser("TRANSCRIPT_CORRECTION_FAILED", f"转写校对失败：{str(exc)[:240]}") from exc
        corrected_count = sum(item.correction_status == "CORRECTED" for item in segments)
        _done(
            db,
            job,
            correction,
            70,
            {"corrected": corrected_count, "review": len(segments) - corrected_count},
        )

        extract = _step(
            db,
            job,
            "EXTRACT_TRAVEL_FACTS",
            72,
            {
                "transcript": transcript.id,
                "prompt_supplement_hash": prompt_supplement_hash(db, "travel_place_extraction"),
            },
        )
        _stage_event(db, job, "places.requested", "正在从完整转写提取旅行地点与观察")
        try:
            mentions = extract_place_mentions(db, settings, asset, None, segments, job)
        except ProviderUnavailable as exc:
            raise NeedsUser(exc.code, str(exc)) from exc
        _done(db, job, extract, 80, {"mentions": len(mentions)})

        note_step = _step(
            db,
            job,
            "GENERATE_AI_NOTE",
            82,
            {
                "transcript": transcript.id,
                "version": transcript.version,
                "place_mentions": len(mentions),
                "prompt_supplement_hash": prompt_supplement_hash(db, "video_note_summary"),
            },
        )
        _stage_event(db, job, "note.requested", "正在基于已验证地点生成 AI 视频笔记", segments=len(segments))
        try:
            note_version = generate_note(db, settings, asset, transcript, segments, job, mentions)
        except ProviderUnavailable as exc:
            raise NeedsUser(exc.code, str(exc)) from exc
        for mention in mentions:
            mention.ai_note_version_id = note_version.id
        db.commit()
        _done(
            db,
            job,
            note_step,
            87,
            {
                "note_id": note_version.ai_note_id,
                "note_version_id": note_version.id,
                "version": note_version.version,
            },
        )

        poi = _step(db, job, "RESOLVE_POI", 88, {"mentions": len(mentions), "provider": "AMap"})
        _stage_event(db, job, "poi.requested", "正在校验地点 POI", mentions=len(mentions))
        confirmed, unresolved = resolve_mentions_with_amap(
            db,
            settings,
            mentions,
            store.get("amap:web-service-key") or settings.amap_api_key,
        )
        _done(
            db,
            job,
            poi,
            92,
            {
                "confirmed": confirmed,
                "unresolved": unresolved,
                "amap_configured": bool(store.get("amap:web-service-key") or settings.amap_api_key),
            },
        )
        place_notes = _step(db, job, "BUILD_PLACE_NOTES", 93, {"confirmed": confirmed})
        built = build_place_notes(db, asset, mentions)
        _done(db, job, place_notes, 95, {"built": built})

        screenshot_plan = _step(db, job, "PLAN_SCREENSHOTS", 92, {"note_version": note_version.id})
        _stage_event(db, job, "screenshot.plan", "正在按章节和主要地点规划代表截图")
        plans = plan_screenshots(db, asset, note_version)
        _done(db, job, screenshot_plan, 93, {"planned": len(plans)})

        video_for_frames: Path | None = None
        download_frames = _step(
            db, job, "DOWNLOAD_VIDEO_FOR_FRAMES", 94, {"planned": len(plans), "max_height": 720}
        )
        if not plans:
            screenshot_error = "SCREENSHOT_PLAN_EMPTY: 未找到可用于截图的章节或转写时间轴"
            _skip_step(db, job, download_frames, 95, screenshot_error)
        else:
            _stage_event(db, job, "screenshot.download", "正在下载受限清晰度视频用于抽帧", planned=len(plans))
            try:
                video_for_frames = download_screenshot_video(settings, resolved.canonical_url, cookie_path)
                _done(
                    db,
                    job,
                    download_frames,
                    95,
                    {"cache_path": str(video_for_frames), "bytes": video_for_frames.stat().st_size},
                )
            except MediaDownloadError as exc:
                if exc.code == "VIDEO_LOGIN_REQUIRED":
                    raise NeedsUser(
                        "VIDEO_LOGIN_REQUIRED",
                        "Bilibili 登录已失效或访问被平台拦截，请扫码登录后继续或跳过截图",
                    ) from exc
                screenshot_error = f"VIDEO_SCREENSHOTS_UNAVAILABLE: {str(exc)[:240]}"
                _fail_step(db, download_frames, RuntimeError(screenshot_error))
                _stage_event(
                    db,
                    job,
                    "screenshot.download.unavailable",
                    "截图视频不可用，继续交付文字笔记",
                    reason=screenshot_error,
                )

        extract_frames = _step(db, job, "EXTRACT_SCREENSHOTS", 96, {"planned": len(plans)})
        if video_for_frames is None:
            _skip_step(db, job, extract_frames, 97, "截图视频不可用")
        else:
            _stage_event(db, job, "screenshot.extract", "正在抽取并筛选代表截图", planned=len(plans))
            try:
                screenshot_count, extract_error = extract_screenshots(
                    db, settings, asset, plans, video_for_frames
                )
                screenshot_error = screenshot_error or extract_error
                _done(
                    db,
                    job,
                    extract_frames,
                    97,
                    {"planned": len(plans), "ready": screenshot_count, "error": screenshot_error},
                )
            except Exception as exc:
                screenshot_error = f"SCREENSHOT_EXTRACTION_FAILED: {str(exc)[:240]}"
                _fail_step(db, extract_frames, RuntimeError(screenshot_error))
                _stage_event(
                    db,
                    job,
                    "screenshot.extract.failed",
                    "代表截图抽取失败，继续交付文字笔记",
                    reason=screenshot_error,
                )

        materialize = _step(db, job, "MATERIALIZE", 98, {"note": note_version.ai_note_id})
        content = db.scalar(
            select(ContentItem).where(
                ContentItem.source_id == source.id, ContentItem.content_type == ContentType.VIDEO_NOTE.value
            )
        )
        if content is None:
            content = ContentItem(
                content_type=ContentType.VIDEO_NOTE.value,
                title=asset.title,
                summary=note_version.overview,
                source_id=source.id,
                structured_json={},
            )
            db.add(content)
        content.summary = note_version.overview
        content.status = "COMPLETED"
        content.structured_json = {
            "video_asset_id": asset.id,
            "note_id": note_version.ai_note_id,
            "note_version_id": note_version.id,
            "place_mentions": len(mentions),
            "confirmed_places": confirmed,
            "unresolved_places": unresolved,
            "screenshots": screenshot_count,
            "screenshot_error": screenshot_error,
        }
        db.flush()
        job.result_content_id = content.id
        _done(db, job, materialize, 99, {"content_id": content.id})
        clean = _step(db, job, "CLEAN_CACHE", 99, {"audio": audio_path.name if audio_path else None})
        if cookie_path:
            cookie_path.unlink(missing_ok=True)
        _done(
            db,
            job,
            clean,
            100,
            {
                "replay_cache_retained": bool(audio_path or video_for_frames),
                "ttl_hours": settings.video_cache_ttl_hours,
            },
        )
        job.status = (
            JobStatus.PARTIAL_SUCCESS.value
            if (
                unresolved
                or not (store.get("amap:web-service-key") or settings.amap_api_key)
                or screenshot_error
            )
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
            detail={
                "note_id": note_version.ai_note_id,
                "partial": job.status == JobStatus.PARTIAL_SUCCESS.value,
            },
            commit=False,
        )
        db.commit()
    except JobCancelled:
        db.rollback()
        cancelled = db.get(Job, job_id)
        if cancelled and cancelled.status == JobStatus.CANCELLED.value:
            step = db.scalar(
                select(JobStep).where(
                    JobStep.job_id == cancelled.id, JobStep.step_name == cancelled.current_step
                )
            )
            if step:
                step.status = "CANCELLED"
                step.finished_at = utc_now()
                step.error = None
            cancelled.lease_owner = None
            cancelled.lease_expire_at = None
            cancelled.heartbeat_at = utc_now()
            record_event(
                db,
                "job.cancel.observed",
                "Worker 已停止该任务的当前阶段并释放执行 lease",
                component="video-pipeline",
                entity_type="job",
                entity_id=cancelled.id,
                detail={"step": cancelled.current_step},
                commit=False,
            )
            db.commit()
    except NeedsUser as exc:
        current_step = db.scalar(
            select(JobStep).where(
                JobStep.job_id == job.id,
                JobStep.step_name == job.current_step,
            )
        )
        if current_step and current_step.status == "RUNNING":
            current_step.status = "FAILED"
            current_step.error = str(exc)[:4000]
            current_step.finished_at = utc_now()
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
        db.rollback()
        job = db.get(Job, job_id)
        if job is None:
            raise
        if isinstance(exc, VideoResolveError):
            job.error_code = exc.code
        current_step = db.scalar(
            select(JobStep).where(
                JobStep.job_id == job.id,
                JobStep.step_name == job.current_step,
            )
        )
        if current_step and current_step.status == "RUNNING":
            current_step.status = "FAILED"
            current_step.error = str(exc)[:4000]
            current_step.finished_at = utc_now()
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
        if cookie_path:
            cookie_path.unlink(missing_ok=True)


def _process_video_replay(db: Session, job: Job, settings: Settings, from_step: str) -> None:
    start = VIDEO_STEPS.index(from_step)
    metadata_artifact = db.scalar(
        select(JobStepArtifact).where(
            JobStepArtifact.job_id == job.id,
            JobStepArtifact.step_name == "FETCH_METADATA",
            JobStepArtifact.status == "AVAILABLE",
        )
    )
    artifact_asset_id = (
        metadata_artifact.artifact_ref_json.get("video_asset_id") if metadata_artifact else None
    )
    asset = db.get(VideoAsset, str(job.payload_json.get("video_asset_id") or artifact_asset_id or ""))
    if asset is None:
        canonical_url = str(job.payload_json.get("locator") or "").rstrip("/")
        asset = db.scalar(select(VideoAsset).where(VideoAsset.canonical_url == canonical_url))
    source = db.get(Source, asset.source_id) if asset else None
    if source is None or asset is None:
        raise NeedsUser("REPLAY_ARTIFACT_MISSING", "视频来源或资产已不可用")
    job.payload_json = {
        **job.payload_json,
        "source_id": source.id,
        "video_asset_id": asset.id,
        "title": asset.title,
    }
    transcript = db.scalar(
        select(Transcript).where(Transcript.video_asset_id == asset.id).order_by(Transcript.version.desc())
    )
    snapshot_id = transcript.metadata_json.get("snapshot_id") if transcript else None
    segments = (
        db.scalars(select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)).all()
        if snapshot_id
        else []
    )
    if (transcript is None or not segments) and start > VIDEO_STEPS.index("DOWNLOAD_AUDIO"):
        raise NeedsUser("REPLAY_ARTIFACT_MISSING", "完整转写中间产物已不可用")
    job.status = JobStatus.RUNNING.value
    job.started_at = utc_now()
    db.commit()
    store = build_secret_store(settings.secret_store, settings.data_dir)
    cookie = store.get(settings.video_cookie_secret_key)
    cookie_path = _temporary_cookie_file(settings, job.id, cookie) if cookie else None
    screenshot_error: str | None = None
    screenshot_count = (
        db.scalar(
            select(func.count(VideoScreenshot.id)).where(
                VideoScreenshot.video_asset_id == asset.id, VideoScreenshot.status == "READY"
            )
        )
        or 0
    )
    try:
        if start <= VIDEO_STEPS.index("DOWNLOAD_AUDIO"):
            _, transcript, segments = _download_and_transcribe_audio(
                db,
                job,
                settings,
                source,
                asset,
                asset.canonical_url,
                asset.bvid or "",
                cookie_path,
            )
            step = _step(
                db,
                job,
                "NORMALIZE_TRANSCRIPT",
                64,
                {"transcript_id": transcript.id},
            )
            _done(db, job, step, 68, {"segments": len(segments), "source": transcript.source_kind})

        if transcript is None:
            raise NeedsUser("REPLAY_ARTIFACT_MISSING", "完整转写中间产物已不可用")
        _trusted_transcript_or_raise(db, source, asset, transcript, segments)

        if start <= VIDEO_STEPS.index("CORRECT_TRANSCRIPT"):
            step = _step(
                db,
                job,
                "CORRECT_TRANSCRIPT",
                69,
                {
                    "transcript_id": transcript.id,
                    "prompt_supplement_hash": prompt_supplement_hash(db, "transcript_correction"),
                },
            )
            segments = correct_transcript(db, settings, asset, transcript, segments, job)
            _done(db, job, step, 70, {"corrected": len(segments)})

        note = db.scalar(select(AINote).where(AINote.video_asset_id == asset.id))
        note_version = (
            db.get(AINoteVersion, note.current_version_id) if note and note.current_version_id else None
        )
        mentions = db.scalars(select(PlaceMention).where(PlaceMention.video_asset_id == asset.id)).all()
        if start <= VIDEO_STEPS.index("EXTRACT_TRAVEL_FACTS"):
            for mention in mentions:
                if mention.extraction_status != "USER_REJECTED":
                    db.delete(mention)
            db.commit()
            step = _step(
                db,
                job,
                "EXTRACT_TRAVEL_FACTS",
                72,
                {
                    "transcript": transcript.id,
                    "prompt_supplement_hash": prompt_supplement_hash(db, "travel_place_extraction"),
                },
            )
            mentions = extract_place_mentions(db, settings, asset, None, segments, job)
            _done(db, job, step, 80, {"mentions": len(mentions)})
        if start <= VIDEO_STEPS.index("GENERATE_AI_NOTE"):
            step = _step(
                db,
                job,
                "GENERATE_AI_NOTE",
                82,
                {
                    "transcript": transcript.id,
                    "place_mentions": len(mentions),
                    "prompt_supplement_hash": prompt_supplement_hash(db, "video_note_summary"),
                },
            )
            note_version = generate_note(db, settings, asset, transcript, segments, job, mentions)
            for mention in mentions:
                mention.ai_note_version_id = note_version.id
            db.commit()
            _done(
                db,
                job,
                step,
                87,
                {"note_id": note_version.ai_note_id, "note_version_id": note_version.id},
            )
        if note_version is None:
            raise NeedsUser("REPLAY_ARTIFACT_MISSING", "AI 笔记中间产物已不可用")

        confirmed = sum(mention.resolution_status == "CONFIRMED" for mention in mentions)
        unresolved = len(mentions) - confirmed
        if start <= VIDEO_STEPS.index("RESOLVE_POI"):
            step = _step(db, job, "RESOLVE_POI", 88, {"mentions": len(mentions), "provider": "AMap"})
            confirmed, unresolved = resolve_mentions_with_amap(
                db, settings, mentions, store.get("amap:web-service-key") or settings.amap_api_key
            )
            _done(db, job, step, 92, {"confirmed": confirmed, "unresolved": unresolved})
        if start <= VIDEO_STEPS.index("BUILD_PLACE_NOTES"):
            step = _step(db, job, "BUILD_PLACE_NOTES", 93, {"confirmed": confirmed})
            _done(db, job, step, 95, {"built": build_place_notes(db, asset, mentions)})

        plans = []
        if start <= VIDEO_STEPS.index("PLAN_SCREENSHOTS"):
            step = _step(db, job, "PLAN_SCREENSHOTS", 92, {"note_version": note_version.id})
            plans = plan_screenshots(db, asset, note_version)
            _done(db, job, step, 93, {"planned": len(plans)})
        else:
            plans = db.scalars(
                select(VideoScreenshot).where(
                    VideoScreenshot.video_asset_id == asset.id,
                    VideoScreenshot.ai_note_version_id == note_version.id,
                )
            ).all()
        video_path: Path | None = None
        skip_login_step = str(job.payload_json.get("skip_login_step") or "")
        if start <= VIDEO_STEPS.index("DOWNLOAD_VIDEO_FOR_FRAMES"):
            step = _step(db, job, "DOWNLOAD_VIDEO_FOR_FRAMES", 94, {"planned": len(plans)})
            if skip_login_step == "DOWNLOAD_VIDEO_FOR_FRAMES":
                screenshot_error = "SCREENSHOTS_SKIPPED_BY_USER: 用户选择跳过登录受限截图"
                _skip_step(db, job, step, 95, "用户选择跳过登录受限截图")
            elif plans:
                try:
                    video_path = download_screenshot_video(settings, asset.canonical_url, cookie_path)
                except MediaDownloadError as exc:
                    if exc.code == "VIDEO_LOGIN_REQUIRED":
                        raise NeedsUser(
                            "VIDEO_LOGIN_REQUIRED",
                            "Bilibili 登录已失效或访问被平台拦截，请扫码登录后继续或跳过截图",
                        ) from exc
                    raise
                _done(db, job, step, 95, {"cache_path": str(video_path)})
            else:
                _skip_step(db, job, step, 95, "没有可执行的截图计划")
        else:
            video_artifact = db.scalar(
                select(JobStepArtifact).where(
                    JobStepArtifact.job_id == job.id,
                    JobStepArtifact.step_name == "DOWNLOAD_VIDEO_FOR_FRAMES",
                    JobStepArtifact.status == "AVAILABLE",
                )
            )
            cached_path = video_artifact.artifact_ref_json.get("cache_path") if video_artifact else None
            if cached_path and Path(str(cached_path)).is_file():
                video_path = Path(str(cached_path))
        if start <= VIDEO_STEPS.index("EXTRACT_SCREENSHOTS"):
            step = _step(db, job, "EXTRACT_SCREENSHOTS", 96, {"planned": len(plans)})
            if video_path:
                screenshot_count, screenshot_error = extract_screenshots(
                    db, settings, asset, plans, video_path
                )
                _done(db, job, step, 97, {"ready": screenshot_count, "error": screenshot_error})
            else:
                _skip_step(db, job, step, 97, "截图视频不可用")

        content = db.scalar(
            select(ContentItem).where(
                ContentItem.source_id == source.id, ContentItem.content_type == ContentType.VIDEO_NOTE.value
            )
        )
        if content is None:
            content = ContentItem(
                content_type=ContentType.VIDEO_NOTE.value,
                title=asset.title,
                summary=note_version.overview,
                source_id=source.id,
            )
            db.add(content)
        content.summary = note_version.overview
        content.status = "COMPLETED"
        content.structured_json = {
            "video_asset_id": asset.id,
            "note_id": note_version.ai_note_id,
            "note_version_id": note_version.id,
            "place_mentions": len(mentions),
            "confirmed_places": confirmed,
            "unresolved_places": unresolved,
            "screenshots": screenshot_count,
            "screenshot_error": screenshot_error,
        }
        db.flush()
        step = _step(db, job, "MATERIALIZE", 98, {"note": note_version.ai_note_id})
        job.result_content_id = content.id
        _done(db, job, step, 99, {"content_id": content.id})
        clean = _step(db, job, "CLEAN_CACHE", 99, {"replay": True})
        _done(db, job, clean, 100, {"replay_cache_retained": True})
        job.status = (
            JobStatus.PARTIAL_SUCCESS.value if unresolved or screenshot_error else JobStatus.COMPLETED.value
        )
        job.current_step, job.progress, job.finished_at = "CLEAN_CACHE", 100, utc_now()
        job.lease_owner = job.lease_expire_at = job.error = job.error_code = None
        job.payload_json = {
            key: value
            for key, value in job.payload_json.items()
            if key not in {"replay_from_step", "skip_login_step"}
        }
        record_event(
            db,
            "job.step_replay.completed",
            f"已从 {from_step} 完成续跑",
            component="video-pipeline",
            entity_type="job",
            entity_id=job.id,
            detail={"step": from_step},
            commit=False,
        )
        db.commit()
    finally:
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
