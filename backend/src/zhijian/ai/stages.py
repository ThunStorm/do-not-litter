from dataclasses import dataclass

from zhijian.ai.capabilities import AICapability, AIExecutionMode


@dataclass(frozen=True)
class StageParameterSpec:
    stage: str
    capability: AICapability
    allowed: frozenset[str]


_COMMON = frozenset(
    {
        "execution_mode",
        "local_profile_id",
        "remote_profile_id",
        "temperature",
        "max_input_tokens",
        "max_output_tokens",
        "thinking",
        "timeout_seconds",
        "retry_count",
        "confidence_threshold",
        "escalation_threshold",
        "domain",
        "domain_pack_ids",
        "cache_enabled",
        "force_regenerate",
    }
)

STAGE_SPECS = {
    "TRANSCRIPT_CORRECTION": StageParameterSpec(
        "TRANSCRIPT_CORRECTION",
        AICapability.TRANSCRIPT_CORRECTION,
        _COMMON | {"chunk_size", "neighbor_segments", "force_full_correction"},
    ),
    "GENERATE_AI_NOTE": StageParameterSpec(
        "GENERATE_AI_NOTE",
        AICapability.GLOBAL_SYNTHESIS,
        _COMMON | {"chunk_size"},
    ),
    "EXTRACT_TRAVEL_FACTS": StageParameterSpec(
        "EXTRACT_TRAVEL_FACTS",
        AICapability.ENTITY_EXTRACTION,
        _COMMON | {"chunk_size", "neighbor_segments"},
    ),
    "SCREENSHOT_UNDERSTANDING": StageParameterSpec(
        "SCREENSHOT_UNDERSTANDING",
        AICapability.SCREENSHOT_UNDERSTANDING,
        _COMMON,
    ),
    "VISION_FACT": StageParameterSpec(
        "VISION_FACT",
        AICapability.SCREENSHOT_UNDERSTANDING,
        _COMMON,
    ),
}


def stage_spec(stage: str) -> StageParameterSpec:
    try:
        return STAGE_SPECS[stage]
    except KeyError as exc:
        raise ValueError(f"未知 AI 阶段：{stage}") from exc


def stage_defaults(stage: str) -> dict[str, object]:
    spec = stage_spec(stage)
    values: dict[str, object] = {"stage": stage, "capability": spec.capability}
    if stage == "TRANSCRIPT_CORRECTION":
        values.update(
            execution_mode=AIExecutionMode.LOCAL_FIRST,
            temperature=0.1,
            thinking=False,
            retry_count=0,
            confidence_threshold=0.75,
            escalation_threshold=0.60,
            neighbor_segments=2,
            cache_enabled=True,
            force_full_correction=False,
        )
    elif stage == "EXTRACT_TRAVEL_FACTS":
        values.update(
            execution_mode=AIExecutionMode.LOCAL_FIRST,
            temperature=0.1,
            thinking=False,
            retry_count=0,
            confidence_threshold=0.75,
            domain="travel",
            cache_enabled=True,
        )
    else:
        values.update(
            execution_mode=AIExecutionMode.AUTO,
            temperature=0.3,
            retry_count=1,
            cache_enabled=True,
        )
    return values
