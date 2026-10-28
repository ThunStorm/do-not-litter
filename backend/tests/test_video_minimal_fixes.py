"""Offline counterexamples for the frozen minimal video work packages."""

import pytest

from zhijian.services.video_support import _insights_from_candidate


@pytest.mark.parametrize(
    ("item", "texts"),
    [
        ({"highlights": ["免费入园"]}, {"s1": "门票100元"}),
        ({"price": "50元"}, {"s1": "门票100元"}),
        ({"best_months": [5]}, {"s1": "十月适合去"}),
        ({"recommended_items": ["海蛎煎"]}, {"s1": "不推荐海蛎煎"}),
        (
            {
                "recommended_items": [
                    {"name": "海蛎煎", "segment_ids": ["s2"], "source_quote": "海蛎煎值得点"}
                ]
            },
            {"s1": "甲店门票100元", "s2": "海蛎煎值得点"},
        ),
        (
            {
                "recommended_items": [
                    {"name": "海蛎煎", "segment_ids": ["s1"], "source_quote": "海蛎煎值得点"}
                ]
            },
            {"s1": "门票100元"},
        ),
    ],
)
def test_wp1_unsupported_fields_never_become_facts(item, texts):
    assert not _insights_from_candidate(item, ["s1"], texts)


@pytest.mark.parametrize(
    ("item", "quote"),
    [
        ({"recommended_items": ["海蛎煎"]}, "海蛎煎值得点"),
        ({"highlights": ["推荐海蛎煎"]}, "海蛎煎值得点"),
        ({"best_months": [10]}, "十月最适合去"),
        ({"best_seasons": ["秋季"]}, "秋季适合去"),
        ({"price": "100元"}, "门票100元"),
    ],
)
def test_wp1_supported_fields_survive(item, quote):
    result = _insights_from_candidate(item, ["s1"], {"s1": quote})
    assert len(result) == 1
    assert result[0]["segment_ids"] == ["s1"]
    assert result[0]["source_quote"] == quote


@pytest.mark.parametrize("good_index,expected_attempts", [(1, 2), (3, 3)])
def test_wp2_quality_rejection_tries_next_track_with_three_request_limit(good_index, expected_attempts):
    from zhijian.resolvers.video.bilibili import SubtitleTrack, first_usable_subtitle

    tracks = [SubtitleTrack(f"https://example.test/{i}", str(i), str(i)) for i in range(5)]
    attempts = []

    def fetch(track):
        attempts.append(track.language)
        return [{"text": "good" if int(track.language) == good_index else "bad"}]

    selected, _, failures = first_usable_subtitle(
        tracks, fetch, accept=lambda track, rows: rows[0]["text"] == "good"
    )
    assert len(attempts) == expected_attempts
    assert (selected is not None) == (good_index < 3)
    assert len(failures) == expected_attempts - int(selected is not None)


def test_wp2_youtube_prefers_vtt_and_skips_srv3():
    from zhijian.resolvers.video.youtube import YouTubeAdapter

    tracks = YouTubeAdapter._subtitle_tracks(
        {
            "subtitles": {
                "zh": [
                    {"ext": "srv3", "url": "https://example.test/xml"},
                    {"ext": "vtt", "url": "https://example.test/vtt"},
                ],
                "en": [{"ext": "srv3", "url": "https://example.test/xml"}],
            }
        }
    )
    assert [t.url for t in tracks] == ["https://example.test/vtt"]


def replay_fixture(db):
    from zhijian.db.models import AINote, AINoteVersion, Job, Source, VideoAsset, VideoScreenshot
    from zhijian.services.video_support import materialize_transcript

    source = Source(source_type="URL", locator="fixture://minimal")
    db.add(source)
    db.flush()
    asset = VideoAsset(source_id=source.id, canonical_url=source.locator, platform="YOUTUBE")
    db.add(asset)
    db.flush()
    tr, segments = materialize_transcript(
        db,
        source,
        asset,
        [{"text": "甲地到乙地自驾。", "start_ms": 0, "end_ms": 10000}],
        source_kind="ASR",
        metadata={"validation_status": "LOCAL_ASR"},
    )
    note = AINote(video_asset_id=asset.id)
    db.add(note)
    db.flush()
    version = AINoteVersion(ai_note_id=note.id, version=1, markdown="existing note", transcript_version=1)
    db.add(version)
    db.flush()
    note.current_version_id = version.id
    job = Job(
        job_type="TRAVEL",
        status="RUNNING",
        payload_json={"video_asset_id": asset.id, "note_id": note.id, "transcript_id": tr.id},
    )
    db.add(job)
    db.add(VideoScreenshot(video_asset_id=asset.id, ai_note_version_id=version.id, planned_timestamp_ms=1000))
    db.commit()
    return asset, note, version, job, segments


@pytest.mark.parametrize("failure", ["download", "extract", "cancel", "login", "success"])
def test_wp3_replay_preserves_core_and_error_classification(app_and_session, tmp_path, monkeypatch, failure):
    from zhijian.core.config import Settings
    from zhijian.db.models import ContentItem
    from zhijian.providers.media import MediaDownloadError
    from zhijian.services import video_pipeline as pipeline
    from zhijian.services.jobs import JobCancelled

    _, factory = app_and_session
    with factory() as db:
        _, _, version, job, _ = replay_fixture(db)
        media = tmp_path / "fake.mp4"
        media.write_bytes(b"fixture")
        calls = []

        def download(*a, **k):
            calls.append("download")
            if failure == "download":
                raise MediaDownloadError("unavailable")
            if failure == "login":
                raise MediaDownloadError("login", code="VIDEO_LOGIN_REQUIRED")
            return media

        def extract(*a, **k):
            calls.append("extract")
            if failure == "extract":
                raise RuntimeError("frame failure")
            if failure == "cancel":
                raise JobCancelled("cancelled")
            return 1, None

        monkeypatch.setattr(pipeline, "download_screenshot_video", download)
        monkeypatch.setattr(pipeline, "extract_screenshots", extract)

        def no_ai(*a, **k):
            pytest.fail("screenshot replay called AI")

        monkeypatch.setattr(pipeline, "get_or_create_grounded_map", no_ai)
        monkeypatch.setattr(pipeline, "generate_note", no_ai)
        settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
        settings.ensure_directories()
        if failure == "cancel":
            with pytest.raises(JobCancelled):
                pipeline._process_video_replay(db, job, settings, "DOWNLOAD_VIDEO_FOR_FRAMES")
        elif failure == "login":
            with pytest.raises(pipeline.NeedsUser):
                pipeline._process_video_replay(db, job, settings, "DOWNLOAD_VIDEO_FOR_FRAMES")
        else:
            pipeline._process_video_replay(db, job, settings, "DOWNLOAD_VIDEO_FOR_FRAMES")
            assert job.status == ("COMPLETED" if failure == "success" else "PARTIAL_SUCCESS")
            content = db.get(ContentItem, job.result_content_id)
            assert bool(content.structured_json["screenshot_error"]) == (failure != "success")
        assert version.markdown == "existing note"
        assert calls.count("download") == 1


def test_wp3_cache_disappears_after_public_replay_gate(app_and_session, tmp_path, monkeypatch):
    from datetime import timedelta

    from zhijian.core.config import Settings
    from zhijian.core.storage import storage_ref
    from zhijian.core.time import utc_now
    from zhijian.db.models import JobStep, JobStepArtifact
    from zhijian.services import job_replay, video_pipeline

    _, factory = app_and_session
    settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
    settings.ensure_directories()
    monkeypatch.setattr(job_replay, "get_settings", lambda: settings)
    with factory() as db:
        _, _, _, job, _ = replay_fixture(db)
        media = settings.cache_dir / "fixture.mp4"
        media.write_bytes(b"fixture")
        job.status = "FAILED"
        job.current_step = "EXTRACT_SCREENSHOTS"
        db.add_all(
            [
                JobStep(job_id=job.id, step_name="DOWNLOAD_VIDEO_FOR_FRAMES", status="COMPLETED"),
                JobStep(job_id=job.id, step_name="EXTRACT_SCREENSHOTS", status="FAILED"),
                JobStepArtifact(
                    job_id=job.id,
                    step_name="DOWNLOAD_VIDEO_FOR_FRAMES",
                    artifact_type="STEP_OUTPUT",
                    status="AVAILABLE",
                    replayable_until=utc_now() + timedelta(hours=1),
                    artifact_ref_json={"cache_path": storage_ref(media, settings)},
                ),
            ]
        )
        db.commit()
        assert job_replay.replay_options(db, job)["step_replay_available"]
        job_replay.queue_step_replay(db, job, "EXTRACT_SCREENSHOTS")
        media.unlink()
        video_pipeline._process_video_replay(db, job, settings, "EXTRACT_SCREENSHOTS")
        assert job.status == "PARTIAL_SUCCESS"


def add_map_artifact(db, asset, guide, *, identity="one"):
    from sqlalchemy import select

    from zhijian.db.models import GroundedMapArtifact, Transcript

    tr = db.scalar(select(Transcript).where(Transcript.video_asset_id == asset.id))
    artifact = GroundedMapArtifact(
        video_asset_id=asset.id,
        transcript_id=tr.id,
        transcript_version=1,
        content_hash=identity,
        semantic_hash=identity,
        prompt_version="fixture",
        supplement_hash="",
        provider="FIXTURE",
        model="FIXTURE",
        semantic_options_json={"route_guides": [guide]},
    )
    db.add(artifact)
    db.flush()
    return artifact


@pytest.mark.parametrize("local", [False, True])
def test_wp4_homonym_stop_requires_local_evidence(app_and_session, local):
    from zhijian.db.models import Place, PlaceMention
    from zhijian.services.route_guides import list_route_guides

    _, factory = app_and_session
    with factory() as db:
        asset, note, version, _, segments = replay_fixture(db)
        artifact = add_map_artifact(
            db,
            asset,
            {"id": "g", "stops": [{"raw_name": "东湖"}], "evidence": {"segment_ids": [segments[0].id]}},
        )
        version.grounded_map_artifact_id = artifact.id
        place = Place(
            name="东湖",
            canonical_name="东湖",
            province="甲省",
            place_type="SCENIC_AREA",
            latitude=1,
            longitude=1,
        )
        db.add(place)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=version.id,
            name="东湖",
            raw_name="东湖",
            place_id=place.id,
            province_hint="甲省",
            resolution_status="CONFIRMED",
            segment_ids_json=[segments[0].id if local else "other-region"],
        )
        db.add(mention)
        db.commit()
        stop = list_route_guides(db, note_id=note.id)[0]["stops"][0]
        assert bool(stop["place_id"]) == local


def test_wp4_route_conditions_and_evidence_are_not_deduplicated():
    from zhijian.services.route_guides import extract_routes

    texts = {"s1": "自驾甲地到乙地，冬季甲路封路。", "s2": "自驾甲地到乙地，夏季甲路通行。"}
    claims = [
        {
            "segment_ids": [sid],
            "supporting_quote": quote,
            "route": {
                "mode": "SELF_DRIVE",
                "stops": ["甲地", "乙地"],
                "road": "甲路",
                "conditions": [{"subject": "甲路", "quote": quote, "segment_ids": [sid]}],
            },
        }
        for sid, quote in texts.items()
    ]
    routes = extract_routes(claims, texts)
    assert len(routes) == 2
    assert {r["conditions"][0]["quote"] for r in routes} == set(texts.values())


def test_wp4_v07_old_note_must_not_switch_to_new_artifact(app_and_session):
    from datetime import timedelta

    from zhijian.core.time import utc_now
    from zhijian.services.route_guides import list_route_guides

    _, factory = app_and_session
    with factory() as db:
        asset, note, version, _, _ = replay_fixture(db)
        old = add_map_artifact(db, asset, {"id": "old", "stops": []}, identity="old")
        old.created_at = utc_now() - timedelta(hours=1)
        version.grounded_map_artifact_id = old.id
        db.commit()
        assert list_route_guides(db, note_id=note.id)[0]["artifact_id"] == old.id
        newer = add_map_artifact(db, asset, {"id": "new", "stops": []}, identity="new")
        newer.created_at = utc_now()
        db.commit()
        assert list_route_guides(db, note_id=note.id)[0]["artifact_id"] == old.id


@pytest.mark.parametrize("good_index,expected_http,expected_asr", [(1, 2, 0), (3, 3, 1)])
def test_wp2_pipeline_counts_subtitle_and_asr_calls(
    app_and_session, tmp_path, monkeypatch, good_index, expected_http, expected_asr
):
    from types import SimpleNamespace

    from zhijian.core.config import Settings
    from zhijian.db.models import Source
    from zhijian.resolvers.video.bilibili import ResolvedVideo, SubtitleTrack
    from zhijian.services import video_pipeline as pipeline
    from zhijian.services.jobs import JobCancelled
    from zhijian.services.video_support import materialize_transcript

    _, factory = app_and_session
    with factory() as db:
        asset, _, _, job, _ = replay_fixture(db)
        source = db.get(Source, asset.source_id)
        job.payload_json = {
            **job.payload_json,
            "source_id": source.id,
            "locator": asset.canonical_url,
            "video_platform": "YOUTUBE",
        }
        calls = {"http": 0, "asr": 0}
        rows = [{"text": "甲地好吃的海蛎煎。", "start_ms": 0, "end_ms": 10000}]

        def fetch(track):
            calls["http"] += 1
            return rows if int(track.track_id) == good_index else []

        resolved = ResolvedVideo(
            asset.canonical_url,
            "",
            None,
            "",
            1,
            "fixture",
            "fixture",
            10000,
            None,
            [
                SubtitleTrack("https://example.test", "zh-CN", "中文", track_id=str(i), platform="YOUTUBE")
                for i in range(5)
            ],
        )
        monkeypatch.setattr(
            pipeline,
            "video_adapter_for_platform",
            lambda *a, **k: SimpleNamespace(resolve=lambda *a: resolved, fetch_subtitle_segments=fetch),
        )
        monkeypatch.setattr(pipeline, "materialize_cover", lambda *a: None)

        def asr(_db, _job, _settings, _source, _asset, *a):
            calls["asr"] += 1
            tr, segs = materialize_transcript(
                _db, _source, _asset, rows, source_kind="ASR", metadata={"validation_status": "LOCAL_ASR"}
            )
            return None, tr, segs

        monkeypatch.setattr(pipeline, "_download_and_transcribe_audio", asr)

        def stop_before_ai(*a, **k):
            raise JobCancelled("offline measurement ends before AI")

        monkeypatch.setattr(pipeline, "correct_transcript", stop_before_ai)
        settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
        settings.ensure_directories()
        pipeline.process_video_job(db, job, settings)
        assert calls == {"http": expected_http, "asr": expected_asr}


@pytest.mark.parametrize("month,word", [(11, "十一月"), (12, "十二月")])
def test_wp1_two_digit_chinese_month_is_supported(month, word):
    assert _insights_from_candidate({"best_months": [month]}, ["s"], {"s": word + "适合去"})


def test_wp1_noncontiguous_quote_cannot_be_supported():
    assert not _insights_from_candidate(
        {
            "recommended_items": [
                {"name": "海蛎煎", "segment_ids": ["s1", "s3"], "source_quote": "海蛎煎值得点"}
            ]
        },
        ["s1", "s3"],
        {"s1": "海蛎煎", "s2": "另一家店", "s3": "值得点"},
    )


def test_wp1_materialization_revalidates_old_untrusted_metadata(app_and_session):
    from sqlalchemy import select

    from zhijian.db.models import Place, PlaceInsightItem, PlaceMention
    from zhijian.services.video_support import materialize_place_insights

    _, factory = app_and_session
    with factory() as db:
        asset, _, version, _, segments = replay_fixture(db)
        segments[0].text = segments[0].corrected_text = "门票100元"
        place = Place(name="甲地", canonical_name="甲地", place_type="SCENIC_AREA", latitude=1, longitude=1)
        db.add(place)
        db.flush()
        sid = segments[0].id
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=version.id,
            name="甲地",
            place_id=place.id,
            segment_ids_json=[sid],
            metadata_json={
                "insights": [
                    {
                        "insight_type": "PRICE",
                        "value_text": value,
                        "segment_ids": [sid],
                        "source_quote": quote,
                    }
                    for value, quote in [("免费", "门票100元"), ("100元", "门票100元"), ("50元", "门票50元")]
                ]
            },
        )
        db.add(mention)
        db.flush()
        materialize_place_insights(db, mention)
        db.flush()
        stored = db.scalars(
            select(PlaceInsightItem).where(PlaceInsightItem.place_mention_id == mention.id)
        ).all()
        assert [i.value_text for i in stored] == ["100元"]


@pytest.mark.parametrize("code", ["VIDEO_NETWORK_FAILED", "VIDEO_LOGIN_REQUIRED"])
def test_wp2_network_and_login_are_bounded(code):
    from zhijian.resolvers.video.bilibili import SubtitleTrack, VideoResolveError, first_usable_subtitle

    attempts = []

    def fetch(track):
        attempts.append(track)
        raise VideoResolveError(code, "safe failure")

    tracks = [SubtitleTrack("https://example.test", "zh-CN", "中文")] * 5
    if code == "VIDEO_LOGIN_REQUIRED":
        with pytest.raises(VideoResolveError):
            first_usable_subtitle(tracks, fetch)
        assert len(attempts) == 1
    else:
        assert first_usable_subtitle(tracks, fetch)[0] is None
        assert len(attempts) == 3


def test_wp4_distinct_conditions_get_distinct_guide_ids():
    from zhijian.services.route_guides import extract_routes

    quote = "自驾甲地到乙地，冬季甲路封路，夏季甲路通行。"
    claims = [
        {
            "segment_ids": ["s"],
            "supporting_quote": quote,
            "route": {
                "mode": "SELF_DRIVE",
                "stops": ["甲地", "乙地"],
                "road": "甲路",
                "conditions": [{"subject": "甲路", "quote": condition, "segment_ids": ["s"]}],
            },
        }
        for condition in ["冬季甲路封路", "夏季甲路通行"]
    ]
    routes = extract_routes(claims, {"s": quote})
    assert len(routes) == len({r["id"] for r in routes}) == 2


def test_wp1_price_substring_is_not_same_amount():
    assert not _insights_from_candidate({"price": "50元"}, ["s"], {"s": "门票150元"})


def test_wp1_shared_segment_does_not_transfer_other_places_fact(app_and_session):
    from zhijian.core.config import Settings
    from zhijian.services.video_support import extract_place_mentions

    _, factory = app_and_session
    with factory() as db:
        asset, _, _, _, segments = replay_fixture(db)
        segments[0].text = segments[0].corrected_text = "甲地门票100元。乙地免费入园。"
        mentions = extract_place_mentions(
            db,
            Settings(_env_file=None),
            asset,
            None,
            segments,
            candidates=[
                {
                    "name": name,
                    "raw_name": name,
                    "quote": quote,
                    "segment_ids": [segments[0].id],
                    "highlights": ["免费入园"],
                }
                for name, quote in [("甲地", "甲地门票100元"), ("乙地", "乙地免费入园")]
            ],
        )
        assert mentions[0].metadata_json["insights"] == []
        assert len(mentions[1].metadata_json["insights"]) == 1


def test_wp4_same_words_in_different_source_segments_keep_unique_identity():
    from zhijian.services.route_guides import extract_routes

    quote = "自驾甲地到乙地。"
    claims = [
        {
            "segment_ids": [sid],
            "supporting_quote": quote,
            "route": {"mode": "SELF_DRIVE", "stops": ["甲地", "乙地"]},
        }
        for sid in ["s1", "s2"]
    ]
    routes = extract_routes(claims, {"s1": quote, "s2": quote})
    assert len(routes) == len({r["id"] for r in routes}) == 2


@pytest.mark.parametrize("quote", ["门票大概100元", "听说免费入园"])
def test_wp1_explicit_uncertainty_does_not_become_source_fact(quote):
    item = {"price": "100元"} if "100" in quote else {"highlights": ["免费入园"]}
    assert not _insights_from_candidate(item, ["s"], {"s": quote})


@pytest.mark.parametrize("case", ["legacy_unbound", "wrong_asset", "wrong_transcript"])
def test_v07_missing_or_mismatched_binding_never_uses_latest(app_and_session, case):
    from zhijian.services.route_guides import list_route_guides

    _, factory = app_and_session
    with factory() as db:
        asset, note, version, _, _ = replay_fixture(db)
        artifact = add_map_artifact(db, asset, {"id": "g", "stops": []})
        if case != "legacy_unbound":
            version.grounded_map_artifact_id = artifact.id
        if case == "wrong_asset":
            from zhijian.db.models import Source, VideoAsset

            other_source = Source(source_type="URL", locator="fixture://other")
            db.add(other_source)
            db.flush()
            other = VideoAsset(source_id=other_source.id, canonical_url="fixture://other")
            db.add(other)
            db.flush()
            artifact.video_asset_id = other.id
        if case == "wrong_transcript":
            artifact.transcript_version = 2
        db.commit()
        assert list_route_guides(db, note_id=note.id) == []


def test_v07_migration_preserves_old_rows_and_enforces_reference(tmp_path, monkeypatch):
    import sqlite3
    from pathlib import Path
    from types import SimpleNamespace

    from alembic.config import Config

    from alembic import command

    db_path = tmp_path / "app.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE grounded_map_artifacts (id VARCHAR(64) PRIMARY KEY)")
        db.execute("CREATE TABLE ai_note_versions (id VARCHAR(64) PRIMARY KEY, markdown TEXT)")
        db.execute("INSERT INTO ai_note_versions VALUES ('ntv_old', 'old note')")
        db.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        db.execute("INSERT INTO alembic_version VALUES ('0026')")
        before = db.execute("SELECT * FROM ai_note_versions").fetchall()
    monkeypatch.setattr("zhijian.core.config.get_settings", lambda: SimpleNamespace(database_path=db_path))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0027")
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT id,markdown FROM ai_note_versions").fetchall() == before
        assert db.execute("SELECT grounded_map_artifact_id FROM ai_note_versions").fetchall() == [(None,)]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE ai_note_versions SET grounded_map_artifact_id='missing-artifact'")
        db.rollback()
    command.downgrade(config, "0026")
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT * FROM ai_note_versions").fetchall() == before
    command.upgrade(config, "0027")
