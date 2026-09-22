from __future__ import annotations

from hashlib import sha256

from sqlalchemy.orm import Session

from zhijian.db.models import Setting


def _key(stage: str, model: str) -> str:
    digest = sha256(model.encode()).hexdigest()[:20]
    return f"ai-runtime-hint:{stage.upper()}:{digest}"


def read_runtime_hint(db: Session, stage: str, model: str) -> dict[str, int]:
    if not hasattr(db, "get"):
        return {}
    saved = db.get(Setting, _key(stage, model))
    value = saved.value_json if saved and isinstance(saved.value_json, dict) else {}
    if value.get("model") != model:
        return {}
    return {
        key: int(value[key])
        for key in ("safe_max_chars", "safe_max_segments")
        if int(value.get(key) or 0) > 0
    }


def tighten_runtime_hint(
    db: Session,
    stage: str,
    model: str,
    *,
    safe_max_chars: int,
    safe_max_segments: int,
) -> dict[str, int]:
    current = read_runtime_hint(db, stage, model)
    value = {
        "safe_max_chars": min(current.get("safe_max_chars", safe_max_chars), safe_max_chars),
        "safe_max_segments": min(
            current.get("safe_max_segments", safe_max_segments), safe_max_segments
        ),
    }
    key = _key(stage, model)
    saved = db.get(Setting, key)
    payload = {"model": model, **value}
    if saved is None:
        db.add(Setting(key=key, value_json=payload))
    else:
        saved.value_json = payload
    db.commit()
    return value
