"""Utilities for chunking repository files"""


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


def chunk_text(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split text into overlapping line based chunks"""

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

        chunks.append("\n".join(chunk_lines))
        start += step

    return chunks


def guess_language(
    file_path: str,
) -> str | None:
    """Guess the programming language from a repository file extension"""

    for extension, language in _EXTENSION_LANGUAGE_MAP.items():
        if file_path.endswith(extension):
            return language

    return None