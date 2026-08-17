from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path


class MacVisionOCRProvider:
    """Use the macOS Vision framework without adding a third-party OCR runtime."""

    def __init__(self, script: Path | None = None, timeout: int = 180) -> None:
        project_root = Path(__file__).resolve().parents[4]
        self.script = script or project_root / "deploy" / "macos" / "vision_ocr.swift"
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return platform.system() == "Darwin" and Path("/usr/bin/swift").is_file() and self.script.is_file()

    def recognize(self, path: Path) -> tuple[str, list[dict]]:
        if not self.available:
            raise RuntimeError("macOS Vision OCR 当前不可用")
        result = subprocess.run(
            ["/usr/bin/swift", str(self.script), str(path)],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "Vision OCR 执行失败").strip()[:500])
        rows = json.loads(result.stdout)
        segments = [
            {
                "text": str(row["text"]),
                "locator": {"file": path.name, "ocr_index": index + 1, "bbox": row.get("bbox")},
                "confidence": float(row.get("confidence", 0)),
            }
            for index, row in enumerate(rows)
            if str(row.get("text", "")).strip()
        ]
        return "\n".join(segment["text"] for segment in segments), segments
