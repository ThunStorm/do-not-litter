"""Conservative, quote-derived qualifiers. No network, persistence or place-name dictionary."""

from __future__ import annotations

import calendar
import re

from zhijian.services.travel_timing import _number

VERSION = "travel-semantics-v1"


def temporal_semantics(text: str, *, scope: str = "PLACE", period_type: str | None = None) -> dict:
    activity = next(
        (
            code
            for pattern, code in (
                (r"禁渔|休渔|禁捕|钓鱼|捕捞", "FISHING"),
                (r"骑马", "HORSE_RIDING"),
                (r"骑行|骑车", "CYCLING"),
                (r"自驾|封路|道路|路段|公路|落石", "SELF_DRIVE"),
                (r"观赏|观花|油菜花|水性杨花|红嘴鸥|日照金山|灌水|红叶|雾凇", "VIEWING"),
                (r"徒步|登山", "HIKING"),
            )
            if re.search(pattern, text)
        ),
        "GENERAL_VISIT",
    )
    if activity == "GENERAL_VISIT" and period_type in {
        "BEST_VIEWING",
        "BLOOM",
        "FOLIAGE",
        "SNOW",
        "MIGRATION",
    }:
        activity = "VIEWING"
    if activity == "SELF_DRIVE" and re.search(r"部分|路段|公路|廊道|东线|西线", text):
        scope = "ROAD_SECTION"
    purpose = (
        "ACCESS"
        if activity == "SELF_DRIVE"
        else "VIEWING"
        if activity == "VIEWING"
        else "ACTIVITY"
        if activity != "GENERAL_VISIT"
        else "VISIT"
    )
    token = r"([0-9一二三四五六七八九十]{1,3})"
    date = re.search(
        token + r"月" + token + r"[日号](?:至|到|[-—~～])(?:次年)?(?:" + token + r"月)?" + token + r"[日号]",
        text,
    )
    start = end = None
    precision = "QUALITATIVE"
    if date:
        m1, d1, m2, d2 = date.groups()
        a, b, c, d = _number(m1), _number(d1), _number(m2 or m1), _number(d2)
        if (
            1 <= a <= 12
            and 1 <= c <= 12
            and 1 <= b <= calendar.monthrange(2000, a)[1]
            and 1 <= d <= calendar.monthrange(2000, c)[1]
        ):
            start, end, precision = {"month": a, "day": b}, {"month": c, "day": d}, "DAY"
    if not start:
        match = re.search(token + r"月?(?:至|到|[-—~～])(?:次年)?" + token + r"月", text)
        if match and all(1 <= _number(v) <= 12 for v in match.groups()):
            start, end, precision = {"month": _number(match[1])}, {"month": _number(match[2])}, "MONTH"
        elif re.search(token + r"月", text):
            precision = "MONTH"
        elif re.search(r"春[季天]|夏[季天]|秋[季天]|冬[季天]", text):
            precision = "SEASON"
    return {
        "schema_version": VERSION,
        "scope": scope,
        "purpose": purpose,
        "activity": activity,
        "precision": precision,
        "start": start,
        "end": end,
        "cross_year": bool(
            start and end and (end["month"], end.get("day", 1)) < (start["month"], start.get("day", 1))
        ),
        "interpretation_status": "NEEDS_REVIEW"
        if re.search(r"存疑|待核|疑似|S[一二三四五六七八九十幺]+", text)
        else "SOURCE_REPORTED",
    }


def classify_entity(item: dict) -> dict:
    raw = str(item.get("raw_name") or item.get("raw_label") or item.get("name") or "")
    kind = str(item.get("entity_type") or item.get("kind") or "PLACE")
    uncertain = (
        kind == "PLACE_UNCERTAIN"
        or item.get("review_status") == "NEEDS_REVIEW"
        or bool(re.search(r"待核|疑似|S[一二三四五六七八九十幺]+", raw))
    )
    identity = (
        "UNRESOLVED_NAME"
        if uncertain
        else "AREA"
        if kind in {"AREA", "PLACE_AREA", "AREA_DESTINATION"}
        else "GENERIC"
        if kind == "GENERIC_FEATURE"
        else "LINEAR"
        if kind == "LINEAR_FEATURE"
        else "WAYPOINT"
        if item.get("subject_role") == "REFERENCE"
        else "PLACE"
    )
    return {
        "raw_name": raw,
        "identity": identity,
        "review_status": "NEEDS_REVIEW" if uncertain else "SOURCE_REPORTED",
        "eligible_for_poi": identity == "PLACE"
        and item.get("subject_role", "PRIMARY") in {"PRIMARY", "SECONDARY"}
        and item.get("visit_intent") in {"RECOMMENDED", "OPTIONAL"},
    }


def scoped_travel_facts(text: str, segment_ids: list[str], *, scope: str = "PLACE") -> list[dict]:
    facts = []
    for sentence in filter(None, (s.strip() for s in re.split(r"[。！？!?；;]", text))):
        kind = (
            "ROAD_RESTRICTION"
            if re.search(r"封路|落石|禁止.*自驾|不能.*自驾|不[能可]开车", sentence)
            else "ACCESS_MODE"
            if re.search(r"自驾|骑行|包车|公交|公共交通|火车|米轨", sentence)
            else None
        )
        if kind:
            facts.append(
                {
                    "insight_type": kind,
                    "value_text": sentence,
                    "source_quote": sentence,
                    "segment_ids": list(segment_ids),
                    "provenance": "SOURCE_FACT",
                    "value_json": temporal_semantics(sentence, scope=scope),
                }
            )
    return facts
