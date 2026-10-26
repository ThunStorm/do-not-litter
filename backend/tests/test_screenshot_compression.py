import base64
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageStat

from zhijian.core.config import Settings
from zhijian.db.models import Job, Source, VideoAsset, VideoScreenshot
from zhijian.services import video_screenshots, visual_facts


@pytest.fixture
def screenshot_path(tmp_path):
    image = Image.new("RGB", (512, 288))
    image.putdata(
        [
            (40 + x // 3, 50 + y // 2, 80 + (x + y) // 5)
            for y in range(image.height)
            for x in range(image.width)
        ]
    )
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 280, 120), fill="white", outline="black", width=2)
    draw.text((45, 45), "MENU / OPEN 09:00-18:00", fill="black")
    draw.text((45, 75), "PRICE 128 / ROAD 205", fill="red")
    for x in range(0, 512, 12):
        draw.line((x, 155, x, 270), fill="white", width=1)
    path = tmp_path / "shot.jpg"
    image.save(path, quality=97, subsampling=0)
    return path


@pytest.mark.parametrize("sampling", [0, 2])
def test_compression_reduces_size_and_preserves_resolution_and_detail(screenshot_path, sampling):
    if sampling == 2:
        with Image.open(screenshot_path) as image:
            source = image.convert("RGB")
        source.save(screenshot_path, quality=97, subsampling=2)
    original = screenshot_path.read_bytes()
    with Image.open(screenshot_path) as image:
        source = image.convert("RGB")

    compressed = video_screenshots._compress_screenshot(screenshot_path)

    assert compressed.suffix == ".webp"
    assert compressed.stat().st_size <= len(original) * 0.95
    assert not screenshot_path.exists()
    with Image.open(compressed) as image:
        assert image.format == "WEBP"
        assert image.size == source.size
        difference = ImageChops.difference(source, image.convert("RGB"))
    # 38 dB corresponds to RGB mean squared pixel error <= 10.31.
    assert sum(ImageStat.Stat(difference).sum2) / (512 * 288 * 3) <= 10.31
    if sampling == 0:
        # Thin colored text needs the lossless fallback: lossy WebP always subsamples chroma.
        assert difference.getbbox() is None


@pytest.mark.parametrize("reason", ["quality", "size", "codec", "disk"])
def test_compression_failure_or_no_benefit_keeps_original(screenshot_path, monkeypatch, reason):
    original = screenshot_path.read_bytes()
    if reason == "quality":
        monkeypatch.setattr(video_screenshots, "_screenshot_psnr", lambda *_args: 0)
    elif reason == "size":
        monkeypatch.setattr(
            Image.Image, "save", lambda _image, output, **_kwargs: output.write(b"x" * len(original))
        )
    elif reason == "codec":

        def fail(*_args, **_kwargs):
            raise OSError("WebP codec unavailable")

        monkeypatch.setattr(Image.Image, "save", fail)
    else:
        write_bytes = Path.write_bytes

        def fail(path, data):
            write_bytes(path, data[:10])
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_bytes", fail)

    assert video_screenshots._compress_screenshot(screenshot_path) == screenshot_path
    assert screenshot_path.read_bytes() == original
    assert not screenshot_path.with_suffix(".webp").exists()
    assert not screenshot_path.with_suffix(".webp.tmp").exists()


def test_extraction_registers_compressed_path_and_final_file_hash(screenshot_path, tmp_path, monkeypatch):
    original = screenshot_path.read_bytes()

    def run(command, **_kwargs):
        for index in range(1, 4):
            Path(str(command[-1]).replace("%02d", f"{index:02d}")).write_bytes(original)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(video_screenshots.subprocess, "run", run)
    plan = SimpleNamespace(id="shot", planned_timestamp_ms=10_000, status="PLANNED")
    ready, error = video_screenshots.extract_screenshots(
        SimpleNamespace(commit=lambda: None),
        SimpleNamespace(permanent_dir=tmp_path, data_dir=tmp_path),
        SimpleNamespace(id="video"),
        [plan],
        tmp_path / "video.mp4",
    )

    from zhijian.core.storage import resolve_ref

    path = resolve_ref(plan.image_path, SimpleNamespace(data_dir=tmp_path))
    assert (ready, error, plan.status) == (1, None, "READY")
    assert path.suffix == ".webp"
    assert path.stat().st_size < len(original)
    assert plan.content_hash == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (plan.width, plan.height) == (512, 288)
    assert list(path.parent.iterdir()) == [path]


def _store_screenshot(factory, path):
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://compression")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url="fixture://compression")
        db.add(asset)
        db.flush()
        shot = VideoScreenshot(
            video_asset_id=asset.id, planned_timestamp_ms=0, status="READY", image_path=str(path)
        )
        db.add(shot)
        db.commit()
        return shot.id


@pytest.mark.parametrize("compressed", [False, True])
def test_image_endpoint_serves_old_jpeg_and_new_webp(client, app_and_session, screenshot_path, compressed):
    path = video_screenshots._compress_screenshot(screenshot_path) if compressed else screenshot_path
    _, factory = app_and_session
    screenshot_id = _store_screenshot(factory, path)

    response = client.get(f"/api/video-screenshots/{screenshot_id}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == ("image/webp" if compressed else "image/jpeg")
    assert response.content == path.read_bytes()


@pytest.mark.parametrize("compressed", [False, True])
def test_vision_request_uses_actual_image_format(app_and_session, screenshot_path, monkeypatch, compressed):
    path = video_screenshots._compress_screenshot(screenshot_path) if compressed else screenshot_path
    _, factory = app_and_session
    screenshot_id = _store_screenshot(factory, path)
    captured = {}
    monkeypatch.setattr(visual_facts, "_vision_profile", lambda *_args: True)
    monkeypatch.setattr(visual_facts, "provider_for_role", lambda *_args: (object(), "fixture", "vision"))

    def execute(_gateway, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(content='{"facts":[]}')

    monkeypatch.setattr(visual_facts.AIWorkloadGateway, "execute_cached_json", execute)
    with factory() as db:
        job = Job(
            job_type="TRAVEL", status="QUEUED", payload_json={"visual_fact_screenshot_id": screenshot_id}
        )
        db.add(job)
        db.commit()
        visual_facts.process_visual_fact_job(db, job, Settings(_env_file=None, data_dir=path.parent))
        assert job.status == "COMPLETED"

    url = captured["messages"][1]["content"][1]["image_url"]["url"]
    media_type = "image/webp" if compressed else "image/jpeg"
    assert url == f"data:{media_type};base64,{base64.b64encode(path.read_bytes()).decode()}"
