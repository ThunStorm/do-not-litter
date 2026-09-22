from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ASRProvider(Protocol):
    provider_id: str

    def transcribe(
        self, media: Path, *, context: str | None = None
    ) -> tuple[str, list[dict]]: ...


class WhisperCppProvider:
    provider_id = "WHISPER_CPP"

    def __init__(self, binary: str, model: Path, *, no_gpu: bool = False) -> None:
        self.binary = shutil.which(binary) or binary
        self.model = model
        self.no_gpu = no_gpu

    def transcribe(
        self, media: Path, *, context: str | None = None
    ) -> tuple[str, list[dict]]:
        del context
        ffmpeg = shutil.which("ffmpeg")
        whisper = shutil.which(self.binary)
        if not ffmpeg:
            raise RuntimeError("FFmpeg 未安装")
        if not whisper:
            raise RuntimeError("Whisper.cpp 未安装")
        if not self.model.is_file():
            raise RuntimeError(f"Whisper 模型不存在：{self.model}")
        with tempfile.TemporaryDirectory(prefix="zhijian-asr-") as temporary:
            directory = Path(temporary)
            wav = directory / "audio.wav"
            output = directory / "transcript"
            convert = subprocess.run(
                [ffmpeg, "-y", "-i", str(media), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            if convert.returncode != 0:
                raise RuntimeError(f"音频提取失败：{convert.stderr[-500:]}")
            arguments = [
                whisper,
                "-m",
                str(self.model),
                "-f",
                str(wav),
                "-l",
                "auto",
                "-oj",
                "-of",
                str(output),
            ]
            if self.no_gpu:
                arguments.append("-ng")
            result = subprocess.run(
                arguments,
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            if (
                not self.no_gpu
                and result.returncode != 0
                and "failed to allocate buffer" in (result.stderr or "")
            ):
                result = subprocess.run(
                    [*arguments, "-ng"],
                    capture_output=True,
                    text=True,
                    timeout=3600,
                    check=False,
                )
            transcript = output.with_suffix(".json")
            if result.returncode != 0 or not transcript.is_file():
                raise RuntimeError(f"Whisper 转写失败：{(result.stderr or result.stdout)[-500:]}")
            data = json.loads(transcript.read_text(encoding="utf-8", errors="replace"))
            raw_segments = data.get("transcription") or data.get("segments") or []
            segments: list[dict] = []
            for item in raw_segments:
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                offsets = item.get("offsets") or {}
                if offsets:
                    # Current whisper.cpp JSON offsets are already milliseconds.
                    start_ms = int(offsets.get("from", 0))
                    end_ms = int(offsets.get("to", offsets.get("from", 0)))
                else:
                    start_ms = int(float(item.get("start", 0)) * 1000)
                    end_ms = int(float(item.get("end", item.get("start", 0))) * 1000)
                segments.append(
                    {
                        "text": text,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "locator": {"file": media.name, "method": "whisper.cpp"},
                    }
                )
            text = "\n".join(segment["text"] for segment in segments).strip()
            if not text:
                raise RuntimeError("Whisper 未产生带时间码的转写结果")
            return text, segments


class WhisperCppCpuProvider(WhisperCppProvider):
    """A conservative local fallback when the Metal path is unavailable or unstable."""

    provider_id = "WHISPER_CPP_CPU"

    def __init__(self, binary: str, model: Path) -> None:
        super().__init__(binary, model, no_gpu=True)


class Qwen3ASRProvider:
    provider_id = "QWEN3_ASR"

    def __init__(
        self,
        python: Path,
        runner: Path,
        model: Path,
        aligner_model: Path,
        *,
        timeout_seconds: int = 3600,
    ) -> None:
        self.python = python
        self.runner = runner
        self.model = model
        self.aligner_model = aligner_model
        self.timeout_seconds = timeout_seconds
        self.last_metadata: dict = {}

    def transcribe(
        self, media: Path, *, context: str | None = None
    ) -> tuple[str, list[dict]]:
        for path, label in (
            (self.python, "Qwen Runtime Python"),
            (self.runner, "Qwen Runner"),
            (self.model, "Qwen ASR 模型"),
            (self.aligner_model, "Qwen Forced Aligner 模型"),
        ):
            if not path.exists():
                raise RuntimeError(f"{label}不存在：{path}")
        command = [
            str(self.python),
            str(self.runner),
            str(media),
            "--model",
            str(self.model),
            "--forced-aligner",
            str(self.aligner_model),
        ]
        if context:
            command.extend(("--context", context))
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Qwen3-ASR 失败：{(result.stderr or result.stdout)[-500:]}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Qwen3-ASR Runner 未返回合法 JSON") from exc
        text = str(payload.get("text") or "").strip()
        raw_segments = payload.get("segments")
        if not text or not isinstance(raw_segments, list) or not raw_segments:
            raise RuntimeError("Qwen3-ASR 未返回带时间码的转写")
        segments: list[dict] = []
        previous_start = previous_end = -1
        for item in raw_segments:
            start_ms = int(item.get("start_ms") or 0)
            end_ms = int(item.get("end_ms") or 0)
            value = str(item.get("text") or "").strip()
            if (
                not value
                or start_ms < previous_start
                or end_ms < previous_end
                or end_ms < start_ms
            ):
                raise RuntimeError("QWEN_ASR_ALIGNMENT_FAILED: 时间码为空、逆序或区间非法")
            previous_start, previous_end = start_ms, end_ms
            segments.append(
                {
                    "text": value,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "confidence": item.get("confidence"),
                    "locator": dict(item.get("locator") or {}),
                }
            )
        self.last_metadata = {
            key: payload.get(key)
            for key in ("model", "backend", "runtime_version", "aligner_model", "language", "metrics")
        }
        return text, segments


@dataclass(frozen=True, slots=True)
class ASRProviderRegistry:
    """Registry keeps provider selection out of the Video Pipeline."""

    binary: str
    model: Path
    qwen_python: Path | None = None
    qwen_runner: Path | None = None
    qwen_model: Path | None = None
    qwen_aligner_model: Path | None = None
    qwen_timeout_seconds: int = 3600

    def get(self, provider_id: str) -> ASRProvider:
        if provider_id == "WHISPER_CPP":
            return WhisperCppProvider(self.binary, self.model)
        if provider_id == "WHISPER_CPP_CPU":
            return WhisperCppCpuProvider(self.binary, self.model)
        if provider_id == "QWEN3_ASR" and all(
            (self.qwen_python, self.qwen_runner, self.qwen_model, self.qwen_aligner_model)
        ):
            return Qwen3ASRProvider(
                self.qwen_python,
                self.qwen_runner,
                self.qwen_model,
                self.qwen_aligner_model,
                timeout_seconds=self.qwen_timeout_seconds,
            )
        raise ValueError(f"不支持的本地 ASR Provider：{provider_id}")

    @property
    def default_provider_id(self) -> str:
        return "WHISPER_CPP"
