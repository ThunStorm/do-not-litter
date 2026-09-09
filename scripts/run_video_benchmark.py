"""Score captured video-workflow outputs against frozen fixture annotations.

This script never invokes a provider, downloads a video, or reads production data.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _text(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _change_key(value: dict[str, Any]) -> tuple[str, str]:
    return str(value.get("segment_id") or ""), _text(value.get("corrected_text"))


def _place_key(value: dict[str, Any]) -> tuple[str, str]:
    return _text(value.get("name")), str(value.get("place_type") or "")


def _insight_key(value: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _text(value.get("place")),
        str(value.get("insight_type") or ""),
        _text(value.get("expected_value", value.get("value"))),
        str(value.get("segment_id") or ""),
    )


def _candidate_key(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("external_poi_id") or value.get("id") or value.get("name") or "")
    return str(value)


def _score(expected: set[tuple[Any, ...]], actual: set[tuple[Any, ...]]) -> dict[str, float | int]:
    matches = len(expected & actual)
    return {
        "expected": len(expected),
        "actual": len(actual),
        "matched": matches,
        "precision": round(matches / len(actual), 4) if actual else 1.0 if not expected else 0.0,
        "recall": round(matches / len(expected), 4) if expected else 1.0,
    }


def validate_samples(samples: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    required = {
        "transcript_changes",
        "required_places",
        "forbidden_places",
        "place_types",
        "insights",
        "section_topics",
        "required_evidence",
        "poi_resolution",
    }
    for sample in samples:
        sample_id = str(sample.get("sample_id") or "")
        if not sample_id or sample_id in ids:
            raise ValueError("每个 Golden sample 必须有唯一 sample_id")
        ids.add(sample_id)
        expected = sample.get("expected")
        if not isinstance(expected, dict) or required - set(expected):
            raise ValueError(f"{sample_id} 缺少完整 expected 注释")


def evaluate(samples: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate_samples(samples)
    expected = {str(sample["sample_id"]): sample["expected"] for sample in samples}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sample_id = str(row.get("sample_id") or "")
        if sample_id not in expected:
            raise ValueError(f"结果包含未知 Video Golden sample：{sample_id}")
        groups[str(row.get("profile") or "unknown")].append(row)
    return {
        "profiles": {name: _profile_summary(items, expected) for name, items in sorted(groups.items())},
        "production_eligible": False,
        "notice": "Fixture 分数不能替代真实 Provider、视频或发布验收。",
    }


def _profile_summary(rows: list[dict[str, Any]], expected: dict[str, dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"expected": 0, "actual": 0, "matched": 0})
    schema_passes = 0
    forbidden_places = 0
    poi_matches = poi_expected = 0
    auto_confirmed = correct_auto_confirms = false_auto_confirms = review_count = unresolved_count = 0
    evidence_matches = evidence_expected = 0
    visit_window_matches = visit_window_expected = 0
    knowledge_matches = knowledge_expected = 0
    poi_candidate_matches = poi_candidate_expected = poi_rank_total = 0
    for row in rows:
        annotation = expected[str(row["sample_id"])]
        schema_passes += bool(row.get("schema_pass"))
        scores = {
            "transcript_changes": _score(
                {_change_key(item) for item in annotation["transcript_changes"]},
                {_change_key(item) for item in row.get("transcript_changes", [])},
            ),
            "places": _score(
                {_place_key(item) for item in annotation["required_places"]},
                {_place_key(item) for item in row.get("places", [])},
            ),
            "insights": _score(
                {_insight_key(item) for item in annotation["insights"]},
                {_insight_key(item) for item in row.get("insights", [])},
            ),
            "sections": _score(
                {_text(item) for item in annotation["section_topics"]},
                {_text(item) for item in row.get("section_topics", [])},
            ),
        }
        for name, score in scores.items():
            for key in totals[name]:
                totals[name][key] += int(score[key])
        actual_insights = {_insight_key(item) for item in row.get("insights", [])}
        window_types = {"BEST_MONTH", "BEST_SEASON", "BEST_TIME_SLOT"}
        knowledge_types = {"RECOMMENDED_ITEM", "HIGHLIGHT", "AUTHOR_OPINION", "AUDIENCE", "WARNING"}
        for insight in annotation["insights"]:
            key = _insight_key(insight)
            if insight.get("insight_type") in window_types:
                visit_window_expected += 1
                visit_window_matches += int(key in actual_insights)
            if insight.get("insight_type") in knowledge_types:
                knowledge_expected += 1
                knowledge_matches += int(key in actual_insights)
        actual_names = {_text(item.get("name")) for item in row.get("places", [])}
        forbidden_places += sum(_text(name) in actual_names for name in annotation["forbidden_places"])
        evidence = {str(item) for item in row.get("evidence_segment_ids", [])}
        required_evidence = {str(item) for item in annotation["required_evidence"]}
        evidence_matches += len(evidence & required_evidence)
        evidence_expected += len(required_evidence)
        for name, result in annotation["poi_resolution"].items():
            poi_expected += 1
            actual = row.get("poi_resolution", {}).get(name)
            if actual == result:
                poi_matches += 1
            if actual == "CONFIRMED":
                auto_confirmed += 1
                if result == "CONFIRMED":
                    correct_auto_confirms += 1
                else:
                    false_auto_confirms += 1
            review_count += int(actual == "REVIEW")
            unresolved_count += int(actual == "UNRESOLVED")
        expected_candidates = annotation.get(
            "poi_candidates", {item["name"]: item["name"] for item in annotation["required_places"]}
        )
        actual_candidates = row.get("poi_candidates", {})
        for name, expected_candidate in expected_candidates.items():
            candidates = [_candidate_key(item) for item in actual_candidates.get(name, [])]
            poi_candidate_expected += 1
            if str(expected_candidate) in candidates:
                poi_candidate_matches += 1
                poi_rank_total += candidates.index(str(expected_candidate)) + 1
    metrics = {name: _score_from_total(total) for name, total in totals.items()}
    return {
        "samples": len(rows),
        "schema_pass_rate": round(schema_passes / len(rows), 4) if rows else 0.0,
        "transcript_changes": metrics["transcript_changes"],
        "places": metrics["places"],
        "insights": metrics["insights"],
        "sections": metrics["sections"],
        "forbidden_place_count": forbidden_places,
        "evidence_coverage": round(evidence_matches / evidence_expected, 4) if evidence_expected else 1.0,
        "visit_window_recall": round(visit_window_matches / visit_window_expected, 4) if visit_window_expected else 1.0,
        "knowledge_coverage": round(knowledge_matches / knowledge_expected, 4) if knowledge_expected else 1.0,
        "poi_resolution_accuracy": round(poi_matches / poi_expected, 4) if poi_expected else 1.0,
        "poi_quality": {
            "candidate_recall": round(poi_candidate_matches / poi_candidate_expected, 4)
            if poi_candidate_expected
            else 1.0,
            "correct_candidate_mean_rank": round(poi_rank_total / poi_candidate_matches, 4)
            if poi_candidate_matches
            else None,
            "auto_confirm_precision": round(correct_auto_confirms / auto_confirmed, 4)
            if auto_confirmed
            else 1.0,
            "false_confirm_count": false_auto_confirms,
            "review_rate": round(review_count / poi_expected, 4) if poi_expected else 0.0,
            "unresolved_rate": round(unresolved_count / poi_expected, 4) if poi_expected else 0.0,
        },
    }


def _score_from_total(total: dict[str, int]) -> dict[str, float | int]:
    expected, actual, matched = total["expected"], total["actual"], total["matched"]
    return {
        **total,
        "precision": round(matched / actual, 4) if actual else 1.0 if not expected else 0.0,
        "recall": round(matched / expected, 4) if expected else 1.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估冻结的视频工作流 Fixture Benchmark")
    parser.add_argument("samples", type=Path, help="Video Workflow Golden JSON")
    parser.add_argument("runs", type=Path, help="已采集的结构化输出 JSON 数组")
    parser.add_argument("--output", type=Path, help="可选：写入 JSON 结果")
    args = parser.parse_args()
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    rows = json.loads(args.runs.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not isinstance(rows, list):
        raise SystemExit("samples 和 runs 均必须为 JSON 数组")
    encoded = json.dumps(evaluate(samples, rows), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
