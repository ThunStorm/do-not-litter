"""Append-only temporal projection replay from an explicitly selected immutable Map."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256

from sqlalchemy import select

from zhijian.db.models import GroundedMapArtifact, VideoCoverAsset
from zhijian.services.temporal_context import (
    VERSION,
    candidate_contexts,
    recover_source_membership,
    validate_applications,
)


def replay_temporal_map(db, source, asset, transcript, segments, cover):
    if (
        source.video_asset_id != asset.id
        or source.transcript_id != transcript.id
        or source.transcript_version != transcript.version
    ):
        raise ValueError("EXPLICIT_SOURCE_MAP_IDENTITY_MISMATCH")
    from zhijian.services.cover_text import cover_contexts
    from zhijian.services.grounded_map import _content_hash

    if source.content_hash != _content_hash(segments) or any(
        s.snapshot_id != transcript.metadata_json.get("snapshot_id") for s in segments
    ):
        raise ValueError("SOURCE_TRANSCRIPT_CONTENT_CHANGED")
    if cover.get("contexts"):
        image = db.get(VideoCoverAsset, cover.get("cover_id"))
        if not image or image.video_asset_id != asset.id or image.content_hash != cover.get("cover_hash"):
            raise ValueError("COVER_SOURCE_IDENTITY_MISMATCH")
        checked = cover_contexts(cover)
        keys = [
            "raw_time_text",
            "source_text",
            "scope",
            "scope_terms",
            "intent",
            "purpose",
            "activity",
            "regions",
        ]
        if [{k: c.get(k) for k in keys} for c in checked] != [
            {k: c.get(k) for k in keys} for c in cover["contexts"]
        ]:
            raise ValueError("COVER_CONTEXT_NOT_SUPPORTED_BY_REGIONS")
    contexts = candidate_contexts(segments) + cover.get("contexts", [])
    identity = sha256(
        json.dumps(
            [
                source.id,
                source.semantic_hash,
                VERSION,
                cover.get("semantic_identity", cover["identity"]),
                "temporal-replay-v2-review",
            ],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = db.scalar(select(GroundedMapArtifact).where(GroundedMapArtifact.semantic_hash == identity))
    if existing:
        return existing
    entities = deepcopy(source.entities_json)
    units = deepcopy(source.content_units_json)
    recover_source_membership(entities, units, contexts, segments)
    apps = []
    for e in entities:
        e["verified_temporal_applications"] = validate_applications(e, units, contexts, segments)
        e["temporal_artifact_hash"] = identity
        apps.extend(e["verified_temporal_applications"])
    from zhijian.services.temporal_context import unresolved_temporal_evidence

    options = {
        **deepcopy(source.semantic_options_json),
        "unresolved_temporal_evidence": unresolved_temporal_evidence(segments, source.claims_json),
        "temporal_context_version": VERSION,
        "temporal_contexts": contexts,
        "temporal_applications": apps,
        "cover_text": deepcopy(cover),
        "cover_text_identity": cover.get("semantic_identity", cover["identity"]),
        "temporal_replay": {
            "source_artifact_id": source.id,
            "kind": "DETERMINISTIC_SOURCE_REPLAY",
            "new_model_calls": 0,
            "source_provider": source.provider,
            "source_model": source.model,
        },
    }
    result = GroundedMapArtifact(
        video_asset_id=asset.id,
        transcript_id=transcript.id,
        transcript_version=transcript.version,
        content_hash=source.content_hash,
        semantic_hash=identity,
        prompt_version=source.prompt_version,
        supplement_hash=source.supplement_hash,
        domain=source.domain,
        domain_pack_version=source.domain_pack_version,
        provider="deterministic-replay",
        model=source.model,
        semantic_options_json=options,
        facts_json=deepcopy(source.facts_json),
        places_json=deepcopy(source.places_json),
        content_units_json=units,
        entities_json=entities,
        relations_json=deepcopy(source.relations_json),
        claims_json=deepcopy(source.claims_json),
        warnings_json=deepcopy(source.warnings_json),
        producer_version=source.producer_version,
    )
    db.add(result)
    db.commit()
    return result


def append_projection_note_version(db, note, source_version, artifact, mentions):
    """Append a metadata projection revision while preserving the saved model prose and old identities."""
    from sqlalchemy import func

    from zhijian.db.models import AINoteSection, AINoteVersion, PlaceMention, VideoAsset
    from zhijian.services.video_note_search import sync_video_note_search_index

    original = db.get(GroundedMapArtifact, source_version.grounded_map_artifact_id)
    if (
        note.current_version_id != source_version.id
        or not original
        or artifact.video_asset_id != note.video_asset_id
        or artifact.transcript_id != original.transcript_id
        or artifact.content_hash != original.content_hash
        or artifact.claims_json != original.claims_json
        or artifact.facts_json != original.facts_json
    ):
        raise ValueError("NOTE_REPLAY_REQUIRES_IDENTICAL_EXPLICIT_FACT_SOURCE")
    old_mentions = list(
        db.scalars(select(PlaceMention).where(PlaceMention.ai_note_version_id == source_version.id))
    )
    new_by_entity = {(m.metadata_json or {}).get("semantic", {}).get("entity_id"): m for m in mentions}
    mapping = {}
    for old in old_mentions:
        entity = (old.metadata_json or {}).get("semantic", {}).get("entity_id")
        if entity in new_by_entity:
            mapping[old.id] = new_by_entity[entity].id
    sections = list(
        db.scalars(select(AINoteSection).where(AINoteSection.ai_note_version_id == source_version.id))
    )
    if any(mid not in mapping for section in sections for mid in section.place_mention_ids_json):
        raise ValueError("NOTE_REPLAY_MENTION_IDENTITY_MISMATCH")
    values = {
        c.name: deepcopy(getattr(source_version, c.name))
        for c in AINoteVersion.__table__.columns
        if c.name not in {"id", "created_at", "updated_at", "version", "grounded_map_artifact_id"}
    }
    values["warnings_json"] = [
        *source_version.warnings_json,
        f"时节依据投影更新，正文复用已保存模型输出；来源版本：{source_version.id}，没有新增模型调用。",
    ]
    values["prompt_version"] = "temporal-note-projection-v1"
    result = AINoteVersion(
        **values,
        version=(
            db.scalar(select(func.max(AINoteVersion.version)).where(AINoteVersion.ai_note_id == note.id)) or 0
        )
        + 1,
        grounded_map_artifact_id=artifact.id,
    )
    db.add(result)
    db.flush()
    for section in sections:
        fields = {
            c.name: deepcopy(getattr(section, c.name))
            for c in AINoteSection.__table__.columns
            if c.name not in {"id", "ai_note_version_id", "place_mention_ids_json", "anchor_id"}
        }
        new = AINoteSection(
            **fields,
            ai_note_version_id=result.id,
            place_mention_ids_json=[mapping[mid] for mid in section.place_mention_ids_json],
            anchor_id="",
        )
        db.add(new)
        db.flush()
        new.anchor_id = "section-" + new.id
    for mention in old_mentions:
        if mention.extraction_status == "EXTRACTED":
            mention.extraction_status = "SUPERSEDED"
    for mention in mentions:
        mention.ai_note_version_id = result.id
    note.current_version_id = result.id
    sync_video_note_search_index(db, note, result, db.get(VideoAsset, note.video_asset_id))
    db.commit()
    return result
