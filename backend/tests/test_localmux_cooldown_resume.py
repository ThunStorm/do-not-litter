from datetime import timedelta

import httpx
import pytest
from sqlalchemy import delete, select

from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.interface_contract import InterfaceCapabilities
from zhijian.ai.job_config import SNAPSHOT_KEY
from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import AICacheEntry, ExternalCallAudit, Job, JobStep, JobStepArtifact
from zhijian.providers.llm import OpenAICompatibleProvider, provider_error_details
from zhijian.services import job_replay, jobs, video_pipeline, video_support

ADDRESS = "http://127.0.0.1:8317/v1"
MODEL = "qoder/Sonus"
STEP = "EXTRACT_TRAVEL_FACTS"


def mux_provider():
    return OpenAICompatibleProvider(
        "localaimux",
        ADDRESS,
        "test-key",
        connection_type="LOCAL_ROUTER",
        interface_capabilities=InterfaceCapabilities(model=MODEL, base_url=ADDRESS, sampled_at="2026-11-06"),
    )


def cooldown_response(url, request_id="req-b-cooldown", delay="30", **fields):
    return httpx.Response(
        503,
        request=httpx.Request("POST", url),
        headers={"Retry-After": delay, "X-Request-ID": request_id},
        json={
            "error": {
                "type": "localmux_error",
                "code": "LMX_PROVIDER_COOLDOWN",
                "upstream_dispatched": False,
                "cooldown_reason": "transient_failure",
                **fields,
            }
        },
    )


@pytest.mark.parametrize(
    "delay,fields",
    [
        ("31", {}),
        ("0", {}),
        ("30", {"upstream_dispatched": True}),
        ("30", {"upstream_dispatched": None}),
        ("30", {"cooldown_reason": "rate_limited"}),
    ],
)
def test_unconfirmed_or_nontransient_refusals_are_not_safe_to_defer(monkeypatch, delay, fields):
    monkeypatch.setattr(
        "zhijian.providers.llm._post", lambda url, **kw: cooldown_response(url, delay=delay, **fields)
    )
    with pytest.raises(httpx.HTTPStatusError):
        mux_provider().generate_json([{"role": "user", "content": "fixture"}], model=MODEL)


@pytest.mark.parametrize(
    "outcome,expected_error",
    [
        ("resume", None),
        ("rejected_again", "AI_PROVIDER_CIRCUIT_OPEN"),
        ("cache_expired", "REPLAY_COOLDOWN_INPUT_CHANGED"),
        ("artifact_expired", "REPLAY_COOLDOWN_UNAVAILABLE"),
        ("attempt_limit", "AI_PROVIDER_ATTEMPT_BUDGET"),
        ("cancel", None),
    ],
)
def test_first_payload_timeout_then_cooldown_replays_the_unsent_chunk_once(
    app_and_session, tmp_path, monkeypatch, outcome, expected_error
):
    app, factory = app_and_session
    settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
    now = [utc_now()]
    monkeypatch.setattr(jobs, "utc_now", lambda: now[0])
    monkeypatch.setattr(job_replay, "utc_now", lambda: now[0])

    # The wire fixture distinguishes Gateway requests from Adapter dispatch.
    http_calls, upstream = [], []
    cooling = False

    def post(url, **kwargs):
        nonlocal cooling
        chunk = kwargs["json"]["messages"][-1]["content"]
        http_calls.append(chunk)
        if cooling:
            return cooldown_response(url)
        upstream.append(chunk)
        if chunk == "timeout-a":
            cooling = True
            return httpx.Response(
                504,
                request=httpx.Request("POST", url),
                headers={"X-Request-ID": "req-a-timeout"},
                json={
                    "error": {
                        "type": "localmux_error",
                        "code": "LMX_PROCESS_TIMEOUT",
                        "reason_code": "upstream_first_payload_timeout",
                        "timeout_layer": "upstream_first_payload",
                        "timeout_limit_ms": 120_000,
                    }
                },
            )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": '{"section_facts":[],"places":[],"warnings":[]}'}}]},
        )

    monkeypatch.setattr("zhijian.providers.llm._post", post)
    monkeypatch.setattr(
        video_support, "_provider_from_config", lambda *_args: (mux_provider(), "localaimux", MODEL)
    )
    config = {
        "name": "fixture",
        "enabled": True,
        "provider": "LocalAiMux",
        "model": MODEL,
        "base_url": ADDRESS,
        "location": "REMOTE",
        "modalities": ["text"],
        "capabilities": ["STRUCTURED_EXTRACTION"],
        "reliability_mode": "DIRECT",
    }
    monkeypatch.setattr(
        video_support, "_profile_supports_capability", lambda profile, *a, **kw: bool(profile)
    )

    def run_replay(db, job, _settings, from_step):
        assert from_step == STEP
        provider, provider_name, model = video_support.provider_for_role(db, settings, "grounded_map", job)
        boundary = job.payload_json.get(jobs.COOLDOWN_RESUME_KEY)
        gateway = AIWorkloadGateway()
        for index, chunk in enumerate(("already-done", "rejected-b"), start=1):
            result = gateway.execute_cached_json(
                db,
                job=job,
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider=provider,
                provider_name=provider_name,
                model=model,
                messages=[{"role": "user", "content": chunk}],
                semantic_options={},
                cache_enabled=True,
                force_regenerate=False,
                max_stage_attempts=1 if boundary and outcome == "attempt_limit" else 2,
                attempt_metadata={"chunk_index": index, "split_path": "root"},
                cooldown_boundary=boundary,
            )
            if result.metadata.get("cooldown_boundary_reached"):
                boundary = None
            if not boundary and chunk == "already-done" and http_calls == ["already-done"]:
                with pytest.raises(httpx.HTTPStatusError) as timeout:
                    mux_provider().generate_json([{"role": "user", "content": "timeout-a"}], model=MODEL)
                assert (
                    provider_error_details(timeout.value)["reason_code"] == "upstream_first_payload_timeout"
                )
        job.status = "COMPLETED"
        job.lease_owner = None
        job.lease_expire_at = None
        db.commit()

    monkeypatch.setattr(video_pipeline, "_process_video_replay", run_replay)

    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="QUEUED",
            current_step=STEP,
            priority=-10,
            payload_json={
                "replay_from_step": STEP,
                "transcript_id": "fixture-transcript",
                SNAPSHOT_KEY: {
                    "version": 1,
                    "settings": {
                        "model-routing": {"primary_id": "cooldown-fixture"},
                        "model-profile:cooldown-fixture": config,
                    },
                },
            },
        )
        db.add(job)
        db.flush()
        job_id = job.id
        db.add_all(
            [
                JobStep(job_id=job_id, step_name="FETCH_METADATA", status="COMPLETED"),
                JobStep(
                    job_id=job_id,
                    step_name=STEP,
                    status="RUNNING",
                    started_at=now[0],
                    input_json={
                        "transcript": "fixture-transcript",
                        "prompt_supplement_hash": video_support.prompt_supplement_hash(
                            db, "travel_place_extraction", job
                        ),
                    },
                ),
                JobStepArtifact(
                    job_id=job_id,
                    step_name="FETCH_METADATA",
                    status="AVAILABLE",
                    artifact_type="STEP_OUTPUT",
                    replayable_until=now[0] + timedelta(minutes=3),
                ),
            ]
        )
        db.commit()
        job = jobs.lease_next_job(db, "worker-1", 120)
        original_fence = jobs.job_run_fence(job)
        video_pipeline.process_video_job(db, job, settings)
        assert job.status == "QUEUED" and job.lease_owner is None
        assert job.payload_json[jobs.COOLDOWN_RESUME_KEY]["prior_fence"] == original_fence
        assert upstream == ["already-done", "timeout-a"]
        assert jobs.lease_next_job(db, "worker-1", 120) is None

        other = Job(job_type="TRAVEL", status="QUEUED", priority=10, payload_json={})
        db.add(other)
        db.commit()
        assert jobs.lease_next_job(db, "worker-1", 120).id == other.id

        if outcome == "cache_expired":
            db.execute(delete(AICacheEntry))
            db.commit()
        elif outcome == "artifact_expired":
            artifact = db.scalar(select(JobStepArtifact).where(JobStepArtifact.job_id == job_id))
            artifact.status = "EXPIRED"
            db.commit()

    # A fresh Session/worker sees the durable wait, not a process-local sleep.
    if outcome == "cancel":
        from fastapi.testclient import TestClient

        assert TestClient(app).post(f"/api/jobs/{job_id}/cancel").status_code == 200
    now[0] += timedelta(seconds=30)
    cooling = outcome == "rejected_again"
    with factory() as db:
        leased = jobs.lease_next_job(db, "worker-2", 120)
        if outcome == "cancel":
            assert leased is None
            assert db.get(Job, job_id).status == "CANCELLED"
        else:
            assert leased.id == job_id and jobs.job_run_fence(leased) != original_fence
            video_pipeline.process_video_job(db, leased, settings)
            assert leased.status == ("COMPLETED" if outcome == "resume" else "NEEDS_USER")
            assert leased.error_code == expected_error
            assert jobs.lease_next_job(db, "worker-2", 120) is None

        assert upstream == ["already-done", "timeout-a"] + (["rejected-b"] if outcome == "resume" else [])
        rows = db.scalars(select(ExternalCallAudit).where(ExternalCallAudit.job_id == job_id)).all()
        rejected = [row for row in rows if row.request_meta_json.get("upstream_dispatched") is False]
        assert len(rejected) == (2 if outcome == "rejected_again" else 1)
        assert rejected[0].error_code == "AI_PROVIDER_CIRCUIT_OPEN"
        assert len(http_calls) == (4 if outcome in {"resume", "rejected_again"} else 3)
