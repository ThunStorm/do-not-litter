"""Non-secret, frozen interface metadata for explicitly selected local routers."""

import hashlib
import json
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field, field_validator

from zhijian.ai.reliability import AIProviderError

Support = Literal["SUPPORTED", "UNSUPPORTED", "UNKNOWN"]
NORMALIZATION_VERSION = "zhijian-stateless-v1"


class InterfaceParameter(BaseModel):
    support: Support = "UNKNOWN"
    minimum: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    maximum: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class InterfaceCapabilities(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    base_url: str = Field(max_length=1000)
    sampled_at: str = Field(max_length=80)
    source: Literal["LocalAiMux 接口目录"] = "LocalAiMux 接口目录"
    version: Literal["zhijian-stateless-v1"] = NORMALIZATION_VERSION
    gateway_schema_version: int | None = Field(default=None, ge=1, le=10000)
    system: Support = "UNKNOWN"
    history: Support = "UNKNOWN"
    multiple_messages: Support = "UNKNOWN"
    json_object: Support = "UNKNOWN"
    thinking: Support = "UNKNOWN"
    usage: Support = "UNKNOWN"
    finish_reason: Support = "UNKNOWN"
    temperature: InterfaceParameter = Field(default_factory=InterfaceParameter)
    output: InterfaceParameter = Field(default_factory=InterfaceParameter)
    output_field: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    limiting_layer: Literal["gateway", "adapter", "public_interface", "model", "unknown"] = "unknown"

    @field_validator("base_url")
    @classmethod
    def credential_free_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("接口端口无效") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or any((parsed.username, parsed.password, parsed.query, parsed.fragment))
        ):
            raise ValueError("接口能力地址不能含凭据、查询参数或片段")
        return value.rstrip("/")

    def fingerprint(self) -> str:
        value = self.model_dump(exclude={"sampled_at"})
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _support(value: Any) -> Support:
    if isinstance(value, dict):
        value = value.get("effective_support", value.get("support"))
    return value if value in ("SUPPORTED", "UNSUPPORTED", "UNKNOWN") else "UNKNOWN"


def _parameter(value: Any) -> InterfaceParameter:
    value = value if isinstance(value, dict) else {}
    return InterfaceParameter(support=_support(value), minimum=value.get("min"), maximum=value.get("max"))


def read_interface_capabilities(base_url: str, model: str, api_key: str) -> InterfaceCapabilities:
    """Read only metadata, with bounded responses and no redirect of the credential."""
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or any((parsed.username, parsed.password, parsed.query, parsed.fragment))
    ):
        raise AIProviderError("AI_PROVIDER_INTERFACE_INVALID", "接口地址应为不含凭据或查询参数的 HTTP 地址")
    prefix = parsed.path.removesuffix("/v1").rstrip("/")
    metadata_url = urlunsplit((parsed.scheme, parsed.netloc, f"{prefix}/api/chat/models", "", ""))
    deadline = monotonic() + 30

    def read(client: httpx.Client, url: str) -> tuple[list[dict], int | None]:
        if monotonic() > deadline:
            raise ValueError("metadata deadline exceeded")
        with client.stream("GET", url) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                if monotonic() > deadline:
                    raise ValueError("metadata deadline exceeded")
                body.extend(chunk)
                if len(body) > 1_000_000:
                    raise ValueError("metadata too large")
        envelope = json.loads(body)
        if not isinstance(envelope, dict):
            raise ValueError("invalid envelope")
        data = envelope.get("data")
        if not isinstance(data, list) or len(data) > 1000:
            raise ValueError("invalid catalog")
        version = envelope.get("schema_version")
        return data, version if type(version) is int else None

    try:
        with httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            interfaces, schema_version = read(client, metadata_url)
            models, _ = read(client, f"{base_url}/models")
        ids = [item["id"] for item in models]
        interface_ids = [item["id"] for item in interfaces]
        if (
            len(set(ids)) != len(ids)
            or len(set(interface_ids)) != len(interface_ids)
            or set(ids) != set(interface_ids)
        ):
            raise ValueError("catalog mismatch")
        entry = next((item for item in interfaces if item["id"] == model), None)
        if entry is None:
            raise AIProviderError("AI_PROVIDER_NOT_FOUND", "当前凭据的接口目录中没有该模型")
        chat = entry.get("chat")
        if not isinstance(chat, dict):
            raise ValueError("missing interface capabilities")
        details = chat.get("details") or {}

        def capability(name: str):
            return chat.get(name, details.get(name))

        output_field = (
            "max_completion_tokens"
            if _support(chat.get("max_completion_tokens")) == "SUPPORTED"
            else "max_tokens"
        )
        layer = chat.get("limiting_layer", "unknown")
        return InterfaceCapabilities(
            model=model,
            base_url=base_url,
            sampled_at=datetime.now(UTC).isoformat(),
            gateway_schema_version=schema_version,
            system=_support(chat.get("system")),
            history=_support(chat.get("history")),
            multiple_messages=_support(chat.get("multiple_messages")),
            json_object=_support(capability("json_object")),
            thinking=_support(capability("thinking")),
            usage=_support(capability("usage")),
            finish_reason=_support(capability("finish_reason")),
            temperature=_parameter(chat.get("temperature")),
            output=_parameter(chat.get(output_field)),
            output_field=output_field,
            limiting_layer=layer
            if layer in {"gateway", "adapter", "public_interface", "model"}
            else "unknown",
        )
    except AIProviderError:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise AIProviderError("AI_PROVIDER_AUTH_ERROR", "接口目录鉴权失败，请核对本机路由的凭据") from exc
        raise AIProviderError(
            "AI_PROVIDER_INTERFACE_UNAVAILABLE", "接口能力目录不可用，请确认网关版本和地址"
        ) from exc
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise AIProviderError(
            "AI_PROVIDER_INTERFACE_UNAVAILABLE", "无法核对接口能力，原配置保持不变"
        ) from exc


def normalize_messages(messages: list[dict]) -> list[dict]:
    """Merge leading instructions only; never flatten history or media into text."""
    prefix = 0
    while prefix < len(messages) and messages[prefix].get("role") == "system":
        prefix += 1
    if prefix <= 1:
        return list(messages)
    if not all(isinstance(message.get("content"), str) for message in messages[:prefix]):
        raise AIProviderError("AI_PROVIDER_INTERFACE_MESSAGES", "接口不支持非文本指令")
    return [
        {"role": "system", "content": "\n\n".join(m["content"] for m in messages[:prefix])},
        *messages[prefix:],
    ]


def router_payload(
    capabilities: InterfaceCapabilities | None,
    base_url: str,
    model: str,
    messages: list[dict],
    *,
    json_mode: bool,
    temperature: float | None,
    max_output_tokens: int | None,
) -> tuple[dict, dict]:
    if capabilities is None or capabilities.model != model or capabilities.base_url != base_url.rstrip("/"):
        raise AIProviderError(
            "AI_PROVIDER_INTERFACE_NOT_CHECKED", "请读取并保存当前模型的接口能力后再运行任务"
        )
    normalized = normalize_messages(messages)
    roles = [message.get("role") for message in normalized]
    if any(not isinstance(message.get("content"), str) for message in normalized):
        raise AIProviderError("AI_PROVIDER_INTERFACE_MESSAGES", "当前接口适配只支持文本，图像需独立验收")
    if "system" in roles and capabilities.system != "SUPPORTED":
        raise AIProviderError(
            "AI_PROVIDER_INTERFACE_MESSAGES", "该接口尚未提供系统指令，不能保留本次任务规则；需上游桥接支持"
        )
    if "user" not in roles or any(role not in {"system", "user", "assistant"} for role in roles):
        raise AIProviderError("AI_PROVIDER_INTERFACE_MESSAGES", "该接口不支持当前角色组合")
    if roles not in (["user"], ["system", "user"]) and (
        capabilities.history != "SUPPORTED" or capabilities.multiple_messages != "SUPPORTED"
    ):
        raise AIProviderError(
            "AI_PROVIDER_INTERFACE_MESSAGES", "该接口尚未支持本次消息组合；不会丢弃上下文后调用"
        )
    payload: dict = {"model": model, "messages": normalized}
    omitted = []
    for name, value, parameter in (
        ("temperature", temperature, capabilities.temperature),
        (capabilities.output_field, max_output_tokens, capabilities.output),
    ):
        if value is None:
            continue
        if parameter.support != "SUPPORTED" or parameter.minimum is None or parameter.maximum is None:
            omitted.append(name)
        elif not parameter.minimum <= value <= parameter.maximum:
            raise AIProviderError(
                "AI_PROVIDER_INTERFACE_PARAMETER", "生成参数超出该接口已声明范围，请调整设置或采用模型默认值"
            )
        else:
            payload[name] = value
    if json_mode:
        if capabilities.json_object == "SUPPORTED":
            payload["response_format"] = {"type": "json_object"}
        else:
            omitted.append("response_format")
    return payload, {
        "interface_fingerprint": capabilities.fingerprint(),
        "normalization_version": NORMALIZATION_VERSION,
        "effective_input_hash": hashlib.sha256(
            json.dumps(normalized, ensure_ascii=False).encode()
        ).hexdigest(),
        "effective_parameters": {k: v for k, v in payload.items() if k not in {"model", "messages"}},
        "omitted_parameters": omitted,
    }
