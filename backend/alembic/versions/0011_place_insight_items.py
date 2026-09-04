"""Add durable, evidence-linked place insight items.

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "place_insight_items" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "place_insight_items",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "place_mention_id", sa.String(64), sa.ForeignKey("place_mentions.id", ondelete="CASCADE")
            ),
            sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.id", ondelete="SET NULL")),
            sa.Column("insight_type", sa.String(64), nullable=False),
            sa.Column("value_key", sa.String(128), nullable=False, server_default=""),
            sa.Column("value_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("provenance", sa.String(32), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
            sa.Column(
                "supersedes_id", sa.String(64), sa.ForeignKey("place_insight_items.id", ondelete="SET NULL")
            ),
            sa.Column("segment_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_by", sa.String(64), nullable=False, server_default="system"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_place_insights_place_status", "place_insight_items", ["place_id", "status"])
    # SQLite is the supported runtime.  Legacy brief values are retained as
    # source facts only when their original mention still has Segment evidence.
    for insight_type, key in (
        ("HIGHLIGHT", "feature"),
        ("RECOMMENDED_ITEM", "experience"),
        ("PRICE", "price"),
        ("QUEUE", "queue"),
        ("AUDIENCE", "audience"),
        ("WARNING", "warning"),
        ("AUTHOR_OPINION", "author_opinion"),
    ):
        bind.exec_driver_sql(f"""
            INSERT INTO place_insight_items (
                id, place_id, place_mention_id, source_id, insight_type, value_key, value_text,
                value_json, provenance, confidence, status, segment_ids_json, metadata_json,
                created_by, created_at, updated_at
            )
            SELECT
                'ins_' || lower(hex(randomblob(16))), pm.place_id, pm.id, va.source_id,
                '{insight_type}', '{key}', json_extract(pm.brief_json, '$.{key}'), '{{}}',
                CASE WHEN json_array_length(pm.segment_ids_json) > 0
                    THEN 'SOURCE_FACT'
                    ELSE 'LEGACY_UNVERIFIED'
                END,
                pm.confidence, 'ACTIVE', pm.segment_ids_json,
                CASE WHEN json_array_length(pm.segment_ids_json) > 0
                    THEN '{{}}'
                    ELSE '{{"legacy_unverified":true}}'
                END,
                'migration:0011', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM place_mentions pm
            LEFT JOIN video_assets va ON va.id = pm.video_asset_id
            WHERE pm.place_id IS NOT NULL
              AND COALESCE(json_extract(pm.brief_json, '$.{key}'), '') <> ''
              AND NOT EXISTS (
                SELECT 1 FROM place_insight_items existing
                WHERE existing.place_mention_id = pm.id
                  AND existing.insight_type = '{insight_type}'
                  AND existing.value_key = '{key}'
              )
        """)


def downgrade() -> None:
    op.drop_index("ix_place_insights_place_status", table_name="place_insight_items")
    op.drop_table("place_insight_items")
