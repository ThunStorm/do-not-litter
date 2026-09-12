from __future__ import annotations

from datetime import timedelta

from zhijian.core.time import utc_now
from zhijian.db.models import ExternalCallAudit, Setting, SystemEvent
from zhijian.services.log_retention import purge_expired_logs


def test_purge_expired_logs_uses_general_retention_and_keeps_recent_events(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        db.add(Setting(key="app:general", value_json={"data_retention_days": 7}))
        old = utc_now() - timedelta(days=8)
        recent = utc_now() - timedelta(days=1)
        db.add_all(
            [
                SystemEvent(
                    id="evt_old",
                    created_at=old,
                    component="test",
                    event_type="test.old",
                    message="old",
                    detail_json={},
                ),
                SystemEvent(
                    id="evt_recent",
                    created_at=recent,
                    component="test",
                    event_type="test.recent",
                    message="recent",
                    detail_json={},
                ),
                ExternalCallAudit(
                    id="xca_old",
                    created_at=old,
                    updated_at=old,
                    capability="LLM",
                    provider="test",
                    operation="test",
                    status="FAILED",
                    request_meta_json={},
                    response_meta_json={},
                ),
            ]
        )
        db.commit()

        result = purge_expired_logs(db)

        assert result == {"system_events": 1, "external_call_audits": 1}
        assert db.get(SystemEvent, "evt_old") is None
        assert db.get(SystemEvent, "evt_recent") is not None
        assert db.get(ExternalCallAudit, "xca_old") is None
