"""Evidence-validated author routes stored in immutable Grounded Map JSON extensions.

A guide is source content, never a provider navigation result or a user RouteDraft.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from sqlalchemy import select

from zhijian.db.models import AINote, AINoteVersion, GroundedMapArtifact, Place, PlaceMention, VideoAsset

VERSION = "route-guide-v1"
MODES = {
    "SELF_DRIVE": r"自驾|包车",
    "CYCLING": r"骑行|骑车",
    "RAIL": r"火车|铁路|米轨",
    "FOOD_THEME": r"美食|吃货",
}
KINDS = {"EXPLICIT_SEQUENCE", "EXPLICIT_LIST", "PARTIAL_SEQUENCE", "CORRIDOR_ONLY", "UNORDERED_LOOP"}


def normalize(text):
    return re.sub(r"\W", "", str(text))


def validate_route(raw: dict, claim: dict, texts: dict[str, str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    ids = claim.get("segment_ids") or []
    quote = str(claim.get("supporting_quote") or "")
    if not ids or not quote or any(sid not in texts for sid in ids):
        return None
    positions = [list(texts).index(sid) for sid in ids]
    if positions != list(range(positions[0], positions[0] + len(positions))):
        return None
    if normalize(quote) not in normalize("".join(texts[sid] for sid in ids)):
        return None
    mode, kind = raw.get("mode"), raw.get("sequence_kind", "EXPLICIT_SEQUENCE")
    if mode not in MODES or kind not in KINDS or not re.search(MODES[mode], quote):
        return None
    stops = raw.get("stops", [])
    if (
        not isinstance(stops, list)
        or len(stops) > 40
        or any(not isinstance(s, str) or not s or len(s) > 300 for s in stops)
    ):
        return None
    if any(normalize(stop) not in normalize(quote) for stop in stops):
        return None
    offsets = [normalize(quote).index(normalize(s)) for s in stops]
    if kind == "EXPLICIT_SEQUENCE" and (
        len(stops) < 2 or offsets != sorted(offsets) or len(set(stops)) != len(stops)
    ):
        return None
    # All asserted restrictions keep their own exact evidence; do not widen their scope.
    conditions = []
    for condition in raw.get("conditions", []) if isinstance(raw.get("conditions", []), list) else []:
        if not isinstance(condition, dict):
            return None
        cquote, cids = str(condition.get("quote") or ""), condition.get("segment_ids", [])
        subject = str(condition.get("subject") or "")
        if (
            not cquote
            or not cids
            or not subject
            or normalize(subject) not in normalize(cquote)
            or any(sid not in texts for sid in cids)
        ):
            return None
        cp = [list(texts).index(sid) for sid in cids]
        if cp != list(range(cp[0], cp[0] + len(cp))) or normalize(cquote) not in normalize(
            "".join(texts[sid] for sid in cids)
        ):
            return None
        conditions.append(
            {
                "subject": subject,
                "scope": "ROAD_SECTION",
                "quote": cquote,
                "segment_ids": cids,
                "activity": condition.get("activity") if condition.get("activity") in MODES else mode,
            }
        )
    road = str(raw.get("road") or "")
    if road and road not in quote:
        return None
    subject = str(raw.get("subject") or road or (stops[0] if stops else ""))
    if not subject or normalize(subject) not in normalize(quote):
        return None
    name = str(raw.get("name") or "作者路线")[:300]
    uncertain = bool(raw.get("recovered_from_prose")) or bool(
        re.search(r"待核|疑似|S[一二三四五六七八九十幺]+", quote)
    )
    identifier = hashlib.sha256((mode + kind + subject + road + quote + repr(stops)).encode()).hexdigest()[
        :24
    ]
    return {
        "id": "rg_" + identifier,
        "schema_version": VERSION,
        "name": name,
        "mode": mode,
        "subject": subject,
        "sequence_kind": kind,
        "road": road,
        "road_covers_all_stops": False,
        "stops": [
            {
                "raw_name": s,
                "order": i if kind == "EXPLICIT_SEQUENCE" else None,
                "review_status": "NEEDS_REVIEW",
                "place_id": None,
            }
            for i, s in enumerate(stops)
        ],
        "conditions": conditions,
        "evidence": {"quote": quote, "segment_ids": ids},
        "review_status": "NEEDS_REVIEW" if uncertain else "SOURCE_REPORTED",
        "is_closed_loop_verified": False,
        "navigation": None,
        "display_notice": "站点顺序示意，非道路导航；视频作者观点，未核实时效",
    }


def extract_routes(claims, texts, entities=None):
    from zhijian.services.route_recovery import explicit_route_lists, recover_route

    routes, seen = [], set()
    candidates = []
    for claim in claims:
        raw = claim.get("route")
        if raw is not None:
            candidates.append((raw, claim))
        elif recovered := recover_route(claim, texts, entities or []):
            candidates.append(recovered)
    candidates.extend(explicit_route_lists(texts))
    for raw, claim in candidates:
        route = validate_route(raw, claim, texts)
        if not route:
            continue
        key = (
            route["mode"],
            tuple(s["raw_name"] for s in route["stops"]),
            route["road"],
            route["subject"] if not route["stops"] else "",
        )
        if key not in seen:
            seen.add(key)
            routes.append(route)
    for route in routes:
        route["related_guide_ids"] = [
            other["id"]
            for other in routes
            if other is not route and route["road"] and route["road"] == other["road"]
        ]
    return routes


def list_route_guides(db, *, note_id=None):
    # Only explicit persisted guides are read: a GET never reparses history or calls a provider.
    query = (
        select(AINote, AINoteVersion, VideoAsset)
        .join(AINoteVersion, AINote.current_version_id == AINoteVersion.id)
        .join(VideoAsset, AINote.video_asset_id == VideoAsset.id)
    )
    if note_id:
        query = query.where(AINote.id == note_id)
    notes = db.execute(query.order_by(AINote.id)).all()
    asset_ids = {a.id for _, _, a in notes}
    if not asset_ids:
        return []
    artifacts = db.scalars(
        select(GroundedMapArtifact)
        .where(GroundedMapArtifact.video_asset_id.in_(asset_ids))
        .order_by(GroundedMapArtifact.created_at.desc(), GroundedMapArtifact.id.desc())
    ).all()
    mentions = defaultdict(list)
    for m, p in db.execute(
        select(PlaceMention, Place)
        .join(Place, PlaceMention.place_id == Place.id)
        .where(
            PlaceMention.ai_note_version_id.in_([v.id for _, v, _ in notes]),
            PlaceMention.extraction_status.not_in(["USER_REJECTED", "SUPERSEDED"]),
            PlaceMention.resolution_status == "CONFIRMED",
            Place.deleted_at.is_(None),
        )
    ).all():
        mentions[m.ai_note_version_id].append((m, p))
    result = []
    for note, version, asset in notes:
        artifact = next(
            (
                a
                for a in artifacts
                if a.video_asset_id == asset.id and a.transcript_version == version.transcript_version
            ),
            None,
        )
        if not artifact:
            continue
        for guide in (artifact.semantic_options_json or {}).get("route_guides", []):
            stops = []
            for stop in guide["stops"]:
                bound = {p.id: p for m, p in mentions[version.id] if stop["raw_name"] in {m.name, m.raw_name}}
                p = next(iter(bound.values())) if len(bound) == 1 else None
                stops.append(
                    {
                        **stop,
                        "place_id": p.id if p else None,
                        "review_status": "CONFIRMED" if p else "NEEDS_REVIEW",
                    }
                )
            result.append(
                {
                    **guide,
                    "id": f"{note.id}:{guide['id']}",
                    "guide_id": guide["id"],
                    "stops": stops,
                    "note_id": note.id,
                    "version_id": version.id,
                    "artifact_id": artifact.id,
                    "source_id": asset.source_id,
                    "source_title": asset.title,
                    "evidence_url": f"/video-notes/{note.id}",
                }
            )
    return result
