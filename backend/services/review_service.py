"""Central orchestrator that runs the end to end PR review flow.

Kept intentionally thin: it wires together the GitHub service, RAG
service, specialist agents, and the final validator.
"""
from __future__ import annotations

import asyncio
import logging
import time


from agents.bug_agent import BugAgent
from agents.performance_agent import PerformanceAgent
from agents.quality_agent import QualityAgent
from agents.security_agent import SecurityAgent
from agents.validator_agent import FinalValidatorAgent
from config.settings import Settings
from models.agent import AgentContext, AgentReview
from services.github_service import GitHubService
from services.rag_service import RAGService
from utils.github_url import parse_pull_request_url
from llm.factory import get_llm_provider
from agents.review_writer_agent import ReviewWriterAgent
from models.client_review import ClientReview

logger = logging.getLogger(__name__)


class ReviewService:
    """Coordinates the full PR review pipeline."""

    def __init__(
        self,
        settings: Settings,
        github_service: GitHubService,
        rag_service: RAGService,
    ) -> None:
        self._settings = settings
        self._github = github_service
        self._rag = rag_service

        quality_llm = get_llm_provider(
            provider=settings.quality_llm_provider,
            model=settings.quality_llm_model,
            settings=settings,
        )

        security_llm = get_llm_provider(
            provider=settings.security_llm_provider,
            model=settings.security_llm_model,
            settings=settings,
        )

        bug_llm = get_llm_provider(
            provider=settings.bug_llm_provider,
            model=settings.bug_llm_model,
            settings=settings,
        )

        performance_llm = get_llm_provider(
            provider=settings.performance_llm_provider,
            model=settings.performance_llm_model,
            settings=settings,
        )

        # architecture_llm = get_llm_provider(
        #     provider=settings.architecture_llm_provider,
        #     model=settings.architecture_llm_model,
        #     settings=settings,
        # )

        validator_llm = get_llm_provider(
            provider=settings.validator_llm_provider,
            model=settings.validator_llm_model,
            settings=settings,
        )

        self._specialist_agents = [
            QualityAgent(quality_llm),
            SecurityAgent(security_llm),
            BugAgent(bug_llm),
            PerformanceAgent(performance_llm),
            
        ]
        review_writer_llm = get_llm_provider(
            provider=settings.review_writer_llm_provider,
            model=settings.review_writer_llm_model,
            settings=settings,
        )

        self._validator = FinalValidatorAgent(validator_llm)
        self._review_writer = ReviewWriterAgent(review_writer_llm)

    async def review_pull_request(self, pr_url: str) -> ClientReview:
        start_time = time.monotonic()
        reference = parse_pull_request_url(pr_url)
        logger.info("Starting review for %s/%s#%s", reference.owner, reference.repository, reference.number)

        pull_request = await self._github.fetch_pull_request(reference)
        logger.info("Fetched PR with %d changed files", len(pull_request.changed_files))

        retrieval_result = await self._rag.build_context(pull_request)

        logger.info(
            "Retrieved %d changed-file chunks and %d supporting context chunks",
            len(retrieval_result.changed_file_chunks),
            len(retrieval_result.supporting_chunks),
        )

        context = AgentContext(
            pull_request=pull_request,
            changed_file_context=retrieval_result.changed_file_chunks,
            supporting_context=retrieval_result.supporting_chunks,
        )

        specialist_reviews = await self._run_specialist_agents(context)

        logger.info("Running final validator agent")

        final_review = await self._validator.validate(
            context,
            specialist_reviews,
        )

        logger.info("Writing client-facing review")

        client_review = await self._review_writer.write(
            pull_request,
            final_review,
        )
        duration = time.monotonic() - start_time
        logger.info(
            "Completed review for %s/%s#%s in %.2fs with %d final findings",
            reference.owner,
            reference.repository,
            reference.number,
            duration,
            len(client_review.code_review)
        )
        return client_review

    async def _run_specialist_agents(self, context: AgentContext) -> list[AgentReview]:
        logger.info("Running %d specialist agents concurrently", len(self._specialist_agents))
        results = await asyncio.gather(
            *(agent.review(context) for agent in self._specialist_agents)
        )
        for review in results:
            logger.info("%s agent reported %d findings", review.agent_name, len(review.findings))
        return list(results)
