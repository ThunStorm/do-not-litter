from types import SimpleNamespace

import httpx
import pytest

from zhijian.ai.budget import AIBudgetExceeded, soft_budget_state
from zhijian.ai.capabilities import AICapability
from zhijian.ai.cost_router import choose_auto_route
from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy
from zhijian.ai.transcript_quality import correction_candidates
from zhijian.db.models import ExternalCallAudit, Job, Setting
from zhijian.providers.llm import FallbackLLMProvider
from zhijian.services.video_support import parse_model_json, provider_for_role


def test_whisper_correction_uses_semantic_candidates_and_neighbors() -> None:
    segments = [
        SimpleNamespace(raw_text=text, text=text, confidence=0.99)
        for text in (
            "开场白没有需要校对的信息",
            "普通介绍内容",
            "午饭后继续出发",
            "十月去国家森林公园看红叶",
            "普通结尾内容",
            "最后一句无关内容",
        )
    ]

    candidates = correction_candidates(segments, source_kind="WHISPER_CPP_ASR", neighbor_segments=1)

    assert candidates == segments[2:5]
    assert correction_candidates(segments, source_kind="MANUAL_SUBTITLE") == []
    assert correction_candidates(segments[:2], source_kind="ASR") == segments[:2]


def test_long_prompts_follow_profile_retry_policy() -> None:
    attempts = 0

    class Provider:
        def generate_json(self, _messages, *, model):
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("temporary network failure")

    provider = FallbackLLMProvider(
        Provider(),
        "fixture",
        None,
        None,
        sleeper=lambda _seconds: None,
        primary_reliability=ModelReliabilityPolicy("GUARDED", retry_count=1),
    )
    with pytest.raises(AIProviderError):
        provider.generate_json([{"role": "user", "content": "x" * 8_000}], model="fixture")
    assert attempts == 2


def test_rate_limits_retry_without_retry_after() -> None:
    attempts = 0

    class Provider:
        def generate_json(self, _messages, *, model):
            nonlocal attempts
            attempts += 1
            request = httpx.Request("POST", "https://fixture.test")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    provider = FallbackLLMProvider(
        Provider(),
        "fixture",
        None,
        None,
        sleeper=lambda _seconds: None,
        primary_reliability=ModelReliabilityPolicy("FREE_TIER", retry_count=2),
    )
    with pytest.raises(AIProviderError):
        provider.generate_json([], model="fixture")
    assert attempts == 3


def test_tolerant_json_parser_repairs_wrapping_and_trailing_commas() -> None:
    assert parse_model_json('说明：{"ok": true,}') == {"ok": True}


def test_auto_router_prefers_local_and_reserves_remote_strong() -> None:
    profiles = {
        "local": {"provider": "ollama", "location": "LOCAL", "quality_tier": "MAIN"},
        "remote": {"provider": "remote", "location": "REMOTE", "quality_tier": "STRONG"},
    }

    balanced = choose_auto_route("NOTE_REDUCE", AICapability.GLOBAL_SYNTHESIS, profiles)
    quality = choose_auto_route(
        "NOTE_REDUCE", AICapability.GLOBAL_SYNTHESIS, profiles, quality_preset="QUALITY"
    )
    pressured = choose_auto_route(
        "NOTE_REDUCE", AICapability.GLOBAL_SYNTHESIS, profiles, budget_pressure=True
    )

    assert balanced and (balanced.primary_id, balanced.fallback_id) == ("local", "remote")
    assert quality and quality.route == "REMOTE_STRONG"
    assert pressured and (pressured.primary_id, pressured.fallback_id) == ("local", "")


def test_new_jobs_apply_auto_router_before_provider_calls(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        local = {
            "provider": "ollama",
            "location": "LOCAL",
            "base_url": "http://local.test",
            "model": "local-model",
            "quality_tier": "MAIN",
        }
        remote = {
            "provider": "remote",
            "location": "REMOTE",
            "base_url": "https://remote.test",
            "model": "remote-model",
            "quality_tier": "STRONG",
        }
        db.add_all(
            [
                Setting(key="model-profile:local", value_json=local),
                Setting(key="model-profile:remote", value_json=remote),
                Setting(key="model-routing", value_json={"primary_id": "local", "fallback_id": "remote"}),
            ]
        )
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={"ai_automation_version": "v2"})
        db.add(job)
        db.commit()

        class Provider:
            def generate_json(self, *_args, **_kwargs):
                raise AssertionError("router test must not call a provider")

        monkeypatch.setattr(
            "zhijian.services.video_support._provider_from_config",
            lambda config, *_args: (Provider(), str(config["provider"]).lower(), str(config["model"])),
        )
        settings = SimpleNamespace(secret_store="file", data_dir="/tmp")
        _, _, model = provider_for_role(db, settings, "note_reduce", job)
        assert model == "local-model"

        job.payload_json = {**job.payload_json, "quality_preset": "QUALITY"}
        _, _, model = provider_for_role(db, settings, "note_reduce", job)
        assert model == "remote-model"

        job.payload_json = {**job.payload_json, "ai_soft_budget": {"status": "WARNING"}}
        routed, _, model = provider_for_role(db, settings, "note_reduce", job)
        assert model == "local-model"
        assert isinstance(routed, FallbackLLMProvider) and routed.fallback is None


def test_soft_budget_warns_before_the_hard_gate(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add_all(
            [
                job,
                Setting(
                    key="app:general",
                    value_json={"ai_max_remote_prompt_tokens_per_job": 4_000},
                ),
            ]
        )
        db.flush()
        warning = soft_budget_state(db, job, location="REMOTE", input_chars=6_000)
        assert warning and warning.status == "WARNING"
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="remote",
                operation="fixture",
                status="COMPLETED",
                request_meta_json={"location": "REMOTE"},
                response_meta_json={"prompt_tokens": 3_900},
            )
        )
        db.commit()
        hard = soft_budget_state(db, job, location="REMOTE", input_chars=800)
        assert hard and hard.status == "HARD_LIMIT"
        with pytest.raises(AIBudgetExceeded):
            from zhijian.ai.budget import ensure_ai_budget

            ensure_ai_budget(db, job, location="REMOTE", input_chars=800)
