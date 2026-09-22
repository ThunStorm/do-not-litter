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
        now = utc_now()
        job = Job(
            job_type="VIDEO",
            status="PARTIAL_SUCCESS",
            payload_json={},
            started_at=now,
            finished_at=now + timedelta(seconds=10),
        )
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
                JobStep(
                    job_id=job.id,
                    step_name="FETCH_METADATA",
                    status="COMPLETED",
                    output_json={"duration_ms": 600_000},
                ),
                JobStep(
                    job_id=job.id,
                    step_name="CORRECT_TRANSCRIPT",
                    status="COMPLETED",
                    output_json={
                        "transcript_chars": 1_000,
                        "total_segments": 20,
                        "candidate_segments": 4,
                        "source_class": "LOCAL_ASR_WITH_CONFIDENCE",
                        "correction_coverage_ratio": 0.2,
                        "correction_target_chars": 150,
                        "correction_context_chars": 100,
                        "correction_input_chars": 250,
                        "correction_input_ratio": 0.25,
                    },
                ),
                JobStep(
                    job_id=job.id,
                    step_name="ASR",
                    status="COMPLETED",
                    started_at=now + timedelta(seconds=1),
                    finished_at=now + timedelta(seconds=2),
                ),
                JobStep(
                    job_id=job.id,
                    step_name="RESOLVE_POI",
                    status="COMPLETED",
                    output_json={"amap_request_count": 4, "amap_cache_hit_count": 2},
                    finished_at=now + timedelta(seconds=7),
                ),
                JobStep(
                    job_id=job.id,
                    step_name="EXTRACT_SCREENSHOTS",
                    status="COMPLETED",
                    output_json={"screenshot_process_count": 6},
                    started_at=now + timedelta(seconds=8),
                    finished_at=now + timedelta(seconds=9),
                ),
                JobStep(
                    job_id=job.id,
                    step_name="MATERIALIZE",
                    status="COMPLETED",
                    finished_at=now + timedelta(milliseconds=9_500),
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
        "retries": 0,
        "fallbacks": 1,
        "cache_hits": 0,
        "wall_time_ms": 50,
    }
    assert result["baseline_metrics"] == {
        "video_minutes": 10.0,
        "transcript_chars": 1_000,
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "correction_candidate_segments": 4,
        "total_segments": 20,
        "correction_source_class": "LOCAL_ASR_WITH_CONFIDENCE",
        "correction_coverage_ratio": 0.2,
        "correction_target_chars": 150,
        "correction_context_chars": 100,
        "correction_input_chars": 250,
        "correction_input_ratio": 0.25,
        "ground_map_input_chars": 0,
        "ground_map_chunks": 0,
        "ground_map_retries": 0,
        "model_attempts": 1,
        "retries": 0,
        "fallbacks": 1,
        "amap_requests": 4,
        "amap_cache_hits": 2,
        "screenshot_processes": 6,
        "asr_runtime_ms": 1_000,
        "screenshot_stage_ms": 1_000,
        "pipeline_wall_ms": 10_000,
        "time_to_first_useful_note_ms": 9_500,
    }
    assert result["replay_artifacts"][0]["content_hash"] == "output-hash"
