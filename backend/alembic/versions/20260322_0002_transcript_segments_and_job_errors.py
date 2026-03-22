"""Transcript segments with embeddings; ingestion job error fields.

Revision ID: 20260322_0002
Revises: 20260321_0001
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0002"
down_revision: Union[str, None] = "20260321_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match Mistral `mistral-embed` output dimension (architecture / product brief).
EMBEDDING_DIMENSION = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "ingestion_jobs",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "transcript_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_ts", sa.Float(), nullable=False),
        sa.Column("end_ts", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            Vector(EMBEDDING_DIMENSION),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "chunk_index", name="uq_transcript_segments_video_chunk"),
    )
    op.create_index(
        "ix_transcript_segments_video_id",
        "transcript_segments",
        ["video_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_segments_video_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_column("ingestion_jobs", "error_code")
    op.drop_column("ingestion_jobs", "error_message")
