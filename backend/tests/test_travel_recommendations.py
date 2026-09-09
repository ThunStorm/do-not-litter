import json

from zhijian.ai.stages import STAGE_SPECS
from zhijian.db.models import Job, Place, PlaceVisitWindow, Source, VideoAsset, VideoScreenshot
from zhijian.services.pipeline import process_job
from zhijian.services.travel_recommendations import recommendation_for_place, visit_window_summary
from zhijian.services.visual_facts import score_visual_fact_cases


def test_visit_window_and_recommendation_are_deterministic(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        place = Place(name="秋山", canonical_name="秋山", place_type="PARK", latitude=30, longitude=120)
        db.add(place)
        db.flush()
        window = PlaceVisitWindow(
            place_id=place.id,
            month=10,
            period_type="FOLIAGE",
            suitability="RECOMMENDED",
            source_text="十月红叶最好",
            provenance="SOURCE_FACT",
        )
        db.add(window)
        db.commit()
        timing = visit_window_summary([window], 10)
        recommendation = recommendation_for_place(place, windows=[window], insights=[], events=[], month=10)
    assert timing["state"] == "BEST"
    assert timing["reason"] == "十月红叶最好"
    assert recommendation["tier"] == "WORTH_CONSIDERING"
    assert recommendation["reasons"][0]["kind"] == "SYSTEM_JUDGMENT"


def test_preference_api_and_unsupported_vision_skip(client, app_and_session, tmp_path) -> None:
    _, factory = app_and_session
    place_id = client.get("/api/travel/map?zoom=8").json()["markers"][0]["id"]
    assert (
        client.post(f"/api/travel/places/{place_id}/preferences", json={"event_type": "LIKE"}).status_code
        == 200
    )
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://visual")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url="fixture://visual")
        db.add(asset)
        db.flush()
        screenshot = VideoScreenshot(video_asset_id=asset.id, planned_timestamp_ms=0, status="PLANNED")
        db.add(screenshot)
        db.flush()
        job = Job(
            job_type="TRAVEL", status="QUEUED", payload_json={"visual_fact_screenshot_id": screenshot.id}
        )
        db.add(job)
        db.commit()
        process_job(db, job)
        assert job.status == "PARTIAL_SUCCESS"
        assert job.error_code == "SKIPPED_UNSUPPORTED"
    assert "VISION_FACT" in STAGE_SPECS


def test_visual_fact_golden_has_no_severe_hallucinations() -> None:
    with open("dev docs/benchmark/vision-fact-golden-v1.json") as handle:
        cases = json.load(handle)["cases"]
    predictions = {case["id"]: case["facts"] for case in cases}
    score = score_visual_fact_cases(cases, predictions)
    assert score["fact_precision"] == 1
    assert score["fact_recall"] == 1
    assert score["severe_hallucination_count"] == 0
