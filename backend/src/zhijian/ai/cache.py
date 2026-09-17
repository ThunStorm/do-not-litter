import json
from collections.abc import Callable
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.reliability import AIProviderError
from zhijian.db.models import AICacheEntry, ExternalCallAudit, Job
from zhijian.providers.llm import LLMResult

CACHE_SCHEMA_VERSION = "v2"
CACHE_PARSER_VERSION = "structured-json-v2"
LEGACY_CACHE_SCHEMA_VERSION = "v1"
LEGACY_CACHE_PARSER_VERSION = "v1"


def cache_key(
    *,
    stage: str,
    capability: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    semantic_options: dict[str, Any],
) -> str:
    return _cache_key(
        stage=stage,
        capability=capability,
        provider=provider,
        model=model,
        messages=messages,
        semantic_options=semantic_options,
        schema_version=CACHE_SCHEMA_VERSION,
        parser_version=CACHE_PARSER_VERSION,
    )


def legacy_cache_key(
    *,
    stage: str,
    capability: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    semantic_options: dict[str, Any],
) -> str:
    return _cache_key(
        stage=stage,
        capability=capability,
        provider=provider,
        model=model,
        messages=messages,
        semantic_options=semantic_options,
        schema_version=LEGACY_CACHE_SCHEMA_VERSION,
        parser_version=LEGACY_CACHE_PARSER_VERSION,
    )


def _cache_key(
    *,
    stage: str,
    capability: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    semantic_options: dict[str, Any],
    schema_version: str,
    parser_version: str,
) -> str:
    payload = {
        "stage": stage,
        "capability": capability,
        "provider": provider,
        "model": model,
        "messages": messages,
        "semantic_options": semantic_options,
        "schema_version": schema_version,
        "parser_version": parser_version,
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
    validate: Callable[[LLMResult], None] | None = None,
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
    if previous is None:
        legacy_key = legacy_cache_key(
            stage=stage,
            capability=capability,
            provider=provider,
            model=model,
            messages=messages,
            semantic_options=semantic_options,
        )
        previous = db.scalar(
            select(AICacheEntry)
            .where(AICacheEntry.cache_key == legacy_key)
            .order_by(AICacheEntry.created_at.desc())
        )
    invalid_previous = False
    if cache_enabled and not force_regenerate and previous:
        data = previous.result_json
        cached = LLMResult(
            content=str(data["content"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            usage=dict(data.get("usage") or {}),
            metadata=dict(data.get("metadata") or {}),
        )
        try:
            if validate:
                validate(cached)
        except AIProviderError as exc:
            invalid_previous = True
            _record_invalid_cache(db, job, stage, capability, previous, location, exc)
        else:
            _record_cache_hit(db, job, stage, capability, previous, location)
            return cached
    result = call()
    if validate:
        validate(result)
    usage = dict(getattr(result, "usage", {}) or {})
    metadata = {
        key: value
        for key, value in dict(getattr(result, "metadata", {}) or {}).items()
        if key in {"finish_reason", "content_length", "response_id"}
    }
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
                    "metadata": metadata,
                },
                previous_entry_id=(
                    previous.id if previous and (force_regenerate or invalid_previous) else None
                ),
            )
        )
        db.commit()
    return LLMResult(str(result.content), str(result.provider), str(result.model), usage, metadata)


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
                "cache_entry_id": entry.id,
            },
            response_meta_json={
                "prompt_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count")),
                "completion_tokens": usage.get("completion_tokens", usage.get("eval_count")),
                "cached_tokens": usage.get("cached_tokens", usage.get("prompt_tokens", 0)),
                "content_length": len(str(entry.result_json.get("content") or "")),
            },
        )
    )
    db.commit()


def _record_invalid_cache(
    db: Session,
    job: Job | None,
    stage: str,
    capability: str,
    entry: AICacheEntry,
    location: str | None,
    error: AIProviderError,
) -> None:
    db.add(
        ExternalCallAudit(
            job_id=job.id if job else None,
            capability=capability,
            provider=entry.provider,
            operation=stage,
            status="SKIPPED",
            duration_ms=0,
            request_meta_json={
                "stage": stage,
                "model": entry.model,
                "location": location or ("LOCAL" if entry.provider.lower() == "ollama" else "REMOTE"),
                "cache_hit": True,
                "cache_invalid": True,
                "cache_entry_id": entry.id,
            },
            response_meta_json={
                "content_length": len(str(entry.result_json.get("content") or "")),
                "parser_version": CACHE_PARSER_VERSION,
            },
            error_code="AI_CACHE_INVALID",
            error_message=f"{error.code}: {str(error)[:420]}",
        )
    )
    db.commit()
