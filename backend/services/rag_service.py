"""Repository context retrieval for pull request reviews.

Strategy:

1. Always include the full content of files changed in the PR.

2. Discover a limited number of additional repository files likely related
   to the changed files using directory proximity and simple import matching.

3. Chunk related repository files and store them temporarily in a ChromaDB
   collection scoped to the review.

4. Retrieve the top-K related chunks most relevant to the PR using semantic
   similarity.

5. Merge mandatory changed-file context with retrieved supporting context.

6. Delete the temporary collection once retrieval is complete so the vector
   store does not grow unbounded across reviews.
"""

from __future__ import annotations

import logging
import re

import chromadb

from config.settings import Settings
from models.pr import PullRequest
from models.rag import RepositoryChunk, RetrievalResult
from services.github_service import GitHubService

logger = logging.getLogger(__name__)


_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE),
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    re.compile(
        r"""^\s*import\s+.*from\s+['"](.+?)['"]""",
        re.MULTILINE,
    ),
    re.compile(
        r"""require\(\s*['"](.+?)['"]\s*\)""",
    ),
]

# Maximum number of additional repository files considered as candidates.
MAX_RELATED_CANDIDATE_FILES = 40

# Maximum number of related files read and embedded.
# Changed files are NOT subject to this limit.
MAX_RELATED_FILES_TO_READ = 25


class RAGService:
    """Build repository context for a single pull request review."""

    def __init__(
        self,
        settings: Settings,
        github_service: GitHubService,
    ) -> None:
        """Initialize the repository context retrieval service."""

        self._settings = settings
        self._github = github_service
        self._client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
        )

    async def build_context(
        self,
        pull_request: PullRequest,
    ) -> RetrievalResult:
        """Build mandatory and retrieved repository context for a PR.

        All changed-file chunks are included deterministically. Additional
        repository context is selected using semantic retrieval.
        """

        # Changed files are mandatory review context.
        changed_chunks = await self._read_changed_file_chunks(
            pull_request,
        )

        # Discover additional repository files related to the PR.
        related_paths = await self._select_related_paths(
            pull_request,
        )

        # Limit only additional repository files.
        related_paths = related_paths[:MAX_RELATED_FILES_TO_READ]

        # Read and chunk additional repository files.
        related_chunks = await self._read_and_chunk_paths(
            pull_request,
            related_paths,
        )

        # Retrieve the most relevant supporting chunks.
        retrieved_chunks = await self._retrieve_supporting_context(
            pull_request,
            related_chunks,
        )

        # Combine mandatory and retrieved context.
        final_chunks = self._merge_chunks(
            changed_chunks,
            retrieved_chunks,
        )

        logger.info(
            "Built repository context for %s/%s#%s: "
            "%d mandatory chunks + %d retrieved chunks = %d total",
            pull_request.reference.owner,
            pull_request.reference.repository,
            pull_request.reference.number,
            len(changed_chunks),
            len(retrieved_chunks),
            len(final_chunks),
        )

        return RetrievalResult(chunks=final_chunks)

    async def _read_changed_file_chunks(
        self,
        pull_request: PullRequest,
    ) -> list[RepositoryChunk]:
        """Read and chunk every file changed by the pull request.

        Changed-file content is mandatory context and is never filtered
        through semantic retrieval.
        """

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

    async def _select_related_paths(
        self,
        pull_request: PullRequest,
    ) -> list[str]:
        """Select repository files likely related to the changed files.

        Related files are discovered using:

        - directory proximity
        - imports appearing in changed-file patches

        Changed files themselves are excluded because they are already
        mandatory review context.
        """

        reference = pull_request.reference

        changed_paths = {
            changed_file.filename
            for changed_file in pull_request.changed_files
        }

        repository_paths = await self._github.fetch_repository_tree(
            reference.owner,
            reference.repository,
            pull_request.head_branch,
        )

        same_directory_paths = self._find_same_directory_paths(
            changed_paths,
            repository_paths,
        )

        imported_modules = self._extract_imports_from_patches(
            pull_request,
        )

        import_related_paths = self._resolve_import_paths(
            imported_modules,
            repository_paths,
        )

        candidates = self._deduplicate_paths(
            same_directory_paths,
            import_related_paths,
        )

        # Changed files are handled separately as mandatory context.
        candidates = [
            path
            for path in candidates
            if path not in changed_paths
        ]

        return candidates[:MAX_RELATED_CANDIDATE_FILES]

    @staticmethod
    def _find_same_directory_paths(
        changed_paths: set[str],
        repository_paths: list[str],
    ) -> list[str]:
        """Return repository files located in changed-file directories."""

        changed_directories = {
            path.rsplit("/", 1)[0]
            for path in changed_paths
            if "/" in path
        }

        results: list[str] = []

        for path in repository_paths:
            if "/" not in path:
                continue

            directory = path.rsplit("/", 1)[0]

            if directory in changed_directories:
                results.append(path)

        return results

    @staticmethod
    def _extract_imports_from_patches(
        pull_request: PullRequest,
    ) -> set[str]:
        """Extract import references appearing in changed-file patches."""

        imported_modules: set[str] = set()

        for changed_file in pull_request.changed_files:
            if not changed_file.patch:
                continue

            for pattern in _IMPORT_PATTERNS:
                matches = pattern.findall(changed_file.patch)
                imported_modules.update(matches)

        return imported_modules

    @staticmethod
    def _resolve_import_paths(
        imported_modules: set[str],
        repository_paths: list[str],
    ) -> list[str]:
        """Resolve simple import references to repository file paths.

        This is intentionally conservative. It supports straightforward
        dotted Python-style imports and basic path-based imports but does not
        attempt to fully resolve package aliases or language-specific module
        resolution rules.
        """

        resolved: list[str] = []

        for module in imported_modules:
            normalized_module = (
                module.replace("\\", "/")
                .replace(".", "/")
                .lstrip("/")
            )

            for repository_path in repository_paths:
                normalized_path = repository_path.replace("\\", "/")

                path_without_extension = normalized_path.rsplit(
                    ".",
                    1,
                )[0]

                if (
                    path_without_extension == normalized_module
                    or path_without_extension.endswith(
                        f"/{normalized_module}"
                    )
                ):
                    resolved.append(repository_path)

        return resolved

    async def _read_and_chunk_paths(
        self,
        pull_request: PullRequest,
        paths: list[str],
    ) -> list[RepositoryChunk]:
        """Read repository paths at the PR head and split them into chunks."""

        reference = pull_request.reference
        chunks: list[RepositoryChunk] = []

        for file_path in paths:
            content = await self._github.fetch_file_content(
                reference.owner,
                reference.repository,
                file_path,
                pull_request.head_branch,
            )

            if not content:
                continue

            language = _guess_language(file_path)

            chunk_texts = _chunk_text(
                content,
                self._settings.rag_chunk_size,
                self._settings.rag_chunk_overlap,
            )

            for index, chunk_text in enumerate(chunk_texts):
                chunks.append(
                    RepositoryChunk(
                        file_path=file_path,
                        content=chunk_text,
                        chunk_index=index,
                        language=language,
                    )
                )

        return chunks

    async def _retrieve_supporting_context(
        self,
        pull_request: PullRequest,
        chunks: list[RepositoryChunk],
    ) -> list[RepositoryChunk]:
        """Retrieve related repository chunks most relevant to the PR."""

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

            top_k = min(
                self._settings.rag_top_k,
                len(chunks),
            )

            results = collection.query(
                query_texts=[query_text],
                n_results=top_k,
            )

            retrieved = self._to_repository_chunks(
                results,
                chunks,
            )

            logger.info(
                "RAG retrieval for %s/%s#%s: "
                "%d chunks retrieved from %d related chunks",
                reference.owner,
                reference.repository,
                reference.number,
                len(retrieved),
                len(chunks),
            )

            return retrieved

        finally:
            # Collections are scoped to a single review and removed
            # immediately after retrieval.
            self._client.delete_collection(
                name=collection_name,
            )

    @staticmethod
    def _merge_chunks(
        changed_chunks: list[RepositoryChunk],
        retrieved_chunks: list[RepositoryChunk],
    ) -> list[RepositoryChunk]:
        """Merge mandatory and retrieved context without duplicates."""

        seen: set[tuple[str, int]] = set()
        merged: list[RepositoryChunk] = []

        for chunk in changed_chunks + retrieved_chunks:
            key = (
                chunk.file_path,
                chunk.chunk_index,
            )

            if key in seen:
                continue

            seen.add(key)
            merged.append(chunk)

        return merged

    @staticmethod
    def _deduplicate_paths(
        *path_groups: list[str],
    ) -> list[str]:
        """Merge path groups while preserving their original priority order."""

        seen: set[str] = set()
        result: list[str] = []

        for paths in path_groups:
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    result.append(path)

        return result

    @staticmethod
    def _build_query_text(
        pull_request: PullRequest,
    ) -> str:
        """Build the semantic search query representing the pull request."""

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
        """Convert ChromaDB query results back into repository chunks."""

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
        """Create a valid ChromaDB collection name for a pull request."""

        raw = f"pr-{owner}-{repository}-{number}".lower()

        return re.sub(
            r"[^a-z0-9_-]",
            "-",
            raw,
        )[:63]


def _chunk_text(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split text into overlapping line-based chunks."""

    lines = content.splitlines()

    if not lines:
        return []

    chunks: list[str] = []

    start = 0
    step = max(chunk_size - overlap, 1)

    while start < len(lines):
        chunk_lines = lines[
            start : start + chunk_size
        ]

        chunks.append(
            "\n".join(chunk_lines)
        )

        start += step

    return chunks


_EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _guess_language(
    file_path: str,
) -> str | None:
    """Guess the programming language from a repository file extension."""

    for extension, language in _EXTENSION_LANGUAGE_MAP.items():
        if file_path.endswith(extension):
            return language

    return None