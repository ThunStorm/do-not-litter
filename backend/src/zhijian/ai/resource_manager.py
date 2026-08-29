from collections.abc import Callable
from contextlib import contextmanager
from threading import Lock
from typing import TypeVar

T = TypeVar("T")


class LocalAIResourceManager:
    """Serialize GPU-heavy local ASR, text and vision work inside one process."""

    def __init__(self) -> None:
        # ponytail: process-global lock; use a shared lease only if multiple workers become supported.
        self._lock = Lock()
        self.active_kind: str | None = None

    @contextmanager
    def acquire(self, kind: str):
        with self._lock:
            self.active_kind = kind
            try:
                yield
            finally:
                self.active_kind = None

    def run(self, kind: str, call: Callable[[], T]) -> T:
        with self.acquire(kind):
            return call()


local_ai_resource_manager = LocalAIResourceManager()
