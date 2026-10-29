"""Versioned author-theme evidence. Pure extraction/validation; no history mutation."""

from __future__ import annotations

import re
from hashlib import sha256

VERSION = "temporal-context-v6-source-review"
INTENT = re.compile(r"推荐|整理|盘点|分享|适合|哪里|避暑小城")
TIME = re.compile(
    r"暑假|寒假|暑期|春[季天]|夏[季天]|秋[季天]|冬[季天]|盛夏|(?<![0-9])(?:1[0-2]|[1-9]|[一二三四五六七八九十]{1,3})月份?(?:[0-9一二三四五六七八九十]{1,3}[日号])?(?:(?:到|至|[-—～])(?:次年)?(?:1[0-2]|[1-9]|[一二三四五六七八九十]{1,3})月份?(?:[0-9一二三四五六七八九十]{1,3}[日号])?)?"
)
NEGATIVE = re.compile(r"不推荐|不再推荐|并不推荐|不建议|不适合|别去|不要去")


def candidate_contexts(segments):
    result = []
    for index, segment in enumerate(segments):
        if not getattr(segment, "snapshot_id", None):
            continue
        # Each candidate has a bounded continuous source interval. No truncation of its quote.
        if not TIME.search(segment.corrected_text or segment.text):
            continue
        chain = [segment]
        for following in segments[index + 1 : index + 3]:
            if following.snapshot_id != segment.snapshot_id:
                break
            chain.append(following)
            if sum(len(s.corrected_text or s.text) for s in chain) >= 700:
                break
        text = "".join(s.corrected_text or s.text for s in chain)
        # Dates in demand/background clauses are never used as recommendation dates.
        clauses = re.split(r"[。！？!?；;]", text)
        sentence = next(
            (
                s
                for s in clauses
                if TIME.search(s)
                and INTENT.search(s)
                and re.search(
                    r"哪里|哪些|目的地推荐|推荐目的地|清单|合集|盘点|整理|"
                    r"(?:推荐|分享)(?:这|那)?(?:一些|几个|这些|一批|[0-9]+个)",
                    s,
                )
                and not NEGATIVE.search(s)
                and not re.search(r"去年|前年|统计|游客最多|出行高峰", s)
            ),
            "",
        )
        if not sentence:
            continue
        raw = TIME.search(sentence).group()
        if "月" in raw:
            from zhijian.services.video_support import _months_in_text

            if not _months_in_text(raw):
                continue
        if any(c["raw_time_text"] == raw and set(c["segment_ids"]) & {s.id for s in chain} for c in result):
            continue
        ids = [s.id for s in chain]
        result.append(
            {
                "context_id": "tc_" + sha256((raw + text).encode()).hexdigest()[:16],
                "source_kind": "SOURCE_FACT",
                "source_text": text,
                "segment_ids": ids,
                "raw_time_text": raw,
                "purpose": "VISIT",
                "activity": "SUMMER_ESCAPE" if "避暑" in sentence else "GENERAL_VISIT",
                "scope": "AUTHOR_THEME",
                "interpretation_status": "SOURCE_REPORTED",
                "parser_version": VERSION,
            }
        )
    return result


def validate_applications(entity, units, contexts, segments):
    """An application requires a quoted membership claim inside its own ContentUnit."""
    if not contexts or not entity.get("temporal_applications"):
        return []
    if any(not getattr(s, "snapshot_id", None) for s in segments):
        return []
    texts = {s.id: s.corrected_text or s.text for s in segments}
    order = list(texts)
    snapshots = {s.id: s.snapshot_id for s in segments}
    unit = next((u for u in units if u.get("content_unit_id") == entity.get("content_unit_id")), {})
    if (
        entity.get("subject_role") not in {"PRIMARY", "SECONDARY"}
        or entity.get("visit_intent") not in {"RECOMMENDED", "OPTIONAL", "NEUTRAL"}
        or entity.get("poi_policy") not in {"RESOLVE", "AREA_RESOLVE"}
        or unit.get("unit_type") not in {"AREA_GUIDE", "PLACE_GUIDE", "MULTI_PLACE_LIST"}
    ):
        return []
    accepted = []
    for app in entity.get("temporal_applications", []) or []:
        if not isinstance(app, dict) or app.get("relation") not in {"INCLUDED", "OPTIONAL"}:
            continue
        context = next((c for c in contexts if c["context_id"] == app.get("context_id")), None)
        ids, quote = app.get("segment_ids", []), app.get("supporting_quote", "")
        owned_ids = {
            *unit.get("segment_ids", []),
            *entity.get("segment_ids", []),
            *entity.get("_source_recovered_ids", []),
        }
        if not context or not ids or not quote or any(s not in owned_ids or s not in texts for s in ids):
            continue
        positions = [order.index(s) for s in ids]
        if positions != list(range(positions[0], positions[0] + len(ids))):
            continue
        if quote not in "".join(texts[s] for s in ids) or NEGATIVE.search(quote):
            continue
        if not (
            any(entity.get(k) and entity[k] in quote for k in ("name", "raw_name"))
            or unit.get("anchor_entity_ids") == [entity.get("entity_id")]
        ):
            continue
        if entity.get("visit_intent") == "NEUTRAL":
            primary_entry = (
                entity.get("subject_role") == "PRIMARY"
                and unit.get("anchor_entity_ids") == [entity.get("entity_id")]
                and re.search(r"接下来|首先|第.{0,4}个|下一个|最后", quote)
                and any(c.get("source_kind") == "SOURCE_FACT" for c in contexts)
            )
            explicit_child = (
                app.get("repair_rule") == "EXPLICIT_SOURCE_LIST_CHILD"
                and ids == entity.get("_source_recovered_ids")
                and re.search(r"所以一定要(?:过来|来|去)打卡", quote)
            )
            if not primary_entry and not explicit_child:
                continue
        if any(s not in texts for s in context["segment_ids"]):
            continue
        if len({snapshots[s] for s in [*ids, *context["segment_ids"]]}) != 1:
            continue
        if context.get("source_kind") == "COVER_TEXT":
            if context.get("intent") != "RECOMMENDED":
                continue
            body = "".join(texts[s] for s in unit.get("segment_ids", []) if s in texts)
            body += (
                entity.get("name", "")
                + entity.get("raw_name", "")
                + str(entity.get("city_hint", ""))
                + str(entity.get("province_hint", ""))
            )
            if any(t not in body for t in context.get("scope_terms", [])):
                continue
            if context.get("scope") == "SPECIFIC_PLACE" and not any(
                entity.get(k) and entity[k] in context["source_text"] for k in ("name", "raw_name")
            ):
                continue
            start = -1
        else:
            start = order.index(context["segment_ids"][0])
        if start > positions[0]:
            continue
        # A subsequent explicit theme is a boundary; model references cannot cross it.
        if context.get("source_kind") != "COVER_TEXT" and any(
            start < order.index(c["segment_ids"][0]) <= positions[0]
            for c in contexts
            if c != context and c.get("segment_ids")
        ):
            continue
        accepted.append(
            {
                "context": context,
                "entity_id": entity["entity_id"],
                "content_unit_id": unit["content_unit_id"],
                "segment_ids": ids,
                "supporting_quote": quote,
                "relation": "OPTIONAL" if entity.get("visit_intent") == "OPTIONAL" else app["relation"],
                "validation_status": "VERIFIED",
                **({"derivation": app["repair_rule"]} if app.get("repair_rule") else {}),
            }
        )
    return accepted


def application_windows(applications):
    from zhijian.services.video_support import _calendar_fields_from_text, _months_in_text

    for app in applications:
        c = app["context"]
        raw = c["raw_time_text"]
        for month in _months_in_text(raw) or [None]:
            yield {
                **_calendar_fields_from_text(raw),
                "month": month,
                "period_type": "OTHER",
                "suitability": "INFORMATIONAL" if app["relation"] == "OPTIONAL" else "RECOMMENDED",
                "source_text": c["source_text"],
                "segment_ids": c["segment_ids"],
                "provenance": "THEME_CONTEXT",
                "context_label": raw + ("避暑推荐" if c["activity"] == "SUMMER_ESCAPE" else "推荐主题"),
                "theme_context": app,
            }


def projected_theme_windows(db, entity_ids=None):
    """Same version-bound DTO projection for Place and Destination; never write on GET."""
    from types import SimpleNamespace

    from sqlalchemy import or_, select

    from zhijian.db.models import (
        AINoteVersion,
        GroundedMapArtifact,
        PlaceMention,
        Segment,
        Transcript,
        VideoAsset,
    )

    query = select(PlaceMention).where(PlaceMention.extraction_status == "EXTRACTED")
    if entity_ids is not None:
        query = query.where(
            or_(PlaceMention.place_id.in_(entity_ids), PlaceMention.destination_id.in_(entity_ids))
        )
    cache = {}
    result = []
    for m in db.scalars(query).all():
        pid = m.place_id or m.destination_id
        if not pid:
            continue
        version = db.get(AINoteVersion, m.ai_note_version_id) if m.ai_note_version_id else None
        if not version or not version.grounded_map_artifact_id:
            continue
        artifact = db.get(GroundedMapArtifact, version.grounded_map_artifact_id)
        asset = db.get(VideoAsset, m.video_asset_id)
        if (
            not artifact
            or not asset
            or artifact.video_asset_id != m.video_asset_id
            or artifact.transcript_version != version.transcript_version
            or artifact.semantic_hash != (m.metadata_json or {}).get("temporal_artifact_hash")
        ):
            continue
        if artifact.id not in cache:
            transcript = db.get(Transcript, artifact.transcript_id)
            sid = (transcript.metadata_json or {}).get("snapshot_id") if transcript else None
            segments = (
                list(
                    db.scalars(
                        select(Segment).where(Segment.snapshot_id == sid).order_by(Segment.ordinal)
                    ).all()
                )
                if sid
                else []
            )
            if (
                not transcript
                or transcript.video_asset_id != asset.id
                or transcript.version != version.transcript_version
            ):
                segments = []
            cache[artifact.id] = segments
        segments = cache[artifact.id]
        entity_id = (m.metadata_json or {}).get("semantic", {}).get("entity_id")
        entity = next((e for e in artifact.entities_json if e.get("entity_id") == entity_id), None)
        if not entity:
            continue
        if m.destination_id:
            texts = {s.id: s.corrected_text or s.text for s in segments}
            for i, local in enumerate((m.metadata_json or {}).get("visit_windows", [])):
                ids = local.get("segment_ids", [])
                positions = [list(texts).index(sid) for sid in ids if sid in texts]
                if (
                    not ids
                    or len(positions) != len(ids)
                    or positions != list(range(positions[0], positions[0] + len(ids)))
                    or local.get("source_text", "") not in "".join(texts.get(sid, "") for sid in ids)
                ):
                    continue
                result.append(
                    SimpleNamespace(
                        **{k: v for k, v in local.items() if k != "segment_ids"},
                        id=f"area:{m.id}:{i}",
                        place_id=pid,
                        place_mention_id=m.id,
                        source_id=asset.source_id,
                        segment_ids_json=ids,
                        provenance="SOURCE_FACT",
                        confidence=m.confidence,
                        status="ACTIVE",
                    )
                )
        entity = {
            **entity,
            "visit_intent": m.visit_intent,
            "subject_role": m.subject_role,
            "poi_policy": m.poi_policy,
        }
        apps = validate_applications(
            entity,
            artifact.content_units_json,
            artifact.semantic_options_json.get("temporal_contexts", []),
            segments,
        )
        if apps != (m.metadata_json or {}).get("temporal_applications", []):
            continue
        local = (m.metadata_json or {}).get("visit_windows", [])
        for index, w in enumerate(application_windows(apps)):
            conflicts = [
                v
                for v in local
                if v.get("suitability") in {"AVOID", "RESTRICTED"}
                and v.get("semantics", {}).get("purpose", "VISIT") == "VISIT"
                and temporal_windows_overlap(v, w)
            ]
            if conflicts:
                w["suitability"] = "INFORMATIONAL"
                w["theme_context"] = {**w["theme_context"], "exclusions": conflicts}
            result.append(
                SimpleNamespace(
                    **{k: v for k, v in w.items() if k != "segment_ids"},
                    id=f"theme:{m.id}:{index}",
                    place_id=pid,
                    place_mention_id=m.id,
                    source_id=asset.source_id,
                    segment_ids_json=w["segment_ids"],
                    confidence=m.confidence,
                    status="ACTIVE",
                    note_id=version.ai_note_id,
                    note_version_id=version.id,
                )
            )
    return result


def analysis_status(metadata):
    metadata = metadata or {}
    if metadata.get("visit_windows"):
        return "HAS_LOCAL_TIME"
    if metadata.get("temporal_applications"):
        return "HAS_THEME_CONTEXT"
    status = metadata.get("temporal_analysis", {}).get("status")
    return {"NO_TIME_MENTIONED": "NO_LOCAL_TIME", "ANALYZED": "TIME_UNRESOLVED"}.get(
        status, status or "NOT_ANALYZED"
    )


def window_semantics(item):
    from zhijian.services.travel_semantics import temporal_semantics

    context = getattr(item, "theme_context", {}).get("context", {})
    result = temporal_semantics(
        context.get("raw_time_text", item.source_text or ""), period_type=item.period_type
    )
    if context:
        result.update(source_kind="THEME_CONTEXT", purpose=context["purpose"], activity=context["activity"])
    return result


def matches_theme(window, query):
    context = getattr(window, "theme_context", {}).get("context", {})
    if window.provenance != "THEME_CONTEXT" or not context:
        return False
    raw = context["raw_time_text"]
    return (
        query == "SUMMER_ESCAPE"
        and context["activity"] == query
        or query == "SUMMER_HOLIDAY"
        and raw in {"暑假", "暑期"}
        or query == "WINTER_HOLIDAY"
        and raw == "寒假"
    )


def contexts_for_chunk(contexts, segments, chunk):
    """Send the active preceding theme and switches inside this chunk, without truncation."""
    positions = {s.id: i for i, s in enumerate(segments)}
    start, end = positions[chunk[0].id], positions[chunk[-1].id]
    covers = [c for c in contexts if c.get("source_kind") == "COVER_TEXT"]
    contexts = [c for c in contexts if c.get("segment_ids")]
    prior = [c for c in contexts if positions[c["segment_ids"][0]] < start]
    active = max(prior, key=lambda c: positions[c["segment_ids"][0]]) if prior else None
    return covers + [c for c in contexts if c is active or start <= positions[c["segment_ids"][0]] <= end]


def recover_source_membership(entities, units, contexts, segments):
    """Recover only explicit author list entries, retaining the exact cited source and lineage."""
    texts = {s.id: s.corrected_text or s.text for s in segments}
    order = list(texts)
    snapshots = {s.id: s.snapshot_id for s in segments}
    unit_by_id = {u["content_unit_id"]: u for u in units}
    for e in entities:
        e.pop("_source_recovered_ids", None)
        apps = e.get("temporal_applications") or []
        e["temporal_applications"] = [dict(a) for a in apps if isinstance(a, dict)]
        # Remove superfluous references only when the unmodified quote occurs in exactly one declared Segment.
        for a in e["temporal_applications"]:
            quote = a.get("supporting_quote", "")
            hits = [sid for sid in a.get("segment_ids", []) if quote and quote in texts.get(sid, "")]
            if len(hits) == 1 and a.get("segment_ids") != hits:
                a["original_segment_ids"] = list(a["segment_ids"])
                a["segment_ids"] = hits
                a["repair_rule"] = "EXACT_QUOTE_MINIMAL_DECLARED_SEGMENT"
    # First establish primary entries from explicit sequencing and an existing author recommendation theme.
    for e in entities:
        u = unit_by_id.get(e.get("content_unit_id"), {})
        if (
            e.get("subject_role") != "PRIMARY"
            or e.get("visit_intent") not in {"NEUTRAL", "RECOMMENDED"}
            or u.get("anchor_entity_ids") != [e.get("entity_id")]
        ):
            continue
        for sid in e.get("segment_ids", []):
            text = texts.get(sid, "")
            for clause in re.split(r"[。！？!?；;]", text):
                if (
                    not re.search(r"接下来|首先|第.{0,4}个|下一个|最后", clause)
                    or not any(e.get(k) and e[k] in clause for k in ["name", "raw_name"])
                    or NEGATIVE.search(clause)
                ):
                    continue
                for c in contexts_for_chunk(contexts, segments, [next(s for s in segments if s.id == sid)]):
                    if c.get("source_kind") in {"COVER_TEXT", "SOURCE_FACT"} and not any(
                        a.get("context_id") == c["context_id"] for a in e["temporal_applications"]
                    ):
                        e["temporal_applications"].append(
                            {
                                "context_id": c["context_id"],
                                "relation": "INCLUDED",
                                "segment_ids": [sid],
                                "supporting_quote": clause,
                                "repair_rule": "EXPLICIT_SOURCE_LIST_ENTRY",
                            }
                        )
    parents = {}
    for e in entities:
        u = unit_by_id.get(e.get("content_unit_id"), {})
        if u.get("anchor_entity_ids") == [e.get("entity_id")]:
            parents[e.get("content_unit_id")] = validate_applications(e, units, contexts, segments)
    for e in entities:
        if (
            e.get("subject_role") != "SECONDARY"
            or e.get("visit_intent") not in {"RECOMMENDED", "NEUTRAL"}
            or not parents.get(e.get("content_unit_id"))
        ):
            continue
        for sid in e.get("segment_ids", []):
            pos = order.index(sid) if sid in texts else -1
            if pos < 0 or pos + 1 >= len(order):
                continue
            following = order[pos + 1]
            if snapshots[sid] != snapshots[following]:
                continue
            name = e.get("raw_name") or e.get("name") or ""
            match = re.search(r"(?:还有|例如|比如|推荐)" + re.escape(name), texts[sid]) if name else None
            if not match:
                continue
            quote = (texts[sid] + texts[following])[match.start() :]
            quote = re.split(r"当然|同时|接下来|另外|其次|作为|[。！？!?；;]", quote, maxsplit=1)[0]
            if (
                not re.search(r"所以一定要(?:过来|来|去)打卡", quote)
                or NEGATIVE.search(quote)
                or re.search(r"网友|听说|据说|有人说|别人说", quote)
            ):
                continue
            peers = [
                other.get("raw_name") or other.get("name")
                for other in entities
                if other.get("entity_id") != e.get("entity_id")
            ]
            if any(
                peer
                and (
                    texts[following].startswith(peer)
                    or re.search(r"(?:还有|另外|同时|以及|和|与)" + re.escape(peer), quote)
                )
                for peer in peers
            ):
                continue
            ids = [sid, following]
            if quote not in texts[sid] + texts[following]:
                continue
            e["_source_recovered_ids"] = ids
            for parent in parents[e["content_unit_id"]]:
                c = parent["context"]
                if not any(
                    a["context"]["context_id"] == c["context_id"]
                    for a in validate_applications(e, units, contexts, segments)
                ):
                    e["temporal_applications"].append(
                        {
                            "context_id": c["context_id"],
                            "relation": "INCLUDED",
                            "segment_ids": ids,
                            "supporting_quote": quote,
                            "repair_rule": "EXPLICIT_SOURCE_LIST_CHILD",
                        }
                    )
    return entities


def unresolved_temporal_evidence(segments, claims):
    """Retain omitted restrictions as unassigned source evidence; never turn them into city windows."""
    from zhijian.services.travel_timing import has_temporal_scope

    quotes = [c.get("supporting_quote", "") for c in claims]
    result = []
    seen = set()
    for i, s in enumerate(segments):
        chain = [s]
        if i + 1 < len(segments) and segments[i + 1].snapshot_id == s.snapshot_id:
            chain.append(segments[i + 1])
        joined = "".join(x.corrected_text or x.text for x in chain)
        for quote in re.split(r"[。！？!?；;]", joined):
            if not (
                has_temporal_scope(quote)
                and re.search(r"不再推荐|不推荐|不建议|不适合|封路|封山|闭园", quote)
            ):
                continue
            if quote in seen or any(quote in existing for existing in quotes):
                continue
            start = joined.find(quote)
            end = start + len(quote)
            offset = 0
            ids = []
            for x in chain:
                size = len(x.corrected_text or x.text)
                if offset < end and offset + size > start:
                    ids.append(x.id)
                offset += size
            seen.add(quote)
            result.append(
                {
                    "source_kind": "SOURCE_FACT",
                    "status": "NEEDS_REVIEW",
                    "scope": "UNRESOLVED_LOCAL_SUBJECT",
                    "source_text": quote,
                    "segment_ids": ids,
                    "reason": "NO_VALIDATED_SUBJECT_BINDING",
                }
            )
    # Prefer a complete contiguous quote to its suffix from the next overlapping pair.
    return [
        r
        for r in result
        if not any(
            r["source_text"] != other["source_text"] and r["source_text"] in other["source_text"]
            for other in result
        )
    ]


def temporal_windows_overlap(local, theme):
    """Compare explicit calendar ranges; retain uncertainty instead of inventing holiday dates."""
    from datetime import date

    from zhijian.services.travel_semantics import temporal_semantics
    from zhijian.services.travel_timing import SEASON_MONTHS

    def days(w):
        raw = w.get("theme_context", {}).get("context", {}).get("raw_time_text", w.get("source_text", ""))
        sem = temporal_semantics(raw)
        a, b = sem.get("start"), sem.get("end")
        if a and b and a.get("day") and b.get("day"):
            start = date(2000, a["month"], a["day"]).timetuple().tm_yday
            end = date(2000, b["month"], b["day"]).timetuple().tm_yday
            return (
                set(range(start, end + 1))
                if start <= end
                else set(range(start, 367)) | set(range(1, end + 1))
            )
        months = {w["month"]} if w.get("month") else set(SEASON_MONTHS.get(w.get("season"), ()))
        if a and b and sem["precision"] == "MONTH":
            x, y = a["month"], b["month"]
            months = set(range(x, y + 1)) if x <= y else set(range(x, 13)) | set(range(1, y + 1))
        if not months:
            return None
        return {
            i for i in range(1, 367) if date.fromordinal(date(2000, 1, 1).toordinal() + i - 1).month in months
        }

    a, b = days(local), days(theme)
    return True if a is None or b is None else bool(a & b)
