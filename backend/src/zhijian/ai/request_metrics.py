"""Deterministic numeric request diagnostics; never persist prompts or quotes."""

import json
import re
from contextlib import suppress

from zhijian.ai.token_usage import estimate_tokens


def request_metrics(messages: list[dict[str, str]], *, domain_chars: int = 0) -> dict[str, int]:
    bodies = [str(item.get("content") or "") for item in messages]
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
    return {
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
