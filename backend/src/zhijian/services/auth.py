from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import SecretStore, build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import AccessSession
from zhijian.db.session import get_db

LAN_TOKEN_KEY = "lan-access-token"


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_secret_store(settings: Settings = Depends(get_settings)) -> SecretStore:
    return build_secret_store(settings.secret_store, settings.data_dir)


def ensure_lan_token(store: SecretStore) -> str:
    current = store.get(LAN_TOKEN_KEY)
    if current:
        return current
    token = secrets.token_urlsafe(36)
    store.set(LAN_TOKEN_KEY, token)
    return token


def create_session(db: Session, client_label: str) -> tuple[str, AccessSession]:
    raw = secrets.token_urlsafe(36)
    now = utc_now()
    session = AccessSession(
        token_hash=token_hash(raw),
        expires_at=now + timedelta(hours=get_settings().session_ttl_hours),
        client_label=client_label,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw, session


def verify_lan_token(candidate: str, store: SecretStore) -> bool:
    expected = ensure_lan_token(store)
    return hmac.compare_digest(candidate, expected)


def require_session(
    request: Request,
    session_token: str | None = Cookie(default=None, alias="zhijian_session"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AccessSession | None:
    client_host = request.client.host if request.client else ""
    if settings.allow_localhost_without_session and client_host in {"127.0.0.1", "::1", "testclient"}:
        return None
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要局域网会话")
    now = utc_now()
    db.execute(delete(AccessSession).where(AccessSession.expires_at < now))
    session = db.scalar(select(AccessSession).where(AccessSession.token_hash == token_hash(session_token)))
    if session is None or session.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会话已失效")
    session.last_seen_at = now
    db.commit()
    return session
