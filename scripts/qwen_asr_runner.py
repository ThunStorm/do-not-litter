"""Run Qwen3-ASR in an isolated MLX process and emit transcript JSON only."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import resource
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

BACKEND_ID = "mlx-qwen3-asr"
DEFAULT_MODEL_ID = "Qwen/Qwen3-ASR-0.6B"
DEFAULT_ALIGNER_ID = "Qwen/Qwen3-ForcedAligner-0.6B"
RUNTIME_DISTRIBUTION = "mlx-qwen3-asr"


class QwenRuntime(Protocol):
    def load_model(self, model_id: str) -> tuple[Any, Any]: ...

    def transcribe(self, audio: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    api: QwenRuntime
    version: str


def _load_runtime() -> RuntimeInfo:
    try:
        import mlx_qwen3_asr
    except ImportError as exc:
        raise RuntimeError(
            "隔离 Runtime 缺少 mlx-qwen3-asr；请在 data/runtime/qwen-asr/venv 安装固定版本"
        ) from exc
    try:
        version = importlib.metadata.version(RUNTIME_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return RuntimeInfo(api=mlx_qwen3_asr, version=version)


def _duration_ms(path: Path) -> int:
    if path.suffix.casefold() == ".wav":
        try:
            with wave.open(str(path), "rb") as audio:
                return round(audio.getnframes() / audio.getframerate() * 1000)
        except (wave.Error, ZeroDivisionError):
            pass
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("无法读取音频时长，不能验证 Qwen 时间码") from exc
    if result.returncode or duration <= 0:
        raise RuntimeError("无法读取音频时长，不能验证 Qwen 时间码")
    return round(duration * 1000)


def _value(item: object, name: str, default: object = None) -> object:
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _segments(result: object, duration_ms: int, model_id: str) -> list[dict[str, Any]]:
    raw_segments = _value(result, "segments", [])
    if not isinstance(raw_segments, list) or not raw_segments:
        raise RuntimeError("QWEN_ASR_ALIGNMENT_FAILED: Runtime 未返回时间码")
    normalized: list[dict[str, Any]] = []
    previous_start = previous_end = -1
    for item in raw_segments:
        text = str(_value(item, "text", "") or "").strip()
        start = _value(item, "start", _value(item, "start_time"))
        end = _value(item, "end", _value(item, "end_time"))
        try:
            start_ms, end_ms = round(float(start) * 1000), round(float(end) * 1000)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("QWEN_ASR_ALIGNMENT_FAILED: 时间码不是数值") from exc
        if (
            not text
            or start_ms < 0
            or end_ms < start_ms
            or start_ms < previous_start
            or end_ms < previous_end
        ):
            raise RuntimeError("QWEN_ASR_ALIGNMENT_FAILED: 时间码为空、逆序或区间非法")
        if end_ms > duration_ms + 2000:
            raise RuntimeError("QWEN_ASR_ALIGNMENT_FAILED: 时间码异常超出音频时长")
        previous_start, previous_end = start_ms, end_ms
        normalized.append(
            {
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "confidence": None,
                "locator": {"method": "qwen3-forced-aligner", "model": model_id},
            }
        )
    return normalized


def _peak_memory_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def transcribe(
    audio_path: Path,
    *,
    context: str = "",
    language: str | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    aligner_id: str = DEFAULT_ALIGNER_ID,
    runtime: RuntimeInfo | None = None,
) -> dict[str, Any]:
    path = audio_path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise RuntimeError("audio path 必须是本机文件")
    duration_ms = _duration_ms(path)
    runtime = runtime or _load_runtime()
    loaded_at = time.perf_counter()
    model, _config = runtime.api.load_model(model_id)
    model_load_ms = round((time.perf_counter() - loaded_at) * 1000)
    started = time.perf_counter()
    result = runtime.api.transcribe(
        str(path),
        model=model,
        language=language,
        context=context or None,
        return_timestamps=True,
        forced_aligner=aligner_id,
    )
    asr_runtime_ms = round((time.perf_counter() - started) * 1000)
    text = str(_value(result, "text", "") or "").strip()
    if not text:
        raise RuntimeError("Qwen3-ASR 未返回转写文本")
    segments = _segments(result, duration_ms, model_id)
    return {
        "text": text,
        "language": str(_value(result, "language", language or "") or ""),
        "model": model_id,
        "backend": BACKEND_ID,
        "runtime_version": runtime.version,
        "aligner_model": aligner_id,
        "segments": segments,
        "metrics": {
            "model_load_ms": model_load_ms,
            "asr_runtime_ms": asr_runtime_ms,
            "alignment_runtime_ms": None,
            "peak_memory_bytes": _peak_memory_bytes(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="隔离运行 Qwen3-ASR MLX，并只向 stdout 输出 JSON")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--context", default="")
    parser.add_argument("--language")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--forced-aligner", default=DEFAULT_ALIGNER_ID)
    args = parser.parse_args()
    try:
        payload = transcribe(
            args.audio,
            context=args.context,
            language=args.language,
            model_id=args.model,
            aligner_id=args.forced_aligner,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
