"""Add semantic video-map fields and destination knowledge.

Revision ID: 0024
Revises: 0023
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "grounded_map_artifacts" in tables:
        existing = _columns("grounded_map_artifacts")
        for name in ("content_units_json", "entities_json", "relations_json", "claims_json"):
            if name not in existing:
                op.add_column(
                    "grounded_map_artifacts",
                    sa.Column(name, sa.JSON(), nullable=False, server_default="[]"),
                )
    if "place_mentions" in tables:
        existing = _columns("place_mentions")
        additions = (
            ("content_unit_id", sa.String(96), ""),
            ("subject_role", sa.String(32), "LEGACY"),
            ("visit_intent", sa.String(32), "NOT_APPLICABLE"),
            ("poi_policy", sa.String(32), "LEGACY"),
            ("semantic_confidence", sa.Float(), "0"),
        )
        for name, type_, default in additions:
            if name not in existing:
                op.add_column(
                    "place_mentions", sa.Column(name, type_, nullable=False, server_default=default)
                )
    if "destinations" not in tables:
        op.create_table(
            "destinations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("canonical_name", sa.String(300), nullable=False),
            sa.Column("scope_type", sa.String(32), nullable=False, server_default="OTHER"),
            sa.Column("country", sa.String(64), nullable=False, server_default="中国"),
            sa.Column("province", sa.String(64), nullable=False, server_default=""),
            sa.Column("city", sa.String(64), nullable=False, server_default=""),
            sa.Column("district", sa.String(64), nullable=False, server_default=""),
            sa.Column("adcode", sa.String(32), nullable=False, server_default=""),
            sa.Column("center_latitude", sa.Float()),
            sa.Column("center_longitude", sa.Float()),
            sa.Column("external_provider", sa.String(64)),
            sa.Column("external_area_id", sa.String(128)),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("scope_type", "canonical_name", name="uq_destination_scope_name"),
        )
    if "place_mentions" in tables and "destination_id" not in _columns("place_mentions"):
        op.add_column(
            "place_mentions",
            # SQLite cannot add a foreign-key constraint with ALTER TABLE. The
            # application owns this optional link and the table-level links keep
            # their normal constraints on fresh schemas.
            sa.Column("destination_id", sa.String(64)),
        )
    if "destination_place_links" not in tables:
        op.create_table(
            "destination_place_links",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "destination_id",
                sa.String(64),
                sa.ForeignKey("destinations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.id", ondelete="SET NULL")),
            sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="SET NULL")),
            sa.Column(
                "place_mention_id", sa.String(64), sa.ForeignKey("place_mentions.id", ondelete="SET NULL")
            ),
            sa.Column("content_unit_id", sa.String(96), nullable=False, server_default=""),
            sa.Column("relation_type", sa.String(32), nullable=False, server_default="RECOMMENDED_IN"),
            sa.Column("segment_ids_json", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "destination_id",
                "place_id",
                "video_asset_id",
                "content_unit_id",
                name="uq_destination_place_video_unit",
            ),
        )


def downgrade() -> None:
    op.drop_table("destination_place_links")
    op.drop_column("place_mentions", "destination_id")
    op.drop_table("destinations")
    for name in ("semantic_confidence", "poi_policy", "visit_intent", "subject_role", "content_unit_id"):
        op.drop_column("place_mentions", name)
    for name in ("claims_json", "relations_json", "entities_json", "content_units_json"):
        op.drop_column("grounded_map_artifacts", name)
