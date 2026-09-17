import json
from dataclasses import replace
from time import sleep
from typing import Any

from zhijian.ai.capabilities import AICapability
from zhijian.ai.reliability import (
    ReliabilityGuards,
    classify_provider_error,
    provider_identity,
    provider_rate_limit_identity,
    resolve_reliability_policy,
    retry_after_seconds,
)
from zhijian.ai.schemas import ModelProfile
from zhijian.providers.llm import LLMProvider, ProviderRequestOptions


def model_profile_from_value(profile_id: str, value: dict[str, Any]) -> ModelProfile:
    default_location = "LOCAL" if str(value.get("provider")).lower() == "ollama" else "REMOTE"
    location = str(value.get("location") or default_location)
    capabilities = {item for item in value.get("capabilities", []) if item in AICapability._value2member_map_}
    return ModelProfile(
        id=profile_id,
        provider=str(value.get("provider") or ""),
        model=str(value.get("model") or ""),
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
        max_output_tokens=int(value.get("max_output_tokens") or 4_096),
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
    """Run interactive tests through the same account-level pacing used by jobs."""
    policy = resolve_reliability_policy(profile.model_dump(mode="python"))
    if profile.location == "REMOTE":
        policy = replace(
            policy,
            mode="GUARDED",
            request_interval_seconds=max(4.0, policy.request_interval_seconds),
            max_concurrency=1,
            retry_count=0,
            json_retry_count=0,
            circuit_breaker_enabled=True,
            circuit_breaker_cooldown_seconds=max(120.0, policy.circuit_breaker_cooldown_seconds),
        )
    key = provider_identity(provider, profile.model)
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
            max_output_tokens=min(64, profile.max_output_tokens),
            thinking=False,
        )
        result = getattr(provider, method)(messages, model=profile.model, options=options)
    except Exception as exc:
        error = classify_provider_error(exc)
        failure_policy = policy
        if error.code in {
            "AI_PROVIDER_RATE_LIMITED",
            "AI_PROVIDER_THROTTLED",
            "AI_PROVIDER_QUOTA_EXHAUSTED",
        }:
            error.open_circuit = True
            retry_after = retry_after_seconds(error.cause or error)
            if retry_after is not None:
                failure_policy = replace(
                    policy,
                    circuit_breaker_cooldown_seconds=retry_after,
                )
        ReliabilityGuards.failure(key, failure_policy, error)
        raise error from exc
    else:
        ReliabilityGuards.success(key)
        return result
    finally:
        ReliabilityGuards.release(semaphore)


def probe_model_profile(provider: LLMProvider, profile: ModelProfile) -> dict[str, str]:
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
