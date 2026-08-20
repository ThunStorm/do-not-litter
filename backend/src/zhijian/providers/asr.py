from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class WhisperCppProvider:
    def __init__(self, binary: str, model: Path) -> None:
        self.binary = shutil.which(binary) or binary
        self.model = model

    def transcribe(self, media: Path) -> tuple[str, list[dict]]:
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
            result = subprocess.run(
                arguments,
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            if result.returncode != 0 and "failed to allocate buffer" in (result.stderr or ""):
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
                    # whisper.cpp exposes offsets in 10 ms ticks.
                    start_ms = int(offsets.get("from", 0)) * 10
                    end_ms = int(offsets.get("to", offsets.get("from", 0))) * 10
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
