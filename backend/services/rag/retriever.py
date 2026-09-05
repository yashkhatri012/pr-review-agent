"""Retrieve repository context using semantic similarity"""

from __future__ import annotations

import re

import chromadb

from models.pr import PullRequest
from models.rag import RepositoryChunk


class ContextRetriever:
    """Retrieve repository chunks relevant to a pull request"""

    def __init__(
        self,
        chroma_client: chromadb.PersistentClient,
        top_k: int,
    ) -> None:
        """Initialize the context retriever"""

        self._client = chroma_client
        self._top_k = top_k

    def retrieve(
        self,
        pull_request: PullRequest,
        chunks: list[RepositoryChunk],
    ) -> list[RepositoryChunk]:
        """Retrieve the most relevant supporting chunks"""

        if not chunks:
            return []

        reference = pull_request.reference

        collection_name = self._collection_name(
            reference.owner,
            reference.repository,
            reference.number,
        )

        collection = self._client.get_or_create_collection(
            name=collection_name,
        )

        try:
            collection.add(
                ids=[
                    f"{chunk.file_path}::{chunk.chunk_index}"
                    for chunk in chunks
                ],
                documents=[
                    chunk.content
                    for chunk in chunks
                ],
                metadatas=[
                    {
                        "file_path": chunk.file_path,
                        "language": chunk.language or "",
                    }
                    for chunk in chunks
                ],
            )

            query_text = self._build_query_text(
                pull_request,
            )

            return self._query_collection(
                collection=collection,
                query_text=query_text,
                chunks=chunks,
            )

        finally:
            self._client.delete_collection(
                name=collection_name,
            )

    def retrieve_for_agents(
        self,
        pull_request: PullRequest,
        chunks: list[RepositoryChunk],
        agent_queries: dict[str, str],
    ) -> dict[str, list[RepositoryChunk]]:
        """Retrieve supporting chunks separately for each review agent.

        The repository chunks are indexed once and then queried separately
        using each agent's specialized semantic query.
        """

        if not chunks or not agent_queries:
            return {
                agent_name: []
                for agent_name in agent_queries
            }

        reference = pull_request.reference

        collection_name = self._collection_name(
            reference.owner,
            reference.repository,
            reference.number,
        )

        collection = self._client.get_or_create_collection(
            name=collection_name,
        )

        try:
            collection.add(
                ids=[
                    f"{chunk.file_path}::{chunk.chunk_index}"
                    for chunk in chunks
                ],
                documents=[
                    chunk.content
                    for chunk in chunks
                ],
                metadatas=[
                    {
                        "file_path": chunk.file_path,
                        "language": chunk.language or "",
                    }
                    for chunk in chunks
                ],
            )

            results: dict[str, list[RepositoryChunk]] = {}

            for agent_name, query_text in agent_queries.items():
                results[agent_name] = self._query_collection(
                    collection=collection,
                    query_text=query_text,
                    chunks=chunks,
                )

            return results

        finally:
            self._client.delete_collection(
                name=collection_name,
            )

    def _query_collection(
        self,
        collection,
        query_text: str,
        chunks: list[RepositoryChunk],
    ) -> list[RepositoryChunk]:
        """Query a Chroma collection and convert results into repository chunks"""

        top_k = min(
            self._top_k,
            len(chunks),
        )

        results = collection.query(
            query_texts=[query_text],
            n_results=top_k,
        )

        return self._to_repository_chunks(
            results,
            chunks,
        )

    @staticmethod
    def _build_query_text(
        pull_request: PullRequest,
    ) -> str:
        """Build the semantic search query representing the pull request"""

        parts = [
            f"PR TITLE:\n{pull_request.title}",
            f"PR DESCRIPTION:\n{pull_request.description or ''}",
        ]

        for changed_file in pull_request.changed_files:
            parts.append(
                f"CHANGED FILE: {changed_file.filename}\n"
                f"DIFF:\n{changed_file.patch or ''}"
            )

        return "\n\n".join(parts)[:8000]

    @staticmethod
    def _to_repository_chunks(
        results: dict,
        original_chunks: list[RepositoryChunk],
    ) -> list[RepositoryChunk]:
        """Convert ChromaDB query results back into repository chunks"""

        by_id = {
            f"{chunk.file_path}::{chunk.chunk_index}": chunk
            for chunk in original_chunks
        }

        ids = results.get("ids", [[]])[0]

        return [
            by_id[chunk_id]
            for chunk_id in ids
            if chunk_id in by_id
        ]

    @staticmethod
    def _collection_name(
        owner: str,
        repository: str,
        number: int,
    ) -> str:
        """Create a valid ChromaDB collection name for a pull request"""

        raw = f"pr-{owner}-{repository}-{number}".lower()

        return re.sub(
            r"[^a-z0-9_-]",
            "-",
            raw,
        )[:63]