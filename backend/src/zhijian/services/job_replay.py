from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import as_utc, utc_now
from zhijian.db.models import Job, JobStep, JobStepArtifact, SystemEvent
from zhijian.domain.enums import JobStatus
from zhijian.services.audit import record_event
from zhijian.services.video_support import prompt_supplement_hash

VIDEO_STEP_ORDER = (
    "VALIDATE_LINK",
    "FETCH_METADATA",
    "FETCH_SUBTITLE",
    "DOWNLOAD_AUDIO",
    "ASR",
    "NORMALIZE_TRANSCRIPT",
    "CORRECT_TRANSCRIPT",
    "EXTRACT_TRAVEL_FACTS",
    "GENERATE_AI_NOTE",
    "RESOLVE_POI",
    "BUILD_PLACE_NOTES",
    "PLAN_SCREENSHOTS",
    "DOWNLOAD_VIDEO_FOR_FRAMES",
    "EXTRACT_SCREENSHOTS",
    "MATERIALIZE",
    "CLEAN_CACHE",
)
REPLAYABLE_START_INDEX = VIDEO_STEP_ORDER.index("CORRECT_TRANSCRIPT")
LOGIN_SKIPPABLE_STEPS = {"DOWNLOAD_VIDEO_FOR_FRAMES"}
PROMPT_ROLE_BY_STEP = {
    "CORRECT_TRANSCRIPT": "transcript_correction",
    "GENERATE_AI_NOTE": "video_note_summary",
    "EXTRACT_TRAVEL_FACTS": "travel_place_extraction",
}


def full_replay_options(job: Job) -> dict:
    return {
        "full_replay_available": True,
        "full_replay_reason": (
            "将停止当前流程并创建新的完整任务"
            if job.status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}
            or job.lease_owner
            else None
        ),
    }


def replay_options(db: Session, job: Job) -> dict:
    steps = {item.step_name: item for item in db.scalars(select(JobStep).where(JobStep.job_id == job.id))}
    failed = next(
        (
            steps[name]
            for name in VIDEO_STEP_ORDER
            if name in steps and steps[name].status == "FAILED"
        ),
        None,
    )
    if (
        failed is None
        and job.status in {JobStatus.FAILED.value, JobStatus.NEEDS_USER.value}
        and steps.get(job.current_step)
        and steps[job.current_step].status in {"PENDING", "RUNNING"}
    ):
        failed = steps[job.current_step]
    if failed is None or failed.step_name not in VIDEO_STEP_ORDER:
        return _unavailable(job, "REPLAY_STEP_MISMATCH", "没有可续跑的失败步骤")
    if job.status not in {
        JobStatus.FAILED.value,
        JobStatus.NEEDS_USER.value,
        JobStatus.PARTIAL_SUCCESS.value,
    }:
        return _unavailable(job, "REPLAY_JOB_STATE", "当前任务状态不允许步骤续跑")
    if job.lease_owner:
        return _unavailable(job, "REPLAY_LEASE_ACTIVE", "当前执行 lease 尚未释放")
    index = VIDEO_STEP_ORDER.index(failed.step_name)
    login_audio_resume = (
        job.error_code == "VIDEO_LOGIN_REQUIRED" and failed.step_name == "DOWNLOAD_AUDIO"
    )
    if index < REPLAYABLE_START_INDEX and not login_audio_resume:
        return _unavailable(
            job, "REPLAY_ARTIFACT_MISSING", "当前版本仅支持从转写校对及后续阶段续跑"
        )
    prompt_changed_steps = [
        step_name
        for step_name, role in PROMPT_ROLE_BY_STEP.items()
        if VIDEO_STEP_ORDER.index(step_name) <= index
        and steps.get(step_name)
        and steps[step_name].input_json.get("prompt_supplement_hash")
        != prompt_supplement_hash(db, role)
    ]
    if prompt_changed_steps:
        index = min(VIDEO_STEP_ORDER.index(step_name) for step_name in prompt_changed_steps)
        failed = steps[VIDEO_STEP_ORDER[index]]
    reused = [
        name
        for name in VIDEO_STEP_ORDER[:index]
        if steps.get(name) and steps[name].status in {"COMPLETED", "REUSED"}
    ]
    artifacts = {
        item.step_name: item
        for item in db.scalars(
            select(JobStepArtifact).where(
                JobStepArtifact.job_id == job.id,
                JobStepArtifact.artifact_type == "STEP_OUTPUT",
            )
        )
    }
    required = [name for name in reused if name != "CLEAN_CACHE"]
    missing = [name for name in required if name not in artifacts]
    if missing:
        return _unavailable(job, "REPLAY_ARTIFACT_MISSING", f"缺少上游中间产物：{missing[0]}")
    missing_files = [
        name
        for name in required
        if artifacts[name].artifact_ref_json.get("cache_path")
        and not Path(str(artifacts[name].artifact_ref_json["cache_path"])).is_file()
    ]
    if missing_files:
        return _unavailable(
            job, "REPLAY_ARTIFACT_MISSING", f"中间产物文件已不存在：{missing_files[0]}"
        )
    now = utc_now()
    expired = [
        name
        for name in required
        if artifacts[name].status != "AVAILABLE"
        or as_utc(artifacts[name].replayable_until) <= now
    ]
    if expired:
        return _unavailable(job, "REPLAY_ARTIFACT_EXPIRED", f"中间产物已清理：{expired[0]}")
    deadline = min((as_utc(artifacts[name].replayable_until) for name in required), default=now)
    return {
        "step_replay_available": True,
        "replay_from_step": failed.step_name,
        "replayable_until": deadline,
        "remaining_seconds": max(0, round((deadline - now).total_seconds())),
        "reused_steps": reused,
        "rerun_steps": list(VIDEO_STEP_ORDER[index:]),
        "reason": None,
        "code": None,
        "prompt_changed_steps": prompt_changed_steps,
        **_login_recovery_options(job, failed.step_name),
        **full_replay_options(job),
    }


def queue_step_replay(
    db: Session, job: Job, step_name: str, source_event_id: str | None = None
) -> dict:
    options = replay_options(db, job)
    if not options["step_replay_available"]:
        raise ValueError(f'{options["code"]}:{options["reason"]}')
    if step_name != options["replay_from_step"]:
        raise ValueError("REPLAY_STEP_MISMATCH:请求步骤与服务端可续跑步骤不一致")
    if source_event_id:
        event = db.get(SystemEvent, source_event_id)
        if (
            event is None
            or event.entity_type != "job"
            or event.entity_id != job.id
            or event.level not in {"ERROR", "CRITICAL"}
            or str(event.detail_json.get("step") or job.current_step) != step_name
        ):
            raise ValueError("REPLAY_EVENT_MISMATCH:错误事件与失败步骤不一致")
    steps = {
        item.step_name: item
        for item in db.scalars(select(JobStep).where(JobStep.job_id == job.id))
    }
    start = VIDEO_STEP_ORDER.index(step_name)
    for name in VIDEO_STEP_ORDER[:start]:
        if name in steps and steps[name].status in {"COMPLETED", "REUSED"}:
            steps[name].status = "REUSED"
    for name in VIDEO_STEP_ORDER[start:]:
        if name in steps:
            steps[name].status = "PENDING"
            steps[name].progress = 0
            steps[name].error = None
            steps[name].started_at = None
            steps[name].finished_at = None
    for artifact in db.scalars(
        select(JobStepArtifact).where(JobStepArtifact.job_id == job.id)
    ):
        if artifact.step_name in VIDEO_STEP_ORDER[start:]:
            artifact.status = "INVALIDATED"
            artifact.invalidated_at = utc_now()
    job.payload_json = {
        **job.payload_json,
        "replay_from_step": step_name,
        "source_event_id": source_event_id,
    }
    job.status = JobStatus.QUEUED.value
    job.current_step = step_name
    job.progress = max(0, round(start / len(VIDEO_STEP_ORDER) * 100))
    job.error = job.error_code = None
    job.started_at = job.finished_at = job.heartbeat_at = None
    job.retry_count += 1
    record_event(
        db,
        "job.step_replay.queued",
        f"已从 {step_name} 排队续跑",
        component="api",
        actor="user",
        entity_type="job",
        entity_id=job.id,
        detail={
            "step": step_name,
            "source_event_id": source_event_id,
            "reused_steps": options["reused_steps"],
            "rerun_steps": options["rerun_steps"],
        },
        commit=False,
    )
    db.commit()
    return options


def queue_login_step_skip(db: Session, job: Job) -> dict:
    options = replay_options(db, job)
    if not options.get("login_required"):
        raise ValueError("LOGIN_SKIP_NOT_REQUIRED:当前任务不是登录失效阻塞")
    if not options.get("skip_step_available") or not options.get("replay_from_step"):
        raise ValueError(
            f'LOGIN_SKIP_UNAVAILABLE:{options.get("skip_step_reason") or "当前步骤不能跳过"}'
        )
    step_name = str(options["replay_from_step"])
    queue_step_replay(db, job, step_name)
    job.payload_json = {**job.payload_json, "skip_login_step": step_name}
    record_event(
        db,
        "job.login_step_skip.queued",
        f"用户选择跳过 {step_name} 并继续处理",
        component="api",
        actor="user",
        entity_type="job",
        entity_id=job.id,
        detail={"step": step_name},
        commit=False,
    )
    db.commit()
    return options


def _unavailable(job: Job, code: str, reason: str) -> dict:
    return {
        "step_replay_available": False,
        "replay_from_step": None,
        "replayable_until": None,
        "remaining_seconds": 0,
        "reused_steps": [],
        "rerun_steps": [],
        "reason": reason,
        "code": code,
        **_login_recovery_options(job, job.current_step),
        **full_replay_options(job),
    }


def _login_recovery_options(job: Job, step_name: str) -> dict:
    login_required = (
        job.status == JobStatus.NEEDS_USER.value and job.error_code == "VIDEO_LOGIN_REQUIRED"
    )
    skip_available = login_required and step_name in LOGIN_SKIPPABLE_STEPS
    return {
        "login_required": login_required,
        "skip_step_available": skip_available,
        "skip_step_reason": (
            None
            if skip_available
            else "该步骤是生成正文所必需的，登录后重试才能继续"
            if login_required
            else None
        ),
    }
