from collections import deque
from contextlib import contextmanager
from dataclasses import replace
from threading import Condition, local
from time import sleep
from typing import Any
from urllib.parse import urlsplit

from zhijian.ai.capabilities import AICapability
from zhijian.ai.reliability import (
    ReliabilityGuards,
    classify_provider_error,
    provider_rate_limit_identity,
    resolve_reliability_policy,
)
from zhijian.ai.schemas import ModelProfile
from zhijian.ai.structured_output import parse_json_object
from zhijian.core.time import utc_now
from zhijian.providers.llm import LLMProvider, ProviderRequestOptions

BUSINESS_PROBE_VERSION = "business-mini-v1"


def business_probe_status(value: dict, capability: str) -> str:
    from datetime import datetime, timedelta

    from zhijian.core.time import as_utc

    records = value.get("business_assessments") or []
    record = next((row for row in records if row.get("stage") == capability), None)
    if (
        record
        and record.get("model") == value.get("model")
        and record.get("prompt_version") == BUSINESS_PROBE_VERSION
    ):
        try:
            if utc_now() - as_utc(datetime.fromisoformat(record["tested_at"])) <= timedelta(days=30):
                return str(record.get("probe_status") or "NOT_TESTED")
        except (ValueError, KeyError, TypeError):
            pass
    return "FAIL" if (value.get("probe_results") or {}).get(capability) == "FAIL" else "NOT_TESTED"


def business_assessments(model: str, results: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "stage": stage,
            "model": model,
            "prompt_version": BUSINESS_PROBE_VERSION,
            "benchmark_version": BUSINESS_PROBE_VERSION,
            "probe_status": status,
            "tested_at": utc_now().isoformat(),
            "evidence_ref": f"{BUSINESS_PROBE_VERSION}:{stage}",
        }
        for stage, status in results.items()
        if stage != "FORMAT_SMOKE" and status != "NOT_TESTED"
    ]


_manual_test_condition = Condition()
_manual_test_tickets: deque[object] = deque()
_manual_test_state = local()


@contextmanager
def queued_model_test():
    """FIFO for entire manual operations, including all calls in a capability probe."""
    if getattr(_manual_test_state, "active", False):
        yield
        return
    ticket = object()
    with _manual_test_condition:
        _manual_test_tickets.append(ticket)
        _manual_test_condition.notify_all()
    try:
        with _manual_test_condition:
            _manual_test_condition.wait_for(lambda: _manual_test_tickets[0] is ticket)
        _manual_test_state.active = True
        yield
    finally:
        _manual_test_state.active = False
        with _manual_test_condition:
            _manual_test_tickets.remove(ticket)
            _manual_test_condition.notify_all()


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
    policy = resolve_reliability_policy(profile.model_dump(mode="python"))
    policy = replace(
        policy,
        mode="GUARDED",
        max_concurrency=1,
        retry_count=0,
        json_retry_count=0,
        circuit_breaker_enabled=False,
        request_interval_seconds=max(
            4.0 if profile.location == "REMOTE" else 0, policy.request_interval_seconds
        ),
    )
    key = provider_rate_limit_identity(provider)
    semaphore = None
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
        result = getattr(provider, method)(messages, model=profile.model, options=options)
    except Exception as exc:
        error = classify_provider_error(exc)
        raise error from exc
    finally:
        ReliabilityGuards.release(semaphore)
    return result


def probe_model_profile(provider: LLMProvider, profile: ModelProfile) -> dict[str, str]:
    with queued_model_test():
        return _probe_model_profile(provider, profile)


def _probe_model_profile(provider: LLMProvider, profile: ModelProfile) -> dict[str, str]:
    results = {capability.value: "NOT_TESTED" for capability in AICapability}

    def text(messages: list[dict[str, str]]):
        return invoke_profile_model(provider, profile, "generate_text", messages)

    def structured(messages: list[dict[str, str]]):
        return invoke_profile_model(provider, profile, "generate_json", messages)

    text([{"role": "user", "content": "Reply PONG only."}])
    text([{"role": "user", "content": "请只回答：已收到。"}])
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
            "仅据 s1：西安10月门票20元，不推荐周末；s2：洛阳推荐米粉。"
            '返回 {"sections":[{"summary":"原文事实","segment_ids":["s1或s2"]}]}，'
            "保留两地、月份、价格、否定与推荐菜。",
            lambda value: (
                len(value.get("sections", [])) == 2
                and any(
                    item.get("segment_ids") == ["s1"]
                    and all(term in item.get("summary", "") for term in ("西安", "10月", "20元", "不推荐"))
                    for item in value["sections"]
                )
                and any(
                    item.get("segment_ids") == ["s2"]
                    and all(term in item.get("summary", "") for term in ("洛阳", "米粉"))
                    for item in value["sections"]
                )
            ),
        ),
    }
    for capability, (prompt, validate) in cases.items():
        result = structured([{"role": "user", "content": prompt}])
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
