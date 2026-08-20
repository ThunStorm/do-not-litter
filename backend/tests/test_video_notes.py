from __future__ import annotations

from sqlalchemy import select

from zhijian.core.config import Settings
from zhijian.db.models import AINote, AINoteSection, AINoteVersion, Job, Source, Transcript, VideoAsset
from zhijian.domain.enums import JobType
from zhijian.resolvers.video.url_parser import parse_bilibili_url
from zhijian.services.capture import create_capture_job
from zhijian.services.video_support import materialize_transcript


def test_bilibili_parser_keeps_bvid_and_selected_page() -> None:
    parsed = parse_bilibili_url("https://www.bilibili.com/video/BV1Tvbe6EEw2/?p=3")
    assert parsed.bvid == "BV1Tvbe6EEw2"
    assert parsed.page_number == 3
    assert not parsed.is_short


def test_video_capture_only_creates_durable_job_without_network(app_and_session) -> None:
    _, factory = app_and_session
    settings = Settings(_env_file=None, data_dir="/tmp/zhijian-video-test")
    with factory() as db:
        source, job = create_capture_job(
            db,
            settings,
            locator="https://www.bilibili.com/video/BV1Tvbe6EEw2/",
            source_type="URL",
        )
        assert source.source_type == "URL"
        assert job.job_type == JobType.TRAVEL.value
        assert job.payload_json["video_platform"] == "BILIBILI"
        assert db.scalar(select(Job).where(Job.id == job.id)) is not None


def test_timestamped_transcript_reuses_same_fingerprint(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(
            source_type="URL", locator="https://www.bilibili.com/video/BV1Tvbe6EEw2/", title="fixture"
        )
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id,
            canonical_url=source.locator,
            bvid="BV1Tvbe6EEw2",
            cid="123",
            page_number=1,
            title="fixture",
            uploader="tester",
        )
        db.add(asset)
        db.commit()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": "第一段", "start_ms": 0, "end_ms": 1500},
                {"text": "第二段", "start_ms": 1500, "end_ms": 3200},
            ],
            source_kind="FIXTURE",
        )
        reused, reused_segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": "第一段", "start_ms": 0, "end_ms": 1500},
                {"text": "第二段", "start_ms": 1500, "end_ms": 3200},
            ],
            source_kind="FIXTURE",
        )
        assert transcript.id == reused.id
        assert len(segments) == len(reused_segments) == 2
        assert db.scalar(select(Transcript).where(Transcript.video_asset_id == asset.id)) is not None


def test_video_note_api_returns_versioned_sections(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(
            source_type="URL", locator="https://www.bilibili.com/video/BV1Tvbe6EEw2/", title="fixture"
        )
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id,
            canonical_url=source.locator,
            bvid="BV1Tvbe6EEw2",
            cid="123",
            page_number=1,
            title="测试视频",
            uploader="tester",
        )
        db.add(asset)
        db.flush()
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="# 测试视频",
            overview="可回溯的摘要",
            transcript_version=1,
        )
        db.add(version)
        db.flush()
        db.add(
            AINoteSection(
                ai_note_version_id=version.id,
                ordinal=0,
                heading="开场",
                body_markdown="内容",
                segment_ids_json=["seg-fixture"],
                start_ms=0,
                end_ms=3000,
            )
        )
        note.current_version_id = version.id
        db.commit()
        note_id = note.id
    response = client.get(f"/api/video-notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["sections"][0]["heading"] == "开场"
