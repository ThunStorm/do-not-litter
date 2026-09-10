from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from zhijian.db.models import ExternalCallAudit


def audited_call[T](
    db: Session,
    *,
    job_id: str | None,
    capability: str,
    provider: str,
    operation: str,
    request_meta: dict[str, Any],
    call: Callable[[], T],
    response_meta: Callable[[T], dict[str, Any]] | None = None,
) -> T:
    started = perf_counter()
    try:
        value = call()
    except Exception as exc:
        db.add(
            ExternalCallAudit(
                job_id=job_id,
                capability=capability,
                provider=provider,
                operation=operation,
                status="FAILED",
                duration_ms=round((perf_counter() - started) * 1000),
                request_meta_json=request_meta,
                error_code=getattr(exc, "code", None),
                error_message=str(exc)[:500],
            )
        )
        db.commit()
        raise
    db.add(
        ExternalCallAudit(
            job_id=job_id,
            capability=capability,
            provider=provider,
            operation=operation,
            status="COMPLETED",
            duration_ms=round((perf_counter() - started) * 1000),
            request_meta_json=request_meta,
            response_meta_json=response_meta(value) if response_meta else {},
        )
    )
    db.commit()
    return value
