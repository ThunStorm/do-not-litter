import json
from datetime import UTC, datetime

from sqlalchemy import select

from zhijian.ai.reliability import ModelReliabilityPolicy
from zhijian.core.config import Settings
from zhijian.db.models import AICacheEntry, AINote, ExternalCallAudit, Job, Source, VideoAsset
from zhijian.providers.llm import FallbackLLMProvider, LLMResult
from zhijian.services.grounded_map import get_or_create_grounded_map
from zhijian.services.video_support import (
    _compact_note_facts,
    _note_evidence_packs,
    extract_place_mentions,
    generate_note,
    materialize_transcript,
)


def test_note_evidence_pack_is_deduplicated_and_bounded() -> None:
    duplicate = {
        "summary": "同一事实",
        "key_points": ["要点", "要点"],
        "supporting_quotes": ["逐字证据", "逐字证据"],
        "segment_ids": ["seg-1"],
        "place_mention_ids": ["pm-1"],
    }
    compact = _compact_note_facts([duplicate, duplicate, {**duplicate, "segment_ids": ["seg-2"]}])
    packs = _note_evidence_packs(compact, max_chars=10_000, max_facts=1)
    assert len(compact) == 2
    assert compact[0]["supporting_quotes"] == ["逐字证据"]
    assert [len(pack) for pack in packs] == [1, 1]


class FixtureProvider:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def generate_json(self, messages, *, model):
        self.calls.append(messages)
        if "Grounded Map" in messages[0]["content"]:
            return LLMResult(
                json.dumps(
                    {
                        "section_facts": [
                            {
                                "summary": "西安蓝田水陆庵适合秋季到访。",
                                "key_points": ["秋季开放"],
                                "supporting_quotes": ["西安蓝田水陆庵秋天开放"],
                                "segment_ids": ["seg-placeholder"],
                            }
                        ],
                        "places": [
                            {
                                "raw_name": "西安蓝田水陆庵",
                                "name": "西安蓝田水陆庵",
                                "suggested_name": "西安蓝田水陆庵",
                                "city_hint": "西安",
                                "province_hint": "陕西",
                                "place_type": "TEMPLE",
                                "reason": "秋季开放",
                                "quote": "西安蓝田水陆庵秋天开放",
                                "segment_ids": ["seg-placeholder"],
                                "confidence": 0.9,
                            }
                        ],
                        "warnings": [],
                    },
                    ensure_ascii=False,
                ).replace("seg-placeholder", _segment_id(messages)),
                "fixture",
                model,
                {"prompt_tokens": 10, "completion_tokens": 2},
            )
        return LLMResult(
            json.dumps(
                {
                    "overview": "已整理为可回溯的旅行笔记。",
                    "sections": [
                        {
                            "section_kind": "PLACE",
                            "heading": "水陆庵",
                            "thesis": "秋季开放。",
                            "summary": "适合秋季到访。",
                            "bullets": ["秋季开放"],
                            "body_markdown": "适合秋季到访。",
                            "segment_ids": [_segment_id(messages)],
                            "place_mention_ids": [],
                            "supporting_quotes": ["西安蓝田水陆庵秋天开放"],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "fixture",
            model,
            {"prompt_tokens": 5, "completion_tokens": 2},
        )


def _segment_id(messages: list[dict[str, str]]) -> str:
    text = messages[-1]["content"]
    marker = "segment:"
    if marker in text:
        return text.split(marker, 1)[1].split(" ", 1)[0]
    return json.loads(text.split("GroundedEvidencePack。仅据此生成全局笔记：\n", 1)[1])[0]["segment_ids"][0]


def test_grounded_map_is_reused_and_place_materialization_is_llm_free(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    provider = FixtureProvider()
    selected = {"provider": "fixture", "model": "fixture-model"}
    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (provider, selected["provider"], selected["model"]),
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="西安旅行")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [{"text": "西安蓝田水陆庵秋天开放", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        artifact = get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments)
        selected.update(provider="other-provider", model="other-model")
        reused = get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments)
        assert reused.id == artifact.id
        assert reused.provider == "fixture"
        assert reused.producer_version == "grounded-map-v3"
        assert len(provider.calls) == 1

        mentions = extract_place_mentions(
            db, Settings(_env_file=None), asset, None, segments, candidates=artifact.places_json
        )
        assert [item.name for item in mentions] == ["西安蓝田水陆庵"]
        assert db.scalars(select(ExternalCallAudit)).all() == []

        compact = Job(job_type="TRAVEL", status="RUNNING", payload_json={"note_render_profile": "COMPACT"})
        detailed = Job(job_type="TRAVEL", status="RUNNING", payload_json={"note_render_profile": "DETAILED"})
        db.add_all([compact, detailed])
        db.flush()
        generate_note(db, Settings(_env_file=None), asset, transcript, segments, compact, mentions, artifact)
        generate_note(db, Settings(_env_file=None), asset, transcript, segments, detailed, mentions, artifact)
        assert len(provider.calls) == 3
        assert all("Render Profile" not in call[-1]["content"] for call in provider.calls[:1])


def test_grounded_map_splits_truncated_chunks(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    batch_sizes: list[int] = []

    class Provider:
        def generate_json(self, messages, *, model):
            batch_size = messages[-1]["content"].count("[segment:")
            batch_sizes.append(batch_size)
            if batch_size > 2:
                return LLMResult("", "fixture", model, {}, {"finish_reason": "length"})
            return LLMResult(
                '{"section_facts":[],"places":[],"warnings":[]}',
                "fixture",
                model,
                {},
            )

    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (Provider(), "fixture", "fixture-model"),
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/split-map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="拆分地图")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": f"第{index}段旅行信息", "start_ms": index * 1000, "end_ms": (index + 1) * 1000}
                for index in range(4)
            ],
            source_kind="ASR",
        )
        artifact = get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments)

    assert batch_sizes == [4, 2, 2]
    assert artifact.facts_json == []


def test_grounded_map_uses_cached_fallback_after_local_truncation(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    local_calls: list[int] = []
    remote_calls: list[int] = []
    routes: list[str] = []

    class Local:
        name = "ollama"

        def generate_json(self, messages, *, model):
            count = messages[-1]["content"].count("[segment:")
            local_calls.append(count)
            return LLMResult("", self.name, model, {}, {"finish_reason": "length"})

    class Remote:
        name = "remote"

        def generate_json(self, messages, *, model):
            remote_calls.append(messages[-1]["content"].count("[segment:"))
            return LLMResult('{"section_facts":[],"places":[],"warnings":[]}', self.name, model, {})

    provider = FallbackLLMProvider(
        Local(),
        "local-model",
        Remote(),
        "remote-model",
        primary_reliability=ModelReliabilityPolicy("STANDARD", retry_count=0, json_retry_count=0),
        fallback_reliability=ModelReliabilityPolicy("STANDARD", retry_count=0, json_retry_count=0),
        fallback_decider=lambda exc: exc.code != "AI_PROVIDER_OUTPUT_TRUNCATED",
        on_attempt_start=lambda _name, _model, route, *_args: routes.append(route) or "attempt",
    )
    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (provider, "ollama", "local-model"),
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/fallback-map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="回退地图")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": f"第{index}段旅行信息", "start_ms": index * 1000, "end_ms": (index + 1) * 1000}
                for index in range(4)
            ],
            source_kind="ASR",
        )
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.commit()
        artifact = get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments, job)

        assert local_calls == [4]
        assert remote_calls == [2, 2]
        assert routes == ["primary", "fallback", "fallback"]
        assert artifact.semantic_options_json["fallback_chunk_count"] == 2
        assert db.query(AICacheEntry).filter_by(provider="remote").count() == 2


def test_grounded_map_switches_remaining_chunks_when_local_cannot_fit_wall_budget(
    app_and_session, monkeypatch
) -> None:
    _, factory = app_and_session
    routes: list[str] = []

    class Provider:
        def __init__(self, name: str) -> None:
            self.name = name

        def generate_json(self, _messages, *, model):
            routes.append(self.name)
            return LLMResult('{"section_facts":[],"places":[],"warnings":[]}', self.name, model, {})

    policy = ModelReliabilityPolicy("STANDARD", retry_count=0, json_retry_count=0)
    provider = FallbackLLMProvider(
        Provider("ollama"),
        "local-model",
        Provider("remote"),
        "remote-model",
        primary_reliability=policy,
        fallback_reliability=policy,
    )
    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (provider, "ollama", "local-model"),
    )
    monkeypatch.setattr(
        "zhijian.services.video_support._transcript_chunks",
        lambda segments, *_args, **_kwargs: [
            segments[index : index + 2] for index in range(0, len(segments), 2)
        ],
    )
    monkeypatch.setattr("zhijian.services.grounded_map.remaining_ai_wall_seconds", lambda *_args: 700)
    ticks = iter(range(0, 10_000, 100))
    monkeypatch.setattr("zhijian.services.grounded_map.perf_counter", lambda: next(ticks))
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/wall-map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="预算地图")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": f"第{index}段旅行信息", "start_ms": index * 1000, "end_ms": (index + 1) * 1000}
                for index in range(8)
            ],
            source_kind="ASR",
        )
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={}, started_at=datetime.now(UTC))
        db.add(job)
        db.commit()
        get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments, job)

        assert routes == ["ollama", "ollama", "remote", "remote"]


def test_grounded_map_prechunks_for_local_models(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    batch_sizes: list[int] = []
    monkeypatch.setattr("zhijian.ai.gateway.local_ai_resource_manager.run", lambda _kind, call: call())

    class Provider:
        def generate_json(self, messages, *, model):
            batch_sizes.append(messages[-1]["content"].count("[segment:"))
            assert "禁止输出空字符串、空数组" in messages[0]["content"]
            return LLMResult(
                '{"section_facts":[],"places":[],"warnings":[]}',
                "ollama",
                model,
                {},
            )

    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (Provider(), "ollama", "local-model"),
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/local-map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="本地模型分块")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": f"第{index}段", "start_ms": index * 1000, "end_ms": (index + 1) * 1000}
                for index in range(130)
            ],
            source_kind="ASR",
        )
        get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments)

    assert batch_sizes == [64, 64, 2]


def test_grounded_map_hint_keeps_five_segments_per_chunk(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    batch_sizes: list[int] = []

    class Provider:
        name = "ollama"

        def generate_json(self, messages, *, model):
            batch_sizes.append(messages[-1]["content"].count("[segment:"))
            return LLMResult('{"section_facts":[],"places":[],"warnings":[]}', self.name, model, {})

    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (Provider(), "ollama", "local-model"),
    )
    monkeypatch.setattr(
        "zhijian.services.grounded_map.read_runtime_hint",
        lambda *_args: {"safe_max_chars": 240, "safe_max_segments": 5},
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/hinted-map", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="安全分块")
        db.add(asset)
        db.flush()
        transcript, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": "山" * 48, "start_ms": index * 1000, "end_ms": (index + 1) * 1000}
                for index in range(71)
            ],
            source_kind="ASR",
        )
        get_or_create_grounded_map(db, Settings(_env_file=None), asset, transcript, segments)

    assert batch_sizes == [5] * 14 + [1]


def test_note_profile_regeneration_starts_at_reduce(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/note", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="笔记")
        db.add(asset)
        db.flush()
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.commit()
        note_id, asset_id = note.id, asset.id

    response = client.post(f"/api/video-notes/{note_id}/regenerate?profile_id=COMPACT")
    assert response.status_code == 200
    with factory() as db:
        job = db.get(Job, response.json()["job_id"])
        assert job and job.payload_json["replay_from_step"] == "GENERATE_AI_NOTE"
        assert job.payload_json["video_asset_id"] == asset_id
        assert job.payload_json["note_id"] == note_id
        assert job.payload_json["ai_submission_config"]["version"] == 1
