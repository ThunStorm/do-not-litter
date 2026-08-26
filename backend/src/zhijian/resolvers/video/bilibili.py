from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from .url_parser import parse_bilibili_url

ALLOWED_HOSTS = {"www.bilibili.com", "m.bilibili.com", "bilibili.com", "b23.tv", "www.b23.tv"}
API_HOSTS = {"api.bilibili.com"}


class VideoResolveError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(slots=True)
class SubtitleTrack:
    url: str
    language: str
    language_doc: str
    source: str = "BILIBILI_PLAYER"


@dataclass(slots=True)
class ResolvedVideo:
    canonical_url: str
    bvid: str
    aid: str | None
    cid: str
    page_number: int
    title: str
    uploader: str
    duration_ms: int | None
    cover_url: str | None
    subtitles: list[SubtitleTrack] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def is_bilibili_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and (parsed.hostname or "").lower() in ALLOWED_HOSTS
    except ValueError:
        return False


class BilibiliResolver:
    """Bounded resolver: only Bilibili/API HTTPS endpoints, no arbitrary redirects."""

    def __init__(self, *, timeout: int = 45, max_redirects: int = 3, proxy_url: str = "") -> None:
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.proxy_url = proxy_url or None

    def resolve(self, raw_url: str, cookie: str | None = None) -> ResolvedVideo:
        candidate = self._resolve_short_url(raw_url)
        parsed = parse_bilibili_url(candidate)
        if not parsed.bvid:
            raise VideoResolveError("VIDEO_UNSUPPORTED_URL", "未识别到 BV 号，请粘贴常规 Bilibili 视频链接")
        headers = {"User-Agent": "Mozilla/5.0 (Zhijian local video note)"}
        if cookie:
            headers["Cookie"] = cookie
        data = self._get_json(
            "https://api.bilibili.com/x/web-interface/view?" + urlencode({"bvid": parsed.bvid}), headers
        )
        if data.get("code") != 0 or not data.get("data"):
            raise VideoResolveError("VIDEO_METADATA_FAILED", str(data.get("message") or "无法读取视频元数据"))
        video = data["data"]
        pages = video.get("pages") or []
        if parsed.page_number > len(pages):
            raise VideoResolveError("VIDEO_PAGE_NOT_FOUND", "视频分 P 不存在")
        page = pages[parsed.page_number - 1]
        cid = str(page.get("cid") or "")
        if not cid:
            raise VideoResolveError("VIDEO_METADATA_FAILED", "视频未提供可处理的分 P")
        canonical = f"https://www.bilibili.com/video/{video.get('bvid') or parsed.bvid}"
        if parsed.page_number > 1:
            canonical += f"?p={parsed.page_number}"
        subtitles = self._fetch_subtitles(video.get("bvid") or parsed.bvid, cid, headers)
        return ResolvedVideo(
            canonical_url=canonical,
            bvid=str(video.get("bvid") or parsed.bvid),
            aid=str(video.get("aid")) if video.get("aid") else None,
            cid=cid,
            page_number=parsed.page_number,
            title=str(page.get("part") or video.get("title") or "未命名视频"),
            uploader=str((video.get("owner") or {}).get("name") or ""),
            duration_ms=int(float(page.get("duration") or video.get("duration") or 0) * 1000) or None,
            cover_url=_https_url(video.get("pic")),
            subtitles=subtitles,
            metadata={
                "pubdate": video.get("pubdate"),
                "desc": video.get("desc", "")[:2000],
                "pages": len(pages),
            },
        )

    def fetch_subtitle_segments(self, track: SubtitleTrack) -> list[dict[str, Any]]:
        data = self._get_json(track.url, {"User-Agent": "Mozilla/5.0 (Zhijian local video note)"})
        body = data.get("body") if isinstance(data, dict) else None
        if not isinstance(body, list):
            raise VideoResolveError("VIDEO_SUBTITLE_INVALID", "字幕文件格式不受支持")
        result = []
        for item in body:
            text = str(item.get("content") or "").strip()
            if not text:
                continue
            result.append(
                {
                    "text": text,
                    "start_ms": int(float(item.get("from") or 0) * 1000),
                    "end_ms": int(float(item.get("to") or item.get("from") or 0) * 1000),
                    "confidence": None,
                }
            )
        if not result:
            raise VideoResolveError("VIDEO_SUBTITLE_EMPTY", "视频字幕为空")
        return result

    def _resolve_short_url(self, raw_url: str) -> str:
        parsed = parse_bilibili_url(raw_url)
        if not parsed.is_short:
            return raw_url
        current = raw_url
        with httpx.Client(timeout=self.timeout, follow_redirects=False, proxy=self.proxy_url) as client:
            for _ in range(self.max_redirects):
                response = client.get(current, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code not in {301, 302, 303, 307, 308}:
                    break
                target = urljoin(current, response.headers.get("location", ""))
                target_host = (urlparse(target).hostname or "").lower()
                if urlparse(target).scheme != "https" or target_host not in ALLOWED_HOSTS:
                    raise VideoResolveError("VIDEO_REDIRECT_BLOCKED", "短链跳转目标不在 Bilibili 许可范围")
                current = target
            else:
                raise VideoResolveError("VIDEO_TOO_MANY_REDIRECTS", "短链重定向次数超出限制")
        return current

    def _get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        host = (urlparse(url).hostname or "").lower()
        if urlparse(url).scheme != "https" or host not in (ALLOWED_HOSTS | API_HOSTS):
            raise VideoResolveError("VIDEO_HOST_BLOCKED", "外部访问目标不在许可范围")
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise VideoResolveError("VIDEO_SSRF_BLOCKED", "禁止访问本地或私有地址")
        except ValueError:
            pass
        with httpx.Client(timeout=self.timeout, follow_redirects=False, proxy=self.proxy_url) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _fetch_subtitles(self, bvid: str, cid: str, headers: dict[str, str]) -> list[SubtitleTrack]:
        try:
            data = self._get_json(
                "https://api.bilibili.com/x/player/v2?" + urlencode({"bvid": bvid, "cid": cid}), headers
            )
        except (httpx.HTTPError, VideoResolveError):
            return []
        subtitles = ((data.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
        tracks: list[SubtitleTrack] = []
        for item in subtitles:
            url = str(item.get("subtitle_url") or "")
            if url.startswith("//"):
                url = "https:" + url
            if not url.startswith("https://"):
                continue
            tracks.append(SubtitleTrack(url, str(item.get("lan") or ""), str(item.get("lan_doc") or "")))
        return sorted(
            tracks, key=lambda track: (0 if track.language.lower().startswith("zh") else 1, track.language)
        )


def _https_url(value: object) -> str | None:
    url = str(value or "")
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://"):
        return "https://" + url.removeprefix("http://")
    return url or None
