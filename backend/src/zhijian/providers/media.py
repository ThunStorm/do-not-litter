from __future__ import annotations

from pathlib import Path
from typing import Any


class MediaDownloadError(RuntimeError):
    def __init__(self, message: str, *, code: str = "VIDEO_MEDIA_UNAVAILABLE") -> None:
        self.code = code
        super().__init__(message)


class YtDlpMediaProvider:
    """Bounded temporary media adapter. Its caller has already validated the Bilibili URL."""

    def __init__(self, cache_dir: Path, *, max_bytes: int, timeout: int, proxy_url: str = "") -> None:
        self.cache_dir = cache_dir
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.proxy_url = proxy_url

    def download_audio(self, url: str, cookie_file: Path | None = None) -> Path:
        return self._download(url, cookie_file, "bestaudio/best")

    def download_video(self, url: str, cookie_file: Path | None = None) -> Path:
        # Bilibili DASH normally exposes video-only MP4 plus audio-only M4A.
        # Do not demand a combined stream or treat a portrait frame's height
        # as its quality cap; yt-dlp's res sort chooses the nearest 720p
        # candidate and falls back to the smallest usable video stream.
        return self._download(url, cookie_file, "bv*[ext=mp4]/bv*/best", video_only=True)

    def _download(
        self, url: str, cookie_file: Path | None, video_format: str, *, video_only: bool = False
    ) -> Path:
        try:
            import yt_dlp
        except ImportError as exc:
            raise MediaDownloadError("yt-dlp 尚未安装") from exc
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        template = str(self.cache_dir / "%(id)s.%(ext)s")
        options: dict[str, Any] = {
            "format": video_format,
            "outtmpl": template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "socket_timeout": self.timeout,
            "max_filesize": self.max_bytes,
            "overwrites": False,
            "restrictfilenames": True,
            "http_headers": {"Referer": "https://www.bilibili.com"},
        }
        if video_only:
            options["format_sort"] = ["res:720"]
        if self.proxy_url:
            options["proxy"] = self.proxy_url
        if cookie_file:
            options["cookiefile"] = str(cookie_file)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                requested = info.get("requested_downloads") or []
                path = Path(requested[0].get("filepath")) if requested else Path(ydl.prepare_filename(info))
        except Exception as exc:
            message = str(exc)[:300]
            login_markers = (
                "http error 401",
                "http error 403",
                "http error 412",
                "login required",
                "sign in",
                "cookies are needed",
                "fresh cookies",
            )
            code = (
                "VIDEO_LOGIN_REQUIRED"
                if any(marker in message.lower() for marker in login_markers)
                else "VIDEO_MEDIA_UNAVAILABLE"
            )
            raise MediaDownloadError(f"媒体提取失败：{message}", code=code) from exc
        if not path.is_file() or path.stat().st_size > self.max_bytes:
            path.unlink(missing_ok=True)
            raise MediaDownloadError("媒体文件不存在或超过安全大小限制")
        return path
