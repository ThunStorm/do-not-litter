#!/usr/bin/env python3
"""Render and manage the two per-user launchd services for the Mac mini backend."""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "deploy" / "macos" / "generated"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
SERVICES = {
    "api": ("cn.zhijian.api", ROOT / ".venv" / "bin" / "zhijian-api"),
    "worker": ("cn.zhijian.worker", ROOT / ".venv" / "bin" / "zhijian-worker"),
}


def environment() -> dict[str, str]:
    return {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONUNBUFFERED": "1",
        "ZHIJIAN_ENV": "production",
        "ZHIJIAN_HOST": "0.0.0.0",
        "ZHIJIAN_PORT": "8787",
        "ZHIJIAN_DATA_DIR": str(ROOT / "data"),
        "ZHIJIAN_SECRET_STORE": "keychain",
        "ZHIJIAN_ALLOW_LOCALHOST_WITHOUT_SESSION": "true",
        "ZHIJIAN_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "ZHIJIAN_WHISPER_BINARY": "/opt/homebrew/bin/whisper-cli",
        "ZHIJIAN_WHISPER_MODEL": str(ROOT / "data" / "models" / "whisper" / "ggml-base.bin"),
    }


def plist(service: str, label: str, executable: Path) -> dict[str, object]:
    logs = ROOT / "data" / "logs"
    return {
        "Label": label,
        "ProgramArguments": [str(executable)],
        "WorkingDirectory": str(ROOT),
        "EnvironmentVariables": environment(),
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Background",
        "ThrottleInterval": 5,
        "StandardOutPath": str(logs / f"{service}.stdout.log"),
        "StandardErrorPath": str(logs / f"{service}.stderr.log"),
    }


def render(destination: Path = GENERATED) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for service, (label, executable) in SERVICES.items():
        target = destination / f"{label}.plist"
        with target.open("wb") as handle:
            plistlib.dump(plist(service, label, executable), handle, sort_keys=False)
        rendered.append(target)
    return rendered


def launchctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *arguments], check=check, text=True, capture_output=True
    )


def validate_install() -> None:
    missing = [
        str(executable)
        for _, executable in SERVICES.values()
        if not executable.is_file()
    ]
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        missing.append(str(ROOT / "frontend" / "dist" / "index.html"))
    if missing:
        raise SystemExit("安装前缺少构建产物：\n- " + "\n- ".join(missing))
    if shutil.which("launchctl") is None:
        raise SystemExit("当前系统没有 launchctl；此安装器仅支持 macOS。")


def install() -> None:
    validate_install()
    (ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)
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
        if not loaded:
            launchctl("bootstrap", domain, str(target))
        launchctl("kickstart", "-k", f"{domain}/{label}")
        print(f"已启动 {label}")


def uninstall() -> None:
    domain = f"gui/{os.getuid()}"
    for label, _ in SERVICES.values():
        target = LAUNCH_AGENTS / f"{label}.plist"
        launchctl("bootout", f"{domain}/{label}", check=False)
        if target.exists():
            target.unlink()
        print(f"已移除 {label}（数据目录未删除）")


def status() -> None:
    domain = f"gui/{os.getuid()}"
    for label, _ in SERVICES.values():
        result = launchctl("print", f"{domain}/{label}", check=False)
        state = "RUNNING" if result.returncode == 0 else "NOT_LOADED"
        print(f"{label}: {state}")


def main() -> None:
    parser = argparse.ArgumentParser(description="至简 Mac mini launchd 管理器")
    parser.add_argument("action", choices=("render", "install", "uninstall", "status"))
    args = parser.parse_args()
    if args.action == "render":
        for path in render():
            print(path)
    elif args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    else:
        status()


if __name__ == "__main__":
    main()
