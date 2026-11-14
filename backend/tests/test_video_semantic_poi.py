from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from zhijian.core.config import Settings
from zhijian.db.models import Destination, Place, PlaceMention, Source, VideoAsset
from zhijian.providers.amap import POICandidate
from zhijian.services.grounded_map import _canonical_payload, _semantic_escalation_reasons
from zhijian.services.video_support import (
    _high_information_bullets,
    _poi_review_reasons,
    _poi_score,
    _resolver_v3_decision,
    extract_place_mentions,
    materialize_destinations,
    materialize_transcript,
    resolve_mentions_with_amap,
)


def test_semantic_fixture_covers_all_frozen_cases() -> None:
    path = Path(__file__).parents[2] / "dev docs" / "benchmark" / "video-semantic-poi-golden-v1.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert [item["sample_id"] for item in cases] == [f"G-{index:03d}" for index in range(1, 13)]
    assert cases[4]["expected"]["reference"] == ["沈阳故宫"]
    assert cases[5]["expected"]["actionable"] == ["北京故宫", "沈阳故宫"]
    assert cases[8]["expected"]["destination"] == "天津市"


def test_semantic_payload_preserves_multi_unit_reference_evidence() -> None:
    class SegmentStub:
        def __init__(self, segment_id: str, text: str) -> None:
            self.id, self.text, self.corrected_text = segment_id, text, ""

    segments = [
        SegmentStub("seg-bj", "北京故宫比沈阳故宫规模大，推荐先看中轴线。"),
        SegmentStub("seg-tj", "第二站天津，推荐五大道，时间多可去天津之眼。"),
    ]
    payload = {
        "content_units": [
            {"content_unit_id": "unit-bj", "unit_type": "AREA_GUIDE", "segment_ids": ["seg-bj"]},
            {"content_unit_id": "unit-tj", "unit_type": "AREA_GUIDE", "segment_ids": ["seg-tj"]},
        ],
        "entities": [
            {
                "entity_id": "bj",
                "raw_name": "北京故宫",
                "content_unit_id": "unit-bj",
                "subject_role": "PRIMARY",
                "visit_intent": "RECOMMENDED",
                "poi_policy": "RESOLVE",
                "quote": "北京故宫比沈阳故宫规模大",
                "segment_ids": ["seg-bj"],
            },
            {
                "entity_id": "sy",
                "raw_name": "沈阳故宫",
                "content_unit_id": "unit-bj",
                "subject_role": "REFERENCE",
                "visit_intent": "NOT_APPLICABLE",
                "poi_policy": "REFERENCE_ONLY",
                "quote": "北京故宫比沈阳故宫规模大",
                "segment_ids": ["seg-bj"],
            },
            {
                "entity_id": "tj",
                "raw_name": "五大道",
                "content_unit_id": "unit-tj",
                "subject_role": "PRIMARY",
                "visit_intent": "RECOMMENDED",
                "poi_policy": "RESOLVE",
                "quote": "推荐五大道",
                "segment_ids": ["seg-tj"],
            },
        ],
        "relations": [
            {
                "relation_type": "COMPARED_WITH",
                "source_entity_id": "bj",
                "target_entity_id": "sy",
                "segment_ids": ["seg-bj"],
            }
        ],
        "claims": [
            {
                "claim_id": "claim-bj",
                "content_unit_id": "unit-bj",
                "text": "先看中轴线",
                "supporting_quote": "推荐先看中轴线",
                "segment_ids": ["seg-bj"],
            }
        ],
        "warnings": [],
    }
    _, _, _, units, entities, relations, claims = _canonical_payload(payload, segments)  # type: ignore[arg-type]
    assert len(units) == 2
    assert {item["content_unit_id"] for item in entities} == {"unit-bj", "unit-tj"}
    assert next(item for item in entities if item["entity_id"] == "sy")["poi_policy"] == "REFERENCE_ONLY"
    assert relations[0]["relation_type"] == "COMPARED_WITH"
    assert claims[0]["supporting_quote"] == "推荐先看中轴线"
    assert _semantic_escalation_reasons(entities) == {
        "bj": ["LOW_CONFIDENCE"],
        "sy": ["LOW_CONFIDENCE"],
        "tj": ["LOW_CONFIDENCE"],
    }


def test_reference_gate_and_destination_are_not_poi_fallbacks(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/semantic")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "北京故宫比沈阳故宫大。", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        candidates = [
            {
                "name": "北京故宫",
                "raw_name": "北京故宫",
                "quote": "北京故宫比沈阳故宫大",
                "segment_ids": [segments[0].id],
                "poi_policy": "RESOLVE",
                "content_unit_id": "unit-bj",
                "subject_role": "PRIMARY",
                "visit_intent": "NEUTRAL",
                "place_type": "MUSEUM",
            },
            {
                "name": "沈阳故宫",
                "raw_name": "沈阳故宫",
                "quote": "北京故宫比沈阳故宫大",
                "segment_ids": [segments[0].id],
                "poi_policy": "REFERENCE_ONLY",
                "content_unit_id": "unit-bj",
                "subject_role": "REFERENCE",
                "visit_intent": "NOT_APPLICABLE",
                "place_type": "MUSEUM",
            },
            {
                "name": "北京市",
                "raw_name": "北京",
                "quote": "北京故宫比沈阳故宫大",
                "segment_ids": [segments[0].id],
                "poi_policy": "AREA_RESOLVE",
                "content_unit_id": "unit-bj",
                "subject_role": "PRIMARY",
                "visit_intent": "NOT_APPLICABLE",
                "city_hint": "北京市",
                "place_type": "AREA",
            },
        ]
        mentions = extract_place_mentions(
            db, Settings(_env_file=None), asset, None, segments, candidates=candidates
        )
        reference = next(item for item in mentions if item.poi_policy == "REFERENCE_ONLY")
        actionable = next(item for item in mentions if item.poi_policy == "RESOLVE")
        assert reference.resolution_status == "SKIPPED"
        metrics: dict[str, int] = {}
        resolve_mentions_with_amap(db, Settings(_env_file=None), mentions, metrics=metrics)
        assert metrics == {
            "poi_skipped_reference": 1,
            "poi_resolve_requested": 1,
            "amap_request_count": 0,
            "amap_cache_hit_count": 0,
        }
        place = Place(
            name="故宫博物院",
            canonical_name="故宫博物院",
            origin="AI_EXTRACTED",
            place_type="MUSEUM",
            latitude=116.4,
            longitude=39.9,
        )
        db.add(place)
        db.flush()
        actionable.place_id, actionable.resolution_status = place.id, "CONFIRMED"
        created, linked = materialize_destinations(db, asset, mentions)
        assert created == linked == 1
        destination = db.scalar(select(Destination).where(Destination.canonical_name == "北京市"))
        assert destination and destination.name == "北京市"
        assert reference.destination_id is None and reference.place_id is None


def test_review_api_and_manual_poi_routes_hide_reference_mentions(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/review-filter")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        review = PlaceMention(
            video_asset_id=asset.id,
            name="故宫",
            raw_name="故宫",
            suggested_name="故宫",
            poi_policy="RESOLVE",
            resolution_status="REVIEW",
        )
        reference = PlaceMention(
            video_asset_id=asset.id,
            name="沈阳故宫",
            raw_name="沈阳故宫",
            suggested_name="沈阳故宫",
            poi_policy="REFERENCE_ONLY",
            resolution_status="REVIEW",
        )
        db.add_all([review, reference])
        db.commit()
        reference_id = reference.id
    response = client.get("/api/travel/place-reviews")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["故宫"]
    blocked = client.post(
        f"/api/travel/place-mentions/{reference_id}/confirm",
        json={"provider": "AMAP", "poi_id": "ignored", "expected_revision": 0},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "MENTION_NOT_POI_ELIGIBLE"


def test_normalized_auto_confirm_and_note_quality_gate() -> None:
    mention = PlaceMention(
        name="国博",
        raw_name="国博",
        suggested_name="国博",
        city_hint="北京市",
        place_type="MUSEUM",
        poi_policy="RESOLVE",
        metadata_json={"resolver_context": {"aliases": ["国家博物馆"]}},
    )
    candidate = POICandidate(
        "national", "中国国家博物馆", "北京市东城区", "北京市", "北京市", "东城区", 116.41, 39.9, "140000"
    )
    candidate.score, candidate.match_reasons, candidate.match_explanation = _poi_score(mention, candidate, [])
    decision = _resolver_v3_decision(mention, [candidate], _poi_review_reasons(candidate, None))
    assert decision["decision"] == "AUTO_NORMALIZED"
    assert _high_information_bullets(["景色优美", "十月中旬红叶最好", "十月中旬红叶最好"]) == (
        ["十月中旬红叶最好"],
        2,
    )


def test_shared_segment_transition_does_not_attach_previous_restriction_to_next_place():
    from types import SimpleNamespace

    text = "除了高反人群，其他人都非常适合。第四个，辽宁千山。老人孩子都可以过来。"
    payload = {
        "entities": [
            {
                "entity_id": "qianshan",
                "raw_name": "辽宁千山",
                "quote": "第四个，辽宁千山。",
                "segment_ids": ["shared"],
                "content_unit_id": "q",
                "subject_role": "PRIMARY",
                "visit_intent": "RECOMMENDED",
                "poi_policy": "RESOLVE",
                "recommendation_evidence": {
                    "statements": [
                        {
                            "statement_id": "bad",
                            "quote": "除了高反人群，其他人都非常适合",
                            "segment_ids": ["shared"],
                            "subject_entity_id": "qianshan",
                            "intent": "NOT_RECOMMENDED",
                            "scope": "LOCAL_DETAIL",
                        },
                        {
                            "statement_id": "good",
                            "quote": "老人孩子都可以过来",
                            "segment_ids": ["shared"],
                            "subject_entity_id": "qianshan",
                            "intent": "RECOMMENDED",
                            "scope": "PLACE_OVERALL",
                        },
                    ]
                },
            }
        ],
        "content_units": [
            {
                "content_unit_id": "q",
                "unit_type": "PLACE_GUIDE",
                "anchor_entity_ids": ["qianshan"],
                "segment_ids": ["shared"],
            }
        ],
        "claims": [
            {
                "claim_id": "bad",
                "text": "高反人群不适合千山",
                "content_unit_id": "q",
                "subject_entity_ids": ["qianshan"],
                "supporting_quote": "除了高反人群，其他人都非常适合",
                "segment_ids": ["shared"],
                "claim_type": "CAUTION",
            },
            {
                "claim_id": "good",
                "text": "千山适合老人孩子",
                "content_unit_id": "q",
                "subject_entity_ids": ["qianshan"],
                "supporting_quote": "老人孩子都可以过来",
                "segment_ids": ["shared"],
                "claim_type": "AUDIENCE",
            },
        ],
    }
    segment = SimpleNamespace(id="shared", text=text, corrected_text=text)
    _, _, warnings, units, entities, _, claims = _canonical_payload(payload, [segment])
    bad, good = claims
    assert bad["subject_entity_ids"] == []
    assert bad["text"] == "除了高反人群，其他人都非常适合"
    assert bad["supporting_quote"] == bad["text"] and bad["segment_ids"] == ["shared"]
    assert (
        next(u for u in units if u["content_unit_id"] == bad["content_unit_id"])["unit_type"]
        == "SUPPLEMENTAL"
    )
    assert good["subject_entity_ids"] == ["qianshan"] and good["content_unit_id"] == "q"
    assert [s["quote"] for s in entities[0]["recommendation_evidence"]["statements"]] == [
        "老人孩子都可以过来"
    ]
    assert entities[0]["visit_intent"] == "RECOMMENDED"
    assert any("归属待核" in w for w in warnings)


def test_transition_guard_preserves_explicit_forward_reference_and_ambiguous_repeated_quote():
    from types import SimpleNamespace

    for text, quote in [
        ("辽宁千山门票便宜。第四个，辽宁千山。", "辽宁千山门票便宜"),
        ("老人孩子都适合。第四个，辽宁千山。老人孩子都适合。", "老人孩子都适合"),
    ]:
        payload = {
            "entities": [
                {
                    "entity_id": "q",
                    "raw_name": "辽宁千山",
                    "quote": "第四个，辽宁千山。",
                    "segment_ids": ["s"],
                    "content_unit_id": "u",
                    "subject_role": "PRIMARY",
                }
            ],
            "claims": [
                {
                    "claim_id": "c",
                    "content_unit_id": "u",
                    "text": quote,
                    "supporting_quote": quote,
                    "subject_entity_ids": ["q"],
                    "segment_ids": ["s"],
                }
            ],
        }
        result = _canonical_payload(payload, [SimpleNamespace(id="s", text=text, corrected_text=text)])
        assert result[-1][0]["subject_entity_ids"] == ["q"]
        assert not result[2]


def test_transition_guard_keeps_unmatched_raw_statement_and_blocks_unproven_poi():
    from types import SimpleNamespace

    text = "这里不适合老人。第四个，辽宁千山。"
    payload = {
        "entities": [
            {
                "entity_id": "q",
                "raw_name": "辽宁千山",
                "quote": "第四个，辽宁千山。",
                "segment_ids": ["s"],
                "subject_role": "PRIMARY",
                "visit_intent": "NOT_RECOMMENDED",
                "recommendation_evidence": {
                    "statements": [
                        {
                            "statement_id": "r",
                            "subject_entity_id": "q",
                            "segment_ids": ["s"],
                            "quote": "这里不适合老人",
                            "intent": "NOT_RECOMMENDED",
                            "scope": "PLACE_OVERALL",
                        }
                    ]
                },
            }
        ]
    }
    result = _canonical_payload(payload, [SimpleNamespace(id="s", text=text, corrected_text=text)])
    entity = result[4][0]
    assert entity["recommendation_evidence"]["statements"] == []
    assert entity["visit_intent"] == "NEUTRAL" and entity["poi_policy"] == "SKIP"
    assert result[-1][0]["text"] == "这里不适合老人"
    assert result[-1][0]["subject_entity_ids"] == []
