from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SessionRequest(BaseModel):
    token: str = Field(pattern=r"^\d{4}$")
    client_label: str = Field(default="", max_length=200)


class CaptureRequest(BaseModel):
    url: HttpUrl | None = None
    text: str | None = Field(default=None, max_length=2_000_000)
    title: str | None = Field(default=None, max_length=500)
    ai_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict, max_length=3)


class CaptureResponse(BaseModel):
    source_id: str
    job_id: str
    job_type: str
    status: str


class StepReplayRequest(BaseModel):
    step_name: str = Field(min_length=1, max_length=64)
    source_event_id: str | None = Field(default=None, max_length=64)


class JobView(BaseModel):
    id: str
    job_type: str
    status: str
    current_step: str
    progress: int
    title: str
    error: str | None
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    retry_count: int = 0
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    last_activity_at: datetime | None = None
    current_step_status: str | None = None
    current_step_started_at: datetime | None = None
    current_step_message: str | None = None
    runtime_state: str = "UNKNOWN"
    last_activity_age_seconds: int | None = None
    last_activity_source: str | None = None
    completion_summary: str | None = None
    model_step: str | None = None
    provider: str | None = None
    model: str | None = None


class ContentView(BaseModel):
    id: str
    content_type: str
    title: str
    summary: str
    status: str
    user_state: str
    structured: dict[str, Any]
    updated_at: datetime


class MapMarker(BaseModel):
    id: str
    marker_id: str | None = None
    place_id: str | None = None
    origin: str = "AI_EXTRACTED"
    visibility: str = "VISIBLE"
    name: str
    canonical_name: str = ""
    place_type: str
    latitude: float
    longitude: float
    user_state: str
    summary: str
    address: str = ""
    preview_image: str | None = None
    brief: dict[str, Any] = {}
    source_count: int = 0


class PlacePreview(BaseModel):
    id: str
    name: str
    address: str
    place_type: str
    summary: str
    user_state: str
    observations: list[dict[str, Any]]


class PlaceInsightView(BaseModel):
    id: str
    insight_type: str
    value_key: str
    value_text: str
    value_json: dict[str, Any]
    provenance: str
    confidence: float
    status: str
    segment_ids: list[str]


class PlaceVisitWindowView(BaseModel):
    id: str
    season: str | None = None
    month: int | None = None
    month_segment: str | None = None
    day_time_slot: str | None = None
    period_type: str = "BEST_VISIT"
    suitability: str = "INFORMATIONAL"
    source_text: str = ""
    segment_ids: list[str] = Field(default_factory=list)
    provenance: str
    confidence: float
    status: str


class PlaceVisitWindowUpdate(BaseModel):
    season: str | None = Field(default=None, pattern="^(SPRING|SUMMER|AUTUMN|WINTER)$")
    month: int | None = Field(default=None, ge=1, le=12)
    month_segment: str | None = Field(default=None, pattern="^(EARLY|MID|LATE)$")
    day_time_slot: str | None = Field(
        default=None,
        pattern="^(EARLY_MORNING|MORNING|NOON|AFTERNOON|SUNSET|EVENING|NIGHT|BREAKFAST|LUNCH|DINNER|LATE_NIGHT)$",
    )
    period_type: str = Field(
        default="BEST_VISIT",
        pattern="^(BEST_VISIT|BEST_VIEWING|HIGH_WATER|LOW_WATER|FISHING_CLOSURE|SEASONAL_CLOSURE|BLOOM|FOLIAGE|SNOW|MIGRATION|WEATHER_SEASON|PEAK_SEASON|OFF_SEASON|OTHER)$",
    )
    suitability: str = Field(default="RECOMMENDED", pattern="^(RECOMMENDED|AVOID|RESTRICTED|INFORMATIONAL)$")
    source_text: str = Field(default="", max_length=500)

    def model_post_init(self, __context: Any) -> None:
        if not any((self.season, self.month, self.month_segment, self.day_time_slot, self.source_text)):
            raise ValueError("至少选择一个适宜时间条件")


class BulkPlaceUpdate(BaseModel):
    place_ids: list[str] = Field(min_length=1, max_length=100)
    action: Literal["hide", "restore", "state", "add_route", "remove_route"]
    value: str | None = Field(default=None, max_length=100)


class PlaceDetailView(PlacePreview):
    coordinate_system: str
    coordinates: list[float]
    provider: str | None = None
    external_poi_id: str | None = None
    metadata: dict[str, Any]
    insights: list[PlaceInsightView] = Field(default_factory=list)
    visit_windows: list[PlaceVisitWindowView] = Field(default_factory=list)
    display: dict[str, Any] = Field(default_factory=dict)
    note: dict[str, Any] = Field(default_factory=dict)
    marker: dict[str, Any] = Field(default_factory=dict)


class PlaceNoteUpdate(BaseModel):
    markdown: str = Field(max_length=20_000)
    expected_revision: int = Field(ge=0)


class PlaceOverlayUpdate(BaseModel):
    display_name: str = Field(default="", max_length=300)
    override_place_type: str = Field(default="", max_length=64)
    custom_tags: list[str] = Field(default_factory=list, max_length=30)
    expected_revision: int = Field(ge=0)


class ManualPlaceCreate(BaseModel):
    mode: Literal["CUSTOM", "AMAP_POI"] = "CUSTOM"
    name: str = Field(default="", max_length=300)
    place_type: str = Field(default="LANDMARK", max_length=64)
    longitude: float
    latitude: float
    note: str = Field(default="", max_length=20_000)
    poi_id: str | None = Field(default=None, max_length=128)


class POIReviewDecision(BaseModel):
    provider: Literal["AMAP"] = "AMAP"
    poi_id: str = Field(min_length=1, max_length=128)
    expected_revision: int | None = Field(default=None, ge=0)


class POISearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    expected_revision: int = Field(ge=0)


class NearbyPOIRequest(BaseModel):
    longitude: float
    latitude: float


class MapOverviewView(BaseModel):
    coordinate_system: str = "GCJ02"
    total_places: int
    visible_places: int
    markers: list[MapMarker]
    clusters: list[dict[str, Any]] = []
    selected_place_id: str | None = None
    selected_preview: PlacePreview | None = None
    route_draft_count: int = 0
    viewport: dict[str, Any] = {}


class PlaceListView(BaseModel):
    items: list[MapMarker]
    next_cursor: str | None = None
    total: int


class MapMarkerCreate(BaseModel):
    longitude: float | None = None
    latitude: float | None = None
    custom_name: str | None = Field(default=None, max_length=300)
    place_type: str = Field(default="LANDMARK", max_length=64)
    summary: str = Field(default="", max_length=2000)
    provider_poi_id: str | None = Field(default=None, max_length=128)


class RouteDraftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    city: str = Field(default="", max_length=64)
    place_ids: list[str] = []


class RouteDraftUpdate(BaseModel):
    place_ids: list[str]


class RouteDraftMetadataUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    city: str = Field(default="", max_length=64)


class PlaceInsightUpdate(BaseModel):
    insight_type: str = Field(min_length=1, max_length=64)
    value_key: str = Field(default="", max_length=128)
    value_text: str = Field(min_length=1, max_length=500)
    value_json: dict[str, Any] = Field(default_factory=dict)


class RouteDraftView(BaseModel):
    id: str
    name: str
    city: str
    status: str
    places: list[PlacePreview]


class ProviderConfig(BaseModel):
    provider: str
    base_url: str
    model: str
    timeout_seconds: int = Field(default=300, ge=5, le=900)
    api_key: str | None = None


class ModelProfileConfig(ProviderConfig):
    name: str = Field(min_length=1, max_length=80)
    location: Literal["LOCAL", "REMOTE"] | None = None
    modalities: set[str] = Field(default_factory=lambda: {"text"})
    capabilities: set[str] = Field(default_factory=set)
    supports_json_mode: bool = False
    supports_json_schema: bool = False
    supports_thinking: bool = False
    supports_tools: bool = False
    context_window: int = Field(default=32_768, ge=1, le=1_000_000)
    recommended_working_context: int = Field(default=8_192, ge=1, le=1_000_000)
    max_output_tokens: int = Field(default=4_096, ge=1, le=131_072)
    quality_tier: Literal["FAST", "MAIN", "STRONG", "SPECIALIST"] = "MAIN"
    specialties: set[str] = Field(default_factory=set)
    enabled: bool = True


class ModelRoutingConfig(BaseModel):
    primary_id: str | None = None
    fallback_id: str | None = None


class TranscriptProcessingConfig(BaseModel):
    chunk_chars: int = Field(default=12_000, ge=2_000, le=24_000)
    batch_size: int = Field(default=128, ge=16, le=256)
    timeout_seconds: float = Field(default=180, ge=30, le=300)


class PromptSupplementsConfig(BaseModel):
    transcript_correction: str = Field(default="", max_length=1000)
    video_note_summary: str = Field(default="", max_length=1000)
    travel_place_extraction: str = Field(default="", max_length=1000)

    @field_validator("transcript_correction", "video_note_summary", "travel_place_extraction")
    @classmethod
    def reject_contract_overrides(cls, value: str) -> str:
        text = value.strip()
        forbidden = re.compile(
            r"(?:忽略|覆盖|取代|撤销|绕过).{0,20}(?:规则|提示词|系统|约束|契约|格式|结构)"
            r"|(?:JSON|Schema|response[_ -]?format|system prompt|ignore previous)"
            r"|(?:输出|返回).{0,8}(?:格式|结构|字段|键名)"
            r"|(?:新增|删除|修改).{0,8}(?:字段|键名|ID|顺序)"
            r"|(?:Segment\s*ID|ID).{0,8}(?:重复|顺序|唯一)",
            re.IGNORECASE,
        )
        if forbidden.search(text):
            raise ValueError("补充提示词不能修改核心 JSON、字段、ID、顺序或系统契约")
        return text


class ProfileConfig(BaseModel):
    name: str = Field(default="", max_length=100)
    education: str = Field(default="", max_length=100)
    major: str = Field(default="", max_length=120)
    graduation_year: str = Field(default="", max_length=20)
    graduate_status: str = Field(default="", max_length=80)
    household_registration: str = Field(default="", max_length=120)
    preferred_regions: list[str] = []


class GeneralConfig(BaseModel):
    app_name: str = Field(default="至简", min_length=1, max_length=40)
    default_city: str = Field(default="", max_length=64)
    data_retention_days: int = Field(default=90, ge=7, le=3650)
    ai_retry_count: int = Field(default=1, ge=0, le=3)
    ai_retry_wait_seconds: float = Field(default=5, ge=0, le=300)
    ai_request_interval_seconds: float = Field(default=3, ge=0, le=60)
    ai_max_model_attempts_per_job: int = Field(default=48, ge=1, le=500)
    ai_max_remote_prompt_tokens_per_job: int = Field(default=300_000, ge=1_000, le=10_000_000)
    ai_max_remote_completion_tokens_per_job: int = Field(default=100_000, ge=1_000, le=10_000_000)
    ai_max_local_prompt_tokens_per_job: int = Field(default=600_000, ge=1_000, le=10_000_000)
    ai_max_local_completion_tokens_per_job: int = Field(default=200_000, ge=1_000, le=10_000_000)
    ai_max_wall_time_seconds_per_job: int = Field(default=1_800, ge=60, le=86_400)


class AMapConfig(BaseModel):
    js_key: str = Field(default="", max_length=256)
    security_code: str | None = Field(default=None, max_length=512)
    web_service_key: str | None = Field(default=None, max_length=512)
