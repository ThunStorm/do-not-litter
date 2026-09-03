import multiprocessing
import os
from pathlib import Path

from zhijian.ai.resource_manager import LocalAIResourceManager


def _hold_lock(lock_path: str, acquired, release) -> None:
    with LocalAIResourceManager(Path(lock_path)).acquire("ASR"):
        acquired.set()
        release.wait(5)


def _acquire_lock(lock_path: str, acquired) -> None:
    with LocalAIResourceManager(Path(lock_path)).acquire("MODEL_TEST"):
        acquired.set()


def _exit_while_holding(lock_path: str, acquired) -> None:
    with LocalAIResourceManager(Path(lock_path)).acquire("ASR"):
        acquired.set()
        os._exit(0)


def test_local_ai_resource_manager_marks_and_releases_heavy_work() -> None:
    manager = LocalAIResourceManager()
    assert manager.run("ASR", lambda: manager.active_kind) == "ASR"
    assert manager.active_kind is None


def test_resource_lease_serializes_processes(tmp_path) -> None:
    lock_path = tmp_path / "local-ai.lock"
    held, release, waited = multiprocessing.Event(), multiprocessing.Event(), multiprocessing.Event()
    owner = multiprocessing.Process(target=_hold_lock, args=(str(lock_path), held, release))
    waiter = multiprocessing.Process(target=_acquire_lock, args=(str(lock_path), waited))
    owner.start()
    assert held.wait(3)
    waiter.start()
    assert not waited.wait(0.2)
    release.set()
    assert waited.wait(3)
    owner.join(3)
    waiter.join(3)
    assert owner.exitcode == waiter.exitcode == 0


def test_resource_lease_releases_after_process_exit(tmp_path) -> None:
    lock_path = tmp_path / "local-ai.lock"
    held = multiprocessing.Event()
    owner = multiprocessing.Process(target=_exit_while_holding, args=(str(lock_path), held))
    owner.start()
    assert held.wait(3)
    owner.join(3)
    assert owner.exitcode == 0
    assert LocalAIResourceManager(lock_path).run("MODEL_TEST", lambda: "released") == "released"
