from __future__ import annotations

import json
import sys
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

import zhijian.services.video_support as video_support
from zhijian.ai.transcript_quality import correction_candidates
from zhijian.core.config import Settings
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    ContentItem,
    Job,
    Place,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    PlaceVisitWindow,
    Setting,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.domain.enums import JobType
from zhijian.providers.amap import POICandidate
from zhijian.providers.llm import FallbackLLMProvider, LLMResult, OllamaProvider
from zhijian.providers.media import YtDlpMediaProvider
from zhijian.resolvers.video.bilibili import SubtitleTrack
from zhijian.resolvers.video.url_parser import parse_bilibili_url
from zhijian.services.capture import create_capture_job
from zhijian.services.jobs import JobCancelled
from zhijian.services.transcript_retention import purge_expired_transcripts
from zhijian.services.video_pipeline import (
    NeedsUser,
    _subtitle_decision,
    _trusted_transcript_or_raise,
)
from zhijian.services.video_support import (
    _section_facts,
    build_place_notes,
    correct_transcript,
    extract_place_mentions,
    generate_note,
    materialize_place_insights,
    materialize_transcript,
    normalized_confidence,
    provider_for_role,
    resolve_mentions_with_amap,
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


def test_transcript_repairs_only_the_known_tenfold_timeline(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/timing", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id, canonical_url=source.locator, title="fixture", duration_ms=1_000
        )
        db.add(asset)
        db.commit()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "字幕", "start_ms": 9_000, "end_ms": 10_000}],
            source_kind="BILIBILI_PLAYER",
        )
        assert segments[-1].locator_json["end_ms"] == 1_000


def test_generated_subtitle_is_rejected_without_retaining_text_or_url(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/video", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id,
            canonical_url=source.locator,
            bvid="BV1fixture",
            cid="123",
            page_number=1,
            title="九月旅行",
            duration_ms=530_000,
        )
        db.add(asset)
        db.commit()
        decision = _subtitle_decision(
            asset,
            SubtitleTrack(
                "https://aisubtitle.hdslb.com/bfs/subtitle/secret-query.json?token=not-for-audit",
                "ai-zh",
                "中文（自动生成）",
                track_id="track-fixture",
            ),
            [{"text": "露丝独自照顾妹妹长大", "start_ms": 84_490, "end_ms": 85_970}],
        )

    serialized = json.dumps(decision, ensure_ascii=False)
    assert decision["accepted"] is False
    assert decision["validation_reasons"] == ["PLATFORM_SUBTITLE_UNVERIFIED"]
    assert decision["generated"] is True
    assert "露丝" not in serialized
    assert "token=" not in serialized
    assert len(decision["url_sha256"]) == len(decision["body_sha256"]) == 64


def test_generated_subtitle_timeline_anomaly_is_rejected(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/timeline", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id,
            canonical_url=source.locator,
            title="fixture",
            duration_ms=530_000,
        )
        db.add(asset)
        db.commit()
        decision = _subtitle_decision(
            asset,
            SubtitleTrack("https://a.hdslb.com/ai-zh", "ai-zh", "中文（自动生成）"),
            [{"text": "错误字幕", "start_ms": 0, "end_ms": 838_520}],
        )

    assert decision["accepted"] is False
    assert decision["timeline_ratio"] == 1.5821
    assert "PLATFORM_SUBTITLE_TIMELINE_INVALID" in decision["validation_reasons"]


def test_note_generation_requires_a_trusted_transcript(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/trusted", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(
            source_id=source.id,
            canonical_url=source.locator,
            bvid="BV1fixture",
            cid="123",
            page_number=1,
            title="fixture",
            duration_ms=10_000,
        )
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "可信转写", "start_ms": 0, "end_ms": 1_000}],
            source_kind="WHISPER_CPP_ASR",
            metadata={
                "requested_bvid": asset.bvid,
                "requested_cid": asset.cid,
                "validation_status": "LOCAL_ASR",
            },
        )
        _trusted_transcript_or_raise(db, source, asset, transcript, segments)
        transcript.metadata_json = {**transcript.metadata_json, "validation_status": "REJECTED_PLATFORM"}
        db.commit()

        with pytest.raises(NeedsUser, match="来源一致性") as raised:
            _trusted_transcript_or_raise(db, source, asset, transcript, segments)

    assert raised.value.code == "TRANSCRIPT_SOURCE_MISMATCH"


def test_ai_correction_is_persisted_before_note_generation(monkeypatch, app_and_session) -> None:
    _, factory = app_and_session

    class Provider:
        def generate_json(self, messages, model):
            assert any("保留作者自然口语语气" in message["content"] for message in messages)
            values = json.loads(messages[-1]["content"])["segments"]
            corrected = {
                "闪西兰田的水路案": "西安蓝田水陆庵",
                "国家深林公元": "国家森林公园",
                "窗口鸡很短": "窗口期很短",
            }
            return SimpleNamespace(
                content=(
                    '{"changes":['
                    + ",".join(
                        '{"segment_id":"'
                        + item["id"]
                        + '","corrected_text":"'
                        + corrected[item["raw_text"]]
                        + '","confidence":0.96,"reason":"纠正同音字"}'
                        for item in values
                    )
                    + "]}"
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
        provider.generate_json([{"role": "user", "content": "ping"}], model="ignored").provider == "fallback"
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


def test_ollama_transcript_correction_caps_batch_size() -> None:
    assert video_support._correction_batch_size("ollama", 128) == 32
    assert video_support._correction_batch_size("OpenAI Compatible", 128) == 128


def test_transcript_stage_policy_overrides_general_route(monkeypatch, app_and_session) -> None:
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
                value_json={"primary_id": "general"},
            )
        )
        db.add(
            Setting(
                key="ai-stage-policy:TRANSCRIPT_CORRECTION",
                value_json={"remote_profile_id": "transcript"},
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
    path = YtDlpMediaProvider(tmp_path, max_bytes=1024, timeout=10).download_video(
        "https://www.bilibili.com/video/BV1JH826zEKC"
    )
    assert path == target
    assert captured["format"] == "bv*[ext=mp4]/bv*/best"
    assert captured["format_sort"] == ["res:720"]
    assert captured["http_headers"]["Referer"] == "https://www.bilibili.com"


def test_confidence_labels_do_not_abort_place_extraction() -> None:
    assert normalized_confidence("high") == 0.85
    assert normalized_confidence("中") == 0.6
    assert normalized_confidence("bad-value") == 0.0


def test_platform_subtitle_quality_gate_keeps_clean_segments_local() -> None:
    clean = SimpleNamespace(raw_text="清晰的平台字幕。", text="清晰的平台字幕。", confidence=0.99)
    broken = SimpleNamespace(raw_text="啊啊啊啊", text="啊啊啊啊", confidence=0.99)
    assert correction_candidates([clean, broken], source_kind="BILIBILI", force_full=False) == [broken]
    assert correction_candidates([clean], source_kind="BILIBILI", force_full=True) == [clean]


def test_section_facts_keep_only_evidence_bound_places() -> None:
    facts = _section_facts(
        {
            "section_facts": [
                {
                    "summary": "市场体验",
                    "segment_ids": ["seg_1"],
                    "places": [
                        {"name": "菜市场", "segment_ids": ["seg_1"]},
                        {"name": "无证据地点", "segment_ids": ["seg_missing"]},
                    ],
                }
            ]
        },
        {"seg_1"},
    )
    assert facts[0]["places"] == [{"name": "菜市场", "segment_ids": ["seg_1"]}]


def test_place_extraction_uses_persisted_map_facts_without_model(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/video", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db, source, asset, [{"text": "去菜市场", "start_ms": 0, "end_ms": 1000}], source_kind="ASR"
        )
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
        version = AINoteVersion(
            id="version",
            ai_note_id=note.id,
            version=1,
            markdown="# 旅行",
            transcript_version=1,
            map_facts_json=[
                {
                    "segment_ids": [segments[0].id],
                    "places": [
                        {
                            "name": "菜市场",
                            "segment_ids": [segments[0].id],
                            "confidence": "high",
                            "recommended_items": ["海蛎煎"],
                            "highlights": ["清晨最热闹"],
                            "best_months": [4],
                            "best_time_slots": ["MORNING"],
                        }
                    ],
                }
            ],
        )
        note.current_version_id = version.id
        db.add(version)
        db.commit()
        monkeypatch.setattr(
            video_support,
            "provider_for_role",
            lambda *_args: (_ for _ in ()).throw(AssertionError("默认地点聚合不应调用模型")),
        )
        mentions = extract_place_mentions(db, Settings(_env_file=None), asset, version, segments)
        assert len(mentions) == 1 and mentions[0].name == "菜市场"
        values = {(item["insight_type"], item["value_key"]) for item in mentions[0].metadata_json["insights"]}
        assert values == {
            ("RECOMMENDED_ITEM", "海蛎煎"),
            ("HIGHLIGHT", "清晨最热闹"),
            ("BEST_MONTH", "04"),
            ("BEST_TIME_SLOT", "morning"),
        }


def test_remote_place_extraction_uses_map_facts_not_full_transcript(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/remote-video", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "这段长转写不应再次送往地点模型", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="# 旅行",
            transcript_version=1,
            map_facts_json=[
                {
                    "segment_ids": [segments[0].id],
                    "places": [{"name": "菜市场", "segment_ids": [segments[0].id]}],
                }
            ],
        )
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            payload_json={"ai_overrides": {"EXTRACT_TRAVEL_FACTS": {"execution_mode": "REMOTE_ONLY"}}},
        )
        db.add_all([version, job])
        db.flush()
        captured: dict[str, object] = {}
        monkeypatch.setattr(video_support, "provider_for_role", lambda *_args: (object(), "remote", "model"))
        def cached(*_args, **kwargs):
            captured["messages"] = kwargs["messages"]
            return LLMResult(
                '{"places":[{"name":"菜市场","segment_ids":["' + segments[0].id + '"]}]}',
                "remote",
                "model",
                {},
            )

        monkeypatch.setattr(video_support, "_cached_stage_json", cached)
        mentions = extract_place_mentions(db, Settings(_env_file=None), asset, version, segments, job)
        assert mentions[0].name == "菜市场"
        context = captured["messages"][-1]["content"]
        assert "SectionFacts" in context
        assert "这段长转写不应再次送往地点模型" not in context


def test_time_phrases_fall_back_to_evidence_bound_place_windows(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/time-video", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行季节")
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {
                    "text": "黑瞎子岛十月中旬是最佳观赏期。当地五月到八月为休渔期。",
                    "start_ms": 0,
                    "end_ms": 1000,
                }
            ],
            source_kind="ASR",
        )
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="# 旅行",
            transcript_version=1,
            map_facts_json=[
                {
                    "segment_ids": [segments[0].id],
                    "places": [
                        {
                            "name": "黑瞎子岛",
                            "segment_ids": [segments[0].id],
                            "confidence": "high",
                            "visit_windows": [
                                {
                                    "period_type": "SNOW",
                                    "suitability": "RECOMMENDED",
                                    "months": [12],
                                    "source_text": "十二月雪季最美",
                                    "segment_ids": [segments[0].id],
                                }
                            ],
                        }
                    ],
                }
            ],
        )
        db.add(version)
        db.commit()
        monkeypatch.setattr(
            video_support,
            "provider_for_role",
            lambda *_args: (_ for _ in ()).throw(AssertionError("默认地点聚合不应调用模型")),
        )

        mention = extract_place_mentions(db, Settings(_env_file=None), asset, version, segments)[0]
        windows = mention.metadata_json["visit_windows"]
        assert {(item["period_type"], item["month"]) for item in windows} == {
            ("BEST_VIEWING", 10),
            ("FISHING_CLOSURE", 5),
            ("FISHING_CLOSURE", 6),
            ("FISHING_CLOSURE", 7),
            ("FISHING_CLOSURE", 8),
        }
        assert all(item["segment_ids"] == [segments[0].id] for item in windows)
        place = Place(
            name="黑瞎子岛",
            canonical_name="黑瞎子岛",
            origin="AI_EXTRACTED",
            place_type="SCENIC_AREA",
            latitude=48.3,
            longitude=134.5,
            resolution_status="CONFIRMED",
        )
        db.add(place)
        db.flush()
        mention.place_id = place.id
        materialize_place_insights(db, mention)
        db.commit()
        stored = db.scalars(select(PlaceVisitWindow).where(PlaceVisitWindow.place_id == place.id)).all()
        assert len(stored) == 5
        assert {item.suitability for item in stored if item.period_type == "FISHING_CLOSURE"} == {
            "RESTRICTED"
        }
        assert all(item.segment_ids_json == [segments[0].id] for item in stored)


def test_place_insights_keep_their_own_segment_and_quote() -> None:
    insights = video_support._insights_from_candidate(
        {
            "recommended_items": [
                {"name": "海蛎煎", "segment_ids": ["seg_2"], "source_quote": "海蛎煎值得点"}
            ],
            "best_months": [10],
        },
        ["seg_1", "seg_2"],
        {"seg_1": "十月最适合去。", "seg_2": "海蛎煎值得点。"},
    )

    assert insights == [
        {
            "insight_type": "RECOMMENDED_ITEM",
            "value_key": "海蛎煎",
            "value_text": "海蛎煎",
            "value_json": {"category": ""},
            "segment_ids": ["seg_2"],
            "source_quote": "海蛎煎值得点",
            "provenance": "SOURCE_FACT",
        },
        {
            "insight_type": "BEST_MONTH",
            "value_key": "10",
            "value_text": "10月",
            "value_json": {},
            "segment_ids": ["seg_1"],
            "source_quote": "十月最适合去。",
            "provenance": "SOURCE_FACT",
        },
    ]


def test_place_notes_keep_cross_source_facts_and_opinions_distinct(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/one", title="视频一")
        other_source = Source(source_type="URL", locator="https://example.test/two", title="视频二")
        db.add_all([source, other_source])
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        place = Place(
            name="陶陶居",
            canonical_name="陶陶居",
            origin="AI_EXTRACTED",
            place_type="RESTAURANT",
            latitude=23.11,
            longitude=113.24,
        )
        db.add_all([asset, place])
        db.flush()
        mention = PlaceMention(video_asset_id=asset.id, name="陶陶居", place_id=place.id)
        db.add(mention)
        db.add_all(
            [
                PlaceInsightItem(
                    place_id=place.id,
                    place_mention_id=mention.id,
                    source_id=source.id,
                    insight_type="RECOMMENDED_ITEM",
                    value_text="虾饺",
                    provenance="SOURCE_FACT",
                    source_quote="虾饺值得点",
                ),
                PlaceInsightItem(
                    place_id=place.id,
                    source_id=other_source.id,
                    insight_type="AUTHOR_OPINION",
                    value_text="适合早茶",
                    provenance="SOURCE_OPINION",
                    source_quote="我更喜欢早上来",
                ),
            ]
        )
        db.commit()

        assert build_place_notes(db, asset, [mention]) == 1
        note = db.scalar(select(PlaceNoteVersion).where(PlaceNoteVersion.place_id == place.id))
        assert note is not None
        assert "推荐菜 / 核心体验" in note.markdown
        assert "[来源事实] 虾饺（视频一：虾饺值得点）" in note.markdown
        assert "作者态度" in note.markdown
        assert "[来源观点] 适合早茶（视频二：我更喜欢早上来）" in note.markdown


def test_poi_resolution_scores_candidates_and_sends_ambiguous_mentions_to_review(
    app_and_session, monkeypatch
) -> None:
    _, factory = app_and_session

    class Provider:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def search(self, *_args, **_kwargs):
            return [
                POICandidate(
                    "best",
                    "四季民福烤鸭店（故宫店）",
                    "北京市东城区",
                    "北京市",
                    "北京市",
                    "东城区",
                    116.4,
                    39.9,
                    "050000",
                ),
                POICandidate(
                    "near",
                    "四季民福烤鸭店（王府井店）",
                    "北京市东城区",
                    "北京市",
                    "北京市",
                    "东城区",
                    116.41,
                    39.91,
                    "050000",
                ),
            ]

        def detail(self, poi_id: str):
            return POICandidate(
                poi_id,
                "四季民福烤鸭店（故宫店）",
                "北京市东城区",
                "北京市",
                "北京市",
                "东城区",
                116.4,
                39.9,
                "050000",
            )

    monkeypatch.setattr(video_support, "AMapPOIProvider", Provider)
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/poi", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="四季民福烤鸭店",
            raw_name="四季民福烤鸭店",
            suggested_name="四季民福烤鸭店（故宫店）",
            city_hint="北京市",
            place_type="RESTAURANT",
            segment_ids_json=["seg_fixture"],
            confidence=0.9,
            metadata_json={"visit_windows": [{"source_text": "秋季最好"}]},
        )
        db.add(mention)
        db.commit()
        confirmed, unresolved = resolve_mentions_with_amap(
            db, Settings(_env_file=None), [mention], api_key="test"
        )
        assert (confirmed, unresolved) == (0, 1)
        assert mention.resolution_status == "REVIEW"
        assert mention.metadata_json["poi_candidates"][0]["score"] >= 80
        assert mention.metadata_json["visit_windows"] == [{"source_text": "秋季最好"}]


def test_note_map_reduce_persists_compact_facts(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/map-reduce", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": "第一段" * 40, "start_ms": 0, "end_ms": 1000},
                {"text": "第二段" * 40, "start_ms": 1000, "end_ms": 2000},
            ],
            source_kind="ASR",
        )

        class Provider:
            def generate_json(self, messages, *, model):
                content = messages[-1]["content"]
                ids = [segment.id for segment in segments if segment.id in content]
                if "SectionFacts" in content:
                    ids = [segment.id for segment in segments]
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "overview": "紧凑总览",
                            "sections": [{"heading": "市场", "summary": "总结", "segment_ids": ids}],
                            "section_facts": [
                                {
                                    "summary": "事实",
                                    "segment_ids": ids,
                                    "places": [{"name": "菜市场", "segment_ids": ids}],
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    provider="fixture",
                    model=model,
                )

        monkeypatch.setattr(
            video_support,
            "provider_for_role",
            lambda *_args: (Provider(), "fixture", "fixture-model"),
        )
        version = generate_note(
            db,
            Settings(_env_file=None, video_note_chunk_chars=100),
            asset,
            transcript,
            segments,
        )
        assert version.map_facts_json and version.map_facts_json[0]["places"][0]["name"] == "菜市场"


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
