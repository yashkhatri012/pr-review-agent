"""Models describing the final, validated review output."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from models.finding import ReviewFinding
from models.pr import PullRequestReference


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_SUGGESTIONS = "approved_with_suggestions"
    CHANGES_REQUESTED = "changes_requested"


class ReviewSummary(BaseModel):
    decision: ReviewDecision
    summary: str
    total_findings: int


class FinalReview(BaseModel):
    pull_request: PullRequestReference
    summary: ReviewSummary
    findings: list[ReviewFinding] = Field(default_factory=list)
