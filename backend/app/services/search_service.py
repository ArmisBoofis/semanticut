"""Semantic search: hybrid macro retrieval + structured context + direct LLM timestamp."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import AppError
from app.models.transcript_macro_segment import TranscriptMacroSegment
from app.models.transcript_segment import TranscriptSegment
from app.models.video import Video
from app.schemas.video import VideoSearchMatchResponse
from app.services import mistral_client
from app.services.macro_grouping import offset_for_micro_in_macro

_MACRO_RANK_FETCH_LIMIT = 120


def _confidence_from_distance(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance / 2.0))


def _match_quality_tier(confidence: float) -> str:
    if confidence >= 0.72:
        return "strong"
    if confidence >= 0.48:
        return "partial"
    return "weak"


def _adaptive_macro_shortlist(
    macro_rows: list[tuple[TranscriptMacroSegment, float]],
) -> list[TranscriptMacroSegment]:
    """Keep up to K_max macros whose distance is within max and within gap of the best."""
    if not macro_rows:
        return []
    best_d = float(macro_rows[0][1])
    max_d = settings.search_macro_max_cosine_distance
    gap = settings.search_macro_gap_from_best
    k_max = settings.search_macro_top_k_max

    if best_d > max_d:
        return []

    out: list[TranscriptMacroSegment] = []
    for m, d in macro_rows:
        if len(out) >= k_max:
            break
        if d > max_d:
            continue
        if d - best_d > gap:
            continue
        out.append(m)
    return out


async def search_best_segment(
    session: AsyncSession,
    video_id: UUID,
    query: str,
) -> VideoSearchMatchResponse:
    """Hybrid macro retrieval + timestamp extraction; legacy micro-only without macros."""
    q = query.strip()
    if not q:
        raise AppError("VALIDATION_ERROR", "query cannot be empty", 400)

    v_stmt = select(Video.id).where(Video.id == video_id)
    v_res = await session.execute(v_stmt)
    if v_res.scalar_one_or_none() is None:
        raise AppError("NOT_FOUND", "vidéo introuvable", 404)

    try:
        query_embedding = mistral_client.embed_texts_batch([q])[0]
    except Exception as exc:
        mistral_client.log_mistral_error(exc, context="search_query")
        raise AppError(
            "UPSTREAM_ERROR",
            "échec du calcul d’embedding pour la requête",
            502,
        ) from exc

    macro_count = await session.scalar(
        select(func.count())
        .select_from(TranscriptMacroSegment)
        .where(TranscriptMacroSegment.video_id == video_id)
    )
    if not macro_count:
        return await _search_micro_only(session, video_id, query_embedding)

    return await _search_two_pass(session, video_id, query_embedding, q)


async def _search_micro_only(
    session: AsyncSession,
    video_id: UUID,
    query_embedding: list[float],
) -> VideoSearchMatchResponse:
    """Legacy path: no macro rows (pre-migration / empty). Macro context = micro text."""
    max_d = settings.search_macro_max_cosine_distance
    distance_expr = TranscriptSegment.embedding.cosine_distance(query_embedding)
    stmt = (
        select(TranscriptSegment, distance_expr.label("dist"))
        .where(TranscriptSegment.video_id == video_id)
        .order_by(distance_expr)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        raise AppError(
            "NO_MATCH",
            "aucun segment de transcription pour cette vidéo",
            404,
        )

    seg, dist = row[0], row[1]
    distance = float(dist)
    if distance > max_d:
        raise AppError(
            "NO_MATCH",
            "aucun passage pertinent trouvé pour cette requête",
            404,
        )

    confidence = _confidence_from_distance(distance)
    text = seg.text
    return VideoSearchMatchResponse(
        start_ts=seg.start_ts,
        end_ts=seg.end_ts,
        text=text,
        confidence=confidence,
        macro_context_text=text,
        match_start_offset=0,
        match_end_offset=len(text),
        match_quality=_match_quality_tier(confidence),
    )


async def _search_two_pass(
    session: AsyncSession,
    video_id: UUID,
    query_embedding: list[float],
    user_query: str,
) -> VideoSearchMatchResponse:
    """Dense + BM25 retrieval, RRF fusion, then direct timestamp extraction."""
    fused_macros = await _hybrid_macro_retrieval(
        session=session,
        video_id=video_id,
        query_embedding=query_embedding,
        user_query=user_query,
    )
    if not fused_macros:
        raise AppError("NO_MATCH", "aucun passage pertinent trouvé pour cette requête", 404)

    context_macros = fused_macros[: settings.search_macro_top_k]
    macro_ctx = await _load_context_macros_with_micros(session, video_id, context_macros)
    if not macro_ctx:
        raise AppError("NO_MATCH", "aucun passage pertinent trouvé pour cette requête", 404)
    payload = _build_structured_context_payload(video_id=video_id, macro_context=macro_ctx)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    try:
        ts_res = mistral_client.select_timestamp_from_structured_context(
            user_query=user_query,
            structured_context_json=payload_json,
        )
    except Exception as exc:
        mistral_client.log_mistral_error(exc, context="search_timestamp_llm")
        raise AppError(
            "UPSTREAM_ERROR",
            "échec de l’analyse sémantique (timestamp)",
            502,
        ) from exc

    seg, owning_macro, micros_in_macro = _pick_micro_from_timestamp(
        macro_context=macro_ctx,
        llm_start=ts_res.start if ts_res.status == "ok" else None,
    )
    if seg is None or owning_macro is None or micros_in_macro is None:
        raise AppError("NO_MATCH", "aucun passage pertinent trouvé pour cette requête", 404)
    confidence = await _micro_confidence_against_query(session, seg.id, query_embedding)
    start_off, end_off = _offsets_for_macro_highlight(owning_macro, micros_in_macro, seg)
    macro_text = owning_macro.text

    return VideoSearchMatchResponse(
        start_ts=seg.start_ts,
        end_ts=seg.end_ts,
        text=seg.text,
        confidence=confidence,
        macro_context_text=macro_text,
        match_start_offset=start_off,
        match_end_offset=end_off,
        match_quality=_match_quality_tier(confidence),
    )


async def _hybrid_macro_retrieval(
    *,
    session: AsyncSession,
    video_id: UUID,
    query_embedding: list[float],
    user_query: str,
) -> list[TranscriptMacroSegment]:
    macro_dist = TranscriptMacroSegment.embedding.cosine_distance(query_embedding)
    dense_rows = (
        await session.execute(
            select(TranscriptMacroSegment, macro_dist.label("dist"))
            .where(TranscriptMacroSegment.video_id == video_id)
            .order_by(macro_dist)
            .limit(_MACRO_RANK_FETCH_LIMIT)
        )
    ).all()
    retained_dense = _adaptive_macro_shortlist([(m, float(d)) for m, d in dense_rows])
    dense_rank = {m.id: i + 1 for i, m in enumerate(retained_dense)}
    dense_map = {m.id: m for m in retained_dense}
    if not dense_map:
        return []

    tsquery = func.plainto_tsquery("simple", user_query)
    rank_expr = cast(
        func.ts_rank_cd(func.to_tsvector("simple", TranscriptMacroSegment.text), tsquery),
        Float,
    )
    bm25_rows = (
        await session.execute(
            select(TranscriptMacroSegment, rank_expr.label("rank"))
            .where(TranscriptMacroSegment.video_id == video_id, rank_expr > 0.0)
            .order_by(rank_expr.desc())
            .limit(_MACRO_RANK_FETCH_LIMIT)
        )
    ).all()
    bm25_rank = {m.id: i + 1 for i, (m, _r) in enumerate(bm25_rows)}
    for m, _r in bm25_rows:
        dense_map.setdefault(m.id, m)

    rrf_k = settings.search_rrf_k
    scored = []
    for mid, macro in dense_map.items():
        score = 0.0
        if mid in dense_rank:
            score += 1.0 / (rrf_k + dense_rank[mid])
        if mid in bm25_rank:
            score += 1.0 / (rrf_k + bm25_rank[mid])
        scored.append((macro, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [m for m, _ in scored if _ > 0.0]


async def _load_context_macros_with_micros(
    session: AsyncSession,
    video_id: UUID,
    macros: list[TranscriptMacroSegment],
) -> list[tuple[TranscriptMacroSegment, list[TranscriptSegment]]]:
    if not macros:
        return []
    out: list[tuple[TranscriptMacroSegment, list[TranscriptSegment]]] = []
    for macro in macros:
        micros = (
            await session.execute(
                select(TranscriptSegment)
                .where(
                    TranscriptSegment.video_id == video_id,
                    TranscriptSegment.chunk_index >= macro.micro_chunk_start,
                    TranscriptSegment.chunk_index <= macro.micro_chunk_end,
                )
                .order_by(TranscriptSegment.chunk_index.asc())
            )
        ).scalars().all()
        if micros:
            out.append((macro, micros))
    return out


def _build_structured_context_payload(
    *,
    video_id: UUID,
    macro_context: list[tuple[TranscriptMacroSegment, list[TranscriptSegment]]],
) -> dict:
    return {
        "video_id": str(video_id),
        "macros": [
            {
                "macro_id": str(m.id),
                "macro_index": m.macro_index,
                "start": m.start_ts,
                "end": m.end_ts,
                "text": m.text,
                "micros": [
                    {
                        "id": str(seg.id),
                        "chunk_index": seg.chunk_index,
                        "start": seg.start_ts,
                        "end": seg.end_ts,
                        "text": seg.text,
                    }
                    for seg in micros
                ],
            }
            for m, micros in macro_context
        ],
    }


def _pick_micro_from_timestamp(
    *,
    macro_context: list[tuple[TranscriptMacroSegment, list[TranscriptSegment]]],
    llm_start: float | None,
) -> tuple[TranscriptSegment | None, TranscriptMacroSegment | None, list[TranscriptSegment] | None]:
    if not macro_context:
        return None, None, None
    if llm_start is None:
        top_macro, top_micros = macro_context[0]
        return top_micros[0], top_macro, top_micros
    best_seg: TranscriptSegment | None = None
    best_macro: TranscriptMacroSegment | None = None
    best_micros: list[TranscriptSegment] | None = None
    best_d = float("inf")
    for macro, micros in macro_context:
        for seg in micros:
            if seg.start_ts <= llm_start <= seg.end_ts:
                return seg, macro, micros
            d = abs(seg.start_ts - llm_start)
            if d < best_d:
                best_d = d
                best_seg = seg
                best_macro = macro
                best_micros = micros
    return best_seg, best_macro, best_micros


async def _micro_confidence_against_query(
    session: AsyncSession,
    segment_id: UUID,
    query_embedding: list[float],
) -> float:
    dist_expr = TranscriptSegment.embedding.cosine_distance(query_embedding)
    row = (
        await session.execute(
            select(dist_expr.label("dist")).where(TranscriptSegment.id == segment_id).limit(1)
        )
    ).first()
    if row is None:
        return 0.0
    return _confidence_from_distance(float(row[0]))


def _offsets_for_macro_highlight(
    macro: TranscriptMacroSegment,
    micros: list[TranscriptSegment],
    selected: TranscriptSegment,
) -> tuple[int, int]:
    texts = [s.text for s in micros]
    local_idx = next((i for i, s in enumerate(micros) if s.id == selected.id), None)
    if local_idx is None:
        raise AppError("INTERNAL_ERROR", "incohérence macro/micro", 500)
    start_off, end_off = offset_for_micro_in_macro(texts, local_idx)
    if macro.text[start_off:end_off] != selected.text:
        raise AppError("INTERNAL_ERROR", "incohérence des décalages macro/micro", 500)
    return start_off, end_off
