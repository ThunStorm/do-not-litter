from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Setting, SystemEvent
from zhijian.services.audit import record_event


def purge_expired_logs(db: Session) -> dict[str, int]:
    setting = db.get(Setting, "app:general")
    value = setting.value_json if setting and isinstance(setting.value_json, dict) else {}
    try:
        days = max(7, min(3650, int(value.get("data_retention_days") or 90)))
    except (TypeError, ValueError):
        days = 90
    cutoff = utc_now() - timedelta(days=days)
    events = db.execute(delete(SystemEvent).where(SystemEvent.created_at < cutoff)).rowcount or 0
    attempts = (
        db.execute(delete(ExternalCallAudit).where(ExternalCallAudit.created_at < cutoff)).rowcount or 0
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
