from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

from zhijian.core.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).astimezone().isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "event_type",
            "duration_ms",
            "status_code",
            "error_code",
            "path",
            "job_id",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings, service: str) -> None:
    root = logging.getLogger()
    if any(getattr(handler, "_zhijian", False) for handler in root.handlers):
        return
    root.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        settings.data_dir / "logs" / f"{service}.jsonl",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    handler._zhijian = True  # type: ignore[attr-defined]
    root.addHandler(handler)
