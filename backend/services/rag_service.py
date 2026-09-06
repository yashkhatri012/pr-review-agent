"""Repository context retrieval for pull request reviews."""

from __future__ import annotations

import logging

import chromadb

from config.settings import Settings
from models.pr import PullRequest
from models.rag import RepositoryChunk, RetrievalResult
from services.github_service import GitHubService
from services.rag.chunker import chunk_text, guess_language
from services.rag.file_selector import (
    MAX_RELATED_CANDIDATE_FILES,
    RelatedFileSelector,
)
from services.rag.retriever import ContextRetriever

logger = logging.getLogger(__name__)


# Maximum number of related files read and embedded.
# Changed files are NOT subject to this limit.
MAX_RELATED_FILES_TO_READ = 25


class RAGService:
    """Build repository context for a single pull request review"""

    def __init__(
        self,
        settings: Settings,
        github_service: GitHubService,
    ) -> None:
        """Initialize the repository context retrieval service"""

        self._settings = settings
        self._github = github_service

        chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
        )

        self._file_selector = RelatedFileSelector(
            github_service,
        )

        self._retriever = ContextRetriever(
            chroma_client=chroma_client,
            top_k=settings.rag_top_k,
        )

    async def build_context(
        self,
        pull_request: PullRequest,
        agent_queries: dict[str, str],
    ) -> RetrievalResult:
        """Build changed file and agent-specific supporting context"""

        changed_chunks = await self._read_changed_file_chunks(
            pull_request,
        )

        related_paths = await self._file_selector.select(
            pull_request,
        )

        related_paths = related_paths[
            :MAX_RELATED_FILES_TO_READ
        ]

        related_chunks = await self._read_and_chunk_paths(
            pull_request,
            related_paths,
        )

        supporting_chunks = self._retriever.retrieve_for_agents(
            pull_request,
            related_chunks,
            agent_queries,
        )

        supporting_chunk_count = sum(
            len(chunks)
            for chunks in supporting_chunks.values()
        )

        logger.info(
            "rag_context_built",
            extra={
                "event": "rag_context_built",
                "repository": f"{pull_request.reference.owner}/{pull_request.reference.repository}",
                "pull_request": pull_request.reference.number,
                "changed_file_chunks": len(changed_chunks),
                "supporting_chunks": supporting_chunk_count,
                "agent_count": len(agent_queries),
            },
        )

        return RetrievalResult(
            changed_file_chunks=changed_chunks,
            supporting_chunks=supporting_chunks,
        )

    async def _read_changed_file_chunks(
        self,
        pull_request: PullRequest,
    ) -> list[RepositoryChunk]:
        """Read and chunk every file changed by the pull request"""

        changed_paths = list(
            dict.fromkeys(
                changed_file.filename
                for changed_file in pull_request.changed_files
            )
        )

        return await self._read_and_chunk_paths(
            pull_request,
            changed_paths,
        )

    async def _read_and_chunk_paths(
        self,
        pull_request: PullRequest,
        paths: list[str],
    ) -> list[RepositoryChunk]:
        """Read repository paths at the PR head and split them into chunks"""

        reference = pull_request.reference
        chunks: list[RepositoryChunk] = []

        for file_path in paths:
            content = await self._github.fetch_file_content(
                reference.owner,
                reference.repository,
                file_path,
                pull_request.head_sha,
            )

            if not content:
                continue

            language = guess_language(file_path)

            chunk_texts = chunk_text(
                content,
                self._settings.rag_chunk_size,
                self._settings.rag_chunk_overlap,
            )

            for index, text in enumerate(chunk_texts):
                chunks.append(
                    RepositoryChunk(
                        file_path=file_path,
                        content=text,
                        chunk_index=index,
                        language=language,
                    )
                )

        return chunks