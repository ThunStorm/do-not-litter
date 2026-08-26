from __future__ import annotations

import json
import sys
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

import zhijian.services.video_support as video_support
from zhijian.core.config import Settings
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    ContentItem,
    Job,
    Setting,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.domain.enums import JobType
from zhijian.providers.llm import FallbackLLMProvider, LLMResult, OllamaProvider
from zhijian.providers.media import YtDlpMediaProvider
from zhijian.resolvers.video.url_parser import parse_bilibili_url
from zhijian.services.capture import create_capture_job
from zhijian.services.jobs import JobCancelled
from zhijian.services.transcript_retention import purge_expired_transcripts
from zhijian.services.video_support import (
    correct_transcript,
    materialize_transcript,
    normalized_confidence,
    provider_for_role,
)


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


def test_ai_correction_is_persisted_before_note_generation(monkeypatch, app_and_session) -> None:
    _, factory = app_and_session

    class Provider:
        def generate_json(self, messages, model):
            assert any("保留作者自然口语语气" in message["content"] for message in messages)
            values = json.loads(messages[-1]["content"])["segments"]
            if len(values) > 1:
                return SimpleNamespace(content='{"segments":[', provider="deepseek", model=model)
            item = values[0]
            corrected = {
                "闪西兰田的水路案": "西安蓝田水陆庵",
                "国家深林公元": "国家森林公园",
                "窗口鸡很短": "窗口期很短",
            }[item["raw_text"]]
            return SimpleNamespace(
                content=(
                    '{"segments":[{"id":"'
                    + item["id"]
                    + '","corrected_text":"'
                    + corrected
                    + '","confidence":0.96,"reason":"纠正同音字"}]}'
                ),
                provider="deepseek",
                model=model,
            )

    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/video", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="西安旅行")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": "闪西兰田的水路案", "start_ms": 0, "end_ms": 1200},
                {"text": "国家深林公元", "start_ms": 1200, "end_ms": 2400},
                {"text": "窗口鸡很短", "start_ms": 2400, "end_ms": 3600},
            ],
            source_kind="ASR",
        )
        db.add(
            Setting(
                key="prompt:supplements",
                value_json={"transcript_correction": "保留作者自然口语语气。"},
            )
        )
        db.commit()
        provider = Provider()
        monkeypatch.setattr(
            "zhijian.services.video_support.provider_for_role",
            lambda *_args: (provider, "deepseek", "deepseek-chat"),
        )
        correct_transcript(db, Settings(_env_file=None), asset, transcript, segments)
        assert segments[0].raw_text == "闪西兰田的水路案"
        assert segments[0].corrected_text == "西安蓝田水陆庵"
        assert segments[0].correction_status == "CORRECTED"
        assert segments[1].corrected_text == "国家森林公园"
        assert segments[2].corrected_text == "窗口期很短"
        assert transcript.text == "西安蓝田水陆庵\n国家森林公园\n窗口期很短"


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
    legacy = client.get(f"/api/video-notes/{version.id}")
    assert legacy.status_code == 200
    assert legacy.json()["id"] == note_id
    assert client.get("/api/video-notes/ntv_missing").status_code == 404


def test_ollama_requests_release_model_immediately(monkeypatch) -> None:
    captured: dict = {}

    def post(*_args, **kwargs):
        captured.update(kwargs["json"])
        return httpx.Response(
            200,
            json={"message": {"content": '{"ok":true}'}, "prompt_eval_count": 1},
            request=httpx.Request("POST", "http://ollama.test/api/chat"),
        )

    monkeypatch.setattr(httpx, "post", post)
    OllamaProvider("http://ollama.test").generate_json([{"role": "user", "content": "ping"}], model="qwen")
    assert captured["keep_alive"] == 0
    assert captured["format"] == "json"


def test_blank_primary_response_uses_fallback_model() -> None:
    class Provider:
        def __init__(self, content: str, name: str) -> None:
            self.content = content
            self.name = name

        def generate_json(self, _messages, *, model):
            return LLMResult(self.content, self.name, model, {})

    provider = FallbackLLMProvider(
        Provider("", "primary"),
        "primary-model",
        Provider('{"ok":true}', "fallback"),
        "fallback-model",
        retry_count=0,
        request_interval_seconds=0,
    )
    result = provider.generate_json([], model="ignored")
    assert result.content == '{"ok":true}'
    assert result.provider == "fallback"
    assert provider.primary_disabled is True
    second = provider.generate_json([], model="ignored")
    assert second.provider == "fallback"


def test_cancellation_is_checked_before_fallback_model() -> None:
    fallback_calls = 0

    class Primary:
        def generate_json(self, _messages, *, model):
            raise httpx.ConnectError(f"{model} unavailable")

    class Fallback:
        def generate_json(self, _messages, *, model):
            nonlocal fallback_calls
            fallback_calls += 1
            return LLMResult('{"ok":true}', "fallback", model, {})

    provider = FallbackLLMProvider(
        Primary(),
        "primary-model",
        Fallback(),
        "fallback-model",
        before_fallback=lambda: (_ for _ in ()).throw(JobCancelled("任务已取消")),
        retry_count=0,
        request_interval_seconds=0,
    )
    with pytest.raises(JobCancelled):
        provider.generate_json([], model="ignored")
    assert fallback_calls == 0


def test_llm_retry_policy_waits_before_calls_and_between_retries() -> None:
    attempts = 0
    sleeps: list[float] = []

    class Provider:
        def generate_json(self, _messages, *, model):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                request = httpx.Request("POST", "https://model.test/chat/completions")
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)
            return LLMResult('{"ok":true}', "primary", model, {})

    provider = FallbackLLMProvider(
        Provider(),
        "primary-model",
        None,
        None,
        retry_count=2,
        retry_wait_seconds=5,
        request_interval_seconds=1,
        sleeper=sleeps.append,
    )
    assert provider.generate_json([], model="ignored").content == '{"ok":true}'
    assert attempts == 3
    assert sleeps == [1, 60, 1, 60, 1]


def test_llm_attempt_callback_tracks_primary_and_fallback() -> None:
    attempts: list[tuple[str, str, int, bool, bool]] = []

    class Primary:
        def generate_json(self, _messages, *, model):
            request = httpx.Request("POST", "https://primary.test/chat/completions")
            raise httpx.HTTPStatusError(
                "unavailable", request=request, response=httpx.Response(503, request=request)
            )

    class Fallback:
        def generate_json(self, _messages, *, model):
            return LLMResult('{"ok":true}', "fallback", model, {"prompt_tokens": 3})

    provider = FallbackLLMProvider(
        Primary(),
        "primary-model",
        Fallback(),
        "fallback-model",
        retry_count=0,
        request_interval_seconds=0,
        on_attempt=lambda _provider, _model, route, attempt, chars, result, exc: attempts.append(
            (route, _model, attempt, result is not None, exc is not None)
        ),
    )
    assert (
        provider.generate_json([{"role": "user", "content": "ping"}], model="ignored").provider
        == "fallback"
    )
    assert attempts == [
        ("primary", "primary-model", 1, False, True),
        ("fallback", "fallback-model", 1, True, False),
    ]


def test_transcript_correction_chunks_limit_segment_count() -> None:
    segments = [SimpleNamespace(text="x" * 9, corrected_text="x" * 9) for _ in range(232)]
    chunks = video_support._transcript_chunks(
        segments,
        max_chars=video_support.TRANSCRIPT_CORRECTION_CHUNK_CHARS,
        max_segments=video_support.TRANSCRIPT_CORRECTION_BATCH_SIZE,
    )
    assert [len(chunk) for chunk in chunks] == [128, 104]


def test_transcript_model_route_overrides_general_route(monkeypatch, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        for profile_id, model in (("general", "general-model"), ("transcript", "transcript-model")):
            db.add(
                Setting(
                    key=f"model-profile:{profile_id}",
                    value_json={
                        "provider": "fixture",
                        "base_url": f"https://{profile_id}.test",
                        "model": model,
                    },
                )
            )
        db.add(
            Setting(
                key="model-routing",
                value_json={"primary_id": "general", "transcript_primary_id": "transcript"},
            )
        )
        db.commit()
        monkeypatch.setattr(
            video_support,
            "_provider_from_config",
            lambda config, *_args: (
                SimpleNamespace(base_url=config["base_url"]),
                config["provider"],
                config["model"],
            ),
        )
        provider, _, model = provider_for_role(db, Settings(_env_file=None), "transcript_correction")
        assert model == "transcript-model"
        assert provider.primary_model == "transcript-model"


def test_bilibili_screenshot_download_prefers_video_dash(monkeypatch, tmp_path) -> None:
    target = tmp_path / "video.mp4"
    target.write_bytes(b"video")
    captured: dict = {}

    class FakeYtDlp:
        def __init__(self, options):
            captured.update(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download):
            assert download is True
            return {"requested_downloads": [{"filepath": str(target)}]}

        def prepare_filename(self, _info):
            return str(target)

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYtDlp))
    path = YtDlpMediaProvider(tmp_path, max_bytes=1024, timeout=10).download_video("https://www.bilibili.com/video/BV1JH826zEKC")
    assert path == target
    assert captured["format"] == "bv*[ext=mp4]/bv*/best"
    assert captured["format_sort"] == ["res:720"]
    assert captured["http_headers"]["Referer"] == "https://www.bilibili.com"


def test_confidence_labels_do_not_abort_place_extraction() -> None:
    assert normalized_confidence("high") == 0.85
    assert normalized_confidence("中") == 0.6
    assert normalized_confidence("bad-value") == 0.0


def test_transcript_correction_stops_before_next_batch_when_cancelled(monkeypatch) -> None:
    monkeypatch.setattr(
        video_support,
        "ensure_job_active",
        lambda *_args: (_ for _ in ()).throw(JobCancelled("任务已取消")),
    )
    monkeypatch.setattr(
        video_support,
        "provider_for_role",
        lambda *_args: (_ for _ in ()).throw(AssertionError("取消后不应创建模型调用")),
    )
    segment = SimpleNamespace(correction_status="UNCORRECTED")
    with pytest.raises(JobCancelled):
        correct_transcript(
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            [segment],
            SimpleNamespace(),
        )


def test_transcript_correction_http_failure_does_not_split_and_amplify(monkeypatch) -> None:
    calls = 0

    class Provider:
        def generate_json(self, _messages, *, model):
            nonlocal calls
            calls += 1
            raise httpx.ConnectError(f"{model} unavailable")

    monkeypatch.setattr(
        video_support,
        "provider_for_role",
        lambda *_args: (Provider(), "fixture", "fixture-model"),
    )
    segments = [
        SimpleNamespace(
            id=f"seg_{index}",
            correction_status="UNCORRECTED",
            raw_text="待校对文本",
            text="待校对文本",
            corrected_text=None,
            locator_json={"start_ms": index * 1000, "end_ms": (index + 1) * 1000},
        )
        for index in range(4)
    ]
    with pytest.raises(httpx.ConnectError):
        correct_transcript(
            SimpleNamespace(),
            SimpleNamespace(video_note_chunk_chars=12_000),
            SimpleNamespace(title="fixture"),
            SimpleNamespace(),
            segments,
        )
    assert calls == 1


def test_transcript_export_and_retention_purge(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(
            source_type="URL",
            locator="https://www.bilibili.com/video/BV-retention",
            title="fixture",
        )
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="保留测试")
        db.add(asset)
        db.flush()
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "完整转写", "start_ms": 0, "end_ms": 1000}],
            source_kind="FIXTURE",
        )
        exported = client.get(f"/api/video-notes/{note.id}/transcript/export")
        assert exported.status_code == 200
        assert "完整转写" in exported.text
        transcript.retention_until = transcript.created_at - timedelta(days=1)
        db.commit()
        assert purge_expired_transcripts(db) == 1
        db.refresh(transcript)
        assert transcript.purged_at is not None and transcript.text == ""
        assert db.get(type(segments[0]), segments[0].id).text == ""
    assert client.get(f"/api/video-notes/{note.id}/transcript").status_code == 410
    assert client.get(f"/api/video-notes/{note.id}/transcript/export").status_code == 410


def test_delete_last_video_note_prunes_orphan_source_asset_and_transcript(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/delete", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="删除测试")
        db.add(asset)
        db.flush()
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="# 删除测试",
            overview="摘要",
            transcript_version=1,
        )
        db.add(version)
        db.flush()
        note.current_version_id = version.id
        content = ContentItem(
            content_type="VIDEO_NOTE",
            title=asset.title,
            source_id=source.id,
        )
        db.add(content)
        transcript, _ = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "保留的转写", "start_ms": 0, "end_ms": 1000}],
            source_kind="FIXTURE",
        )
        db.commit()
        note_id, source_id, asset_id, transcript_id, content_id = (
            note.id,
            source.id,
            asset.id,
            transcript.id,
            content.id,
        )
    response = client.delete(f"/api/video-notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "DELETED"
    assert response.json()["source_deleted"] is True
    with factory() as db:
        assert db.get(AINote, note_id) is None
        assert db.get(ContentItem, content_id) is None
        assert db.get(Source, source_id) is None
        assert db.get(VideoAsset, asset_id) is None
        assert db.get(Transcript, transcript_id) is None
