"""GitHub integration: fetching PR metadata, diffs, and repository files."""
from __future__ import annotations

import base64
import logging

import httpx

from models.pr import ChangedFile, PullRequest, PullRequestReference

logger = logging.getLogger(__name__)

# Directories that never contain content worth sending to the LLM.
IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "__pycache__",
}


class GitHubServiceError(Exception):
    """Base class for GitHub integration errors."""


class GitHubNotFoundError(GitHubServiceError):
    """Raised when a PR or repository does not exist (or is inaccessible)."""


class GitHubAuthError(GitHubServiceError):
    """Raised when GitHub rejects the request due to missing/invalid auth."""


class GitHubRateLimitError(GitHubServiceError):
    """Raised when the GitHub API rate limit has been exhausted."""


class GitHubService:
    """Thin, typed wrapper around the GitHub REST API."""

    def __init__(self, token: str | None, base_url: str, timeout: float = 30.0) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get(self, client: httpx.AsyncClient, path: str, **kwargs) -> httpx.Response:
        url = f"{self._base_url}{path}"
        try:
            response = await client.get(url, headers=self._headers(), **kwargs)
        except httpx.HTTPError as exc:
            raise GitHubServiceError(f"Network error calling GitHub: {exc}") from exc

        if response.status_code == 404:
            raise GitHubNotFoundError(
                f"GitHub resource not found (it may be private or not exist): {path}"
            )
        if response.status_code in (401, 403):
            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining == "0":
                raise GitHubRateLimitError("GitHub API rate limit exceeded.")
            raise GitHubAuthError(
                "GitHub rejected the request. Check GITHUB_TOKEN and repository access."
            )
        if response.status_code >= 400:
            raise GitHubServiceError(
                f"GitHub API error ({response.status_code}) for {path}: {response.text[:300]}"
            )
        return response

    async def fetch_pull_request(self, reference: PullRequestReference) -> PullRequest:
        """Fetch PR metadata and its changed files."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            pr_path = f"/repos/{reference.owner}/{reference.repository}/pulls/{reference.number}"
            pr_response = await self._get(client, pr_path)
            pr_data = pr_response.json()

            changed_files = await self._fetch_changed_files(client, reference)

        return PullRequest(
            reference=reference,
            title=pr_data.get("title", ""),
            description=pr_data.get("body"),
            author=pr_data.get("user", {}).get("login", "unknown"),
            base_branch=pr_data.get("base", {}).get("ref", ""),
            head_branch=pr_data.get("head", {}).get("ref", ""),
            changed_files=changed_files,
        )

    async def _fetch_changed_files(
        self, client: httpx.AsyncClient, reference: PullRequestReference
    ) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        page = 1
        while True:
            path = (
                f"/repos/{reference.owner}/{reference.repository}"
                f"/pulls/{reference.number}/files"
            )
            response = await self._get(client, path, params={"per_page": 100, "page": page})
            batch = response.json()
            if not batch:
                break
            for item in batch:
                files.append(
                    ChangedFile(
                        filename=item["filename"],
                        status=item.get("status", "modified"),
                        additions=item.get("additions", 0),
                        deletions=item.get("deletions", 0),
                        patch=item.get("patch"),
                    )
                )
            if len(batch) < 100:
                break
            page += 1
        return files

    async def fetch_repository_tree(
        self, owner: str, repository: str, ref: str
    ) -> list[str]:
        """Return all source file paths in the repository at ``ref``,
        excluding ignored directories."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            path = f"/repos/{owner}/{repository}/git/trees/{ref}"
            response = await self._get(client, path, params={"recursive": "1"})
            tree = response.json().get("tree", [])

        file_paths = []
        for entry in tree:
            if entry.get("type") != "blob":
                continue
            file_path = entry.get("path", "")
            if self._is_ignored(file_path):
                continue
            file_paths.append(file_path)
        return file_paths

    async def fetch_file_content(
        self, owner: str, repository: str, path: str, ref: str
    ) -> str | None:
        """Fetch the text content of a single repository file, or None if
        it cannot be read as text (e.g. binary, too large)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await self._get(
                    client,
                    f"/repos/{owner}/{repository}/contents/{path}",
                    params={"ref": ref},
                )
            except GitHubNotFoundError:
                return None

        data = response.json()
        if data.get("encoding") != "base64" or "content" not in data:
            return None
        try:
            return base64.b64decode(data["content"]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            logger.debug("Skipping non-UTF-8 file: %s", path)
            return None

    @staticmethod
    def _is_ignored(file_path: str) -> bool:
        parts = set(file_path.split("/"))
        return bool(parts & IGNORED_DIRECTORIES)
