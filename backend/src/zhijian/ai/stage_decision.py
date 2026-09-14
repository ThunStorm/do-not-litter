"""Small, auditable first-phase decisions before a model stage is entered."""

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from zhijian.db.models import Job
from zhijian.services.audit import record_event


@dataclass(frozen=True)
class StageDecision:
    stage: str
    decision: str
    reason_code: str
    estimated_tokens_saved: int = 0


def decide_stage(
    stage: str, *, reusable: bool = False, has_relevant_segments: bool = True, estimated_tokens: int = 0
) -> StageDecision:
    if reusable:
        return StageDecision(stage, "REUSE", "ARTIFACT_REUSED", max(0, estimated_tokens))
    if not has_relevant_segments:
        return StageDecision(stage, "SKIP", "NO_RELEVANT_SEGMENTS")
    return StageDecision(stage, "RUN", "SEMANTIC_INPUT_CHANGED")


def record_stage_decision(db: Session, job: Job | None, decision: StageDecision) -> None:
    if job is None:
        return
    record_event(
        db,
        "ai.stage.decision",
        f"{decision.stage} 自动决策：{decision.decision}",
        component="video-pipeline",
        entity_type="job",
        entity_id=job.id,
        detail=asdict(decision),
        commit=False,
    )
