
"""Models describing the input to, and output from, review agents"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.finding import ReviewFinding
from models.pr import PullRequest
from models.rag import RepositoryChunk


class AgentContext(BaseModel):
    """Everything a specialized agent needs to perform its review.

    Changed file context contains the full content of files modified by the
    pull request and represents the primary review target. Supporting context
    contains relevant chunks retrieved from unchanged repository files and is
    provided only to help understand dependencies, behavior, and architecture.
    """

    pull_request: PullRequest

    changed_file_context: list[RepositoryChunk] = Field(
        default_factory=list,
    )

    supporting_context: list[RepositoryChunk] = Field(
        default_factory=list,
    )


class AgentReview(BaseModel):
    """The structured output every specialized agent must produce"""

    agent_name: str
    findings: list[ReviewFinding] = Field(default_factory=list)

