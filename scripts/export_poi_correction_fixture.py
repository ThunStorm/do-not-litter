"""Export manually confirmed POI decisions as reviewable Golden-fixture drafts.

The script is read-only: it never calls a Provider, changes a mention, or writes
into the checked-in Golden file. Review the output before selectively merging it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.db.models import PlaceMention


def export_corrections(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    mentions = db.scalars(
        select(PlaceMention)
        .where(PlaceMention.resolution_status == "CONFIRMED")
        .order_by(PlaceMention.created_at.desc())
        .limit(limit)
    ).all()
    drafts: list[dict[str, Any]] = []
    for mention in mentions:
        metadata = mention.metadata_json or {}
        if metadata.get("confirmation_origin") != "MANUAL_CONFIRMED":
            continue
        selected_id = str(metadata.get("poi_id") or "")
        manual_confirmation = metadata.get("manual_confirmation", {})
        manual_confirmation = manual_confirmation if isinstance(manual_confirmation, dict) else {}
        candidate = next(
            (
                item
                for item in metadata.get("poi_candidates", [])
                if isinstance(item, dict) and item.get("provider_id") == selected_id
            ),
            manual_confirmation.get("candidate", {}),
        )
        if not selected_id or not isinstance(candidate, dict):
            continue
        drafts.append(
            {
                "sample_id": f"manual-{mention.id}",
                "mention": {
                    "name": mention.name,
                    "raw_name": mention.raw_name,
                    "suggested_name": mention.suggested_name,
                    "city_hint": mention.city_hint,
                    "province_hint": mention.province_hint,
                    "place_type": mention.place_type,
                },
                "candidates": [
                    {
                        key: candidate.get(key, "")
                        for key in (
                            "provider_id",
                            "name",
                            "address",
                            "province",
                            "city",
                            "district",
                            "longitude",
                            "latitude",
                            "typecode",
                        )
                    }
                ],
                "expected": {"candidate_id": selected_id, "status": "CONFIRMED"},
                "review_required": "人工确认导出；请确认脱敏与业务代表性后再合入 Golden。",
            }
        )
    return drafts


def main() -> None:
    parser = argparse.ArgumentParser(description="导出人工 POI 纠错为待审 Golden 草稿")
    parser.add_argument("--database-url", required=True, help="只读目标 SQLite 的 SQLAlchemy URL")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    try:
        with Session(engine) as db:
            drafts = export_corrections(db, max(1, min(args.limit, 1000)))
    finally:
        engine.dispose()
    args.output.write_text(json.dumps(drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
