import re

import pytest

from zhijian.ai.interface_contract import InterfaceCapabilities, router_payload
from zhijian.ai.model_registry import probe_system_instruction
from zhijian.ai.reliability import AIProviderError
from zhijian.ai.schemas import ModelProfile
from zhijian.providers.llm import LLMResult, OpenAICompatibleProvider


@pytest.mark.parametrize("answer,status", [("system", "PASS"), ("USER_OVERRIDE", "FAIL")])
def test_role_probe_can_test_unknown_without_promoting_production(monkeypatch, answer, status):
    capabilities = InterfaceCapabilities(
        model="fixture", base_url="http://localhost/v1", sampled_at="fixture"
    )
    provider = OpenAICompatibleProvider(
        "fixture",
        "http://localhost/v1",
        "fixture",
        connection_type="LOCAL_ROUTER",
        interface_capabilities=capabilities,
    )
    profile = ModelProfile(
        id="fixture",
        provider="fixture",
        model="fixture",
        connection_type="LOCAL_ROUTER",
        interface_capabilities=capabilities,
    )

    def invoke(candidate, selected, method, messages):
        assert candidate is not provider
        assert candidate.interface_capabilities.system == "SUPPORTED"
        assert [message["role"] for message in messages] == ["system", "user"]
        target = re.search(r"SYSTEM_[a-f0-9]+", messages[0]["content"]).group()
        assert target not in messages[1]["content"]
        return LLMResult(target if answer == "system" else answer, "fixture", "fixture", {})

    monkeypatch.setattr("zhijian.ai.model_registry.invoke_profile_model", invoke)
    result = probe_system_instruction(provider, profile)
    assert result["status"] == status
    assert provider.interface_capabilities.system == "UNKNOWN"
    assert profile.interface_capabilities.system == "UNKNOWN"
    with pytest.raises(AIProviderError, match="尚未提供系统指令"):
        router_payload(
            capabilities,
            "http://localhost/v1",
            "fixture",
            [{"role": "system", "content": "fixture"}, {"role": "user", "content": "fixture"}],
            json_mode=False,
            temperature=None,
            max_output_tokens=None,
        )


def test_probe_error_is_unverified_and_does_not_expose_provider_body(monkeypatch):
    profile = ModelProfile(id="fixture", provider="fixture", model="fixture")

    class Provider:
        cancel_check = None

    def fail(*args):
        raise AIProviderError("AI_PROVIDER_AUTH_ERROR", "secret-provider-body")

    monkeypatch.setattr("zhijian.ai.model_registry.invoke_profile_model", fail)
    result = probe_system_instruction(Provider(), profile)
    assert result["status"] == "NOT_TESTED"
    assert result["error_code"] == "AI_PROVIDER_AUTH_ERROR"
    assert "secret-provider-body" not in str(result)


def test_cancelled_probe_does_not_turn_into_unverified_result(monkeypatch):
    from zhijian.services.jobs import JobCancelled

    class Provider:
        @staticmethod
        def cancel_check():
            raise JobCancelled("fixture cancelled")

    def fail(*args):
        raise AIProviderError("AI_PROVIDER_TIMEOUT", "fixture")

    monkeypatch.setattr("zhijian.ai.model_registry.invoke_profile_model", fail)
    with pytest.raises(JobCancelled):
        probe_system_instruction(Provider(), ModelProfile(id="fixture", provider="fixture", model="fixture"))


def test_interface_mode_runs_in_worker_without_business_probes(app_and_session, monkeypatch):
    from zhijian.api import router as api
    from zhijian.db.models import Job, Setting
    from zhijian.services.model_tests import enqueue_model_tests, lease_model_test, run_model_test

    _, factory = app_and_session
    monkeypatch.setattr(
        api,
        "probe_saved_interface",
        lambda *args: {
            "probe_results": {"SYSTEM_INSTRUCTION": "FAIL"},
            "interface_probe": {"status": "FAIL", "reason": "fixture", "error_code": None},
        },
    )
    with factory() as db:
        db.add(
            Setting(
                key="model-profile:fixture",
                value_json={
                    "name": "fixture",
                    "provider": "fixture",
                    "model": "fixture",
                    "base_url": "https://fixture.test/v1",
                },
            )
        )
        db.commit()
        queued = enqueue_model_tests(db, ["fixture"], "INTERFACE")
        assert enqueue_model_tests(db, ["fixture"], "INTERFACE")[0]["id"] == queued[0]["id"]
        job = lease_model_test(db, "fixture", 60, set())
        job_id = job.id
    run_model_test(factory, job_id, 60)
    with factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "COMPLETED"
        assert job.payload_json["test_results"]["INTERFACE"]["probe_results"]["SYSTEM_INSTRUCTION"] == "FAIL"
        assert "PROBE" not in job.payload_json["test_results"]
