from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any, Protocol

import httpx

AttemptCallback = Callable[[str, str, str, int, int, "LLMResult | None", "Exception | None"], None]


@dataclass(slots=True)
class LLMResult:
    content: str
    provider: str
    model: str
    usage: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderRequestOptions:
    temperature: float | None = None
    max_output_tokens: int | None = None
    thinking: bool | None = None


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
    def __init__(self, name: str, base_url: str, api_key: str, timeout: float = 120) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool,
        options: ProviderRequestOptions | None = None,
    ) -> LLMResult:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if options and options.temperature is not None:
            payload["temperature"] = options.temperature
        if options and options.max_output_tokens is not None:
            payload["max_tokens"] = options.max_output_tokens
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResult(
            content=data["choices"][0]["message"]["content"],
            provider=self.name,
            model=model,
            usage=data.get("usage", {}),
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
    """Use a second saved model only when a different provider can help."""

    _blocked_until: dict[str, float] = {}

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
        sleeper: Callable[[float], None] = sleep,
        request_options: ProviderRequestOptions | None = None,
    ) -> None:
        self.primary = primary
        self.primary_model = primary_model
        self.fallback = fallback
        self.fallback_model = fallback_model
        self.primary_disabled = False
        self.before_fallback = before_fallback
        self.retry_count = retry_count
        self.retry_wait_seconds = retry_wait_seconds
        self.request_interval_seconds = request_interval_seconds
        self.on_retry = on_retry
        self.on_attempt = on_attempt
        self.sleeper = sleeper
        self.request_options = request_options

    @staticmethod
    def _endpoint(provider: LLMProvider) -> str:
        return str(getattr(provider, "base_url", "")).rstrip("/").lower()

    @staticmethod
    def _retry_after(exc: Exception) -> float:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
            try:
                return max(1.0, float(exc.response.headers.get("Retry-After", "60")))
            except ValueError:
                return 60.0
        return 0.0

    @staticmethod
    def _retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in {408, 409, 425, 429} or exc.response.status_code >= 500
        return isinstance(exc, (httpx.HTTPError, TimeoutError, ConnectionError, ValueError))

    def _invoke(
        self, provider: LLMProvider, method: str, messages: list[dict[str, str]], model: str, route: str
    ) -> LLMResult:
        endpoint = self._endpoint(provider)
        input_chars = sum(len(str(message.get("content") or "")) for message in messages)
        for attempt in range(self.retry_count + 1):
            if endpoint and self._blocked_until.get(endpoint, 0.0) > monotonic():
                exc = httpx.HTTPStatusError(
                    "provider cooling down after rate limit",
                    request=httpx.Request("POST", endpoint),
                    response=httpx.Response(429, request=httpx.Request("POST", endpoint)),
                )
                if self.on_attempt:
                    self.on_attempt(
                        getattr(provider, "name", "ollama"),
                        model,
                        route,
                        attempt + 1,
                        input_chars,
                        None,
                        exc,
                    )
                raise exc
            if self.request_interval_seconds:
                self.sleeper(self.request_interval_seconds)
            if self.before_fallback:
                self.before_fallback()
            try:
                if self.request_options is None:
                    result = getattr(provider, method)(messages, model=model)
                else:
                    result = getattr(provider, method)(messages, model=model, options=self.request_options)
                if not result.content or not result.content.strip():
                    raise ValueError("模型返回了空内容")
                if self.on_attempt:
                    self.on_attempt(
                        result.provider, result.model, route, attempt + 1, input_chars, result, None
                    )
                return result
            except Exception as exc:
                if self.on_attempt:
                    self.on_attempt(
                        getattr(provider, "name", "ollama"),
                        model,
                        route,
                        attempt + 1,
                        input_chars,
                        None,
                        exc,
                    )
                cooldown = self._retry_after(exc)
                if cooldown and endpoint:
                    self._blocked_until[endpoint] = monotonic() + cooldown
                if attempt >= self.retry_count or not self._retryable(exc):
                    raise
                if self.on_retry:
                    self.on_retry(attempt + 1, exc)
                wait_seconds = max(self.retry_wait_seconds, cooldown)
                if wait_seconds:
                    self.sleeper(wait_seconds)
                if cooldown and endpoint:
                    self._blocked_until.pop(endpoint, None)
        raise RuntimeError("模型重试状态异常")

    def _call(self, method: str, messages: list[dict[str, str]]) -> LLMResult:
        if not self.primary_disabled:
            try:
                return self._invoke(self.primary, method, messages, self.primary_model, "primary")
            except (httpx.HTTPError, TimeoutError, ConnectionError, ValueError):
                self.primary_disabled = True
                if (
                    self.fallback is None
                    or not self.fallback_model
                    or (
                        self._endpoint(self.primary)
                        and self._endpoint(self.primary) == self._endpoint(self.fallback)
                    )
                ):
                    raise
        if self.fallback is None or not self.fallback_model:
            raise ValueError("主模型不可用且未配置备用模型")
        return self._invoke(self.fallback, method, messages, self.fallback_model, "fallback")

    def generate_text(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = options
        return self._call("generate_text", messages)

    def generate_json(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = options
        return self._call("generate_json", messages)

    def generate(
        self, messages: list[dict[str, str]], *, model: str, options: ProviderRequestOptions | None = None
    ) -> LLMResult:
        if options is not None:
            self.request_options = options
        return self._call("generate", messages)
