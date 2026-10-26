from itertools import permutations
from types import SimpleNamespace

import pytest

from zhijian.services.recommendation_intent import VERSION, assess, summarize
from zhijian.services.video_support import _merge_place_candidates, resolve_mentions_with_amap


def statement(text, intent="RECOMMENDED", scope="PLACE_OVERALL", **extra):
    return {
        "statement_id": text,
        "intent": intent,
        "scope": scope,
        "subject_entity_id": "a",
        "speaker": "AUTHOR",
        "quote": text,
        "segment_ids": ["s"],
        **extra,
    }


def candidate(statements, intent="RECOMMENDED"):
    return {
        "name": "A",
        "raw_name": "A",
        "entity_id": "a",
        "segment_ids": ["s"],
        "visit_intent": intent,
        "recommendation_evidence": {"statements": statements},
    }


@pytest.mark.parametrize("local", ["别坐游船", "下雨别来", "菜品贵", "交通不方便"])
def test_place_positive_and_local_warning_remain_independent(local):
    text = "A值得去，但" + local
    evidence = assess(
        candidate([statement("A值得去"), statement(local, "NOT_RECOMMENDED", "LOCAL_DETAIL")]), {"s": text}
    )
    assert evidence["status"] == "RECOMMENDED"
    assert evidence["assessment_status"] == "VERIFIED"
    assert len(evidence["statements"]) == 2


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ({"subject_entity_id": "b"}, "WRONG_SUBJECT"),
        ({"segment_ids": ["foreign"]}, "UNGROUNDED_QUOTE"),
        ({"quote": "伪造值得去"}, "UNGROUNDED_QUOTE"),
        ({"intent": "FAKE"}, "INVALID_STATEMENT"),
        ({"condition": "伪造条件"}, "UNGROUNDED_CONTEXT"),
    ],
)
def test_invalid_evidence_cannot_create_recommendation(mutation, reason):
    result = (
        assess(candidate([statement("A值得去", **mutation)]), {"s": "A值得去"})
        if "quote" not in mutation
        else assess(candidate([{**statement("A值得去"), **mutation}]), {"s": "A值得去"})
    )
    assert result["status"] == "UNKNOWN"
    assert reason in result["reason_codes"]


def test_conflicting_candidate_order_never_overwrites_opinion():
    items = [
        candidate([statement("A值得去")]),
        candidate([statement("A不值得去", "NOT_RECOMMENDED")], "NOT_RECOMMENDED"),
    ]
    results = [
        assess(_merge_place_candidates(list(order))[0], {"s": "A值得去。A不值得去"})
        for order in permutations(items)
    ]
    assert results[0] == results[1]
    assert results[0]["status"] == "CONFLICT"
    assert len(results[0]["statements"]) == 2


@pytest.mark.parametrize("text", ["A不是不推荐", "A风景很好", "不少人说A不值得去"])
def test_uncertain_polarity_is_reviewed(text):
    result = assess(candidate([statement(text)]), {"s": text})
    assert result["assessment_status"] == "NEEDS_REVIEW"
    assert result["status"] == "UNKNOWN"


def test_other_speaker_and_local_only_do_not_become_author_recommendation():
    for value in (
        statement("A不值得去", "NOT_RECOMMENDED", speaker="OTHER"),
        statement("游船不推荐", "NOT_RECOMMENDED", "LOCAL_DETAIL"),
    ):
        result = assess(candidate([value], "NEUTRAL"), {"s": value["quote"]})
        assert result["status"] == "UNKNOWN"


def test_explicit_revision_preserves_old_statement():
    old = statement("去年不推荐A", "NOT_RECOMMENDED", statement_id="old", time_context="去年")
    new = statement("现在A值得去", statement_id="new", supersedes=["old"], time_context="现在")
    result = assess(candidate([old, new]), {"s": "去年不推荐A，现在A值得去"})
    assert result["status"] == "RECOMMENDED"
    assert len(result["statements"]) == 2


def mention(identifier, evidence, **values):
    return SimpleNamespace(
        id=identifier,
        name="A",
        metadata_json={"recommendation_evidence": evidence},
        extraction_status="EXTRACTED",
        visit_intent="NOT_RECOMMENDED" if evidence["status"] == "NOT_RECOMMENDED" else "RECOMMENDED",
        ai_note_version_id="version",
        video_asset_id=identifier,
        poi_policy="RESOLVE",
        resolution_status="UNRESOLVED",
        **values,
    )


def test_cross_source_conflict_and_legacy_are_conservative():
    positive = {
        "schema_version": VERSION,
        "assessment_status": "VERIFIED",
        "status": "RECOMMENDED",
        "statements": [],
    }
    negative = {**positive, "status": "NOT_RECOMMENDED"}
    assert summarize([mention("a", positive), mention("b", negative)])["status"] == "CONFLICT"
    legacy = mention("old", positive)
    legacy.metadata_json = {}
    assert summarize([legacy])["status"] == "UNKNOWN"


def test_suspicious_evidence_zero_poi_calls(app_and_session, monkeypatch):
    from zhijian.core.config import Settings

    _, factory = app_and_session
    calls = []
    monkeypatch.setattr(
        "zhijian.services.video_support.AMapPOIProvider.search", lambda *args, **kwargs: calls.append(1)
    )
    m = mention("m", {"schema_version": VERSION, "status": "CONFLICT", "assessment_status": "NEEDS_REVIEW"})
    with factory() as db:
        # No persisted entity required: the early gate must precede any provider access.
        resolve_mentions_with_amap(db, Settings(_env_file=None), [m], api_key="fake")
    assert m.resolution_status == "REVIEW"
    assert calls == []


def test_manual_confirmation_does_not_change_author_or_user_preference(client, app_and_session):
    from zhijian.db.models import Place, PlaceMention, Source, VideoAsset

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/negative-position")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        evidence = assess(
            candidate([statement("A不值得去", "NOT_RECOMMENDED")], "NOT_RECOMMENDED"), {"s": "A不值得去"}
        )
        m = PlaceMention(
            video_asset_id=asset.id,
            name="A",
            visit_intent="NOT_RECOMMENDED",
            resolution_status="REVIEW",
            poi_policy="RESOLVE",
            metadata_json={
                "recommendation_evidence": evidence,
                "poi_candidates": [
                    {
                        "provider_id": "test-poi",
                        "name": "A",
                        "province": "云南省",
                        "city": "昆明市",
                        "district": "五华区",
                        "address": "昆明",
                        "longitude": 102.7,
                        "latitude": 25.05,
                    }
                ],
            },
        )
        db.add(m)
        db.commit()
        mid = m.id
    result = client.post(
        f"/api/travel/place-mentions/{mid}/confirm",
        json={"provider": "AMAP", "poi_id": "test-poi", "expected_revision": 0},
    )
    assert result.status_code == 200
    pid = result.json()["place_id"]
    detail = client.get(f"/api/travel/places/{pid}").json()
    assert detail["recommendation_summary"]["status"] == "NOT_RECOMMENDED"
    assert not any(
        item["place_id"] == pid
        for item in client.get("/api/travel/recommendations?include_mismatch=true").json()
    )
    assert detail["recommendation"]["tier"] not in {"PRIORITY", "WORTH_CONSIDERING"}
    assert detail["recommendation_summary"]["source_opinions"][0]["statements"][0]["quote"] == "A不值得去"
    with factory() as db:
        m = db.get(PlaceMention, mid)
        assert m.visit_intent == "NOT_RECOMMENDED" and m.metadata_json["recommendation_evidence"] == evidence
        assert db.get(Place, pid).user_state not in {"LIKED", "DISLIKED", "VISITED", "WANT_TO_GO"}


def test_compiler_preserves_subject_binding_in_recommendation_evidence():
    import json

    from zhijian.ai.request_compiler import CompiledRequest

    compiler = CompiledRequest([], {"snapshot_identity": "test"}, {"seg": "s1"}, {"seg"}, "GROUND_MAP")
    value = {
        "content_units": [{"content_unit_id": "u", "segment_ids": ["s1"]}],
        "entities": [
            {
                "entity_id": "a",
                "content_unit_id": "u",
                "segment_ids": ["s1"],
                "recommendation_evidence": {"statements": [{**statement("A值得去"), "segment_ids": ["s1"]}]},
            }
        ],
        "claims": [],
        "relations": [],
    }
    decoded = json.loads(compiler.decode(json.dumps(value)))
    entity = decoded["entities"][0]
    assert entity["recommendation_evidence"]["statements"][0]["subject_entity_id"] == entity["entity_id"]
    assert entity["recommendation_evidence"]["statements"][0]["segment_ids"] == ["seg"]


@pytest.mark.parametrize(
    "text, intent, expected",
    [
        ("A值得去，但下雨别来", "RECOMMENDED", "RECOMMENDED"),
        ("A值得去，但A不值得去", "RECOMMENDED", "UNKNOWN"),
        ("A的游船不推荐", "NOT_RECOMMENDED", "UNKNOWN"),
        ("不少人说A不推荐", "NOT_RECOMMENDED", "UNKNOWN"),
    ],
)
def test_negation_scope_and_attribution_doubts_are_conservative(text, intent, expected):
    assert assess(candidate([statement(text, intent)], intent), {"s": text})["status"] == expected


def test_shared_segment_attitudes_do_not_broadcast_to_peer():
    data = candidate([statement("B不值得去", "NOT_RECOMMENDED")], "NOT_RECOMMENDED")
    data["_peer_names"] = ["B"]
    assert assess(data, {"s": "A值得去，B不值得去"})["status"] == "UNKNOWN"


def test_explicit_different_conditions_do_not_become_universal_recommendation_or_conflict():
    positive = statement("晴天A值得去", condition="晴天")
    negative = statement("雨天A不值得去", "NOT_RECOMMENDED", condition="雨天")
    result = assess(candidate([positive, negative]), {"s": "晴天A值得去，雨天A不值得去"})
    assert result["status"] == "UNKNOWN" and result["assessment_status"] == "VERIFIED"
