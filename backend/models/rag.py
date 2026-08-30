"""Models used by the RAG (retrieval augmented generation) service."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryChunk(BaseModel):
    """A chunk of source code retrieved from the repository."""

    file_path: str
    content: str
    chunk_index: int
    language: str | None = None


class RetrievalResult(BaseModel):
    """The set of chunks retrieved as context for a PR review."""

    chunks: list[RepositoryChunk] = Field(default_factory=list)
