"""Async ingestion pipeline orchestration (worker entrypoints)."""

from __future__ import annotations

import asyncio
import dataclasses
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
from app.models.transcript_macro_segment import TranscriptMacroSegment
from app.models.transcript_segment import TranscriptSegment
from app.models.video import IngestionJob, Video
from app.services import mistral_client
from app.services.macro_grouping import (
    MicroSpan,
    group_micros_into_macros,
    group_micros_into_macros_by_words,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class FragmentPlanItem:
    index: int
    start_offset_sec: float
    duration_sec: float


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


async def extract_audio_fragment_wav(
    video_path: Path,
    *,
    start_offset_sec: float,
    duration_sec: float,
    out_path: Path,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_offset_sec:.6f}",
        "-t",
        f"{duration_sec:.6f}",
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
        raise RuntimeError(proc.stderr or "ffmpeg fragment extraction failed")


def build_fragment_plan(
    *,
    duration_seconds: float,
    max_fragment_seconds: int,
) -> list[FragmentPlanItem]:
    safe_duration = max(0.0, float(duration_seconds))
    max_sec = max(1, int(max_fragment_seconds))
    if safe_duration <= 0:
        return []

    out: list[FragmentPlanItem] = []
    current_start = 0.0
    idx = 0
    while current_start < safe_duration:
        remaining = safe_duration - current_start
        frag_dur = min(float(max_sec), remaining)
        out.append(
            FragmentPlanItem(
                index=idx,
                start_offset_sec=current_start,
                duration_sec=frag_dur,
            )
        )
        current_start += frag_dur
        idx += 1
    return out


def merge_fragment_chunks_with_global_timestamps(
    *,
    fragment_plan: list[FragmentPlanItem],
    fragment_chunks: list[list[tuple[float, float, str]]],
) -> list[tuple[float, float, str]]:
    if len(fragment_plan) != len(fragment_chunks):
        raise ValueError("fragment plan and chunks length mismatch")
    merged: list[tuple[float, float, str]] = []
    prev_start = -1.0
    for frag, local_chunks in zip(fragment_plan, fragment_chunks, strict=True):
        offset = frag.start_offset_sec
        for local_start, local_end, text in local_chunks:
            global_start = local_start + offset
            global_end = max(local_end + offset, global_start)
            if global_start < prev_start:
                raise ValueError("non-monotonic reconstructed timestamps")
            merged.append((global_start, global_end, text))
            prev_start = global_start
    return merged


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

    fragment_threshold = settings.ingestion_fragment_max_seconds
    fragment_mode = media_duration > fragment_threshold
    fragment_plan = (
        build_fragment_plan(
            duration_seconds=media_duration,
            max_fragment_seconds=fragment_threshold,
        )
        if fragment_mode
        else []
    )
    if fragment_mode:
        logger.info(
            "fragment_plan_built video_id=%s fragment_count=%s duration_seconds=%.3f max_fragment_seconds=%s",
            video_id,
            len(fragment_plan),
            media_duration,
            fragment_threshold,
        )

    with tempfile.TemporaryDirectory(prefix="semanticut-ingest-") as tmp:
        tmp_path = Path(tmp)
        audio_path = tmp_path / "audio.wav"
        if fragment_mode:
            async with async_session_maker() as session:
                if not await video_exists(session, video_id):
                    logger.info("video deleted before fragment transcription: %s", video_id)
                    return
                await _apply_job_update(
                    session,
                    job_id,
                    phase=phases.PHASE_TRANSCRIBING,
                    progress_percent=phases.progress_at_phase_start(phases.PHASE_TRANSCRIBING),
                )
                await session.commit()

            all_fragment_chunks: list[list[tuple[float, float, str]]] = []
            transcribing_start = phases.progress_at_phase_start(phases.PHASE_TRANSCRIBING)
            transcribing_end = phases.progress_at_phase_start(phases.PHASE_CHUNKING)
            transcribing_span = max(1, transcribing_end - transcribing_start)
            total_fragments = len(fragment_plan)

            for frag_idx, fragment in enumerate(fragment_plan):
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

                fragment_audio = tmp_path / f"audio-fragment-{fragment.index:04d}.wav"
                try:
                    await extract_audio_fragment_wav(
                        video_path=video_file,
                        start_offset_sec=fragment.start_offset_sec,
                        duration_sec=fragment.duration_sec,
                        out_path=fragment_audio,
                    )
                except Exception as exc:
                    logger.exception("ffmpeg fragment extraction failed: %s", exc)
                    async with async_session_maker() as session:
                        await _fail_job(
                            session,
                            job_id,
                            code="AUDIO_EXTRACTION_FAILED",
                            message="Audio extraction failed (ffmpeg).",
                            phase=phases.PHASE_EXTRACTING_AUDIO,
                        )
                    return

                try:
                    transcript = await asyncio.to_thread(
                        mistral_client.transcribe_audio_file,
                        fragment_audio,
                    )
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

                fragment_chunks = _chunks_from_transcription(transcript, fragment.duration_sec)
                if not fragment_chunks:
                    async with async_session_maker() as session:
                        await _fail_job(
                            session,
                            job_id,
                            code="EMPTY_TRANSCRIPT",
                            message="Transcription returned no usable text.",
                            phase=phases.PHASE_TRANSCRIBING,
                        )
                    return
                all_fragment_chunks.append(fragment_chunks)

                progress = transcribing_start + int(
                    ((frag_idx + 1) / total_fragments) * transcribing_span
                )
                progress = min(progress, transcribing_end)
                async with async_session_maker() as session:
                    if not await video_exists(session, video_id):
                        logger.info("video deleted during fragment transcription: %s", video_id)
                        return
                    await _apply_job_update(
                        session,
                        job_id,
                        phase=phases.PHASE_TRANSCRIBING,
                        progress_percent=progress,
                    )
                    await session.commit()

            try:
                chunks = merge_fragment_chunks_with_global_timestamps(
                    fragment_plan=fragment_plan,
                    fragment_chunks=all_fragment_chunks,
                )
            except ValueError as exc:
                async with async_session_maker() as session:
                    await _fail_job(
                        session,
                        job_id,
                        code="CHUNK_RECONSTRUCTION_FAILED",
                        message=str(exc),
                        phase=phases.PHASE_CHUNKING,
                    )
                return
            logger.info(
                "fragment_reconstruction_summary video_id=%s fragment_count=%s merged_segment_count=%s min_start_ts=%.3f max_end_ts=%.3f",
                video_id,
                len(fragment_plan),
                len(chunks),
                chunks[0][0],
                chunks[-1][1],
            )
        else:
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
                logger.info("video deleted during chunking: %s", video_id)
                return
            await _apply_job_update(
                session,
                job_id,
                phase=phases.PHASE_CHUNKING,
                progress_percent=phases.progress_at_phase_start(phases.PHASE_CHUNKING),
            )
            await session.commit()

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

        micro_spans = [
            MicroSpan(chunk_index=idx, start_ts=t0, end_ts=t1, text=text)
            for idx, (t0, t1, text) in enumerate(chunks)
        ]
        if settings.transcript_macro_target_mode == "chars":
            macro_groups = group_micros_into_macros(
                micro_spans,
                target_chars=settings.transcript_macro_target_chars,
            )
        else:
            macro_groups = group_micros_into_macros_by_words(
                micro_spans,
                target_words=settings.transcript_macro_target_words,
            )
        macro_texts = [g.text for g in macro_groups]
        try:
            macro_embeddings = await asyncio.to_thread(
                mistral_client.embed_texts_batch,
                macro_texts,
            )
            if len(macro_embeddings) != len(macro_groups):
                raise RuntimeError("macro embedding count does not match macro group count")
        except Exception as exc:
            mistral_client.log_mistral_error(exc, context="macro_embeddings")
            async with async_session_maker() as session:
                await _fail_job(
                    session,
                    job_id,
                    code="EMBEDDING_FAILED",
                    message="Macro embedding generation failed. Check server logs.",
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
            await session.execute(
                delete(TranscriptMacroSegment).where(TranscriptMacroSegment.video_id == video_id)
            )
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
            for g, emb in zip(macro_groups, macro_embeddings, strict=True):
                session.add(
                    TranscriptMacroSegment(
                        video_id=video_id,
                        macro_index=g.macro_index,
                        micro_chunk_start=g.micro_chunk_start,
                        micro_chunk_end=g.micro_chunk_end,
                        start_ts=g.start_ts,
                        end_ts=g.end_ts,
                        text=g.text,
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
