from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.policies import resolve_stage_policy
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
    PlaceDeletionTombstone,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    PlaceVisitWindow,
    Segment,
    Setting,
    Snapshot,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.domain.enums import ResolutionStatus
from zhijian.domain.schemas import GeneralConfig, TranscriptProcessingConfig
from zhijian.providers.amap import AMapPOIProvider, POICandidate
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
from zhijian.services.place_knowledge import aggregate_place_knowledge, normalize_insight
from zhijian.services.transcript_retention import retention_deadline

TRANSCRIPT_CORRECTION_TIMEOUT_SECONDS = 180.0
TRANSCRIPT_CORRECTION_CHUNK_CHARS = 12_000
TRANSCRIPT_CORRECTION_BATCH_SIZE = 128
PLACE_EXTRACTION_CHUNK_CHARS = 8_000
PLACE_EXTRACTION_NEIGHBOR_SEGMENTS = 3
NOTE_SECTION_KINDS = {"PLACE", "AREA", "ROUTE", "SUPPLEMENTAL"}
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
        "顶层只使用 overview、warnings、sections、section_facts。",
        "章节字段保持 heading、thesis、summary、bullets、body_markdown、segment_ids。",
        "每个章节必须引用当前输入中的有效 Segment ID。",
        "地点时间窗口必须逐字引用 Transcript 并绑定有效 Segment ID。",
        "Section 锚点和时间范围由服务端生成，模型不得编造。",
    ],
    "travel_place_extraction": [
        "固定返回 JSON 对象与 places 数组。",
        "地点及时间窗口的字段结构不可改变。",
        "每个地点必须引用当前输入中的有效 Segment ID。",
        "时间窗口必须逐字引用 Transcript 并绑定有效 Segment ID。",
        "不得生成、猜测或改写经纬度。",
        "名称歧义只能保留候选并进入校验，不得伪造已确认 POI。",
    ],
}
ROLE_STAGE = {
    "transcript_correction": "TRANSCRIPT_CORRECTION",
    "video_note_summary": "GENERATE_AI_NOTE",
    "travel_place_extraction": "EXTRACT_TRAVEL_FACTS",
    "visual_fact": "VISION_FACT",
}

VISIT_PERIOD_TYPES = {
    "BEST_VISIT",
    "BEST_VIEWING",
    "HIGH_WATER",
    "LOW_WATER",
    "FISHING_CLOSURE",
    "SEASONAL_CLOSURE",
    "BLOOM",
    "FOLIAGE",
    "SNOW",
    "MIGRATION",
    "WEATHER_SEASON",
    "PEAK_SEASON",
    "OFF_SEASON",
    "OTHER",
}
VISIT_SUITABILITIES = {"RECOMMENDED", "AVOID", "RESTRICTED", "INFORMATIONAL"}
VISIT_SEASONS = {"SPRING", "SUMMER", "AUTUMN", "WINTER"}
VISIT_MONTH_SEGMENTS = {"EARLY", "MID", "LATE"}
VISIT_DAY_TIME_SLOTS = {
    "EARLY_MORNING",
    "MORNING",
    "NOON",
    "AFTERNOON",
    "SUNSET",
    "EVENING",
    "NIGHT",
    "BREAKFAST",
    "LUNCH",
    "DINNER",
    "LATE_NIGHT",
}
TEMPORAL_CUE = re.compile(
    r"最佳(?:观赏|游览|旅行|到访|拍摄)?(?:期|时间|季节)?|最好|最美|最漂亮|最适合|最合适|"
    r"适合.{0,8}(?:去|前往|游览|观赏|拍摄)|建议.{0,8}(?:去|前往|游览|观赏)|"
    r"丰水期|丰水季|汛期|枯水期|枯水季|平水期|休渔期|禁渔期|禁捕期|开渔期|捕捞期|"
    r"封山期|闭园期|开放期|停航期|封航期|结冰期|融冰期|"
    r"花期|花季|樱花季|赏花期|红叶期|红叶季|赏枫期|雪季|冰雪季|"
    r"候鸟季|迁徙期|雨季|旱季|旺季|淡季"
)
MONTH_TOKEN = re.compile(r"(?:(1[0-2]|0?[1-9])|([一二三四五六七八九十]{1,3}))月")


def _chinese_month(value: str) -> int | None:
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + digits.get(value[1:], 0)
    if value.endswith("十"):
        return digits.get(value[:-1], 0) * 10
    return digits.get(value)


def _months_in_text(value: str) -> list[int]:
    matches = list(MONTH_TOKEN.finditer(value))
    parsed = []
    for match in matches:
        month = int(match.group(1)) if match.group(1) else _chinese_month(match.group(2))
        parsed.append(month if month and 1 <= month <= 12 else None)
    months = []
    for compact in re.finditer(r"([一二三四五六七八九])([一二三四五六七八九])月", value):
        months.extend(
            month
            for month in (_chinese_month(compact.group(1)), _chinese_month(compact.group(2)))
            if month and month not in months
        )
    for compact in re.finditer(r"(1[0-2]|[1-9])[、和及与](1[0-2]|[1-9])月", value):
        months.extend(month for month in map(int, compact.groups()) if month not in months)
    for index, month in enumerate(parsed):
        if month and index + 1 < len(parsed) and parsed[index + 1]:
            connector = value[matches[index].end() : matches[index + 1].start()]
            if re.fullmatch(r"\s*(?:至|到|[-—~～])\s*", connector):
                end = parsed[index + 1]
                span = (
                    list(range(month, end + 1))
                    if month <= end
                    else list(range(month, 13)) + list(range(1, end + 1))
                )
                months.extend(value for value in span if value not in months)
        if month and month not in months:
            months.append(month)
    return months


def _period_type_from_text(value: str) -> str:
    for pattern, period_type in (
        (r"休渔期|禁渔期|禁捕期|开渔期|捕捞期", "FISHING_CLOSURE"),
        (r"封山期|闭园期|开放期|停航期|封航期", "SEASONAL_CLOSURE"),
        (r"丰水期|丰水季|汛期", "HIGH_WATER"),
        (r"枯水期|枯水季|平水期", "LOW_WATER"),
        (r"花期|花季|樱花季|赏花期", "BLOOM"),
        (r"红叶期|红叶季|赏枫期", "FOLIAGE"),
        (r"雪季|冰雪季|结冰期|融冰期", "SNOW"),
        (r"候鸟季|迁徙期", "MIGRATION"),
        (r"雨季|旱季", "WEATHER_SEASON"),
        (r"旺季", "PEAK_SEASON"),
        (r"淡季", "OFF_SEASON"),
        (r"最佳|最好|最美|最漂亮|最适合|最合适", "BEST_VIEWING"),
    ):
        if re.search(pattern, value):
            return period_type
    return "OTHER"


def _suitability_from_text(value: str, period_type: str) -> str:
    if period_type in {"FISHING_CLOSURE", "SEASONAL_CLOSURE"} and re.search(
        r"休渔|禁渔|禁捕|封山|闭园|停航|封航", value
    ):
        return "RESTRICTED"
    if re.search(r"避开|不建议|不适合|不要|谨慎", value):
        return "AVOID"
    if re.search(r"最佳|最好|最美|最漂亮|最适合|最合适|推荐|适宜|值得", value):
        return "RECOMMENDED"
    return "INFORMATIONAL"


def _calendar_fields_from_text(value: str) -> dict[str, object]:
    seasons = (
        (r"春季|春天|春日", "SPRING"),
        (r"夏季|夏天|夏日", "SUMMER"),
        (r"秋季|秋天|秋日", "AUTUMN"),
        (r"冬季|冬天|冬日", "WINTER"),
    )
    season = next(
        (code for pattern, code in seasons if re.search(pattern, value)),
        None,
    )
    month_segment = next(
        (code for text, code in (("上旬", "EARLY"), ("中旬", "MID"), ("下旬", "LATE")) if text in value),
        None,
    )
    day_times = (
        (r"清晨|日出", "EARLY_MORNING"),
        (r"上午", "MORNING"),
        (r"中午|正午", "NOON"),
        (r"下午", "AFTERNOON"),
        (r"日落|黄昏", "SUNSET"),
        (r"傍晚|晚间", "EVENING"),
        (r"夜间|夜晚", "NIGHT"),
    )
    day_time_slot = next(
        (code for pattern, code in day_times if re.search(pattern, value)),
        None,
    )
    return {"season": season, "month_segment": month_segment, "day_time_slot": day_time_slot}


def _normalized_evidence_text(value: str) -> str:
    return re.sub(r"[^\w]", "", value.casefold())


def _visit_windows_from_candidate(
    item: dict[str, Any], segment_ids: list[str], segment_texts: dict[str, str]
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    seen: set[tuple[object, ...]] = set()

    def add(raw: dict[str, Any], evidence_ids: list[str], source_text: str) -> None:
        evidence = "".join(segment_texts.get(segment_id, "") for segment_id in evidence_ids)
        if not source_text or _normalized_evidence_text(source_text) not in _normalized_evidence_text(
            evidence
        ):
            return
        period_type = str(raw.get("period_type") or "OTHER").upper()
        suitability = str(raw.get("suitability") or "INFORMATIONAL").upper()
        season = str(raw.get("season") or "").upper() or None
        month_segment = str(raw.get("month_segment") or "").upper() or None
        day_time_slot = str(raw.get("day_time_slot") or "").upper() or None
        period_type = period_type if period_type in VISIT_PERIOD_TYPES else "OTHER"
        suitability = suitability if suitability in VISIT_SUITABILITIES else "INFORMATIONAL"
        season = season if season in VISIT_SEASONS else None
        month_segment = month_segment if month_segment in VISIT_MONTH_SEGMENTS else None
        day_time_slot = day_time_slot if day_time_slot in VISIT_DAY_TIME_SLOTS else None
        raw_months = raw.get("months") if isinstance(raw.get("months"), list) else [raw.get("month")]
        months = list(
            dict.fromkeys(
                int(value) for value in raw_months if str(value).isdigit() and 1 <= int(value) <= 12
            )
        )
        for month in months or [None]:
            candidate = {
                "period_type": period_type,
                "suitability": suitability,
                "season": season,
                "month": month,
                "month_segment": month_segment,
                "day_time_slot": day_time_slot,
                "source_text": source_text[:500],
                "segment_ids": evidence_ids,
            }
            key = tuple(candidate[field] for field in candidate if field != "segment_ids")
            if key not in seen:
                seen.add(key)
                windows.append(candidate)

    for raw in item.get("visit_windows") or []:
        if not isinstance(raw, dict):
            continue
        evidence_ids = [value for value in raw.get("segment_ids", []) if value in segment_ids]
        add(raw, evidence_ids, str(raw.get("source_text") or "").strip())

    covered_sources = {_normalized_evidence_text(window["source_text"]) for window in windows}
    for segment_id in segment_ids:
        text = segment_texts.get(segment_id, "")
        if not TEMPORAL_CUE.search(text):
            continue
        for sentence in (part.strip() for part in re.split(r"[。！？!?；;]", text)):
            if (
                not sentence
                or not TEMPORAL_CUE.search(sentence)
                or _normalized_evidence_text(sentence) in covered_sources
            ):
                continue
            period_type = _period_type_from_text(sentence)
            fields = _calendar_fields_from_text(sentence)
            add(
                {
                    **fields,
                    "period_type": period_type,
                    "suitability": _suitability_from_text(sentence, period_type),
                    "months": _months_in_text(sentence),
                },
                [segment_id],
                sentence,
            )
            covered_sources.add(_normalized_evidence_text(sentence))
    return windows


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
    domain_messages, domain_versions = domain_context_messages(
        db, policy.domain_pack_ids, AICapability(capability)
    )
    enriched_messages = [messages[0], *domain_messages, *messages[1:]] if messages else domain_messages
    return AIWorkloadGateway().execute_cached_json(
        db,
        job=job,
        stage=stage,
        capability=capability,
        provider=provider,
        provider_name=provider_name,
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
        cache_enabled=bool(policy.cache_enabled),
        force_regenerate=policy.force_regenerate,
    )


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


def _profile_request_interval(config: dict[str, str] | None, default: float) -> float:
    value = (config or {}).get("request_interval_seconds", "")
    return default if not value else float(value)


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
    primary_id = str(routes.get("primary_id") or "")
    fallback_id = str(routes.get("fallback_id") or "")
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
            primary_id, fallback_id = (local_id, remote_id) if local_id else (remote_id, "")
        elif mode == "REMOTE_FIRST":
            primary_id, fallback_id = (remote_id, local_id) if remote_id else (local_id, "")
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
        primary_interval: float | None = None,
        fallback_interval: float | None = None,
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
            request_interval_seconds=(
                policy.ai_request_interval_seconds if primary_interval is None else primary_interval
            ),
            fallback_request_interval_seconds=fallback_interval,
            on_retry=on_retry,
            on_attempt=on_attempt,
            request_options=request_options,
        )

    if primary_config is None:
        raise ProviderUnavailable("尚未在设置中选择主模型")
    timeout_cap = (
        transcript_processing_config(db).timeout_seconds if role == "transcript_correction" else None
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
        return (
            with_policy(
                fallback,
                fallback_model,
                primary_interval=_profile_request_interval(
                    fallback_config, policy.ai_request_interval_seconds
                ),
            ),
            fallback_name,
            fallback_model,
        )
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
    return (
        with_policy(
            primary,
            primary_model,
            fallback,
            fallback_model,
            _profile_request_interval(primary_config, policy.ai_request_interval_seconds),
            _profile_request_interval(fallback_config, policy.ai_request_interval_seconds)
            if fallback_config
            else None,
        ),
        primary_name,
        primary_model,
    )


def materialize_transcript(
    db: Session,
    source: Source,
    asset: VideoAsset,
    raw_segments: list[dict[str, Any]],
    *,
    source_kind: str,
    language: str = "zh-CN",
    metadata: dict[str, Any] | None = None,
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
        ratio = normalized[-1]["end_ms"] / asset.duration_ms
        if 8 <= ratio <= 12:
            normalized = [
                {
                    **item,
                    "start_ms": round(item["start_ms"] / 10),
                    "end_ms": round(item["end_ms"] / 10),
                }
                for item in normalized
            ]
        else:
            raise ValueError("转写末段时间显著超过视频时长，拒绝物化异常时间轴")
    fingerprint = "\n".join(f"{item['start_ms']}:{item['end_ms']}:{item['text']}" for item in normalized)
    fingerprint_sha = __import__("hashlib").sha256(fingerprint.encode()).hexdigest()
    provenance = metadata or {}
    existing = db.scalar(
        select(Transcript).where(Transcript.video_asset_id == asset.id).order_by(Transcript.version.desc())
    )
    if (
        existing
        and (
            existing.metadata_json.get("fingerprint") == fingerprint
            or existing.metadata_json.get("fingerprint_sha256") == fingerprint_sha
        )
        and existing.source_kind == source_kind
        and (existing.metadata_json.get("validation_status") == provenance.get("validation_status"))
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
        metadata_json={
            "kind": "VIDEO_TRANSCRIPT",
            "video_asset_id": asset.id,
            "source_kind": source_kind,
            **provenance,
        },
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
            **provenance,
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


def _map_facts_context(note: AINoteVersion, max_chars: int) -> str:
    facts = [item for item in note.map_facts_json or [] if isinstance(item, dict)]
    selected: list[dict[str, Any]] = []
    for fact in facts:
        candidate = json.dumps({"section_facts": [*selected, fact]}, ensure_ascii=False)
        if len(candidate) > max_chars and selected:
            break
        if len(candidate) <= max_chars:
            selected.append(fact)
    if not selected:
        return '没有可用的 SectionFacts；返回 {"places": []}，不要依据常识补全地点。'
    return "以下是按时间块验证的 SectionFacts。仅据此提取地点，保留已有 Segment ID：\n" + json.dumps(
        {"section_facts": selected}, ensure_ascii=False
    )


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


def _overlapped_transcript_chunks(
    segments: list[Segment], max_chars: int, neighbor_segments: int
) -> list[list[Segment]]:
    chunks = _transcript_chunks(segments, max_chars)
    if neighbor_segments <= 0 or len(chunks) < 2:
        return chunks
    positions = {segment.id: index for index, segment in enumerate(segments)}
    result = []
    for index, chunk in enumerate(chunks):
        if index == 0:
            result.append(chunk)
            continue
        first = positions[chunk[0].id]
        result.append(segments[max(0, first - neighbor_segments) : positions[chunk[-1].id] + 1])
    return result


def _normalized_text(value: object) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _candidate_has_evidence(candidate: dict[str, Any], ids: list[str], segment_texts: dict[str, str]) -> bool:
    quote = _normalized_text(candidate.get("quote"))
    raw_name = _normalized_text(candidate.get("raw_name") or candidate.get("name"))
    evidence = "".join(_normalized_text(segment_texts.get(segment_id, "")) for segment_id in ids)
    return bool(quote and raw_name and quote in evidence and raw_name in evidence)


def _merge_place_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        raw_name = str(candidate.get("raw_name") or candidate.get("name") or "")
        key = (
            _normalized_insight_key(raw_name),
            _normalized_insight_key(candidate.get("city_hint")),
            str(candidate.get("place_type") or "UNKNOWN"),
        )
        if not key[0]:
            continue
        current = merged.get(key)
        if current is None:
            merged[key] = {
                **candidate,
                "segment_ids": list(candidate.get("segment_ids") or []),
            }
            continue
        current["segment_ids"] = list(
            dict.fromkeys([*current["segment_ids"], *candidate.get("segment_ids", [])])
        )
        quotes = [value for value in (current.get("quote"), candidate.get("quote")) if value]
        current["quote"] = "\n".join(dict.fromkeys(str(value) for value in quotes))[:1000]
        for field in (
            "highlights",
            "recommended_items",
            "best_months",
            "best_seasons",
            "best_time_slots",
            "visit_windows",
            "warnings",
        ):
            before = current.get(field, [])
            after = candidate.get(field, [])
            values = [
                *(before if isinstance(before, list) else []),
                *(after if isinstance(after, list) else []),
            ]
            current[field] = list(
                dict.fromkeys(json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values)
            )
            current[field] = [json.loads(value) for value in current[field]]
        current["confidence"] = max(
            normalized_confidence(current.get("confidence")),
            normalized_confidence(candidate.get("confidence")),
        )
    return list(merged.values())


def _place_evidence_index(mentions: list[PlaceMention]) -> list[dict[str, object]]:
    return [
        {
            "mention_id": mention.id,
            "name": mention.name,
            "place_type": mention.place_type,
            "segment_ids": mention.segment_ids_json,
            "quotes": [mention.quote],
        }
        for mention in mentions
        if mention.extraction_status != "USER_REJECTED" and mention.quote
    ]


def _ground_section(
    item: dict[str, object], segments: list[Segment], mentions: list[PlaceMention]
) -> dict[str, object] | None:
    valid_ids = {segment.id for segment in segments}
    ids = [str(value) for value in item.get("segment_ids", []) if value in valid_ids]
    if not ids:
        return None
    evidence = "\n".join(
        str(segment.corrected_text or segment.text) for segment in segments if segment.id in ids
    )
    requested_quotes = [str(value).strip() for value in item.get("supporting_quotes", []) if value]
    quotes = [quote for quote in requested_quotes if _normalized_text(quote) in _normalized_text(evidence)]
    related = [mention for mention in mentions if set(mention.segment_ids_json) & set(ids)]
    requested_ids = {str(value) for value in item.get("place_mention_ids", [])}
    related = [mention for mention in related if not requested_ids or mention.id in requested_ids]
    kind = str(item.get("section_kind") or "").upper()
    if kind not in NOTE_SECTION_KINDS:
        kind = "PLACE" if related else "SUPPLEMENTAL"
    if kind in {"PLACE", "AREA", "ROUTE"} and not related:
        return None
    if not quotes:
        quotes = [
            str(
                next(
                    (
                        segment.corrected_text or segment.text
                        for segment in segments
                        if segment.id in ids
                    ),
                )
            )
        ]
    names = list(dict.fromkeys(mention.name for mention in related))
    if kind == "PLACE":
        heading = names[0]
    elif kind == "AREA":
        city = next((mention.city_hint for mention in related if mention.city_hint), "周边")
        heading = f"{city}｜{'・'.join(names[:3])}"
    elif kind == "ROUTE":
        heading = " → ".join(names[:4])
    else:
        heading = "补充信息"
    return {
        **item,
        "section_kind": kind,
        "heading": heading[:500],
        "segment_ids": ids,
        "place_mention_ids": [mention.id for mention in related],
        "supporting_quotes": quotes[:8],
    }


def _ground_map_facts(
    facts: list[dict[str, object]], segments: list[Segment], mentions: list[PlaceMention]
) -> list[dict[str, object]]:
    valid_ids = {segment.id for segment in segments}
    result = []
    for fact in facts:
        ids = [str(value) for value in fact.get("segment_ids", []) if value in valid_ids]
        if not ids:
            continue
        evidence = "\n".join(
            str(segment.corrected_text or segment.text) for segment in segments if segment.id in ids
        )
        quotes = [
            str(value)
            for value in fact.get("supporting_quotes", [])
            if _normalized_text(value) in _normalized_text(evidence)
        ]
        if not quotes:
            quotes = [
                str(
                    next(
                        (segment.corrected_text or segment.text for segment in segments if segment.id in ids),
                        "",
                    )
                )
            ]
        result.append(
            {
                **fact,
                "segment_ids": ids,
                "supporting_quotes": quotes[:8],
                "place_mention_ids": [
                    mention.id for mention in mentions if set(mention.segment_ids_json) & set(ids)
                ],
                "places": [],
            }
        )
    return result


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


def _correction_batch_size(provider_name: str, configured: int) -> int:
    return min(configured, 32) if provider_name.lower() == "ollama" else configured


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
        _correction_batch_size(provider_name, processing.batch_size),
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
        "correction_prompt_supplement_hash": prompt_supplement_hash(db, "transcript_correction"),
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
            section_count = (
                db.scalar(
                    select(func.count(AINoteSection.id)).where(
                        AINoteSection.ai_note_version_id == note.current_version_id
                    )
                )
                or 0
            )
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
    mentions: list[PlaceMention] | None = None,
) -> AINoteVersion:
    mentions = mentions or []
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
                        f"视频标题：{asset.title}\n已验证地点 Evidence Index："
                        f"{json.dumps(_place_evidence_index(mentions), ensure_ascii=False)}\n"
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
            map_facts.extend(_ground_map_facts(_section_facts(payload, chunk_ids), chunk, mentions))
            sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
            raw_sections.extend(
                item
                for item in sections
                if isinstance(item, dict) and any(value in chunk_ids for value in item.get("segment_ids", []))
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
                    "content": ("以下是带逐字 Evidence 的 GroundedEvidencePack。仅据此生成全局笔记：\n")
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
    for ordinal, raw_item in enumerate(raw_sections):
        item = _ground_section(raw_item, segments, mentions)
        if item is None:
            continue
        segment_ids = list(item["segment_ids"])
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
                section_kind=str(item["section_kind"]),
                thesis=thesis,
                summary=summary,
                bullets_json=bullets,
                anchor_id=f"section-{section_id}",
                body_markdown=body,
                segment_ids_json=segment_ids,
                place_mention_ids_json=list(item["place_mention_ids"]),
                evidence_quotes_json=list(item["supporting_quotes"]),
                start_ms=refs[0].locator_json.get("start_ms") if refs else None,
                end_ms=refs[-1].locator_json.get("end_ms") if refs else None,
            )
        )
        rendered.extend(["", f"## {heading}", body])
        created_sections += 1
    if not created_sections and segments:
        fallback = _fallback_sections([segments])
        item = _ground_section(fallback[0], segments, mentions) or {
            **fallback[0],
            "section_kind": "SUPPLEMENTAL",
            "place_mention_ids": [],
            "supporting_quotes": [str(segments[0].corrected_text or segments[0].text)],
        }
        refs = segments
        section_id = new_id("nsc")
        db.add(
            AINoteSection(
                id=section_id,
                ai_note_version_id=version.id,
                ordinal=0,
                heading=str(item["heading"]),
                section_kind=str(item["section_kind"]),
                thesis=str(item.get("thesis") or ""),
                summary=str(item.get("summary") or ""),
                bullets_json=list(item.get("bullets") or []),
                anchor_id=f"section-{section_id}",
                body_markdown=str(item["body_markdown"]),
                segment_ids_json=list(item["segment_ids"]),
                place_mention_ids_json=list(item["place_mention_ids"]),
                evidence_quotes_json=list(item["supporting_quotes"]),
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
    note: AINoteVersion | None,
    segments: list[Segment],
    job: Job | None = None,
) -> list[PlaceMention]:
    policy = _resolved_stage_policy(db, "EXTRACT_TRAVEL_FACTS", job)
    chunk_chars = int(policy.chunk_size or PLACE_EXTRACTION_CHUNK_CHARS)
    neighbor_segments = int(policy.neighbor_segments or PLACE_EXTRACTION_NEIGHBOR_SEGMENTS)
    provider, provider_name, model = provider_for_role(db, settings, "travel_place_extraction", job)
    prompt = (Path(__file__).resolve().parents[1] / "prompts" / "travel_place_extraction.md").read_text(
        encoding="utf-8"
    )
    candidates: list[dict[str, Any]] = []
    chunks = _overlapped_transcript_chunks(segments, chunk_chars, neighbor_segments)
    for chunk_index, chunk in enumerate(chunks):
        response = _cached_stage_json(
            db,
            job=job,
            stage="EXTRACT_TRAVEL_FACTS",
            capability="ENTITY_EXTRACTION",
            provider=provider,
            provider_name=provider_name,
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                *prompt_supplement_messages(db, "travel_place_extraction"),
                {
                    "role": "user",
                    "content": (
                        f"视频标题：{asset.title}\n分块：{chunk_index + 1}\n"
                        + _transcript_context(chunk, chunk_chars)
                    ),
                },
            ],
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
        values = parse_model_json(response.content).get("places", [])
        candidates.extend(value for value in values if isinstance(value, dict))
    valid_ids = {segment.id for segment in segments}
    segment_texts = {segment.id: segment.corrected_text or segment.text for segment in segments}
    rejected_names = {
        _normalized_insight_key(item.raw_name or item.name)
        for item in db.scalars(
            select(PlaceMention).where(
                PlaceMention.video_asset_id == asset.id,
                PlaceMention.extraction_status == "USER_REJECTED",
            )
        )
    }
    created: list[PlaceMention] = []
    for item in _merge_place_candidates(candidates)[:80]:
        ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not ids or not item.get("name") or not _candidate_has_evidence(item, ids, segment_texts):
            record_event(
                db,
                "place.extraction.evidence_rejected",
                "地点候选缺少可逐字核验的转写 Evidence，已丢弃",
                component="video-pipeline",
                level="WARNING",
                entity_type="video_asset",
                entity_id=asset.id,
                detail={"name": str(item.get("name") or "")[:300]},
                commit=False,
            )
            continue
        if _normalized_insight_key(item.get("raw_name") or item["name"]) in rejected_names:
            continue
        insights = _insights_from_candidate(item, ids, segment_texts)
        visit_windows = _visit_windows_from_candidate(item, ids, segment_texts)
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=note.id if note else None,
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
            metadata_json={
                "insights": insights,
                "visit_windows": visit_windows,
                "resolver_context": {
                    "aliases": [str(value)[:300] for value in item.get("aliases", []) if value][:10],
                    "district_hint": str(item.get("district_hint") or "")[:64],
                    "nearby_landmarks": [
                        str(value)[:300] for value in item.get("nearby_landmarks", []) if value
                    ][:10],
                },
            },
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


def _normalized_insight_key(value: object) -> str:
    return re.sub(r"\s+", "", str(value).strip().lower())[:128]


def _insights_from_candidate(
    item: dict[str, Any], segment_ids: list[str], segment_texts: dict[str, str]
) -> list[dict[str, Any]]:
    """Keep structured source facts beside their mention until POI resolution assigns a Place."""
    if not segment_ids:
        return []
    result: list[dict[str, Any]] = []

    def add(
        insight_type: str,
        value: object,
        *,
        value_key: object = "",
        value_json: dict[str, Any] | None = None,
        evidence_ids: list[str] | None = None,
        source_quote: object = "",
        provenance: str = "SOURCE_FACT",
    ) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            ids = [value for value in evidence_ids or [] if value in segment_ids]
            if not ids:
                ids = [
                    segment_id
                    for segment_id in segment_ids
                    if _normalized_insight_key(text)
                    in _normalized_insight_key(segment_texts.get(segment_id, ""))
                ][:1]
            if not ids and insight_type == "BEST_MONTH":
                ids = [segment_id for segment_id in segment_ids if "月" in segment_texts.get(segment_id, "")][
                    :1
                ]
            ids = ids or list(segment_ids)
            quote = str(source_quote or "").strip() or str(segment_texts.get(ids[0], "")).strip()
            result.append(
                {
                    "insight_type": insight_type,
                    "value_key": _normalized_insight_key(value_key or text),
                    "value_text": text[:500],
                    "value_json": value_json or {},
                    "segment_ids": ids,
                    "source_quote": quote[:500],
                    "provenance": provenance,
                }
            )

    for value in item.get("highlights") or [item.get("feature") or item.get("reason")]:
        add("HIGHLIGHT", value)
    for value in item.get("recommended_items") or [item.get("experience")]:
        if isinstance(value, dict):
            add(
                "RECOMMENDED_ITEM",
                value.get("name") or value.get("value"),
                value_key=value.get("category"),
                value_json={"category": value.get("category", "")},
                evidence_ids=value.get("segment_ids"),
                source_quote=value.get("source_quote"),
            )
        else:
            add("RECOMMENDED_ITEM", value)
    for value in item.get("best_months") or []:
        month = str(value).zfill(2) if str(value).isdigit() else str(value)
        add("BEST_MONTH", f"{int(value)}月" if str(value).isdigit() else value, value_key=month)
    for value in item.get("best_seasons") or []:
        add("BEST_SEASON", value)
    for value in item.get("best_time_slots") or []:
        add("BEST_TIME_SLOT", value)
    for insight_type, field in (
        ("SUGGESTED_DURATION", "suggested_duration"),
        ("PRICE", "price"),
        ("QUEUE", "queue"),
        ("AUDIENCE", "audience"),
        ("WARNING", "warnings"),
        ("AUTHOR_OPINION", "author_opinion"),
    ):
        values = item.get(field) or (item.get("warning") if field == "warnings" else [])
        for value in values if isinstance(values, list) else [values]:
            add(
                insight_type,
                value,
                provenance="SOURCE_OPINION" if insight_type == "AUTHOR_OPINION" else "SOURCE_FACT",
            )
    return result


def materialize_place_insights(db: Session, mention: PlaceMention) -> None:
    if not mention.place_id or not mention.segment_ids_json:
        return
    db.query(PlaceInsightItem).filter(
        PlaceInsightItem.place_mention_id == mention.id,
        PlaceInsightItem.provenance.in_(("SOURCE_FACT", "SOURCE_OPINION")),
    ).delete(synchronize_session=False)
    asset = db.get(VideoAsset, mention.video_asset_id)
    for item in mention.metadata_json.get("insights", []):
        value_key, value_json = normalize_insight(
            str(item["insight_type"]),
            str(item["value_text"]),
            str(item.get("value_key") or ""),
            item.get("value_json") if isinstance(item.get("value_json"), dict) else {},
        )
        db.add(
            PlaceInsightItem(
                place_id=mention.place_id,
                place_mention_id=mention.id,
                source_id=asset.source_id if asset else None,
                insight_type=str(item["insight_type"]),
                value_key=value_key,
                value_text=str(item["value_text"]),
                value_json=value_json,
                provenance=str(item.get("provenance") or "SOURCE_FACT"),
                confidence=mention.confidence,
                segment_ids_json=list(item.get("segment_ids") or mention.segment_ids_json),
                source_quote=str(item.get("source_quote") or "")[:500],
            )
        )
    db.query(PlaceVisitWindow).filter(
        PlaceVisitWindow.place_mention_id == mention.id,
        PlaceVisitWindow.provenance == "SOURCE_FACT",
    ).delete(synchronize_session=False)
    for item in mention.metadata_json.get("visit_windows", []):
        if not isinstance(item, dict):
            continue
        db.add(
            PlaceVisitWindow(
                place_id=mention.place_id,
                place_mention_id=mention.id,
                source_id=asset.source_id if asset else None,
                season=item.get("season"),
                month=item.get("month"),
                month_segment=item.get("month_segment"),
                day_time_slot=item.get("day_time_slot"),
                period_type=item.get("period_type") or "OTHER",
                suitability=item.get("suitability") or "INFORMATIONAL",
                source_text=str(item.get("source_text") or "")[:500],
                segment_ids_json=list(item.get("segment_ids") or mention.segment_ids_json),
                provenance="SOURCE_FACT",
                confidence=mention.confidence,
            )
        )


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
            candidates = _rank_poi_candidates(provider, mention, mentions)
        except Exception as exc:
            mention.metadata_json = {**mention.metadata_json, "poi_error": str(exc)[:240]}
            continue
        if not candidates:
            mention.resolution_status = ResolutionStatus.UNRESOLVED.value
            continue
        selected = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        review_reasons = _poi_review_reasons(selected, runner_up)
        if review_reasons:
            mention.resolution_status = ResolutionStatus.REVIEW.value
            mention.metadata_json = {
                **mention.metadata_json,
                "poi_candidates": [_candidate_metadata(item) for item in candidates[:5]],
                "reason": "；".join(review_reasons),
                "poi_decision": "REVIEW",
            }
            continue
        try:
            verified = provider.detail(selected.provider_id)
        except Exception:
            verified = None
        if verified is None:
            mention.resolution_status = ResolutionStatus.REVIEW.value
            mention.metadata_json = {
                **mention.metadata_json,
                "poi_candidates": [_candidate_metadata(item) for item in candidates[:5]],
                "reason": "POI 详情复核失败，等待人工确认",
                "poi_decision": "REVIEW",
            }
            continue
        selected = verified
        tombstone = db.scalar(
            select(PlaceDeletionTombstone).where(
                PlaceDeletionTombstone.external_provider == "AMap",
                PlaceDeletionTombstone.external_poi_id == selected.provider_id,
            )
        )
        if tombstone is not None:
            mention.resolution_status = ResolutionStatus.REJECTED.value
            mention.metadata_json = {
                **mention.metadata_json,
                "deleted_by_user": True,
                "suppressed_poi_id": selected.provider_id,
            }
            continue
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
        mention.metadata_json = {
            **mention.metadata_json,
            "poi_name": selected.name,
            "poi_id": selected.provider_id,
            "poi_score": candidates[0].score,
            "poi_match_reasons": candidates[0].match_reasons,
            "poi_explanation": candidates[0].match_explanation,
            "poi_candidates": [_candidate_metadata(item) for item in candidates[:5]],
            "poi_decision": "CONFIRMED",
        }
        materialize_place_insights(db, mention)
        confirmed += 1
    db.commit()
    return confirmed, len(mentions) - confirmed


def _rank_poi_candidates(
    provider: AMapPOIProvider, mention: PlaceMention, mentions: list[PlaceMention] | None = None
) -> list[POICandidate]:
    queries = _poi_queries(mention)
    deduped: dict[str, POICandidate] = {}
    for query, city in queries:
        for candidate in provider.search(query, city, city_limit=bool(city)):
            if candidate.provider_id and candidate.provider_id not in deduped:
                deduped[candidate.provider_id] = candidate
    for candidate in deduped.values():
        candidate.score, candidate.match_reasons, candidate.match_explanation = _poi_score(
            mention, candidate, mentions or []
        )
    return sorted(deduped.values(), key=lambda item: (-item.score, item.name))


def _poi_queries(mention: PlaceMention) -> list[tuple[str, str]]:
    context = mention.metadata_json.get("resolver_context", {})
    aliases = context.get("aliases", []) if isinstance(context, dict) else []
    names = [mention.suggested_name, mention.name, mention.raw_name, *aliases]
    locations = [mention.city_hint, mention.province_hint, "", *([mention.city_hint] * len(aliases))]
    result: list[tuple[str, str]] = []
    for name, location in zip(names, locations, strict=True):
        value = (name or "").strip()
        pair = (value, (location or "").strip())
        if value and pair not in result:
            result.append(pair)
    return result[:5]


def _poi_score(
    mention: PlaceMention, candidate: POICandidate, mentions: list[PlaceMention] | None = None
) -> tuple[int, list[str], dict[str, Any]]:
    reasons: list[str] = []
    context = mention.metadata_json.get("resolver_context", {})
    context = context if isinstance(context, dict) else {}
    aliases = [str(value) for value in context.get("aliases", []) if value]
    names = [value for value in (mention.suggested_name, mention.name, mention.raw_name, *aliases) if value]
    candidate_key = _normalized_insight_key(candidate.name)
    similarity = max(
        (
            1.0
            if _normalized_insight_key(value) == candidate_key
            else 1.0
            if _normalized_insight_key(value) in candidate_key
            else SequenceMatcher(None, _normalized_insight_key(value), candidate_key).ratio()
            for value in names
        ),
        default=0.0,
    )
    score = round(similarity * 50)
    if similarity >= 0.9:
        reasons.append("名称高度匹配")
    district_hint = str(context.get("district_hint") or "")
    nearby = [str(value) for value in context.get("nearby_landmarks", []) if value]
    location_text = " ".join((candidate.province, candidate.city, candidate.district, candidate.address))
    city_match = bool(mention.city_hint and mention.city_hint in location_text)
    province_match = bool(mention.province_hint and mention.province_hint in location_text)
    district_match = bool(district_hint and district_hint in location_text)
    if mention.city_hint and mention.city_hint in (candidate.city + candidate.address):
        score += 20
        reasons.append("城市匹配")
    if province_match:
        score += 5
        reasons.append("省份匹配")
    if district_match:
        score += 10
        reasons.append("区县匹配")
    type_prefixes = {
        "RESTAURANT": "05",
        "SCENIC_AREA": "11",
        "MUSEUM": "14",
        "PARK": "11",
        "TEMPLE": "11",
        "MARKET": "06",
        "BUSINESS_DISTRICT": "06",
        "ACCOMMODATION": "10",
        "TRANSIT": "15",
    }
    prefix = type_prefixes.get(mention.place_type)
    category_match = bool(prefix and candidate.typecode.startswith(prefix))
    if category_match:
        score += 15
        reasons.append("地点类型匹配")
    nearby_matches = [value for value in nearby if value in (candidate.name + candidate.address)]
    if nearby_matches:
        score += 10
        reasons.append("附近地标匹配")
    cross_cities = {item.city_hint for item in mentions or [] if item.id != mention.id and item.city_hint}
    cross_provinces = {
        item.province_hint for item in mentions or [] if item.id != mention.id and item.province_hint
    }
    cross_location_matches = sorted(
        value for value in cross_cities | cross_provinces if value and value in location_text
    )
    if cross_location_matches:
        score += 20 if not (city_match or province_match or district_match) else 5
        reasons.append("视频内地域上下文匹配")
    explanation = {
        "name_match": round(similarity, 3),
        "city_match": city_match,
        "province_match": province_match,
        "district_match": district_match,
        "category_match": category_match,
        "nearby_context": nearby_matches,
        "cross_place_context": cross_location_matches,
        "coordinate_valid": 73.5 <= candidate.longitude <= 135.1 and 18 <= candidate.latitude <= 53.6,
    }
    return min(score, 100), reasons, explanation


def _poi_review_reasons(selected: POICandidate, runner_up: POICandidate | None) -> list[str]:
    explanation = selected.match_explanation
    reasons: list[str] = []
    if selected.score < 85:
        reasons.append("候选综合分不足")
    if float(explanation.get("name_match") or 0) < 0.9:
        reasons.append("名称匹配不够强")
    if not any(
        explanation.get(key)
        for key in ("city_match", "province_match", "district_match", "nearby_context", "cross_place_context")
    ):
        reasons.append("地域上下文不足")
    if not explanation.get("category_match"):
        reasons.append("地点类型不兼容")
    if runner_up and selected.score - runner_up.score < 15:
        reasons.append("第一、二候选差距过小")
    if not explanation.get("coordinate_valid"):
        reasons.append("候选坐标异常")
    return reasons


def _candidate_metadata(candidate: POICandidate) -> dict[str, Any]:
    return {
        "provider": "AMAP",
        "provider_id": candidate.provider_id,
        "name": candidate.name,
        "address": candidate.address,
        "province": candidate.province,
        "city": candidate.city,
        "district": candidate.district,
        "typecode": candidate.typecode,
        "longitude": candidate.longitude,
        "latitude": candidate.latitude,
        "score": candidate.score,
        "match_reasons": candidate.match_reasons,
        "match_explanation": candidate.match_explanation,
    }


def build_place_notes(db: Session, asset: VideoAsset, mentions: list[PlaceMention]) -> int:
    count = 0
    for place_id in dict.fromkeys(mention.place_id for mention in mentions if mention.place_id):
        place = db.get(Place, place_id)
        if place is None:
            continue
        previous = (
            db.scalar(select(func.max(PlaceNoteVersion.version)).where(PlaceNoteVersion.place_id == place.id))
            or 0
        )
        lines = [
            f"# {place.canonical_name or place.name}",
            "",
            f"- 校正名称：{place.canonical_name or place.name}",
        ]
        insights = db.scalars(
            select(PlaceInsightItem)
            .where(PlaceInsightItem.place_id == place.id, PlaceInsightItem.status == "ACTIVE")
            .order_by(PlaceInsightItem.insight_type, PlaceInsightItem.created_at)
        ).all()
        labels = {
            "highlights": "核心看点",
            "dishes": "推荐菜 / 核心体验",
            "visit_windows": "最佳月份/季节",
            "warnings": "注意事项",
            "prices": "价格",
            "queues": "排队",
            "opinions": "作者态度",
            "other": "其他观察",
        }
        source_ids = {item.source_id for item in insights if item.source_id}
        source_titles = {
            source.id: source.title or "来源未命名"
            for source in db.scalars(select(Source).where(Source.id.in_(source_ids))).all()
        }
        knowledge = aggregate_place_knowledge(insights, source_titles)
        for category, title in labels.items():
            for item in knowledge[category]:
                current = "" if item["current"] else " · 较早观察"
                lines.append(f"\n## {title} · {item['state']}{current}")
                lines.append(f"- {item['source_count'] or 1} 个来源观察；以下内容不等同于系统或个人推断。")
                provenance = {
                    "SOURCE_FACT": "来源事实",
                    "SOURCE_OPINION": "来源观点",
                    "SYSTEM_AGGREGATION": "系统聚合",
                    "PERSONAL_INFERENCE": "个人推断",
                    "USER_ADDED": "个人补充",
                }.get(item["provenance"], item["provenance"])
                for observation in item["observations"]:
                    lines.append(
                        f"- [{provenance}] {item['value_text']}"
                        f"（{observation['source_title']}：{observation['source_quote']}）"
                    )
        lines.append("- 状态：来源观察，建议到店前再次核验。")
        text = "\n".join(lines) + "\n"
        db.add(
            PlaceNoteVersion(
                place_id=place.id,
                version=previous + 1,
                markdown=text,
                model_provider="deterministic",
                model_name="evidence-template",
                evidence_count=len(insights),
            )
        )
        count += 1
    db.commit()
    return count
