from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from zhijian.resolvers.video import is_bilibili_url

URL_PATTERN = re.compile(r"(?:(?:https?://)|(?:www\.)|(?:b23\.tv/))[^\s<>，。；、！!？?）)】}\]\\\"']+", re.I)
TRAILING = "，。；、！!？?）)】}]}\\\"'"


@dataclass(frozen=True, slots=True)
class NormalizedInput:
    kind: str
    selected_url: str | None
    candidates: tuple[str, ...]
    discarded_text_length: int
    raw_input_hash: str


def normalize_capture_input(value: str) -> NormalizedInput:
    cleaned = value.replace("\u200b", "").strip()
    candidates = tuple(dict.fromkeys(_canonical(candidate) for candidate in URL_PATTERN.findall(cleaned)))
    raw_hash = hashlib.sha256(cleaned.encode()).hexdigest()
    if not candidates:
        return NormalizedInput("TEXT_ONLY", None, (), 0, raw_hash)
    selected: str | None = None
    if len(candidates) == 1:
        selected = candidates[0]
    else:
        specialized = [candidate for candidate in candidates if is_bilibili_url(candidate)]
        if len(specialized) == 1:
            selected = specialized[0]
    if selected is None:
        return NormalizedInput("MULTIPLE_URLS", None, candidates, 0, raw_hash)
    return NormalizedInput(
        "URL_ONLY" if cleaned == selected else "SHARE_TEXT_WITH_URL",
        selected,
        candidates,
        max(0, len(cleaned) - len(selected)),
        raw_hash,
    )


def _canonical(value: str) -> str:
    value = value.rstrip(TRAILING)
    if value.startswith("www.") or value.startswith("b23.tv/"):
        value = "https://" + value
    parts = urlsplit(value)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, parts.fragment))
