
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel) #some type that will be determined later
# ResponseModelT is a generic type variable that can be used to represent any subclass of BaseModel



class LLMProviderError(Exception):
    """Raised when a provider call fails or returns an unusable response"""


class BaseLLM(ABC):
    """Common interface all LLM provider adapters must implement"""

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT] | None = None,
    ) -> ResponseModelT | str:
        """Generate a completion from the LLM provider"""
        raise NotImplementedError

    