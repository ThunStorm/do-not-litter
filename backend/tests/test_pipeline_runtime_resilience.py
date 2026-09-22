from datetime import timedelta

from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Job
from zhijian.services.jobs import job_run_fence, recover_stale_jobs
from zhijian.services.model_attempts import begin_model_attempt, finish_model_attempt


def test_model_attempt_is_visible_before_completion(app_and_session) -> None:
    _, factory = app_and_session
    settings = Settings(_env_file=None, worker_heartbeat_seconds=1000)
    now = utc_now()
    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            payload_json={"title": "实时模型调用"},
            current_step="GENERATE_AI_NOTE",
            lease_owner="worker:test",
            lease_expire_at=now + timedelta(seconds=90),
            heartbeat_at=now,
            started_at=now,
        )
        db.add(job)
        db.commit()
        attempt_id = begin_model_attempt(
            db,
            settings,
            job,
            provider="ollama",
            operation="note_reduce",
            request_meta={
                "stage": "NOTE_REDUCE",
                "step": "GENERATE_AI_NOTE",
                "model": "qwen-test",
                "route": "primary",
                "timeout_seconds": 300,
            },
        )
        assert db.get(ExternalCallAudit, attempt_id).status == "RUNNING"
        assert finish_model_attempt(
            db,
            job,
            attempt_id,
            status="COMPLETED",
            duration_ms=12,
            request_meta_updates={"recovery": None},
            response_meta={"prompt_tokens": 3},
            error_code=None,
            error_message=None,
        )
        attempt = db.get(ExternalCallAudit, attempt_id)
        assert attempt.status == "COMPLETED"
        assert attempt.duration_ms == 12


def test_watchdog_times_out_attempt_and_fences_late_result(app_and_session) -> None:
    _, factory = app_and_session
    now = utc_now()
    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            payload_json={},
            current_step="GENERATE_AI_NOTE",
            lease_owner="worker:test",
            lease_expire_at=now - timedelta(seconds=1),
            heartbeat_at=now,
            started_at=now - timedelta(minutes=1),
        )
        db.add(job)
        db.flush()
        attempt = ExternalCallAudit(
            job_id=job.id,
            capability="LLM",
            provider="ollama",
            operation="note_reduce",
            status="RUNNING",
            request_meta_json={
                "deadline_at": (now - timedelta(seconds=1)).isoformat(),
                "run_fence": job_run_fence(job),
            },
            response_meta_json={},
            created_at=now - timedelta(minutes=1),
        )
        db.add(attempt)
        db.commit()
        assert recover_stale_jobs(db, 900, 0) == 1
        db.refresh(job)
        db.refresh(attempt)
        assert job.status == "FAILED"
        assert job.error_code == "AI_PROVIDER_TIMEOUT"
        assert attempt.status == "TIMED_OUT"
        assert not finish_model_attempt(
            db,
            job,
            attempt.id,
            status="COMPLETED",
            duration_ms=70_000,
            request_meta_updates={},
            response_meta={"prompt_tokens": 3},
            error_code=None,
            error_message=None,
        )
        db.refresh(job)
        assert job.status == "FAILED"


def test_job_api_returns_active_attempt(client, app_and_session) -> None:
    _, factory = app_and_session
    now = utc_now()
    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            payload_json={"title": "实时模型调用"},
            current_step="GENERATE_AI_NOTE",
            lease_owner="worker:test",
            lease_expire_at=now + timedelta(seconds=90),
            heartbeat_at=now,
            started_at=now,
        )
        db.add(job)
        db.flush()
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="ollama",
                operation="note_reduce",
                status="RUNNING",
                request_meta_json={
                    "stage": "NOTE_REDUCE",
                    "step": "GENERATE_AI_NOTE",
                    "model": "qwen-test",
                    "route": "primary",
                    "chunk_index": 1,
                    "chunk_count": 2,
                    "timeout_seconds": 300,
                    "deadline_at": (now + timedelta(seconds=300)).isoformat(),
                    "run_fence": job_run_fence(job),
                },
                response_meta_json={},
            )
        )
        db.commit()
        job_id = job.id
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    active = response.json()["active_attempt"]
    assert active["status"] == "RUNNING"
    assert active["stage"] == "NOTE_REDUCE"
    assert active["chunk_index"] == 1
