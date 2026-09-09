import importlib.util
import json
from pathlib import Path

from zhijian.ai.benchmark import summarize, validate_cases


def _runner():
    path = Path(__file__).parents[2] / "scripts" / "run_ai_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_ai_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_formal_benchmark_writes_matrix_and_routing_recommendation(tmp_path: Path) -> None:
    cases = json.loads(
        (Path(__file__).parents[2] / "dev docs" / "benchmark" / "ai-benchmark-cases-v1.json").read_text()
    )
    validate_cases(cases)
    rows = [
        {
            "case_id": case["case_id"],
            "provider": "ollama" if model != "remote-baseline" else "remote",
            "model": model,
            "location": "LOCAL" if model != "remote-baseline" else "REMOTE",
            "stage": case["stage"],
            "schema_valid": True,
            "entity_recall": 1,
            "place_recall": 1,
            "evidence_coverage": 1,
            "poi_top_n_candidate_recall": 1,
            "place_insight_coverage": 1,
            "visit_window_recall": 1,
            "json_repair_count": 0,
            "hallucination_count": 0,
            "latency_ms": 20,
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "total_tokens": 5,
            "error_type": None,
        }
        for case in cases
        for model in ("remote-baseline", "qwen3.5:9b")
        if case["stage"] != "VISION_FACT"
    ]
    summary = summarize(cases[:-1], rows)
    assert summary["recommendations"]["PLACE_EXTRACT"]["mode"] == "LOCAL_FIRST"
    assert summary["release_gate"]["passed"] is True
    run_dir = _runner().write_run(tmp_path, cases[:-1], rows)
    assert (run_dir / "metadata.json").is_file()
    assert (run_dir / "raw-results.jsonl").is_file()
    assert "qwen3.5:9b" in (run_dir / "summary.md").read_text()
