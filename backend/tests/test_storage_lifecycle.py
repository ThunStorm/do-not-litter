from __future__ import annotations

import gzip
import logging
import sqlite3
from pathlib import Path

import pytest

from zhijian.core.config import Settings
from zhijian.core.file_logs import LogPolicy, SealedLogHandler, maintain, preview, volumes
from zhijian.core.storage import adopt, atomic_json, digest, preflight, read_json, resolve_ref, validate_root
from zhijian.storage_cli import apply, plan, recover


@pytest.fixture
def instance(tmp_path):
    root = tmp_path / "旧 数据"
    root.mkdir()
    with sqlite3.connect(root / "app.db") as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE proof (value TEXT)")
        db.execute("INSERT INTO proof VALUES ('WAL中的资料')")
        db.execute("CREATE TABLE video_screenshots (image_path TEXT)")
        db.execute("INSERT INTO video_screenshots VALUES (?)", (str(root / "permanent/image.jpg"),))
    (root / "permanent").mkdir()
    (root / "permanent/image.jpg").write_bytes(b"permanent-image")
    (root / "runtime/venv").mkdir(parents=True)
    (root / "runtime/venv/python").write_text("installation-only")
    control = tmp_path / "control/storage.json"
    adopt(root, control)
    return root, control, tmp_path / "新 资料"


def test_migration_preserves_data_references_and_rejects_post_release_rollback(instance):
    root, control, target = instance
    before = digest(root / "permanent/image.jpg")
    plan(control, target)
    events = []

    def verify(config):
        assert config["root"] == str(target)
        assert read_json(control.with_name("maintenance-state.json"))["stage"] == "VERIFYING"
        with sqlite3.connect(target / "app.db") as db:
            assert db.execute("SELECT value FROM proof").fetchone()[0] == "WAL中的资料"
        settings = Settings(_env_file=None, ENV="production", storage_config=control)
        assert resolve_ref(root / "permanent/image.jpg", settings) == target / "permanent/image.jpg"
        assert resolve_ref("storage:permanent/image.jpg", settings).is_file()

    result = apply(
        control, stop=lambda: events.append("stop"), start=lambda: events.append("start"), verify=verify
    )
    assert result["stage"] == "RELEASED" and events == ["stop", "start"]
    assert digest(target / "permanent/image.jpg") == before
    assert (root / "permanent/image.jpg").is_file()
    assert not (target / "runtime/venv").exists()
    assert read_json(control)["generation"] == 2
    with pytest.raises(ValueError, match="拒绝退回旧库"):
        recover(control, stop=lambda: None, start=lambda: None)


def test_copy_failure_recovery_is_persistent_and_keeps_original(instance, monkeypatch):
    root, control, target = instance
    plan(control, target)
    import zhijian.storage_cli as cli

    original_copy = cli.shutil.copy2
    monkeypatch.setattr(cli.shutil, "copy2", lambda *a, **kw: (_ for _ in ()).throw(OSError("full")))
    with pytest.raises(OSError):
        apply(control, stop=lambda: None, start=lambda: None, verify=lambda _: None)
    assert read_json(control.with_name("maintenance-state.json"))["stage"] == "FAILED"
    assert validate_root(read_json(control)) == root
    monkeypatch.setattr(cli.shutil, "copy2", original_copy)
    assert recover(control, stop=lambda: None, start=lambda: None)["stage"] == "ROLLED_BACK"
    assert (root / "permanent/image.jpg").read_bytes() == b"permanent-image"


def test_single_service_start_failure_rolls_back_before_writes(instance):
    root, control, target = instance
    plan(control, target)
    with pytest.raises(RuntimeError):
        apply(
            control,
            stop=lambda: None,
            start=lambda: (_ for _ in ()).throw(RuntimeError("worker failed")),
            verify=lambda _: None,
        )
    assert read_json(control)["root"] == str(target)
    recover(control, stop=lambda: None, start=lambda: None)
    assert read_json(control)["root"] == str(root)
    assert target.is_dir()


@pytest.mark.parametrize("fault", ["missing_marker", "wrong_identity", "missing_database"])
def test_registered_root_never_silently_creates_new_database(instance, fault):
    root, control, _ = instance
    if fault == "missing_marker":
        (root / ".zhijian-instance.json").unlink()
    elif fault == "wrong_identity":
        config = read_json(control)
        config["root_identity"][0] += 1
        atomic_json(control, config)
    else:
        (root / "app.db").unlink()
    with pytest.raises(ValueError):
        Settings(_env_file=None, ENV="production", storage_config=control)
    if fault == "missing_database":
        assert not (root / "app.db").exists()


def test_production_environment_conflict_and_explicit_dev_override(instance, tmp_path):
    _, control, _ = instance
    with pytest.raises(ValueError, match="冲突"):
        Settings(_env_file=None, ENV="production", storage_config=control, data_dir=tmp_path)
    assert Settings(_env_file=None, data_dir=tmp_path, storage_config=control).data_dir == tmp_path


def test_path_validation_prevents_nested_roots_and_symlink_escape(instance, tmp_path):
    root, control, _ = instance
    for target in (root, root / "nested", root.parent):
        with pytest.raises(ValueError):
            preflight(root, target)
    outside = tmp_path / "original"
    outside.write_text("user-media")
    (root / "permanent/link").symlink_to(outside)
    settings = Settings(_env_file=None, data_dir=root, storage_config=control)
    for ref in ("storage:../original", "storage:permanent/link", outside):
        with pytest.raises(ValueError):
            resolve_ref(ref, settings)
    assert outside.read_text() == "user-media"


def seal(root, control, service="api"):
    handler = SealedLogHandler(root, service, control)
    logger = logging.getLogger("isolated-file-lifecycle")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("有中文的证据行")
    handler.seal()
    logger.info("active must stay")
    logger.removeHandler(handler)
    handler.close()
    return volumes(root)[0]


def test_compression_verified_and_idempotent_active_and_business_files_untouched(tmp_path):
    root, control = tmp_path / "logs", tmp_path / "control/storage.json"
    row = seal(root, control)
    now = row["closed_at"] + 49 * 3600
    result = maintain(root, control, now=now)
    assert result["compressed"] == 1
    archive = volumes(root)[0]
    with gzip.open(archive["path"], "rb") as stream:
        assert stream.read().decode() == "有中文的证据行\n"
    assert not Path(row["path"]).exists()
    assert (root / "active/api.log").read_text() == "active must stay\n"
    assert maintain(root, control, now=now)["compressed"] == 0
    assert preview(root, LogPolicy(), now=now)["delete_count"] == 0


def test_compression_failure_preserves_original_and_policy_boundary(tmp_path, monkeypatch):
    root, control = tmp_path / "logs", tmp_path / "control/storage.json"
    row = seal(root, control)
    import zhijian.core.file_logs as logs

    monkeypatch.setattr(logs.gzip, "open", lambda *a, **kw: (_ for _ in ()).throw(OSError("corrupt")))
    assert maintain(root, control, now=row["closed_at"] + 49 * 3600)["errors"]
    assert digest(row["path"]) == row["sha256"]
    assert not list((root / "archive").glob("*.tmp"))
    assert preview(root, LogPolicy(), now=row["closed_at"] + 30 * 86400)["delete_count"] == 1
    with pytest.raises(ValueError):
        LogPolicy(retention_days=2, compression_delay_hours=48)


def test_manifest_time_not_mtime_and_maintenance_gate(tmp_path):
    root, control = tmp_path / "logs", tmp_path / "control/storage.json"
    row = seal(root, control)
    import os

    os.utime(row["path"], (1, 1))
    assert preview(root, LogPolicy(), now=row["closed_at"] + 3600)["delete_count"] == 0
    atomic_json(control.with_name("maintenance-state.json"), {"stage": "COPYING"})
    assert maintain(root, control, now=row["closed_at"] + 40 * 86400)["paused"]
    assert Path(row["path"]).is_file()


def test_seal_and_compress_crash_windows_are_recovered(tmp_path):
    from zhijian.core.file_logs import compress_volume, recover_volumes

    root, control = tmp_path / "logs", tmp_path / "control/storage.json"
    row = seal(root, control)
    Path(row["index"]).unlink()  # Crash after closed-volume rename, before index commit.
    recover_volumes(root)
    recovered = volumes(root)[0]
    assert recovered["sha256"] == row["sha256"]
    original = Path(row["path"]).read_bytes()
    compress_volume(recovered)
    Path(row["path"]).write_bytes(original)  # Crash after index commit, before deleting source.
    recover_volumes(root)
    assert not Path(row["path"]).exists()
    assert len(volumes(root)) == 1


def test_maintenance_lock_and_busy_jobs_never_interrupt_work(instance):
    from zhijian.core.storage import maintenance_lock

    root, control, target = instance
    plan(control, target)
    with sqlite3.connect(root / "app.db") as db:
        db.execute("CREATE TABLE jobs (status TEXT, lease_owner TEXT)")
        db.execute("INSERT INTO jobs VALUES ('RUNNING', 'worker')")
    actions = []
    with pytest.raises(ValueError, match="安全窗口"):
        apply(
            control,
            stop=lambda: actions.append("stop"),
            start=lambda: None,
            verify=lambda _: None,
            drain_timeout=0,
        )
    assert actions == []
    assert read_json(control.with_name("maintenance-state.json"))["stage"] == "PLANNED"
    with maintenance_lock(control), pytest.raises(BlockingIOError), maintenance_lock(control):
        pass


def test_stdio_wrapper_preserves_complete_lines_and_exit_code(tmp_path):
    import os
    import subprocess
    import sys

    root = tmp_path / "data"
    script = tmp_path / "qa_stream.py"
    script.write_text(
        "import sys\nfor i in range(500):\n print(str(i)+':'+('中文'*100), flush=True)\n"
        "print('stderr-final', file=sys.stderr, flush=True)\nsys.exit(7)\n"
    )
    control = tmp_path / "control/storage.json"
    atomic_json(control.with_name("log-policy.json"), LogPolicy(volume_bytes=65536).model_dump())
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "ENV": "testing",
        "ZHIJIAN_DATA_DIR": str(root),
        "ZHIJIAN_STORAGE_CONFIG": str(control),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src") + os.pathsep + str(tmp_path),
    }
    result = subprocess.run(
        [sys.executable, "-m", "zhijian.stdio_wrapper", "qa", "qa_stream"],
        env=env,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 7
    rows = [row for row in volumes(root / "logs") if row["service"] == "stdio-qa-stdout"]
    text = (
        "".join(Path(row["path"]).read_text() for row in rows)
        + (root / "logs/active/stdio-qa-stdout.log").read_text()
    )
    assert text.splitlines() == [str(i) + ":" + "中文" * 100 for i in range(500)]
    assert (root / "logs/active/stdio-qa-stderr.log").read_text() == "stderr-final\n"
    assert len(rows) >= 2


def test_stdio_wrapper_forwards_signal_and_reaps_child(tmp_path):
    import os
    import subprocess
    import sys
    import time

    script = tmp_path / "qa_signal.py"
    script.write_text(
        "import os,signal,time\nfrom pathlib import Path\n"
        "Path(os.environ['READY']).write_text(str(os.getpid()))\n"
        "def done(s,f):\n print('child-terminated',flush=True)\n raise SystemExit(0)\n"
        "signal.signal(signal.SIGTERM,done)\nwhile True:time.sleep(.05)\n"
    )
    ready = tmp_path / "ready"
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "READY": str(ready),
        "ENV": "testing",
        "ZHIJIAN_DATA_DIR": str(tmp_path / "data"),
        "ZHIJIAN_STORAGE_CONFIG": str(tmp_path / "control/storage.json"),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src") + os.pathsep + str(tmp_path),
    }
    process = subprocess.Popen([sys.executable, "-m", "zhijian.stdio_wrapper", "qa", "qa_signal"], env=env)
    try:
        for _ in range(100):
            if ready.exists():
                break
            time.sleep(0.02)
        assert ready.exists()
        time.sleep(0.05)
        process.terminate()
        assert process.wait(timeout=5) == 0
        assert "child-terminated" in (tmp_path / "data/logs/active/stdio-qa-stdout.log").read_text()
        with pytest.raises(ProcessLookupError):
            os.kill(int(ready.read_text()), 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_second_root_change_keeps_original_legacy_aliases(instance):
    root, control, target = instance
    plan(control, target)
    apply(control, stop=lambda: None, start=lambda: None, verify=lambda _: None)
    final = target.parent / "第三份资料"
    plan(control, final)
    apply(control, stop=lambda: None, start=lambda: None, verify=lambda _: None)
    assert read_json(control)["old_roots"] == [str(root), str(target)]
    settings = Settings(_env_file=None, ENV="production", storage_config=control)
    assert resolve_ref(root / "permanent/image.jpg", settings) == final / "permanent/image.jpg"
    assert read_json(control)["generation"] == 3
