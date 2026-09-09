"""Deterministic normalization and evidence-preserving Place knowledge views."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

VOLATILE_TYPES = {"PRICE", "QUEUE", "OPENING_HOURS", "MENU", "TICKET"}
CATEGORY_BY_TYPE = {
    "HIGHLIGHT": "highlights",
    "RECOMMENDED_ITEM": "dishes",
    "BEST_MONTH": "visit_windows",
    "BEST_SEASON": "visit_windows",
    "BEST_TIME_SLOT": "visit_windows",
    "WARNING": "warnings",
    "PRICE": "prices",
    "QUEUE": "queues",
    "AUTHOR_OPINION": "opinions",
}
CHINESE_RANGES = {"七八十": (70, 80), "一两百": (100, 200), "两三百": (200, 300)}
CHINESE_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "两": 2}


def normalize_insight(
    insight_type: str, value_text: str, value_key: str = "", value_json: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    """Return a stable key and structured representation without rewriting source wording."""
    text = str(value_text or "").strip()
    data = dict(value_json or {})
    if insight_type in {"PRICE", "QUEUE"}:
        numeric = _numeric_range(text, insight_type)
        if numeric:
            data["normalized"] = numeric
            return f"{insight_type}:{numeric['min']}-{numeric['max']}{numeric['unit']}", data
    if insight_type == "AUTHOR_OPINION":
        sentiment = (
            "AVOID"
            if any(word in text for word in ("不推荐", "别去", "不建议"))
            else "RECOMMEND"
            if "推荐" in text
            else "NEUTRAL"
        )
        data["normalized"] = {"sentiment": sentiment}
        return f"OPINION:{sentiment}:{_text_key(text)}", data
    return value_key.strip() or _text_key(text), data


def aggregate_place_knowledge(
    insights: list[Any], source_titles: dict[str, str] | None = None
) -> dict[str, Any]:
    """Aggregate active evidence only; each returned statement retains its source observations."""
    source_titles = source_titles or {}
    by_type: dict[str, list[Any]] = defaultdict(list)
    for insight in insights:
        if insight.status == "ACTIVE":
            by_type[str(insight.insight_type)].append(insight)
    knowledge: dict[str, list[dict[str, Any]]] = defaultdict(list)
    consensus: dict[str, str] = {}
    source_ids: set[str] = set()
    for insight_type, items in by_type.items():
        clusters: list[list[Any]] = []
        for item in items:
            target = next((cluster for cluster in clusters if _equivalent(cluster[0], item)), None)
            if target is None:
                clusters.append([item])
            else:
                target.append(item)
        states: list[str] = []
        latest = max(items, key=_observed_at) if insight_type in VOLATILE_TYPES else None
        for cluster in clusters:
            state = _state(cluster, len(clusters))
            states.append(state)
            observations = [
                _observation(item, source_titles) for item in sorted(cluster, key=_observed_at, reverse=True)
            ]
            source_ids.update(item.source_id for item in cluster if item.source_id)
            knowledge[CATEGORY_BY_TYPE.get(insight_type, "other")].append(
                {
                    "insight_type": insight_type,
                    "value_text": cluster[0].value_text,
                    "state": state,
                    "source_count": len({item.source_id for item in cluster if item.source_id}),
                    "evidence_complete": all(_evidence_complete(item) for item in cluster),
                    "provenance": _provenance(cluster),
                    "current": latest in cluster if latest is not None else True,
                    "observations": observations,
                }
            )
        consensus[insight_type] = (
            "CONFLICT" if "CONFLICT" in states else "CONSENSUS" if "CONSENSUS" in states else "SINGLE_SOURCE"
        )
    return {
        "highlights": knowledge["highlights"],
        "dishes": knowledge["dishes"],
        "visit_windows": knowledge["visit_windows"],
        "warnings": knowledge["warnings"],
        "prices": knowledge["prices"],
        "queues": knowledge["queues"],
        "opinions": knowledge["opinions"],
        "other": knowledge["other"],
        "consensus": consensus,
        "sources": [
            {"source_id": source_id, "title": source_titles.get(source_id, "来源未命名")}
            for source_id in sorted(source_ids)
        ],
    }


def _numeric_range(text: str, insight_type: str) -> dict[str, int | str] | None:
    for phrase, bounds in CHINESE_RANGES.items():
        if phrase in text:
            return {"min": bounds[0], "max": bounds[1], "unit": "CNY" if insight_type == "PRICE" else "MIN"}
    numbers = [int(value) for value in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        phrases = re.findall(r"[一二三四五六七八九十两百]+", text)
        numbers = [_chinese_number(value) for value in phrases if _chinese_number(value) is not None]
    if not numbers:
        return None
    factor = 60 if insight_type == "QUEUE" and any(unit in text for unit in ("小时", "h")) else 1
    minimum, maximum = numbers[0] * factor, (numbers[1] if len(numbers) > 1 else numbers[0]) * factor
    return {"min": minimum, "max": maximum, "unit": "CNY" if insight_type == "PRICE" else "MIN"}


def _chinese_number(value: str) -> int | None:
    total = current = 0
    for char in value:
        if char in CHINESE_DIGITS:
            current = CHINESE_DIGITS[char]
        elif char == "十":
            total += (current or 1) * 10
            current = 0
        elif char == "百":
            total += (current or 1) * 100
            current = 0
        else:
            return None
    return total + current if total + current else None


def _text_key(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()[:128]


def _equivalent(left: Any, right: Any) -> bool:
    left_data = dict(left.value_json or {}).get("normalized", {})
    right_data = dict(right.value_json or {}).get("normalized", {})
    if (
        isinstance(left_data, dict)
        and isinstance(right_data, dict)
        and {"min", "max"} <= set(left_data)
        and {"min", "max"} <= set(right_data)
    ):
        return int(left_data["min"]) <= int(right_data["max"]) and int(right_data["min"]) <= int(
            left_data["max"]
        )
    return str(left.value_key or _text_key(left.value_text)) == str(
        right.value_key or _text_key(right.value_text)
    )


def _state(cluster: list[Any], cluster_count: int) -> str:
    if cluster_count > 1:
        return "CONFLICT"
    if len({item.source_id for item in cluster if item.source_id}) >= 2 and all(
        _evidence_complete(item) for item in cluster
    ):
        return "CONSENSUS"
    return "SINGLE_SOURCE"


def _evidence_complete(item: Any) -> bool:
    return bool(item.source_id and item.source_quote and item.segment_ids_json)


def _observed_at(item: Any) -> datetime:
    metadata = item.metadata_json if isinstance(item.metadata_json, dict) else {}
    value = metadata.get("observed_at")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return item.created_at


def _observation(item: Any, source_titles: dict[str, str]) -> dict[str, Any]:
    return {
        "insight_id": item.id,
        "place_mention_id": item.place_mention_id,
        "source_id": item.source_id,
        "source_title": source_titles.get(item.source_id or "", "来源未命名"),
        "source_quote": item.source_quote,
        "segment_ids": item.segment_ids_json,
        "observed_at": _observed_at(item).isoformat(),
    }


def _provenance(items: list[Any]) -> str:
    values = {str(item.provenance) for item in items}
    return values.pop() if len(values) == 1 else "MIXED"
