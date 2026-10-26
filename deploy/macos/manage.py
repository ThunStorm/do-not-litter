#!/usr/bin/env python3
"""Render and manage the two per-user launchd services for the Mac mini backend."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "deploy" / "macos" / "generated"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LAUNCH_LOGS = Path.home() / "Library" / "Logs" / "Zhijian"
RUNTIME_ROOT = Path("/Volumes/D/Library/Application Support/Zhijian")
SYSTEM_PYTHON = Path(
    "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
)
RUNTIME_VENV = RUNTIME_ROOT / "venv"
PYTHON = RUNTIME_VENV / "bin" / "python"
PYTHONPATH = str(ROOT / "backend" / "src")
OLLAMA_MODELS = Path("/Volumes/D/Projects/ollama-models")
sys.path.insert(0, PYTHONPATH)
from zhijian.core.storage import DEFAULT_CONTROL, read_json, validate_root


def data_root() -> Path:
    config = read_json(DEFAULT_CONTROL)
    return validate_root(config) if config else ROOT / "data"


DEFAULT_OLLAMA_MODELS = Path.home() / ".ollama" / "models"
SERVICES = {
    "api": ("cn.zhijian.api", "zhijian.main"),
    "worker": ("cn.zhijian.worker", "zhijian.worker"),
}


def environment() -> dict[str, str]:
    return {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": PYTHONPATH,
        "ENV": "production",
        "ZHIJIAN_HOST": "0.0.0.0",
        "ZHIJIAN_PORT": "8787",
        "ZHIJIAN_DATA_DIR": str(data_root()),
        "ZHIJIAN_SECRET_STORE": "keychain",
        "ZHIJIAN_ALLOW_LOCALHOST_WITHOUT_SESSION": "true",
        "ZHIJIAN_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "ZHIJIAN_WHISPER_BINARY": "/opt/homebrew/bin/whisper-cli",
        "ZHIJIAN_WHISPER_MODEL": str(
            data_root() / "models" / "whisper" / "ggml-base.bin"
        ),
    }


def plist(service: str, label: str, module: str) -> dict[str, object]:
    return {
        "Label": label,
        "ProgramArguments": [
            str(PYTHON),
            "-m",
            "zhijian.stdio_wrapper",
            service,
            module,
        ],
        "WorkingDirectory": str(Path.home()),
        "EnvironmentVariables": environment(),
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Background",
        "ThrottleInterval": 5,
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
    }


def render(destination: Path = GENERATED) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for service, (label, module) in SERVICES.items():
        target = destination / f"{label}.plist"
        with target.open("wb") as handle:
            plistlib.dump(plist(service, label, module), handle, sort_keys=False)
        rendered.append(target)
    return rendered


def launchctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *arguments], check=check, text=True, capture_output=True
    )


def _bootout_and_wait(domain: str, label: str) -> None:
    launchctl("bootout", f"{domain}/{label}", check=False)
    for _ in range(50):
        if launchctl("print", f"{domain}/{label}", check=False).returncode != 0:
            return
        time.sleep(0.1)
    raise SystemExit(f"等待 {label} 卸载超时；拒绝立即重新加载")


def validate_install() -> None:
    missing = [str(PYTHON)] if not PYTHON.is_file() else []
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        missing.append(str(ROOT / "frontend" / "dist" / "index.html"))
    if missing:
        raise SystemExit("安装前缺少构建产物：\n- " + "\n- ".join(missing))
    if shutil.which("launchctl") is None:
        raise SystemExit("当前系统没有 launchctl；此安装器仅支持 macOS。")


def ensure_ollama_models_link() -> None:
    """Keep Ollama.app on the persistent external-volume model store."""
    if not all((OLLAMA_MODELS / name).is_dir() for name in ("blobs", "manifests")):
        raise SystemExit(f"Ollama 模型目录无效或外置卷未挂载：{OLLAMA_MODELS}")
    DEFAULT_OLLAMA_MODELS.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_OLLAMA_MODELS.is_symlink():
        if DEFAULT_OLLAMA_MODELS.resolve() == OLLAMA_MODELS.resolve():
            print(f"Ollama 模型目录已就绪：{DEFAULT_OLLAMA_MODELS} -> {OLLAMA_MODELS}")
            return
        raise SystemExit(f"Ollama 默认模型路径已指向其他位置：{DEFAULT_OLLAMA_MODELS}")
    if DEFAULT_OLLAMA_MODELS.exists():
        timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
        backup = DEFAULT_OLLAMA_MODELS.with_name(f"models.before-zhijian-{timestamp}")
        shutil.move(DEFAULT_OLLAMA_MODELS, backup)
        print(f"已备份原 Ollama 默认模型目录：{backup}")
    DEFAULT_OLLAMA_MODELS.symlink_to(OLLAMA_MODELS, target_is_directory=True)
    print(f"已固定 Ollama 模型目录：{DEFAULT_OLLAMA_MODELS} -> {OLLAMA_MODELS}")


def bootstrap_runtime() -> None:
    if not SYSTEM_PYTHON.is_file():
        raise SystemExit(f"缺少本机 Python 3.14：{SYSTEM_PYTHON}")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if not PYTHON.is_file():
        subprocess.run(
            [str(SYSTEM_PYTHON), "-m", "venv", str(RUNTIME_VENV)], check=True
        )
    subprocess.run(
        [str(PYTHON), "-m", "pip", "install", "-e", f"{ROOT / 'backend'}[dev]"],
        check=True,
    )
    subprocess.run(
        [str(PYTHON), "-c", "import zhijian, sys; print(sys.version.split()[0])"],
        check=True,
    )


def install() -> None:
    validate_install()
    ensure_ollama_models_link()
    LAUNCH_LOGS.mkdir(parents=True, exist_ok=True)
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    generated = render()
    domain = f"gui/{os.getuid()}"
    timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    for source in generated:
        target = LAUNCH_AGENTS / source.name
        label = source.stem
        loaded = launchctl("print", f"{domain}/{label}", check=False).returncode == 0
        if target.exists():
            backup = target.with_suffix(f".plist.{timestamp}.bak")
            shutil.copy2(target, backup)
        shutil.copy2(source, target)
        if loaded:
            _bootout_and_wait(domain, label)
        launchctl("bootstrap", domain, str(target))
        launchctl("kickstart", "-k", f"{domain}/{label}")
        print(f"已启动 {label}")


def uninstall() -> None:
    domain = f"gui/{os.getuid()}"
    for label, _ in SERVICES.values():
        target = LAUNCH_AGENTS / f"{label}.plist"
        _bootout_and_wait(domain, label)
        if target.exists():
            target.unlink()
        print(f"已移除 {label}（数据目录未删除）")


def _service_running(domain: str, label: str) -> bool:
    result = launchctl("print", f"{domain}/{label}", check=False)
    return (
        result.returncode == 0
        and "state = running" in result.stdout
        and "pid =" in result.stdout
    )


def _api_ready() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8787/health", timeout=3
        ) as response:
            health = json.load(response)
        with urllib.request.urlopen("http://127.0.0.1:8787/", timeout=3) as response:
            body = response.read()
        ready = health.get("status") == "ok" and bool(body)
        return ready, f"health={health.get('status')} html_bytes={len(body)}"
    except (
        OSError,
        TimeoutError,
        ValueError,
        http.client.IncompleteRead,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:160]}"


def _worker_ready() -> tuple[bool, str]:
    try:
        with sqlite3.connect(f"file:{data_root() / 'app.db'}?mode=ro", uri=True) as db:
            row = db.execute(
                "SELECT value_json FROM settings WHERE key = 'runtime:worker-heartbeat'"
            ).fetchone()
        value = json.loads(row[0]) if row else {}
        sampled = datetime.fromisoformat(
            str(value.get("at") or "").replace("Z", "+00:00")
        )
        age = max(
            0,
            (
                datetime.now(timezone.utc) - sampled.astimezone(timezone.utc)
            ).total_seconds(),
        )
        config = read_json(DEFAULT_CONTROL)
        loaded = not config or (
            value.get("storage_root") == str(data_root())
            and value.get("storage_generation") == config["generation"]
        )
        ready = age <= 75 and loaded
        return ready, f"pid={value.get('pid')} heartbeat_age={round(age)}s"
    except (OSError, TypeError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:160]}"


def _ensure_no_active_jobs() -> None:
    from zhijian.core.storage import require_idle

    require_idle(data_root() / "app.db")


def restart() -> None:
    validate_install()
    from zhijian.core.storage import maintenance_lock

    with maintenance_lock(DEFAULT_CONTROL):
        _ensure_no_active_jobs()
        stop_services()
        archive_legacy_stdio()
        start_services()


def stop_services() -> None:
    domain = f"gui/{os.getuid()}"
    for label, _ in SERVICES.values():
        _bootout_and_wait(domain, label)
    # launchd must close every child handle before file movement.
    for label, _ in SERVICES.values():
        if _service_running(domain, label):
            raise RuntimeError("服务未完全退出")


def start_services() -> None:
    domain = f"gui/{os.getuid()}"
    for service in ("worker", "api"):
        label, module = SERVICES[service]
        target = LAUNCH_AGENTS / f"{label}.plist"
        with target.open("wb") as handle:
            plistlib.dump(plist(service, label, module), handle, sort_keys=False)
        launchctl("bootstrap", domain, str(target))
        print(f"已启动 {label}")


def archive_legacy_stdio() -> None:
    import uuid

    # This runs only after both services and their file handles are closed.
    from zhijian.core.storage import (
        atomic_json,
        digest,
    )

    for source in sorted((data_root() / "logs").glob("*.jsonl*")):
        if not source.is_file() or source.is_symlink():
            continue
        target = (
            data_root()
            / "logs/archive"
            / f"legacy-{source.name}-{uuid.uuid4().hex}.log"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise RuntimeError("旧运行日志复制校验失败")
        atomic_json(
            str(target) + ".meta.json",
            {
                "service": source.name.split(".")[0],
                "closed_at": time.time(),
                "original_bytes": target.stat().st_size,
                "sha256": digest(target),
                "filename": target.name,
                "policy_version": 1,
            },
        )
        source.unlink()
    for service in SERVICES:
        for stream in ("stdout", "stderr"):
            source = LAUNCH_LOGS / f"{service}.{stream}.log"
            if not source.is_file():
                continue
            target = (
                data_root()
                / "logs/archive"
                / f"stdio-legacy-{service}-{stream}-{uuid.uuid4().hex}.log"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if digest(source) != digest(target):
                raise RuntimeError("旧启动日志复制校验失败")
            atomic_json(
                str(target) + ".meta.json",
                {
                    "service": f"stdio-{service}-{stream}",
                    "closed_at": time.time(),
                    "original_bytes": target.stat().st_size,
                    "sha256": digest(target),
                    "filename": target.name,
                    "policy_version": 1,
                },
            )
            source.unlink()


def verify_storage(config) -> None:
    for _ in range(30):
        if status():
            with urllib.request.urlopen(
                "http://127.0.0.1:8787/api/settings/storage", timeout=5
            ) as response:
                loaded = json.load(response)
            if (
                loaded["root"] == config["root"]
                and loaded["generation"] == config["generation"]
            ):
                return
        time.sleep(1)
    raise RuntimeError("新数据目录健康/实际加载代次验收失败")


def status() -> bool:
    domain = f"gui/{os.getuid()}"
    for label, _ in SERVICES.values():
        state = "RUNNING" if _service_running(domain, label) else "NOT_RUNNING"
        print(f"{label}: {state}")
    api_ready, api_detail = _api_ready()
    worker_ready, worker_detail = _worker_ready()
    print(f"api-content: {'READY' if api_ready else 'FAILED'} ({api_detail})")
    print(
        f"worker-heartbeat: {'READY' if worker_ready else 'FAILED'} ({worker_detail})"
    )
    return api_ready and worker_ready


def main() -> None:
    parser = argparse.ArgumentParser(description="至简 Mac mini launchd 管理器")
    parser.add_argument(
        "action",
        choices=(
            "runtime",
            "render",
            "install",
            "restart",
            "uninstall",
            "status",
            "storage-adopt",
            "storage-plan",
            "storage-apply",
            "storage-recover",
        ),
    )
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    if args.action == "storage-adopt":
        from zhijian.core.storage import adopt

        print(json.dumps(adopt(data_root(), DEFAULT_CONTROL), ensure_ascii=False))
    elif args.action == "storage-plan":
        from zhijian.storage_cli import plan

        result = plan(DEFAULT_CONTROL, args.target)
        result.pop("inventory", None)
        print(json.dumps(result, ensure_ascii=False))
    elif args.action == "storage-apply":
        from zhijian.storage_cli import apply

        print(
            apply(
                DEFAULT_CONTROL,
                stop=stop_services,
                start=start_services,
                verify=verify_storage,
            )
        )
    elif args.action == "storage-recover":
        from zhijian.storage_cli import recover

        print(
            recover(
                DEFAULT_CONTROL,
                stop=stop_services,
                start=start_services,
                verify=verify_storage,
            )
        )
    elif args.action == "runtime":
        bootstrap_runtime()
    elif args.action == "render":
        for path in render():
            print(path)
    elif args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    elif args.action == "restart":
        restart()
    else:
        raise SystemExit(0 if status() else 1)


if __name__ == "__main__":
    main()
