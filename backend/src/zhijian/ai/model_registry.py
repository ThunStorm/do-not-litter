import json
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
from zhijian.providers.llm import LLMProvider, ProviderRequestOptions

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
    results[AICapability.CLASSIFICATION.value] = "PASS"
    evidence_id = "evidence_probe_01"
    result = structured(
        [{"role": "user", "content": f'仅返回 JSON：{{"id":"{evidence_id}","ok":true}}'}],
    )
    try:
        value = json.loads(result.content)
        if value.get("id") == evidence_id:
            results[AICapability.STRUCTURED_EXTRACTION.value] = "PASS"
            results[AICapability.ENTITY_EXTRACTION.value] = "PASS"
            results[AICapability.TRANSCRIPT_CORRECTION.value] = "PASS"
        else:
            results[AICapability.STRUCTURED_EXTRACTION.value] = "FAIL"
            results[AICapability.ENTITY_EXTRACTION.value] = "FAIL"
            results[AICapability.TRANSCRIPT_CORRECTION.value] = "FAIL"
    except (AttributeError, TypeError, ValueError):
        results[AICapability.STRUCTURED_EXTRACTION.value] = "FAIL"
        results[AICapability.ENTITY_EXTRACTION.value] = "FAIL"
        results[AICapability.TRANSCRIPT_CORRECTION.value] = "FAIL"
    return results
