from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import ExternalCallAudit, Job, Setting
from zhijian.domain.schemas import GeneralConfig


class AIBudgetExceeded(RuntimeError):
    code = "AI_BUDGET_EXCEEDED"


def ensure_ai_budget(db: Session, job: Job | None, *, location: str, input_chars: int) -> None:
    if job is None:
        return
    setting = db.get(Setting, "app:general")
    config = GeneralConfig(
        **(setting.value_json if setting and isinstance(setting.value_json, dict) else {})
    )
    elapsed = (utc_now() - as_utc(job.started_at)).total_seconds() if job.started_at else 0
    if elapsed >= config.ai_max_wall_time_seconds_per_job:
        raise AIBudgetExceeded("本任务已达到 AI 处理时长上限")
    location = location.upper()
    if location not in {"LOCAL", "REMOTE"}:
        raise ValueError(f"未知 AI 执行位置：{location}")
    rows = db.scalars(select(ExternalCallAudit).where(ExternalCallAudit.job_id == job.id)).all()
    actual = [row for row in rows if not (row.request_meta_json or {}).get("cache_hit")]
    if len(actual) >= config.ai_max_model_attempts_per_job:
        raise AIBudgetExceeded("本任务已达到 AI 模型调用次数上限")
    location_rows = [row for row in actual if _audit_location(row) == location]
    prompt_tokens = sum(
        int((row.response_meta_json or {}).get("prompt_tokens") or 0) for row in location_rows
    )
    completion_tokens = sum(
        int((row.response_meta_json or {}).get("completion_tokens") or 0) for row in location_rows
    )
    estimate = max(1, input_chars // 4)
    remote = location == "REMOTE"
    prompt_limit = (
        config.ai_max_remote_prompt_tokens_per_job if remote else config.ai_max_local_prompt_tokens_per_job
    )
    completion_limit = (
        config.ai_max_remote_completion_tokens_per_job
        if remote
        else config.ai_max_local_completion_tokens_per_job
    )
    if prompt_tokens + estimate > prompt_limit or completion_tokens >= completion_limit:
        raise AIBudgetExceeded("本任务已达到 AI Token 预算上限")


def _audit_location(row: ExternalCallAudit) -> str:
    """Prefer the persisted routing decision; retain compatibility with pre-Gateway audits."""
    value = str((row.request_meta_json or {}).get("location") or "").upper()
    if value in {"LOCAL", "REMOTE"}:
        return value
    return "LOCAL" if row.provider.lower() == "ollama" else "REMOTE"
