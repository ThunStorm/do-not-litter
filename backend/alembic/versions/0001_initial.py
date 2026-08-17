"""Initial local-first schema.

Revision ID: 0001
Revises:
Create Date: 2026-08-18
"""
from __future__ import annotations

from alembic import op

from zhijian.db.base import Base
from zhijian.db import models  # noqa: F401


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
