from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import (
    Claim,
    ContentItem,
    Evidence,
    Job,
    JobStep,
    Place,
    Segment,
    Snapshot,
)
from zhijian.domain.enums import ContentType, JobStatus, JobType, ResolutionStatus
from zhijian.services.audit import record_event
from zhijian.services.classifier import classify_capture
from zhijian.services.resolver import resolve_payload

STEPS = ("RECEIVED", "RESOLVE", "SEGMENT", "EXTRACT", "MATERIALIZE")


def _upsert_step(db: Session, job: Job, name: str, progress: int, status: str) -> JobStep:
    step = db.scalar(select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == name))
    if step is None:
        step = JobStep(job_id=job.id, step_name=name, status=status, progress=progress)
        db.add(step)
    step.status = status
    step.progress = progress
    if status == "RUNNING" and step.started_at is None:
        step.started_at = utc_now()
    if status == "COMPLETED":
        step.finished_at = utc_now()
    job.current_step = name
    job.progress = progress
    job.heartbeat_at = utc_now()
    db.commit()
    return step


def _extract_recruitment(text: str) -> dict:
    deadline_patterns = (
        r"(?:报名|截止)[^。\n]{0,20}?(20\d{2}[年\-/]\d{1,2}[月\-/]\d{1,2}日?(?:\s*\d{1,2}[:：]\d{2})?)",
        r"(20\d{2}年\d{1,2}月\d{1,2}日\s*\d{1,2}[:：]\d{2})前",
    )
    deadline = None
    for pattern in deadline_patterns:
        match = re.search(pattern, text)
        if match:
            deadline = match.group(1)
            break
    degree = "本科及以上" if "本科" in text else None
    positions = None
    position_match = re.search(r"(?:招聘|设置)[^。\n]{0,12}?(\d{1,4})\s*个?岗位", text)
    if position_match:
        positions = int(position_match.group(1))
    return {
        "deadline": deadline,
        "degree": degree,
        "position_count": positions,
        "eligibility": [
            {"label": "学历", "value": degree or "信息不足", "status": "REVIEW" if degree else "UNKNOWN"},
            {"label": "应届身份", "value": "需要个人档案确认", "status": "REVIEW"},
        ],
    }


def _extract_travel(text: str) -> dict:
    mentions = []
    for match in re.finditer(r"([\u4e00-\u9fff]{2,18}(?:店|馆|餐厅|景区|公园|古镇|山|湖))", text):
        name = match.group(1)
        if name not in mentions:
            mentions.append(name)
        if len(mentions) >= 12:
            break
    return {"place_mentions": mentions, "observation_count": len(mentions)}


def process_job(db: Session, job: Job) -> None:
    if job.payload_json.get("video_platform") == "BILIBILI":
        from zhijian.services.video_pipeline import process_video_job

        process_video_job(db, job)
        return
    job.status = JobStatus.RUNNING.value
    job.started_at = job.started_at or utc_now()
    db.commit()
    try:
        _upsert_step(db, job, "RECEIVED", 10, "COMPLETED")
        _upsert_step(db, job, "RESOLVE", 25, "RUNNING")
        text, raw_segments, resolve_meta = resolve_payload(job.payload_json)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        snapshot = Snapshot(
            source_id=job.payload_json["source_id"],
            content_hash=content_hash,
            metadata_json=resolve_meta,
        )
        db.add(snapshot)
        db.flush()
        if job.job_type == JobType.UNKNOWN.value:
            inferred_type = classify_capture(
                str(job.payload_json.get("locator", "")),
                str(job.payload_json.get("title", "")),
                text,
            )
            job.job_type = inferred_type.value
        _upsert_step(db, job, "RESOLVE", 35, "COMPLETED")

        _upsert_step(db, job, "SEGMENT", 45, "RUNNING")
        segment_models: list[Segment] = []
        for index, item in enumerate(raw_segments[:3000]):
            segment = Segment(
                snapshot_id=snapshot.id,
                ordinal=index,
                locator_json=item.get("locator", {}),
                text=item.get("text", ""),
                confidence=item.get("confidence"),
            )
            db.add(segment)
            segment_models.append(segment)
        db.flush()
        _upsert_step(db, job, "SEGMENT", 58, "COMPLETED")

        _upsert_step(db, job, "EXTRACT", 68, "RUNNING")
        title = job.payload_json.get("title") or _title_from_text(text)
        if job.job_type == JobType.RECRUITMENT.value:
            structured = _extract_recruitment(text)
            content_type = ContentType.RECRUITMENT.value
            summary = "已提取报名时间、学历与岗位信息；存在歧义的条件保留为待确认。"
        elif job.job_type == JobType.TRAVEL.value:
            structured = _extract_travel(text)
            content_type = ContentType.TRAVEL.value
            summary = "已提取地点候选与来源观察，坐标需经 POI Provider 确认。"
        else:
            structured = {"reason": "当前第一版只处理招聘与旅行内容"}
            content_type = ContentType.UNSUPPORTED.value
            summary = "已保存来源，但当前 Processor 不支持该内容。"
        _upsert_step(db, job, "EXTRACT", 82, "COMPLETED")

        _upsert_step(db, job, "MATERIALIZE", 90, "RUNNING")
        content = ContentItem(
            content_type=content_type,
            title=title,
            summary=summary,
            source_id=job.payload_json["source_id"],
            status="COMPLETED" if content_type != ContentType.UNSUPPORTED.value else "UNSUPPORTED",
            structured_json=structured,
        )
        db.add(content)
        db.flush()
        _materialize_evidence(db, content, structured, segment_models)
        if content_type == ContentType.TRAVEL.value:
            _materialize_unresolved_places(db, content, structured)
        job.result_content_id = content.id
        job.status = JobStatus.COMPLETED.value
        job.progress = 100
        job.current_step = "MATERIALIZE"
        job.finished_at = utc_now()
        job.lease_owner = None
        job.lease_expire_at = None
        _upsert_step(db, job, "MATERIALIZE", 100, "COMPLETED")
        record_event(
            db,
            "job.completed",
            f"任务处理完成：{title}",
            component="worker",
            entity_type="job",
            entity_id=job.id,
            detail={"content_id": content.id, "content_type": content_type},
            commit=False,
        )
        db.commit()
    except Exception as exc:
        job.status = JobStatus.FAILED.value
        job.error = str(exc)[:4000]
        job.finished_at = utc_now()
        job.lease_owner = None
        job.lease_expire_at = None
        record_event(
            db,
            "job.failed",
            f"任务处理失败：{str(exc)[:240]}",
            component="worker",
            level="ERROR",
            entity_type="job",
            entity_id=job.id,
            commit=False,
        )
        db.commit()
        raise


def _title_from_text(text: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "未命名内容")
    return first_line[:120]


def _materialize_evidence(
    db: Session, content: ContentItem, structured: dict, segments: list[Segment]
) -> None:
    if not segments:
        return
    first_segment = segments[0]
    for predicate, value in list(structured.items())[:8]:
        if value in (None, [], {}):
            continue
        claim = Claim(
            subject_type="CONTENT",
            subject_id=content.id,
            predicate=predicate,
            value_json={"value": value},
        )
        db.add(claim)
        db.flush()
        db.add(
            Evidence(
                claim_id=claim.id,
                segment_id=first_segment.id,
                quote=first_segment.text[:500],
                locator_json=first_segment.locator_json,
            )
        )


def _materialize_unresolved_places(db: Session, content: ContentItem, structured: dict) -> None:
    for name in structured.get("place_mentions", []):
        db.add(
            Place(
                content_item_id=content.id,
                name=name,
                place_type="UNKNOWN",
                latitude=0,
                longitude=0,
                resolution_status=ResolutionStatus.UNRESOLVED.value,
                summary="等待高德 POI 确认",
            )
        )
