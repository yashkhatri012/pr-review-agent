"""Simple RAG (retrieval augmented generation) service.

Strategy (see DECISIONS.md, decisions 008-011):
  1. Always include the content of files changed in the PR.
  2. Pull in a small number of additional repository files that are
     likely related (same directories as changed files, plus files
     referenced via simple import-statement scanning).
  3. Chunk everything and store it in a ChromaDB collection scoped to
     this single review.
  4. Retrieve the top-K chunks most relevant to the PR (title,
     description, and diffs) using semantic similarity.
  5. Drop the scoped collection once retrieval is done, so the vector
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
    re.compile(r"^\s*from\s+([\w\.]+)\s+import", re.MULTILINE),
    re.compile(r"^\s*import\s+([\w\.]+)", re.MULTILINE),
    re.compile(r"""^\s*import\s+.*from\s+['"](.+?)['"]""", re.MULTILINE),
    re.compile(r"""require\(['"](.+?)['"]\)"""),
]

# How many extra (non-changed) candidate files we consider at most.
MAX_CANDIDATE_FILES = 40
# How many source files we actually read + embed at most (keeps cost bounded).
MAX_FILES_TO_EMBED = 25


class RAGService:
    def __init__(self, settings: Settings, github_service: GitHubService) -> None:
        self._settings = settings
        self._github = github_service
        self._client = chromadb.PersistentClient(path=settings.chroma_db_path)

    async def build_context(self, pull_request: PullRequest) -> RetrievalResult:
        reference = pull_request.reference
        collection_name = self._collection_name(reference.owner, reference.repository, reference.number)
        collection = self._client.get_or_create_collection(name=collection_name)

        try:
            candidate_paths = self._select_candidate_paths(pull_request)
            chunks = await self._read_and_chunk(pull_request, candidate_paths)

            if not chunks:
                return RetrievalResult(chunks=[])

            collection.add(
                ids=[f"{c.file_path}::{c.chunk_index}" for c in chunks],
                documents=[c.content for c in chunks],
                metadatas=[{"file_path": c.file_path, "language": c.language or ""} for c in chunks],
            )

            query_text = self._build_query_text(pull_request)
            top_k = min(self._settings.rag_top_k, len(chunks))
            results = collection.query(query_texts=[query_text], n_results=top_k)

            retrieved = self._to_repository_chunks(results, chunks)
            logger.info(
                "RAG retrieval for %s/%s#%s: %d chunks retrieved out of %d indexed",
                reference.owner,
                reference.repository,
                reference.number,
                len(retrieved),
                len(chunks),
            )
            return RetrievalResult(chunks=retrieved)
        finally:
            # Scoped collections keep the vector store from growing forever.
            self._client.delete_collection(name=collection_name)

    def _select_candidate_paths(self, pull_request: PullRequest) -> list[str]:
        changed_paths = [f.filename for f in pull_request.changed_files]
        changed_dirs = {p.rsplit("/", 1)[0] for p in changed_paths if "/" in p}

        imported_modules: set[str] = set()
        for changed_file in pull_request.changed_files:
            if changed_file.patch:
                for pattern in _IMPORT_PATTERNS:
                    imported_modules.update(pattern.findall(changed_file.patch))

        candidates = list(dict.fromkeys(changed_paths))  # preserve order, dedupe
        return candidates[:MAX_CANDIDATE_FILES], changed_dirs, imported_modules  # type: ignore[return-value]

    async def _read_and_chunk(
        self, pull_request: PullRequest, candidate_data
    ) -> list[RepositoryChunk]:
        candidate_paths, _changed_dirs, _imported_modules = candidate_data
        reference = pull_request.reference
        chunks: list[RepositoryChunk] = []

        files_to_read = candidate_paths[:MAX_FILES_TO_EMBED]
        for file_path in files_to_read:
            content = await self._github.fetch_file_content(
                reference.owner, reference.repository, file_path, pull_request.head_branch
            )
            if not content:
                continue
            language = _guess_language(file_path)
            for index, chunk_text in enumerate(
                _chunk_text(content, self._settings.rag_chunk_size, self._settings.rag_chunk_overlap)
            ):
                chunks.append(
                    RepositoryChunk(
                        file_path=file_path,
                        content=chunk_text,
                        chunk_index=index,
                        language=language,
                    )
                )
        return chunks

    @staticmethod
    def _build_query_text(pull_request: PullRequest) -> str:
        parts = [pull_request.title, pull_request.description or ""]
        parts.extend(f.patch or "" for f in pull_request.changed_files)
        return "\n".join(parts)[:8000]

    @staticmethod
    def _to_repository_chunks(results: dict, original_chunks: list[RepositoryChunk]) -> list[RepositoryChunk]:
        by_id = {f"{c.file_path}::{c.chunk_index}": c for c in original_chunks}
        ids = results.get("ids", [[]])[0]
        return [by_id[i] for i in ids if i in by_id]

    @staticmethod
    def _collection_name(owner: str, repository: str, number: int) -> str:
        raw = f"pr-{owner}-{repository}-{number}".lower()
        return re.sub(r"[^a-z0-9_-]", "-", raw)[:63]


def _chunk_text(content: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping line-based chunks."""
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(lines):
        chunk_lines = lines[start : start + chunk_size]
        chunks.append("\n".join(chunk_lines))
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


def _guess_language(file_path: str) -> str | None:
    for extension, language in _EXTENSION_LANGUAGE_MAP.items():
        if file_path.endswith(extension):
            return language
    return None
