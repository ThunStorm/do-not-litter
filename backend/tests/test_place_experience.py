from sqlalchemy import select

from zhijian.db.models import (
    AINote,
    AINoteVersion,
    GroundedMapArtifact,
    Place,
    PlaceMention,
    Segment,
    Snapshot,
    Source,
    VideoAsset,
)
from zhijian.services.place_experience import effective_windows
from zhijian.services.video_support import _visit_windows_from_candidate


def test_relative_snow_weather_and_negative_recommendation():
    windows = _visit_windows_from_candidate({}, ["s"], {"s": "冬天赏雪，但不推荐下雪的时候来，最好是晴天。"})
    assert windows[0]["season"] == "WINTER"
    assert windows[0]["suitability"] == "AVOID"
    windows = _visit_windows_from_candidate({}, ["s"], {"s": "最好看的时候是雪后的三到五天。"})
    assert windows and windows[0]["period_type"] == "SNOW"


def test_single_anchor_recovers_owned_unit_without_writing_or_broadcast(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://snow")
        db.add(source)
        db.flush()
        snap = Snapshot(source_id=source.id, content_hash="snow")
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="雪景")
        db.add_all([snap, asset])
        db.flush()
        segments = [
            Segment(snapshot_id=snap.id, ordinal=i, text=t)
            for i, t in enumerate(
                [
                    "雪山的雪景最具童话感。",
                    "冬季推荐十二月下旬赏雪，最好在雪后三到五天前往。",
                    "去年十一月初雪。",
                ]
            )
        ]
        place = Place(
            name="雪山", place_type="SCENIC_AREA", latitude=40, longitude=120, resolution_status="CONFIRMED"
        )
        db.add_all([place, *segments])
        db.flush()
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
        version = AINoteVersion(ai_note_id=note.id, version=1, markdown="雪山", transcript_version=1)
        db.add(version)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=version.id,
            place_id=place.id,
            name="雪山",
            quote=segments[0].text,
            segment_ids_json=[segments[0].id],
            subject_role="PRIMARY",
            visit_intent="RECOMMENDED",
            content_unit_id="u",
            metadata_json={"semantic": {"entity_id": "e"}},
        )
        from zhijian.db.models import Transcript

        transcript = Transcript(video_asset_id=asset.id, version=1, source_kind="ASR")
        db.add(transcript)
        db.flush()
        artifact = GroundedMapArtifact(
            video_asset_id=asset.id,
            transcript_id=transcript.id,
            transcript_version=1,
            content_hash="snow",
            semantic_hash="snow",
            prompt_version="v",
            supplement_hash="",
            provider="fixture",
            model="fixture",
            content_units_json=[
                {
                    "content_unit_id": "u",
                    "unit_type": "PLACE_GUIDE",
                    "anchor_entity_ids": ["e"],
                    "segment_ids": [s.id for s in segments],
                }
            ],
        )
        db.add_all([artifact, mention])
        db.commit()
        pid = place.id
        assert any(w.month == 12 for w in effective_windows(db, [pid]))
        assert not any(w.month == 11 for w in effective_windows(db, [pid]))
        artifact.content_units_json = [
            {**artifact.content_units_json[0], "anchor_entity_ids": ["e", "other"]}
        ]
        db.commit()
        assert effective_windows(db, [pid]) == []
        artifact.content_units_json = [{**artifact.content_units_json[0], "anchor_entity_ids": ["e"]}]
        db.commit()
    result = client.get("/api/travel/map?month=12").json()
    marker = next(m for m in result["markers"] if m["id"] == pid)
    assert marker["timing_status"] == "EVIDENCE"
    assert "12月" in marker["visit_window_summary"]
    assert marker["recording_reasons"] == ["雪山的雪景最具童话感。"]
    detail = client.get(f"/api/travel/places/{pid}").json()
    assert any(w["month"] == 12 for w in detail["visit_windows"])
    assert detail["source_notes"][0]["note_id"].startswith("note_")
    assert detail["source_notes"][0]["title"] == "雪景"
    with factory() as db:
        from zhijian.db.models import PlaceVisitWindow

        assert not db.scalars(select(PlaceVisitWindow).where(PlaceVisitWindow.place_id == pid)).all()


def test_shared_scenery_can_inherit_season_across_chunks_but_not_dates(client, app_and_session):
    # Build the existing exact-version fixture, then connect an explicit multi-place unit.
    test_single_anchor_recovers_owned_unit_without_writing_or_broadcast(client, app_and_session)
    _, factory = app_and_session
    with factory() as db:
        artifact = db.scalar(select(GroundedMapArtifact).where(GroundedMapArtifact.semantic_hash == "snow"))
        primary = db.scalar(select(PlaceMention).where(PlaceMention.name == "雪山"))
        source_segment = db.get(Segment, primary.segment_ids_json[0])
        scene = Segment(snapshot_id=source_segment.snapshot_id, ordinal=4, text="山湖周边也有雪景。")
        peer = Place(
            name="山湖", place_type="SCENIC_AREA", latitude=40, longitude=121, resolution_status="CONFIRMED"
        )
        db.add_all([scene, peer])
        db.flush()
        common = dict(
            video_asset_id=primary.video_asset_id,
            ai_note_version_id=primary.ai_note_version_id,
            content_unit_id="shared",
            visit_intent="RECOMMENDED",
        )
        db.add_all(
            [
                PlaceMention(
                    **common,
                    place_id=primary.place_id,
                    name="雪山",
                    subject_role="PRIMARY",
                    quote=source_segment.text,
                    segment_ids_json=[source_segment.id],
                    metadata_json={"semantic": {"entity_id": "bridge"}},
                ),
                PlaceMention(
                    **common,
                    place_id=peer.id,
                    name="山湖",
                    subject_role="SECONDARY",
                    quote=scene.text,
                    segment_ids_json=[scene.id],
                    metadata_json={"semantic": {"entity_id": "peer"}},
                ),
            ]
        )
        artifact.content_units_json = [
            *artifact.content_units_json,
            {
                "content_unit_id": "shared",
                "unit_type": "MULTI_PLACE_LIST",
                "anchor_entity_ids": ["bridge", "peer"],
                "segment_ids": [source_segment.id, scene.id],
            },
        ]
        db.commit()
        pid = peer.id
        values = effective_windows(db, [pid])
        assert len(values) == 1 and values[0].provenance == "SEMANTIC_CONTEXT"
        assert values[0].season == "WINTER" and values[0].month is None
        # A different landscape without a shared scenic theme must not inherit.
        scene.text = "山湖周边也有云海。"
        artifact.content_units_json = [
            artifact.content_units_json[0],
            {**artifact.content_units_json[1], "segment_ids": [scene.id]},
        ]
        db.commit()
        assert effective_windows(db, [pid]) == []
        scene.text = "山湖周边也有雪景。"
        db.commit()
    marker = next(m for m in client.get("/api/travel/map?month=12").json()["markers"] if m["id"] == pid)
    assert "冬季" in marker["travel_brief"]["timing"]
    assert marker["travel_brief"]["inherited"]
    assert not marker["travel_brief"]["conditions"]


def test_negative_place_goes_to_review_without_any_poi_lookup(client, app_and_session, monkeypatch):
    from zhijian.core.config import Settings
    from zhijian.services.video_support import extract_place_mentions, resolve_mentions_with_amap

    def no_provider(*args, **kwargs):
        raise AssertionError("negative place must never instantiate a POI provider")

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", no_provider)
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://negative")
        db.add(source)
        db.flush()
        snapshot = Snapshot(source_id=source.id, content_hash="negative")
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add_all([snapshot, asset])
        db.flush()
        segment = Segment(snapshot_id=snapshot.id, text="我不推荐游客去假山。")
        db.add(segment)
        db.flush()
        mentions = extract_place_mentions(
            db,
            Settings(_env_file=None),
            asset,
            None,
            [segment],
            candidates=[
                {
                    "name": "假山",
                    "raw_name": "假山",
                    "quote": segment.text,
                    "segment_ids": [segment.id],
                    "subject_role": "PRIMARY",
                    "visit_intent": "NOT_RECOMMENDED",
                    "poi_policy": "SKIP",
                }
            ],
        )
        assert mentions
        metrics = {}
        assert resolve_mentions_with_amap(
            db, Settings(_env_file=None), mentions, api_key="unused", metrics=metrics
        ) == (0, 1)
        assert mentions[0].place_id is None and mentions[0].resolution_status == "REVIEW"
        assert metrics["amap_request_count"] == 0
    reviews = client.get("/api/travel/place-reviews").json()
    assert any("AUTHOR_NOT_RECOMMENDED" in r["reason_codes"] for r in reviews)


def test_readable_timing_and_warnings_never_render_internal_rank():
    from types import SimpleNamespace

    from zhijian.services.travel_brief import travel_brief

    w = SimpleNamespace(
        provenance="SOURCE_FACT",
        source_text="十二月下旬开始，这里几乎天天有雾凇。",
        month=12,
        month_segment="LATE",
        season=None,
        day_time_slot=None,
        suitability="INFORMATIONAL",
        period_type="OTHER",
    )
    result = travel_brief({"themes": ["雾凇"], "warnings": ["有风会吹散雾凇。"]}, [w])
    assert result["timing"] == "视频提到，从12月下旬开始几乎天天有雾凇。"
    assert result["warnings"] == ["有风会吹散雾凇。"]
    assert "可以考虑" not in str(result) and "需注意" not in str(result)
