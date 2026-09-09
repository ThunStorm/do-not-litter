import importlib.util
from pathlib import Path


def _probe():
    path = Path(__file__).parents[2] / "scripts" / "run_ai_capability_probe.py"
    spec = importlib.util.spec_from_file_location("run_ai_capability_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capability_probe_marks_structured_answers_and_vision_boundary() -> None:
    module = _probe()
    answer = {
        "category": "travel",
        "items": ["故宫"],
        "entities": ["故宫"],
        "changes": ["水陆庵"],
        "note": "故宫",
        "places": ["故宫"],
        "insights": ["故宫"],
        "candidates": ["故宫"],
    }
    matrix = module.probe_model("fixture", lambda _model, _prompt: answer)
    assert matrix["CLASSIFY"] == "PASS"
    assert matrix["PLACE_INSIGHT"] == "PASS"
    assert matrix["VISION_FACT"] == "NOT_TESTED"
    degraded = module.probe_model("fixture", lambda _model, _prompt: {"category": "other"})
    assert degraded["CLASSIFY"] == "DEGRADED"
