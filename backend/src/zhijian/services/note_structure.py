"""Evidence-preserving organization shared by generation and historical read views."""

from __future__ import annotations

import re
from typing import Any

PLACE_KINDS = {"PLACE", "PLACE_GUIDE", "AREA_GUIDE"}
COMPARISON_KINDS = {"CATEGORY_COMPARE", "MULTI_PLACE_LIST", "ROUTE", "MIXED"}


def _unique(values: list) -> list:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _identity(mention: Any) -> str:
    return str(
        mention.place_id or (mention.metadata_json or {}).get("semantic", {}).get("entity_id") or mention.id
    )


def _legacy_scopes(sections: list[dict], known: dict[str, Any], segments: list[Any]) -> dict[int, list[str]]:
    order = {s.id: i for i, s in enumerate(segments)}
    texts = {s.id: str(s.corrected_text or s.text) for s in segments}
    anchors = []
    for section in sections:
        mids = [mid for mid in section.get("place_mention_ids", []) if mid in known]
        positions = [order[sid] for sid in section.get("segment_ids", []) if sid in order]
        if (
            section.get("section_kind") in PLACE_KINDS
            and positions
            and len({_identity(known[mid]) for mid in mids}) == 1
        ):
            anchors.append((min(positions), _identity(known[mids[0]])))
    anchors.sort()
    result = {}
    for index, section in enumerate(sections):
        ids = section.get("segment_ids", [])
        if (
            section.get("place_mention_ids")
            or section.get("section_kind") not in PLACE_KINDS
            or not ids
            or not set(ids) <= set(order)
        ):
            continue
        candidates = [
            mid
            for mid, mention in known.items()
            if str(section.get("heading") or "").startswith(mention.name)
        ]
        if len({_identity(known[mid]) for mid in candidates}) != 1:
            continue
        identity = _identity(known[candidates[0]])
        start, end = min(order[sid] for sid in ids), max(order[sid] for sid in ids)
        preceding = [a for a in anchors if a[0] <= start]
        following = [a[0] for a in anchors if a[0] > start and a[1] != identity]
        quotes = section.get("evidence_quotes") or section.get("supporting_quotes") or []
        evidence = re.sub(r"\s+", "", "".join(texts[sid] for sid in ids))
        if (
            preceding
            and preceding[-1][1] == identity
            and (not following or end < min(following))
            and quotes
            and all(re.sub(r"\s+", "", str(q)) in evidence for q in quotes)
        ):
            result[index] = candidates
    return result


def organize_sections(
    sections: list[dict],
    mentions: list[Any],
    facts: list[dict] | None = None,
    *,
    segments: list[Any] | None = None,
    legacy: bool = False,
    content_units: list[dict] | None = None,
) -> list[dict]:
    """Never guess a place from a heading or a shared segment. Keep comparisons independent."""
    known = {
        m.id: m
        for m in mentions
        if m.extraction_status not in {"USER_REJECTED", "SUPERSEDED"}
        and m.poi_policy not in {"REFERENCE_ONLY", "SKIP"}
    }
    entity_mentions = {
        (m.metadata_json or {}).get("semantic", {}).get("entity_id"): mid for mid, m in known.items()
    }
    unit_roots = {}
    unit_segments = {}
    for unit in content_units or []:
        anchors = [entity_mentions[e] for e in unit.get("anchor_entity_ids", []) if e in entity_mentions]
        if (
            unit.get("unit_type") not in PLACE_KINDS
            or len(unit.get("anchor_entity_ids", [])) != 1 or len(anchors) != 1
        ):
            continue
        uid = unit["content_unit_id"]
        unit_roots[uid] = anchors[0]
        unit_segments[uid] = set(unit.get("segment_ids", []))
    scopes: dict[str, set[str]] = {}
    for fact in facts or []:
        ids = [i for i in fact.get("place_mention_ids", []) if i in known]
        if len({_identity(known[i]) for i in ids}) == 1:
            for mid in ids:
                scopes.setdefault(mid, set()).update(fact.get("segment_ids", []))
    legacy_scopes = _legacy_scopes(sections, known, segments or []) if legacy else {}
    groups: dict[tuple, list[dict]] = {}
    names: dict[tuple, str] = {}
    for index, section in enumerate(sections):
        item = dict(section)
        ids = [i for i in item.get("place_mention_ids", []) if i in known]
        kind = item.get("section_kind") or item.get("unit_type") or "SUPPLEMENTAL"
        evidence = set(item.get("segment_ids", []))
        if not ids and kind in PLACE_KINDS and evidence:
            candidates = [mid for mid, covered in scopes.items() if evidence <= covered]
            if len({_identity(known[mid]) for mid in candidates}) == 1:
                ids = candidates
                item["place_mention_ids"] = ids
        if not ids and index in legacy_scopes:
            ids = legacy_scopes[index]
            item["organization_basis"] = "具名标题、相邻已绑定地点章节与逐字来源区间一致；仅阅读归组"
        identities = {_identity(known[mid]) for mid in ids}
        roots = {
            unit_roots.get(getattr(known[mid], "content_unit_id", ""), mid) for mid in ids
        }
        rooted = [
            root for uid, root in unit_roots.items()
            if evidence and evidence <= unit_segments[uid] and (not roots or roots == {root})
        ]
        within_destination = bool(ids) and roots == set(rooted)
        if len(set(rooted)) == 1 and (
            kind not in COMPARISON_KINDS
            or (within_destination and kind in {"CATEGORY_COMPARE", "MULTI_PLACE_LIST"})
        ):
            root = rooted[0]
            key = ("PLACE", _identity(known[root]))
            names[key] = known[root].name
            item["reading_parent_mention_id"] = root
        elif kind in PLACE_KINDS and len(identities) == 1:
            key = ("PLACE", next(iter(identities)))
            names[key] = known[ids[0]].name
        else:
            # A comparison is not distributed to every mentioned destination.
            key = ("OTHER", index)
        groups.setdefault(key, []).append(item)
    result = []
    for key, members in groups.items():
        first = members[0]
        merged = dict(first)
        if key[0] == "PLACE":
            merged["heading"] = names[key]
            merged["section_kind"] = "PLACE_GUIDE"
        bodies = []
        all_quotes = [
            line[2:].strip() for item in members
            for line in str(item.get("body_markdown", "")).splitlines() if line.startswith("> ")
        ]
        seen_quotes = set()
        seen_bullets = set()
        seen_labels = set()
        review_labels = {
            "作者意见或归纳待核对，以原文为准：", "以下原文尚未形成完整归纳：",
            "作者意见与条件原文：", "作者原文（保留意见、条件与局部限制）：",
            "以下来源片段可能含尚未归纳的限制：",
        }
        for item in members:
            body = str(item.get("body_markdown") or item.get("summary") or "").strip()
            lines = []
            for line in body.splitlines():
                if line.startswith("- "):
                    bullet = re.sub(r"\s+", "", line[2:])
                    if bullet in seen_bullets:
                        continue
                    seen_bullets.add(bullet)
                if line.startswith("> "):
                    quote = re.sub(r"\s+", "", line[2:])
                    if quote in seen_quotes or any(
                        quote != re.sub(r"\s+", "", other) and quote in re.sub(r"\s+", "", other)
                        for other in all_quotes
                    ):
                        continue
                    seen_quotes.add(quote)
                lines.append(line)
            cleaned = []
            for index, line in enumerate(lines):
                if line in review_labels:
                    following = next((v for v in lines[index + 1:] if v.strip()), "")
                    if line in seen_labels or not following.startswith("> "):
                        continue
                    seen_labels.add(line)
                cleaned.append(line)
            body = "\n".join(cleaned).strip()
            if not body and item.get("bullets"):
                body = "\n".join(f"- {v}" for v in item["bullets"])
            extra = [
                str(v)
                for v in item.get("bullets", [])
                if str(v).strip() and re.sub(r"\s+", "", str(v)) not in re.sub(r"\s+", "", body)
            ]
            if extra:
                body = body + "\n\n" + "\n".join("- " + v for v in extra)
            if body and body not in [b[1] for b in bodies]:
                heading = str(item.get("heading") or "")
                if key[0] == "PLACE" and (heading == names[key] or heading == "待归纳的证据要点"):
                    heading = ""
                bodies.append((heading, body))
        merged["body_markdown"] = "\n\n".join(
            (f"### {heading}\n\n" if len(bodies) > 1 and heading else "") + body for heading, body in bodies
        )
        for field in ["segment_ids", "place_mention_ids", "supporting_quotes", "evidence_quotes", "bullets"]:
            merged[field] = _unique([value for item in members for value in item.get(field, [])])
        merged["source_section_ids"] = _unique(
            [sid for item in members for sid in item.get("source_section_ids", [item.get("id")])]
        )
        merged["source_ranges"] = _unique(
            [
                r
                for item in members
                for r in item.get(
                    "source_ranges", [{"start_ms": item.get("start_ms"), "end_ms": item.get("end_ms")}]
                )
                if r.get("start_ms") is not None
            ]
        )
        starts = [item.get("start_ms") for item in members if item.get("start_ms") is not None]
        ends = [item.get("end_ms") for item in members if item.get("end_ms") is not None]
        if starts:
            merged["start_ms"] = min(starts)
        if ends:
            merged["end_ms"] = max(ends)
        result.append(merged)
    # Destination chapters first; independent comparisons/topics follow, stable within each set.
    return sorted(result, key=lambda item: (
        0 if item.get("section_kind") in PLACE_KINDS else 1, item.get("start_ms") or 0
    ))


def structured_overview(sections: list[dict], fallback: str, limit: int = 300) -> str:
    if not sections:
        return fallback
    parts = []
    for section in sections:
        thesis = str(section.get("thesis") or section.get("summary") or "").strip()
        if not thesis:
            continue
        if any(marker in thesis for marker in ("待核对", "待归纳", "本包", "本段", "见原文")):
            continue
        # Keep complete source-derived sentences and avoid exposing package scaffolding.
        sentence = re.split(r"(?<=[。！？])", thesis)[0]
        text = (
            f"{section.get('heading', '')}：{sentence}"
            if section.get("section_kind") in PLACE_KINDS
            else sentence
        )
        if len(" ".join([*parts, text])) > limit:
            break
        if text not in parts:
            parts.append(text)
    if len(parts) < len(sections) and parts:
        parts.append(f"其余内容见下方{len(sections)}个地点与主题章节。")
    if parts:
        return " ".join(parts)
    names = _unique([s.get("heading") for s in sections if s.get("section_kind") in PLACE_KINDS])
    return ("内容涉及" + "、".join(names) + "；具体信息与待核对事项见下文。") if names else fallback


def destination_overview(sections):
    names = _unique([s.get("heading") for s in sections if s.get("section_kind") in PLACE_KINDS])
    if names:
        return "视频介绍了" + "、".join(names) + "的看点与出行条件。正文按目的地整理，附有原文与待核对事项。"
    return "视频要点和相关来源见下文。"
