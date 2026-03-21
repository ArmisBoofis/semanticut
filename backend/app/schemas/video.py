from datetime import datetime
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
