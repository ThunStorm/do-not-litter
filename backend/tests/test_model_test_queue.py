import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi import HTTPException

from zhijian.ai.model_test_queue import model_test_groups, queued_model_test
from zhijian.db.models import Job, Setting
from zhijian.services.jobs import lease_next_job
from zhijian.services.model_tests import enqueue_model_tests, lease_model_test, run_model_test


def profile(provider="DeepSeek", base="https://api.example.test/v1"):
    return {
        "name": "Fixture",
        "provider": provider,
        "base_url": base,
        "model": "fixture",
        "location": "REMOTE",
        "api_key": "must-not-enter-job",
    }


def hold_group(directory, entered, release):
    import os

    from zhijian.core.config import get_settings

    os.environ["ZHIJIAN_DATA_DIR"] = directory
    get_settings.cache_clear()
    with queued_model_test({"cross-process-fixture"}):
        entered.set()
        assert release.wait(5)


def test_supplier_or_entry_conflict_without_grouping_generic_adapters():
    first = model_test_groups(profile())
    assert first & model_test_groups(profile(base="https://another.fixture/v1"))
    assert first & model_test_groups(profile("Other", "https://API.EXAMPLE.TEST/v2/"))
    assert not model_test_groups(profile("OpenAI Compatible", "https://a.fixture/v1")) & model_test_groups(
        profile("OpenAI Compatible", "https://b.fixture/v1")
    )
    assert model_test_groups(profile()) == model_test_groups({**profile(), "api_key": "different-key"})
    assert model_test_groups(profile(base="https://example.test:bad"))


@pytest.mark.parametrize("first_interval,second_interval", [(0, 0), (11, 0), (0, 11)])
@pytest.mark.parametrize("failed", [False, True])
def test_local_direct_calls_wait_after_completion_across_models(
    monkeypatch, first_interval, second_interval, failed
):
    from types import SimpleNamespace

    import zhijian.ai.model_registry as registry
    import zhijian.ai.model_test_queue as queue
    from zhijian.ai.reliability import AIProviderError
    from zhijian.ai.schemas import ModelProfile

    clock, starts = [100.0], []
    monkeypatch.setattr(queue, "time", lambda: clock[0])
    monkeypatch.setattr(queue, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(registry.ReliabilityGuards, "acquire", lambda *_args, **_kwargs: (None, 0, 0))

    class Provider:
        # No Base URL: native local adapters must still obey the hardware gap.
        def generate_text(self, *_args, **_kwargs):
            starts.append(clock[0])
            clock[0] += 8
            if failed and len(starts) == 1:
                raise ValueError("fixture failed after loading")
            return SimpleNamespace(content="ok")

    for index, interval in enumerate([first_interval, second_interval]):
        value = {
            "id": str(index), "provider": f"local-adapter-{index}", "model": str(index),
            "location": "LOCAL", "reliability_mode": "DIRECT", "request_interval_seconds": interval,
            "base_url": f"http://local-fixture-{index}:1234",
        }
        with queued_model_test(model_test_groups(value)):
            if failed and index == 0:
                with pytest.raises(AIProviderError):
                    registry.invoke_profile_model(Provider(), ModelProfile(**value), "generate_text", [])
            else:
                registry.invoke_profile_model(Provider(), ModelProfile(**value), "generate_text", [])
    assert starts[1] - (starts[0] + 8) == max(5, first_interval, second_interval)


@pytest.mark.parametrize("provider,location", [("Ollama", "REMOTE"), ("custom-local", "LOCAL")])
def test_local_hardware_group_is_shared_across_providers_and_entries(provider, location):
    first = model_test_groups({**profile("Ollama", "http://a.fixture:11434"), "location": "LOCAL"})
    second = model_test_groups({**profile(provider, "http://b.fixture:10000"), "location": location})
    assert first & second


@pytest.mark.parametrize("saved", [False, True])
def test_local_probe_waiting_for_group_does_not_take_hardware_lock(
    app_and_session, monkeypatch, saved
):
    from types import SimpleNamespace

    import zhijian.ai.model_test_queue as queue
    import zhijian.api.router as api
    from zhijian.domain.schemas import ModelProfileConfig

    _, factory = app_and_session
    value = {**profile("ollama", "http://local.fixture:11434"), "location": "LOCAL"}
    groups = model_test_groups(value)
    if saved:
        with factory() as db:
            db.add(Setting(key="model-profile:a", value_json=value))
            db.commit()

    def probe(_provider, _profile, **kwargs):
        with queued_model_test(kwargs["groups"]):
            return {"FORMAT_SMOKE": "PASS"}

    monkeypatch.setattr(api, "probe_model_profile", probe)
    monkeypatch.setattr(api, "_model_profile_provider", lambda *_args: None)

    def request():
        if saved:
            with factory() as db:
                return api.probe_saved_model_profile("a", None, db, SimpleNamespace(get=lambda _key: None))
        return api.probe_model_profile_draft(ModelProfileConfig(**value), None)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with queued_model_test(groups):
            future = pool.submit(request)
            with queue._condition:
                assert queue._condition.wait_for(lambda: len(queue._tickets) == 2, timeout=2)
            # A Worker holding the group can still obtain the hardware lock:
            # the waiting API request must not hold it in the opposite order.
            assert api.local_ai_resource_manager._lock.acquire(timeout=0.2)
            api.local_ai_resource_manager._lock.release()
        assert future.result(timeout=2)["probe_results"]["FORMAT_SMOKE"] == "PASS"
    assert model_test_groups(profile(base="https://[invalid"))


@pytest.mark.parametrize("busy", [False, True])
def test_manual_request_respects_rpm_and_all_http429_cool_down(monkeypatch, busy):
    from types import SimpleNamespace

    import httpx

    from zhijian.ai.model_registry import invoke_profile_model, model_profile_from_value
    from zhijian.ai.reliability import AIProviderError
    from zhijian.providers.llm import LLMResult

    pacing = []
    monkeypatch.setattr(
        "zhijian.ai.model_registry.pace_model_test",
        lambda interval, cooldown=0: pacing.append((interval, cooldown)),
    )

    def generate(*_args, **_kwargs):
        if busy:
            request = httpx.Request("POST", "https://fixture.test")
            httpx.Response(429, request=request, json={"error": {"message": "busy_queue"}}).raise_for_status()
        return LLMResult("PONG", "fixture", "fixture", {})

    provider = SimpleNamespace(
        name="fixture", base_url="https://fixture.test", api_key="fixture", generate_text=generate
    )
    value = model_profile_from_value("fixture", {**profile(), "rate_limit_rpm": 5})
    if busy:
        with pytest.raises(AIProviderError):
            invoke_profile_model(provider, value, "generate_text", [])
        assert pacing[-1] == (0, 60)
    else:
        invoke_profile_model(provider, value, "generate_text", [])
        assert pacing == [(12, 0)]


def test_conflicting_fifo_does_not_block_independent_entry_and_failure_releases():
    entered, release, independent = Event(), Event(), Event()
    order = []

    def operation(index, groups):
        with queued_model_test(groups):
            order.append(index)
            if index == 0:
                entered.set()
                assert release.wait(3)
                raise ValueError("fixture failure")
            if index == 2:
                independent.set()

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(operation, 0, {"same"})
        assert entered.wait(2)
        second = pool.submit(operation, 1, {"same"})
        third = pool.submit(operation, 2, {"independent"})
        assert independent.wait(2)
        release.set()
        with pytest.raises(ValueError):
            first.result()
        second.result()
        third.result()
    assert order == [0, 2, 1]


def test_cross_process_group_is_serialized(tmp_path, monkeypatch):
    from zhijian.core.config import get_settings

    monkeypatch.setenv("ZHIJIAN_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    context = multiprocessing.get_context("spawn")
    entered, release = context.Event(), context.Event()
    child = context.Process(target=hold_group, args=(str(tmp_path), entered, release))
    child.start()
    try:
        assert entered.wait(3)
        with ThreadPoolExecutor(max_workers=1) as pool:

            def second():
                with queued_model_test({"cross-process-fixture"}):
                    return "done"

            future = pool.submit(second)
            with pytest.raises(TimeoutError):
                future.result(timeout=0.2)
            release.set()
            assert future.result(timeout=3) == "done"
    finally:
        release.set()
        child.join(timeout=3)
        if child.is_alive():
            child.terminate()
            child.join()
        get_settings.cache_clear()
    assert child.exitcode == 0


def test_worker_queue_deduplicates_and_leases_only_independent_groups(client, app_and_session):
    _, factory = app_and_session
    original_job_ids = {item["id"] for item in client.get("/api/jobs").json()}
    original_counts = client.get("/api/dashboard").json()["job_counts"]
    with factory() as db:
        db.add_all(
            [
                Setting(key="model-profile:a", value_json=profile()),
                Setting(key="model-profile:b", value_json=profile()),
                Setting(key="model-profile:c", value_json=profile("Other", "https://other.fixture")),
            ]
        )
        db.commit()
    queued = client.post("/api/settings/model-tests", json={"mode": "BOTH"})
    assert queued.status_code == 200
    assert len(queued.json()) == 3
    assert {x["status"] for x in queued.json()} == {"QUEUED"}
    repeated = client.post("/api/settings/model-tests", json={"profile_ids": ["a"], "mode": "TEST"})
    assert repeated.json()[0]["id"] == next(x["id"] for x in queued.json() if x["profile_id"] == "a")
    assert {item["id"] for item in client.get("/api/jobs").json()} == original_job_ids
    assert client.get("/api/dashboard").json()["job_counts"] == original_counts
    with factory() as db:
        assert db.query(Job).filter_by(job_type="MODEL_TEST").count() == 3
        assert "must-not-enter-job" not in str([j.payload_json for j in db.query(Job).all()])
        regular = lease_next_job(db, "regular-worker", 60)
        assert regular is None or regular.job_type != "MODEL_TEST"
        first = lease_model_test(db, "test-worker", 60, set())
        busy = set(first.payload_json["groups"])
        second = lease_model_test(db, "test-worker", 60, busy)
        assert first.payload_json["profile_id"] == "a"
        assert second.payload_json["profile_id"] == "c"
        assert lease_model_test(db, "test-worker", 60, busy | set(second.payload_json["groups"])) is None


def test_worker_persists_partial_result_and_next_model_is_independent(app_and_session, monkeypatch):
    _, factory = app_and_session
    monkeypatch.setattr(
        "zhijian.api.router.test_model_profile", lambda *_args: {"status": "READY", "message": "fixture"}
    )

    def probe(profile_id, *_args):
        if profile_id == "a":
            raise HTTPException(502, "AI_PROVIDER_BAD_REQUEST：fixture invalid request")
        return {"probe_results": {"GLOBAL_SYNTHESIS": "PASS"}}

    monkeypatch.setattr("zhijian.api.router.probe_saved_model_profile", probe)
    monkeypatch.setattr("zhijian.services.model_tests.build_secret_store", lambda *_args: None)
    with factory() as db:
        db.add_all(
            [
                Setting(key="model-profile:a", value_json=profile()),
                Setting(key="model-profile:b", value_json=profile()),
            ]
        )
        db.commit()
        enqueue_model_tests(db, None, "BOTH")
        first = lease_model_test(db, "owner", 60, set())
        first_id = first.id
    run_model_test(factory, first_id, 60)
    with factory() as db:
        failed = db.get(Job, first_id)
        assert failed.status == "FAILED" and failed.error_code == "AI_PROVIDER_BAD_REQUEST"
        assert failed.payload_json["test_results"]["TEST"]["status"] == "READY"
        assert failed.lease_owner is None
        second = lease_model_test(db, "owner", 60, set())
        second_id = second.id
    run_model_test(factory, second_id, 60)
    with factory() as db:
        assert db.get(Job, second_id).status == "COMPLETED"


def test_worker_initializes_real_secret_store(app_and_session, monkeypatch, tmp_path):
    from zhijian.core.config import Settings

    _, factory = app_and_session
    settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
    monkeypatch.setattr("zhijian.services.model_tests.get_settings", lambda: settings)

    def connection(_profile_id, _request, _db, store):
        store.set("worker-fixture", "fixture-secret")
        assert store.get("worker-fixture") == "fixture-secret"
        return {"status": "READY", "message": "fixture"}

    monkeypatch.setattr("zhijian.api.router.test_model_profile", connection)
    with factory() as db:
        db.add(Setting(key="model-profile:a", value_json=profile()))
        db.commit()
        enqueue_model_tests(db, ["a"], "TEST")
        job_id = lease_model_test(db, "owner", 60, set()).id
    run_model_test(factory, job_id, 60)
    with factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "COMPLETED", job.error
        assert "fixture-secret" not in str(job.payload_json)


def test_group_cooldown_is_shared_across_operations(tmp_path, monkeypatch):
    import zhijian.ai.model_test_queue as queue
    from zhijian.core.config import get_settings

    monkeypatch.setenv("ZHIJIAN_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    sleeps = []
    monkeypatch.setattr(queue, "sleep", sleeps.append)
    with queued_model_test({"cooldown"}):
        queue.pace_model_test(0, cooldown=60)
    with queued_model_test({"cooldown"}):
        queue.pace_model_test(4)
    assert sleeps and 59 < sleeps[0] <= 60
    get_settings.cache_clear()


def test_cancelled_waiter_does_not_release_another_operations_group():
    import zhijian.ai.model_test_queue as queue

    release, running, cancel = Event(), Event(), Event()

    def holder():
        with queued_model_test({"cancel-shared"}):
            running.set()
            assert release.wait(3)

    def check():
        if cancel.is_set():
            raise ValueError("cancelled fixture")

    def waiter():
        with queued_model_test({"cancel-shared"}, check):
            return True

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(holder)
        assert running.wait(2)
        second = pool.submit(waiter)
        with queue._condition:
            assert queue._condition.wait_for(lambda: len(queue._tickets) >= 2, timeout=2)
        cancel.set()
        with pytest.raises(ValueError):
            second.result(timeout=2)
        cancel.clear()
        third = pool.submit(waiter)
        with pytest.raises(TimeoutError):
            third.result(timeout=0.1)
        release.set()
        first.result(timeout=2)
        assert third.result(timeout=2)


def test_model_test_late_result_cannot_overwrite_new_run_fence(app_and_session, monkeypatch):
    from zhijian.core.time import utc_now

    _, factory = app_and_session
    with factory() as db:
        db.add(Setting(key="model-profile:a", value_json=profile()))
        db.commit()
        enqueue_model_tests(db, ["a"], "TEST")
        job_id = lease_model_test(db, "old-owner", 60, set()).id

    def late_response(*_args):
        with factory() as db:
            job = db.get(Job, job_id)
            job.lease_owner = "new-owner"
            job.retry_count = 1
            job.started_at = utc_now()
            db.commit()
        return {"status": "READY", "message": "fixture"}

    monkeypatch.setattr("zhijian.api.router.test_model_profile", late_response)
    monkeypatch.setattr("zhijian.services.model_tests.build_secret_store", lambda *_args: None)
    run_model_test(factory, job_id, 60)
    with factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "RUNNING" and job.lease_owner == "new-owner" and job.retry_count == 1
