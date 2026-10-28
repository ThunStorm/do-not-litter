"""Deterministic recovery for evidenced prose routes when a model omits route objects.

Only explicit transport/route grammar is interpreted; unknown nodes remain raw and reviewed.
"""

from __future__ import annotations

import re

HAN = r"[\u4e00-\u9fff]"


def _nodes(value, names):
    value = re.split(r"可以|两个古城|而且|铺装路|弯道|这个体|运气|就够了|这一段", value, maxsplit=1)[0]
    parts = re.split(r"[、，,→]|途经|经由|做到|到|北上|南下", value)
    result = []
    for part in parts:
        part = re.sub(r"^(?:从|一路从|推荐走|建议走|途经|走)", "", part).strip()
        part = re.split(r"出发|可以连成|就够了|这一段|两个古城|运气|铺装路|这个体|谁走", part)[0]
        if not part:
            continue
        # Split concatenated known and unknown place words without canonicalizing either.
        hits = sorted((part.find(name), -len(name), name) for name in names if name in part)
        cursor = 0
        for start, _, name in hits:
            if start < cursor:
                continue
            prefix = part[cursor:start]
            if re.fullmatch(HAN + r"{2,12}", prefix):
                result.append(prefix)
            result.append(name)
            cursor = start + len(name)
        tail = part[cursor:]
        if re.fullmatch(HAN + r"{2,12}", tail):
            result.append(tail)
    return list(dict.fromkeys(result))


def recover_route(claim, texts, entities):
    quote = str(claim.get("supporting_quote") or "")
    if not re.search(r"路线|环线|骑行|米轨|火车|环湖自驾|自驾.*走|全程自驾|出发.*途经|G\d+.*从", quote):
        return None
    ids = list(claim.get("segment_ids") or [])
    if not ids or any(sid not in texts for sid in ids):
        return None
    # A quote may omit the transport heading present in exactly its owned, contiguous segments.
    full = "".join(texts[sid] for sid in ids)
    mode = next(
        (
            code
            for pattern, code in (
                (r"骑行|骑车", "CYCLING"),
                (r"火车|米轨|铁路", "RAIL"),
                (r"吃货|美食", "FOOD_THEME"),
                (r"自驾|包车", "SELF_DRIVE"),
            )
            if re.search(pattern, quote)
        ),
        None,
    )
    if not mode and re.search(r"G\d+[^。]{0,15}自驾", full):
        quote, mode = full, "SELF_DRIVE"
    if not mode:
        return None
    names = {str(e.get("raw_name") or "") for e in entities} - {""}
    road = next(iter(re.findall(r"(?:[GS]\d{2,4}|S[一二三四五六七八九十幺]+)", quote)), "")
    span = None
    if match := re.search(r"(" + HAN + r"{2,12})出发[，,]?途经([^。]+)", quote):
        span = match[1] + "、" + match[2]
    elif "从" in quote and re.search(r"到|途经", quote):
        span = quote.rsplit("从", 1)[1].split("。", 1)[0]
    elif match := re.search(r"(?:推荐走|建议走)([^。]+)", quote):
        span = match[1]
    elif mode == "FOOD_THEME" and "主要是" in quote:
        span = quote.split("主要是", 1)[1].split("这几个", 1)[0]
    elif mode == "SELF_DRIVE" and "连成" in quote and "到" in quote:
        span = quote.split("的话", 1)[-1].split("连成", 1)[0]
    stops = _nodes(span, names) if span else []
    kind = (
        "EXPLICIT_LIST"
        if mode == "FOOD_THEME"
        else "PARTIAL_SEQUENCE"
        if "连成" in quote
        else "EXPLICIT_SEQUENCE"
    )
    if len(stops) < 2:
        stops = []
        kind = "UNORDERED_LOOP" if "环湖自驾" in quote else "CORRIDOR_ONLY"
    if not stops:
        if mode == "RAIL" or mode == "FOOD_THEME":
            return None  # An isolated train mention is not an itinerary.
        subject = road or next(iter(re.findall(r"[东西南北]线", quote)), "")
        if not subject:
            subject = next((name for name in sorted(names, key=len, reverse=True) if name in quote), "")
    else:
        subject = road or stops[0]
    if not subject:
        return None
    return {
        "name": subject + " · 来源路线",
        "subject": subject,
        "mode": mode,
        "sequence_kind": kind,
        "stops": stops,
        "road": road,
        "recovered_from_prose": True,
    }, {**claim, "supporting_quote": quote}


def explicit_route_lists(texts):
    """Recover children of an explicit transport heading, never an arbitrary place enumeration."""
    text = "".join(texts.values())
    offsets, start = [], 0
    for sid, value in texts.items():
        offsets.append((start, start + len(value), sid))
        start += len(value)
    for heading in re.finditer(r"自驾[^。]{0,12}推荐[一二三四五六七八九十两\d]+条路线[：:]", text):
        end = min(heading.end() + 350, len(text))
        tail = text[heading.end() : end]
        stop = re.search(r"然后是一个|吃货|美食|如果你", tail)
        if stop:
            tail = tail[: stop.start()]
        matches = list(re.finditer(r"首先是|然后是|最后一个就是|其次是", tail))
        for i, marker in enumerate(matches):
            part = tail[marker.end() : matches[i + 1].start() if i + 1 < len(matches) else len(tail)]
            if not re.search(r"路线|环线", part):
                continue
            road = next(iter(re.findall(r"[GS]\d{2,4}", part)), "")
            if "串联" in part:
                nodes = part.split("串联", 1)[1].split("。", 1)[0]
                kind = "PARTIAL_SEQUENCE"
            else:
                pieces = re.split(r"[，,：:]", part, maxsplit=1)
                if len(pieces) < 2:
                    continue
                nodes = pieces[1].split("。", 1)[0]
                kind = "EXPLICIT_LIST"
            stops = _nodes(nodes, set())
            if len(stops) < 2:
                continue
            quote_end = heading.end() + (matches[i + 1].start() if i + 1 < len(matches) else len(tail))
            quote = text[heading.start() : quote_end]
            ids = [sid for a, b, sid in offsets if a < quote_end and b > heading.start()]
            subject = road or re.split(r"[：:，,]", part)[0].strip()
            yield (
                {
                    "name": subject + " · 来源路线",
                    "subject": subject,
                    "mode": "SELF_DRIVE",
                    "sequence_kind": kind,
                    "stops": stops,
                    "road": road,
                    "recovered_from_prose": True,
                },
                {"supporting_quote": quote, "segment_ids": ids},
            )
