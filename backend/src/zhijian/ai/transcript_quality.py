import re
from typing import Any

_BROKEN_TEXT = re.compile(r"\ufffd|(.)\1{3,}|[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SEMANTIC_CANDIDATE = re.compile(
    r"\d|[一二三四五六七八九十百千万]+[月日号点岁元块折]|"
    r"(?:路|街|巷|桥|站|港|山|湖|寺|庙|馆|园|村|镇|店|市场|酒店|民宿|餐厅)|"
    r"(?:价格|门票|开放|预约|排队|季|花期|红叶|雪|迁徙)"
)


def correction_candidates(
    segments: list[Any], *, source_kind: str, force_full: bool = False, neighbor_segments: int = 2
) -> list[Any]:
    if force_full:
        return list(segments)
    kind = source_kind.upper()
    if any(marker in kind for marker in ("MANUAL", "HUMAN", "OFFICIAL")) and "AI" not in kind:
        return []
    platform_subtitle = "ASR" not in kind
    candidates: list[int] = []
    previous = ""
    for index, segment in enumerate(segments):
        text = str(getattr(segment, "raw_text", "") or getattr(segment, "text", "")).strip()
        confidence = getattr(segment, "confidence", None)
        suspicious = (
            not text
            or _BROKEN_TEXT.search(text) is not None
            or text == previous
            or (confidence is not None and float(confidence) < 0.85)
        )
        if suspicious or ("WHISPER" in kind and _SEMANTIC_CANDIDATE.search(text)):
            candidates.append(index)
        previous = text
    if not platform_subtitle and "WHISPER" not in kind:
        return list(segments)  # Legacy ASR without source-quality evidence remains conservative.
    if "WHISPER" not in kind:
        return [segments[index] for index in candidates]
    nearby = {
        related
        for index in candidates
        for related in range(
            max(0, index - neighbor_segments), min(len(segments), index + neighbor_segments + 1)
        )
    }
    return [segment for index, segment in enumerate(segments) if index in nearby]
