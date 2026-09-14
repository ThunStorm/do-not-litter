"""Idempotently backfill current Video Note FTS rows without invoking an LLM."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.services.video_note_search import backfill_video_note_search_index


def main() -> None:
    parser = argparse.ArgumentParser(description="回填当前视频笔记全文索引")
    parser.add_argument("--database-url", required=True, help="目标 SQLite 的 SQLAlchemy URL")
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    try:
        with Session(engine) as db:
            count = backfill_video_note_search_index(db)
            db.commit()
    finally:
        engine.dispose()
    print(f"indexed={count}")


if __name__ == "__main__":
    main()
