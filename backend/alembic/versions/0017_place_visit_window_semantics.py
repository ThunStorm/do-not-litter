"""Add evidence-bound visit-window semantics.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("place_visit_windows")}
    if "period_type" not in columns:
        op.add_column(
            "place_visit_windows",
            sa.Column("period_type", sa.String(32), nullable=False, server_default="BEST_VISIT"),
        )
    if "suitability" not in columns:
        op.add_column(
            "place_visit_windows",
            sa.Column("suitability", sa.String(16), nullable=False, server_default="INFORMATIONAL"),
        )
    if "segment_ids_json" not in columns:
        op.add_column(
            "place_visit_windows",
            sa.Column("segment_ids_json", sa.JSON(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    op.drop_column("place_visit_windows", "segment_ids_json")
    op.drop_column("place_visit_windows", "suitability")
    op.drop_column("place_visit_windows", "period_type")
