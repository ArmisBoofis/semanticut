"""Unit tests for adaptive macro shortlist (no DB)."""

import json
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import settings
from app.services.search_service import (
    _adaptive_macro_shortlist,
    _anchor_overlap_score,
    _build_structured_context_payload,
    _enforce_near_peak_segment,
    _force_scene_intent_for_vague_query,
    _offsets_for_macro_highlight,
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


def test_pick_micro_from_anchor_quote_intent_prefers_verbatim() -> None:
    macro = SimpleNamespace(id=uuid4())
    m0 = SimpleNamespace(id=uuid4(), text="la phrase exacte est ici")
    m1 = SimpleNamespace(id=uuid4(), text="la phrase partielle")
    seg, _owner, _micros = _pick_micro_from_anchor(
        macro_context=[(macro, [m1, m0])],
        anchor_text="la phrase exacte",
        quote_intent=True,
    )
    assert seg is m0


def test_offsets_for_macro_highlight_degrades_without_exception() -> None:
    macro = SimpleNamespace(text="prefix micro-texte suffix")
    selected = SimpleNamespace(id=uuid4(), text="micro-texte")
    other = SimpleNamespace(id=uuid4(), text="autre")
    start, end = _offsets_for_macro_highlight(macro, [other, selected], selected)
    assert macro.text[start:end] == selected.text


def test_curated_quote_set_within_tolerance() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "quote_precision_set.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    for case in cases:
        macro = SimpleNamespace(id=uuid4())
        micros = [
            SimpleNamespace(
                id=uuid4(),
                text=item["text"],
                start_ts=float(item["start_ts"]),
            )
            for item in case["micro_segments"]
        ]
        seg, _owner, _micros = _pick_micro_from_anchor(
            macro_context=[(macro, micros)],
            anchor_text=case["query"],
            quote_intent=True,
        )
        assert seg is not None
        delta = abs(float(seg.start_ts) - float(case["expected_start_ts"]))
        assert delta <= float(case["tolerance_seconds"])


def test_anchor_overlap_score_prefers_containment() -> None:
    contain = _anchor_overlap_score("bonjour le monde", "xx bonjour le monde yy")
    partial = _anchor_overlap_score("bonjour le monde", "bonjour rapide")
    assert contain > partial


def test_force_scene_intent_for_vague_query_defaults_to_scene() -> None:
    assert _force_scene_intent_for_vague_query("montre moi le passage sur la migration", "quote") == "scene"
    assert _force_scene_intent_for_vague_query("montre moi le passage sur la migration", "scene") == "scene"


def test_force_scene_intent_for_verbatim_query_keeps_quote() -> None:
    query = 'il dit "bonjour et bienvenue" mot pour mot'
    assert _force_scene_intent_for_vague_query(query, "quote") == "quote"


def test_enforce_near_peak_segment_falls_back_when_too_far() -> None:
    peak = SimpleNamespace(id=uuid4(), start_ts=100.0)
    near = SimpleNamespace(id=uuid4(), start_ts=125.0)
    far = SimpleNamespace(id=uuid4(), start_ts=165.0)
    selected = _enforce_near_peak_segment(selected=far, peak=peak, candidates=[far, near, peak], max_delta_seconds=30.0)
    assert selected is near


def test_enforce_near_peak_segment_keeps_selected_when_close() -> None:
    peak = SimpleNamespace(id=uuid4(), start_ts=100.0)
    selected = SimpleNamespace(id=uuid4(), start_ts=120.0)
    out = _enforce_near_peak_segment(selected=selected, peak=peak, candidates=[selected, peak], max_delta_seconds=30.0)
    assert out is selected


def test_curated_vague_scene_set_within_peak_window() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "vague_scene_set.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    for case in cases:
        micros = [
            SimpleNamespace(
                id=uuid4(),
                text=item["text"],
                start_ts=float(item["start_ts"]),
            )
            for item in case["micro_segments"]
        ]
        peak = next(
            m for m in micros if float(case["expected_zone_start_ts"]) <= m.start_ts <= float(case["expected_zone_end_ts"])
        )
        selected = _enforce_near_peak_segment(
            selected=micros[-1],
            peak=peak,
            candidates=micros,
            max_delta_seconds=float(case["tolerance_seconds"]),
        )
        assert selected is not None
        assert abs(float(selected.start_ts) - float(peak.start_ts)) <= float(case["tolerance_seconds"])
