"""Bounded, inference-free model directory reads for the settings picker."""

import json
from time import monotonic
from urllib.parse import urlsplit, urlunsplit

import httpx

from zhijian.ai.interface_contract import validate_mux_catalogs
from zhijian.ai.reliability import AIProviderError
from zhijian.core.time import utc_now


def catalog_origin(base_url: str) -> tuple[str, str, int]:
    try:
        url = urlsplit(base_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or any((url.username, url.password, url.query, url.fragment))
            or any(ord(char) < 32 for char in base_url)
            or (url.port is not None and not 1 <= url.port <= 65535)
        ):
            raise ValueError
        return url.scheme, url.hostname, url.port or (443 if url.scheme == "https" else 80)
    except ValueError as exc:
        raise AIProviderError(
            "MODEL_CATALOG_INVALID_URL", "模型目录地址应为不含凭据或查询参数的 HTTP 地址"
        ) from exc


def read_model_catalog(provider: str, base_url: str, api_key: str | None, connection_type: str) -> dict:
    catalog_origin(base_url)
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    ollama = provider.strip().lower() == "ollama" and connection_type == "DIRECT"
    prefix = parsed.path.removesuffix("/v1").rstrip("/")
    url = (
        urlunsplit((parsed.scheme, parsed.netloc, prefix + "/api/tags", "", ""))
        if ollama
        else base_url + "/models"
    )
    deadline = monotonic() + 30

    def read(client: httpx.Client, target: str, field: str) -> list[dict]:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise httpx.ReadTimeout("catalog deadline exceeded")
        with client.stream(
            "GET", target, timeout=httpx.Timeout(min(20, remaining), connect=min(5, remaining))
        ) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 1_000_000:
                    raise ValueError("response limit")
                if monotonic() >= deadline:
                    raise httpx.ReadTimeout("catalog deadline exceeded")
        envelope = json.loads(body)
        entries = envelope.get(field) if isinstance(envelope, dict) else None
        if not isinstance(entries, list) or len(entries) > 1000:
            raise ValueError("invalid catalog")
        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("invalid model")
            model_id = entry.get("model", entry.get("name")) if ollama else entry.get("id")
            if (
                not isinstance(model_id, str)
                or not 0 < len(model_id) <= 200
                or model_id != model_id.strip()
                or any(ord(char) < 32 for char in model_id)
                or (api_key and api_key in model_id)
            ):
                raise ValueError("invalid model id")
            result.append({"id": model_id})
            if connection_type == "LOCAL_ROUTER":
                result[-1]["owned_by"] = entry.get("owned_by")
        if len({entry["id"] for entry in result}) != len(result):
            raise ValueError("duplicate model id")
        return result

    try:
        with httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=httpx.Timeout(20, connect=5),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            models = read(client, url, "models" if ollama else "data")
            if connection_type == "LOCAL_ROUTER":
                capabilities_url = urlunsplit(
                    (parsed.scheme, parsed.netloc, prefix + "/api/chat/models", "", "")
                )
                capabilities = read(client, capabilities_url, "data")
                actual_ids = validate_mux_catalogs(models, capabilities)
                models = [{"id": entry["id"]} for entry in models if entry["id"] in actual_ids]
    except httpx.HTTPStatusError as exc:
        raise AIProviderError(
            "MODEL_CATALOG_UNAVAILABLE",
            f"模型目录返回 HTTP {exc.response.status_code}，可保留原模型或手动填写",
        ) from exc
    except httpx.TimeoutException as exc:
        raise AIProviderError(
            "MODEL_CATALOG_UNAVAILABLE", "模型目录读取超时，请稍后刷新；原模型已保留，也可手动填写"
        ) from exc
    except (httpx.HTTPError, httpx.InvalidURL, ValueError, UnicodeError) as exc:
        message = (
            "本机路由的实际模型目录与能力目录不一致，请稍后刷新；原模型已保留"
            if isinstance(exc, ValueError) and str(exc) == "catalog mismatch"
            else "模型目录格式或响应不可用，可保留原模型或手动填写"
        )
        raise AIProviderError("MODEL_CATALOG_UNAVAILABLE", message) from exc
    return {"models": models, "sampled_at": utc_now().isoformat()}
