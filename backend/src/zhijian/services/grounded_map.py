"""Canonical, profile-independent semantic maps for video transcripts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.reliability import AIProviderError
from zhijian.ai.runtime_hints import read_runtime_hint, tighten_runtime_hint
from zhijian.ai.stage_decision import decide_stage, record_stage_decision
from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import GroundedMapArtifact, Job, JobStep, Segment, Transcript, VideoAsset
from zhijian.providers.llm import FallbackLLMProvider
from zhijian.services.audit import record_event

MAP_PROMPT_VERSION = "semantic-map-v3"
MAP_ARTIFACT_SCHEMA_VERSION = "grounded-map-v3"
LOCAL_MAP_CHUNK_CHARS = 6_000
LOCAL_MAP_CHUNK_SEGMENTS = 64
UNIT_TYPES = {
    "AREA_GUIDE",
    "PLACE_GUIDE",
    "MULTI_PLACE_LIST",
    "ROUTE",
    "THEME",
    "CATEGORY_COMPARE",
    "EXPERIENCE",
    "FOOD",
    "MIXED",
    "SUPPLEMENTAL",
}
SUBJECT_ROLES = {"PRIMARY", "SECONDARY", "REFERENCE", "CONTEXT"}
VISIT_INTENTS = {"RECOMMENDED", "OPTIONAL", "NEUTRAL", "NOT_RECOMMENDED", "NOT_APPLICABLE"}
POI_POLICIES = {"RESOLVE", "AREA_RESOLVE", "REFERENCE_ONLY", "SKIP"}


def _content_hash(segments: list[Segment]) -> str:
    payload = [{"id": segment.id, "text": segment.corrected_text or segment.text} for segment in segments]
    return sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _quote_is_grounded(quote: object, ids: list[str], texts: dict[str, str]) -> bool:
    compact = "".join(str(quote or "").split())
    evidence = "".join("".join(texts.get(item, "").split()) for item in ids)
    return bool(compact and compact in evidence)


def _canonical_payload(
    payload: dict[str, Any], chunk: list[Segment]
) -> tuple[list[dict], list[dict], list[str], list[dict], list[dict], list[dict], list[dict]]:
    """Validate Semantic Map v3 and retain old facts/places as compatibility projections."""
    valid_ids = {segment.id for segment in chunk}
    texts = {segment.id: str(segment.corrected_text or segment.text) for segment in chunk}
    facts: list[dict] = []
    for value in payload.get("section_facts", []):
        if not isinstance(value, dict):
            continue
        ids = [str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids]
        quotes = [
            str(item) for item in value.get("supporting_quotes", []) if _quote_is_grounded(item, ids, texts)
        ]
        if ids and quotes:
            facts.append(
                {
                    "summary": str(value.get("summary") or "")[:1000],
                    "key_points": [str(item)[:500] for item in value.get("key_points", []) if item][:12],
                    "supporting_quotes": quotes[:8],
                    "segment_ids": ids,
                }
            )
    places: list[dict] = []
    for value in payload.get("places", []):
        if not isinstance(value, dict):
            continue
        ids = [str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids]
        raw_name = str(value.get("raw_name") or value.get("name") or "").strip()
        if raw_name and ids and _quote_is_grounded(value.get("quote"), ids, texts):
            places.append({**value, "raw_name": raw_name[:300], "segment_ids": ids})
    warnings = [str(item)[:300] for item in payload.get("warnings", []) if item][:20]
    unit_default = f"unit-{chunk[0].id}" if chunk else "unit-unknown"
    entities: list[dict] = []
    entity_values = payload.get("entities") if isinstance(payload.get("entities"), list) else places
    for index, value in enumerate(entity_values):
        if not isinstance(value, dict):
            continue
        ids = [str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids]
        raw_name = str(value.get("raw_name") or value.get("name") or "").strip()
        quote = str(value.get("quote") or "").strip()
        if not (raw_name and ids and _quote_is_grounded(quote, ids, texts)):
            continue
        policy = str(value.get("poi_policy") or "RESOLVE").upper()
        role = str(value.get("subject_role") or "PRIMARY").upper()
        intent = str(value.get("visit_intent") or "NEUTRAL").upper()
        entities.append(
            {
                **value,
                "entity_id": str(value.get("entity_id") or f"entity-{chunk[0].id}-{index}")[:96],
                "content_unit_id": str(value.get("content_unit_id") or unit_default)[:96],
                "raw_name": raw_name[:300],
                "name": str(value.get("name") or value.get("canonical_hint") or raw_name)[:300],
                "canonical_hint": str(value.get("canonical_hint") or value.get("name") or raw_name)[:300],
                "entity_type": str(value.get("entity_type") or "PLACE").upper(),
                "place_type": str(value.get("place_type") or "UNKNOWN").upper(),
                "subject_role": role if role in SUBJECT_ROLES else "CONTEXT",
                "visit_intent": intent if intent in VISIT_INTENTS else "NOT_APPLICABLE",
                "poi_policy": policy if policy in POI_POLICIES else "SKIP",
                "segment_ids": ids,
                "quote": quote[:1000],
                "confidence": float(value.get("confidence") or 0),
            }
        )
    units: list[dict] = []
    unit_values = payload.get("content_units") if isinstance(payload.get("content_units"), list) else []
    seen_units: set[str] = set()
    for _index, value in enumerate(unit_values):
        if not isinstance(value, dict):
            continue
        unit_id = str(value.get("content_unit_id") or value.get("unit_id") or "")[:96]
        ids = [str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids]
        if not unit_id or not ids or unit_id in seen_units:
            continue
        seen_units.add(unit_id)
        unit_type = str(value.get("unit_type") or "MIXED").upper()
        units.append(
            {
                "content_unit_id": unit_id,
                "unit_type": unit_type if unit_type in UNIT_TYPES else "MIXED",
                "topic": str(value.get("topic") or "")[:500],
                "anchor_entity_ids": [str(item)[:96] for item in value.get("anchor_entity_ids", []) if item][
                    :20
                ],
                "segment_ids": ids,
            }
        )
    for entity in entities:
        if entity["content_unit_id"] not in seen_units:
            seen_units.add(entity["content_unit_id"])
            units.append(
                {
                    "content_unit_id": entity["content_unit_id"],
                    "unit_type": "MIXED",
                    "topic": "",
                    "anchor_entity_ids": [],
                    "segment_ids": entity["segment_ids"],
                }
            )
    entity_ids = {item["entity_id"] for item in entities}
    relations: list[dict] = []
    for value in payload.get("relations", []) if isinstance(payload.get("relations"), list) else []:
        if not isinstance(value, dict):
            continue
        source_id = str(value.get("source_entity_id") or "")
        target_id = str(value.get("target_entity_id") or "")
        if source_id in entity_ids and target_id in entity_ids:
            relations.append(
                {
                    "relation_type": str(value.get("relation_type") or "RELATED")[:64],
                    "source_entity_id": source_id,
                    "target_entity_id": target_id,
                    "segment_ids": [
                        str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids
                    ],
                }
            )
    claims: list[dict] = []
    claim_values = payload.get("claims") if isinstance(payload.get("claims"), list) else facts
    for index, value in enumerate(claim_values):
        if not isinstance(value, dict):
            continue
        ids = [str(item) for item in value.get("segment_ids", []) if str(item) in valid_ids]
        quote = str(
            value.get("supporting_quote") or next(iter(value.get("supporting_quotes", [])), "")
        ).strip()
        text = str(value.get("text") or value.get("summary") or "").strip()
        if not (ids and text and _quote_is_grounded(quote, ids, texts)):
            continue
        claims.append(
            {
                "claim_id": str(value.get("claim_id") or f"claim-{chunk[0].id}-{index}")[:96],
                "content_unit_id": str(value.get("content_unit_id") or unit_default)[:96],
                "subject_entity_ids": [
                    str(item)[:96] for item in value.get("subject_entity_ids", []) if item
                ][:20],
                "claim_type": str(value.get("claim_type") or "OTHER")[:64],
                "text": text[:1000],
                "importance": str(value.get("importance") or "MEDIUM")[:32],
                "segment_ids": ids,
                "supporting_quote": quote[:1000],
            }
        )
    return facts, places, warnings, units, entities, relations, claims


def _semantic_escalation_reasons(entities: list[dict], threshold: float = 0.6) -> dict[str, list[str]]:
    """Select only uncertain entity evidence for a remote refinement, never the whole transcript."""
    by_name: dict[str, set[str]] = {}
    for entity in entities:
        by_name.setdefault(str(entity.get("raw_name") or ""), set()).add(
            str(entity.get("content_unit_id") or "")
        )
    result: dict[str, list[str]] = {}
    for entity in entities:
        reasons: list[str] = []
        if float(entity.get("confidence") or 0) < threshold:
            reasons.append("LOW_CONFIDENCE")
        if entity.get("subject_role") == "CONTEXT" and entity.get("poi_policy") == "RESOLVE":
            reasons.append("ROLE_POLICY_CONFLICT")
        if len(by_name.get(str(entity.get("raw_name") or ""), set())) > 1:
            reasons.append("CROSS_UNIT_ENTITY")
        if reasons:
            result[str(entity["entity_id"])] = reasons
    return result


def _escalation_segments(
    segments: list[Segment], entities: list[dict], entity_ids: set[str]
) -> list[Segment]:
    target_ids = {
        str(segment_id)
        for entity in entities
        if str(entity.get("entity_id") or "") in entity_ids
        for segment_id in entity.get("segment_ids", [])
    }
    positions = {segment.id: index for index, segment in enumerate(segments)}
    indexes = {
        neighbor
        for segment_id in target_ids
        if segment_id in positions
        for neighbor in range(
            max(0, positions[segment_id] - 2), min(len(segments), positions[segment_id] + 3)
        )
    }
    return [segment for index, segment in enumerate(segments) if index in indexes]


def artifact_for_transcript(db: Session, transcript: Transcript) -> GroundedMapArtifact | None:
    return db.scalar(
        select(GroundedMapArtifact)
        .where(
            GroundedMapArtifact.transcript_id == transcript.id,
            GroundedMapArtifact.transcript_version == transcript.version,
        )
        .order_by(GroundedMapArtifact.created_at.desc())
    )


def get_or_create_grounded_map(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    transcript: Transcript,
    segments: list[Segment],
    job: Job | None = None,
) -> GroundedMapArtifact:
    # Import at execution time: video_support owns Provider policy and cache wiring.
    from zhijian.services.video_support import (
        ProviderUnavailable,
        _cached_stage_json,
        _resolved_stage_policy,
        _transcript_chunks,
        parse_model_json,
        prompt_supplement_hash,
        prompt_supplement_messages,
        provider_for_role,
    )

    policy = _resolved_stage_policy(db, "GROUND_MAP", job)
    provider, provider_name, model = provider_for_role(db, settings, "grounded_map", job)
    content_hash = _content_hash(segments)
    supplement_hash = prompt_supplement_hash(db, "travel_place_extraction")
    _, domain_versions = domain_context_messages(
        db, policy.domain_pack_ids, AICapability.STRUCTURED_EXTRACTION
    )
    domain_pack_version = domain_context_hash(domain_versions)
    semantic_options = {
        "temperature": policy.temperature,
        "max_output_tokens": policy.max_output_tokens,
        "thinking": policy.thinking,
        "domain": policy.domain or "travel",
        "domain_pack_ids": list(policy.domain_pack_ids),
        "domain_context_hash": domain_pack_version,
    }
    semantic_hash = sha256(
        json.dumps(
            {
                "transcript_id": transcript.id,
                "transcript_version": transcript.version,
                "content_hash": content_hash,
                "prompt_version": MAP_PROMPT_VERSION,
                "schema_version": MAP_ARTIFACT_SCHEMA_VERSION,
                "supplement_hash": supplement_hash,
                "semantic_options": semantic_options,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = db.scalar(
        select(GroundedMapArtifact).where(GroundedMapArtifact.semantic_hash == semantic_hash)
    )
    estimated_tokens = sum(len(segment.corrected_text or segment.text) for segment in segments) // 4
    record_stage_decision(
        db,
        job,
        decide_stage(
            "GROUND_MAP",
            reusable=existing is not None,
            has_relevant_segments=bool(segments),
            estimated_tokens=estimated_tokens,
        ),
    )
    if existing is not None:
        db.commit()
        return existing

    prompt = (Path(__file__).resolve().parents[1] / "prompts" / "grounded_map.md").read_text(encoding="utf-8")
    facts: list[dict] = []
    places: list[dict] = []
    warnings: list[str] = []
    content_units: list[dict] = []
    entities: list[dict] = []
    relations: list[dict] = []
    claims: list[dict] = []
    chunk_chars = int(policy.chunk_size or settings.video_note_chunk_chars)
    max_segments = None
    if provider_name.lower() == "ollama" and policy.chunk_size is None:
        chunk_chars = min(chunk_chars, LOCAL_MAP_CHUNK_CHARS)
        max_segments = LOCAL_MAP_CHUNK_SEGMENTS
    saved_hint = read_runtime_hint(db, "GROUND_MAP", model)
    if saved_hint.get("safe_max_chars"):
        chunk_chars = min(chunk_chars, saved_hint["safe_max_chars"])
    if saved_hint.get("safe_max_segments"):
        max_segments = min(max_segments or len(segments), saved_hint["safe_max_segments"])
    chunks = _transcript_chunks(segments, chunk_chars, max_segments=max_segments)
    stage_started = perf_counter()
    logical_attempts = 0
    completed_chars = 0
    total_chars = max(1, sum(len(segment.corrected_text or segment.text) for segment in segments))

    def request_chunk(
        chunk: list[Segment], *, chunk_index: int, chunk_count: int, split_path: str = "root"
    ) -> None:
        nonlocal completed_chars, logical_attempts
        if policy.wall_time_seconds and perf_counter() - stage_started >= policy.wall_time_seconds:
            raise AIProviderError(
                "AI_STAGE_WALL_TIME_EXCEEDED", "证据地图已达到阶段总时限", switch_model=False
            )
        if policy.max_attempts and logical_attempts >= policy.max_attempts:
            raise AIProviderError("AI_PROVIDER_ATTEMPT_BUDGET", "证据地图已达到尝试上限", switch_model=False)
        logical_attempts += 1
        text = "\n".join(
            f"[segment:{segment.id} {segment.locator_json.get('start_ms', 0)}-"
            f"{segment.locator_json.get('end_ms', 0)}ms] "
            f"{segment.corrected_text or segment.text}"
            for segment in chunk
        )
        messages = [
            {"role": "system", "content": prompt},
            *prompt_supplement_messages(db, "travel_place_extraction"),
            {
                "role": "user",
                "content": f"视频标题：{asset.title}\n分块：{chunk_index}/{chunk_count}\n{text}",
            },
        ]
        try:
            response = _cached_stage_json(
                db,
                job=job,
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=messages,
                attempt_metadata={
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                    "split_path": split_path,
                    "segment_count": len(chunk),
                },
            )
        except AIProviderError as exc:
            if exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED":
                raise
            if len(chunk) <= 1:
                if not isinstance(provider, FallbackLLMProvider):
                    raise
                response = provider.generate_fallback_json(messages)
            else:
                midpoint = len(chunk) // 2
                safe_max_chars = max(
                    sum(len(item.corrected_text or item.text) for item in part)
                    for part in (chunk[:midpoint], chunk[midpoint:])
                )
                persisted = tighten_runtime_hint(
                    db,
                    "GROUND_MAP",
                    model,
                    safe_max_chars=max(1, safe_max_chars),
                    safe_max_segments=midpoint,
                )
                if job:
                    hints = dict(job.payload_json.get("ai_runtime_hints") or {})
                    model_hints = dict(hints.get("ground_map") or {})
                    model_hints[model] = {**persisted, "reason": exc.code}
                    hints["ground_map"] = model_hints
                    job.payload_json = {**job.payload_json, "ai_runtime_hints": hints}
                    db.commit()
                request_chunk(
                    chunk[:midpoint],
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    split_path=f"{split_path}.L",
                )
                request_chunk(
                    chunk[midpoint:],
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    split_path=f"{split_path}.R",
                )
                return
        (
            chunk_facts,
            chunk_places,
            chunk_warnings,
            chunk_units,
            chunk_entities,
            chunk_relations,
            chunk_claims,
        ) = _canonical_payload(parse_model_json(response.content), chunk)
        facts.extend(chunk_facts)
        places.extend(chunk_places)
        warnings.extend(chunk_warnings)
        content_units.extend(chunk_units)
        entities.extend(chunk_entities)
        relations.extend(chunk_relations)
        claims.extend(chunk_claims)
        completed_chars += sum(len(segment.corrected_text or segment.text) for segment in chunk)
        if job:
            step = db.scalar(
                select(JobStep).where(
                    JobStep.job_id == job.id,
                    JobStep.step_name == "EXTRACT_TRAVEL_FACTS",
                )
            )
            if step:
                step.progress = min(99, round(completed_chars / total_chars * 100))
                job.heartbeat_at = utc_now()
                db.commit()

    for index, chunk in enumerate(chunks or [segments], start=1):
        request_chunk(chunk, chunk_index=index, chunk_count=max(1, len(chunks)))

    escalation_reasons = _semantic_escalation_reasons(entities, float(policy.escalation_threshold or 0.6))
    if job and provider_name.lower() == "ollama" and escalation_reasons:
        target_entity_ids = set(list(escalation_reasons)[:8])
        target_segments = _escalation_segments(segments, entities, target_entity_ids)
        if target_segments:
            try:
                remote_provider, remote_name, remote_model = provider_for_role(
                    db, settings, "grounded_map_escalation", job
                )
                local_hypotheses = [
                    item for item in entities if str(item.get("entity_id") or "") in target_entity_ids
                ]
                target_text = "\n".join(
                    f"[segment:{segment.id} {segment.locator_json.get('start_ms', 0)}-"
                    f"{segment.locator_json.get('end_ms', 0)}ms] {segment.corrected_text or segment.text}"
                    for segment in target_segments
                )
                escalation_json = json.dumps(escalation_reasons, ensure_ascii=False)
                hypotheses_json = json.dumps(local_hypotheses, ensure_ascii=False)
                refined = _cached_stage_json(
                    db,
                    job=job,
                    stage="GROUND_MAP",
                    capability="STRUCTURED_EXTRACTION",
                    provider=remote_provider,
                    provider_name=remote_name,
                    model=remote_model,
                    messages=[
                        {"role": "system", "content": prompt},
                        *prompt_supplement_messages(db, "travel_place_extraction"),
                        {
                            "role": "user",
                            "content": (
                                f"视频标题：{asset.title}\n仅校验以下歧义片段及本地假设；"
                                "不得扩展为完整转写。保留既有 entity_id。\n"
                                f"Remote escalation reasons：{escalation_json}\n"
                                f"Local hypotheses：{hypotheses_json}\n"
                                f"{target_text}"
                            ),
                        },
                    ],
                    attempt_metadata={
                        "semantic_escalation": True,
                        "entity_count": len(target_entity_ids),
                        "reason_codes": sorted(
                            {reason for values in escalation_reasons.values() for reason in values}
                        ),
                    },
                )
                (
                    _facts,
                    _places,
                    remote_warnings,
                    _units,
                    remote_entities,
                    _relations,
                    _claims,
                ) = _canonical_payload(parse_model_json(refined.content), target_segments)
                replacement = {str(item["entity_id"]): item for item in remote_entities}
                entities = [replacement.get(str(item["entity_id"]), item) for item in entities]
                warnings.extend(remote_warnings)
                record_event(
                    db,
                    "ai.remote_escalation",
                    "已对歧义语义实体执行小上下文远程校验",
                    component="video-pipeline",
                    entity_type="job",
                    entity_id=job.id,
                    detail={
                        "stage": "GROUND_MAP",
                        "entity_count": len(target_entity_ids),
                        "segment_count": len(target_segments),
                        "reasons": escalation_reasons,
                    },
                    commit=False,
                )
            except (AIProviderError, ProviderUnavailable) as exc:
                record_event(
                    db,
                    "ai.remote_escalation.unavailable",
                    "歧义语义实体的远程校验不可用，保留本地结果并进入保守后续流程",
                    component="video-pipeline",
                    level="WARNING",
                    entity_type="job",
                    entity_id=job.id,
                    detail={"stage": "GROUND_MAP", "reason": str(exc)[:240]},
                    commit=False,
                )
    semantic_options["semantic_entity_count"] = len(entities)
    semantic_options["semantic_actionable_count"] = sum(
        item.get("poi_policy") == "RESOLVE" for item in entities
    )
    semantic_options["semantic_reference_count"] = sum(
        item.get("poi_policy") in {"REFERENCE_ONLY", "SKIP"} for item in entities
    )
    semantic_options["semantic_unit_count"] = len(content_units)
    semantic_options["remote_escalation_count"] = int(
        bool(job and provider_name.lower() == "ollama" and escalation_reasons)
    )

    artifact = GroundedMapArtifact(
        video_asset_id=asset.id,
        transcript_id=transcript.id,
        transcript_version=transcript.version,
        content_hash=content_hash,
        semantic_hash=semantic_hash,
        prompt_version=MAP_PROMPT_VERSION,
        supplement_hash=supplement_hash,
        domain=str(semantic_options["domain"]),
        domain_pack_version=domain_pack_version,
        provider=provider_name,
        model=model,
        semantic_options_json=semantic_options,
        facts_json=facts,
        places_json=places,
        content_units_json=content_units,
        entities_json=entities,
        relations_json=relations,
        claims_json=claims,
        warnings_json=list(dict.fromkeys(warnings)),
        producer_version=MAP_ARTIFACT_SCHEMA_VERSION,
    )
    db.add(artifact)
    db.commit()
    return artifact
