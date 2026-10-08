"""Keep reported, locally estimated and unavailable token counts separate."""

from typing import Any


def estimate_tokens(characters: int) -> int:
    """Existing conservative character heuristic; not a provider tokenizer."""
    return max(0, (characters + 1) // 2)


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def token_usage(metadata: dict, input_chars: int = 0) -> dict[str, int]:
    result = {}
    for side, provider_field, characters in (
        ("input", "prompt", input_chars),
        ("output", "completion", metadata.get("content_length")),
    ):
        reported = _count(metadata.get(f"{provider_field}_tokens"))
        if metadata.get("usage_source") == "UNKNOWN":
            reported = None
        estimated = None
        if reported is None:
            estimated = _count(metadata.get(f"estimated_{provider_field}_tokens"))
            if estimated is None and _count(characters) is not None and characters > 0:
                estimated = estimate_tokens(characters)
        result.update({
            f"{side}_tokens": reported or 0,
            f"estimated_{side}_tokens": estimated or 0,
            f"estimated_{side}_calls": int(estimated is not None),
            f"unknown_{side}_calls": int(reported is None and estimated is None),
        })
    return result
