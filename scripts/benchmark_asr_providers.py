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


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {str(row.get("category") or "") for row in rows}
    missing = sorted(REQUIRED_CATEGORIES - categories)
    if missing:
        raise ValueError(f"ASR Benchmark 缺少场景：{'、'.join(missing)}")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("provider") or "")].append(row)
    return {
        "providers": {provider: _summary(values) for provider, values in sorted(groups.items())},
        "production_eligible": False,
        "notice": "离线 Benchmark 不替代真实视频回放或默认 Provider 切换验收。",
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    entity_expected = entity_matches = proper_expected = proper_matches = 0
    alignment: list[float] = []
    runtime: list[int] = []
    memory: list[int] = []
    failures = 0
    for row in rows:
        expected = {str(value) for value in row.get("expected_entities", [])}
        actual = {str(value) for value in row.get("actual_entities", [])}
        entity_expected += len(expected)
        entity_matches += len(expected & actual)
        if row.get("category") == "PROPER_NOUNS":
            proper_expected += len(expected)
            proper_matches += len(expected & actual)
        alignment.append(float(row.get("timestamp_alignment") or 0))
        runtime.append(int(row.get("runtime_ms") or 0))
        if row.get("peak_memory_bytes") is not None:
            memory.append(int(row["peak_memory_bytes"]))
        failures += int(bool(row.get("failed")))
    return {
        "samples": len(rows),
        "place_entity_recall": round(entity_matches / entity_expected, 4) if entity_expected else 1.0,
        "proper_noun_accuracy": round(proper_matches / proper_expected, 4) if proper_expected else 1.0,
        "timestamp_alignment": round(sum(alignment) / len(alignment), 4) if alignment else 0.0,
        "runtime_ms": sum(runtime),
        "peak_memory_bytes": max(memory) if memory else None,
        "failure_count": failures,
    }


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
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
