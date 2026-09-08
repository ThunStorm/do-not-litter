from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from zhijian.ai.budget import ensure_ai_budget
from zhijian.ai.cache import cached_json_result
from zhijian.ai.capabilities import AIModelLocation
from zhijian.ai.resource_manager import local_ai_resource_manager
from zhijian.ai.schemas import AIRequest, AIResult
from zhijian.db.models import Job
from zhijian.providers.llm import FallbackLLMProvider, LLMProvider, LLMResult, ProviderRequestOptions


class AIWorkloadGateway:
    """Shared execution boundary for model attempts after a stage has selected its route."""

    def execute_cached_json(
        self,
        db: Session,
        *,
        job: Job | None,
        stage: str,
        capability: str,
        provider: LLMProvider,
        provider_name: str,
        model: str,
        messages: list[dict[str, str]],
        semantic_options: dict[str, Any],
        cache_enabled: bool,
        force_regenerate: bool,
    ) -> LLMResult:
        """Cache one route result while enforcing budget and local serialization per actual attempt."""

        def call() -> LLMResult:
            if isinstance(provider, FallbackLLMProvider):
                def run_attempt(
                    attempt_provider: LLMProvider,
                    method: str,
                    attempt_messages: list[dict[str, str]],
                    attempt_model: str,
                    options: ProviderRequestOptions | None,
                ) -> LLMResult:
                    return self._execute_attempt(
                        db, job, attempt_provider, method, attempt_messages, attempt_model, options
                    )

                provider.attempt_runner = run_attempt
                return provider.generate_json(messages, model=model)
            return self._execute_attempt(db, job, provider, "generate_json", messages, model, None)

        return cached_json_result(
            db,
            job=job,
            stage=stage,
            capability=capability,
            provider=provider_name,
            model=model,
            messages=messages,
            semantic_options=semantic_options,
            location="LOCAL" if provider_name == "ollama" else "REMOTE",
            cache_enabled=cache_enabled,
            force_regenerate=force_regenerate,
            call=call,
        )

    @staticmethod
    def _execute_attempt(
        db: Session,
        job: Job | None,
        provider: LLMProvider,
        method: str,
        messages: list[dict[str, str]],
        model: str,
        options: ProviderRequestOptions | None,
    ) -> LLMResult:
        provider_name = str(getattr(provider, "name", "ollama"))
        location = "LOCAL" if provider_name == "ollama" else "REMOTE"
        ensure_ai_budget(
            db,
            job,
            location=location,
            input_chars=sum(len(message.get("content") or "") for message in messages),
        )

        def invoke() -> LLMResult:
            if options is None:
                return getattr(provider, method)(messages, model=model)
            return getattr(provider, method)(messages, model=model, options=options)

        return local_ai_resource_manager.run("TEXT_LLM", invoke) if location == "LOCAL" else invoke()

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
