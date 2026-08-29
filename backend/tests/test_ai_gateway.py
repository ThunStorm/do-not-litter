from zhijian.ai import (
    AICapability,
    AIEvidenceSegment,
    AIModelLocation,
    AIRequest,
    AIWorkloadGateway,
)
from zhijian.providers.llm import LLMResult


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
