from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from utils.gemini_key_manager import GeminiKeyManager


class RotatingGemini(BaseChatModel):
    """Chat model that selects a different Gemini API key per request. 
       Note: it is used only for project management otherwise I have set up LLMRegistry for all other LLM providers like groq, mistral, openai, and ollama.
       To prevent exhaution of the API key quota, I have implemented a class that rotates through a list of Gemini API keys for each request"""

    model: str
    key_manager: GeminiKeyManager

    @property
    def _llm_type(self) -> str:
        return "rotating-gemini"

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ):
        llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=self.key_manager.get_next_key(),
        )

        return await llm._agenerate(
            messages,
            stop=stop,
            **kwargs,
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ):
        llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=self.key_manager.get_next_key(),
        )

        return llm._generate(
            messages,
            stop=stop,
            **kwargs,
        )