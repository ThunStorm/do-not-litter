"""Immutable, secret-free AI settings captured when a Job is submitted."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.db.models import Job, Setting

SNAPSHOT_KEY = "ai_submission_config"
_SETTING_KEYS = {"model-routing", "app:general", "prompt:supplements", "transcript-processing"}
_SETTING_PREFIXES = ("model-profile:", "ai-stage-policy:", "ai-domain-pack:")
_SECRET_FIELDS = {"api_key", "secret", "token", "password", "cookie", "authorization"}
ASR_DEFAULT_KEY = "asr:default"
ASR_PROVIDERS = {"WHISPER_CPP", "QWEN3_ASR"}


def default_asr_provider(db: Session, settings: Settings) -> str:
    row = db.get(Setting, ASR_DEFAULT_KEY)
    provider = (row.value_json or {}).get("provider") if row else None
    return provider if provider in ASR_PROVIDERS else settings.default_asr_provider


def capture_ai_config(db: Session, settings: Settings) -> dict[str, Any]:
    rows = db.scalars(
        select(Setting).where(
            or_(
                Setting.key.in_(_SETTING_KEYS),
                *(Setting.key.like(f"{prefix}%") for prefix in _SETTING_PREFIXES),
            )
        )
    ).all()
    values: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row.value_json, dict):
            continue
        value = deepcopy(row.value_json)
        if row.key.startswith("model-profile:"):
            value = {key: item for key, item in value.items() if key.lower() not in _SECRET_FIELDS}
        values[row.key] = value
    return {
        "version": 1,
        "settings": values,
        "default_asr_provider": default_asr_provider(db, settings),
        "video_note_chunk_chars": settings.video_note_chunk_chars,
    }


def job_setting(db: Session, key: str, job: Job | None = None) -> dict[str, Any]:
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY) if job else None
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        values = snapshot.get("settings")
        value = values.get(key) if isinstance(values, dict) else None
    else:
        row = db.get(Setting, key)
        value = row.value_json if row else None
    return deepcopy(value) if isinstance(value, dict) else {}


def job_video_note_chunk_chars(job: Job | None, default: int) -> int:
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY) if job else None
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        return int(snapshot.get("video_note_chunk_chars") or default)
    return default


def job_asr_provider(job: Job, settings: Settings) -> str:
    provider = (job.payload_json or {}).get("asr_provider")
    if provider in ASR_PROVIDERS:
        return provider
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY)
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        provider = snapshot.get("default_asr_provider")
        if provider in ASR_PROVIDERS:
            return provider
    return settings.default_asr_provider
