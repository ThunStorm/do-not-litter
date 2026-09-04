"""Add local place editing, manual-place, and review state.

Revision ID: 0012
Revises: 0011
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    place_columns = {item["name"] for item in sa.inspect(bind).get_columns("places")}
    for name, column in (
        (
            "coordinate_source",
            sa.Column("coordinate_source", sa.String(32), nullable=False, server_default="AMAP_POI"),
        ),
        (
            "poi_binding_status",
            sa.Column("poi_binding_status", sa.String(32), nullable=False, server_default="AUTO_CONFIRMED"),
        ),
        ("deleted_at", sa.Column("deleted_at", sa.DateTime(timezone=True))),
        ("revision", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")),
    ):
        if name not in place_columns:
            op.add_column("places", column)
    marker_columns = {item["name"] for item in sa.inspect(bind).get_columns("map_marker_states")}
    for name, column in (
        ("updated_by", sa.Column("updated_by", sa.String(64), nullable=False, server_default="system")),
        ("revision", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")),
    ):
        if name not in marker_columns:
            op.add_column("map_marker_states", column)
    if "place_user_notes" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "place_user_notes",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("markdown", sa.Text(), nullable=False, server_default=""),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(64), nullable=False, server_default="local-user"),
            sa.Column("updated_by", sa.String(64), nullable=False, server_default="local-user"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("place_id", name="uq_place_user_note"),
        )
    if "place_user_overlays" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "place_user_overlays",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
            sa.Column("override_place_type", sa.String(64), nullable=False, server_default=""),
            sa.Column("custom_tags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("place_id", name="uq_place_user_overlay"),
        )


def downgrade() -> None:
    op.drop_table("place_user_overlays")
    op.drop_table("place_user_notes")
    op.drop_column("map_marker_states", "revision")
    op.drop_column("map_marker_states", "updated_by")
    op.drop_column("places", "revision")
    op.drop_column("places", "deleted_at")
    op.drop_column("places", "poi_binding_status")
    op.drop_column("places", "coordinate_source")
