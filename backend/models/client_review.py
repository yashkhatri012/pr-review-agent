

"""Models representing the human readable review returned to the client."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.review import ReviewDecision


class ReviewInsight(BaseModel):
    """A concise insight included in the overall PR review."""

    text: str = Field(min_length=1)


class ClientReviewSummary(BaseModel):
    """Human readable summary of the overall pull request review."""

    decision: ReviewDecision

    overview: str = Field(
        min_length=1,
        description="A concise overall assessment of the pull request.",
    )

    key_points: list[ReviewInsight] = Field(default_factory=list)

    total_findings: int = Field(ge=0)


class CodeReviewComment(BaseModel):
    """A human readable review comment for a validated finding."""

    severity: str

    file: str

    line: int | None = None

    title: str

    review_comment: str

    why_it_matters: str

    suggested_fix: str


class ClientReview(BaseModel):
    """The complete human readable PR review returned to the client."""

    summary: ClientReviewSummary

    code_review: list[CodeReviewComment] = Field(default_factory=list)