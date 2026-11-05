"""Conservative identity repair for a place introduction split across map requests."""

from __future__ import annotations

import re


def topic_chunks(segments, split):
    """Prefer explicit speaker topic transitions; share the original boundary Segment."""
    groups = []
    start = 0
    for index, segment in enumerate(segments):
        text = str(segment.corrected_text or segment.text)
        if index - start > 3 and re.search(r"接下来|最后一个|第[二三四五六七八九十]个", text):
            groups.append(segments[start : index + 1])
            start = index
    if start < len(segments):
        groups.append(segments[start:])
    return [chunk for group in groups for chunk in split(group)]


_REGION_PREFIX = re.compile(r"^(?:西藏|云南|广西|贵州|四川|广东|新疆|内蒙古)(?=.{2,})")
_TRANSITION = re.compile(r"接下来|最后一个|第[二三四五六七八九十]个")


def region_name_forms(entity):
    names = {str(entity.get(key) or "") for key in ("raw_name", "canonical_hint", "name")}
    forms = names | {_REGION_PREFIX.sub("", name) for name in names}
    return {name.removesuffix("市").removesuffix("镇") for name in forms if len(name) >= 2}


def _regional_anchor(entity):
    return (
        entity
        and entity.get("subject_role") == "PRIMARY"
        and (entity.get("entity_type") == "AREA" or entity.get("place_type") in {"AREA", "CITY", "TOWN"})
    )


def join_boundary_entities(entities, units, claims, relations, segments):
    """Use shared introductions to reconcile region guides without changing source IDs."""
    order = {s.id: i for i, s in enumerate(segments)}
    texts = {s.id: str(s.corrected_text or s.text) for s in segments}
    by_id = {e["entity_id"]: e for e in entities}
    aliases = {}
    guides = [
        dict(u)
        for u in units
        if len(u.get("anchor_entity_ids", [])) == 1
        and (u.get("unit_type") in {"AREA_GUIDE", "PLACE_GUIDE"} or u.get("unit_type_omitted"))
        and u.get("segment_ids")
        and set(u["segment_ids"]) <= order.keys()
    ]
    guides.sort(key=lambda u: (order[u["segment_ids"][0]], order[u["segment_ids"][-1]], u["content_unit_id"]))
    for left, right in zip(guides, guides[1:], strict=False):
        aid, bid = left["anchor_entity_ids"][0], right["anchor_entity_ids"][0]
        a, b = by_id.get(aid), by_id.get(bid)
        if aid == bid or not _regional_anchor(a):
            continue
        ls, rs = left["segment_ids"], right["segment_ids"]
        boundary = rs[0]
        shared = boundary in a["segment_ids"] and boundary in ls
        forms = region_name_forms(a)
        if b is None:
            # A rejected entity contributes no quote. Its omitted-type unit can continue an
            # explicitly named introduction already verified in this same boundary segment.
            if (
                right.get("unit_type_omitted")
                and shared
                and _TRANSITION.search(texts[boundary])
                and any(right.get("topic", "").startswith(name) and name in texts[boundary] for name in forms)
            ):
                aliases[bid] = aliases.get(aid, aid)
            continue
        if not _regional_anchor(b):
            continue
        if any(a.get(k) and b.get(k) and a[k] != b[k] for k in ("city_hint", "province_hint")):
            continue
        prefixes = [_REGION_PREFIX.match(str(e.get("raw_name") or "")) for e in (a, b)]
        if all(prefixes) and prefixes[0].group() != prefixes[1].group():
            continue
        common = forms & region_name_forms(b)
        if not common:
            continue
        tail, head = texts[ls[-1]].strip(), texts[boundary].strip()
        continuation = (
            len(ls) <= 2
            and order[ls[-1]] + 1 == order[boundary]
            and tail
            and tail[-1] not in "。！？.!?；;"
            and re.match(r"^(?:定|是|的|了|时候|月份|间|度)", head)
        )
        shared_intro = shared and boundary in b["segment_ids"] and _TRANSITION.search(texts[boundary])
        if not (shared_intro or continuation):
            continue
        if not any(all(name in str(e.get("quote", "")) for e in (a, b)) for name in common):
            continue
        aliases[aid] = bid
    for entity_id in list(aliases):
        target = aliases[entity_id]
        while target in aliases:
            target = aliases[target]
        aliases[entity_id] = target
    if not aliases:
        return entities, units, claims, relations
    groups = {}
    for entity in entities:
        key = aliases.get(entity["entity_id"], entity["entity_id"])
        groups.setdefault(key, []).append(entity)
    result = []
    for key, members in groups.items():
        members.sort(key=lambda e: min((order[s] for s in e["segment_ids"]), default=10**9))
        item = dict(by_id[key])
        if len(members) > 1 or key in aliases.values():
            item["identity_derivation"] = {
                "version": "adjacent-area-introduction-v1",
                "entity_ids": list(
                    dict.fromkeys(
                        [e["entity_id"] for e in members] + [a for a in aliases if aliases[a] == key]
                    )
                ),
                "content_unit_ids": [e["content_unit_id"] for e in members],
            }
            item["segment_ids"] = sorted({s for e in members for s in e["segment_ids"]}, key=order.get)
            item["aliases"] = list(dict.fromkeys(e["raw_name"] for e in members))
            item["recommendation_evidence"] = {
                "schema_version": "recommendation-v1",
                "statements": [
                    {**s, "subject_entity_id": key}
                    for e in members
                    for s in (e.get("recommendation_evidence") or {}).get("statements", [])
                ],
            }
            item["temporal_applications"] = [v for e in members for v in e.get("temporal_applications", [])]
        result.append(item)
    units = [
        {
            **u,
            **(
                {"unit_type": "AREA_GUIDE", "reading_derivation": "shared-source-introduction"}
                if u.get("unit_type_omitted")
                and any(e in aliases or e in aliases.values() for e in u.get("anchor_entity_ids", []))
                else {}
            ),
            "anchor_entity_ids": list(
                dict.fromkeys(aliases.get(e, e) for e in u.get("anchor_entity_ids", []))
            ),
        }
        for u in units
    ]
    claims = [
        {
            **c,
            "subject_entity_ids": list(
                dict.fromkeys(aliases.get(e, e) for e in c.get("subject_entity_ids", []))
            ),
        }
        for c in claims
    ]
    relations = [
        {**r, **{k: aliases.get(r[k], r[k]) for k in ("source_entity_id", "target_entity_id")}}
        for r in relations
    ]
    return result, units, claims, relations
