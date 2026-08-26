from __future__ import annotations

import time
from threading import Event, Thread

from zhijian import worker


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
