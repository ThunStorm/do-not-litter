from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from zhijian.core.url_policy import HttpsHostPolicy

ALLOWED_HOSTS = {
    "www.bilibili.com",
    "m.bilibili.com",
    "bilibili.com",
    "b23.tv",
    "www.b23.tv",
    "player.bilibili.com",
}
PAGE_URL_POLICY = HttpsHostPolicy(exact_hosts=frozenset(ALLOWED_HOSTS))
_VIDEO_ID = re.compile(r"^/(?:s/)?video/(BV[0-9A-Za-z]+|av[0-9]+)(?:/|$)", re.I)
_BVID = re.compile(r"BV[0-9A-Za-z]+", re.I)


@dataclass(frozen=True, slots=True)
class BilibiliURL:
    bvid: str | None
    page_number: int
    is_short: bool
    aid: str | None = None


def normalize_bilibili_url(url: str) -> str:
    """Upgrade known legacy HTTP links locally; never request an HTTP endpoint."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if parsed.scheme == "http":
        secure = parsed._replace(scheme="https").geturl()
        if PAGE_URL_POLICY.allows(secure):
            return secure
    return url


def parse_bilibili_url(url: str) -> BilibiliURL:
    parsed = urlparse(normalize_bilibili_url(url))
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in ALLOWED_HOSTS:
        raise ValueError("仅允许 Bilibili 视频链接")
    if parsed.scheme != "https":
        raise ValueError("视频链接必须使用 HTTPS")
    if not PAGE_URL_POLICY.allows(parsed.geturl()):
        raise ValueError("视频链接不能包含用户凭据或非标准端口")
    params = parse_qs(parsed.query)
    page_value = params.get("p", ["1"])[0]
    try:
        page_number = max(1, int(page_value))
    except ValueError:
        page_number = 1
    match = _VIDEO_ID.match(parsed.path)
    video_id = match.group(1) if match else ""
    if host == "player.bilibili.com" and parsed.path == "/player.html":
        bvid = params.get("bvid", [""])[0]
        aid = params.get("aid", [""])[0]
        if _BVID.fullmatch(bvid):
            video_id = bvid
        elif aid.isascii() and aid.isdigit():
            video_id = f"av{aid}"
        else:
            video_id = ""
    bvid = "BV" + video_id[2:] if video_id.lower().startswith("bv") else None
    aid = str(int(video_id[2:])) if video_id.lower().startswith("av") else None
    return BilibiliURL(bvid=bvid, page_number=page_number, is_short=host in {"b23.tv", "www.b23.tv"}, aid=aid)
