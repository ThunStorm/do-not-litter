from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SessionRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    client_label: str = Field(default="", max_length=200)


class CaptureRequest(BaseModel):
    url: HttpUrl | None = None
    text: str | None = Field(default=None, max_length=2_000_000)
    title: str | None = Field(default=None, max_length=500)


class CaptureResponse(BaseModel):
    source_id: str
    job_id: str
    job_type: str
    status: str


class JobView(BaseModel):
    id: str
    job_type: str
    status: str
    current_step: str
    progress: int
    title: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


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
    name: str
    place_type: str
    latitude: float
    longitude: float
    user_state: str
    summary: str


class PlacePreview(BaseModel):
    id: str
    name: str
    address: str
    place_type: str
    summary: str
    user_state: str
    observations: list[dict[str, Any]]


class MapOverviewView(BaseModel):
    coordinate_system: str = "GCJ02"
    total_places: int
    visible_places: int
    markers: list[MapMarker]
    clusters: list[dict[str, Any]] = []
    selected_place_id: str | None = None
    selected_preview: PlacePreview | None = None
    route_draft_count: int = 0


class RouteDraftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    city: str = Field(default="", max_length=64)
    place_ids: list[str] = []


class RouteDraftUpdate(BaseModel):
    place_ids: list[str]


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
    timeout_seconds: int = 60
    api_key: str | None = None
