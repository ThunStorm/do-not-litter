from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from zhijian.providers.asr import (
    ASRProviderRegistry,
    Qwen3ASRProvider,
    WhisperCppCpuProvider,
    WhisperCppProvider,
)


def _benchmark():
    path = Path(__file__).parents[2] / "scripts" / "benchmark_asr_providers.py"
    spec = importlib.util.spec_from_file_location("benchmark_asr_providers", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asr_registry_preserves_default_and_exposes_cpu_fallback(tmp_path) -> None:
    registry = ASRProviderRegistry("whisper-cli", tmp_path / "model.bin")

    assert registry.default_provider_id == "WHISPER_CPP"
    assert isinstance(registry.get("WHISPER_CPP"), WhisperCppProvider)
    assert isinstance(registry.get("WHISPER_CPP_CPU"), WhisperCppCpuProvider)
    with pytest.raises(ValueError, match="不支持的本地 ASR Provider"):
        registry.get("UNKNOWN")


def test_qwen_provider_passes_context_and_parses_runner_json(tmp_path, monkeypatch) -> None:
    paths = [tmp_path / name for name in ("python", "runner.py", "model", "aligner")]
    for path in paths:
        path.touch()
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        return type(
            "Result",
            (),
            {
                "returncode": 0,
                "stderr": "",
                "stdout": (
                    '{"text":"大理古城","model":"qwen","backend":"mlx","runtime_version":"1",'
                    '"segments":[{"text":"大理古城","start_ms":0,"end_ms":1000,"locator":{}}]}'
                ),
            },
        )()

    monkeypatch.setattr("zhijian.providers.asr.subprocess.run", run)
    registry = ASRProviderRegistry("whisper-cli", tmp_path / "whisper", *paths)
    provider = registry.get("QWEN3_ASR")
    text, segments = provider.transcribe(tmp_path / "audio.wav", context="大理 古城")

    assert isinstance(provider, Qwen3ASRProvider)
    assert text == "大理古城" and segments[0]["end_ms"] == 1000
    assert commands[0][-2:] == ["--context", "大理 古城"]
    assert provider.last_metadata["runtime_version"] == "1"


def test_asr_benchmark_requires_all_frozen_scenarios() -> None:
    categories = sorted(_benchmark().REQUIRED_CATEGORIES)
    rows = [
        {
            "provider": "WHISPER_CPP_CPU",
            "category": category,
            "expected_entities": ["翠湖"],
            "actual_entities": ["翠湖"],
            "timestamp_alignment": 1,
            "runtime_ms": 100,
            "peak_memory_bytes": 10,
        }
        for category in categories
    ]

    result = _benchmark().evaluate(rows)

    assert result["providers"]["WHISPER_CPP_CPU"]["place_entity_recall"] == 1
    assert result["providers"]["WHISPER_CPP_CPU"]["failure_count"] == 0
    with pytest.raises(ValueError, match="缺少场景"):
        _benchmark().evaluate(rows[:1])
