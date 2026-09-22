"""Validate recorded production-graduation evidence without invoking services."""

from __future__ import annotations

from typing import Any


def graduation_gate(evidence: dict[str, Any]) -> dict[str, Any]:
    videos = evidence.get("real_videos") if isinstance(evidence.get("real_videos"), list) else []
    covered = {int(item.get("duration_minutes") or 0) for item in videos if item.get("passed") is True}
    replay = set(evidence.get("replay_checks") or [])
    providers = set(evidence.get("provider_checks") or [])
    asr = evidence.get("asr") or {}
    quality = evidence.get("quality") or {}
    baseline = evidence.get("baseline") or {}
    candidate = evidence.get("candidate") or {}

    def number(values: dict, key: str) -> float:
        return float(values.get(key) or 0)

    checks = {
        "fixture": bool((evidence.get("fixture") or {}).get("passed")),
        "real_videos": {10, 30, 60}.issubset(covered),
        "replay": {"same_profile", "different_profile", "force_regenerate", "step_replay"}.issubset(replay),
        "provider": {"LOCAL", "REMOTE", "FALLBACK", "TIMEOUT", "INVALID_JSON"}.issubset(providers),
        "asr": (
            number(asr, "qwen_failures") <= number(asr, "whisper_failures")
            and number(asr, "qwen_place_recall") >= number(asr, "whisper_place_recall")
            and number(asr, "qwen_proper_noun_accuracy")
            >= number(asr, "whisper_proper_noun_accuracy")
            and bool(asr.get("timestamps_passed"))
            and bool(asr.get("long_form_passed"))
            and not bool(asr.get("oom"))
        ),
        "quality": (
            number(quality, "critical_hallucinations") == 0
            and number(quality, "timestamp_mutations") == 0
            and number(quality, "segment_identity_mutations") == 0
            and number(quality, "wrong_auto_confirms") == 0
            and number(quality, "place_recall") >= number(quality, "baseline_place_recall")
            and number(quality, "evidence_coverage") >= number(quality, "baseline_evidence_coverage")
        ),
        "token": (
            number(baseline, "prompt_tokens") > 0
            and number(candidate, "prompt_tokens") <= number(baseline, "prompt_tokens") * 0.7
            and number(candidate, "note_profile_prompt_tokens")
            <= number(baseline, "note_profile_prompt_tokens") * 0.3
            and number(candidate, "unchanged_replay_tokens")
            <= max(10, number(baseline, "prompt_tokens") * 0.01)
        ),
        "performance": (
            number(candidate, "time_to_first_useful_note_ms")
            < number(baseline, "time_to_first_useful_note_ms")
            and number(candidate, "amap_requests") <= number(baseline, "amap_requests")
            and number(candidate, "screenshot_processes") < number(baseline, "screenshot_processes")
            and number(candidate, "retries") <= number(baseline, "retries")
            and number(candidate, "fallbacks") <= number(baseline, "fallbacks")
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}
