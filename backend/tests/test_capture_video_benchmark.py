import importlib.util
from datetime import timedelta
from pathlib import Path

from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Job, JobStep, JobStepArtifact, Setting


def _capture():
    path = Path(__file__).parents[2] / "scripts" / "capture_video_benchmark.py"
    spec = importlib.util.spec_from_file_location("capture_video_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capture_video_benchmark_exports_replay_safe_metrics(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="VIDEO", status="PARTIAL_SUCCESS", payload_json={})
        db.add_all(
            [
                job,
                Setting(key="model-profile:local", value_json={"provider": "ollama", "model": "qwen"}),
                Setting(key="ai-stage-policy:GENERATE_AI_NOTE", value_json={"cache_enabled": True}),
            ]
        )
        db.flush()
        db.add_all(
            [
                JobStep(
                    job_id=job.id,
                    step_name="GENERATE_AI_NOTE",
                    status="COMPLETED",
                    output_json={"note": "ok"},
                ),
                JobStepArtifact(
                    job_id=job.id,
                    step_name="GENERATE_AI_NOTE",
                    artifact_ref_json={"note": "ok"},
                    input_hash="input-hash",
                    content_hash="output-hash",
                    replayable_until=utc_now() + timedelta(hours=1),
                ),
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="ollama",
                    operation="video_note_summary",
                    status="COMPLETED",
                    duration_ms=50,
                    request_meta_json={"stage": "GENERATE_AI_NOTE", "route": "fallback"},
                    response_meta_json={"prompt_tokens": 3, "completion_tokens": 2},
                ),
            ]
        )
        db.commit()
        result = _capture().capture(db, sample_id="fixture-01", profile_id="local", job_id=job.id)

    assert result["sample_id"] == "fixture-01"
    assert result["stage_metrics"]["GENERATE_AI_NOTE"] == {
        "input_tokens": 3,
        "output_tokens": 2,
        "cached_tokens": 0,
        "attempts": 1,
        "fallbacks": 1,
        "cache_hits": 0,
        "wall_time_ms": 50,
    }
    assert result["replay_artifacts"][0]["content_hash"] == "output-hash"
