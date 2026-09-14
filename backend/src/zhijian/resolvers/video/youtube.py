from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from zhijian.core.url_policy import HttpsHostPolicy

from .bilibili import ResolvedVideo, SubtitleTrack, VideoResolveError

YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
PAGE_POLICY = HttpsHostPolicy(exact_hosts=YOUTUBE_HOSTS)
SUBTITLE_POLICY = HttpsHostPolicy(
    exact_hosts=YOUTUBE_HOSTS,
    host_suffixes=frozenset({"googlevideo.com", "youtube.com"}),
)
_VTT_TIMESTAMP = re.compile(
    r"(?P<start>(?:\d+:)?\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>(?:\d+:)?\d{2}:\d{2}\.\d{3})"
)


def is_youtube_url(url: str) -> bool:
    return PAGE_POLICY.allows(url)


class YouTubeAdapter:
    platform = "YOUTUBE"

    def __init__(self, *, timeout: int, proxy_url: str = "") -> None:
        self.timeout = timeout
        self.proxy_url = proxy_url

    def resolve(self, raw_url: str, cookie: str | None = None) -> ResolvedVideo:
        del cookie
        if not is_youtube_url(raw_url):
            raise VideoResolveError("VIDEO_UNSUPPORTED_URL", "仅允许公开 YouTube 视频链接")
        try:
            import yt_dlp
        except ImportError as exc:
            raise VideoResolveError("VIDEO_METADATA_UNAVAILABLE", "yt-dlp 尚未安装") from exc
        options = {
            "skip_download": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": self.timeout,
        }
        if self.proxy_url:
            options["proxy"] = self.proxy_url
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(raw_url, download=False)
        except Exception as exc:
            message = str(exc)[:300]
            code = "VIDEO_UNAVAILABLE" if any(
                marker in message.lower()
                for marker in ("private", "unavailable", "sign in", "rate limit", "429")
            ) else "VIDEO_METADATA_FAILED"
            raise VideoResolveError(code, f"YouTube 元数据读取失败：{message}") from exc
        video_id = str(info.get("id") or "")
        if not video_id:
            raise VideoResolveError("VIDEO_METADATA_FAILED", "YouTube 未返回视频标识")
        return ResolvedVideo(
            canonical_url=f"https://www.youtube.com/watch?v={video_id}",
            bvid=video_id,
            aid=None,
            cid="",
            page_number=1,
            title=str(info.get("title") or "未命名视频"),
            uploader=str(info.get("uploader") or info.get("channel") or ""),
            duration_ms=int(float(info.get("duration") or 0) * 1000) or None,
            cover_url=str(info.get("thumbnail") or "") or None,
            subtitles=self._subtitle_tracks(info),
            metadata={"video_id": video_id, "webpage_url": str(info.get("webpage_url") or raw_url)},
        )

    def fetch_subtitle_segments(self, track: SubtitleTrack) -> list[dict]:
        if not SUBTITLE_POLICY.allows(track.url):
            raise VideoResolveError("VIDEO_HOST_BLOCKED", "YouTube 字幕地址不在许可范围")
        try:
            response = httpx.get(track.url, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VideoResolveError("VIDEO_SUBTITLE_UNAVAILABLE", "YouTube 字幕获取失败") from exc
        return _parse_vtt(response.text)

    def build_timestamp_url(self, canonical_url: str, timestamp_ms: int) -> str:
        parsed = urlparse(canonical_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params["t"] = [str(max(0, timestamp_ms // 1000))]
        return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    @staticmethod
    def _subtitle_tracks(info: dict) -> list[SubtitleTrack]:
        tracks: list[SubtitleTrack] = []
        sources = ((False, info.get("subtitles") or {}), (True, info.get("automatic_captions") or {}))
        for generated, source in sources:
            for language, entries in source.items():
                if not isinstance(entries, list):
                    continue
                item = next(
                    (
                        value
                        for value in entries
                        if isinstance(value, dict)
                        and value.get("url")
                        and value.get("ext") in {"vtt", "srv3"}
                    ),
                    None,
                )
                if not isinstance(item, dict):
                    continue
                tracks.append(
                    SubtitleTrack(
                        url=str(item["url"]),
                        language=str(language),
                        language_doc=str(language),
                        track_id=f"{language}:{'auto' if generated else 'manual'}",
                        is_generated=generated,
                        endpoint="yt-dlp",
                        platform="YOUTUBE",
                    )
                )
        return sorted(tracks, key=lambda item: (item.generated, item.language))


def _parse_vtt(value: str) -> list[dict]:
    rows: list[dict] = []
    current: dict | None = None
    for line in value.splitlines():
        match = _VTT_TIMESTAMP.search(line)
        if match:
            if current and current["text"]:
                rows.append(current)
            current = {
                "text": "",
                "start_ms": _timestamp_ms(match.group("start")),
                "end_ms": _timestamp_ms(match.group("end")),
                "confidence": None,
            }
        elif current and line.strip() and not line.startswith("WEBVTT"):
            current["text"] = f"{current['text']} {re.sub(r'<[^>]+>', '', line).strip()}".strip()
    if current and current["text"]:
        rows.append(current)
    if not rows:
        raise VideoResolveError("VIDEO_SUBTITLE_INVALID", "YouTube 字幕格式不受支持或为空")
    return rows


def _timestamp_ms(value: str) -> int:
    parts = value.split(":")
    seconds = float(parts[-1]) + int(parts[-2]) * 60 + (int(parts[-3]) * 3600 if len(parts) == 3 else 0)
    return int(seconds * 1000)
