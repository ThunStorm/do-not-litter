import fcntl
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from time import sleep
from typing import TypeVar

T = TypeVar("T")


class LocalAIResourceManager:
    """Serialize GPU-heavy local ASR, text and vision work across processes."""

    def __init__(self, lock_path: Path | None = None) -> None:
        self._lock = Lock()
        data_dir = Path(os.environ.get("ZHIJIAN_DATA_DIR", "./data"))
        self.lock_path = lock_path or data_dir / "runtime" / "local-ai.lock"
        self.active_kind: str | None = None

    @contextmanager
    def acquire(self, kind: str, cancel_check: Callable[[], None] | None = None) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if cancel_check:
            cancel_check()
            while not self._lock.acquire(timeout=0.25):
                cancel_check()
        else:
            self._lock.acquire()
        try:
            with self.lock_path.open("a+") as handle:
                if cancel_check:
                    while True:
                        cancel_check()
                        try:
                            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            break
                        except BlockingIOError:
                            sleep(0.25)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                self.active_kind = kind
                try:
                    if cancel_check:
                        cancel_check()
                    yield
                finally:
                    self.active_kind = None
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock.release()

    def run(self, kind: str, call: Callable[[], T], *, cancel_check: Callable[[], None] | None = None) -> T:
        with self.acquire(kind, cancel_check):
            return call()


local_ai_resource_manager = LocalAIResourceManager()
