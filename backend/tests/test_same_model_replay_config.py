from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from zhijian.ai.budget import AIBudgetExceeded, ensure_ai_budget
from zhijian.ai.interface_contract import InterfaceCapabilities
from zhijian.ai.job_config import (
    EXECUTION_HISTORY_KEY,
    EXECUTION_KEY,
    PENDING_EXECUTION_KEY,
    SNAPSHOT_KEY,
    build_execution_config,
    capture_ai_config,
    job_setting,
    job_stage_override,
)
from zhijian.ai.reliability import AIProviderError
from zhijian.core.config import get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Job, JobStep, JobStepArtifact, Setting, Source, SystemEvent
from zhijian.services.job_replay import VIDEO_STEP_ORDER, resume_deferred_full_replays
from zhijian.services.video_support import prompt_supplement_hash


def router_profile(**changes):
    return {
        "name": "路由测试",
        "provider": "LocalAiMux",
        "model": "codebuddy/glm-5.3",
        "base_url": "http://127.0.0.1:8317/v1",
        "connection_type": "LOCAL_ROUTER",
        "location": "REMOTE",
        "capabilities": ["TRANSCRIPT_CORRECTION"],
        "max_output_tokens": 4096,
        "timeout_seconds": 120,
        **changes,
    }


def capability(**changes):
    return InterfaceCapabilities(
        model="codebuddy/glm-5.3",
        base_url="http://127.0.0.1:8317/v1",
        sampled_at="2026-10-09",
        system="SUPPORTED",
        **changes,
    )


def seed_frozen_job(db, settings):
    profile = Setting(key="model-profile:original", value_json=router_profile())
    policy = Setting(
        key="ai-stage-policy:TRANSCRIPT_CORRECTION",
        value_json={
            "execution_mode": "REMOTE_ONLY",
            "remote_profile_id": "original",
            "temperature": 0.1,
            "max_output_tokens": 512,
            "thinking": False,
            "timeout_seconds": 120,
            "retry_count": 0,
        },
    )
    db.add_all(
        [
            profile,
            policy,
            Setting(key="app:general", value_json={"ai_retry_count": 1, "ai_max_model_attempts_per_job": 1}),
            Setting(key="transcript-processing", value_json={"batch_size": 16, "timeout_seconds": 120}),
            Setting(key="prompt:supplements", value_json={"transcript_correction": "原规则"}),
        ]
    )
    db.commit()
    job = Job(
        job_type="TRAVEL",
        status="NEEDS_USER",
        current_step="CORRECT_TRANSCRIPT",
        payload_json={
            SNAPSHOT_KEY: capture_ai_config(db, settings),
            "ai_overrides": {"TRANSCRIPT_CORRECTION": {"timeout_seconds": 77}},
        },
    )
    db.add(job)
    db.commit()
    profile.value_json = router_profile(
        interface_capabilities=capability().model_dump(),
        timeout_seconds=240,
        max_output_tokens=8192,
        temperature=0.6,
        api_key="must-not-enter-snapshot",
    )
    policy.value_json = {
        **policy.value_json,
        "timeout_seconds": 200,
        "retry_count": 2,
        "temperature": 0.9,
        "max_output_tokens": 2048,
    }
    db.get(Setting, "app:general").value_json = {"ai_retry_count": 3, "ai_max_model_attempts_per_job": 99}
    db.get(Setting, "transcript-processing").value_json = {"batch_size": 64, "timeout_seconds": 210}
    db.get(Setting, "prompt:supplements").value_json = {"transcript_correction": "新规则"}
    db.commit()
    return job, profile


def test_save_automatically_checks_and_persists_interface_without_probe(client, app_and_session, monkeypatch):
    reads = []

    def read(base_url, model, key):
        reads.append((base_url, model, key))
        return capability(json_object="SUPPORTED")

    monkeypatch.setattr("zhijian.ai.interface_contract.read_interface_capabilities", read)
    result = client.post("/api/settings/model-profiles", json=router_profile(api_key="fixture-key"))
    assert result.status_code == 200 and len(reads) == 1
    saved = result.json()
    assert saved["interface_capabilities"]["system"] == "SUPPORTED"
    assert saved["supports_json_mode"] is True and saved["probe_results"] == {}
    unchanged = client.put(
        f"/api/settings/model-profiles/{saved['id']}",
        json={**router_profile(), "name": "改名称", "timeout_seconds": 300},
    )
    assert unchanged.status_code == 200 and len(reads) == 1
    assert unchanged.json()["interface_capabilities"] == saved["interface_capabilities"]
    _, factory = app_and_session
    with factory() as db:
        assert "fixture-key" not in str(db.get(Setting, f"model-profile:{saved['id']}").value_json)


@pytest.mark.parametrize(
    "change", [{"model": "codebuddy/other"}, {"base_url": "http://127.0.0.1:9999/v1"}, {"api_key": "new-key"}]
)
def test_save_binding_or_key_change_reads_again(client, monkeypatch, change):
    calls = []

    def read(address, model, key):
        calls.append((address, model, key))
        return capability().model_copy(update={"base_url": address, "model": model})

    monkeypatch.setattr("zhijian.ai.interface_contract.read_interface_capabilities", read)
    saved = client.post("/api/settings/model-profiles", json=router_profile(api_key="old-key")).json()
    result = client.put(f"/api/settings/model-profiles/{saved['id']}", json={**router_profile(), **change})
    if "base_url" in change:
        assert result.status_code == 422 and len(calls) == 1
        result = client.put(
            f"/api/settings/model-profiles/{saved['id']}",
            json={**router_profile(), **change, "api_key": "new-address-key"},
        )
    assert result.status_code == 200 and len(calls) == 2
    assert result.json()["interface_capabilities"]["model"] == change.get("model", router_profile()["model"])


def test_failed_save_preserves_profile_and_secret(client, app_and_session, monkeypatch):
    monkeypatch.setattr("zhijian.ai.interface_contract.read_interface_capabilities", lambda *_: capability())
    saved = client.post("/api/settings/model-profiles", json=router_profile(api_key="old-key")).json()

    def fail(*_):
        raise AIProviderError("AI_PROVIDER_INTERFACE_UNAVAILABLE", "模拟目录失败")

    monkeypatch.setattr("zhijian.ai.interface_contract.read_interface_capabilities", fail)
    result = client.put(
        f"/api/settings/model-profiles/{saved['id']}", json=router_profile(model="other", api_key="new-key")
    )
    assert result.status_code == 400 and "原配置保持不变" in result.json()["detail"]
    app, factory = app_and_session
    settings = app.dependency_overrides[get_settings]()
    assert (
        build_secret_store(settings.secret_store, settings.data_dir).get(
            f"model-profile:{saved['id']}:api-key"
        )
        == "old-key"
    )
    with factory() as db:
        assert (
            db.get(Setting, f"model-profile:{saved['id']}").value_json["model"] == router_profile()["model"]
        )


def test_direct_save_does_not_read_router_catalog(client, monkeypatch):
    def fail(*_):
        pytest.fail("DIRECT must not read a Mux catalog")

    monkeypatch.setattr("zhijian.ai.interface_contract.read_interface_capabilities", fail)
    assert (
        client.post(
            "/api/settings/model-profiles",
            json=router_profile(connection_type="DIRECT", api_key="fixture-key"),
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "cap",
    [
        None,
        capability().model_copy(update={"model": "different"}).model_dump(),
        capability().model_copy(update={"system": "UNSUPPORTED"}).model_dump(),
    ],
)
def test_capture_rejects_missing_or_incompatible_interface_before_job_creation(client, app_and_session, cap):
    _, factory = app_and_session
    with factory() as db:
        db.add_all(
            [
                Setting(key="model-profile:router", value_json=router_profile(interface_capabilities=cap)),
                Setting(
                    key="ai-stage-policy:TRANSCRIPT_CORRECTION",
                    value_json={"execution_mode": "REMOTE_ONLY", "remote_profile_id": "router"},
                ),
            ]
        )
        db.commit()
        counts = [db.scalar(select(func.count()).select_from(t)) for t in (Source, Job)]
    result = client.post("/api/capture", json={"text": "https://www.bilibili.com/video/BV1fixture"})
    assert result.status_code == 422
    assert result.json()["detail"]["code"].startswith("AI_PROVIDER_INTERFACE_")
    with factory() as db:
        assert [db.scalar(select(func.count()).select_from(t)) for t in (Source, Job)] == counts


@pytest.mark.parametrize("endpoint", ["retry", "retry-full"])
def test_replay_refreshes_original_models_parameters_and_freezes_this_run(client, app_and_session, endpoint):
    app, factory = app_and_session
    with factory() as db:
        job, _ = seed_frozen_job(db, app.dependency_overrides[get_settings]())
        original = deepcopy(job.payload_json[SNAPSHOT_KEY])
        job.payload_json = {**job.payload_json, "replay_from_step": "CORRECT_TRANSCRIPT"}
        db.add(
            JobStepArtifact(job_id=job.id, step_name="ASR", replayable_until=utc_now() + timedelta(hours=1))
        )
        db.commit()
        job_id = job.id
    assert client.post(f"/api/jobs/{job_id}/{endpoint}").status_code == 200
    with factory() as db:
        job = db.get(Job, job_id)
        execution = job.payload_json[EXECUTION_KEY]
        assert job.payload_json[SNAPSHOT_KEY] == original and execution["revision"] == 1
        assert execution["limits_policy_version"] == 2
        assert "replay_from_step" not in job.payload_json
        assert (
            db.scalar(select(JobStepArtifact).where(JobStepArtifact.job_id == job.id)).status == "INVALIDATED"
        )
        current = job_setting(db, "model-profile:original", job)
        assert current["timeout_seconds"] == 240 and current["max_output_tokens"] == 8192
        assert current["temperature"] == 0.6
        assert current["interface_capabilities"]["system"] == "SUPPORTED"
        stage = job_setting(db, "ai-stage-policy:TRANSCRIPT_CORRECTION", job)
        assert stage["temperature"] == 0.9 and stage["max_output_tokens"] == 2048
        assert stage["timeout_seconds"] == 200 and stage["retry_count"] == 2
        assert job_stage_override(job, "TRANSCRIPT_CORRECTION")["timeout_seconds"] == 77
        assert job_setting(db, "transcript-processing", job) == {"batch_size": 64, "timeout_seconds": 210}
        assert job_setting(db, "app:general", job)["ai_max_model_attempts_per_job"] == 1
        assert job_setting(db, "app:general", job)["ai_retry_count"] == 3
        assert job_setting(db, "prompt:supplements", job)["transcript_correction"] == "原规则"
        assert "must-not-enter-snapshot" not in str(execution)
        row = db.get(Setting, "model-profile:original")
        row.value_json = {**row.value_json, "timeout_seconds": 500}
        db.commit()
        assert job_setting(db, "model-profile:original", job)["timeout_seconds"] == 240
        event = db.scalar(
            select(SystemEvent).where(SystemEvent.entity_id == job.id).order_by(SystemEvent.created_at.desc())
        )
        assert event.detail_json["execution_config"]["fingerprint"] == execution["fingerprint"]
        job.status = "FAILED"
        db.commit()
    assert client.post(f"/api/jobs/{job_id}/{endpoint}").status_code == 200
    with factory() as db:
        job = db.get(Job, job_id)
        assert job.payload_json[EXECUTION_KEY]["revision"] == 2
        assert job.payload_json[EXECUTION_HISTORY_KEY][0]["revision"] == 1
        assert (
            job.payload_json[EXECUTION_HISTORY_KEY][0]["settings"]["model-profile:original"][
                "timeout_seconds"
            ]
            == 240
        )
        assert job_setting(db, "model-profile:original", job)["timeout_seconds"] == 500


@pytest.mark.parametrize(
    "change",
    [
        {"model": "new"},
        {"provider": "different"},
        {"base_url": "http://127.0.0.1:9999/v1"},
        {"connection_type": "DIRECT"},
        {"location": "LOCAL"},
        {"enabled": False},
        None,
    ],
)
def test_replay_rejects_changed_identity_deleted_or_disabled_without_mutating_job(
    client, app_and_session, change
):
    app, factory = app_and_session
    with factory() as db:
        job, profile = seed_frozen_job(db, app.dependency_overrides[get_settings]())
        original = deepcopy(job.payload_json)
        if change is None:
            db.delete(profile)
        else:
            profile.value_json = {**profile.value_json, **change}
        db.commit()
        job_id = job.id
    result = client.post(f"/api/jobs/{job_id}/retry-full")
    assert result.status_code == 409 and result.json()["detail"]["code"].startswith("REPLAY_MODEL_")
    with factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "NEEDS_USER" and job.retry_count == 0 and job.payload_json == original


def test_step_replay_preserves_completed_asr_and_submission_snapshot(client, app_and_session):
    app, factory = app_and_session
    with factory() as db:
        job, _ = seed_frozen_job(db, app.dependency_overrides[get_settings]())
        original = deepcopy(job.payload_json[SNAPSHOT_KEY])
        for step_name in VIDEO_STEP_ORDER[:6]:
            db.add(
                JobStep(
                    job_id=job.id,
                    step_name=step_name,
                    status="COMPLETED",
                    output_json={"transcript_id": "existing"},
                )
            )
            db.add(
                JobStepArtifact(
                    job_id=job.id, step_name=step_name, replayable_until=utc_now() + timedelta(hours=1)
                )
            )
        db.add(
            JobStep(
                job_id=job.id,
                step_name="CORRECT_TRANSCRIPT",
                status="FAILED",
                input_json={
                    "prompt_supplement_hash": prompt_supplement_hash(db, "transcript_correction", job)
                },
            )
        )
        db.commit()
        job_id = job.id
    result = client.post(f"/api/jobs/{job_id}/retry-from-step", json={"step_name": "CORRECT_TRANSCRIPT"})
    assert result.status_code == 200
    with factory() as db:
        job = db.get(Job, job_id)
        asr = db.scalar(select(JobStep).where(JobStep.job_id == job_id, JobStep.step_name == "ASR"))
        correction = db.scalar(
            select(JobStep).where(JobStep.job_id == job_id, JobStep.step_name == "CORRECT_TRANSCRIPT")
        )
        assert asr.status == "REUSED" and asr.output_json == {"transcript_id": "existing"}
        assert correction.status == "PENDING" and job.payload_json[SNAPSHOT_KEY] == original
        assert job_setting(db, "model-profile:original", job)["interface_capabilities"] is not None


def test_active_full_replay_uses_pending_config_without_changing_running_config(client, app_and_session):
    app, factory = app_and_session
    with factory() as db:
        job, _ = seed_frozen_job(db, app.dependency_overrides[get_settings]())
        job.status = "RUNNING"
        job.lease_owner = "old-worker"
        db.commit()
        job_id = job.id
    result = client.post(f"/api/jobs/{job_id}/retry-full")
    assert result.status_code == 200 and result.json()["deferred"] is True
    with factory() as db:
        job = db.get(Job, job_id)
        pending = deepcopy(job.payload_json[PENDING_EXECUTION_KEY])
        assert EXECUTION_KEY not in job.payload_json
        assert job_setting(db, "model-profile:original", job).get("interface_capabilities") is None
        row = db.get(Setting, "model-profile:original")
        row.value_json = {**row.value_json, "timeout_seconds": 900, "model": "later-different"}
        job.lease_owner = None
        db.commit()
        assert resume_deferred_full_replays(db) == 1
        assert PENDING_EXECUTION_KEY not in job.payload_json and job.payload_json[EXECUTION_KEY] == pending
        assert job_setting(db, "model-profile:original", job)["timeout_seconds"] == 240


def test_consecutive_submissions_and_replay_keep_entry_specific_parameters(client, app_and_session):
    from zhijian.services.video_support import provider_for_role

    app, factory = app_and_session
    settings = app.dependency_overrides[get_settings]()
    store = build_secret_store(settings.secret_store, settings.data_dir)
    with factory() as db:
        for name, base, mode, retries in [
            ("free", "https://free.fixture/v1", "FREE_TIER", 2),
            ("official", "https://official.fixture/v1", "DIRECT", 0),
        ]:
            db.add(
                Setting(
                    key=f"model-profile:{name}",
                    value_json={
                        "name": name,
                        "provider": "OpenAI Compatible",
                        "base_url": base,
                        "model": "deepseek-v4-flash",
                        "location": "REMOTE",
                        "reliability_mode": mode,
                        "retry_count": retries,
                        "max_output_tokens": 4096,
                        "capabilities": [
                            "TRANSCRIPT_CORRECTION",
                            "GLOBAL_SYNTHESIS",
                            "STRUCTURED_EXTRACTION",
                        ],
                    },
                )
            )
            store.set(f"model-profile:{name}:api-key", "fixture-account")
        db.merge(Setting(key="model-routing", value_json={"primary_id": "free", "fallback_id": None}))
        db.add(
            Setting(
                key="ai-stage-policy:TRANSCRIPT_CORRECTION",
                value_json={
                    "execution_mode": "REMOTE_ONLY",
                    "remote_profile_id": "free",
                    "max_attempts": 4,
                },
            )
        )
        db.commit()
    first = client.post("/api/capture", json={"text": "https://www.bilibili.com/video/BV1fixture"})
    assert first.status_code == 200
    with factory() as db:
        original_job = db.get(Job, first.json()["job_id"])
        snapshot = deepcopy(original_job.payload_json[SNAPSHOT_KEY])
        db.get(Setting, "model-profile:free").value_json = {
            **db.get(Setting, "model-profile:free").value_json,
            "retry_count": 1,
            "max_output_tokens": 8192,
        }
        db.get(Setting, "model-routing").value_json = {"primary_id": "official", "fallback_id": None}
        db.get(Setting, "ai-stage-policy:TRANSCRIPT_CORRECTION").value_json = {
            "execution_mode": "REMOTE_ONLY",
            "remote_profile_id": "official",
            "retry_count": 0,
            "temperature": 0.8,
            "max_attempts": 4,
        }
        original_job.status = "FAILED"
        db.commit()
    second = client.post("/api/capture", json={"text": "https://www.bilibili.com/video/BV1fixture"})
    assert second.status_code == 200
    assert client.post(f"/api/jobs/{first.json()['job_id']}/retry").status_code == 200
    with factory() as db:
        old = db.get(Job, first.json()["job_id"])
        new = db.get(Job, second.json()["job_id"])
        assert old.payload_json[SNAPSHOT_KEY] == snapshot
        assert job_setting(db, "model-routing", old)["primary_id"] == "free"
        assert job_setting(db, "model-routing", new)["primary_id"] == "official"
        original_provider, _, _ = provider_for_role(db, settings, "transcript_correction", old)
        new_provider, _, _ = provider_for_role(db, settings, "transcript_correction", new)
        assert original_provider.primary.profile_id == "free"
        assert original_provider.primary_reliability.retry_count == 1
        assert original_provider.request_options.max_output_tokens == 8192
        assert new_provider.primary.profile_id == "official"
        assert (
            new_provider.primary_reliability.mode == "DIRECT"
            and new_provider.primary_reliability.retry_count == 0
        )
        assert new_provider.request_options.max_output_tokens == 4096


def test_replay_budget_keeps_prior_run_attempts_and_original_limit(app_and_session):
    app, factory = app_and_session
    with factory() as db:
        job, _ = seed_frozen_job(db, app.dependency_overrides[get_settings]())
        job.payload_json = {**job.payload_json, EXECUTION_KEY: build_execution_config(db, job)}
        job.started_at = utc_now()
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="LocalAiMux",
                operation="correction",
                status="COMPLETED",
                created_at=utc_now() - timedelta(days=1),
                request_meta_json={
                    "location": "REMOTE",
                    "model": "codebuddy/glm-5.3",
                    "profile_id": "original",
                },
                response_meta_json={"prompt_tokens": 10, "completion_tokens": 2},
            )
        )
        db.commit()
        with pytest.raises(AIBudgetExceeded, match="次数上限"):
            ensure_ai_budget(
                db,
                job,
                location="REMOTE",
                input_chars=4,
                provider="LocalAiMux",
                model="codebuddy/glm-5.3",
                profile_id="original",
            )
