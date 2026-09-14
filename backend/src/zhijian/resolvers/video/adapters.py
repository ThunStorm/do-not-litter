"""Small registry for platform-specific video ingress adapters.

Everything after the adapter returns a normalized descriptor remains the
existing Transcript/Evidence/Note/Place pipeline.
"""
from __future__ import annotations

from typing import Protocol

from zhijian.resolvers.video.bilibili import BilibiliResolver, ResolvedVideo, SubtitleTrack
from zhijian.resolvers.video.local import LocalVideoAdapter
from zhijian.resolvers.video.youtube import YouTubeAdapter


class VideoSourceAdapter(Protocol):
    platform: str

    def resolve(self, raw_url: str, cookie: str | None = None) -> ResolvedVideo: ...

    def fetch_subtitle_segments(self, track: SubtitleTrack) -> list[dict]: ...

    def build_timestamp_url(self, canonical_url: str, timestamp_ms: int) -> str: ...


def video_adapter_for_platform(
    platform: str, *, timeout: int, max_redirects: int, proxy_url: str
) -> VideoSourceAdapter:
    if platform == "BILIBILI":
        return BilibiliResolver(timeout=timeout, max_redirects=max_redirects, proxy_url=proxy_url)
    if platform == "LOCAL":
        return LocalVideoAdapter()
    if platform == "YOUTUBE":
        return YouTubeAdapter(timeout=timeout, proxy_url=proxy_url)
    raise ValueError(f"不支持的视频平台：{platform}")
