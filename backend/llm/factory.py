"""Factory for constructing the configured LLM provider.

This is the ONLY place in the application (besides ``llm/`` itself) that
knows the mapping from a provider name to a concrete implementation.
Agents and services call ``get_llm_provider()`` and never import a
provider class directly.
"""
from __future__ import annotations

from config.settings import Settings, get_settings
from llm.base import BaseLLM, LLMProviderError
from llm.gemini import GeminiLLM
from llm.groq import GroqLLM
from llm.mistral import MistralLLM
from llm.openai import OpenAILLM

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "gemini": GeminiLLM,
    "groq": GroqLLM,
    "mistral": MistralLLM,
    "openai": OpenAILLM,
}


def get_llm_provider(settings: Settings | None = None) -> BaseLLM:
    """Instantiate the LLM provider configured via ``LLM_PROVIDER``."""
    settings = settings or get_settings()
    provider_key = settings.llm_provider.lower()

    provider_cls = _PROVIDERS.get(provider_key)
    if provider_cls is None:
        raise LLMProviderError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
            f"Supported providers: {', '.join(sorted(_PROVIDERS))}"
        )

    api_key = _resolve_api_key(provider_key, settings)
    return provider_cls(api_key=api_key, model=settings.llm_model)


def _resolve_api_key(provider_key: str, settings: Settings) -> str:
    api_keys = {
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
        "mistral": settings.mistral_api_key,
        "openai": settings.openai_api_key,
    }
    api_key = api_keys.get(provider_key)
    if not api_key:
        raise LLMProviderError(
            f"No API key configured for provider '{provider_key}'. "
            f"Set the corresponding *_API_KEY environment variable."
        )
    return api_key
