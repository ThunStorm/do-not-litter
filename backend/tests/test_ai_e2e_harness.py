import importlib.util
from pathlib import Path


def _harness():
    path = Path(__file__).parents[2] / "scripts" / "run_ai_e2e_harness.py"
    spec = importlib.util.spec_from_file_location("run_ai_e2e_harness", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_e2e_harness_marks_missing_external_conditions_without_claiming_production() -> None:
    result = _harness().evaluate([], ["REMOTE_PROVIDER_KEY", "LEGAL_TEST_VIDEO"])
    assert result["status"] == "BLOCKED_EXTERNAL"
    assert result["production_proven"] is False
    assert "LOCAL" in result["missing_signals"]


def test_e2e_harness_accepts_complete_captured_coverage() -> None:
    capture = {
        "source_kind": "PLATFORM_SUBTITLE",
        "location": "LOCAL",
        "execution_mode": "LOCAL_ONLY",
        "cache": True,
        "force_regenerate": True,
        "fallback": True,
        "replay": True,
        "cancel": True,
    }
    remote_capture = {
        **capture,
        "source_kind": "asr_video",
        "location": "REMOTE",
        "execution_mode": "REMOTE_ONLY",
    }
    captures = [capture, remote_capture]
    captures += [{**capture, "execution_mode": mode} for mode in ("LOCAL_FIRST", "REMOTE_FIRST", "AUTO")]
    result = _harness().evaluate(captures)
    assert result["status"] == "READY_FOR_REVIEW"
    assert result["production_proven"] is False
