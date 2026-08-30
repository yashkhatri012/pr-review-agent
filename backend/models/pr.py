"""Domain models representing a GitHub Pull Request."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PullRequestReference(BaseModel):
    """Identifies a specific pull request on GitHub."""

    owner: str
    repository: str
    number: int
    url: str


class ChangedFile(BaseModel):
    """A single file changed within a pull request."""

    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None


class PullRequest(BaseModel):
    """Full representation of a pull request used throughout the app."""

    reference: PullRequestReference
    title: str
    description: str | None = None
    author: str
    base_branch: str
    head_branch: str
    changed_files: list[ChangedFile] = Field(default_factory=list)
