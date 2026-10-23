"""Secret-free submission intent and per-run execution settings."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import Job, Setting

SNAPSHOT_KEY = "ai_submission_config"
RECOVERY_KEY = "ai_recovery_config"
EXECUTION_KEY = "ai_execution_config"
PENDING_EXECUTION_KEY = "ai_pending_execution_config"
EXECUTION_HISTORY_KEY = "ai_execution_history"
_SETTING_KEYS = {"model-routing", "app:general", "prompt:supplements", "transcript-processing"}
_SETTING_PREFIXES = ("model-profile:", "ai-stage-policy:", "ai-domain-pack:")
_SECRET_FIELDS = {"api_key", "secret", "token", "password", "cookie", "authorization"}
ASR_DEFAULT_KEY = "asr:default"
ASR_PROVIDERS = {"WHISPER_CPP", "QWEN3_ASR"}
TEXT_STAGES = (
    "TRANSCRIPT_CORRECTION",
    "GROUND_MAP",
    "NOTE_REDUCE",
    "GENERATE_AI_NOTE",
    "EXTRACT_TRAVEL_FACTS",
)
_PROFILE_RUNTIME_FIELDS = {
    "temperature",
    "probe_results",
    "business_assessments",
    "interface_capabilities",
    "supports_json_mode",
    "timeout_seconds",
    "request_interval_seconds",
    "max_concurrency",
    "retry_count",
    "json_retry_count",
    "rate_limit_rpm",
    "reliability_mode",
    "circuit_breaker_enabled",
    "circuit_breaker_threshold",
    "circuit_breaker_cooldown_seconds",
    "max_output_tokens",
    "context_window",
    "recommended_working_context",
    "supports_json_schema",
    "supports_thinking",
    "supports_tools",
}
_GENERAL_RUNTIME_FIELDS = {
    "ai_retry_count",
    "ai_retry_wait_seconds",
    "ai_request_interval_seconds",
    "ai_json_retry_count",
}


def _uses_global_pool(policy: dict) -> bool:
    slots = {
        "LOCAL_ONLY": ("local_profile_id",),
        "REMOTE_ONLY": ("remote_profile_id",),
    }.get(policy.get("execution_mode"), ("local_profile_id", "remote_profile_id"))
    return any(not policy.get(slot) for slot in slots)


def profile_identity(value: dict[str, Any]) -> tuple:
    from zhijian.ai.model_registry import model_connection_type

    provider = str(value.get("provider") or "").strip().lower()
    return (
        provider,
        str(value.get("model") or ""),
        str(value.get("base_url") or "").rstrip("/"),
        model_connection_type(value),
        str(value.get("location") or ("LOCAL" if provider == "ollama" else "REMOTE")),
    )


def stage_profile_ids(values: dict, overrides: dict, stages=TEXT_STAGES) -> set[str]:
    """Select configured candidates without opening clients or invoking inference."""
    from zhijian.ai.model_registry import business_probe_status
    from zhijian.ai.policies import resolve_stage_policy

    routing = values.get("model-routing") or {}
    global_ids = {str(routing.get(key) or "") for key in ("primary_id", "fallback_id")}
    result = set()
    for stage in stages:
        policy = resolve_stage_policy(
            stage, saved=values.get(f"ai-stage-policy:{stage}"), job_override=overrides.get(stage)
        )
        mode = policy.execution_mode
        for field, location in (("local_profile_id", "LOCAL"), ("remote_profile_id", "REMOTE")):
            if mode == "LOCAL_ONLY" and location != "LOCAL" or mode == "REMOTE_ONLY" and location != "REMOTE":
                continue
            explicit = getattr(policy, field)
            candidates = {explicit} if explicit else global_ids
            for profile_id in candidates:
                profile = values.get(f"model-profile:{profile_id}") or {}
                if not profile_id or profile_identity(profile)[-1] != location:
                    continue
                if (
                    explicit
                    or not values.get(f"ai-stage-policy:{stage}")
                    or policy.capability.value in profile.get("capabilities", [])
                    or (
                        stage in {"NOTE_REDUCE", "GENERATE_AI_NOTE"}
                        and (
                            business_probe_status(profile, "GLOBAL_SYNTHESIS") == "PASS"
                            or (
                                mode != "AUTO"
                                and profile_id == routing.get("primary_id")
                                and location == ("REMOTE" if mode.startswith("REMOTE") else "LOCAL")
                            )
                        )
                    )
                ):
                    result.add(profile_id)
        if mode in {"LOCAL_FIRST", "REMOTE_FIRST", "AUTO"}:
            result.update(
                profile_id
                for profile_id in global_ids
                if profile_id
                and policy.capability.value
                in (values.get(f"model-profile:{profile_id}") or {}).get("capabilities", [])
            )
    return result


def validate_job_interfaces(values: dict, overrides: dict, stages=TEXT_STAGES) -> None:
    from zhijian.ai.interface_contract import InterfaceCapabilities, router_payload
    from zhijian.ai.model_registry import model_connection_type

    for stage in stages:
        for profile_id in stage_profile_ids(values, overrides, (stage,)):
            profile = values.get(f"model-profile:{profile_id}") or {}
            if model_connection_type(profile) != "LOCAL_ROUTER":
                continue
            capability = profile.get("interface_capabilities")
            router_payload(
                InterfaceCapabilities.model_validate(capability) if capability else None,
                str(profile.get("base_url") or ""),
                str(profile.get("model") or ""),
                [{"role": "system", "content": "保留任务规则"}, {"role": "user", "content": "配置检查"}],
                json_mode=True,
                temperature=None,
                max_output_tokens=None,
            )


def build_execution_config(
    db: Session,
    job: Job,
    *,
    recovery: dict | None = None,
    recovery_overrides: dict | None = None,
    full: bool = False,
    stages: tuple[str, ...] | None = None,
) -> dict | None:
    """Freeze latest necessary settings; never mutate submission intent or Job state."""
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY)
    if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        return None  # Legacy jobs do not acquire a fabricated submission snapshot.
    values = deepcopy(snapshot.get("settings") or {})
    for key in values:
        if key.startswith("model-profile:"):
            values[key] = secret_free_model_profile(values[key])
    for key in ("app:general", "transcript-processing"):
        values.setdefault(key, {})
    effective_recovery = (
        recovery if recovery is not None else ({} if full else job.payload_json.get(RECOVERY_KEY) or {})
    )
    values.update(deepcopy(effective_recovery.get("settings") or {}))
    overrides = deepcopy(job.payload_json.get("ai_overrides") or {})
    if not full:
        for stage, override in (
            recovery_overrides
            if recovery_overrides is not None
            else job.payload_json.get("ai_recovery_overrides") or {}
        ).items():
            overrides[stage] = {**overrides.get(stage, {}), **override}
    stages = (
        stages
        if stages is not None
        else (
            *TEXT_STAGES,
            *(key.removeprefix("ai-stage-policy:") for key in values if key.startswith("ai-stage-policy:")),
        )
    )
    profile_ids = stage_profile_ids(values, overrides, stages)
    changes = []
    sources = {}
    execution_values = {}
    for key, original in list(values.items()):
        if key.startswith("model-profile:"):
            if key.removeprefix("model-profile:") not in profile_ids:
                continue
            fields = _PROFILE_RUNTIME_FIELDS
        elif key.startswith("ai-stage-policy:"):
            from zhijian.ai.schemas import AIStagePolicy

            fields = set(AIStagePolicy.model_fields) - {
                "stage",
                "capability",
                "execution_mode",
                "local_profile_id",
                "remote_profile_id",
                "version",
                "domain",
                "domain_pack_ids",
            }
        elif key == "app:general":
            fields = _GENERAL_RUNTIME_FIELDS
        elif key == "transcript-processing":
            fields = {"chunk_chars", "batch_size", "timeout_seconds"}
        else:
            continue
        row = db.get(Setting, key)
        current = secret_free_model_profile(row.value_json or {}) if row else {}
        if key.startswith("model-profile:"):
            if not row or not current.get("enabled", True):
                raise ValueError("REPLAY_MODEL_UNAVAILABLE:原任务模型已删除或禁用，请恢复该模型后重跑")
            if profile_identity(original) != profile_identity(current):
                raise ValueError(
                    "REPLAY_MODEL_IDENTITY_CHANGED:原任务模型身份已改变，不能自动切换；请恢复原模型或新建任务"
                )
        elif key.startswith("ai-stage-policy:") and any(
            original.get(field) != current.get(field)
            for field in ("execution_mode", "local_profile_id", "remote_profile_id")
        ):
            continue  # A different current route's runtime options are not this model's settings.
        elif key.startswith("ai-stage-policy:") and (
            _uses_global_pool(original)
            and (values.get("model-routing") or {})
            != ((routing.value_json or {}) if (routing := db.get(Setting, "model-routing")) else {})
        ):
            continue  # Empty stage slots belong to their submission-time global model pool.
        if not row:
            continue
        sources[key] = row.updated_at.isoformat()
        merged = deepcopy(original)
        changed_fields = []
        for field in fields:
            if original.get(field) != current.get(field):
                changed_fields.append(field)
            if field in current:
                merged[field] = deepcopy(current[field])
            else:
                merged.pop(field, None)
        values[key] = merged
        execution_values[key] = merged
        if changed_fields:
            changes.append({"setting": key, "fields": sorted(changed_fields)})
    from zhijian.ai.reliability import AIProviderError

    try:
        validate_job_interfaces(values, overrides, tuple(stage for stage in stages if stage in TEXT_STAGES))
    except AIProviderError as exc:
        raise ValueError(f"{exc.code}:{exc}") from exc
    version = (
        max(
            int((job.payload_json.get(key) or {}).get("revision") or 0)
            for key in (EXECUTION_KEY, PENDING_EXECUTION_KEY)
        )
        + 1
    )
    fingerprint = hashlib.sha256(
        json.dumps(
            {"settings": values, "limits_policy_version": 2}, sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()
    return {
        "version": 1,
        "limits_policy_version": 2,
        "revision": version,
        "sampled_at": utc_now().isoformat(),
        "settings": execution_values,
        "sources": sources,
        "changes": changes,
        "fingerprint": fingerprint,
    }


def execution_config_summary(config: dict | None) -> dict:
    return {
        key: deepcopy(config[key])
        for key in ("revision", "fingerprint", "changes")
        if config and key in config
    }


def install_execution_config(job: Job, config: dict | None) -> None:
    if not config:
        return
    previous = (job.payload_json or {}).get(EXECUTION_KEY)
    history = list((job.payload_json or {}).get(EXECUTION_HISTORY_KEY) or [])
    if previous and previous != config:
        history.append(deepcopy(previous))
    job.payload_json = {**job.payload_json, EXECUTION_KEY: config, EXECUTION_HISTORY_KEY: history}


def default_asr_provider(db: Session, settings: Settings) -> str:
    row = db.get(Setting, ASR_DEFAULT_KEY)
    provider = (row.value_json or {}).get("provider") if row else None
    return provider if provider in ASR_PROVIDERS else settings.default_asr_provider


def capture_ai_config(db: Session, settings: Settings) -> dict[str, Any]:
    rows = db.scalars(
        select(Setting).where(
            or_(
                Setting.key.in_(_SETTING_KEYS),
                *(Setting.key.like(f"{prefix}%") for prefix in _SETTING_PREFIXES),
            )
        )
    ).all()
    values: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row.value_json, dict):
            continue
        value = deepcopy(row.value_json)
        if row.key.startswith("model-profile:"):
            value = secret_free_model_profile(value)
        values[row.key] = value
    return {
        "version": 1,
        "settings": values,
        "limits_policy_version": 2,
        "default_asr_provider": default_asr_provider(db, settings),
        "video_note_chunk_chars": settings.video_note_chunk_chars,
    }


def secret_free_model_profile(value: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(item) for key, item in value.items() if key.lower() not in _SECRET_FIELDS}


def job_setting(db: Session, key: str, job: Job | None = None) -> dict[str, Any]:
    execution = (job.payload_json or {}).get(EXECUTION_KEY) if job else None
    execution_values = execution.get("settings") if isinstance(execution, dict) else None
    if isinstance(execution_values, dict) and key in execution_values:
        value = execution_values[key]
        return deepcopy(value) if isinstance(value, dict) else {}
    recovery = (job.payload_json or {}).get(RECOVERY_KEY) if job else None
    recovery_values = recovery.get("settings") if isinstance(recovery, dict) else None
    if isinstance(recovery_values, dict) and key in recovery_values:
        value = recovery_values[key]
        return deepcopy(value) if isinstance(value, dict) else {}
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY) if job else None
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        values = snapshot.get("settings")
        value = values.get(key) if isinstance(values, dict) else None
    else:
        row = db.get(Setting, key)
        value = row.value_json if row else None
    return deepcopy(value) if isinstance(value, dict) else {}


def latest_profile_assessment(db: Session, profile_id: str, frozen: dict) -> tuple[dict, dict]:
    """Use committed assessments for this identity, without replacing execution intent."""
    # A fresh connection avoids both the ORM identity cache and an old read transaction.
    with db.get_bind().connect() as connection:
        row = connection.execute(
            select(Setting.value_json, Setting.updated_at).where(Setting.key == f"model-profile:{profile_id}")
        ).first()
    metadata = {"profile_id": profile_id, "checked_at": utc_now().isoformat()}
    if row is None or profile_identity(frozen) != profile_identity(row.value_json or {}):
        # Never borrow another model's assessment. Existing in-flight submission
        # semantics remain frozen; replay still rejects changed/deleted identities.
        return frozen, {**metadata, "source": "SNAPSHOT_IDENTITY_UNAVAILABLE"}
    current = row.value_json or {}
    result = deepcopy(frozen)
    for key in ("probe_results", "business_assessments"):
        result[key] = deepcopy(current.get(key) or ({} if key == "probe_results" else []))
    result["enabled"] = bool(current.get("enabled", True))
    metadata.update(
        {
            "source": "CURRENT_SAVED",
            "updated_at": row.updated_at.isoformat(),
            "assessment_hash": hashlib.sha256(
                json.dumps(
                    {key: result[key] for key in ("probe_results", "business_assessments")},
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode()
            ).hexdigest(),
        }
    )
    return result, metadata


def job_stage_override(job: Job | None, stage: str) -> dict[str, Any] | None:
    if job is None:
        return None
    submitted = (job.payload_json.get("ai_overrides") or {}).get(stage) or {}
    recovery = (job.payload_json.get("ai_recovery_overrides") or {}).get(stage) or {}
    merged = {**submitted, **recovery}
    return merged or None


def job_video_note_chunk_chars(job: Job | None, default: int) -> int:
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY) if job else None
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        return int(snapshot.get("video_note_chunk_chars") or default)
    return default


def job_asr_provider(job: Job, settings: Settings) -> str:
    provider = (job.payload_json or {}).get("asr_provider")
    if provider in ASR_PROVIDERS:
        return provider
    snapshot = (job.payload_json or {}).get(SNAPSHOT_KEY)
    if isinstance(snapshot, dict) and snapshot.get("version") == 1:
        provider = snapshot.get("default_asr_provider")
        if provider in ASR_PROVIDERS:
            return provider
    return settings.default_asr_provider
