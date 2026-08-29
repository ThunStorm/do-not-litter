from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from zhijian.ai.capabilities import (
    AICachePolicy,
    AICapability,
    AIExecutionMode,
    AIPrivacyPolicy,
    AIQualityTarget,
)


class AIEvidenceSegment(BaseModel):
    id: str
    text: str
    locator: dict[str, Any] = Field(default_factory=dict)


class AIRequest(BaseModel):
    capability: AICapability
    stage: str
    input_text: str | None = None
    evidence_segments: list[AIEvidenceSegment] = Field(default_factory=list)
    output_schema: dict[str, Any] | None = None
    quality_target: AIQualityTarget = AIQualityTarget.BALANCED
    execution_mode: AIExecutionMode | None = None
    provider_override: str | None = None
    model_override: str | None = None
    domain: str | None = None
    domain_pack_ids: list[str] = Field(default_factory=list)
    privacy: AIPrivacyPolicy = AIPrivacyPolicy.NORMAL
    max_input_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    cache_policy: AICachePolicy = AICachePolicy.USE
    force_regenerate: bool = False
    allow_escalation: bool = True


class AIResult(BaseModel):
    data: Any
    provider: str
    model: str
    capability: AICapability
    execution_route: str
    local_attempted: bool
    remote_attempted: bool
    escalated: bool = False
    validation_status: str = "NOT_VALIDATED"
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    duration_ms: int
    prompt_version: str = "legacy"
    schema_version: str = "legacy"
    parser_version: str = "legacy"
    escalation_reasons: list[str] = Field(default_factory=list)


class ModelProfile(BaseModel):
    id: str
    provider: str
    model: str
    location: Literal["LOCAL", "REMOTE"] = "REMOTE"
    modalities: set[str] = Field(default_factory=lambda: {"text"})
    capabilities: set[AICapability] = Field(default_factory=set)
    supports_json_mode: bool = False
    supports_json_schema: bool = False
    supports_thinking: bool = False
    supports_tools: bool = False
    context_window: int = Field(default=32_768, ge=1)
    recommended_working_context: int = Field(default=8_192, ge=1)
    max_output_tokens: int = Field(default=4_096, ge=1)
    quality_tier: Literal["FAST", "MAIN", "STRONG", "SPECIALIST"] = "MAIN"
    specialties: set[str] = Field(default_factory=set)
    enabled: bool = True


class AIStagePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    capability: AICapability
    execution_mode: AIExecutionMode | None = None
    local_profile_id: str | None = None
    remote_profile_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_input_tokens: int | None = Field(default=None, ge=1, le=131_072)
    max_output_tokens: int | None = Field(default=None, ge=1, le=32_768)
    thinking: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=900)
    retry_count: int | None = Field(default=None, ge=0, le=3)
    confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    escalation_threshold: float | None = Field(default=None, ge=0, le=1)
    context_strategy: str | None = Field(default=None, max_length=80)
    chunk_size: int | None = Field(default=None, ge=1, le=100_000)
    neighbor_segments: int | None = Field(default=None, ge=0, le=10)
    domain: str | None = Field(default=None, max_length=80)
    domain_pack_ids: list[str] = Field(default_factory=list, max_length=20)
    cache_enabled: bool | None = None
    force_regenerate: bool = False
    force_full_correction: bool | None = None
    version: int = Field(default=1, ge=1)


class ResolvedAIStagePolicy(AIStagePolicy):
    sources: dict[str, str] = Field(default_factory=dict)
