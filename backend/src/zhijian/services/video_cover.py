from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.core.url_policy import HttpsHostPolicy
from zhijian.db.models import VideoAsset, VideoCoverAsset

COVER_URL_POLICY = HttpsHostPolicy(host_suffixes=frozenset({"hdslb.com", "biliimg.com"}))
MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/avif": "avif"}


def normalize_cover_url(value: str | None) -> str | None:
    if not value:
        return None
    value = "https:" + value if value.startswith("//") else value.replace("http://", "https://", 1)
    if not COVER_URL_POLICY.allows(value):
        return None
    return value


def materialize_cover(db: Session, settings: Settings, asset: VideoAsset) -> VideoCoverAsset | None:
    existing = db.query(VideoCoverAsset).filter_by(video_asset_id=asset.id).one_or_none()
    if (
        existing
        and existing.status == "READY"
        and existing.derivative_path
        and Path(existing.derivative_path).is_file()
    ):
        return existing
    source_url = normalize_cover_url(asset.cover_url)
    cover = existing or VideoCoverAsset(video_asset_id=asset.id, source_url=source_url or "")
    if not existing:
        db.add(cover)
    if not source_url:
        cover.status, cover.error_code = "UNAVAILABLE", "COVER_URL_INVALID"
        db.commit()
        return cover
    try:
        response = httpx.get(
            source_url,
            headers={"Referer": "https://www.bilibili.com", "User-Agent": "Mozilla/5.0"},
            timeout=20,
            follow_redirects=False,
        )
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        content = response.content
        if (
            response.status_code != 200
            or content_type not in MIME_EXT
            or not content
            or len(content) > 12 * 1024 * 1024
        ):
            raise ValueError("COVER_RESPONSE_INVALID")
        digest = hashlib.sha256(content).hexdigest()
        directory = settings.permanent_dir / "video-covers"
        derivative_dir = directory / "derivatives"
        directory.mkdir(parents=True, exist_ok=True)
        derivative_dir.mkdir(parents=True, exist_ok=True)
        original = directory / f"{digest}.{MIME_EXT[content_type]}"
        original.write_bytes(content) if not original.exists() else None
        derivative = derivative_dir / f"{digest}-672x378.webp"
        with Image.open(original) as image:
            image.verify()
        with Image.open(original) as image:
            width, height = image.size
            image.convert("RGB").resize((672, 378)).save(derivative, "WEBP", quality=84)
        cover.source_url, cover.local_path, cover.derivative_path = source_url, str(original), str(derivative)
        cover.content_hash = digest
        cover.content_type = content_type
        cover.width, cover.height, cover.byte_size = width, height, len(content)
        cover.status, cover.error_code = "READY", None
    except Exception as exc:
        cover.status, cover.error_code = "UNAVAILABLE", str(exc)[:64]
    db.commit()
    return cover
