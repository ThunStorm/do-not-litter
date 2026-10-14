from types import SimpleNamespace

import pytest
from sqlalchemy import select

from zhijian.ai.request_metrics import provider_cache_metrics, request_metrics
from zhijian.db.models import Place, PlaceMention, PlaceVisitWindow, Source, VideoAsset
from zhijian.services.title_temporal import parse_title_temporal_context, title_identity, title_projection
from zhijian.services.video_support import _ground_map_facts, materialize_place_insights


@pytest.mark.parametrize(
    "title, intent, months, period",
    [
        ("十一月哪里人少景美", "RECOMMENDED", [11], "BEST_VISIT"),
        ("十一月出发十二月回来", "UNKNOWN", [11, 12], "BEST_VISIT"),
        ("去年十一月旅行记录", "UNKNOWN", [11], "BEST_VISIT"),
        ("十月中旬赏红叶", "RECOMMENDED", [10], "FOLIAGE"),
        ("十一月不要去故宫", "AVOID", [11], "BEST_VISIT"),
        ("11月闭园", "RESTRICTED", [11], "SEASONAL_CLOSURE"),
        ("11月旅行", "UNKNOWN", [11], "BEST_VISIT"),
        ("13月哪里人少景美", "UNKNOWN", [], "BEST_VISIT"),
        ("秋天赏花推荐", "RECOMMENDED", [], "BLOOM"),
    ],
)
def test_title_golden(title, intent, months, period):
    context = parse_title_temporal_context(title)
    assert context["intent"] == intent
    assert context["months"] == months
    assert context["period_type"] == period
    assert context["source_kind"] == "TITLE_METADATA"
    assert context["source_text"] in title
    if "中旬" in title:
        assert context["month_segment"] == "MID"


def mention(**changes):
    return SimpleNamespace(
        id="mention-a",
        name="故宫",
        raw_name="故宫",
        subject_role="PRIMARY",
        visit_intent="RECOMMENDED",
        poi_policy="RESOLVE",
        extraction_status="EXTRACTED",
        segment_ids_json=["seg-a"],
        content_unit_id="u1",
        metadata_json=changes.pop("metadata", {}),
        **changes,
    )


def test_conservative_scope_and_conflicts():
    context = parse_title_temporal_context("十一月哪里人少景美")
    candidate = mention()
    assert title_projection(context, candidate, "推荐故宫", [])["status"] == "INHERITED"
    candidate.poi_policy = "REFERENCE_ONLY"
    assert title_projection(context, candidate, "对比故宫", [])["status"] == "INELIGIBLE"
    candidate.poi_policy = "RESOLVE"
    assert title_projection(context, candidate, "故宫十一月闭园", [])["status"] == "BODY_PRECEDENCE"
    assert title_projection(context, candidate, "故宫十二月最好", [])["status"] == "BODY_PRECEDENCE"
    specific = parse_title_temporal_context("十一月颐和园推荐")
    assert title_projection(specific, candidate, "推荐故宫", [])["status"] == "OUT_OF_SCOPE"
    foliage = parse_title_temporal_context("十月中旬赏红叶")
    assert title_projection(foliage, candidate, "推荐博物馆", [])["status"] == "OUT_OF_SCOPE"
    assert title_projection(foliage, candidate, "这里红叶最好", [])["status"] == "INHERITED"
    geographic = parse_title_temporal_context("十一月云南哪里人少景美")
    assert title_projection(geographic, candidate, "推荐故宫", [])["status"] == "OUT_OF_SCOPE"
    assert title_projection(geographic, candidate, "云南故宫推荐", [])["status"] == "INHERITED"
    candidate.visit_intent = "NOT_RECOMMENDED"
    assert title_projection(context, candidate, "不推荐故宫", [])["status"] == "INELIGIBLE"


def test_title_identity_changes_with_title_even_without_temporal_cues():
    assert title_identity("十一月哪里人少景美") != title_identity("十二月哪里人少景美")
    assert title_identity("北京攻略") != title_identity("天津攻略")


def test_claim_subject_wins_over_shared_segment():
    candidates = [
        mention(metadata={"semantic": {"entity_id": "a"}}),
        mention(metadata={"semantic": {"entity_id": "b"}}),
    ]
    candidates[1].id = "mention-b"
    seg = SimpleNamespace(id="seg-a", text="故宫十一月闭园，颐和园推荐十月。", corrected_text="")
    fact = {
        "summary": "故宫闭园",
        "segment_ids": ["seg-a"],
        "supporting_quotes": ["故宫十一月闭园"],
        "subject_entity_ids": ["a"],
        "content_unit_id": "u1",
    }
    assert _ground_map_facts([fact], [seg], candidates)[0]["place_mention_ids"] == ["mention-a"]
    fact["subject_entity_ids"] = ["unknown"]
    assert _ground_map_facts([fact], [seg], candidates)[0]["place_mention_ids"] == []
    del fact["subject_entity_ids"]
    assert _ground_map_facts([fact], [seg], candidates)[0]["place_mention_ids"] == []


def test_materialization_is_idempotent_preserves_manual_and_title_source(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/title")
        place = Place(name="故宫", place_type="SCENIC_AREA", latitude=39.9, longitude=116.4)
        db.add_all([source, place])
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="十一月哪里人少景美")
        db.add(asset)
        db.flush()
        candidate = PlaceMention(
            video_asset_id=asset.id,
            place_id=place.id,
            name="故宫",
            raw_name="故宫",
            segment_ids_json=["seg-a"],
            confidence=0.9,
            metadata_json={
                "temporal_context": title_projection(
                    parse_title_temporal_context(asset.title), mention(), "推荐故宫", []
                )
            },
        )
        db.add(candidate)
        db.flush()
        manual = PlaceVisitWindow(place_id=place.id, provenance="USER", month=5, source_text="人工维护")
        db.add(manual)
        db.flush()
        materialize_place_insights(db, candidate)
        db.flush()
        first = db.scalar(select(PlaceVisitWindow).where(PlaceVisitWindow.provenance == "TITLE_CONTEXT"))
        assert first and first.month == 11 and first.source_id == source.id
        assert first.segment_ids_json == []
        first_id = first.id
        from fastapi.testclient import TestClient

        from zhijian.api.router import _visit_window_view

        view = _visit_window_view(first)
        assert view.source_kind == "TITLE_METADATA" and view.source_id == source.id
        db.commit()
        with TestClient(app_and_session[0]) as client:
            assert client.delete(f"/api/travel/places/{place.id}/visit-windows/{first.id}").status_code == 409
        materialize_place_insights(db, candidate)
        db.flush()
        windows = db.scalars(select(PlaceVisitWindow).where(PlaceVisitWindow.place_id == place.id)).all()
        assert {item.id for item in windows} == {manual.id, first_id}
        # Rebinding the mention reconciles derived windows to the new Place only.
        other = Place(name="新规范地点", place_type="SCENIC_AREA", latitude=40, longitude=116)
        db.add(other)
        db.flush()
        candidate.place_id = other.id
        materialize_place_insights(db, candidate)
        db.flush()
        moved = db.scalar(select(PlaceVisitWindow).where(PlaceVisitWindow.provenance == "TITLE_CONTEXT"))
        assert moved.place_id == other.id and moved.id != first_id
        asset.title = "去年十一月旅行记录"
        materialize_place_insights(db, candidate)
        db.flush()
        assert db.get(PlaceVisitWindow, manual.id)
        assert not db.scalar(select(PlaceVisitWindow).where(PlaceVisitWindow.provenance == "TITLE_CONTEXT"))


def test_metrics_keep_prefix_stable_and_dynamic_body_distinct():
    a = request_metrics(
        [{"role": "system", "content": "仅返回有证据JSON"}, {"role": "user", "content": "分片1"}]
    )
    b = request_metrics(
        [{"role": "system", "content": "仅返回有证据JSON"}, {"role": "user", "content": "分片2"}]
    )
    assert a["static_prompt_fingerprint"] == b["static_prompt_fingerprint"]
    assert a["prompt_fingerprint"] != b["prompt_fingerprint"]
    assert a["static_prefix_chars"] == len("仅返回有证据JSON")
    assert a["dynamic_body_chars"] == 3


def test_provider_cache_metrics_do_not_invent_usage():
    assert provider_cache_metrics({}) == {"reported_cached_tokens": None, "cache_kind": "UNKNOWN"}
    assert provider_cache_metrics({"cached_tokens": True})["reported_cached_tokens"] is None
    assert provider_cache_metrics({"cached_tokens": 123}, "UNKNOWN")["cache_kind"] == "UNKNOWN"
    assert provider_cache_metrics({"prompt_tokens_details": {"cached_tokens": 12}}) == {
        "reported_cached_tokens": 12,
        "cache_kind": "PROVIDER_PREFIX_CACHE_HIT",
    }


def test_shared_segment_time_claim_and_title_do_not_cross_places(app_and_session):
    from zhijian.core.config import Settings
    from zhijian.services.video_support import extract_place_mentions, materialize_transcript

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/shared")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="十一月哪里人少景美")
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "故宫与颐和园都推荐。故宫十一月闭园，颐和园风景好。", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        candidates = [
            {
                "name": name,
                "entity_id": entity,
                "quote": name,
                "segment_ids": [segments[0].id],
                "visit_intent": "RECOMMENDED",
                "subject_role": "PRIMARY",
                "poi_policy": "RESOLVE",
            }
            for name, entity in [("故宫", "a"), ("颐和园", "b")]
        ]
        result = extract_place_mentions(
            db,
            Settings(_env_file=None),
            asset,
            None,
            segments,
            candidates=candidates,
            claims=[
                {
                    "subject_entity_ids": ["a"],
                    "segment_ids": [segments[0].id],
                    "supporting_quote": "故宫十一月闭园",
                }
            ],
        )
        a, b = result
        assert a.metadata_json["temporal_context"]["status"] == "BODY_PRECEDENCE"
        assert b.metadata_json["temporal_context"]["status"] == "INHERITED"
        assert not b.metadata_json["visit_windows"]
        assert a.metadata_json["visit_windows"][0]["suitability"] == "RESTRICTED"


def test_artifact_cache_title_edit_and_note_fallback_are_grounded(app_and_session, monkeypatch):
    import json

    import zhijian.services.video_support as support
    from zhijian.core.config import Settings
    from zhijian.providers.llm import LLMResult
    from zhijian.services.grounded_map import get_or_create_grounded_map

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/cache-title")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="十一月哪里人少景美")
        db.add(asset)
        db.flush()
        transcript, segments = support.materialize_transcript(
            db, source, asset, [{"text": "推荐故宫看建筑", "start_ms": 0, "end_ms": 1000}], source_kind="ASR"
        )
        calls = []
        monkeypatch.setattr(
            support, "provider_for_role", lambda *args: (SimpleNamespace(), "fixture", "fixture")
        )

        def response(*args, **kwargs):
            calls.append(kwargs["stage"])
            return LLMResult(
                json.dumps(
                    {
                        "content_units": [],
                        "relations": [],
                        "claims": [],
                        "warnings": [],
                        "entities": [
                            {
                                "entity_id": "a",
                                "raw_name": "故宫",
                                "quote": "推荐故宫",
                                "segment_ids": [segments[0].id],
                                "visit_intent": "RECOMMENDED",
                            }
                        ],
                    }
                ),
                "fixture",
                "fixture",
                {},
            )

        monkeypatch.setattr(support, "_cached_stage_json", response)
        settings = Settings(_env_file=None)
        first = get_or_create_grounded_map(db, settings, asset, transcript, segments)
        assert get_or_create_grounded_map(db, settings, asset, transcript, segments).id == first.id
        assert len(calls) == 1
        asset.title = "十二月哪里人少景美"
        second = get_or_create_grounded_map(db, settings, asset, transcript, segments)
        assert second.id != first.id and second.semantic_hash != first.semantic_hash
        assert len(calls) == 2
        candidates = support.extract_place_mentions(
            db, settings, asset, None, segments, candidates=second.entities_json
        )

        def unavailable(*args, **kwargs):
            raise RuntimeError("fixture unavailable")

        monkeypatch.setattr(support, "_cached_stage_json", unavailable)
        second.facts_json = [
            {"summary": "推荐故宫", "supporting_quotes": ["推荐故宫"], "segment_ids": [segments[0].id]}
        ]
        version = support.generate_note(
            db, settings, asset, transcript, segments, mentions=candidates, grounded_map=second
        )
        assert "12 月适合前往 · 来自视频标题" in version.overview
        assert "来自视频标题" in version.markdown
        assert all(fact["segment_ids"] == [segments[0].id] for fact in version.map_facts_json)
