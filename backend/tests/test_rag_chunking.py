
"""Tests for RAG chunking and repository-context helper behavior."""

from services.rag_service import (
    RAGService,
    _chunk_text,
    _guess_language,
)


def test_chunk_text_returns_empty_for_empty_content() -> None:
    """Empty content should produce no chunks."""

    assert _chunk_text("", chunk_size=10, overlap=2) == []


def test_chunk_text_returns_single_chunk_when_content_fits() -> None:
    """Content smaller than the chunk size should produce one chunk."""

    content = "\n".join(
        [
            "line 1",
            "line 2",
            "line 3",
        ]
    )

    chunks = _chunk_text(
        content,
        chunk_size=10,
        overlap=2,
    )

    assert chunks == [content]


def test_chunk_text_splits_content_by_line_count() -> None:
    """Content larger than the chunk size should be split into chunks."""

    content = "\n".join(
        [
            "line 1",
            "line 2",
            "line 3",
            "line 4",
            "line 5",
        ]
    )

    chunks = _chunk_text(
        content,
        chunk_size=2,
        overlap=0,
    )

    assert chunks == [
        "line 1\nline 2",
        "line 3\nline 4",
        "line 5",
    ]


def test_chunk_text_applies_overlap() -> None:
    """Adjacent chunks should share overlapping lines."""

    content = "\n".join(
        [
            "line 1",
            "line 2",
            "line 3",
            "line 4",
            "line 5",
        ]
    )

    chunks = _chunk_text(
        content,
        chunk_size=3,
        overlap=1,
    )

    assert chunks == [
        "line 1\nline 2\nline 3",
        "line 3\nline 4\nline 5",
        "line 5",
    ]


def test_chunk_text_handles_overlap_equal_to_chunk_size() -> None:
    """Chunking should still progress when overlap equals chunk size."""

    content = "\n".join(
        [
            "line 1",
            "line 2",
            "line 3",
        ]
    )

    chunks = _chunk_text(
        content,
        chunk_size=2,
        overlap=2,
    )

    assert chunks == [
        "line 1\nline 2",
        "line 2\nline 3",
        "line 3",
    ]


def test_guess_language_for_python() -> None:
    """Python files should be identified correctly."""

    assert _guess_language("src/service.py") == "python"


def test_guess_language_for_typescript() -> None:
    """TypeScript files should be identified correctly."""

    assert _guess_language("src/component.ts") == "typescript"


def test_guess_language_for_tsx() -> None:
    """TSX files should be identified as TypeScript."""

    assert _guess_language("src/component.tsx") == "typescript"


def test_guess_language_for_javascript() -> None:
    """JavaScript files should be identified correctly."""

    assert _guess_language("src/index.js") == "javascript"


def test_guess_language_for_unknown_extension() -> None:
    """Unknown file extensions should return None."""

    assert _guess_language("src/file.unknown") is None


def test_find_same_directory_paths() -> None:
    """Files beside changed files should be discovered."""

    changed_paths = {
        "services/review_service.py",
        "agents/bug_agent.py",
    }

    repository_paths = [
        "services/review_service.py",
        "services/github_service.py",
        "services/rag_service.py",
        "agents/bug_agent.py",
        "agents/security_agent.py",
        "models/review.py",
    ]

    results = RAGService._find_same_directory_paths(
        changed_paths,
        repository_paths,
    )

    assert results == [
        "services/review_service.py",
        "services/github_service.py",
        "services/rag_service.py",
        "agents/bug_agent.py",
        "agents/security_agent.py",
    ]


def test_find_same_directory_paths_ignores_root_files() -> None:
    """Root-level files should not match a changed directory."""

    changed_paths = {
        "main.py",
    }

    repository_paths = [
        "main.py",
        "settings.py",
        "services/rag_service.py",
    ]

    results = RAGService._find_same_directory_paths(
        changed_paths,
        repository_paths,
    )

    assert results == []


def test_resolve_import_paths_for_python_module() -> None:
    """Python dotted imports should resolve to repository files."""

    imported_modules = {
        "services.github_service",
    }

    repository_paths = [
        "services/github_service.py",
        "services/rag_service.py",
        "models/pr.py",
    ]

    results = RAGService._resolve_import_paths(
        imported_modules,
        repository_paths,
    )

    assert results == [
        "services/github_service.py",
    ]


def test_resolve_import_paths_for_nested_module() -> None:
    """Nested module imports should resolve correctly."""

    imported_modules = {
        "pr_review.services.github_service",
    }

    repository_paths = [
        "pr_review/services/github_service.py",
        "pr_review/services/rag_service.py",
    ]

    results = RAGService._resolve_import_paths(
        imported_modules,
        repository_paths,
    )

    assert results == [
        "pr_review/services/github_service.py",
    ]


def test_resolve_import_paths_returns_empty_when_not_found() -> None:
    """Unknown imports should not produce repository paths."""

    imported_modules = {
        "external.package",
    }

    repository_paths = [
        "services/github_service.py",
        "models/pr.py",
    ]

    results = RAGService._resolve_import_paths(
        imported_modules,
        repository_paths,
    )

    assert results == []


def test_deduplicate_paths_preserves_priority_order() -> None:
    """Path groups should be merged without duplicates."""

    results = RAGService._deduplicate_paths(
        [
            "services/a.py",
            "services/b.py",
        ],
        [
            "services/b.py",
            "models/c.py",
        ],
    )

    assert results == [
        "services/a.py",
        "services/b.py",
        "models/c.py",
    ]


def test_collection_name_is_lowercase() -> None:
    """Collection names should be normalized to lowercase."""

    result = RAGService._collection_name(
        "MyOwner",
        "MyRepository",
        123,
    )

    assert result == "pr-myowner-myrepository-123"


def test_collection_name_replaces_invalid_characters() -> None:
    """Invalid collection-name characters should be replaced."""

    result = RAGService._collection_name(
        "my.owner",
        "my/repository",
        123,
    )

    assert result == "pr-my-owner-my-repository-123"


def test_collection_name_is_limited_to_63_characters() -> None:
    """Collection names should respect the configured maximum length."""

    result = RAGService._collection_name(
        "very-long-owner-name-that-keeps-going",
        "very-long-repository-name-that-keeps-going",
        123456,
    )

    assert len(result) <= 63

