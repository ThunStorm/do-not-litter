"""Evaluate captured Gateway benchmark runs against the checked-in Golden samples.

This script never invokes a provider.  Operators capture real E2E runs first, then
pass their redacted metrics JSON here to produce a repeatable release-gate result.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def evaluate(samples: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {str(sample["sample_id"]): sample["expected"] for sample in samples}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sample_id = str(row.get("sample_id") or "")
        if sample_id not in expected:
            raise ValueError(f"结果包含未知 Golden sample：{sample_id}")
        groups[str(row.get("profile") or "unknown")].append(row)
    profiles = {name: _profile_summary(items, expected) for name, items in sorted(groups.items())}
    return {"profiles": profiles, "release_gate": _release_gate(profiles)}


def _profile_summary(rows: list[dict[str, Any]], expected: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def mean(key: str) -> float:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return round(sum(values) / len(values), 4) if values else 0.0

    schema_passes = [bool(row.get("schema_pass")) for row in rows]
    coverage_passes = [
        float(row.get("evidence_coverage") or 0) >= float(expected[str(row["sample_id"])].get("evidence_min_coverage", 0))
        for row in rows
    ]
    return {
        "samples": len(rows),
        "schema_pass_rate": mean("schema_pass"),
        "evidence_coverage": mean("evidence_coverage"),
        "place_recall": mean("place_recall"),
        "key_entity_recall": mean("key_entity_recall"),
        "note_coverage": mean("note_coverage"),
        "critical_hallucinations": sum(int(row.get("critical_hallucinations") or 0) for row in rows),
        "local_prompt_tokens": sum(int(row.get("local_prompt_tokens") or 0) for row in rows),
        "local_completion_tokens": sum(int(row.get("local_completion_tokens") or 0) for row in rows),
        "remote_prompt_tokens": sum(int(row.get("remote_prompt_tokens") or 0) for row in rows),
        "remote_completion_tokens": sum(int(row.get("remote_completion_tokens") or 0) for row in rows),
        "model_attempts": sum(int(row.get("model_attempts") or 0) for row in rows),
        "escalation_count": sum(int(row.get("escalation_count") or 0) for row in rows),
        "cache_hits": sum(int(row.get("cache_hits") or 0) for row in rows),
        "wall_time_ms": sum(int(row.get("wall_time_ms") or 0) for row in rows),
        "schema_all_pass": all(schema_passes),
        "evidence_all_pass": all(coverage_passes),
    }


def _release_gate(profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = profiles.get("BASELINE")
    candidate = profiles.get("CANDIDATE")
    if not baseline or not candidate:
        return {"passed": False, "reason": "需要 BASELINE 与 CANDIDATE 两组真实运行结果"}
    baseline_remote = baseline["remote_prompt_tokens"] + baseline["remote_completion_tokens"]
    candidate_remote = candidate["remote_prompt_tokens"] + candidate["remote_completion_tokens"]
    reduction = 0.0 if not baseline_remote else round((1 - candidate_remote / baseline_remote) * 100, 2)
    checks = {
        "schema": candidate["schema_pass_rate"] >= 0.95 and candidate["schema_all_pass"],
        "evidence": candidate["evidence_coverage"] >= 0.90 and candidate["evidence_all_pass"],
        "hallucination": candidate["critical_hallucinations"] == 0,
        "quality_not_lower": candidate["place_recall"] >= baseline["place_recall"]
        and candidate["key_entity_recall"] >= baseline["key_entity_recall"],
        "remote_token_reduction": reduction >= 50,
    }
    return {"passed": all(checks.values()), "checks": checks, "remote_token_reduction_percent": reduction}


def main() -> None:
    parser = argparse.ArgumentParser(description="评估已采集的 AI Gateway Golden Benchmark")
    parser.add_argument("samples", type=Path, help="Golden sample 定义 JSON")
    parser.add_argument("runs", type=Path, help="真实 E2E 采集的结果 JSON 数组")
    parser.add_argument("--output", type=Path, help="可选：写入 JSON 结果")
    args = parser.parse_args()
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    rows = json.loads(args.runs.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not isinstance(rows, list):
        raise SystemExit("samples 和 runs 均必须为 JSON 数组")
    result = evaluate(samples, rows)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
