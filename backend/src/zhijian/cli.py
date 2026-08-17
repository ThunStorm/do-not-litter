from __future__ import annotations

from zhijian.core.config import get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.db.session import SessionLocal, init_database
from zhijian.services.auth import ensure_lan_token
from zhijian.services.seed import seed_demo_data


def init_command() -> None:
    settings = get_settings()
    init_database()
    store = build_secret_store(settings.secret_store, settings.data_dir)
    token = ensure_lan_token(store)
    if settings.app_env == "development":
        with SessionLocal() as db:
            seed_demo_data(db)
    print(f"至简已初始化：{settings.data_dir.resolve()}")
    print(f"局域网 Token（请妥善保存）：{token}")


if __name__ == "__main__":
    init_command()
