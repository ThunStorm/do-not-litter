from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from zhijian.api.router import router
from zhijian.core.config import get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.db.session import SessionLocal, init_database
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
    init_database()
    store = build_secret_store(settings.secret_store, settings.data_dir)
    ensure_lan_token(store)
    if settings.app_env == "development":
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="至简 API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )
    app.include_router(router)
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
