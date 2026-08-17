from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.db.models import Job, Source
from zhijian.domain.enums import JobStatus
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
) -> tuple[Source, Job]:
    job_type = classify_capture(locator, title, text)
    source = Source(
        source_type=source_type,
        locator=locator,
        title=title or None,
        metadata_json=metadata or {},
    )
    db.add(source)
    db.flush()
    payload = {
        "source_id": source.id,
        "locator": locator,
        "title": title,
        "text": text,
        "file_path": str(file_path) if file_path else None,
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
