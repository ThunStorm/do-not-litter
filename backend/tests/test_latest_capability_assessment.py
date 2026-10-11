"""Capability gates use new assessments, while execution intent stays frozen."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from zhijian.ai.job_config import SNAPSHOT_KEY, capture_ai_config, job_setting, latest_profile_assessment
from zhijian.ai.model_registry import business_assessments
from zhijian.core.config import get_settings
from zhijian.db.models import Job, Setting, SystemEvent
from zhijian.services.video_support import ProviderUnavailable, provider_for_role


def profile(capability, status):
    return {
        "name": "Original model",
        "provider": "DeepSeek",
        "model": "original",
        "base_url": "https://api.example.test",
        "location": "REMOTE",
        "enabled": True,
        "capabilities": [capability],
        "max_output_tokens": 512,
        "probe_results": {capability: status},
        "business_assessments": business_assessments("original", {capability: status}),
    }


@pytest.mark.parametrize(
    "stage,role,capability",
    [
        ("TRANSCRIPT_CORRECTION", "transcript_correction", "TRANSCRIPT_CORRECTION"),
        ("GROUND_MAP", "grounded_map", "STRUCTURED_EXTRACTION"),
        ("GENERATE_AI_NOTE", "video_note_summary", "GLOBAL_SYNTHESIS"),
        ("NOTE_REDUCE", "note_reduce", "GLOBAL_SYNTHESIS"),
    ],
)
def test_each_stage_uses_current_results_and_keeps_old_execution_settings(
    app_and_session, monkeypatch, stage, role, capability
):
    _, factory = app_and_session
    seen = []

    def create_provider(config, *_args):
        seen.append(deepcopy(config))
        return SimpleNamespace(name="deepseek"), "deepseek", config["model"]

    monkeypatch.setattr("zhijian.services.video_support._provider_from_config", create_provider)
    with factory() as db:
        original = profile(capability, "FAIL")
        db.add_all(
            [
                Setting(key="model-profile:original", value_json=original),
                Setting(key="model-routing", value_json={"primary_id": "original"}),
                Setting(
                    key=f"ai-stage-policy:{stage}",
                    value_json={
                        "execution_mode": "REMOTE_ONLY",
                        "remote_profile_id": "original",
                        "temperature": 0.1,
                    },
                ),
            ]
        )
        db.commit()
        snapshot = capture_ai_config(db, get_settings())
        job = Job(job_type="TRAVEL", payload_json={SNAPSHOT_KEY: snapshot})
        db.add(job)
        db.commit()
        with pytest.raises(ProviderUnavailable):
            provider_for_role(db, get_settings(), role, job)
        with factory() as writer:
            writer.get(Setting, "model-profile:original").value_json = {
                **profile(capability, "PASS"),
                "max_output_tokens": 8192,
            }
            writer.get(Setting, "model-routing").value_json = {"primary_id": "different"}
            writer.get(Setting, f"ai-stage-policy:{stage}").value_json = {
                "execution_mode": "LOCAL_ONLY",
                "local_profile_id": "different",
                "temperature": 0.9,
            }
            writer.commit()
        provider, _, model = provider_for_role(db, get_settings(), role, job)
        assert model == "original"
        assert provider.request_options.temperature == 0.1
        assert provider.request_options.max_output_tokens == 512
        assert seen[-1]["probe_results"][capability] == "PASS"
        assert job.payload_json[SNAPSHOT_KEY] == snapshot
        assert job_setting(db, "model-profile:original", job)["probe_results"][capability] == "FAIL"
        events = db.query(SystemEvent).filter_by(event_type="ai.capability.checked", entity_id=job.id).all()
        assert events[-1].detail_json["profiles"][0]["status"] == "PASS"
        assert events[-1].detail_json["profiles"][0]["source"] == "CURRENT_SAVED"
        with factory() as writer:
            writer.get(Setting, "model-profile:original").value_json = profile(capability, "FAIL")
            writer.commit()
        with pytest.raises(ProviderUnavailable):
            provider_for_role(db, get_settings(), role, job)


def test_latest_pass_does_not_need_stale_capability_declaration(app_and_session, monkeypatch):
    _, factory = app_and_session
    monkeypatch.setattr(
        "zhijian.services.video_support._provider_from_config",
        lambda config, *_args: (SimpleNamespace(name="deepseek"), "deepseek", config["model"]),
    )
    with factory() as db:
        original = {**profile("STRUCTURED_EXTRACTION", "FAIL"), "capabilities": ["CLASSIFICATION"]}
        db.add_all(
            [
                Setting(key="model-profile:original", value_json=original),
                Setting(key="model-routing", value_json={"primary_id": "original"}),
                Setting(key="ai-stage-policy:GROUND_MAP", value_json={"execution_mode": "AUTO"}),
            ]
        )
        db.commit()
        job = Job(job_type="TRAVEL", payload_json={SNAPSHOT_KEY: capture_ai_config(db, get_settings())})
        db.add(job)
        db.commit()
        db.get(Setting, "model-profile:original").value_json = profile("STRUCTURED_EXTRACTION", "PASS")
        db.commit()
        assert provider_for_role(db, get_settings(), "grounded_map", job)[2] == "original"


def test_identity_mismatch_does_not_borrow_another_models_pass(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        frozen = profile("GLOBAL_SYNTHESIS", "FAIL")
        db.add(
            Setting(
                key="model-profile:original",
                value_json={**profile("GLOBAL_SYNTHESIS", "PASS"), "model": "different"},
            )
        )
        db.commit()
        result, metadata = latest_profile_assessment(db, "original", frozen)
        assert result == frozen and metadata["source"] == "SNAPSHOT_IDENTITY_UNAVAILABLE"
        current = db.get(Setting, "model-profile:original")
        current.value_json = {**profile("GLOBAL_SYNTHESIS", "PASS"), "enabled": False}
        db.commit()
        result, metadata = latest_profile_assessment(db, "original", frozen)
        assert result["enabled"] is False and metadata["source"] == "CURRENT_SAVED"
