"""Deterministic grouping of micro transcript segments into macro units (coarse retrieval)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    """Approximate word count (runs of non-whitespace; aligns with French/English prose)."""
    return len(_WORD_RE.findall(text.strip())) if text else 0


@dataclass(frozen=True, slots=True)
class MicroSpan:
    """One micro segment row (ordered by chunk_index)."""

    chunk_index: int
    start_ts: float
    end_ts: float
    text: str


@dataclass(frozen=True, slots=True)
class MacroGroup:
    """Macro unit built from consecutive micro spans; text is \" \".join(micro texts)."""

    macro_index: int
    micro_chunk_start: int
    micro_chunk_end: int
    start_ts: float
    end_ts: float
    text: str


def group_micros_into_macros(micros: list[MicroSpan], *, target_chars: int) -> list[MacroGroup]:
    """
    Greedy grouping: accumulate consecutive micros until adding the next would exceed
    ``target_chars`` on the joined string (space-separated), then start a new macro.
    """
    if target_chars < 1:
        raise ValueError("target_chars must be >= 1")
    if not micros:
        return []

    groups: list[MacroGroup] = []
    current: list[MicroSpan] = []
    macro_idx = 0

    def emit() -> None:
        nonlocal macro_idx
        if not current:
            return
        macro_text = " ".join(m.text for m in current)
        groups.append(
            MacroGroup(
                macro_index=macro_idx,
                micro_chunk_start=current[0].chunk_index,
                micro_chunk_end=current[-1].chunk_index,
                start_ts=current[0].start_ts,
                end_ts=current[-1].end_ts,
                text=macro_text,
            )
        )
        current.clear()
        macro_idx += 1

    for seg in micros:
        if not current:
            current.append(seg)
            continue
        cur_text = " ".join(m.text for m in current)
        if len(cur_text) + 1 + len(seg.text) > target_chars:
            emit()
            current.append(seg)
        else:
            current.append(seg)

    emit()
    return groups


def group_micros_into_macros_by_words(micros: list[MicroSpan], *, target_words: int) -> list[MacroGroup]:
    """
    Greedy grouping by approximate word count on space-joined micro text (same join as char mode).
    Primary macro sizing for search: target is word-like units per PRD.
    """
    if target_words < 1:
        raise ValueError("target_words must be >= 1")
    if not micros:
        return []

    groups: list[MacroGroup] = []
    current: list[MicroSpan] = []
    macro_idx = 0

    def emit() -> None:
        nonlocal macro_idx
        if not current:
            return
        macro_text = " ".join(m.text for m in current)
        groups.append(
            MacroGroup(
                macro_index=macro_idx,
                micro_chunk_start=current[0].chunk_index,
                micro_chunk_end=current[-1].chunk_index,
                start_ts=current[0].start_ts,
                end_ts=current[-1].end_ts,
                text=macro_text,
            )
        )
        current.clear()
        macro_idx += 1

    for seg in micros:
        if not current:
            current.append(seg)
            continue
        trial = " ".join(m.text for m in current) + " " + seg.text
        if count_words(trial) > target_words:
            emit()
            current.append(seg)
        else:
            current.append(seg)

    emit()
    return groups


def micro_offsets_in_macro_text(micro_texts: list[str]) -> list[tuple[int, int]]:
    """
    For macro text built as \" \".join(micro_texts), return (start, end) str offsets
    for each micro piece (end exclusive), using Python string indices on the joined string.
    """
    if not micro_texts:
        return []
    out: list[tuple[int, int]] = []
    pos = 0
    for i, piece in enumerate(micro_texts):
        if i > 0:
            pos += 1  # space
        start = pos
        end = start + len(piece)
        out.append((start, end))
        pos = end
    return out


def offset_for_micro_in_macro(micro_texts: list[str], micro_local_index: int) -> tuple[int, int]:
    """Return (start, end) for the micro at index within the same macro group."""
    offs = micro_offsets_in_macro_text(micro_texts)
    if micro_local_index < 0 or micro_local_index >= len(offs):
        raise IndexError("micro_local_index out of range for macro")
    return offs[micro_local_index]
