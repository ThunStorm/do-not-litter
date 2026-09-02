from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

import httpx

from zhijian.core.time import as_utc, utc_now

GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
LOGIN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Zhijian/1.0",
    "Referer": "https://www.bilibili.com/",
}
QR_TTL_SECONDS = 180


class BilibiliAuthError(RuntimeError):
    pass


@dataclass(slots=True)
class _QRSession:
    qrcode_key: str
    expires_at: datetime


@dataclass(slots=True)
class BilibiliLoginPoll:
    status: str
    message: str
    cookie: str | None = None
    account_name: str | None = None
    account_id: str | None = None


_sessions: dict[str, _QRSession] = {}
_sessions_lock = Lock()


def start_bilibili_login(*, timeout: int, proxy_url: str = "") -> dict[str, Any]:
    _discard_expired_sessions()
    response = _get(GENERATE_URL, timeout=timeout, proxy_url=proxy_url)
    payload = _json(response, "无法生成 Bilibili 登录二维码")
    data = payload.get("data") or {}
    qr_url = str(data.get("url") or "")
    qrcode_key = str(data.get("qrcode_key") or "")
    if payload.get("code") != 0 or not qr_url.startswith("https://") or len(qrcode_key) != 32:
        raise BilibiliAuthError(str(payload.get("message") or "无法生成 Bilibili 登录二维码"))
    session_id = secrets.token_urlsafe(24)
    expires_at = utc_now() + timedelta(seconds=QR_TTL_SECONDS)
    with _sessions_lock:
        _sessions[session_id] = _QRSession(qrcode_key=qrcode_key, expires_at=expires_at)
    return {
        "session_id": session_id,
        "qr_url": qr_url,
        "expires_at": expires_at,
        "status": "WAITING_SCAN",
    }


def poll_bilibili_login(
    session_id: str, *, timeout: int, proxy_url: str = ""
) -> BilibiliLoginPoll:
    with _sessions_lock:
        session = _sessions.get(session_id)
    if session is None or as_utc(session.expires_at) <= utc_now():
        _forget_session(session_id)
        return BilibiliLoginPoll("EXPIRED", "二维码已过期，请刷新后重试")
    response = _get(
        POLL_URL,
        params={"qrcode_key": session.qrcode_key},
        timeout=timeout,
        proxy_url=proxy_url,
    )
    payload = _json(response, "无法读取扫码状态")
    data = payload.get("data") or {}
    status_code = int(data.get("code") or 0)
    if payload.get("code") != 0:
        raise BilibiliAuthError(str(payload.get("message") or "无法读取扫码状态"))
    if status_code == 86101:
        return BilibiliLoginPoll("WAITING_SCAN", "等待使用哔哩哔哩 App 扫码")
    if status_code == 86090:
        return BilibiliLoginPoll("WAITING_CONFIRM", "已扫码，请在手机上确认登录")
    if status_code == 86038:
        _forget_session(session_id)
        return BilibiliLoginPoll("EXPIRED", "二维码已过期，请刷新后重试")
    if status_code != 0:
        raise BilibiliAuthError(str(data.get("message") or "扫码登录失败"))
    cookie = _cookie_header(response)
    if "SESSDATA=" not in cookie:
        raise BilibiliAuthError("扫码成功，但 Bilibili 未返回有效登录凭证")
    account = _verify_cookie(cookie, timeout=timeout, proxy_url=proxy_url)
    _forget_session(session_id)
    return BilibiliLoginPoll(
        "SUCCESS",
        "登录成功",
        cookie=cookie,
        account_name=str(account.get("uname") or "Bilibili 用户"),
        account_id=str(account.get("mid") or ""),
    )


def _get(
    url: str,
    *,
    timeout: int,
    proxy_url: str,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    try:
        with httpx.Client(timeout=timeout, proxy=proxy_url or None, follow_redirects=False) as client:
            response = client.get(url, params=params, headers=headers or LOGIN_HEADERS)
            response.raise_for_status()
            return response
    except httpx.HTTPError as exc:
        raise BilibiliAuthError("Bilibili 登录服务暂时不可用") from exc


def _json(response: httpx.Response, fallback: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise BilibiliAuthError(fallback) from exc
    if not isinstance(payload, dict):
        raise BilibiliAuthError(fallback)
    return payload


def _cookie_header(response: httpx.Response) -> str:
    values: dict[str, str] = {}
    for cookie in response.cookies.jar:
        values[cookie.name] = cookie.value
    preferred = ["SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid"]
    names = [name for name in preferred if name in values]
    names.extend(sorted(name for name in values if name not in names))
    return "; ".join(f"{name}={values[name]}" for name in names)


def _verify_cookie(cookie: str, *, timeout: int, proxy_url: str) -> dict[str, Any]:
    response = _get(
        NAV_URL,
        timeout=timeout,
        proxy_url=proxy_url,
        headers={**LOGIN_HEADERS, "Cookie": cookie},
    )
    payload = _json(response, "无法验证 Bilibili 登录状态")
    data = payload.get("data") or {}
    if payload.get("code") != 0 or not data.get("isLogin"):
        raise BilibiliAuthError("Bilibili 登录凭证验证失败，请刷新二维码重试")
    return data


def _forget_session(session_id: str) -> None:
    with _sessions_lock:
        _sessions.pop(session_id, None)


def _discard_expired_sessions() -> None:
    now = utc_now()
    with _sessions_lock:
        expired = [key for key, value in _sessions.items() if as_utc(value.expires_at) <= now]
        for key in expired:
            _sessions.pop(key, None)
