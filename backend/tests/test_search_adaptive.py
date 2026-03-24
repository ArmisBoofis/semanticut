"""Unit tests for adaptive macro shortlist (no DB)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import settings
from app.services.search_service import (
    _adaptive_macro_shortlist,
    _anchor_overlap_score,
    _build_structured_context_payload,
    _pick_micro_from_anchor,
)


def test_adaptive_empty_when_best_over_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "search_macro_max_cosine_distance", 0.3)
    rows = [(SimpleNamespace(), 0.4)]
    assert _adaptive_macro_shortlist(rows) == []


def test_adaptive_drops_when_gap_exceeds_best(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "search_macro_gap_from_best", 0.1)
    monkeypatch.setattr(settings, "search_macro_max_cosine_distance", 0.95)
    monkeypatch.setattr(settings, "search_macro_top_k_max", 5)
    rows = [
        (SimpleNamespace(), 0.2),
        (SimpleNamespace(), 0.35),
    ]
    out = _adaptive_macro_shortlist(rows)
    assert len(out) == 1


def test_adaptive_keeps_within_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "search_macro_gap_from_best", 0.2)
    monkeypatch.setattr(settings, "search_macro_max_cosine_distance", 0.95)
    monkeypatch.setattr(settings, "search_macro_top_k_max", 5)
    rows = [
        (SimpleNamespace(), 0.2),
        (SimpleNamespace(), 0.35),
    ]
    out = _adaptive_macro_shortlist(rows)
    assert len(out) == 2


def test_adaptive_respects_k_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "search_macro_gap_from_best", 1.0)
    monkeypatch.setattr(settings, "search_macro_max_cosine_distance", 0.95)
    monkeypatch.setattr(settings, "search_macro_top_k_max", 2)
    rows = [(SimpleNamespace(), 0.1 + i * 0.01) for i in range(5)]
    out = _adaptive_macro_shortlist(rows)
    assert len(out) == 2


def test_build_structured_payload_includes_macro_and_micro_ids() -> None:
    macro = SimpleNamespace(
        id=uuid4(),
        macro_index=3,
        start_ts=10.0,
        end_ts=22.0,
        text="macro text",
    )
    micro = SimpleNamespace(
        id=uuid4(),
        chunk_index=8,
        start_ts=12.0,
        end_ts=14.0,
        text="micro text",
    )
    payload = _build_structured_context_payload(
        video_id=uuid4(),
        macro_context=[(macro, [micro])],
    )
    assert len(payload["macros"]) == 1
    assert payload["macros"][0]["macro_index"] == 3
    assert payload["macros"][0]["micros"][0]["chunk_index"] == 8


def test_pick_micro_from_anchor_fallbacks_to_first_when_none() -> None:
    macro = SimpleNamespace(id=uuid4())
    m0 = SimpleNamespace(id=uuid4(), text="bonjour monde")
    m1 = SimpleNamespace(id=uuid4(), text="autre segment")
    seg, owner, micros = _pick_micro_from_anchor(
        macro_context=[(macro, [m0, m1])],
        anchor_text=None,
    )
    assert seg is m0
    assert owner is macro
    assert micros == [m0, m1]


def test_pick_micro_from_anchor_uses_lexical_overlap() -> None:
    macro = SimpleNamespace(id=uuid4())
    m0 = SimpleNamespace(id=uuid4(), text="nous allons parler de python")
    m1 = SimpleNamespace(id=uuid4(), text="introduction au postgresql")
    seg, owner, micros = _pick_micro_from_anchor(
        macro_context=[(macro, [m0, m1])],
        anchor_text="parler de python",
    )
    assert seg is m0
    assert owner is macro
    assert micros == [m0, m1]


def test_anchor_overlap_score_prefers_containment() -> None:
    contain = _anchor_overlap_score("bonjour le monde", "xx bonjour le monde yy")
    partial = _anchor_overlap_score("bonjour le monde", "bonjour rapide")
    assert contain > partial
