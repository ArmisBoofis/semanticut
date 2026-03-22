"""Cooperative cancellation for ingestion (same-process hook; workers also poll DB)."""

from __future__ import annotations

import threading
from uuid import UUID

_lock = threading.Lock()
_cancelled_video_ids: set[UUID] = set()


def request_cancel_ingestion(video_id: UUID) -> None:
    """Mark a video so a co-located worker can stop between phases."""
    with _lock:
        _cancelled_video_ids.add(video_id)


def is_cancel_requested(video_id: UUID) -> bool:
    with _lock:
        return video_id in _cancelled_video_ids


def clear_cancel_request(video_id: UUID) -> None:
    with _lock:
        _cancelled_video_ids.discard(video_id)
