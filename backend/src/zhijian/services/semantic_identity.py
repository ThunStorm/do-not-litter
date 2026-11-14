"""Conservative identity repair for a place introduction split across map requests."""

from __future__ import annotations

import re
from hashlib import sha256
from os.path import commonprefix


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


def guard_shared_segment_scope(entities, units, claims, texts):
    """Quarantine a uniquely located quote before its subject's explicit introduction.

    A shared Segment is not proof that its opening clause belongs to the next place.
    Keep uncertain source words unassigned; never guess the preceding owner.
    """
    by_id = {e["entity_id"]: e for e in entities}
    warnings, preserved = [], set()

    def before_intro(entity, item, quote):
        ids = item.get("segment_ids", [])
        name = "".join(str(entity.get("raw_name") or "").split())
        quote = "".join(str(quote or "").split())
        if len(ids) != 1 or not quote or not name or name in quote:
            return False
        if entity.get("subject_role") != "PRIMARY" or name not in str(entity.get("quote", "")):
            return False
        text = "".join(texts.get(ids[0], "").split())
        starts = [m.start() for m in re.finditer(re.escape(quote), text)]
        if len(starts) != 1:
            return False
        for transition in _TRANSITION.finditer(text):
            name_at = text.find(name, transition.end())
            if 0 <= name_at - transition.end() <= 12 and starts[0] + len(quote) <= transition.start():
                return True
        return False

    def quarantine(item, quote):
        ids = list(item.get("segment_ids", []))
        key = (tuple(ids), quote)
        review_id = "source-review-" + sha256(str(key).encode()).hexdigest()[:20]
        if key not in preserved:
            units.append(
                {
                    "content_unit_id": review_id,
                    "unit_type": "SUPPLEMENTAL",
                    "topic": "归属待核的原文",
                    "anchor_entity_ids": [],
                    "segment_ids": ids,
                }
            )
            preserved.add(key)
        item.update(
            content_unit_id=review_id,
            subject_entity_ids=[],
            text=quote,
            supporting_quote=quote,
            attribution_status="NEEDS_REVIEW",
        )
        warnings.append("归属待核：转场前原句未绑定到后续地点：" + quote[:160])

    for claim in claims:
        quote = claim.get("supporting_quote", "")
        if any(
            before_intro(by_id[sid], claim, quote)
            for sid in claim.get("subject_entity_ids", [])
            if sid in by_id
        ):
            quarantine(claim, quote)
    for entity in entities:
        evidence = entity.get("recommendation_evidence")
        if not isinstance(evidence, dict) or not isinstance(evidence.get("statements"), list):
            continue
        valid, rejected = [], set()
        for statement in evidence["statements"]:
            quote = statement.get("quote", "") if isinstance(statement, dict) else ""
            if not isinstance(statement, dict) or not before_intro(entity, statement, quote):
                valid.append(statement)
                continue
            rejected.add(statement.get("statement_id"))
            if (tuple(statement.get("segment_ids", [])), quote) not in preserved:
                claim = {
                    "claim_id": "review-" + str(statement.get("statement_id", "")),
                    "claim_type": "OTHER",
                    "importance": "MEDIUM",
                    "segment_ids": list(statement.get("segment_ids", [])),
                }
                quarantine(claim, quote)
                claims.append(claim)
        if rejected:
            for statement in valid:
                if isinstance(statement, dict):
                    statement["supersedes"] = [
                        s for s in statement.get("supersedes", []) if s not in rejected
                    ]
            entity["recommendation_evidence"] = {**evidence, "statements": valid}
            if not valid:
                entity.update(visit_intent="NEUTRAL", poi_policy="SKIP")
    return warnings


def region_name_forms(entity):
    names = {str(entity.get(key) or "") for key in ("raw_name", "canonical_hint", "name")}
    forms = names | {_REGION_PREFIX.sub("", name) for name in names}
    return {name.removesuffix("市").removesuffix("镇") for name in forms if len(name) >= 2}


def _regional_anchor(entity):
    return (
        entity
        and entity.get("subject_role") == "PRIMARY"
        and (
            entity.get("entity_type") == "AREA"
            or entity.get("place_type") in {"AREA", "CITY", "TOWN", "SCENIC_AREA"}
        )
    )


def _shared_scenic_intro(left, right, text):
    """A scenic identity needs the same unique, literal introduction, not equal names alone."""
    names = [str(e.get("raw_name") or "") for e in (left, right)]
    if not all(names) or not (names[0].endswith(names[1]) or names[1].endswith(names[0])):
        return False
    prefix = commonprefix(["".join(str(e.get("quote") or "").split()) for e in (left, right)])
    source = "".join(text.split())
    return bool(
        prefix
        and source.count(prefix) == 1
        and _TRANSITION.search(prefix)
        and any(name in prefix for name in region_name_forms(left) & region_name_forms(right))
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
        and (
            u.get("unit_type") in {"AREA_GUIDE", "PLACE_GUIDE"}
            or u.get("unit_type_omitted")
            or (
                u.get("unit_type") == "MULTI_PLACE_LIST"
                and by_id.get(u["anchor_entity_ids"][0], {}).get("place_type") == "SCENIC_AREA"
            )
        )
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
                a.get("place_type") != "SCENIC_AREA"
                and right.get("unit_type_omitted")
                and shared
                and _TRANSITION.search(texts[boundary])
                and any(right.get("topic", "").startswith(name) and name in texts[boundary] for name in forms)
            ):
                aliases[bid] = aliases.get(aid, aid)
            continue
        if not _regional_anchor(b):
            continue
        scenic = any(e.get("place_type") == "SCENIC_AREA" for e in (a, b))
        if scenic and not (
            all(e.get("place_type") == "SCENIC_AREA" for e in (a, b))
            and shared
            and boundary in b["segment_ids"]
            and _shared_scenic_intro(a, b, texts[boundary])
        ):
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
                "version": "adjacent-scenic-introduction-v1"
                if item.get("place_type") == "SCENIC_AREA"
                else "adjacent-area-introduction-v1",
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
                {"reading_derivation": "shared-scenic-introduction"}
                if any(
                    e["entity_id"] in [aliases.get(a, a) for a in u.get("anchor_entity_ids", [])]
                    and u["content_unit_id"]
                    in (e.get("identity_derivation") or {}).get("content_unit_ids", [])
                    and (e.get("identity_derivation") or {}).get("version")
                    == "adjacent-scenic-introduction-v1"
                    for e in result
                )
                else {}
            ),
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


def resolve_review_claims_from_source(entities, units, claims, segments):
    """Resolve only an exact existing opinion with a uniquely named preceding source.

    This is not nearest-place assignment: both the same quote/IDs and an independently
    named preceding Segment inside the same guide are required.
    """
    order = {s.id: i for i, s in enumerate(segments)}
    text = {s.id: str(s.corrected_text or s.text) for s in segments}
    primary = [e for e in entities if e.get("subject_role") == "PRIMARY"]
    for claim in claims:
        ids = claim.get("segment_ids", [])
        if claim.get("attribution_status") != "NEEDS_REVIEW" or len(ids) != 1:
            continue
        index = order.get(ids[0], 0)
        if not index:
            continue
        previous = segments[index - 1].id
        named = [e for e in primary if any(name in text[previous] for name in region_name_forms(e))]
        if len(named) != 1:
            continue
        owner = named[0]
        guides = [
            u
            for u in units
            if u.get("anchor_entity_ids") == [owner["entity_id"]]
            and {previous, ids[0]} <= set(u.get("segment_ids", []))
            and u.get("unit_type") in {"PLACE_GUIDE", "AREA_GUIDE", "MULTI_PLACE_LIST"}
        ]
        statements = [
            s
            for s in (owner.get("recommendation_evidence") or {}).get("statements", [])
            if isinstance(s, dict)
            and s.get("speaker") == "AUTHOR"
            and s.get("subject_entity_id") == owner["entity_id"]
            and s.get("segment_ids") == ids
            and "".join(str(s.get("quote", "")).split())
            == "".join(str(claim.get("supporting_quote", "")).split())
        ]
        if len(guides) != 1 or not statements:
            continue
        claim.update(
            subject_entity_ids=[owner["entity_id"]],
            content_unit_id=guides[0]["content_unit_id"],
            attribution_status="RESOLVED_FROM_SOURCE",
            attribution_derivation={
                "version": "exact-opinion-and-named-previous-source-v1",
                "previous_segment_id": previous,
                "statement_ids": [s["statement_id"] for s in statements],
            },
        )
