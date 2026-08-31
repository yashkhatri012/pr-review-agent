import pytest
from pydantic import ValidationError

from models.finding import ReviewFinding, Severity
from models.pr import ChangedFile, PullRequest, PullRequestReference
from models.review import FinalReview, ReviewDecision, ReviewSummary


def test_review_finding_requires_valid_severity():
    with pytest.raises(ValidationError):
        ReviewFinding(
            severity="not-a-real-severity",
            file="app.py",
            title="x",
            description="x",
            evidence="x",
            suggestion="x",
        )


def test_review_finding_accepts_valid_data():
    finding = ReviewFinding(
        severity=Severity.HIGH,
        file="src/api/auth.py",
        line=42,
        title="Missing authorization check",
        description="Ownership is not verified.",
        evidence="Resource fetched directly by id.",
        suggestion="Verify ownership before returning the resource.",
        source_agents=["security"],
    )
    assert finding.severity == Severity.HIGH
    assert finding.source_agents == ["security"]


def test_pull_request_model_roundtrip():
    reference = PullRequestReference(owner="o", repository="r", number=1, url="https://github.com/o/r/pull/1")
    pr = PullRequest(
    reference=reference,
    title="Add feature",
    author="octocat",
    base_branch="main",
    head_branch="feature",
    head_sha="abc123def456",
    changed_files=[
        ChangedFile(
            filename="a.py",
            status="modified",
            additions=1,
            deletions=0,
        )
    ],
)
    assert pr.reference.number == 1
    assert len(pr.changed_files) == 1


def test_final_review_total_findings_is_explicit_not_derived():
    reference = PullRequestReference(owner="o", repository="r", number=1, url="https://github.com/o/r/pull/1")
    summary = ReviewSummary(decision=ReviewDecision.APPROVED, summary="Looks good.", total_findings=0)
    review = FinalReview(pull_request=reference, summary=summary, findings=[])
    assert review.summary.decision == ReviewDecision.APPROVED
    assert review.findings == []
