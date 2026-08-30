"""Request/response models for the public API surface."""
from __future__ import annotations

from pydantic import BaseModel, HttpUrl

from models.review import FinalReview


class ReviewRequest(BaseModel):
    """Incoming request body for POST /api/review."""

    pr_url: HttpUrl


class ReviewResponse(BaseModel):
    """Response body for POST /api/review."""

    status: str
    review: FinalReview


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str
