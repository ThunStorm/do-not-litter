"""Single local/CI entry; no install, production read, deployment, commit or push."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_guards(out):
    results = {}
    cases = {
        "python_caught": [
            sys.executable,
            "-c",
            "import socket\ntry: socket.create_connection(('example.test',443))\nexcept RuntimeError: pass",
        ],
        "python_child": [
            sys.executable,
            "-c",
            "import subprocess,sys; subprocess.run([sys.executable,'-c',"
            "\"import socket; socket.getaddrinfo('example.test',443)\"],env={})",
        ],
        "node_caught": ["node", "-e", "try {require('node:net').connect(443,'example.test')} catch(e) {}"],
    }
    for name, command in cases.items():
        audit = out / f"selftest-{name}.network.log"
        audit.write_text("")
        env = {
            **os.environ,
            "ZHIJIAN_OFFLINE_GUARD": "1",
            "ZHIJIAN_NETWORK_AUDIT": str(audit),
            "PYTHONPATH": str(ROOT / "scripts/offline_guard"),
            "NODE_OPTIONS": "--require=" + str(ROOT / "scripts/offline_guard/node.cjs"),
        }
        result = subprocess.run(command, env=env, capture_output=True, check=False)
        results[name] = result.returncode == 91 and bool(audit.read_text())
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    steps = []
    guard_selftests = verify_guards(out)
    with tempfile.TemporaryDirectory(prefix="g0-check-") as folder:
        audit = out / "checks.network.log"
        audit.write_text("")
        base = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(ROOT / "scripts/offline_guard"), str(ROOT / "backend/src")]),
            "ZHIJIAN_OFFLINE_GUARD": "1",
            "ZHIJIAN_NETWORK_AUDIT": str(audit),
            "ZHIJIAN_STORAGE_CONFIG": str(Path(folder) / "storage.json"),
        }
        node_env = {**base, "NODE_OPTIONS": "--require=" + str(ROOT / "scripts/offline_guard/node.cjs")}
        commands = [
            (
                "ruff",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "backend/src",
                    "backend/tests",
                ],
                base,
            ),
            (
                "ruff-g0",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--config",
                    "backend/pyproject.toml",
                    "scripts/check_g0.py",
                    "scripts/check_quality_baseline.py",
                    "scripts/offline_guard/sitecustomize.py",
                ],
                base,
            ),
            (
                "backend",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "backend/tests",
                    "-q",
                    "--tb=short",
                    f"--junitxml={out / 'backend.junit.xml'}",
                ],
                base,
            ),
            ("frontend-lint", ["pnpm", "--dir", "frontend", "lint"], node_env),
            ("frontend-test", ["pnpm", "--dir", "frontend", "test"], node_env),
            ("frontend-types", ["pnpm", "--dir", "frontend", "exec", "tsc", "-b"], node_env),
            (
                "frontend-build",
                [
                    "pnpm",
                    "--dir",
                    "frontend",
                    "exec",
                    "vite",
                    "build",
                    "--outDir",
                    str(Path(folder) / "dist"),
                ],
                node_env,
            ),
            # Runner needs git for source inventory; replay subprocess itself is guarded.
            (
                "quality",
                [sys.executable, "scripts/check_quality_baseline.py", "--output", str(out / "quality.json")],
                os.environ.copy(),
            ),
        ]
        for name, command, env in commands:
            start = time.monotonic()
            step_audit = out / f"{name}.network.log"
            step_audit.write_text("")
            env = {**env, "ZHIJIAN_NETWORK_AUDIT": str(step_audit)}
            with (out / f"{name}.log").open("w") as stream:
                result = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False
                )
            steps.append(
                dict(
                    name=name,
                    command=command,
                    exit_code=result.returncode,
                    network_blocked_attempts=len(step_audit.read_text().splitlines()),
                    seconds=round(time.monotonic() - start, 3),
                )
            )
            print(f"{name}: {result.returncode}", flush=True)
        report = dict(
            steps=steps,
            guard_selftests=guard_selftests,
            network_blocked_attempts=sum(s["network_blocked_attempts"] for s in steps),
            hosted_ci="HOSTED_NOT_RUN",
            platform=sys.platform,
            platform_gaps=[
                "Real macOS Keychain",
                "Real Vision/OCR",
                "LaunchAgent lifecycle",
                "Real Provider/AMap/media",
                "Independent human gold/holdout",
            ],
            python=sys.version,
            versions={},
        )
        for executable in ["node", "pnpm"]:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
            report["versions"][executable] = result.stdout.strip()
        (out / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
        return (
            any(s["exit_code"] for s in steps)
            or bool(report["network_blocked_attempts"])
            or not all(guard_selftests.values())
        )


if __name__ == "__main__":
    sys.exit(main())
