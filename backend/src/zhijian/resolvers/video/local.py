from __future__ import annotations

from pathlib import Path

from .bilibili import ResolvedVideo, SubtitleTrack, VideoResolveError


class LocalVideoAdapter:
    """Normalize an uploaded local video without inventing a public source URL."""

    platform = "LOCAL"
    allowed_suffixes = {".mp4", ".mov", ".webm", ".m4v"}

    def resolve(self, raw_url: str, cookie: str | None = None) -> ResolvedVideo:
        del cookie
        path = Path(raw_url).resolve()
        if path.suffix.lower() not in self.allowed_suffixes or not path.is_file():
            raise VideoResolveError("VIDEO_LOCAL_UNAVAILABLE", "本地视频文件不存在或格式不受支持")
        return ResolvedVideo(
            canonical_url=path.as_uri(),
            bvid="",
            aid=None,
            cid="",
            page_number=1,
            title=path.stem,
            uploader="本地文件",
            duration_ms=None,
            cover_url=None,
            subtitles=[],
            metadata={"local_path": str(path), "filename": path.name},
        )

    def fetch_subtitle_segments(self, track: SubtitleTrack) -> list[dict]:
        del track
        raise VideoResolveError("VIDEO_SUBTITLE_UNAVAILABLE", "本地视频没有平台字幕")

    def build_timestamp_url(self, canonical_url: str, timestamp_ms: int) -> str:
        del canonical_url, timestamp_ms
        return ""
