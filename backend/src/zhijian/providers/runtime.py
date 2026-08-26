from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import httpx


@dataclass(slots=True)
class RuntimeCheck:
    name: str
    status: str
    detail: str
    path: str | None = None


def _run(arguments: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)


def check_binary(name: str) -> RuntimeCheck:
    path = shutil.which(name)
    if not path:
        return RuntimeCheck(name, "MISSING", "未找到可执行文件")
    try:
        version_flag = "-version" if name == "ffmpeg" else "--version"
        result = _run([path, version_flag])
        text = result.stdout or result.stderr
        detail = text.splitlines()[0] if text else path
        return RuntimeCheck(name, "READY" if result.returncode == 0 else "DEGRADED", detail[:200], path)
    except Exception as exc:
        return RuntimeCheck(name, "UNAVAILABLE", str(exc)[:200], path)


def check_whisper(binary: str, model: Path) -> RuntimeCheck:
    executable = shutil.which(binary)
    if not executable:
        return RuntimeCheck("whisper.cpp", "MISSING", f"未找到 {binary}")
    if not model.is_file():
        return RuntimeCheck("whisper.cpp", "DEGRADED", f"运行时已安装，模型缺失：{model}", executable)
    size_mb = model.stat().st_size / 1024 / 1024
    return RuntimeCheck(
        "whisper.cpp",
        "READY",
        f"{model.name} · {size_mb:.0f} MB · Metal（内存紧张时 CPU 回退）",
        executable,
    )


def check_ollama(base_url: str) -> RuntimeCheck:
    executable = shutil.which("ollama")
    if not executable:
        return RuntimeCheck("ollama", "MISSING", "未找到 ollama")
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
        names = [str(item.get("name", "")) for item in models[:4]]
        detail = f"服务在线 · {len(models)} 个模型" + (f" · {', '.join(names)}" if names else "")
        return RuntimeCheck("ollama", "READY", detail, executable)
    except Exception as exc:
        return RuntimeCheck("ollama", "UNAVAILABLE", f"已安装但服务未响应：{str(exc)[:140]}", executable)


def runtime_report(ollama_base_url: str, whisper_binary: str, whisper_model: Path) -> list[dict]:
    vision_ready = platform.system() == "Darwin" and shutil.which("swift") is not None
    vision = RuntimeCheck(
        "macos-vision-ocr",
        "READY" if vision_ready else "MISSING",
        "Apple Vision · 中文与英文 OCR" if vision_ready else "当前节点不支持 macOS Vision",
        shutil.which("swift"),
    )
    checks = [
        vision,
        check_binary("ffmpeg"),
        check_whisper(whisper_binary, whisper_model),
        check_ollama(ollama_base_url),
    ]
    return [asdict(check) for check in checks]


@lru_cache(maxsize=1)
def hardware_report() -> dict:
    report = {
        "machine_name": platform.node() or "Mac mini",
        "model": "未知",
        "chip": platform.processor() or "未知",
        "cpu_cores": None,
        "gpu": "未知",
        "gpu_cores": None,
        "memory": "未知",
        "architecture": platform.machine(),
    }
    profiler_path = Path("/usr/sbin/system_profiler")
    profiler = str(profiler_path) if profiler_path.is_file() else shutil.which("system_profiler")
    if profiler:
        try:
            result = _run([profiler, "SPHardwareDataType", "SPDisplaysDataType", "-json"], timeout=20)
            payload = json.loads(result.stdout) if result.returncode == 0 else {}
            hardware = (payload.get("SPHardwareDataType") or [{}])[0]
            display = (payload.get("SPDisplaysDataType") or [{}])[0]
            processors = str(hardware.get("number_processors", ""))
            core_match = re.search(r"(?:proc\s+)?(\d+)", processors)
            total_cores = core_match.group(1) if core_match else None
            report.update(
                {
                    "machine_name": hardware.get("machine_name") or report["machine_name"],
                    "model": hardware.get("machine_model") or report["model"],
                    "chip": hardware.get("chip_type") or report["chip"],
                    "cpu_cores": int(total_cores) if total_cores and total_cores.isdigit() else None,
                    "gpu": display.get("sppci_model") or display.get("_name") or report["gpu"],
                    "gpu_cores": int(display["sppci_cores"])
                    if str(display.get("sppci_cores", "")).isdigit()
                    else None,
                    "memory": hardware.get("physical_memory") or report["memory"],
                }
            )
        except Exception:
            pass
    disk = shutil.disk_usage(Path.cwd())
    report["disk"] = {
        "total_gb": round(disk.total / 1024**3, 1),
        "used_gb": round(disk.used / 1024**3, 1),
        "free_gb": round(disk.free / 1024**3, 1),
    }
    report["lan_ip"] = local_ip()
    sw_vers = Path("/usr/bin/sw_vers")
    if sw_vers.is_file():
        result = _run([str(sw_vers), "-productVersion"])
        report["os_version"] = result.stdout.strip() if result.returncode == 0 else platform.release()
    else:
        report["os_version"] = platform.release()
    return report


def runtime_metrics(data_dir: Path, worker_heartbeat_at: datetime | None = None) -> dict:
    """Return live host readings without caching hardware configuration.

    The first implementation intentionally uses only the standard library.  On macOS
    `getloadavg` is a genuine kernel reading; on platforms without it the CPU field is
    explicitly unavailable rather than represented as a made-up zero.
    """
    sampled_at = datetime.now(UTC)
    cpu_count = os.cpu_count() or 1
    try:
        cpu_percent: float | None = round(min(100.0, max(0.0, os.getloadavg()[0] / cpu_count * 100)), 1)
        cpu_reason: str | None = "1 分钟系统负载 / 逻辑核心数"
    except (AttributeError, OSError):
        cpu_percent, cpu_reason = None, "当前系统无法读取 CPU 负载"

    memory_data = _memory_metrics()

    try:
        disk = shutil.disk_usage(data_dir)
        disk_data = {
            "used_bytes": disk.used,
            "total_bytes": disk.total,
            "percent": round(disk.used / disk.total * 100, 1) if disk.total else None,
            "unavailable_reason": None,
        }
    except OSError as exc:
        disk_data = {
            "used_bytes": None,
            "total_bytes": None,
            "percent": None,
            "unavailable_reason": str(exc)[:160],
        }

    heartbeat = worker_heartbeat_at
    if heartbeat and heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    heartbeat_age = round((sampled_at - heartbeat).total_seconds(), 1) if heartbeat else None
    return {
        "sampled_at": sampled_at,
        "cpu": {
            "percent": cpu_percent,
            "unavailable_reason": cpu_reason if cpu_percent is None else None,
            "source": cpu_reason,
        },
        "memory": {
            **memory_data,
        },
        "disk": disk_data,
        "worker": {"heartbeat_at": heartbeat, "heartbeat_age_seconds": heartbeat_age},
    }


def _memory_metrics() -> dict:
    if platform.system() == "Darwin":
        try:
            return _macos_memory_metrics(_run(["/usr/bin/vm_stat"]).stdout)
        except (OSError, ValueError):
            return _unavailable_memory("当前系统无法读取 macOS 内存页统计")
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = int(page_size * os.sysconf("SC_PHYS_PAGES"))
        available = int(page_size * os.sysconf("SC_AVPHYS_PAGES"))
        used = max(0, total - available)
        return {
            "used_bytes": used,
            "total_bytes": total,
            "available_bytes": available,
            "cached_bytes": None,
            "compressed_bytes": None,
            "percent": round(used / total * 100, 1) if total else None,
            "method": "posix-available-pages",
            "unavailable_reason": None,
        }
    except (AttributeError, OSError, ValueError):
        return _unavailable_memory("当前系统无法读取内存页统计")


def _macos_memory_metrics(vm_stat: str) -> dict:
    """Compute memory usage without treating inactive file cache as application memory."""
    page_match = re.search(r"page size of (\d+) bytes", vm_stat)
    total_match = re.search(r"\((\d+) pages with a page size", vm_stat)
    if not page_match:
        raise ValueError("无法解析 macOS 内存统计")
    page_size = int(page_match.group(1))
    total = int(total_match.group(1)) if total_match else int(os.sysconf("SC_PHYS_PAGES"))
    pages = {
        name: int(value)
        for name, value in re.findall(
            r"Pages (free|active|inactive|speculative|wired down|occupied by compressor):\s+(\d+)",
            vm_stat,
        )
    }
    required = {"free", "inactive", "speculative"}
    if not required.issubset(pages):
        raise ValueError("macOS 内存页字段不完整")
    available_pages = pages["free"] + pages["inactive"] + pages["speculative"]
    available = min(total * page_size, available_pages * page_size)
    used = max(0, total * page_size - available)
    cached = (pages["inactive"] + pages["speculative"]) * page_size
    compressed = pages.get("occupied by compressor", 0) * page_size
    return {
        "used_bytes": used,
        "total_bytes": total * page_size,
        "available_bytes": available,
        "cached_bytes": cached,
        "compressed_bytes": compressed,
        "percent": round(used / (total * page_size) * 100, 1) if total else None,
        "method": "macos-reclaimable-pages",
        "unavailable_reason": None,
    }


def _unavailable_memory(reason: str) -> dict:
    return {
        "used_bytes": None,
        "total_bytes": None,
        "available_bytes": None,
        "cached_bytes": None,
        "compressed_bytes": None,
        "percent": None,
        "method": None,
        "unavailable_reason": reason,
    }


def local_ip() -> str:
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(("192.0.2.1", 80))
        return str(connection.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        connection.close()
