import fcntl
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
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
    def acquire(self, kind: str) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            self.active_kind = kind
            try:
                yield
            finally:
                self.active_kind = None
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def run(self, kind: str, call: Callable[[], T]) -> T:
        with self.acquire(kind):
            return call()


local_ai_resource_manager = LocalAIResourceManager()
