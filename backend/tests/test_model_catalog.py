from types import SimpleNamespace

import httpx
import pytest

from zhijian.ai.model_catalog import catalog_origin, read_model_catalog
from zhijian.ai.reliability import AIProviderError
from zhijian.db.models import Setting


def transport(monkeypatch, handle):
    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs)
    )


@pytest.mark.parametrize(
    "provider,base,path",
    [
        ("DeepSeek", "https://api.example.test", "/models"),
        ("OpenRouter", "https://api.example.test/api/v1", "/api/v1/models"),
        ("Ollama", "http://127.0.0.1:11434", "/api/tags"),
    ],
)
def test_catalog_reads_metadata_only_and_returns_exact_ids(monkeypatch, provider, base, path):
    requests = []

    def handle(request):
        requests.append(request)
        assert request.method == "GET" and request.url.path == path
        assert request.headers["Authorization"] == "Bearer fixture-key"
        field = "models" if provider == "Ollama" else "data"
        entry = {"model": "qwen3.5:9b"} if provider == "Ollama" else {"id": "codebuddy/hy3"}
        entry["api_key"] = "upstream-secret"
        return httpx.Response(200, json={field: [entry]})

    transport(monkeypatch, handle)
    result = read_model_catalog(provider, base, "fixture-key", "DIRECT")
    assert len(requests) == 1
    assert result["models"] == [{"id": "qwen3.5:9b" if provider == "Ollama" else "codebuddy/hy3"}]
    assert "secret" not in str(result) and "fixture-key" not in str(result)


@pytest.mark.parametrize("mismatch", [False, True])
def test_mux_catalogs_must_match(monkeypatch, mismatch):
    paths = []

    def handle(request):
        paths.append(request.url.path)
        model = "other/model" if mismatch and len(paths) == 2 else "codebuddy/hy3"
        return httpx.Response(200, json={"data": [{"id": model}]})

    transport(monkeypatch, handle)
    if mismatch:
        with pytest.raises(AIProviderError, match="实际模型目录与能力目录不一致"):
            read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")
    else:
        assert read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")[
            "models"
        ] == [{"id": "codebuddy/hy3"}]
    assert paths == ["/v1/models", "/api/chat/models"]


@pytest.mark.parametrize("owner,alias", [("localmux", "cheap"), ("provider", "cheap"), ("localmux", "other")])
def test_mux_picker_accepts_only_known_mux_owned_routes_and_returns_actual_models(monkeypatch, owner, alias):
    def handle(request):
        entries = [{"id": "codebuddy/hy3"}]
        if request.url.path == "/v1/models":
            entries.append({"id": alias, "owned_by": owner})
        return httpx.Response(200, json={"data": entries})

    transport(monkeypatch, handle)
    if owner == "localmux" and alias == "cheap":
        result = read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")
        assert result["models"] == [{"id": "codebuddy/hy3"}]
    else:
        with pytest.raises(AIProviderError, match="实际模型目录与能力目录不一致"):
            read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")


@pytest.mark.parametrize("late", [False, True])
def test_mux_cold_catalog_read_uses_remaining_budget_without_retry(monkeypatch, late):
    import zhijian.ai.model_catalog as catalog

    clock = [0]
    timeouts = []
    monkeypatch.setattr(catalog, "monotonic", lambda: clock[0])

    def handle(request):
        timeouts.append(request.extensions["timeout"])
        clock[0] += 19 if late and len(timeouts) == 2 else 12
        return httpx.Response(200, json={"data": [{"id": "codebuddy/hy3"}]})

    transport(monkeypatch, handle)
    if late:
        with pytest.raises(AIProviderError, match="读取超时"):
            read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")
    else:
        assert read_model_catalog("LocalAiMux", "http://127.0.0.1:8317/v1", "fixture-key", "LOCAL_ROUTER")[
            "models"
        ] == [{"id": "codebuddy/hy3"}]
    assert len(timeouts) == 2
    assert [timeout["read"] for timeout in timeouts] == [20, 18]
    assert [timeout["connect"] for timeout in timeouts] == [5, 5]


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/a",
        "http://user:key@example.test",
        "http://example.test?key=x",
        "http://example.test:0",
        "http://example.test\n",
    ],
)
def test_catalog_rejects_credential_or_invalid_urls(url):
    with pytest.raises(AIProviderError):
        catalog_origin(url)


@pytest.mark.parametrize(
    "failure", ["redirect", "timeout", "duplicate", "oversize", "bad_json", "too_many", "credential_echo"]
)
def test_catalog_failure_is_bounded_and_redacted(monkeypatch, failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://other.test/secret"})
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-key-in-exception", request=request)
        if failure == "oversize":
            return httpx.Response(200, content=b"x" * 1_000_001)
        if failure == "bad_json":
            return httpx.Response(200, content=b"not-json-secret")
        if failure == "too_many":
            return httpx.Response(200, json={"data": [{"id": f"model-{index}"} for index in range(1001)]})
        if failure == "credential_echo":
            return httpx.Response(200, json={"data": [{"id": "secret-key"}]})
        return httpx.Response(200, json={"data": [{"id": "duplicate"}, {"id": "duplicate"}]})

    transport(monkeypatch, handle)
    with pytest.raises(AIProviderError) as error:
        read_model_catalog("Custom", "https://example.test/v1", "secret-key", "DIRECT")
    assert "secret" not in str(error.value) and len(calls) == 1


def test_saved_catalog_uses_keychain_without_saving_or_switching(client, app_and_session, monkeypatch):
    import zhijian.ai.model_catalog as catalog
    from zhijian.api.router import get_secret_store

    app, factory = app_and_session
    with factory() as db:
        db.add(
            Setting(
                key="model-profile:catalog-fixture",
                value_json={
                    "provider": "Custom",
                    "base_url": "https://example.test/v1",
                    "model": "old/model",
                },
            )
        )
        db.commit()
    keys = []
    app.dependency_overrides[get_secret_store] = lambda: SimpleNamespace(
        get=lambda key: keys.append(key) or "saved-secret"
    )
    calls = []

    def read(provider, base, key, connection):
        calls.append(key)
        return {"models": [{"id": "new/model"}], "sampled_at": "fixture"}

    monkeypatch.setattr(catalog, "read_model_catalog", read)
    payload = {"profile_id": "catalog-fixture", "provider": "Custom", "base_url": "https://example.test/v1"}
    response = client.post("/api/settings/model-catalog", json=payload)
    assert response.status_code == 200 and response.json()["models"] == [{"id": "new/model"}]
    assert calls == ["saved-secret"] and keys == ["model-profile:catalog-fixture:api-key"]
    with factory() as db:
        assert db.get(Setting, "model-profile:catalog-fixture").value_json["model"] == "old/model"
    response = client.post(
        "/api/settings/model-catalog", json={**payload, "base_url": "https://other.test/v1"}
    )
    assert response.status_code == 422 and calls == ["saved-secret"]
    response = client.post(
        "/api/settings/model-catalog",
        json={**payload, "base_url": "https://other.test/v1", "api_key": "new-secret"},
    )
    assert response.status_code == 200 and calls[-1] == "new-secret"
    assert "secret" not in response.text
    assert (
        client.post("/api/settings/model-catalog", json={**payload, "profile_id": "missing"}).status_code
        == 404
    )
