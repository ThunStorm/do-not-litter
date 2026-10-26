from pathlib import Path

from zhijian.core.config import Settings, get_settings
from zhijian.core.storage import adopt, read_json


def configured(app_and_session, tmp_path):
    app, factory = app_and_session
    with factory() as db:
        root = Path(db.get_bind().url.database).resolve().parent
    control = tmp_path / "control/storage.json"
    adopt(root, control)
    settings = Settings(_env_file=None, data_dir=root, storage_config=control)
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def test_storage_plan_is_background_only_and_never_switches_db(
    client, app_and_session, tmp_path, monkeypatch
):
    settings = configured(app_and_session, tmp_path)
    calls = []
    monkeypatch.setattr(
        "zhijian.api.storage.launch_plan",
        lambda *a, **kw: calls.append((a, kw)) or type("Process", (), {"pid": 12345})(),
    )
    target = tmp_path.parent / (tmp_path.name + "-new-data")
    response = client.post("/api/settings/storage/plan", json={"path": str(target)})
    assert response.status_code == 200 and response.json()["stage"] == "SCANNING"
    assert len(calls) == 1
    assert calls[0][0][1] == str(target)
    assert read_json(settings.storage_config)["root"] == str(settings.data_dir)
    assert not target.exists()
    assert client.get("/api/settings/storage").json()["plan"]["stage"] == "SCANNING"


def test_policy_requires_preview_and_preserves_audit_setting(client, app_and_session, tmp_path):
    settings = configured(app_and_session, tmp_path)
    before = client.get("/api/settings/general").json()
    status = client.get("/api/settings/storage").json()
    policy = {**status["policy"], "retention_days": 20}
    assert (
        client.post(
            "/api/settings/storage/logs/apply", json={"policy": policy, "token": "0" * 64}
        ).status_code
        == 409
    )
    impact = client.post("/api/settings/storage/logs/preview", json=policy).json()
    assert impact["delete_count"] == 0
    response = client.post(
        "/api/settings/storage/logs/apply", json={"policy": policy, "token": impact["token"]}
    )
    assert response.status_code == 200
    assert read_json(settings.storage_config.with_name("log-policy.json"))["version"] == 2
    assert client.get("/api/settings/general").json() == before
    invalid = {**policy, "retention_days": 1, "compression_delay_hours": 48}
    assert client.post("/api/settings/storage/logs/preview", json=invalid).status_code == 422
