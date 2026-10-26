from __future__ import annotations

from collections.abc import Generator
from urllib.parse import quote

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from zhijian.core.config import Settings, get_settings
from zhijian.db.base import Base


def build_engine(settings: Settings | None = None) -> Engine:
    active = settings or get_settings()
    engine = create_engine(
        f"sqlite:///file:{quote(str(active.database_path))}?mode=rw&uri=true"
        if active.is_production
        else f"sqlite:///{active.database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection: object, _: object) -> None:
        if active.is_production and active.storage_config.exists():
            from zhijian.core.storage import read_json, validate_root

            if validate_root(read_json(active.storage_config)) != active.data_dir:
                raise RuntimeError("数据库连接根目录与启动配置不一致")
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_database() -> None:
    from zhijian.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
