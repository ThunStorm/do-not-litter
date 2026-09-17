import httpx
import pytest

from zhijian.ai.budget import AIBudgetExceeded
from zhijian.ai.reliability import (
    AIProviderError,
    ModelReliabilityPolicy,
    provider_rate_limit_identity,
)
from zhijian.ai.structured_output import parse_json_object, validate_structured_output
from zhijian.providers.llm import FallbackLLMProvider, LLMResult


def _rate_limited() -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://models.test/chat/completions")
    return httpx.HTTPStatusError(
        "rate limited", request=request, response=httpx.Response(429, request=request)
    )


def test_direct_success_has_no_wait_or_retry() -> None:
    sleeps: list[float] = []

    class Provider:
        def generate_json(self, _messages, *, model):
            return LLMResult('{"places":[]}', "paid", model, {})

    provider = FallbackLLMProvider(
        Provider(),
        "paid-model",
        None,
        None,
        sleeper=sleeps.append,
        primary_reliability=ModelReliabilityPolicy("DIRECT"),
    )
    assert provider.generate_json([], model="ignored").content == '{"places":[]}'
    assert sleeps == []


def test_standard_retries_invalid_json_once(monkeypatch) -> None:
    monkeypatch.setattr("zhijian.providers.llm.retry_wait_seconds", lambda *_args: 0)

    class Provider:
        calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            return LLMResult("not json" if self.calls == 1 else '{"places":[]}', "model", model, {})

    raw = Provider()
    provider = FallbackLLMProvider(
        raw,
        "model",
        None,
        None,
        primary_reliability=ModelReliabilityPolicy("STANDARD", json_retry_count=1),
        result_validator=lambda result: validate_structured_output(result.content, "EXTRACT_TRAVEL_FACTS"),
    )
    assert provider.generate_json([], model="ignored").content == '{"places":[]}'
    assert raw.calls == 2


def test_structured_error_does_not_consume_http_retry(monkeypatch) -> None:
    monkeypatch.setattr("zhijian.providers.llm.retry_wait_seconds", lambda *_args: 0)

    class Provider:
        calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            return LLMResult("not json", "model", model, {})

    raw = Provider()
    provider = FallbackLLMProvider(
        raw,
        "model",
        None,
        None,
        primary_reliability=ModelReliabilityPolicy("STANDARD", retry_count=1, json_retry_count=1),
        result_validator=lambda result: validate_structured_output(result.content, "EXTRACT_TRAVEL_FACTS"),
    )
    with pytest.raises(AIProviderError) as raised:
        provider.generate_json([], model="ignored")
    assert raised.value.code == "AI_PROVIDER_INVALID_JSON"
    assert raw.calls == 2


def test_free_tier_retries_429_without_retry_after(monkeypatch) -> None:
    monkeypatch.setattr("zhijian.providers.llm.retry_wait_seconds", lambda *_args: 0)

    class Provider:
        calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            if self.calls < 3:
                raise _rate_limited()
            return LLMResult('{"places":[]}', "free", model, {})

    raw = Provider()
    provider = FallbackLLMProvider(
        raw,
        "free-model",
        None,
        None,
        primary_reliability=ModelReliabilityPolicy("FREE_TIER", retry_count=2, max_concurrency=1),
    )
    assert provider.generate_json([], model="ignored").provider == "free"
    assert raw.calls == 3


def test_quota_exhausted_opens_circuit_without_retry() -> None:
    class Provider:
        name = "free"
        base_url = "https://free.test"
        calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            request = httpx.Request("POST", self.base_url)
            response = httpx.Response(
                429,
                json={"error": {"message": "quota exhausted"}},
                request=request,
            )
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    raw = Provider()
    with pytest.raises(AIProviderError) as raised:
        FallbackLLMProvider(
            raw,
            "model:free",
            None,
            None,
            primary_reliability=ModelReliabilityPolicy("FREE_TIER", retry_count=2),
        ).generate_json([], model="ignored")
    assert raised.value.code == "AI_PROVIDER_QUOTA_EXHAUSTED"
    assert raw.calls == 1


def test_openrouter_privacy_policy_block_is_not_retried() -> None:
    class Provider:
        name = "openrouter"
        base_url = "https://openrouter.ai/api/v1"
        calls = 0

        def generate_json(self, _messages, *, model):
            self.calls += 1
            request = httpx.Request("POST", f"{self.base_url}/chat/completions")
            response = httpx.Response(
                404,
                json={
                    "error": {
                        "message": (
                            "0 endpoints out of 9 requested are available matching your guardrail "
                            "restrictions and data policy. ZDR violation (account settings)."
                        )
                    }
                },
                request=request,
            )
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    raw = Provider()
    with pytest.raises(AIProviderError) as raised:
        FallbackLLMProvider(
            raw,
            "openrouter/free",
            None,
            None,
            primary_reliability=ModelReliabilityPolicy("STANDARD", retry_count=2),
        ).generate_json([], model="ignored")
    assert raised.value.code == "AI_PROVIDER_POLICY_BLOCKED"
    assert "OpenRouter 隐私/ZDR" in str(raised.value)
    assert raw.calls == 1


def test_tpm_limit_is_throttled_without_retry_or_paid_model_delay() -> None:
    class Provider:
        name = "remote"
        base_url = "https://remote.test"
        api_key = "fixture"
        calls: list[str] = []

        def generate_json(self, _messages, *, model):
            self.calls.append(model)
            if model == "free-model":
                request = httpx.Request("POST", self.base_url)
                response = httpx.Response(
                    429,
                    json={
                        "error": {
                            "code": "insufficient_quota",
                            "message": "inference exceeds tpm/rpm limit",
                        }
                    },
                    request=request,
                )
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)
            return LLMResult('{"places":[]}', self.name, model, {})

    raw = Provider()
    with pytest.raises(AIProviderError) as raised:
        FallbackLLMProvider(
            raw,
            "free-model",
            None,
            None,
            primary_reliability=ModelReliabilityPolicy(
                "GUARDED", retry_count=2, circuit_breaker_enabled=True
            ),
        ).generate_json([], model="ignored")
    assert raised.value.code == "AI_PROVIDER_THROTTLED"

    sleeps: list[float] = []
    result = FallbackLLMProvider(
        raw,
        "paid-model",
        None,
        None,
        sleeper=sleeps.append,
        primary_reliability=ModelReliabilityPolicy("DIRECT"),
    ).generate_json([], model="ignored")
    assert result.model == "paid-model"
    assert sleeps == []
    assert raw.calls == ["free-model", "paid-model"]


def test_guarded_circuit_opens_after_threshold() -> None:
    class Provider:
        name = "guarded"
        base_url = "https://guarded.test"

        def generate_json(self, _messages, *, model):
            raise _rate_limited()

    raw = Provider()
    policy = ModelReliabilityPolicy(
        "GUARDED",
        retry_count=0,
        circuit_breaker_enabled=True,
        circuit_breaker_threshold=2,
    )
    for _ in range(2):
        with pytest.raises(AIProviderError, match="rate limited"):
            FallbackLLMProvider(raw, "model", None, None, primary_reliability=policy).generate_json(
                [], model="ignored"
            )
    with pytest.raises(AIProviderError) as raised:
        FallbackLLMProvider(raw, "model", None, None, primary_reliability=policy).generate_json(
            [], model="ignored"
        )
    assert raised.value.code == "AI_PROVIDER_CIRCUIT_OPEN"


def test_same_endpoint_different_model_can_fallback() -> None:
    class Primary:
        name = "openrouter"
        base_url = "https://openrouter.ai/api/v1"

        def generate_json(self, _messages, *, model):
            request = httpx.Request("POST", self.base_url)
            raise httpx.HTTPStatusError(
                "unavailable", request=request, response=httpx.Response(503, request=request)
            )

    class Fallback:
        name = "openrouter"
        base_url = "https://openrouter.ai/api/v1"

        def generate_json(self, _messages, *, model):
            return LLMResult('{"places":[]}', "openrouter", model, {})

    provider = FallbackLLMProvider(
        Primary(),
        "model-a:free",
        Fallback(),
        "model-b:free",
        primary_reliability=ModelReliabilityPolicy("DIRECT"),
        fallback_reliability=ModelReliabilityPolicy("DIRECT"),
    )
    assert provider.generate_json([], model="ignored").model == "model-b:free"


def test_models_with_same_credential_share_rate_limit_identity() -> None:
    class Provider:
        name = "remote"
        base_url = "https://shared.test/v1"

        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    assert provider_rate_limit_identity(Provider("same")) == provider_rate_limit_identity(
        Provider("same")
    )
    assert provider_rate_limit_identity(Provider("same")) != provider_rate_limit_identity(
        Provider("other")
    )


def test_budget_rejection_does_not_switch_provider_or_record_attempt() -> None:
    attempts: list[str] = []

    class Provider:
        name = "remote"
        base_url = "https://budget.test/v1"

        def generate_json(self, *_args, **_kwargs):
            raise AssertionError("budget gate must run before provider")

    provider = FallbackLLMProvider(
        Provider(),
        "primary",
        Provider(),
        "fallback",
        attempt_runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AIBudgetExceeded("本任务已达到 AI 模型调用次数上限")
        ),
        on_attempt=lambda provider_name, *_args: attempts.append(provider_name),
        primary_reliability=ModelReliabilityPolicy("STANDARD"),
        fallback_reliability=ModelReliabilityPolicy("STANDARD"),
    )
    with pytest.raises(AIProviderError) as raised:
        provider.generate_json([], model="ignored")
    assert raised.value.code == "AI_BUDGET_EXCEEDED"
    assert raised.value.switch_model is False
    assert attempts == []


def test_safe_json_recovery_rejects_truncation_and_array() -> None:
    assert parse_json_object('说明：```json\n{"places":[],}\n```') == {"places": []}
    with pytest.raises(AIProviderError, match="截断") as truncated:
        parse_json_object('{"places":[')
    assert truncated.value.code == "AI_PROVIDER_OUTPUT_TRUNCATED"
    with pytest.raises(AIProviderError) as array:
        parse_json_object("[]")
    assert array.value.code == "AI_PROVIDER_SCHEMA_INVALID"
