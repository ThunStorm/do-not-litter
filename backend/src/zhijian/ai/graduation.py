"""Validate recorded production-graduation evidence without invoking services."""

from __future__ import annotations

from typing import Any


def graduation_gate(evidence: dict[str, Any]) -> dict[str, Any]:
    videos = evidence.get("real_videos") if isinstance(evidence.get("real_videos"), list) else []
    covered = {int(item.get("duration_minutes") or 0) for item in videos if item.get("passed") is True}
    replay = set(evidence.get("replay_checks") or [])
    providers = set(evidence.get("provider_checks") or [])
    checks = {
        "fixture": bool((evidence.get("fixture") or {}).get("passed")),
        "real_videos": {10, 30, 60}.issubset(covered),
        "replay": {"same_profile", "different_profile", "force_regenerate", "step_replay"}.issubset(replay),
        "provider": {"LOCAL", "REMOTE", "FALLBACK", "TIMEOUT", "INVALID_JSON"}.issubset(providers),
    }
    return {"passed": all(checks.values()), "checks": checks}
