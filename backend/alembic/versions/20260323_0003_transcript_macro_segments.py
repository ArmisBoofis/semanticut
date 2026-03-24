"""Transcript macro segments for coarse semantic retrieval.

Revision ID: 20260323_0003
Revises: 20260322_0002
Create Date: 2026-03-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260323_0003"
down_revision: Union[str, None] = "20260322_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSION = 1024


def upgrade() -> None:
    op.create_table(
        "transcript_macro_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("macro_index", sa.Integer(), nullable=False),
        sa.Column("micro_chunk_start", sa.Integer(), nullable=False),
        sa.Column("micro_chunk_end", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint(
            "video_id",
            "macro_index",
            name="uq_transcript_macro_segments_video_macro_idx",
        ),
    )
    op.create_index(
        "ix_transcript_macro_segments_video_id",
        "transcript_macro_segments",
        ["video_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_macro_segments_video_id", table_name="transcript_macro_segments")
    op.drop_table("transcript_macro_segments")
