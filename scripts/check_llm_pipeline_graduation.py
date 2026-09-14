"""Check a captured LLM graduation manifest; never calls a Provider or Worker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.ai.graduation import graduation_gate


def main() -> None:
    parser = argparse.ArgumentParser(description="检查已采集的 LLM Pipeline 毕业证据")
    parser.add_argument("manifest", type=Path, help="离线采集的 JSON manifest")
    args = parser.parse_args()
    result = graduation_gate(json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
