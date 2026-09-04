"""Move legacy transcript routing into the transcript stage policy.

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _json(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def upgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT value_json FROM settings WHERE key = 'model-routing'")).first()
    routes = _json(row[0]) if row else {}
    legacy_ids = [routes.get("transcript_primary_id"), routes.get("transcript_fallback_id")]
    if not any(legacy_ids):
        return
    profiles = {
        key.removeprefix("model-profile:"): _json(value)
        for key, value in bind.execute(
            sa.text("SELECT key, value_json FROM settings WHERE key LIKE 'model-profile:%'")
        )
    }
    stage_key = "ai-stage-policy:TRANSCRIPT_CORRECTION"
    stage_row = bind.execute(
        sa.text("SELECT value_json FROM settings WHERE key = :key"), {"key": stage_key}
    ).first()
    policy = _json(stage_row[0]) if stage_row else {}
    for profile_id in legacy_ids:
        if not profile_id:
            continue
        profile = profiles.get(profile_id, {})
        is_local = profile.get("location") == "LOCAL" or str(profile.get("provider", "")).lower() == "ollama"
        field = "local_profile_id" if is_local else "remote_profile_id"
        policy.setdefault(field, profile_id)
    policy["version"] = int(policy.get("version") or 0) + 1
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value_json", sa.JSON),
        sa.column("is_secret_ref", sa.Boolean),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    if stage_row:
        bind.execute(
            settings.update()
            .where(settings.c.key == stage_key)
            .values(value_json=policy, updated_at=datetime.now(UTC))
        )
    else:
        op.bulk_insert(
            settings,
            [
                {
                    "key": stage_key,
                    "value_json": policy,
                    "is_secret_ref": False,
                    "updated_at": datetime.now(UTC),
                }
            ],
        )
    legacy_keys = {"transcript_primary_id", "transcript_fallback_id"}
    cleaned = {key: value for key, value in routes.items() if key not in legacy_keys}
    bind.execute(
        settings.update()
        .where(settings.c.key == "model-routing")
        .values(value_json=cleaned, updated_at=datetime.now(UTC))
    )


def downgrade() -> None:
    # The old dual-routing semantics are intentionally not recreated.
    pass
