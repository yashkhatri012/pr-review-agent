
"""Tests for agent-specific repository context retrieval"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.pr import PullRequest, PullRequestReference
from models.rag import RepositoryChunk
from services.rag.retriever import ContextRetriever



@pytest.fixture
def pull_request() -> PullRequest:
    """Create a minimal pull request for retrieval tests"""

    return PullRequest(
        reference=PullRequestReference(
            owner="test-owner",
            repository="test-repo",
            number=1,
        ),
        title="Add authentication",
        description="Add authentication to the API.",
        author="test-user",
        base_branch="main",
        head_branch="feature/auth",
        head_sha="abc123",
        changed_files=[],
    )

@pytest.fixture
def repository_chunks() -> list[RepositoryChunk]:
    """Create repository chunks used by retrieval tests."""

    return [
        RepositoryChunk(
            file_path="auth/service.py",
            content="def authenticate_user(token): ...",
            chunk_index=0,
            language="python",
        ),
        RepositoryChunk(
            file_path="api/routes.py",
            content="def get_user(): ...",
            chunk_index=0,
            language="python",
        ),
        RepositoryChunk(
            file_path="database/users.py",
            content="def find_user(user_id): ...",
            chunk_index=0,
            language="python",
        ),
    ]


@pytest.mark.asyncio
async def test_retrieve_for_agents_returns_results_per_agent(
    pull_request: PullRequest,
    repository_chunks: list[RepositoryChunk],
) -> None:
    """Retrieve supporting context separately for each agent"""

    chroma_client = MagicMock()

    collection = MagicMock()

    collection.query.side_effect = [
        {
            "ids": [
                [
                    "auth/service.py::0",
                ],
            ],
        },
        {
            "ids": [
                [
                    "database/users.py::0",
                ],
            ],
        },
    ]

    chroma_client.get_or_create_collection.return_value = collection

    retriever = ContextRetriever(
        chroma_client=chroma_client,
        top_k=2,
    )

    agent_queries = {
        "security": "Find authentication and authorization code.",
        "bug": "Find code related to correctness and error handling.",
    }

    results = retriever.retrieve_for_agents(
        pull_request,
        repository_chunks,
        agent_queries,
    )

    assert set(results) == {
        "security",
        "bug",
    }

    assert results["security"] == [
        repository_chunks[0],
    ]

    assert results["bug"] == [
        repository_chunks[2],
    ]

    assert collection.query.call_count == 2


def test_retrieve_for_agents_returns_empty_results_for_empty_chunks(
    pull_request: PullRequest,
) -> None:
    """Return an empty result for every agent when no chunks exist"""

    chroma_client = MagicMock()

    retriever = ContextRetriever(
        chroma_client=chroma_client,
        top_k=5,
    )

    agent_queries = {
        "security": "Find security-related code.",
        "bug": "Find bug-related code.",
    }

    results = retriever.retrieve_for_agents(
        pull_request,
        [],
        agent_queries,
    )

    assert results == {
        "security": [],
        "bug": [],
    }

    chroma_client.get_or_create_collection.assert_not_called()


def test_retrieve_for_agents_returns_empty_results_for_empty_queries(
    pull_request: PullRequest,
    repository_chunks: list[RepositoryChunk],
) -> None:
    """Return an empty dictionary when no agent queries are supplied"""

    chroma_client = MagicMock()

    retriever = ContextRetriever(
        chroma_client=chroma_client,
        top_k=5,
    )

    results = retriever.retrieve_for_agents(
        pull_request,
        repository_chunks,
        {},
    )

    assert results == {}

    chroma_client.get_or_create_collection.assert_not_called()

