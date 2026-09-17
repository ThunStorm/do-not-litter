from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import ExternalCallAudit, Job, Setting, Transcript, VideoAsset
from zhijian.domain.schemas import GeneralConfig
from zhijian.services.audit import record_event


class AIBudgetExceeded(RuntimeError):
    code = "AI_BUDGET_EXCEEDED"


@dataclass(frozen=True)
class SoftBudgetState:
    status: str
    expected_prompt_tokens: int
    expected_completion_tokens: int
    expected_total_calls: int
    projected_prompt_tokens: int


def _config(db: Session) -> GeneralConfig:
    setting = db.get(Setting, "app:general")
    return GeneralConfig(
        **(setting.value_json if setting and isinstance(setting.value_json, dict) else {})
    )


def _expected_budget(db: Session, job: Job, input_chars: int) -> dict[str, int]:
    stored = job.payload_json.get("ai_soft_budget") if isinstance(job.payload_json, dict) else None
    if isinstance(stored, dict) and all(
        key in stored
        for key in ("expected_prompt_tokens", "expected_completion_tokens", "expected_total_calls")
    ):
        return {
            key: int(stored.get(key) or 0)
            for key in ("expected_prompt_tokens", "expected_completion_tokens", "expected_total_calls")
        }
    asset_id = str(job.payload_json.get("video_asset_id") or "")
    transcript_chars = 0
    if asset_id:
        transcript = db.scalar(
            select(Transcript)
            .where(Transcript.video_asset_id == asset_id)
            .order_by(Transcript.version.desc())
        )
        transcript_chars = len(transcript.text) if transcript else 0
    if not transcript_chars and asset_id:
        asset = db.get(VideoAsset, asset_id)
        transcript_chars = max(0, int((asset.duration_ms or 0) / 1000) * 24)
    base_tokens = max(1, max(transcript_chars, input_chars) // 4)
    expected = {
        "expected_prompt_tokens": base_tokens * 2,
        "expected_completion_tokens": max(256, base_tokens // 5),
        "expected_total_calls": max(1, (transcript_chars + 11_999) // 12_000 + 1),
    }
    job.payload_json = {**job.payload_json, "ai_soft_budget": {**expected, "status": "EXPECTED"}}
    return expected


def soft_budget_state(
    db: Session,
    job: Job | None,
    *,
    location: str,
    input_chars: int = 0,
    provider: str | None = None,
    model: str | None = None,
    profile_id: str | None = None,
) -> SoftBudgetState | None:
    if job is None:
        return None
    config = _config(db)
    location = location.upper()
    previous = (job.payload_json.get("ai_soft_budget") or {}).get("status")
    expected = _expected_budget(db, job, input_chars)
    filters = [
        ExternalCallAudit.job_id == job.id,
        ExternalCallAudit.capability == "LLM",
    ]
    if job.started_at:
        filters.append(ExternalCallAudit.created_at >= job.started_at)
    rows = db.scalars(select(ExternalCallAudit).where(*filters)).all()
    actual = [row for row in rows if not (row.request_meta_json or {}).get("cache_hit")]
    if location == "REMOTE" and (provider or model or profile_id):
        actual = [
            row
            for row in actual
            if _same_remote_target(
                row,
                provider=provider,
                model=model,
                profile_id=profile_id,
            )
        ]
    prompt_tokens = sum(
        int((row.response_meta_json or {}).get("prompt_tokens") or 0)
        for row in actual
        if _audit_location(row) == location
    )
    estimate = max(1, input_chars // 4)
    limit = (
        config.ai_max_remote_prompt_tokens_per_job
        if location == "REMOTE"
        else config.ai_max_local_prompt_tokens_per_job
    )
    projected = max(prompt_tokens + estimate, expected["expected_prompt_tokens"])
    status = (
        "HARD_LIMIT"
        if projected >= limit
        else "WARNING"
        if projected >= limit * config.ai_soft_budget_warning_ratio
        else "EXPECTED"
    )
    job.payload_json = {
        **job.payload_json,
        "ai_soft_budget": {**expected, "status": status, "projected_prompt_tokens": projected},
    }
    if previous != status and status != "EXPECTED":
        record_event(
            db,
            "ai.budget.soft_limit",
            f"AI Token 预算进入 {status}",
            component="ai-gateway",
            level="WARNING",
            entity_type="job",
            entity_id=job.id,
            detail={"location": location, "projected_prompt_tokens": projected, "prompt_limit": limit},
            commit=False,
        )
    return SoftBudgetState(
        status,
        expected["expected_prompt_tokens"],
        expected["expected_completion_tokens"],
        expected["expected_total_calls"],
        projected,
    )


def ensure_ai_budget(
    db: Session,
    job: Job | None,
    *,
    location: str,
    input_chars: int,
    provider: str | None = None,
    model: str | None = None,
    profile_id: str | None = None,
) -> SoftBudgetState | None:
    if job is None:
        return None
    config = _config(db)
    elapsed = (utc_now() - as_utc(job.started_at)).total_seconds() if job.started_at else 0
    if elapsed >= config.ai_max_wall_time_seconds_per_job:
        raise AIBudgetExceeded("本轮任务已达到 AI 处理时长上限")
    location = location.upper()
    if location not in {"LOCAL", "REMOTE"}:
        raise ValueError(f"未知 AI 执行位置：{location}")
    soft_state = soft_budget_state(
        db,
        job,
        location=location,
        input_chars=input_chars,
        provider=provider,
        model=model,
        profile_id=profile_id,
    )
    filters = [
        ExternalCallAudit.job_id == job.id,
        ExternalCallAudit.capability == "LLM",
    ]
    if job.started_at:
        filters.append(ExternalCallAudit.created_at >= job.started_at)
    rows = db.scalars(select(ExternalCallAudit).where(*filters)).all()
    actual = [row for row in rows if not (row.request_meta_json or {}).get("cache_hit")]
    target_rows = (
        [
            row
            for row in actual
            if _same_remote_target(
                row,
                provider=provider,
                model=model,
                profile_id=profile_id,
            )
        ]
        if provider or model or profile_id
        else [row for row in actual if _audit_location(row) == "REMOTE"]
    )
    if location == "REMOTE" and len(target_rows) >= config.ai_max_model_attempts_per_job:
        raise AIBudgetExceeded("本轮该远程模型已达到调用次数上限")
    location_rows = (
        target_rows
        if location == "REMOTE"
        else [row for row in actual if _audit_location(row) == "LOCAL"]
    )
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
        target = "该远程模型" if remote else "本地模型"
        raise AIBudgetExceeded(f"本轮{target}已达到 AI Token 预算上限")
    return soft_state


def _audit_location(row: ExternalCallAudit) -> str:
    """Prefer the persisted routing decision; retain compatibility with pre-Gateway audits."""
    value = str((row.request_meta_json or {}).get("location") or "").upper()
    if value in {"LOCAL", "REMOTE"}:
        return value
    return "LOCAL" if row.provider.lower() == "ollama" else "REMOTE"


def _same_remote_target(
    row: ExternalCallAudit,
    *,
    provider: str | None,
    model: str | None,
    profile_id: str | None,
) -> bool:
    if _audit_location(row) != "REMOTE":
        return False
    metadata = row.request_meta_json or {}
    saved_profile_id = str(metadata.get("profile_id") or "")
    if profile_id and saved_profile_id:
        return saved_profile_id == profile_id
    return row.provider.lower() == str(provider or "").lower() and str(metadata.get("model") or "") == str(
        model or ""
    )
