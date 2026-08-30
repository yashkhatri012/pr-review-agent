"""Central application configuration.

Every environment variable used by the application must be declared here.
No other module should call ``os.environ`` / ``os.getenv`` directly -- this
is the single source of truth for configuration, and it is what makes
switching LLM providers a one-line change (see DECISIONS.md, decision 007).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider selection -------------------------------------------------
    llm_provider: str = "gemini"
    llm_model: str = ""

    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    mistral_api_key: str | None = None
    openai_api_key: str | None = None

    # --- GitHub -------------------------------------------------------------
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"

    # --- RAG / ChromaDB -------------------------------------------------------
    chroma_db_path: str = "./data/chroma"
    chroma_collection_name: str = "pr_review_agent"
    rag_chunk_size: int = 200
    rag_chunk_overlap: int = 20
    rag_top_k: int = 8

    # --- App -------------------------------------------------------------
    log_level: str = "INFO"
    app_name: str = "PR Review Agent"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()
