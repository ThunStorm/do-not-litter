import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from zhijian.ai.reliability import AIProviderError
from zhijian.ai.token_usage import estimate_tokens
from zhijian.core.config import Settings
from zhijian.db.models import GroundedMapArtifact, Job, Source, SystemEvent, VideoAsset
from zhijian.providers.llm import LLMResult
from zhijian.services import video_support as vs


@pytest.mark.parametrize("single_oversized", [False, True])
def test_note_full_request_preflight_preserves_evidence_and_bounds_calls(
    app_and_session, monkeypatch, single_oversized
):
    _, factory = app_and_session
    calls = []
    monkeypatch.setattr(vs, "provider_for_role", lambda *a: (SimpleNamespace(), "fixture", "fixture"))
    # A contextual message is added after initial packing; preflight must include it.
    monkeypatch.setattr(
        vs,
        "domain_context_messages",
        lambda *a, **kw: (
            [{"role": "system", "content": "领域规则" * (2000 if single_oversized else 450)}],
            {},
        ),
    )
    original_pack = vs._note_evidence_packs
    monkeypatch.setattr(vs, "_note_evidence_packs", lambda facts, **kw: [facts])

    def cached(db, **kw):
        final, *_ = vs._prepare_stage_request(
            db,
            job=kw["job"],
            stage=kw["stage"],
            capability=kw["capability"],
            messages=kw["messages"],
            request_segments=kw["request_segments"],
        )
        estimated = estimate_tokens(sum(len(m["content"]) for m in final))
        if estimated > 2600:
            raise AIProviderError("AI_STAGE_INPUT_BUDGET", f"完整请求估算 {estimated} Token，超过2600")
        facts = json.loads(kw["messages"][-1]["content"].split("全局笔记：\n")[1])
        calls.extend(facts)
        return LLMResult(
            json.dumps(
                {
                    "sections": [
                        {
                            "heading": "事实",
                            "summary": f["summary"],
                            "body_markdown": f["summary"],
                            "segment_ids": f["segment_ids"],
                            "supporting_quotes": f["supporting_quotes"],
                            "place_mention_ids": [],
                        }
                        for f in facts
                    ]
                },
                ensure_ascii=False,
            ),
            "fixture",
            "fixture",
            {},
        )

    monkeypatch.setattr(vs, "_cached_stage_json", cached)
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/budget")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="预算测试")
        db.add(asset)
        db.flush()
        transcript, segments = vs.materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": f"地点{i}原始证据。" * 15, "start_ms": i * 1000, "end_ms": (i + 1) * 1000}
                for i in range(4)
            ],
            source_kind="ASR",
        )
        facts = [
            {
                "summary": "事实内容" * 120,
                "key_points": [],
                "supporting_quotes": [s.text],
                "segment_ids": [s.id],
                "place_mention_ids": [],
            }
            for s in segments[: 1 if single_oversized else 4]
        ]
        monkeypatch.setattr(vs, "_ground_map_facts", lambda *a: facts)
        artifact = GroundedMapArtifact(
            video_asset_id=asset.id,
            transcript_id=transcript.id,
            transcript_version=transcript.version,
            content_hash="x",
            semantic_hash="x",
            prompt_version="test",
            supplement_hash="",
            provider="fixture",
            model="fixture",
            facts_json=facts,
        )
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            payload_json={
                "ai_overrides": {"NOTE_REDUCE": {"max_input_tokens": 2600, "max_output_tokens": 8192}}
            },
        )
        db.add_all([artifact, job])
        db.commit()
        if single_oversized:
            with pytest.raises(AIProviderError, match="单条证据无法继续拆分") as exc:
                vs.generate_note(db, Settings(_env_file=None), asset, transcript, segments, job, [], artifact)
            assert exc.value.code == "AI_STAGE_INPUT_BUDGET"
            assert calls == []
        else:
            version = vs.generate_note(
                db, Settings(_env_file=None), asset, transcript, segments, job, [], artifact
            )
            assert {sid for f in calls for sid in f["segment_ids"]} == {s.id for s in segments}
            assert {q for f in calls for q in f["supporting_quotes"]} == {s.text for s in segments}
            assert len(calls) == 4
            assert version.grounded_map_artifact_id == artifact.id
            assert db.scalars(
                select(SystemEvent).where(SystemEvent.event_type == "video.note.input_split")
            ).all()
        # The normal packer still retains an indivisible fact rather than silently truncating it.
        assert original_pack(facts[:1], max_chars=1, max_facts=1) == [facts[:1]]


def test_gateway_input_rejection_has_numeric_diagnostics_and_no_attempt(app_and_session):
    from zhijian.ai.gateway import AIWorkloadGateway
    from zhijian.db.models import ExternalCallAudit

    _, factory = app_and_session
    provider = SimpleNamespace(generate_json=lambda *a, **kw: pytest.fail("must not call provider"))
    with factory() as db:
        with pytest.raises(AIProviderError, match="51 Token（101字符）.*50") as exc:
            AIWorkloadGateway().execute_cached_json(
                db,
                job=None,
                stage="NOTE_REDUCE",
                capability="GLOBAL_SYNTHESIS",
                provider=provider,
                provider_name="fixture",
                model="fixture",
                messages=[{"role": "user", "content": "字" * 101}],
                max_input_tokens=50,
                semantic_options={},
                force_regenerate=False,
                cache_enabled=False,
            )
        assert exc.value.code == "AI_STAGE_INPUT_BUDGET"
        assert db.scalars(select(ExternalCallAudit)).all() == []


def test_exact_cache_hit_still_reuses_result_after_input_budget_is_lowered(app_and_session):
    from zhijian.ai.gateway import AIWorkloadGateway

    _, factory = app_and_session
    calls = []

    def generate(*a, **kw):
        calls.append(1)
        return LLMResult('{"changes":[]}', "fixture", "fixture", {})

    provider = SimpleNamespace(name="fixture", generate_json=generate)
    with factory() as db:
        common = dict(
            job=None,
            stage="TRANSCRIPT_CORRECTION",
            capability="TRANSCRIPT_CORRECTION",
            provider=provider,
            provider_name="fixture",
            model="fixture",
            messages=[{"role": "user", "content": "缓存证据" * 20}],
            semantic_options={},
            cache_enabled=True,
            force_regenerate=False,
        )
        gateway = AIWorkloadGateway()
        first = gateway.execute_cached_json(db, **common, max_input_tokens=100)
        cached = gateway.execute_cached_json(db, **common, max_input_tokens=1)
        assert cached.content == first.content
        assert calls == [1]
