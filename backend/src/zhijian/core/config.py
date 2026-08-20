from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZHIJIAN_",
        extra="ignore",
    )

    app_name: str = "至简"
    app_env: str = Field(default="development", alias="ENV")
    host: str = "127.0.0.1"
    port: int = 8787
    data_dir: Path = Path("./data")
    frontend_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    secret_store: str = "file"
    session_cookie_name: str = "zhijian_session"
    session_ttl_hours: int = 24 * 7
    allow_localhost_without_session: bool = True
    max_upload_mb: int = 100
    worker_poll_seconds: float = 1.0
    worker_lease_seconds: int = 90
    worker_heartbeat_seconds: int = 20
    auth_max_attempts: int = 5
    auth_window_seconds: int = 300
    auth_lockout_seconds: int = 600
    ollama_base_url: str = "http://127.0.0.1:11434"
    whisper_binary: str = "whisper-cli"
    whisper_model: Path = Path("./data/models/whisper/ggml-base.bin")
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    mimo_base_url: str = ""
    amap_api_key: str = ""
    video_media_downloader: str = "yt-dlp"
    video_max_duration_seconds: int = 2 * 60 * 60
    video_max_media_mb: int = 800
    video_cache_ttl_hours: int = 24
    video_network_timeout_seconds: int = 45
    video_max_redirects: int = 3
    video_proxy_url: str = ""
    video_cookie_secret_key: str = "video-bilibili-cookie"
    video_note_chunk_chars: int = 12_000
    video_note_model: str = ""
    travel_extraction_model: str = ""
    place_note_model: str = ""

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def permanent_dir(self) -> Path:
        return self.data_dir / "permanent"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.permanent_dir / "sources",
            self.permanent_dir / "snapshots",
            self.permanent_dir / "evidence",
            self.permanent_dir / "exports",
            self.data_dir / "browser" / "profile",
            self.data_dir / "models",
            self.data_dir / "models" / "whisper",
            self.cache_dir / "video",
            self.cache_dir / "audio",
            self.cache_dir / "frames",
            self.cache_dir / "temp",
            self.data_dir / "logs",
            self.data_dir / "secrets",
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
