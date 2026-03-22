"""Async ingestion pipeline orchestration (worker entrypoints)."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.ingestion import phases
from app.ingestion.cancellation import clear_cancel_request, is_cancel_requested
from app.models.transcript_segment import TranscriptSegment
from app.models.video import IngestionJob, Video
from app.services import mistral_client

logger = logging.getLogger(__name__)


def resolve_video_file_path(storage_path: str) -> Path:
    """Map registered `storage_path` to a host path (see `VIDEO_STORAGE_ROOT` for relative paths)."""
    raw = storage_path.strip()
    p = PurePosixPath(raw)
    if p.is_absolute():
        return Path(raw)
    root = Path(settings.video_storage_root)
    return (root / raw).resolve()


async def ffprobe_duration_seconds(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    proc = await asyncio.to_thread(_run)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "ffprobe failed")
    data = json.loads(proc.stdout)
    dur = float(data.get("format", {}).get("duration", 0.0) or 0.0)
    if dur <= 0:
        raise RuntimeError("could not read media duration")
    return dur


async def extract_audio_wav(video_path: Path, out_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out_path),
    ]

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    proc = await asyncio.to_thread(_run)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "ffmpeg audio extraction failed")


def _split_text_into_time_chunks(
    text: str,
    duration_sec: float,
    *,
    max_chars: int = 700,
    overlap: int = 80,
) -> list[tuple[float, float, str]]:
    """Split long transcript text into timestamped chunks (proportional to character span)."""
    n = len(text)
    if n == 0:
        return []
    if duration_sec <= 0:
        duration_sec = 1.0
    chunks: list[tuple[float, float, str]] = []
    start_idx = 0
    while start_idx < n:
        end_idx = min(n, start_idx + max_chars)
        chunk = text[start_idx:end_idx].strip()
        if not chunk:
            break
        t0 = (start_idx / n) * duration_sec
        t1 = (end_idx / n) * duration_sec
        if t1 <= t0:
            t1 = t0 + 0.05
        chunks.append((t0, t1, chunk))
        if end_idx >= n:
            break
        start_idx = end_idx - overlap
        if start_idx < 0:
            start_idx = 0
    return chunks


def _chunks_from_transcription(
    transcript: mistral_client.TranscriptionResult,
    media_duration: float,
) -> list[tuple[float, float, str]]:
    if transcript.segments:
        out: list[tuple[float, float, str]] = []
        for s in transcript.segments:
            out.append((s.start, max(s.end, s.start + 0.05), s.text))
        return out
    text = transcript.text.strip()
    if not text:
        return []
    return _split_text_into_time_chunks(text, media_duration)


async def _apply_job_update(
    session: AsyncSession,
    job_id: UUID,
    *,
    status: str | None = None,
    phase: str | None = None,
    progress_percent: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Apply partial job update; does not commit."""
    values: dict = {}
    if status is not None:
        values["status"] = status
    if phase is not None:
        values["phase"] = phase
    if progress_percent is not None:
        values["progress_percent"] = progress_percent
    if error_code is not None:
        values["error_code"] = error_code
    if error_message is not None:
        values["error_message"] = error_message
    if not values:
        return
    await session.execute(update(IngestionJob).where(IngestionJob.id == job_id).values(**values))


async def claim_next_pending_job(session: AsyncSession) -> tuple[UUID, UUID] | None:
    """Lock one pending job and mark it running (SKIP LOCKED). Returns (job_id, video_id)."""
    stmt = (
        select(IngestionJob)
        .where(IngestionJob.status == IngestionJob.STATUS_PENDING)
        .order_by(IngestionJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = IngestionJob.STATUS_RUNNING
    job.phase = phases.PHASE_EXTRACTING_AUDIO
    job.progress_percent = phases.progress_at_phase_start(phases.PHASE_EXTRACTING_AUDIO)
    job.error_code = None
    job.error_message = None
    await session.flush()
    return job.id, job.video_id


async def video_exists(session: AsyncSession, video_id: UUID) -> bool:
    n = await session.scalar(select(func.count()).select_from(Video).where(Video.id == video_id))
    return bool(n)


async def run_ingestion_for_job(job_id: UUID, video_id: UUID) -> None:
    """Execute ingestion phases for a claimed job. Uses fresh sessions per step."""
    from app.db import async_session_maker

    clear_cancel_request(video_id)

    async with async_session_maker() as session:
        if not await video_exists(session, video_id):
            logger.info("ingestion skipped: video %s no longer exists", video_id)
            return
        job_row = await session.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
        if job_row is None or job_row.status != IngestionJob.STATUS_RUNNING:
            return
        video = await session.scalar(
            select(Video)
            .options(selectinload(Video.ingestion_job))
            .where(Video.id == video_id),
        )
        if video is None:
            return
        storage_path = video.storage_path

    video_file = resolve_video_file_path(storage_path)
    if not video_file.is_file():
        async with async_session_maker() as session:
            await _fail_job(
                session,
                job_id,
                code="FILE_NOT_FOUND",
                message="Video file is missing or not readable at the configured path.",
                phase=phases.PHASE_EXTRACTING_AUDIO,
            )
        return

    if not settings.mistral_api_key:
        async with async_session_maker() as session:
            await _fail_job(
                session,
                job_id,
                code="MISTRAL_NOT_CONFIGURED",
                message="Mistral API key is not configured on the server.",
                phase=phases.PHASE_EXTRACTING_AUDIO,
            )
        return

    try:
        media_duration = await ffprobe_duration_seconds(video_file)
    except Exception as exc:
        mistral_client.log_mistral_error(exc, context="ffprobe")
        async with async_session_maker() as session:
            await _fail_job(
                session,
                job_id,
                code="MEDIA_PROBE_FAILED",
                message="Could not read video duration (ffprobe).",
                phase=phases.PHASE_EXTRACTING_AUDIO,
            )
        return

    if is_cancel_requested(video_id):
        async with async_session_maker() as session:
            await _fail_job(
                session,
                job_id,
                code="CANCELLED",
                message="Ingestion was cancelled.",
                phase=phases.PHASE_EXTRACTING_AUDIO,
            )
        return

    with tempfile.TemporaryDirectory(prefix="semanticut-ingest-") as tmp:
        tmp_path = Path(tmp)
        audio_path = tmp_path / "audio.wav"
        try:
            await extract_audio_wav(video_file, audio_path)
        except Exception as exc:
            logger.exception("ffmpeg extraction failed: %s", exc)
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="AUDIO_EXTRACTION_FAILED",
                    message="Audio extraction failed (ffmpeg).",
                    phase=phases.PHASE_EXTRACTING_AUDIO,
                )
            return

        async with async_session_maker() as session:
            if not await video_exists(session, video_id):
                logger.info("video deleted during extraction: %s", video_id)
                return
            await _apply_job_update(
                session,
                job_id,
                phase=phases.PHASE_TRANSCRIBING,
                progress_percent=phases.progress_at_phase_start(phases.PHASE_TRANSCRIBING),
            )
            await session.commit()

        if is_cancel_requested(video_id):
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="CANCELLED",
                    message="Ingestion was cancelled.",
                    phase=phases.PHASE_TRANSCRIBING,
                )
            return

        try:
            transcript = await asyncio.to_thread(mistral_client.transcribe_audio_file, audio_path)
        except Exception as exc:
            mistral_client.log_mistral_error(exc, context="transcription")
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="TRANSCRIPTION_FAILED",
                    message="Transcription failed. Check server logs.",
                    phase=phases.PHASE_TRANSCRIBING,
                )
            return

        async with async_session_maker() as session:
            if not await video_exists(session, video_id):
                logger.info("video deleted during transcription: %s", video_id)
                return
            await _apply_job_update(
                session,
                job_id,
                phase=phases.PHASE_CHUNKING,
                progress_percent=phases.progress_at_phase_start(phases.PHASE_CHUNKING),
            )
            await session.commit()

        chunks = _chunks_from_transcription(transcript, media_duration)
        if not chunks:
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="EMPTY_TRANSCRIPT",
                    message="Transcription returned no usable text.",
                    phase=phases.PHASE_CHUNKING,
                )
            return

        async with async_session_maker() as session:
            if not await video_exists(session, video_id):
                return
            await _apply_job_update(
                session,
                job_id,
                phase=phases.PHASE_EMBEDDING,
                progress_percent=phases.progress_at_phase_start(phases.PHASE_EMBEDDING),
            )
            await session.commit()

        texts = [c[2] for c in chunks]
        try:
            embeddings = await asyncio.to_thread(mistral_client.embed_texts_batch, texts)
            if len(embeddings) != len(chunks):
                raise RuntimeError("embedding count does not match chunk count")
        except Exception as exc:
            mistral_client.log_mistral_error(exc, context="embeddings")
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="EMBEDDING_FAILED",
                    message="Embedding generation failed. Check server logs.",
                    phase=phases.PHASE_EMBEDDING,
                )
            return

        async with async_session_maker() as session:
            if not await video_exists(session, video_id):
                return
            await _apply_job_update(
                session,
                job_id,
                phase=phases.PHASE_INDEXING,
                progress_percent=phases.progress_at_phase_start(phases.PHASE_INDEXING),
            )
            await session.commit()

        async with async_session_maker() as session:
            if not await video_exists(session, video_id):
                return
            await session.execute(delete(TranscriptSegment).where(TranscriptSegment.video_id == video_id))
            for idx, ((t0, t1, text), emb) in enumerate(zip(chunks, embeddings, strict=True)):
                session.add(
                    TranscriptSegment(
                        video_id=video_id,
                        chunk_index=idx,
                        start_ts=t0,
                        end_ts=t1,
                        text=text,
                        embedding=emb,
                    )
                )
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(
                    status=IngestionJob.STATUS_COMPLETED,
                    phase=None,
                    progress_percent=100,
                    error_code=None,
                    error_message=None,
                )
            )
            await session.commit()

    clear_cancel_request(video_id)


async def _fail_job(
    session: AsyncSession,
    job_id: UUID,
    *,
    code: str,
    message: str,
    phase: str | None,
) -> None:
    await session.execute(
        update(IngestionJob)
        .where(IngestionJob.id == job_id)
        .values(
            status=IngestionJob.STATUS_FAILED,
            error_code=code,
            error_message=message,
            phase=phase,
        )
    )
    await session.commit()


async def get_ingestion_status_payload(session: AsyncSession, video_id: UUID) -> dict | None:
    """Return status dict for GET /videos/{id}/status, or None if video missing."""
    stmt = (
        select(Video)
        .options(selectinload(Video.ingestion_job))
        .where(Video.id == video_id)
    )
    result = await session.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        return None
    job = video.ingestion_job
    if job is None:
        return None
    return {
        "video_id": video.id,
        "job_id": job.id,
        "status": job.status,
        "phase": job.phase,
        "progress_percent": job.progress_percent,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
