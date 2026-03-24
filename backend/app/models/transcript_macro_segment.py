from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.transcript_segment import EMBEDDING_DIMENSION

if TYPE_CHECKING:
    from app.models.video import Video


class TranscriptMacroSegment(Base):
    """Coarse retrieval unit: concatenated micro spans with one embedding per row."""

    __tablename__ = "transcript_macro_segments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    video_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    macro_index: Mapped[int] = mapped_column(Integer, nullable=False)
    micro_chunk_start: Mapped[int] = mapped_column(Integer, nullable=False)
    micro_chunk_end: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ts: Mapped[float] = mapped_column(Float, nullable=False)
    end_ts: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    video: Mapped["Video"] = relationship(back_populates="transcript_macro_segments")
