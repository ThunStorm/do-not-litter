from types import SimpleNamespace

import pytest

from zhijian.ai.model_credentials import mux_credential_account, resolve_model_key, save_model_key
from zhijian.api.router import get_secret_store
from zhijian.db.models import Setting

BASE = {"provider": "LocalAiMux", "base_url": "http://127.0.0.1:8317/v1", "connection_type": "DIRECT"}


def setup_keys(app_and_session):
    app, factory = app_and_session
    secrets = {"model-profile:old:api-key": "legacy-secret"}
    store = SimpleNamespace(get=secrets.get, set=lambda key, value: secrets.update({key: value}))
    app.dependency_overrides[get_secret_store] = lambda: store
    with factory() as db:
        db.add(Setting(key="model-profile:old", value_json={**BASE, "model": "old"}, is_secret_ref=True))
        db.commit()
    return factory, store, secrets


def test_mux_shared_legacy_resolution_and_endpoint_isolation(app_and_session):
    factory, store, secrets = setup_keys(app_and_session)
    with factory() as db:
        assert resolve_model_key(db, store, BASE) == "legacy-secret"
        for change in [
            {"base_url": "http://other.test/v1"},
            {"base_url": "http://127.0.0.1:8318/v1"},
            {"base_url": "http://127.0.0.1:8317/other"},
            {"provider": "Custom"},
        ]:
            assert resolve_model_key(db, store, {**BASE, **change}) is None
        assert resolve_model_key(db, store, {**BASE, "connection_type": "LOCAL_ROUTER"}) == "legacy-secret"
        db.add(Setting(key="model-profile:second", value_json=BASE))
        db.commit()
        secrets["model-profile:second:api-key"] = "different-secret"
        with pytest.raises(ValueError, match="不一致"):
            resolve_model_key(db, store, BASE)
        save_model_key(store, BASE, "new", "unified-secret")
        assert resolve_model_key(db, store, BASE, profile_id="old") == "unified-secret"
        assert resolve_model_key(db, store, BASE, "explicit-secret") == "explicit-secret"
        assert secrets[mux_credential_account(BASE)] == "unified-secret"


def test_mux_status_catalog_and_save_reuse_without_secret_return(client, app_and_session, monkeypatch):
    factory, store, secrets = setup_keys(app_and_session)
    response = client.post("/api/settings/model-credentials/status", json=BASE)
    assert response.json() == {"api_key_saved": True, "conflict": False}
    assert "secret" not in response.text
    calls = []

    def read(provider, base, key, connection):
        calls.append(key)
        return {"models": [{"id": "qoder/Kimi-K3"}], "sampled_at": "fixture"}

    monkeypatch.setattr("zhijian.ai.model_catalog.read_model_catalog", read)
    assert client.post("/api/settings/model-catalog", json=BASE).status_code == 200
    assert calls == ["legacy-secret"]
    payload = {**BASE, "name": "New Mux", "model": "qoder/Kimi-K3", "location": "REMOTE"}
    response = client.post("/api/settings/model-profiles", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["api_key_saved"] is True
    assert "legacy-secret" not in response.text
    assert secrets[mux_credential_account(BASE)] == "legacy-secret"
    assert (
        client.post("/api/settings/model-profiles", json={**payload, "api_key": "rotated-secret"}).status_code
        == 200
    )
    assert client.post("/api/settings/model-catalog", json={**BASE, "profile_id": "old"}).status_code == 200
    assert calls[-1] == "rotated-secret"
    with factory() as db:
        assert "secret" not in str(db.get(Setting, "model-profile:old").value_json)


def test_mux_missing_key_is_local_validation_not_upstream_401(client, app_and_session, monkeypatch):
    setup_keys(app_and_session)
    other = {**BASE, "base_url": "http://127.0.0.1:8318/v1"}
    monkeypatch.setattr(
        "zhijian.ai.model_catalog.read_model_catalog", lambda *args: pytest.fail("network read")
    )
    assert client.post("/api/settings/model-credentials/status", json=other).json()["api_key_saved"] is False
    response = client.post("/api/settings/model-catalog", json=other)
    assert response.status_code == 422 and "API Key" in response.text


def test_runtime_uses_unified_key_without_rewriting_profile(tmp_path):
    from zhijian.core.config import Settings
    from zhijian.core.secret_store import FileSecretStore
    from zhijian.services.video_support import _provider_from_config

    settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
    store = FileSecretStore(tmp_path / "secrets")
    store.set("model-profile:old:api-key", "old-secret")
    store.set(mux_credential_account(BASE), "unified-secret")
    provider, _, _ = _provider_from_config({**BASE, "model": "test-model"}, settings, "old")
    assert provider.api_key == "unified-secret"
