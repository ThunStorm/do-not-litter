"""Own stdout/stderr handles so launchd never holds an unbounded application log."""

from __future__ import annotations

import logging
import signal
import subprocess
import sys
from contextlib import suppress
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Thread


def main():
    # This small fallback is independent of the data volume and survives bootstrap failure.
    boot = logging.getLogger("zhijian.bootstrap")
    root = Path.home() / "Library/Logs/Zhijian"
    root.mkdir(parents=True, exist_ok=True)
    service, module = sys.argv[1:3]
    handler = RotatingFileHandler(root / f"boot-{service}.log", maxBytes=128 * 1024, backupCount=2)
    boot.addHandler(handler)
    boot.setLevel(logging.INFO)
    try:
        import os

        from zhijian.core.config import get_settings
        from zhijian.core.file_logs import SealedLogHandler

        # Normal bootstrap logging has the same immutable-volume lifecycle on a stable root.
        from zhijian.core.storage import DEFAULT_CONTROL

        control = Path(os.environ.get("ZHIJIAN_STORAGE_CONFIG", DEFAULT_CONTROL))
        sealed_boot = SealedLogHandler(root, f"boot-{service}", control)
        boot.removeHandler(handler)
        handler.close()
        boot.addHandler(sealed_boot)
        settings = get_settings()
        streams = []
        for name in ("stdout", "stderr"):
            log = logging.getLogger(f"stdio.{service}.{name}")
            log.propagate = False
            log.setLevel(logging.INFO)
            output = SealedLogHandler(
                settings.data_dir / "logs", f"stdio-{service}-{name}", settings.storage_config
            )
            output.setFormatter(logging.Formatter("%(message)s"))
            log.addHandler(output)
            streams.append(log)
        child = subprocess.Popen(
            [sys.executable, "-m", module],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            start_new_session=True,
        )

        def forward(signum, frame):
            import os

            with suppress(ProcessLookupError):
                os.killpg(child.pid, signum)

        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(signum, forward)

        def consume(pipe, log):
            with pipe:
                while line := pipe.readline(65536):
                    log.info(line.removesuffix("\n"))

        threads = [
            Thread(target=consume, args=(pipe, log))
            for pipe, log in zip((child.stdout, child.stderr), streams, strict=True)
        ]
        for thread in threads:
            thread.start()
        code = child.wait()
        for thread in threads:
            thread.join()
        return code if code >= 0 else 128 - code
    except Exception:
        boot.exception("服务启动/输出包装失败")
        return 1
    finally:
        logging.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
