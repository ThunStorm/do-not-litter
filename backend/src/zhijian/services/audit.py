from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from zhijian.db.models import SystemEvent


def record_event(
    db: Session,
    event_type: str,
    message: str,
    *,
    component: str = "api",
    level: str = "INFO",
    actor: str = "local-user",
    entity_type: str | None = None,
    entity_id: str | None = None,
    request_id: str | None = None,
    detail: dict[str, Any] | None = None,
    commit: bool = True,
) -> SystemEvent:
    event = SystemEvent(
        level=level.upper(),
        component=component,
        event_type=event_type,
        message=message[:500],
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        detail_json=detail or {},
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event
