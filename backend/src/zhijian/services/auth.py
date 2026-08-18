from __future__ import annotations

import hashlib
import hmac
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import SecretStore, build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import AccessSession
from zhijian.db.session import get_db

LAN_TOKEN_KEY = "lan-access-token"
_attempts: dict[str, deque] = defaultdict(deque)
_locked_until: dict[str, datetime] = {}
_attempt_lock = Lock()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_secret_store(settings: Settings = Depends(get_settings)) -> SecretStore:
    return build_secret_store(settings.secret_store, settings.data_dir)


def ensure_lan_token(store: SecretStore) -> str:
    current = store.get(LAN_TOKEN_KEY)
    if current and len(current) == 4 and current.isdigit():
        return current
    token = f"{secrets.randbelow(10_000):04d}"
    store.set(LAN_TOKEN_KEY, token)
    return token


def rotate_lan_token(store: SecretStore) -> str:
    previous = store.get(LAN_TOKEN_KEY)
    token = ensure_lan_token(store)
    while token == previous:
        token = f"{secrets.randbelow(10_000):04d}"
        store.set(LAN_TOKEN_KEY, token)
    return token


def assert_auth_attempt_allowed(client_host: str, settings: Settings) -> None:
    now = utc_now()
    with _attempt_lock:
        locked = _locked_until.get(client_host)
        if locked and locked > now:
            seconds = max(1, int((locked - now).total_seconds()))
            raise HTTPException(status_code=429, detail=f"尝试过多，请在 {seconds} 秒后重试")
        queue = _attempts[client_host]
        cutoff = now - timedelta(seconds=settings.auth_window_seconds)
        while queue and queue[0] < cutoff:
            queue.popleft()


def record_auth_failure(client_host: str, settings: Settings) -> None:
    now = utc_now()
    with _attempt_lock:
        queue = _attempts[client_host]
        queue.append(now)
        if len(queue) >= settings.auth_max_attempts:
            _locked_until[client_host] = now + timedelta(seconds=settings.auth_lockout_seconds)
            queue.clear()


def clear_auth_failures(client_host: str) -> None:
    with _attempt_lock:
        _attempts.pop(client_host, None)
        _locked_until.pop(client_host, None)


def create_session(db: Session, client_label: str, ttl_hours: int) -> tuple[str, AccessSession]:
    raw = secrets.token_urlsafe(36)
    now = utc_now()
    session = AccessSession(
        token_hash=token_hash(raw),
        expires_at=now + timedelta(hours=ttl_hours),
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
