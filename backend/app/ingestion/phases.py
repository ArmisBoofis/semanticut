"""Ingestion phase names and progress mapping.

Progress rule: each phase start maps to a monotonic percent (0, 20, 40, 60, 80);
`completed` sets 100; `failed` leaves the last progress/phase as set when the error occurred.
"""

from __future__ import annotations

PHASE_EXTRACTING_AUDIO = "extracting_audio"
PHASE_TRANSCRIBING = "transcribing"
PHASE_CHUNKING = "chunking"
PHASE_EMBEDDING = "embedding"
PHASE_INDEXING = "indexing"

_ORDER = (
    PHASE_EXTRACTING_AUDIO,
    PHASE_TRANSCRIBING,
    PHASE_CHUNKING,
    PHASE_EMBEDDING,
    PHASE_INDEXING,
)


def progress_at_phase_start(phase: str) -> int:
    """Return overall progress percent (0–100) at the start of the given phase."""
    try:
        idx = _ORDER.index(phase)
    except ValueError:
        return 0
    return min(100, idx * 20)
