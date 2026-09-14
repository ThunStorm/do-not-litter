"""Deterministic token-cost anomaly checks; never re-run work automatically."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.db.models import ExternalCallAudit, Job, SystemEvent
from zhijian.services.audit import record_event


@dataclass(frozen=True)
class TokenAnomaly:
    stage: str
    provider: str
    model: str
    suspected_reason: str


def detect_token_anomalies(
    rows: list[ExternalCallAudit], expected_prompt_tokens: int = 0
) -> list[TokenAnomaly]:
    actual = [row for row in rows if not (row.request_meta_json or {}).get("cache_hit")]
    by_stage: dict[str, list[ExternalCallAudit]] = defaultdict(list)
    for row in actual:
        by_stage[str((row.request_meta_json or {}).get("stage") or row.operation)].append(row)
    anomalies: list[TokenAnomaly] = []
    for stage, attempts in by_stage.items():
        sample = attempts[0]
        provider = str(sample.provider)
        model = str((sample.request_meta_json or {}).get("model") or provider)
        hashes = [str((item.request_meta_json or {}).get("input_hash") or "") for item in attempts]
        if any(count > 1 for value, count in Counter(hashes).items() if value):
            anomalies.append(TokenAnomaly(stage, provider, model, "REPEATED_STAGE_INPUT"))
        fallback_runs = sum(
            str((item.request_meta_json or {}).get("route") or "") == "fallback" for item in attempts
        )
        if fallback_runs >= 2:
            anomalies.append(TokenAnomaly(stage, provider, model, "FALLBACK_CONSECUTIVE"))
        chunk_count = max(int((item.request_meta_json or {}).get("chunk_count") or 0) for item in attempts)
        if chunk_count and len(attempts) > chunk_count * 2:
            anomalies.append(TokenAnomaly(stage, provider, model, "CHUNK_ATTEMPTS_ABNORMAL"))
    prompt_tokens = sum(int((row.response_meta_json or {}).get("prompt_tokens") or 0) for row in actual)
    if expected_prompt_tokens and prompt_tokens > expected_prompt_tokens * 1.5 and actual:
        largest = max(actual, key=lambda row: int((row.response_meta_json or {}).get("prompt_tokens") or 0))
        anomalies.append(
            TokenAnomaly(
                str((largest.request_meta_json or {}).get("stage") or largest.operation),
                str(largest.provider),
                str((largest.request_meta_json or {}).get("model") or largest.provider),
                "PROMPT_TOKENS_ABOVE_EXPECTED",
            )
        )
    return list(dict.fromkeys(anomalies))


def record_token_anomalies(db: Session, job: Job) -> list[TokenAnomaly]:
    rows = db.scalars(
        select(ExternalCallAudit).where(
            ExternalCallAudit.job_id == job.id,
            ExternalCallAudit.capability == "LLM",
        )
    ).all()
    expected = int((job.payload_json.get("ai_soft_budget") or {}).get("expected_prompt_tokens") or 0)
    existing = {
        (
            str((event.detail_json or {}).get("stage") or ""),
            str((event.detail_json or {}).get("suspected_reason") or ""),
        )
        for event in db.scalars(
            select(SystemEvent).where(
                SystemEvent.entity_type == "job",
                SystemEvent.entity_id == job.id,
                SystemEvent.event_type == "AI_TOKEN_ANOMALY",
            )
        )
    }
    created = []
    for anomaly in detect_token_anomalies(rows, expected):
        if (anomaly.stage, anomaly.suspected_reason) in existing:
            continue
        record_event(
            db,
            "AI_TOKEN_ANOMALY",
            f"检测到 Token 异常：{anomaly.suspected_reason}",
            component="ai-gateway",
            level="WARNING",
            entity_type="job",
            entity_id=job.id,
            detail=asdict(anomaly),
            commit=False,
        )
        created.append(anomaly)
    if created:
        db.flush()
    return created
