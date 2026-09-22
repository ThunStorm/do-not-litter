from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _module(name: str):
    path = Path(__file__).parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Adapter:
    def transcribe(self, media: Path, context_hints: list[str]):
        del media, context_hints
        return "大理古城 2026", [{"text": "大理古城 2026", "start_ms": 0, "end_ms": 1000}], {
            "model_load_ms": 10,
        }


def _manifest(tmp_path: Path, runner) -> dict:
    samples = []
    categories = sorted(runner.scorer.REQUIRED_CATEGORIES)
    for index in range(runner.MIN_REVIEWED_SAMPLES):
        category = categories[index % len(categories)]
        sample_id = f"{category.lower()}_{index:02d}"
        audio = tmp_path / f"{sample_id}.wav"
        audio.write_bytes(b"fixture")
        duration_ms = runner.MIN_LONG_FORM_DURATION_MS if category == "LONG_FORM" else 1000
        samples.append(
            {
                "id": sample_id,
                "category": category,
                "audio": audio.name,
                "duration_ms": duration_ms,
                "reference_text": "大理古城 2026",
                "reference_segments": [{"text": "大理古城 2026", "start_ms": 0, "end_ms": 1000}],
                "expected_entities": ["大理古城"],
                "expected_numbers": ["2026"],
                "context_hints": ["大理古城"],
            }
        )
    return {
        "ground_truth_reviewed_by": "测试人员",
        "ground_truth_reviewed_at": "2026-09-16T00:00:00+08:00",
        "samples": samples,
        "full_video_replays": [
            {"id": "video-one", "reviewed_by": "测试人员", "replayed_at": "2026-09-16T00:00:00+08:00"},
            {"id": "video-two", "reviewed_by": "测试人员", "replayed_at": "2026-09-16T00:00:00+08:00"},
        ],
    }


def test_runner_captures_four_providers_and_qwen_context_without_registry_changes(tmp_path: Path) -> None:
    runner = _module("run_asr_benchmark")
    manifest = _manifest(tmp_path, runner)
    samples = runner.validate_manifest(manifest, tmp_path / "manifest.json")
    providers = list(runner.PROVIDERS)

    adapters = {provider: _Adapter() for provider in providers}
    rows = runner.run_benchmark(samples, providers, adapters, tmp_path / "output")
    result = runner.scorer.evaluate(rows)

    assert len(rows) == len(samples) * (len(providers) + 1)
    assert result["providers"]["WHISPER_CPP_BASE"]["cer"] == 0
    assert result["providers"]["WHISPER_CPP_BASE"]["weighted_score"] >= 0.9
    assert result["qwen_context"]["context_gain"] == 0
    assert (tmp_path / "output" / "runs" / "qwen3-asr" / "results.json").is_file()
    assert result["production_eligible"] is False
    assert "Qwen Context 对照" in runner._render_report(result, manifest)


def test_runner_requires_manual_ground_truth_and_two_real_video_evidence(tmp_path: Path) -> None:
    runner = _module("run_asr_benchmark")
    manifest = _manifest(tmp_path, runner)
    manifest["ground_truth_reviewed_by"] = ""

    try:
        runner.validate_manifest(manifest, tmp_path / "manifest.json")
    except ValueError as exc:
        assert "人工核对" in str(exc)
    else:
        raise AssertionError("缺少人工 Ground Truth 不得进入 Benchmark")
