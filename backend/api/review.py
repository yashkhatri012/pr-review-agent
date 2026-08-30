"""API routes for triggering and health-checking PR reviews."""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from config.settings import Settings, get_settings
from llm.base import LLMProviderError
from llm.factory import get_llm_provider
from models.api import HealthResponse, ReviewRequest, ReviewResponse
from services.github_service import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
)
from services.rag_service import RAGService
from services.review_service import ReviewService
from utils.github_url import InvalidPullRequestUrlError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["review"])


@lru_cache
def _get_github_service() -> GitHubService:
    settings = get_settings()
    return GitHubService(token=settings.github_token, base_url=settings.github_api_base_url)


@lru_cache
def _get_rag_service() -> RAGService:
    settings = get_settings()
    return RAGService(settings=settings, github_service=_get_github_service())


def get_review_service(settings: Settings = Depends(get_settings)) -> ReviewService:
    """Build a ReviewService for this request.

    The LLM provider is constructed fresh per request (cheap: no network
    call happens until ``generate`` is invoked) so that provider/model
    configuration changes are always picked up without restarting the
    process's cached singletons.
    """
    llm = get_llm_provider(settings)
    return ReviewService(
        settings=settings,
        github_service=_get_github_service(),
        rag_service=_get_rag_service(),
        llm=llm,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/review", response_model=ReviewResponse)
async def review_pull_request(
    request: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    pr_url = str(request.pr_url)

    try:
        final_review = await review_service.review_pull_request(pr_url)
    except InvalidPullRequestUrlError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GitHubServiceError as exc:
        logger.error("GitHub service error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch data from GitHub.") from exc
    except LLMProviderError as exc:
        logger.error("LLM provider error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="The configured LLM provider failed to produce a review."
        ) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected error while reviewing %s", pr_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred."
        ) from exc

    return ReviewResponse(status="completed", review=final_review)
