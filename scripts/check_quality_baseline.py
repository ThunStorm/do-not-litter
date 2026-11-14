"""G0 offline baseline: hashes, source reachability, saved-response rule replay and metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backend/tests/fixtures/quality_baseline_v1/manifest.json"
TARGETS = [
    "test_yunnan_multiregion_travel_golden.py",  # P0_CRITICAL, never omitted
    "test_note_quality.py",
    "test_title_temporal_evidence.py",
    "test_video_temporal_context.py",
    "test_cover_text.py",
    "test_temporal_theme.py",
    "test_quality_baseline.py",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(gold, output, dimension, role):
    """Explicit adjudicated semantic keys; multiset intersection enforces one-to-one matching.

    Unjudged inputs and outputs without an adjudicated scope are not TP or FP.
    NEEDS_REVIEW remains an orthogonal disposition.
    """
    judged = [
        r for r in gold if r["dimension"] == dimension and r["role"] == role and r["judgment"] == "judged"
    ]
    scoped = [
        r
        for r in output
        if r["dimension"] == dimension and r["role"] == role and r.get("judgment") == "judged"
    ]
    if not judged and not scoped:
        return dict(TP=None, FP=None, FN=None, precision=None, recall=None)
    expected = Counter(r["semantic_key"] for r in judged if r.get("positive", True))
    actual = Counter(r["semantic_key"] for r in scoped)
    tp = sum((expected & actual).values())
    fp, fn = sum(actual.values()) - tp, sum(expected.values()) - tp
    return dict(
        TP=tp,
        FP=fp,
        FN=fn,
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
    )


def contract_errors(expected, output):
    """Frozen structural contract, deliberately separate from human semantic scoring."""
    errors = []
    by_id = {r["id"]: r for r in output}
    for original in expected:
        candidate = by_id.get(original["id"])
        if candidate is None or candidate["quote"] != original["quote"]:
            errors.append("MISSING_CRITICAL_QUALIFIER:" + original["id"])
            continue
        if (
            candidate["identity"] != original["identity"]
            or candidate["segment_ids"] != original["segment_ids"]
        ):
            errors.append("CROSS_SOURCE:" + original["id"])
        if candidate.get("confirmed_poi") != original.get("confirmed_poi"):
            errors.append("WRONG_POI:" + original["id"])
    return errors


def snapshot():
    paths = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
    # Data/reports are excluded to avoid self-referential hashes. Capture all source/tests/config.
    files = {}
    for raw in paths.decode().split("\0"):
        p = ROOT / raw
        if (
            raw
            and p.is_file()
            and (
                raw.startswith(("backend/", "frontend/", "scripts/", ".github/"))
                or raw in {"pnpm-lock.yaml", "pnpm-workspace.yaml"}
            )
        ):
            files[raw] = digest(p)
    return dict(
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        status=subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
        files=files,
        sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    )


def inspect_manifest(manifest):
    errors = [p for p, h in manifest["frozen_files"].items() if digest(ROOT / p) != h]
    rows = [r for c in manifest["categories"] for r in c["records"]]
    for r in rows:
        if hashlib.sha256(r["quote"].encode()).hexdigest() != r["quote_sha256"]:
            errors.append("quote:" + r["id"])
        if r["judgment"] == "judged" and not (r["adjudicator"] and r["adjudicated_at"]):
            errors.append("adjudication:" + r["id"])
    return rows, errors


def source_metrics(manifest):
    base = ROOT / "backend/tests/fixtures"
    december = json.loads((base / "travel_pipeline/december_reverse_bv1hrxe6yebq/baseline.json").read_text())
    temporal = json.loads((base / "video_temporal_context.json").read_text())
    maps = {
        "december": {s["id"]: s["text"] for s in december["segments"]},
        "title_cover_temporal": {s["id"]: s["corrected_text"] for s in temporal["segments"]},
    }
    # The Yunnan normalized sN mapping is exactly the existing replay parser's mapping.
    import re

    text = (base / "travel_pipeline/yunnan_bv16yem6reyx/zhijian-transcript-BV16Yem6REyX.txt").read_text()
    maps["yunnan"] = {
        f"s{i}": m[3] for i, m in enumerate(re.finditer(r"\[(\d+:\d+) - (\d+:\d+)\] (.+)", text))
    }
    reached, total = 0, 0
    for c in manifest["categories"]:
        for row in c["records"]:
            total += 1
            texts = maps.get(c["id"], {})
            reached += all(s in texts for s in row["segment_ids"]) and row["quote"] in "".join(
                texts.get(s, "") for s in row["segment_ids"]
            )
    return dict(
        reachable=reached,
        total=total,
        rate=reached / total if total else None,
        scope="Frozen file references only; unknown DB identities remain null",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    rows, errors = inspect_manifest(manifest)
    audit = args.output.with_suffix(".network.log").resolve()
    audit.write_text("")
    env = {
        **os.environ,
        "ZHIJIAN_OFFLINE_GUARD": "1",
        "ZHIJIAN_NETWORK_AUDIT": str(audit),
        "PYTHONPATH": os.pathsep.join(
            [str(ROOT / "scripts/offline_guard"), str(ROOT / "backend/src"), str(ROOT / "scripts")]
        ),
    }
    junit = args.output.with_suffix(".junit.xml").resolve()
    start = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *["backend/tests/" + t for t in TARGETS],
            "-q",
            "--tb=short",
            f"--junitxml={junit}",
        ],
        cwd=ROOT,
        env=env,
        check=False,
    )
    judged = sum(r["judgment"] == "judged" for r in rows)
    reachability = source_metrics(manifest)
    if reachability["reachable"] != reachability["total"]:
        errors.append("SOURCE_UNREACHABLE")
    saved = json.loads(
        (
            ROOT / "backend/tests/fixtures/travel_pipeline/december_reverse_bv1hrxe6yebq/baseline.json"
        ).read_text()
    )
    mentions = saved["mentions"]
    dispositions = Counter(
        m.get("metadata_json", {}).get("recommendation_evidence", {}).get("assessment_status", "UNKNOWN")
        for m in mentions
    )
    report = dict(
        schema_version="g0-report-v1",
        fixture_sha256=digest(MANIFEST),
        parser_version=snapshot(),
        categories=[
            {k: v for k, v in c.items() if k != "records"} | {"count": len(c["records"])}
            for c in manifest["categories"]
        ],
        adjudication=dict(
            total=len(rows),
            judged=judged,
            unjudged=len(rows) - judged,
            coverage=judged / len(rows) if rows else None,
        ),
        quality={
            d: {
                role: score(rows, [], d, role)
                for role in ["RECOMMENDED", "COMPARISON", "BACKGROUND", "UNJUDGED"]
            }
            for d in ["place", "fact", "poi_identity"]
        },
        poi_auto_confirmation=dict(
            total=0,
            judged=0,
            wrong=None,
            accuracy=None,
            adjudication_coverage=None,
            scope="No resolver executed",
        ),
        source_reachability=reachability,
        saved_output_inventory=dict(
            december=dict(
                places=len(mentions),
                facts=len(saved["semantic_map"]["claims"]),
                roles=dict(Counter(m.get("subject_role", "UNKNOWN") for m in mentions)),
                recommendation_dispositions=dict(dispositions),
                output_judgment="unjudged",
                poi_identities_evaluated=0,
            ),
            yunnan=dict(
                reference_candidates=71,
                real_response_model="codex/gpt-6-luna",
                model_parameters=None,
                output_judgment="unjudged",
            ),
        ),
        semantic_completeness=None,
        errors=errors,
        pytest_exit_code=result.returncode,
        runtime_seconds=round(time.monotonic() - start, 3),
        comparison=dict(
            sample_count=sum(bool(c["records"]) for c in manifest["categories"]),
            category_count=len(manifest["categories"]),
            model="SAVED_RESPONSE_ONLY",
            parameters=None,
            input_sha256=digest(MANIFEST),
            cache_mode="OFFLINE_FILES",
            first_requests=0,
            recovery=0,
            fallback=0,
            undispatched=0,
            tokens=None,
            token_basis="NOT_MEASURED; no provider invocation",
        ),
        network=dict(
            blocked_attempts=len(audit.read_text().splitlines()),
            guard="deny Python sockets; child guard inherited; allow read-only uname/mount",
        ),
        hosted_ci="HOSTED_NOT_RUN",
        independent_holdout=manifest["holdout_status"],
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return bool(errors or result.returncode or audit.read_text())


if __name__ == "__main__":
    sys.exit(main())
