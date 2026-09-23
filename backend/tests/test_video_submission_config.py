from __future__ import annotations

import json
from types import SimpleNamespace

from sqlalchemy import func, select

from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import domain_context_messages
from zhijian.ai.job_config import SNAPSHOT_KEY, job_asr_provider, job_setting
from zhijian.core.config import Settings
from zhijian.db.models import (
    AINote,
    AINoteVersion,
    ContentItem,
    Job,
    Place,
    PlaceMention,
    Setting,
    VideoAsset,
)
from zhijian.providers.amap import POICandidate
from zhijian.providers.llm import LLMResult
from zhijian.providers.runtime import RuntimeCheck
from zhijian.services.capture import create_capture_job
from zhijian.services.job_replay import queue_full_replay
from zhijian.services.video_pipeline import _bind_job_to_asset_source, _materialize_core_content
from zhijian.services.video_support import (
    extract_place_mentions,
    generate_note,
    materialize_transcript,
    note_for_job,
    prompt_supplement_value,
    provider_for_role,
    resolve_mentions_with_amap,
)


def test_asr_default_is_saved_per_submission_and_full_retry(client, app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    monkeypatch.setattr(
        "zhijian.api.router.check_qwen_asr",
        lambda *_: RuntimeCheck("qwen3-asr", "READY", "test"),
    )
    monkeypatch.setattr(
        "zhijian.api.router.check_whisper",
        lambda *_: RuntimeCheck("whisper.cpp", "READY", "test"),
    )
    assert client.get("/api/settings/asr").json() == {"default_provider": "WHISPER_CPP"}
    assert client.put("/api/settings/asr", json={"default_provider": "QWEN3_ASR"}).status_code == 200
    first = client.post("/api/capture", json={"text": "https://www.bilibili.com/video/BV1same"})
    video = client.post("/api/capture/file", files={"upload": ("clip.mp4", b"video", "video/mp4")})
    audio = client.post("/api/capture/file", files={"upload": ("clip.wav", b"audio", "audio/wav")})
    assert first.status_code == video.status_code == audio.status_code == 200
    assert client.get(f"/api/jobs/{first.json()['job_id']}").json()["asr_provider"] == "QWEN3_ASR"

    assert client.put("/api/settings/asr", json={"default_provider": "WHISPER_CPP"}).status_code == 200
    second = client.post("/api/capture", json={"text": "https://www.bilibili.com/video/BV1same"})
    assert second.status_code == 200
    with factory() as db:
        old_jobs = [db.get(Job, response.json()["job_id"]) for response in (first, video, audio)]
        new_job = db.get(Job, second.json()["job_id"])
        for job in old_jobs:
            assert job.payload_json["asr_provider"] == "QWEN3_ASR"
            assert job.payload_json[SNAPSHOT_KEY]["default_asr_provider"] == "QWEN3_ASR"
            assert job_asr_provider(job, Settings(_env_file=None)) == "QWEN3_ASR"
        assert new_job.payload_json["asr_provider"] == "WHISPER_CPP"
        assert new_job.payload_json[SNAPSHOT_KEY]["default_asr_provider"] == "WHISPER_CPP"
        original = old_jobs[0]
        original.status = "FAILED"
        db.commit()
        queue_full_replay(db, original)
        assert original.payload_json["asr_provider"] == "QWEN3_ASR"


def test_unavailable_asr_cannot_be_saved(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "zhijian.api.router.check_qwen_asr",
        lambda *_: RuntimeCheck("qwen3-asr", "MISSING", "test"),
    )
    assert client.put("/api/settings/asr", json={"default_provider": "QWEN3_ASR"}).status_code == 409
    assert client.put("/api/settings/asr", json={"default_provider": "OTHER"}).status_code == 422
    assert client.get("/api/settings/asr").json() == {"default_provider": "WHISPER_CPP"}


def test_queued_and_replayed_jobs_keep_submission_ai_config(app_and_session, monkeypatch, tmp_path) -> None:
    _, factory = app_and_session
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with factory() as db:
        for name in ("a", "b", "c"):
            db.add(
                Setting(
                    key=f"model-profile:{name}",
                    value_json={
                        "provider": "Ollama",
                        "base_url": "http://127.0.0.1:11434",
                        "model": f"model-{name}",
                        "location": "LOCAL",
                        "api_key": "must-not-enter-job-payload",
                    },
                )
            )
        routing = Setting(key="model-routing", value_json={"primary_id": "a"})
        policy = Setting(
            key="ai-stage-policy:GENERATE_AI_NOTE",
            value_json={"execution_mode": "LOCAL_ONLY", "local_profile_id": "a"},
        )
        supplement = Setting(key="prompt:supplements", value_json={"video_note_summary": "首次偏好"})
        general = Setting(key="app:general", value_json={"ai_retry_count": 1})
        processing = Setting(key="transcript-processing", value_json={"batch_size": 16})
        domain = Setting(
            key="ai-domain-pack:travel",
            value_json={"id": "travel", "name": "旅行术语", "version": "v1", "rules": ["首次规则"]},
        )
        db.add_all([routing, policy, supplement, general, processing, domain])
        db.commit()
        source_a, first = create_capture_job(
            db, settings, locator="https://www.bilibili.com/video/BV1same", source_type="URL"
        )

        routing.value_json = {"primary_id": "b"}
        policy.value_json = {"execution_mode": "LOCAL_ONLY", "local_profile_id": "b"}
        supplement.value_json = {"video_note_summary": "第二次偏好"}
        general.value_json = {"ai_retry_count": 2}
        processing.value_json = {"batch_size": 32}
        domain.value_json = {"id": "travel", "name": "旅行术语", "version": "v2", "rules": ["第二次规则"]}
        db.commit()
        source_b, second = create_capture_job(
            db, settings, locator="https://www.bilibili.com/video/BV1same", source_type="URL"
        )
        routing.value_json = {"primary_id": "c"}
        policy.value_json = {"execution_mode": "LOCAL_ONLY", "local_profile_id": "c"}
        supplement.value_json = {"video_note_summary": "后来偏好"}
        general.value_json = {"ai_retry_count": 3}
        processing.value_json = {"batch_size": 64}
        domain.value_json = {"id": "travel", "name": "旅行术语", "version": "v3", "rules": ["后来规则"]}
        profile_b = db.get(Setting, "model-profile:b")
        profile_b.value_json = {**profile_b.value_json, "model": "model-b-later"}
        db.commit()

        assert first.payload_json[SNAPSHOT_KEY]["settings"]["model-routing"]["primary_id"] == "a"
        assert second.payload_json[SNAPSHOT_KEY]["settings"]["model-routing"]["primary_id"] == "b"
        assert "api_key" not in second.payload_json[SNAPSHOT_KEY]["settings"]["model-profile:b"]
        assert prompt_supplement_value(db, "video_note_summary", first) == "首次偏好"
        assert prompt_supplement_value(db, "video_note_summary", second) == "第二次偏好"
        assert job_setting(db, "ai-stage-policy:GENERATE_AI_NOTE", first)["local_profile_id"] == "a"
        assert job_setting(db, "ai-stage-policy:GENERATE_AI_NOTE", second)["local_profile_id"] == "b"
        assert job_setting(db, "app:general", first)["ai_retry_count"] == 1
        assert job_setting(db, "app:general", second)["ai_retry_count"] == 2
        assert job_setting(db, "transcript-processing", second)["batch_size"] == 32
        assert domain_context_messages(db, ["travel"], AICapability.GLOBAL_SYNTHESIS, first)[1] == {
            "travel": "v1"
        }
        assert domain_context_messages(db, ["travel"], AICapability.GLOBAL_SYNTHESIS, second)[1] == {
            "travel": "v2"
        }

        monkeypatch.setattr(
            "zhijian.services.video_support._provider_from_config",
            lambda config, *_args: (SimpleNamespace(), "ollama", config["model"]),
        )
        assert provider_for_role(db, settings, "video_note_summary", first)[2] == "model-a"
        assert provider_for_role(db, settings, "video_note_summary", second)[2] == "model-b"
        _, third = create_capture_job(
            db, settings, locator="https://www.bilibili.com/video/BV1later", source_type="URL"
        )
        assert provider_for_role(db, settings, "video_note_summary", third)[2] == "model-c"
        first.status = "COMPLETED"
        db.commit()
        queue_full_replay(db, first)
        assert first.status == "QUEUED"
        assert provider_for_role(db, settings, "video_note_summary", first)[2] == "model-a"
        assert source_a.id != source_b.id


def test_same_video_submissions_make_two_notes_and_share_one_place(
    client, app_and_session, monkeypatch, tmp_path
) -> None:
    _, factory = app_and_session
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with factory() as db:
        db.add(Setting(key="model-routing", value_json={"primary_id": "a"}))
        for name in ("a", "b", "c"):
            db.add(
                Setting(
                    key=f"model-profile:{name}",
                    value_json={
                        "provider": "Ollama",
                        "base_url": "http://127.0.0.1:11434",
                        "model": f"model-{name}",
                        "location": "LOCAL",
                    },
                )
            )
        db.commit()
        first_source, first = create_capture_job(
            db, settings, locator="https://www.bilibili.com/video/BV1two", source_type="URL"
        )
        routing = db.get(Setting, "model-routing")
        routing.value_json = {"primary_id": "b"}
        db.commit()
        second_source, second = create_capture_job(
            db, settings, locator="https://www.bilibili.com/video/BV1two", source_type="URL"
        )
        routing.value_json = {"primary_id": "c"}
        db.commit()
        asset = VideoAsset(
            source_id=first_source.id,
            canonical_url=first_source.locator,
            title="同一个视频标题",
        )
        db.add(asset)
        db.flush()
        _bind_job_to_asset_source(db, second, second_source, asset)
        db.commit()

        monkeypatch.setattr(
            "zhijian.services.video_support._provider_from_config",
            lambda config, *_args: (SimpleNamespace(), "ollama", config["model"]),
        )

        def note_result(_db, *, model, messages, **_kwargs):
            segment_id = messages[-1]["content"].split("segment:", 1)[1].split(" ", 1)[0]
            return LLMResult(
                json.dumps(
                    {
                        "overview": f"由 {model} 整理",
                        "warnings": [],
                        "section_facts": [],
                        "sections": [
                            {
                                "section_kind": "PLACE",
                                "heading": "翠湖公园的游览要点",
                                "summary": "春天可游览翠湖公园",
                                "bullets": ["春天可游览翠湖公园"],
                                "segment_ids": [segment_id],
                                "supporting_quotes": ["昆明翠湖公园春天适合游览"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                "ollama",
                model,
                {},
            )

        monkeypatch.setattr("zhijian.services.video_support._cached_stage_json", note_result)

        class AMapFixture:
            request_count = 0
            cache_hit_count = 0

            def __init__(self, *_args, **_kwargs) -> None:
                self.candidate = POICandidate(
                    "amap-cuihu",
                    "翠湖公园",
                    "昆明市五华区",
                    "云南省",
                    "昆明市",
                    "五华区",
                    102.7,
                    25.05,
                    "110000",
                )

            def search(self, *_args, **_kwargs):
                return [self.candidate]

            def detail(self, _provider_id):
                return self.candidate

        monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", AMapFixture)
        note_ids = []
        transcript_ids = []
        first_transcript = None
        first_segments = []
        for job in (first, second):
            transcript, segments = materialize_transcript(
                db,
                first_source,
                asset,
                [{"text": "昆明翠湖公园春天适合游览", "start_ms": 0, "end_ms": 1000}],
                source_kind="ASR",
                submission_job_id=job.id,
            )
            transcript_ids.append(transcript.id)
            if job.id == first.id:
                first_transcript, first_segments = transcript, segments
            mentions = extract_place_mentions(
                db,
                settings,
                asset,
                None,
                segments,
                job,
                candidates=[
                    {
                        "name": "翠湖公园",
                        "raw_name": "翠湖公园",
                        "quote": "昆明翠湖公园春天适合游览",
                        "segment_ids": [segments[0].id],
                        "city_hint": "昆明市",
                        "place_type": "PARK",
                        "poi_policy": "RESOLVE",
                        "subject_role": "PRIMARY",
                        "visit_intent": "RECOMMENDED",
                        "confidence": 0.9,
                    }
                ],
            )
            version = generate_note(db, settings, asset, transcript, segments, job, mentions)
            note_ids.append(version.ai_note_id)
            assert resolve_mentions_with_amap(db, settings, mentions, "fixture") == (1, 0)
            _materialize_core_content(db, job, first_source, asset, version, mentions, 1, 0)
            job.status = "COMPLETED"
            db.commit()

        assert first_transcript and first_segments
        old_version_id = db.get(AINote, note_ids[0]).current_version_id
        old_mention_id = db.scalar(
            select(PlaceMention.id).where(PlaceMention.ai_note_version_id == old_version_id)
        )
        replay_mentions = extract_place_mentions(
            db,
            settings,
            asset,
            None,
            first_segments,
            first,
            candidates=[
                {
                    "name": "翠湖公园",
                    "raw_name": "翠湖公园",
                    "quote": "昆明翠湖公园春天适合游览",
                    "segment_ids": [first_segments[0].id],
                    "city_hint": "昆明市",
                    "place_type": "PARK",
                    "poi_policy": "RESOLVE",
                    "confidence": 0.9,
                }
            ],
        )
        replayed = generate_note(
            db, settings, asset, first_transcript, first_segments, first, replay_mentions
        )
        assert replayed.ai_note_id == note_ids[0]
        assert replayed.id != old_version_id
        assert resolve_mentions_with_amap(db, settings, replay_mentions, "fixture") == (1, 0)
        _materialize_core_content(db, first, first_source, asset, replayed, replay_mentions, 1, 0)
        regeneration = Job(job_type="TRAVEL", status="COMPLETED", payload_json={"note_id": note_ids[0]})
        db.add(regeneration)
        db.flush()
        assert note_for_job(db, asset, regeneration).id == note_ids[0]
        regenerated_content = _materialize_core_content(
            db, regeneration, first_source, asset, replayed, replay_mentions, 1, 0
        )
        assert regenerated_content.id == first.result_content_id
        assert (
            db.scalar(select(func.count(AINoteVersion.id)).where(AINoteVersion.ai_note_id == note_ids[0]))
            == 2
        )
        assert (
            db.scalar(
                select(func.count(PlaceMention.id)).where(
                    PlaceMention.ai_note_version_id == old_version_id,
                    PlaceMention.extraction_status == "SUPERSEDED",
                )
            )
            == 1
        )

        assert transcript_ids[0] != transcript_ids[1]
        assert note_ids[0] != note_ids[1]
        assert db.scalar(select(func.count(AINote.id)).where(AINote.video_asset_id == asset.id)) == 2
        assert (
            db.scalar(select(func.count(ContentItem.id)).where(ContentItem.source_id == first_source.id)) == 2
        )
        assert db.scalar(select(func.count(Place.id)).where(Place.external_poi_id == "amap-cuihu")) == 1
        versions = [db.get(AINoteVersion, db.get(AINote, note_id).current_version_id) for note_id in note_ids]
        assert [version.model_name for version in versions] == ["model-a", "model-b"]

    notes = [item for item in client.get("/api/video-notes").json() if item["id"] in note_ids]
    assert [item["title"] for item in notes] == ["同一个视频标题", "同一个视频标题"]
    search = [
        item for item in client.get("/api/video-notes?query=同一个视频标题").json() if item["id"] in note_ids
    ]
    assert len(search) == 2
    assert all(item["place_summary"]["confirmed"] == 1 for item in notes)
    assert [
        client.get(f"/api/video-notes/{note_id}/transcript").json()["id"] for note_id in note_ids
    ] == transcript_ids
    place_ids = [
        client.get(f"/api/video-notes/{note_id}/places").json()[0]["place_id"] for note_id in note_ids
    ]
    assert place_ids[0] == place_ids[1]
    superseded = client.post(
        f"/api/travel/place-mentions/{old_mention_id}/confirm",
        json={"provider": "AMAP", "poi_id": "amap-cuihu", "expected_revision": 0},
    )
    assert superseded.status_code == 409
    assert superseded.json()["detail"]["code"] == "MENTION_SUPERSEDED"

    assert client.delete(f"/api/video-notes/{note_ids[0]}").status_code == 200
    assert client.get(f"/api/video-notes/{note_ids[1]}").status_code == 200
    with factory() as db:
        assert (
            db.scalar(select(func.count(ContentItem.id)).where(ContentItem.source_id == first_source.id)) == 1
        )
        assert db.scalar(select(func.count(Place.id)).where(Place.external_poi_id == "amap-cuihu")) == 1
