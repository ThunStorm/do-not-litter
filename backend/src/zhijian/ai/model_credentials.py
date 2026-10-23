"""Server-only LocalAiMux credentials scoped to a validated service endpoint."""

import hashlib
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.model_catalog import catalog_origin
from zhijian.ai.reliability import AIProviderError
from zhijian.core.secret_store import SecretStore
from zhijian.db.models import Setting


def mux_credential_account(value: dict) -> str | None:
    if str(value.get("provider") or "").strip().lower() != "localaimux":
        return None
    base = str(value.get("base_url") or "")
    origin = catalog_origin(base)
    identity = repr((*origin, urlsplit(base).path.rstrip("/")))
    return "localmux:" + hashlib.sha256(identity.encode()).hexdigest() + ":api-key"


def resolve_model_key(
    db: Session,
    store: SecretStore,
    value: dict,
    supplied: str | None = None,
    profile_id: str | None = None,
) -> str | None:
    if supplied:
        return supplied
    account = mux_credential_account(value)
    if account:
        shared = store.get(account)
        if shared:
            return shared
        keys = set()
        for setting in db.scalars(select(Setting).where(Setting.key.startswith("model-profile:"))):
            saved = setting.value_json or {}
            try:
                matches = mux_credential_account(saved) == account
            except AIProviderError:
                continue
            if matches:
                key = store.get(f"{setting.key}:api-key")
                if key:
                    keys.add(key)
        if len(keys) > 1:
            raise ValueError("LocalAiMux 已保存凭据不一致，请填写该服务统一使用的 API Key")
        return next(iter(keys), None)
    return store.get(f"model-profile:{profile_id}:api-key") if profile_id else None


def save_model_key(store: SecretStore, value: dict, profile_id: str, key: str) -> None:
    account = mux_credential_account(value)
    if account:
        store.set(account, key)
    store.set(f"model-profile:{profile_id}:api-key", key)
