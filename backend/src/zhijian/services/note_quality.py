"""Read-only, version-scoped quality diagnostics. No model or database writes."""

from __future__ import annotations

import re

VERSION = "note-quality-v1"
RISK = re.compile(r"灌水|(?:没有房|没房)|(?:开渔节|元旦)|不建议|不推荐|积雪|结冰|人多价格高|不要门票|免费")


def norm(value):
    return re.sub(r"\s+", "", str(value))


def safe_note_prose(text, quotes, split_months):
    evidence = norm("".join(quotes))
    if any(re.search(rf"(?<!十){month}月份?", text) for month in split_months):
        return False
    return all(phrase not in text or phrase in evidence for phrase in ("评为", "列为", "认证"))


def clean_note_prose(text):
    marker = r"已验证(?:RECOMMENDED|推荐)"
    return re.sub(rf"[（(](?:s\d+(?:[、，,]s\d+)*(?:[，,]\s*{marker})?|{marker})[)）]", "", text)


def source_gaps(segments, claims, units, *, sections=None):
    """Flag untranslated source risks; this never creates a verified semantic Claim."""
    result = []
    texts = {s.id: str(s.corrected_text or s.text) for s in segments}
    quote_ranges = {}
    source_evidence = list(claims)
    for section in sections or []:
        if section.get("section_kind") == "SOURCE_REVIEW":
            continue  # Pending fallback evidence cannot clear its own warning.
        for quote in (section.get("supporting_quotes") or section.get("evidence_quotes") or []):
            source_evidence.append({"segment_ids": section.get("segment_ids", []), "supporting_quote": quote})
    for claim in source_evidence:
        ids = claim.get("segment_ids", [])
        quote = norm(claim.get("supporting_quote", ""))
        if not quote or not ids or not set(ids) <= texts.keys():
            continue
        source = "".join(norm(texts[sid]) for sid in ids)
        ranges = [(m.start(), m.end()) for m in re.finditer(re.escape(quote), source)]
        offset = 0
        for sid in ids:
            quote_ranges.setdefault(sid, []).extend((left - offset, right - offset) for left, right in ranges)
            offset += len(norm(texts[sid]))
    for index, segment in enumerate(segments):
        text = texts[segment.id]
        for match in RISK.finditer(text):
            start, end = len(norm(text[: match.start()])), len(norm(text[: match.end()]))
            if any(left <= start and end <= right for left, right in quote_ranges.get(segment.id, [])):
                continue
            owners = [u for u in units if segment.id in u.get("segment_ids", [])]
            refs = [segment]
            if (
                index
                and match.start() < 20
                and not texts[segments[index - 1].id].endswith(("。", "！", "？", ".", "!", "?"))
            ):
                refs.insert(0, segments[index - 1])
            if (
                index + 1 < len(segments)
                and match.end() > len(text) - 30
                and not text.endswith(("。", "！", "？", ".", "!", "?"))
            ):
                refs.append(segments[index + 1])
            result.append(
                {
                    "reason": "POSSIBLE_SOURCE_OMISSION",
                    "content_unit_id": owners[0]["content_unit_id"] if len(owners) == 1 else "",
                    "segment_ids": [s.id for s in refs],
                    "supporting_quote": "".join(str(s.corrected_text or s.text) for s in refs),
                }
            )
            break
    return result


def quality_summary(version_id, sections, facts, mentions, *, gaps=None, generation=None):
    issues = []
    candidate_reviews = []
    for mention in mentions:
        from zhijian.services.recommendation_intent import mention_opinion

        opinion = mention_opinion(mention)
        if opinion["review_required"]:
            if getattr(mention, "subject_role", "LEGACY") in {"SECONDARY", "CONTEXT", "REFERENCE"} and set(
                opinion.get("reason_codes", [])
            ) == {"MISSING_OVERALL_EVIDENCE"}:
                candidate_reviews.append(
                    {
                        "mention_id": mention.id,
                        "kind": "NO_INDEPENDENT_AUTHOR_OPINION",
                        "reason_codes": opinion["reason_codes"],
                    }
                )
                continue
            issues.append(
                {
                    "kind": "AUTHOR_OPINION_REVIEW",
                    "mention_id": mention.id,
                    "section_ids": [
                        s["id"] for s in sections if mention.id in s.get("place_mention_ids", [])
                    ],
                    "reason_codes": opinion.get("reason_codes", []),
                }
            )
    represented = 0
    for index, fact in enumerate(facts):
        if fact.get("attribution_status") == "NEEDS_REVIEW":
            issues.append({"kind": "SOURCE_ATTRIBUTION_REVIEW", "fact_index": index, "section_ids": []})
        relevant = [
            s
            for s in sections
            if set(fact.get("place_mention_ids", [])) <= set(s.get("place_mention_ids", []))
        ]
        quotes = [norm(q) for s in relevant for q in s.get("evidence_quotes", s.get("supporting_quotes", []))]
        ids = {sid for s in relevant for sid in s.get("segment_ids", [])}
        covered = set(fact.get("segment_ids", [])) <= ids and all(
            any(norm(q) in value for value in quotes) for q in fact.get("supporting_quotes", [])
        )
        if covered:
            represented += 1
        else:
            issues.append({"kind": "FACT_EVIDENCE_MISSING", "fact_index": index, "section_ids": []})
    for gap in gaps or []:
        issues.append(
            {
                "kind": gap["reason"],
                "segment_ids": gap["segment_ids"],
                "section_ids": [
                    s["id"] for s in sections if set(gap["segment_ids"]) <= set(s.get("segment_ids", []))
                ],
            }
        )
    generation = generation or {}
    mode = generation.get("generation_mode") if generation.get("note_version_id") == version_id else None
    mode = mode if mode in {"MODEL", "HYBRID", "DETERMINISTIC_FALLBACK"} else "UNKNOWN"
    if (
        generation.get("note_version_id") == version_id
        and mode != "UNKNOWN"
        and isinstance(generation.get("omitted_fact_count"), int)
        and generation["omitted_fact_count"] > 0
    ):
        issues.append(
            {
                "kind": "MODEL_FACTS_NOT_SUMMARIZED",
                "count": generation["omitted_fact_count"],
                "section_ids": [],
            }
        )
    return {
        "note_version_id": version_id,
        "assessment_version": VERSION,
        "status": "NEEDS_REVIEW" if issues else "UNKNOWN",
        "generation_mode": mode,
        "fact_count": len(facts),
        "evidence_represented_count": represented,
        "summarized_fact_count": None,
        "issue_count": len(issues),
        "issues": issues,
        "candidate_review_count": len(candidate_reviews),
        "candidate_review_issues": candidate_reviews,
    }
