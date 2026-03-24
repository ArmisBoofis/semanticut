from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.transcript_macro_segment import TranscriptMacroSegment
from app.models.transcript_segment import TranscriptSegment

# Primary keys use UUID (v4) — stable public identifiers for REST and joins across Epic 2+.


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transcript_segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by=TranscriptSegment.chunk_index,
    )
    transcript_macro_segments: Mapped[list[TranscriptMacroSegment]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by=TranscriptMacroSegment.macro_index,
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    # Canonical job status for newly registered videos (Epic 2).
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    video_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    video: Mapped["Video"] = relationship(back_populates="ingestion_job")
