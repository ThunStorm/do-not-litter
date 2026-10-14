import json
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.budget import ensure_ai_budget, remaining_ai_wall_seconds
from zhijian.ai.cache import cached_json_result
from zhijian.ai.capabilities import AIModelLocation
from zhijian.ai.reliability import check_output_budget
from zhijian.ai.request_compiler import CompiledRequest
from zhijian.ai.request_metrics import provider_cache_metrics, request_metrics
from zhijian.ai.resource_manager import local_ai_resource_manager
from zhijian.ai.runtime_hints import runtime_hint_scope
from zhijian.ai.schemas import AIRequest, AIResult
from zhijian.ai.structured_output import stage_json_schema, validate_structured_output
from zhijian.ai.token_usage import estimate_tokens
from zhijian.db.models import ExternalCallAudit, Job
from zhijian.providers.llm import (
    FallbackLLMProvider,
    LLMProvider,
    LLMResult,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderRequestOptions,
    interface_signature,
)
from zhijian.services.jobs import ensure_job_active, job_run_fence
from zhijian.services.model_attempts import advance_model_attempt


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
        attempt_metadata: dict[str, Any] | None = None,
        result_validator: Callable[[LLMResult], None] | None = None,
        fallback_only: bool = False,
        compiled_request: CompiledRequest | None = None,
        stage_deadline: float | None = None,
        domain_chars: int = 0,
        max_stage_attempts: int | None = None,
        max_input_tokens: int | None = None,
    ) -> LLMResult:
        """Cache one route result while enforcing budget and local serialization per actual attempt."""
        local_schema = stage_json_schema(stage)

        def validate_result(result: LLMResult) -> None:
            from zhijian.ai.reliability import AIProviderError

            try:
                check_output_budget(result.content, result.metadata, result.usage)
                validate_structured_output(result.content, stage, getattr(result, "metadata", {}))
                original = result.content
                if compiled_request:
                    already_decoded = bool(result.metadata.get("canonical_decoded"))
                    result.content = compiled_request.decode(
                        result.content, namespace_ids=not already_decoded
                    )
                    result.metadata["canonical_decoded"] = True
                    if not already_decoded:
                        result.metadata["original_result_hash"] = sha256(original.encode()).hexdigest()
                if result_validator:
                    result_validator(result)
            except AIProviderError as exc:
                result.metadata["parse_quality"] = (
                    "INCOMPLETE"
                    if exc.code in {"AI_PROVIDER_OUTPUT_TRUNCATED", "AI_PROVIDER_REASONING_BUDGET"}
                    else "INVALID"
                )
                raise

        hard_deadline = min(
            perf_counter() + remaining_ai_wall_seconds(db, job) if job else float("inf"),
            stage_deadline if stage_deadline is not None else float("inf"),
        )

        def check_deadline() -> None:
            if job:
                ensure_job_active(db, job)
            if perf_counter() >= hard_deadline:
                from zhijian.ai.reliability import AIProviderError

                raise AIProviderError(
                    "AI_STAGE_WALL_TIME_EXCEEDED", "模型执行剩余时限已耗尽", switch_model=False
                )

        def check_request_limits(attempt_messages: list[dict[str, str]]) -> None:
            from zhijian.ai.reliability import AIProviderError

            if (
                max_input_tokens
                and estimate_tokens(sum(len(item.get("content") or "") for item in attempt_messages))
                > max_input_tokens
            ):
                raise AIProviderError(
                    "AI_STAGE_INPUT_BUDGET", "完整请求的输入估算超过阶段预算，需缩小分块", switch_model=False
                )
            if job and max_stage_attempts:
                rows = db.scalars(
                    select(ExternalCallAudit).where(
                        ExternalCallAudit.job_id == job.id, ExternalCallAudit.capability == "LLM"
                    )
                ).all()
                consumed = sum(
                    1
                    for row in rows
                    if (row.request_meta_json or {}).get("stage") == stage
                    and (row.request_meta_json or {}).get("run_fence") == job_run_fence(job)
                    and not (row.request_meta_json or {}).get("cache_hit")
                )
                if consumed >= max_stage_attempts:
                    raise AIProviderError(
                        "AI_PROVIDER_ATTEMPT_BUDGET", "本阶段实际调用已达到尝试上限", switch_model=False
                    )

        def call() -> LLMResult:
            if isinstance(provider, FallbackLLMProvider):
                provider.attempt_metadata = {
                    "stage": stage,
                    "request_metrics": request_metrics(messages, domain_chars=domain_chars),
                    **(compiled_request.identity if compiled_request else {}),
                    "input_hash": sha256(
                        json.dumps(
                            messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest(),
                    **{
                        key: value
                        for key, value in (attempt_metadata or {}).items()
                        if key
                        in {"chunk_index", "chunk_count", "split_path", "segment_count", "planned_calls"}
                    },
                }

                def run_attempt(
                    attempt_provider: LLMProvider,
                    method: str,
                    attempt_messages: list[dict[str, str]],
                    attempt_model: str,
                    options: ProviderRequestOptions | None,
                ) -> LLMResult:
                    if isinstance(attempt_provider, OllamaProvider) and local_schema:
                        options = replace(options or ProviderRequestOptions(), response_schema=local_schema)
                    return self._execute_attempt(
                        db,
                        job,
                        attempt_provider,
                        method,
                        attempt_messages,
                        attempt_model,
                        options,
                        ensure_budget=False,
                        deadline=hard_deadline,
                        attempt_id=provider._attempt_context.get("attempt_id"),
                        before_dispatch=provider.dispatch_guard,
                    )

                def ensure_attempt_budget(
                    attempt_provider: LLMProvider,
                    attempt_model: str,
                    attempt_messages: list[dict[str, str]],
                ) -> None:
                    check_deadline()
                    check_request_limits(attempt_messages)
                    provider_name = str(getattr(attempt_provider, "name", "ollama"))
                    ensure_ai_budget(
                        db,
                        job,
                        location="LOCAL" if provider_name == "ollama" else "REMOTE",
                        input_chars=sum(len(message.get("content") or "") for message in attempt_messages),
                        provider=provider_name,
                        model=attempt_model,
                        profile_id=getattr(attempt_provider, "profile_id", None),
                    )

                provider.before_attempt = ensure_attempt_budget
                provider.cancel_check = check_deadline
                provider.attempt_runner = run_attempt
                provider.result_validator = validate_result if not provider._legacy_reliability else None
                try:
                    return (
                        provider.generate_fallback_json(messages)
                        if fallback_only
                        else provider.generate_json(messages, model=model)
                    )
                finally:
                    provider.cancel_check = None
            check_deadline()
            check_request_limits(messages)
            result = self._execute_attempt(
                db,
                job,
                provider,
                "generate_json",
                messages,
                model,
                ProviderRequestOptions(response_schema=local_schema)
                if isinstance(provider, OllamaProvider) and local_schema
                else None,
                deadline=hard_deadline,
            )
            validate_result(result)
            return result

        semantic_options = {
            **semantic_options,
            "provider_execution_scope": runtime_hint_scope(provider, model),
        }
        if isinstance(provider, OllamaProvider) or isinstance(
            getattr(provider, "primary", None), OllamaProvider
        ):
            semantic_options = {**semantic_options, "native_response_schema": local_schema}
        if signature := interface_signature(provider):
            semantic_options = {**semantic_options, "interface_contract": signature}
        if compiled_request:
            semantic_options = {**semantic_options, **compiled_request.identity}
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
            validate=validate_result,
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
        *,
        ensure_budget: bool = True,
        deadline: float = float("inf"),
        attempt_id: str | None = None,
        before_dispatch: Callable[[], None] | None = None,
    ) -> LLMResult:
        provider_name = str(getattr(provider, "name", "ollama"))
        original_timeout = getattr(provider, "timeout", None)
        queued_at = perf_counter()
        if (job or deadline != float("inf")) and getattr(provider, "timeout", None) is not None:
            deadline = min(deadline, queued_at + float(provider.timeout))
        location = "LOCAL" if provider_name == "ollama" else "REMOTE"
        if ensure_budget:
            ensure_ai_budget(
                db,
                job,
                location=location,
                input_chars=sum(len(message.get("content") or "") for message in messages),
                provider=provider_name,
                model=model,
                profile_id=getattr(provider, "profile_id", None),
            )
            timeout = getattr(provider, "timeout", None)
            if timeout is not None and job is not None:
                provider.timeout = min(float(timeout), max(1.0, remaining_ai_wall_seconds(db, job)))

        def invoke() -> LLMResult:
            if perf_counter() >= deadline:
                from zhijian.ai.reliability import AIProviderError

                raise AIProviderError(
                    "AI_STAGE_WALL_TIME_EXCEEDED", "排队后模型执行时限已耗尽", switch_model=False
                )
            if job:
                ensure_job_active(db, job)
            if getattr(provider, "timeout", None) is not None:
                provider.timeout = min(float(provider.timeout), deadline - perf_counter())
            if isinstance(provider, (OllamaProvider, OpenAICompatibleProvider)):
                provider.cancel_check = check_active if job or deadline != float("inf") else None
            if attempt_id:
                advance_model_attempt(db, attempt_id, "DISPATCHED")
            if before_dispatch:
                before_dispatch()
                check_active()
                if getattr(provider, "timeout", None) is not None:
                    provider.timeout = min(float(provider.timeout), deadline - perf_counter())
            started = perf_counter()
            result = (
                getattr(provider, method)(messages, model=model)
                if options is None
                else getattr(provider, method)(messages, model=model, options=options)
            )
            if not isinstance(result, LLMResult):
                result = LLMResult(
                    result.content,
                    result.provider,
                    result.model,
                    dict(getattr(result, "usage", {}) or {}),
                    dict(getattr(result, "metadata", {}) or {}),
                )
            check_active()
            provider_ms = round((perf_counter() - started) * 1000)
            if attempt_id:
                advance_model_attempt(db, attempt_id, "VALIDATING")
            result.metadata["request_metrics"] = {
                **request_metrics(messages),
                **result.metadata.get("request_metrics", {}),
            }
            result.metadata.update(provider_cache_metrics(result.usage, result.metadata.get("usage_source")))
            result.metadata["provider_ms"] = provider_ms
            result.metadata["queue_ms"] = round((started - queued_at) * 1000)
            return result

        def check_active() -> None:
            if job:
                ensure_job_active(db, job)
            if perf_counter() >= deadline:
                from zhijian.ai.reliability import AIProviderError

                raise AIProviderError(
                    "AI_STAGE_WALL_TIME_EXCEEDED", "等待已耗尽模型执行时限", switch_model=False
                )

        try:
            if location == "LOCAL":
                return local_ai_resource_manager.run("TEXT_LLM", invoke, cancel_check=check_active)
            return invoke()
        finally:
            if original_timeout is not None:
                provider.timeout = original_timeout
            if isinstance(provider, (OllamaProvider, OpenAICompatibleProvider)):
                provider.cancel_check = None

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
