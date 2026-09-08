"""Export one existing video Job's replay-safe benchmark record without calling a provider."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.db.models import (
    ExternalCallAudit,
    Job,
    JobStep,
    JobStepArtifact,
    Setting,
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(word in key.lower() for word in ("key", "secret", "token", "cookie")) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def capture(db: Session, *, sample_id: str, profile_id: str, job_id: str) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job 不存在")
    profile = db.get(Setting, f"model-profile:{profile_id}")
    if profile is None:
        raise ValueError("Model Profile 不存在")
    steps = db.scalars(select(JobStep).where(JobStep.job_id == job_id).order_by(JobStep.started_at)).all()
    artifacts = db.scalars(
        select(JobStepArtifact).where(
            JobStepArtifact.job_id == job_id,
            JobStepArtifact.status == "AVAILABLE",
        )
    ).all()
    audits = db.scalars(
        select(ExternalCallAudit)
        .where(ExternalCallAudit.job_id == job_id)
        .order_by(ExternalCallAudit.created_at)
    ).all()
    stage_metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "attempts": 0, "fallbacks": 0, "cache_hits": 0, "wall_time_ms": 0}
    )
    for audit in audits:
        request, response = audit.request_meta_json or {}, audit.response_meta_json or {}
        stage = str(request.get("stage") or request.get("step") or audit.operation)
        values = stage_metrics[stage]
        cache_hit = bool(request.get("cache_hit"))
        values["attempts"] += int(not cache_hit)
        values["fallbacks"] += int(request.get("route") == "fallback")
        values["cache_hits"] += int(cache_hit)
        values["input_tokens"] += int(response.get("prompt_tokens") or 0)
        values["output_tokens"] += int(response.get("completion_tokens") or 0)
        values["cached_tokens"] += int(response.get("cached_tokens") or 0)
        values["wall_time_ms"] += int(audit.duration_ms or 0)
    return {
        "sample_id": sample_id,
        "profile": profile_id,
        "job_id": job.id,
        "job_status": job.status,
        "model_profile": _redact(profile.value_json),
        "stage_policies": {
            item.key.removeprefix("ai-stage-policy:"): _redact(item.value_json)
            for item in db.scalars(select(Setting).where(Setting.key.like("ai-stage-policy:%")))
        },
        "stage_metrics": dict(stage_metrics),
        "stage_outputs": {step.step_name: _redact(step.output_json) for step in steps},
        "replay_artifacts": [
            {
                "step": item.step_name,
                "input_hash": item.input_hash,
                "content_hash": item.content_hash,
                "schema_version": item.schema_version,
                "producer_version": item.producer_version,
                "replayable_until": item.replayable_until.isoformat(),
            }
            for item in artifacts
        ],
        "peak_memory_bytes": None,
        "notice": "只读导出；未调用 Provider、未下载视频。输出仍可能含业务内容，请按本地数据规则保管。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="导出已有 Video Job 的 Benchmark 采集记录")
    parser.add_argument("--database-url", required=True, help="只读目标 SQLite 的 SQLAlchemy URL")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    try:
        with Session(engine) as db:
            value = capture(db, sample_id=args.sample_id, profile_id=args.profile_id, job_id=args.job_id)
    finally:
        engine.dispose()
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
