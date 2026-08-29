from time import perf_counter

from zhijian.ai.capabilities import AIModelLocation
from zhijian.ai.schemas import AIRequest, AIResult
from zhijian.providers.llm import LLMProvider


class AIWorkloadGateway:
    """WP1 pass-through seam; routing, validation, cache and audit arrive in later packages."""

    def execute(
        self,
        request: AIRequest,
        *,
        provider: LLMProvider,
        model: str,
        messages: list[dict[str, str]],
        location: AIModelLocation,
    ) -> AIResult:
        started = perf_counter()
        selected_model = request.model_override or model
        result = (
            provider.generate_json(messages, model=selected_model)
            if request.output_schema is not None
            else provider.generate_text(messages, model=selected_model)
        )
        usage = result.usage
        cached_tokens = usage.get("cached_tokens")
        if cached_tokens is None:
            cached_tokens = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        return AIResult(
            data=result.content,
            provider=result.provider,
            model=result.model,
            capability=request.capability,
            execution_route="DIRECT",
            local_attempted=location == AIModelLocation.LOCAL,
            remote_attempted=location == AIModelLocation.REMOTE,
            evidence_ids=[segment.id for segment in request.evidence_segments],
            input_tokens=usage.get("prompt_tokens", usage.get("prompt_eval_count")),
            output_tokens=usage.get("completion_tokens", usage.get("eval_count")),
            cached_tokens=cached_tokens,
            duration_ms=round((perf_counter() - started) * 1000),
        )
