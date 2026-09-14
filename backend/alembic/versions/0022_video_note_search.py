"""Create the deterministic Video Note FTS index.

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS video_note_search "
            "USING fts5(note_id UNINDEXED, version_id UNINDEXED, title, body, sections, places, "
            "tokenize='trigram')"
        )
    except Exception:
        op.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS video_note_search "
            "USING fts5(note_id UNINDEXED, version_id UNINDEXED, title, body, sections, places, "
            "tokenize='unicode61')"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS video_note_search")
