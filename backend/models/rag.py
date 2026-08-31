
"""Models used by the RAG service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryChunk(BaseModel):
    """A chunk of source code extracted from a repository file."""

    file_path: str
    content: str
    chunk_index: int
    language: str | None = None


class RetrievalResult(BaseModel):
    """Repository context assembled for a pull request review.

    Changed file chunks are mandatory review context. Supporting chunks are
    retrieved from related, unchanged repository files to provide additional
    architectural and dependency context.
    """

    changed_file_chunks: list[RepositoryChunk] = Field(
        default_factory=list,
    )

    supporting_chunks: list[RepositoryChunk] = Field(
        default_factory=list,
    )

