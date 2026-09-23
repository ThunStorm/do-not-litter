from __future__ import annotations

import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.ai.capabilities import AICapability
from zhijian.ai.cost_router import RouteDecision, choose_auto_route
from zhijian.ai.domain_context import domain_context_hash, domain_context_messages
from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.job_config import SNAPSHOT_KEY, job_setting, job_video_note_chunk_chars
from zhijian.ai.policies import resolve_stage_policy
from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy, resolve_reliability_policy
from zhijian.ai.runtime_hints import read_runtime_hint, tighten_note_reduce_hint, tighten_runtime_hint
from zhijian.ai.stage_decision import decide_stage, record_stage_decision
from zhijian.ai.transcript_quality import correction_candidates, transcript_source_class
from zhijian.core.config import Settings
from zhijian.core.ids import new_id
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    ContentItem,
    Destination,
    DestinationPlaceLink,
    GroundedMapArtifact,
    Job,
    JobStep,
    Place,
    PlaceDeletionTombstone,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    PlaceVisitWindow,
    Segment,
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
    provider_error_details,
)
from zhijian.services.audit import record_event
from zhijian.services.jobs import JobCancelled, ensure_job_active
from zhijian.services.model_attempts import begin_model_attempt, finish_model_attempt
from zhijian.services.place_knowledge import aggregate_place_knowledge, normalize_insight
from zhijian.services.transcript_retention import retention_deadline
from zhijian.services.video_note_search import sync_video_note_search_index

TRANSCRIPT_CORRECTION_TIMEOUT_SECONDS = 180.0
TRANSCRIPT_CORRECTION_CHUNK_CHARS = 12_000
TRANSCRIPT_CORRECTION_BATCH_SIZE = 128
PLACE_EXTRACTION_CHUNK_CHARS = 8_000
PLACE_EXTRACTION_NEIGHBOR_SEGMENTS = 3
NOTE_SECTION_KINDS = {
    "PLACE",
    "AREA",
    "ROUTE",
    "SUPPLEMENTAL",
    "AREA_GUIDE",
    "PLACE_GUIDE",
    "MULTI_PLACE_LIST",
    "THEME",
    "CATEGORY_COMPARE",
    "EXPERIENCE",
    "FOOD",
    "MIXED",
}
LOW_INFORMATION_BULLETS = (
    "景色优美",
    "非常值得一去",
    "体验很好",
    "很有特色",
    "非常推荐",
    "环境不错",
    "值得打卡",
)
PROMPT_SUPPLEMENT_SETTING_KEY = "prompt:supplements"
PROMPT_CORE_CONTRACTS = {
    "transcript_correction": [
        "固定返回 JSON 对象与 changes 数组。",
        "只返回确实需要修改的 target Segment；未返回的 target 保持原文。",
        "不得返回 context Segment，不得新增或重复 Segment ID。",
        "字段固定为 segment_id、corrected_text、confidence、reason。",
        "不得改变时间码、分段边界或 Segment 身份。",
        "只校正识别、断句和专名错误，不得新增事实。",
    ],
    "video_note_summary": [
        "固定返回 JSON 对象及约定字段结构。",
        "顶层只使用 overview、warnings、sections、section_facts。",
        "章节字段保持 heading、thesis、summary、bullets、body_markdown、segment_ids 与 content_unit_id；"
        "比较/背景实体不得改写成推荐地点。",
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
        "名称歧义只能保留候选并进入校验，不得伪造已确认 POI；"
        "必须保留 content_unit_id、subject_role、visit_intent、poi_policy，REFERENCE_ONLY 不进入 POI。",
    ],
}
ROLE_STAGE = {
    "transcript_correction": "TRANSCRIPT_CORRECTION",
    "video_note_summary": "GENERATE_AI_NOTE",
    "note_reduce": "NOTE_REDUCE",
    "grounded_map": "GROUND_MAP",
    "grounded_map_escalation": "GROUND_MAP",
    "travel_place_extraction": "EXTRACT_TRAVEL_FACTS",
    "visual_fact": "VISION_FACT",
}
NOTE_RENDER_PROFILES = {
    "CURRENT_DEFAULT": {
        "version": "1",
        "instruction": "保持当前完整视频笔记结构，逐段引用 Grounded Evidence。",
        "overview_limit": 800,
        "max_bullets": 6,
    },
    "COMPACT": {
        "version": "1",
        "instruction": "面向快速回看，优先结论、地点和注意事项；不得省略 Evidence 绑定。",
        "overview_limit": 420,
        "max_bullets": 3,
    },
    "DETAILED": {
        "version": "1",
        "instruction": "保留更多已验证细节、时间线和条件，但不得补充 Evidence 之外的事实。",
        "overview_limit": 1200,
        "max_bullets": 8,
    },
    "TRAVEL_GUIDE": {
        "version": "1",
        "instruction": "按旅行者决策组织已验证的到访建议、地点和注意事项；不得编排行程或虚构信息。",
        "overview_limit": 800,
        "max_bullets": 6,
    },
}


def note_render_profile(profile_id: str) -> tuple[str, dict[str, object]]:
    profile = NOTE_RENDER_PROFILES.get(profile_id)
    if profile is None:
        raise ValueError(f"不支持的笔记渲染 Profile：{profile_id}")
    return profile_id, profile


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

# AMap typecodes are hierarchical.  Keep the mapping here so candidate scoring,
# review explanations and offline benchmarks cannot silently drift apart.
PLACE_TYPE_CATEGORY_PREFIXES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "RESTAURANT": (("05",), ("06",)),
    "SCENIC_AREA": (("11",), ("14",)),
    "NEIGHBORHOOD": (("1203", "1901"), ("12", "19")),
    "PEDESTRIAN_STREET": (("0614", "1901"), ("06", "19")),
    "BUSINESS_DISTRICT": (("0601", "0614"), ("06",)),
    "MARKET": (("0607", "0614"), ("06",)),
    "PARK": (("11",), ()),
    "MUSEUM": (("14",), ()),
    "TEMPLE": (("11",), ()),
    "VILLAGE": (("1901", "1203"), ("19", "12")),
    "TOWN": (("1102", "1901"), ("11", "19")),
    "LANDMARK": (("11", "19"), ()),
    "ACCOMMODATION": (("10",), ("12",)),
    "HOTEL": (("10",), ("12",)),
    "TRANSIT": (("15",), ()),
    "TRANSPORT": (("15",), ()),
}


def _category_compatibility(place_type: str, typecode: str) -> str:
    mapping = PLACE_TYPE_CATEGORY_PREFIXES.get(place_type)
    if not mapping or not typecode:
        return "UNMAPPED"
    strong, weak = mapping
    if any(typecode.startswith(prefix) for prefix in strong):
        return "STRONG"
    if any(typecode.startswith(prefix) for prefix in weak):
        return "WEAK"
    return "INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class ResolutionFeatureVector:
    """Deterministic V2 features; V1 remains the decision-maker during shadowing."""

    name_match: float
    city_match: bool
    province_match: bool
    district_match: bool
    category_match: str
    nearby_landmark_match: bool
    query_consensus_count: int
    candidate_gap: int
    coordinate_valid: bool
    cross_city_conflict: bool
    chain_risk: bool
    distance_to_cluster_m: float | None
    prior_confirmation_match: bool


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


def prompt_supplement_value(db: Session, role: str, job: Job | None = None) -> str:
    if not hasattr(db, "get"):
        return ""
    values = job_setting(db, PROMPT_SUPPLEMENT_SETTING_KEY, job)
    return str(values.get(role) or "").strip()


def prompt_supplement_hash(db: Session, role: str, job: Job | None = None) -> str:
    value = prompt_supplement_value(db, role, job)
    return sha256(f"prompt-supplement-v1\0{role}\0{value}".encode()).hexdigest()


def prompt_supplement_messages(db: Session, role: str, job: Job | None = None) -> list[dict[str, str]]:
    value = prompt_supplement_value(db, role, job)
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
    from zhijian.ai.structured_output import parse_json_object

    return parse_json_object(content)


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
    attempt_metadata: dict[str, Any] | None = None,
    result_validator: Callable[[LLMResult], None] | None = None,
) -> LLMResult:
    if not hasattr(db, "scalar"):
        return provider.generate_json(messages, model=model)
    policy = _resolved_stage_policy(db, stage, job)
    domain_messages, domain_versions = domain_context_messages(
        db, policy.domain_pack_ids, AICapability(capability), job
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
                    "GROUND_MAP": "travel_place_extraction",
                    "NOTE_REDUCE": "video_note_summary",
                }[stage],
                job,
            ),
        },
        cache_enabled=bool(policy.cache_enabled),
        force_regenerate=policy.force_regenerate,
        attempt_metadata=attempt_metadata,
        result_validator=result_validator,
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


def _profile_config(db: Session, profile_id: str | None, job: Job | None = None) -> dict[str, Any] | None:
    if not profile_id:
        return None
    return job_setting(db, f"model-profile:{profile_id}", job) or None


def _profile_location(config: dict[str, Any] | None) -> str:
    if not config:
        return ""
    return config.get("location") or ("LOCAL" if config.get("provider", "").lower() == "ollama" else "REMOTE")


def _profile_supports_capability(
    config: dict[str, Any] | None,
    capability: AICapability,
    *,
    allow_unverified: bool = False,
) -> bool:
    if not config or not bool(config.get("enabled", True)):
        return False
    capabilities = {str(item) for item in config.get("capabilities") or []}
    probe = str((config.get("probe_results") or {}).get(capability.value) or "NOT_TESTED").upper()
    if allow_unverified:
        return True
    return probe != "FAIL" and (not capabilities or capability.value in capabilities)


def _profile_request_interval(config: dict[str, Any] | None, default: float) -> float:
    value = (config or {}).get("request_interval_seconds")
    return default if not value else float(value)


def transcript_processing_config(db: Session, job: Job | None = None) -> TranscriptProcessingConfig:
    if not hasattr(db, "get"):
        return TranscriptProcessingConfig()
    return TranscriptProcessingConfig(**job_setting(db, "transcript-processing", job))


def transcript_force_full_correction(db: Session, job: Job | None) -> bool:
    return bool(_resolved_stage_policy(db, "TRANSCRIPT_CORRECTION", job).force_full_correction)


def _resolved_stage_policy(db: Session, stage: str, job: Job | None):
    if not hasattr(db, "get"):
        return resolve_stage_policy(stage)
    saved = job_setting(db, f"ai-stage-policy:{stage}", job)
    override = (job.payload_json.get("ai_overrides") or {}).get(stage) if job else None
    return resolve_stage_policy(
        stage,
        saved=saved or None,
        job_override=override if isinstance(override, dict) else None,
    )


def _provider_from_config(
    config: dict[str, Any], settings: Settings, profile_id: str, timeout_cap: float | None = None
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
        provider = OllamaProvider(base_url, timeout)
        provider.profile_id = profile_id
        return provider, "ollama", model
    store = build_secret_store(settings.secret_store, settings.data_dir)
    api_key = store.get(f"model-profile:{profile_id}:api-key")
    if not api_key:
        raise ProviderUnavailable("尚未保存模型的 API Key")
    provider = OpenAICompatibleProvider(
        name or "openai-compatible",
        base_url,
        api_key,
        timeout,
        supports_json_mode=bool(config.get("supports_json_mode")),
    )
    provider.profile_id = profile_id
    return provider, name or "openai-compatible", model


def provider_for_role(
    db: Session, settings: Settings, role: str, job: Job | None = None
) -> tuple[LLMProvider, str, str]:
    routes = job_setting(db, "model-routing", job)
    primary_id = str(routes.get("primary_id") or "")
    fallback_id = str(routes.get("fallback_id") or "")
    stage = ROLE_STAGE.get(role)
    stage_setting = job_setting(db, f"ai-stage-policy:{stage}", job) if stage else {}
    job_override = (job.payload_json.get("ai_overrides") or {}).get(stage) if job and stage else None
    automation_enabled = bool(job and job.payload_json.get("ai_automation_version") == "v2")
    resolved_policy = (
        resolve_stage_policy(
            stage,
            saved=stage_setting or None,
            job_override=job_override if isinstance(job_override, dict) else None,
        )
        if stage and (stage_setting or job_override or automation_enabled)
        else None
    )
    primary_config = _profile_config(db, primary_id, job)
    fallback_config = _profile_config(db, fallback_id, job)
    route_decision: RouteDecision | None = None
    budget_pressure = bool(
        job and str((job.payload_json.get("ai_soft_budget") or {}).get("status") or "") == "WARNING"
    )
    if resolved_policy:
        local_id = resolved_policy.local_profile_id
        remote_id = resolved_policy.remote_profile_id
        candidates = tuple(
            (item_id, config)
            for item_id, config in ((primary_id, primary_config), (fallback_id, fallback_config))
            if _profile_supports_capability(
                config,
                resolved_policy.capability,
                allow_unverified=resolved_policy.allow_unverified_model,
            )
        )
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
        elif mode == "AUTO":
            candidate_ids = {item for item in (primary_id, fallback_id, local_id, remote_id) if item}
            candidates = {
                item_id: config
                for item_id in candidate_ids
                if (config := _profile_config(db, item_id, job)) is not None
            }
            route_decision = choose_auto_route(
                stage,
                resolved_policy.capability,
                candidates,
                quality_preset=(
                    str(job.payload_json.get("quality_preset") or "BALANCED") if job else "BALANCED"
                ),
                budget_pressure=budget_pressure,
            )
            if route_decision:
                primary_id, fallback_id = route_decision.primary_id, route_decision.fallback_id
        if role == "grounded_map_escalation":
            primary_id, fallback_id = remote_id, ""
        primary_config = _profile_config(db, primary_id, job)
        fallback_config = _profile_config(db, fallback_id, job)
        if not _profile_supports_capability(
            primary_config,
            resolved_policy.capability,
            allow_unverified=resolved_policy.allow_unverified_model,
        ):
            primary_config = None
        if not _profile_supports_capability(
            fallback_config,
            resolved_policy.capability,
            allow_unverified=resolved_policy.allow_unverified_model,
        ):
            fallback_config = None
    policy = GeneralConfig(**job_setting(db, "app:general", job))

    def on_retry(attempt: int, exc: Exception) -> None:
        error = provider_error_details(exc)
        reliability = error.get("reliability") if isinstance(error.get("reliability"), dict) else {}
        wait_seconds = float(reliability.get("wait_seconds") or policy.ai_retry_wait_seconds)
        record_event(
            db,
            "model.call.retrying",
            f"AI 接口异常，{wait_seconds:g} 秒后执行第 {attempt} 次重试",
            component="video-pipeline",
            level="WARNING",
            entity_type="job" if job else None,
            entity_id=job.id if job else None,
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
                "wait_seconds": wait_seconds,
                "reliability": reliability or None,
                "error_code": error.get("code"),
                "reason": error.get("message", "")[:240],
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
        duration_ms: int,
        attempt_metadata: dict[str, Any],
    ) -> None:
        usage = result.usage if result else {}
        error = provider_error_details(exc) if exc else {}
        status_code = error.get("status_code")
        cached = usage.get("cached_tokens")
        if cached is None:
            cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        attempt_id = str(attempt_metadata.pop("attempt_id", ""))
        response_meta = {
            "prompt_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count")),
            "completion_tokens": usage.get("completion_tokens", usage.get("eval_count")),
            "cached_tokens": cached,
            "usage": usage,
            "status_code": status_code,
            "provider_error": error or None,
            "finish_reason": (result.metadata if result else {}).get("finish_reason"),
            "response_id": (result.metadata if result else {}).get("response_id"),
            "content_length": (result.metadata if result else {}).get("content_length"),
        }
        if attempt_id and not finish_model_attempt(
            db,
            job,
            attempt_id,
            status="FAILED" if exc else "COMPLETED",
            duration_ms=duration_ms,
            request_meta_updates=attempt_metadata,
            response_meta=response_meta,
            error_code=(error.get("code") or getattr(exc, "code", None)) if exc else None,
            error_message=error.get("message") if exc else None,
        ):
            raise JobCancelled("本次模型调用所属的任务执行权已失效")

    def on_attempt_start(
        provider: str,
        model: str,
        route: str,
        attempt: int,
        input_chars: int,
        attempt_metadata: dict[str, Any],
    ) -> str:
        recovery = attempt_metadata.get("recovery") or (
            "fallback_model"
            if route == "fallback"
            else "split_same_model"
            if str(attempt_metadata.get("split_path") or "root") != "root"
            else None
        )
        return begin_model_attempt(
            db,
            settings,
            job,
            provider=provider,
            operation=role,
            request_meta={
                "stage": stage,
                "step": {
                    "transcript_correction": "CORRECT_TRANSCRIPT",
                    "video_note_summary": "GENERATE_AI_NOTE",
                    "note_reduce": "NOTE_REDUCE",
                    "grounded_map": "EXTRACT_TRAVEL_FACTS",
                    "travel_place_extraction": "EXTRACT_TRAVEL_FACTS",
                }.get(role, role),
                "model": model,
                "location": "LOCAL" if provider.lower() == "ollama" else "REMOTE",
                "route": route,
                "route_decision": route_decision.route if route_decision else None,
                "route_reason": route_decision.reason_code if route_decision else None,
                "attempt": attempt,
                "input_chars": input_chars,
                **attempt_metadata,
                "recovery": recovery,
            },
        )

    def with_policy(
        primary: LLMProvider,
        primary_model: str,
        fallback: LLMProvider | None = None,
        fallback_model: str | None = None,
        primary_interval: float | None = None,
        fallback_interval: float | None = None,
    ) -> FallbackLLMProvider:
        def reliability_for(config: dict[str, Any] | None) -> ModelReliabilityPolicy:
            resolved = resolve_reliability_policy(config)
            if resolved_policy and resolved_policy.retry_count is not None:
                resolved = replace(resolved, retry_count=resolved_policy.retry_count)
            if budget_pressure:
                resolved = replace(resolved, retry_count=0, json_retry_count=0)
            return resolved

        def options_for(config: dict[str, Any] | None) -> ProviderRequestOptions | None:
            profile_max_output_tokens = int((config or {}).get("max_output_tokens") or 0) or None
            max_output_tokens = (
                resolved_policy.max_output_tokens
                if resolved_policy and resolved_policy.max_output_tokens is not None
                else profile_max_output_tokens
            )
            if not resolved_policy and max_output_tokens is None:
                return None
            return ProviderRequestOptions(
                temperature=resolved_policy.temperature if resolved_policy else None,
                max_output_tokens=max_output_tokens,
                thinking=resolved_policy.thinking if resolved_policy else None,
                context_window=int((config or {}).get("context_window") or 0) or None,
            )

        request_options = options_for(primary_config)
        return FallbackLLMProvider(
            primary,
            primary_model,
            fallback,
            fallback_model,
            retry_count=policy.ai_retry_count,
            retry_wait_seconds=policy.ai_retry_wait_seconds,
            request_interval_seconds=(
                policy.ai_request_interval_seconds if primary_interval is None else primary_interval
            ),
            fallback_request_interval_seconds=fallback_interval,
            on_retry=on_retry,
            on_attempt=on_attempt,
            on_attempt_start=on_attempt_start,
            request_options=request_options,
            fallback_request_options=options_for(fallback_config),
            primary_reliability=reliability_for(primary_config),
            fallback_reliability=reliability_for(fallback_config),
            fallback_decider=(
                lambda exc: exc.code not in {"AI_PROVIDER_OUTPUT_TRUNCATED", "AI_PROVIDER_CONTEXT_TOO_LARGE"}
            )
            if role in {"transcript_correction", "grounded_map", "note_reduce"}
            else None,
            max_attempts=resolved_policy.max_attempts if resolved_policy else None,
        )

    if primary_config is None and fallback_config is not None:
        primary_id, primary_config = fallback_id, fallback_config
        fallback_id, fallback_config = "", None
    if primary_config is None:
        raise ProviderUnavailable("尚未在设置中选择主模型")
    if resolved_policy and resolved_policy.allow_unverified_model and job:
        record_event(
            db,
            "ai.route.capability_override",
            f"{stage} 使用用户明确允许的未验证模型",
            component="ai-gateway",
            level="WARNING",
            entity_type="job",
            entity_id=job.id,
            detail={"stage": stage, "primary_profile_id": primary_id, "fallback_profile_id": fallback_id},
        )
    if route_decision and job:
        record_event(
            db,
            "ai.route.decision",
            f"{stage} 自动路由：{route_decision.route}",
            component="ai-gateway",
            entity_type="job",
            entity_id=job.id,
            detail={
                "stage": stage,
                "route": route_decision.route,
                "reason_code": route_decision.reason_code,
                "budget_pressure": budget_pressure,
            },
            commit=False,
        )
    timeout_cap = (
        transcript_processing_config(db, job).timeout_seconds if role == "transcript_correction" else None
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
    submission_job_id: str | None = None,
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
    provenance = dict(metadata or {})
    if submission_job_id:
        provenance["submission_job_id"] = submission_job_id
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
        and (not submission_job_id or existing.metadata_json.get("submission_job_id") == submission_job_id)
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
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        raw_name = str(candidate.get("raw_name") or candidate.get("name") or "")
        key = (
            _normalized_insight_key(raw_name),
            _normalized_insight_key(candidate.get("city_hint")),
            str(candidate.get("place_type") or "UNKNOWN"),
            str(candidate.get("content_unit_id") or candidate.get("entity_id") or ""),
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
            "quotes": [mention.quote[:500]],
        }
        for mention in sorted(mentions, key=lambda item: item.id)
        if mention.extraction_status != "USER_REJECTED"
        and mention.poi_policy not in {"REFERENCE_ONLY", "SKIP"}
        and mention.quote
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
    kind = str(item.get("unit_type") or item.get("section_kind") or "").upper()
    if kind not in NOTE_SECTION_KINDS:
        kind = "PLACE" if related else "SUPPLEMENTAL"
    if kind in {"PLACE", "AREA", "ROUTE"} and not related:
        return None
    if not quotes:
        quotes = [
            str(next(segment.corrected_text or segment.text for segment in segments if segment.id in ids))
        ]
    names = list(dict.fromkeys(mention.name for mention in related))
    heading = str(item.get("heading") or "").strip()
    if not heading and kind == "PLACE":
        heading = names[0]
    elif not heading and kind in {"AREA", "AREA_GUIDE"}:
        city = next((mention.city_hint for mention in related if mention.city_hint), "周边")
        heading = f"{city}｜{'・'.join(names[:3])}"
    elif not heading and kind == "ROUTE":
        heading = " → ".join(names[:4])
    elif not heading:
        heading = "补充信息"
    return {
        **item,
        "section_kind": kind,
        "heading": heading[:500],
        "segment_ids": ids,
        "place_mention_ids": [mention.id for mention in related],
        "supporting_quotes": quotes[:8],
    }


def _high_information_bullets(values: list[object]) -> tuple[list[str], int]:
    """Drop duplicate boilerplate without asking another model to review the note."""
    result: list[str] = []
    seen: set[str] = set()
    removed = 0
    for value in values:
        text = str(value).strip()
        key = _normalized_text(text)
        generic = key and any(_normalized_text(item) == key for item in LOW_INFORMATION_BULLETS)
        if not text or key in seen or generic:
            removed += 1
            continue
        seen.add(key)
        result.append(text)
    return result, removed


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
                    mention.id
                    for mention in mentions
                    if mention.poi_policy not in {"REFERENCE_ONLY", "SKIP"}
                    and set(mention.segment_ids_json) & set(ids)
                ],
                "places": [],
            }
        )
    return result


def _compact_note_facts(facts: list[dict[str, object]]) -> list[dict[str, object]]:
    compact: list[dict[str, object]] = []
    seen: set[str] = set()
    for fact in facts:
        value = {
            "summary": str(fact.get("summary") or "")[:800],
            "key_points": list(dict.fromkeys(str(item)[:300] for item in fact.get("key_points", []) if item))[
                :8
            ],
            "warnings": list(dict.fromkeys(str(item)[:300] for item in fact.get("warnings", []) if item))[:4],
            "segment_ids": list(dict.fromkeys(str(item) for item in fact.get("segment_ids", []) if item)),
            "supporting_quotes": list(
                dict.fromkeys(str(item)[:500] for item in fact.get("supporting_quotes", []) if item)
            )[:2],
            "place_mention_ids": list(
                dict.fromkeys(str(item) for item in fact.get("place_mention_ids", []) if item)
            ),
        }
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if value["segment_ids"] and key not in seen:
            compact.append(value)
            seen.add(key)
    return compact


def _note_evidence_packs(
    facts: list[dict[str, object]], *, max_chars: int, max_facts: int
) -> list[list[dict[str, object]]]:
    packs: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    used = 0
    for fact in facts:
        size = len(json.dumps(fact, ensure_ascii=False))
        if current and (used + size > max_chars or len(current) >= max_facts):
            packs.append(current)
            current, used = [], 0
        current.append(fact)
        used += size
    if current:
        packs.append(current)
    return packs


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
    pending = [segment for segment in segments if segment.correction_status not in {"CORRECTED", "UNCHANGED"}]
    if not pending:
        return segments
    correction_policy = _resolved_stage_policy(db, "TRANSCRIPT_CORRECTION", job)
    neighbor_count = int(correction_policy.neighbor_segments or 2)
    transcript_metadata = getattr(transcript, "metadata_json", {}) or {}
    source_class = transcript_source_class(
        pending,
        source_kind=str(getattr(transcript, "source_kind", "ASR") or "ASR"),
        provider_id=str(transcript_metadata.get("provider_id") or ""),
    )
    candidates = correction_candidates(
        pending,
        source_kind=str(getattr(transcript, "source_kind", "ASR") or "ASR"),
        provider_id=str(transcript_metadata.get("provider_id") or ""),
        force_full=transcript_force_full_correction(db, job),
        neighbor_segments=neighbor_count,
    )
    positions = {segment.id: index for index, segment in enumerate(segments)}

    def context_value(segment: Segment) -> dict[str, str]:
        return {
            "id": segment.id,
            "text": str(segment.corrected_text or segment.text or segment.raw_text),
        }

    correction_items = {}
    for target in candidates:
        index = positions[target.id]
        correction_items[target.id] = {
            "target": {
                "id": target.id,
                "text": str(target.raw_text or target.text),
                "start_ms": target.locator_json.get("start_ms"),
                "end_ms": target.locator_json.get("end_ms"),
            },
            "context_before": [
                context_value(item) for item in segments[max(0, index - neighbor_count) : index]
            ],
            "context_after": [
                context_value(item) for item in segments[index + 1 : index + neighbor_count + 1]
            ],
        }
    target_chars = sum(len(item["target"]["text"]) for item in correction_items.values())
    context_chars = sum(
        len(context["text"])
        for item in correction_items.values()
        for context in [*item["context_before"], *item["context_after"]]
    )
    transcript_chars = sum(len(segment.raw_text or segment.text) for segment in segments)
    transcript.metadata_json = {
        **transcript_metadata,
        "correction_source_class": source_class,
        "correction_candidate_segments": len(candidates),
        "correction_coverage_ratio": len(candidates) / max(1, len(segments)),
        "correction_target_chars": target_chars,
        "correction_context_chars": context_chars,
        "correction_input_chars": target_chars + context_chars,
        "correction_input_ratio": (target_chars + context_chars) / max(1, transcript_chars),
        "transcript_chars": transcript_chars,
    }
    candidate_ids = {segment.id for segment in candidates}
    for segment in pending:
        if segment.id not in candidate_ids:
            segment.correction_status = "UNCHANGED"
            segment.correction_reason = "通过转写质量门禁，未发送模型校对"
    if not candidates:
        record_stage_decision(db, job, decide_stage("TRANSCRIPT_CORRECTION", has_relevant_segments=False))
        transcript.text = "\n".join(segment.corrected_text or segment.text for segment in segments)
        transcript.metadata_json = {
            **(getattr(transcript, "metadata_json", {}) or {}),
            "correction_status": "PASS_THROUGH",
            "correction_coverage": 1.0,
        }
        db.commit()
        return segments
    record_stage_decision(
        db,
        job,
        decide_stage(
            "TRANSCRIPT_CORRECTION",
            estimated_tokens=sum(len(segment.raw_text or segment.text) for segment in candidates) // 4,
        ),
    )
    provider, provider_name, model = provider_for_role(db, settings, "transcript_correction", job)
    if job and isinstance(provider, FallbackLLMProvider):
        provider.before_fallback = lambda: ensure_job_active(db, job)
    prompt = (Path(__file__).resolve().parents[1] / "prompts" / "transcript_correction.md").read_text(
        encoding="utf-8"
    )
    processing = transcript_processing_config(db, job)
    configured_batch_size = _correction_batch_size(provider_name, processing.batch_size)
    runtime_hints = (job.payload_json.get("ai_runtime_hints") or {}) if job else {}
    correction_hints = (
        runtime_hints.get("transcript_correction")
        if isinstance(runtime_hints.get("transcript_correction"), dict)
        else {}
    )
    saved = {**read_runtime_hint(db, "TRANSCRIPT_CORRECTION", model), **(correction_hints.get(model) or {})}
    saved_batch_size = int(saved.get("safe_max_segments") or saved.get("max_batch_size") or 0)
    saved_max_chars = int(saved.get("safe_max_chars") or 0)
    adaptive_batch_size = (
        min(configured_batch_size, saved_batch_size) if saved_batch_size > 0 else configured_batch_size
    )
    chunks = _transcript_chunks(
        candidates,
        min(processing.chunk_chars, saved_max_chars) if saved_max_chars else processing.chunk_chars,
        adaptive_batch_size,
    )

    corrected_count = 0

    def validated_changes(batch: list[Segment], response: LLMResult) -> list[dict[str, Any]]:
        payload = parse_model_json(response.content)
        values = payload.get("changes")
        if not isinstance(values, list):
            raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "校对输出缺少 changes 数组")
        ids = [str(item.get("segment_id") or "") for item in values if isinstance(item, dict)]
        allowed = {segment.id for segment in batch}
        if len(ids) != len(values) or any(not value for value in ids):
            raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "changes 必须使用 segment_id")
        if len(ids) != len(set(ids)) or set(ids) - allowed:
            raise AIProviderError(
                "AI_PROVIDER_SCHEMA_INVALID",
                "changes 包含重复、未知或只读 context Segment ID",
            )
        return values

    def apply_batch_result(batch: list[Segment], response: LLMResult, values: list[dict[str, Any]]) -> None:
        nonlocal corrected_count
        by_id = {str(item["segment_id"]): item for item in values}
        for segment in batch:
            item = by_id.get(segment.id)
            text = str(item.get("corrected_text") or "").strip() if item else ""
            segment.correction_provider = response.provider
            segment.correction_model = response.model
            if not text or text == str(segment.raw_text or segment.text).strip():
                segment.corrected_text = segment.raw_text or segment.text
                segment.correction_status = "UNCHANGED"
                segment.correction_reason = "模型确认无需修改，保留原始转写"
                continue
            segment.corrected_text = text
            segment.text = text
            segment.correction_status = "CORRECTED"
            segment.correction_confidence = normalized_confidence(item.get("confidence"))
            segment.correction_reason = str(item.get("reason") or "语音转写校对")[:500]
            corrected_count += 1
        if job:
            ensure_job_active(db, job)
            job.heartbeat_at = utc_now()
        db.commit()

    def request_batch(
        batch: list[Segment], *, batch_index: int, batch_total: int, split_path: str = "root"
    ) -> None:
        nonlocal adaptive_batch_size
        if job:
            ensure_job_active(db, job)
        payload = {
            "video_title": asset.title,
            "items": [correction_items[item.id] for item in batch],
        }
        try:
            messages = [
                {"role": "system", "content": prompt},
                *prompt_supplement_messages(db, "transcript_correction", job),
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
                attempt_metadata={
                    "chunk_index": batch_index,
                    "chunk_count": batch_total,
                    "split_path": split_path,
                    "segment_count": len(batch),
                },
                result_validator=lambda result: validated_changes(batch, result),
            )
        except AIProviderError as exc:
            if exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED":
                raise
            if len(batch) <= 1:
                if not isinstance(provider, FallbackLLMProvider):
                    raise
                response = provider.generate_fallback_json(messages)
                apply_batch_result(batch, response, validated_changes(batch, response))
                return
            midpoint = len(batch) // 2
            adaptive_batch_size = min(adaptive_batch_size, midpoint)
            safe_max_chars = max(
                sum(len(item.raw_text or item.text) for item in part)
                for part in (batch[:midpoint], batch[midpoint:])
            )
            persisted = tighten_runtime_hint(
                db,
                "TRANSCRIPT_CORRECTION",
                model,
                safe_max_chars=max(1, safe_max_chars),
                safe_max_segments=adaptive_batch_size,
            )
            if job:
                hints = dict(job.payload_json.get("ai_runtime_hints") or {})
                model_hints = dict(hints.get("transcript_correction") or {})
                model_hints[model] = {
                    "max_batch_size": adaptive_batch_size,
                    **persisted,
                    "reason": exc.code,
                }
                hints["transcript_correction"] = model_hints
                job.payload_json = {**job.payload_json, "ai_runtime_hints": hints}
                record_event(
                    db,
                    "transcript.correction.batch.split",
                    f"校对输出截断，已将 {len(batch)} 个 Segment 拆为更小批次",
                    component="video-pipeline",
                    level="WARNING",
                    entity_type="job",
                    entity_id=job.id,
                    detail={
                        "step": "CORRECT_TRANSCRIPT",
                        "error_code": exc.code,
                        "segments": len(batch),
                        "split_sizes": [midpoint, len(batch) - midpoint],
                        "split_path": split_path,
                        "adaptive_batch_size": adaptive_batch_size,
                    },
                )
            request_batch(
                batch[:midpoint],
                batch_index=batch_index,
                batch_total=batch_total,
                split_path=f"{split_path}.L",
            )
            request_batch(
                batch[midpoint:],
                batch_index=batch_index,
                batch_total=batch_total,
                split_path=f"{split_path}.R",
            )
            return
        except (httpx.HTTPError, TimeoutError, ConnectionError):
            if job:
                ensure_job_active(db, job)
            raise
        if job:
            ensure_job_active(db, job)
        apply_batch_result(batch, response, validated_changes(batch, response))

    pending_chunks = list(chunks)
    completed_batches = 0
    while pending_chunks:
        chunk = pending_chunks.pop(0)
        if len(chunk) > adaptive_batch_size:
            pending_chunks = [
                chunk[index : index + adaptive_batch_size]
                for index in range(0, len(chunk), adaptive_batch_size)
            ] + pending_chunks
            continue
        batch_index = completed_batches + 1
        batch_total = completed_batches + 1 + len(pending_chunks)
        started = perf_counter()
        if job:
            ensure_job_active(db, job)
            job.heartbeat_at = utc_now()
            record_event(
                db,
                "transcript.correction.batch.started",
                f"AI 校对 {batch_index}/{batch_total}",
                component="video-pipeline",
                entity_type="job",
                entity_id=job.id,
                detail={
                    "step": "CORRECT_TRANSCRIPT",
                    "batch_index": batch_index,
                    "batch_total": batch_total,
                    "segments": len(chunk),
                    "provider": provider_name,
                    "model": model,
                },
                commit=False,
            )
            db.commit()
        request_batch(chunk, batch_index=batch_index, batch_total=batch_total)
        completed_batches += 1
        if job:
            ensure_job_active(db, job)
            job.heartbeat_at = utc_now()
            record_event(
                db,
                "transcript.correction.batch.completed",
                f"AI 校对 {batch_index}/{batch_total} 已完成",
                component="video-pipeline",
                entity_type="job",
                entity_id=job.id,
                detail={
                    "step": "CORRECT_TRANSCRIPT",
                    "batch_index": batch_index,
                    "batch_total": batch_total,
                    "duration_ms": round((perf_counter() - started) * 1000),
                },
                commit=False,
            )
            db.commit()
    corrected_count = sum(segment.correction_status == "CORRECTED" for segment in segments)
    unchanged_count = sum(segment.correction_status == "UNCHANGED" for segment in segments)
    transcript.text = "\n".join(segment.corrected_text or segment.text for segment in segments)
    transcript.metadata_json = {
        **(getattr(transcript, "metadata_json", {}) or {}),
        "correction_status": "CORRECTED" if corrected_count + unchanged_count == len(segments) else "REVIEW",
        "correction_provider": provider_name,
        "correction_model": model,
        "correction_coverage": (corrected_count + unchanged_count) / max(1, len(segments)),
        "correction_prompt_supplement_hash": prompt_supplement_hash(db, "transcript_correction", job),
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


def note_for_job(db: Session, asset: VideoAsset, job: Job | None) -> AINote | None:
    if job is None:
        return db.scalar(
            select(AINote).where(AINote.video_asset_id == asset.id).order_by(AINote.created_at.desc())
        )
    note_id = str(job.payload_json.get("note_id") or "")
    if not note_id and job.result_content_id:
        content = db.get(ContentItem, job.result_content_id)
        note_id = str((content.structured_json or {}).get("note_id") or "") if content else ""
    if not note_id:
        step = db.scalar(
            select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == "GENERATE_AI_NOTE")
        )
        note_id = str((step.output_json or {}).get("note_id") or "") if step else ""
    if note_id:
        note = db.get(AINote, note_id)
        if note is not None and note.video_asset_id == asset.id:
            return note
    return db.scalar(select(AINote).where(AINote.submission_job_id == job.id))


def mentions_for_job(
    db: Session, asset: VideoAsset, job: Job | None, note: AINote | None = None
) -> list[PlaceMention]:
    if note and note.current_version_id:
        current = db.scalars(
            select(PlaceMention).where(PlaceMention.ai_note_version_id == note.current_version_id)
        ).all()
        if current:
            return current
    owner_id = note.submission_job_id if note and note.submission_job_id else job.id if job else None
    if owner_id:
        rows = db.scalars(
            select(PlaceMention).where(
                PlaceMention.video_asset_id == asset.id,
                PlaceMention.submission_job_id == owner_id,
            )
        ).all()
        if rows or (job and SNAPSHOT_KEY in job.payload_json and note is None):
            return rows
    if job and SNAPSHOT_KEY in job.payload_json:
        return []
    return db.scalars(
        select(PlaceMention).where(
            PlaceMention.video_asset_id == asset.id,
            PlaceMention.submission_job_id.is_(None),
            PlaceMention.ai_note_version_id.is_(None),
        )
    ).all()


def generate_note(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    transcript: Transcript,
    segments: list[Segment],
    job: Job | None = None,
    mentions: list[PlaceMention] | None = None,
    grounded_map: GroundedMapArtifact | None = None,
) -> AINoteVersion:
    mentions = mentions or []
    requested_profile = str((job.payload_json.get("note_render_profile") if job else "") or "CURRENT_DEFAULT")
    profile_id, render_profile = note_render_profile(requested_profile)
    provider, provider_name, model = provider_for_role(
        db, settings, "note_reduce" if grounded_map else "video_note_summary", job
    )
    chunk_chars = job_video_note_chunk_chars(job, settings.video_note_chunk_chars)
    chunks = _transcript_chunks(segments, chunk_chars)
    system = Path(__file__).resolve().parents[1] / "prompts" / "video_note.md"
    system_text = system.read_text(encoding="utf-8")
    supplement_messages = prompt_supplement_messages(db, "video_note_summary", job)
    place_evidence_json = json.dumps(_place_evidence_index(mentions), ensure_ascii=False)
    valid_ids = {segment.id for segment in segments}
    raw_sections: list[dict[str, object]] = []
    semantic_claims = list(grounded_map.claims_json or []) if grounded_map else []
    claim_facts = [
        {
            "summary": item.get("text", ""),
            "key_points": [item.get("text", "")],
            "supporting_quotes": [item.get("supporting_quote", "")],
            "segment_ids": item.get("segment_ids", []),
            "content_unit_id": item.get("content_unit_id", ""),
            "claim_ids": [item.get("claim_id", "")],
        }
        for item in semantic_claims
        if isinstance(item, dict)
    ]
    map_facts: list[dict[str, object]] = (
        _ground_map_facts(claim_facts or grounded_map.facts_json, segments, mentions) if grounded_map else []
    )
    overview_parts: list[str] = []
    warnings: list[str] = list(grounded_map.warnings_json) if grounded_map else []
    response = LLMResult("", provider_name, model, {})
    note_generation_mode = "MODEL"
    if grounded_map is not None:
        record_stage_decision(
            db,
            job,
            decide_stage(
                "NOTE_REDUCE",
                has_relevant_segments=bool(map_facts),
                estimated_tokens=len(json.dumps(map_facts, ensure_ascii=False)) // 4,
            ),
        )
    for chunk_index, chunk in enumerate((chunks or [segments]) if grounded_map is None else []):
        context = _transcript_context(chunk, chunk_chars)
        try:
            messages = [
                {"role": "system", "content": system_text},
                *supplement_messages,
                {
                    "role": "user",
                    "content": (
                        f"视频标题：{asset.title}\n已验证地点 Evidence Index："
                        f"{place_evidence_json}\n"
                        f"Render Profile（{profile_id}）：{render_profile['instruction']}\n"
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
            note_generation_mode = "HYBRID"
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
    if map_facts:
        reduce_policy = _resolved_stage_policy(db, "NOTE_REDUCE", job)
        saved_hint = read_runtime_hint(db, "NOTE_REDUCE", model)
        max_input_tokens = min(
            int(reduce_policy.max_input_tokens or 6000),
            int(saved_hint.get("safe_max_input_tokens") or 6000),
        )
        max_facts = int(saved_hint.get("safe_max_facts") or 40)
        compact_facts = _compact_note_facts(map_facts)
        fixed_chars = (
            len(system_text)
            + sum(len(message.get("content") or "") for message in supplement_messages)
            + len(place_evidence_json)
            + len(str(render_profile["instruction"]))
            + 500
        )
        packs = _note_evidence_packs(
            compact_facts,
            max_chars=max(1000, max_input_tokens * 4 - fixed_chars),
            max_facts=max_facts,
        )
        reduced_sections: list[dict[str, object]] = []
        failed_segment_ids: set[str] = set()
        stage_started = perf_counter()
        logical_attempts = 0
        completed_weight = 0
        total_weight = max(1, sum(len(json.dumps(item, ensure_ascii=False)) for item in compact_facts))

        def request_pack(
            pack: list[dict[str, object]], *, pack_index: int, pack_count: int, split_path: str = "root"
        ) -> None:
            nonlocal completed_weight, logical_attempts, response
            if (
                reduce_policy.wall_time_seconds
                and perf_counter() - stage_started >= reduce_policy.wall_time_seconds
            ):
                raise AIProviderError(
                    "AI_STAGE_WALL_TIME_EXCEEDED", "笔记归纳已达到阶段总时限", switch_model=False
                )
            if reduce_policy.max_attempts and logical_attempts >= reduce_policy.max_attempts:
                raise AIProviderError(
                    "AI_PROVIDER_ATTEMPT_BUDGET", "笔记归纳已达到尝试上限", switch_model=False
                )
            logical_attempts += 1
            messages = [
                {"role": "system", "content": system_text},
                *supplement_messages,
                {
                    "role": "user",
                    "content": (
                        f"Render Profile（{profile_id}）：{render_profile['instruction']}\n"
                        "已验证地点 Evidence Index："
                        f"{place_evidence_json}\n"
                        f"Evidence 分包：{pack_index}/{pack_count}（{split_path}）\n"
                        "以下是带逐字 Evidence 的 GroundedEvidencePack。仅据此生成全局笔记：\n"
                    )
                    + json.dumps(pack, ensure_ascii=False),
                },
            ]
            try:
                reduced = _cached_stage_json(
                    db,
                    job=job,
                    stage="NOTE_REDUCE",
                    capability="GLOBAL_SYNTHESIS",
                    provider=provider,
                    provider_name=provider_name,
                    model=model,
                    messages=messages,
                    attempt_metadata={
                        "chunk_index": pack_index,
                        "chunk_count": pack_count,
                        "split_path": split_path,
                        "segment_count": len(pack),
                    },
                )
            except AIProviderError as exc:
                if exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED":
                    raise
                if len(pack) <= 1:
                    if not isinstance(provider, FallbackLLMProvider):
                        raise
                    reduced = provider.generate_fallback_json(messages)
                else:
                    midpoint = len(pack) // 2
                    tighten_note_reduce_hint(
                        db,
                        model,
                        safe_max_input_tokens=max(
                            1, len(json.dumps(pack[:midpoint], ensure_ascii=False)) // 4
                        ),
                        safe_max_facts=midpoint,
                    )
                    request_pack(
                        pack[:midpoint],
                        pack_index=pack_index,
                        pack_count=pack_count,
                        split_path=f"{split_path}.L",
                    )
                    request_pack(
                        pack[midpoint:],
                        pack_index=pack_index,
                        pack_count=pack_count,
                        split_path=f"{split_path}.R",
                    )
                    return
            payload = parse_model_json(reduced.content)
            sections = payload.get("sections")
            accepted = (
                [
                    item
                    for item in sections
                    if isinstance(item, dict)
                    and any(value in valid_ids for value in item.get("segment_ids", []))
                ]
                if isinstance(sections, list)
                else []
            )
            reduced_sections.extend(accepted)
            if payload.get("overview"):
                overview_parts.append(str(payload["overview"]).strip())
            response = reduced
            completed_weight += sum(len(json.dumps(item, ensure_ascii=False)) for item in pack)
            if job:
                step = db.scalar(
                    select(JobStep).where(
                        JobStep.job_id == job.id,
                        JobStep.step_name == "GENERATE_AI_NOTE",
                    )
                )
                if step:
                    step.progress = min(99, round(completed_weight / total_weight * 100))
                    job.heartbeat_at = utc_now()
                    db.commit()

        for pack_index, pack in enumerate(packs, start=1):
            try:
                request_pack(pack, pack_index=pack_index, pack_count=len(packs))
            except Exception as exc:
                failed_segment_ids.update(
                    str(segment_id) for fact in pack for segment_id in fact.get("segment_ids", [])
                )
                warnings.append(f"第 {pack_index} 个笔记归纳分包不可用")
                record_event(
                    db,
                    "video.note.reduce_fallback",
                    "笔记归纳分包不可用，已保留确定性提纲",
                    component="video-pipeline",
                    level="WARNING",
                    entity_type="video_asset",
                    entity_id=asset.id,
                    detail={"reason": str(exc)[:240], "pack": pack_index, "pack_count": len(packs)},
                )
        if reduced_sections:
            failed_segments = [segment for segment in segments if segment.id in failed_segment_ids]
            raw_sections = [
                *reduced_sections,
                *_fallback_sections(_transcript_chunks(failed_segments, 12_000)),
            ]
            if failed_segment_ids:
                note_generation_mode = "HYBRID"
        else:
            note_generation_mode = "DETERMINISTIC_FALLBACK"
    note = note_for_job(db, asset, job)
    if note is None:
        note = AINote(video_asset_id=asset.id, submission_job_id=job.id if job else None)
        db.add(note)
        db.flush()
    if job:
        job.payload_json = {**job.payload_json, "note_id": note.id}
    old = db.scalar(select(func.max(AINoteVersion.version)).where(AINoteVersion.ai_note_id == note.id)) or 0
    overview = " ".join(dict.fromkeys(value for value in overview_parts if value))[
        : int(render_profile["overview_limit"])
    ]
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
        prompt_version=f"video-note-v2+{prompt_supplement_hash(db, 'video_note_summary', job)[:8]}",
        render_profile_id=profile_id,
        render_profile_version=str(render_profile["version"]),
        transcript_version=transcript.version,
    )
    db.add(version)
    db.flush()
    rendered = [f"# {asset.title}", "", overview]
    created_sections = 0
    low_information_removed = 0
    for ordinal, raw_item in enumerate(raw_sections):
        item = _ground_section(raw_item, segments, mentions)
        if item is None:
            continue
        segment_ids = list(item["segment_ids"])
        body = str(item.get("body_markdown") or item.get("body") or "")
        heading = str(item.get("heading") or f"要点 {ordinal + 1}")
        thesis = str(item.get("thesis") or item.get("summary") or "")[:500]
        summary = str(item.get("summary") or thesis)
        bullets, removed = _high_information_bullets(list(item.get("bullets", [])))
        low_information_removed += removed
        bullets = bullets[: int(render_profile["max_bullets"])]
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
    if low_information_removed:
        warnings.append(f"已移除 {low_information_removed} 条低信息或重复要点")
        record_event(
            db,
            "note.low_information_removed",
            "已移除低信息或重复笔记要点",
            component="video-pipeline",
            entity_type="video_asset",
            entity_id=asset.id,
            detail={"count": low_information_removed},
            commit=False,
        )
    if note.current_version_id:
        active_ids = {mention.id for mention in mentions}
        for previous in db.scalars(
            select(PlaceMention).where(PlaceMention.ai_note_version_id == note.current_version_id)
        ):
            if previous.id not in active_ids and previous.extraction_status == "EXTRACTED":
                previous.extraction_status = "SUPERSEDED"
    note.current_version_id = version.id
    note.status = "COMPLETED"
    for mention in mentions:
        mention.ai_note_version_id = version.id
    if not response.content:
        note_generation_mode = "DETERMINISTIC_FALLBACK"
    if job:
        job.payload_json = {
            **job.payload_json,
            "note_generation_mode": note_generation_mode,
        }
    sync_video_note_search_index(db, note, version, asset)
    db.commit()
    return version


def extract_place_mentions(
    db: Session,
    settings: Settings,
    asset: VideoAsset,
    note: AINoteVersion | None,
    segments: list[Segment],
    job: Job | None = None,
    candidates: list[dict[str, Any]] | None = None,
) -> list[PlaceMention]:
    if candidates is None:  # Explicit legacy / force re-extract path only.
        policy = _resolved_stage_policy(db, "EXTRACT_TRAVEL_FACTS", job)
        chunk_chars = int(policy.chunk_size or PLACE_EXTRACTION_CHUNK_CHARS)
        neighbor_segments = int(policy.neighbor_segments or PLACE_EXTRACTION_NEIGHBOR_SEGMENTS)
        provider, provider_name, model = provider_for_role(db, settings, "travel_place_extraction", job)
        prompt = (Path(__file__).resolve().parents[1] / "prompts" / "travel_place_extraction.md").read_text(
            encoding="utf-8"
        )
        candidates = []
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
                    *prompt_supplement_messages(db, "travel_place_extraction", job),
                    {
                        "role": "user",
                        "content": (
                            f"视频标题：{asset.title}\n分块：{chunk_index + 1}\n"
                            + _transcript_context(chunk, chunk_chars)
                        ),
                    },
                ],
                attempt_metadata={"chunk_index": chunk_index + 1, "chunk_count": len(chunks)},
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
                PlaceMention.submission_job_id == job.id if job else PlaceMention.submission_job_id.is_(None),
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
        poi_policy = str(item.get("poi_policy") or "LEGACY").upper()
        if poi_policy not in {"RESOLVE", "AREA_RESOLVE", "REFERENCE_ONLY", "SKIP"}:
            poi_policy = "LEGACY"
        subject_role = str(item.get("subject_role") or "LEGACY").upper()
        if subject_role not in {"PRIMARY", "SECONDARY", "REFERENCE", "CONTEXT"}:
            subject_role = "LEGACY"
        visit_intent = str(item.get("visit_intent") or "NOT_APPLICABLE").upper()
        if visit_intent not in {"RECOMMENDED", "OPTIONAL", "NEUTRAL", "NOT_RECOMMENDED", "NOT_APPLICABLE"}:
            visit_intent = "NOT_APPLICABLE"
        insights = _insights_from_candidate(item, ids, segment_texts)
        visit_windows = _visit_windows_from_candidate(item, ids, segment_texts)
        mention = PlaceMention(
            video_asset_id=asset.id,
            submission_job_id=job.id if job else None,
            ai_note_version_id=note.id if note else None,
            name=str(item["name"])[:300],
            raw_name=str(item.get("raw_name") or item["name"])[:300],
            suggested_name=str(item.get("suggested_name") or item["name"])[:300],
            content_unit_id=str(item.get("content_unit_id") or "")[:96],
            subject_role=subject_role,
            visit_intent=visit_intent,
            poi_policy=poi_policy,
            semantic_confidence=normalized_confidence(item.get("confidence")),
            city_hint=str(item.get("city_hint") or "")[:64],
            province_hint=str(item.get("province_hint") or "")[:64],
            place_type=str(item.get("place_type") or "UNKNOWN")[:64],
            reason=str(item.get("reason") or ""),
            quote=str(item.get("quote") or ""),
            segment_ids_json=ids,
            confidence=normalized_confidence(item.get("confidence")),
            extraction_status="EXTRACTED",
            resolution_status=(
                "AREA_RESOLVED"
                if poi_policy == "AREA_RESOLVE"
                else "SKIPPED"
                if poi_policy in {"REFERENCE_ONLY", "SKIP"}
                else ResolutionStatus.UNRESOLVED.value
            ),
            metadata_json={
                "insights": insights,
                "visit_windows": visit_windows,
                "semantic": {
                    "entity_id": str(item.get("entity_id") or "")[:96],
                    "content_unit_id": str(item.get("content_unit_id") or "")[:96],
                    "subject_role": subject_role,
                    "visit_intent": visit_intent,
                    "poi_policy": poi_policy,
                },
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
    db: Session,
    settings: Settings,
    mentions: list[PlaceMention],
    api_key: str | None = None,
    metrics: dict[str, int] | None = None,
) -> tuple[int, int]:
    actionable = [item for item in mentions if (item.poi_policy or "LEGACY") in {"RESOLVE", "LEGACY"}]
    skipped = [item for item in mentions if item not in actionable]
    for mention in skipped:
        if mention.poi_policy in {"REFERENCE_ONLY", "SKIP"}:
            mention.resolution_status = "SKIPPED"
        elif mention.poi_policy == "AREA_RESOLVE":
            mention.resolution_status = "AREA_RESOLVED"
    if metrics is not None:
        metrics["poi_skipped_reference"] = sum(
            item.poi_policy in {"REFERENCE_ONLY", "SKIP"} for item in skipped
        )
        metrics["poi_resolve_requested"] = len(actionable)
    if not mentions:
        if metrics is not None:
            metrics["amap_request_count"] = 0
            metrics["amap_cache_hit_count"] = 0
        return 0, 0
    effective_key = api_key or settings.amap_api_key
    if not effective_key:
        if metrics is not None:
            metrics["amap_request_count"] = 0
            metrics["amap_cache_hit_count"] = 0
        db.commit()
        return 0, len(actionable)
    provider = AMapPOIProvider(
        effective_key,
        cache_ttl_seconds=settings.amap_cache_ttl_seconds,
    )
    asset_ids = {mention.video_asset_id for mention in mentions}
    submission_ids = {mention.submission_job_id for mention in mentions if mention.submission_job_id}
    session_mentions = db.scalars(
        select(PlaceMention).where(
            PlaceMention.video_asset_id.in_(asset_ids),
            PlaceMention.submission_job_id.in_(submission_ids)
            if submission_ids
            else PlaceMention.submission_job_id.is_(None),
            PlaceMention.extraction_status == "EXTRACTED",
        )
    ).all()
    _assign_geo_sessions(db, session_mentions)
    confirmed = 0
    candidate_results: dict[str, list[POICandidate] | Exception] = {}
    searchable = [
        mention
        for mention in actionable
        if not (
            mention.resolution_status == ResolutionStatus.CONFIRMED.value
            and (mention.metadata_json or {}).get("confirmation_origin") == "MANUAL_CONFIRMED"
        )
    ]
    with ThreadPoolExecutor(max_workers=max(1, settings.amap_max_concurrency)) as executor:
        futures = {
            executor.submit(_rank_poi_candidates, provider, mention, mentions): mention.id
            for mention in searchable
        }
        for future in as_completed(futures):
            mention_id = futures[future]
            try:
                candidate_results[mention_id] = future.result()
            except Exception as exc:
                candidate_results[mention_id] = exc
    for mention in actionable:
        if (
            mention.resolution_status == ResolutionStatus.CONFIRMED.value
            and (mention.metadata_json or {}).get("confirmation_origin") == "MANUAL_CONFIRMED"
        ):
            confirmed += 1
            continue
        candidates = candidate_results.get(mention.id, [])
        if isinstance(candidates, Exception):
            exc = candidates
            mention.metadata_json = {**mention.metadata_json, "poi_error": str(exc)[:240]}
            continue
        if not candidates:
            mention.resolution_status = ResolutionStatus.UNRESOLVED.value
            continue
        selected = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        shadow = _resolver_v2_shadow(mention, candidates)
        review_reasons = _poi_review_reasons(selected, runner_up)
        resolver_v3 = _resolver_v3_decision(mention, candidates, review_reasons)
        contextual_verification: dict[str, Any] | None = None
        if shadow["decision"] == "AUTO_CONTEXTUAL":
            try:
                contextual = provider.detail(selected.provider_id)
            except Exception:
                contextual = None
            if contextual is not None:
                contextual_verification = _candidate_metadata(contextual)
        if resolver_v3["decision"] == "REVIEW":
            reason_codes = list(selected.match_explanation.get("review_reason_codes", []))
            if shadow["decision"] == "AUTO_CONTEXTUAL":
                reason_codes.append(
                    "CONTEXTUAL_VERIFICATION_COMPLETE"
                    if contextual_verification
                    else "CONTEXTUAL_VERIFICATION_FAILED"
                )
            mention.resolution_status = ResolutionStatus.REVIEW.value
            mention.metadata_json = {
                **mention.metadata_json,
                "poi_candidates": [_candidate_metadata(item) for item in candidates[:5]],
                "reason": "；".join(review_reasons or ["候选未满足 AUTO_STRONG 门禁"]),
                "reason_codes": list(dict.fromkeys(reason_codes or ["AUTO_STRONG_GATE_FAILED"])),
                "poi_decision": resolver_v3["decision"],
                "contextual_verification": contextual_verification,
                "resolver_v2_shadow": shadow,
                "resolver_v3": resolver_v3,
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
                "reason_codes": ["DETAIL_VERIFICATION_FAILED"],
                "poi_decision": "REVIEW",
                "resolver_v2_shadow": shadow,
                "resolver_v3": resolver_v3,
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
            "poi_decision": resolver_v3["decision"],
            "confirmation_origin": "AUTO_STRONG",
            "confirmation_at": utc_now().isoformat(),
            "resolver_version": "poi-v3",
            "resolver_v2_shadow": shadow,
            "resolver_v3": resolver_v3,
        }
        materialize_place_insights(db, mention)
        confirmed += 1
    db.commit()
    if metrics is not None:
        metrics["amap_request_count"] = int(getattr(provider, "request_count", 0))
        metrics["amap_cache_hit_count"] = int(getattr(provider, "cache_hit_count", 0))
    if metrics is not None:
        metrics["poi_auto_exact"] = sum(
            item.metadata_json.get("poi_decision") == "AUTO_EXACT" for item in actionable
        )
        metrics["poi_auto_normalized"] = sum(
            item.metadata_json.get("poi_decision") == "AUTO_NORMALIZED" for item in actionable
        )
        metrics["poi_review"] = sum(
            item.resolution_status == ResolutionStatus.REVIEW.value for item in actionable
        )
        metrics["poi_unresolved"] = sum(
            item.resolution_status == ResolutionStatus.UNRESOLVED.value for item in actionable
        )
    return confirmed, len(actionable) - confirmed


def materialize_destinations(db: Session, asset: VideoAsset, mentions: list[PlaceMention]) -> tuple[int, int]:
    """Persist AREA semantics separately and link only confirmed actionable Places."""
    by_unit: dict[str, Destination] = {}
    created = linked = 0
    for mention in mentions:
        if mention.poi_policy != "AREA_RESOLVE":
            continue
        canonical = (mention.city_hint or mention.name or mention.raw_name).strip()
        if not canonical:
            continue
        scope_type = (
            "DISTRICT"
            if (mention.metadata_json or {}).get("resolver_context", {}).get("district_hint")
            else "CITY"
        )
        destination = db.scalar(
            select(Destination).where(
                Destination.scope_type == scope_type,
                Destination.canonical_name == canonical,
            )
        )
        if destination is None:
            destination = Destination(
                name=mention.name,
                canonical_name=canonical,
                scope_type=scope_type,
                province=mention.province_hint,
                city=mention.city_hint or canonical,
                district=str(
                    (mention.metadata_json or {}).get("resolver_context", {}).get("district_hint") or ""
                ),
                metadata_json={"origin": "SEMANTIC_MAP", "representative_anchor": None},
            )
            db.add(destination)
            db.flush()
            created += 1
        mention.destination_id = destination.id
        mention.resolution_status = "AREA_RESOLVED"
        by_unit[mention.content_unit_id] = destination
    for mention in mentions:
        if mention.resolution_status != ResolutionStatus.CONFIRMED.value or not mention.place_id:
            continue
        destination = by_unit.get(mention.content_unit_id)
        if destination is None:
            continue
        exists = db.scalar(
            select(DestinationPlaceLink).where(
                DestinationPlaceLink.destination_id == destination.id,
                DestinationPlaceLink.place_id == mention.place_id,
                DestinationPlaceLink.video_asset_id == asset.id,
                DestinationPlaceLink.content_unit_id == mention.content_unit_id,
            )
        )
        if exists is not None:
            continue
        db.add(
            DestinationPlaceLink(
                destination_id=destination.id,
                place_id=mention.place_id,
                source_id=asset.source_id,
                video_asset_id=asset.id,
                place_mention_id=mention.id,
                content_unit_id=mention.content_unit_id,
                relation_type=("RECOMMENDED_IN" if mention.visit_intent == "RECOMMENDED" else "NEARBY"),
                segment_ids_json=mention.segment_ids_json,
                confidence=mention.semantic_confidence,
                metadata_json={"subject_role": mention.subject_role, "visit_intent": mention.visit_intent},
            )
        )
        linked += 1
    db.commit()
    return created, linked


def _assign_geo_sessions(db: Session, mentions: list[PlaceMention]) -> None:
    """Attach deterministic, local region context without altering extracted facts."""
    if not mentions:
        return
    segment_ids = {segment_id for mention in mentions for segment_id in mention.segment_ids_json}
    ordinals = {
        segment.id: segment.ordinal
        for segment in db.scalars(select(Segment).where(Segment.id.in_(segment_ids))).all()
    }
    place_ids = {mention.place_id for mention in mentions if mention.place_id}
    places = {place.id: place for place in db.scalars(select(Place).where(Place.id.in_(place_ids))).all()}
    by_asset: dict[str, list[PlaceMention]] = {}
    for mention in mentions:
        by_asset.setdefault(mention.video_asset_id, []).append(mention)
    for asset_id, rows in by_asset.items():
        rows.sort(
            key=lambda item: (
                min((ordinals.get(value, 10**9) for value in item.segment_ids_json), default=10**9),
                item.id,
            )
        )
        session_number = 0
        active_city = active_province = ""
        sessions: dict[str, list[PlaceMention]] = {}
        for mention in rows:
            place = places.get(mention.place_id or "")
            explicit_city = mention.city_hint or (place.city if place else "")
            explicit_province = mention.province_hint or (place.province if place else "")
            if (explicit_city or explicit_province) and (explicit_city, explicit_province) != (
                active_city,
                active_province,
            ):
                session_number += 1
                active_city, active_province = explicit_city, explicit_province
            session_id = f"geo:{asset_id}:{session_number or 1}"
            context = (mention.metadata_json or {}).get("resolver_context", {})
            context = context if isinstance(context, dict) else {}
            mention.metadata_json = {
                **(mention.metadata_json or {}),
                "resolver_context": {
                    **context,
                    "geo_session_id": session_id,
                    "geo_session_city": active_city,
                    "geo_session_province": active_province,
                },
            }
            sessions.setdefault(session_id, []).append(mention)
        for rows_in_session in sessions.values():
            anchor_rows = [
                item
                for item in rows_in_session
                if item.resolution_status == ResolutionStatus.CONFIRMED.value
                and (item.metadata_json or {}).get("confirmation_origin")
                in {"AUTO_STRONG", "MANUAL_CONFIRMED"}
                and places.get(item.place_id or "")
            ]
            anchors = [item.id for item in anchor_rows]
            anchor_locations = [
                {
                    "mention_id": item.id,
                    "longitude": places[item.place_id].longitude,
                    "latitude": places[item.place_id].latitude,
                    "city": places[item.place_id].city,
                }
                for item in anchor_rows
            ]
            for mention in rows_in_session:
                context = mention.metadata_json["resolver_context"]
                mention.metadata_json = {
                    **mention.metadata_json,
                    "resolver_context": {
                        **context,
                        "geo_anchor_mention_ids": anchors,
                        "geo_anchors": anchor_locations,
                        "nearby_anchor": anchor_locations[0] if anchor_locations else None,
                    },
                }


def _rank_poi_candidates(
    provider: AMapPOIProvider, mention: PlaceMention, mentions: list[PlaceMention] | None = None
) -> list[POICandidate]:
    queries = _poi_queries(mention)
    deduped: dict[str, POICandidate] = {}
    query_provenance: dict[str, list[dict[str, str]]] = {}
    for query, city in queries:
        for candidate in provider.search(query, city, city_limit=bool(city)):
            if candidate.provider_id:
                deduped.setdefault(candidate.provider_id, candidate)
                provenance = {"query": query, "city": city or "全国"}
                if provenance not in query_provenance.setdefault(candidate.provider_id, []):
                    query_provenance[candidate.provider_id].append(provenance)
    context = (mention.metadata_json or {}).get("resolver_context", {})
    context = context if isinstance(context, dict) else {}
    nearby = context.get("nearby_anchor")
    relation = str(context.get("nearby_relation") or "")
    if isinstance(nearby, dict) and relation and hasattr(provider, "around"):
        longitude, latitude = nearby.get("longitude"), nearby.get("latitude")
        if isinstance(longitude, (int, float)) and isinstance(latitude, (int, float)):
            radius = _nearby_radius(relation)
            if radius:
                for candidate in provider.around(longitude, latitude, mention.suggested_name, radius=radius):
                    if candidate.provider_id:
                        deduped.setdefault(candidate.provider_id, candidate)
                        provenance = {"query": mention.suggested_name, "city": f"nearby:{relation}"}
                        if provenance not in query_provenance.setdefault(candidate.provider_id, []):
                            query_provenance[candidate.provider_id].append(provenance)
    for candidate in deduped.values():
        candidate.score, candidate.match_reasons, candidate.match_explanation = _poi_score(
            mention, candidate, mentions or []
        )
        hits = query_provenance.get(candidate.provider_id, [])
        candidate.match_explanation.update(
            {
                "query_provenance": hits,
                "query_consensus_count": len(hits),
                "query_diversity": len({item["city"] for item in hits}),
                "negative_evidence": _negative_evidence(mention, candidate, len(queries), len(hits)),
            }
        )
    return sorted(deduped.values(), key=lambda item: (-item.score, item.name))


def _nearby_radius(relation: str) -> int | None:
    return {
        "VERY_NEAR": 250,
        "对面": 250,
        "隔壁": 250,
        "NEAR": 700,
        "附近": 700,
        "WALKABLE": 1500,
        "步行可达": 1500,
        "REGIONAL": 3000,
        "同片区": 3000,
    }.get(relation)


def _negative_evidence(
    mention: PlaceMention, candidate: POICandidate, query_count: int, consensus_count: int
) -> list[str]:
    explanation = candidate.match_explanation
    context = (mention.metadata_json or {}).get("resolver_context", {})
    context = context if isinstance(context, dict) else {}
    effective_city = mention.city_hint or str(context.get("geo_session_city") or "")
    negative: list[str] = []
    if effective_city and candidate.city and not explanation.get("city_match"):
        negative.append("CROSS_CITY_CONFLICT")
    if explanation.get("category_compatibility") == "INCOMPATIBLE":
        negative.append("CATEGORY_CONFLICT")
    if query_count > 1 and consensus_count <= 1:
        negative.append("QUERY_DISAGREEMENT")
    if any(marker in candidate.name for marker in ("店", "分店", "门店")) and "店" not in mention.name:
        negative.append("CHAIN_BRANCH_AMBIGUITY")
    return negative


def _poi_queries(mention: PlaceMention) -> list[tuple[str, str]]:
    context = (mention.metadata_json or {}).get("resolver_context", {})
    aliases = context.get("aliases", []) if isinstance(context, dict) else []
    names = [mention.suggested_name, mention.name, mention.raw_name, *aliases]
    session_city = str(context.get("geo_session_city") or "") if isinstance(context, dict) else ""
    session_province = str(context.get("geo_session_province") or "") if isinstance(context, dict) else ""
    city = mention.city_hint or session_city
    province = mention.province_hint or session_province
    locations = [city, province, "", *([city] * len(aliases))]
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
    context = (mention.metadata_json or {}).get("resolver_context", {})
    context = context if isinstance(context, dict) else {}
    aliases = [str(value) for value in context.get("aliases", []) if value]
    names = [value for value in (mention.suggested_name, mention.name, mention.raw_name, *aliases) if value]
    candidate_key = _normalized_insight_key(candidate.name)
    mention_tokens = _normalized_poi_tokens(" ".join(str(value) for value in names))
    candidate_tokens = _normalized_poi_tokens(candidate.name)
    token_overlap = len(mention_tokens & candidate_tokens) / max(1, len(mention_tokens | candidate_tokens))
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
    session_city = str(context.get("geo_session_city") or "")
    session_province = str(context.get("geo_session_province") or "")
    unit_city = str(context.get("unit_city") or "")
    effective_city = mention.city_hint or unit_city or session_city
    effective_province = mention.province_hint or session_province
    city_match = bool(effective_city and effective_city in location_text)
    province_match = bool(effective_province and effective_province in location_text)
    district_match = bool(district_hint and district_hint in location_text)
    if effective_city and effective_city in (candidate.city + candidate.address):
        score += 20
        reasons.append("城市匹配")
    if province_match:
        score += 5
        reasons.append("省份匹配")
    if district_match:
        score += 10
        reasons.append("区县匹配")
    category_compatibility = _category_compatibility(mention.place_type, candidate.typecode)
    category_match = category_compatibility == "STRONG"
    if category_compatibility == "STRONG":
        score += 15
        reasons.append("地点类型匹配")
    elif category_compatibility == "WEAK":
        score += 5
        reasons.append("地点类型弱兼容")
    elif category_compatibility == "INCOMPATIBLE":
        score -= 15
        reasons.append("地点类型冲突")
    nearby_matches = [value for value in nearby if value in (candidate.name + candidate.address)]
    if nearby_matches:
        score += 10
        reasons.append("附近地标匹配")
    cross_cities = {
        item.city_hint
        or str((item.metadata_json or {}).get("resolver_context", {}).get("geo_session_city") or "")
        for item in mentions or []
        if item.id != mention.id
    }
    cross_provinces = {
        item.province_hint
        or str((item.metadata_json or {}).get("resolver_context", {}).get("geo_session_province") or "")
        for item in mentions or []
        if item.id != mention.id
    }
    cross_location_matches = sorted(
        value for value in cross_cities | cross_provinces if value and value in location_text
    )
    if cross_location_matches:
        score += 20 if not (city_match or province_match or district_match) else 5
        reasons.append("视频内地域上下文匹配")
    explanation = {
        "name_match": round(similarity, 3),
        "normalized_token_overlap": round(token_overlap, 3),
        "city_match": city_match,
        "unit_city_match": bool(unit_city and unit_city in location_text),
        "province_match": province_match,
        "district_match": district_match,
        "category_match": category_match,
        "category_compatibility": category_compatibility,
        "nearby_context": nearby_matches,
        "cross_place_context": cross_location_matches,
        "coordinate_valid": 73.5 <= candidate.longitude <= 135.1 and 18 <= candidate.latitude <= 53.6,
        "reference_only": mention.poi_policy in {"REFERENCE_ONLY", "SKIP"},
        "distance_to_unit_cluster_m": None,
    }
    return min(score, 100), reasons, explanation


def _normalized_poi_tokens(value: str) -> set[str]:
    """Small deterministic normalizer for short Chinese POI names and official suffixes."""
    normalized = _normalized_insight_key(value)
    for suffix in ("广播电视塔", "森林公园", "湿地景区", "博物馆", "风景区", "景区", "公园", "旅游区"):
        normalized = normalized.replace(suffix, "")
    return {normalized} if normalized else set()


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
    category = explanation.get("category_compatibility")
    if category == "UNMAPPED":
        reasons.append("地点类型尚无可靠分类映射")
    elif category == "WEAK":
        reasons.append("地点类型只有弱兼容候选")
    elif category == "INCOMPATIBLE" or not explanation.get("category_match"):
        reasons.append("地点类型与候选冲突")
    if runner_up and selected.score - runner_up.score < 15:
        reasons.append("第一、二候选差距过小")
    if not explanation.get("coordinate_valid"):
        reasons.append("候选坐标异常")
    code_by_reason = {
        "候选综合分不足": "SCORE_BELOW_THRESHOLD",
        "名称匹配不够强": "NAME_MATCH_WEAK",
        "地域上下文不足": "GEO_CONTEXT_MISSING",
        "地点类型尚无可靠分类映射": "CATEGORY_UNMAPPED",
        "地点类型只有弱兼容候选": "CATEGORY_WEAK_ONLY",
        "地点类型与候选冲突": "CATEGORY_CONFLICT",
        "第一、二候选差距过小": "CANDIDATE_GAP_SMALL",
        "候选坐标异常": "COORDINATE_INVALID",
    }
    explanation["review_reason_codes"] = [code_by_reason[item] for item in reasons]
    return reasons


def _resolver_v2_shadow(mention: PlaceMention, candidates: list[POICandidate]) -> dict[str, Any]:
    """Calculate a transparent V2 outcome without changing the authoritative V1 result."""
    if not candidates:
        return {"version": "poi-v2-shadow", "decision": "UNRESOLVED", "features": {}}
    selected = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    explanation = selected.match_explanation
    candidate_gap = selected.score - runner_up.score if runner_up else 100
    name = _normalized_insight_key(selected.name)
    branch_markers = ("店", "分店", "门店", "酒店", "宾馆", "咖啡")
    feature = ResolutionFeatureVector(
        name_match=float(explanation.get("name_match") or 0),
        city_match=bool(explanation.get("city_match")),
        province_match=bool(explanation.get("province_match")),
        district_match=bool(explanation.get("district_match")),
        category_match=str(explanation.get("category_compatibility") or "UNMAPPED"),
        nearby_landmark_match=bool(explanation.get("nearby_context")),
        query_consensus_count=int(explanation.get("query_consensus_count") or 1),
        candidate_gap=candidate_gap,
        coordinate_valid=bool(explanation.get("coordinate_valid")),
        cross_city_conflict=bool(mention.city_hint and not explanation.get("city_match") and selected.city),
        chain_risk=any(marker in name for marker in branch_markers),
        distance_to_cluster_m=None,
        prior_confirmation_match=bool(explanation.get("prior_confirmation_match")),
    )
    negative_evidence = set(explanation.get("negative_evidence") or [])
    hard_risk = (
        not feature.coordinate_valid
        or feature.category_match in {"INCOMPATIBLE", "UNMAPPED"}
        or feature.cross_city_conflict
        or feature.chain_risk
        or feature.candidate_gap < 15
        or "CROSS_CITY_CONFLICT" in negative_evidence
        or "CHAIN_BRANCH_AMBIGUITY" in negative_evidence
    )
    if feature.name_match >= 0.9 and not hard_risk:
        decision = "AUTO_STRONG"
    elif feature.name_match >= 0.9 and feature.nearby_landmark_match and not feature.cross_city_conflict:
        decision = "AUTO_CONTEXTUAL"
    else:
        decision = "REVIEW"
    return {
        "version": "poi-v2-shadow",
        "decision": decision,
        "selected_provider_id": selected.provider_id,
        "features": asdict(feature),
    }


def _auto_strong_allowed(selected: POICandidate, shadow: dict[str, Any], review_reasons: list[str]) -> bool:
    """Only strict, evidence-clean candidates can create a confirmed Place."""
    negative = set(selected.match_explanation.get("negative_evidence") or [])
    return not review_reasons and shadow.get("decision") == "AUTO_STRONG" and not negative


def _resolver_v3_decision(
    mention: PlaceMention, candidates: list[POICandidate], review_reasons: list[str]
) -> dict[str, Any]:
    """Keep the proven V2 precision gate, then name the exact/normalized V3 outcome."""
    policy = mention.poi_policy or "LEGACY"
    if not candidates or policy not in {"RESOLVE", "LEGACY"}:
        return {"version": "poi-v3", "decision": "REVIEW", "features": {"policy": policy}}
    selected = candidates[0]
    shadow = _resolver_v2_shadow(mention, candidates)
    if not _auto_strong_allowed(selected, shadow, review_reasons):
        return {"version": "poi-v3", "decision": "REVIEW", "features": shadow["features"]}
    candidate_name = _normalized_insight_key(selected.name)
    mention_names = {
        _normalized_insight_key(value)
        for value in (mention.suggested_name, mention.name, mention.raw_name)
        if value
    }
    decision = "AUTO_EXACT" if candidate_name in mention_names else "AUTO_NORMALIZED"
    return {
        "version": "poi-v3",
        "decision": decision,
        "selected_provider_id": selected.provider_id,
        "features": {
            **shadow["features"],
            "normalized_token_overlap": selected.match_explanation.get("normalized_token_overlap", 0),
            "unit_city_match": selected.match_explanation.get("unit_city_match", False),
        },
    }


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
