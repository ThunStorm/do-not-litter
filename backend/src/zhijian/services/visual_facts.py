"""Experimental, evidence-bound visual fact extraction for retained screenshots."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.model_registry import model_profile_from_value
from zhijian.ai.policies import resolve_stage_policy
from zhijian.core.config import Settings
from zhijian.core.time import utc_now
from zhijian.db.models import Job, JobStep, PlaceMention, Setting, VideoAsset, VideoScreenshot, VisualFact
from zhijian.domain.enums import JobStatus
from zhijian.services.audit import record_event
from zhijian.services.video_support import normalized_confidence, parse_model_json, provider_for_role

FACT_TYPES = {"STORE_SIGN", "MENU", "DISH", "PRICE", "OPENING_HOURS", "ROAD_SIGN", "NOTICE"}


def score_visual_fact_cases(
    cases: list[dict[str, Any]], predictions: dict[str, list[dict[str, Any]]]
) -> dict[str, float | int]:
    """Small offline Golden scorer; any unsupported prediction is a severe hallucination."""
    expected = {
        (case["id"], str(fact["fact_type"]), str(fact["value"]).strip())
        for case in cases
        for fact in case.get("facts", [])
    }
    actual = {
        (case_id, str(fact.get("fact_type")), str(fact.get("value") or "").strip())
        for case_id, facts in predictions.items()
        for fact in facts
        if str(fact.get("value") or "").strip()
    }
    matched = expected & actual
    severe = sum(1 for item in actual - expected if item[1] not in FACT_TYPES or item[2])
    return {
        "fact_precision": len(matched) / len(actual) if actual else 1.0,
        "fact_recall": len(matched) / len(expected) if expected else 1.0,
        "evidence_linkage": sum(bool(case.get("screenshot_id")) for case in cases) / len(cases)
        if cases
        else 1.0,
        "hallucination_count": len(actual - expected),
        "severe_hallucination_count": severe,
    }


def process_visual_fact_job(db: Session, job: Job, settings: Settings) -> None:
    screenshot = db.get(VideoScreenshot, str(job.payload_json.get("visual_fact_screenshot_id") or ""))
    if screenshot is None or screenshot.status != "READY" or not screenshot.image_path:
        _finish(db, job, "SKIPPED_UNSUPPORTED", "截图尚不可用，未执行视觉识别")
        return
    if not _vision_profile(db, job):
        _finish(db, job, "SKIPPED_UNSUPPORTED", "未配置显式 Vision-capable Profile")
        return
    path = Path(screenshot.image_path)
    if not path.is_file():
        _finish(db, job, "SKIPPED_UNSUPPORTED", "截图文件已不可用，未执行视觉识别")
        return
    job.status, job.started_at, job.current_step, job.progress = (
        JobStatus.RUNNING.value,
        job.started_at or utc_now(),
        "VISION_FACT",
        15,
    )
    db.add(
        JobStep(job_id=job.id, step_name="VISION_FACT", status="RUNNING", progress=0, started_at=utc_now())
    )
    db.commit()
    provider, provider_name, model = provider_for_role(db, settings, "visual_fact", job)
    image = base64.b64encode(path.read_bytes()).decode()
    prompt = (
        "只提取截图中清晰可见的店招、菜单、菜名、价格、营业时间、路牌或告示。"
        '返回 JSON {"facts":[{"fact_type":"PRICE","value":"...","confidence":0.0}]}；'
        "看不清时返回空 facts，禁止常识补全。"
    )
    image_content: Any = (
        prompt
        if provider_name == "ollama"
        else [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
        ]
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "视觉事实必须独立于字幕，不判断两者谁正确。"},
        {
            "role": "user",
            "content": image_content,
            **({"images": [image]} if provider_name == "ollama" else {}),
        },
    ]
    result = AIWorkloadGateway().execute_cached_json(
        db,
        job=job,
        stage="VISION_FACT",
        capability="SCREENSHOT_UNDERSTANDING",
        provider=provider,
        provider_name=provider_name,
        model=model,
        messages=messages,
        semantic_options={"screenshot_id": screenshot.id, "model_version": "vision-fact-v1"},
        cache_enabled=False,
        force_regenerate=False,
    )
    payload = parse_model_json(result.content)
    mention = db.get(PlaceMention, screenshot.place_mention_id) if screenshot.place_mention_id else None
    asset = db.get(VideoAsset, screenshot.video_asset_id)
    facts = []
    for item in payload.get("facts", []) if isinstance(payload.get("facts"), list) else []:
        if not isinstance(item, dict) or str(item.get("fact_type")) not in FACT_TYPES:
            continue
        value = str(item.get("value") or "").strip()
        if value:
            facts.append(
                VisualFact(
                    screenshot_id=screenshot.id,
                    place_id=mention.place_id if mention else None,
                    source_id=asset.source_id if asset else None,
                    fact_type=str(item["fact_type"]),
                    value=value[:1000],
                    confidence=normalized_confidence(item.get("confidence")),
                    timestamp_ms=screenshot.actual_timestamp_ms or screenshot.planned_timestamp_ms,
                    provider=provider_name,
                    model=model,
                )
            )
    db.add_all(facts)
    _finish(db, job, "COMPLETED", f"已提取 {len(facts)} 条实验性视觉事实", commit=False)
    record_event(
        db,
        "visual_fact.extracted",
        f"截图视觉事实提取完成：{len(facts)} 条",
        component="vision-fact",
        entity_type="job",
        entity_id=job.id,
        detail={"screenshot_id": screenshot.id, "provider": provider_name, "model": model},
        commit=False,
    )
    db.commit()


def _vision_profile(db: Session, job: Job) -> bool:
    saved = db.get(Setting, "ai-stage-policy:VISION_FACT")
    policy = resolve_stage_policy(
        "VISION_FACT",
        saved=saved.value_json if saved and isinstance(saved.value_json, dict) else None,
        job_override=(job.payload_json.get("ai_overrides") or {}).get("VISION_FACT"),
    )
    for profile_id in (policy.local_profile_id, policy.remote_profile_id):
        setting = db.get(Setting, f"model-profile:{profile_id}") if profile_id else None
        if setting and isinstance(setting.value_json, dict):
            profile = model_profile_from_value(profile_id, setting.value_json)
            if profile.enabled and "image" in profile.modalities:
                return True
    return False


def _finish(db: Session, job: Job, status: str, message: str, *, commit: bool = True) -> None:
    step = db.scalar(select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == "VISION_FACT"))
    if step is None:
        step = JobStep(job_id=job.id, step_name="VISION_FACT", status=status, progress=100)
        db.add(step)
    step.status, step.progress, step.finished_at, step.output_json = (
        status,
        100,
        utc_now(),
        {"message": message},
    )
    job.status = JobStatus.COMPLETED.value if status == "COMPLETED" else JobStatus.PARTIAL_SUCCESS.value
    job.current_step, job.progress, job.finished_at = "VISION_FACT", 100, utc_now()
    job.error_code, job.error = (None, None) if status == "COMPLETED" else ("SKIPPED_UNSUPPORTED", message)
    job.lease_owner = job.lease_expire_at = None
    if commit:
        db.commit()
