"""Central orchestrator that runs the end to end PR review flow.

"""

from __future__ import annotations


import logging
import time
from agents.bug_agent import BugAgent
from agents.performance_agent import PerformanceAgent
from agents.quality_agent import QualityAgent
from agents.review_writer_agent import ReviewWriterAgent
from agents.security_agent import SecurityAgent
from agents.validator_agent import FinalValidatorAgent
from config.settings import Settings
from graph.review_graph import ReviewGraph
from llm.service import LLMService
from models.agent import AgentContext
from models.client_review import ClientReview
from services.github_service import GitHubService
from services.rag_service import RAGService
from utils.github_url import parse_pull_request_url

logger = logging.getLogger(__name__)


class ReviewService:
    """Prepare pull request context and execute the review graph."""

    def __init__(
        self,
        settings: Settings,
        github_service: GitHubService,
        rag_service: RAGService,
        llm_service: LLMService,
    ) -> None:
        """Initialize the services and agents used by the review pipeline."""

        self._settings = settings
        self._github = github_service
        self._rag = rag_service

        self._review_graph = ReviewGraph(
        quality_agent=QualityAgent(
            llm_service.get_llm_for_agent("quality")
        ),
        security_agent=SecurityAgent(
            llm_service.get_llm_for_agent("security")
        ),
        bug_agent=BugAgent(
            llm_service.get_llm_for_agent("bug")
        ),
        performance_agent=PerformanceAgent(
            llm_service.get_llm_for_agent("performance")
        ),
        validator=FinalValidatorAgent(
            llm_service.get_llm_for_agent("validator")
        ),
        review_writer=ReviewWriterAgent(
            llm_service.get_llm_for_agent("review_writer")
        ),
    )

    async def review_pull_request(
        self,
        pr_url: str,
    ) -> ClientReview:
        """Run the complete pull request review pipeline."""

        start_time = time.monotonic()

        reference = parse_pull_request_url(pr_url)

        logger.info(
            "Starting review for %s/%s#%s",
            reference.owner,
            reference.repository,
            reference.number,
        )

        pull_request = await self._github.fetch_pull_request(
            reference
        )

        logger.info(
            "Fetched PR with %d changed files",
            len(pull_request.changed_files),
        )

        retrieval_result = await self._rag.build_context(
            pull_request
        )

        logger.info(
            "Retrieved %d changed-file chunks and "
            "%d supporting context chunks",
            len(retrieval_result.changed_file_chunks),
            len(retrieval_result.supporting_chunks),
        )

        context = AgentContext(
            pull_request=pull_request,
            changed_file_context=retrieval_result.changed_file_chunks,
            supporting_context=retrieval_result.supporting_chunks,
        )

        graph_result = await self._review_graph.run(
            context
        )

        client_review = graph_result["client_review"]

        duration = time.monotonic() - start_time

        logger.info(
            "Completed review for %s/%s#%s in %.2fs with "
            "%d final findings",
            reference.owner,
            reference.repository,
            reference.number,
            duration,
            len(client_review.code_review),
        )

        return client_review