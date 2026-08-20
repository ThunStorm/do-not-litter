from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from zhijian.api.router import router
from zhijian.api.video_notes import router as video_notes_router
from zhijian.core.config import get_settings
from zhijian.core.logging import configure_logging
from zhijian.core.secret_store import build_secret_store
from zhijian.db.session import SessionLocal, init_database
from zhijian.services.audit import record_event
from zhijian.services.auth import ensure_lan_token
from zhijian.services.seed import seed_demo_data


class SPAStaticFiles(StaticFiles):
    """Serve index.html for client-side routes while preserving real asset 404s."""

    async def get_response(self, path: str, scope: dict) -> object:
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404 or path.startswith("assets/"):
                return response
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or path.startswith("assets/"):
                raise
        return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings, "api")
    init_database()
    store = build_secret_store(settings.secret_store, settings.data_dir)
    ensure_lan_token(store)
    with SessionLocal() as db:
        record_event(db, "service.api.started", "至简 API 已启动", actor="system")
    if settings.app_env == "development":
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="至简 API", version="0.2.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_log(request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex[:16]
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logging.getLogger("zhijian.api").exception(
                "request failed",
                extra={"request_id": request_id, "event_type": "request.failed", "path": request.url.path},
            )
            raise
        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("zhijian.api").info(
            "%s %s %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "event_type": "request.completed",
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Requested-With", "X-Request-ID"],
    )
    app.include_router(router)
    app.include_router(video_notes_router)
    frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("zhijian.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
