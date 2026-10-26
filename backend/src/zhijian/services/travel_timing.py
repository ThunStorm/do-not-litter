"""Shared calendar matching and conservative, evidence-derived display labels."""

from __future__ import annotations

import re
from typing import Any

SEASON_MONTHS = {"SPRING": (3, 4, 5), "SUMMER": (6, 7, 8), "AUTUMN": (9, 10, 11), "WINTER": (12, 1, 2)}
SEASON_LABELS = {"SPRING": "春季", "SUMMER": "夏季", "AUTUMN": "秋季", "WINTER": "冬季"}
SEGMENT_LABELS = {"EARLY": "上旬", "MID": "中旬", "LATE": "下旬"}
SLOT_LABELS = {
    "EARLY_MORNING": "清晨",
    "MORNING": "上午",
    "NOON": "中午",
    "AFTERNOON": "下午",
    "SUNSET": "日落",
    "EVENING": "傍晚",
    "NIGHT": "夜间",
}
ALL_YEAR = re.compile(r"全年|一年四季|四季皆宜|四季都(?:适合|可以)")
TEMPORAL_SCOPE = re.compile(
    r"\d{1,2}月|[一二三四五六七八九十]{1,3}月|春[季天日]|夏[季天日]|秋[季天日]|冬[季天日]|上旬|中旬|下旬|清晨|日出|上午|中午|下午|日落|黄昏|傍晚|夜[间晚]|全年|四季|观赏期|游览时间|旅行季节|丰水|枯水|汛期|休渔|禁渔|禁捕|封山|闭园|停航|封航|花[期季]|红叶[期季]|赏枫|雪季|雪后|下雪|晴天|早晨|结冰|融冰|候鸟|迁徙期|雨季|旱季|旺季|淡季"
)


def has_temporal_scope(text: str) -> bool:
    return bool(TEMPORAL_SCOPE.search(text))


def valid_window(item: Any) -> bool:
    # Human windows may intentionally be qualitative. Derived windows need temporal evidence.
    return item.provenance not in {"SOURCE_FACT", "TITLE_CONTEXT", "SEMANTIC_CONTEXT"} or has_temporal_scope(
        item.source_text or ""
    )


def matches_window(
    item: Any,
    *,
    month: int | None = None,
    season: str | None = None,
    month_segment: str | None = None,
    day_time_slot: str | None = None,
) -> bool:
    if not valid_window(item):
        return False
    if month is not None:
        if item.month is not None and item.month != month:
            return False
        if item.month is None and item.season and month not in SEASON_MONTHS.get(item.season, ()):
            return False
        if item.month is None and not item.season and not ALL_YEAR.search(item.source_text or ""):
            return False
    if (
        season
        and item.season != season
        and not (
            not item.season
            and (item.month in SEASON_MONTHS.get(season, ()) or ALL_YEAR.search(item.source_text or ""))
        )
    ):
        return False
    return (not month_segment or item.month_segment == month_segment) and (
        not day_time_slot or item.day_time_slot == day_time_slot
    )


def _number(value: str) -> int:
    if value.isdigit():
        return int(value)
    digits = {c: i for i, c in enumerate("零一二三四五六七八九")}
    if "十" in value:
        a, b = value.split("十", 1)
        return (digits.get(a, 1) if a else 1) * 10 + digits.get(b, 0)
    return digits.get(value, 0)


def window_label(item: Any) -> str:
    relative = re.search(
        r"雪后(?:的)?[一二三四五六七八九十\d]+(?:到|至|–|-)?[一二三四五六七八九十\d]*天",
        item.source_text or "",
    )
    if relative:
        return (
            f"{item.month}月{SEGMENT_LABELS.get(item.month_segment, '')} · " if item.month else ""
        ) + relative.group(0)
    # Preserve exact dates only when explicitly present in the original evidence.
    token = r"([0-9一二三四五六七八九十]{1,3})"
    match = re.search(
        token + r"月" + token + r"[日号]?(?:至|到|[-—~～])(?:" + token + r"月)?" + token + r"[日号]?",
        item.source_text or "",
    )
    if match:
        m1, d1, m2, d2 = match.groups()
        a, b, c, d = _number(m1), _number(d1), _number(m2 or m1), _number(d2)
        if (
            1 <= a <= 12
            and 1 <= c <= 12
            and 1 <= b <= 31
            and 1 <= d <= 31
            and (not item.month or item.month == a)
        ):
            return f"{a}月{b}–{d}日" if a == c else f"{a}月{b}日–{c}月{d}日"
    if ALL_YEAR.search(item.source_text or "") and not item.month and not item.season:
        return "全年"
    parts = [
        f"{item.month}月" if item.month else SEASON_LABELS.get(item.season, ""),
        SEGMENT_LABELS.get(item.month_segment, ""),
        SLOT_LABELS.get(item.day_time_slot, ""),
    ]
    return "".join(parts) or {
        "HIGH_WATER": "丰水期",
        "LOW_WATER": "枯水期",
        "BLOOM": "花期",
        "FOLIAGE": "红叶期",
        "SNOW": "雪季",
        "MIGRATION": "迁徙期",
        "WEATHER_SEASON": "气候时段",
        "PEAK_SEASON": "旺季",
        "OFF_SEASON": "淡季",
        "SEASONAL_CLOSURE": "受限时段",
        "FISHING_CLOSURE": "休渔期",
    }.get(item.period_type, "时段待明确")
