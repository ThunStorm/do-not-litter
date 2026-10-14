"""Conservative, versioned title metadata; never manufacture transcript evidence."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any

TITLE_TEMPORAL_VERSION = "title-temporal-v1"
TOPICS = {
    "FOLIAGE": r"红叶|赏枫|枫叶",
    "BLOOM": r"赏花|花期|花季|樱花",
    "SNOW": r"雪季|冰雪|赏雪",
    "MIGRATION": r"候鸟|迁徙",
}


def parse_title_temporal_context(title: str) -> dict[str, Any]:
    from zhijian.services.video_support import (
        _calendar_fields_from_text,
        _months_in_text,
        _period_type_from_text,
    )

    fields = _calendar_fields_from_text(title)
    months = _months_in_text(title)
    period = _period_type_from_text(title)
    period = next((code for code, pattern in TOPICS.items() if re.search(pattern, title)), period)
    intent = "UNKNOWN"
    scope = "SPECIFIC_PLACE"
    if re.search(r"去年|前年|记录|回顾|游记|出发|回来|返程|拍摄|摄于|实录", title):
        scope = "TRIP_TIME"
    elif months or any(fields.values()):
        if re.search(r"闭园|封山|停航|禁渔|休渔", title):
            intent = "RESTRICTED"
            period = "FISHING_CLOSURE" if re.search(r"禁渔|休渔", title) else "SEASONAL_CLOSURE"
        elif re.search(r"不推荐|不建议|不适合|不要|别去|避开", title):
            intent = "AVOID"
        elif re.search(r"推荐|适合|适宜|最佳|最好|最美|哪里|去哪|人少景美|赏红叶|赏枫|赏花|赏雪", title):
            intent = "RECOMMENDED"
        if re.search(r"哪里|去哪|人少景美|目的地", title) or period in TOPICS:
            scope = "VIDEO_THEME"
    # A single title with several independent time clauses has no safe global scope.
    clauses = [part for part in re.split(r"[，,；;。！？!?]|但|而", title) if _months_in_text(part)]
    if len(clauses) > 1 or len(title) > 500:
        intent, scope = "UNKNOWN", "AMBIGUOUS"
    # Residual theme words are a scope guard, not a guessed geographic entity.
    scope_terms = []
    if scope == "VIDEO_THEME":
        residual = re.sub(
            r"[一二三四五六七八九十\d]+月|上旬|中旬|下旬|春季|夏季|秋季|冬季|春天|夏天|秋天|冬天", "", title
        )
        residual = re.sub(
            r"哪里|去哪儿?|人少景美|目的地|推荐|适合|适宜|最佳|最好|最美|小众|旅行|旅游|攻略|赏红叶|赏枫|赏花|赏雪|花期|花季|雪季|红叶|枫叶|樱花|清晨|日出|上午|中午|下午|日落|黄昏|傍晚|夜间|夜晚",
            "",
            residual,
        )
        scope_terms = re.findall(r"[\w]+", residual)
    return {
        "source_kind": "TITLE_METADATA",
        "source_text": title,
        "months": months,
        **fields,
        "period_type": "BEST_VISIT" if period == "OTHER" else period,
        "intent": intent,
        "scope": scope,
        "scope_terms": scope_terms,
        "confidence": 0.75 if intent != "UNKNOWN" else 0.0,
        "parser_version": TITLE_TEMPORAL_VERSION,
    }


def title_identity(title: str) -> dict[str, str]:
    context = parse_title_temporal_context(title)
    return {
        "normalized_title": re.sub(r"\s+", " ", title).strip(),
        "title_temporal_context_hash": sha256(
            json.dumps(context, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "title_parser_version": TITLE_TEMPORAL_VERSION,
    }


def title_projection(context: dict[str, Any], mention: Any, body: str, windows: list[dict]) -> dict[str, Any]:
    from zhijian.services.video_support import _calendar_fields_from_text, _months_in_text

    status = "INHERITED"
    if (
        context["intent"] != "RECOMMENDED"
        or mention.visit_intent != "RECOMMENDED"
        or mention.subject_role not in {"PRIMARY", "SECONDARY"}
        or mention.poi_policy not in {"RESOLVE", "AREA_RESOLVE"}
        or mention.extraction_status == "USER_REJECTED"
    ):
        status = "INELIGIBLE"
    elif (
        context["scope"] == "SPECIFIC_PLACE"
        and not any(name and name in context["source_text"] for name in (mention.name, mention.raw_name))
        or context["scope"] not in {"VIDEO_THEME", "SPECIFIC_PLACE"}
        or context["period_type"] in TOPICS
        and not re.search(TOPICS[context["period_type"]], body)
        or any(
            term
            not in body
            + mention.name
            + mention.raw_name
            + str(getattr(mention, "city_hint", "") or "")
            + str(getattr(mention, "province_hint", "") or "")
            for term in context.get("scope_terms", [])
        )
    ):
        status = "OUT_OF_SCOPE"
    elif (
        windows
        or _months_in_text(body)
        or any(_calendar_fields_from_text(body).values())
        or re.search(r"闭园|封山|不推荐|不建议|不适合|不要去", body)
    ):
        status = "BODY_PRECEDENCE"
    return {
        **context,
        "status": status,
        "content_unit_id": mention.content_unit_id,
        "conflict_recorded": status == "BODY_PRECEDENCE",
    }


def verified_title_context(context: object, title: str) -> bool:
    if not isinstance(context, dict) or context.get("status") != "INHERITED":
        return False
    parsed = parse_title_temporal_context(title)
    return parsed["intent"] == "RECOMMENDED" and all(
        context.get(key) == value for key, value in parsed.items()
    )


def title_context_label(context: dict) -> str:
    months = "、".join(str(value) for value in context.get("months", []))
    season = {"SPRING": "春季", "SUMMER": "夏季", "AUTUMN": "秋季", "WINTER": "冬季"}.get(
        context.get("season"), ""
    )
    part = {"EARLY": "上旬", "MID": "中旬", "LATE": "下旬"}.get(context.get("month_segment"), "")
    slot = {
        "EARLY_MORNING": "清晨",
        "MORNING": "上午",
        "NOON": "中午",
        "AFTERNOON": "下午",
        "SUNSET": "日落",
        "EVENING": "傍晚",
        "NIGHT": "夜间",
    }.get(context.get("day_time_slot"), "")
    return f"{months + ' 月' if months else season}{part}{slot}适合前往 · 来自视频标题"
