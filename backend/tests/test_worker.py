from __future__ import annotations

import time
from threading import Event, Thread

from zhijian import worker
from zhijian.db.models import Job, SystemEvent


def test_worker_heartbeat_runs_independently_of_job_loop(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(worker, "_persist_worker_heartbeat", calls.append)
    stopped = Event()
    thread = Thread(target=worker._heartbeat_loop, args=("worker:test", 0.01, stopped))
    thread.start()
    deadline = time.monotonic() + 0.2
    while len(calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.005)
    stopped.set()
    thread.join(timeout=1)
    assert calls.count("worker:test") >= 2


def test_unhandled_worker_error_fails_and_releases_job(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            current_step="RECEIVED",
            lease_owner="worker:test",
            payload_json={"title": "异常兜底"},
        )
        db.add(job)
        db.commit()
        job_id = job.id
        worker._fail_unhandled_job(db, job_id, PermissionError("video_pipeline.py"))
        db.refresh(job)
        assert job.status == "FAILED"
        assert job.error_code == "WORKER_UNHANDLED_EXCEPTION"
        assert job.lease_owner is None
        event = db.query(SystemEvent).filter_by(entity_id=job_id).one()
        assert event.event_type == "job.worker.unhandled_exception"
