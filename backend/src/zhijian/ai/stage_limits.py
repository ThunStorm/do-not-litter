"""Pure limit resolution shared by settings preview and execution."""

from zhijian.ai.job_config import EXECUTION_KEY, SNAPSHOT_KEY

LIMITS_POLICY_VERSION = 2


def limits_policy_version(job) -> int:
    if job is None:
        return LIMITS_POLICY_VERSION
    payload = job.payload_json or {}
    for key in (EXECUTION_KEY, SNAPSHOT_KEY):
        config = payload.get(key)
        if isinstance(config, dict):
            return int(config.get("limits_policy_version") or 1)
    return 1


def request_timeout(
    profile: float,
    stage: float | None,
    correction: float | None = None,
    version: int = LIMITS_POLICY_VERSION,
) -> dict:
    if version < 2:
        return {
            "seconds": min(v for v in (profile, stage, correction) if v is not None),
            "source": "LEGACY_MINIMUM",
        }
    if stage is not None:
        return {"seconds": stage, "source": "STAGE_POLICY"}
    if correction is not None and correction < profile:
        return {"seconds": correction, "source": "LEGACY_TRANSCRIPT"}
    return {"seconds": profile, "source": "MODEL_PROFILE"}


def correction_batch_limits(policy, processing, version: int = LIMITS_POLICY_VERSION) -> tuple[int, int]:
    if version < 2:
        return processing.chunk_chars, processing.batch_size
    return int(policy.chunk_size or processing.chunk_chars), int(policy.batch_size or processing.batch_size)


def preview_stage_limits(policy, profiles, routing, processing, job_wall: int, chunk_default: int) -> dict:
    from zhijian.ai.job_config import stage_profile_ids
    from zhijian.ai.model_registry import profile_supports_capability
    from zhijian.ai.policies import resolve_stage_policy

    resolved = resolve_stage_policy(policy.stage, job_override=policy.model_dump(exclude_none=True))
    values = {"model-routing": routing, **{f"model-profile:{k}": v for k, v in profiles.items()}}
    candidates = stage_profile_ids(
        values, {policy.stage: resolved.model_dump(exclude={"sources"})}, (policy.stage,)
    )
    order = list(
        dict.fromkeys(
            [
                resolved.local_profile_id,
                resolved.remote_profile_id,
                routing.get("primary_id"),
                routing.get("fallback_id"),
            ]
        )
    )
    candidates = [
        profile_id
        for profile_id in order
        if profile_id in candidates
        and profile_supports_capability(
            profiles[profile_id],
            resolved.capability.value,
            allow_unverified=resolved.allow_unverified_model,
            explicitly_selected=profile_id in {resolved.local_profile_id, resolved.remote_profile_id}
            or (
                policy.stage in {"NOTE_REDUCE", "GENERATE_AI_NOTE"}
                and resolved.execution_mode != "AUTO"
                and profile_id == routing.get("primary_id")
            ),
        )
    ]
    if resolved.execution_mode in {"LOCAL_ONLY", "REMOTE_ONLY"}:
        candidates = candidates[:1]
    timeouts = []
    for profile_id in candidates:
        profile = profiles[profile_id]
        limit = request_timeout(
            float(profile.get("timeout_seconds") or 300),
            resolved.timeout_seconds,
            processing.timeout_seconds if policy.stage == "TRANSCRIPT_CORRECTION" else None,
        )
        timeouts.append(
            {
                "profile_id": profile_id,
                "name": profile.get("name") or profile.get("model"),
                **limit,
                "initial_ceiling_seconds": min(
                    limit["seconds"], resolved.wall_time_seconds or job_wall, job_wall
                ),
            }
        )
    chunk_chars, batch_size = None, None
    if policy.stage == "TRANSCRIPT_CORRECTION":
        chunk_chars, batch_size = correction_batch_limits(resolved, processing)
    elif policy.stage in {"GROUND_MAP", "GENERATE_AI_NOTE", "EXTRACT_TRAVEL_FACTS"}:
        chunk_chars = resolved.chunk_size or chunk_default
    elif policy.stage == "NOTE_REDUCE":
        chunk_chars = resolved.chunk_size
    return {
        "limits_policy_version": LIMITS_POLICY_VERSION,
        "request_timeouts": timeouts,
        "wall_time_seconds": resolved.wall_time_seconds,
        "job_wall_time_seconds": job_wall,
        "chunk_chars": chunk_chars,
        "batch_size": batch_size,
    }
