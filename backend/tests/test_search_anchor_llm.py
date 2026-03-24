"""Tests for Mistral anchor selection (mocked HTTP client)."""

import pytest

from app.services import mistral_client
from app.services.mistral_client import _parse_json_object_from_chat_content


def test_parse_json_strips_markdown_fence() -> None:
    raw = '```json\n{"intent":"scene","anchor":"x","status":"ok"}\n```'
    assert _parse_json_object_from_chat_content(raw)["anchor"] == "x"


def test_select_search_anchor_rejects_non_substring(monkeypatch: pytest.MonkeyPatch) -> None:
    class Msg:
        content = '{"intent":"scene","anchor":"not in text","status":"ok"}'

    class Choice:
        message = Msg()

    class Res:
        choices = [Choice()]

    def fake_build():
        class Chat:
            def complete(self, **_kwargs):
                return Res()

        class C:
            chat = Chat()

        return C()

    monkeypatch.setattr(mistral_client, "_build_mistral", fake_build)
    monkeypatch.setattr(mistral_client.settings, "mistral_api_key", "test-key")

    r = mistral_client.select_search_anchor(
        user_query="q",
        transcript_excerpt="hello world",
    )
    assert r.anchor is None
    assert r.status == "no_match"


def test_select_search_anchor_accepts_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    class Msg:
        content = '{"intent":"quote","anchor":"hello","status":"ok"}'

    class Choice:
        message = Msg()

    class Res:
        choices = [Choice()]

    def fake_build():
        class Chat:
            def complete(self, **_kwargs):
                return Res()

        class C:
            chat = Chat()

        return C()

    monkeypatch.setattr(mistral_client, "_build_mistral", fake_build)
    monkeypatch.setattr(mistral_client.settings, "mistral_api_key", "test-key")

    r = mistral_client.select_search_anchor(
        user_query="citation",
        transcript_excerpt="hello world",
    )
    assert r.anchor == "hello"
    assert r.status == "ok"
    assert r.intent == "quote"


def test_select_sentence_anchor_from_structured_context_plain_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Msg:
        content = "Bonjour et bienvenue dans ce tutoriel."

    class Choice:
        message = Msg()

    class Res:
        choices = [Choice()]

    def fake_build():
        class Chat:
            def complete(self, **_kwargs):
                return Res()

        class C:
            chat = Chat()

        return C()

    monkeypatch.setattr(mistral_client, "_build_mistral", fake_build)
    monkeypatch.setattr(mistral_client.settings, "mistral_api_key", "test-key")
    r = mistral_client.select_sentence_anchor_from_structured_context(
        user_query="q",
        structured_context_json='{"macros":[]}',
    )
    assert r.status == "ok"
    assert r.anchor == "Bonjour et bienvenue dans ce tutoriel."


def test_select_sentence_anchor_from_structured_context_no_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Msg:
        content = "no_match"

    class Choice:
        message = Msg()

    class Res:
        choices = [Choice()]

    def fake_build():
        class Chat:
            def complete(self, **_kwargs):
                return Res()

        class C:
            chat = Chat()

        return C()

    monkeypatch.setattr(mistral_client, "_build_mistral", fake_build)
    monkeypatch.setattr(mistral_client.settings, "mistral_api_key", "test-key")
    r = mistral_client.select_sentence_anchor_from_structured_context(
        user_query="q",
        structured_context_json='{"macros":[]}',
    )
    assert r.status == "no_match"
    assert r.anchor is None
