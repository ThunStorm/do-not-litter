import importlib.util
import json
from pathlib import Path


def _runner():
    path = Path(__file__).parents[2] / "scripts" / "run_video_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_video_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_video_fixture_benchmark_scores_complete_expected_outputs() -> None:
    path = Path(__file__).parents[2] / "dev docs" / "benchmark" / "video-workflow-golden-v1.json"
    samples = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        {
            "sample_id": sample["sample_id"],
            "profile": "FIXTURE",
            "schema_pass": True,
            "transcript_changes": sample["expected"]["transcript_changes"],
            "places": sample["expected"]["required_places"],
            "insights": sample["expected"]["insights"],
            "section_topics": sample["expected"]["section_topics"],
            "evidence_segment_ids": sample["expected"]["required_evidence"],
            "poi_resolution": sample["expected"]["poi_resolution"],
        }
        for sample in samples
    ]

    result = _runner().evaluate(samples, rows)
    profile = result["profiles"]["FIXTURE"]

    assert len(samples) == 12
    assert profile["schema_pass_rate"] == 1
    assert profile["places"]["recall"] == 1
    assert profile["insights"]["precision"] == 1
    assert profile["forbidden_place_count"] == 0
    assert profile["poi_resolution_accuracy"] == 1
    assert profile["poi_quality"]["false_confirm_count"] == 0
    assert result["production_eligible"] is False
