from types import SimpleNamespace

from sqlalchemy import func, select

from zhijian.db.models import MapMarkerState, Place, PlaceMention, PlaceVisitWindow, Source, VideoAsset
from zhijian.services.travel_recommendations import visit_window_summary
from zhijian.services.travel_timing import matches_window, window_label
from zhijian.services.video_support import _visit_windows_from_candidate


def window(**values):
    return SimpleNamespace(
        month=None,
        season=None,
        month_segment=None,
        day_time_slot=None,
        source_id="src",
        segment_ids_json=["seg"],
        provenance="SOURCE_FACT",
        **values,
    )


def test_landscape_superlative_never_becomes_best_time():
    text = "中国最美十大森林之一，是保存最完好的天然胡杨林"
    assert _visit_windows_from_candidate({}, ["seg"], {"seg": text}) == []
    invalid = window(source_text=text, period_type="BEST_VIEWING", suitability="RECOMMENDED")
    assert visit_window_summary([invalid])["state"] == "UNKNOWN"


def test_precise_evidence_wins_and_original_quote_is_preserved():
    bad = window(source_text="中国最美十大森林", period_type="BEST_VIEWING", suitability="RECOMMENDED")
    good = window(
        source_text="最佳观赏期是十月十五号到十月二十五",
        period_type="BEST_VIEWING",
        suitability="RECOMMENDED",
    )
    good.month = 10
    result = visit_window_summary([bad, good])
    assert result["summary"] == "10月15–25日 · 最佳"
    assert result["reason"] == good.source_text
    assert len(result["evidence"]) == 1
    assert (
        window_label(window(source_text="12月25日到1月5日", period_type="OTHER", suitability="RECOMMENDED"))
        == "12月25日–1月5日"
    )


def test_season_matches_month_and_restrictions_take_priority():
    autumn = window(source_text="秋天推荐前往", period_type="BEST_VISIT", suitability="RECOMMENDED")
    autumn.season = "AUTUMN"
    assert matches_window(autumn, month=10)
    assert not matches_window(autumn, month=5)
    assert "秋季" in visit_window_summary([autumn])["summary"]
    closed = window(source_text="十月闭园", period_type="SEASONAL_CLOSURE", suitability="RESTRICTED")
    closed.month = 10
    assert visit_window_summary([autumn, closed], 10)["state"] == "CLOSED"


def test_map_get_does_not_create_projection_and_hide_still_works(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        before = db.scalar(select(func.count(MapMarkerState.id)))
    marker = client.get("/api/travel/map").json()["markers"][0]
    with factory() as db:
        assert db.scalar(select(func.count(MapMarkerState.id))) == before
    assert client.post(f"/api/travel/places/{marker['id']}/marker/hide").json()["visibility"] == "HIDDEN"
    assert client.post(f"/api/travel/places/{marker['id']}/marker/restore").json()["visibility"] == "VISIBLE"


def test_source_count_is_distinct_and_default_requires_completed_analysis(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        place = Place(
            name="全年地点",
            canonical_name="全年地点",
            place_type="PARK",
            latitude=30,
            longitude=120,
            resolution_status="CONFIRMED",
        )
        source = Source(source_type="URL", locator="fixture://year-round")
        db.add_all([source, place])
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url="fixture://year-round")
        db.add(asset)
        db.flush()
        for _ in range(2):
            db.add(
                PlaceMention(
                    video_asset_id=asset.id,
                    place_id=place.id,
                    name=place.name,
                    metadata_json={"temporal_analysis": {"status": "NO_TIME_MENTIONED"}},
                )
            )
        db.commit()
        place_id = place.id
    result = client.get(f"/api/travel/map?selected_place_id={place_id}").json()
    marker = next(m for m in result["markers"] if m["id"] == place_id)
    assert marker["source_count"] == 1
    assert marker["timing_status"] == "DEFAULT_ALL_YEAR"
    assert marker["visit_window_state"] == "UNKNOWN"
    assert "全年适合" in marker["visit_window_summary"]
    assert any(m["id"] == place_id for m in client.get("/api/travel/map?month=5").json()["markers"])
    assert not any(
        m["id"] == place_id
        for m in client.get("/api/travel/map?month=5&visit_window_state=BEST").json()["markers"]
    )
    with factory() as db:
        db.add(
            PlaceMention(video_asset_id=asset.id, place_id=place_id, name="旧来源未分析", metadata_json={})
        )
        db.commit()
    marker = next(m for m in client.get("/api/travel/map").json()["markers"] if m["id"] == place_id)
    assert marker["timing_status"] == "UNANALYZED"
    assert not any(m["id"] == place_id for m in client.get("/api/travel/map?month=5").json()["markers"])


def test_map_month_filter_includes_season_only_window(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        place = Place(
            name="秋山",
            canonical_name="秋山",
            place_type="PARK",
            latitude=30,
            longitude=120,
            resolution_status="CONFIRMED",
        )
        db.add(place)
        db.flush()
        db.add(
            PlaceVisitWindow(
                place_id=place.id,
                season="AUTUMN",
                source_text="秋季适合",
                provenance="SOURCE_FACT",
                suitability="RECOMMENDED",
            )
        )
        db.commit()
        place_id = place.id
    october = client.get("/api/travel/map?month=10").json()["markers"]
    assert any(m["id"] == place_id for m in october)
    assert not any(m["id"] == place_id for m in client.get("/api/travel/map?month=5").json()["markers"])


def test_split_temporal_sentence_keeps_both_segment_ids():
    parts = {"a": "最佳观赏期是", "b": "十月十五号到十月二十五。"}
    result = _visit_windows_from_candidate({}, ["a", "b"], parts)
    assert len(result) == 1
    assert result[0]["month"] == 10
    assert result[0]["segment_ids"] == ["a", "b"]
    assert result[0]["source_text"] == "最佳观赏期是十月十五号到十月二十五"
    assert _visit_windows_from_candidate({}, ["a"], parts)[0]["month"] is None


def test_year_round_closure_is_not_presented_as_suitable():
    closed = window(source_text="全年闭园", period_type="SEASONAL_CLOSURE", suitability="RESTRICTED")
    result = visit_window_summary([closed])
    assert result["state"] == "CLOSED"
    assert "全年适合" not in result["summary"]
    assert "全年" in result["summary"]
