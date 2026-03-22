from __future__ import annotations

from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import AppError
from app.ingestion.cancellation import request_cancel_ingestion
from app.models.video import IngestionJob, Video

# Allowed video extensions for registration (path-based registration only in Story 2.1).
_ALLOWED_VIDEO_SUFFIXES = frozenset(
    {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".mpeg", ".mpg"}
)

_UPLOAD_SUBDIR = "uploads"


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


def _suffix_from_upload_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        return ""
    try:
        pure = PurePosixPath(filename.strip())
    except ValueError:
        return ""
    return pure.suffix.lower()


async def register_video_from_upload(
    session: AsyncSession,
    *,
    label: str,
    file: UploadFile,
) -> Video:
    """Save multipart file under VIDEO_STORAGE_ROOT/uploads and register like POST /videos."""
    suffix = _suffix_from_upload_filename(file.filename)
    if not suffix:
        raise AppError(
            "VALIDATION_ERROR",
            "le fichier doit avoir une extension vidéo reconnue",
            400,
        )
    if suffix not in _ALLOWED_VIDEO_SUFFIXES:
        raise AppError(
            "UNSUPPORTED_MEDIA",
            f"extension vidéo non prise en charge ({suffix!r})",
            400,
        )

    root = Path(settings.video_storage_root).resolve()
    upload_dir = (root / _UPLOAD_SUBDIR).resolve()
    try:
        upload_dir.relative_to(root)
    except ValueError as exc:
        raise AppError(
            "INVALID_STORAGE_PATH",
            "video storage root is misconfigured",
            500,
        ) from exc

    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4()}{suffix}"
    dest = (upload_dir / safe_name).resolve()
    try:
        dest.relative_to(root)
    except ValueError as exc:
        raise AppError(
            "INVALID_STORAGE_PATH",
            "refusing to write outside video storage root",
            500,
        ) from exc

    max_bytes = settings.video_upload_max_bytes
    written = 0
    chunk_size = 1024 * 1024
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise AppError(
                        "PAYLOAD_TOO_LARGE",
                        "fichier trop volumineux (limite dépassée)",
                        413,
                    )
                out.write(chunk)
    except AppError:
        dest.unlink(missing_ok=True)
        raise
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise AppError(
            "UPLOAD_WRITE_FAILED",
            "impossible d’enregistrer le fichier sur le serveur",
            500,
        ) from exc

    if written == 0:
        dest.unlink(missing_ok=True)
        raise AppError("VALIDATION_ERROR", "fichier vide", 400)

    relative_storage = f"{_UPLOAD_SUBDIR}/{safe_name}"
    return await create_video_with_job(session, label=label, storage_path=relative_storage)


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


async def delete_video(session: AsyncSession, *, video_id: UUID) -> None:
    """Remove a video row; ORM cascade removes the linked ingestion job row.

    Storage files are not deleted here (DB-only cleanup in Story 2.3).
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await session.execute(stmt)
    video = result.scalars().first()
    if video is None:
        raise AppError("NOT_FOUND", "video not found", 404)
    request_cancel_ingestion(video_id)
    await session.delete(video)


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


def ingestion_phase_for_video(video: Video) -> str | None:
    """Return job phase, or None if no job row."""
    job = video.ingestion_job
    if job is None:
        return None
    return job.phase


def ingestion_progress_percent_for_video(video: Video) -> int | None:
    """Return job progress percent, or None if no job row."""
    job = video.ingestion_job
    if job is None:
        return None
    return job.progress_percent


