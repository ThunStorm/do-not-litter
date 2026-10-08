from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest
from sqlalchemy import select

from zhijian.ai.budget import AIBudgetExceeded, ensure_ai_budget
from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.interface_contract import (
    InterfaceCapabilities,
    InterfaceParameter,
    read_interface_capabilities,
)
from zhijian.ai.job_config import capture_ai_config, job_setting
from zhijian.ai.model_registry import invoke_profile_model
from zhijian.ai.reliability import (
    AIProviderError,
    ModelReliabilityPolicy,
    ReliabilityGuards,
    classify_provider_error,
)
from zhijian.ai.schemas import ModelProfile
from zhijian.ai.structured_output import parse_json_object
from zhijian.core.config import get_settings
from zhijian.db.models import ExternalCallAudit, Job, Setting
from zhijian.domain.schemas import ModelProfileConfig
from zhijian.providers.llm import (
    FallbackLLMProvider,
    LLMResult,
    OpenAICompatibleProvider,
    ProviderRequestOptions,
    interface_signature,
)


def contract(**changes) -> InterfaceCapabilities:
    return InterfaceCapabilities(
        model="codebuddy/hy3",
        base_url="http://127.0.0.1:8317/v1",
        sampled_at="2026-10-06",
        **changes,
    )


@pytest.mark.parametrize(
    "address",
    [
        "http://key@localhost/v1",
        "http://localhost/v1?key=fixture",
        "file:///tmp",
        "http://localhost:invalid/v1",
    ],
)
def test_router_address_cannot_persist_credentials_or_invalid_protocol(address):
    with pytest.raises(ValueError):
        ModelProfileConfig(
            name="fixture",
            provider="LocalAiMux",
            model="fixture",
            base_url=address,
            connection_type="LOCAL_ROUTER",
        )


def provider(capabilities) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        "LocalAiMux",
        "http://127.0.0.1:8317/v1",
        "fixture-key",
        connection_type="LOCAL_ROUTER",
        interface_capabilities=capabilities,
    )


def model_response(payload=None):
    return httpx.Response(
        200,
        request=httpx.Request("POST", "http://fixture.test"),
        json=payload
        or {
            "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        },
    )


def test_metadata_read_checks_catalogs_and_does_not_copy_secrets(monkeypatch):
    requests = []
    original = httpx.Client

    def handle(request):
        requests.append(request)
        assert request.method == "GET"
        entry = {"id": "codebuddy/hy3"}
        if request.url.path.endswith("/api/chat/models"):
            entry["chat"] = {"system": "UNSUPPORTED", "max_tokens": {"support": "UNSUPPORTED"}}
            entry["api_key"] = "do-not-copy-this"
        return httpx.Response(200, json={"data": [entry]})

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs)
    )
    result = read_interface_capabilities("http://127.0.0.1:8317/v1", "codebuddy/hy3", "fixture-key")
    assert len(requests) == 2 and result.output.support == "UNSUPPORTED"
    assert "do-not-copy-this" not in result.model_dump_json()
    assert result.json_object == "UNKNOWN"


def test_router_omits_optional_parameters_and_counts_unknown_usage(monkeypatch):
    payloads = []
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: payloads.append(kwargs["json"]) or model_response()
    )
    result = provider(contract()).generate_json(
        [{"role": "user", "content": "Return JSON ok"}],
        model="codebuddy/hy3",
        options=ProviderRequestOptions(temperature=0.2, max_output_tokens=4096, thinking=False),
    )
    assert set(payloads[0]) == {"model", "messages"}
    assert result.usage == {} and result.metadata["usage_source"] == "UNKNOWN"
    assert result.metadata["finish_reason"] is None and result.metadata["reported_finish_reason"] == "stop"
    assert result.metadata["estimated_prompt_tokens"] > 0
    assert set(result.metadata["omitted_parameters"]) == {
        "temperature",
        "max_tokens",
        "thinking",
        "response_format",
    }


def test_router_cancellable_request_disables_environment_proxy(monkeypatch):
    requests = []
    client_options = []
    original_client = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        return model_response()

    def client(**kwargs):
        client_options.append(kwargs)
        return original_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    router = provider(contract())
    router.cancel_check = lambda: None
    result = router.generate_json(
        [{"role": "user", "content": "Return JSON ok"}], model="codebuddy/hy3"
    )
    assert result.content == '{"ok":true}'
    assert len(requests) == 1 and requests[0].url.path == "/v1/chat/completions"
    assert client_options[0]["trust_env"] is False


def test_router_preserves_rules_and_uses_declared_output_field(monkeypatch):
    calls = []
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: calls.append(kwargs["json"]) or model_response()
    )
    cap = contract(
        system="SUPPORTED",
        json_object="SUPPORTED",
        output_field="max_completion_tokens",
        output=InterfaceParameter(support="SUPPORTED", minimum=1, maximum=8192),
    )
    provider(cap).generate_json(
        [
            {"role": "system", "content": "core evidence IDs"},
            {"role": "system", "content": "low preference"},
            {"role": "user", "content": "evidence_01"},
        ],
        model="codebuddy/hy3",
        options=ProviderRequestOptions(max_output_tokens=4096),
    )
    assert calls[0]["messages"] == [
        {"role": "system", "content": "core evidence IDs\n\nlow preference"},
        {"role": "user", "content": "evidence_01"},
    ]
    assert calls[0]["max_completion_tokens"] == 4096 and "max_tokens" not in calls[0]
    assert calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    "messages,cap",
    [
        ([{"role": "system", "content": "core"}, {"role": "user", "content": "evidence"}], contract()),
        (
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "old"},
                {"role": "user", "content": "next"},
            ],
            contract(),
        ),
        ([{"role": "user", "content": [{"type": "image_url"}]}], contract()),
    ],
)
def test_incompatible_messages_stop_before_inference(monkeypatch, messages, cap):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: pytest.fail("must not send"))
    with pytest.raises(AIProviderError) as raised:
        provider(cap).generate_json(messages, model="codebuddy/hy3")
    assert raised.value.code == "AI_PROVIDER_INTERFACE_MESSAGES" and not raised.value.switch_model


def test_stale_interface_and_out_of_range_stop_before_inference(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: pytest.fail("must not send"))
    with pytest.raises(AIProviderError, match="读取并保存"):
        provider(contract()).generate_text([{"role": "user", "content": "x"}], model="different")
    cap = contract(output=InterfaceParameter(support="SUPPORTED", minimum=1, maximum=128))
    with pytest.raises(AIProviderError, match="超出"):
        provider(cap).generate_text(
            [{"role": "user", "content": "x"}],
            model="codebuddy/hy3",
            options=ProviderRequestOptions(max_output_tokens=129),
        )


def test_compatibility_errors_do_not_open_circuit_or_leak_message():
    response = httpx.Response(
        400,
        request=httpx.Request("POST", "http://fixture.test"),
        json={
            "error": {"code": "LMX_UNSUPPORTED_PARAMETER", "message": "private-fixture-key"},
        },
    )
    error = classify_provider_error(httpx.HTTPStatusError("400", request=response.request, response=response))
    assert error.code == "AI_PROVIDER_INTERFACE_INVALID" and "private-fixture-key" not in str(error)
    policy = ModelReliabilityPolicy("GUARDED", circuit_breaker_enabled=True, circuit_breaker_threshold=2)
    for _ in range(4):
        assert ReliabilityGuards.failure("interface-fixture", policy, error) == "CLOSED"
    semaphore, _, state = ReliabilityGuards.acquire("interface-fixture", policy)
    ReliabilityGuards.release(semaphore)
    assert state == "CLOSED"


def test_json_retry_retains_all_instructions_before_user():
    calls = []

    class Raw:
        def generate_json(self, messages, **kwargs):
            calls.append(messages)
            return LLMResult("invalid" if len(calls) == 1 else '{"ok":true}', "fixture", "fixture", {})

    result = FallbackLLMProvider(
        Raw(),
        "fixture",
        None,
        None,
        sleeper=lambda _: None,
        primary_reliability=ModelReliabilityPolicy("STANDARD", json_retry_count=1),
        result_validator=lambda result: parse_json_object(result.content),
    ).generate_json(
        [{"role": "system", "content": "Evidence core"}, {"role": "user", "content": "id_01"}],
        model="fixture",
    )
    assert result.content == '{"ok":true}'
    assert [m["role"] for m in calls[1]] == ["system", "user"]
    assert "Evidence core" in calls[1][0]["content"] and "只返回合法 JSON" in calls[1][0]["content"]
    assert calls[1][1]["content"] == "id_01"


def test_probe_uses_optional_profile_limit_instead_of_fixed_64():
    options = []

    class Raw:
        def generate_text(self, messages, **kwargs):
            options.append(kwargs["options"])
            return LLMResult("PONG", "fixture", "fixture", {})

    for limit in (4096, None):
        invoke_profile_model(
            Raw(),
            ModelProfile(
                id="x", provider="fixture", model="fixture", location="LOCAL", max_output_tokens=limit
            ),
            "generate_text",
            [{"role": "user", "content": "PONG"}],
        )
    assert [option.max_output_tokens for option in options] == [4096, None]
    assert all(option.thinking is None for option in options)


def test_manual_test_bypasses_circuit_without_resetting_production(monkeypatch):
    from zhijian.ai import model_registry
    from zhijian.ai.reliability import provider_identity

    monkeypatch.setattr(model_registry, "sleep", lambda _: None)
    raw = provider(contract())
    profile = ModelProfile(id="manual", provider="LocalAiMux", model="codebuddy/hy3")
    key = provider_identity(raw, profile.model)
    policy = ModelReliabilityPolicy("GUARDED", circuit_breaker_enabled=True, circuit_breaker_threshold=1)
    ReliabilityGuards.failure(key, policy, AIProviderError("AI_PROVIDER_TIMEOUT", "fixture"))
    opened = ReliabilityGuards._circuits[key].open_until
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: model_response())
    assert invoke_profile_model(raw, profile, "generate_text", [{"role": "user", "content": "PONG"}]).content
    assert ReliabilityGuards._circuits[key].open_until == opened
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            429,
            request=httpx.Request("POST", "http://fixture.test"),
            json={"error": {"message": "rate limit"}},
        ),
    )
    with pytest.raises(AIProviderError) as failure:
        invoke_profile_model(raw, profile, "generate_text", [{"role": "user", "content": "PONG"}])
    assert failure.value.code == "AI_PROVIDER_RATE_LIMITED"
    assert ReliabilityGuards._circuits[key].open_until == opened
    ReliabilityGuards._circuits.pop(key)


def test_manual_queue_fifo_across_models_and_failed_operation():
    from zhijian.ai.model_registry import _manual_test_condition, _manual_test_tickets, queued_model_test

    release = Event()
    running = Event()
    order = []

    def operation(index):
        with queued_model_test():
            with queued_model_test():
                order.append(index)
            if index == 0:
                running.set()
                assert release.wait(3)
                raise ValueError("first failed")
            return index

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(operation, 0)]
        assert running.wait(2)
        for index in range(1, 4):
            futures.append(pool.submit(operation, index))
            with _manual_test_condition:
                assert _manual_test_condition.wait_for(
                    lambda expected=index + 1: len(_manual_test_tickets) == expected, timeout=2
                )
        release.set()
        with pytest.raises(ValueError, match="first failed"):
            futures[0].result(timeout=2)
        assert [future.result(timeout=2) for future in futures[1:]] == [1, 2, 3]
    assert order == [0, 1, 2, 3] and not _manual_test_tickets


def test_legacy_named_mux_is_identified_without_guessing_a_port(client, monkeypatch):
    from zhijian.ai import interface_contract
    from zhijian.ai.model_registry import model_connection_type

    raw = {
        "name": "Local Ai Mux",
        "provider": "",
        "model": "codebuddy/hy3",
        "base_url": "http://127.0.0.1:8317/v1",
        "max_output_tokens": 4096,
        "api_key": "fixture-key",
    }
    assert model_connection_type(raw) == "LOCAL_ROUTER"
    assert model_connection_type({**raw, "name": "custom"}) == "DIRECT"
    assert model_connection_type({**raw, "connection_type": "DIRECT"}) == "DIRECT"
    monkeypatch.setattr(interface_contract, "read_interface_capabilities", lambda *args: contract())
    calls = []
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: calls.append(kwargs["json"]) or model_response()
    )
    from zhijian.api.router import _test_model_connection

    _test_model_connection(raw, "fixture-key")
    assert set(calls[0]) == {"model", "messages"}


def test_interface_changes_are_frozen_and_change_cache_signature(app_and_session):
    app, factory = app_and_session
    original = contract(system="SUPPORTED")
    changed = contract(system="UNSUPPORTED")
    assert interface_signature(provider(original)) != interface_signature(provider(changed))
    assert original.fingerprint() == original.model_copy(update={"sampled_at": "later"}).fingerprint()
    with factory() as db:
        key = "model-profile:contract-fixture"
        db.add(
            Setting(
                key=key,
                value_json={
                    "connection_type": "LOCAL_ROUTER",
                    "interface_capabilities": original.model_dump(),
                },
            )
        )
        db.commit()
        snapshot = capture_ai_config(db, app.dependency_overrides[get_settings]())
        job = Job(job_type="TRAVEL", status="QUEUED", payload_json={"ai_submission_config": snapshot})
        row = db.get(Setting, key)
        row.value_json = {"connection_type": "LOCAL_ROUTER", "interface_capabilities": changed.model_dump()}
        db.commit()
        assert job_setting(db, key, job)["interface_capabilities"]["system"] == "SUPPORTED"


def test_actual_cache_invalidates_when_router_contract_changes(app_and_session, monkeypatch):
    _, factory = app_and_session
    calls = []
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: (
            calls.append(kwargs["json"])
            or model_response(
                {
                    "choices": [{"message": {"content": '{"changes":[]}'}, "finish_reason": "stop"}],
                }
            )
        ),
    )
    with factory() as db:
        gateway = AIWorkloadGateway()
        arguments = dict(
            db=db,
            job=None,
            stage="TRANSCRIPT_CORRECTION",
            capability="TRANSCRIPT_CORRECTION",
            provider_name="LocalAiMux",
            model="codebuddy/hy3",
            messages=[{"role": "user", "content": "same evidence"}],
            semantic_options={},
            cache_enabled=True,
            force_regenerate=False,
        )
        first = provider(contract())
        gateway.execute_cached_json(provider=first, **arguments)
        gateway.execute_cached_json(provider=first, **arguments)
        gateway.execute_cached_json(provider=provider(contract(system="SUPPORTED")), **arguments)
        assert len(calls) == 2


def test_fallback_uses_its_own_interface_and_options(monkeypatch):
    calls = []

    def post(*args, **kwargs):
        payload = kwargs["json"]
        calls.append(payload)
        if len(calls) == 1:
            return httpx.Response(503, request=httpx.Request("POST", "http://fixture.test"))
        return model_response()

    monkeypatch.setattr(httpx, "post", post)
    primary_cap = contract(output=InterfaceParameter(support="SUPPORTED", minimum=1, maximum=4096))
    primary_cap = primary_cap.model_copy(update={"model": "qoder/X"})
    wrapped = FallbackLLMProvider(
        provider(primary_cap),
        "qoder/X",
        provider(contract()),
        "codebuddy/hy3",
        sleeper=lambda _: None,
        primary_reliability=ModelReliabilityPolicy("STANDARD", retry_count=0),
        fallback_reliability=ModelReliabilityPolicy("STANDARD", retry_count=0),
        request_options=ProviderRequestOptions(max_output_tokens=128),
        fallback_request_options=ProviderRequestOptions(max_output_tokens=256, temperature=0.7),
    )
    wrapped.generate_json([{"role": "user", "content": "JSON"}], model="qoder/X")
    assert calls[0]["max_tokens"] == 128
    assert set(calls[1]) == {"model", "messages"} and calls[1]["model"] == "codebuddy/hy3"


def test_unknown_usage_estimates_apply_to_hard_budget(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.flush()
        db.add(Setting(key="app:general", value_json={"ai_max_remote_prompt_tokens_per_job": 1000}))
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="LocalAiMux",
                operation="fixture",
                status="COMPLETED",
                request_meta_json={"location": "REMOTE", "model": "codebuddy/hy3"},
                response_meta_json={
                    "prompt_tokens": None,
                    "usage_source": "UNKNOWN",
                    "estimated_prompt_tokens": 1000,
                },
            )
        )
        db.commit()
        with pytest.raises(AIBudgetExceeded):
            ensure_ai_budget(
                db, job, location="REMOTE", input_chars=4, provider="LocalAiMux", model="codebuddy/hy3"
            )


def test_saved_metadata_read_is_read_only_and_separate_from_business_probe(
    client, app_and_session, monkeypatch
):
    from zhijian.ai import interface_contract

    monkeypatch.setattr(
        interface_contract, "read_interface_capabilities", lambda *args: contract(system="UNSUPPORTED")
    )
    payload = {
        "name": "Router",
        "provider": "LocalAiMux",
        "model": "codebuddy/hy3",
        "base_url": "http://127.0.0.1:8317/v1",
        "connection_type": "LOCAL_ROUTER",
        "max_output_tokens": None,
        "api_key": "fixture-key",
    }
    saved = client.post("/api/settings/model-profiles", json=payload).json()
    response = client.post(
        f"/api/settings/model-profiles/{saved['id']}/interface-capabilities", json={**payload, "api_key": ""}
    )
    assert response.status_code == 200 and response.json()["system"] == "UNSUPPORTED"
    _, factory = app_and_session
    with factory() as db:
        stored = db.scalar(select(Setting).where(Setting.key == f"model-profile:{saved['id']}"))
        assert stored.value_json["interface_capabilities"] is None and "api_key" not in stored.value_json
    assert client.get("/api/settings/model-profiles").json()[-1]["probe_results"] == {}
    direct = client.post(
        "/api/settings/model-profiles/interface-capabilities-draft",
        json={
            **payload,
            "connection_type": "DIRECT",
            "interface_capabilities": contract().model_dump(),
        },
    )
    assert direct.status_code == 422
