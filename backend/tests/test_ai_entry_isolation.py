from dataclasses import replace
from types import SimpleNamespace

from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.runtime_hints import read_runtime_hint, runtime_hint_scope, tighten_runtime_hint
from zhijian.providers.llm import LLMResult, ProviderRequestOptions


def entry(base_url="https://free.fixture/v1", key="fixture-account", tokens=4096):
    return SimpleNamespace(
        name="openai compatible",
        base_url=base_url,
        api_key=key,
        profile_id="profile-fixture",
        request_options=ProviderRequestOptions(max_output_tokens=tokens),
        timeout=300,
    )


def test_same_model_hints_do_not_cross_entry_account_or_parameters(app_and_session):
    model = "deepseek-v4-flash"
    free = entry()
    with app_and_session[1]() as db:
        # Keep the unscoped historical record without borrowing it into v2.
        tighten_runtime_hint(db, "TRANSCRIPT_CORRECTION", model, safe_max_chars=96, safe_max_segments=1)
        scope = runtime_hint_scope(free, model)
        assert read_runtime_hint(db, "TRANSCRIPT_CORRECTION", model, scope=scope) == {}
        tighten_runtime_hint(
            db, "TRANSCRIPT_CORRECTION", model, scope=scope, safe_max_chars=96, safe_max_segments=1
        )
        for other in [entry("https://official.fixture/v1"), entry(key="other-account"), entry(tokens=8192)]:
            assert (
                read_runtime_hint(db, "TRANSCRIPT_CORRECTION", model, scope=runtime_hint_scope(other, model))
                == {}
            )
        assert read_runtime_hint(db, "TRANSCRIPT_CORRECTION", model, scope=scope)["safe_max_segments"] == 1
        assert "fixture-account" not in scope


def test_cache_does_not_reuse_another_entry_or_old_output_limit(app_and_session):
    class Provider:
        name = "openai compatible"
        api_key = "fixture-account"
        profile_id = "profile-fixture"
        timeout = 300

        def __init__(self, base):
            self.base_url = base
            self.request_options = ProviderRequestOptions(max_output_tokens=4096)
            self.calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            return LLMResult('{"changes":[]}', self.name, model, {})

    free, official = Provider("https://free.fixture"), Provider("https://official.fixture")
    with app_and_session[1]() as db:

        def call(provider):
            return AIWorkloadGateway().execute_cached_json(
                db,
                job=None,
                stage="TRANSCRIPT_CORRECTION",
                capability="LLM",
                provider=provider,
                provider_name=provider.name,
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "Return JSON changes."}],
                semantic_options={},
                cache_enabled=True,
                force_regenerate=False,
            )

        call(free)
        call(official)
        call(official)
        assert (free.calls, official.calls) == (1, 1)
        official.request_options = replace(official.request_options, max_output_tokens=8192)
        call(official)
        assert official.calls == 2


def test_reasoning_only_cutoff_is_not_treated_as_smaller_input_or_json_retry(app_and_session):
    import pytest

    from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy
    from zhijian.db.models import AICacheEntry
    from zhijian.providers.llm import FallbackLLMProvider

    class Provider:
        name = "openai-compatible"
        calls = 0

        def generate_json(self, _messages, *, model, **_kwargs):
            self.calls += 1
            return LLMResult(
                "",
                self.name,
                model,
                {
                    "completion_tokens": 4096,
                    "completion_tokens_details": {"reasoning_tokens": 4096},
                },
                {"finish_reason": "length"},
            )

    client = Provider()
    provider = FallbackLLMProvider(
        client,
        "free-m",
        None,
        None,
        primary_reliability=ModelReliabilityPolicy(
            "GUARDED",
            retry_count=2,
            json_retry_count=2,
        ),
    )
    with app_and_session[1]() as db, pytest.raises(AIProviderError) as caught:
        AIWorkloadGateway().execute_cached_json(
            db,
            job=None,
            stage="TRANSCRIPT_CORRECTION",
            capability="LLM",
            provider=provider,
            provider_name=client.name,
            model="free-m",
            messages=[],
            semantic_options={},
            cache_enabled=True,
            force_regenerate=False,
        )
    assert caught.value.code == "AI_PROVIDER_REASONING_BUDGET"
    assert not caught.value.retryable and not caught.value.switch_model
    assert client.calls == 1
    with app_and_session[1]() as db:
        from sqlalchemy import select

        assert db.scalars(select(AICacheEntry)).all() == []


def test_remaining_job_deadline_does_not_change_saved_entry_timeout(app_and_session, monkeypatch):
    from time import perf_counter

    from zhijian.db.models import Job
    from zhijian.providers.llm import FallbackLLMProvider

    class Provider:
        name = "deepseek"
        timeout = 300

        def generate_json(self, _messages, *, model, **_kwargs):
            return LLMResult('{"changes":[]}', self.name, model, {})

    monkeypatch.setattr("zhijian.ai.gateway.remaining_ai_wall_seconds", lambda *_: 60)
    monkeypatch.setattr("zhijian.ai.gateway.ensure_job_active", lambda *_: None)
    monkeypatch.setattr("zhijian.ai.gateway.ensure_ai_budget", lambda *_, **__: None)
    client = Provider()
    provider = FallbackLLMProvider(client, "m", None, None)
    before = runtime_hint_scope(provider, "m")
    with app_and_session[1]() as db:
        AIWorkloadGateway().execute_cached_json(
            db,
            job=Job(id="test-job", payload_json={}),
            stage="TRANSCRIPT_CORRECTION",
            capability="LLM",
            provider=provider,
            provider_name="deepseek",
            model="m",
            messages=[],
            semantic_options={},
            cache_enabled=False,
            force_regenerate=False,
            stage_deadline=perf_counter() + 30,
        )
    assert client.timeout == 300
    assert runtime_hint_scope(provider, "m") == before


def test_local_only_semantic_escalation_cannot_use_global_remote_entry(app_and_session):
    import pytest

    from zhijian.db.models import Setting
    from zhijian.services.video_support import ProviderUnavailable, provider_for_role

    app, factory = app_and_session
    from zhijian.core.config import get_settings

    settings = app.dependency_overrides[get_settings]()
    with factory() as db:
        db.add(Setting(key="model-routing", value_json={"primary_id": "remote"}))
        db.add(
            Setting(
                key="model-profile:local",
                value_json={
                    "name": "local",
                    "provider": "ollama",
                    "model": "local-m",
                    "location": "LOCAL",
                    "base_url": "http://127.0.0.1:11434",
                    "capabilities": ["STRUCTURED_EXTRACTION"],
                    "max_output_tokens": 512,
                    "temperature": 0.8,
                },
            )
        )
        db.add(
            Setting(
                key="ai-stage-policy:GROUND_MAP",
                value_json={
                    "execution_mode": "LOCAL_ONLY",
                    "local_profile_id": "local",
                    "allow_unverified_model": True,
                    "max_output_tokens": 4096,
                },
            )
        )
        db.commit()
        selected, _, _ = provider_for_role(db, settings, "grounded_map")
        assert selected.request_options.max_output_tokens == 512
        assert selected.request_options.temperature == 0.8
        policy = db.get(Setting, "ai-stage-policy:GROUND_MAP")
        policy.value_json = {**policy.value_json, "temperature": 0.2}
        db.commit()
        selected, _, _ = provider_for_role(db, settings, "grounded_map")
        assert selected.request_options.temperature == 0.2
        with pytest.raises(ProviderUnavailable, match="仅允许本地模型"):
            provider_for_role(db, settings, "grounded_map_escalation")
        db.delete(policy)
        db.get(Setting, "model-routing").value_json = {"primary_id": "local"}
        profile = db.get(Setting, "model-profile:local")
        profile.value_json = {**profile.value_json, "max_output_tokens": None}
        db.commit()
        selected, _, _ = provider_for_role(db, settings, "grounded_map")
        assert selected.request_options.temperature == 0.8


def test_five_normal_correction_batches_are_not_limited_to_four_calls(app_and_session, monkeypatch):
    from sqlalchemy import select

    from zhijian.core.config import get_settings
    from zhijian.core.time import utc_now
    from zhijian.db.models import (
        ExternalCallAudit,
        Job,
        Segment,
        Setting,
        Snapshot,
        Source,
        Transcript,
        VideoAsset,
    )
    from zhijian.services.jobs import job_run_fence
    from zhijian.services.video_support import correct_transcript

    app, factory = app_and_session

    class Provider:
        name = "deepseek"
        base_url = "https://official.fixture/v1"
        api_key = "fixture-account"
        calls = 0

        def generate_json(self, _messages, *, model, **_kwargs):
            self.calls += 1
            db.add(
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider=self.name,
                    operation="correction",
                    status="COMPLETED",
                    duration_ms=0,
                    request_meta_json={"stage": "TRANSCRIPT_CORRECTION", "run_fence": job_run_fence(job)},
                    response_meta_json={"prompt_tokens": 20, "completion_tokens": 5},
                )
            )
            db.commit()
            return LLMResult('{"changes":[]}', self.name, model, {"finish_reason": "stop"})

    provider = Provider()
    monkeypatch.setattr(
        "zhijian.services.video_support.provider_for_role",
        lambda *_args: (provider, provider.name, "deepseek-v4-flash"),
    )
    monkeypatch.setattr(
        "zhijian.services.video_support.correction_candidates", lambda pending, **_kwargs: pending
    )
    with factory() as db:
        source = Source(source_type="URL", locator="https://video.fixture", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="fixture")
        snapshot = Snapshot(source_id=source.id, content_hash="fixture")
        db.add_all([asset, snapshot])
        db.flush()
        transcript = Transcript(video_asset_id=asset.id, source_kind="ASR", segment_count=80)
        values = [
            Segment(snapshot_id=snapshot.id, ordinal=i, text="西安门票20元。", raw_text="西安门票20元。")
            for i in range(80)
        ]
        job = Job(job_type="TRAVEL", status="RUNNING", started_at=utc_now(), payload_json={})
        db.add_all([transcript, job, *values])
        db.add(Setting(key="transcript-processing", value_json={"batch_size": 16, "chunk_chars": 3000}))
        db.add(Setting(key="ai-stage-policy:TRANSCRIPT_CORRECTION", value_json={"max_attempts": 4}))
        db.commit()
        tighten_runtime_hint(
            db, "TRANSCRIPT_CORRECTION", "deepseek-v4-flash", safe_max_chars=96, safe_max_segments=1
        )
        correct_transcript(
            db,
            app.dependency_overrides[get_settings](),
            asset,
            transcript,
            values,
            job,
        )
        assert provider.calls == 5 and all(v.correction_status == "UNCHANGED" for v in values)
        assert len(db.scalars(select(ExternalCallAudit).where(ExternalCallAudit.job_id == job.id)).all()) == 5
