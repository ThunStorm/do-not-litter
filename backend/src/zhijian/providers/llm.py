from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(slots=True)
class LLMResult:
    content: str
    provider: str
    model: str
    usage: dict[str, Any]


class LLMProvider(Protocol):
    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult: ...


class OllamaProvider:
    def __init__(self, base_url: str, timeout: float = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False, "format": "json"},
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


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key: str, timeout: float = 120) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "messages": messages, "response_format": {"type": "json_object"}},
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
