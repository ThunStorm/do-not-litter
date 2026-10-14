"""Deterministic numeric request diagnostics; never persist prompts or quotes."""

import json
import re
from contextlib import suppress
from hashlib import sha256

from zhijian.ai.token_usage import estimate_tokens


def provider_cache_metrics(usage: dict, usage_source: str | None = None) -> dict:
    value = usage.get("cached_tokens")
    if value is None and isinstance(usage.get("prompt_tokens_details"), dict):
        value = usage["prompt_tokens_details"].get("cached_tokens")
    valid = (
        isinstance(value, int) and not isinstance(value, bool) and value >= 0 and usage_source != "UNKNOWN"
    )
    return {
        "reported_cached_tokens": value if valid else None,
        "cache_kind": "PROVIDER_PREFIX_CACHE_HIT" if valid and value > 0 else "UNKNOWN",
    }


def request_metrics(
    messages: list[dict[str, str]], *, domain_chars: int | None = None
) -> dict[str, int | str]:
    bodies = [str(item.get("content") or "") for item in messages]
    if domain_chars is None:
        domain_chars = sum(len(body) for body in bodies if body.startswith("以下领域上下文"))
    text = "\n".join(bodies)
    keys = re.findall(r'"([^"\\]+)"\s*:', text)
    references = re.findall(r"(?m)^\[segment:([^\s]+) [^\]]+\] (.*)$", text)

    def visit(value):
        if isinstance(value, dict):
            if (value.get("segment_id") or value.get("id")) and isinstance(value.get("text"), str):
                references.append((str(value.get("segment_id") or value["id"]), value["text"]))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for body in bodies:
        with suppress(json.JSONDecodeError, TypeError):
            visit(json.loads(body))
    unique_chars = sum(len(body) for body in dict(references).values())
    quotes = re.findall(r'"(?:quote|supporting_quote)"\s*:\s*("(?:[^"\\]|\\.)*")', text)
    prefix = []
    for item in messages:
        if item.get("role") == "user" or str(item.get("content") or "").startswith("以下领域上下文"):
            break
        prefix.append(item)
    prefix_chars = sum(len(str(item.get("content") or "")) for item in prefix)
    wire = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode()
    return {
        "metrics_version": "prompt-prefix-v1",
        "prompt_fingerprint": sha256(wire).hexdigest(),
        "static_prompt_fingerprint": sha256(
            json.dumps(prefix, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
        "static_prefix_chars": prefix_chars,
        "dynamic_body_chars": sum(map(len, bodies)) - prefix_chars,
        "raw_request_bytes": len(wire),
        "request_bytes_scope": "MESSAGES_JSON",
        "system_chars": sum(
            len(body) for item, body in zip(messages, bodies, strict=True) if item.get("role") == "system"
        )
        - domain_chars,
        "domain_chars": domain_chars,
        "user_body_chars": sum(
            len(body) for item, body in zip(messages, bodies, strict=True) if item.get("role") == "user"
        ),
        "unique_transcript_chars": unique_chars,
        "duplicate_context_chars": sum(len(body) for _, body in references) - unique_chars,
        "evidence_quote_chars": sum(len(json.loads(value)) for value in quotes),
        "id_chars": sum(
            len(value) for value in re.findall(r"(?:seg|plc|job|ntv)_[a-f0-9]{32}|\bs\d+\b", text)
        ),
        "json_key_chars": sum(map(len, keys)),
        "json_bytes": len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode()),
        "model_input_chars": sum(map(len, bodies)),
        "estimated_input_tokens": estimate_tokens(sum(map(len, bodies))),
        "request_count": 1,
    }
