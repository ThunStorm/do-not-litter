import re
from dataclasses import replace
from time import sleep
from typing import Any
from urllib.parse import urlsplit

from zhijian.ai.capabilities import AICapability
from zhijian.ai.model_test_queue import (
    model_test_groups,
    pace_model_test,
    queued_model_test,
    uses_local_model_hardware,
)
from zhijian.ai.reliability import (
    ReliabilityGuards,
    classify_provider_error,
    provider_rate_limit_identity,
    resolve_reliability_policy,
    retry_after_seconds,
)
from zhijian.ai.schemas import ModelProfile
from zhijian.ai.structured_output import parse_json_object
from zhijian.core.time import utc_now
from zhijian.providers.llm import LLMProvider, ProviderRequestOptions

BUSINESS_PROBE_VERSION = "business-mini-v1"
NOTE_PROBE_VERSION = "note-synthesis-v2"
LOCAL_TEST_INTERVAL_SECONDS = 5.0
NOTE_PROBE_SOURCES = {"s1": "西安10月门票20元，不推荐周末。", "s2": "洛阳推荐米粉。"}


def _probe_version(capability: str) -> str:
    return NOTE_PROBE_VERSION if capability == "GLOBAL_SYNTHESIS" else BUSINESS_PROBE_VERSION


def business_probe_status(value: dict, capability: str) -> str:
    from datetime import datetime, timedelta

    from zhijian.core.time import as_utc

    records = value.get("business_assessments") or []
    record = next((row for row in records if row.get("stage") == capability), None)
    if (
        record
        and record.get("model") == value.get("model")
        and record.get("prompt_version") == _probe_version(capability)
    ):
        try:
            if (
                timedelta(0)
                <= utc_now() - as_utc(datetime.fromisoformat(record["tested_at"]))
                <= timedelta(days=30)
            ):
                return str(record.get("probe_status") or "NOT_TESTED")
        except (ValueError, KeyError, TypeError):
            pass
    # v1 note layout/wording failures are not evidence against the revised contract.
    # Keep the historical record, but never treat an invalid/expired record as current.
    if capability == "GLOBAL_SYNTHESIS" and record:
        return "NOT_TESTED"
    return "FAIL" if (value.get("probe_results") or {}).get(capability) == "FAIL" else "NOT_TESTED"


def business_assessments(
    model: str, results: dict[str, str], diagnostics: dict[str, dict[str, str]] | None = None
) -> list[dict[str, str]]:
    return [
        {
            "stage": stage,
            "model": model,
            "prompt_version": _probe_version(stage),
            "benchmark_version": _probe_version(stage),
            "probe_status": status,
            "tested_at": utc_now().isoformat(),
            "evidence_ref": f"{_probe_version(stage)}:{stage}",
            **(diagnostics or {}).get(stage, {}),
        }
        for stage, status in results.items()
        if stage != "FORMAT_SMOKE" and status != "NOT_TESTED"
    ]


def profile_supports_capability(
    value: dict | None,
    capability: str,
    *,
    allow_unverified: bool = False,
    explicitly_selected: bool = False,
) -> bool:
    if not value or not value.get("enabled", True):
        return False
    if capability == "GLOBAL_SYNTHESIS" and "text" not in (value.get("modalities") or ["text"]):
        return False
    probe = business_probe_status(value, capability)
    capabilities = set(value.get("capabilities") or [])
    return allow_unverified or (
        probe != "FAIL"
        and (
            not capabilities
            or capability in capabilities
            or probe == "PASS"
            or (explicitly_selected and probe == "NOT_TESTED")
        )
    )


def _assess_note_probe(value: dict) -> tuple[str, str]:
    """Check note evidence and simple facts; ambiguous paraphrases remain unverified."""
    sections = value.get("sections")
    if not isinstance(sections, list) or not sections:
        return "FAIL", "NOTE_PROBE_SECTIONS_INVALID"
    coverage = {key: [] for key in NOTE_PROBE_SOURCES}
    summaries = {key: [] for key in NOTE_PROBE_SOURCES}
    for section in sections:
        if (
            not isinstance(section, dict)
            or not isinstance(section.get("summary"), str)
            or not section["summary"].strip()
        ):
            return "FAIL", "NOTE_PROBE_SUMMARY_MISSING"
        ids = section.get("segment_ids")
        if (
            not isinstance(ids, list)
            or not ids
            or any(not isinstance(item, str) or item not in NOTE_PROBE_SOURCES for item in ids)
            or len(ids) != len(set(ids))
        ):
            return "FAIL", "NOTE_PROBE_SOURCE_INVALID"
        quotes = section.get("supporting_quotes")
        if not isinstance(quotes, list) or not quotes:
            return "FAIL", "NOTE_PROBE_QUOTE_MISSING"
        bullets = section.get("bullets", [])
        if not isinstance(bullets, list) or any(not isinstance(item, str) for item in bullets):
            return "FAIL", "NOTE_PROBE_BULLETS_INVALID"
        text = " ".join([section["summary"], *bullets])
        source = "\n".join(NOTE_PROBE_SOURCES[item] for item in ids)
        if set(re.findall(r"\d+(?:元|月)", text)) - set(re.findall(r"\d+(?:元|月)", source)):
            return "FAIL", "NOTE_PROBE_FACT_CONTRADICTION"
        if "s1" in ids and re.search(r"(?<!不)推荐周末|周末(?:很|也)?(?:推荐|适合)", text):
            return "FAIL", "NOTE_PROBE_FACT_CONTRADICTION"
        if "s2" in ids and re.search(r"不(?:推荐|建议)(?:洛阳)?米粉|米粉不(?:推荐|建议)", text):
            return "FAIL", "NOTE_PROBE_FACT_CONTRADICTION"
        for quote in quotes:
            if not isinstance(quote, str) or not quote.strip() or quote not in source:
                return "FAIL", "NOTE_PROBE_QUOTE_INVALID"
            for segment_id in ids:
                coverage[segment_id].extend(
                    part for part in quote.split("\n") if part and part in NOTE_PROBE_SOURCES[segment_id]
                )
        for segment_id in ids:
            summaries[segment_id].append(text)
    for segment_id, terms in (("s1", ("西安", "10月", "20元", "不推荐周末")), ("s2", ("洛阳", "推荐米粉"))):
        if not all(any(term in quote for quote in coverage[segment_id]) for term in terms):
            return "FAIL", "NOTE_PROBE_FACT_EVIDENCE_MISSING"
    first, second = " ".join(summaries["s1"]), " ".join(summaries["s2"])
    if not (
        "西安" in first
        and re.search(r"10月|十月", first)
        and re.search(r"20元|二十元", first)
        and "周末" in first
        and re.search(r"不推荐|不建议|避开|避免", first)
        and "洛阳" in second
        and "米粉" in second
        and re.search(r"推荐|建议|尝|吃", second)
    ):
        return "NOT_TESTED", "NOTE_PROBE_SUMMARY_UNCERTAIN"
    return "PASS", "NOTE_PROBE_EVIDENCE_COVERED"


def model_connection_type(value: dict[str, Any]) -> str:
    if value.get("connection_type"):
        return value["connection_type"]
    names = [
        str(value.get(key) or "").lower().replace(" ", "").replace("-", "") for key in ("provider", "name")
    ]
    # Only legacy, explicitly named Mux profiles; never infer a provider from its port alone.
    if any(name in {"localaimux", "localmux"} for name in names) and urlsplit(
        str(value.get("base_url") or "")
    ).hostname in {"localhost", "127.0.0.1", "::1"}:
        return "LOCAL_ROUTER"
    return "DIRECT"


def model_profile_from_value(profile_id: str, value: dict[str, Any]) -> ModelProfile:
    default_location = "LOCAL" if str(value.get("provider")).lower() == "ollama" else "REMOTE"
    location = str(value.get("location") or default_location)
    capabilities = {item for item in value.get("capabilities", []) if item in AICapability._value2member_map_}
    return ModelProfile(
        id=profile_id,
        provider=str(value.get("provider") or ""),
        model=str(value.get("model") or ""),
        connection_type=model_connection_type(value),
        interface_capabilities=value.get("interface_capabilities"),
        reliability_mode=str(value.get("reliability_mode") or "STANDARD").upper(),
        request_interval_seconds=value.get("request_interval_seconds"),
        max_concurrency=value.get("max_concurrency"),
        retry_count=value.get("retry_count"),
        json_retry_count=value.get("json_retry_count"),
        rate_limit_rpm=value.get("rate_limit_rpm"),
        circuit_breaker_enabled=value.get("circuit_breaker_enabled"),
        circuit_breaker_threshold=value.get("circuit_breaker_threshold"),
        circuit_breaker_cooldown_seconds=value.get("circuit_breaker_cooldown_seconds"),
        location=location,
        modalities=set(value.get("modalities") or {"text"}),
        capabilities={AICapability(item) for item in capabilities},
        supports_json_mode=bool(value.get("supports_json_mode")),
        supports_json_schema=bool(value.get("supports_json_schema")),
        supports_thinking=bool(value.get("supports_thinking")),
        supports_tools=bool(value.get("supports_tools")),
        context_window=int(value.get("context_window") or 32_768),
        recommended_working_context=int(value.get("recommended_working_context") or 8_192),
        max_output_tokens=value.get("max_output_tokens", 4_096),
        quality_tier=str(value.get("quality_tier") or "MAIN"),
        specialties=set(value.get("specialties") or []),
        enabled=bool(value.get("enabled", True)),
    )


def invoke_profile_model(
    provider: LLMProvider,
    profile: ModelProfile,
    method: str,
    messages: list[dict[str, str]],
):
    """Keep pacing, but neither consult nor change the production circuit breaker."""
    local_hardware = uses_local_model_hardware(profile.model_dump(mode="python"))
    policy = resolve_reliability_policy(profile.model_dump(mode="python"))
    policy = replace(
        policy,
        mode="GUARDED",
        max_concurrency=1,
        retry_count=0,
        json_retry_count=0,
        circuit_breaker_enabled=False,
        request_interval_seconds=max(
            LOCAL_TEST_INTERVAL_SECONDS if local_hardware else 4.0, policy.request_interval_seconds
        ),
    )
    key = provider_rate_limit_identity(provider)
    semaphore = None
    local_interval = max(
        policy.request_interval_seconds,
        60 / policy.rate_limit_rpm if policy.rate_limit_rpm else 0,
    )
    attempted = False
    try:
        semaphore, wait_seconds, _ = ReliabilityGuards.acquire(
            key,
            policy,
            limiter_key=provider_rate_limit_identity(provider),
        )
        if wait_seconds:
            sleep(wait_seconds)
        options = ProviderRequestOptions(
            max_output_tokens=profile.max_output_tokens,
            thinking=False if profile.supports_thinking or profile.provider.lower() == "deepseek" else None,
        )
        if local_hardware or getattr(provider, "base_url", None):
            pace_model_test(local_interval)
        attempted = True
        result = getattr(provider, method)(messages, model=profile.model, options=options)
    except Exception as exc:
        error = classify_provider_error(exc)
        if (
            error.code in {"AI_PROVIDER_RATE_LIMITED", "AI_PROVIDER_THROTTLED", "AI_PROVIDER_QUOTA_EXHAUSTED"}
            or getattr(getattr(error.cause, "response", None), "status_code", None) == 429
        ):
            pace_model_test(0, max(60, retry_after_seconds(error.cause or error) or 0))
        raise error from exc
    finally:
        ReliabilityGuards.release(semaphore)
        if local_hardware and attempted:
            # Count the hardware settling interval from completion, including
            # failures; the shared hardware group carries it to the next model.
            pace_model_test(0, cooldown=local_interval, finished=True)
    return result


def probe_model_profile(
    provider: LLMProvider, profile: ModelProfile, *, diagnostics: dict | None = None, groups=None
) -> dict[str, str]:
    groups = groups or model_test_groups(
        {**profile.model_dump(), "base_url": getattr(provider, "base_url", "")}
    )
    with queued_model_test(groups, getattr(provider, "cancel_check", None)):
        return _probe_model_profile(provider, profile, diagnostics=diagnostics)


def _probe_model_profile(
    provider: LLMProvider, profile: ModelProfile, *, diagnostics: dict | None = None
) -> dict[str, str]:
    results = {capability.value: "NOT_TESTED" for capability in AICapability}

    def invoke(method: str, messages: list[dict[str, str]], probe_stage: str):
        from zhijian.ai.reliability import AIProviderError

        try:
            return invoke_profile_model(provider, profile, method, messages)
        except AIProviderError as exc:
            exc.probe_stage = probe_stage
            raise

    def structured(messages: list[dict[str, str]], probe_stage: str = "FORMAT_SMOKE"):
        return invoke(
            "generate_json",
            [{**message, "content": f"仅返回 JSON 对象。\n{message['content']}"} for message in messages],
            probe_stage,
        )

    invoke("generate_text", [{"role": "user", "content": "Reply PONG only."}], "TEXT_CONNECTIVITY")
    invoke("generate_text", [{"role": "user", "content": "请只回答：已收到。"}], "CHINESE_CONNECTIVITY")
    evidence_id = "evidence_probe_01"
    result = structured(
        [{"role": "user", "content": f'仅返回 JSON：{{"id":"{evidence_id}","ok":true}}'}],
    )
    try:
        value = parse_json_object(result.content)
        results["FORMAT_SMOKE"] = (
            "PASS" if value.get("id") == evidence_id and value.get("ok") is True else "FAIL"
        )
    except (AttributeError, TypeError, ValueError, RuntimeError):
        results["FORMAT_SMOKE"] = "FAIL"
    if results["FORMAT_SMOKE"] != "PASS":
        return results
    cases = {
        "TRANSCRIPT_CORRECTION": (
            "校对错音，保留数字和否定，仅返回变化。s1：水路庵门票20元，不推荐周末。"
            '返回 {"changes":[{"segment_id":"s1","corrected_text":"水陆庵门票20元，不推荐周末。"}]}',
            lambda value: (
                value.get("changes")
                == [{"segment_id": "s1", "corrected_text": "水陆庵门票20元，不推荐周末。"}]
            ),
        ),
        "ENTITY_EXTRACTION": (
            "只据 s1：推荐西安和洛阳，不是比较项天津。提取所有地名与逐字quote，"
            '返回 {"places":[{"name":地名,"segment_ids":["s1"],"quote":地名,'
            '"poi_policy":"RESOLVE或REFERENCE_ONLY"}]}',
            lambda value: (
                {item.get("name") for item in value.get("places", [])} == {"西安", "洛阳", "天津"}
                and all(
                    item.get("segment_ids") == ["s1"]
                    and item.get("quote") == item.get("name")
                    and item.get("poi_policy")
                    == ("REFERENCE_ONLY" if item.get("name") == "天津" else "RESOLVE")
                    for item in value.get("places", [])
                )
            ),
        ),
        "STRUCTURED_EXTRACTION": (
            "仅据 s1：西安和洛阳适合10月，门票20元，不推荐周末。"
            '返回 {"claims":[{"type":"MONTH或PRICE或NEGATIVE","segment_ids":["s1"],'
            '"quote":"逐字子串"}]}；三种事实都保留。',
            lambda value: (
                {item.get("type") for item in value.get("claims", [])} == {"MONTH", "PRICE", "NEGATIVE"}
                and all(
                    item.get("segment_ids") == ["s1"]
                    and item.get("quote")
                    and item["quote"] in "西安和洛阳适合10月，门票20元，不推荐周末。"
                    and {"MONTH": "10月", "PRICE": "20元", "NEGATIVE": "不推荐"}.get(
                        item.get("type"), "__INVALID__"
                    )
                    in item["quote"]
                    for item in value.get("claims", [])
                )
            ),
        ),
        "GLOBAL_SYNTHESIS": (
            "仅据 s1：西安10月门票20元，不推荐周末。s2：洛阳推荐米粉。"
            '返回 JSON {"sections":[{"heading":"标题","summary":"概述",'
            '"bullets":["事实要点"],"segment_ids":["s1"],"supporting_quotes":["逐字原文"]}]}。'
            "可合并或拆分章节、调整顺序，摘要可改写；保留两地、月份、价格、否定和推荐菜。"
            "每条引文必须来自对应 segment_ids，所有必需事实都要有逐字引文覆盖。",
            None,
        ),
    }
    for capability, (prompt, validate) in cases.items():
        result = structured([{"role": "user", "content": prompt}], capability)
        if capability == "GLOBAL_SYNTHESIS":
            from hashlib import sha256

            from zhijian.ai.reliability import AIProviderError
            from zhijian.providers.llm import provider_error_details

            if (getattr(result, "metadata", {}) or {}).get("finish_reason") in {"length", "max_tokens"}:
                error = AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "笔记能力小样输出截断，本次无法判定")
                error.probe_stage = capability
                raise error
            try:
                status, reason = _assess_note_probe(parse_json_object(result.content))
            except (ValueError, TypeError, AttributeError, RuntimeError):
                status, reason = "FAIL", "NOTE_PROBE_JSON_INVALID"
            results[capability] = status
            if diagnostics is not None:
                diagnostics[capability] = {
                    "reason_code": reason,
                    "response_hash": sha256(result.content.encode()).hexdigest(),
                    "response_preview": provider_error_details(ValueError(result.content))["message"],
                }
            continue
        try:
            value = parse_json_object(result.content)
            results[capability] = (
                "PASS"
                if validate(value)
                and (getattr(result, "metadata", {}) or {}).get("finish_reason")
                not in {"length", "max_tokens"}
                else "FAIL"
            )
        except (ValueError, TypeError, AttributeError, RuntimeError):
            results[capability] = "FAIL"
    return results
