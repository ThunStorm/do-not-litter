"""Read-only, version-bound place advice and explicitly shared seasonal context."""

from __future__ import annotations

import re
from collections import defaultdict
from types import SimpleNamespace

from sqlalchemy import select

from zhijian.db.models import AINoteVersion, GroundedMapArtifact, PlaceMention, Segment, Snapshot, VideoAsset

THEMES = {
    "雾凇": r"雾凇",
    "雪景": r"雪景|赏雪|雪后",
    "云海": r"云海",
    "秋色": r"红叶|赏枫",
    "花景": r"赏花|花期",
}
WARNING = re.compile(
    r"不推荐|不建议|避开|需要|注意|贵|成本|交通|耗时|寒冷|保暖|穿厚|天黑|阴天|无风|有风|大风|体力|限制|关闭|封山|封路|会化|融化|危险|预约|限流"
)


def _verified(quote, ids, texts):
    def normalize(value):
        return re.sub(r"\W", "", value)

    return bool(
        quote
        and ids
        and all(sid in texts for sid in ids)
        and normalize(quote) in normalize("".join(texts[sid] for sid in ids))
    )


def experience_projection(db, place_ids=None):
    from zhijian.services.video_support import _visit_windows_from_candidate

    query = select(PlaceMention).where(PlaceMention.place_id.is_not(None))
    if place_ids is not None:
        # Load peers for evidence links across chunks of the same note, not just the requested point.
        query = query.where(
            PlaceMention.video_asset_id.in_(
                select(PlaceMention.video_asset_id).where(PlaceMention.place_id.in_(place_ids))
            )
        )
    mentions = [
        m
        for m in db.scalars(query.order_by(PlaceMention.updated_at.desc())).all()
        if m.extraction_status not in {"USER_REJECTED", "SUPERSEDED"}
        and m.subject_role in {"PRIMARY", "SECONDARY"}
        and m.visit_intent in {"RECOMMENDED", "OPTIONAL"}
    ]
    versions = {
        v.id: v
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
    artifacts = db.scalars(
        select(GroundedMapArtifact)
        .where(GroundedMapArtifact.video_asset_id.in_(assets))
        .order_by(GroundedMapArtifact.created_at.desc())
    ).all()
    all_ids = {sid for m in mentions for sid in m.segment_ids_json or []}
    for a in artifacts:
        all_ids.update(sid for u in a.content_units_json for sid in u.get("segment_ids", []))
        all_ids.update(sid for c in a.claims_json for sid in c.get("segment_ids", []))
    rows = db.execute(
        select(Segment, Snapshot.source_id)
        .join(Snapshot, Segment.snapshot_id == Snapshot.id)
        .where(Segment.id.in_(all_ids))
    ).all()
    result = defaultdict(
        lambda: {"windows": [], "reasons": [], "warnings": [], "sources": [], "themes": [], "access": []}
    )
    units, owned = {}, []
    for m in mentions:
        asset, version = assets.get(m.video_asset_id), versions.get(m.ai_note_version_id)
        if not asset:
            continue
        texts = {s.id: s.corrected_text or s.text for s, src in rows if src == asset.source_id}
        artifact = next(
            (
                a
                for a in artifacts
                if version
                and a.video_asset_id == m.video_asset_id
                and a.transcript_version == version.transcript_version
                and any(u.get("content_unit_id") == m.content_unit_id for u in a.content_units_json)
            ),
            None,
        )
        unit = (
            next(
                (u for u in artifact.content_units_json if u.get("content_unit_id") == m.content_unit_id), {}
            )
            if artifact
            else {}
        )
        entity = (m.metadata_json or {}).get("semantic", {}).get("entity_id")
        key = (m.ai_note_version_id, m.content_unit_id)
        direct = list(m.segment_ids_json or [])
        sole_anchor = unit.get("unit_type") == "PLACE_GUIDE" and unit.get("anchor_entity_ids") == [entity]
        ids = list(unit.get("segment_ids", direct)) if sole_anchor else direct
        scoped = {sid: texts[sid] for sid in ids if sid in texts}
        temporal_texts = scoped
        if not sole_anchor:
            names = [m.name, m.raw_name]
            other_names = (
                {
                    str(e.get("raw_name") or e.get("name") or "")
                    for e in (artifact.entities_json if artifact else [])
                    if e.get("entity_id") != entity
                }
                - set(names)
                - {""}
            )
            temporal_texts = {
                sid: "。".join(
                    part
                    for part in re.split(r"[。！？!?；;，,]|但|而", text)
                    if any(name and name in part for name in names)
                    and not any(name in part for name in other_names)
                )
                for sid, text in scoped.items()
            }
        windows = _visit_windows_from_candidate({}, list(temporal_texts), temporal_texts)
        windows = [w for w in windows if not re.search(r"去年|前年|20\d{2}年", w["source_text"])]
        view = result[m.place_id]
        if version:
            src = {
                "note_id": version.ai_note_id,
                "version_id": version.id,
                "title": asset.title or "视频笔记",
            }
            if src not in view["sources"]:
                view["sources"].append(src)
        unit_text = "".join(texts.get(sid, "") for sid in unit.get("segment_ids", []))
        themes = {name for name, pattern in THEMES.items() if re.search(pattern, unit_text)}
        shared_subject = any(
            entity in c.get("subject_entity_ids", [])
            and c.get("content_unit_id") == m.content_unit_id
            and set(c.get("subject_entity_ids", [])) & set(unit.get("anchor_entity_ids", []))
            and _verified(c.get("supporting_quote", ""), c.get("segment_ids", []), texts)
            for c in (artifact.claims_json if artifact else [])
        )
        if unit.get("unit_type") in {"PLACE_GUIDE", "MULTI_PLACE_LIST"} and (
            entity in unit.get("anchor_entity_ids", []) or shared_subject
        ):
            entry = units.setdefault(key, {"peers": set(), "themes": themes, "seeds": [], "unit": unit})
            entry["peers"].add(m.place_id)
            if sole_anchor:
                entry["seeds"].extend(
                    (w, asset.source_id)
                    for w in windows
                    if w.get("season") and w["suitability"] not in {"AVOID", "RESTRICTED"}
                )
        # Shared claims are allowed only when this entity is explicitly a subject.
        theme_support = [m.quote]
        for claim in artifact.claims_json if artifact else []:
            if (
                entity not in claim.get("subject_entity_ids", [])
                or claim.get("content_unit_id") != m.content_unit_id
            ):
                continue
            if not _verified(claim.get("supporting_quote", ""), claim.get("segment_ids", []), texts):
                continue
            if claim.get("claim_type") == "COMPARISON":
                continue
            text = str(claim.get("text") or "").strip().replace("转写称", "视频提到，")
            if not text:
                continue
            theme_support.append(text)
            bucket = (
                "access"
                if claim.get("claim_type")
                in {"TRANSPORT", "ACCESS_MODE", "SCENIC_ROAD", "TRANSPORT_NOTE", "PARKING"}
                else "warnings"
                if WARNING.search(text) or claim.get("claim_type") in {"WARNING", "PRICE", "TRANSPORT"}
                else "reasons"
            )
            if text not in view[bucket]:
                view[bucket].append(text)
        if (
            not view["reasons"]
            and _verified(m.quote, direct, texts)
            and re.search(r"代表|最|包括|推荐|独特|冰景|雪景|风光|也有|都有", m.quote)
            and not m.quote.startswith("如果")
        ):
            view["reasons"].append(m.quote.strip())
        view["themes"] = sorted(
            set(view["themes"])
            | {name for name, pattern in THEMES.items() if re.search(pattern, "".join(theme_support))}
        )
        owned.append((m, key, windows, asset.source_id))
    # A repeated resolved place joins adjacent thematic units within this exact note version.
    # Only coarse seasons travel across this graph; dates, conditions and warnings stay local.
    for m, key, windows, source_id in owned:
        if not any(w.get("season") or w.get("month") for w in windows) and key in units:
            visited, queue = set(), [key]
            while queue:
                current = queue.pop()
                if current in visited:
                    continue
                visited.add(current)
                queue.extend(
                    other
                    for other, data in units.items()
                    if other not in visited
                    and other[0] == key[0]
                    and data["peers"] & units[current]["peers"]
                    and data["themes"] & units[current]["themes"]
                )
            seeds = [(w, src) for k in visited for w, src in units[k]["seeds"]]
            seasons = {w["season"] for w, _ in seeds}
            if len(seasons) == 1:
                w, inherited_source = seeds[0]
                result[m.place_id]["windows"].append(
                    SimpleNamespace(
                        id=f"context:{m.id}",
                        place_id=m.place_id,
                        source_id=inherited_source,
                        source_text=w["source_text"],
                        segment_ids_json=w["segment_ids"],
                        provenance="SEMANTIC_CONTEXT",
                        context_label="同篇笔记的共同景观季节",
                        period_type="BEST_VISIT",
                        suitability="INFORMATIONAL",
                        season=w["season"],
                        month=None,
                        month_segment=None,
                        day_time_slot=None,
                        confidence=m.confidence,
                        status="ACTIVE",
                    )
                )
        for i, w in enumerate(windows):
            result[m.place_id]["windows"].append(
                SimpleNamespace(
                    **{k: v for k, v in w.items() if k != "segment_ids"},
                    id=f"projection:{m.id}:{i}",
                    place_id=m.place_id,
                    source_id=source_id,
                    segment_ids_json=w["segment_ids"],
                    provenance="SOURCE_FACT",
                    confidence=m.confidence,
                    status="ACTIVE",
                )
            )
    if place_ids is not None:
        result = {key: value for key, value in result.items() if key in place_ids}
    return dict(result)


def effective_windows(db, place_ids=None, *, experiences=None):
    from zhijian.db.models import PlaceVisitWindow

    query = select(PlaceVisitWindow).where(PlaceVisitWindow.status == "ACTIVE")
    if place_ids is not None:
        query = query.where(PlaceVisitWindow.place_id.in_(place_ids))
    saved = list(db.scalars(query).all())
    keys = {(w.place_id, w.source_text, w.month, w.season) for w in saved}
    for pid, view in (
        experiences if experiences is not None else experience_projection(db, place_ids)
    ).items():
        if place_ids is not None and pid not in place_ids:
            continue
        for w in view["windows"]:
            key = (w.place_id, w.source_text, w.month, w.season)
            if key not in keys:
                saved.append(w)
                keys.add(key)
    return saved
