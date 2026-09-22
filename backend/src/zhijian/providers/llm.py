from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter, sleep
from typing import Any, Protocol

import httpx

from zhijian.ai.reliability import (
    AIProviderError,
    ModelReliabilityPolicy,
    ReliabilityGuards,
    classify_provider_error,
    provider_identity,
    provider_rate_limit_identity,
    retry_after_seconds,
    retry_wait_seconds,
)

AttemptCallback = Callable[
    [str, str, str, int, int, "LLMResult | None", "Exception | None", int, dict[str, Any]], None
]
AttemptStartCallback = Callable[[str, str, str, int, int, dict[str, Any]], str | None]
BeforeAttemptCallback = Callable[["LLMProvider", str, list[dict[str, str]]], None]
FallbackDecider = Callable[[AIProviderError], bool]
AttemptRunner = Callable[
    ["LLMProvider", str, list[dict[str, str]], str, "ProviderRequestOptions | None"], "LLMResult"
]


@dataclass(slots=True)
class LLMResult:
    content: str
    provider: str
    model: str
    usage: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderRequestOptions:
    temperature: float | None = None
    max_output_tokens: int | None = None
    thinking: bool | None = None
    context_window: int | None = None


class LLMProvider(Protocol):
    def generate_text(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult: ...

    def generate_json(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult: ...

    def generate(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult: ...


def provider_error_details(exc: Exception) -> dict[str, Any]:
    """Return bounded, structured provider diagnostics without persisting response bodies."""

    response = getattr(exc, "response", None) or getattr(getattr(exc, "cause", None), "response", None)
    status_code = getattr(response, "status_code", None)
    details: dict[str, Any] = {"type": type(exc).__name__, "message": _redact_provider_text(str(exc))}
    if status_code is not None:
        details["status_code"] = int(status_code)
        headers = getattr(response, "headers", {})
        for key in ("x-request-id", "request-id"):
            if headers.get(key):
                details["request_id"] = str(headers[key])[:160]
                break
        try:
            payload = response.json()
        except (TypeError, ValueError):
            payload = None
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            for key in ("code", "type", "message"):
                value = error.get(key)
                if isinstance(value, (str, int, float)) and value != "":
                    details[f"provider_{key}"] = _redact_provider_text(str(value))
            if details.get("provider_message"):
                details["message"] = details["provider_message"]
        retry_after = headers.get("retry-after")
        if retry_after:
            details["retry_after"] = str(retry_after)[:32]
    classified = classify_provider_error(exc)
    details["code"] = classified.code
    reliability = getattr(exc, "reliability_metadata", None)
    if isinstance(reliability, dict):
        details["reliability"] = reliability
    return details


def _redact_provider_text(value: str) -> str:
    text = str(value)
    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(api[-_]?key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED]", text)
    return text[:500]


class OllamaProvider:
    def __init__(self, base_url: str, timeout: float = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool,
        options: ProviderRequestOptions | None = None,
    ) -> LLMResult:
        runtime_options = {}
        if options and options.temperature is not None:
            runtime_options["temperature"] = options.temperature
        if options and options.max_output_tokens is not None:
            runtime_options["num_predict"] = options.max_output_tokens
        if options and options.context_window is not None:
            runtime_options["num_ctx"] = options.context_window
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "keep_alive": 0,
                **({"format": "json"} if json_mode else {}),
                **({"options": runtime_options} if runtime_options else {}),
                **({"think": options.thinking} if options and options.thinking is not None else {}),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResult(
            content=data.get("message", {}).get("content", ""),
            provider="ollama",
            model=model,
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
            metadata={
                "finish_reason": data.get("done_reason"),
                "content_length": len(data.get("message", {}).get("content", "")),
            },
        )

    def generate_text(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self._generate(messages, model=model, json_mode=False, options=options)

    def generate_json(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self._generate(messages, model=model, json_mode=True, options=options)

    def generate(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self.generate_json(messages, model=model, options=options)


class OpenAICompatibleProvider:
    def __init__(
        self, name: str, base_url: str, api_key: str, timeout: float = 120, *, supports_json_mode: bool = True
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.supports_json_mode = supports_json_mode

    def _generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool,
        options: ProviderRequestOptions | None = None,
    ) -> LLMResult:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode and self.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}
        if options and options.temperature is not None:
            payload["temperature"] = options.temperature
        if options and options.max_output_tokens is not None:
            payload["max_tokens"] = options.max_output_tokens
        if (
            options
            and options.thinking is not None
            and (self.name.lower() == "deepseek" or "api.deepseek.com" in self.base_url.lower())
        ):
            payload["thinking"] = {"type": "enabled" if options.thinking else "disabled"}
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            data = response.json()
            choice = (data.get("choices") or [])[0]
            message = choice.get("message") or {}
            content = message.get("content")
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(
                "AI_PROVIDER_EMPTY_RESPONSE", "Provider 未返回可用 choices", retryable=True, cause=exc
            ) from exc
        return LLMResult(
            content=str(content or ""),
            provider=self.name,
            model=str(data.get("model") or model),
            usage=data.get("usage", {}),
            metadata={
                "finish_reason": choice.get("finish_reason"),
                "response_id": data.get("id"),
                "request_id": response.headers.get("x-request-id") or response.headers.get("request-id"),
                "content_length": len(str(content or "")),
            },
        )

    def generate_text(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self._generate(messages, model=model, json_mode=False, options=options)

    def generate_json(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self._generate(messages, model=model, json_mode=True, options=options)

    def generate(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        return self.generate_json(messages, model=model, options=options)


class FallbackLLMProvider:
    """Run each saved model under its own reliability policy before switching routes."""

    def __init__(
        self,
        primary: LLMProvider,
        primary_model: str,
        fallback: LLMProvider | None,
        fallback_model: str | None,
        before_fallback: Callable[[], None] | None = None,
        retry_count: int = 2,
        retry_wait_seconds: float = 5,
        request_interval_seconds: float = 1,
        on_retry: Callable[[int, Exception], None] | None = None,
        on_attempt: AttemptCallback | None = None,
        on_attempt_start: AttemptStartCallback | None = None,
        before_attempt: BeforeAttemptCallback | None = None,
        attempt_runner: AttemptRunner | None = None,
        sleeper: Callable[[float], None] = sleep,
        request_options: ProviderRequestOptions | None = None,
        fallback_request_interval_seconds: float | None = None,
        fallback_request_options: ProviderRequestOptions | None = None,
        attempt_metadata: dict[str, Any] | None = None,
        primary_reliability: ModelReliabilityPolicy | None = None,
        fallback_reliability: ModelReliabilityPolicy | None = None,
        result_validator: Callable[[LLMResult], None] | None = None,
        fallback_decider: FallbackDecider | None = None,
        max_attempts: int | None = None,
    ) -> None:
        self.primary, self.primary_model = primary, primary_model
        self.fallback, self.fallback_model = fallback, fallback_model
        self.primary_disabled = False
        self.before_fallback = before_fallback
        self.retry_count = retry_count
        self.retry_wait_seconds = retry_wait_seconds
        self.on_retry, self.on_attempt, self.on_attempt_start, self.before_attempt = (
            on_retry,
            on_attempt,
            on_attempt_start,
            before_attempt,
        )
        self.attempt_runner, self.sleeper = (
            attempt_runner,
            sleeper,
        )
        self.request_options, self.fallback_request_options = request_options, fallback_request_options
        self.attempt_metadata = dict(attempt_metadata or {})
        self.primary_reliability = primary_reliability or ModelReliabilityPolicy(
            "DIRECT", request_interval_seconds=request_interval_seconds, retry_count=retry_count
        )
        self.fallback_reliability = fallback_reliability or ModelReliabilityPolicy(
            "DIRECT",
            request_interval_seconds=(
                fallback_request_interval_seconds
                if fallback_request_interval_seconds is not None
                else request_interval_seconds
            ),
            retry_count=retry_count,
        )
        self.result_validator = result_validator
        self.fallback_decider = fallback_decider
        self.max_attempts = max_attempts
        self._legacy_reliability = primary_reliability is None and fallback_reliability is None
        self._remaining_attempts = 0
        self._attempt_context: dict[str, Any] = {}

    @staticmethod
    def _same_target(
        primary: LLMProvider, primary_model: str, fallback: LLMProvider, fallback_model: str
    ) -> bool:
        return provider_identity(primary, primary_model) == provider_identity(fallback, fallback_model)

    def _attempt_metadata(self, provider: LLMProvider, policy: ModelReliabilityPolicy) -> dict[str, Any]:
        if self._legacy_reliability:
            return dict(self.attempt_metadata)
        metadata = {**self.attempt_metadata, **self._attempt_context, "reliability_mode": policy.mode}
        timeout = getattr(provider, "timeout", None)
        if timeout is not None:
            metadata["timeout_seconds"] = timeout
        profile_id = getattr(provider, "profile_id", None)
        if profile_id:
            metadata["profile_id"] = profile_id
        return metadata

    def _invoke(
        self,
        provider: LLMProvider,
        method: str,
        messages: list[dict[str, str]],
        model: str,
        route: str,
        policy: ModelReliabilityPolicy,
    ) -> LLMResult:
        input_chars = sum(len(str(message.get("content") or "")) for message in messages)
        key = provider_identity(provider, model)
        http_retries = json_retries = attempt = 0
        call_messages = list(messages)
        while True:
            if self._remaining_attempts <= 0:
                raise AIProviderError(
                    "AI_PROVIDER_ATTEMPT_BUDGET", "本次模型调用已达到尝试上限", switch_model=True
                )
            attempt += 1
            semaphore = None
            wait_before = 0.0
            circuit_state = "CLOSED"
            started = perf_counter()
            result: LLMResult | None = None
            attempt_id: str | None = None
            try:
                if self._legacy_reliability and policy.request_interval_seconds:
                    self.sleeper(policy.request_interval_seconds)
                semaphore, wait_before, circuit_state = ReliabilityGuards.acquire(
                    key,
                    policy,
                    limiter_key=provider_rate_limit_identity(provider),
                )
                if wait_before:
                    self.sleeper(wait_before)
                if route == "fallback" and self.before_fallback:
                    self.before_fallback()
                if self.before_attempt:
                    self.before_attempt(provider, model, call_messages)
                attempt_metadata = self._attempt_metadata(provider, policy)
                if self.on_attempt_start:
                    attempt_id = self.on_attempt_start(
                        str(getattr(provider, "name", "ollama")),
                        model,
                        route,
                        attempt,
                        input_chars,
                        attempt_metadata,
                    )
                self._remaining_attempts -= 1
                options = self.fallback_request_options if route == "fallback" else self.request_options
                if self.attempt_runner:
                    result = self.attempt_runner(provider, method, call_messages, model, options)
                elif options is None:
                    result = getattr(provider, method)(call_messages, model=model)
                else:
                    result = getattr(provider, method)(call_messages, model=model, options=options)
                if str(result.metadata.get("finish_reason") or "").lower() in {"length", "max_tokens"}:
                    raise AIProviderError("AI_PROVIDER_OUTPUT_TRUNCATED", "模型输出达到长度上限")
                if not result.content or not result.content.strip():
                    raise AIProviderError("AI_PROVIDER_EMPTY_RESPONSE", "模型返回了空内容", retryable=True)
                if method == "generate_json" and self.result_validator:
                    self.result_validator(result)
            except Exception as exc:
                if type(exc).__name__ == "JobCancelled":
                    if self.on_attempt and attempt_id:
                        metadata = self._attempt_metadata(provider, policy)
                        metadata["attempt_id"] = attempt_id
                        self.on_attempt(
                            str(getattr(provider, "name", "ollama")),
                            model,
                            route,
                            attempt,
                            input_chars,
                            result,
                            exc,
                            round((perf_counter() - started) * 1000),
                            metadata,
                        )
                    raise
                error = classify_provider_error(exc)
                if error.code == "AI_BUDGET_EXCEEDED":
                    raise error from exc
                is_json_error = error.code in {"AI_PROVIDER_INVALID_JSON", "AI_PROVIDER_SCHEMA_INVALID"}
                retry_json = is_json_error and json_retries < policy.json_retry_count
                retry_http = not is_json_error and error.retryable and http_retries < policy.retry_count
                retry = retry_json or retry_http
                if retry_json:
                    json_retries += 1
                    call_messages = [
                        *messages,
                        {
                            "role": "system",
                            "content": (
                                "上一次响应无法被解析。只返回合法 JSON 对象，不要 Markdown、"
                                "解释或代码块，并保持原字段契约。"
                            ),
                        },
                    ]
                elif retry_http:
                    http_retries += 1
                circuit_state = ReliabilityGuards.failure(key, policy, error)
                if not retry:
                    wait_seconds = 0.0
                elif self._legacy_reliability:
                    wait_seconds = max(
                        self.retry_wait_seconds,
                        retry_after_seconds(error.cause or error) or 0,
                    )
                else:
                    wait_seconds = retry_wait_seconds(error.cause or error, max(http_retries, json_retries))
                error.reliability_metadata = {
                    "circuit_state": circuit_state,
                    "wait_seconds": round(wait_seconds, 3),
                    "retry_after": getattr(getattr(error.cause, "response", None), "headers", {}).get(
                        "Retry-After"
                    ),
                    "recovery": "retry_same_model" if retry_json else None,
                    "json_attempt": json_retries or None,
                }
                self._attempt_context = error.reliability_metadata
                if self.on_attempt:
                    metadata = self._attempt_metadata(provider, policy)
                    if attempt_id:
                        metadata["attempt_id"] = attempt_id
                    self.on_attempt(
                        str(getattr(provider, "name", "ollama")),
                        model,
                        route,
                        attempt,
                        input_chars,
                        result,
                        error,
                        round((perf_counter() - started) * 1000),
                        metadata,
                    )
                if not retry:
                    raise error from exc
                if self.on_retry:
                    self.on_retry(attempt, error)
                if wait_seconds:
                    self.sleeper(wait_seconds)
            else:
                ReliabilityGuards.success(key)
                result.metadata = {
                    **result.metadata,
                    "circuit_state": circuit_state,
                    "wait_seconds": wait_before,
                }
                self._attempt_context = result.metadata
                if self.on_attempt:
                    metadata = self._attempt_metadata(provider, policy)
                    if attempt_id:
                        metadata["attempt_id"] = attempt_id
                    self.on_attempt(
                        result.provider,
                        result.model,
                        route,
                        attempt,
                        input_chars,
                        result,
                        None,
                        round((perf_counter() - started) * 1000),
                        metadata,
                    )
                return result
            finally:
                ReliabilityGuards.release(semaphore)

    def _call(self, method: str, messages: list[dict[str, str]]) -> LLMResult:
        if not self._legacy_reliability:
            self.primary_disabled = False
        free_tier = "FREE_TIER" in {self.primary_reliability.mode, self.fallback_reliability.mode}
        self._remaining_attempts = (
            4
            if free_tier
            else 1 + self.primary_reliability.retry_count + self.primary_reliability.json_retry_count
        )
        if self.fallback:
            self._remaining_attempts += (
                1 + self.fallback_reliability.retry_count + self.fallback_reliability.json_retry_count
            )
        if self.max_attempts is not None:
            self._remaining_attempts = min(self._remaining_attempts, self.max_attempts)
        if not self.primary_disabled:
            try:
                return self._invoke(
                    self.primary, method, messages, self.primary_model, "primary", self.primary_reliability
                )
            except AIProviderError as exc:
                self.primary_disabled = True
                if (
                    self.fallback is None
                    or not self.fallback_model
                    or not exc.switch_model
                    or (self.fallback_decider is not None and not self.fallback_decider(exc))
                    or self._same_target(self.primary, self.primary_model, self.fallback, self.fallback_model)
                ):
                    raise
        if self.fallback is None or not self.fallback_model:
            raise AIProviderError("AI_PROVIDER_UNAVAILABLE", "主模型不可用且未配置备用模型")
        return self._invoke(
            self.fallback, method, messages, self.fallback_model, "fallback", self.fallback_reliability
        )

    def generate_text(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = self.fallback_request_options = options
        return self._call("generate_text", messages)

    def generate_json(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = self.fallback_request_options = options
        return self._call("generate_json", messages)

    def generate_fallback_json(self, messages: list[dict[str, str]]) -> LLMResult:
        if self.fallback is None or not self.fallback_model:
            raise AIProviderError("AI_PROVIDER_UNAVAILABLE", "当前阶段没有可用备用模型")
        self._remaining_attempts = (
            1 + self.fallback_reliability.retry_count + self.fallback_reliability.json_retry_count
        )
        if self.max_attempts is not None:
            self._remaining_attempts = min(self._remaining_attempts, self.max_attempts)
        return self._invoke(
            self.fallback,
            "generate_json",
            messages,
            self.fallback_model,
            "fallback",
            self.fallback_reliability,
        )

    def generate(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = self.fallback_request_options = options
        return self._call("generate", messages)
