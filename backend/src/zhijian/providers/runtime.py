from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass

import httpx


@dataclass(slots=True)
class RuntimeCheck:
    name: str
    status: str
    detail: str


def check_binary(name: str) -> RuntimeCheck:
    path = shutil.which(name)
    if not path:
        return RuntimeCheck(name, "MISSING", "未找到")
    result = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    detail = (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else path
    return RuntimeCheck(name, "READY", detail[:200])


def check_ollama(base_url: str) -> RuntimeCheck:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
        return RuntimeCheck("ollama", "READY", f"已安装 {len(models)} 个模型")
    except Exception as exc:
        return RuntimeCheck("ollama", "UNAVAILABLE", str(exc)[:200])


def runtime_report(ollama_base_url: str) -> list[dict[str, str]]:
    vision = RuntimeCheck(
        "macos-vision-ocr",
        "READY" if platform.system() == "Darwin" and shutil.which("swift") else "MISSING",
        "macOS Vision 中文 OCR" if platform.system() == "Darwin" else "仅 Mac mini 可用",
    )
    checks = [vision, check_binary("ffmpeg"), check_binary("whisper-cli"), check_ollama(ollama_base_url)]
    return [asdict(check) for check in checks]
