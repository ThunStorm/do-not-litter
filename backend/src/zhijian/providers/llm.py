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
    def generate_text(self, messages: list[dict[str, str]], *, model: str) -> LLMResult: ...

    def generate_json(self, messages: list[dict[str, str]], *, model: str) -> LLMResult: ...

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult: ...


class OllamaProvider:
    def __init__(self, base_url: str, timeout: float = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _generate(self, messages: list[dict[str, str]], *, model: str, json_mode: bool) -> LLMResult:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                **({"format": "json"} if json_mode else {}),
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

    def generate_text(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self._generate(messages, model=model, json_mode=False)

    def generate_json(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self._generate(messages, model=model, json_mode=True)

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self.generate_json(messages, model=model)


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key: str, timeout: float = 120) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _generate(self, messages: list[dict[str, str]], *, model: str, json_mode: bool) -> LLMResult:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
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

    def generate_text(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self._generate(messages, model=model, json_mode=False)

    def generate_json(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self._generate(messages, model=model, json_mode=True)

    def generate(self, messages: list[dict[str, str]], *, model: str) -> LLMResult:
        return self.generate_json(messages, model=model)
