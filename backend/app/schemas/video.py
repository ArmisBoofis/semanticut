from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VideoCreateRequest(BaseModel):
    """Request body for POST /videos."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1, max_length=512)
    storage_path: str = Field(..., min_length=1)


class VideoCreatedResponse(BaseModel):
    """201 response for POST /videos — direct payload (no wrapper)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    storage_path: str
    ingestion_status: str = Field(
        ...,
        description=(
            "Value from `ingestion_jobs.status` for this video (e.g. `pending`). "
            "Reserved value `unknown` means no related job row (data integrity issue)."
        ),
    )
    created_at: datetime


class VideoIngestionStatusResponse(BaseModel):
    """GET /videos/{video_id}/status — detailed ingestion job payload."""

    model_config = ConfigDict(from_attributes=True)

    video_id: UUID
    job_id: UUID
    status: str
    phase: str | None = None
    progress_percent: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoListItem(BaseModel):
    """Single item in GET /videos array."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    ingestion_status: str = Field(
        ...,
        description=(
            "Value from `ingestion_jobs.status` for this video (e.g. `pending`). "
            "Reserved value `unknown` means no related job row (data integrity issue)."
        ),
    )
    ingestion_phase: str | None = Field(
        default=None,
        description="Current ingestion phase from `ingestion_jobs.phase` when a job exists.",
    )
    ingestion_progress_percent: int | None = Field(
        default=None,
        description="Progress 0–100 from `ingestion_jobs.progress_percent` when set.",
    )
    created_at: datetime


class VideoSearchRequest(BaseModel):
    """Body for POST /videos/{video_id}/search."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=4000)


class VideoSearchMatchResponse(BaseModel):
    """200 response for semantic search — fine micro segment + macro context for UI."""

    start_ts: float = Field(..., description="Fine (micro) segment start in seconds from video start.")
    end_ts: float = Field(..., description="Fine (micro) segment end in seconds from video start.")
    text: str = Field(..., description="Fine segment text (seek/snippet).")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Derived from cosine distance on the fine pass (higher is better).",
    )
    macro_context_text: str = Field(
        ...,
        description="Full coarse unit text; micro highlight is a slice via offsets.",
    )
    match_start_offset: int = Field(
        ...,
        ge=0,
        description="Start index into macro_context_text for the fine span (Python str semantics).",
    )
    match_end_offset: int = Field(
        ...,
        ge=0,
        description="End index into macro_context_text (exclusive) for the fine span.",
    )
    match_quality: Literal["strong", "partial", "weak"] = Field(
        ...,
        description="Tiered relevance (avoids misleading percentage scoreboards).",
    )
