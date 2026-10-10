"""Synthetic, deterministic A/B projection gate; no inference or external calls."""

from hashlib import sha256
from typing import Any

from zhijian.ai.request_compiler import compact, compile_request
from zhijian.ai.request_metrics import request_metrics
from zhijian.db.models import Segment
from zhijian.services.evidence_trace import evidence_trace


def evaluate_request_optimization(samples: list[dict[str, Any]]) -> dict:
    rows = []
    extra = [
        {
            "sample_id": "S-PRICE",
            "title": "门票20元，停车5元/小时，不推荐周末",
            "expected": {"actionable": [], "reference": []},
        },
        {
            "sample_id": "S-SEASON",
            "title": "10月上旬秋季丰水期，下午排队，推荐米粉",
            "expected": {"actionable": [], "reference": []},
        },
        {
            "sample_id": "S-NO-PLACE",
            "title": "这段视频只讲软件设置，没有地点",
            "expected": {"actionable": [], "reference": []},
        },
        {
            "sample_id": "S-ASR",
            "title": "水路庵 / 水陆庵：错音输入变体保留",
            "expected": {"actionable": ["水陆庵"], "reference": []},
        },
        {
            "sample_id": "S-FAST",
            "title": "水陆庵翠华山南五台单次速读",
            "expected": {"actionable": ["水陆庵", "翠华山", "南五台"], "reference": []},
        },
        {
            "sample_id": "S-LONG",
            "title": "合成长视频跨块，末段仍有事实",
            "expected": {"actionable": ["故宫", "天坛"], "reference": []},
        },
    ]
    for sample in [*samples, *extra]:
        identifier = sample["sample_id"]
        expected = sample["expected"]
        snapshot = f"synthetic:{identifier}"
        actionable, references = expected["actionable"], expected["reference"]
        texts = [sample["title"], "推荐：" + "、".join(actionable), "仅作比较：" + "、".join(references)]
        if identifier == "S-LONG":
            texts = [f"第{index}分钟的完整合成转写。" for index in range(30)] + texts
        values = [
            Segment(
                id="seg_" + sha256(f"{identifier}:{index}".encode()).hexdigest()[:32],
                snapshot_id=snapshot,
                ordinal=index,
                text=text,
                raw_text=text,
                corrected_text="",
                locator_json={"start_ms": index * 60000, "end_ms": (index + 1) * 60000},
            )
            for index, text in enumerate(texts)
        ]
        stage_metrics = []
        coverage: set[str] = set()
        for offset in range(0, len(values), 5):
            chunk = values[offset : offset + 5]
            messages = [
                {"role": "system", "content": "提取所有地点，引用逐字证据；比较项仅供参考。"},
                {
                    "role": "user",
                    "content": "\n".join(
                        f"[segment:{item.id} {item.locator_json['start_ms']}-"
                        f"{item.locator_json['end_ms']}ms] {item.text}"
                        for item in chunk
                    ),
                },
            ]
            compiled = compile_request("GROUND_MAP", messages, values, snapshot)
            coverage.update(compiled.allowed)
            stage_metrics.append(
                {
                    "stage": "GROUND_MAP",
                    "baseline": request_metrics(messages),
                    "candidate": request_metrics(compiled.messages),
                    "input_identity": compiled.identity,
                }
            )
        entries = [
            {
                "target": {"id": item.id, "text": item.text},
                "context_before": [
                    {"id": prev.id, "text": prev.text} for prev in values[max(0, index - 1) : index]
                ],
                "context_after": [
                    {"id": after.id, "text": after.text} for after in values[index + 1 : index + 2]
                ],
            }
            for index, item in enumerate(values)
        ]
        correction = [
            {"role": "system", "content": "校对仅限目标，保持否定、数字、单位和原意。"},
            {"role": "user", "content": compact({"items": entries})},
        ]
        compiled = compile_request("TRANSCRIPT_CORRECTION", correction, values, snapshot)
        stage_metrics.append(
            {
                "stage": "TRANSCRIPT_CORRECTION",
                "baseline": request_metrics(correction),
                "candidate": request_metrics(compiled.messages),
                "input_identity": compiled.identity,
            }
        )
        facts = [
            {
                "summary": item.text,
                "key_points": [item.text],
                "supporting_quotes": [item.text],
                "segment_ids": [item.id],
                "place_mention_ids": [],
            }
            for item in values
        ]
        mention = "plc_" + sha256(identifier.encode()).hexdigest()[:32]
        facts[0]["place_mention_ids"] = [mention]
        index = [
            {
                "mention_id": mention,
                "name": sample["title"],
                "segment_ids": [values[0].id],
                "quotes": [values[0].text],
            }
        ]
        note = [
            {"role": "system", "content": "生成笔记，保留 Evidence、否定、价格、月份。"},
            {
                "role": "user",
                "content": "已验证地点 Evidence Index："
                + compact(index)
                + "\n以下是带逐字 Evidence 的 GroundedEvidencePack。仅据此生成全局笔记：\n"
                + compact(facts),
            },
        ]
        reduced = compile_request("NOTE_REDUCE", note, values, snapshot)
        stage_metrics.append(
            {
                "stage": "NOTE_REDUCE",
                "baseline": request_metrics(note),
                "candidate": request_metrics(reduced.messages),
                "input_identity": reduced.identity,
            }
        )
        # Expected output is a fixture, not a model answer. Test schema/ID/quote transport separately.
        ids = {item.id: f"s{index}" for index, item in enumerate(values, 1)}
        output = {"changes": [{"segment_id": ids[item.id], "corrected_text": item.text} for item in values]}
        import json

        decoded = json.loads(compiled.decode(compact(output)))
        restored = {item["segment_id"]: item["corrected_text"] for item in decoded["changes"]}
        traces = [evidence_trace(values, [item.id], item.text, snapshot)["valid"] for item in values]
        rows.append(
            {
                "sample_id": identifier,
                "source": "SYNTHETIC",
                "request_metrics": stage_metrics,
                "source_coverage": len(coverage) / len(values),
                "claim_evidence_validity": sum(traces) / len(traces),
                "lossless_roundtrip": restored == {item.id: item.text for item in values},
                "expected_actionable": actionable,
                "expected_reference": references,
                "actionable_poi_precision": None,
                "actionable_poi_recall": None,
                "manual_review_rate": None,
                "review_reasons": [],
                "model_quality": "NOT_VERIFIED",
                "reported_input_tokens": None,
                "reported_output_tokens": None,
                "usage_source": "UNKNOWN",
                "provider_calls": 0,
            }
        )
    baseline_bytes = sum(stage["baseline"]["json_bytes"] for row in rows for stage in row["request_metrics"])
    candidate_bytes = sum(
        stage["candidate"]["json_bytes"] for row in rows for stage in row["request_metrics"]
    )
    return {
        "benchmark_version": "request-synthetic-v1",
        "rows": rows,
        "baseline_json_bytes": baseline_bytes,
        "candidate_json_bytes": candidate_bytes,
        "byte_reduction_percent": round((1 - candidate_bytes / baseline_bytes) * 100, 2),
        "offline_gate": all(
            row["lossless_roundtrip"] and row["source_coverage"] == 1 and row["claim_evidence_validity"] == 1
            for row in rows
        ),
        "provider_calls": 0,
        "real_token_target": "NOT_VERIFIED",
        "real_business_quality": "NOT_VERIFIED",
        "production_proven": False,
    }
