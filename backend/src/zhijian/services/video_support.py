from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.ai.budget import ensure_ai_budget
from zhijian.ai.cache import cached_json_result
from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.policies import resolve_stage_policy
from zhijian.ai.resource_manager import local_ai_resource_manager
from zhijian.ai.transcript_quality import correction_candidates
from zhijian.core.config import Settings
from zhijian.core.ids import new_id
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    ExternalCallAudit,
    Job,
    Place,
    PlaceMention,
    PlaceNoteVersion,
    Segment,
    Setting,
    Snapshot,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.domain.enums import ResolutionStatus
from zhijian.domain.schemas import GeneralConfig, TranscriptProcessingConfig
from zhijian.providers.amap import AMapPOIProvider
from zhijian.providers.llm import (
    FallbackLLMProvider,
    LLMProvider,
    LLMResult,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderRequestOptions,
)
from zhijian.services.audit import record_event
from zhijian.services.jobs import ensure_job_active
from zhijian.services.transcript_retention import retention_deadline

TRANSCRIPT_CORRECTION_TIMEOUT_SECONDS = 180.0
TRANSCRIPT_CORRECTION_CHUNK_CHARS = 12_000
TRANSCRIPT_CORRECTION_BATCH_SIZE = 128
PROMPT_SUPPLEMENT_SETTING_KEY = "prompt:supplements"
PROMPT_CORE_CONTRACTS = {
    "transcript_correction": [
        "固定返回 JSON 对象与 segments 数组。",
        "每个输入 Segment ID 必须且只能返回一次。",
        "Segment ID 不得新增、遗漏、重复或改变顺序。",
        "字段固定为 id、corrected_text、confidence、reason。",
        "不得改变时间码、分段边界或 Segment 身份。",
        "只校正识别、断句和专名错误，不得新增事实。",
    ],
    "video_note_summary": [
        "固定返回 JSON 对象及约定字段结构。",
        "顶层只使用 overview、warnings、sections。",
        "章节字段保持 heading、thesis、summary、bullets、body_markdown、segment_ids。",
        "每个章节必须引用当前输入中的有效 Segment ID。",
        "不得用无证据内容替代 Transcript 或 Evidence。",
        "Section 锚点和时间范围由服务端生成，模型不得编造。",
    ],
    "travel_place_extraction": [
        "固定返回 JSON 对象与 places 数组。",
        "地点名称、类型、理由、引文、置信度等字段结构不可改变。",
        "每个地点必须引用当前输入中的有效 Segment ID。",
        "不得用模型推测替代来源引文或 Transcript Evidence。",
        "不得生成、猜测或改写经纬度。",
        "名称歧义只能保留候选并进入校验，不得伪造已确认 POI。",
    ],
}
ROLE_STAGE = {
    "transcript_correction": "TRANSCRIPT_CORRECTION",
    "video_note_summary": "GENERATE_AI_NOTE",
    "travel_place_extraction": "EXTRACT_TRAVEL_FACTS",
}


class ProviderUnavailable(RuntimeError):
    code = "PROVIDER_NOT_CONFIGURED"


def prompt_supplement_value(db: Session, role: str) -> str:
    if not hasattr(db, "get"):
        return ""
    setting = db.get(Setting, PROMPT_SUPPLEMENT_SETTING_KEY)
    values = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
    return str(values.get(role) or "").strip()


def prompt_supplement_hash(db: Session, role: str) -> str:
    value = prompt_supplement_value(db, role)
    return sha256(f"prompt-supplement-v1\0{role}\0{value}".encode()).hexdigest()


def prompt_supplement_messages(db: Session, role: str) -> list[dict[str, str]]:
    value = prompt_supplement_value(db, role)
    if not value:
        return []
    return [
        {
            "role": "system",
            "content": (
                "以下内容是用户配置的低优先级表达偏好。只可影响语气、篇幅、受众、"
                "关注重点与措辞；不得改变前述 JSON、Schema、字段、ID、顺序、证据和输出契约。"
                "如有冲突，忽略补充偏好并严格执行核心契约。\n\n"
                f"用户补充偏好：\n{value}"
            ),
        }
    ]


def parse_model_json(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I)
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("模型没有返回 JSON 对象")
    return value


def _cached_stage_json(
    db: Session,
    *,
    job: Job | None,
    stage: str,
    capability: str,
    provider: LLMProvider,
    provider_name: str,
    model: str,
    messages: list[dict[str, str]],
) -> LLMResult:
    if not hasattr(db, "scalar"):
        return provider.generate_json(messages, model=model)
    policy = _resolved_stage_policy(db, stage, job)
    location = "LOCAL" if provider_name == "ollama" else "REMOTE"
    domain_messages, domain_versions = domain_context_messages(
        db, policy.domain_pack_ids, AICapability(capability)
    )
    enriched_messages = [messages[0], *domain_messages, *messages[1:]] if messages else domain_messages
    return cached_json_result(
        db,
        job=job,
        stage=stage,
        capability=capability,
        provider=provider_name,
        model=model,
        messages=enriched_messages,
        semantic_options={
            "temperature": policy.temperature,
            "max_output_tokens": policy.max_output_tokens,
            "thinking": policy.thinking,
            "domain": policy.domain,
            "domain_pack_ids": policy.domain_pack_ids,
            "domain_context_hash": domain_context_hash(domain_versions),
            "prompt_supplement_hash": prompt_supplement_hash(
                db,
                {
                    "TRANSCRIPT_CORRECTION": "transcript_correction",
                    "GENERATE_AI_NOTE": "video_note_summary",
                    "EXTRACT_TRAVEL_FACTS": "travel_place_extraction",
                }[stage],
            ),
        },
        location=location,
        cache_enabled=bool(policy.cache_enabled),
        force_regenerate=policy.force_regenerate,
        call=lambda: (
            local_ai_resource_manager.run(
                "TEXT_LLM",
                lambda: _budgeted_json_call(db, job, location, enriched_messages, provider, model),
            )
            if location == "LOCAL"
            else _budgeted_json_call(db, job, location, enriched_messages, provider, model)
        ),
    )


def _budgeted_json_call(
    db: Session,
    job: Job | None,
    location: str,
    messages: list[dict[str, str]],
    provider: LLMProvider,
    model: str,
) -> LLMResult:
    ensure_ai_budget(
        db,
        job,
        location=location,
        input_chars=sum(len(message.get("content") or "") for message in messages),
    )
    return provider.generate_json(messages, model=model)


def normalized_confidence(value: object) -> float:
    if isinstance(value, str):
        label = value.strip().lower()
        if label in {"high", "高", "high_confidence"}:
            return 0.85
        if label in {"medium", "中", "medium_confidence"}:
            return 0.6
        if label in {"low", "低", "low_confidence"}:
            return 0.3
    try:
        return max(0.0, min(1.0, float(value or 0)))
    except (TypeError, ValueError):
        return 0.0


def _profile_config(db: Session, profile_id: str | None) -> dict[str, str] | None:
    if not profile_id:
        return None
    saved = db.get(Setting, f"model-profile:{profile_id}")
    if saved is None or not isinstance(saved.value_json, dict):
        return None
    return {key: str(value) if value is not None else "" for key, value in saved.value_json.items()}


def _profile_location(config: dict[str, str] | None) -> str:
    if not config:
        return ""
    return config.get("location") or ("LOCAL" if config.get("provider", "").lower() == "ollama" else "REMOTE")


def transcript_processing_config(db: Session) -> TranscriptProcessingConfig:
    if not hasattr(db, "get"):
        return TranscriptProcessingConfig()
    setting = db.get(Setting, "transcript-processing")
    value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
    return TranscriptProcessingConfig(**value)


def transcript_force_full_correction(db: Session, job: Job | None) -> bool:
    return bool(_resolved_stage_policy(db, "TRANSCRIPT_CORRECTION", job).force_full_correction)


def _resolved_stage_policy(db: Session, stage: str, job: Job | None):
    if not hasattr(db, "get"):
        return resolve_stage_policy(stage)
    saved = db.get(Setting, f"ai-stage-policy:{stage}")
    override = (job.payload_json.get("ai_overrides") or {}).get(stage) if job else None
    return resolve_stage_policy(
        stage,
        saved=saved.value_json if saved and isinstance(saved.value_json, dict) else None,
        job_override=override if isinstance(override, dict) else None,
    )


def _provider_from_config(
    config: dict[str, str], settings: Settings, profile_id: str, timeout_cap: float | None = None
) -> tuple[LLMProvider, str, str]:
    name = config.get("provider", "").lower()
    base_url = config.get("base_url", "")
    model = config.get("model", "")
    if not base_url:
        raise ProviderUnavailable("尚未配置可用模型服务地址")
    if not model:
        raise ProviderUnavailable("尚未配置模型名")
    timeout = float(config.get("timeout_seconds") or 300)
    if timeout_cap is not None:
        timeout = min(timeout, timeout_cap)
    if name == "ollama":
        return OllamaProvider(base_url, timeout), "ollama", model
    store = build_secret_store(settings.secret_store, settings.data_dir)
    api_key = store.get(f"model-profile:{profile_id}:api-key")
    if not api_key:
        raise ProviderUnavailable("尚未保存模型的 API Key")
    return (
        OpenAICompatibleProvider(name or "openai-compatible", base_url, api_key, timeout),
        name or "openai-compatible",
        model,
    )


def provider_for_role(
    db: Session, settings: Settings, role: str, job: Job | None = None
) -> tuple[LLMProvider, str, str]:
    routing = db.get(Setting, "model-routing")
    routes = routing.value_json if routing and isinstance(routing.value_json, dict) else {}
    primary_id = str(
        (routes.get("transcript_primary_id") if role == "transcript_correction" else None)
        or routes.get("primary_id")
        or ""
    )
    fallback_id = str(
        (routes.get("transcript_fallback_id") if role == "transcript_correction" else None)
        or routes.get("fallback_id")
        or ""
    )
    stage = ROLE_STAGE.get(role)
    stage_setting = db.get(Setting, f"ai-stage-policy:{stage}") if stage else None
    job_override = (job.payload_json.get("ai_overrides") or {}).get(stage) if job and stage else None
    resolved_policy = (
        resolve_stage_policy(
            stage,
            saved=(
                stage_setting.value_json
                if stage_setting and isinstance(stage_setting.value_json, dict)
                else None
            ),
            job_override=job_override if isinstance(job_override, dict) else None,
        )
        if stage and (stage_setting or job_override)
        else None
    )
    primary_config = _profile_config(db, primary_id)
    fallback_config = _profile_config(db, fallback_id)
    if resolved_policy:
        local_id = resolved_policy.local_profile_id
        remote_id = resolved_policy.remote_profile_id
        candidates = ((primary_id, primary_config), (fallback_id, fallback_config))
        local_id = local_id or next(
            (item_id for item_id, config in candidates if _profile_location(config) == "LOCAL"), ""
        )
        remote_id = remote_id or next(
            (item_id for item_id, config in candidates if _profile_location(config) == "REMOTE"), ""
        )
        mode = resolved_policy.execution_mode
        if mode == "LOCAL_ONLY":
            primary_id, fallback_id = local_id, ""
        elif mode == "REMOTE_ONLY":
            primary_id, fallback_id = remote_id, ""
        elif mode == "LOCAL_FIRST":
            primary_id, fallback_id = local_id, remote_id
        elif mode == "REMOTE_FIRST":
            primary_id, fallback_id = remote_id, local_id
        primary_config = _profile_config(db, primary_id)
        fallback_config = _profile_config(db, fallback_id)
    general_setting = db.get(Setting, "app:general")
    policy = GeneralConfig(
        **(
            general_setting.value_json
            if general_setting and isinstance(general_setting.value_json, dict)
            else {}
        )
    )

    def on_retry(attempt: int, exc: Exception) -> None:
        record_event(
            db,
            "model.call.retrying",
            f"AI 接口异常，{policy.ai_retry_wait_seconds:g} 秒后执行第 {attempt} 次重试",
            component="video-pipeline",
            level="WARNING",
            detail={
                "role": role,
                "stage": stage,
                    "execution_mode": resolved_policy.execution_mode if resolved_policy else "LEGACY",
                    "stage_policy_version": resolved_policy.version if resolved_policy else None,
                    "resolved_policy": (
                        {
                            "temperature": resolved_policy.temperature,
                            "thinking": resolved_policy.thinking,
                            "max_input_tokens": resolved_policy.max_input_tokens,
                            "max_output_tokens": resolved_policy.max_output_tokens,
                            "timeout_seconds": resolved_policy.timeout_seconds,
                            "retry_count": resolved_policy.retry_count,
                            "confidence_threshold": resolved_policy.confidence_threshold,
                            "escalation_threshold": resolved_policy.escalation_threshold,
                            "domain": resolved_policy.domain,
                        }
                        if resolved_policy
                        else None
                    ),
                "retry_attempt": attempt,
                "retry_limit": policy.ai_retry_count,
                "wait_seconds": policy.ai_retry_wait_seconds,
                "reason": str(exc)[:240],
            },
        )

    def on_attempt(
        provider: str,
        model: str,
        route: str,
        attempt: int,
        input_chars: int,
        result: LLMResult | None,
        exc: Exception | None,
    ) -> None:
        usage = result.usage if result else {}
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        cached = usage.get("cached_tokens")
        if cached is None:
            cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        db.add(
            ExternalCallAudit(
                job_id=job.id if job else None,
                capability="LLM",
                provider=provider,
                operation=role,
                status="COMPLETED" if result else "FAILED",
                request_meta_json={
                    "step": {
                        "transcript_correction": "CORRECT_TRANSCRIPT",
                        "video_note_summary": "GENERATE_AI_NOTE",
                        "travel_place_extraction": "EXTRACT_TRAVEL_FACTS",
                    }.get(role, role),
                    "model": model,
                    "location": "LOCAL" if provider == "ollama" else "REMOTE",
                    "route": route,
                    "attempt": attempt,
                    "input_chars": input_chars,
                },
                response_meta_json={
                    "prompt_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count")),
                    "completion_tokens": usage.get("completion_tokens", usage.get("eval_count")),
                    "cached_tokens": cached,
                    "usage": usage,
                    "status_code": status_code,
                },
                error_code=str(status_code) if status_code else getattr(exc, "code", None),
                error_message=str(exc)[:500] if exc else None,
            )
        )
        db.commit()

    def with_policy(
        primary: LLMProvider,
        primary_model: str,
        fallback: LLMProvider | None = None,
        fallback_model: str | None = None,
    ) -> FallbackLLMProvider:
        request_options = None
        if resolved_policy and any(
            value is not None
            for value in (
                resolved_policy.temperature,
                resolved_policy.max_output_tokens,
                resolved_policy.thinking,
            )
        ):
            request_options = ProviderRequestOptions(
                temperature=resolved_policy.temperature,
                max_output_tokens=resolved_policy.max_output_tokens,
                thinking=resolved_policy.thinking,
            )
        return FallbackLLMProvider(
            primary,
            primary_model,
            fallback,
            fallback_model,
            retry_count=(
                resolved_policy.retry_count
                if resolved_policy and resolved_policy.retry_count is not None
                else policy.ai_retry_count
            ),
            retry_wait_seconds=policy.ai_retry_wait_seconds,
            request_interval_seconds=policy.ai_request_interval_seconds,
            on_retry=on_retry,
            on_attempt=on_attempt,
            request_options=request_options,
        )
    if primary_config is None:
        raise ProviderUnavailable("尚未在设置中选择主模型")
    timeout_cap = (
        transcript_processing_config(db).timeout_seconds
        if role == "transcript_correction"
        else None
    )
    if resolved_policy and resolved_policy.timeout_seconds:
        timeout_cap = (
            min(timeout_cap, resolved_policy.timeout_seconds)
            if timeout_cap
            else resolved_policy.timeout_seconds
        )
    try:
        primary, primary_name, primary_model = _provider_from_config(
            primary_config, settings, primary_id, timeout_cap
        )
    except ProviderUnavailable:
        if fallback_config is None:
            raise
        fallback, fallback_name, fallback_model = _provider_from_config(
            fallback_config, settings, fallback_id, timeout_cap
        )
        return with_policy(fallback, fallback_model), fallback_name, fallback_model
    fallback: LLMProvider | None = None
    fallback_model: str | None = None
    if fallback_config and fallback_id:
        try:
            fallback, _, fallback_model = _provider_from_config(
                fallback_config, settings, fallback_id, timeout_cap
            )
        except ProviderUnavailable:
            fallback = None
            fallback_model = None
    return with_policy(primary, primary_model, fallback, fallback_model), primary_name, primary_model


def materialize_transcript(
    db: Session,
    source: Source,
    asset: VideoAsset,
    raw_segments: list[dict[str, Any]],
    *,
    source_kind: str,
    language: str = "zh-CN",
) -> tuple[Transcript, list[Segment]]:
    normalized = []
    for item in raw_segments:
        text = str(item.get("text") or "").strip()
        start_ms = int(item.get("start_ms") or 0)
        end_ms = max(start_ms, int(item.get("end_ms") or start_ms))
        if text:
            normalized.append(
                {"text": text, "start_ms": start_ms, "end_ms": end_ms, "confidence": item.get("confidence")}
            )
    if not normalized:
        raise ValueError("没有可用的带时间码转写片段")
    if asset.duration_ms and normalized[-1]["end_ms"] > asset.duration_ms * 2:
        raise ValueError("转写末段时间显著超过视频时长，拒绝物化异常时间轴")
    fingerprint = "\n".join(f"{item['start_ms']}:{item['end_ms']}:{item['text']}" for item in normalized)
    fingerprint_sha = __import__("hashlib").sha256(fingerprint.encode()).hexdigest()
    existing = db.scalar(
        select(Transcript).where(Transcript.video_asset_id == asset.id).order_by(Transcript.version.desc())
    )
    if existing and (
        existing.metadata_json.get("fingerprint") == fingerprint
        or existing.metadata_json.get("fingerprint_sha256") == fingerprint_sha
    ):
        snapshot_id = existing.metadata_json.get("snapshot_id")
        segments = db.scalars(
            select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)
        ).all()
        return existing, segments
    version = (existing.version + 1) if existing else 1
    snapshot = Snapshot(
        source_id=source.id,
        content_hash=fingerprint_sha,
        metadata_json={"kind": "VIDEO_TRANSCRIPT", "video_asset_id": asset.id, "source_kind": source_kind},
    )
    db.add(snapshot)
    db.flush()
    segments = []
    for ordinal, item in enumerate(normalized):
        segment = Segment(
            snapshot_id=snapshot.id,
            kind="VIDEO_TRANSCRIPT",
            ordinal=ordinal,
            text=item["text"],
            raw_text=item["text"],
            corrected_text=item["text"],
            correction_status="UNCORRECTED",
            correction_reason="等待模型校对",
            confidence=item["confidence"],
            locator_json={"start_ms": item["start_ms"], "end_ms": item["end_ms"]},
        )
        db.add(segment)
        segments.append(segment)
    db.flush()
    transcript = Transcript(
        video_asset_id=asset.id,
        version=version,
        source_kind=source_kind,
        language=language,
        text="\n".join(item["text"] for item in normalized),
        segment_count=len(segments),
        retention_until=retention_deadline(),
        metadata_json={
            "snapshot_id": snapshot.id,
            "fingerprint_sha256": fingerprint_sha,
        },
    )
    db.add(transcript)
    db.commit()
    return transcript, segments


def _transcript_context(segments: list[Segment], max_chars: int) -> str:
    lines = []
    used = 0
    for segment in segments:
        start = segment.locator_json.get("start_ms", 0)
        end = segment.locator_json.get("end_ms", start)
        line = f"[segment:{segment.id} {start}-{end}ms] {segment.corrected_text or segment.text}"
        if lines and used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


def _transcript_chunks(
    segments: list[Segment], max_chars: int, max_segments: int | None = None
) -> list[list[Segment]]:
    chunks: list[list[Segment]] = []
    current: list[Segment] = []
    used = 0
    for segment in segments:
        size = len(segment.corrected_text or segment.text) + 80
        over_segment_limit = max_segments is not None and len(current) >= max_segments
        if current and (used + size > max_chars or over_segment_limit):
            chunks.append(current)
            current, used = [], 0
        current.append(segment)
        used += size
    if current:
        chunks.append(current)
    return chunks


def _fallback_sections(chunks: list[list[Segment]]) -> list[dict[str, object]]:
    result = []
    for index, chunk in enumerate(chunks):
        if not chunk:
            continue
        texts = [re.sub(r"\s+", " ", segment.corrected_text or segment.text).strip() for segment in chunk]
        texts = [text for text in texts if text]
        heading_source = next((text for text in texts if len(text) >= 6), f"时间线详述 {index + 1}")
        heading = re.split(r"[。！？；，]", heading_source, maxsplit=1)[0][:24] or f"时间线详述 {index + 1}"
        bullets = [text[:120] for text in texts[:6]]
        thesis = "；".join(texts[:2])[:80] or "本段转写等待进一步归纳。"
        result.append(
            {
                "heading": heading,
                "thesis": thesis,
                "summary": thesis,
                "bullets": bullets,
                "body_markdown": "\n".join(f"- {value}" for value in bullets),
                "segment_ids": [segment.id for segment in chunk],
            }
        )
    return result


def _section_facts(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, object]]:
    declared = payload.get("section_facts") if isinstance(payload.get("section_facts"), list) else []
    facts = [item for item in declared if isinstance(item, dict)]
    if not facts:
        facts = [
            {
                "summary": item.get("summary") or item.get("thesis") or "",
                "key_points": item.get("bullets") or [],
                "places": [],
                "segment_ids": item.get("segment_ids") or [],
            }
            for item in payload.get("sections", [])
            if isinstance(item, dict)
        ]
    result = []
    for item in facts:
        segment_ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not segment_ids:
            continue
        places = [
            value
            for value in item.get("places", [])
            if isinstance(value, dict)
            and value.get("name")
            and any(segment_id in valid_ids for segment_id in value.get("segment_ids", segment_ids))
        ]
        result.append(
            {
                "summary": str(item.get("summary") or "")[:800],
                "key_points": [str(value)[:300] for value in item.get("key_points", []) if value][:8],
                "places": places[:20],
                "warnings": [str(value)[:300] for value in item.get("warnings", []) if value][:8],
                "segment_ids": segment_ids,
            }
        )
    return result


def _stage_execution_mode(db: Session, stage: str, job: Job | None) -> str:
    return str(_resolved_stage_policy(db, stage, job).execution_mode)


def correct_transcript(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    transcript: Transcript,
    segments: list[Segment],
    job: Job | None = None,
) -> list[Segment]:
    if job:
        ensure_job_active(db, job)
    pending = [segment for segment in segments if segment.correction_status != "CORRECTED"]
    if not pending:
        return segments
    candidates = correction_candidates(
        pending,
        source_kind=str(getattr(transcript, "source_kind", "ASR") or "ASR"),
        force_full=transcript_force_full_correction(db, job),
    )
    candidate_ids = {segment.id for segment in candidates}
    for segment in pending:
        if segment.id not in candidate_ids:
            segment.correction_status = "UNCHANGED"
            segment.correction_reason = "平台字幕通过质量门禁，未发送模型校对"
    if not candidates:
        transcript.text = "\n".join(segment.corrected_text or segment.text for segment in segments)
        transcript.metadata_json = {
            **transcript.metadata_json,
            "correction_status": "PASS_THROUGH",
            "correction_coverage": 1.0,
        }
        db.commit()
        return segments
    provider, provider_name, model = provider_for_role(db, settings, "transcript_correction", job)
    if job and isinstance(provider, FallbackLLMProvider):
        provider.before_fallback = lambda: ensure_job_active(db, job)
    prompt = (Path(__file__).resolve().parents[1] / "prompts" / "transcript_correction.md").read_text(
        encoding="utf-8"
    )
    processing = transcript_processing_config(db)
    chunks = _transcript_chunks(
        candidates,
        processing.chunk_chars,
        processing.batch_size,
    )
    def request_batch(batch: list[Segment]) -> list[tuple[list[Segment], LLMResult, list]]:
        if job:
            ensure_job_active(db, job)
        payload = {
            "video_title": asset.title,
            "segments": [
                {
                    "id": item.id,
                    "start_ms": item.locator_json.get("start_ms"),
                    "end_ms": item.locator_json.get("end_ms"),
                    "raw_text": item.raw_text or item.text,
                }
                for item in batch
            ],
        }
        try:
            messages = [
                {"role": "system", "content": prompt},
                *prompt_supplement_messages(db, "transcript_correction"),
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ]
            response = _cached_stage_json(
                db,
                job=job,
                stage="TRANSCRIPT_CORRECTION",
                capability="TRANSCRIPT_CORRECTION",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=messages,
            )
        except (httpx.HTTPError, TimeoutError, ConnectionError):
            if job:
                ensure_job_active(db, job)
            raise
        if job:
            ensure_job_active(db, job)
        try:
            payload = parse_model_json(response.content)
            values = payload.get("changes", payload.get("segments", []))
        except (json.JSONDecodeError, ValueError):
            if job:
                ensure_job_active(db, job)
            return [(batch, response, [])]
        return [(batch, response, values if isinstance(values, list) else [])]

    corrected_count = 0
    for batch_index, chunk in enumerate(chunks, start=1):
        started = perf_counter()
        if job:
            ensure_job_active(db, job)
            job.heartbeat_at = utc_now()
            record_event(
                db,
                "transcript.correction.batch.started",
                f"AI 校对 {batch_index}/{len(chunks)}",
                component="video-pipeline",
                entity_type="job",
                entity_id=job.id,
                detail={
                    "step": "CORRECT_TRANSCRIPT",
                    "batch_index": batch_index,
                    "batch_total": len(chunks),
                    "segments": len(chunk),
                    "provider": provider_name,
                    "model": model,
                },
                commit=False,
            )
            db.commit()
        for effective_chunk, response, values in request_batch(chunk):
            by_id = {
                str(item.get("segment_id") or item.get("id")): item
                for item in values
                if isinstance(item, dict) and (item.get("segment_id") or item.get("id"))
            }
            for segment in effective_chunk:
                item = by_id.get(segment.id)
                text = str(item.get("corrected_text") or "").strip() if item else ""
                if not text:
                    segment.corrected_text = segment.raw_text or segment.text
                    segment.correction_status = "REVIEW"
                    segment.correction_reason = "模型未返回有效校对，保留原始转写"
                    continue
                segment.corrected_text = text
                segment.text = text
                segment.correction_status = "CORRECTED"
                segment.correction_confidence = normalized_confidence(item.get("confidence"))
                segment.correction_reason = str(item.get("reason") or "语音转写校对")[:500]
                segment.correction_provider = response.provider
                segment.correction_model = response.model
                corrected_count += 1
            if job:
                ensure_job_active(db, job)
                job.heartbeat_at = utc_now()
            db.commit()
        if job:
            ensure_job_active(db, job)
            job.heartbeat_at = utc_now()
            record_event(
                db,
                "transcript.correction.batch.completed",
                f"AI 校对 {batch_index}/{len(chunks)} 已完成",
                component="video-pipeline",
                entity_type="job",
                entity_id=job.id,
                detail={
                    "step": "CORRECT_TRANSCRIPT",
                    "batch_index": batch_index,
                    "batch_total": len(chunks),
                    "duration_ms": round((perf_counter() - started) * 1000),
                },
                commit=False,
            )
            db.commit()
    corrected_count = sum(segment.correction_status == "CORRECTED" for segment in segments)
    unchanged_count = sum(segment.correction_status == "UNCHANGED" for segment in segments)
    transcript.text = "\n".join(segment.corrected_text or segment.text for segment in segments)
    transcript.metadata_json = {
        **transcript.metadata_json,
        "correction_status": "CORRECTED" if corrected_count + unchanged_count == len(segments) else "REVIEW",
        "correction_provider": provider_name,
        "correction_model": model,
        "correction_coverage": (corrected_count + unchanged_count) / max(1, len(segments)),
        "correction_prompt_supplement_hash": prompt_supplement_hash(
            db, "transcript_correction"
        ),
    }
    record_event(
        db,
        "transcript.corrected",
        f"已完成转写校对：{corrected_count} 段修改，{unchanged_count} 段保持原文",
        component="video-pipeline",
        entity_type="transcript",
        entity_id=transcript.id,
        detail={
            "provider": provider_name,
            "model": model,
            "coverage": (corrected_count + unchanged_count) / len(segments),
        },
        commit=False,
    )
    db.commit()
    return segments


def repair_legacy_transcript_timing(db: Session) -> int:
    """Version-correct historical 10x whisper timelines without overwriting evidence history."""
    repaired = 0
    assets = db.scalars(select(VideoAsset).where(VideoAsset.duration_ms.is_not(None))).all()
    for asset in assets:
        transcript = db.scalar(
            select(Transcript)
            .where(Transcript.video_asset_id == asset.id)
            .order_by(Transcript.version.desc())
        )
        if transcript is None or transcript.purged_at or not asset.duration_ms:
            continue
        snapshot_id = transcript.metadata_json.get("snapshot_id")
        segments = db.scalars(
            select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)
        ).all()
        if not segments or int(segments[-1].locator_json.get("end_ms") or 0) <= asset.duration_ms * 2:
            continue
        source = db.get(Source, asset.source_id)
        if source is None:
            continue
        raw = [
            {
                "text": segment.text,
                "start_ms": round(int(segment.locator_json.get("start_ms") or 0) / 10),
                "end_ms": round(int(segment.locator_json.get("end_ms") or 0) / 10),
                "confidence": segment.confidence,
            }
            for segment in segments
        ]
        corrected, corrected_segments = materialize_transcript(
            db,
            source,
            asset,
            raw,
            source_kind=f"{transcript.source_kind}_TIMEBASE_FIXED",
            language=transcript.language,
        )
        note = db.scalar(select(AINote).where(AINote.video_asset_id == asset.id))
        if note and note.current_version_id:
            current = db.get(AINoteVersion, note.current_version_id)
            section_count = db.scalar(
                select(func.count(AINoteSection.id)).where(
                    AINoteSection.ai_note_version_id == note.current_version_id
                )
            ) or 0
            if current and not section_count:
                fallback_sections = _fallback_sections(_transcript_chunks(corrected_segments, 12_000))
                for ordinal, item in enumerate(fallback_sections):
                    refs = [segment for segment in corrected_segments if segment.id in item["segment_ids"]]
                    db.add(
                        AINoteSection(
                            ai_note_version_id=current.id,
                            ordinal=ordinal,
                            heading=str(item["heading"]),
                            body_markdown=str(item["body_markdown"]),
                            segment_ids_json=list(item["segment_ids"]),
                            start_ms=refs[0].locator_json.get("start_ms"),
                            end_ms=refs[-1].locator_json.get("end_ms"),
                        )
                    )
                current.transcript_version = corrected.version
                db.commit()
                from zhijian.services.video_screenshots import plan_screenshots

                plan_screenshots(db, asset, current)
        record_event(
            db,
            "transcript.timebase.repaired",
            "已创建修正版转写时间轴",
            component="worker",
            entity_type="transcript",
            entity_id=corrected.id,
            detail={"previous_version": transcript.version, "version": corrected.version},
            commit=False,
        )
        db.commit()
        repaired += 1
    return repaired


def generate_note(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    transcript: Transcript,
    segments: list[Segment],
    job: Job | None = None,
) -> AINoteVersion:
    provider, provider_name, model = provider_for_role(db, settings, "video_note_summary", job)
    chunks = _transcript_chunks(segments, settings.video_note_chunk_chars)
    system = Path(__file__).resolve().parents[1] / "prompts" / "video_note.md"
    valid_ids = {segment.id for segment in segments}
    raw_sections: list[dict[str, object]] = []
    map_facts: list[dict[str, object]] = []
    overview_parts: list[str] = []
    warnings: list[str] = []
    response = LLMResult("", provider_name, model, {})
    for chunk_index, chunk in enumerate(chunks or [segments]):
        context = _transcript_context(chunk, settings.video_note_chunk_chars)
        try:
            messages = [
                {"role": "system", "content": system.read_text(encoding="utf-8")},
                *prompt_supplement_messages(db, "video_note_summary"),
                {
                    "role": "user",
                    "content": (
                        f"视频标题：{asset.title}\n"
                        f"分块：{chunk_index + 1}/{max(1, len(chunks))}\n{context}"
                    ),
                },
            ]
            response = _cached_stage_json(
                db,
                job=job,
                stage="GENERATE_AI_NOTE",
                capability="GLOBAL_SYNTHESIS",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=messages,
            )
            payload = parse_model_json(response.content)
            if payload.get("overview"):
                overview_parts.append(str(payload["overview"]).strip())
            warnings.extend(str(value) for value in payload.get("warnings", []) if value)
            chunk_ids = {segment.id for segment in chunk}
            map_facts.extend(_section_facts(payload, chunk_ids))
            sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
            raw_sections.extend(
                item
                for item in sections
                if isinstance(item, dict)
                and any(value in chunk_ids for value in item.get("segment_ids", []))
            )
        except Exception as exc:
            warnings.append(f"第 {chunk_index + 1} 段模型总结不可用")
            raw_sections.extend(_fallback_sections([chunk]))
            record_event(
                db,
                "video.note.chunk_fallback",
                f"第 {chunk_index + 1} 段模型笔记生成失败，已使用提纲兜底",
                component="video-pipeline",
                level="WARNING",
                entity_type="video_asset",
                entity_id=asset.id,
                detail={"reason": str(exc)[:240], "chunk": chunk_index + 1},
            )
    if not raw_sections:
        raw_sections = _fallback_sections(chunks)
    if len(map_facts) > 1:
        try:
            reduce_messages = [
                {"role": "system", "content": system.read_text(encoding="utf-8")},
                *prompt_supplement_messages(db, "video_note_summary"),
                {
                    "role": "user",
                    "content": (
                        "以下是按时间块验证的 SectionFacts。仅据此生成全局笔记，不要要求完整转写：\n"
                    )
                    + json.dumps(map_facts, ensure_ascii=False),
                },
            ]
            reduced = _cached_stage_json(
                db,
                job=job,
                stage="GENERATE_AI_NOTE",
                capability="GLOBAL_SYNTHESIS",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=reduce_messages,
            )
            reduced_payload = parse_model_json(reduced.content)
            reduced_sections = reduced_payload.get("sections")
            if isinstance(reduced_sections, list):
                accepted = [
                    item
                    for item in reduced_sections
                    if isinstance(item, dict)
                    and any(value in valid_ids for value in item.get("segment_ids", []))
                ]
                if accepted:
                    raw_sections = accepted
                    response = reduced
                    if reduced_payload.get("overview"):
                        overview_parts.append(str(reduced_payload["overview"]).strip())
        except Exception as exc:
            warnings.append("全局归纳不可用，已保留分块笔记")
            record_event(
                db,
                "video.note.reduce_fallback",
                "全局归纳不可用，已保留分块笔记",
                component="video-pipeline",
                level="WARNING",
                entity_type="video_asset",
                entity_id=asset.id,
                detail={"reason": str(exc)[:240]},
            )
    note = db.scalar(select(AINote).where(AINote.video_asset_id == asset.id))
    if note is None:
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
    old = db.scalar(select(func.max(AINoteVersion.version)).where(AINoteVersion.ai_note_id == note.id)) or 0
    overview = " ".join(dict.fromkeys(value for value in overview_parts if value))[:800]
    if not overview:
        overview = "已根据完整校对稿整理视频主题、关键地点与注意事项。"
    markdown = "# " + asset.title + "\n\n" + overview + "\n"
    version = AINoteVersion(
        ai_note_id=note.id,
        version=old + 1,
        markdown=markdown,
        overview=overview,
        warnings_json=warnings,
        map_facts_json=map_facts,
        model_provider=response.provider,
        model_name=response.model,
        prompt_version=f"video-note-v2+{prompt_supplement_hash(db, 'video_note_summary')[:8]}",
        transcript_version=transcript.version,
    )
    db.add(version)
    db.flush()
    rendered = [f"# {asset.title}", "", overview]
    created_sections = 0
    for ordinal, item in enumerate(raw_sections):
        segment_ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not segment_ids:
            continue
        body = str(item.get("body_markdown") or item.get("body") or "")
        heading = str(item.get("heading") or f"要点 {ordinal + 1}")
        thesis = str(item.get("thesis") or item.get("summary") or "")[:500]
        summary = str(item.get("summary") or thesis)
        bullets = [str(value) for value in item.get("bullets", []) if value][:6]
        if not body:
            body = "\n".join([summary, *[f"- {value}" for value in bullets]]).strip()
        refs = [segment for segment in segments if segment.id in segment_ids]
        section_id = new_id("nsc")
        db.add(
            AINoteSection(
                id=section_id,
                ai_note_version_id=version.id,
                ordinal=ordinal,
                heading=heading,
                thesis=thesis,
                summary=summary,
                bullets_json=bullets,
                anchor_id=f"section-{section_id}",
                body_markdown=body,
                segment_ids_json=segment_ids,
                start_ms=refs[0].locator_json.get("start_ms") if refs else None,
                end_ms=refs[-1].locator_json.get("end_ms") if refs else None,
            )
        )
        rendered.extend(["", f"## {heading}", body])
        created_sections += 1
    if not created_sections and segments:
        fallback = _fallback_sections([segments])
        item = fallback[0]
        refs = segments
        section_id = new_id("nsc")
        db.add(
            AINoteSection(
                id=section_id,
                ai_note_version_id=version.id,
                ordinal=0,
                heading=str(item["heading"]),
                thesis=str(item.get("thesis") or ""),
                summary=str(item.get("summary") or ""),
                bullets_json=list(item.get("bullets") or []),
                anchor_id=f"section-{section_id}",
                body_markdown=str(item["body_markdown"]),
                segment_ids_json=list(item["segment_ids"]),
                start_ms=refs[0].locator_json.get("start_ms"),
                end_ms=refs[-1].locator_json.get("end_ms"),
            )
        )
    version.markdown = "\n".join(rendered).strip() + "\n"
    note.current_version_id = version.id
    note.status = "COMPLETED"
    db.commit()
    return version


def extract_place_mentions(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    note: AINoteVersion,
    segments: list[Segment],
    job: Job | None = None,
) -> list[PlaceMention]:
    remote_reprocess = _stage_execution_mode(db, "EXTRACT_TRAVEL_FACTS", job) == "REMOTE_ONLY"
    if remote_reprocess:
        provider, provider_name, model = provider_for_role(db, settings, "travel_place_extraction", job)
        prompt = (Path(__file__).resolve().parents[1] / "prompts" / "travel_place_extraction.md").read_text(
            encoding="utf-8"
        )
        messages = [
            {"role": "system", "content": prompt},
            *prompt_supplement_messages(db, "travel_place_extraction"),
            {"role": "user", "content": _transcript_context(segments, settings.video_note_chunk_chars)},
        ]
        response = _cached_stage_json(
            db,
            job=job,
            stage="EXTRACT_TRAVEL_FACTS",
            capability="ENTITY_EXTRACTION",
            provider=provider,
            provider_name=provider_name,
            model=model,
            messages=messages,
        )
        if response.provider != provider_name or response.model != model:
            record_event(
                db,
                "model_routing.fallback_used",
                f"地点提取主模型不可用，已切换至备用模型：{response.provider} / {response.model}",
                component="video-pipeline",
                entity_type="video_asset",
                entity_id=asset.id,
            )
        candidates = parse_model_json(response.content).get("places", [])
    else:
        candidates = [
            candidate
            for fact in note.map_facts_json or []
            if isinstance(fact, dict)
            for candidate in fact.get("places", [])
            if isinstance(candidate, dict)
        ]
    valid_ids = {segment.id for segment in segments}
    created: list[PlaceMention] = []
    for item in candidates[:80]:
        if not isinstance(item, dict):
            continue
        ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not ids or not item.get("name"):
            continue
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=note.id,
            name=str(item["name"])[:300],
            raw_name=str(item.get("raw_name") or item["name"])[:300],
            suggested_name=str(item.get("suggested_name") or item["name"])[:300],
            city_hint=str(item.get("city_hint") or "")[:64],
            province_hint=str(item.get("province_hint") or "")[:64],
            place_type=str(item.get("place_type") or "UNKNOWN")[:64],
            reason=str(item.get("reason") or ""),
            quote=str(item.get("quote") or ""),
            segment_ids_json=ids,
            confidence=normalized_confidence(item.get("confidence")),
            extraction_status="EXTRACTED",
            resolution_status=ResolutionStatus.UNRESOLVED.value,
            brief_json={
                "feature": str(item.get("feature") or item.get("reason") or "")[:500],
                "experience": str(item.get("experience") or "")[:500],
                "price": str(item.get("price") or "")[:200],
                "queue": str(item.get("queue") or "")[:200],
                "audience": str(item.get("audience") or "")[:300],
                "warning": str(item.get("warning") or "")[:300],
                "author_opinion": str(item.get("author_opinion") or "")[:500],
            },
        )
        db.add(mention)
        created.append(mention)
    db.commit()
    return created


def resolve_mentions_with_amap(
    db: Session, settings: Settings, mentions: list[PlaceMention], api_key: str | None = None
) -> tuple[int, int]:
    if not mentions:
        return 0, 0
    effective_key = api_key or settings.amap_api_key
    if not effective_key:
        return 0, len(mentions)
    provider = AMapPOIProvider(effective_key)
    confirmed = 0
    for mention in mentions:
        try:
            candidates = provider.search(mention.name, mention.city_hint, city_limit=bool(mention.city_hint))
        except Exception as exc:
            mention.metadata_json = {"poi_error": str(exc)[:240]}
            continue
        if not candidates:
            continue
        if len(candidates) > 1 and candidates[0].name != (mention.suggested_name or mention.name):
            mention.resolution_status = ResolutionStatus.REVIEW.value
            mention.metadata_json = {
                "poi_candidates": [item.name for item in candidates[:5]],
                "reason": "多个高德候选，等待人工确认",
            }
            continue
        selected = candidates[0]
        place = db.scalar(
            select(Place).where(
                Place.external_provider == "AMap", Place.external_poi_id == selected.provider_id
            )
        )
        if place is None:
            place = Place(
                name=selected.name,
                canonical_name=selected.name,
                origin="AI_EXTRACTED",
                place_type=mention.place_type,
                province=selected.province,
                city=selected.city,
                district=selected.district,
                address=selected.address,
                latitude=selected.latitude,
                longitude=selected.longitude,
                coordinate_system=selected.coordinate_system,
                external_provider="AMap",
                external_poi_id=selected.provider_id,
                resolution_status=ResolutionStatus.CONFIRMED.value,
                summary=mention.reason,
            )
            db.add(place)
            db.flush()
        else:
            place.canonical_name = selected.name
        mention.place_id = place.id
        mention.resolution_status = ResolutionStatus.CONFIRMED.value
        mention.metadata_json = {"poi_name": selected.name, "poi_id": selected.provider_id}
        confirmed += 1
    db.commit()
    return confirmed, len(mentions) - confirmed


def build_place_notes(db: Session, asset: VideoAsset, mentions: list[PlaceMention]) -> int:
    count = 0
    for mention in mentions:
        if not mention.place_id:
            continue
        place = db.get(Place, mention.place_id)
        if place is None:
            continue
        previous = (
            db.scalar(select(func.max(PlaceNoteVersion.version)).where(PlaceNoteVersion.place_id == place.id))
            or 0
        )
        brief = mention.brief_json or {}
        lines = [
            f"# {place.canonical_name or place.name}",
            "",
            f"- 视频来源：{asset.title}",
            f"- 转写名称：{mention.raw_name or mention.name}",
            f"- 校正名称：{place.canonical_name or place.name}",
            f"- 依据：{mention.quote or mention.reason}",
        ]
        labels = {
            "feature": "特色", "experience": "菜品 / 体验", "price": "价格", "queue": "排队",
            "audience": "适合人群", "warning": "注意事项", "author_opinion": "作者态度",
        }
        for key, label in labels.items():
            value = brief.get(key)
            if value:
                lines.append(f"- {label}：{value}")
        lines.append("- 状态：来源观察，建议到店前再次核验。")
        text = "\n".join(lines) + "\n"
        db.add(
            PlaceNoteVersion(
                place_id=place.id,
                version=previous + 1,
                markdown=text,
                model_provider="deterministic",
                model_name="evidence-template",
                evidence_count=1,
            )
        )
        count += 1
    db.commit()
    return count
