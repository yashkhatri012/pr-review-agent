"""Provider-agnostic LLM interface.

Every concrete provider (Gemini, Groq, Mistral, OpenAI, ...) implements
``BaseLLM``. Nothing outside the ``llm/`` package should ever import a
provider SDK directly -- see DECISIONS.md, decision 006.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMProviderError(Exception):
    """Raised when a provider call fails or returns an unusable response."""


class BaseLLM(ABC):
    """Common interface all LLM provider adapters must implement."""

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT] | None = None,
    ) -> ResponseModelT | str:
        """Generate a completion.

        If ``response_model`` is provided, the raw text returned by the
        provider is parsed and validated into that Pydantic model. If
        parsing/validation fails, an ``LLMProviderError`` is raised.
        """
        raise NotImplementedError


def parse_structured_response(
    raw_text: str,
    response_model: type[ResponseModelT],
    provider_name: str,
) -> ResponseModelT:
    """Parse raw LLM text into a validated Pydantic model.

    Shared by all providers so JSON-extraction/validation behavior is
    consistent regardless of which provider produced the text.
    """
    cleaned = _strip_code_fences(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Provider %s returned non-JSON output", provider_name)
        raise LLMProviderError(
            f"{provider_name} response could not be parsed as JSON: {exc}"
        ) from exc

    try:
        return response_model.model_validate(data)
    except ValidationError as exc:
        logger.error("Provider %s returned JSON that failed validation", provider_name)
        raise LLMProviderError(
            f"{provider_name} response failed schema validation: {exc}"
        ) from exc


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Drop the opening fence (``` or ```json) and the closing fence.
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped
