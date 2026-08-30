"""Central orchestrator that runs the end-to-end PR review flow.

Kept intentionally thin: it wires together the GitHub service, RAG
service, specialist agents, and the final validator. See DECISIONS.md,
decision 015.
"""
from __future__ import annotations

import asyncio
import logging
import time

from agents.architecture_agent import ArchitectureAgent
from agents.base import BaseReviewAgent
from agents.bug_agent import BugAgent
from agents.performance_agent import PerformanceAgent
from agents.quality_agent import QualityAgent
from agents.security_agent import SecurityAgent
from agents.validator_agent import FinalValidatorAgent
from config.settings import Settings
from llm.base import BaseLLM
from models.agent import AgentContext, AgentReview
from models.review import FinalReview
from services.github_service import GitHubService
from services.rag_service import RAGService
from utils.github_url import parse_pull_request_url

logger = logging.getLogger(__name__)


class ReviewService:
    """Coordinates the full PR review pipeline."""

    def __init__(
        self,
        settings: Settings,
        github_service: GitHubService,
        rag_service: RAGService,
        llm: BaseLLM,
    ) -> None:
        self._settings = settings
        self._github = github_service
        self._rag = rag_service
        self._specialist_agents: list[BaseReviewAgent] = [
            QualityAgent(llm),
            SecurityAgent(llm),
            BugAgent(llm),
            PerformanceAgent(llm),
            ArchitectureAgent(llm),
        ]
        self._validator = FinalValidatorAgent(llm)

    async def review_pull_request(self, pr_url: str) -> FinalReview:
        start_time = time.monotonic()
        reference = parse_pull_request_url(pr_url)
        logger.info("Starting review for %s/%s#%s", reference.owner, reference.repository, reference.number)

        pull_request = await self._github.fetch_pull_request(reference)
        logger.info("Fetched PR with %d changed files", len(pull_request.changed_files))

        retrieval_result = await self._rag.build_context(pull_request)
        logger.info("Retrieved %d repository context chunks", len(retrieval_result.chunks))

        context = AgentContext(
            pull_request=pull_request,
            repository_context=retrieval_result.chunks,
        )

        specialist_reviews = await self._run_specialist_agents(context)

        logger.info("Running final validator agent")
        final_review = await self._validator.validate(context, specialist_reviews)

        duration = time.monotonic() - start_time
        logger.info(
            "Completed review for %s/%s#%s in %.2fs with %d final findings",
            reference.owner,
            reference.repository,
            reference.number,
            duration,
            len(final_review.findings),
        )
        return final_review

    async def _run_specialist_agents(self, context: AgentContext) -> list[AgentReview]:
        logger.info("Running %d specialist agents concurrently", len(self._specialist_agents))
        results = await asyncio.gather(
            *(agent.review(context) for agent in self._specialist_agents)
        )
        for review in results:
            logger.info("%s agent reported %d findings", review.agent_name, len(review.findings))
        return list(results)
