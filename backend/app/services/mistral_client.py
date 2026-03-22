"""Mistral-only transcription and embeddings (architecture: Mistral stack only).

Transcription follows the official offline flow:
https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
(`from mistralai.client import Mistral`, `client.audio.transcriptions.complete`, model `voxtral-mini-latest`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptionSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    segments: list[TranscriptionSegment]


def _build_mistral():
    """SDK client as in Mistral docs (`mistralai.client.Mistral` exposes `audio.transcriptions`)."""
    from mistralai.client import Mistral

    key = settings.mistral_api_key
    if not key:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    return Mistral(api_key=key)


def _parse_segments(raw: Any) -> list[TranscriptionSegment]:
    if raw is None:
        return []
    out: list[TranscriptionSegment] = []
    for item in raw:
        if isinstance(item, dict):
            start = float(item.get("start", 0) or 0)
            end = float(item.get("end", start) or start)
            text = str(item.get("text", "") or "").strip()
        else:
            start = float(getattr(item, "start", None) or getattr(item, "start_time", None) or 0.0)
            end = float(getattr(item, "end", None) or getattr(item, "end_time", None) or start)
            text = str(getattr(item, "text", "") or "").strip()
        if text:
            out.append(
                TranscriptionSegment(
                    start=start,
                    end=max(end, start + 0.05),
                    text=text,
                )
            )
    return out


def transcribe_audio_file(audio_path: Path) -> TranscriptionResult:
    """Voxtral Mini Transcribe via `POST /v1/audio/transcriptions` (official Python SDK)."""
    client = _build_mistral()
    model = settings.mistral_transcription_model

    def _complete(*, with_segment_timestamps: bool) -> Any:
        # Docs: pass an open file and `file_name` (multipart upload).
        with audio_path.open("rb") as f:
            kwargs: dict[str, Any] = {
                "model": model,
                "file": {
                    "content": f,
                    "file_name": audio_path.name,
                },
                "diarize": False,
            }
            if with_segment_timestamps:
                # Docs: `segment` | `word`; not compatible with `language` on the same request.
                kwargs["timestamp_granularities"] = ["segment"]
            return client.audio.transcriptions.complete(**kwargs)

    try:
        transcription_response = _complete(with_segment_timestamps=True)
    except Exception as exc:
        logger.warning(
            "Transcription with timestamp_granularities failed, retrying basic call: %s",
            exc,
        )
        transcription_response = _complete(with_segment_timestamps=False)

    text = str(getattr(transcription_response, "text", "") or "").strip()
    segments = _parse_segments(getattr(transcription_response, "segments", None))
    if not text and segments:
        text = " ".join(s.text for s in segments)
    return TranscriptionResult(text=text, segments=segments)


def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text (Mistral `mistral-embed`)."""
    if not texts:
        return []
    client = _build_mistral()
    model = settings.mistral_embedding_model
    res = client.embeddings.create(model=model, inputs=texts)
    data = getattr(res, "data", None) or []
    out: list[list[float]] = []
    for i, row in enumerate(data):
        emb = getattr(row, "embedding", None)
        if emb is None:
            raise RuntimeError(f"missing embedding at index {i}")
        out.append(list(emb))
    if len(out) != len(texts):
        raise RuntimeError("embedding batch size mismatch")
    return out


def log_mistral_error(exc: BaseException, *, context: str) -> None:
    """Log full exception server-side; API returns a safe summary only."""
    logger.exception("Mistral error (%s): %s", context, exc)
