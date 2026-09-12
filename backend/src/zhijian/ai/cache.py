import json
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.db.models import AICacheEntry, ExternalCallAudit, Job
from zhijian.providers.llm import LLMResult


def cache_key(
    *,
    stage: str,
    capability: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    semantic_options: dict[str, Any],
) -> str:
    payload = {
        "stage": stage,
        "capability": capability,
        "provider": provider,
        "model": model,
        "messages": messages,
        "semantic_options": semantic_options,
        "schema_version": "v1",
        "parser_version": "v1",
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def cached_json_result(
    db: Session,
    *,
    job: Job | None,
    stage: str,
    capability: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    semantic_options: dict[str, Any],
    location: str | None = None,
    cache_enabled: bool,
    force_regenerate: bool,
    call: Any,
) -> LLMResult:
    key = cache_key(
        stage=stage,
        capability=capability,
        provider=provider,
        model=model,
        messages=messages,
        semantic_options=semantic_options,
    )
    previous = db.scalar(
        select(AICacheEntry).where(AICacheEntry.cache_key == key).order_by(AICacheEntry.created_at.desc())
    )
    if cache_enabled and not force_regenerate and previous:
        data = previous.result_json
        _record_cache_hit(db, job, stage, capability, previous, location)
        return LLMResult(
            content=str(data["content"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            usage=dict(data.get("usage") or {}),
        )
    result = call()
    usage = dict(getattr(result, "usage", {}) or {})
    if cache_enabled:
        db.add(
            AICacheEntry(
                cache_key=key,
                stage=stage,
                capability=capability,
                provider=str(result.provider),
                model=str(result.model),
                result_json={
                    "content": str(result.content),
                    "provider": str(result.provider),
                    "model": str(result.model),
                    "usage": usage,
                },
                previous_entry_id=previous.id if previous and force_regenerate else None,
            )
        )
        db.commit()
    return LLMResult(str(result.content), str(result.provider), str(result.model), usage)


def _record_cache_hit(
    db: Session, job: Job | None, stage: str, capability: str, entry: AICacheEntry, location: str | None
) -> None:
    usage = entry.result_json.get("usage") or {}
    db.add(
        ExternalCallAudit(
            job_id=job.id if job else None,
            capability=capability,
            provider=entry.provider,
            operation=stage,
            status="COMPLETED",
            duration_ms=0,
            request_meta_json={
                "stage": stage,
                "model": entry.model,
                "location": location or ("LOCAL" if entry.provider.lower() == "ollama" else "REMOTE"),
                "cache_hit": True,
            },
            response_meta_json={
                "prompt_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count")),
                "completion_tokens": usage.get("completion_tokens", usage.get("eval_count")),
                "cached_tokens": usage.get("cached_tokens", usage.get("prompt_tokens", 0)),
            },
        )
    )
    db.commit()
