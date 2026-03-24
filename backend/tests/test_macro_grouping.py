"""Unit tests for macro grouping and offset helpers (no DB / Mistral)."""

from app.services.macro_grouping import (
    MicroSpan,
    count_words,
    group_micros_into_macros,
    group_micros_into_macros_by_words,
    offset_for_micro_in_macro,
    micro_offsets_in_macro_text,
)


def test_group_respects_target_chars() -> None:
    micros = [
        MicroSpan(0, 0.0, 1.0, "a" * 100),
        MicroSpan(1, 1.0, 2.0, "b" * 100),
        MicroSpan(2, 2.0, 3.0, "c" * 100),
    ]
    groups = group_micros_into_macros(micros, target_chars=150)
    assert len(groups) >= 2
    for g in groups:
        texts = [m.text for m in micros if g.micro_chunk_start <= m.chunk_index <= g.micro_chunk_end]
        assert g.text == " ".join(texts)


def test_offsets_join_consistent() -> None:
    pieces = ["hello", "world", "x"]
    joined = " ".join(pieces)
    offs = micro_offsets_in_macro_text(pieces)
    for i, (lo, hi) in enumerate(offs):
        assert joined[lo:hi] == pieces[i]


def test_offset_for_micro_in_macro() -> None:
    texts = ["aa", "bbb"]
    assert offset_for_micro_in_macro(texts, 0) == (0, 2)
    assert offset_for_micro_in_macro(texts, 1) == (3, 6)
    assert " ".join(texts)[3:6] == texts[1]


def test_count_words() -> None:
    assert count_words("un deux trois") == 3
    assert count_words("  ") == 0


def test_group_respects_target_words() -> None:
    micros = [
        MicroSpan(0, 0.0, 1.0, "one two three"),
        MicroSpan(1, 1.0, 2.0, "four five six"),
        MicroSpan(2, 2.0, 3.0, "seven eight"),
    ]
    groups = group_micros_into_macros_by_words(micros, target_words=4)
    assert len(groups) >= 2
    for g in groups:
        texts = [m.text for m in micros if g.micro_chunk_start <= m.chunk_index <= g.micro_chunk_end]
        assert g.text == " ".join(texts)
        assert count_words(g.text) <= 4 or len(texts) == 1
