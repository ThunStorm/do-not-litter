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
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Place(Base, TimestampMixin):
    __tablename__ = "places"
    __table_args__ = (Index("ix_places_city_status", "city", "resolution_status"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("plc"))
    content_item_id: Mapped[str | None] = mapped_column(ForeignKey("content_items.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    place_type: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="中国", nullable=False)
    province: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    district: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    coordinate_system: Mapped[str] = mapped_column(String(16), default="GCJ02", nullable=False)
    external_provider: Mapped[str | None] = mapped_column(String(64))
    external_poi_id: Mapped[str | None] = mapped_column(String(128))
    resolution_status: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    user_state: Mapped[str] = mapped_column(String(32), default="DISCOVERED", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PlaceObservation(Base):
    __tablename__ = "place_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("obs"))
    place_id: Mapped[str] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    segment_id: Mapped[str | None] = mapped_column(ForeignKey("segments.id", ondelete="SET NULL"))
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
