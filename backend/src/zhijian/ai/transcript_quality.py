import re
from typing import Any

_BROKEN_TEXT = re.compile(r"\ufffd|(.)\1{3,}|[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SEMANTIC_CANDIDATE = re.compile(
    r"\d|[一二三四五六七八九十百千万]+[月日号点岁元块折]|"
    r"(?:路|街|巷|桥|站|港|山|湖|寺|庙|馆|园|村|镇|店|市场|酒店|民宿|餐厅)|"
    r"(?:价格|门票|开放|预约|排队|季|花期|红叶|雪|迁徙)"
)
TRUSTED_HUMAN_SUBTITLE = "TRUSTED_HUMAN_SUBTITLE"
GENERATED_PLATFORM_SUBTITLE = "GENERATED_PLATFORM_SUBTITLE"
LOCAL_ASR_WITH_CONFIDENCE = "LOCAL_ASR_WITH_CONFIDENCE"
LOCAL_ASR_WITHOUT_CONFIDENCE = "LOCAL_ASR_WITHOUT_CONFIDENCE"


def transcript_source_class(
    segments: list[Any], *, source_kind: str, provider_id: str = ""
) -> str:
    kind = source_kind.upper()
    if any(marker in kind for marker in ("MANUAL", "HUMAN", "OFFICIAL")) and "AI" not in kind:
        return TRUSTED_HUMAN_SUBTITLE
    if "SUBTITLE" in kind or ("BILIBILI" in kind and "ASR" not in kind):
        return GENERATED_PLATFORM_SUBTITLE
    if provider_id or "ASR" in kind:
        if any(getattr(segment, "confidence", None) is not None for segment in segments):
            return LOCAL_ASR_WITH_CONFIDENCE
        return LOCAL_ASR_WITHOUT_CONFIDENCE
    return LOCAL_ASR_WITHOUT_CONFIDENCE


def correction_candidates(
    segments: list[Any],
    *,
    source_kind: str,
    provider_id: str = "",
    force_full: bool = False,
    neighbor_segments: int = 2,
) -> list[Any]:
    del neighbor_segments  # 邻段只属于只读 context，不再扩大 target 集合。
    if force_full:
        return list(segments)
    source_class = transcript_source_class(
        segments,
        source_kind=source_kind,
        provider_id=provider_id,
    )
    if source_class == TRUSTED_HUMAN_SUBTITLE:
        return []
    candidates: list[int] = []
    seen: set[str] = set()
    for index, segment in enumerate(segments):
        text = str(getattr(segment, "raw_text", "") or getattr(segment, "text", "")).strip()
        confidence = getattr(segment, "confidence", None)
        compact = re.sub(r"\s+", "", text)
        suspicious = (
            not text
            or _BROKEN_TEXT.search(text) is not None
            or compact in seen
            or len(compact) <= 1
            or len(compact) > 500
            or (confidence is not None and float(confidence) < 0.85)
            or _SEMANTIC_CANDIDATE.search(text) is not None
        )
        if suspicious:
            candidates.append(index)
        if compact:
            seen.add(compact)
    return [segments[index] for index in candidates]
