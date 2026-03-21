from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import AppError
from app.models.video import IngestionJob, Video

# Allowed video extensions for registration (path-based registration only in Story 2.1).
_ALLOWED_VIDEO_SUFFIXES = frozenset(
    {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".mpeg", ".mpg"}
)


def validate_registration(label: str, storage_path: str) -> tuple[str, str]:
    """Normalize and validate registration fields; raises AppError on failure."""
    label_clean = label.strip()
    path_clean = storage_path.strip()
    if not label_clean:
        raise AppError("VALIDATION_ERROR", "label cannot be empty", 400)
    if not path_clean:
        raise AppError("VALIDATION_ERROR", "storage_path cannot be empty", 400)
    if "\x00" in path_clean:
        raise AppError("INVALID_STORAGE_PATH", "storage_path contains invalid characters", 400)
    try:
        pure = PurePosixPath(path_clean)
    except ValueError as exc:
        raise AppError("INVALID_STORAGE_PATH", str(exc), 400) from exc
    if pure.is_absolute():
        for part in pure.parts:
            if part == "..":
                raise AppError(
                    "INVALID_STORAGE_PATH",
                    "absolute paths must not contain parent directory segments",
                    400,
                )
    else:
        if ".." in pure.parts:
            raise AppError(
                "INVALID_STORAGE_PATH",
                "relative paths must not contain parent directory segments",
                400,
            )
    suffix = pure.suffix.lower()
    if suffix not in _ALLOWED_VIDEO_SUFFIXES:
        raise AppError(
            "UNSUPPORTED_MEDIA",
            f"unsupported or missing video file extension (got {suffix!r})",
            400,
        )
    return label_clean, path_clean


async def create_video_with_job(
    session: AsyncSession,
    *,
    label: str,
    storage_path: str,
) -> Video:
    label_ok, path_ok = validate_registration(label, storage_path)
    video = Video(label=label_ok, storage_path=path_ok)
    video.ingestion_job = IngestionJob(status=IngestionJob.STATUS_PENDING)
    session.add(video)
    await session.flush()
    await session.refresh(video, attribute_names=["ingestion_job"])
    return video


async def list_videos(session: AsyncSession) -> list[Video]:
    stmt = (
        select(Video)
        .options(selectinload(Video.ingestion_job))
        .order_by(Video.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def ingestion_status_for_video(video: Video) -> str:
    """Return job status, or reserved `unknown` if the relationship is missing."""
    job = video.ingestion_job
    if job is None:
        return "unknown"
    return job.status


