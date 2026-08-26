from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.db.models import Setting
from zhijian.providers.runtime import runtime_metrics

METRICS_SAMPLE_KEY = "runtime:metrics-sample"
STALE_AFTER_SECONDS = 75


def persist_runtime_metrics_sample(db: Session, settings: Settings) -> dict[str, Any]:
    """Persist one host sample so LAN clients read the same server-side data."""
    heartbeat = db.get(Setting, "runtime:worker-heartbeat")
    heartbeat_at = heartbeat.updated_at if heartbeat else None
    metrics = runtime_metrics(settings.data_dir, heartbeat_at)
    value = _json_value(metrics)
    setting = db.get(Setting, METRICS_SAMPLE_KEY)
    if setting is None:
        setting = Setting(key=METRICS_SAMPLE_KEY, value_json=value)
        db.add(setting)
    else:
        setting.value_json = value
    db.commit()
    return value


def read_runtime_metrics_sample(db: Session, now: datetime | None = None) -> dict[str, Any]:
    """Read a persisted sample without executing host probes in the request path."""
    setting = db.get(Setting, METRICS_SAMPLE_KEY)
    value = dict(setting.value_json) if setting and isinstance(setting.value_json, dict) else {}
    sampled_at = _parse_datetime(value.get("sampled_at"))
    now = now or datetime.now(UTC)
    freshness = "PENDING"
    if sampled_at:
        freshness = "FRESH" if (now - sampled_at).total_seconds() <= STALE_AFTER_SECONDS else "STALE"
    worker = dict(value.get("worker") or {})
    heartbeat_at = _parse_datetime(worker.get("heartbeat_at"))
    worker["heartbeat_age_seconds"] = (
        round((now - heartbeat_at).total_seconds(), 1) if heartbeat_at else None
    )
    return {
        "sampled_at": value.get("sampled_at"),
        "freshness": freshness,
        "cpu": _metric(value.get("cpu")),
        "memory": _metric(value.get("memory")),
        "disk": _metric(value.get("disk")),
        "worker": worker,
    }


def _metric(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {
        "percent": None,
        "unavailable_reason": "等待首个采样",
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
