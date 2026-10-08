import asyncio
import fcntl
import os
import sys
from time import perf_counter

import httpx
import pytest

from zhijian.ai.budget import _budget_tokens
from zhijian.ai.resource_manager import LocalAIResourceManager
from zhijian.ai.token_usage import token_usage
from zhijian.db.models import ExternalCallAudit, Job
from zhijian.providers.asr import _run_process
from zhijian.providers.llm import FallbackLLMProvider, LLMResult, OpenAICompatibleProvider
from zhijian.services.external_audit import audited_call
from zhijian.services.jobs import JobCancelled, ensure_job_active


def test_usage_keeps_reported_zero_and_estimates_only_missing_fields():
    counts = token_usage({"prompt_tokens": 0, "completion_tokens": 2}, 100)
    assert counts["input_tokens"] == 0 and counts["estimated_input_calls"] == 0
    partial = token_usage({"prompt_tokens": 10, "content_length": 101}, 1000)
    assert partial["input_tokens"] == 10 and partial["estimated_output_tokens"] == 51
    unknown = token_usage({"usage_source": "UNKNOWN", "prompt_tokens": 0}, 100)
    assert unknown["estimated_input_tokens"] == 50 and unknown["unknown_output_calls"] == 1


def test_usage_http_estimates_history_without_rewriting_audits(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="COMPLETED", payload_json={})
        db.add(job)
        db.flush()
        for response, request in [
            ({"prompt_tokens": 10, "completion_tokens": 2}, {}),
            ({"usage_source": "UNKNOWN", "content_length": 40}, {"input_chars": 100}),
            ({}, {"input_chars": 80}),
            ({"prompt_tokens": 999, "completion_tokens": 999}, {"cache_hit": True}),
        ]:
            db.add(ExternalCallAudit(job_id=job.id, capability="LLM", provider="test",
                                     operation="test", status="COMPLETED",
                                     request_meta_json=request, response_meta_json=response))
        db.commit()
        job_id = job.id
    total = client.get(f"/api/jobs/{job_id}/ai-usage").json()["total"]
    assert total["input_tokens"] == 10 and total["output_tokens"] == 2
    assert total["estimated_input_tokens"] == 90 and total["estimated_output_tokens"] == 20
    assert total["unknown_output_calls"] == 1 and total["calls"] == 3
    with factory() as db:
        rows = db.query(ExternalCallAudit).filter_by(job_id=job_id).all()
        historical = next(row for row in rows if row.response_meta_json.get("content_length") == 40)
        assert historical.response_meta_json == {"usage_source": "UNKNOWN", "content_length": 40}
        failed = next(row for row in rows if row.request_meta_json.get("input_chars") == 80)
        assert _budget_tokens(failed, "prompt") == 40


@pytest.mark.parametrize("connection_type", ["DIRECT", "LOCAL_ROUTER"])
def test_http_cancellation_closes_waiting_request(monkeypatch, connection_type):
    cancelled = []
    original_client = httpx.AsyncClient

    async def handler(request):
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    provider = OpenAICompatibleProvider(
        "test", "https://test.invalid/v1", "dummy", timeout=60,
        connection_type=connection_type,
        interface_capabilities={
            "model": "test", "base_url": "https://test.invalid/v1", "sampled_at": "2026-10-08"
        } if connection_type == "LOCAL_ROUTER" else None,
    )
    checks = []

    def check():
        checks.append(True)
        if len(checks) >= 3:
            raise JobCancelled("cancelled")

    provider.cancel_check = check
    started = perf_counter()
    with pytest.raises(JobCancelled):
        provider.generate_json([{"role": "user", "content": "test"}], model="test")
    assert perf_counter() - started < 2 and cancelled == [True]


def test_timeout_skips_same_model_retry_but_uses_allowed_fallback():
    calls = []

    class Provider:
        def __init__(self, name):
            self.name = name

        def generate_json(self, messages, *, model):
            calls.append(model)
            if self.name == "primary":
                raise httpx.ReadTimeout("timeout")
            return LLMResult('{"ok":true}', self.name, model, {})

    provider = FallbackLLMProvider(Provider("primary"), "slow", Provider("fallback"), "fast",
                                   retry_count=3, sleeper=lambda seconds: None)
    assert provider.generate_json([], model="slow").provider == "fallback"
    assert calls == ["slow", "fast"]


def test_asr_cancellation_reaps_subprocess(tmp_path):
    pid_file = tmp_path / "pid"

    def check():
        if pid_file.exists():
            raise JobCancelled("cancelled")

    started = perf_counter()
    with pytest.raises(JobCancelled):
        _run_process([sys.executable, "-c",
                      "import os,time,pathlib,sys;"
                      "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));"
                      "time.sleep(60)", str(pid_file)], timeout=60, cancel_check=check)
    assert perf_counter() - started < 3
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_cancellation_guard_rejects_old_run_after_requeue(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", lease_owner="worker", retry_count=1, payload_json={})
        db.add(job)
        db.commit()
        job_id = job.id
        with factory() as other:
            other.get(Job, job_id).retry_count = 2
            other.commit()
        with pytest.raises(JobCancelled):
            ensure_job_active(db, job)


def test_request_interval_can_be_cancelled_before_call():
    checks = []
    intervals = []

    def check():
        checks.append(True)
        if len(checks) >= 3:
            raise JobCancelled("cancelled")

    class Provider:
        def generate_json(self, messages, *, model):
            pytest.fail("cancelled wait must not send a request")

    provider = FallbackLLMProvider(Provider(), "test", None, None, request_interval_seconds=10,
                                   sleeper=intervals.append)
    provider.cancel_check = check
    with pytest.raises(JobCancelled):
        provider.generate_json([], model="test")
    assert intervals == [0.25, 0.25]


def test_asr_wait_reports_activity_and_cancellation_is_not_provider_failure(monkeypatch, app_and_session):
    from zhijian.providers import asr

    times = iter(range(0, 1000, 11))
    monkeypatch.setattr(asr, "monotonic", lambda: next(times))
    waits = []

    def on_wait(seconds):
        waits.append(seconds)
        raise JobCancelled("cancelled")

    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="CANCELLED", payload_json={})
        db.add(job)
        db.commit()
        with pytest.raises(JobCancelled):
            audited_call(db, job_id=job.id, capability="ASR", provider="test", operation="transcribe",
                         request_meta={}, call=lambda: _run_process(
                             [sys.executable, "-c", "import time;time.sleep(60)"], timeout=300,
                             cancel_check=lambda: None, on_wait=on_wait,
                         ))
        assert waits and waits[0] >= 30
        assert db.query(ExternalCallAudit).filter_by(job_id=job.id).one().status == "CANCELLED"


@pytest.mark.parametrize("lock_kind", ["thread", "process"])
def test_waiting_local_resource_lock_can_be_cancelled(tmp_path, lock_kind):
    path = tmp_path / "lock"
    manager = LocalAIResourceManager(path)
    checks = []

    def check():
        checks.append(True)
        if len(checks) >= 3:
            raise JobCancelled("cancelled")

    with path.open("a+") as handle:
        if lock_kind == "thread":
            manager._lock.acquire()
        else:
            fcntl.flock(handle, fcntl.LOCK_EX)
        started = perf_counter()
        try:
            with pytest.raises(JobCancelled):
                manager.run(
                    "ASR", lambda: pytest.fail("cancelled waiter acquired resource"), cancel_check=check
                )
        finally:
            if lock_kind == "thread":
                manager._lock.release()
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
    assert perf_counter() - started < 2
    assert manager.run("ASR", lambda: "released") == "released"
