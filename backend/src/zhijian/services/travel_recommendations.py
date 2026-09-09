"""Deterministic travel timing and recommendation views with evidence traces."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from zhijian.services.place_knowledge import aggregate_place_knowledge

VISIT_STATE_LABELS = {
    "BEST": "最佳",
    "GOOD": "适合",
    "POSSIBLE": "可以考虑",
    "CAUTION": "需注意",
    "CLOSED": "关闭或受限",
    "UNKNOWN": "时间未知",
}
TIER_LABELS = {
    "PRIORITY": "优先关注",
    "WORTH_CONSIDERING": "值得考虑",
    "GENERAL": "一般",
    "MISMATCH": "不符合偏好",
}
TRAIT_LABELS = {
    "nature": "自然景观",
    "urban": "城市探索",
    "historic": "历史人文",
    "food": "美食",
    "hiking": "徒步",
    "island": "海岛",
    "commercial": "商业体验",
    "crowded": "游客较多",
    "local": "本地生活",
    "luxury": "品质消费",
    "budget": "预算友好",
    "family": "适合家庭",
    "nightlife": "夜生活",
}
PLACE_TYPE_TRAITS = {
    "SCENIC_AREA": ("nature",),
    "PARK": ("nature",),
    "VILLAGE": ("nature", "local"),
    "MUSEUM": ("historic",),
    "TEMPLE": ("historic",),
    "TOWN": ("historic", "local"),
    "LANDMARK": ("historic",),
    "RESTAURANT": ("food",),
    "MARKET": ("food", "local"),
    "NEIGHBORHOOD": ("urban", "local"),
    "BUSINESS_DISTRICT": ("urban", "commercial"),
    "HOTEL": ("luxury",),
}
TRAIT_KEYWORDS = {
    "hiking": ("徒步", "登山", "爬山"),
    "island": ("海岛", "岛屿"),
    "crowded": ("人多", "拥挤", "排队"),
    "local": ("本地", "市井", "当地人"),
    "luxury": ("高端", "奢华", "精致"),
    "budget": ("平价", "便宜", "性价比"),
    "family": ("亲子", "家庭", "儿童"),
    "nightlife": ("夜市", "酒吧", "夜生活"),
}
EVENT_WEIGHTS = {"SAVE": 1, "PLANNED": 1, "VISITED": 1, "LIKE": 3, "DISMISS": -4, "DISLIKE": -3}
EXPLICIT_EVENTS = {"LIKE", "DISLIKE"}
BEST_PERIODS = {"BEST_VISIT", "BEST_VIEWING", "BLOOM", "FOLIAGE", "SNOW", "MIGRATION"}
SEASON_MONTHS = {"SPRING": (3, 4, 5), "SUMMER": (6, 7, 8), "AUTUMN": (9, 10, 11), "WINTER": (12, 1, 2)}


def visit_window_summary(windows: list[Any], month: int | None = None) -> dict[str, Any]:
    applicable = [item for item in windows if _matches_month(item, month)]
    if not applicable:
        return {
            "state": "UNKNOWN",
            "summary": "时间未知",
            "reason": "尚无可追溯的适宜时间证据",
            "evidence": [],
        }
    selected = max(applicable, key=lambda item: _state_rank(_window_state(item)))
    state = _window_state(selected)
    return {
        "state": state,
        "summary": f"{month} 月：{VISIT_STATE_LABELS[state]}"
        if month
        else f"适宜时间：{VISIT_STATE_LABELS[state]}",
        "reason": selected.source_text or _default_reason(selected, state),
        "evidence": [
            {
                "source_id": item.source_id,
                "segment_ids": list(item.segment_ids_json or []),
                "source_text": item.source_text,
            }
            for item in applicable
        ],
    }


def recommendation_for_place(
    place: Any,
    *,
    windows: list[Any],
    insights: list[Any],
    events: list[Any],
    month: int | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    traits = place_traits(place, insights, tags or [])
    preference, timing = _preference_weights(events, traits), visit_window_summary(windows, month)
    latest_event = max(events, key=lambda item: item.created_at, default=None)
    excluded = (
        place.user_state == "DISMISSED"
        or (latest_event is not None and latest_event.event_type == "DISMISS")
        or (month is not None and timing["state"] == "CLOSED")
    )
    reasons, score = [], 0
    for trait in traits:
        if contribution := preference.get(trait["trait"]):
            score += contribution["weight"]
            reasons.append(
                {
                    "kind": "PERSONAL_PREFERENCE",
                    "text": contribution["reason"],
                    "weight": contribution["weight"],
                    "trace": trait,
                }
            )
    timing_weight = {"BEST": 3, "GOOD": 2, "POSSIBLE": 1, "CAUTION": -1}.get(timing["state"], 0)
    score += timing_weight
    if timing_weight:
        reasons.append(
            {
                "kind": "SYSTEM_JUDGMENT",
                "text": timing["summary"] + "，" + timing["reason"],
                "weight": timing_weight,
                "trace": timing,
            }
        )
    consensus = set(aggregate_place_knowledge(insights)["consensus"].values())
    if "CONFLICT" in consensus:
        score -= 1
        reasons.append(
            {
                "kind": "SYSTEM_JUDGMENT",
                "text": "来源事实存在冲突，已降低优先级",
                "weight": -1,
                "trace": {"consensus": "CONFLICT"},
            }
        )
    elif "CONSENSUS" in consensus:
        score += 2
        reasons.append(
            {
                "kind": "SOURCE_FACT",
                "text": "多来源证据一致",
                "weight": 2,
                "trace": {"consensus": "CONSENSUS"},
            }
        )
    if place.user_state == "PLANNED":
        score += 1
        reasons.append(
            {
                "kind": "PERSONAL_PREFERENCE",
                "text": "你已将此地点加入计划",
                "weight": 1,
                "trace": {"event": "PLANNED"},
            }
        )
    tier = (
        "MISMATCH"
        if excluded or score < 0
        else "PRIORITY"
        if score >= 4
        else "WORTH_CONSIDERING"
        if score >= 2
        else "GENERAL"
    )
    return {
        "place_id": place.id,
        "tier": tier,
        "label": TIER_LABELS[tier],
        "excluded": excluded,
        "reasons": sorted(reasons, key=lambda item: item["weight"], reverse=True)[:4],
        "traits": traits,
        "visit_window": timing,
    }


def place_traits(place: Any, insights: list[Any], tags: list[str]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for trait in PLACE_TYPE_TRAITS.get(str(place.place_type), ()):
        found[trait] = {
            "trait": trait,
            "label": TRAIT_LABELS[trait],
            "source": "PLACE_ATTRIBUTE",
            "reason": f"地点类型：{place.place_type}",
        }
    text = " ".join(
        [str(place.summary or ""), *[str(item.value_text or "") for item in insights], *tags]
    ).lower()
    for trait, words in TRAIT_KEYWORDS.items():
        if word := next((item for item in words if item in text), None):
            found.setdefault(
                trait,
                {
                    "trait": trait,
                    "label": TRAIT_LABELS[trait],
                    "source": "USER_TAG" if word in tags else "SOURCE_FACT",
                    "reason": f"证据提及：{word}",
                },
            )
    return list(found.values())


def group_by_place(items: list[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        grouped[item.place_id].append(item)
    return grouped


def _matches_month(item: Any, month: int | None) -> bool:
    return (
        month is None or item.month == month
        if item.month is not None
        else month in SEASON_MONTHS.get(str(item.season or ""), ())
        if item.season
        else True
    )


def _window_state(item: Any) -> str:
    if item.period_type in {"SEASONAL_CLOSURE", "FISHING_CLOSURE"}:
        return "CLOSED"
    if item.suitability in {"RESTRICTED", "AVOID"}:
        return "CAUTION"
    return (
        "BEST"
        if item.suitability == "RECOMMENDED" and item.period_type in BEST_PERIODS
        else "GOOD"
        if item.suitability == "RECOMMENDED"
        else "POSSIBLE"
    )


def _state_rank(state: str) -> int:
    return {"CLOSED": 6, "CAUTION": 5, "BEST": 4, "GOOD": 3, "POSSIBLE": 2, "UNKNOWN": 1}[state]


def _default_reason(item: Any, state: str) -> str:
    return (
        "来源记录该时段关闭或受限"
        if state == "CLOSED"
        else "来源记录该时段需注意"
        if state == "CAUTION"
        else "来源记录的适宜时间"
    )


def _preference_weights(events: list[Any], traits: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    explicit_seen: set[str] = set()
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if not (weight := EVENT_WEIGHTS.get(str(event.event_type), 0)):
            continue
        for trait in traits:
            name = trait["trait"]
            if name in explicit_seen and event.event_type not in EXPLICIT_EVENTS:
                continue
            if event.event_type in EXPLICIT_EVENTS:
                explicit_seen.add(name)
            if current := result.get(name):
                current["weight"] += weight
            else:
                layer = "明确偏好" if event.event_type in EXPLICIT_EVENTS else "行为"
                result[name] = {"weight": weight, "reason": f"你的{layer}显示偏向{trait['label']}"}
    return result
