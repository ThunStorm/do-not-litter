import re
from typing import Any

_BROKEN_TEXT = re.compile(r"\ufffd|(.)\1{3,}|[\x00-\x08\x0b\x0c\x0e-\x1f]")


def correction_candidates(
    segments: list[Any], *, source_kind: str, force_full: bool = False
) -> list[Any]:
    if force_full:
        return list(segments)
    platform_subtitle = "ASR" not in source_kind.upper()
    candidates = []
    previous = ""
    for segment in segments:
        text = str(getattr(segment, "raw_text", "") or getattr(segment, "text", "")).strip()
        confidence = getattr(segment, "confidence", None)
        suspicious = (
            not text
            or _BROKEN_TEXT.search(text) is not None
            or text == previous
            or (confidence is not None and float(confidence) < 0.85)
        )
        if suspicious or not platform_subtitle:
            candidates.append(segment)
        previous = text
    return candidates
