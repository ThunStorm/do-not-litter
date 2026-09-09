"""Offline contracts and scoring for captured AI benchmark results.

This module deliberately does not invoke a provider.  Provider probes and E2E
captures feed it JSON that can be validated and compared repeatedly.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

BENCHMARK_STAGES = frozenset(
    {
        "CLASSIFY",
        "STRUCTURED_EXTRACT",
        "ENTITY_EXTRACT",
        "TRANSCRIPT_CORRECT",
        "NOTE_GENERATE",
        "PLACE_EXTRACT",
        "PLACE_INSIGHT",
        "PLACE_AGGREGATE",
        "POI_CONTEXT_RANK",
        "VISION_FACT",
    }
)
CASE_FIELDS = frozenset(
    {
        "case_id",
        "stage",
        "input_fixture",
        "expected_schema",
        "expected_entities",
        "expected_evidence",
        "forbidden_claims",
        "baseline_model",
        "tags",
    }
)
RESULT_FIELDS = frozenset(
    {
        "case_id",
        "provider",
        "model",
        "location",
        "stage",
        "schema_valid",
        "entity_recall",
        "place_recall",
        "evidence_coverage",
        "poi_top_n_candidate_recall",
        "place_insight_coverage",
        "visit_window_recall",
        "json_repair_count",
        "hallucination_count",
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "error_type",
    }
)


def validate_cases(cases: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for case in cases:
        missing = CASE_FIELDS - set(case)
        if missing:
            raise ValueError(f"Benchmark Case 缺少字段：{', '.join(sorted(missing))}")
        case_id, stage = str(case["case_id"]), str(case["stage"])
        if not case_id or case_id in seen:
            raise ValueError("每个 Benchmark Case 必须有唯一 case_id")
        if stage not in BENCHMARK_STAGES:
            raise ValueError(f"未知 Benchmark Stage：{stage}")
        if not isinstance(case["expected_schema"], dict):
            raise ValueError(f"{case_id} 的 expected_schema 必须是 JSON Schema object")
        list_fields = ("expected_entities", "expected_evidence", "forbidden_claims", "tags")
        if not all(isinstance(case[name], list) for name in list_fields):
            raise ValueError(f"{case_id} 的 entities/evidence/forbidden_claims/tags 必须是数组")
        seen.add(case_id)


def validate_results(cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    validate_cases(cases)
    case_stages = {str(case["case_id"]): str(case["stage"]) for case in cases}
    for row in rows:
        missing = RESULT_FIELDS - set(row)
        if missing:
            raise ValueError(f"Benchmark Result 缺少字段：{', '.join(sorted(missing))}")
        case_id = str(row["case_id"])
        if case_id not in case_stages:
            raise ValueError(f"结果包含未知 Benchmark Case：{case_id}")
        if str(row["stage"]) != case_stages[case_id]:
            raise ValueError(f"{case_id} 的 Stage 与 Case 不一致")
        if str(row["location"]) not in {"LOCAL", "REMOTE"}:
            raise ValueError("Benchmark Result location 必须是 LOCAL 或 REMOTE")
        for field in (
            "entity_recall",
            "place_recall",
            "evidence_coverage",
            "poi_top_n_candidate_recall",
            "place_insight_coverage",
            "visit_window_recall",
        ):
            value = float(row[field])
            if not 0 <= value <= 1:
                raise ValueError(f"{field} 必须在 0 到 1 之间")
        non_negative_fields = (
            "hallucination_count",
            "json_repair_count",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        )
        for field in non_negative_fields:
            if int(row[field]) < 0:
                raise ValueError(f"{field} 不得为负数")
        if int(row["total_tokens"]) != int(row["prompt_tokens"]) + int(row["completion_tokens"]):
            raise ValueError("total_tokens 必须等于 prompt_tokens + completion_tokens")


def summarize(cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate_results(cases, rows)
    baseline_by_stage = {str(case["stage"]): str(case["baseline_model"]) for case in cases}
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["model"]), str(row["stage"]), str(row["location"])].append(row)
    matrix = []
    for (model, stage, location), items in sorted(grouped.items()):
        schema = _mean(items, "schema_valid")
        entity_recall = _mean(items, "entity_recall")
        place_recall = _mean(items, "place_recall")
        evidence = _mean(items, "evidence_coverage")
        poi_recall = _mean(items, "poi_top_n_candidate_recall")
        insight_coverage = _mean(items, "place_insight_coverage")
        visit_window_recall = _mean(items, "visit_window_recall")
        hallucinations = sum(int(item["hallucination_count"]) for item in items)
        latencies = sorted(int(item["latency_ms"]) for item in items)
        matrix.append(
            {
                "model": model,
                "stage": stage,
                "location": location,
                "samples": len(items),
                "schema_valid_rate": schema,
                "entity_recall": entity_recall,
                "place_recall": place_recall,
                "evidence_coverage": evidence,
                "poi_top_n_candidate_recall": poi_recall,
                "place_insight_coverage": insight_coverage,
                "visit_window_recall": visit_window_recall,
                "json_repair_rate": round(
                    sum(int(item["json_repair_count"]) for item in items) / len(items), 4
                ),
                "hallucination_count": hallucinations,
                "latency_ms": round(mean(latencies), 2),
                "p95_latency_ms": latencies[max(0, int(len(latencies) * 0.95) - 1)],
                "total_tokens": sum(int(item["total_tokens"]) for item in items),
                "error_count": sum(bool(item["error_type"]) for item in items),
                "classification": "UNSUPPORTED",
            }
        )
    baselines = {stage: _find_matrix(matrix, model, stage) for stage, model in baseline_by_stage.items()}
    for item in matrix:
        baseline = baselines[item["stage"]]
        checks = {
            "schema": item["schema_valid_rate"] >= 0.95,
            "evidence": item["evidence_coverage"] >= 0.90,
            "hallucination": item["hallucination_count"] == 0,
            "errors": item["error_count"] == 0,
            "entity_recall": baseline is None or item["entity_recall"] >= baseline["entity_recall"],
            "place_recall": baseline is None or item["place_recall"] >= baseline["place_recall"],
            "poi_top_n_candidate_recall": baseline is None
            or item["poi_top_n_candidate_recall"] >= baseline["poi_top_n_candidate_recall"],
            "place_insight_coverage": baseline is None
            or item["place_insight_coverage"] >= baseline["place_insight_coverage"],
            "visit_window_recall": baseline is None
            or item["visit_window_recall"] >= baseline["visit_window_recall"],
            "json_repair_rate": baseline is None
            or item["json_repair_rate"] <= baseline["json_repair_rate"],
        }
        quality_ok = all(checks.values())
        item["quality_gate"] = checks
        if quality_ok:
            item["classification"] = "RECOMMENDED" if item["location"] == "LOCAL" else "ACCEPTABLE"
        elif item["error_count"] == item["samples"]:
            item["classification"] = "UNSUPPORTED"
        else:
            item["classification"] = "REMOTE_PREFERRED"
    candidates = [item for item in matrix if item["location"] == "LOCAL"]
    return {
        "matrix": matrix,
        "release_gate": {
            "passed": bool(candidates)
            and all(item["classification"] == "RECOMMENDED" for item in candidates),
            "candidates": [{"model": item["model"], "stage": item["stage"]} for item in candidates],
        },
        "recommendations": _recommend(matrix, baseline_by_stage),
    }


def _mean(rows: list[dict[str, Any]], field: str) -> float:
    return round(mean(float(row[field]) for row in rows), 4)


def _find_matrix(matrix: list[dict[str, Any]], model: str, stage: str) -> dict[str, Any] | None:
    return next((item for item in matrix if item["model"] == model and item["stage"] == stage), None)


def _recommend(matrix: list[dict[str, Any]], baseline_by_stage: dict[str, str]) -> dict[str, dict[str, Any]]:
    recommendations: dict[str, dict[str, Any]] = {}
    for stage, baseline in sorted(baseline_by_stage.items()):
        local = [
            item for item in matrix if item["stage"] == stage and item["classification"] == "RECOMMENDED"
        ]
        if local:
            chosen = min(local, key=lambda item: (item["latency_ms"], item["total_tokens"]))
            recommendations[stage] = {
                "recommended": chosen["model"],
                "fallback": baseline,
                "mode": "LOCAL_FIRST",
                "reason": ["达到质量门禁；延迟与 Token 只作排序依据"],
            }
        else:
            recommendations[stage] = {
                "recommended": baseline,
                "fallback": None,
                "mode": "REMOTE_FIRST",
                "reason": ["没有达到门槛的本地结果"],
            }
    return recommendations
