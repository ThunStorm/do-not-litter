from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    if key in {"start_ms", "end_ms"}:
        return (getattr(item, "locator_json", {}) or {}).get(key, default)
    return getattr(item, key, default)


def assess_transcript_quality(
    segments: Iterable[Any], *, duration_ms: int | None, generated: bool = False, language: str = ""
) -> dict[str, object]:
    """Return deterministic, non-sensitive transcript quality evidence."""
    values = list(segments)
    starts = [max(0, int(_value(item, "start_ms", 0) or 0)) for item in values]
    ends = [
        max(start, int(_value(item, "end_ms", start) or start))
        for item, start in zip(values, starts, strict=True)
    ]
    texts = [str(_value(item, "text", "") or "").strip() for item in values]
    duration = max(0, int(duration_ms or 0))
    last_end = max(ends, default=0)
    monotonic = sum(start >= previous for previous, start in zip(starts, starts[1:], strict=False))
    duplicate = len(texts) - len(set(text for text in texts if text))
    chars = sum(len(text) for text in texts)
    reasons: list[str] = []
    normalized_language = language.lower().replace("_", "-")
    if generated:
        reasons.append("PLATFORM_SUBTITLE_UNVERIFIED")
    elif normalized_language and "zh" not in normalized_language.split("-"):
        reasons.append("PLATFORM_SUBTITLE_LANGUAGE_UNVERIFIED")
    if not values:
        reasons.append("PLATFORM_SUBTITLE_EMPTY")
    if len(values) > 1 and monotonic < len(values) - 1:
        reasons.append("PLATFORM_SUBTITLE_NON_MONOTONIC")
    if duration and last_end > duration + max(30_000, round(duration * 0.2)):
        reasons.append("PLATFORM_SUBTITLE_TIMELINE_INVALID")
    metrics = {
        "timeline_coverage": round(min(1.0, last_end / duration), 4) if duration else None,
        "timeline_ratio": round(last_end / duration, 4) if duration else None,
        "monotonic_ratio": round(monotonic / max(1, len(values) - 1), 4),
        "duplicate_ratio": round(duplicate / max(1, len(values)), 4),
        "text_density": round(chars / max(1, last_end / 1000), 4),
    }
    return {
        "status": "PASS" if not reasons else "SUSPECT",
        "validation_status": "TRUSTED_PLATFORM" if not reasons else "REJECTED_PLATFORM",
        "reasons": reasons,
        "metrics": metrics,
    }
