"""Evidence-preserving organization shared by generation and historical read views."""

from __future__ import annotations

import re
from typing import Any

PLACE_KINDS = {"PLACE", "PLACE_GUIDE"}
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
) -> list[dict]:
    """Never guess a place from a heading or a shared segment. Keep comparisons independent."""
    known = {
        m.id: m
        for m in mentions
        if m.extraction_status not in {"USER_REJECTED", "SUPERSEDED"}
        and m.poi_policy not in {"REFERENCE_ONLY", "SKIP"}
    }
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
        if kind in PLACE_KINDS and len(identities) == 1:
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
        bodies = []
        for item in members:
            body = str(item.get("body_markdown") or item.get("summary") or "").strip()
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
                bodies.append((str(item.get("heading") or ""), body))
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
    return sorted(result, key=lambda item: 0 if item.get("section_kind") in PLACE_KINDS else 1)


def structured_overview(sections: list[dict], fallback: str, limit: int = 300) -> str:
    if not sections:
        return fallback
    parts = []
    for section in sections:
        thesis = str(section.get("thesis") or section.get("summary") or "").strip()
        if not thesis:
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
        parts.append(text)
    if len(parts) < len(sections) and parts:
        parts.append(f"其余内容见下方{len(sections)}个地点与主题章节。")
    return " ".join(parts) if parts else fallback
