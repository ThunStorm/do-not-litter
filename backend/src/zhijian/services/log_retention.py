from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Job, JobStepArtifact, Setting, SystemEvent
from zhijian.services.audit import record_event


def purge_expired_logs(db: Session) -> dict[str, int]:
    setting = db.get(Setting, "app:general")
    value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
    try:
        days = max(7, min(3650, int(value.get("data_retention_days") or 90)))
    except (TypeError, ValueError):
        days = 90
    cutoff = utc_now() - timedelta(days=days)
    protected = set(
        db.scalars(
            select(Job.id).where(or_(Job.status.in_(["QUEUED", "RUNNING"]), Job.lease_owner.is_not(None)))
        ).all()
    )
    protected.update(
        db.scalars(
            select(JobStepArtifact.job_id).where(
                JobStepArtifact.status == "AVAILABLE", JobStepArtifact.replayable_until > utc_now()
            )
        ).all()
    )
    event_ids = (
        select(SystemEvent.id)
        .where(
            SystemEvent.created_at < cutoff,
            or_(SystemEvent.entity_id.is_(None), SystemEvent.entity_id.not_in(protected)),
        )
        .order_by(SystemEvent.created_at)
        .limit(500)
    )
    events = db.execute(delete(SystemEvent).where(SystemEvent.id.in_(event_ids))).rowcount or 0
    attempts = (
        db.execute(
            delete(ExternalCallAudit).where(
                ExternalCallAudit.id.in_(
                    select(ExternalCallAudit.id)
                    .where(
                        ExternalCallAudit.created_at < cutoff,
                        ExternalCallAudit.status != "RUNNING",
                        or_(ExternalCallAudit.job_id.is_(None), ExternalCallAudit.job_id.not_in(protected)),
                    )
                    .order_by(ExternalCallAudit.created_at)
                    .limit(500)
                )
            )
        ).rowcount
        or 0
    )
    if events or attempts:
        record_event(
            db,
            "logs.retention.purged",
            "运行日志已按保留策略清理",
            component="worker",
            actor="system",
            detail={"cutoff": cutoff.isoformat(), "system_events": events, "external_call_audits": attempts},
            commit=False,
        )
        db.commit()
    return {"system_events": events, "external_call_audits": attempts}
