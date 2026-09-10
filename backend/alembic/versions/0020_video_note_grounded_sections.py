"""Add explicit grounded-video-note section evidence.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ai_note_sections")}
    additions = (
        ("section_kind", sa.Column("section_kind", sa.String(32), nullable=False, server_default="SUPPLEMENTAL")),
        ("place_mention_ids_json", sa.Column("place_mention_ids_json", sa.JSON(), nullable=False, server_default="[]")),
        ("evidence_quotes_json", sa.Column("evidence_quotes_json", sa.JSON(), nullable=False, server_default="[]")),
    )
    for name, column in additions:
        if name not in columns:
            op.add_column("ai_note_sections", column)


def downgrade() -> None:
    for name in ("evidence_quotes_json", "place_mention_ids_json", "section_kind"):
        op.drop_column("ai_note_sections", name)
