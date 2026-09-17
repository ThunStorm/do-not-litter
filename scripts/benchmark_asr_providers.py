"""Score captured local-ASR samples; it never invokes an ASR engine itself."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REQUIRED_CATEGORIES = {
    "MANDARIN_TRAVEL",
    "RAPID_PLACES",
    "PROPER_NOUNS",
    "BACKGROUND_MUSIC",
    "MULTI_SPEAKER",
    "LONG_FORM",
}
PRIMARY_PROVIDERS = {
    "WHISPER_CPP_BASE",
    "WHISPER_CPP_LARGE_V3_TURBO_Q5",
    "SENSEVOICE_SHERPA_ONNX_INT8",
    "QWEN3_ASR_MLX_0_6B",
}


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate captured rows without making a production-selection claim."""
    primary_rows = [row for row in rows if str(row.get("benchmark_mode") or "DEFAULT") == "DEFAULT"]
    categories = {str(row.get("category") or "") for row in primary_rows}
    missing = sorted(REQUIRED_CATEGORIES - categories)
    if missing:
        raise ValueError(f"ASR Benchmark 缺少场景：{'、'.join(missing)}")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary_rows:
        groups[str(row.get("provider") or "")].append(row)
    providers = {provider: _summary(values) for provider, values in sorted(groups.items())}
    for provider, values in providers.items():
        provider_categories = {str(row.get("category") or "") for row in groups[provider]}
        values["missing_categories"] = sorted(REQUIRED_CATEGORIES - provider_categories)
    _add_weighted_scores(providers)
    qwen_context = _qwen_context_summary(rows)
    return {
        "providers": providers,
        "qwen_context": qwen_context,
        "recommendation": _recommend(providers, qwen_context),
        "production_eligible": False,
        "notice": "离线 Benchmark 不替代人工 Ground Truth、完整真实视频回放或默认 Provider 切换验收。",
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    entity_expected = entity_matches = proper_expected = proper_matches = 0
    number_expected = number_matches = false_hotwords = 0
    values: dict[str, list[float]] = defaultdict(list)
    peak_memory: list[int] = []
    alignment_memory: list[int] = []
    failures = 0
    for row in rows:
        expected = {str(value) for value in row.get("expected_entities", [])}
        actual = {str(value) for value in row.get("actual_entities", [])}
        entity_expected += len(expected)
        entity_matches += len(expected & actual)
        if row.get("category") == "PROPER_NOUNS":
            proper_expected += len(expected)
            proper_matches += len(expected & actual)
        expected_numbers = {str(value) for value in row.get("expected_numbers", [])}
        actual_numbers = {str(value) for value in row.get("actual_numbers", [])}
        number_expected += len(expected_numbers)
        number_matches += len(expected_numbers & actual_numbers)
        false_hotwords += len(row.get("false_hotword_insertions", []))
        for key in (
            "timestamp_alignment",
            "runtime_ms",
            "cer",
            "segment_coverage",
            "hallucination_rate",
            "long_form_drift_ms",
            "rtf",
            "model_load_ms",
            "first_run_ms",
            "warm_run_ms",
            "alignment_runtime_ms",
        ):
            if row.get(key) is not None:
                values[key].append(float(row[key]))
        if row.get("peak_memory_bytes") is not None:
            peak_memory.append(int(row["peak_memory_bytes"]))
        if row.get("alignment_peak_memory_bytes") is not None:
            alignment_memory.append(int(row["alignment_peak_memory_bytes"]))
        failures += int(bool(row.get("failed")))
    return {
        "samples": len(rows),
        "place_entity_recall": _ratio(entity_matches, entity_expected),
        "proper_noun_accuracy": _ratio(proper_matches, proper_expected),
        "number_accuracy": _ratio(number_matches, number_expected),
        "timestamp_alignment": _mean(values["timestamp_alignment"]),
        "runtime_ms": round(sum(values["runtime_ms"])),
        "cer": _mean(values["cer"]),
        "segment_coverage": _mean(values["segment_coverage"]),
        "hallucination_rate": _mean(values["hallucination_rate"]),
        "long_form_drift_ms": _mean(values["long_form_drift_ms"]),
        "rtf": _mean(values["rtf"]),
        "model_load_ms": _mean(values["model_load_ms"]),
        "first_run_ms": _mean(values["first_run_ms"]),
        "warm_run_ms": _mean(values["warm_run_ms"]),
        "alignment_runtime_ms": _mean(values["alignment_runtime_ms"]),
        "peak_memory_bytes": max(peak_memory) if peak_memory else None,
        "alignment_peak_memory_bytes": max(alignment_memory) if alignment_memory else None,
        "false_hotword_insertions": false_hotwords,
        "failure_count": failures,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _add_weighted_scores(providers: dict[str, dict[str, Any]]) -> None:
    rtfs = [value["rtf"] for value in providers.values() if value["rtf"] is not None]
    memories = [value["peak_memory_bytes"] for value in providers.values() if value["peak_memory_bytes"]]
    fastest_rtf = min(rtfs) if rtfs else None
    lowest_memory = min(memories) if memories else None
    for value in providers.values():
        cer = value["cer"] if value["cer"] is not None else 1.0
        hallucination_rate = value["hallucination_rate"] if value["hallucination_rate"] is not None else 1.0
        resource_parts: list[float] = []
        if fastest_rtf is not None and value["rtf"] is not None:
            resource_parts.append(min(1.0, fastest_rtf / max(value["rtf"], 0.0001)))
        if lowest_memory is not None and value["peak_memory_bytes"]:
            resource_parts.append(min(1.0, lowest_memory / value["peak_memory_bytes"]))
        resource = sum(resource_parts) / len(resource_parts) if resource_parts else 0.0
        value["weighted_score"] = round(
            0.30 * value["place_entity_recall"]
            + 0.20 * value["proper_noun_accuracy"]
            + 0.15 * (value["segment_coverage"] or 0)
            + 0.15 * (1 - cer)
            + 0.10 * (value["timestamp_alignment"] or 0)
            + 0.05 * (1 - hallucination_rate)
            + 0.05 * resource,
            4,
        )


def _qwen_context_summary(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    qwen_rows = [row for row in rows if row.get("provider") == "QWEN3_ASR_MLX_0_6B"]
    with_context = [row for row in qwen_rows if row.get("benchmark_mode") == "WITH_CONTEXT"]
    without_context = [row for row in qwen_rows if row.get("benchmark_mode") == "DEFAULT"]
    if not with_context or not without_context:
        return None
    baseline = _summary(without_context)
    contextual = _summary(with_context)
    return {
        "without_context": baseline,
        "with_context": contextual,
        "context_gain": round(contextual["place_entity_recall"] - baseline["place_entity_recall"], 4),
    }


def _recommend(providers: dict[str, dict[str, Any]], qwen_context: dict[str, Any] | None) -> dict[str, Any]:
    missing = sorted(PRIMARY_PROVIDERS - set(providers))
    incomplete = {
        provider: value["missing_categories"]
        for provider, value in providers.items()
        if value["missing_categories"]
    }
    if missing or incomplete:
        return {
            "status": "INCOMPLETE",
            "decision": None,
            "reason": "四个必测 Provider 均须覆盖六类场景后才可给出候选建议。",
            "missing_providers": missing,
            "incomplete_providers": incomplete,
        }
    baseline = providers["WHISPER_CPP_BASE"]
    eligible = {
        provider: value
        for provider, value in providers.items()
        if value["failure_count"] <= baseline["failure_count"]
        and value["place_entity_recall"] >= baseline["place_entity_recall"]
        and value["timestamp_alignment"] is not None
    }
    if not eligible:
        return {
            "status": "REVIEW_REQUIRED",
            "decision": "RUN_PARAFORMER_CHALLENGE",
            "reason": "没有候选同时满足基线失败数、地点 Recall 与时间码数据门槛。",
        }
    best_id, best = max(eligible.items(), key=lambda item: item[1]["weighted_score"])
    if best_id == "WHISPER_CPP_BASE":
        decision = "KEEP_CURRENT"
    elif best_id == "WHISPER_CPP_LARGE_V3_TURBO_Q5" and best["weighted_score"] - baseline["weighted_score"] < 0.03:
        decision = "UPGRADE_WHISPER_MODEL"
    elif best_id == "QWEN3_ASR_MLX_0_6B" and _qwen_resource_heavy(best):
        decision = "ADD_ADVANCED_PROVIDER"
    else:
        decision = "ADD_NEW_DEFAULT_PROVIDER"
    result: dict[str, Any] = {
        "status": "REVIEW_REQUIRED",
        "decision": decision,
        "candidate": best_id,
        "reason": "评分仅提供候选建议；默认 Provider 仍须经人工确认、完整视频回放与资源门禁。",
    }
    if qwen_context is not None:
        result["qwen_context_gain"] = qwen_context["context_gain"]
    return result


def _qwen_resource_heavy(summary: dict[str, Any]) -> bool:
    return bool(summary["alignment_peak_memory_bytes"] or summary["alignment_runtime_ms"])


def main() -> None:
    parser = argparse.ArgumentParser(description="评估本地 ASR Provider 采集结果")
    parser.add_argument("samples", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.samples.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("samples 必须是 JSON 数组")
    result = json.dumps(evaluate(rows), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
