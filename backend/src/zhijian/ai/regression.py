"""Offline regression gate for token reductions without quality trade-offs."""

from __future__ import annotations

from typing import Any


def pipeline_regression_gate(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    def metric(values: dict[str, Any], key: str) -> float:
        return float(values.get(key) or 0)

    def tokens(values: dict[str, Any]) -> int:
        return sum(
            int(values.get(key) or 0)
            for key in (
                "local_prompt_tokens",
                "local_completion_tokens",
                "remote_prompt_tokens",
                "remote_completion_tokens",
            )
        )

    baseline_tokens, candidate_tokens = tokens(baseline), tokens(candidate)
    quality_improved = any(
        metric(candidate, key) >= metric(baseline, key) + 0.02
        for key in ("place_recall", "key_entity_recall", "evidence_coverage", "note_coverage")
    )
    checks = {
        "token_growth": candidate_tokens <= baseline_tokens * 1.15 or quality_improved,
        "evidence": metric(candidate, "evidence_coverage") >= metric(baseline, "evidence_coverage"),
        "place_recall": metric(candidate, "place_recall") >= metric(baseline, "place_recall"),
        "hallucination": metric(candidate, "critical_hallucinations")
        <= metric(baseline, "critical_hallucinations"),
        "auto_confirm_precision": metric(candidate, "wrong_confirm_count") == 0,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "baseline_total_tokens": baseline_tokens,
        "candidate_total_tokens": candidate_tokens,
        "token_change_percent": (
            0.0 if not baseline_tokens else round((candidate_tokens / baseline_tokens - 1) * 100, 2)
        ),
    }
