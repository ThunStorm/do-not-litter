"""Ephemeral authority projection; never a second review queue."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.db.models import AINoteVersion, Job, JobStep, PlaceMention
from zhijian.services.jobs import COOLDOWN_RESUME_KEY


def review_projection(db: Session, mode: str = "ALL") -> dict:
    jobs = {j.id: j for j in db.scalars(select(Job).where(Job.job_type != "MODEL_TEST"))}
    steps = db.scalars(select(JobStep).where(JobStep.status.in_(["FAILED", "NEEDS_USER"]))).all()
    issues = {}
    failed_jobs = set()
    for step in steps:
        job = jobs.get(step.job_id)
        if not job or job.status not in {"FAILED", "NEEDS_USER"}:
            continue
        key = f"STEP:{step.id}:{job.retry_count}:{step.version}"
        issues[key] = dict(
            key=key,
            job_id=job.id,
            kind="MANUAL",
            reason=job.error_code or "STEP_FAILED",
            label=step.error or job.error or "步骤需要处理",
            href=f"/tasks/{job.id}",
        )
        failed_jobs.add(job.id)
    for job in jobs.values():
        waiting = job.status == "QUEUED" and COOLDOWN_RESUME_KEY in job.payload_json
        if waiting or (job.status in {"FAILED", "NEEDS_USER"} and job.id not in failed_jobs):
            key = f"JOB:{job.id}:{job.retry_count}"
            issues[key] = dict(
                key=key,
                job_id=job.id,
                kind="WAIT" if waiting else "MANUAL",
                reason="AUTO_COOLDOWN" if waiting else job.error_code or "JOB_NEEDS_ATTENTION",
                label="后台冷却，到期自动继续，无需人工操作" if waiting else job.error or "任务需要处理",
                href=f"/tasks/{job.id}",
            )
    versions = {v.id: v for v in db.scalars(select(AINoteVersion))}
    mentions = db.scalars(
        select(PlaceMention).where(
            PlaceMention.resolution_status.in_(["REVIEW", "UNRESOLVED"]),
            PlaceMention.extraction_status == "EXTRACTED",
            PlaceMention.poi_policy.in_(["RESOLVE", "LEGACY"]),
        )
    )
    for m in mentions:
        version = versions.get(m.ai_note_version_id)
        key = f"POI:{m.id}:{m.ai_note_version_id or 'UNKNOWN'}"
        owner = jobs.get(m.submission_job_id)
        active = bool(owner and (owner.status in {"QUEUED", "RUNNING"} or owner.lease_owner))
        issues[key] = dict(
            key=key,
            job_id=m.submission_job_id,
            kind="WAIT" if active else "MANUAL",
            reason="POI_REVIEW",
            label=f"{m.raw_name or m.name}："
            + ("所属任务处理中，等待完成后复核" if active else "地点位置待确认"),
            href=f"/place-reviews?mention={m.id}",
            version_id=version.id if version else None,
        )
    values = [i for i in issues.values() if mode == "ALL" or i["kind"] == mode]
    manual = [i for i in issues.values() if i["kind"] == "MANUAL"]
    return dict(
        version="review-projection-v1",
        issues=values,
        issue_count=len(values),
        task_count=len({i["job_id"] for i in values if i["job_id"] in jobs}),
        unknown_task_count=sum(i["job_id"] not in jobs for i in values),
        manual_issue_count=len(manual),
        manual_task_count=len({i["job_id"] for i in manual if i["job_id"] in jobs}),
        waiting_issue_count=sum(i["kind"] == "WAIT" for i in issues.values()),
    )
