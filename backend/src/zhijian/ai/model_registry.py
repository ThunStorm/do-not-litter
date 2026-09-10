import json
from typing import Any

from zhijian.ai.capabilities import AICapability
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
        request_interval_seconds=value.get("request_interval_seconds"),
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


def probe_model_profile(provider: LLMProvider, profile: ModelProfile) -> dict[str, str]:
    results = {capability.value: "FAIL" for capability in AICapability}
    options = ProviderRequestOptions(thinking=False) if profile.provider.lower() == "ollama" else None

    def text(messages: list[dict[str, str]]):
        return provider.generate_text(messages, model=profile.model, options=options)

    def structured(messages: list[dict[str, str]]):
        return provider.generate_json(messages, model=profile.model, options=options)

    try:
        text([{"role": "user", "content": "Reply PONG only."}])
        text([{"role": "user", "content": "请只回答：已收到。"}])
        results[AICapability.CLASSIFICATION.value] = "PASS"
    except Exception:
        return results
    evidence_id = "evidence_probe_01"
    try:
        result = structured(
            [{"role": "user", "content": f'仅返回 JSON：{{"id":"{evidence_id}","ok":true}}'}],
        )
        value = json.loads(result.content)
        if value.get("id") == evidence_id:
            results[AICapability.STRUCTURED_EXTRACTION.value] = "PASS"
            results[AICapability.ENTITY_EXTRACTION.value] = "PASS"
            results[AICapability.TRANSCRIPT_CORRECTION.value] = "PASS"
    except Exception:
        pass
    if "image" in profile.modalities:
        results[AICapability.VISION.value] = "FAIL"
        results[AICapability.DOCUMENT_VISION.value] = "FAIL"
        results[AICapability.SCREENSHOT_UNDERSTANDING.value] = "FAIL"
    if profile.supports_thinking:
        results[AICapability.CONFLICT_RESOLUTION.value] = "FAIL"
    return results
