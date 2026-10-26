"""Closed immutable log volumes, verified gzip and bounded retention. Never touch active files."""

from __future__ import annotations

import gzip
import json
import logging
import os
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from zhijian.core.storage import atomic_json, digest, gated, maintenance_lock, read_json


class LogPolicy(BaseModel):
    version: int = 1
    compress: bool = True
    compression_delay_hours: int = Field(default=48, ge=1, le=8760)
    retention_days: int = Field(default=30, ge=1, le=3650)
    volume_bytes: int = Field(default=10 * 1024**2, ge=64 * 1024, le=100 * 1024**2)
    capacity_bytes: int = Field(default=1024**3, ge=1024**2, le=100 * 1024**3)
    bootstrap_retention_days: int = Field(default=7, ge=1, le=3650)
    bootstrap_capacity_bytes: int = Field(default=128 * 1024**2, ge=1024**2, le=1024**3)
    low_space_bytes: int = Field(default=1024**3, ge=0, le=100 * 1024**3)

    @model_validator(mode="after")
    def validate_window(self):
        if self.compression_delay_hours >= min(self.retention_days, self.bootstrap_retention_days) * 24:
            raise ValueError("压缩延迟必须小于两类日志的总保留期")
        return self


def load_policy(control):
    return LogPolicy.model_validate(read_json(Path(control).with_name("log-policy.json")) or {})


class SealedLogHandler(logging.FileHandler):
    def __init__(self, root, service, control):
        self.log_root, self.service, self.control = Path(root), service, Path(control)
        self.active = self.log_root / "active" / f"{service}.log"
        self.active.parent.mkdir(parents=True, exist_ok=True)
        (self.log_root / "archive").mkdir(parents=True, exist_ok=True)
        self.active_state = self.active.with_suffix(".state.json")
        opened = read_json(self.active_state).get("opened_day")
        self.open_day = datetime.fromisoformat(opened).date() if opened else datetime.now(UTC).date()
        if not opened:
            atomic_json(self.active_state, {"opened_day": self.open_day.isoformat()})
        self.policy_loaded = 0.0
        self.policy = LogPolicy()
        super().__init__(self.active, encoding="utf-8")

    def emit(self, record):
        try:
            if time.monotonic() - self.policy_loaded > 5:
                self.policy = load_policy(self.control)
                self.policy_loaded = time.monotonic()
            if self.stream.tell() >= self.policy.volume_bytes or self.open_day != datetime.now(UTC).date():
                try:
                    with maintenance_lock(self.control):
                        if not gated(self.control):
                            self.seal()
                except OSError:
                    if self.stream is None or self.stream.closed:
                        self.stream = self._open()
            super().emit(record)
        except Exception:
            self.handleError(record)

    def seal(self):
        self.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        now = datetime.now(UTC)
        target = (
            self.log_root
            / "archive"
            / f"{self.service}-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex}.log"
        )
        try:
            os.replace(self.active, target)
        finally:
            self.stream = self._open()
        atomic_json(
            str(target) + ".meta.json",
            {
                "service": self.service,
                "closed_at": now.timestamp(),
                "original_bytes": target.stat().st_size,
                "sha256": digest(target),
                "policy_version": self.policy.version,
                "filename": target.name,
            },
        )
        self.open_day = now.date()
        atomic_json(self.active_state, {"opened_day": self.open_day.isoformat()})


def volumes(root):
    archive = Path(root) / "archive"
    result = []
    if archive.exists():
        for path in archive.glob("*.meta.json"):
            meta = read_json(path)
            name = meta.get("filename", "")
            if not name or Path(name).name != name:
                continue
            file = archive / name
            if file.is_file() and not file.is_symlink():
                result.append({**meta, "index": str(path), "path": str(file), "bytes": file.stat().st_size})
    return sorted(result, key=lambda v: (v["closed_at"], v["filename"]))


def preview(root, policy, *, now=None):
    now = time.time() if now is None else now
    rows = volumes(root)
    candidates, remaining = [], []
    for group in ("application", "bootstrap"):
        group_rows = [
            r
            for r in rows
            if (r["service"].startswith("stdio-") or r["service"].startswith("boot-"))
            == (group == "bootstrap")
        ]
        days = policy.retention_days if group == "application" else policy.bootstrap_retention_days
        capacity = policy.capacity_bytes if group == "application" else policy.bootstrap_capacity_bytes
        total = sum(r["bytes"] for r in group_rows)
        for r in group_rows:
            reason = (
                "EXPIRED"
                if now - r["closed_at"] >= days * 86400
                else "CAPACITY"
                if total > capacity
                else None
            )
            if reason:
                candidates.append({**r, "reason": reason})
                total -= r["bytes"]
            else:
                remaining.append(r)
    import hashlib

    token = hashlib.sha256(
        json.dumps(
            {"rows": rows, "policy": policy.model_dump(), "delete_paths": [r["path"] for r in candidates]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return {
        "token": token,
        "delete_count": len(candidates),
        "delete_bytes": sum(r["bytes"] for r in candidates),
        "candidates": candidates,
        "oldest_closed_at": min((r["closed_at"] for r in remaining), default=None),
        "archived_bytes": sum(r["bytes"] for r in rows),
    }


def compress_volume(row):
    source = Path(row["path"])
    if source.suffix == ".gz":
        return False
    target, temporary = Path(str(source) + ".gz"), Path(str(source) + ".gz.tmp")
    if temporary.is_symlink() or target.is_symlink():
        raise ValueError("归档临时文件不能为符号链接")
    try:
        with source.open("rb") as src, temporary.open("wb") as output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as archive:
                import shutil

                shutil.copyfileobj(src, archive, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        import hashlib

        with gzip.open(temporary, "rb") as check:
            actual = hashlib.file_digest(check, "sha256").hexdigest()
        if actual != row["sha256"]:
            raise ValueError("压缩完整性校验失败")
        os.replace(temporary, target)
        atomic_json(
            row["index"],
            {
                k: v
                for k, v in {
                    **row,
                    "filename": target.name,
                    "compressed_bytes": target.stat().st_size,
                }.items()
                if k not in {"path", "index", "bytes", "reason"}
            },
        )
        source.unlink()
        return True
    finally:
        temporary.unlink(missing_ok=True)


def recover_volumes(root):
    """Recover crash windows after seal rename and after gzip index commit."""
    archive = Path(root) / "archive"
    for path in archive.glob("*.log"):
        if path.is_symlink():
            continue
        index = Path(str(path) + ".meta.json")
        if index.exists():
            meta = read_json(index)
            if meta.get("filename") == path.name + ".gz":
                compressed = Path(str(path) + ".gz")
                import hashlib

                with gzip.open(compressed, "rb") as stream:
                    valid = hashlib.file_digest(stream, "sha256").hexdigest() == meta["sha256"]
                if not valid or digest(path) != meta["sha256"]:
                    raise ValueError("恢复归档哈希不一致，保留两份文件")
                path.unlink()
            continue
        match = re.match(r"^(?P<service>.+)-(?P<at>\d{8}T\d{12}Z)-[0-9a-f]{32}\.log$", path.name)
        if not match:
            continue  # Unknown ownership is preserved, never inferred from mtime.
        closed = datetime.strptime(match["at"], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC).timestamp()
        atomic_json(
            index,
            {
                "service": match["service"],
                "closed_at": closed,
                "original_bytes": path.stat().st_size,
                "sha256": digest(path),
                "policy_version": 1,
                "filename": path.name,
            },
        )


def maintain(root, control, *, policy=None, now=None, limit=16, seconds=5):
    now = time.time() if now is None else now
    started = time.monotonic()
    result = {"compressed": 0, "deleted": 0, "errors": [], "at": now, "root": str(root)}
    with maintenance_lock(control):
        if gated(control):
            return {**result, "paused": True}
        recover_volumes(root)
        policy = policy or load_policy(control)
        plan = preview(root, policy, now=now)
        delete_paths = {r["path"] for r in plan["candidates"]}
        work = [
            row
            for row in volumes(root)
            if row["path"] in delete_paths
            or (
                policy.compress
                and not row["filename"].endswith(".gz")
                and now - row["closed_at"] >= policy.compression_delay_hours * 3600
            )
        ]
        for row in work[:limit]:
            if time.monotonic() - started >= seconds:
                break
            try:
                if row["path"] in delete_paths:
                    Path(row["path"]).unlink()
                    Path(row["index"]).unlink()
                    result["deleted"] += 1
                elif policy.compress and now - row["closed_at"] >= policy.compression_delay_hours * 3600:
                    result["compressed"] += int(compress_volume(row))
            except (OSError, ValueError):
                result["errors"].append("LOG_ARCHIVE_IO_OR_INTEGRITY")
        result["pending"] = max(0, len(work) - limit)
        import shutil

        result["low_space"] = shutil.disk_usage(root).free < policy.low_space_bytes
        result["policy_version"] = policy.version
        summary = Path(control).with_name("log-maintenance.json")
        previous = read_json(summary)
        atomic_json(summary, {**result, "runs": {**previous.get("runs", {}), str(root): result}})
    return result
