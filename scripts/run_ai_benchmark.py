"""Evaluate captured Gateway benchmark runs against the checked-in Golden samples.

This script never invokes a provider.  Operators capture real E2E runs first, then
pass their redacted metrics JSON here to produce a repeatable release-gate result.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.ai.benchmark import summarize as summarize_standard


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


def evaluate_cases(cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate formal per-case rows without calling a model or reading a database."""
    return summarize_standard(cases, rows)


def write_run(output_root: Path, cases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> Path:
    """Write the portable comparison bundle required by the Benchmark contract."""
    run_dir = output_root / f"run-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True)
    summary = evaluate_cases(cases, rows)
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "result_count": len(rows),
        "notice": "离线汇总；不会调用 Provider、下载视频或修改路由。",
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (run_dir / "raw-results.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    return run_dir


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# AI Benchmark Summary",
        "",
        "| Model | Stage | Schema | Entity | Place | Evidence | POI Top-N | Insight | Visit window | Avg/P95 latency | Result |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["matrix"]:
        lines.append(
            "| {model} | {stage} | {schema_valid_rate:.0%} | {entity_recall:.0%} | "
            "{place_recall:.0%} | {evidence_coverage:.0%} | {poi_top_n_candidate_recall:.0%} | "
            "{place_insight_coverage:.0%} | {visit_window_recall:.0%} | "
            "{latency_ms:.0f}/{p95_latency_ms} ms | {classification} |".format(
                **item
            )
        )
    lines += ["", "## Stage routing recommendation", "", "```json", json.dumps(summary["recommendations"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="评估已采集的 AI Gateway Golden Benchmark")
    parser.add_argument("samples", type=Path, help="Golden sample 定义 JSON")
    parser.add_argument("runs", type=Path, help="已采集的结果 JSON 数组")
    parser.add_argument("--output", type=Path, help="可选：写入 JSON 结果")
    parser.add_argument("--output-dir", type=Path, help="正式 Benchmark 运行包目录")
    args = parser.parse_args()
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    rows = json.loads(args.runs.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not isinstance(rows, list):
        raise SystemExit("samples 和 runs 均必须为 JSON 数组")
    formal_cases = bool(samples and isinstance(samples[0], dict) and "case_id" in samples[0])
    if formal_cases:
        if args.output_dir:
            run_dir = write_run(args.output_dir, samples, rows)
            result = {"run_dir": str(run_dir), **evaluate_cases(samples, rows)}
        else:
            result = evaluate_cases(samples, rows)
    else:
        if args.output_dir:
            raise SystemExit("--output-dir 只接受正式 Benchmark Case（需要 case_id）")
        result = evaluate(samples, rows)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
