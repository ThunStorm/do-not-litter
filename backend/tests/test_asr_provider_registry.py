from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from zhijian.providers.asr import ASRProviderRegistry, WhisperCppCpuProvider, WhisperCppProvider


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
