from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from zhijian.api.router import router
from zhijian.core.config import Settings, get_settings
from zhijian.db.base import Base
from zhijian.db.session import build_engine, get_db
from zhijian.services.seed import seed_demo_data


@pytest.fixture
def app_and_session(tmp_path) -> Generator[tuple[FastAPI, sessionmaker[Session]], None, None]:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        allow_localhost_without_session=True,
        secret_store="file",
    )
    settings.ensure_directories()
    engine = build_engine(settings)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        seed_demo_data(db)

    app = FastAPI()
    app.include_router(router)

    def override_db() -> Generator[Session, None, None]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    yield app, factory
    engine.dispose()


@pytest.fixture
def client(app_and_session) -> TestClient:
    app, _ = app_and_session
    return TestClient(app)
