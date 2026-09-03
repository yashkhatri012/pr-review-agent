"""API routes for triggering and monitoring PR reviews."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse

from config.settings import Settings, get_settings
from llm.service import LLMService
from models.api import HealthResponse, ReviewRequest, ReviewResponse
from services.github_service import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
)
from services.rag_service import RAGService
from services.review_job import ReviewJobManager
from services.review_service import ReviewService
from utils.github_url import InvalidPullRequestUrlError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["review"],
)

_job_manager = ReviewJobManager()


@lru_cache
def _get_github_service() -> GitHubService:
    """Return the shared GitHub service instance."""

    settings = get_settings()

    return GitHubService(
        token=settings.github_token,
        base_url=settings.github_api_base_url,
    )


@lru_cache
def _get_rag_service() -> RAGService:
    """Return the shared RAG service instance."""

    settings = get_settings()

    return RAGService(
        settings=settings,
        github_service=_get_github_service(),
    )


@lru_cache
def _get_llm_service() -> LLMService:
    """Return the shared LLM service instance."""

    return LLMService(get_settings())


def get_review_service(
    settings: Settings = Depends(get_settings),
) -> ReviewService:
    """Build a ReviewService for this request."""

    return ReviewService(
        settings=settings,
        github_service=_get_github_service(),
        rag_service=_get_rag_service(),
        llm_service=_get_llm_service(),
    )


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    """Return the application health status."""

    return HealthResponse(status="ok")


@router.post(
    "/review",
    response_model=ReviewResponse,
)
async def review_pull_request(
    request: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Run a pull request review synchronously."""

    pr_url = str(request.pr_url)

    try:
        final_review = await review_service.review_pull_request(
            pr_url
        )

    except InvalidPullRequestUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except GitHubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except GitHubAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except GitHubServiceError as exc:
        logger.error(
            "GitHub service error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch data from GitHub.",
        ) from exc

    except ValueError as exc:
        logger.error(
            "LLM configuration error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The LLM configuration is invalid.",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected error while reviewing %s",
            pr_url,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        ) from exc

    return ReviewResponse(
        status="completed",
        review=final_review,
    )


@router.post("/review/start")
async def start_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    review_service: ReviewService = Depends(get_review_service),
) -> dict[str, str]:
    """Start an asynchronous pull request review."""

    job = _job_manager.create_job()

    background_tasks.add_task(
        _job_manager.run_review,
        job,
        review_service,
        str(request.pr_url),
    )

    return {
        "review_id": job.review_id,
    }


@router.get("/review/{review_id}/events")
async def review_events(
    review_id: str,
):
    """Stream progress events for a running review."""

    job = _job_manager.get_job(review_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review job not found.",
        )

    return StreamingResponse(
        _job_manager.stream_events(job),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )