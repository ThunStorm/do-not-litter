"""Verify captured AI E2E evidence without starting Jobs or calling a Provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_SIGNALS = frozenset(
    {
        "PLATFORM_SUBTITLE",
        "ASR",
        "LOCAL",
        "REMOTE",
        "LOCAL_ONLY",
        "REMOTE_ONLY",
        "LOCAL_FIRST",
        "REMOTE_FIRST",
        "AUTO",
        "CACHE",
        "FORCE_REGENERATE",
        "FALLBACK",
        "REPLAY",
        "CANCEL",
    }
)


def evaluate(captures: list[dict[str, Any]], blockers: list[str] | None = None) -> dict[str, Any]:
    signals: set[str] = set()
    for capture in captures:
        source_kind = str(capture.get("source_kind") or "").upper()
        if source_kind == "ASR_VIDEO":
            source_kind = "ASR"
        if source_kind in {"PLATFORM_SUBTITLE", "ASR"}:
            signals.add(source_kind)
        location = str(capture.get("location") or "").upper()
        if location in {"LOCAL", "REMOTE"}:
            signals.add(location)
        mode = str(capture.get("execution_mode") or "").upper()
        if mode in REQUIRED_SIGNALS:
            signals.add(mode)
        for name in ("cache", "force_regenerate", "fallback", "replay", "cancel"):
            if capture.get(name):
                signals.add(name.upper())
    missing = sorted(REQUIRED_SIGNALS - signals)
    blockers = sorted(set(blockers or []))
    status = "BLOCKED_EXTERNAL" if blockers else "READY_FOR_REVIEW" if not missing else "INCOMPLETE"
    return {
        "status": status,
        "blockers": blockers,
        "captured_signals": sorted(signals),
        "missing_signals": missing,
        "production_proven": False,
        "notice": "只核验已采集的 E2E 证据；不会启动 Job、下载视频、调用 Provider 或改路由。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="核验已采集的 AI Gateway E2E 覆盖")
    parser.add_argument("captures", type=Path, help="人工或只读采集的 JSON 数组")
    parser.add_argument("--external-blocker", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    captures = json.loads(args.captures.read_text(encoding="utf-8"))
    if not isinstance(captures, list):
        raise SystemExit("captures 必须是 JSON 数组")
    encoded = json.dumps(evaluate(captures, args.external_blocker), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
