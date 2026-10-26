"""Read-only audit of map timing/brief coverage; never changes stored evidence."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from zhijian.core.config import get_settings
from zhijian.services.travel_recommendations import visit_window_summary
from zhijian.services.travel_timing import valid_window


def audit(database: Path) -> dict:
    with sqlite3.connect(
        f"file:{quote(str(database.resolve()))}?mode=ro", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        places = db.execute(
            "SELECT id,name,summary FROM places WHERE deleted_at IS NULL AND (resolution_status='CONFIRMED' OR origin='USER_CREATED') ORDER BY name"
        ).fetchall()
        results = []
        for place in places:
            rows = db.execute(
                "SELECT * FROM place_visit_windows WHERE place_id=? AND status='ACTIVE'",
                (place["id"],),
            ).fetchall()
            windows = [
                SimpleNamespace(
                    **{
                        **dict(r),
                        "segment_ids_json": json.loads(r["segment_ids_json"] or "[]"),
                    }
                )
                for r in rows
            ]
            latest = db.execute(
                "SELECT brief_json,metadata_json FROM place_mentions WHERE place_id=? ORDER BY updated_at DESC,id DESC LIMIT 1",
                (place["id"],),
            ).fetchone()
            invalid = [w.id for w in windows if not valid_window(w)]
            status = (
                (
                    json.loads(latest["metadata_json"] or "{}").get("temporal_analysis")
                    or {}
                ).get("status")
                if latest
                else None
            )
            brief = json.loads(latest["brief_json"] or "{}") if latest else {}
            issues = []
            if invalid:
                issues.append("派生时间缺少时间语义：展示过滤；历史重算待确认")
            if not windows:
                issues.append("无时间窗口：需核对标题和正文，不等于全年适合")
            if not (brief.get("feature") or place["summary"]):
                issues.append("无简短特色：需从已保存证据归纳")
            results.append(
                {
                    "place_id": place["id"],
                    "name": place["name"],
                    "active_windows": len(windows),
                    "invalid_window_ids": invalid,
                    "analysis_status": status or "UNANALYZED",
                    "projected_timing": visit_window_summary(windows)["summary"],
                    "issues": issues,
                }
            )
        return {
            "read_only": True,
            "place_count": len(results),
            "needs_analysis": sum(
                r["analysis_status"] == "UNANALYZED" for r in results
            ),
            "invalid_windows": sum(len(r["invalid_window_ids"]) for r in results),
            "places": results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=get_settings().database_path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.database.resolve():
        parser.error("output must not overwrite the database")
    report = audit(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "places"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
