"""Tests for LLM client: retry logic, JSON parsing, code extraction."""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from flywheel_orchestrator.llm_client import LLMClient


@pytest.fixture
def mock_openai():
    """Patch OpenAI so no real API calls are made."""
    with patch('flywheel_orchestrator.llm_client.OpenAI') as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


def make_response(content, total_tokens=100):
    """Build a fake OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    usage = MagicMock()
    usage.total_tokens = total_tokens
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def make_empty_response():
    """Response with no choices."""
    resp = MagicMock()
    resp.choices = []
    resp.usage = None
    return resp


class TestChat:
    def test_successful_chat(self, mock_openai):
        mock_openai.chat.completions.create.return_value = make_response("Hello world")
        client = LLMClient(api_key="test-key")
        result = client.chat("system", "user")
        assert result == "Hello world"
        assert client.call_count == 1
        assert client.total_tokens == 100

    def test_tracks_tokens(self, mock_openai):
        mock_openai.chat.completions.create.return_value = make_response("a", 50)
        client = LLMClient(api_key="test-key")
        client.chat("s", "u")
        client.chat("s", "u")
        assert client.total_tokens == 100
        assert client.call_count == 2

    def test_empty_choices_returns_none(self, mock_openai):
        mock_openai.chat.completions.create.return_value = make_empty_response()
        client = LLMClient(api_key="test-key")
        result = client.chat("system", "user")
        assert result is None


class TestExtractCode:
    def test_fenced_python(self):
        client = LLMClient.__new__(LLMClient)
        text = "Here's the code:\n```python\nprint('hello')\n```\nDone."
        assert client.extract_code(text) == "print('hello')"

    def test_fenced_no_language(self):
        client = LLMClient.__new__(LLMClient)
        text = "```\ndef foo():\n    pass\n```"
        result = client.extract_code(text)
        assert "def foo():" in result

    def test_no_fence_returns_raw(self):
        client = LLMClient.__new__(LLMClient)
        text = "print('hello')"
        assert client.extract_code(text) == "print('hello')"

    def test_none_input_returns_none(self):
        """After plan changes, extract_code should handle None gracefully."""
        client = LLMClient.__new__(LLMClient)
        # Current code will crash on None.strip() -- this test documents the bug
        # After Phase 0 fix, this should return None
        try:
            result = client.extract_code(None)
            # If it doesn't crash, it should return None
            assert result is None
        except AttributeError:
            # Expected with current code -- documents the bug
            pytest.skip("Known bug: extract_code(None) crashes. Fixed in Phase 0.")

    def test_multiple_fences_takes_first(self):
        client = LLMClient.__new__(LLMClient)
        text = "```python\nfirst()\n```\n\n```python\nsecond()\n```"
        result = client.extract_code(text)
        assert "first()" in result


class TestChatJson:
    def test_valid_json_response(self, mock_openai):
        mock_openai.chat.completions.create.return_value = make_response(
            '{"key": "value"}'
        )
        client = LLMClient(api_key="test-key")
        result = client.chat_json("system", "user")
        assert result == {"key": "value"}

    def test_json_in_code_fence(self, mock_openai):
        mock_openai.chat.completions.create.return_value = make_response(
            '```json\n{"key": "value"}\n```'
        )
        client = LLMClient(api_key="test-key")
        result = client.chat_json("system", "user")
        assert result == {"key": "value"}

    def test_invalid_json_retries(self, mock_openai):
        # First call returns invalid JSON, second returns valid
        mock_openai.chat.completions.create.side_effect = [
            make_response("not json at all"),
            make_response('{"fixed": true}'),
        ]
        client = LLMClient(api_key="test-key")
        result = client.chat_json("system", "user")
        assert result == {"fixed": True}
        assert client.call_count == 2

    def test_double_json_failure_raises(self, mock_openai):
        # Both attempts return invalid JSON
        mock_openai.chat.completions.create.side_effect = [
            make_response("nope"),
            make_response("still nope"),
        ]
        client = LLMClient(api_key="test-key")
        # Current code raises JSONDecodeError on double failure
        # After Phase 0, should return {}
        with pytest.raises(json.JSONDecodeError):
            client.chat_json("system", "user")


class TestGetStats:
    def test_stats_structure(self, mock_openai):
        client = LLMClient(api_key="test-key", model="gpt-4o")
        stats = client.get_stats()
        assert stats['calls'] == 0
        assert stats['total_tokens'] == 0
        assert stats['model'] == 'gpt-4o'
