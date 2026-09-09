from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import platform
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from zhijian.ai.domain_context import DOMAIN_PACK_PREFIX, DomainPack
from zhijian.ai.model_registry import model_profile_from_value, probe_model_profile
from zhijian.ai.policies import resolve_stage_policy, validate_stage_policy
from zhijian.ai.resource_manager import local_ai_resource_manager
from zhijian.ai.schemas import AIStagePolicy
from zhijian.ai.stages import STAGE_SPECS, stage_spec
from zhijian.core.config import Settings, get_settings
from zhijian.core.ids import new_id
from zhijian.core.secret_store import SecretStore
from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import (
    AccessSession,
    AINoteVersion,
    Claim,
    ContentItem,
    Evidence,
    ExternalCallAudit,
    Job,
    JobStep,
    MapMarkerState,
    Place,
    PlaceDeletionTombstone,
    PlaceInsightItem,
    PlaceMention,
    PlaceObservation,
    PlaceUserNote,
    PlaceUserOverlay,
    PlaceVisitWindow,
    RouteDraft,
    RouteDraftItem,
    Segment,
    Setting,
    Snapshot,
    Source,
    SystemEvent,
    VideoScreenshot,
)
from zhijian.db.session import get_db
from zhijian.domain.enums import JobStatus, ResolutionStatus
from zhijian.domain.schemas import (
    AMapConfig,
    BulkPlaceUpdate,
    CaptureRequest,
    CaptureResponse,
    ContentView,
    GeneralConfig,
    HardDeletePlacesRequest,
    JobView,
    ManualPlaceCreate,
    MapMarker,
    MapMarkerCreate,
    MapOverviewView,
    ModelProfileConfig,
    ModelRoutingConfig,
    NearbyPOIRequest,
    PlaceDetailView,
    PlaceInsightUpdate,
    PlaceInsightView,
    PlaceListView,
    PlaceNoteUpdate,
    PlaceOverlayUpdate,
    PlacePreview,
    PlaceVisitWindowUpdate,
    PlaceVisitWindowView,
    POIReviewDecision,
    POISearchRequest,
    ProfileConfig,
    PromptSupplementsConfig,
    ProviderConfig,
    RouteDraftCreate,
    RouteDraftMetadataUpdate,
    RouteDraftUpdate,
    RouteDraftView,
    SessionRequest,
    StepReplayRequest,
    TranscriptProcessingConfig,
)
from zhijian.providers.amap import AMapPOIProvider
from zhijian.providers.llm import (
    LLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderRequestOptions,
)
from zhijian.providers.runtime import hardware_report, runtime_report
from zhijian.services.audit import record_event
from zhijian.services.auth import (
    assert_auth_attempt_allowed,
    clear_auth_failures,
    create_session,
    ensure_lan_token,
    get_secret_store,
    record_auth_failure,
    require_session,
    rotate_lan_token,
    token_hash,
    verify_lan_token,
)
from zhijian.services.bilibili_auth import (
    BilibiliAuthError,
    poll_bilibili_login,
    start_bilibili_login,
)
from zhijian.services.capture import create_capture_job, safe_upload_path
from zhijian.services.input_normalizer import normalize_capture_input
from zhijian.services.job_replay import queue_login_step_skip, queue_step_replay, replay_options
from zhijian.services.place_knowledge import aggregate_place_knowledge, normalize_insight
from zhijian.services.runtime_monitor import read_runtime_metrics_sample
from zhijian.services.source_retention import prune_source_if_orphan, source_deletion_state
from zhijian.services.video_support import (
    PROMPT_CORE_CONTRACTS,
    PROMPT_SUPPLEMENT_SETTING_KEY,
    materialize_place_insights,
    prompt_supplement_hash,
    transcript_processing_config,
)

router = APIRouter()
Protected = Annotated[object | None, Depends(require_session)]
JOB_STALE_AFTER_SECONDS = 90
LLM_JOB_STALE_AFTER_SECONDS = 500
LLM_JOB_STEPS = {
    "CORRECT_TRANSCRIPT",
    "GENERATE_AI_NOTE",
    "EXTRACT_TRAVEL_FACTS",
    "BUILD_PLACE_NOTES",
}


def _safe_step_input(step: JobStep | None) -> dict:
    return step.input_json if step and isinstance(step.input_json, dict) else {}


def _job_step(db: Session, job_id: str, name: str) -> JobStep | None:
    return db.scalar(select(JobStep).where(JobStep.job_id == job_id, JobStep.step_name == name))


def job_view(job: Job, db: Session | None = None) -> JobView:
    step = _job_step(db, job.id, job.current_step) if db else None
    step_input = _safe_step_input(step)
    last_activity, last_activity_source = next(
        (
            (value, source)
            for value, source in (
                (job.heartbeat_at, "JOB_HEARTBEAT"),
                (step.finished_at if step else None, "STEP_FINISHED"),
                (step.started_at if step else None, "STEP_STARTED"),
                (job.started_at, "JOB_STARTED"),
                (job.created_at, "JOB_CREATED"),
            )
            if value is not None
        ),
        (None, None),
    )
    model_step = job.current_step if job.current_step in LLM_JOB_STEPS else None
    if db and model_step is None:
        latest_llm_step = db.scalar(
            select(JobStep)
            .where(JobStep.job_id == job.id, JobStep.step_name.in_(LLM_JOB_STEPS))
            .order_by(JobStep.started_at.desc())
        )
        model_step = latest_llm_step.step_name if latest_llm_step else None
        step_input = _safe_step_input(latest_llm_step) if latest_llm_step else step_input
    provider = step_input.get("provider") if model_step else None
    model = step_input.get("model") if model_step else None
    if db and model_step and not (provider and model):
        routing = db.get(Setting, "model-routing")
        route = routing.value_json if routing and isinstance(routing.value_json, dict) else {}
        profile_id = route.get("primary_id")
        profile = db.get(Setting, f"model-profile:{profile_id}") if profile_id else None
        profile_value = profile.value_json if profile and isinstance(profile.value_json, dict) else {}
        provider = profile_value.get("provider") or provider
        model = profile_value.get("model") or model
    completion_summary = None
    if job.status == JobStatus.PARTIAL_SUCCESS.value and db and job.result_content_id:
        content = db.get(ContentItem, job.result_content_id)
        structured = content.structured_json if content and isinstance(content.structured_json, dict) else {}
        unresolved = int(structured.get("unresolved_places") or 0)
        if not structured.get("amap_configured", True):
            completion_summary = "所有处理步骤已完成；AI 笔记已生成，未配置高德 POI"
        elif unresolved:
            completion_summary = f"所有处理步骤已完成；AI 笔记已生成，{unresolved} 个地点待确认"
        else:
            completion_summary = "所有处理步骤已完成；部分补充信息待处理"
    now = utc_now()
    last_activity_age = (
        max(0, round((now - as_utc(last_activity)).total_seconds())) if last_activity else None
    )
    runtime_state = (
        "STALLED"
        if job.status == JobStatus.RUNNING.value
        and (
            last_activity_age is None
            or last_activity_age
            > (LLM_JOB_STALE_AFTER_SECONDS if job.current_step in LLM_JOB_STEPS else JOB_STALE_AFTER_SECONDS)
        )
        else "ACTIVE"
        if job.status == JobStatus.RUNNING.value
        else "IDLE"
    )
    return JobView(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        current_step=job.current_step,
        progress=job.progress,
        title=str(job.payload_json.get("title") or job.payload_json.get("locator") or "未命名任务"),
        error=job.error,
        error_code=job.error_code,
        created_at=as_utc(job.created_at),
        started_at=as_utc(job.started_at) if job.started_at else None,
        finished_at=as_utc(job.finished_at) if job.finished_at else None,
        retry_count=job.retry_count,
        worker_id=job.lease_owner,
        heartbeat_at=as_utc(job.heartbeat_at) if job.heartbeat_at else None,
        last_activity_at=as_utc(last_activity) if last_activity else None,
        current_step_status=step.status if step else None,
        current_step_started_at=as_utc(step.started_at) if step and step.started_at else None,
        current_step_message=(step.output_json or {}).get("message") if step else None,
        runtime_state=runtime_state,
        last_activity_age_seconds=last_activity_age,
        last_activity_source=last_activity_source,
        completion_summary=completion_summary,
        model_step=model_step,
        provider=str(provider) if provider else None,
        model=str(model) if model else None,
    )


def content_view(item: ContentItem) -> ContentView:
    return ContentView(
        id=item.id,
        content_type=item.content_type,
        title=item.title,
        summary=item.summary,
        status=item.status,
        user_state=item.user_state,
        structured=item.structured_json,
        updated_at=item.updated_at,
    )


def preview_for_place(db: Session, place: Place) -> PlacePreview:
    observations = db.scalars(
        select(PlaceObservation).where(PlaceObservation.place_id == place.id).limit(5)
    ).all()
    return PlacePreview(
        id=place.id,
        name=place.name,
        address=place.address,
        place_type=place.place_type,
        summary=place.summary,
        user_state=place.user_state,
        observations=[
            {"type": observation.observation_type, **observation.value_json} for observation in observations
        ],
    )


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "zhijian"}


@router.post("/api/auth/session")
def exchange_session(
    payload: SessionRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
    settings: Settings = Depends(get_settings),
) -> dict:
    client_host = request.client.host if request.client else "unknown"
    assert_auth_attempt_allowed(client_host, settings)
    if not verify_lan_token(payload.token, store):
        record_auth_failure(client_host, settings)
        record_event(
            db,
            "auth.session.denied",
            "局域网配对码校验失败",
            level="WARNING",
            actor=client_host,
        )
        raise HTTPException(status_code=401, detail="访问 Token 无效")
    clear_auth_failures(client_host)
    raw, session = create_session(db, payload.client_label, settings.session_ttl_hours)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=settings.session_ttl_hours * 3600,
        expires=as_utc(session.expires_at),
        path="/",
    )
    record_event(db, "auth.session.created", "新设备已建立可信会话", actor=client_host)
    return {"status": "ok", "expires_at": session.expires_at}


@router.get("/api/admin/lan-token")
def read_lan_token(
    _: Protected,
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    token = ensure_lan_token(store)
    return {"token": token, "display": token, "digits": 4}


@router.post("/api/admin/lan-token/rotate")
def rotate_lan_access_token(
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    token = rotate_lan_token(store)
    db.query(AccessSession).delete()
    record_event(db, "auth.token.rotated", "局域网配对码已轮换，已有设备会话已失效")
    return {"token": token, "display": token, "digits": 4, "sessions_revoked": True}


@router.get("/api/status")
def status_view(
    _: Protected,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    checks = runtime_report(settings.ollama_base_url, settings.whisper_binary, settings.whisper_model)
    hardware = hardware_report()
    heartbeat = db.get(Setting, "runtime:worker-heartbeat")
    worker_running = False
    if heartbeat:
        heartbeat_at = heartbeat.updated_at
        if heartbeat_at.tzinfo is None:
            heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
        age = (utc_now() - heartbeat_at).total_seconds()
        worker_running = age <= max(30, settings.worker_heartbeat_seconds * 3)
    metrics = read_runtime_metrics_sample(db)
    return {
        "node_name": hardware["machine_name"],
        "deployment_target": "mac_mini",
        "system": platform.system(),
        "release": hardware["os_version"],
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "data_dir": str(settings.data_dir.resolve()),
        "database": str(settings.database_path.resolve()),
        "services": {
            "api": "RUNNING",
            "worker": "RUNNING" if worker_running else "STALE",
            "sqlite": "RUNNING",
        },
        "runtime": {
            "ollama": settings.ollama_base_url,
            "asr": next((item["detail"] for item in checks if item["name"] == "whisper.cpp"), "未检测"),
        },
        "hardware": hardware,
        "metrics": metrics,
        "lan_url": f"http://{hardware['lan_ip']}:{settings.port}",
        "runtime_checks": checks,
    }


@router.get("/api/dashboard")
def dashboard(_: Protected, db: Session = Depends(get_db)) -> dict:
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(5)).all()
    contents = db.scalars(select(ContentItem).order_by(ContentItem.updated_at.desc()).limit(6)).all()
    counts = dict(db.execute(select(Job.status, func.count(Job.id)).group_by(Job.status)).all())
    return {
        "job_counts": counts,
        "jobs": [job_view(job, db).model_dump() for job in jobs],
        "contents": [content_view(item).model_dump() for item in contents],
    }


@router.post("/api/capture", response_model=CaptureResponse)
def capture(
    payload: CaptureRequest,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CaptureResponse:
    for stage, override in payload.ai_overrides.items():
        try:
            if {"stage", "capability", "version"} & set(override):
                raise ValueError("任务阶段覆盖不能重写 stage、capability 或版本")
            policy = AIStagePolicy(
                stage=stage,
                capability=stage_spec(stage).capability,
                **override,
            )
            validate_stage_policy(policy, _stage_profiles(db))
            missing_pack = any(
                db.get(Setting, f"{DOMAIN_PACK_PREFIX}{pack_id}") is None
                for pack_id in policy.domain_pack_ids
            )
            if missing_pack:
                raise ValueError("任务阶段覆盖引用了不存在的领域包")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    raw_input = str(payload.url or payload.text or "")
    if not raw_input:
        raise HTTPException(status_code=422, detail="URL 与正文至少提供一项")
    normalized = normalize_capture_input(raw_input)
    if normalized.kind == "MULTIPLE_URLS":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CAPTURE_MULTIPLE_URLS",
                "message": "检测到多个不同链接，请只保留一个后提交",
                "candidates": normalized.candidates,
            },
        )
    is_url = normalized.selected_url is not None
    locator = normalized.selected_url or "text://local"
    metadata = {
        "capture_input_kind": normalized.kind,
        "selected_url": normalized.selected_url,
        "candidate_count": len(normalized.candidates),
        "discarded_text_length": normalized.discarded_text_length,
        "raw_input_hash": normalized.raw_input_hash,
    }
    source, job = create_capture_job(
        db,
        settings,
        locator=locator,
        source_type="URL" if is_url else "TEXT",
        title=payload.title or "",
        text="" if is_url else raw_input,
        metadata=metadata,
        ai_overrides=payload.ai_overrides,
    )
    return CaptureResponse(
        source_id=source.id,
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
    )


@router.post("/api/capture/file", response_model=CaptureResponse)
async def capture_file(
    _: Protected,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CaptureResponse:
    content = await upload.read((settings.max_upload_mb + 1) * 1024 * 1024)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件超过大小限制")
    filename = Path(upload.filename or "upload.bin").name
    suffix = Path(filename).suffix.lower()
    allowed = {
        ".pdf",
        ".docx",
        ".xlsx",
        ".xlsm",
        ".png",
        ".jpg",
        ".jpeg",
        ".txt",
        ".md",
        ".mp3",
        ".m4a",
        ".wav",
        ".aac",
        ".mp4",
        ".mov",
        ".webm",
    }
    if suffix not in allowed:
        raise HTTPException(status_code=415, detail=f"暂不支持 {suffix or '未知'} 文件")
    path = safe_upload_path(settings, filename, content)
    metadata = {
        "filename": filename,
        "mime": upload.content_type,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    source, job = create_capture_job(
        db,
        settings,
        locator=str(path),
        source_type="FILE",
        title=filename,
        file_path=path,
        metadata=metadata,
    )
    return CaptureResponse(
        source_id=source.id,
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
    )


@router.get("/api/jobs", response_model=list[JobView])
def list_jobs(_: Protected, db: Session = Depends(get_db)) -> list[JobView]:
    return [job_view(job, db) for job in db.scalars(select(Job).order_by(Job.created_at.desc())).all()]


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    steps = db.scalars(select(JobStep).where(JobStep.job_id == job_id)).all()
    rank = {
        "VALIDATE_LINK": 10,
        "FETCH_METADATA": 20,
        "FETCH_SUBTITLE": 30,
        "DOWNLOAD_AUDIO": 40,
        "ASR": 50,
        "NORMALIZE_TRANSCRIPT": 60,
        "CORRECT_TRANSCRIPT": 65,
        "GENERATE_AI_NOTE": 70,
        "EXTRACT_TRAVEL_FACTS": 80,
        "RESOLVE_POI": 90,
        "BUILD_PLACE_NOTES": 100,
        "PLAN_SCREENSHOTS": 110,
        "DOWNLOAD_VIDEO_FOR_FRAMES": 120,
        "EXTRACT_SCREENSHOTS": 130,
        "RECEIVED": 10,
        "RESOLVE": 20,
        "SEGMENT": 30,
        "EXTRACT": 40,
        "MATERIALIZE": 140,
        "CLEAN_CACHE": 150,
    }
    steps.sort(key=lambda item: (rank.get(item.step_name, 999), item.started_at or job.created_at, item.id))
    events = db.scalars(
        select(SystemEvent)
        .where(SystemEvent.entity_type == "job", SystemEvent.entity_id == job_id)
        .order_by(SystemEvent.created_at.desc())
        .limit(12)
    ).all()
    return {
        **job_view(job, db).model_dump(),
        "steps": [
            {
                "name": step.step_name,
                "status": step.status,
                "progress": step.progress,
                "error": step.error,
                "started_at": as_utc(step.started_at) if step.started_at else None,
                "finished_at": as_utc(step.finished_at) if step.finished_at else None,
                "input": _redact_detail(step.input_json),
                "output": _redact_detail(step.output_json),
            }
            for step in steps
        ],
        "events": [event_view(event) for event in events],
    }


@router.get("/api/jobs/{job_id}/ai-usage")
def job_ai_usage(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    rows = db.scalars(
        select(ExternalCallAudit)
        .where(ExternalCallAudit.job_id == job_id)
        .order_by(ExternalCallAudit.created_at)
    ).all()

    def empty() -> dict[str, int]:
        return {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "duration_ms": 0,
        }

    total, local, remote = empty(), empty(), empty()
    by_stage: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    cache_hits = escalations = 0
    for row in rows:
        request_meta = row.request_meta_json or {}
        response_meta = row.response_meta_json or {}
        stage = str(request_meta.get("stage") or row.operation)
        model = str(request_meta.get("model") or row.provider)
        location = str(request_meta.get("location") or ("LOCAL" if row.provider == "ollama" else "REMOTE"))
        cache_hit = bool(request_meta.get("cache_hit"))
        values = {
            "calls": 0 if cache_hit else 1,
            "input_tokens": 0 if cache_hit else int(response_meta.get("prompt_tokens") or 0),
            "output_tokens": 0 if cache_hit else int(response_meta.get("completion_tokens") or 0),
            "cached_tokens": int(response_meta.get("cached_tokens") or 0),
            "duration_ms": int(row.duration_ms or 0),
        }
        targets = (
            total,
            local if location == "LOCAL" else remote,
            by_stage.setdefault(stage, empty()),
            by_model.setdefault(model, empty()),
        )
        for target in targets:
            for key, value in values.items():
                target[key] += value
        cache_hits += int(bool(request_meta.get("cache_hit")))
        escalations += int(bool(request_meta.get("escalated")))
    return {
        "total": total,
        "local": local,
        "remote": remote,
        "by_stage": by_stage,
        "by_model": by_model,
        "cache": {"hits": cache_hits},
        "escalations": escalations,
    }


@router.websocket("/api/jobs/{job_id}/stream")
async def stream_job(
    websocket: WebSocket,
    job_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> None:
    """Push durable job progress; reconnecting clients can always fall back to GET."""
    try:
        client_host = websocket.client.host if websocket.client else ""
        if client_host not in {"127.0.0.1", "::1", "testclient"}:
            raw_session = websocket.cookies.get(settings.session_cookie_name)
            if not raw_session:
                await websocket.close(code=4401, reason="会话已失效")
                return
            session = db.scalar(
                select(AccessSession).where(AccessSession.token_hash == token_hash(raw_session))
            )
            if session is None or as_utc(session.expires_at) < utc_now():
                await websocket.close(code=4401, reason="会话已失效")
                return

        await websocket.accept()
        while True:
            db.expire_all()
            job = db.get(Job, job_id)
            if job is None:
                await websocket.send_json({"type": "error", "detail": "任务不存在"})
                await websocket.close(code=4404)
                return
            payload = {"type": "job.progress", **job_view(job, db).model_dump(mode="json")}
            await websocket.send_json(payload)
            if job.status in {
                JobStatus.COMPLETED.value,
                JobStatus.PARTIAL_SUCCESS.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
                JobStatus.NEEDS_USER.value,
            }:
                await websocket.close(code=1000)
                return
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.post("/api/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    _: Protected,
    source_event_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}:
        raise HTTPException(status_code=409, detail="任务仍在处理，请先取消或等待结束后再重试")
    if job.status == JobStatus.CANCELLED.value and job.lease_owner:
        raise HTTPException(status_code=409, detail="正在停止当前阶段，确认停止后才能重试")
    if source_event_id:
        event = db.get(SystemEvent, source_event_id)
        if event is None or event.entity_type != "job" or event.entity_id != job.id:
            raise HTTPException(status_code=409, detail="错误事件不属于该任务，无法重跑")
        if event.level not in {"ERROR", "CRITICAL"}:
            raise HTTPException(status_code=409, detail="仅错误事件可以触发所属任务重跑")
    job.status = JobStatus.QUEUED.value
    job.error = None
    job.error_code = None
    job.finished_at = None
    job.started_at = None
    job.heartbeat_at = None
    job.lease_owner = None
    job.lease_expire_at = None
    job.current_step = "RECEIVED"
    job.progress = 0
    job.retry_count += 1
    for step in db.scalars(select(JobStep).where(JobStep.job_id == job.id)).all():
        step.status = "PENDING"
        step.progress = 0
        step.error = None
        step.started_at = None
        step.finished_at = None
        step.output_json = {}
    record_event(
        db,
        "job.retry.queued",
        "任务已重新入队，将从首个步骤开始新的尝试",
        component="api",
        actor="user",
        entity_type="job",
        entity_id=job.id,
        detail={"retry_count": job.retry_count, "source_event_id": source_event_id},
        commit=False,
    )
    db.commit()
    return {"status": job.status, "retry_count": job.retry_count}


@router.get("/api/jobs/{job_id}/replay-options")
def get_replay_options(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return replay_options(db, job)


@router.post("/api/jobs/{job_id}/retry-from-step")
def retry_from_step(
    job_id: str,
    payload: StepReplayRequest,
    _: Protected,
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        options = queue_step_replay(db, job, payload.step_name, payload.source_event_id)
    except ValueError as exc:
        code, _, message = str(exc).partition(":")
        raise HTTPException(status_code=409, detail={"code": code, "message": message}) from exc
    return {"status": job.status, "retry_count": job.retry_count, **options}


@router.post("/api/jobs/{job_id}/skip-login-step")
def skip_login_step(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        options = queue_login_step_skip(db, job)
    except ValueError as exc:
        code, _, message = str(exc).partition(":")
        raise HTTPException(status_code=409, detail={"code": code, "message": message}) from exc
    return {"status": job.status, "retry_count": job.retry_count, **options}


@router.post("/api/jobs/{job_id}/retry-full")
def retry_full(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    now = utc_now()
    active = job.status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value} or bool(job.lease_owner)
    if active:
        job.status = JobStatus.CANCELLED.value
        job.finished_at = now
        job.heartbeat_at = now
        if job.lease_owner:
            job.lease_expire_at = now + timedelta(seconds=60)
        current_step = _job_step(db, job.id, job.current_step)
        if current_step and current_step.status in {"PENDING", "RUNNING"}:
            current_step.status = "CANCELLED"
            current_step.finished_at = now
            current_step.error = None
    payload = {
        key: value
        for key, value in job.payload_json.items()
        if key not in {"replay_from_step", "source_event_id"}
    }
    replacement = Job(
        job_type=job.job_type,
        status=JobStatus.QUEUED.value,
        priority=job.priority,
        payload_json=payload,
        created_at=now,
    )
    db.add(replacement)
    db.flush()
    record_event(
        db,
        "job.full_replay.queued",
        "已创建新的完整任务；原运行流程已请求停止" if active else "已创建新的完整任务",
        component="api",
        actor="user",
        entity_type="job",
        entity_id=job.id,
        detail={"replacement_job_id": replacement.id, "stopped_active_job": active},
        commit=False,
    )
    db.commit()
    return {
        "status": replacement.status,
        "job_id": replacement.id,
        "replaced_job_id": job.id,
        "stopped_active_job": active,
    }


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in {
        JobStatus.COMPLETED.value,
        JobStatus.PARTIAL_SUCCESS.value,
        JobStatus.FAILED.value,
        JobStatus.NEEDS_USER.value,
        JobStatus.CANCELLED.value,
    }:
        raise HTTPException(status_code=409, detail="该任务已经结束，不能再次取消")
    job.status = JobStatus.CANCELLED.value
    job.finished_at = utc_now()
    job.heartbeat_at = utc_now()
    job.lease_expire_at = utc_now() + timedelta(seconds=60)
    step = _job_step(db, job.id, job.current_step)
    if step:
        step.status = "CANCELLED"
        step.finished_at = utc_now()
        step.error = None
    record_event(
        db,
        "job.cancel.requested",
        "已请求取消；正在等待当前阶段在安全边界停止",
        component="api",
        actor="user",
        entity_type="job",
        entity_id=job.id,
        detail={"step": job.current_step, "lease_owner": job.lease_owner},
        commit=False,
    )
    db.commit()
    return {"status": job.status, "stopping": bool(job.lease_owner)}


@router.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}:
        raise HTTPException(status_code=409, detail="请先取消或等待任务结束后再删除")
    title = str(job.payload_json.get("title") or job.payload_json.get("locator") or job.id)
    db.execute(delete(SystemEvent).where(SystemEvent.entity_type == "job", SystemEvent.entity_id == job_id))
    db.delete(job)
    record_event(
        db,
        "job.deleted",
        f"已删除任务历史：{title[:120]}",
        actor="user",
        entity_type="deleted_job",
        entity_id=job_id,
    )
    db.commit()
    return {"status": "DELETED", "id": job_id}


@router.get("/api/content", response_model=list[ContentView])
def list_content(
    _: Protected,
    content_type: str | None = None,
    query: str | None = None,
    db: Session = Depends(get_db),
) -> list[ContentView]:
    statement = select(ContentItem).order_by(ContentItem.updated_at.desc())
    if content_type:
        statement = statement.where(ContentItem.content_type == content_type.upper())
    if query:
        statement = statement.where(ContentItem.title.contains(query))
    return [content_view(item) for item in db.scalars(statement).all()]


@router.get("/api/content/{content_id}")
def get_content(content_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    claims = db.scalars(
        select(Claim).where(Claim.subject_type == "CONTENT", Claim.subject_id == content_id)
    ).all()
    claim_ids = [claim.id for claim in claims]
    evidence = db.scalars(select(Evidence).where(Evidence.claim_id.in_(claim_ids))).all() if claim_ids else []
    return {
        **content_view(item).model_dump(),
        "claims": [
            {"id": claim.id, "predicate": claim.predicate, "value": claim.value_json} for claim in claims
        ],
        "evidence": [
            {"id": item.id, "claim_id": item.claim_id, "quote": item.quote, "locator": item.locator_json}
            for item in evidence
        ],
    }


@router.delete("/api/content/{content_id}")
def delete_content(content_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    claims = db.scalars(
        select(Claim).where(Claim.subject_type == "CONTENT", Claim.subject_id == content_id)
    ).all()
    claim_ids = [claim.id for claim in claims]
    if claim_ids:
        db.execute(delete(Evidence).where(Evidence.claim_id.in_(claim_ids)))
        db.execute(delete(Claim).where(Claim.id.in_(claim_ids)))
    title, source_id = item.title, item.source_id
    db.delete(item)
    db.flush()
    source_deleted = prune_source_if_orphan(db, source_id)
    record_event(
        db,
        "content.deleted",
        f"已删除内容历史：{title[:120]}",
        actor="user",
        entity_type="deleted_content",
        entity_id=content_id,
        detail={"source_deleted": source_deleted},
        commit=False,
    )
    db.commit()
    return {"status": "DELETED", "id": content_id, "source_deleted": source_deleted}


@router.get("/api/sources")
def list_sources(
    _: Protected,
    query: str | None = None,
    source_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(Source).order_by(Source.updated_at.desc())
    if query:
        statement = statement.where(Source.title.contains(query) | Source.locator.contains(query))
    if source_type:
        statement = statement.where(Source.source_type == source_type.upper())
    result = []
    for source in db.scalars(statement).all():
        snapshot_count = (
            db.scalar(select(func.count(Snapshot.id)).where(Snapshot.source_id == source.id)) or 0
        )
        content_count = (
            db.scalar(select(func.count(ContentItem.id)).where(ContentItem.source_id == source.id)) or 0
        )
        result.append(
            {
                "id": source.id,
                "source_type": source.source_type,
                "locator": source.locator,
                "title": source.title or "未命名来源",
                "authority": source.authority,
                "snapshot_count": snapshot_count,
                "content_count": content_count,
                "updated_at": source.updated_at,
            }
        )
    return result


@router.get("/api/sources/{source_id}")
def source_detail(source_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    snapshots = db.scalars(
        select(Snapshot).where(Snapshot.source_id == source_id).order_by(Snapshot.captured_at.desc())
    ).all()
    snapshot_ids = [snapshot.id for snapshot in snapshots]
    segment_count = (
        db.scalar(select(func.count(Segment.id)).where(Segment.snapshot_id.in_(snapshot_ids))) or 0
        if snapshot_ids
        else 0
    )
    contents = db.scalars(select(ContentItem).where(ContentItem.source_id == source_id)).all()
    return {
        "id": source.id,
        "source_type": source.source_type,
        "locator": source.locator,
        "title": source.title,
        "authority": source.authority,
        "metadata": source.metadata_json,
        "snapshots": [
            {
                "id": snapshot.id,
                "content_hash": snapshot.content_hash,
                "raw_path": snapshot.raw_path,
                "captured_at": snapshot.captured_at,
            }
            for snapshot in snapshots
        ],
        "segment_count": segment_count,
        "contents": [content_view(item).model_dump() for item in contents],
        "deletion": source_deletion_state(db, source_id),
    }


@router.delete("/api/sources/{source_id}")
def delete_source(source_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    state = source_deletion_state(db, source_id)
    if not state["allowed"]:
        raise HTTPException(status_code=409, detail="请先删除关联内容、视频笔记并结束活跃任务")
    title = source.title or source.locator
    db.delete(source)
    record_event(
        db,
        "source.deleted",
        f"已删除来源审计记录：{title[:120]}",
        actor="user",
        entity_type="deleted_source",
        entity_id=source_id,
        detail=state,
        commit=False,
    )
    db.commit()
    return {"status": "DELETED", "id": source_id}


@router.get("/api/todos")
def list_todos(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    todos: list[dict] = []
    for item in db.scalars(
        select(ContentItem).where(ContentItem.status == "NEEDS_USER").order_by(ContentItem.updated_at.desc())
    ).all():
        todos.append(
            {
                "id": f"content:{item.id}",
                "kind": "CONTENT_REVIEW",
                "title": item.title,
                "detail": "结构化结果存在需要人工确认的字段",
                "to": f"/content/{item.id}",
                "created_at": item.updated_at,
            }
        )
    for job in db.scalars(select(Job).where(Job.status.in_(["FAILED", "NEEDS_USER"]))).all():
        todos.append(
            {
                "id": f"job:{job.id}",
                "kind": "JOB_FAILURE" if job.status == "FAILED" else "JOB_REVIEW",
                "title": job_view(job).title,
                "detail": job.error or "任务等待确认",
                "to": f"/tasks/{job.id}",
                "created_at": job.created_at,
            }
        )
    unresolved = db.scalars(select(Place).where(Place.resolution_status == "UNRESOLVED")).all()
    for place in unresolved:
        todos.append(
            {
                "id": f"place:{place.id}",
                "kind": "PLACE_REVIEW",
                "title": place.name,
                "detail": "地点需要通过高德 POI 确认",
                "to": f"/places/{place.id}",
                "created_at": place.updated_at,
            }
        )
    return sorted(todos, key=lambda item: str(item["created_at"]), reverse=True)


@router.get("/api/profile")
def read_profile(_: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, "profile:local")
    return ProfileConfig(**(setting.value_json if setting else {})).model_dump()


@router.put("/api/profile")
def save_profile(payload: ProfileConfig, _: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, "profile:local")
    if setting is None:
        setting = Setting(key="profile:local", value_json=payload.model_dump())
        db.add(setting)
    else:
        setting.value_json = payload.model_dump()
    record_event(db, "profile.updated", "本地报考档案已更新", entity_type="profile", entity_id="local")
    return payload.model_dump()


@router.get("/api/settings/general")
def read_general_settings(_: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, "app:general")
    return GeneralConfig(**(setting.value_json if setting else {})).model_dump()


@router.put("/api/settings/general")
def save_general_settings(payload: GeneralConfig, _: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, "app:general")
    if setting is None:
        setting = Setting(key="app:general", value_json=payload.model_dump())
        db.add(setting)
    else:
        setting.value_json = payload.model_dump()
    record_event(db, "settings.general.updated", "通用设置已保存")
    return payload.model_dump()


@router.get("/api/settings/bilibili")
def read_bilibili_settings(
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    account = db.get(Setting, "bilibili:login")
    value = account.value_json if account else {}
    return {
        "cookie_saved": bool(store.get(settings.video_cookie_secret_key)),
        "account_name": value.get("account_name"),
        "verified_at": value.get("verified_at"),
    }


@router.post("/api/settings/bilibili/login")
def create_bilibili_login(
    _: Protected,
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return start_bilibili_login(
            timeout=settings.video_network_timeout_seconds,
            proxy_url=settings.video_proxy_url,
        )
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/settings/bilibili/login/{session_id}")
def read_bilibili_login(
    session_id: str,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    try:
        result = poll_bilibili_login(
            session_id,
            timeout=settings.video_network_timeout_seconds,
            proxy_url=settings.video_proxy_url,
        )
    except BilibiliAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if result.status != "SUCCESS" or not result.cookie:
        return {"status": result.status, "message": result.message}
    store.set(settings.video_cookie_secret_key, result.cookie)
    verified_at = utc_now().isoformat()
    account = db.get(Setting, "bilibili:login")
    value = {
        "account_name": result.account_name,
        "account_id": result.account_id,
        "verified_at": verified_at,
    }
    if account is None:
        db.add(Setting(key="bilibili:login", value_json=value))
    else:
        account.value_json = value
    record_event(
        db,
        "settings.bilibili.updated",
        "Bilibili 扫码登录已完成，登录凭证已安全更新",
        entity_type="settings",
        entity_id="bilibili",
        detail={"account_id": result.account_id},
        commit=False,
    )
    db.commit()
    return {
        "status": "SUCCESS",
        "message": result.message,
        "cookie_saved": True,
        "account_name": result.account_name,
        "verified_at": verified_at,
    }


@router.get("/api/settings/amap")
def read_amap_settings(
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    js = db.get(Setting, "amap:js-key")
    return {
        "js_key": str(js.value_json.get("value") or "") if js else "",
        "security_code_saved": bool(store.get("amap:security-code")),
        "web_service_key_saved": bool(store.get("amap:web-service-key")),
    }


@router.put("/api/settings/amap")
def save_amap_settings(
    payload: AMapConfig,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    js = db.get(Setting, "amap:js-key")
    if js is None:
        js = Setting(key="amap:js-key", value_json={"value": payload.js_key})
        db.add(js)
    else:
        js.value_json = {"value": payload.js_key}
    for key, value in (
        ("amap:security-code", payload.security_code),
        ("amap:web-service-key", payload.web_service_key),
    ):
        if value:
            store.set(key, value)
            setting = db.get(Setting, key)
            if setting is None:
                db.add(Setting(key=key, value_json={"saved": True}, is_secret_ref=True))
            else:
                setting.value_json, setting.is_secret_ref = {"saved": True}, True
    record_event(
        db,
        "settings.amap.updated",
        "高德地图配置已保存",
        entity_type="settings",
        entity_id="amap",
        commit=False,
    )
    db.commit()
    return read_amap_settings(None, db, store)


@router.post("/api/settings/amap/test")
def test_amap_settings(
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    web_key = store.get("amap:web-service-key")
    if not web_key:
        raise HTTPException(status_code=422, detail="尚未保存高德 Web 服务 Key")
    try:
        candidates = AMapPOIProvider(web_key).search("北京", "北京市")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"高德 Web 服务测试失败：{str(exc)[:240]}") from exc
    return {"status": "READY", "message": f"Web 服务可用，测试返回 {len(candidates)} 个 POI 候选"}


def _redact_detail(value: object) -> object:
    if isinstance(value, dict):
        secret_keys = {"api_key", "authorization", "cookie", "token", "password", "body", "content", "text"}
        return {
            str(key): "[REDACTED]" if str(key).lower() in secret_keys else _redact_detail(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_detail(item) for item in value]
    return value


def event_view(event: SystemEvent) -> dict:
    return {
        "id": event.id,
        # SQLite returns datetime columns without tzinfo. Event storage is
        # UTC by contract, so restore the offset before JSON serialization.
        "created_at": as_utc(event.created_at),
        "level": event.level,
        "component": event.component,
        "event_type": event.event_type,
        "message": event.message,
        "actor": event.actor,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "request_id": event.request_id,
        "detail": _redact_detail(event.detail_json),
    }


@router.get("/api/logs")
def list_logs(
    _: Protected,
    level: list[str] | None = Query(default=None),
    component: str | None = None,
    event_type: str | None = None,
    job_id: str | None = None,
    request_id: str | None = None,
    entity_id: str | None = None,
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    query: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> dict:
    statement = select(SystemEvent)
    if level:
        statement = statement.where(SystemEvent.level.in_([item.upper() for item in level]))
    if component:
        statement = statement.where(SystemEvent.component == component)
    if event_type:
        statement = statement.where(SystemEvent.event_type == event_type)
    if job_id:
        statement = statement.where(SystemEvent.entity_type == "job", SystemEvent.entity_id == job_id)
    if request_id:
        statement = statement.where(SystemEvent.request_id == request_id)
    if entity_id:
        statement = statement.where(SystemEvent.entity_id == entity_id)
    if from_at:
        statement = statement.where(SystemEvent.created_at >= from_at)
    if to_at:
        statement = statement.where(SystemEvent.created_at <= to_at)
    if query:
        statement = statement.where(
            or_(
                SystemEvent.message.contains(query),
                SystemEvent.event_type.contains(query),
                SystemEvent.entity_id.contains(query),
                SystemEvent.request_id.contains(query),
            )
        )
    if cursor:
        pivot = db.get(SystemEvent, cursor)
        if pivot is not None:
            statement = statement.where(
                or_(
                    SystemEvent.created_at > pivot.created_at,
                    and_(SystemEvent.created_at == pivot.created_at, SystemEvent.id > pivot.id),
                )
                if sort == "asc"
                else or_(
                    SystemEvent.created_at < pivot.created_at,
                    and_(SystemEvent.created_at == pivot.created_at, SystemEvent.id < pivot.id),
                )
            )
    events = db.scalars(
        statement.order_by(
            SystemEvent.created_at.asc() if sort == "asc" else SystemEvent.created_at.desc(),
            SystemEvent.id.asc() if sort == "asc" else SystemEvent.id.desc(),
        ).limit(limit + 1)
    ).all()
    has_more = len(events) > limit
    events = events[:limit]
    return {
        "items": [event_view(event) for event in events],
        "next_cursor": events[-1].id if has_more and events else None,
        "server_time": utc_now(),
        "applied_filters": {
            "level": level or [],
            "component": component,
            "event_type": event_type,
            "job_id": job_id,
            "request_id": request_id,
            "entity_id": entity_id,
            "query": query,
            "from": from_at,
            "to": to_at,
            "sort": sort,
        },
    }


def _place_query(
    *,
    city: str | None = None,
    place_type: str | None = None,
    user_state: str | None = None,
    origin: str | None = None,
    query: str | None = None,
    season: str | None = None,
    month: int | None = None,
    month_segment: str | None = None,
    day_time_slot: str | None = None,
    source_id: str | None = None,
    route_id: str | None = None,
):
    statement = select(Place).where(
        or_(Place.resolution_status == ResolutionStatus.CONFIRMED.value, Place.origin == "USER_CREATED"),
        Place.deleted_at.is_(None),
    )
    if city:
        statement = statement.where(Place.city == city)
    if place_type:
        statement = statement.where(Place.place_type == place_type)
    if user_state:
        statement = statement.where(Place.user_state == user_state)
    if query:
        statement = statement.where(Place.name.contains(query) | Place.address.contains(query))
    if origin:
        statement = statement.where(Place.origin == origin)
    if any(value is not None for value in (season, month, month_segment, day_time_slot)):
        window = select(PlaceVisitWindow.id).where(
            PlaceVisitWindow.place_id == Place.id, PlaceVisitWindow.status == "ACTIVE"
        )
        if season:
            window = window.where(PlaceVisitWindow.season == season)
        if month is not None:
            window = window.where(PlaceVisitWindow.month == month)
        if month_segment:
            window = window.where(PlaceVisitWindow.month_segment == month_segment)
        if day_time_slot:
            window = window.where(PlaceVisitWindow.day_time_slot == day_time_slot)
        statement = statement.where(window.exists())
    if source_id:
        statement = statement.where(
            select(PlaceInsightItem.id)
            .where(
                PlaceInsightItem.place_id == Place.id,
                PlaceInsightItem.status == "ACTIVE",
                PlaceInsightItem.source_id == source_id,
            )
            .exists()
        )
    if route_id:
        statement = statement.where(
            select(RouteDraftItem.id)
            .where(RouteDraftItem.place_id == Place.id, RouteDraftItem.route_draft_id == route_id)
            .exists()
        )
    return statement


@router.get("/api/travel/map", response_model=MapOverviewView)
def map_overview(
    _: Protected,
    city: str | None = None,
    district: str | None = None,
    place_type: str | None = None,
    user_state: str | None = None,
    origin: str | None = None,
    query: str | None = None,
    best_month: str | None = None,
    best_season: str | None = None,
    best_time_slot: str | None = None,
    season: str | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    month_segment: str | None = Query(default=None, pattern="^(EARLY|MID|LATE)$"),
    day_time_slot: str | None = None,
    route_id: str | None = None,
    source_id: str | None = None,
    visibility: str = Query(default="VISIBLE", pattern="^(VISIBLE|HIDDEN|ALL)$"),
    selected_place_id: str | None = None,
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    zoom: float = Query(default=4.0, ge=3, le=20),
    db: Session = Depends(get_db),
) -> MapOverviewView:
    if city and zoom == 4:
        zoom = 8
    default_bbox = (73.5, 18.0, 135.1, 53.6)
    west, south, east, north = default_bbox
    if bbox:
        try:
            west, south, east, north = (float(part) for part in bbox.split(","))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="bbox 格式应为 west,south,east,north") from exc
    statement = _place_query(
        city=city,
        place_type=place_type,
        user_state=user_state,
        query=query,
        season=season,
        month=month,
        month_segment=month_segment,
        day_time_slot=day_time_slot,
        source_id=source_id,
        route_id=route_id,
    )
    if district:
        statement = statement.where(Place.district == district)
    # The old query names remain a one-dimensional compatibility surface.  They
    # never participate in the new correlated-window conjunction.
    for insight_type, value in (
        ("BEST_MONTH", best_month.zfill(2) if best_month and best_month.isdigit() else best_month),
        ("BEST_SEASON", best_season),
        ("BEST_TIME_SLOT", best_time_slot),
    ):
        if value:
            statement = statement.where(
                select(PlaceInsightItem.id)
                .where(
                    PlaceInsightItem.place_id == Place.id,
                    PlaceInsightItem.status == "ACTIVE",
                    PlaceInsightItem.insight_type == insight_type,
                    PlaceInsightItem.value_key == value,
                )
                .exists()
            )
    statement = statement.where(Place.longitude.between(west, east), Place.latitude.between(south, north))
    ordered_places = db.scalars(statement.order_by(Place.name.asc())).all()
    places = list({place.id: place for place in ordered_places}.values())
    place_ids = [place.id for place in places]
    # A place is its durable domain record; its map projection has an explicit
    # lifecycle.  Backfill projections lazily for places created before v0.4,
    # so every visible marker can be hidden/restored without touching evidence.
    existing_states = (
        db.scalars(select(MapMarkerState).where(MapMarkerState.place_id.in_(place_ids))).all()
        if place_ids
        else []
    )
    existing_by_place = {item.place_id: item for item in existing_states}
    missing_states = [
        MapMarkerState(place_id=place.id, origin=place.origin or "AI_EXTRACTED", visibility="VISIBLE")
        for place in places
        if place.id not in existing_by_place
    ]
    if missing_states:
        db.add_all(missing_states)
        db.flush()
        db.commit()
    states = (
        {
            item.place_id: item
            for item in db.scalars(select(MapMarkerState).where(MapMarkerState.place_id.in_(place_ids))).all()
        }
        if places
        else {}
    )
    visible_places = [
        place
        for place in places
        if visibility == "ALL"
        or (states.get(place.id).visibility if states.get(place.id) else "VISIBLE") == visibility
    ]
    if origin:
        visible_places = [
            place
            for place in visible_places
            if (states.get(place.id).origin if states.get(place.id) else place.origin) == origin
        ]
    selected = next((place for place in visible_places if place.id == selected_place_id), None)
    route_count = db.scalar(select(func.count(RouteDraftItem.id))) or 0
    return MapOverviewView(
        total_places=len(places),
        visible_places=len(visible_places),
        markers=[_map_marker_view(db, place, states.get(place.id)) for place in visible_places],
        clusters=[],
        selected_place_id=selected.id if selected else None,
        selected_preview=preview_for_place(db, selected) if selected else None,
        route_draft_count=route_count,
        viewport={"bbox": [west, south, east, north], "zoom": zoom, "is_default_china": not bbox},
    )


@router.get("/api/travel/places", response_model=PlaceListView)
def travel_places(
    _: Protected,
    city: str | None = None,
    place_type: str | None = None,
    user_state: str | None = None,
    origin: str | None = None,
    query: str | None = None,
    season: str | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    month_segment: str | None = Query(default=None, pattern="^(EARLY|MID|LATE)$"),
    day_time_slot: str | None = None,
    route_id: str | None = None,
    visibility: str = Query(default="ALL", pattern="^(VISIBLE|HIDDEN|ALL)$"),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PlaceListView:
    statement = _place_query(
        city=city,
        place_type=place_type,
        user_state=user_state,
        origin=origin,
        query=query,
        season=season,
        month=month,
        month_segment=month_segment,
        day_time_slot=day_time_slot,
        route_id=route_id,
    )
    if cursor:
        statement = statement.where(Place.id > cursor)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    places = db.scalars(statement.order_by(Place.id.asc()).limit(limit + 1)).all()
    next_cursor = places[limit].id if len(places) > limit else None
    places = places[:limit]
    states = (
        {
            state.place_id: state
            for state in db.scalars(
                select(MapMarkerState).where(MapMarkerState.place_id.in_([place.id for place in places]))
            ).all()
        }
        if places
        else {}
    )
    items = [
        _map_marker_view(db, place, states.get(place.id))
        for place in places
        if visibility == "ALL"
        or (states.get(place.id).visibility if states.get(place.id) else "VISIBLE") == visibility
    ]
    return PlaceListView(items=items, next_cursor=next_cursor, total=total)


@router.get("/api/travel/dashboard")
def travel_dashboard(_: Protected, db: Session = Depends(get_db)) -> dict:
    places = db.scalars(
        select(Place)
        .where(
            or_(Place.resolution_status == ResolutionStatus.CONFIRMED.value, Place.origin == "USER_CREATED"),
            Place.deleted_at.is_(None),
        )
        .order_by(Place.updated_at.desc())
        .limit(8)
    ).all()
    states = (
        {
            state.place_id: state
            for state in db.scalars(
                select(MapMarkerState).where(MapMarkerState.place_id.in_([place.id for place in places]))
            ).all()
        }
        if places
        else {}
    )
    latest_visit = db.scalar(
        select(Place.updated_at).where(Place.user_state == "VISITED").order_by(Place.updated_at.desc())
    )
    return {
        "days_since_last_trip": max(0, (utc_now() - as_utc(latest_visit)).days) if latest_visit else None,
        "map_places": [_map_marker_view(db, place, states.get(place.id)).model_dump() for place in places],
        "recent_discoveries": [
            _map_marker_view(db, place, states.get(place.id)).model_dump() for place in places[:4]
        ],
        "recommended_places": [],
        "pending_reviews": db.scalar(
            select(func.count(PlaceMention.id)).where(PlaceMention.resolution_status == "REVIEW")
        )
        or 0,
    }


@router.post("/api/travel/export")
def export_travel_places(
    _: Protected,
    format: str = Query(default="json", pattern="^(csv|json|geojson)$"),
    db: Session = Depends(get_db),
) -> Response:
    places = db.scalars(
        select(Place)
        .where(Place.resolution_status == ResolutionStatus.CONFIRMED.value)
        .order_by(Place.name.asc())
    ).all()
    states = (
        {
            state.place_id: state
            for state in db.scalars(
                select(MapMarkerState).where(MapMarkerState.place_id.in_([place.id for place in places]))
            ).all()
        }
        if places
        else {}
    )
    views = [
        _map_marker_view(db, place, states.get(place.id))
        for place in places
        if states.get(place.id) is None or states[place.id].visibility == "VISIBLE"
    ]
    filename = f"zhijian-places.{format}"
    if format == "geojson":
        payload = {
            "type": "FeatureCollection",
            "coordinate_system": "GCJ02",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [view.longitude, view.latitude]},
                    "properties": {
                        "place_id": view.place_id,
                        "name": view.name,
                        "canonical_name": view.canonical_name,
                        "place_type": view.place_type,
                        "address": view.address,
                        "origin": view.origin,
                        "user_state": view.user_state,
                        "source_count": view.source_count,
                        "coordinate_system": "GCJ02",
                    },
                }
                for view in views
            ],
        }
        return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    rows = [
        {
            "place_id": view.place_id,
            "name": view.name,
            "canonical_name": view.canonical_name,
            "place_type": view.place_type,
            "longitude": view.longitude,
            "latitude": view.latitude,
            "coordinate_system": "GCJ02",
            "address": view.address,
            "origin": view.origin,
            "user_state": view.user_state,
            "source_count": view.source_count,
        }
        for view in views
    ]
    if format == "json":
        return Response(
            json.dumps(rows, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    buffer = io.StringIO()
    fieldnames = list(rows[0]) if rows else ["place_id", "name", "coordinate_system"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        "\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _map_marker_view(db: Session, place: Place, state: MapMarkerState | None) -> MapMarker:
    mention = db.scalar(
        select(PlaceMention).where(PlaceMention.place_id == place.id).order_by(PlaceMention.updated_at.desc())
    )
    screenshot = db.scalar(
        select(VideoScreenshot)
        .where(
            VideoScreenshot.place_mention_id == (mention.id if mention else ""),
            VideoScreenshot.status == "READY",
        )
        .order_by(VideoScreenshot.created_at.desc())
    )
    overlay = db.scalar(select(PlaceUserOverlay).where(PlaceUserOverlay.place_id == place.id))
    return MapMarker(
        id=place.id,
        marker_id=state.id if state else None,
        place_id=place.id,
        origin=state.origin if state else place.origin,
        visibility=state.visibility if state else "VISIBLE",
        name=(
            state.custom_label
            if state and state.custom_label
            else (overlay.display_name if overlay and overlay.display_name else place.name)
        ),
        canonical_name=place.canonical_name or place.name,
        place_type=(
            overlay.override_place_type if overlay and overlay.override_place_type else place.place_type
        ),
        latitude=place.latitude,
        longitude=place.longitude,
        user_state=place.user_state,
        summary=place.summary,
        address=place.address,
        preview_image=f"/api/video-screenshots/{screenshot.id}/image" if screenshot else None,
        brief=mention.brief_json if mention else {},
        source_count=(
            db.scalar(select(func.count(PlaceMention.id)).where(PlaceMention.place_id == place.id)) or 0
        ),
    )


@router.get("/api/travel/map/bootstrap")
def map_bootstrap(
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    js = db.get(Setting, "amap:js-key")
    security_code = store.get("amap:security-code") or ""
    web_service_key = store.get("amap:web-service-key") or settings.amap_api_key
    return {
        "js_key": str(js.value_json.get("value") or "") if js else "",
        "security_code": security_code,
        "security_code_configured": bool(security_code),
        "web_service_configured": bool(web_service_key),
        "default_viewport": {"bbox": [73.5, 18.0, 135.1, 53.6], "zoom": 4},
        "diagnostics": ["JS Key 仅在已认证客户端使用", "请在高德控制台配置局域网访问域名白名单"],
    }


@router.post("/api/travel/map/markers")
def create_map_marker(payload: MapMarkerCreate, _: Protected, db: Session = Depends(get_db)) -> dict:
    if payload.longitude is None or payload.latitude is None or not payload.custom_name:
        raise HTTPException(status_code=422, detail="当前版本请提供地图点选坐标和自定义名称")
    place = Place(
        name=payload.custom_name,
        canonical_name=payload.custom_name,
        origin="USER",
        place_type=payload.place_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        resolution_status=ResolutionStatus.CONFIRMED.value,
        summary=payload.summary,
        metadata_json={"confirmation_source": "USER_CONFIRMED"},
    )
    db.add(place)
    db.flush()
    marker = MapMarkerState(place_id=place.id, origin="USER", visibility="VISIBLE", created_by="local-user")
    db.add(marker)
    record_event(
        db,
        "map.marker.created",
        f"已新增用户 Marker：{place.name}",
        entity_type="place",
        entity_id=place.id,
        commit=False,
    )
    db.commit()
    return {"marker_id": marker.id, "place_id": place.id}


@router.delete("/api/travel/map/markers/{marker_id}")
def delete_map_marker(marker_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    marker = db.get(MapMarkerState, marker_id)
    if marker is None:
        raise HTTPException(status_code=404, detail="Marker 不存在")
    marker.visibility = "DELETED" if marker.origin == "USER" else "HIDDEN"
    marker.deleted_at = utc_now() if marker.origin == "USER" else None
    record_event(
        db,
        "map.marker.hidden",
        "Marker 已从地图隐藏，可恢复",
        entity_type="place",
        entity_id=marker.place_id,
        commit=False,
    )
    db.commit()
    return {"marker_id": marker.id, "visibility": marker.visibility}


@router.post("/api/travel/map/markers/{marker_id}/restore")
def restore_map_marker(marker_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    marker = db.get(MapMarkerState, marker_id)
    if marker is None:
        raise HTTPException(status_code=404, detail="Marker 不存在")
    marker.visibility, marker.deleted_at = "VISIBLE", None
    record_event(
        db,
        "map.marker.restored",
        "Marker 已恢复显示",
        entity_type="place",
        entity_id=marker.place_id,
        commit=False,
    )
    db.commit()
    return {"marker_id": marker.id, "visibility": marker.visibility}


@router.get("/api/travel/places/{place_id}/preview", response_model=PlacePreview)
def place_preview(place_id: str, _: Protected, db: Session = Depends(get_db)) -> PlacePreview:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    return preview_for_place(db, place)


@router.get("/api/travel/places/{place_id}", response_model=PlaceDetailView)
def place_detail(place_id: str, _: Protected, db: Session = Depends(get_db)) -> PlaceDetailView:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    insights = db.scalars(
        select(PlaceInsightItem)
        .where(PlaceInsightItem.place_id == place.id, PlaceInsightItem.status == "ACTIVE")
        .order_by(PlaceInsightItem.insight_type, PlaceInsightItem.created_at)
    ).all()
    overlay = db.scalar(select(PlaceUserOverlay).where(PlaceUserOverlay.place_id == place.id))
    note = db.scalar(select(PlaceUserNote).where(PlaceUserNote.place_id == place.id))
    marker = db.scalar(select(MapMarkerState).where(MapMarkerState.place_id == place.id))
    visit_windows = db.scalars(
        select(PlaceVisitWindow)
        .where(PlaceVisitWindow.place_id == place.id, PlaceVisitWindow.status == "ACTIVE")
        .order_by(PlaceVisitWindow.created_at)
    ).all()
    source_titles = {
        source.id: source.title or "来源未命名"
        for source in db.scalars(
            select(Source).where(Source.id.in_({item.source_id for item in insights if item.source_id}))
        ).all()
    }
    mention_ids = {item.place_mention_id for item in insights if item.place_mention_id}
    mention_versions = {
        mention.id: mention.ai_note_version_id
        for mention in db.scalars(
            select(PlaceMention).where(PlaceMention.id.in_(mention_ids))
        ).all()
    }
    version_ids = set(mention_versions.values()) - {None}
    note_ids = {
        version.id: version.ai_note_id
        for version in db.scalars(select(AINoteVersion).where(AINoteVersion.id.in_(version_ids))).all()
    }
    knowledge = aggregate_place_knowledge(insights, source_titles)
    for category in (
        "highlights", "dishes", "visit_windows", "warnings", "prices", "queues", "opinions", "other"
    ):
        for item in knowledge[category]:
            for observation in item["observations"]:
                note_id = note_ids.get(mention_versions.get(observation["place_mention_id"]))
                if note_id:
                    observation["evidence_url"] = f"/video-notes/{note_id}"
    return PlaceDetailView(
        **preview_for_place(db, place).model_dump(),
        coordinate_system=place.coordinate_system,
        coordinates=[place.longitude, place.latitude],
        provider=place.external_provider,
        external_poi_id=place.external_poi_id,
        metadata=place.metadata_json,
        knowledge=knowledge,
        insights=[
            PlaceInsightView(
                id=item.id,
                insight_type=item.insight_type,
                value_key=item.value_key,
                value_text=item.value_text,
                value_json=item.value_json,
                provenance=item.provenance,
                    confidence=item.confidence,
                    status=item.status,
                    segment_ids=item.segment_ids_json,
                    source_quote=item.source_quote,
                )
            for item in insights
        ],
        visit_windows=[_visit_window_view(item) for item in visit_windows],
        display={
            "name": overlay.display_name or place.name if overlay else place.name,
            "place_type": overlay.override_place_type or place.place_type if overlay else place.place_type,
            "tags": overlay.custom_tags_json if overlay else [],
            "revision": overlay.revision if overlay else 0,
        },
        note={"markdown": note.markdown, "revision": note.revision}
        if note
        else {"markdown": "", "revision": 0},
        marker={"id": marker.id, "visibility": marker.visibility, "revision": marker.revision}
        if marker
        else {},
    )


def _revision_conflict(current: int) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": "REVISION_CONFLICT", "latest_revision": current})


def _visit_window_view(item: PlaceVisitWindow) -> PlaceVisitWindowView:
    return PlaceVisitWindowView(
        id=item.id,
        season=item.season,
        month=item.month,
        month_segment=item.month_segment,
        day_time_slot=item.day_time_slot,
        period_type=item.period_type,
        suitability=item.suitability,
        source_text=item.source_text,
        segment_ids=item.segment_ids_json,
        provenance=item.provenance,
        confidence=item.confidence,
        status=item.status,
    )


@router.post("/api/travel/places/{place_id}/visit-windows", response_model=PlaceVisitWindowView)
def create_visit_window(
    place_id: str,
    payload: PlaceVisitWindowUpdate,
    _: Protected,
    db: Session = Depends(get_db),
) -> PlaceVisitWindowView:
    if db.get(Place, place_id) is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    item = PlaceVisitWindow(
        place_id=place_id,
        season=payload.season,
        month=payload.month,
        month_segment=payload.month_segment,
        day_time_slot=payload.day_time_slot,
        period_type=payload.period_type,
        suitability=payload.suitability,
        source_text=payload.source_text,
        provenance="USER_ADDED",
        confidence=1.0,
    )
    db.add(item)
    record_event(
        db,
        "place.visit_window.created",
        "地点适宜时间已更新",
        actor="user",
        entity_type="place",
        entity_id=place_id,
        commit=False,
    )
    db.commit()
    return _visit_window_view(item)


@router.delete("/api/travel/places/{place_id}/visit-windows/{window_id}")
def delete_visit_window(place_id: str, window_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    item = db.get(PlaceVisitWindow, window_id)
    if item is None or item.place_id != place_id or item.provenance == "SOURCE_FACT":
        raise HTTPException(status_code=409, detail={"code": "CANNOT_DELETE_SOURCE_FACT"})
    item.status = "REMOVED"
    db.commit()
    return {"id": item.id, "status": item.status}


def _deletion_impact(db: Session, place: Place) -> dict:
    return {
        "place_id": place.id,
        "name": place.name,
        "marker": db.scalar(select(func.count(MapMarkerState.id)).where(MapMarkerState.place_id == place.id))
        or 0,
        "notes": db.scalar(select(func.count(PlaceUserNote.id)).where(PlaceUserNote.place_id == place.id))
        or 0,
        "overlays": db.scalar(
            select(func.count(PlaceUserOverlay.id)).where(PlaceUserOverlay.place_id == place.id)
        )
        or 0,
        "insights": db.scalar(
            select(func.count(PlaceInsightItem.id)).where(PlaceInsightItem.place_id == place.id)
        )
        or 0,
        "visit_windows": db.scalar(
            select(func.count(PlaceVisitWindow.id)).where(PlaceVisitWindow.place_id == place.id)
        )
        or 0,
        "route_references": db.scalar(
            select(func.count(RouteDraftItem.id)).where(RouteDraftItem.place_id == place.id)
        )
        or 0,
        "mentions_preserved": db.scalar(
            select(func.count(PlaceMention.id)).where(PlaceMention.place_id == place.id)
        )
        or 0,
        "source_evidence_preserved": True,
    }


@router.get("/api/travel/places/{place_id}/deletion-impact")
def place_deletion_impact(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    return _deletion_impact(db, place)


def _hard_delete_place(db: Session, place: Place) -> dict:
    impact = _deletion_impact(db, place)
    if place.external_provider and place.external_poi_id:
        db.add(
            PlaceDeletionTombstone(
                external_provider=place.external_provider,
                external_poi_id=place.external_poi_id,
                normalized_name=place.name.casefold(),
                former_place_id=place.id,
            )
        )
    for mention in db.scalars(select(PlaceMention).where(PlaceMention.place_id == place.id)).all():
        mention.place_id, mention.resolution_status, mention.metadata_json = (
            None,
            ResolutionStatus.REJECTED.value,
            {
                **mention.metadata_json,
                "deleted_by_user": True,
                "former_place_id": place.id,
                "former_provider": place.external_provider,
                "former_poi_id": place.external_poi_id,
            },
        )
    for model in (
        PlaceObservation,
        PlaceInsightItem,
        PlaceVisitWindow,
        MapMarkerState,
        PlaceUserNote,
        PlaceUserOverlay,
        RouteDraftItem,
    ):
        db.execute(delete(model).where(model.place_id == place.id))
    db.delete(place)
    record_event(
        db,
        "place.deleted.hard",
        "地点已永久删除；来源与证据已保留",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        detail=impact,
        commit=False,
    )
    return impact


@router.delete("/api/travel/places/bulk-hard-delete")
def hard_delete_places(
    payload: HardDeletePlacesRequest, _: Protected, db: Session = Depends(get_db)
) -> dict:
    place_ids = list(dict.fromkeys(payload.place_ids))
    places = db.scalars(select(Place).where(Place.id.in_(place_ids))).all()
    if len(places) != len(place_ids):
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    impacts = [_hard_delete_place(db, place) for place in places]
    db.commit()
    return {"requested": len(place_ids), "deleted": len(places), "impacts": impacts}


@router.delete("/api/travel/places/{place_id}/hard")
def hard_delete_place(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    impact = _hard_delete_place(db, place)
    db.commit()
    return {"place_id": place_id, "status": "DELETED", "impact": impact}


@router.patch("/api/travel/places/bulk")
def bulk_update_places(payload: BulkPlaceUpdate, _: Protected, db: Session = Depends(get_db)) -> dict:
    places = db.scalars(
        select(Place).where(Place.id.in_(list(dict.fromkeys(payload.place_ids))), Place.deleted_at.is_(None))
    ).all()
    if len(places) != len(set(payload.place_ids)):
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if payload.action in {"hide", "restore"}:
        for place in places:
            marker = db.scalar(select(MapMarkerState).where(MapMarkerState.place_id == place.id))
            if marker is None:
                marker = MapMarkerState(place_id=place.id, origin=place.origin)
                db.add(marker)
            marker.visibility = "HIDDEN" if payload.action == "hide" else "VISIBLE"
    elif payload.action == "state":
        if payload.value not in {"SAVED", "PLANNED", "VISITED", "DISMISSED"}:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STATE"})
        for place in places:
            place.user_state = payload.value
    elif payload.action in {"add_route", "remove_route"}:
        route = db.get(RouteDraft, payload.value)
        if route is None:
            raise HTTPException(status_code=404, detail={"code": "ROUTE_NOT_FOUND"})
        current = [
            item.place_id
            for item in db.scalars(
                select(RouteDraftItem).where(RouteDraftItem.route_draft_id == route.id)
            ).all()
        ]
        selected = {place.id for place in places}
        _replace_route_items(
            db,
            route.id,
            current + list(selected)
            if payload.action == "add_route"
            else [item for item in current if item not in selected],
        )
    db.commit()
    return {"requested": len(payload.place_ids), "succeeded": len(places), "failed": []}


@router.put("/api/travel/places/{place_id}/note")
def update_place_note(
    place_id: str, payload: PlaceNoteUpdate, _: Protected, db: Session = Depends(get_db)
) -> dict:
    if db.get(Place, place_id) is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    note = db.scalar(select(PlaceUserNote).where(PlaceUserNote.place_id == place_id))
    if note is None:
        if payload.expected_revision != 0:
            raise _revision_conflict(0)
        note = PlaceUserNote(place_id=place_id, markdown=payload.markdown, revision=1)
        db.add(note)
    else:
        if note.revision != payload.expected_revision:
            raise _revision_conflict(note.revision)
        note.markdown, note.revision = payload.markdown, note.revision + 1
    record_event(
        db,
        "place.note.updated",
        "地点个人备注已更新",
        actor="user",
        entity_type="place",
        entity_id=place_id,
        commit=False,
    )
    db.commit()
    return {"markdown": note.markdown, "revision": note.revision}


@router.patch("/api/travel/places/{place_id}/overlay")
def update_place_overlay(
    place_id: str, payload: PlaceOverlayUpdate, _: Protected, db: Session = Depends(get_db)
) -> dict:
    if db.get(Place, place_id) is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    overlay = db.scalar(select(PlaceUserOverlay).where(PlaceUserOverlay.place_id == place_id))
    if overlay is None:
        if payload.expected_revision != 0:
            raise _revision_conflict(0)
        overlay = PlaceUserOverlay(place_id=place_id, revision=1)
        db.add(overlay)
    elif overlay.revision != payload.expected_revision:
        raise _revision_conflict(overlay.revision)
    else:
        overlay.revision += 1
    overlay.display_name = payload.display_name
    overlay.override_place_type = payload.override_place_type
    overlay.custom_tags_json = list(dict.fromkeys(tag.strip() for tag in payload.custom_tags if tag.strip()))
    record_event(
        db,
        "place.overlay.updated",
        "地点显示覆盖已更新",
        actor="user",
        entity_type="place",
        entity_id=place_id,
        commit=False,
    )
    db.commit()
    return {"display_name": overlay.display_name, "revision": overlay.revision}


@router.post("/api/travel/places/{place_id}/marker/{action}")
def update_place_marker(place_id: str, action: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if action not in {"hide", "restore"}:
        raise HTTPException(status_code=404, detail="不支持的 Marker 操作")
    marker = db.scalar(select(MapMarkerState).where(MapMarkerState.place_id == place_id))
    if marker is None:
        marker = MapMarkerState(place_id=place_id, origin=place.origin, visibility="VISIBLE")
        db.add(marker)
    marker.visibility, marker.revision, marker.updated_by = (
        ("HIDDEN" if action == "hide" else "VISIBLE"),
        marker.revision + 1,
        "local-user",
    )
    record_event(
        db,
        "place.marker.hidden" if action == "hide" else "place.marker.restored",
        "地点地图投影已更新",
        actor="user",
        entity_type="place",
        entity_id=place_id,
        commit=False,
    )
    db.commit()
    return {"marker_id": marker.id, "visibility": marker.visibility, "revision": marker.revision}


def _place_insight_view(insight: PlaceInsightItem) -> PlaceInsightView:
    return PlaceInsightView(
        id=insight.id,
        insight_type=insight.insight_type,
        value_key=insight.value_key,
        value_text=insight.value_text,
        value_json=insight.value_json,
        provenance=insight.provenance,
        confidence=insight.confidence,
        status=insight.status,
        segment_ids=insight.segment_ids_json,
        source_quote=insight.source_quote,
    )


@router.post("/api/travel/places/{place_id}/insights", response_model=PlaceInsightView)
def create_place_insight(
    place_id: str, payload: PlaceInsightUpdate, _: Protected, db: Session = Depends(get_db)
) -> PlaceInsightView:
    if db.get(Place, place_id) is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    value_key, value_json = normalize_insight(
        payload.insight_type, payload.value_text, payload.value_key, payload.value_json
    )
    insight = PlaceInsightItem(
        place_id=place_id,
        insight_type=payload.insight_type,
        value_key=value_key,
        value_text=payload.value_text,
        value_json=value_json,
        provenance="USER_ADDED",
        confidence=1.0,
        status="ACTIVE",
        created_by="local-user",
    )
    db.add(insight)
    db.commit()
    return _place_insight_view(insight)


@router.patch("/api/travel/places/{place_id}/insights/{insight_id}", response_model=PlaceInsightView)
def update_place_insight(
    place_id: str, insight_id: str, payload: PlaceInsightUpdate, _: Protected, db: Session = Depends(get_db)
) -> PlaceInsightView:
    insight = db.get(PlaceInsightItem, insight_id)
    if insight is None or insight.place_id != place_id or insight.provenance == "SOURCE_FACT":
        raise HTTPException(status_code=409, detail={"code": "CANNOT_EDIT_SOURCE_FACT"})
    insight.insight_type = payload.insight_type
    insight.value_text = payload.value_text
    insight.value_key, insight.value_json = normalize_insight(
        payload.insight_type, payload.value_text, payload.value_key, payload.value_json
    )
    db.commit()
    return _place_insight_view(insight)


@router.delete("/api/travel/places/{place_id}/insights/{insight_id}")
def delete_place_insight(place_id: str, insight_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    insight = db.get(PlaceInsightItem, insight_id)
    if insight is None or insight.place_id != place_id or insight.provenance == "SOURCE_FACT":
        raise HTTPException(status_code=409, detail={"code": "CANNOT_DELETE_SOURCE_FACT"})
    insight.status = "RETRACTED"
    db.commit()
    return {"id": insight.id, "status": insight.status}


@router.post("/api/travel/places")
def create_manual_place(
    payload: ManualPlaceCreate,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    if payload.mode == "AMAP_POI":
        web_key = store.get("amap:web-service-key") or settings.amap_api_key
        if not web_key or not payload.poi_id:
            raise HTTPException(status_code=422, detail={"code": "INVALID_POI"})
        candidate = AMapPOIProvider(web_key).detail(payload.poi_id)
        if candidate is None:
            raise HTTPException(status_code=422, detail={"code": "INVALID_POI"})
        if db.scalar(
            select(PlaceDeletionTombstone).where(
                PlaceDeletionTombstone.external_provider == "AMAP",
                PlaceDeletionTombstone.external_poi_id == candidate.provider_id,
            )
        ):
            raise HTTPException(status_code=409, detail={"code": "PLACE_SUPPRESSED_BY_USER"})
        existing = db.scalar(
            select(Place).where(
                Place.external_provider == "AMAP", Place.external_poi_id == candidate.provider_id
            )
        )
        if existing:
            return {
                "place_id": existing.id,
                "origin": existing.origin,
                "poi_binding_status": existing.poi_binding_status,
            }
        place = Place(
            name=candidate.name,
            canonical_name=candidate.name,
            origin="USER_CREATED",
            place_type=payload.place_type,
            province=candidate.province,
            city=candidate.city,
            district=candidate.district,
            address=candidate.address,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            coordinate_source="AMAP_POI",
            external_provider="AMAP",
            external_poi_id=candidate.provider_id,
            poi_binding_status="USER_CONFIRMED",
            resolution_status=ResolutionStatus.CONFIRMED.value,
        )
    else:
        if not payload.name.strip():
            raise HTTPException(status_code=422, detail={"code": "PLACE_NAME_REQUIRED"})
        place = Place(
            name=payload.name,
            canonical_name=payload.name,
            origin="USER_CREATED",
            place_type=payload.place_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
            coordinate_source="USER_MAP_CLICK",
            poi_binding_status="UNBOUND",
            resolution_status=ResolutionStatus.UNRESOLVED.value,
        )
    db.add(place)
    db.flush()
    db.add(
        MapMarkerState(
            place_id=place.id, origin="USER_CREATED", visibility="VISIBLE", created_by="local-user"
        )
    )
    if payload.note:
        db.add(PlaceUserNote(place_id=place.id, markdown=payload.note, revision=1))
    record_event(
        db,
        "place.created.manual",
        "用户手工地点已创建",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        commit=False,
    )
    db.commit()
    return {"place_id": place.id, "origin": place.origin, "poi_binding_status": place.poi_binding_status}


@router.delete("/api/travel/places/{place_id}/user-created")
def soft_delete_manual_place(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if place.origin != "USER_CREATED":
        raise HTTPException(status_code=409, detail={"code": "CANNOT_DELETE_NON_USER_PLACE"})
    place.deleted_at, place.revision = utc_now(), place.revision + 1
    record_event(
        db,
        "place.deleted.manual",
        "用户手工地点已软删除",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        commit=False,
    )
    db.commit()
    return {"place_id": place.id, "deleted": True}


@router.post("/api/travel/places/{place_id}/user-created/restore")
def restore_manual_place(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None or place.origin != "USER_CREATED":
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    place.deleted_at, place.revision = None, place.revision + 1
    record_event(
        db,
        "place.restored.manual",
        "用户手工地点已恢复",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        commit=False,
    )
    db.commit()
    return {"place_id": place.id, "deleted": False}


@router.get("/api/travel/places/{place_id}/history")
def place_history(place_id: str, _: Protected, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Place, place_id) is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    events = db.scalars(
        select(SystemEvent)
        .where(SystemEvent.entity_type == "place", SystemEvent.entity_id == place_id)
        .order_by(SystemEvent.created_at.desc())
        .limit(50)
    ).all()
    return [event_view(event) for event in events]


@router.get("/api/travel/place-reviews")
def list_place_reviews(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    mentions = db.scalars(
        select(PlaceMention).where(
            PlaceMention.resolution_status == ResolutionStatus.REVIEW.value,
            PlaceMention.extraction_status != "USER_REJECTED",
        )
    ).all()
    return [
        {
            "mention_id": mention.id,
            "name": mention.name,
            "place_type": mention.place_type,
            "revision": mention.revision,
            "candidates": mention.metadata_json.get("poi_candidates", []),
            "reason": mention.metadata_json.get("reason", ""),
        }
        for mention in mentions
    ]


@router.get("/api/travel/place-reviews/count")
def place_review_count(_: Protected, db: Session = Depends(get_db)) -> dict[str, int]:
    return {
        "count": db.scalar(
            select(func.count(PlaceMention.id)).where(
                PlaceMention.resolution_status == ResolutionStatus.REVIEW.value,
                PlaceMention.extraction_status != "USER_REJECTED",
            )
        )
        or 0
    }


def _poi_candidate_view(candidate: object) -> dict:
    return {
        "provider": "AMAP",
        "provider_id": candidate.provider_id,
        "name": candidate.name,
        "address": candidate.address,
        "province": candidate.province,
        "city": candidate.city,
        "district": candidate.district,
        "typecode": candidate.typecode,
        "longitude": candidate.longitude,
        "latitude": candidate.latitude,
        "score": candidate.score,
        "match_reasons": candidate.match_reasons,
    }


@router.post("/api/travel/map/nearby-pois")
def nearby_pois(
    payload: NearbyPOIRequest,
    _: Protected,
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> list[dict]:
    web_key = store.get("amap:web-service-key") or settings.amap_api_key
    if not web_key:
        raise HTTPException(status_code=422, detail={"code": "POI_PROVIDER_UNAVAILABLE"})
    return [
        _poi_candidate_view(item)
        for item in AMapPOIProvider(web_key).around(payload.longitude, payload.latitude)
    ]


@router.post("/api/travel/map/place-search")
def search_map_pois(
    payload: POISearchRequest,
    _: Protected,
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> list[dict]:
    web_key = store.get("amap:web-service-key") or settings.amap_api_key
    if not web_key:
        raise HTTPException(status_code=422, detail={"code": "POI_PROVIDER_UNAVAILABLE"})
    query = payload.query.strip()
    candidates = AMapPOIProvider(web_key).search(query, "", city_limit=False)
    candidates.sort(key=lambda item: (query not in item.name, abs(len(item.name) - len(query)), item.name))
    return [_poi_candidate_view(item) for item in candidates]


@router.post("/api/travel/place-mentions/{mention_id}/poi-search")
def search_place_review(
    mention_id: str,
    payload: POISearchRequest,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    mention = db.get(PlaceMention, mention_id)
    if mention is None or mention.extraction_status == "USER_REJECTED":
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if mention.revision != payload.expected_revision:
        raise _revision_conflict(mention.revision)
    web_key = store.get("amap:web-service-key") or settings.amap_api_key
    if not web_key:
        raise HTTPException(status_code=422, detail={"code": "POI_PROVIDER_UNAVAILABLE"})
    candidates = AMapPOIProvider(web_key).search(
        payload.query, mention.city_hint, city_limit=bool(mention.city_hint)
    )
    mention.suggested_name = payload.query
    mention.metadata_json = {
        **mention.metadata_json,
        "poi_candidates": [_poi_candidate_view(item) for item in candidates],
    }
    mention.revision += 1
    record_event(
        db,
        "place_mention.poi_search",
        "用户修正了地点名称并重新搜索 POI",
        actor="user",
        entity_type="place_mention",
        entity_id=mention.id,
        commit=False,
    )
    db.commit()
    return {
        "mention_id": mention.id,
        "revision": mention.revision,
        "candidates": mention.metadata_json["poi_candidates"],
    }


@router.post("/api/travel/place-mentions/{mention_id}/confirm")
def confirm_place_review(
    mention_id: str, payload: POIReviewDecision, _: Protected, db: Session = Depends(get_db)
) -> dict:
    mention = db.get(PlaceMention, mention_id)
    if mention is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if mention.extraction_status == "USER_REJECTED":
        raise HTTPException(status_code=409, detail={"code": "MENTION_REJECTED"})
    if payload.expected_revision is not None and mention.revision != payload.expected_revision:
        raise _revision_conflict(mention.revision)
    candidate = next(
        (
            item
            for item in mention.metadata_json.get("poi_candidates", [])
            if item.get("provider_id") == payload.poi_id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(status_code=422, detail={"code": "INVALID_POI"})
    place = db.scalar(
        select(Place).where(Place.external_provider == "AMAP", Place.external_poi_id == payload.poi_id)
    )
    if place is None:
        place = Place(
            name=str(candidate["name"]),
            canonical_name=str(candidate["name"]),
            origin="AI_EXTRACTED",
            place_type=mention.place_type,
            province=str(candidate.get("province") or ""),
            city=str(candidate.get("city") or ""),
            district=str(candidate.get("district") or ""),
            address=str(candidate.get("address") or ""),
            latitude=float(candidate["latitude"]),
            longitude=float(candidate["longitude"]),
            external_provider="AMAP",
            external_poi_id=payload.poi_id,
            poi_binding_status="USER_CONFIRMED",
        )
        db.add(place)
        db.flush()
    mention.place_id, mention.resolution_status, mention.revision = (
        place.id,
        ResolutionStatus.CONFIRMED.value,
        mention.revision + 1,
    )
    materialize_place_insights(db, mention)
    record_event(
        db,
        "place.poi.bound",
        "用户确认了 POI 候选",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        commit=False,
    )
    db.commit()
    return {"place_id": place.id, "mention_id": mention.id, "resolution_status": mention.resolution_status}


@router.post("/api/travel/place-mentions/{mention_id}/{action}")
def update_place_mention_review(
    mention_id: str, action: str, _: Protected, db: Session = Depends(get_db)
) -> dict:
    if action not in {"reject", "restore"}:
        raise HTTPException(status_code=404, detail="不支持的地点标注操作")
    mention = db.get(PlaceMention, mention_id)
    if mention is None:
        raise HTTPException(status_code=404, detail={"code": "PLACE_NOT_FOUND"})
    if action == "reject" and mention.extraction_status == "USER_REJECTED":
        return {
            "mention_id": mention.id,
            "extraction_status": mention.extraction_status,
            "revision": mention.revision,
        }
    mention.extraction_status = "USER_REJECTED" if action == "reject" else "EXTRACTED"
    mention.resolution_status = "REJECTED" if action == "reject" else ResolutionStatus.REVIEW.value
    mention.revision += 1
    record_event(
        db,
        "place_mention.rejected" if action == "reject" else "place_mention.restored",
        "地点标注状态已更新",
        actor="user",
        entity_type="place_mention",
        entity_id=mention.id,
        commit=False,
    )
    db.commit()
    return {
        "mention_id": mention.id,
        "extraction_status": mention.extraction_status,
        "revision": mention.revision,
    }


@router.post("/api/travel/places/{place_id}/{action}")
def update_place_state(
    place_id: str,
    action: str,
    _: Protected,
    db: Session = Depends(get_db),
) -> dict:
    mapping = {"save": "SAVED", "visited": "VISITED", "dismiss": "DISMISSED", "planned": "PLANNED"}
    if action not in mapping:
        raise HTTPException(status_code=404, detail="不支持的地点操作")
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    place.user_state = mapping[action]
    record_event(
        db,
        "place.user_state.updated",
        f"地点状态已更新为 {mapping[action]}",
        actor="user",
        entity_type="place",
        entity_id=place.id,
        detail={"action": action, "user_state": mapping[action]},
        commit=False,
    )
    db.commit()
    return {"id": place.id, "user_state": place.user_state}


@router.get("/api/travel/route-drafts", response_model=list[RouteDraftView])
def list_routes(_: Protected, db: Session = Depends(get_db)) -> list[RouteDraftView]:
    return [_route_view(db, route) for route in db.scalars(select(RouteDraft)).all()]


@router.post("/api/travel/route-drafts", response_model=RouteDraftView)
def create_route(
    payload: RouteDraftCreate,
    _: Protected,
    db: Session = Depends(get_db),
) -> RouteDraftView:
    route = RouteDraft(name=payload.name, city=payload.city)
    db.add(route)
    db.flush()
    _replace_route_items(db, route.id, payload.place_ids)
    db.commit()
    return _route_view(db, route)


@router.put("/api/travel/route-drafts/{route_id}/items", response_model=RouteDraftView)
def update_route_items(
    route_id: str,
    payload: RouteDraftUpdate,
    _: Protected,
    db: Session = Depends(get_db),
) -> RouteDraftView:
    route = db.get(RouteDraft, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="路线清单不存在")
    _replace_route_items(db, route.id, payload.place_ids)
    db.commit()
    return _route_view(db, route)


@router.patch("/api/travel/route-drafts/{route_id}", response_model=RouteDraftView)
def update_route_metadata(
    route_id: str, payload: RouteDraftMetadataUpdate, _: Protected, db: Session = Depends(get_db)
) -> RouteDraftView:
    route = db.get(RouteDraft, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="路线清单不存在")
    route.name, route.city = payload.name.strip(), payload.city.strip()
    db.commit()
    return _route_view(db, route)


@router.delete("/api/travel/route-drafts/{route_id}")
def delete_route(route_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    route = db.get(RouteDraft, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="路线清单不存在")
    db.execute(delete(RouteDraftItem).where(RouteDraftItem.route_draft_id == route_id))
    db.delete(route)
    db.commit()
    return {"id": route_id, "status": "DELETED"}


def _replace_route_items(db: Session, route_id: str, place_ids: list[str]) -> None:
    for item in db.scalars(select(RouteDraftItem).where(RouteDraftItem.route_draft_id == route_id)).all():
        db.delete(item)
    for index, place_id in enumerate(dict.fromkeys(place_ids), start=1):
        if db.get(Place, place_id) is None:
            raise HTTPException(status_code=422, detail=f"地点不存在：{place_id}")
        db.add(RouteDraftItem(route_draft_id=route_id, place_id=place_id, sort_order=index))


def _route_view(db: Session, route: RouteDraft) -> RouteDraftView:
    items = db.scalars(
        select(RouteDraftItem)
        .where(RouteDraftItem.route_draft_id == route.id)
        .order_by(RouteDraftItem.sort_order)
    ).all()
    places = [db.get(Place, item.place_id) for item in items]
    return RouteDraftView(
        id=route.id,
        name=route.name,
        city=route.city,
        status=route.status,
        places=[preview_for_place(db, place) for place in places if place is not None],
    )


def _model_profile_view(setting: Setting) -> dict:
    value = setting.value_json if isinstance(setting.value_json, dict) else {}
    profile = model_profile_from_value(setting.key.removeprefix("model-profile:"), value)
    return {
        "id": profile.id,
        "name": str(value.get("name") or "未命名模型"),
        "provider": str(value.get("provider") or ""),
        "base_url": str(value.get("base_url") or ""),
        "model": str(value.get("model") or ""),
        "timeout_seconds": int(value.get("timeout_seconds") or 60),
        "api_key_saved": setting.is_secret_ref,
        "location": profile.location,
        "modalities": sorted(profile.modalities),
        "capabilities": sorted(item.value for item in profile.capabilities),
        "supports_json_mode": profile.supports_json_mode,
        "supports_json_schema": profile.supports_json_schema,
        "supports_thinking": profile.supports_thinking,
        "supports_tools": profile.supports_tools,
        "context_window": profile.context_window,
        "recommended_working_context": profile.recommended_working_context,
        "max_output_tokens": profile.max_output_tokens,
        "quality_tier": profile.quality_tier,
        "specialties": sorted(profile.specialties),
        "enabled": profile.enabled,
        "probe_results": value.get("probe_results") or {},
    }


def _model_profiles(db: Session) -> list[Setting]:
    return db.scalars(
        select(Setting).where(Setting.key.like("model-profile:%")).order_by(Setting.updated_at.desc())
    ).all()


def _routing_value(db: Session) -> dict[str, str | None]:
    setting = db.get(Setting, "model-routing")
    value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
    return {
        "primary_id": value.get("primary_id"),
        "fallback_id": value.get("fallback_id"),
    }


def _test_model_connection(value: dict, api_key: str | None) -> object:
    provider = _model_profile_provider(value, api_key)

    def call() -> object:
        return provider.generate(
            [{"role": "user", "content": '仅返回 JSON：{"ok":true}'}],
            model=str(value.get("model") or ""),
            options=(
                ProviderRequestOptions(thinking=False)
                if str(value.get("provider") or "").lower() == "ollama"
                else None
            ),
        )

    return (
        local_ai_resource_manager.run("MODEL_TEST", call)
        if model_profile_from_value("test", value).location == "LOCAL"
        else call()
    )


def _model_profile_provider(value: dict, api_key: str | None) -> LLMProvider:
    provider_name = str(value.get("provider") or "").lower()
    timeout = int(value.get("timeout_seconds") or 300)
    if provider_name == "ollama":
        return OllamaProvider(str(value.get("base_url") or ""), timeout)
    if not api_key:
        raise HTTPException(status_code=422, detail="请填写 API Key 后再进行真实测试")
    return OpenAICompatibleProvider(
        provider_name or "openai-compatible", str(value.get("base_url") or ""), api_key, timeout
    )


@router.get("/api/settings/model-profiles")
def list_model_profiles(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    return [_model_profile_view(item) for item in _model_profiles(db)]


@router.post("/api/settings/model-profiles")
def create_model_profile(
    payload: ModelProfileConfig,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    profile_id = new_id("model")
    value = payload.model_dump(mode="json", exclude={"api_key"})
    setting = Setting(key=f"model-profile:{profile_id}", value_json=value)
    if payload.api_key:
        store.set(f"model-profile:{profile_id}:api-key", payload.api_key)
        setting.is_secret_ref = True
    db.add(setting)
    record_event(db, "model_profile.created", f"已保存自定义模型：{payload.name}", actor="user")
    db.commit()
    return _model_profile_view(setting)


@router.put("/api/settings/model-profiles/{profile_id}")
def update_model_profile(
    profile_id: str,
    payload: ModelProfileConfig,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    setting = db.get(Setting, f"model-profile:{profile_id}")
    if setting is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    setting.value_json = payload.model_dump(mode="json", exclude={"api_key"})
    if payload.api_key:
        store.set(f"model-profile:{profile_id}:api-key", payload.api_key)
        setting.is_secret_ref = True
    record_event(db, "model_profile.updated", f"已更新模型：{payload.name}", actor="user")
    db.commit()
    return _model_profile_view(setting)


@router.delete("/api/settings/model-profiles/{profile_id}")
def delete_model_profile(profile_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, f"model-profile:{profile_id}")
    if setting is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    routing = _routing_value(db)
    if profile_id in set(routing.values()):
        raise HTTPException(status_code=409, detail="该模型正在被推理或转写路由使用，请先切换对应模型")
    if any(
        profile_id in (item.value_json or {}).values()
        for item in db.scalars(select(Setting).where(Setting.key.like("ai-stage-policy:%"))).all()
    ):
        raise HTTPException(status_code=409, detail="该模型正在被 AI 阶段策略使用，请先重置对应阶段")
    name = str(setting.value_json.get("name") or profile_id)
    db.delete(setting)
    record_event(db, "model_profile.deleted", f"已删除自定义模型：{name}", actor="user")
    db.commit()
    return {"status": "DELETED", "id": profile_id}


@router.get("/api/settings/model-routing")
def get_model_routing(_: Protected, db: Session = Depends(get_db)) -> dict[str, str | None]:
    return _routing_value(db)


@router.put("/api/settings/model-routing")
def save_model_routing(
    payload: ModelRoutingConfig, _: Protected, db: Session = Depends(get_db)
) -> dict[str, str | None]:
    for profile_id in payload.model_dump().values():
        if profile_id and db.get(Setting, f"model-profile:{profile_id}") is None:
            raise HTTPException(status_code=422, detail="路由模型必须从已保存的模型中选择")
    if payload.primary_id and payload.primary_id == payload.fallback_id:
        raise HTTPException(status_code=422, detail="主模型和备用模型不能相同")
    value = payload.model_dump()
    setting = db.get(Setting, "model-routing")
    if setting is None:
        setting = Setting(key="model-routing", value_json=value)
        db.add(setting)
    else:
        setting.value_json = value
    record_event(db, "model_routing.updated", "已更新通用模型路由", actor="user")
    db.commit()
    return value


def _stage_policy_setting(db: Session, stage: str) -> Setting | None:
    try:
        stage_spec(stage)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return db.get(Setting, f"ai-stage-policy:{stage}")


def _stage_profiles(db: Session) -> dict[str, dict]:
    return {
        setting.key.removeprefix("model-profile:"): setting.value_json
        for setting in _model_profiles(db)
        if isinstance(setting.value_json, dict)
    }


def _resolved_stage_policy_view(db: Session, stage: str, job: Job | None = None) -> dict:
    setting = _stage_policy_setting(db, stage)
    saved = setting.value_json if setting and isinstance(setting.value_json, dict) else None
    overrides = (job.payload_json.get("ai_overrides") or {}).get(stage) if job else None
    return resolve_stage_policy(stage, saved=saved, job_override=overrides).model_dump(mode="json")


@router.get("/api/ai/stages")
def list_ai_stages(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "stage": spec.stage,
            "capability": spec.capability,
            "parameter_spec": sorted(spec.allowed),
            "resolved_default": _resolved_stage_policy_view(db, spec.stage),
        }
        for spec in STAGE_SPECS.values()
    ]


@router.get("/api/ai/stage-policies")
def list_ai_stage_policies(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    return [_resolved_stage_policy_view(db, stage) for stage in STAGE_SPECS]


@router.get("/api/ai/stage-policies/{stage}")
def get_ai_stage_policy(stage: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    return _resolved_stage_policy_view(db, stage)


@router.put("/api/ai/stage-policies/{stage}")
def save_ai_stage_policy(
    stage: str, payload: AIStagePolicy, _: Protected, db: Session = Depends(get_db)
) -> dict:
    if payload.stage != stage:
        raise HTTPException(status_code=422, detail="路径与策略阶段必须一致")
    try:
        validate_stage_policy(payload, _stage_profiles(db))
        missing_pack = any(
            db.get(Setting, f"{DOMAIN_PACK_PREFIX}{pack_id}") is None for pack_id in payload.domain_pack_ids
        )
        if missing_pack:
            raise ValueError("阶段策略引用了不存在的领域包")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = _stage_policy_setting(db, stage)
    value = payload.model_dump(mode="json")
    value["version"] = int((existing.value_json if existing else {}).get("version") or 0) + 1
    if existing is None:
        db.add(Setting(key=f"ai-stage-policy:{stage}", value_json=value))
    else:
        existing.value_json = value
    record_event(db, "ai_stage_policy.updated", f"已更新 AI 阶段策略：{stage}", actor="user")
    db.commit()
    return _resolved_stage_policy_view(db, stage)


@router.delete("/api/ai/stage-policies/{stage}")
def delete_ai_stage_policy(stage: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    setting = _stage_policy_setting(db, stage)
    if setting:
        db.delete(setting)
        record_event(db, "ai_stage_policy.reset", f"已恢复默认 AI 阶段策略：{stage}", actor="user")
        db.commit()
    return _resolved_stage_policy_view(db, stage)


@router.get("/api/ai/domain-packs")
def list_domain_packs(_: Protected, db: Session = Depends(get_db)) -> list[dict]:
    packs = db.scalars(
        select(Setting).where(Setting.key.like(f"{DOMAIN_PACK_PREFIX}%")).order_by(Setting.key)
    ).all()
    return [DomainPack(**item.value_json).model_dump(mode="json") for item in packs]


@router.post("/api/ai/domain-packs")
def create_domain_pack(payload: DomainPack, _: Protected, db: Session = Depends(get_db)) -> dict:
    key = f"{DOMAIN_PACK_PREFIX}{payload.id}"
    if db.get(Setting, key):
        raise HTTPException(status_code=409, detail="领域包 ID 已存在")
    db.add(Setting(key=key, value_json=payload.model_dump(mode="json")))
    record_event(db, "ai_domain_pack.created", f"已创建领域包：{payload.name}", actor="user")
    db.commit()
    return payload.model_dump(mode="json")


@router.put("/api/ai/domain-packs/{pack_id}")
def update_domain_pack(
    pack_id: str, payload: DomainPack, _: Protected, db: Session = Depends(get_db)
) -> dict:
    if payload.id != pack_id:
        raise HTTPException(status_code=422, detail="路径与领域包 ID 必须一致")
    setting = db.get(Setting, f"{DOMAIN_PACK_PREFIX}{pack_id}")
    if setting is None:
        raise HTTPException(status_code=404, detail="领域包不存在")
    setting.value_json = payload.model_dump(mode="json")
    record_event(db, "ai_domain_pack.updated", f"已更新领域包：{payload.name}", actor="user")
    db.commit()
    return payload.model_dump(mode="json")


@router.delete("/api/ai/domain-packs/{pack_id}")
def delete_domain_pack(pack_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    setting = db.get(Setting, f"{DOMAIN_PACK_PREFIX}{pack_id}")
    if setting is None:
        raise HTTPException(status_code=404, detail="领域包不存在")
    in_use = any(
        pack_id in ((item.value_json or {}).get("domain_pack_ids") or [])
        for item in db.scalars(select(Setting).where(Setting.key.like("ai-stage-policy:%"))).all()
    )
    if in_use:
        raise HTTPException(status_code=409, detail="领域包正在被阶段策略使用，请先移除关联")
    db.delete(setting)
    record_event(db, "ai_domain_pack.deleted", f"已删除领域包：{pack_id}", actor="user")
    db.commit()
    return {"status": "DELETED", "id": pack_id}


@router.get("/api/settings/transcript-processing")
def get_transcript_processing(_: Protected, db: Session = Depends(get_db)) -> dict:
    return transcript_processing_config(db).model_dump()


@router.put("/api/settings/transcript-processing")
def save_transcript_processing(
    payload: TranscriptProcessingConfig,
    _: Protected,
    db: Session = Depends(get_db),
) -> dict:
    value = payload.model_dump()
    setting = db.get(Setting, "transcript-processing")
    if setting is None:
        db.add(Setting(key="transcript-processing", value_json=value))
    else:
        setting.value_json = value
    record_event(
        db,
        "transcript_processing.updated",
        "已更新转写分段与超时参数",
        actor="user",
        detail=value,
        commit=False,
    )
    db.commit()
    return value


def _prompt_supplements_view(db: Session) -> dict:
    setting = db.get(Setting, PROMPT_SUPPLEMENT_SETTING_KEY)
    values = PromptSupplementsConfig(
        **(setting.value_json if setting and isinstance(setting.value_json, dict) else {})
    ).model_dump()
    return {
        **values,
        "core_contracts": PROMPT_CORE_CONTRACTS,
        "max_length": 1000,
        "version": "prompt-supplement-v1",
        "hashes": {role: prompt_supplement_hash(db, role) for role in values},
    }


@router.get("/api/settings/prompt-supplements")
def get_prompt_supplements(_: Protected, db: Session = Depends(get_db)) -> dict:
    return _prompt_supplements_view(db)


@router.put("/api/settings/prompt-supplements")
def save_prompt_supplements(
    payload: PromptSupplementsConfig,
    _: Protected,
    db: Session = Depends(get_db),
) -> dict:
    setting = db.get(Setting, PROMPT_SUPPLEMENT_SETTING_KEY)
    values = payload.model_dump()
    if setting is None:
        setting = Setting(key=PROMPT_SUPPLEMENT_SETTING_KEY, value_json=values)
        db.add(setting)
    else:
        setting.value_json = values
    db.flush()
    hashes = {role: prompt_supplement_hash(db, role) for role in values}
    record_event(
        db,
        "prompt_supplements.updated",
        "已更新 AI 补充提示词",
        actor="user",
        entity_type="setting",
        entity_id=PROMPT_SUPPLEMENT_SETTING_KEY,
        detail={
            "active_roles": [role for role, value in values.items() if value],
            "hashes": hashes,
        },
        commit=False,
    )
    db.commit()
    return _prompt_supplements_view(db)


@router.post("/api/settings/model-profiles/{profile_id}/test")
def test_model_profile(
    profile_id: str,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    setting = db.get(Setting, f"model-profile:{profile_id}")
    if setting is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    value = setting.value_json
    try:
        result = _test_model_connection(value, store.get(f"model-profile:{profile_id}:api-key"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型连通测试失败：{str(exc)[:240]}") from exc
    record_event(db, "model_profile.tested", f"真实测试成功：{value.get('name', profile_id)}", actor="user")
    db.commit()
    return {
        "status": "READY",
        "message": "已完成真实推理连通测试。",
        "response_preview": result.content[:200],
    }


@router.post("/api/settings/model-profiles/test-draft")
def test_model_profile_draft(payload: ModelProfileConfig, _: Protected) -> dict:
    """Run a transient model connectivity test without persisting the draft or its secret."""
    value = payload.model_dump(mode="json", exclude={"api_key"})
    try:
        result = _test_model_connection(value, payload.api_key)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型连通测试失败：{str(exc)[:240]}") from exc
    return {
        "status": "READY",
        "message": "草稿已完成真实推理连通测试，尚未保存配置。",
        "response_preview": result.content[:200],
    }


@router.post("/api/settings/model-profiles/{profile_id}/probe")
def probe_saved_model_profile(
    profile_id: str,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    setting = db.get(Setting, f"model-profile:{profile_id}")
    if setting is None or not isinstance(setting.value_json, dict):
        raise HTTPException(status_code=404, detail="模型配置不存在")
    value = dict(setting.value_json)
    try:
        profile = model_profile_from_value(profile_id, value)
        provider = _model_profile_provider(value, store.get(f"model-profile:{profile_id}:api-key"))

        def call() -> dict[str, str]:
            return probe_model_profile(provider, profile)

        results = local_ai_resource_manager.run("MODEL_TEST", call) if profile.location == "LOCAL" else call()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型能力探测失败：{str(exc)[:240]}") from exc
    value["probe_results"] = results
    value["capabilities"] = [key for key, status in results.items() if status == "PASS"]
    value["supports_json_mode"] = results.get("STRUCTURED_EXTRACTION") == "PASS"
    setting.value_json = value
    record_event(
        db,
        "model_profile.probed",
        f"已完成模型能力探测：{value.get('name', profile_id)}",
        actor="user",
        detail={"pass_count": sum(status == "PASS" for status in results.values())},
    )
    db.commit()
    return _model_profile_view(setting)


@router.post("/api/settings/model-profiles/probe-draft")
def probe_model_profile_draft(payload: ModelProfileConfig, _: Protected) -> dict:
    """Probe a draft without persisting its profile or API key."""
    value = payload.model_dump(mode="json", exclude={"api_key"})
    try:
        profile = model_profile_from_value("draft", value)
        provider = _model_profile_provider(value, payload.api_key)
        def probe() -> dict[str, str]:
            return probe_model_profile(provider, profile)

        if profile.location == "LOCAL":
            results = local_ai_resource_manager.run("MODEL_TEST", probe)
        else:
            results = probe()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"草稿能力探测失败：{str(exc)[:240]}") from exc
    capabilities = [key for key, status in results.items() if status == "PASS"]
    return {
        "status": "READY",
        "message": "草稿能力探测已完成，保存后才会写入模型配置。",
        "probe_results": results,
        "capabilities": capabilities,
        "supports_json_mode": "STRUCTURED_EXTRACTION" in capabilities,
    }


@router.get("/api/settings/providers")
def provider_settings(
    _: Protected,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    defaults = {
        "default": {"provider": "DeepSeek", "base_url": settings.deepseek_base_url, "model": "deepseek-chat"},
        "fallback": {"provider": "MiMo", "base_url": settings.mimo_base_url, "model": "mimo-v2-flash"},
        "local": {"provider": "Ollama", "base_url": settings.ollama_base_url, "model": "qwen2.5:7b"},
        "video_note_summary": {
            "provider": "DeepSeek",
            "base_url": settings.deepseek_base_url,
            "model": settings.video_note_model or "deepseek-chat",
        },
        "travel_place_extraction": {
            "provider": "DeepSeek",
            "base_url": settings.deepseek_base_url,
            "model": settings.travel_extraction_model or "deepseek-chat",
        },
        "place_note_summary": {
            "provider": "DeepSeek",
            "base_url": settings.deepseek_base_url,
            "model": settings.place_note_model or "deepseek-chat",
        },
    }
    for role in defaults:
        saved = db.get(Setting, f"provider:{role}")
        if saved:
            defaults[role].update(saved.value_json)
    return defaults


@router.put("/api/settings/providers/{role}")
def save_provider(
    role: str,
    payload: ProviderConfig,
    _: Protected,
    db: Session = Depends(get_db),
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    if role not in {
        "default",
        "fallback",
        "local",
        "video_note_summary",
        "travel_place_extraction",
        "place_note_summary",
    }:
        raise HTTPException(status_code=404, detail="未知 Provider 角色")
    value = {"provider": payload.provider, "base_url": payload.base_url, "model": payload.model}
    setting = db.get(Setting, f"provider:{role}")
    if setting is None:
        setting = Setting(key=f"provider:{role}", value_json=value)
        db.add(setting)
    else:
        setting.value_json = value
    if payload.api_key:
        store.set(f"provider:{role}:api-key", payload.api_key)
        setting.is_secret_ref = True
    db.commit()
    return {**value, "api_key_saved": setting.is_secret_ref}


@router.post("/api/settings/providers/{role}/test")
def test_provider(
    role: str,
    payload: ProviderConfig,
    _: Protected,
    store: SecretStore = Depends(get_secret_store),
) -> dict:
    if role not in {
        "default",
        "fallback",
        "local",
        "video_note_summary",
        "travel_place_extraction",
        "place_note_summary",
    }:
        raise HTTPException(status_code=404, detail="未知 Provider 角色")
    provider_name = payload.provider.lower()
    try:
        if provider_name == "ollama":
            result = OllamaProvider(payload.base_url, payload.timeout_seconds).generate(
                [{"role": "user", "content": '仅返回 JSON：{"ok":true}'}],
                model=payload.model,
            )
        else:
            api_key = payload.api_key or store.get(f"provider:{role}:api-key")
            if not api_key:
                raise HTTPException(status_code=422, detail="尚未保存 API Key")
            result = OpenAICompatibleProvider(
                provider_name,
                payload.base_url,
                api_key,
                payload.timeout_seconds,
            ).generate(
                [{"role": "user", "content": '仅返回 JSON：{"ok":true}'}],
                model=payload.model,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Provider 连通测试失败：{str(exc)[:240]}") from exc
    return {
        "provider": payload.provider,
        "status": "READY",
        "message": "已完成真实推理连通测试。",
        "base_url": payload.base_url,
        "model": payload.model,
        "response_preview": result.content[:200],
    }
