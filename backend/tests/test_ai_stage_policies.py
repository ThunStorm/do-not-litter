from types import SimpleNamespace

from sqlalchemy import select

from zhijian.db.models import ExternalCallAudit, Job, Setting
from zhijian.providers.llm import LLMResult
from zhijian.services.video_support import provider_for_role


def _profile(name: str, location: str, model: str) -> dict[str, object]:
    return {
        "name": name,
        "provider": "Ollama" if location == "LOCAL" else "DeepSeek",
        "base_url": "http://127.0.0.1:11434" if location == "LOCAL" else "https://api.example.test/v1",
        "model": model,
        "timeout_seconds": 120,
        "location": location,
        "modalities": ["text"],
        "max_output_tokens": 4096,
    }


def _policy(local_id: str, remote_id: str, **values: object) -> dict[str, object]:
    return {
        "stage": "TRANSCRIPT_CORRECTION",
        "capability": "TRANSCRIPT_CORRECTION",
        "execution_mode": "LOCAL_FIRST",
        "local_profile_id": local_id,
        "remote_profile_id": remote_id,
        "temperature": 0.1,
        **values,
    }


def test_stage_policy_api_validates_models_and_job_override(client, app_and_session) -> None:
    _, factory = app_and_session
    local = client.post("/api/settings/model-profiles", json=_profile("本机", "LOCAL", "qwen-local"))
    remote = client.post("/api/settings/model-profiles", json=_profile("远程", "REMOTE", "remote-strong"))
    assert local.status_code == 200 and remote.status_code == 200
    local_id, remote_id = local.json()["id"], remote.json()["id"]

    saved = client.put(
        "/api/ai/stage-policies/TRANSCRIPT_CORRECTION",
        json=_policy(local_id, remote_id),
    )
    assert saved.status_code == 200
    assert saved.json()["execution_mode"] == "LOCAL_FIRST"
    assert saved.json()["sources"]["temperature"] == "saved_stage_policy"
    assert client.get("/api/ai/stages").json()[0]["parameter_spec"]

    rejected = client.put(
        "/api/ai/stage-policies/TRANSCRIPT_CORRECTION",
        json=_policy(local_id, remote_id, thinking=True),
    )
    assert rejected.status_code == 422
    captured = client.post(
        "/api/capture",
        json={
            "text": "阶段覆盖测试",
            "ai_overrides": {
                "TRANSCRIPT_CORRECTION": {
                    "execution_mode": "LOCAL_ONLY",
                    "local_profile_id": local_id,
                }
            },
        },
    )
    assert captured.status_code == 200
    with factory() as db:
        job = db.get(Job, captured.json()["job_id"])
        assert job
        assert job.payload_json["ai_overrides"]["TRANSCRIPT_CORRECTION"]["execution_mode"] == "LOCAL_ONLY"


def test_stage_policy_changes_actual_provider_route(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    with factory() as db:
        db.add(Setting(key="model-profile:local", value_json=_profile("本机", "LOCAL", "qwen-local")))
        db.add(Setting(key="model-profile:remote", value_json=_profile("远程", "REMOTE", "remote-strong")))
        db.add(
            Setting(
                key="ai-stage-policy:TRANSCRIPT_CORRECTION",
                value_json=_policy("local", "remote", execution_mode="REMOTE_ONLY", max_output_tokens=1200),
            )
        )
        db.commit()

        def fake_provider(config, *_args):
            provider = SimpleNamespace(
                generate_json=lambda *_args, **_kwargs: LLMResult("{}", "fake", config["model"], {})
            )
            return provider, "fake", config["model"]

        monkeypatch.setattr("zhijian.services.video_support._provider_from_config", fake_provider)
        provider, _, model = provider_for_role(
            db,
            SimpleNamespace(secret_store="file", data_dir="/tmp"),
            "transcript_correction",
        )
        assert model == "remote-strong"
        assert provider.request_options and provider.request_options.max_output_tokens == 1200


def test_model_probe_persists_only_capability_results(client, app_and_session, monkeypatch) -> None:
    _, factory = app_and_session
    created = client.post("/api/settings/model-profiles", json=_profile("探测", "LOCAL", "probe-model"))
    profile_id = created.json()["id"]

    class Provider:
        def generate_text(self, *_args, **_kwargs):
            return LLMResult("PONG", "ollama", "probe-model", {})

        def generate_json(self, *_args, **_kwargs):
            return LLMResult('{"id":"evidence_probe_01","ok":true}', "ollama", "probe-model", {})

    monkeypatch.setattr("zhijian.api.router._model_profile_provider", lambda *_args: Provider())
    response = client.post(f"/api/settings/model-profiles/{profile_id}/probe")
    assert response.status_code == 200
    assert "TRANSCRIPT_CORRECTION" in response.json()["capabilities"]
    with factory() as db:
        stored = db.scalar(select(Setting).where(Setting.key == f"model-profile:{profile_id}"))
        assert stored and "api_key" not in str(stored.value_json)


def test_job_ai_usage_groups_stage_model_and_location(client, app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="COMPLETED", payload_json={})
        db.add(job)
        db.flush()
        db.add_all(
            [
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="ollama",
                    operation="transcript_correction",
                    status="COMPLETED",
                    duration_ms=12,
                    request_meta_json={"stage": "CORRECT_TRANSCRIPT", "model": "qwen", "location": "LOCAL"},
                    response_meta_json={"prompt_tokens": 10, "completion_tokens": 2},
                ),
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="remote",
                    operation="video_note_summary",
                    status="COMPLETED",
                    duration_ms=20,
                    request_meta_json={"stage": "GENERATE_AI_NOTE", "model": "strong", "location": "REMOTE"},
                    response_meta_json={"prompt_tokens": 20, "completion_tokens": 4, "cached_tokens": 5},
                ),
            ]
        )
        db.commit()
        job_id = job.id
    payload = client.get(f"/api/jobs/{job_id}/ai-usage").json()
    assert payload["total"]["calls"] == 2
    assert payload["local"]["input_tokens"] == 10
    assert payload["remote"]["output_tokens"] == 4
    assert payload["by_stage"]["GENERATE_AI_NOTE"]["cached_tokens"] == 5
