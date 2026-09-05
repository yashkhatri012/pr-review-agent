"""Select repository files related to a pull request"""

from __future__ import annotations

import re

from models.pr import PullRequest
from services.github_service import GitHubService


# Maximum number of additional repository files considered as candidates
MAX_RELATED_CANDIDATE_FILES = 40


_IMPORT_PATTERNS = [
    re.compile(
        r"^\s*from\s+([\w.]+)\s+import",
        re.MULTILINE,
    ),
    re.compile(
        r"^\s*import\s+([\w.]+)",
        re.MULTILINE,
    ),
    re.compile(
        r"""^\s*import\s+.*from\s+['"](.+?)['"]""",
        re.MULTILINE,
    ),
    re.compile(
        r"""require\(\s*['"](.+?)['"]\s*\)""",
        re.MULTILINE,
    ),
]


class RelatedFileSelector:
    """Select repository files likely related to changed files"""

    def __init__(
        self,
        github_service: GitHubService,
    ) -> None:
        """Initialize the related file selector"""

        self._github = github_service

    async def select(
        self,
        pull_request: PullRequest,
    ) -> list[str]:
        """Select repository files likely related to the pull request"""

        reference = pull_request.reference

        changed_paths = {
            changed_file.filename
            for changed_file in pull_request.changed_files
        }

        repository_paths = await self._github.fetch_repository_tree(
            reference.owner,
            reference.repository,
            pull_request.head_sha,
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
        """Return repository files located in changed-file directories"""

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
        """Extract import references appearing in changed-file patches"""

        imported_modules: set[str] = set()

        for changed_file in pull_request.changed_files:
            if not changed_file.patch:
                continue

            for pattern in _IMPORT_PATTERNS:
                imported_modules.update(
                    pattern.findall(changed_file.patch)
                )

        return imported_modules

    @staticmethod
    def _resolve_import_paths(
        imported_modules: set[str],
        repository_paths: list[str],
    ) -> list[str]:
        """Resolve simple import references to repository file paths"""

        resolved: list[str] = []

        for module in imported_modules:
            normalized_module = (
                module.replace("\\", "/")
                .replace(".", "/")
                .lstrip("/")
            )

            for repository_path in repository_paths:
                normalized_path = repository_path.replace(
                    "\\",
                    "/",
                )

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

    @staticmethod
    def _deduplicate_paths(
        *path_groups: list[str],
    ) -> list[str]:
        """Merge path groups while preserving priority order"""

        seen: set[str] = set()
        result: list[str] = []

        for paths in path_groups:
            for path in paths:
                if path in seen:
                    continue

                seen.add(path)
                result.append(path)

        return result