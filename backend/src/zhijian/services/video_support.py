from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zhijian.core.config import Settings
from zhijian.core.secret_store import build_secret_store
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    Place,
    PlaceMention,
    PlaceNoteVersion,
    Segment,
    Setting,
    Snapshot,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.domain.enums import ResolutionStatus
from zhijian.providers.amap import AMapPOIProvider
from zhijian.providers.llm import LLMProvider, LLMResult, OllamaProvider, OpenAICompatibleProvider


class ProviderUnavailable(RuntimeError):
    code = "PROVIDER_NOT_CONFIGURED"


def parse_model_json(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I)
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("模型没有返回 JSON 对象")
    return value


def _provider_config(db: Session, settings: Settings, role: str) -> dict[str, str]:
    saved = db.get(Setting, f"provider:{role}") or db.get(Setting, "provider:default")
    if saved:
        return {key: str(value) for key, value in saved.value_json.items()}
    return {"provider": "DeepSeek", "base_url": settings.deepseek_base_url, "model": "deepseek-chat"}


def provider_for_role(db: Session, settings: Settings, role: str) -> tuple[LLMProvider, str, str]:
    config = _provider_config(db, settings, role)
    name = config.get("provider", "").lower()
    base_url = config.get("base_url", "")
    model = config.get("model") or getattr(settings, f"{role}_model", "") or "deepseek-chat"
    if not base_url:
        raise ProviderUnavailable("尚未配置可用模型服务地址")
    if name == "ollama":
        return OllamaProvider(base_url), "ollama", model
    store = build_secret_store(settings.secret_store, settings.data_dir)
    api_key = store.get(f"provider:{role}:api-key") or store.get("provider:default:api-key")
    if not api_key:
        raise ProviderUnavailable("尚未保存视频笔记模型的 API Key")
    return (
        OpenAICompatibleProvider(name or "openai-compatible", base_url, api_key),
        name or "openai-compatible",
        model,
    )


def materialize_transcript(
    db: Session,
    source: Source,
    asset: VideoAsset,
    raw_segments: list[dict[str, Any]],
    *,
    source_kind: str,
    language: str = "zh-CN",
) -> tuple[Transcript, list[Segment]]:
    normalized = []
    for item in raw_segments:
        text = str(item.get("text") or "").strip()
        start_ms = int(item.get("start_ms") or 0)
        end_ms = max(start_ms, int(item.get("end_ms") or start_ms))
        if text:
            normalized.append(
                {"text": text, "start_ms": start_ms, "end_ms": end_ms, "confidence": item.get("confidence")}
            )
    if not normalized:
        raise ValueError("没有可用的带时间码转写片段")
    fingerprint = "\n".join(f"{item['start_ms']}:{item['end_ms']}:{item['text']}" for item in normalized)
    existing = db.scalar(
        select(Transcript).where(Transcript.video_asset_id == asset.id).order_by(Transcript.version.desc())
    )
    if existing and existing.metadata_json.get("fingerprint") == fingerprint:
        snapshot_id = existing.metadata_json.get("snapshot_id")
        segments = db.scalars(
            select(Segment).where(Segment.snapshot_id == snapshot_id).order_by(Segment.ordinal)
        ).all()
        return existing, segments
    version = (existing.version + 1) if existing else 1
    snapshot = Snapshot(
        source_id=source.id,
        content_hash=__import__("hashlib").sha256(fingerprint.encode()).hexdigest(),
        metadata_json={"kind": "VIDEO_TRANSCRIPT", "video_asset_id": asset.id, "source_kind": source_kind},
    )
    db.add(snapshot)
    db.flush()
    segments = []
    for ordinal, item in enumerate(normalized):
        segment = Segment(
            snapshot_id=snapshot.id,
            kind="VIDEO_TRANSCRIPT",
            ordinal=ordinal,
            text=item["text"],
            confidence=item["confidence"],
            locator_json={"start_ms": item["start_ms"], "end_ms": item["end_ms"]},
        )
        db.add(segment)
        segments.append(segment)
    db.flush()
    transcript = Transcript(
        video_asset_id=asset.id,
        version=version,
        source_kind=source_kind,
        language=language,
        text="\n".join(item["text"] for item in normalized),
        segment_count=len(segments),
        metadata_json={"snapshot_id": snapshot.id, "fingerprint": fingerprint},
    )
    db.add(transcript)
    db.commit()
    return transcript, segments


def _transcript_context(segments: list[Segment], max_chars: int) -> str:
    lines = []
    used = 0
    for segment in segments:
        start = segment.locator_json.get("start_ms", 0)
        end = segment.locator_json.get("end_ms", start)
        line = f"[segment:{segment.id} {start}-{end}ms] {segment.text}"
        if lines and used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


def generate_note(
    db: Session, settings: Settings, asset: VideoAsset, transcript: Transcript, segments: list[Segment]
) -> AINoteVersion:
    provider, provider_name, model = provider_for_role(db, settings, "video_note_summary")
    context = _transcript_context(segments, settings.video_note_chunk_chars)
    system = Path(__file__).resolve().parents[1] / "prompts" / "video_note.md"
    response: LLMResult = provider.generate_json(
        [
            {"role": "system", "content": system.read_text(encoding="utf-8")},
            {"role": "user", "content": context},
        ],
        model=model,
    )
    payload = parse_model_json(response.content)
    raw_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    if not raw_sections:
        raw_sections = [
            {
                "heading": "视频要点",
                "body_markdown": payload.get("overview") or "模型未返回章节",
                "segment_ids": [segment.id for segment in segments[:5]],
            }
        ]
    note = db.scalar(select(AINote).where(AINote.video_asset_id == asset.id))
    if note is None:
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
    old = db.scalar(select(func.max(AINoteVersion.version)).where(AINoteVersion.ai_note_id == note.id)) or 0
    overview = str(payload.get("overview") or "")
    markdown = "# " + asset.title + "\n\n" + overview + "\n"
    version = AINoteVersion(
        ai_note_id=note.id,
        version=old + 1,
        markdown=markdown,
        overview=overview,
        warnings_json=payload.get("warnings") or [],
        model_provider=provider_name,
        model_name=model,
        transcript_version=transcript.version,
    )
    db.add(version)
    db.flush()
    rendered = [f"# {asset.title}", "", overview]
    valid_ids = {segment.id for segment in segments}
    for ordinal, item in enumerate(raw_sections):
        segment_ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not segment_ids:
            continue
        body = str(item.get("body_markdown") or item.get("body") or "")
        heading = str(item.get("heading") or f"要点 {ordinal + 1}")
        refs = [segment for segment in segments if segment.id in segment_ids]
        db.add(
            AINoteSection(
                ai_note_version_id=version.id,
                ordinal=ordinal,
                heading=heading,
                body_markdown=body,
                segment_ids_json=segment_ids,
                start_ms=refs[0].locator_json.get("start_ms") if refs else None,
                end_ms=refs[-1].locator_json.get("end_ms") if refs else None,
            )
        )
        rendered.extend(["", f"## {heading}", body])
    version.markdown = "\n".join(rendered).strip() + "\n"
    note.current_version_id = version.id
    note.status = "COMPLETED"
    db.commit()
    return version


def extract_place_mentions(
    db: Session, settings: Settings, asset: VideoAsset, note: AINoteVersion, segments: list[Segment]
) -> list[PlaceMention]:
    provider, _, model = provider_for_role(db, settings, "travel_place_extraction")
    prompt = (Path(__file__).resolve().parents[1] / "prompts" / "travel_place_extraction.md").read_text(
        encoding="utf-8"
    )
    payload = parse_model_json(
        provider.generate_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": _transcript_context(segments, settings.video_note_chunk_chars)},
            ],
            model=model,
        ).content
    )
    valid_ids = {segment.id for segment in segments}
    created: list[PlaceMention] = []
    for item in payload.get("places", [])[:80]:
        if not isinstance(item, dict):
            continue
        ids = [value for value in item.get("segment_ids", []) if value in valid_ids]
        if not ids or not item.get("name"):
            continue
        mention = PlaceMention(
            video_asset_id=asset.id,
            ai_note_version_id=note.id,
            name=str(item["name"])[:300],
            city_hint=str(item.get("city_hint") or "")[:64],
            province_hint=str(item.get("province_hint") or "")[:64],
            place_type=str(item.get("place_type") or "UNKNOWN")[:64],
            reason=str(item.get("reason") or ""),
            quote=str(item.get("quote") or ""),
            segment_ids_json=ids,
            confidence=max(0.0, min(1.0, float(item.get("confidence") or 0))),
            extraction_status="EXTRACTED",
            resolution_status=ResolutionStatus.UNRESOLVED.value,
        )
        db.add(mention)
        created.append(mention)
    db.commit()
    return created


def resolve_mentions_with_amap(
    db: Session, settings: Settings, mentions: list[PlaceMention]
) -> tuple[int, int]:
    if not mentions:
        return 0, 0
    if not settings.amap_api_key:
        return 0, len(mentions)
    provider = AMapPOIProvider(settings.amap_api_key)
    confirmed = 0
    for mention in mentions:
        try:
            candidates = provider.search(mention.name, mention.city_hint, city_limit=bool(mention.city_hint))
        except Exception as exc:
            mention.metadata_json = {"poi_error": str(exc)[:240]}
            continue
        if not candidates:
            continue
        selected = candidates[0]
        place = db.scalar(
            select(Place).where(
                Place.external_provider == "AMap", Place.external_poi_id == selected.provider_id
            )
        )
        if place is None:
            place = Place(
                name=selected.name,
                place_type=mention.place_type,
                province=selected.province,
                city=selected.city,
                district=selected.district,
                address=selected.address,
                latitude=selected.latitude,
                longitude=selected.longitude,
                coordinate_system=selected.coordinate_system,
                external_provider="AMap",
                external_poi_id=selected.provider_id,
                resolution_status=ResolutionStatus.CONFIRMED.value,
                summary=mention.reason,
            )
            db.add(place)
            db.flush()
        mention.place_id = place.id
        mention.resolution_status = ResolutionStatus.CONFIRMED.value
        mention.metadata_json = {"poi_name": selected.name, "poi_id": selected.provider_id}
        confirmed += 1
    db.commit()
    return confirmed, len(mentions) - confirmed


def build_place_notes(db: Session, asset: VideoAsset, mentions: list[PlaceMention]) -> int:
    count = 0
    for mention in mentions:
        if not mention.place_id:
            continue
        place = db.get(Place, mention.place_id)
        if place is None:
            continue
        previous = (
            db.scalar(select(func.max(PlaceNoteVersion.version)).where(PlaceNoteVersion.place_id == place.id))
            or 0
        )
        text = (
            f"# {place.name}\n\n- 视频来源：{asset.title}\n"
            f"- 依据：{mention.quote or mention.reason}\n"
            "- 状态：来源观察，建议到店前再次核验。\n"
        )
        db.add(
            PlaceNoteVersion(
                place_id=place.id,
                version=previous + 1,
                markdown=text,
                model_provider="deterministic",
                model_name="evidence-template",
                evidence_count=1,
            )
        )
        count += 1
    db.commit()
    return count
