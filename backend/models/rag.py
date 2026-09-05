
"""Models used by the RAG service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryChunk(BaseModel):
    """A chunk of source code extracted from a repository file"""

    file_path: str
    content: str
    chunk_index: int
    language: str | None = None


class RetrievalResult(BaseModel):
    """Repository context assembled for a pull request review.

    Changed file chunks are mandatory review context. Supporting chunks are
    retrieved from related, unchanged repository files and separated by
    specialist agent so each agent receives only the repository context
    relevant to its review responsibility.
    """

    changed_file_chunks: list[RepositoryChunk] = Field(
        default_factory=list,
    )

    supporting_chunks: dict[str, list[RepositoryChunk]] = Field(
        default_factory=dict,
    )


# Now supporting chunks looks like:
#     supporting_chunks = {
#     "security": [...],
#     "bug": [...],
#     "quality": [...],
#     "performance": [...],
# }
