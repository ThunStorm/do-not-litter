from typing import Any

from zhijian.ai.capabilities import AICapability, AIModelLocation
from zhijian.ai.model_registry import model_profile_from_value
from zhijian.ai.schemas import AIStagePolicy, ResolvedAIStagePolicy
from zhijian.ai.stages import stage_defaults, stage_spec


def resolve_stage_policy(
    stage: str,
    *,
    saved: dict[str, Any] | None = None,
    job_override: dict[str, Any] | None = None,
    runtime_override: dict[str, Any] | None = None,
) -> ResolvedAIStagePolicy:
    values = stage_defaults(stage)
    sources = {key: "system_default" for key in values}
    for source, override in (
        ("saved_stage_policy", saved),
        ("job_override", job_override),
        ("runtime_override", runtime_override),
    ):
        for key, value in (override or {}).items():
            if key in {"stage", "capability", "version"} or value is None:
                continue
            values[key] = value
            sources[key] = source
        if override and override.get("version"):
            values["version"] = override["version"]
    return ResolvedAIStagePolicy(**values, sources=sources)


def validate_stage_policy(
    policy: AIStagePolicy,
    profiles: dict[str, dict[str, Any]],
) -> None:
    spec = stage_spec(policy.stage)
    if policy.capability != spec.capability:
        raise ValueError("阶段 Capability 不匹配")
    configured = policy.model_dump(exclude_none=True, exclude={"stage", "capability", "version"})
    invalid = set(configured) - set(spec.allowed)
    if invalid:
        raise ValueError(f"阶段不支持参数：{', '.join(sorted(invalid))}")
    for field, expected_location in (
        ("local_profile_id", AIModelLocation.LOCAL.value),
        ("remote_profile_id", AIModelLocation.REMOTE.value),
    ):
        profile_id = getattr(policy, field)
        if not profile_id:
            continue
        value = profiles.get(profile_id)
        if value is None:
            raise ValueError("阶段模型必须从已保存的模型中选择")
        profile = model_profile_from_value(profile_id, value)
        if not profile.enabled or profile.location != expected_location:
            raise ValueError(f"{field.removesuffix('_profile_id')} 模型的位置或启用状态无效")
        if spec.capability in {
            AICapability.VISION,
            AICapability.DOCUMENT_VISION,
            AICapability.SCREENSHOT_UNDERSTANDING,
        } and "image" not in profile.modalities:
            raise ValueError("视觉阶段不能选择 text-only 模型")
        if policy.thinking and not profile.supports_thinking:
            raise ValueError("所选模型未声明支持 thinking，不能保存 thinking=true")
        if policy.max_output_tokens and policy.max_output_tokens > profile.max_output_tokens:
            raise ValueError("阶段最大输出超过模型 Profile 上限")
