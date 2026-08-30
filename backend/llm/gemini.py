"""Google Gemini provider adapter.

Only this module is allowed to know about Gemini's request/response shape.
"""
from __future__ import annotations

import logging

import httpx

from llm.base import BaseLLM, LLMProviderError, ResponseModelT, parse_structured_response

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLM(BaseLLM):
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 60.0) -> None:
        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT] | None = None,
    ) -> ResponseModelT | str:
        url = f"{_API_BASE}/{self._model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        if response_model is not None:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Gemini request failed: %s", exc)
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        body = response.json()
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Unexpected Gemini response shape: {body}") from exc

        if response_model is None:
            return text
        return parse_structured_response(text, response_model, self.provider_name)
