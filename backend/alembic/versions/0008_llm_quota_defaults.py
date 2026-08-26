"""Apply safer AI request defaults to untouched installations.

Revision ID: 0008
Revises: 0007
"""
from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT value_json FROM settings WHERE key = 'app:general'")).first()
    if row is None:
        return
    value = json.loads(row[0]) if isinstance(row[0], str) else dict(row[0] or {})
    if value.get("ai_retry_count", 2) == 2 and value.get("ai_request_interval_seconds", 1) == 1:
        value.update(ai_retry_count=1, ai_request_interval_seconds=3)
        bind.execute(
            sa.text("UPDATE settings SET value_json = :value WHERE key = 'app:general'"),
            {"value": json.dumps(value, ensure_ascii=False)},
        )


def downgrade() -> None:
    pass
