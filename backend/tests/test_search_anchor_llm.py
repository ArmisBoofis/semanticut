"""Tests for Mistral search anchor selection (mocked HTTP client)."""

import pytest

from app.services import mistral_client
from app.services.mistral_client import _parse_json_object_from_chat_content


def test_parse_json_strips_markdown_fence() -> None:
    raw = '```json\n{"intent":"scene","anchor":"x","status":"ok"}\n```'
    assert _parse_json_object_from_chat_content(raw)["anchor"] == "x"


def test_select_search_anchor_from_structured_context_quote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Msg:
        content = '{"intent":"quote","anchor":"phrase exacte","status":"ok"}'

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
    r = mistral_client.select_search_anchor_from_structured_context(
        user_query="q",
        structured_context_json='{"macros":[]}',
    )
    assert r.status == "ok"
    assert r.intent == "quote"
    assert r.anchor == "phrase exacte"


def test_select_search_anchor_from_structured_context_invalid_json_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Msg:
        content = '{"intent":"weird","anchor":"","status":"ok"}'

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
    r = mistral_client.select_search_anchor_from_structured_context(
        user_query="q",
        structured_context_json='{"macros":[]}',
    )
    assert r.status == "no_match"
    assert r.intent == "scene"
    assert r.anchor is None
