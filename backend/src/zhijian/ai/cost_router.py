"""Deterministic first-pass routing for AUTO stages.

This is deliberately conservative: an explicit stage mode wins, and unknown
capability probes are eligible rather than silently excluding a saved model.
"""

from dataclasses import dataclass
from typing import Any

from zhijian.ai.capabilities import AICapability

LOCAL_PREFERRED_STAGES = frozenset(
    {"TRANSCRIPT_CORRECTION", "GROUND_MAP", "EXTRACT_TRAVEL_FACTS"}
)


@dataclass(frozen=True)
class RouteDecision:
    primary_id: str
    fallback_id: str
    route: str
    reason_code: str


def choose_auto_route(
    stage: str,
    capability: AICapability,
    profiles: dict[str, dict[str, Any]],
    *,
    quality_preset: str = "BALANCED",
    budget_pressure: bool = False,
) -> RouteDecision | None:
    eligible = [
        (profile_id, value)
        for profile_id, value in profiles.items()
        if value and bool(value.get("enabled", True)) and _supports(value, capability)
    ]
    local = [(profile_id, value) for profile_id, value in eligible if _location(value) == "LOCAL"]
    remote = [(profile_id, value) for profile_id, value in eligible if _location(value) == "REMOTE"]
    quality = quality_preset.upper() == "QUALITY"
    prefer_local = stage in LOCAL_PREFERRED_STAGES or budget_pressure or not quality
    if prefer_local and local:
        primary_id, _ = _best(local, capability=capability)
        fallback_id = "" if budget_pressure else (_best(remote, capability=capability)[0] if remote else "")
        return RouteDecision(
            primary_id,
            fallback_id,
            "LOCAL",
            "BUDGET_PRESSURE" if budget_pressure else "LOCAL_SUFFICIENT",
        )
    if remote:
        primary_id, value = _best(remote, strong=quality, capability=capability)
        fallback_id = _best(local, capability=capability)[0] if local and not budget_pressure else ""
        return RouteDecision(
            primary_id,
            fallback_id,
            "REMOTE_STRONG" if _tier(value) == "STRONG" else "REMOTE_FAST",
            "QUALITY_PRESET" if quality else "LOCAL_UNAVAILABLE",
        )
    if local:
        primary_id, _ = _best(local, capability=capability)
        return RouteDecision(primary_id, "", "LOCAL", "REMOTE_UNAVAILABLE")
    return None


def _location(profile: dict[str, Any]) -> str:
    default = "LOCAL" if str(profile.get("provider")).lower() == "ollama" else "REMOTE"
    return str(profile.get("location") or default).upper()


def _tier(profile: dict[str, Any]) -> str:
    return str(profile.get("quality_tier") or "MAIN").upper()


def _supports(profile: dict[str, Any], capability: AICapability) -> bool:
    capabilities = {str(item) for item in profile.get("capabilities") or []}
    probe = str((profile.get("probe_results") or {}).get(capability.value) or "NOT_TESTED").upper()
    return probe != "FAIL" and (not capabilities or capability.value in capabilities)


def _best(
    items: list[tuple[str, dict[str, Any]]],
    *,
    strong: bool = False,
    capability: AICapability,
) -> tuple[str, dict[str, Any]]:
    tiers = (
        {"STRONG": 0, "SPECIALIST": 1, "MAIN": 2, "FAST": 3}
        if strong
        else {"FAST": 0, "MAIN": 1, "STRONG": 2, "SPECIALIST": 3}
    )
    return min(
        items,
        key=lambda item: (
            0
            if str((item[1].get("probe_results") or {}).get(capability.value) or "").upper()
            == "PASS"
            else 1,
            tiers.get(_tier(item[1]), 9),
            -int(item[1].get("recommended_working_context") or 0),
            item[0],
        ),
    )
