from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from zhijian.ai.job_config import SNAPSHOT_KEY, capture_ai_config
from zhijian.core.config import Settings
from zhijian.db.models import Job, Source
from zhijian.domain.enums import JobStatus, JobType
from zhijian.resolvers.video import is_bilibili_url, is_youtube_url
from zhijian.services.classifier import classify_capture


def create_capture_job(
    db: Session,
    settings: Settings,
    *,
    locator: str,
    source_type: str,
    title: str = "",
    text: str = "",
    file_path: Path | None = None,
    metadata: dict | None = None,
    ai_overrides: dict | None = None,
    asr_provider: str | None = None,
) -> tuple[Source, Job]:
    is_local_video = bool(
        source_type == "FILE"
        and file_path
        and file_path.suffix.lower() in {".mp4", ".mov", ".webm", ".m4v"}
    )
    is_youtube = source_type == "URL" and is_youtube_url(locator)
    is_video = (source_type == "URL" and (is_bilibili_url(locator) or is_youtube)) or is_local_video
    job_type = JobType.TRAVEL if is_video else classify_capture(locator, title, text)
    source = Source(
        source_type=source_type,
        locator=locator,
        title=title or None,
        metadata_json=metadata or {},
    )
    db.add(source)
    db.flush()
    snapshot = capture_ai_config(db, settings)
    needs_asr = is_video or bool(
        file_path and file_path.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac"}
    )
    payload = {
        "source_id": source.id,
        "locator": locator,
        "title": title,
        "text": text,
        "file_path": str(file_path) if file_path else None,
        "video_platform": (
            "LOCAL" if is_local_video else "YOUTUBE" if is_youtube else "BILIBILI" if is_video else None
        ),
        "ai_overrides": ai_overrides or {},
        "asr_provider": (asr_provider or snapshot["default_asr_provider"]) if needs_asr else None,
        "ai_automation_version": "v2",
        SNAPSHOT_KEY: snapshot,
    }
    job = Job(job_type=job_type.value, status=JobStatus.QUEUED.value, payload_json=payload)
    db.add(job)
    db.commit()
    db.refresh(source)
    db.refresh(job)
    return source, job


def safe_upload_path(settings: Settings, filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix.lower()[:12]
    digest = hashlib.sha256(content).hexdigest()
    path = settings.permanent_dir / "sources" / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(content)
    return path
