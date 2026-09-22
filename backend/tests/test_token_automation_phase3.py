from zhijian.ai.graduation import graduation_gate
from zhijian.ai.regression import pipeline_regression_gate
from zhijian.ai.token_monitor import detect_token_anomalies, record_token_anomalies
from zhijian.core.config import Settings
from zhijian.db.models import ExternalCallAudit, Job, PlaceMention, Source, SystemEvent, VideoAsset
from zhijian.providers.amap import POICandidate
from zhijian.services.video_support import resolve_mentions_with_amap


def _audit(
    *, stage: str, prompt_tokens: int, input_hash: str = "", route: str = "primary"
) -> ExternalCallAudit:
    return ExternalCallAudit(
        capability="LLM",
        provider="fixture",
        operation=stage,
        status="COMPLETED",
        request_meta_json={"stage": stage, "model": "fixture", "input_hash": input_hash, "route": route},
        response_meta_json={"prompt_tokens": prompt_tokens},
    )


def test_token_monitor_detects_repeated_inputs_and_budget_spikes() -> None:
    anomalies = detect_token_anomalies(
        [
            _audit(stage="GROUND_MAP", prompt_tokens=900, input_hash="same"),
            _audit(stage="GROUND_MAP", prompt_tokens=900, input_hash="same"),
        ],
        expected_prompt_tokens=1_000,
    )

    assert {item.suspected_reason for item in anomalies} == {
        "REPEATED_STAGE_INPUT",
        "PROMPT_TOKENS_ABOVE_EXPECTED",
    }


def test_token_monitor_records_without_rerunning_a_job(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="COMPLETED",
            payload_json={"ai_soft_budget": {"expected_prompt_tokens": 100}},
        )
        db.add(job)
        db.flush()
        db.add_all(
            [
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="fixture",
                    operation="NOTE_REDUCE",
                    status="COMPLETED",
                    request_meta_json={"stage": "NOTE_REDUCE", "input_hash": "repeat"},
                    response_meta_json={"prompt_tokens": 100},
                ),
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="fixture",
                    operation="NOTE_REDUCE",
                    status="COMPLETED",
                    request_meta_json={"stage": "NOTE_REDUCE", "input_hash": "repeat"},
                    response_meta_json={"prompt_tokens": 100},
                ),
            ]
        )
        db.commit()
        assert record_token_anomalies(db, job)
        assert db.query(SystemEvent).filter_by(event_type="AI_TOKEN_ANOMALY", entity_id=job.id).count() >= 1
        assert job.status == "COMPLETED"


def test_regression_gate_rejects_cost_growth_without_quality_gain() -> None:
    baseline = {"remote_prompt_tokens": 100, "evidence_coverage": 1, "place_recall": 1}
    candidate = {"remote_prompt_tokens": 116, "evidence_coverage": 1, "place_recall": 1}

    result = pipeline_regression_gate(baseline, candidate)

    assert not result["passed"]
    assert not result["checks"]["token_growth"]


def test_graduation_gate_requires_recorded_real_evidence() -> None:
    evidence = {
        "fixture": {"passed": True},
        "real_videos": [{"duration_minutes": minutes, "passed": True} for minutes in (10, 30, 60)],
        "replay_checks": ["same_profile", "different_profile", "force_regenerate", "step_replay"],
        "provider_checks": ["LOCAL", "REMOTE", "FALLBACK", "TIMEOUT", "INVALID_JSON"],
        "asr": {
            "qwen_failures": 0,
            "whisper_failures": 0,
            "qwen_place_recall": 1,
            "whisper_place_recall": 1,
            "qwen_proper_noun_accuracy": 1,
            "whisper_proper_noun_accuracy": 1,
            "timestamps_passed": True,
            "long_form_passed": True,
            "oom": False,
        },
        "quality": {
            "critical_hallucinations": 0,
            "timestamp_mutations": 0,
            "segment_identity_mutations": 0,
            "wrong_auto_confirms": 0,
            "place_recall": 1,
            "baseline_place_recall": 1,
            "evidence_coverage": 1,
            "baseline_evidence_coverage": 1,
        },
        "baseline": {
            "prompt_tokens": 100,
            "note_profile_prompt_tokens": 100,
            "time_to_first_useful_note_ms": 100,
            "amap_requests": 10,
            "screenshot_processes": 9,
            "retries": 2,
            "fallbacks": 1,
        },
        "candidate": {
            "prompt_tokens": 60,
            "note_profile_prompt_tokens": 20,
            "unchanged_replay_tokens": 0,
            "time_to_first_useful_note_ms": 80,
            "amap_requests": 8,
            "screenshot_processes": 3,
            "retries": 1,
            "fallbacks": 0,
        },
    }

    assert graduation_gate(evidence)["passed"]
    assert not graduation_gate({"fixture": {"passed": True}})["passed"]


def test_only_auto_strong_creates_a_confirmed_place(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session

    class Provider:
        def __init__(self, *_args, **_kwargs) -> None:
            self.candidate = POICandidate(
                "park", "翠湖公园", "昆明市五华区", "云南省", "昆明市", "五华区",
                102.7, 25.05, "110000",
            )

        def search(self, *_args, **_kwargs):
            return [self.candidate]

        def detail(self, provider_id):
            assert provider_id == "park"
            return self.candidate

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/poi")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖公园",
            raw_name="翠湖公园",
            suggested_name="翠湖公园",
            city_hint="昆明市",
            place_type="PARK",
        )
        db.add(mention)
        db.commit()

        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture") == (1, 0)
        assert mention.metadata_json["confirmation_origin"] == "AUTO_STRONG"
