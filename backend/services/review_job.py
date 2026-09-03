"""In-memory review job management and progress event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from models.client_review import ClientReview
from services.review_service import ReviewService

logger = logging.getLogger(__name__)


@dataclass
class ReviewJob:
    """Store the state and events for a single pull request review."""

    review_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=asyncio.Queue,
    )
    result: ClientReview | None = None
    error: str | None = None
    completed: bool = False


class ReviewJobManager:
    """Manage asynchronous review jobs and their progress events."""

    def __init__(self) -> None:
        """Initialize the review job manager."""

        self._jobs: dict[str, ReviewJob] = {}

    def create_job(self) -> ReviewJob:
        """Create and register a new review job."""

        review_id = uuid.uuid4().hex

        job = ReviewJob(
            review_id=review_id,
        )

        self._jobs[review_id] = job

        return job

    def get_job(self, review_id: str) -> ReviewJob | None:
        """Return a review job by its identifier."""

        return self._jobs.get(review_id)

    async def run_review(
        self,
        job: ReviewJob,
        review_service: ReviewService,
        pr_url: str,
    ) -> None:
        """Run a review and publish progress events to its queue."""

        async def publish(
            stage: str,
            status: str,
            message: str,
        ) -> None:
            """Publish a progress event to the job queue."""

            await job.queue.put(
                {
                    "type": "progress",
                    "stage": stage,
                    "status": status,
                    "message": message,
                }
            )

        try:
            review = await review_service.review_pull_request(
                pr_url,
                progress_callback=publish,
            )

            job.result = review
            job.completed = True

            await job.queue.put(
                {
                    "type": "completed",
                    "review": review.model_dump(mode="json"),
                }
            )

        except Exception as exc:
            logger.exception(
                "Review job %s failed",
                job.review_id,
            )

            job.error = str(exc)
            job.completed = True

            await job.queue.put(
                {
                    "type": "error",
                    "message": "The pull request review failed.",
                }
            )

    async def stream_events(
        self,
        job: ReviewJob,
    ):
        """Yield server-sent events for a review job."""

        while True:
            event = await job.queue.get()

            yield (
                "event: "
                f"{event['type']}\n"
                "data: "
                f"{json.dumps(event)}\n\n"
            )

            if event["type"] in {"completed", "error"}:
                break