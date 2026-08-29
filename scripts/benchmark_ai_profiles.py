"""Summarize saved AI benchmark rows without invoking models or downloading data."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def summarize(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("profile") or "unknown")].append(row)
    return {
        profile: {
            "samples": len(items),
            "schema_pass_rate": _mean(items, "schema_pass"),
            "evidence_coverage": _mean(items, "evidence_coverage"),
            "latency_ms": _mean(items, "latency_ms"),
            "local_tokens": sum(int(item.get("local_tokens") or 0) for item in items),
            "remote_tokens": sum(int(item.get("remote_tokens") or 0) for item in items),
            "escalation_rate": _mean(items, "escalated"),
        }
        for profile, items in sorted(groups.items())
    }


def _mean(rows: list[dict], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON array of benchmark rows")
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("benchmark input must be a JSON array")
    print(json.dumps(summarize(rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
