"""Safe structured-output normalization shared by model stages."""

from __future__ import annotations

import json
import re
from typing import Any

from zhijian.ai.reliability import AIProviderError


def _check_incomplete_json(error: json.JSONDecodeError) -> None:
    tail = error.doc[error.pos :]
    partial_literal = tail in {"t", "tr", "tru", "f", "fa", "fal", "fals", "n", "nu", "nul"}
    if (
        not tail
        or error.msg == "Unterminated string starting at"
        or (error.msg == "Expecting value" and partial_literal)
    ):
        raise AIProviderError(
            "AI_PROVIDER_OUTPUT_TRUNCATED",
            "模型返回的 JSON 被截断，响应末尾未闭合",
            switch_model=False,
            cause=error,
        ) from error


def parse_json_with_quality(content: str) -> tuple[dict[str, Any], str, list[str]]:
    original = str(content or "")
    text = original.removeprefix("\ufeff").strip()
    if not text:
        raise AIProviderError("AI_PROVIDER_EMPTY_RESPONSE", "模型没有返回内容", retryable=True)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    if text.startswith("["):
        # A container is not commentary: never extract an object from a root array.
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            _check_incomplete_json(exc)
            raise AIProviderError(
                "AI_PROVIDER_INVALID_JSON", "模型返回的 JSON 无法解析", retryable=True, cause=exc
            ) from exc
        raise AIProviderError(
            "AI_PROVIDER_SCHEMA_INVALID", "模型返回的 JSON 顶层必须是对象", retryable=True
        )
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
    if end != len(text) - 1:
        # A last brace may close an inner object. Inspect the complete tail first.
        try:
            _, consumed = json.JSONDecoder().raw_decode(text, start)
        except json.JSONDecodeError as exc:
            _check_incomplete_json(exc)
            if end < start:
                raise AIProviderError(
                    "AI_PROVIDER_INVALID_JSON", "模型返回的 JSON 无法解析", retryable=True, cause=exc
                ) from exc
        else:
            if text[consumed:].lstrip().startswith(("{", "[", ",")):
                raise AIProviderError(
                    "AI_PROVIDER_INVALID_JSON", "模型返回了额外的 JSON 片段", retryable=True
                )
    # Repair only commas outside quoted strings; never rewrite evidence text.
    candidate = text[start : end + 1]
    rules: list[str] = ["outer_commentary"] if start != 0 or end != len(text) - 1 else []
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        if end == len(text) - 1:
            _check_incomplete_json(exc)
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
    "COVER_TEXT": ("regions",),
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
    if stage == "COVER_TEXT":
        return {
            "type": "object",
            "required": ["regions"],
            "properties": {
                "regions": {
                    "type": "array",
                    "maxItems": 64,
                    "items": {
                        "type": "object",
                        "required": ["text", "bounds", "confidence"],
                        "properties": {
                            "text": {"type": "string", "maxLength": 500},
                            "bounds": {
                                "type": "object",
                                "required": ["left", "top", "right", "bottom"],
                                "properties": {
                                    k: {"type": "number", "minimum": 0, "maximum": 1}
                                    for k in ["left", "top", "right", "bottom"]
                                },
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                }
            },
        }
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


def _validate_ground_map_lists(value: dict[str, Any]) -> None:
    """Reject explicit null/wrong containers before evidence decoding can iterate them."""
    from zhijian.ai.structured_ids import schema_issue

    def check_list(item: dict, field: str, path: str) -> list:
        if field not in item:
            return []  # Preserve the existing omitted-field compatibility contract.
        if not isinstance(item[field], list):
            raise schema_issue("INVALID_LIST", f"{path}.{field}")
        return item[field]

    fields = {
        "section_facts": ("segment_ids", "supporting_quotes", "key_points"),
        "places": ("segment_ids",),
        "entities": ("segment_ids", "temporal_applications"),
        "content_units": ("segment_ids", "anchor_entity_ids"),
        "relations": ("segment_ids",),
        "claims": ("segment_ids", "subject_entity_ids"),
        "warnings": (),
    }
    for collection, nested_fields in fields.items():
        for index, item in enumerate(check_list(value, collection, "$")):
            path = f"$.{collection}[{index}]"
            if collection == "warnings":
                continue
            if not isinstance(item, dict):
                raise schema_issue("INVALID_LOCAL_ITEM", path)
            for field in nested_fields:
                check_list(item, field, path)
            if collection == "entities" and isinstance(evidence := item.get("recommendation_evidence"), dict):
                evidence_path = f"{path}.recommendation_evidence"
                for number, statement in enumerate(check_list(evidence, "statements", evidence_path)):
                    statement_path = f"{evidence_path}.statements[{number}]"
                    if not isinstance(statement, dict):
                        raise schema_issue("INVALID_LOCAL_ITEM", statement_path)
                    check_list(statement, "supersedes", statement_path)


def validate_structured_output(content: str, stage: str, metadata: dict[str, Any] | None = None) -> None:
    if str((metadata or {}).get("finish_reason") or "").lower() in {"length", "max_tokens"}:
        raise AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "模型输出达到长度上限")
    value, quality, rules = parse_json_with_quality(content)
    if metadata is not None:
        metadata.setdefault("parse_quality", quality)
        metadata.setdefault("repair_rules", rules)
        metadata["response_keys"] = sorted(value)
    if stage == "GROUND_MAP":
        _validate_ground_map_lists(value)
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
