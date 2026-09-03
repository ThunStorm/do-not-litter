import importlib.util
from pathlib import Path


def _runner():
    path = Path(__file__).parents[2] / "scripts" / "run_ai_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_ai_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_benchmark_release_gate_requires_real_baseline_and_candidate() -> None:
    samples = [{"sample_id": "sample", "expected": {"evidence_min_coverage": 0.9}}]
    rows = [
        {
            "sample_id": "sample", "profile": "BASELINE", "schema_pass": True,
            "evidence_coverage": 1, "place_recall": 1, "key_entity_recall": 1,
            "remote_prompt_tokens": 100, "remote_completion_tokens": 100,
        },
        {
            "sample_id": "sample", "profile": "CANDIDATE", "schema_pass": True,
            "evidence_coverage": 1, "place_recall": 1, "key_entity_recall": 1,
            "remote_prompt_tokens": 40, "remote_completion_tokens": 40,
        },
    ]
    result = _runner().evaluate(samples, rows)
    assert result["release_gate"]["passed"]
    assert result["release_gate"]["remote_token_reduction_percent"] == 60.0
