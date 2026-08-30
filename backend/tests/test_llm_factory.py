import pytest

from config.settings import Settings
from llm.base import LLMProviderError
from llm.factory import get_llm_provider
from llm.gemini import GeminiLLM
from llm.groq import GroqLLM


def test_factory_returns_configured_provider():
    settings = Settings(llm_provider="gemini", llm_model="gemini-1.5-flash", gemini_api_key="fake-key")
    llm = get_llm_provider(settings)
    assert isinstance(llm, GeminiLLM)


def test_factory_switches_provider_via_settings_only():
    settings = Settings(llm_provider="groq", llm_model="llama3-70b", groq_api_key="fake-key")
    llm = get_llm_provider(settings)
    assert isinstance(llm, GroqLLM)


def test_factory_raises_on_unknown_provider():
    settings = Settings(llm_provider="not-a-provider", llm_model="x")
    with pytest.raises(LLMProviderError):
        get_llm_provider(settings)


def test_factory_raises_when_api_key_missing():
    settings = Settings(llm_provider="openai", llm_model="gpt-4o", openai_api_key=None)
    with pytest.raises(LLMProviderError):
        get_llm_provider(settings)
