import os
import subprocess
import sys
from pathlib import Path


def test_worker_import_does_not_cycle_through_provider_reliability() -> None:
    backend_src = Path(__file__).resolve().parents[1] / "src"
    environment = {**os.environ, "PYTHONPATH": str(backend_src)}
    result = subprocess.run(
        [sys.executable, "-c", "import zhijian.providers.llm; import zhijian.worker"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
