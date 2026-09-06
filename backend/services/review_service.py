"""Central orchestrator that runs the end-to-end PR review flow."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from observability.metrics import (
    review_requests_total,
    review_duration_seconds,
)
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
from observability.context import create_request_id, set_request_id

logger = logging.getLogger(__name__)

ProgressCallback = Callable[
    [str, str, str],
    Awaitable[None],
]


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

        self._quality_agent = QualityAgent(
            llm_service.get_llm_for_agent("quality")
        )

        self._security_agent = SecurityAgent(
            llm_service.get_llm_for_agent("security")
        )

        self._bug_agent = BugAgent(
            llm_service.get_llm_for_agent("bug")
        )

        self._performance_agent = PerformanceAgent(
            llm_service.get_llm_for_agent("performance")
        )

        self._validator = FinalValidatorAgent(
            llm_service.get_llm_for_agent("validator")
        )

        self._review_writer = ReviewWriterAgent(
            llm_service.get_llm_for_agent("review_writer")
        )

        self._review_graph = ReviewGraph(
            quality_agent=self._quality_agent,
            security_agent=self._security_agent,
            bug_agent=self._bug_agent,
            performance_agent=self._performance_agent,
            validator=self._validator,
            review_writer=self._review_writer,
        )

    async def review_pull_request(
        self,
        pr_url: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ClientReview:
        """Run the complete pull request review pipeline."""

        start_time = time.monotonic()
        #For different requests, we want to have different request IDs for observability and tracing purposes
        # So we create a new request ID for each review request and set it in the context
        # created here because review_pull_request is the beginning of the operation
        request_id = create_request_id()
        set_request_id(request_id)

        review_requests_total.inc()

        reference = parse_pull_request_url(pr_url)
        
        logger.info(
            "[request_id=%s] Starting review for %s/%s#%s",
             request_id,
            reference.owner,
            reference.repository,
            reference.number,
        )

        github_start = time.monotonic()

        pull_request = await self._github.fetch_pull_request(
            reference
        )

        github_duration = time.monotonic() - github_start

        logger.info(
            "[request_id=%s] GitHub fetch completed in %.2fs",
            request_id,
            github_duration,
        )

        await self._emit_progress(
            progress_callback,
            "fetch_pull_request",
            "completed",
            (
                f"Fetched pull request with "
                f"{len(pull_request.changed_files)} changed files."
            ),
        )

        # Each specialist gets its own semantic retrieval query.
        agent_queries = {
            self._quality_agent.agent_name:
                self._quality_agent.retrieval_query,

            self._security_agent.agent_name:
                self._security_agent.retrieval_query,

            self._bug_agent.agent_name:
                self._bug_agent.retrieval_query,

            self._performance_agent.agent_name:
                self._performance_agent.retrieval_query,
        }

        await self._emit_progress(
            progress_callback,
            "repository_context",
            "running",
            "Retrieving relevant repository context...",
        )
        rag_start = time.monotonic()
        retrieval_result = await self._rag.build_context(
            pull_request,
            agent_queries,
        )
        rag_duration = time.monotonic() - rag_start

        # extra adds structured attributes to the Python LogRecord
        # it doesn't send JSON anywhere

        logger.info(
        "rag_completed",
        extra={
            "event": "rag_completed",
            "duration_seconds": round(rag_duration, 3),
            "changed_file_chunks": len(
                retrieval_result.changed_file_chunks
            ),
            "supporting_chunks": sum(
                len(chunks)
                for chunks in retrieval_result.supporting_chunks.values()
            ),
        },
    )



        supporting_chunk_count = sum(
            len(chunks)
            for chunks in retrieval_result.supporting_chunks.values()
        )

        

        await self._emit_progress(
            progress_callback,
            "repository_context",
            "completed",
            (
                f"Retrieved {supporting_chunk_count} supporting "
                "repository chunks."
            ),
        )

        # Common context is kept for the validator and writer.
        #
        # The validator still needs the changed-file context because its
        # responsibility is to verify specialist findings against the code.
        base_context = AgentContext(
            pull_request=pull_request,
            changed_file_context=retrieval_result.changed_file_chunks,
            supporting_context=[],
        )

        # Each specialist receives only its own supporting RAG results.
        agent_contexts = {
            "quality": AgentContext(
                pull_request=pull_request,
                changed_file_context=retrieval_result.changed_file_chunks,
                supporting_context=retrieval_result.supporting_chunks.get(
                    "quality",
                    [],
                ),
            ),
            "security": AgentContext(
                pull_request=pull_request,
                changed_file_context=retrieval_result.changed_file_chunks,
                supporting_context=retrieval_result.supporting_chunks.get(
                    "security",
                    [],
                ),
            ),
            "bug": AgentContext(
                pull_request=pull_request,
                changed_file_context=retrieval_result.changed_file_chunks,
                supporting_context=retrieval_result.supporting_chunks.get(
                    "bug",
                    [],
                ),
            ),
            "performance": AgentContext(
                pull_request=pull_request,
                changed_file_context=retrieval_result.changed_file_chunks,
                supporting_context=retrieval_result.supporting_chunks.get(
                    "performance",
                    [],
                ),
            ),
        }

        await self._emit_progress(
            progress_callback,
            "specialist_reviews",
            "running",
            "Running specialist review agents in parallel...",
        )

        graph_result = await self._review_graph.run(
            context=base_context,
            agent_contexts=agent_contexts,
            progress_callback=progress_callback,
        )

        client_review = graph_result["client_review"]

        duration = time.monotonic() - start_time

        review_duration_seconds.observe(duration)
        
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

    @staticmethod
    async def _emit_progress(
        callback: ProgressCallback | None,
        stage: str,
        status: str,
        message: str,
    ) -> None:
        """Emit a progress event when a callback is configured"""

        if callback is None:
            return

        await callback(
            stage,
            status,
            message,
        )