"""Storage bootstrap and managed references. No database import: safe before opening SQLite."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

DEFAULT_CONTROL = Path.home() / "Library/Application Support/Zhijian/storage.json"
MARKER = ".zhijian-instance.json"
CATEGORIES = ("permanent", "cache", "models", "logs", "browser", "secrets", "maintenance")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {} if default is None else default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".storage-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(tmp).unlink(missing_ok=True)


@contextmanager
def maintenance_lock(control, *, blocking=False):
    path = Path(control).parent / "maintenance.lock"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def gated(control):
    return read_json(Path(control).with_name("maintenance-state.json")).get("stage") in {
        "DRAINING",
        "COPYING",
        "SWITCHED",
        "VERIFYING",
        "FAILED",
    }


def validate_root(config):
    root = Path(config["root"])
    # st_dev + inode distinguish missing/replaced mounts and empty directories at the same path.
    if not root.is_dir() or root.is_symlink():
        raise ValueError("数据卷或根目录缺失；拒绝建立新空库")
    stat = root.stat()
    marker = read_json(root / MARKER)
    if (
        marker.get("instance_id") != config["instance_id"]
        or [stat.st_dev, stat.st_ino] != config["root_identity"]
    ):
        raise ValueError("数据卷/实例标记不匹配")
    if not (root / "app.db").is_file():
        raise ValueError("既有实例数据库缺失；拒绝建立新空库")
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        raise ValueError("数据目录不可读写")
    return root


def adopt(root, control):
    root, control = Path(root).resolve(), Path(control)
    if control.exists():
        config = read_json(control)
        if validate_root(config) != root:
            raise ValueError("已绑定其他根目录")
        return config
    if not (root / "app.db").is_file():
        raise ValueError("只能登记已有实例；新实例请显式 init")
    marker = read_json(root / MARKER) or {"instance_id": uuid.uuid4().hex}
    atomic_json(root / MARKER, marker)
    stat = root.stat()
    config = {
        "version": 1,
        "generation": 1,
        "root": str(root),
        "instance_id": marker["instance_id"],
        "root_identity": [stat.st_dev, stat.st_ino],
        "old_roots": [],
    }
    atomic_json(control, config)
    return config


def resolve_ref(value, settings, *, owned=True):
    root = settings.data_dir.resolve()
    path = Path(str(value))
    if ".." in path.parts:
        raise ValueError("拒绝非规范存储引用")
    if str(value).startswith("storage:"):
        path = root / str(value)[8:]
    elif not path.is_absolute():
        path = root / path
    if path.is_absolute() and not path.is_relative_to(root):
        config = read_json(settings.storage_config)
        for old in config.get("old_roots", []):
            if path.is_relative_to(Path(old)):
                path = root / path.relative_to(Path(old))
                break
    if (owned or path.is_relative_to(root)) and (
        not path.resolve().is_relative_to(root)
        or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent)
    ):
        raise ValueError("受管路径逃逸或符号链接")
    return path


def storage_ref(path, settings):
    return "storage:" + str(resolve_ref(path, settings).relative_to(settings.data_dir.resolve()))


def preflight(root, target):
    root, target = Path(root).resolve(), Path(target).expanduser()
    if not target.is_absolute() or ".." in target.parts or target.is_symlink():
        raise ValueError("目标必须是服务端绝对规范路径")
    target = target.resolve()
    if root == target or root.is_relative_to(target) or target.is_relative_to(root):
        raise ValueError("源目标不能相同或相互嵌套")
    if target.exists() and any(target.iterdir()):
        raise ValueError("目标必须是专用空目录")
    parent = target.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise ValueError("目标父目录不存在或不可写")
    # Reject known network/cloud locations. CLI also checks filesystem type on macOS.
    if any(part in {"Mobile Documents", "CloudStorage", "Dropbox", "OneDrive"} for part in target.parts):
        raise ValueError("不支持云同步目录")
    filesystem = "local-test"
    if sys.platform == "darwin":
        mounts = subprocess.run(["/sbin/mount"], check=True, text=True, capture_output=True, timeout=5).stdout
        matching = []
        for line in mounts.splitlines():
            match = re.match(r".+ on (.+) \(([^)]+)\)$", line)
            if match and parent.is_relative_to(Path(match[1])):
                matching.append((len(match[1]), match[2].split(", ")))
        options = max(matching, default=(0, []))[1]
        filesystem = options[0] if options else "unknown"
        if filesystem not in {"apfs", "hfs"} or "local" not in options:
            raise ValueError("仅支持已验证的本机APFS/HFS卷；拒绝网络/未验证文件系统")
    fd, probe = tempfile.mkstemp(prefix=".zhijian-probe-", dir=parent)
    os.close(fd)
    renamed = Path(probe + ".renamed")
    try:
        os.replace(probe, renamed)
        with renamed.open("r+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        Path(probe).unlink(missing_ok=True)
        renamed.unlink(missing_ok=True)
    return {
        "root": str(root),
        "target": str(target),
        "free_bytes": shutil.disk_usage(parent).free,
        "filesystem": filesystem,
    }


def inventory(root):
    root = Path(root)
    files, sizes = {}, {}
    for category in CATEGORIES:
        base = root / category
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"受管目录含符号链接：{path.relative_to(root)}")
            if not path.is_file():
                continue
            if "cookie" in path.name.lower() or path.suffix == ".lock":
                continue
            relative = str(path.relative_to(root))
            files[relative] = {"bytes": path.stat().st_size, "sha256": digest(path)}
            sizes[category] = sizes.get(category, 0) + path.stat().st_size
    return {"files": files, "categories": sizes, "total_bytes": sum(sizes.values())}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def database_check(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("数据库完整性失败")


def require_idle(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if (
            "jobs" in tables
            and db.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING') OR lease_owner IS NOT NULL"
            ).fetchone()[0]
        ):
            raise ValueError("仍有活跃任务/租约，等待自然结束")
        if (
            "external_call_audits" in tables
            and db.execute("SELECT count(*) FROM external_call_audits WHERE status='RUNNING'").fetchone()[0]
        ):
            raise ValueError("仍有在途外部调用")
        if (
            "model_test_runs" in tables
            and db.execute(
                "SELECT count(*) FROM model_test_runs WHERE status IN ('QUEUED','RUNNING')"
            ).fetchone()[0]
        ):
            raise ValueError("仍有模型测试")


def validate_references(dbpath, old_root, new_root, old_roots=()):
    """Inspect only technical path fields; never change source locators, text or Evidence."""
    old_root, new_root = Path(old_root), Path(new_root)
    unknown = []
    with sqlite3.connect(f"file:{dbpath}?mode=ro", uri=True) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, fields in {
            "snapshots": ["raw_path"],
            "video_screenshots": ["image_path"],
            "video_cover_assets": ["derivative_path"],
            "job_step_artifacts": ["artifact_ref_json"],
        }.items():
            if table not in tables:
                continue
            for field in fields:
                for (value,) in db.execute(f'SELECT "{field}" FROM "{table}"'):
                    if field.endswith("json"):
                        value = json.loads(value or "{}").get("cache_path")
                    if not value:
                        continue
                    p = Path(str(value))
                    if str(value).startswith("storage:"):
                        p = new_root / str(value)[8:]
                    elif p.is_absolute() and any(
                        p.is_relative_to(Path(alias)) for alias in [old_root, *old_roots]
                    ):
                        alias = next(
                            Path(alias) for alias in [old_root, *old_roots] if p.is_relative_to(Path(alias))
                        )
                        p = new_root / p.relative_to(alias)
                    elif not p.is_absolute():
                        p = new_root / p
                    else:
                        unknown.append(f"{table}.{field}:root-external")
                        continue
                    if ".." in p.parts or not p.resolve().is_relative_to(new_root):
                        unknown.append(f"{table}.{field}:escape")
                    # Missing historic files may predate migration; compare source presence.
                    elif (old_root / p.relative_to(new_root)).is_file() and not p.is_file():
                        unknown.append(f"{table}.{field}:missing-copy")
    if unknown:
        raise ValueError("技术引用未覆盖：" + ",".join(sorted(set(unknown))))
