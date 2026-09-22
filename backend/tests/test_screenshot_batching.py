from pathlib import Path
from types import SimpleNamespace

from zhijian.services import video_screenshots


def test_screenshot_search_uses_one_ffmpeg_process_per_plan(tmp_path, monkeypatch) -> None:
    calls = 0

    def run(command, **_kwargs):
        nonlocal calls
        calls += 1
        pattern = str(command[-1])
        for index in range(1, 4):
            Path(pattern.replace("%02d", f"{index:02d}")).write_bytes(f"frame-{index}".encode())
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(video_screenshots.subprocess, "run", run)
    monkeypatch.setattr(
        video_screenshots,
        "_quality",
        lambda path: (path.name, float(path.stem[-2:]), 960, 540),
    )
    db = SimpleNamespace(commit=lambda: None)
    settings = SimpleNamespace(permanent_dir=tmp_path)
    asset = SimpleNamespace(id="video")
    plan = SimpleNamespace(
        id="shot",
        planned_timestamp_ms=10_000,
        status="PLANNED",
        selection_reason="",
    )
    metrics = {}

    ready, error = video_screenshots.extract_screenshots(
        db, settings, asset, [plan], tmp_path / "video.mp4", metrics
    )

    assert (ready, error, calls) == (1, None, 1)
    assert metrics["screenshot_process_count"] == 1
    assert plan.actual_timestamp_ms == 11_250
