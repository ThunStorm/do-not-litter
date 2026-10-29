"""Canonical, profile-independent semantic maps for video transcripts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.budget import remaining_ai_wall_seconds
from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.job_config import job_video_note_chunk_chars
from zhijian.ai.policies import stage_attempt_limit
from zhijian.ai.reliability import AIProviderError
from zhijian.ai.runtime_hints import read_runtime_hint, runtime_hint_scope, tighten_runtime_hint
from zhijian.ai.stage_decision import decide_stage, record_stage_decision
from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import GroundedMapArtifact, Job, JobStep, Segment, Transcript, VideoAsset
from zhijian.providers.llm import FallbackLLMProvider, LLMResult
from zhijian.services.audit import record_event
from zhijian.services.jobs import ensure_job_active
from zhijian.services.title_temporal import title_identity

MAP_PROMPT_VERSION = "semantic-map-v9-cover-membership"
MAP_ARTIFACT_SCHEMA_VERSION = "grounded-map-v3"
LOCAL_MAP_CHUNK_CHARS = 6_000
LOCAL_MAP_CHUNK_SEGMENTS = 64
DOWNSTREAM_JOB_RESERVE_SECONDS = 600
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
        evidence = value.get("recommendation_evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("statements"), list):
            entity_id = str(value.get("entity_id") or f"entity-{chunk[0].id}-{index}")
            evidence = {
                **evidence,
                "statements": [
                    {
                        **statement,
                        "statement_id": f"{entity_id}:{statement.get('statement_id', '')}",
                        "supersedes": [f"{entity_id}:{sid}" for sid in statement.get("supersedes", [])],
                    }
                    if isinstance(statement, dict)
                    else statement
                    for statement in evidence["statements"]
                ],
            }
        entities.append(
            {
                **value,
                "recommendation_evidence": evidence,
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
                "route": value.get("route") if isinstance(value.get("route"), dict) else None,
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
    has_fallback = (
        isinstance(provider, FallbackLLMProvider)
        and provider.fallback is not None
        and bool(provider.fallback_model)
    )
    if job and isinstance(provider, FallbackLLMProvider):
        provider.before_fallback = lambda: ensure_job_active(db, job)
    from zhijian.services.cover_text import extract_cover_text
    from zhijian.services.temporal_context import (
        VERSION,
        candidate_contexts,
        contexts_for_chunk,
        validate_applications,
    )

    cover_evidence = extract_cover_text(db, settings, asset, job)
    temporal_contexts = candidate_contexts(segments) + cover_evidence.get("contexts", [])
    content_hash = _content_hash(segments)
    supplement_hash = prompt_supplement_hash(db, "travel_place_extraction", job)
    _, domain_versions = domain_context_messages(
        db, policy.domain_pack_ids, AICapability.STRUCTURED_EXTRACTION, job
    )
    domain_pack_version = domain_context_hash(domain_versions)
    semantic_options = {
        "travel_semantics_version": "travel-semantics-v2",
        "temporal_parser_version": "map-timing-v4",
        "temporal_context_version": VERSION,
        "cover_text_identity": cover_evidence.get("semantic_identity", cover_evidence["identity"]),
        "route_parser_version": "route-guide-v2-prose",
        "temperature": policy.temperature,
        "max_output_tokens": policy.max_output_tokens,
        "thinking": policy.thinking,
        "domain": policy.domain or "travel",
        "domain_pack_ids": list(policy.domain_pack_ids),
        "domain_context_hash": domain_pack_version,
        "provider_execution_scope": runtime_hint_scope(provider, model),
        "execution_mode": policy.execution_mode,
        "escalation_threshold": policy.escalation_threshold,
    }
    semantic_hash = sha256(
        json.dumps(
            {
                "transcript_id": transcript.id,
                "transcript_version": transcript.version,
                "content_hash": content_hash,
                **title_identity(asset.title),
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
    chunk_chars = int(policy.chunk_size or job_video_note_chunk_chars(job, settings.video_note_chunk_chars))
    max_segments = None
    if provider_name.lower() == "ollama":
        chunk_chars = min(chunk_chars, LOCAL_MAP_CHUNK_CHARS)
        output_tokens = int(
            getattr(getattr(provider, "request_options", None), "max_output_tokens", None)
            or policy.max_output_tokens
            or 4096
        )
        # Rich entity/claim JSON needs substantially more output than raw text;
        # the configured input size is an upper bound, not a required batch size.
        max_segments = min(LOCAL_MAP_CHUNK_SEGMENTS, max(1, (output_tokens - 1024) // 192))
    hint_scope = runtime_hint_scope(provider, model)
    saved_hint = read_runtime_hint(db, "GROUND_MAP", model, scope=hint_scope)
    if saved_hint.get("safe_max_chars"):
        # Runtime hints count transcript text; _transcript_chunks adds 80 chars per Segment.
        hint_segments = int(saved_hint.get("safe_max_segments") or 1)
        chunk_chars = min(chunk_chars, int(saved_hint["safe_max_chars"]) + 80 * hint_segments)
    if saved_hint.get("safe_max_segments"):
        max_segments = min(max_segments or len(segments), saved_hint["safe_max_segments"])
    chunks = _transcript_chunks(segments, chunk_chars, max_segments=max_segments)
    planned_calls = max(1, len(chunks))
    stage_started = perf_counter()
    logical_attempts = 0
    fallback_requests = 0
    local_chunk_durations: list[float] = []
    completed_chars = 0
    total_chars = max(1, sum(len(segment.corrected_text or segment.text) for segment in segments))

    def request_chunk(
        chunk: list[Segment],
        *,
        chunk_index: int,
        chunk_count: int,
        split_path: str = "root",
        fallback_only: bool = False,
    ) -> None:
        nonlocal completed_chars, logical_attempts, fallback_requests, planned_calls
        if policy.wall_time_seconds and perf_counter() - stage_started >= policy.wall_time_seconds:
            raise AIProviderError(
                "AI_STAGE_WALL_TIME_EXCEEDED", "证据地图已达到阶段总时限", switch_model=False
            )
        attempt_limit = stage_attempt_limit(policy.max_attempts, planned_calls)
        if attempt_limit and logical_attempts >= attempt_limit:
            raise AIProviderError("AI_PROVIDER_ATTEMPT_BUDGET", "证据地图已达到尝试上限", switch_model=False)
        logical_attempts += 1
        if fallback_only:
            fallback_requests += 1
        text = "\n".join(
            f"[segment:{segment.id} {segment.locator_json.get('start_ms', 0)}-"
            f"{segment.locator_json.get('end_ms', 0)}ms] "
            f"{segment.corrected_text or segment.text}"
            for segment in chunk
        )
        context_text = "\n推荐主题来源注册表（只读，不能作为当前分块新地点）：\n"
        by_id = {s.id: s for s in segments}
        request_contexts = contexts_for_chunk(temporal_contexts, segments, chunk)
        for context in request_contexts:
            if context.get("source_kind") == "COVER_TEXT":
                context_text += (
                    "COVER_TEXT(独立封面文字，无转写Segment)："
                    + json.dumps(
                        {
                            k: context[k]
                            for k in [
                                "context_id",
                                "source_kind",
                                "source_text",
                                "raw_time_text",
                                "cover_hash",
                                "scope",
                                "scope_terms",
                                "intent",
                            ]
                            if k in context
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                continue
            context_text += f"context_id={context['context_id']} 时间原词={context['raw_time_text']}\n"
            for sid in context["segment_ids"]:
                source = by_id[sid]
                context_text += (
                    f"[segment:{sid} {source.locator_json.get('start_ms', 0)}-"
                    f"{source.locator_json.get('end_ms', 0)}ms] "
                    f"{source.corrected_text or source.text}\n"
                )
        messages = [
            {"role": "system", "content": prompt},
            *prompt_supplement_messages(db, "travel_place_extraction", job),
            {
                "role": "user",
                "content": (
                    f"视频标题：{asset.title}\n分块：{chunk_index}/{chunk_count}\n{text}{context_text}"
                ),
            },
        ]

        def validate_evidence(result: LLMResult) -> None:
            payload = parse_model_json(result.content)
            accepted = _canonical_payload(payload, chunk)
            allowed_contexts = {c["context_id"] for c in request_contexts}
            for entity in accepted[4]:
                for app in entity.get("temporal_applications", []) or []:
                    if not isinstance(app, dict) or app.get("context_id") not in allowed_contexts:
                        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "主题引用不在本分块来源注册表")
            collections = ("entities", "claims") if "entities" in payload else ("section_facts", "places")
            counts = (
                (len(accepted[4]), len(accepted[6]))
                if "entities" in payload
                else (len(accepted[0]), len(accepted[1]))
            )
            rejected = sum(
                max(0, len(payload.get(name, [])) - count)
                for name, count in zip(collections, counts, strict=True)
            )
            result.metadata.update(
                rejected_items=rejected, acceptance="PARTIAL_ACCEPTED" if rejected else "ACCEPTED"
            )

        try:
            response = _cached_stage_json(
                db,
                job=job,
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider=provider,
                provider_name=(
                    str(getattr(provider.fallback, "name", ""))
                    if fallback_only and isinstance(provider, FallbackLLMProvider)
                    else provider_name
                ),
                model=(
                    str(provider.fallback_model)
                    if fallback_only and isinstance(provider, FallbackLLMProvider)
                    else model
                ),
                messages=messages,
                result_validator=validate_evidence,
                request_segments=segments,
                stage_deadline=stage_started + policy.wall_time_seconds if policy.wall_time_seconds else None,
                fallback_only=fallback_only,
                attempt_metadata={
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                    "planned_calls": planned_calls,
                    "split_path": split_path,
                    "segment_count": len(chunk),
                },
            )
        except AIProviderError as exc:
            if exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED":
                raise
            if len(chunk) <= 1:
                if fallback_only or not has_fallback:
                    raise
                request_chunk(
                    chunk,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    split_path=split_path,
                    fallback_only=True,
                )
                return
            else:
                midpoint = len(chunk) // 2
                planned_calls += 1
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
                    scope=hint_scope,
                )
                if job:
                    hints = dict(job.payload_json.get("ai_runtime_hints") or {})
                    model_hints = dict(hints.get("ground_map") or {})
                    model_hints[hint_scope] = {"model": model, **persisted, "reason": exc.code}
                    hints["ground_map"] = model_hints
                    job.payload_json = {**job.payload_json, "ai_runtime_hints": hints}
                    db.commit()
                next_fallback = fallback_only or has_fallback
                request_chunk(
                    chunk[:midpoint],
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    split_path=f"{split_path}.L",
                    fallback_only=next_fallback,
                )
                request_chunk(
                    chunk[midpoint:],
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    split_path=f"{split_path}.R",
                    fallback_only=next_fallback,
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

    planned_chunks = chunks or [segments]
    prefer_fallback = False
    for index, chunk in enumerate(planned_chunks, start=1):
        chunk_started = perf_counter()
        previous_fallback_requests = fallback_requests
        request_chunk(
            chunk, chunk_index=index, chunk_count=len(planned_chunks), fallback_only=prefer_fallback
        )
        if fallback_requests == previous_fallback_requests:
            local_chunk_durations.append(perf_counter() - chunk_started)
        if (
            job
            and job.started_at
            and not prefer_fallback
            and len(local_chunk_durations) >= 2
            and index < len(planned_chunks)
            and has_fallback
        ):
            projected = min(local_chunk_durations) * (len(planned_chunks) - index)
            available = remaining_ai_wall_seconds(db, job) - DOWNSTREAM_JOB_RESERVE_SECONDS
            if policy.wall_time_seconds:
                available = min(available, policy.wall_time_seconds - (perf_counter() - stage_started))
            if projected > available:
                prefer_fallback = True
                record_event(
                    db,
                    "ground_map.route.escalated",
                    "本地证据地图预计无法在剩余预算内完成，后续分块改用备用模型",
                    component="video-pipeline",
                    level="WARNING",
                    entity_type="job",
                    entity_id=job.id,
                    detail={
                        "remaining_chunks": len(planned_chunks) - index,
                        "projected_seconds": round(projected),
                        "available_seconds": round(available),
                    },
                )

    remote_escalation_count = 0
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
                        *prompt_supplement_messages(db, "travel_place_extraction", job),
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
                        "planned_calls": planned_calls + 1,
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
                remote_escalation_count += 1
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
    semantic_options["fallback_chunk_count"] = fallback_requests
    semantic_options["remote_escalation_count"] = remote_escalation_count

    from zhijian.services.route_guides import extract_routes

    semantic_options["route_guides"] = extract_routes(
        claims, {segment.id: segment.corrected_text or segment.text for segment in segments}, entities
    )
    from zhijian.services.temporal_context import unresolved_temporal_evidence

    semantic_options["unresolved_temporal_evidence"] = unresolved_temporal_evidence(segments, claims)
    semantic_options["cover_text"] = cover_evidence
    semantic_options["temporal_contexts"] = temporal_contexts
    from zhijian.services.temporal_context import recover_source_membership

    recover_source_membership(entities, content_units, temporal_contexts, segments)
    semantic_options["temporal_applications"] = []
    for entity in entities:
        apps = validate_applications(entity, content_units, temporal_contexts, segments)
        entity["verified_temporal_applications"] = apps
        entity["temporal_artifact_hash"] = semantic_hash
        semantic_options["temporal_applications"].extend(apps)
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
