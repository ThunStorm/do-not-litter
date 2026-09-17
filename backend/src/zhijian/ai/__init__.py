from zhijian.ai.capabilities import (
    AICachePolicy,
    AICapability,
    AIExecutionMode,
    AIModelLocation,
    AIPrivacyPolicy,
    AIQualityTarget,
)
from zhijian.ai.domain_context import DomainPack
from zhijian.ai.schemas import (
    AIEvidenceSegment,
    AIRequest,
    AIResult,
    AIStagePolicy,
    ModelProfile,
    ResolvedAIStagePolicy,
)

__all__ = [
    "AICachePolicy",
    "AICapability",
    "AIEvidenceSegment",
    "DomainPack",
    "AIExecutionMode",
    "AIModelLocation",
    "AIPrivacyPolicy",
    "AIQualityTarget",
    "AIRequest",
    "AIResult",
    "AIStagePolicy",
    "AIWorkloadGateway",
    "ModelProfile",
    "ResolvedAIStagePolicy",
]


def __getattr__(name: str):
    if name == "AIWorkloadGateway":
        from zhijian.ai.gateway import AIWorkloadGateway

        return AIWorkloadGateway
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
