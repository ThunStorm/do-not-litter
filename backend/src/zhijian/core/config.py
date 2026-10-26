from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


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
    data_dir: Path = PROJECT_ROOT / "data"
    storage_config: Path = Path.home() / "Library/Application Support/Zhijian/storage.json"
    storage_generation: int = 0
    frontend_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    secret_store: str = "file"
    session_cookie_name: str = "zhijian_session"
    session_ttl_hours: int = 24 * 7
    allow_localhost_without_session: bool = True
    max_upload_mb: int = 100
    worker_poll_seconds: float = 1.0
    worker_lease_seconds: int = 90
    worker_heartbeat_seconds: int = 20
    worker_watchdog_seconds: int = 5
    attempt_timeout_grace_seconds: int = 5
    job_attempt_timeout_seconds: int = 900
    runtime_metrics_interval_seconds: int = 30
    auth_max_attempts: int = 5
    auth_window_seconds: int = 300
    auth_lockout_seconds: int = 600
    ollama_base_url: str = "http://127.0.0.1:11434"
    whisper_binary: str = "whisper-cli"
    whisper_model: Path = Path("./data/models/whisper/ggml-base.bin")
    default_asr_provider: Literal["WHISPER_CPP", "QWEN3_ASR"] = "WHISPER_CPP"
    qwen_asr_enabled: bool = True
    qwen_asr_python: Path = PROJECT_ROOT / "data/runtime/qwen-asr/venv/bin/python"
    qwen_asr_runner: Path = PROJECT_ROOT / "scripts/qwen_asr_runner.py"
    qwen_asr_model: Path = Path("/Volumes/D/Projects/ollama-models/ASR/Qwen3-ASR-0.6B")
    qwen_asr_aligner_model: Path = Path("/Volumes/D/Projects/ollama-models/ASR/Qwen3-ForcedAligner-0.6B")
    qwen_asr_timeout_seconds: int = 3600
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    mimo_base_url: str = ""
    amap_api_key: str = ""
    amap_max_concurrency: int = 2
    amap_cache_ttl_seconds: int = 24 * 60 * 60
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

    @model_validator(mode="after")
    def resolve_storage(self):
        from zhijian.core.storage import read_json, validate_root

        config = (
            read_json(self.storage_config)
            if self.is_production or "storage_config" in self.model_fields_set
            else {}
        )
        if config:
            root = validate_root(config)
            if self.is_production and "data_dir" in self.model_fields_set and self.data_dir.resolve() != root:
                raise ValueError("生产环境与启动存储配置冲突")
            if self.is_production or "data_dir" not in self.model_fields_set:
                self.data_dir = root
                self.storage_generation = config["generation"]
        self.data_dir = self.data_dir.expanduser().resolve()
        if config and self.data_dir == root:
            self.storage_generation = config["generation"]
        if "whisper_model" not in self.model_fields_set:
            self.whisper_model = self.data_dir / "models/whisper/ggml-base.bin"
        return self

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
        if self.is_production and not self.database_path.is_file():
            raise ValueError("生产数据库缺失；必须显式初始化，拒绝建空库")
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
