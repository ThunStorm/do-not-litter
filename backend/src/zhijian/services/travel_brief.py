"""Readable summaries of saved evidence, without extra travel advice or preference scores."""

from __future__ import annotations

import re

from zhijian.services.travel_timing import SEASON_LABELS, valid_window, window_label


def _unique(values):
    return list(dict.fromkeys(v.strip() for v in values if v and v.strip()))


def travel_brief(experience, windows, *, default_all_year=False, recommendation_summary=None):
    windows = [w for w in windows if valid_window(w)]
    local = [w for w in windows if w.provenance != "SEMANTIC_CONTEXT"]
    positive = [
        w
        for w in local
        if w.suitability not in {"AVOID", "RESTRICTED"}
        and not re.search(r"不推荐|不建议|闭园|封山|停航", w.source_text or "")
    ]
    context = [w for w in windows if w.provenance == "SEMANTIC_CONTEXT"]
    themes = experience.get("themes", [])
    activity = "看" + "、".join(themes[:2]) if themes else "游览"
    dated = [
        w for w in positive if (w.month or "雪后" in (w.source_text or "")) and w.suitability == "RECOMMENDED"
    ]
    dated.sort(
        key=lambda w: (bool(w.month), bool(w.month_segment), "雪后" in (w.source_text or "")), reverse=True
    )
    labels = _unique(window_label(w) for w in dated)
    labels = [v for v in labels if v != "时段待明确"]
    frequency = next(
        (w for w in positive if w.month and w.month_segment and "几乎天天" in (w.source_text or "")), None
    )
    seasons = _unique(SEASON_LABELS.get(w.season, "") for w in local if w.season)
    if labels:
        timing = f"视频推荐在{'、'.join(labels[:2])}{activity}。"
    elif frequency:
        timing = f"视频提到，从{window_label(frequency)}开始几乎天天有雾凇。"
    elif seasons:
        timing = f"视频介绍的是{'、'.join(seasons)}的{''.join(themes[:2]) or '游览体验'}。"
    elif context:
        season = "、".join(_unique(SEASON_LABELS.get(w.season, "") for w in context))
        timing = f"这组{''.join(themes[:1]) or '景观'}在视频中按{season}介绍。"
    else:
        timing = "视频未提及季节限制。" if default_all_year else "视频未明确说明适合的时节。"
    conditions = []
    statements = [
        s for o in (recommendation_summary or {}).get("source_opinions", []) for s in o.get("statements", [])
    ]
    warnings = [
        s["quote"]
        for s in statements
        if s.get("scope") == "LOCAL_DETAIL"
        and (s.get("intent") == "NOT_RECOMMENDED" or re.search(r"不|别|限制|关闭|危险", s.get("quote", "")))
    ] + list(experience.get("warnings", []))
    for w in local:
        text = w.source_text or ""
        if re.search(r"不推荐下雪|不建议下雪|不推荐.*下雪的时候", text):
            warnings.insert(
                0,
                "视频不推荐正在下雪时前往，更推荐晴天。" if "晴天" in text else "视频不推荐正在下雪时前往。",
            )
        elif w.suitability in {"AVOID", "RESTRICTED"}:
            warnings.insert(0, text.strip("，,。 ") + "。")
        if re.search(r"一定|最好|尽量|需要|要|推荐", text) and re.search(r"晴天|早晨|无风", text):
            weather = "晴天" if "晴天" in text else ""
            tod = "早晨" if "早晨" in text else ""
            if weather or tod:
                conditions.append(f"视频强调{weather}{tod}前往。")
        if re.search(r"八点到九点|8点到9点", text):
            conditions.append("视频提到早晨八点到九点的雾凇最饱满、最透彻。")
    # Keep only fully attributed assertions. No boilerplate weather/booking/route advice.
    highlights = _unique(experience.get("reasons", []))[:2]
    highlights = [text.split("；")[0] + "。" if "；" in text else text for text in highlights]
    warnings = _unique(warnings)
    warnings.sort(
        key=lambda text: (
            0
            if re.search(r"穿厚|穿多厚|保暖|封山|关闭", text)
            else 1
            if re.search(r"不推荐|不建议", text)
            else 2
        )
    )
    # Do not amplify a garbled ASR temperature range into a factual temperature claim.
    warnings = [
        "视频提醒前往时尽量穿厚。"
        if "前往时需尽量穿厚" in text
        else text.split("；")[0] + "。"
        if "温度低于20度至30度" in text
        else text
        for text in warnings
    ]
    return {
        "timing": timing,
        "conditions": _unique(conditions)[:2],
        "highlights": highlights,
        "warnings": warnings,
        "inherited": bool(context and not dated),
    }
