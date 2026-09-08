"""Add correlated visit windows and hard-delete suppression.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "place_visit_windows" not in tables:
        op.create_table(
            "place_visit_windows",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "place_mention_id", sa.String(64), sa.ForeignKey("place_mentions.id", ondelete="SET NULL")
            ),
            sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.id", ondelete="SET NULL")),
            sa.Column("season", sa.String(16)),
            sa.Column("month", sa.Integer()),
            sa.Column("month_segment", sa.String(16)),
            sa.Column("day_time_slot", sa.String(32)),
            sa.Column("source_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("provenance", sa.String(32), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("month IS NULL OR month BETWEEN 1 AND 12", name="ck_visit_window_month"),
        )
        op.create_index("ix_place_visit_window_place_status", "place_visit_windows", ["place_id", "status"])
        op.create_index(
            "ix_place_visit_window_time",
            "place_visit_windows",
            ["season", "month", "month_segment", "status"],
        )
        op.create_index("ix_place_visit_window_slot", "place_visit_windows", ["day_time_slot", "status"])
    if "place_deletion_tombstones" not in tables:
        op.create_table(
            "place_deletion_tombstones",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("external_provider", sa.String(64)),
            sa.Column("external_poi_id", sa.String(128)),
            sa.Column("normalized_name", sa.String(300), nullable=False, server_default=""),
            sa.Column("former_place_id", sa.String(64), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reason", sa.String(500), nullable=False, server_default="用户永久删除"),
        )
        op.create_index(
            "ix_place_tombstone_provider_poi",
            "place_deletion_tombstones",
            ["external_provider", "external_poi_id"],
        )
    # Legacy facts deliberately become separate rows: no implied correlation.
    for insight, column in (
        ("BEST_MONTH", "month"),
        ("BEST_SEASON", "season"),
        ("BEST_TIME_SLOT", "day_time_slot"),
    ):
        rows = bind.execute(
            sa.text(
                "SELECT id, place_id, place_mention_id, source_id, value_key, value_text, provenance, confidence, status, created_at, updated_at FROM place_insight_items WHERE insight_type = :kind AND status = 'ACTIVE'"
            ),
            {"kind": insight},
        ).mappings()
        for row in rows:
            value = row["value_key"] or row["value_text"]
            parsed = int(value) if column == "month" and str(value).isdigit() else value
            bind.execute(
                sa.text(
                    f"INSERT INTO place_visit_windows (id, place_id, place_mention_id, source_id, {column}, source_text, provenance, confidence, status, created_at, updated_at) VALUES (:id, :place_id, :mention_id, :source_id, :value, :source_text, :provenance, :confidence, 'ACTIVE', :created_at, :updated_at)"
                ),
                {
                    "id": f"pvw_legacy_{row['id']}",
                    "place_id": row["place_id"],
                    "mention_id": row["place_mention_id"],
                    "source_id": row["source_id"],
                    "value": parsed,
                    "source_text": row["value_text"],
                    "provenance": row["provenance"],
                    "confidence": row["confidence"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            )


def downgrade() -> None:
    op.drop_table("place_deletion_tombstones")
    op.drop_table("place_visit_windows")
