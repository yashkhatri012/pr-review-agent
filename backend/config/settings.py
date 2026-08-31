"""Central application configuration."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Agent specific LLM configuration ------------------------------------

    quality_llm_provider: str = "gemini"
    quality_llm_model: str = ""

    security_llm_provider: str = "gemini"
    security_llm_model: str = ""

    bug_llm_provider: str = "gemini"
    bug_llm_model: str = ""

    performance_llm_provider: str = "gemini"
    performance_llm_model: str = ""

    architecture_llm_provider: str = "gemini"
    architecture_llm_model: str = ""

    validator_llm_provider: str = "gemini"
    validator_llm_model: str = ""

    # --- Provider API keys ----------------------------------------------------

    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    mistral_api_key: str | None = None
    openai_api_key: str | None = None

    # --- GitHub ---------------------------------------------------------------

    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"

    # --- RAG / ChromaDB ------------------------------------------------------

    chroma_db_path: str = "./data/chroma"
    chroma_collection_name: str = "pr_review_agent"
    rag_chunk_size: int = 200
    rag_chunk_overlap: int = 20
    rag_top_k: int = 8

    # --- App -----------------------------------------------------------------

    log_level: str = "INFO"
    app_name: str = "PR Review Agent"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance loaded once per process."""
    return Settings()