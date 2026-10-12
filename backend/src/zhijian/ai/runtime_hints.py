from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from hashlib import sha256

from sqlalchemy.orm import Session

from zhijian.db.models import Setting


def runtime_hint_scope(provider, model: str) -> str:
    """Opaque identity of the actual entry, account and effective call parameters."""
    targets = []
    for route in ("primary", "fallback") if hasattr(provider, "primary") else ("direct",):
        client = getattr(provider, route, None) if route != "direct" else provider
        if client is None:
            continue
        option_field = "fallback_request_options" if route == "fallback" else "request_options"
        options = getattr(provider, option_field, None)
        reliability = getattr(provider, f"{route}_reliability", None)
        targets.append(
            {
                "route": route,
                "provider": str(getattr(client, "name", "")),
                "profile_id": getattr(client, "profile_id", None),
                "base_url": str(getattr(client, "base_url", "")).rstrip("/"),
                "model": getattr(provider, f"{route}_model", model) or model,
                "connection_type": getattr(client, "connection_type", "DIRECT"),
                "request_contract_version": getattr(client, "request_contract_version", None),
                "json_mode": getattr(client, "supports_json_mode", None),
                "interface": getattr(client, "interface_capabilities", None).fingerprint()
                if getattr(client, "interface_capabilities", None) is not None
                else None,
                "credential_hash": sha256(str(getattr(client, "api_key", "")).encode()).hexdigest(),
                "timeout": float(client.timeout) if getattr(client, "timeout", None) is not None else None,
                "options": asdict(options) if is_dataclass(options) else {},
                "reliability": asdict(reliability) if is_dataclass(reliability) else {},
            }
        )
    return sha256(json.dumps(targets, sort_keys=True, default=str).encode()).hexdigest()


def _key(stage: str, model: str, scope: str | None = None) -> str:
    identity = f"{model}:{scope}" if scope else model
    digest = sha256(identity.encode()).hexdigest()[: 32 if scope else 20]
    return f"ai-runtime-hint:{'v2:' if scope else ''}{stage.upper()}:{digest}"


def read_runtime_hint(db: Session, stage: str, model: str, *, scope: str | None = None) -> dict[str, int]:
    if not hasattr(db, "get"):
        return {}
    saved = db.get(Setting, _key(stage, model, scope))
    value = saved.value_json if saved and isinstance(saved.value_json, dict) else {}
    if value.get("model") != model or scope and value.get("scope") != scope:
        return {}
    return {
        key: int(value[key])
        for key in (
            "safe_max_chars",
            "safe_max_segments",
            "safe_max_input_tokens",
            "safe_max_facts",
            "safe_max_quotes",
            "safe_max_sections",
        )
        if int(value.get(key) or 0) > 0
    }


def tighten_runtime_hint(
    db: Session,
    stage: str,
    model: str,
    *,
    safe_max_chars: int,
    safe_max_segments: int,
    scope: str | None = None,
) -> dict[str, int]:
    current = read_runtime_hint(db, stage, model, scope=scope)
    value = {
        "safe_max_chars": min(current.get("safe_max_chars", safe_max_chars), safe_max_chars),
        "safe_max_segments": min(current.get("safe_max_segments", safe_max_segments), safe_max_segments),
    }
    key = _key(stage, model, scope)
    saved = db.get(Setting, key)
    payload = {"model": model, **({"scope": scope} if scope else {}), **value}
    if saved is None:
        db.add(Setting(key=key, value_json=payload))
    else:
        saved.value_json = payload
    db.commit()
    return value


def tighten_note_reduce_hint(
    db: Session,
    model: str,
    *,
    safe_max_input_tokens: int,
    safe_max_facts: int,
    scope: str | None = None,
) -> dict[str, int]:
    current = read_runtime_hint(db, "NOTE_REDUCE", model, scope=scope)
    value = {
        "safe_max_input_tokens": min(
            current.get("safe_max_input_tokens", safe_max_input_tokens), safe_max_input_tokens
        ),
        "safe_max_facts": min(current.get("safe_max_facts", safe_max_facts), safe_max_facts),
    }
    key = _key("NOTE_REDUCE", model, scope)
    saved = db.get(Setting, key)
    payload = {"model": model, **({"scope": scope} if scope else {}), **current, **value}
    if saved is None:
        db.add(Setting(key=key, value_json=payload))
    else:
        saved.value_json = payload
    db.commit()
    return value
