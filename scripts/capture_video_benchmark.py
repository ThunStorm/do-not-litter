"""Export one existing video Job's replay-safe benchmark record without calling a provider."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from zhijian.core.time import as_utc
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


def _elapsed_ms(start, end) -> int | None:
    if start is None or end is None:
        return None
    return max(0, round((as_utc(end) - as_utc(start)).total_seconds() * 1000))


def _baseline_metrics(
    job: Job,
    steps: list[JobStep],
    audits: list[ExternalCallAudit],
    stage_metrics: dict[str, dict[str, int]],
) -> dict[str, Any]:
    by_name = {step.step_name: step for step in steps}
    outputs = {step.step_name: step.output_json or {} for step in steps}
    metadata = outputs.get("FETCH_METADATA", {})
    correction = outputs.get("CORRECT_TRANSCRIPT", {})
    poi = outputs.get("RESOLVE_POI", {})
    screenshots = outputs.get("EXTRACT_SCREENSHOTS", {})
    ground_attempts = []
    ground_chunks: set[tuple[object, object]] = set()
    for audit in audits:
        request = audit.request_meta_json or {}
        stage = str(request.get("stage") or request.get("step") or audit.operation)
        if stage != "GROUND_MAP" or request.get("cache_hit"):
            continue
        ground_attempts.append(request)
        ground_chunks.add((request.get("chunk_index"), request.get("split_path") or "root"))
    prompt_tokens = sum(item["input_tokens"] for item in stage_metrics.values())
    completion_tokens = sum(item["output_tokens"] for item in stage_metrics.values())
    model_attempts = sum(item["attempts"] for item in stage_metrics.values())
    retries = sum(item["retries"] for item in stage_metrics.values())
    fallbacks = sum(item["fallbacks"] for item in stage_metrics.values())
    duration_ms = int(metadata.get("duration_ms") or 0)
    first_useful = by_name.get("MATERIALIZE_CORE") or by_name.get("MATERIALIZE")
    first_useful_at = None
    if job.payload_json.get("first_useful_note_at"):
        try:
            first_useful_at = datetime.fromisoformat(str(job.payload_json["first_useful_note_at"]))
        except ValueError:
            first_useful_at = None
    first_useful_at = first_useful_at or (first_useful.finished_at if first_useful else None)
    asr = by_name.get("ASR")
    screenshot_step = by_name.get("EXTRACT_SCREENSHOTS")
    return {
        "video_minutes": round(duration_ms / 60_000, 4) if duration_ms else None,
        "transcript_chars": int(correction.get("transcript_chars") or 0),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "correction_candidate_segments": int(correction.get("candidate_segments") or 0),
        "total_segments": int(correction.get("total_segments") or 0),
        "correction_source_class": str(correction.get("source_class") or ""),
        "correction_coverage_ratio": float(correction.get("correction_coverage_ratio") or 0),
        "correction_target_chars": int(correction.get("correction_target_chars") or 0),
        "correction_context_chars": int(correction.get("correction_context_chars") or 0),
        "correction_input_chars": int(correction.get("correction_input_chars") or 0),
        "correction_input_ratio": float(correction.get("correction_input_ratio") or 0),
        "ground_map_input_chars": sum(int(item.get("input_chars") or 0) for item in ground_attempts),
        "ground_map_chunks": len(ground_chunks),
        "ground_map_retries": sum(int(item.get("attempt") or 1) > 1 for item in ground_attempts),
        "model_attempts": model_attempts,
        "retries": retries,
        "fallbacks": fallbacks,
        "amap_requests": int(poi.get("amap_request_count") or 0),
        "amap_cache_hits": int(poi.get("amap_cache_hit_count") or 0),
        "screenshot_processes": int(screenshots.get("screenshot_process_count") or 0),
        "asr_runtime_ms": _elapsed_ms(asr.started_at, asr.finished_at) if asr else None,
        "screenshot_stage_ms": (
            _elapsed_ms(screenshot_step.started_at, screenshot_step.finished_at)
            if screenshot_step
            else None
        ),
        "pipeline_wall_ms": _elapsed_ms(job.started_at, job.finished_at),
        "time_to_first_useful_note_ms": (
            _elapsed_ms(job.started_at, first_useful_at) if first_useful_at else None
        ),
    }


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
        lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "attempts": 0,
            "retries": 0,
            "fallbacks": 0,
            "cache_hits": 0,
            "wall_time_ms": 0,
        }
    )
    for audit in audits:
        request, response = audit.request_meta_json or {}, audit.response_meta_json or {}
        stage = str(request.get("stage") or request.get("step") or audit.operation)
        values = stage_metrics[stage]
        cache_hit = bool(request.get("cache_hit"))
        values["attempts"] += int(not cache_hit)
        values["retries"] += int(not cache_hit and int(request.get("attempt") or 1) > 1)
        values["fallbacks"] += int(request.get("route") == "fallback")
        values["cache_hits"] += int(cache_hit)
        values["input_tokens"] += int(response.get("prompt_tokens") or 0)
        values["output_tokens"] += int(response.get("completion_tokens") or 0)
        values["cached_tokens"] += int(response.get("cached_tokens") or 0)
        values["wall_time_ms"] += int(audit.duration_ms or 0)
    metrics = dict(stage_metrics)
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
        "stage_metrics": metrics,
        "baseline_metrics": _baseline_metrics(job, steps, audits, metrics),
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
