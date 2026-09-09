from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _runner():
    path = Path(__file__).parents[2] / "scripts" / "run_poi_resolution_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_poi_resolution_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_poi_resolution_golden_enforces_precision_first_gate() -> None:
    path = Path(__file__).parents[2] / "dev docs" / "benchmark" / "poi-resolution-golden-v1.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    result = _runner().evaluate(cases)

    assert len(cases) >= 10
    assert result["candidate_recall_at_3"] == 1
    assert result["wrong_confirm_count"] == 0
    assert result["auto_confirm_precision"] == 1
    assert {item["sample_id"]: item["status"] for item in result["statuses"]} == {
        str(case["sample_id"]): str(case["expected"]["status"]) for case in cases
    }
