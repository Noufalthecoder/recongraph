"""
Tests for LLM provider abstraction and error handling.
"""

import pytest

from backend.app.investigation.providers import (
    DeterministicMockProvider,
    OpenAICompatibleProvider,
)


def test_mock_provider_fallback_when_context_is_none():
    """Verify mock provider returns safe fallback when context is None."""
    provider = DeterministicMockProvider()
    resp = provider.generate("sys", "user", context=None)
    assert "No evidence context was provided" in resp


def test_openai_compatible_provider_missing_api_key_error():
    """Verify OpenAI-compatible provider raises clear ValueError if API key is not configured."""
    provider = OpenAICompatibleProvider(api_key=None)
    # Ensure environment is clean
    provider.api_key = None

    with pytest.raises(ValueError) as exc:
        provider.generate("sys", "user")

    assert "RECONGRAPH_LLM_API_KEY" in str(exc.value)
