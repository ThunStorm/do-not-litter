"""Independent storage coordinator. API saves plans; only this local CLI switches roots."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path

from zhijian.core.storage import (
    DEFAULT_CONTROL,
    MARKER,
    adopt,
    atomic_json,
    database_check,
    digest,
    inventory,
    maintenance_lock,
    preflight,
    read_json,
    require_idle,
    validate_references,
    validate_root,
)


def plan(control, target):
    with maintenance_lock(control):
        config = read_json(control)
        root = validate_root(config)
        result = preflight(root, target)
        report = inventory(root)
        needed = report["total_bytes"] + (root / "app.db").stat().st_size * 3 + 64 * 1024**2
        if result["free_bytes"] < needed:
            raise ValueError("空间不足，包含一致性备份及余量")
        result.update(
            {
                "generation": config["generation"],
                "required_bytes": needed,
                "inventory": report,
                "stage": "PLANNED",
                "exceptions": {
                    "execution_environment": "保留安装路径，不复制data/runtime中的venv",
                    "keychain": "系统Keychain，不导出",
                    "old_backups": "保留原位置，不作为自动清理对象",
                    "external_models": "显式外部模型库保持原路径",
                },
            }
        )
        atomic_json(Path(control).with_name("storage-plan.json"), result)
        return result


def apply(control, *, stop, start, verify, drain_timeout=300):
    """Callbacks belong to the local supervisor; API/Worker never stop themselves."""
    control = Path(control)
    state_path = control.with_name("maintenance-state.json")
    with maintenance_lock(control):
        config = read_json(control)
        root = validate_root(config)
        draft = read_json(control.with_name("storage-plan.json"))
        if draft.get("generation") != config["generation"]:
            raise ValueError("方案已过期，请重新预检")
        target = Path(draft["target"])
        preflight(root, target)
        if read_json(state_path).get("stage") not in {None, "RELEASED", "ROLLED_BACK", "PLANNED"}:
            raise ValueError("已有维护操作，先恢复")
        state = {
            "stage": "DRAINING",
            "previous_config": config,
            "target": str(target),
            "generation": config["generation"],
        }
        atomic_json(state_path, state)
        stopped = False
        try:
            # Incoming writes are gated before idle check. Existing jobs finish naturally.
            deadline = time.monotonic() + drain_timeout
            while True:
                try:
                    require_idle(root / "app.db")
                    break
                except ValueError:
                    if time.monotonic() >= deadline:
                        raise ValueError("安全窗口仍未到达，保留方案，任务不受中断") from None
                    time.sleep(0.5)
            stop()
            stopped = True
            require_idle(root / "app.db")
            database_check(root / "app.db")
            state["stage"] = "COPYING"
            atomic_json(state_path, state)
            report = inventory(root)  # Consistent after writers/handles have exited.
            required = report["total_bytes"] + (root / "app.db").stat().st_size * 3 + 64 * 1024**2
            if shutil.disk_usage(target.parent).free < required:
                raise ValueError("停机后空间复核不足")
            target.mkdir(mode=0o700, exist_ok=True)
            for relative, meta in report["files"].items():
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copy2(root / relative, destination)
                if digest(destination) != meta["sha256"]:
                    raise ValueError("副本文件哈希不匹配")
                if relative.startswith("secrets/"):
                    destination.chmod(0o600)
            backup = control.parent / f"storage-backup-{config['generation']}.db"
            with (
                sqlite3.connect(f"file:{root / 'app.db'}?mode=ro", uri=True) as source,
                sqlite3.connect(backup) as saved,
            ):
                source.backup(saved)
            backup.chmod(0o600)
            database_check(backup)
            shutil.copy2(backup, target / "app.db")
            database_check(target / "app.db")
            validate_references(target / "app.db", root, target, config.get("old_roots", []))
            atomic_json(target / MARKER, {"instance_id": config["instance_id"]})
            stat = target.stat()
            updated = {
                **config,
                "root": str(target),
                "generation": config["generation"] + 1,
                "root_identity": [stat.st_dev, stat.st_ino],
                "old_roots": list(dict.fromkeys([*config.get("old_roots", []), str(root)])),
            }
            state.update(
                {
                    "backup": str(backup),
                    "backup_sha256": digest(backup),
                    "manifest": report,
                    "stage": "SWITCHED",
                }
            )
            atomic_json(state_path, state)
            if read_json(control) != config:
                raise ValueError("启动配置发生漂移")
            atomic_json(control.with_suffix(".previous.json"), config)
            atomic_json(control, updated)
            state["stage"] = "VERIFYING"
            atomic_json(state_path, state)
            start()
            verify(updated)
            state["stage"] = "RELEASED"
            atomic_json(state_path, state)
            return {"stage": "RELEASED", "root": str(target), "old_copy": str(root), "backup": str(backup)}
        except Exception as exc:
            # Leave a persistent gate, never guess whether the other service has started.
            state.update(
                {
                    "stage": "FAILED" if stopped else "PLANNED",
                    "error": type(exc).__name__,
                    "services_stopped": stopped,
                }
            )
            atomic_json(state_path, state)
            raise


def recover(control, *, stop, start, verify=None):
    control = Path(control)
    with maintenance_lock(control):
        state = read_json(control.with_name("maintenance-state.json"))
        if state.get("stage") in {"RELEASED", "ROLLED_BACK", None}:
            raise ValueError("已放行业务写入；拒绝退回旧库。请另建排空、最新数据同步方案")
        previous = state["previous_config"]
        validate_root(previous)
        current = read_json(control)
        require_idle(Path(current["root"]) / "app.db")
        stop()
        atomic_json(control, previous)
        start()
        if verify:
            verify(previous)
        state["stage"] = "ROLLED_BACK"
        atomic_json(control.with_name("maintenance-state.json"), state)
        return {"stage": "ROLLED_BACK", "root": previous["root"], "target_preserved": state["target"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "adopt", "plan", "status", "logs"])
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    if args.action == "init":
        if not args.root or args.root.exists():
            raise ValueError("新实例必须指定尚不存在的专用目录")
        args.root.mkdir(parents=True, mode=0o700)
        with sqlite3.connect(args.root / "app.db") as db:
            db.execute("PRAGMA user_version=0")
        result = adopt(args.root, args.control)
    elif args.action == "adopt":
        result = adopt(args.root, args.control)
    elif args.action == "plan":
        try:
            result = plan(args.control, args.target)
        except Exception as exc:
            atomic_json(
                args.control.with_name("storage-plan.json"), {"stage": "FAILED", "error": str(exc)[:500]}
            )
            raise
        result.pop("inventory", None)
    elif args.action == "logs":
        from zhijian.core.file_logs import maintain

        result = maintain(validate_root(read_json(args.control)) / "logs", args.control)
    else:
        result = {
            "config": read_json(args.control),
            "state": read_json(args.control.with_name("maintenance-state.json")),
            "plan": read_json(args.control.with_name("storage-plan.json")),
        }
        result.get("plan", {}).pop("inventory", None)
        result.get("state", {}).pop("manifest", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
