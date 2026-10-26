"""Versioned, source-bound author opinions; POI identity and user preference are independent."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select

VERSION = "recommendation-v1"
INTENTS = {"RECOMMENDED", "OPTIONAL", "NOT_RECOMMENDED"}


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement_id: str = Field(min_length=1, max_length=96)
    intent: Literal["RECOMMENDED", "OPTIONAL", "NEUTRAL", "NOT_RECOMMENDED"]
    scope: Literal["PLACE_OVERALL", "LOCAL_DETAIL", "UNCERTAIN"]
    subject_entity_id: str = Field(min_length=1, max_length=96)
    speaker: Literal["AUTHOR", "OTHER", "UNKNOWN"]
    quote: str = Field(min_length=1, max_length=2000)
    segment_ids: list[str] = Field(min_length=1, max_length=40)
    condition: str = Field(default="", max_length=500)
    time_context: str = Field(default="", max_length=500)
    supersedes: list[str] = Field(default_factory=list, max_length=20)


def _norm(text):
    return re.sub(r"\s+", "", str(text))


def assess(candidate, texts):
    """Fail closed on invalid evidence. Linguistic rules flag doubt, never invent an opinion."""
    raw = candidate.get("recommendation_evidence") or {}
    values = raw.get("statements", []) if isinstance(raw, dict) else []
    reasons, statements = set(), []
    if not isinstance(values, list) or len(values) > 80:
        values = []
        reasons.add("INVALID_STATEMENTS")
    for value in values:
        try:
            s = Statement.model_validate(value)
        except ValidationError:
            reasons.add("INVALID_STATEMENT")
            continue
        if s.subject_entity_id != candidate.get("entity_id"):
            reasons.add("WRONG_SUBJECT")
            continue
        if not all(sid in texts for sid in s.segment_ids) or _norm(s.quote) not in _norm(
            "".join(texts.get(sid, "") for sid in s.segment_ids)
        ):
            reasons.add("UNGROUNDED_QUOTE")
            continue
        if any(v and v not in s.quote for v in (s.condition, s.time_context)):
            reasons.add("UNGROUNDED_CONTEXT")
            continue
        if s.scope == "UNCERTAIN" or s.speaker == "UNKNOWN":
            reasons.add("UNCERTAIN_ATTRIBUTION")
        if s.scope == "PLACE_OVERALL" and s.speaker == "AUTHOR":
            # These are consistency alarms, not a natural-language classifier.
            if re.search(r"不是不|并非不|不能说不", s.quote):
                reasons.add("COMPLEX_NEGATION")
            if re.search(r"有人说|不少人说|听说|据说", s.quote):
                reasons.add("ATTRIBUTION_NEEDS_REVIEW")
            parts = re.split(r"[，,；;]?(?:但是|不过|但)", s.quote, maxsplit=1)
            own_names = {str(candidate.get("name") or ""), str(candidate.get("raw_name") or "")} - {""}
            peer_names = set(candidate.get("_peer_names", [])) - own_names
            if any(name in s.quote for name in peer_names):
                reasons.add("MULTI_OR_WRONG_SUBJECT_QUOTE")
            local_tail = (
                len(parts) == 2
                and re.search(r"游船|菜品|门票|费用|下雨|雨天|天气|玩法|交通", parts[1])
                and not any(name in parts[1] for name in own_names)
            )
            clause = parts[0] if local_tail else s.quote
            if re.search(r"(?:游船|菜品|门票|费用|天气|玩法).{0,6}(?:不推荐|不建议|不好)", clause):
                reasons.add("LOCAL_DETAIL_MISSCOPED")
            negative = bool(re.search(r"不值得|不推荐|不建议.{0,5}(?:来|去|到访)|别来|别去", clause))
            positive = bool(re.search(r"值得(?:来|去|到访)|推荐.{0,8}(?:来|去)|建议.{0,8}(?:来|去)", s.quote))
            if (s.intent == "RECOMMENDED" and (negative or not positive)) or (
                s.intent == "NOT_RECOMMENDED" and not negative
            ):
                reasons.add("POLARITY_NEEDS_REVIEW")
        statements.append(s.model_dump())
    statements = sorted(
        {json.dumps(s, ensure_ascii=False, sort_keys=True): s for s in statements}.values(),
        key=lambda s: (s["statement_id"], s["quote"]),
    )
    seen_ids = [s["statement_id"] for s in statements]
    if len(set(seen_ids)) != len(seen_ids):
        reasons.add("DUPLICATE_STATEMENT_ID")
    superseded = set()
    for s in statements:
        if s["supersedes"]:
            if not set(s["supersedes"]) <= set(seen_ids) - {s["statement_id"]} or not re.search(
                r"现在|改造后|改口|改变|以前|去年", s["quote"]
            ):
                reasons.add("UNVERIFIED_REVISION")
            else:
                superseded.update(s["supersedes"])
    active = [
        s
        for s in statements
        if s["statement_id"] not in superseded and s["scope"] == "PLACE_OVERALL" and s["speaker"] == "AUTHOR"
    ]
    intents = {s["intent"] for s in active if s["intent"] in INTENTS}
    conditional = False
    if "RECOMMENDED" in intents and "NOT_RECOMMENDED" in intents:
        positive_conditions = {s["condition"] for s in active if s["intent"] == "RECOMMENDED"}
        negative_conditions = {s["condition"] for s in active if s["intent"] == "NOT_RECOMMENDED"}
        conditional = bool(
            positive_conditions
            and negative_conditions
            and "" not in positive_conditions | negative_conditions
            and not positive_conditions & negative_conditions
        )
        if not conditional:
            reasons.add("CONFLICT")
    label = str(candidate.get("visit_intent") or "NEUTRAL")
    if not active and label in INTENTS:
        reasons.add("MISSING_OVERALL_EVIDENCE")
    if active and label in INTENTS and label not in intents:
        reasons.add("LABEL_EVIDENCE_MISMATCH")
    status = (
        "CONFLICT"
        if "CONFLICT" in reasons
        else "UNKNOWN"
        if reasons or not intents or conditional
        else "NOT_RECOMMENDED"
        if "NOT_RECOMMENDED" in intents
        else "OPTIONAL"
        if "OPTIONAL" in intents
        else "RECOMMENDED"
    )
    return {
        "schema_version": VERSION,
        "assessment_status": "NEEDS_REVIEW" if reasons else "VERIFIED" if active else "UNKNOWN",
        "status": status,
        "statements": statements,
        "reason_codes": sorted(reasons),
    }


def merge_evidence(left, right):
    left = left if isinstance(left, dict) else {}
    right = right if isinstance(right, dict) else {}
    values = [
        *(left.get("statements") if isinstance(left.get("statements"), list) else []),
        *(right.get("statements") if isinstance(right.get("statements"), list) else []),
    ]
    return {
        "schema_version": VERSION,
        "statements": sorted(
            {json.dumps(v, sort_keys=True, ensure_ascii=False): v for v in values}.values(),
            key=lambda v: json.dumps(v, sort_keys=True),
        ),
    }


def mention_opinion(mention):
    evidence = (mention.metadata_json or {}).get("recommendation_evidence")
    if not evidence or evidence.get("schema_version") != VERSION:
        # Legacy labels are disclosed, never promoted to newly verified recommendations.
        return {
            "status": "NOT_RECOMMENDED" if mention.visit_intent == "NOT_RECOMMENDED" else "UNKNOWN",
            "review_required": mention.visit_intent == "NOT_RECOMMENDED",
            "assessment_status": "LEGACY",
            "legacy_intent": mention.visit_intent,
            "statements": [],
            "reason_codes": ["LEGACY_EVIDENCE_UNVERIFIED"],
        }
    return {
        "status": evidence.get("status", "UNKNOWN"),
        "review_required": evidence.get("assessment_status") == "NEEDS_REVIEW",
        **evidence,
    }


def summarize(mentions):
    opinions = []
    for m in sorted(mentions, key=lambda m: m.id):
        if m.extraction_status in {"USER_REJECTED", "SUPERSEDED"}:
            continue
        opinions.append(
            {
                "mention_id": m.id,
                "version_id": m.ai_note_version_id,
                "video_asset_id": m.video_asset_id,
                **mention_opinion(m),
            }
        )
    statuses = {o["status"] for o in opinions}
    qualified = [
        s
        for o in opinions
        for s in o.get("statements", [])
        if s.get("scope") == "PLACE_OVERALL" and s.get("speaker") == "AUTHOR"
    ]
    pos_conditions = {s.get("condition", "") for s in qualified if s["intent"] == "RECOMMENDED"}
    neg_conditions = {s.get("condition", "") for s in qualified if s["intent"] == "NOT_RECOMMENDED"}
    different_conditions = bool(
        pos_conditions
        and neg_conditions
        and "" not in pos_conditions | neg_conditions
        and not pos_conditions & neg_conditions
    )
    status = (
        "CONFLICT"
        if "CONFLICT" in statuses
        or ({"RECOMMENDED", "NOT_RECOMMENDED"} <= statuses and not different_conditions)
        else "UNKNOWN"
        if different_conditions
        else "NOT_RECOMMENDED"
        if "NOT_RECOMMENDED" in statuses
        else "RECOMMENDED"
        if statuses == {"RECOMMENDED"}
        else "OPTIONAL"
        if statuses <= {"OPTIONAL", "RECOMMENDED"} and statuses
        else "UNKNOWN"
    )
    return {
        "version": VERSION,
        "status": status,
        "review_required": status == "CONFLICT" or any(o["review_required"] for o in opinions),
        "source_opinions": opinions,
    }


def projection(db, place_ids):
    from zhijian.db.models import AINote, AINoteVersion, PlaceMention, VideoAsset

    mentions = db.scalars(select(PlaceMention).where(PlaceMention.place_id.in_(place_ids))).all()
    current = dict(db.execute(select(AINote.id, AINote.current_version_id)).all())
    versions = {
        v.id: v.ai_note_id
        for v in db.scalars(
            select(AINoteVersion).where(AINoteVersion.id.in_({m.ai_note_version_id for m in mentions}))
        ).all()
    }
    assets = {
        a.id: a
        for a in db.scalars(
            select(VideoAsset).where(VideoAsset.id.in_({m.video_asset_id for m in mentions}))
        ).all()
    }
    result = {}
    for pid in place_ids:
        summary = summarize(
            [
                m
                for m in mentions
                if m.place_id == pid
                and (
                    not m.ai_note_version_id
                    or current.get(versions.get(m.ai_note_version_id)) == m.ai_note_version_id
                )
            ]
        )
        for opinion in summary["source_opinions"]:
            asset = assets.get(opinion["video_asset_id"])
            opinion["note_id"] = versions.get(opinion["version_id"])
            opinion["title"] = asset.title if asset else "视频笔记"
            opinion["canonical_url"] = asset.canonical_url if asset else ""
        result[pid] = summary
    return result


def source_links(summary):
    links = [
        {"note_id": o["note_id"], "version_id": o["version_id"], "title": o.get("title") or "视频笔记"}
        for o in summary.get("source_opinions", [])
        if o.get("note_id")
    ]
    return list({(v["note_id"], v["version_id"]): v for v in links}.values())
