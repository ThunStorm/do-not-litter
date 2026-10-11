"""Manual tests: FIFO for overlapping supplier/entry groups, independent lanes."""

import fcntl
import hashlib
import json
from collections import deque
from contextlib import ExitStack, contextmanager
from threading import Condition, local
from time import sleep, time
from urllib.parse import urlsplit

from zhijian.core.config import get_settings

_condition = Condition()
_tickets = deque()
_active = set()
_state = local()


def uses_local_model_hardware(value: dict) -> bool:
    return value.get("location") == "LOCAL" or str(value.get("provider") or "").strip().lower() == "ollama"


def model_test_groups(value: dict) -> frozenset[str]:
    raw = str(value.get("base_url") or "")
    try:
        endpoint = urlsplit(raw)
        port = endpoint.port or (443 if endpoint.scheme == "https" else 80)
        origin = f"{endpoint.scheme.lower()}://{(endpoint.hostname or '').lower()}:{port}"
    except ValueError:
        origin = f"invalid:{raw}"
    provider = str(value.get("provider") or "").lower().replace(" ", "").replace("-", "")
    groups = {f"entry:{origin}"} if raw else {"legacy"}
    if provider and provider not in {"openaicompatible", "localmux", "localaimux"}:
        groups.add(f"supplier:{provider}")
    if uses_local_model_hardware(value):
        groups.add("hardware:local")
    return frozenset(hashlib.sha256(group.encode()).hexdigest() for group in groups)


@contextmanager
def queued_model_test(groups=None, cancel_check=None):
    groups = frozenset(groups or {"legacy"})
    if getattr(_state, "groups", None):
        if not groups <= _state.groups:
            raise RuntimeError("嵌套测试不可切换供应商或入口")
        yield
        return
    ticket = (object(), groups)
    with _condition:
        _tickets.append(ticket)
        _condition.notify_all()
    reserved = False
    try:
        with _condition:
            while True:
                if cancel_check:
                    cancel_check()
                earlier = list(_tickets)[: list(_tickets).index(ticket)]
                if not groups & _active and not any(groups & item[1] for item in earlier):
                    _active.update(groups)
                    reserved = True
                    break
                _condition.wait(0.25)
        with ExitStack() as stack:
            handles = {}
            directory = get_settings().data_dir / "runtime" / "model-tests"
            directory.mkdir(parents=True, exist_ok=True)
            for group in sorted(groups):
                handle = stack.enter_context((directory / f"{group}.lock").open("a+"))
                while True:
                    if cancel_check:
                        cancel_check()
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        sleep(0.25)
                handles[group] = handle
            _state.groups, _state.handles, _state.cancel_check = groups, handles, cancel_check
            try:
                yield
            finally:
                _state.groups, _state.handles, _state.cancel_check = None, {}, None
    finally:
        with _condition:
            _tickets.remove(ticket)
            if reserved:
                _active.difference_update(groups)
            _condition.notify_all()


def pace_model_test(interval: float, cooldown: float = 0, *, finished: bool = False) -> None:
    handles = getattr(_state, "handles", {})
    if not handles:
        return
    records = []
    for handle in handles.values():
        handle.seek(0)
        try:
            records.append(json.loads(handle.read() or "{}"))
        except ValueError:
            records.append({})
    deadline = max(
        (max(float(row.get("next_at", 0)), float(row.get("finished_at", 0)) + interval) for row in records),
        default=0,
    )
    if not cooldown:
        remaining = max(0, deadline - time())
        check = getattr(_state, "cancel_check", None)
        if check:
            while remaining > 0:
                check()
                sleep(min(0.25, remaining))
                remaining = max(0, deadline - time())
        elif remaining:
            sleep(remaining)
    next_at = max(deadline, time() + (cooldown or interval))
    for handle, row in zip(handles.values(), records, strict=True):
        handle.seek(0)
        handle.truncate()
        record = {"next_at": next_at}
        if finished or row.get("finished_at"):
            record["finished_at"] = time() if finished else row["finished_at"]
        json.dump(record, handle)
        handle.flush()


def model_test_cancel_check():
    return getattr(_state, "cancel_check", None)
