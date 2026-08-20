from __future__ import annotations

from pathlib import Path


class MediaDownloadError(RuntimeError):
    pass


class YtDlpMediaProvider:
    """Temporary audio-only adapter. Its caller has already passed Bilibili URL validation."""

    def __init__(self, cache_dir: Path, *, max_bytes: int, timeout: int, proxy_url: str = "") -> None:
        self.cache_dir = cache_dir
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.proxy_url = proxy_url

    def download_audio(self, url: str, cookie_file: Path | None = None) -> Path:
        try:
            import yt_dlp
        except ImportError as exc:
            raise MediaDownloadError("yt-dlp 尚未安装") from exc
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        template = str(self.cache_dir / "%(id)s.%(ext)s")
        options = {
            "format": "bestaudio/best",
            "outtmpl": template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "socket_timeout": self.timeout,
            "max_filesize": self.max_bytes,
            "overwrites": False,
            "restrictfilenames": True,
        }
        if self.proxy_url:
            options["proxy"] = self.proxy_url
        if cookie_file:
            options["cookiefile"] = str(cookie_file)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                path = Path(ydl.prepare_filename(info))
        except Exception as exc:
            raise MediaDownloadError(f"媒体提取失败：{str(exc)[:300]}") from exc
        if not path.is_file() or path.stat().st_size > self.max_bytes:
            path.unlink(missing_ok=True)
            raise MediaDownloadError("音频文件不存在或超过安全大小限制")
        return path
