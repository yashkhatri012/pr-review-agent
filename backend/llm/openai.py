"""OpenAI provider adapter."""
from __future__ import annotations

import logging

import httpx

from llm.base import BaseLLM, LLMProviderError, ResponseModelT, parse_structured_response

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAILLM(BaseLLM):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float = 60.0) -> None:
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT] | None = None,
    ) -> ResponseModelT | str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if response_model is not None:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(_API_URL, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("OpenAI request failed: %s", exc)
                raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        body = response.json()
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Unexpected OpenAI response shape: {body}") from exc

        if response_model is None:
            return text
        return parse_structured_response(text, response_model, self.provider_name)
