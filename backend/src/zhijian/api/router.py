from __future__ import annotations

import asyncio
import hashlib
import platform
from datetime import UTC, datetime
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
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import SecretStore
from zhijian.core.time import utc_now
from zhijian.db.models import (
    AccessSession,
    Claim,
    ContentItem,
    Evidence,
    Job,
    JobStep,
    Place,
    PlaceObservation,
    RouteDraft,
    RouteDraftItem,
    Segment,
    Setting,
    Snapshot,
    Source,
    SystemEvent,
)
from zhijian.db.session import get_db
from zhijian.domain.enums import JobStatus, ResolutionStatus
from zhijian.domain.schemas import (
    CaptureRequest,
    CaptureResponse,
    ContentView,
    GeneralConfig,
    JobView,
    MapMarker,
    MapOverviewView,
    PlacePreview,
    ProfileConfig,
    ProviderConfig,
    RouteDraftCreate,
    RouteDraftUpdate,
    RouteDraftView,
    SessionRequest,
)
from zhijian.providers.llm import OllamaProvider, OpenAICompatibleProvider
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
from zhijian.services.capture import create_capture_job, safe_upload_path

router = APIRouter()
Protected = Annotated[object | None, Depends(require_session)]


def job_view(job: Job) -> JobView:
    return JobView(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        current_step=job.current_step,
        progress=job.progress,
        title=str(job.payload_json.get("title") or job.payload_json.get("locator") or "未命名任务"),
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
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
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=settings.session_ttl_hours * 3600,
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
        "jobs": [job_view(job).model_dump() for job in jobs],
        "contents": [content_view(item).model_dump() for item in contents],
    }


@router.post("/api/capture", response_model=CaptureResponse)
def capture(
    payload: CaptureRequest,
    _: Protected,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CaptureResponse:
    if not payload.url and not payload.text:
        raise HTTPException(status_code=422, detail="URL 与正文至少提供一项")
    locator = str(payload.url) if payload.url else "text://local"
    source, job = create_capture_job(
        db,
        settings,
        locator=locator,
        source_type="URL" if payload.url else "TEXT",
        title=payload.title or "",
        text=payload.text or "",
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
    return [job_view(job) for job in db.scalars(select(Job).order_by(Job.created_at.desc())).all()]


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    steps = db.scalars(select(JobStep).where(JobStep.job_id == job_id)).all()
    return {
        **job_view(job).model_dump(),
        "steps": [
            {
                "name": step.step_name,
                "status": step.status,
                "progress": step.progress,
                "error": step.error,
            }
            for step in steps
        ],
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
            if session is None or session.expires_at < utc_now():
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
            payload = {"type": "job.progress", **job_view(job).model_dump(mode="json")}
            await websocket.send_json(payload)
            if job.status in {
                JobStatus.COMPLETED.value,
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
def retry_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    job.status = JobStatus.QUEUED.value
    job.error = None
    job.finished_at = None
    job.lease_owner = None
    job.lease_expire_at = None
    job.retry_count += 1
    db.commit()
    return {"status": job.status, "retry_count": job.retry_count}


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    job.status = JobStatus.CANCELLED.value
    job.finished_at = datetime.now().astimezone()
    db.commit()
    return {"status": job.status}


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
    }


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


@router.get("/api/logs")
def list_logs(
    _: Protected,
    level: str | None = None,
    component: str | None = None,
    query: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(limit)
    if level:
        statement = statement.where(SystemEvent.level == level.upper())
    if component:
        statement = statement.where(SystemEvent.component == component)
    if query:
        statement = statement.where(SystemEvent.message.contains(query))
    return [
        {
            "id": event.id,
            "created_at": event.created_at,
            "level": event.level,
            "component": event.component,
            "event_type": event.event_type,
            "message": event.message,
            "actor": event.actor,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "detail": event.detail_json,
        }
        for event in db.scalars(statement).all()
    ]


@router.get("/api/travel/map", response_model=MapOverviewView)
def map_overview(
    _: Protected,
    city: str = "厦门市",
    district: str | None = None,
    place_type: str | None = None,
    user_state: str | None = None,
    query: str | None = None,
    selected_place_id: str | None = None,
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    db: Session = Depends(get_db),
) -> MapOverviewView:
    statement = select(Place).where(
        Place.resolution_status == ResolutionStatus.CONFIRMED.value,
        Place.city == city,
    )
    if district:
        statement = statement.where(Place.district == district)
    if place_type:
        statement = statement.where(Place.place_type == place_type)
    if user_state:
        statement = statement.where(Place.user_state == user_state)
    if query:
        statement = statement.where(Place.name.contains(query) | Place.address.contains(query))
    if bbox:
        try:
            west, south, east, north = (float(part) for part in bbox.split(","))
            statement = statement.where(
                Place.longitude.between(west, east), Place.latitude.between(south, north)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="bbox 格式应为 west,south,east,north") from exc
    places = db.scalars(statement.order_by(Place.name.asc())).all()
    selected = next((place for place in places if place.id == selected_place_id), None)
    if selected is None and places:
        selected = places[0]
    route_count = db.scalar(select(func.count(RouteDraftItem.id))) or 0
    return MapOverviewView(
        total_places=len(places),
        visible_places=len(places),
        markers=[
            MapMarker(
                id=place.id,
                name=place.name,
                place_type=place.place_type,
                latitude=place.latitude,
                longitude=place.longitude,
                user_state=place.user_state,
                summary=place.summary,
            )
            for place in places
        ],
        selected_place_id=selected.id if selected else None,
        selected_preview=preview_for_place(db, selected) if selected else None,
        route_draft_count=route_count,
    )


@router.get("/api/travel/places/{place_id}/preview", response_model=PlacePreview)
def place_preview(place_id: str, _: Protected, db: Session = Depends(get_db)) -> PlacePreview:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    return preview_for_place(db, place)


@router.get("/api/travel/places/{place_id}")
def place_detail(place_id: str, _: Protected, db: Session = Depends(get_db)) -> dict:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    return {
        **preview_for_place(db, place).model_dump(),
        "coordinate_system": place.coordinate_system,
        "coordinates": [place.longitude, place.latitude],
        "provider": place.external_provider,
        "external_poi_id": place.external_poi_id,
        "metadata": place.metadata_json,
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
    if role not in {"default", "fallback", "local"}:
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
    if role not in {"default", "fallback", "local"}:
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
