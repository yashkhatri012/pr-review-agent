from __future__ import annotations

import os
import threading


class GeminiKeyManager:
    """Thread-safe round-robin manager for Gemini API keys."""

    def __init__(self) -> None:
        self._keys = self._load_keys()
        self._index = 0
        self._lock = threading.Lock()

    @staticmethod
    def _load_keys() -> list[str]:
        """Load configured Gemini API keys from environment variables."""
        keys: list[str] = []

        for index in range(1, 19):
            key = os.getenv(f"GEMINI_API_KEY_{index}")

            if key:
                keys.append(key)

        if not keys:
            raise ValueError(
                "No Gemini API keys configured. "
                "Set GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc."
            )

        return keys

    def get_next_key(self) -> str:
        """Return the next Gemini API key using round-robin rotation."""
        with self._lock:
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)

        return key

    @property
    def key_count(self) -> int:
        """Return the number of configured Gemini API keys."""
        return len(self._keys)