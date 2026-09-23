"""Keep separate notes and mentions for each submission of one video.

Revision ID: 0025
Revises: 0024
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    note_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("ai_notes")}
    if "submission_job_id" not in note_columns:
        # 0003 created an anonymous SQLite UNIQUE(video_asset_id), which
        # batch.drop_constraint cannot identify. Copy all Note IDs unchanged.
        op.create_table(
            "ai_notes_new",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "video_asset_id",
                sa.String(64),
                sa.ForeignKey("video_assets.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("submission_job_id", sa.String(64)),
            sa.Column("current_version_id", sa.String(64)),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("submission_job_id", name="uq_ai_note_submission_job"),
        )
        op.execute(
            "INSERT INTO ai_notes_new "
            "(id, video_asset_id, current_version_id, status, created_at, updated_at) "
            "SELECT id, video_asset_id, current_version_id, status, created_at, updated_at FROM ai_notes"
        )
        op.drop_table("ai_notes")
        op.rename_table("ai_notes_new", "ai_notes")
    mention_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("place_mentions")}
    if "submission_job_id" not in mention_columns:
        op.add_column("place_mentions", sa.Column("submission_job_id", sa.String(64)))
    op.create_index(
        "ix_place_mentions_submission_job", "place_mentions", ["submission_job_id"], if_not_exists=True
    )


def downgrade() -> None:
    duplicate = (
        op.get_bind()
        .exec_driver_sql(
            "SELECT video_asset_id FROM ai_notes GROUP BY video_asset_id HAVING count(*) > 1 LIMIT 1"
        )
        .first()
    )
    if duplicate:
        raise RuntimeError("同一视频已有多篇笔记，不能恢复旧版唯一约束")
    op.drop_index("ix_place_mentions_submission_job", table_name="place_mentions")
    op.drop_column("place_mentions", "submission_job_id")
    op.create_table(
        "ai_notes_old",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "video_asset_id",
            sa.String(64),
            sa.ForeignKey("video_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_version_id", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_asset_id", name="uq_ai_note_video_asset"),
    )
    op.execute(
        "INSERT INTO ai_notes_old (id, video_asset_id, current_version_id, status, created_at, updated_at) "
        "SELECT id, video_asset_id, current_version_id, status, created_at, updated_at FROM ai_notes"
    )
    op.drop_table("ai_notes")
    op.rename_table("ai_notes_old", "ai_notes")
