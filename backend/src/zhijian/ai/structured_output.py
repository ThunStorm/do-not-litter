"""Safe structured-output normalization shared by model stages."""

from __future__ import annotations

import json
import re
from typing import Any

from zhijian.ai.reliability import AIProviderError


def parse_json_object(content: str) -> dict[str, Any]:
    text = str(content or "").replace("\ufeff", "").strip()
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
    candidate = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIProviderError(
            "AI_PROVIDER_INVALID_JSON", "模型返回的 JSON 无法解析", retryable=True, cause=exc
        ) from exc
    if not isinstance(value, dict):
        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "模型返回的 JSON 顶层必须是对象", retryable=True)
    return value


_REQUIRED_FIELDS = {
    "GROUND_MAP": ("section_facts", "places", "warnings"),
    "EXTRACT_TRAVEL_FACTS": ("places",),
    "GENERATE_AI_NOTE": ("overview", "warnings", "sections", "section_facts"),
}


def validate_structured_output(content: str, stage: str, metadata: dict[str, Any] | None = None) -> None:
    if str((metadata or {}).get("finish_reason") or "").lower() in {"length", "max_tokens"}:
        raise AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "模型输出达到长度上限")
    value = parse_json_object(content)
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
