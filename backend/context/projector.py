"""Build focused context views for specialized review agents."""

from __future__ import annotations

from models.agent import AgentContext
from models.rag import RepositoryChunk


class ContextProjector:
    """Project shared review context into an agent-specific view"""

    def project(
        self,
        context: AgentContext,
        keywords: set[str],
    ) -> AgentContext:
        """Return a context containing only relevant supporting chunks.

        Changed-file context is preserved because it represents the primary
        review target. Supporting context is filtered using lightweight
        lexical relevance matching.
        """

        supporting_context = [
            chunk
            for chunk in context.supporting_context
            if self._is_relevant(chunk, keywords)
        ]

        return context.model_copy(
            update={
                "supporting_context": supporting_context,
            }
        )

    @staticmethod
    def _is_relevant(
        chunk: RepositoryChunk,
        keywords: set[str],
    ) -> bool:
        """Return whether a repository chunk is relevant to an agent"""

        searchable_text = (
            f"{chunk.file_path}\n"
            f"{chunk.content}"
        ).lower()

        return any(
            keyword.lower() in searchable_text
            for keyword in keywords
        )