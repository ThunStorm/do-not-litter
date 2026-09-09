from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from zhijian.core.ids import new_id
from zhijian.core.time import utc_now
from zhijian.db.base import Base, TimestampMixin


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("src"))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    authority: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("snap"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_path: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("seg"))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32), default="TEXT", nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locator_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    corrected_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    correction_status: Mapped[str] = mapped_column(String(32), default="UNCORRECTED", nullable=False)
    correction_confidence: Mapped[float | None] = mapped_column(Float)
    correction_reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    correction_provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    correction_model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("clm"))
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    predicate: Mapped[str] = mapped_column(String(128), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), default="EXTRACTED", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ev"))
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id", ondelete="CASCADE"))
    evidence_type: Mapped[str] = mapped_column(String(32), default="TEXT", nullable=False)
    quote: Mapped[str | None] = mapped_column(Text)
    locator_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ContentItem(Base, TimestampMixin):
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cnt"))
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    structured_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    user_state: Mapped[str] = mapped_column(String(32), default="DISCOVERED", nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("job"))
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    current_step: Mapped[str] = mapped_column(String(64), default="RECEIVED", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_content_id: Mapped[str | None] = mapped_column(ForeignKey("content_items.id", ondelete="SET NULL"))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobStep(Base):
    __tablename__ = "job_steps"
    __table_args__ = (UniqueConstraint("job_id", "step_name", name="uq_job_step"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("step"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(128))
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobStepArtifact(Base, TimestampMixin):
    __tablename__ = "job_step_artifacts"
    __table_args__ = (
        UniqueConstraint("job_id", "step_name", "artifact_type", name="uq_job_step_artifact"),
        Index("ix_job_step_artifacts_expiry", "status", "replayable_until"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("artifact"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), default="STEP_OUTPUT", nullable=False)
    artifact_ref_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    schema_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    producer_version: Mapped[str] = mapped_column(String(32), default="video-v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", nullable=False)
    replayable_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Place(Base, TimestampMixin):
    __tablename__ = "places"
    __table_args__ = (
        Index("ix_places_city_status", "city", "resolution_status"),
        UniqueConstraint("external_provider", "external_poi_id", name="uq_place_provider_poi"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("plc"))
    content_item_id: Mapped[str | None] = mapped_column(ForeignKey("content_items.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(32), default="AI_EXTRACTED", nullable=False)
    place_type: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="中国", nullable=False)
    province: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    district: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    coordinate_system: Mapped[str] = mapped_column(String(16), default="GCJ02", nullable=False)
    coordinate_source: Mapped[str] = mapped_column(String(32), default="AMAP_POI", nullable=False)
    external_provider: Mapped[str | None] = mapped_column(String(64))
    external_poi_id: Mapped[str | None] = mapped_column(String(128))
    resolution_status: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    poi_binding_status: Mapped[str] = mapped_column(String(32), default="AUTO_CONFIRMED", nullable=False)
    user_state: Mapped[str] = mapped_column(String(32), default="DISCOVERED", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PlaceObservation(Base):
    __tablename__ = "place_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("obs"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    segment_id: Mapped[str | None] = mapped_column(ForeignKey("segments.id", ondelete="SET NULL"))
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VideoAsset(Base, TimestampMixin):
    __tablename__ = "video_assets"
    __table_args__ = (UniqueConstraint("canonical_url", name="uq_video_asset_canonical_url"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("vid"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), unique=True)
    platform: Mapped[str] = mapped_column(String(32), default="BILIBILI", nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    bvid: Mapped[str | None] = mapped_column(String(32))
    aid: Mapped[str | None] = mapped_column(String(32))
    cid: Mapped[str | None] = mapped_column(String(32))
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    uploader: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    cover_url: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class VideoCoverAsset(Base, TimestampMixin):
    __tablename__ = "video_cover_assets"
    __table_args__ = (UniqueConstraint("video_asset_id", name="uq_cover_asset_video"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cover"))
    video_asset_id: Mapped[str] = mapped_column(ForeignKey("video_assets.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text)
    derivative_path: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    content_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    byte_size: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"
    __table_args__ = (UniqueConstraint("video_asset_id", "version", name="uq_transcript_asset_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("trn"))
    video_asset_id: Mapped[str] = mapped_column(ForeignKey("video_assets.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(24), default="zh-CN", nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    segment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AINote(Base, TimestampMixin):
    __tablename__ = "ai_notes"
    __table_args__ = (UniqueConstraint("video_asset_id", name="uq_ai_note_video_asset"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("note"))
    video_asset_id: Mapped[str] = mapped_column(ForeignKey("video_assets.id", ondelete="CASCADE"))
    current_version_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="PROCESSING", nullable=False)


class AINoteVersion(Base, TimestampMixin):
    __tablename__ = "ai_note_versions"
    __table_args__ = (UniqueConstraint("ai_note_id", "version", name="uq_ai_note_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ntv"))
    ai_note_id: Mapped[str] = mapped_column(ForeignKey("ai_notes.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    overview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    map_facts_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="video-note-v1", nullable=False)
    transcript_version: Mapped[int] = mapped_column(Integer, nullable=False)


class AINoteSection(Base):
    __tablename__ = "ai_note_sections"
    __table_args__ = (UniqueConstraint("ai_note_version_id", "ordinal", name="uq_ai_note_section_order"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("nsc"))
    ai_note_version_id: Mapped[str] = mapped_column(ForeignKey("ai_note_versions.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    thesis: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    bullets_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    anchor_id: Mapped[str] = mapped_column(String(96), default="", nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    segment_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)


class VideoScreenshot(Base, TimestampMixin):
    __tablename__ = "video_screenshots"
    __table_args__ = (Index("ix_video_screenshots_asset", "video_asset_id", "status"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("shot"))
    video_asset_id: Mapped[str] = mapped_column(ForeignKey("video_assets.id", ondelete="CASCADE"))
    ai_note_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_note_versions.id", ondelete="SET NULL")
    )
    ai_note_section_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_note_sections.id", ondelete="SET NULL")
    )
    place_mention_id: Mapped[str | None] = mapped_column(ForeignKey("place_mentions.id", ondelete="SET NULL"))
    segment_id: Mapped[str | None] = mapped_column(ForeignKey("segments.id", ondelete="SET NULL"))
    planned_timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    image_path: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    perceptual_hash: Mapped[str | None] = mapped_column(String(128))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    quality_score: Mapped[float | None] = mapped_column(Float)
    selection_reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    caption: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    content_role: Mapped[str] = mapped_column(String(64), default="KEY_FRAME", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", nullable=False)


class PlaceMention(Base, TimestampMixin):
    __tablename__ = "place_mentions"
    __table_args__ = (Index("ix_place_mentions_asset_status", "video_asset_id", "resolution_status"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pm"))
    video_asset_id: Mapped[str] = mapped_column(ForeignKey("video_assets.id", ondelete="CASCADE"))
    ai_note_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_note_versions.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    suggested_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    city_hint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    province_hint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    place_type: Mapped[str] = mapped_column(String(64), default="UNKNOWN", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    segment_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(32), default="EXTRACTED", nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED", nullable=False)
    place_id: Mapped[str | None] = mapped_column(ForeignKey("places.id", ondelete="SET NULL"))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    brief_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PlaceInsightItem(Base, TimestampMixin):
    __tablename__ = "place_insight_items"
    __table_args__ = (Index("ix_place_insights_place_status", "place_id", "status"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ins"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    place_mention_id: Mapped[str | None] = mapped_column(ForeignKey("place_mentions.id", ondelete="CASCADE"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_key: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    value_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("place_insight_items.id", ondelete="SET NULL")
    )
    segment_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)


class PlaceVisitWindow(Base, TimestampMixin):
    __tablename__ = "place_visit_windows"
    __table_args__ = (
        Index("ix_place_visit_window_place_status", "place_id", "status"),
        Index("ix_place_visit_window_time", "season", "month", "month_segment", "status"),
        Index("ix_place_visit_window_slot", "day_time_slot", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pvw"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    place_mention_id: Mapped[str | None] = mapped_column(ForeignKey("place_mentions.id", ondelete="SET NULL"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    season: Mapped[str | None] = mapped_column(String(16))
    month: Mapped[int | None] = mapped_column(Integer)
    month_segment: Mapped[str | None] = mapped_column(String(16))
    day_time_slot: Mapped[str | None] = mapped_column(String(32))
    period_type: Mapped[str] = mapped_column(String(32), default="BEST_VISIT", nullable=False)
    suitability: Mapped[str] = mapped_column(String(16), default="INFORMATIONAL", nullable=False)
    source_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    segment_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)


class PreferenceEvent(Base, TimestampMixin):
    __tablename__ = "preference_events"
    __table_args__ = (Index("ix_preference_events_place_created", "place_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pref"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class VisualFact(Base, TimestampMixin):
    __tablename__ = "visual_facts"
    __table_args__ = (
        Index("ix_visual_facts_screenshot_status", "screenshot_id", "status"),
        Index("ix_visual_facts_place_status", "place_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("vfact"))
    screenshot_id: Mapped[str] = mapped_column(
        ForeignKey("video_screenshots.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[str | None] = mapped_column(ForeignKey("places.id", ondelete="SET NULL"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), default="vision-fact-v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="EXPERIMENTAL", nullable=False)


class PlaceDeletionTombstone(Base):
    __tablename__ = "place_deletion_tombstones"
    __table_args__ = (Index("ix_place_tombstone_provider_poi", "external_provider", "external_poi_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ptomb"))
    external_provider: Mapped[str | None] = mapped_column(String(64))
    external_poi_id: Mapped[str | None] = mapped_column(String(128))
    normalized_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    former_place_id: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="用户永久删除", nullable=False)


class PlaceUserNote(Base, TimestampMixin):
    __tablename__ = "place_user_notes"
    __table_args__ = (UniqueConstraint("place_id", name="uq_place_user_note"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pnote"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), default="local-user", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), default="local-user", nullable=False)


class PlaceUserOverlay(Base, TimestampMixin):
    __tablename__ = "place_user_overlays"
    __table_args__ = (UniqueConstraint("place_id", name="uq_place_user_overlay"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("poverlay"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    override_place_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    custom_tags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class MapMarkerState(Base, TimestampMixin):
    __tablename__ = "map_marker_states"
    __table_args__ = (UniqueConstraint("place_id", name="uq_map_marker_place"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("marker"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    origin: Mapped[str] = mapped_column(String(32), default="AI_EXTRACTED", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="VISIBLE", nullable=False)
    custom_label: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlaceNoteVersion(Base, TimestampMixin):
    __tablename__ = "place_note_versions"
    __table_args__ = (UniqueConstraint("place_id", "version", name="uq_place_note_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pnv"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ExternalCallAudit(Base, TimestampMixin):
    __tablename__ = "external_call_audits"
    __table_args__ = (Index("ix_external_call_audits_job_created", "job_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("xca"))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    request_meta_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_meta_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))


class AICacheEntry(Base, TimestampMixin):
    __tablename__ = "ai_cache_entries"
    __table_args__ = (Index("ix_ai_cache_key_created", "cache_key", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("aic"))
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    previous_entry_id: Mapped[str | None] = mapped_column(String(64))


class RouteDraft(Base, TimestampMixin):
    __tablename__ = "route_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("route"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)


class RouteDraftItem(Base):
    __tablename__ = "route_draft_items"
    __table_args__ = (
        UniqueConstraint("route_draft_id", "place_id", name="uq_route_place"),
        Index("ix_route_item_order", "route_draft_id", "sort_order"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rti"))
    route_draft_id: Mapped[str] = mapped_column(ForeignKey("route_drafts.id", ondelete="CASCADE"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_secret_ref: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AccessSession(Base):
    __tablename__ = "access_sessions"
    __table_args__ = (Index("ix_sessions_hash_expiry", "token_hash", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ses"))
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    client_label: Mapped[str] = mapped_column(String(200), default="", nullable=False)


class SystemEvent(Base):
    __tablename__ = "system_events"
    __table_args__ = (
        Index("ix_system_events_created", "created_at"),
        Index("ix_system_events_component_level", "component", "level"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evt"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
