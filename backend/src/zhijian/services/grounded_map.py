"""Canonical, profile-independent semantic maps for video transcripts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.reliability import AIProviderError
from zhijian.ai.stage_decision import decide_stage, record_stage_decision
from zhijian.core.config import Settings
from zhijian.db.models import GroundedMapArtifact, Job, Segment, Transcript, VideoAsset

MAP_PROMPT_VERSION = "grounded-map-v1"


def _content_hash(segments: list[Segment]) -> str:
    payload = [{"id": segment.id, "text": segment.corrected_text or segment.text} for segment in segments]
    return sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _quote_is_grounded(quote: object, ids: list[str], texts: dict[str, str]) -> bool:
    compact = "".join(str(quote or "").split())
    evidence = "".join("".join(texts.get(item, "").split()) for item in ids)
    return bool(compact and compact in evidence)


def _canonical_payload(
    payload: dict[str, Any], chunk: list[Segment]
) -> tuple[list[dict], list[dict], list[str]]:
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
    return facts, places, warnings


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
                "supplement_hash": supplement_hash,
                "provider": provider_name,
                "model": model,
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
    chunks = _transcript_chunks(segments, int(policy.chunk_size or settings.video_note_chunk_chars))

    def request_chunk(
        chunk: list[Segment], *, chunk_index: int, chunk_count: int, split_path: str = "root"
    ) -> None:
        text = "\n".join(
            f"[segment:{segment.id} {segment.locator_json.get('start_ms', 0)}-"
            f"{segment.locator_json.get('end_ms', 0)}ms] "
            f"{segment.corrected_text or segment.text}"
            for segment in chunk
        )
        try:
            response = _cached_stage_json(
                db,
                job=job,
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    *prompt_supplement_messages(db, "travel_place_extraction"),
                    {
                        "role": "user",
                        "content": f"视频标题：{asset.title}\n分块：{chunk_index}/{chunk_count}\n{text}",
                    },
                ],
                attempt_metadata={
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                    "split_path": split_path,
                    "segment_count": len(chunk),
                },
            )
        except AIProviderError as exc:
            if exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED" or len(chunk) <= 1:
                raise
            midpoint = len(chunk) // 2
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
        chunk_facts, chunk_places, chunk_warnings = _canonical_payload(
            parse_model_json(response.content), chunk
        )
        facts.extend(chunk_facts)
        places.extend(chunk_places)
        warnings.extend(chunk_warnings)

    for index, chunk in enumerate(chunks or [segments], start=1):
        request_chunk(chunk, chunk_index=index, chunk_count=max(1, len(chunks)))

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
        warnings_json=list(dict.fromkeys(warnings)),
    )
    db.add(artifact)
    db.commit()
    return artifact
