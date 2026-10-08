"""Per-model reliability policy and process-local execution guards."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock, Semaphore
from time import monotonic
from typing import Any, Literal

import httpx

ReliabilityMode = Literal["DIRECT", "STANDARD", "GUARDED", "FREE_TIER"]


@dataclass(frozen=True, slots=True)
class ModelReliabilityPolicy:
    mode: ReliabilityMode
    request_interval_seconds: float = 0
    max_concurrency: int | None = None
    retry_count: int = 0
    json_retry_count: int = 0
    rate_limit_rpm: int | None = None
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold: int = 3
    circuit_breaker_cooldown_seconds: float = 60


_PRESETS: dict[ReliabilityMode, ModelReliabilityPolicy] = {
    "DIRECT": ModelReliabilityPolicy("DIRECT"),
    "STANDARD": ModelReliabilityPolicy("STANDARD", retry_count=1, json_retry_count=1),
    "GUARDED": ModelReliabilityPolicy(
        "GUARDED",
        request_interval_seconds=2,
        max_concurrency=1,
        retry_count=2,
        json_retry_count=1,
        circuit_breaker_enabled=True,
        circuit_breaker_cooldown_seconds=60,
    ),
    "FREE_TIER": ModelReliabilityPolicy(
        "FREE_TIER",
        request_interval_seconds=4,
        max_concurrency=1,
        retry_count=2,
        json_retry_count=1,
        circuit_breaker_enabled=True,
        circuit_breaker_cooldown_seconds=120,
    ),
}


def resolve_reliability_policy(value: dict[str, Any] | None) -> ModelReliabilityPolicy:
    value = value or {}
    raw_mode = str(value.get("reliability_mode") or "STANDARD").upper()
    mode: ReliabilityMode = raw_mode if raw_mode in _PRESETS else "STANDARD"
    preset = _PRESETS[mode]

    def number(key: str, default: float | int | None) -> float | int | None:
        raw = value.get(key)
        return default if raw is None or raw == "" else raw

    return ModelReliabilityPolicy(
        mode=mode,
        request_interval_seconds=float(
            number("request_interval_seconds", preset.request_interval_seconds) or 0
        ),
        max_concurrency=(
            int(number("max_concurrency", preset.max_concurrency))
            if number("max_concurrency", preset.max_concurrency) is not None
            else None
        ),
        retry_count=int(number("retry_count", preset.retry_count) or 0),
        json_retry_count=int(number("json_retry_count", preset.json_retry_count) or 0),
        rate_limit_rpm=(
            int(number("rate_limit_rpm", preset.rate_limit_rpm))
            if number("rate_limit_rpm", preset.rate_limit_rpm) is not None
            else None
        ),
        circuit_breaker_enabled=bool(number("circuit_breaker_enabled", preset.circuit_breaker_enabled)),
        circuit_breaker_threshold=int(
            number("circuit_breaker_threshold", preset.circuit_breaker_threshold) or 3
        ),
        circuit_breaker_cooldown_seconds=float(
            number("circuit_breaker_cooldown_seconds", preset.circuit_breaker_cooldown_seconds) or 60
        ),
    )


class AIProviderError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        switch_model: bool = True,
        open_circuit: bool = False,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.switch_model = switch_model and not code.startswith("AI_PROVIDER_INTERFACE_")
        self.open_circuit = open_circuit
        self.cause = cause


def classify_provider_error(exc: Exception) -> AIProviderError:
    if isinstance(exc, AIProviderError):
        return exc
    if getattr(exc, "code", None) == "AI_BUDGET_EXCEEDED":
        return AIProviderError(
            "AI_BUDGET_EXCEEDED",
            str(exc),
            retryable=False,
            switch_model=False,
            cause=exc,
        )
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    text = str(exc).lower()
    payload = {}
    try:
        payload = response.json() if response is not None else {}
        error = payload.get("error") if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            text = " ".join(str(error.get(key) or "") for key in ("code", "type", "message")).lower()
    except (TypeError, ValueError):
        pass
    mux_code = (
        str((payload.get("error") or {}).get("code") or "")
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict)
        else ""
    )
    mux_errors = {
        "LMX_PROCESS_TIMEOUT": ("AI_PROVIDER_TIMEOUT", "本机路由调用超时，请核对上游总时限与空闲时限", False),
        "LMX_QUOTA_EXHAUSTED": (
            "AI_PROVIDER_QUOTA_EXHAUSTED",
            "订阅额度已耗尽，请等待恢复或选择已授权备用模型",
            True,
        ),
        "LMX_RATE_LIMITED": ("AI_PROVIDER_THROTTLED", "本机路由连接繁忙或供应商限流，请稍后重试", False),
        "LMX_AUTH_REQUIRED": ("AI_PROVIDER_AUTH_ERROR", "上游 CLI 需要重新登录", True),
        "LMX_PROVIDER_COOLDOWN": ("AI_PROVIDER_CIRCUIT_OPEN", "上游连接仍在冷却，请稍后重试", False),
    }
    if mux_code in mux_errors:
        code, message, open_circuit = mux_errors[mux_code]
        # CLI timeouts may consume usage; prefer a configured fallback over repeating them.
        return AIProviderError(code, message, retryable=False, open_circuit=open_circuit, cause=exc)
    if status in {400, 404} and re.search(
        r"0 endpoints out of .* available|zdr violation|guardrail restrictions|data policy",
        text,
    ):
        return AIProviderError(
            "AI_PROVIDER_POLICY_BLOCKED",
            (
                "OpenRouter 隐私/ZDR 策略没有可用端点；请调整 OpenRouter Privacy/Guardrail，"
                "或改用支持 ZDR 的模型"
            ),
            cause=exc,
        )
    if status == 429:
        throttled = bool(re.search(r"\b(?:tpm|rpm)\b|inference exceeds", text))
        if throttled:
            return AIProviderError(
                "AI_PROVIDER_THROTTLED",
                str(exc),
                retryable=False,
                open_circuit=True,
                cause=exc,
            )
        quota = bool(re.search(r"quota|exhausted|insufficient|balance", text))
        return AIProviderError(
            "AI_PROVIDER_QUOTA_EXHAUSTED" if quota else "AI_PROVIDER_RATE_LIMITED",
            str(exc),
            retryable=not quota,
            open_circuit=quota,
            cause=exc,
        )
    if status in {401, 403}:
        return AIProviderError("AI_PROVIDER_AUTH_ERROR", str(exc), open_circuit=True, cause=exc)
    if status == 400:
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            mux_code = payload["error"].get("code")
            if mux_code in {"LMX_UNSUPPORTED_MESSAGES", "LMX_UNSUPPORTED_PARAMETER", "LMX_INVALID_REQUEST"}:
                messages = {
                    "LMX_UNSUPPORTED_MESSAGES": "本机路由接口尚未支持本次消息组合，请核对上游桥接能力",
                    "LMX_UNSUPPORTED_PARAMETER": (
                        "本机路由接口尚未支持请求参数，请读取接口能力或采用模型默认值"
                    ),
                    "LMX_INVALID_REQUEST": "本机路由接口拒绝了请求格式，请核对接口版本和配置",
                }
                return AIProviderError("AI_PROVIDER_INTERFACE_INVALID", messages[mux_code], cause=exc)
        return AIProviderError("AI_PROVIDER_BAD_REQUEST", str(exc), switch_model=False, cause=exc)
    if status == 404:
        return AIProviderError("AI_PROVIDER_NOT_FOUND", str(exc), cause=exc)
    if status == 408:
        return AIProviderError("AI_PROVIDER_TIMEOUT", str(exc), retryable=True, cause=exc)
    if status is not None and int(status) >= 500:
        return AIProviderError("AI_PROVIDER_HTTP_5XX", str(exc), retryable=True, cause=exc)
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return AIProviderError("AI_PROVIDER_TIMEOUT", str(exc), retryable=True, cause=exc)
    if isinstance(exc, (httpx.HTTPError, ConnectionError)):
        return AIProviderError("AI_PROVIDER_NETWORK_ERROR", str(exc), retryable=True, cause=exc)
    return AIProviderError("AI_PROVIDER_RESPONSE_INVALID", str(exc), cause=exc)


def retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    raw = getattr(response, "headers", {}).get("Retry-After") if response is not None else None
    if not raw:
        return None
    try:
        return max(1.0, float(raw))
    except (TypeError, ValueError):
        return None


def retry_wait_seconds(exc: Exception, retry_number: int) -> float:
    retry_after = retry_after_seconds(exc)
    base = retry_after if retry_after is not None else min(20.0, 5.0 * (2 ** max(0, retry_number - 1)))
    return base * random.uniform(1.0, 1.3)


def provider_identity(provider: Any, model: str) -> str:
    name = str(getattr(provider, "name", "ollama")).lower()
    endpoint = str(getattr(provider, "base_url", "")).rstrip("/").lower()
    api_key = str(getattr(provider, "api_key", ""))
    if not endpoint and not api_key:
        return f"memory:{id(provider)}:{model}"
    credential = sha256(f"{name}:{api_key}".encode()).hexdigest() if api_key else name
    return f"{credential}:{endpoint}:{model}"


def provider_rate_limit_identity(provider: Any) -> str:
    """Share pacing across models that use the same endpoint and credential."""
    name = str(getattr(provider, "name", "ollama")).lower()
    endpoint = str(getattr(provider, "base_url", "")).rstrip("/").lower()
    api_key = str(getattr(provider, "api_key", ""))
    if not endpoint and not api_key:
        return f"memory:{id(provider)}"
    credential = sha256(f"{name}:{api_key}".encode()).hexdigest() if api_key else name
    return f"{credential}:{endpoint}"


@dataclass(slots=True)
class _Circuit:
    failures: int = 0
    open_until: float = 0


class ReliabilityGuards:
    """Single-process guards. The Mac mini worker is intentionally single-process today."""

    _lock = Lock()
    _last_started: dict[str, float] = {}
    _semaphores: dict[tuple[str, int], Semaphore] = {}
    _circuits: dict[str, _Circuit] = {}

    @classmethod
    def acquire(
        cls,
        key: str,
        policy: ModelReliabilityPolicy,
        *,
        limiter_key: str | None = None,
    ) -> tuple[Semaphore | None, float, str]:
        if policy.mode == "DIRECT":
            return None, 0.0, "CLOSED"
        limiter_key = limiter_key or key
        semaphore: Semaphore | None = None
        if policy.max_concurrency:
            with cls._lock:
                semaphore = cls._semaphores.setdefault(
                    (limiter_key, policy.max_concurrency), Semaphore(policy.max_concurrency)
                )
            semaphore.acquire()
        with cls._lock:
            circuit = cls._circuits.setdefault(key, _Circuit())
            now = monotonic()
            if policy.circuit_breaker_enabled and circuit.open_until > now:
                if semaphore:
                    semaphore.release()
                raise AIProviderError("AI_PROVIDER_CIRCUIT_OPEN", "模型调用仍在冷却", switch_model=True)
            state = "HALF_OPEN" if policy.circuit_breaker_enabled and circuit.open_until else "CLOSED"
            interval = max(
                policy.request_interval_seconds, 60 / policy.rate_limit_rpm if policy.rate_limit_rpm else 0
            )
            wait = max(0.0, cls._last_started.get(limiter_key, 0) + interval - now)
            cls._last_started[limiter_key] = now + wait
        return semaphore, wait, state

    @classmethod
    def release(cls, semaphore: Semaphore | None) -> None:
        if semaphore:
            semaphore.release()

    @classmethod
    def success(cls, key: str) -> None:
        with cls._lock:
            cls._circuits[key] = _Circuit()

    @classmethod
    def failure(cls, key: str, policy: ModelReliabilityPolicy, error: AIProviderError) -> str:
        if error.code == "AI_PROVIDER_BAD_REQUEST" or error.code.startswith("AI_PROVIDER_INTERFACE_"):
            return "CLOSED"
        if not policy.circuit_breaker_enabled or error.code in {
            "AI_PROVIDER_INVALID_JSON",
            "AI_PROVIDER_SCHEMA_INVALID",
            "AI_PROVIDER_OUTPUT_TRUNCATED",
            "AI_PROVIDER_EMPTY_RESPONSE",
        }:
            return "CLOSED"
        with cls._lock:
            circuit = cls._circuits.setdefault(key, _Circuit())
            circuit.failures += 1
            if error.open_circuit or circuit.failures >= policy.circuit_breaker_threshold:
                circuit.open_until = monotonic() + policy.circuit_breaker_cooldown_seconds
                return "OPEN"
            return "CLOSED"
