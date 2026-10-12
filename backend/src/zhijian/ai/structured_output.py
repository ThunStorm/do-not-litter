"""Safe structured-output normalization shared by model stages."""

from __future__ import annotations

import json
import re
from typing import Any

from zhijian.ai.reliability import AIProviderError


def parse_json_with_quality(content: str) -> tuple[dict[str, Any], str, list[str]]:
    original = str(content or "")
    text = original.removeprefix("\ufeff").strip()
    if not text:
        raise AIProviderError("AI_PROVIDER_EMPTY_RESPONSE", "模型没有返回内容", retryable=True)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0:
        try:
            if isinstance(json.loads(text), list):
                raise AIProviderError(
                    "AI_PROVIDER_SCHEMA_INVALID", "模型返回的 JSON 顶层必须是对象", retryable=True
                )
        except json.JSONDecodeError:
            pass
        raise AIProviderError("AI_PROVIDER_INVALID_JSON", "模型没有返回 JSON 对象", retryable=True)
    if end < start:
        raise AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "模型返回的 JSON 被截断")
    # Repair only commas outside quoted strings; never rewrite evidence text.
    candidate = text[start : end + 1]
    rules: list[str] = ["outer_commentary"] if start != 0 or end != len(text) - 1 else []
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        repaired = re.sub(r'("(?:[^"\\]|\\.)*")|,\s*(?=[}\]])', lambda match: match[1] or "", candidate)
        if repaired != candidate:
            rules.append("trailing_comma")
        try:
            value = json.loads(repaired)
        except json.JSONDecodeError:
            try:
                value, consumed = json.JSONDecoder().raw_decode(repaired)
                suffix = repaired[consumed:].strip()
                if not isinstance(value, dict) or not 1 <= len(suffix) <= 2 or set(suffix) - {"}", "]"}:
                    raise ValueError("suffix is not an extra closing delimiter")
            except (json.JSONDecodeError, ValueError) as repair_exc:
                raise AIProviderError(
                    "AI_PROVIDER_INVALID_JSON", "模型返回的 JSON 无法解析", retryable=True, cause=exc
                ) from repair_exc
            rules.append("extra_closing_delimiters")
    if not isinstance(value, dict):
        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "模型返回的 JSON 顶层必须是对象", retryable=True)
    quality = (
        "DETERMINISTIC_REPAIRED" if rules else "NORMALIZED_VALID" if text != original else "DIRECT_VALID"
    )
    return value, quality, rules


def parse_json_object(content: str) -> dict[str, Any]:
    return parse_json_with_quality(content)[0]


_REQUIRED_FIELDS = {
    "GROUND_MAP": ("section_facts", "places", "warnings"),
    "EXTRACT_TRAVEL_FACTS": ("places",),
    "GENERATE_AI_NOTE": ("overview", "warnings", "sections", "section_facts"),
    "NOTE_REDUCE": ("sections",),
}

_LIST_LIMITS = {
    "GROUND_MAP": {"section_facts": 200, "places": 100, "warnings": 40},
    "GENERATE_AI_NOTE": {"sections": 40, "section_facts": 200, "warnings": 40},
    "NOTE_REDUCE": {"sections": 40, "warnings": 40},
}


def stage_json_schema(stage: str) -> dict | None:
    fields = (
        ("content_units", "entities", "relations", "claims", "warnings")
        if stage == "GROUND_MAP"
        else _REQUIRED_FIELDS.get(stage)
    )
    if stage == "TRANSCRIPT_CORRECTION":
        fields = ("changes",)
    if not fields:
        return None
    return {
        "type": "object",
        "required": list(fields),
        "properties": {
            field: {"type": "array", "items": {"type": "string" if field == "warnings" else "object"}}
            if field not in {"overview"}
            else {"type": "string"}
            for field in fields
        },
    }


def validate_structured_output(content: str, stage: str, metadata: dict[str, Any] | None = None) -> None:
    if str((metadata or {}).get("finish_reason") or "").lower() in {"length", "max_tokens"}:
        raise AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "模型输出达到长度上限")
    value, quality, rules = parse_json_with_quality(content)
    if metadata is not None:
        metadata.setdefault("parse_quality", quality)
        metadata.setdefault("repair_rules", rules)
        metadata["response_keys"] = sorted(value)
    if stage == "GROUND_MAP" and {"entities", "claims"} <= set(value):
        # Empty auxiliary collections may be omitted by compatible endpoints;
        # entity/claim evidence remains mandatory and is validated downstream.
        for field in ("content_units", "entities", "relations", "claims", "warnings"):
            if field in value and not isinstance(value[field], list):
                raise AIProviderError(
                    "AI_PROVIDER_SCHEMA_INVALID", f"模型输出字段 {field} 必须是列表", retryable=True
                )
        if metadata is not None:
            metadata["schema_defaults"] = [
                field for field in ("content_units", "relations", "warnings") if field not in value
            ]
        return
    if stage == "TRANSCRIPT_CORRECTION" and not isinstance(value.get("changes"), list):
        raise AIProviderError(
            "AI_PROVIDER_SCHEMA_INVALID",
            "模型输出缺少字段：changes",
            retryable=True,
        )
    missing = [field for field in _REQUIRED_FIELDS.get(stage, ()) if field not in value]
    if missing:
        raise AIProviderError(
            "AI_PROVIDER_SCHEMA_INVALID", f"模型输出缺少字段：{', '.join(missing)}", retryable=True
        )
    for field in ("segments", "changes", "places", "sections", "section_facts"):
        if field in value and not isinstance(value[field], list):
            raise AIProviderError(
                "AI_PROVIDER_SCHEMA_INVALID", f"模型输出字段 {field} 必须是列表", retryable=True
            )
    for field, limit in _LIST_LIMITS.get(stage, {}).items():
        if isinstance(value.get(field), list) and len(value[field]) > limit:
            raise AIProviderError(
                "AI_PROVIDER_SCHEMA_INVALID",
                f"模型输出字段 {field} 超过上限 {limit}",
                retryable=True,
            )
