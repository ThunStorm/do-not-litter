"""Score deterministic POI-resolution Golden fixtures without contacting a provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from zhijian.db.models import PlaceMention
from zhijian.providers.amap import POICandidate
from zhijian.services.video_support import _poi_review_reasons, _poi_score


def _mention(value: dict[str, Any], suffix: str = "") -> PlaceMention:
    return PlaceMention(
        id=f"fixture{suffix}",
        video_asset_id="fixture",
        name=str(value["name"]),
        raw_name=str(value.get("raw_name") or value["name"]),
        suggested_name=str(value.get("suggested_name") or value["name"]),
        city_hint=str(value.get("city_hint") or ""),
        province_hint=str(value.get("province_hint") or ""),
        place_type=str(value.get("place_type") or "UNKNOWN"),
        metadata_json={
            "resolver_context": {
                "aliases": value.get("aliases") or [],
                "district_hint": value.get("district_hint") or "",
                "nearby_landmarks": value.get("nearby_landmarks") or [],
            }
        },
    )


def _candidate(value: dict[str, Any]) -> POICandidate:
    return POICandidate(**value)


def evaluate(cases: list[dict[str, Any]]) -> dict[str, float | int]:
    correct_at_1 = correct_at_3 = auto_confirmed = correct_auto_confirms = wrong_confirm_count = 0
    statuses: list[dict[str, str]] = []
    for case in cases:
        mention = _mention(case["mention"], str(case["sample_id"]))
        contexts = [mention, *[_mention({"name": value, "city_hint": value}, value) for value in case["mention"].get("cross_place_context", [])]]
        candidates = [_candidate(value) for value in case["candidates"]]
        for candidate in candidates:
            candidate.score, candidate.match_reasons, candidate.match_explanation = _poi_score(
                mention, candidate, contexts
            )
        candidates.sort(key=lambda item: (-item.score, item.name))
        expected = case["expected"]
        expected_id = str(expected["candidate_id"])
        rank = next((index for index, item in enumerate(candidates) if item.provider_id == expected_id), None)
        correct_at_1 += int(rank == 0)
        correct_at_3 += int(rank is not None and rank < 3)
        status = "CONFIRMED" if not _poi_review_reasons(candidates[0], candidates[1] if len(candidates) > 1 else None) else "REVIEW"
        auto_confirmed += int(status == "CONFIRMED")
        correct_auto_confirms += int(status == "CONFIRMED" and expected["status"] == "CONFIRMED" and rank == 0)
        wrong_confirm_count += int(status == "CONFIRMED" and (expected["status"] != "CONFIRMED" or rank != 0))
        statuses.append({"sample_id": str(case["sample_id"]), "status": status})
    total = len(cases)
    return {
        "cases": total,
        "candidate_recall_at_1": round(correct_at_1 / total, 4) if total else 1.0,
        "candidate_recall_at_3": round(correct_at_3 / total, 4) if total else 1.0,
        "auto_confirm_precision": round(correct_auto_confirms / auto_confirmed, 4) if auto_confirmed else 1.0,
        "auto_confirm_rate": round(auto_confirmed / total, 4) if total else 0.0,
        "review_rate": round(sum(item["status"] == "REVIEW" for item in statuses) / total, 4) if total else 0.0,
        "unresolved_rate": 0.0,
        "wrong_confirm_count": wrong_confirm_count,
        "statuses": statuses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估 POI Resolver Golden")
    parser.add_argument("samples", type=Path)
    args = parser.parse_args()
    cases = json.loads(args.samples.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(cases), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
