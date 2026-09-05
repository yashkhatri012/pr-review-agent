"""Centralized LLM configuration and access for PR review agents"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI

from config.settings import Settings

@dataclass(frozen=True)
class LLMConfig:
    """Configuration required to create an LLM"""


    provider: str
    model: str
    

class LLMRegistry:
    """Create LangChain compatible LLM instances"""

    
    def __init__(self, settings: Settings) -> None:
        """Initialize the LLM registry."""
        self._settings = settings

    def get_llm(
        self,
        config: LLMConfig,
    ) -> BaseChatModel:
        """Create and return the configured chat model"""
        provider = config.provider.lower().strip()
        model = config.model.strip()

        if not model:
            raise ValueError(
                f"No model configured for provider '{provider}'."
            )

        match provider:
            case "openai":
                return self._create_openai(model)

            case "groq":
                return self._create_groq(model)

            case "gemini":
                return self._create_gemini(model)

            case "mistral":
                return self._create_mistral(model)

            case _:
                raise ValueError(
                    f"Unsupported LLM provider: '{provider}'."
                )

    def _create_openai(
        self,
        model: str,
    ) -> BaseChatModel:
        """Create an OpenAI chat model"""
        return ChatOpenAI(
            model=model,
            api_key=self._require_api_key(
                self._settings.openai_api_key,
                "OPENAI_API_KEY",
            ),
        )

    def _create_groq(
        self,
        model: str,
    ) -> BaseChatModel:
        """Create a Groq chat model"""
        return ChatOpenAI(
            model=model,
            api_key=self._require_api_key(
                self._settings.groq_api_key,
                "GROQ_API_KEY",
            ),
            base_url="https://api.groq.com/openai/v1",
        )

    def _create_gemini(
        self,
        model: str,
    ) -> BaseChatModel:
        """Create a Gemini chat model"""
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self._require_api_key(
                self._settings.gemini_api_key,
                "GEMINI_API_KEY",
            ),
        )

    def _create_mistral(
        self,
        model: str,
    ) -> BaseChatModel:
        """Create a Mistral chat model"""
        return ChatMistralAI(
            model=model,
            api_key=self._require_api_key(
                self._settings.mistral_api_key,
                "MISTRAL_API_KEY",
            ),
        )

    @staticmethod # Static, no agent state is required
    def _require_api_key(
        api_key: str | None,
        environment_variable: str,
    ) -> str:
        """Return a configured API key or raise an error"""
        if not api_key:
            raise ValueError(
                f"{environment_variable} is not configured."
            )

        return api_key


class LLMService:
    """Provide LLM instances configured for each PR review agent"""

    def __init__(self, settings: Settings) -> None:
        """Initialize the LLM service."""
        self._settings = settings
        self._registry = LLMRegistry(settings)

    def get_llm_for_agent(
        self,
        agent_name: str,
    ) -> BaseChatModel:
        """Return the LLM configured for a named review agent."""
        config = self._get_agent_config(agent_name)

        return self._registry.get_llm(config)

    def _get_agent_config(
        self,
        agent_name: str,
    ) -> LLMConfig:
        """Return the configured provider and model for an agent."""
        configs = {
            "quality": LLMConfig(
                provider=self._settings.quality_llm_provider,
                model=self._settings.quality_llm_model,
            ),
            "security": LLMConfig(
                provider=self._settings.security_llm_provider,
                model=self._settings.security_llm_model,
            ),
            "bug": LLMConfig(
                provider=self._settings.bug_llm_provider,
                model=self._settings.bug_llm_model,
            ),
            "performance": LLMConfig(
                provider=self._settings.performance_llm_provider,
                model=self._settings.performance_llm_model,
            ),
            "architecture": LLMConfig(
                provider=self._settings.architecture_llm_provider,
                model=self._settings.architecture_llm_model,
            ),
            "validator": LLMConfig(
                provider=self._settings.validator_llm_provider,
                model=self._settings.validator_llm_model,
            ),
            "review_writer": LLMConfig(
                provider=self._settings.review_writer_llm_provider,
                model=self._settings.review_writer_llm_model,
            ),
        }

        try:
            return configs[agent_name]
        except KeyError as exc:
            raise ValueError(
                f"Unknown agent: '{agent_name}'."
            ) from exc

