from zhijian.ai import (
    AICapability,
    AIEvidenceSegment,
    AIModelLocation,
    AIRequest,
    AIWorkloadGateway,
)
from zhijian.db.models import Job
from zhijian.providers.llm import FallbackLLMProvider, LLMResult


class Provider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate_text(self, _messages: list[dict[str, str]], *, model: str) -> LLMResult:
        self.calls.append(("text", model))
        return LLMResult("plain", "ollama", model, {"prompt_eval_count": 3, "eval_count": 2})

    def generate_json(self, _messages: list[dict[str, str]], *, model: str) -> LLMResult:
        self.calls.append(("json", model))
        return LLMResult('{"ok":true}', "ollama", model, {"prompt_tokens": 4, "completion_tokens": 2})

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self.generate_json(messages, model=model)


def test_gateway_preserves_provider_call_shape_usage_and_evidence() -> None:
    provider = Provider()
    result = AIWorkloadGateway().execute(
        AIRequest(
            capability=AICapability.STRUCTURED_EXTRACTION,
            stage="GENERATE_AI_NOTE",
            output_schema={"type": "object"},
            model_override="selected-model",
            evidence_segments=[AIEvidenceSegment(id="seg_1", text="证据")],
        ),
        provider=provider,
        model="legacy-model",
        messages=[{"role": "user", "content": "ping"}],
        location=AIModelLocation.LOCAL,
    )

    assert provider.calls == [("json", "selected-model")]
    assert result.data == '{"ok":true}'
    assert result.model == "selected-model"
    assert result.input_tokens == 4
    assert result.output_tokens == 2
    assert result.evidence_ids == ["seg_1"]
    assert result.local_attempted and not result.remote_attempted


def test_gateway_uses_text_for_unstructured_requests() -> None:
    provider = Provider()
    result = AIWorkloadGateway().execute(
        AIRequest(capability=AICapability.CLASSIFICATION, stage="CLASSIFY"),
        provider=provider,
        model="legacy-model",
        messages=[{"role": "user", "content": "ping"}],
        location=AIModelLocation.REMOTE,
    )

    assert provider.calls == [("text", "legacy-model")]
    assert result.data == "plain"
    assert result.remote_attempted and not result.local_attempted


def test_gateway_runs_budgeted_attempts_against_actual_fallback_provider(
    app_and_session, monkeypatch
) -> None:
    class UnavailableLocal:
        name = "ollama"

        def generate_json(self, _messages, *, model):
            raise TimeoutError(f"{model} unavailable")

    class Remote:
        name = "remote"

        def __init__(self) -> None:
            self.models: list[str] = []

        def generate_json(self, _messages, *, model):
            self.models.append(model)
            return LLMResult('{"ok":true}', self.name, model, {})

    _, factory = app_and_session
    remote = Remote()
    locations: list[str] = []
    monkeypatch.setattr(
        "zhijian.ai.gateway.ensure_ai_budget",
        lambda _db, _job, *, location, input_chars: locations.append(f"{location}:{input_chars}"),
    )
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.commit()
        result = AIWorkloadGateway().execute_cached_json(
            db,
            job=job,
            stage="GENERATE_AI_NOTE",
            capability="GLOBAL_SYNTHESIS",
            provider=FallbackLLMProvider(
                UnavailableLocal(),
                "local-model",
                remote,
                "remote-model",
                retry_count=0,
                request_interval_seconds=0,
            ),
            provider_name="ollama",
            model="local-model",
            messages=[{"role": "user", "content": "evidence"}],
            semantic_options={},
            cache_enabled=False,
            force_regenerate=False,
        )

    assert result.provider == "remote"
    assert remote.models == ["remote-model"]
    assert locations == ["LOCAL:8", "REMOTE:8"]
