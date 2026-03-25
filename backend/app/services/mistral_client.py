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
class SearchAnchorResult:
    """LLM phase: intent + sentence anchor from structured macro→micro JSON, or no_match."""

    intent: str  # "quote" | "scene"
    anchor: str | None
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


def _truncate_structured_context_json(structured_context_json: str, max_chars: int = 72_000) -> str:
    if len(structured_context_json) <= max_chars:
        return structured_context_json
    return structured_context_json[:max_chars] + '\n\n{"truncated": true}'


def _structured_search_anchor_prompt(*, user_query: str, structured_context_json: str) -> str:
    """Single prompt for hybrid search: intent (quote vs scene) + one anchor phrase from micro text."""
    body = _truncate_structured_context_json(structured_context_json)
    return (
        "Tu reçois une question utilisateur et un contexte JSON structuré (macro → micro segments de transcription).\n\n"
        "Objectif : inférer un intent (quote vs scene) et retourner UNE phrase d'ancrage présente dans le texte des micros.\n\n"
        "Pertinence (à vérifier en premier) :\n"
        "- Le contexte a été pré-filtré mais peut quand même contenir des passages faiblement liés. "
        "Ne retourne une ancre que si au moins un segment répond **réellement** à l'intention de la question "
        "(le sujet, la demande ou l'information cherchée), pas seulement parce qu'un mot ou une expression "
        "apparaît aussi dans la transcription.\n"
        "- Un chevauchement lexical court ou des mots très courants ne suffisent pas : rejette les coïncidences.\n"
        "- Tolérance utile : si la question porte sur un thème **connexe** au contenu (même idée sous d'autres mots, "
        "aspect voisin du même sujet) et qu'un passage en parle clairement, tu peux répondre avec status \"ok\".\n"
        "- Si la question est hors sujet, sans lien réel avec ce que la vidéo traite, ou si aucun passage ne permet "
        "de répondre de façon honnête à l'utilisateur, retourne **obligatoirement** status \"no_match\" et anchor vide. "
        "En cas de doute sérieux entre « vraiment pertinent » et « on peut forcer un lien », choisis **no_match**.\n\n"
        "Intent « quote » — choisis « quote » si AU MOINS UNE des conditions suivantes est vraie :\n"
        "- L'utilisateur demande explicitement une citation, formulation exacte, mot pour mot, verbatim, à la lettre, "
        "phrase exacte, texte exact, recopier, reproduire, citer, etc.\n"
        "- La question recoupe fortement un passage du contexte (mêmes mots ou presque, même ordre, ou longue sous-chaîne "
        "commune) : c'est une recherche de passage précis → « quote », même sans mot-clé « citation ». "
        "L'ancre doit être la phrase ou le début du micro qui contient ce recoupement le plus serré ; "
        "ne choisis pas un « début de scène » plus large ni un résumé thématique.\n\n"
        "Intent « scene » — question thématique ou vague sans recoupement lexical fort avec une phrase précise du contexte ; "
        "si doute entre quote et scene, préfère « quote » lorsque les mots de la question alignent clairement un passage.\n\n"
        "Règles pour « anchor » :\n"
        "- Texte court, copié tel quel depuis le contexte (champ texte d'un micro).\n"
        "- Si intent = quote : la phrase ou le segment le plus proche lexicalement du passage recherché (saut vers cette phrase).\n"
        "- Si intent = scene : identifie d'abord le micro ou la phrase le PLUS pertinent pour la question ; "
        "l'ancre commence au plus tard 1 à 2 phrases avant ce passage (pas plus tôt). "
        "Ne remonte pas au début large de la scène si cela éloigne du moment pertinent.\n\n"
        "Rappel : si la barre de pertinence ci-dessus n'est pas atteinte, status \"no_match\" et anchor vide "
        "(même si un micro contient des mots de la question).\n\n"
        'Réponds STRICTEMENT avec un unique objet JSON, sans markdown :\n'
        '{"intent":"quote"|"scene","anchor":"<texte ou vide>","status":"ok"|"no_match"}\n'
        "Aucune autre clé, aucun texte hors JSON.\n\n"
        f"Question:\n{user_query.strip()}\n\n"
        f"Contexte JSON:\n{body}\n"
    )


def select_search_anchor_from_structured_context(
    *,
    user_query: str,
    structured_context_json: str,
) -> SearchAnchorResult:
    """Mistral chat: intent + anchor from structured macro→micro JSON (strict JSON response)."""
    prompt = _structured_search_anchor_prompt(
        user_query=user_query,
        structured_context_json=structured_context_json,
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
    anchor = str(anchor_raw).strip() if anchor_raw is not None else ""
    if status != "ok" or not anchor:
        return SearchAnchorResult(intent=intent, anchor=None, status="no_match")
    if len(anchor) > 300:
        return SearchAnchorResult(intent=intent, anchor=None, status="no_match")
    return SearchAnchorResult(intent=intent, anchor=anchor, status="ok")


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
