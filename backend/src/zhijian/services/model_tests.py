"""Persistent manual model tests, executed in a bounded Worker lane."""

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event, Lock, Thread

from sqlalchemy import select, update

from zhijian.ai.job_config import profile_identity
from zhijian.ai.model_test_queue import model_test_groups, queued_model_test
from zhijian.core.config import get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.core.time import utc_now
from zhijian.db.models import Job, Setting
from zhijian.services.jobs import ensure_job_active, job_run_fence, renew_job_lease

_enqueue_lock = Lock()
MAX_PARALLEL = 3


def identity_hash(value):
    return hashlib.sha256(json.dumps(profile_identity(value)).encode()).hexdigest()


def test_job_view(job):
    payload = job.payload_json or {}
    return {
        "id": job.id,
        "profile_id": payload.get("profile_id"),
        "name": payload.get("name"),
        "mode": payload.get("mode"),
        "status": job.status,
        "phase": job.current_step,
        "progress": job.progress,
        "error": job.error,
        "error_code": job.error_code,
        "results": payload.get("test_results") or {},
    }


def enqueue_model_tests(db, profile_ids, mode):
    with _enqueue_lock:
        profiles = db.scalars(
            select(Setting).where(Setting.key.like("model-profile:%")).order_by(Setting.key)
        ).all()
        available = {row.key.removeprefix("model-profile:"): row.value_json for row in profiles}
        ids = list(dict.fromkeys(profile_ids if profile_ids is not None else available))
        if not ids or any(key not in available for key in ids):
            raise ValueError("请选择已保存的模型")
        active = db.scalars(
            select(Job).where(Job.job_type == "MODEL_TEST", Job.status.in_(["QUEUED", "RUNNING"]))
        ).all()
        jobs = []
        for profile_id in ids:
            value = available[profile_id]
            existing = next(
                (
                    job
                    for job in active
                    if job.payload_json.get("profile_id") == profile_id
                    and job.payload_json.get("mode")
                    in ({mode, "BOTH", "PROBE"} if mode == "INTERFACE" else {mode, "BOTH"})
                ),
                None,
            )
            if existing:
                jobs.append(existing)
                continue
            job = Job(
                job_type="MODEL_TEST",
                current_step="QUEUED",
                payload_json={
                    "profile_id": profile_id,
                    "name": value.get("name") or value.get("model"),
                    "mode": mode,
                    "identity_hash": identity_hash(value),
                    "groups": sorted(model_test_groups(value)),
                },
            )
            db.add(job)
            jobs.append(job)
            active.append(job)
        db.commit()
        return [test_job_view(job) for job in jobs]


def lease_model_test(db, owner, lease_seconds, busy):
    jobs = db.scalars(
        select(Job)
        .where(Job.job_type == "MODEL_TEST", Job.status == "QUEUED")
        .order_by(Job.created_at, Job.id)
    ).all()
    blocked = set(busy)
    for job in jobs:
        groups = set(job.payload_json.get("groups") or [])
        if groups & blocked:
            blocked.update(groups)
            continue
        now = utc_now()
        claimed = db.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == "QUEUED")
            .values(
                status="RUNNING",
                started_at=now,
                heartbeat_at=now,
                lease_owner=owner,
                lease_expire_at=now + timedelta(seconds=lease_seconds),
            )
        )
        db.commit()
        if claimed.rowcount:
            db.refresh(job)
            return job
    return None


def run_model_test(factory, job_id, lease_seconds):
    # Reuse the established test/probe handlers so capability persistence and
    # error redaction cannot diverge. They run here in Worker, not an HTTP request.
    from zhijian.api.router import probe_saved_interface, probe_saved_model_profile, test_model_profile

    with factory() as db:
        job = db.get(Job, job_id)
        fence = job_run_fence(job)
        stopped = Event()

        def heartbeat():
            while not stopped.wait(max(1, lease_seconds / 3)):
                with factory() as session:
                    if not renew_job_lease(session, job_id, fence, lease_seconds):
                        return

        thread = Thread(target=heartbeat, daemon=True)
        thread.start()
        results = {}
        try:
            payload = job.payload_json
            row = db.get(Setting, "model-profile:" + payload["profile_id"])
            if row is None or identity_hash(row.value_json) != payload["identity_hash"]:
                raise ValueError("模型身份已变化，请重新提交测试")
            settings = get_settings()
            store = build_secret_store(settings.secret_store, settings.data_dir)
            with queued_model_test(payload["groups"], lambda: ensure_job_active(db, job)):
                for phase in ["TEST", "PROBE"] if payload["mode"] == "BOTH" else [payload["mode"]]:
                    ensure_job_active(db, job)
                    job.current_step = phase
                    job.progress = 10 if phase == "TEST" else 50
                    db.commit()
                    if phase == "TEST":
                        result = test_model_profile(payload["profile_id"], None, db, store)
                        results[phase] = {"status": result["status"], "message": result["message"]}
                    elif phase == "INTERFACE":
                        result = probe_saved_interface(payload["profile_id"], db, store)
                        results[phase] = result
                    else:
                        result = probe_saved_model_profile(payload["profile_id"], None, db, store)
                        results[phase] = {
                            "probe_results": result["probe_results"],
                            "interface_probe": result.get("interface_probe"),
                        }
                    ensure_job_active(db, job)
                    job.payload_json = {**job.payload_json, "test_results": dict(results)}
                    db.commit()
            job.status, job.progress, job.current_step = "COMPLETED", 100, "COMPLETED"
        except Exception as exc:
            from zhijian.providers.llm import provider_error_details
            from zhijian.services.jobs import JobCancelled

            db.rollback()
            db.refresh(job)
            if isinstance(exc, JobCancelled) or job.status == "CANCELLED":
                if job.status == "RUNNING" and job_run_fence(job) == fence:
                    job.status = "CANCELLED"
            else:
                detail = getattr(exc, "detail", None)
                details = provider_error_details(exc)
                job.status = "FAILED"
                job.error = str(detail or details["message"])[:500]
                code = re.search(r"AI_PROVIDER_[A-Z_]+", job.error)
                job.error_code = code.group() if code else "MODEL_TEST_FAILED"
        finally:
            stopped.set()
            thread.join(timeout=1)
            if job_run_fence(job) == fence:
                job.finished_at = job.finished_at or utc_now()
                job.lease_owner = job.lease_expire_at = None
                db.commit()
            else:
                db.rollback()


def model_test_worker_loop(factory, owner, settings, stopped):
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL, thread_name_prefix="model-test") as pool:
        running = {}
        while not stopped.is_set():
            from zhijian.core.storage import read_json

            if read_json(settings.storage_config.with_name("maintenance-state.json")).get("stage") in {
                "COPYING",
                "SWITCHED",
                "VERIFYING",
                "FAILED",
            }:
                stopped.wait(0.5)
                continue
            for future in list(running):
                if future.done():
                    try:
                        future.result()
                    except Exception:
                        import logging

                        logging.getLogger("zhijian.worker").exception("Model test lane failed")
                    del running[future]
            busy = set().union(*running.values()) if running else set()
            while len(running) < MAX_PARALLEL:
                with factory() as db:
                    job = lease_model_test(db, owner, settings.worker_lease_seconds, busy)
                    if job is None:
                        break
                    groups = set(job.payload_json["groups"])
                    future = pool.submit(run_model_test, factory, job.id, settings.worker_lease_seconds)
                    running[future] = groups
                    busy.update(groups)
            stopped.wait(0.5)
