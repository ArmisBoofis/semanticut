"""Mistral-only transcription and embeddings (architecture: Mistral stack only).

Transcription follows the official offline flow:
https://docs.mistral.ai/capabilities/audio_transcription/offline_transcription
(`from mistralai.client import Mistral`, `client.audio.transcriptions.complete`, model `voxtral-mini-latest`).
"""

from __future__ import annotations

import json
import logging
import re
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


@dataclass(frozen=True)
class AnchorSelectionResult:
    """LLM phase: verbatim anchor from transcript excerpt only, or no_match."""

    intent: str  # "quote" | "scene"
    anchor: str | None
    status: str  # "ok" | "no_match"


@dataclass(frozen=True)
class TimestampSelectionResult:
    """LLM phase: strict timestamp extraction from structured context."""

    start: float | None
    status: str  # "ok" | "no_match"


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


def _parse_json_object_from_chat_content(content: str) -> dict[str, Any]:
    t = (content or "").strip()
    if "```" in t:
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
        if fence:
            t = fence.group(1).strip()
    return json.loads(t)


def select_search_anchor(*, user_query: str, transcript_excerpt: str) -> AnchorSelectionResult:
    """
    Mistral chat: infer quote vs scene intent and return a verbatim anchor substring
    from ``transcript_excerpt`` only (or no_match).
    """
    max_chars = 48_000
    body = transcript_excerpt
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[… texte tronqué pour l’analyse …]"

    prompt = (
        "Tu reçois une question utilisateur et des extraits de transcription vidéo.\n"
        "1) Choisis intent: \"quote\" si l’utilisateur vise une formulation exacte ou une citation; "
        "\"scene\" si la question est vague ou thématique (comportement par défaut si doute).\n"
        "2) Choisis une sous-chaîne **verbatim** copiée exactement depuis les extraits ci-dessous "
        "(mêmes caractères, espaces et ponctuation). Pas d’invention.\n"
        "3) Si les extraits ne permettent pas de répondre, status \"no_match\" et anchor vide.\n\n"
        f"Question:\n{user_query.strip()}\n\n"
        f"Extraits (texte source uniquement):\n{body}\n\n"
        "Réponds par un seul objet JSON, sans markdown:\n"
        '{"intent":"quote"|"scene","anchor":"<chaîne verbatim ou vide>","status":"ok"|"no_match"}'
    )

    client = _build_mistral()
    model = settings.mistral_anchor_model
    max_tokens = settings.mistral_anchor_max_tokens
    res = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    raw = getattr(res, "choices", None) or []
    if not raw:
        raise RuntimeError("empty chat response")
    msg = getattr(raw[0], "message", None)
    content = str(getattr(msg, "content", "") or "").strip()
    data = _parse_json_object_from_chat_content(content)
    intent = str(data.get("intent", "scene")).lower()
    if intent not in ("quote", "scene"):
        intent = "scene"
    status = str(data.get("status", "no_match")).lower()
    anchor_raw = data.get("anchor")
    anchor: str | None
    if anchor_raw is None:
        anchor = None
    else:
        anchor = str(anchor_raw).strip() or None

    if status == "no_match" or anchor is None:
        return AnchorSelectionResult(intent=intent, anchor=None, status="no_match")

    if anchor not in transcript_excerpt:
        return AnchorSelectionResult(intent=intent, anchor=None, status="no_match")

    return AnchorSelectionResult(intent=intent, anchor=anchor, status="ok")


def select_timestamp_from_structured_context(
    *,
    user_query: str,
    structured_context_json: str,
) -> TimestampSelectionResult:
    """
    Mistral chat: infer quote vs scene intent from structured macro->micro context
    and return exactly one timestamp (`start`) as float.
    """
    max_chars = 72_000
    body = structured_context_json
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n{\"truncated\": true}"

    prompt = (
        "Tu reçois une question utilisateur et un contexte JSON structuré de macro->micro segments.\n"
        "Objectif: retourner exactement UN timestamp `start` (float secondes) du meilleur micro segment.\n"
        "Règles:\n"
        "- Déduis implicitement quote vs scene: si doute => scene.\n"
        "- Utilise uniquement les micro fournis.\n"
        '- Réponds STRICTEMENT avec un unique objet JSON: {"start": <float>|null, "status":"ok"|"no_match"}\n'
        "- Aucune autre clé, aucun markdown.\n\n"
        f"Question:\n{user_query.strip()}\n\n"
        f"Contexte JSON:\n{body}\n"
    )

    client = _build_mistral()
    model = settings.mistral_anchor_model
    max_tokens = settings.mistral_anchor_max_tokens
    res = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    raw = getattr(res, "choices", None) or []
    if not raw:
        raise RuntimeError("empty chat response")
    msg = getattr(raw[0], "message", None)
    content = str(getattr(msg, "content", "") or "").strip()
    data = _parse_json_object_from_chat_content(content)
    status = str(data.get("status", "no_match")).lower()
    start_raw = data.get("start")
    if status != "ok":
        return TimestampSelectionResult(start=None, status="no_match")

    try:
        start = float(start_raw)
    except (TypeError, ValueError):
        return TimestampSelectionResult(start=None, status="no_match")
    if start < 0:
        return TimestampSelectionResult(start=None, status="no_match")
    return TimestampSelectionResult(start=start, status="ok")


def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text (Mistral `mistral-embed`).

    The API caps how many inputs may be sent in one request; we chunk according to
    ``settings.mistral_embed_batch_size`` and concatenate results in order.
    """
    if not texts:
        return []
    client = _build_mistral()
    model = settings.mistral_embedding_model
    batch_size = settings.mistral_embed_batch_size
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        res = client.embeddings.create(model=model, inputs=chunk)
        data = getattr(res, "data", None) or []
        for i, row in enumerate(data):
            emb = getattr(row, "embedding", None)
            if emb is None:
                raise RuntimeError(f"missing embedding at batch offset {start}, index {i}")
            out.append(list(emb))
        if len(data) != len(chunk):
            raise RuntimeError("embedding batch size mismatch")
    if len(out) != len(texts):
        raise RuntimeError("embedding batch size mismatch")
    return out


def log_mistral_error(exc: BaseException, *, context: str) -> None:
    """Log full exception server-side; API returns a safe summary only."""
    logger.exception("Mistral error (%s): %s", context, exc)
