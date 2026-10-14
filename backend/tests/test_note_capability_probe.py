"""Offline note-probe and routing regression for the 3bebb50 false rejection."""

import json
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest

from zhijian.ai.capabilities import AICapability
from zhijian.ai.cost_router import choose_auto_route
from zhijian.ai.job_config import SNAPSHOT_KEY, build_execution_config, capture_ai_config, job_setting
from zhijian.ai.model_registry import (
    NOTE_PROBE_SOURCES,
    NOTE_PROBE_VERSION,
    _assess_note_probe,
    business_assessments,
    business_probe_status,
)
from zhijian.ai.policies import validate_stage_policy
from zhijian.ai.reliability import classify_provider_error
from zhijian.ai.schemas import AIStagePolicy
from zhijian.core.config import get_settings
from zhijian.core.time import utc_now
from zhijian.db.models import Job, Setting, SystemEvent
from zhijian.providers.llm import LLMResult
from zhijian.services.job_replay import _current_note_recovery
from zhijian.services.video_support import ProviderUnavailable, provider_for_role


def note_section(ids, summary):
    return {
        "summary": summary,
        "segment_ids": ids,
        "supporting_quotes": [NOTE_PROBE_SOURCES[item] for item in ids],
    }


def merged_note():
    return {"sections": [note_section(["s1", "s2"], "西安十月门票二十元，建议避开周末；在洛阳可尝米粉。")]}


@pytest.mark.parametrize("layout", ["merged", "reversed", "split", "bullets"])
def test_note_probe_accepts_evidence_preserving_layouts(layout):
    value = merged_note()
    if layout == "reversed":
        value["sections"] = [
            note_section(["s2"], "洛阳建议尝米粉。"),
            note_section(["s1"], "西安十月门票二十元，周末不建议前往。"),
        ]
    elif layout == "split":
        value["sections"] = [
            note_section(["s1"], "西安十月门票二十元。"),
            note_section(["s1"], "西安建议避开周末。"),
            note_section(["s2"], "洛阳建议尝米粉。"),
        ]
    elif layout == "bullets":
        value["sections"][0].update(
            summary="两地出行建议", bullets=["西安10月门票20元，避开周末", "洛阳推荐米粉"]
        )
    assert _assess_note_probe(value) == ("PASS", "NOTE_PROBE_EVIDENCE_COVERED")


@pytest.mark.parametrize(
    "problem,reason",
    [
        ("unknown_id", "NOTE_PROBE_SOURCE_INVALID"),
        ("duplicate_id", "NOTE_PROBE_SOURCE_INVALID"),
        ("fabricated_quote", "NOTE_PROBE_QUOTE_INVALID"),
        ("wrong_source", "NOTE_PROBE_QUOTE_INVALID"),
        ("missing_fact", "NOTE_PROBE_FACT_EVIDENCE_MISSING"),
        ("price", "NOTE_PROBE_FACT_CONTRADICTION"),
        ("negative", "NOTE_PROBE_FACT_CONTRADICTION"),
        ("food_negative", "NOTE_PROBE_FACT_CONTRADICTION"),
    ],
)
def test_note_probe_rejects_fact_and_evidence_violations(problem, reason):
    value = merged_note()
    section = value["sections"][0]
    if problem == "unknown_id":
        section["segment_ids"] = ["s3"]
    elif problem == "duplicate_id":
        section["segment_ids"] = ["s1", "s1"]
    elif problem == "fabricated_quote":
        section["supporting_quotes"] = ["西安门票100元。"]
    elif problem == "wrong_source":
        section["segment_ids"] = ["s1"]
    elif problem == "missing_fact":
        section["supporting_quotes"] = ["西安10月门票20元", NOTE_PROBE_SOURCES["s2"]]
    elif problem == "price":
        section["summary"] = "西安10月门票100元，不推荐周末；洛阳推荐米粉。"
    elif problem == "negative":
        section["summary"] = "西安10月门票20元，推荐周末；洛阳推荐米粉。"
    else:
        section["summary"] = "西安10月门票20元，不推荐周末；洛阳不推荐米粉。"
    assert _assess_note_probe(value) == ("FAIL", reason)


def test_unrecognized_paraphrase_is_unverified_instead_of_failed():
    value = merged_note()
    value["sections"][0]["summary"] = "古都错峰出行和地方小吃建议。"
    assert _assess_note_probe(value) == ("NOT_TESTED", "NOTE_PROBE_SUMMARY_UNCERTAIN")


def profile_with_assessment(status="FAIL", version="business-mini-v1"):
    record = business_assessments("deepseek-v4-flash", {"GLOBAL_SYNTHESIS": status})[0]
    record["prompt_version"] = version
    return {
        "name": "DeepSeek Flash",
        "model": "deepseek-v4-flash",
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "location": "REMOTE",
        "enabled": True,
        "capabilities": ["GLOBAL_SYNTHESIS"],
        "probe_results": {"GLOBAL_SYNTHESIS": status},
        "business_assessments": [record],
    }


@pytest.mark.parametrize(
    "status,version,expected",
    [
        ("FAIL", "business-mini-v1", "NOT_TESTED"),
        ("PASS", "business-mini-v1", "NOT_TESTED"),
        ("FAIL", NOTE_PROBE_VERSION, "FAIL"),
        ("PASS", NOTE_PROBE_VERSION, "PASS"),
    ],
)
def test_save_auto_execution_and_recovery_agree(app_and_session, monkeypatch, status, version, expected):
    _, factory = app_and_session
    profile = profile_with_assessment(status, version)
    original = deepcopy(profile)
    assert business_probe_status(profile, "GLOBAL_SYNTHESIS") == expected
    policy = AIStagePolicy(
        stage="GENERATE_AI_NOTE",
        capability="GLOBAL_SYNTHESIS",
        execution_mode="REMOTE_FIRST",
        remote_profile_id="flash",
    )
    if expected == "FAIL":
        with pytest.raises(ValueError):
            validate_stage_policy(policy, {"flash": profile})
    else:
        validate_stage_policy(policy, {"flash": profile})
    auto = choose_auto_route("NOTE_REDUCE", AICapability.GLOBAL_SYNTHESIS, {"flash": profile})
    assert (auto is not None) == (expected != "FAIL")
    monkeypatch.setattr(
        "zhijian.services.video_support._provider_from_config",
        lambda config, *_args: (SimpleNamespace(name="deepseek"), "deepseek", config["model"]),
    )
    with factory() as db:
        db.add_all(
            [
                Setting(key="model-profile:flash", value_json=profile),
                Setting(key="model-routing", value_json={"primary_id": "flash"}),
                Setting(
                    key="ai-stage-policy:GENERATE_AI_NOTE", value_json={"execution_mode": "REMOTE_FIRST"}
                ),
            ]
        )
        db.commit()
        job = Job(job_type="TRAVEL", payload_json={})
        recovery = _current_note_recovery(db, job)
        assert (recovery is not None) == (expected != "FAIL")
        if recovery:
            assert recovery["probe"] == expected and recovery["policy"]["remote_profile_id"] == "flash"
        if expected == "FAIL":
            with pytest.raises(ProviderUnavailable) as error:
                provider_for_role(db, get_settings(), "video_note_summary", job)
            assert error.value.code == "MODEL_CAPABILITY_REJECTED"
            assert "GLOBAL_SYNTHESIS" in str(error.value)
        else:
            _, _, model = provider_for_role(db, get_settings(), "video_note_summary", job)
            assert model == profile["model"]
    assert profile == original


def test_note_result_expiry_identity_and_legacy_failure():
    value = profile_with_assessment("FAIL", NOTE_PROBE_VERSION)
    value["business_assessments"][0]["tested_at"] = (utc_now() - timedelta(days=31)).isoformat()
    assert business_probe_status(value, "GLOBAL_SYNTHESIS") == "NOT_TESTED"
    value = profile_with_assessment("PASS", NOTE_PROBE_VERSION)
    value["model"] = "different-model"
    assert business_probe_status(value, "GLOBAL_SYNTHESIS") == "NOT_TESTED"
    value.pop("business_assessments")
    value["probe_results"]["GLOBAL_SYNTHESIS"] = "FAIL"
    assert business_probe_status(value, "GLOBAL_SYNTHESIS") == "FAIL"


def test_note_explicit_selection_does_not_expand_an_undeclared_global_backup(app_and_session, monkeypatch):
    _, factory = app_and_session
    monkeypatch.setattr(
        "zhijian.services.video_support._provider_from_config",
        lambda config, *_args: (SimpleNamespace(name="deepseek"), "deepseek", config["model"]),
    )
    with factory() as db:
        db.add_all(
            [
                Setting(
                    key="model-profile:flash", value_json=profile_with_assessment("PASS", NOTE_PROBE_VERSION)
                ),
                Setting(
                    key="model-profile:old",
                    value_json={
                        "model": "old",
                        "location": "LOCAL",
                        "capabilities": ["STRUCTURED_EXTRACTION"],
                    },
                ),
                Setting(key="model-routing", value_json={"primary_id": "old"}),
                Setting(
                    key="ai-stage-policy:NOTE_REDUCE",
                    value_json={"execution_mode": "REMOTE_FIRST", "remote_profile_id": "flash"},
                ),
            ]
        )
        db.commit()
        provider, _, _ = provider_for_role(db, get_settings(), "note_reduce")
        assert provider.fallback is None


def test_current_note_failure_requires_override_in_recovery_and_execution(app_and_session, monkeypatch):
    _, factory = app_and_session
    monkeypatch.setattr(
        "zhijian.services.video_support._provider_from_config",
        lambda config, *_args: (SimpleNamespace(name="deepseek"), "deepseek", config["model"]),
    )
    with factory() as db:
        db.add_all(
            [
                Setting(
                    key="model-profile:flash", value_json=profile_with_assessment("FAIL", NOTE_PROBE_VERSION)
                ),
                Setting(
                    key="ai-stage-policy:GENERATE_AI_NOTE",
                    value_json={
                        "execution_mode": "REMOTE_ONLY",
                        "remote_profile_id": "flash",
                        "allow_unverified_model": True,
                    },
                ),
            ]
        )
        db.commit()
        job = Job(job_type="TRAVEL", payload_json={})
        recovery = _current_note_recovery(db, job)
        assert recovery and recovery["probe"] == "FAIL"
        assert provider_for_role(db, get_settings(), "video_note_summary", job)[2] == "deepseek-v4-flash"
        value = db.get(Setting, "model-profile:flash")
        value.value_json = {**value.value_json, "modalities": ["image"]}
        db.commit()
        assert _current_note_recovery(db, job) is None
        with pytest.raises(ProviderUnavailable):
            provider_for_role(db, get_settings(), "video_note_summary", job)


@pytest.mark.parametrize("outcome", ["pass", "ambiguous", "truncated", "bad_request"])
def test_saved_probe_records_note_diagnostics_and_preserves_indeterminate_result(
    client, app_and_session, monkeypatch, outcome
):
    _, factory = app_and_session
    original = profile_with_assessment("PASS", NOTE_PROBE_VERSION)
    with factory() as db:
        db.add(Setting(key="model-profile:flash", value_json=original))
        db.commit()
    note = merged_note()
    if outcome == "ambiguous":
        note["sections"][0]["summary"] = "古都出行和地方小吃建议。"
    captured = []

    def invoke(_provider, _profile, method, messages):
        if method == "generate_text":
            return LLMResult("PONG", "fake", "deepseek-v4-flash", {})
        assert any("json" in row["content"].lower() for row in messages)
        captured.append(messages)
        if len(captured) == 1:
            return LLMResult('{"id":"evidence_probe_01","ok":true}', "fake", "m", {})
        if len(captured) < 5:
            return LLMResult("{}", "fake", "m", {})
        if outcome == "bad_request":
            request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
            response = httpx.Response(
                400,
                request=request,
                json={"error": {"message": "must include json; api_key=sk-secret12345678"}},
            )
            error = httpx.HTTPStatusError("bad request", request=request, response=response)
            raise classify_provider_error(error) from error
        return LLMResult(
            json.dumps(note, ensure_ascii=False),
            "fake",
            "m",
            {},
            metadata={"finish_reason": "length" if outcome == "truncated" else "stop"},
        )

    monkeypatch.setattr("zhijian.ai.model_registry.invoke_profile_model", invoke)
    monkeypatch.setattr("zhijian.api.router._model_profile_provider", lambda *_args: SimpleNamespace())
    response = client.post("/api/settings/model-profiles/flash/probe")
    with factory() as db:
        stored = db.get(Setting, "model-profile:flash").value_json
        if outcome in {"truncated", "bad_request"}:
            assert response.status_code == 502 and stored == original
            if outcome == "bad_request":
                assert "must include json" in response.text and "sk-secret12345678" not in response.text
                event = db.query(SystemEvent).filter_by(event_type="model_profile.probe_failed").one()
                assert event.detail_json["probe_stage"] == "GLOBAL_SYNTHESIS"
                assert event.detail_json["error"]["status_code"] == 400
                assert "sk-secret12345678" not in json.dumps(event.detail_json)
        else:
            assert response.status_code == 200, response.text
            assert stored["supports_json_mode"] is False
            assert business_probe_status(stored, "GLOBAL_SYNTHESIS") == "PASS"
            event = db.query(SystemEvent).filter_by(event_type="model_profile.probed").one()
            assert event.detail_json["note_probe"]["status"] == (
                "PASS" if outcome == "pass" else "NOT_TESTED"
            )
            assert event.detail_json["note_probe"]["response_hash"]
            assert original["business_assessments"][0] in stored["business_assessments"]


def test_replay_refreshes_assessments_for_same_model_and_preserves_snapshot(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        original = profile_with_assessment()
        original["capabilities"] = ["TRANSCRIPT_CORRECTION"]
        original["probe_results"]["TRANSCRIPT_CORRECTION"] = "PASS"
        db.add_all(
            [
                Setting(key="model-profile:flash", value_json=original),
                Setting(key="model-routing", value_json={"primary_id": "flash"}),
                Setting(key="ai-stage-policy:NOTE_REDUCE", value_json={"execution_mode": "REMOTE_FIRST"}),
            ]
        )
        db.commit()
        snapshot = capture_ai_config(db, get_settings())
        job = Job(job_type="TRAVEL", payload_json={SNAPSHOT_KEY: snapshot})
        db.add(job)
        db.commit()
        current = profile_with_assessment("PASS", NOTE_PROBE_VERSION)
        current["probe_results"]["TRANSCRIPT_CORRECTION"] = "FAIL"
        db.get(Setting, "model-profile:flash").value_json = current
        db.commit()
        execution = build_execution_config(db, job, stages=("NOTE_REDUCE",))
        merged = execution["settings"]["model-profile:flash"]
        assert business_probe_status(merged, "GLOBAL_SYNTHESIS") == "PASS"
        assert merged["probe_results"]["TRANSCRIPT_CORRECTION"] == "FAIL"
        assert merged["capabilities"] == original["capabilities"]
        assert job.payload_json[SNAPSHOT_KEY] == snapshot
        job.payload_json = {**job.payload_json, "ai_execution_config": execution}
        db.get(Setting, "model-profile:flash").value_json = profile_with_assessment(
            "FAIL", NOTE_PROBE_VERSION
        )
        db.commit()
        assert (
            business_probe_status(job_setting(db, "model-profile:flash", job), "GLOBAL_SYNTHESIS") == "PASS"
        )
        db.get(Setting, "model-profile:flash").value_json = {**current, "model": "different"}
        db.commit()
        with pytest.raises(ValueError, match="REPLAY_MODEL_IDENTITY_CHANGED"):
            build_execution_config(db, job, stages=("NOTE_REDUCE",))


def test_deepseek_probe_actual_requests_satisfy_json_mode_contract(monkeypatch):
    from zhijian.ai.model_registry import _probe_model_profile, model_profile_from_value
    from zhijian.providers.llm import OpenAICompatibleProvider

    captured = []

    def post(url, **kwargs):
        payload = kwargs["json"]
        captured.append(payload)
        assert payload["model"] == "deepseek-v4-flash"
        assert payload["thinking"] == {"type": "disabled"}
        assert payload["max_tokens"] == 4096
        content = "PONG"
        prompt = "\n".join(row["content"] for row in payload["messages"])
        if payload["messages"][0]["role"] == "system":
            import re

            content = re.search(r"SYSTEM_[a-f0-9]+", prompt).group()
        if payload.get("response_format"):
            assert payload["response_format"] == {"type": "json_object"}
            assert any("json" in row["content"].lower() for row in payload["messages"])
            content = (
                '{"id":"evidence_probe_01","ok":true}'
                if "evidence_probe_01" in prompt
                else json.dumps(merged_note())
                if '"sections"' in prompt
                else "{}"
            )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    monkeypatch.setattr("zhijian.providers.llm._post", post)
    monkeypatch.setattr("zhijian.ai.model_registry.sleep", lambda _: None)
    profile = model_profile_from_value("offline", {**profile_with_assessment(), "max_output_tokens": 4096})
    provider = OpenAICompatibleProvider("deepseek", "https://api.deepseek.com", "offline-fixture-key")
    results = _probe_model_profile(provider, profile)
    assert results["GLOBAL_SYNTHESIS"] == "PASS"
    assert results["SYSTEM_INSTRUCTION"] == "PASS"
    assert len(captured) == 8
