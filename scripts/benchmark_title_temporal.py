"""Reproducible synthetic representation A/B; no database or Provider calls."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from zhijian.ai.request_compiler import compile_request
from zhijian.ai.request_metrics import request_metrics
from zhijian.db.models import Segment
from zhijian.services.video_support import _pack_place_evidence

ROOT = Path(__file__).resolve().parents[1]


def benchmark() -> dict:
    segments = [
        Segment(
            id=f"seg_{index:032x}",
            snapshot_id="fixture-snapshot",
            ordinal=index,
            text=f"推荐地点{index}，十月观赏建筑。",
            raw_text=f"推荐地点{index}，十月观赏建筑。",
            corrected_text="",
            locator_json={"start_ms": index * 1000, "end_ms": (index + 1) * 1000},
        )
        for index in range(1, 17)
    ]
    index = [
        {
            "mention_id": f"pm_{value:032x}",
            "name": f"地点{value}",
            "place_type": "SCENIC_AREA",
            "segment_ids": [segment.id for segment in segments],
            "quotes": [segments[value - 1].text],
        }
        for value in range(1, 9)
    ]
    facts = [
        {
            "summary": segments[value - 1].text,
            "supporting_quotes": [segments[value - 1].text],
            "segment_ids": [segments[value - 1].id],
            "place_mention_ids": [index[value - 1]["mention_id"]],
        }
        for value in (1, 2)
    ]
    results = {}
    for stage, prompt in [
        ("GROUND_MAP", "grounded_map.md"),
        ("NOTE_REDUCE", "video_note.md"),
        ("TRANSCRIPT_CORRECTION", "transcript_correction.md"),
    ]:
        system = (ROOT / "backend/src/zhijian/prompts" / prompt).read_text()
        if stage == "GROUND_MAP":
            body = "视频标题：十月旅行推荐\n分块：1/1\n" + "\n".join(
                f"[segment:{s.id} {s.locator_json['start_ms']}-{s.locator_json['end_ms']}ms] {s.text}"
                for s in segments
            )
            optimized = body
        elif stage == "NOTE_REDUCE":
            prefix = "已验证地点 Evidence Index："
            suffix = "\nEvidence 分包：1/1\n仅据此生成全局笔记：\n" + json.dumps(
                facts, ensure_ascii=False
            )
            body = prefix + json.dumps(index[:2], ensure_ascii=False) + suffix
            optimized = (
                prefix
                + json.dumps(_pack_place_evidence(index, facts), ensure_ascii=False)
                + suffix
            )
        else:

            def item(segment):
                return {"id": segment.id, "text": segment.text}

            items = [
                {
                    "target": item(s),
                    "context_before": [item(v) for v in segments[max(0, i - 2) : i]],
                    "context_after": [item(v) for v in segments[i + 1 : i + 3]],
                }
                for i, s in enumerate(segments)
            ]
            body = optimized = json.dumps({"items": items}, ensure_ascii=False)
        baseline = [
            {"role": "system", "content": system},
            {"role": "user", "content": body},
        ]
        started = perf_counter()
        compiled = compile_request(
            stage,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": optimized},
            ],
            segments,
            "fixture-snapshot",
        )
        previous_compiled = compile_request(
            stage, baseline, segments, "fixture-snapshot"
        )
        results[stage] = {
            "existing_compiler_baseline": request_metrics(previous_compiled.messages),
            "baseline": request_metrics(baseline),
            "optimized": request_metrics(compiled.messages),
            "projection_ms": round((perf_counter() - started) * 1000, 3),
            "provider_calls": 0,
            "input_tokens": "UNKNOWN",
            "output_tokens": "UNKNOWN",
            "provider_cached_tokens": "UNKNOWN",
            "provider_duration_ms": "UNKNOWN",
        }
    return {
        "scope": "SYNTHETIC_REPRESENTATION_ONLY",
        "fixture": "16 segments, 8 mentions, 2 pack facts",
        "model": "NONE",
        "temperature": "N/A",
        "client_result_cache": False,
        "real_upstream": False,
        "stages": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                stage: {
                    "before": value["baseline"]["raw_request_bytes"],
                    "after": value["optimized"]["raw_request_bytes"],
                }
                for stage, value in result["stages"].items()
            }
        )
    )
