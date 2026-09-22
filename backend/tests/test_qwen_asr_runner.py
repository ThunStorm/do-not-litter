from __future__ import annotations

import importlib.util
import sys
import wave
from pathlib import Path
from types import SimpleNamespace


def _runner():
    name = "qwen_asr_runner"
    path = Path(__file__).parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _wav(path: Path) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * 16_000)


class _Runtime:
    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def load_model(self, model_id: str):
        self.calls.append(("load", model_id))
        return object(), object()

    def transcribe(self, audio: str, **kwargs):
        self.calls.append(("transcribe", audio, kwargs))
        return SimpleNamespace(text="大理古城", language="Chinese", segments=self.segments)


def test_qwen_runner_emits_shared_contract_and_passes_context(tmp_path: Path) -> None:
    runner = _runner()
    audio = tmp_path / "clip.wav"
    _wav(audio)
    api = _Runtime([{"text": "大理古城", "start": 0.1, "end": 0.9}])

    result = runner.transcribe(
        audio,
        context="大理古城",
        runtime=runner.RuntimeInfo(api=api, version="0.4.4"),
    )

    assert result["text"] == "大理古城"
    assert result["backend"] == "mlx-qwen3-asr"
    assert result["runtime_version"] == "0.4.4"
    assert result["segments"] == [
        {
            "text": "大理古城",
            "start_ms": 100,
            "end_ms": 900,
            "confidence": None,
            "locator": {
                "method": "qwen3-forced-aligner",
                "model": "Qwen/Qwen3-ASR-0.6B",
            },
        }
    ]
    assert api.calls[1][2]["context"] == "大理古城"
    assert api.calls[1][2]["return_timestamps"] is True
    assert api.calls[1][2]["forced_aligner"] == "Qwen/Qwen3-ForcedAligner-0.6B"


def test_qwen_runner_rejects_missing_or_invalid_alignment(tmp_path: Path) -> None:
    runner = _runner()
    audio = tmp_path / "clip.wav"
    _wav(audio)

    for segments in ([], [{"text": "逆序", "start": 0.8, "end": 0.2}]):
        try:
            runner.transcribe(
                audio,
                runtime=runner.RuntimeInfo(api=_Runtime(segments), version="0.4.4"),
            )
        except RuntimeError as exc:
            assert "QWEN_ASR_ALIGNMENT_FAILED" in str(exc)
        else:
            raise AssertionError("Qwen 时间码不合法时必须拒绝结果")
