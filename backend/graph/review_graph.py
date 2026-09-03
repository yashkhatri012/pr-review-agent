"""LangGraph orchestration for the pull request review pipeline."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.base import BaseReviewAgent
from agents.review_writer_agent import ReviewWriterAgent
from agents.validator_agent import FinalValidatorAgent
from graph.state import ReviewGraphState
from models.agent import AgentContext, AgentReview
from models.client_review import ClientReview
from models.review import FinalReview
logger = logging.getLogger(__name__)


class ReviewGraph:
    """Coordinate the parallel specialist and final review stages."""

    def __init__(
        self,
        quality_agent: BaseReviewAgent,
        security_agent: BaseReviewAgent,
        bug_agent: BaseReviewAgent,
        performance_agent: BaseReviewAgent,
        validator: FinalValidatorAgent,
        review_writer: ReviewWriterAgent,
    ) -> None:
        """Initialize the agents used by the review graph."""

        self._quality_agent = quality_agent
        self._security_agent = security_agent
        self._bug_agent = bug_agent
        self._performance_agent = performance_agent
        self._validator = validator
        self._review_writer = review_writer

        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build and compile the pull request review graph."""

        builder = StateGraph(ReviewGraphState)

        #  nodes
        builder.add_node(
            "quality_review",
            self._run_quality_agent,
        )
        builder.add_node(
            "security_review",
            self._run_security_agent,
        )
        builder.add_node(
            "bug_review",
            self._run_bug_agent,
        )
        builder.add_node(
            "performance_review",
            self._run_performance_agent,
        )

        # Final processing nodes.
        builder.add_node(
            "validate_review",
            self._validate_review,
        )
        builder.add_node(
            "write_review",
            self._write_review,
        )

       
        builder.add_edge(
            START,
            "quality_review",
        )
        builder.add_edge(
            START,
            "security_review",
        )
        builder.add_edge(
            START,
            "bug_review",
        )
        builder.add_edge(
            START,
            "performance_review",
        )

       
        builder.add_edge(
            "quality_review",
            "validate_review",
        )
        builder.add_edge(
            "security_review",
            "validate_review",
        )
        builder.add_edge(
            "bug_review",
            "validate_review",
        )
        builder.add_edge(
            "performance_review",
            "validate_review",
        )

        builder.add_edge(
            "validate_review",
            "write_review",
        )

        builder.add_edge(
            "write_review",
            END,
        )

        return builder.compile()

    async def run(
        self,
        context: AgentContext,
    ) -> ReviewGraphState:
        """Execute the pull request review graph."""

        return await self._graph.ainvoke(
            {
                "context": context,
                "specialist_reviews": [],
            }
        )

    async def _run_quality_agent(
        self,
        state: ReviewGraphState,
    ) -> dict[str, list[AgentReview]]:
        """Run the quality specialist agent."""

        return await self._run_specialist(
            self._quality_agent,
            state,
        )

    async def _run_security_agent(
        self,
        state: ReviewGraphState,
    ) -> dict[str, list[AgentReview]]:
        """Run the security specialist agent."""

        return await self._run_specialist(
            self._security_agent,
            state,
        )

    async def _run_bug_agent(
        self,
        state: ReviewGraphState,
    ) -> dict[str, list[AgentReview]]:
        """Run the bug specialist agent."""

        return await self._run_specialist(
            self._bug_agent,
            state,
        )

    async def _run_performance_agent(
        self,
        state: ReviewGraphState,
    ) -> dict[str, list[AgentReview]]:
        """Run the performance specialist agent."""

        return await self._run_specialist(
            self._performance_agent,
            state,
        )

    async def _run_specialist(
        self,
        agent: BaseReviewAgent,
        state: ReviewGraphState,
    ) -> dict[str, list[AgentReview]]:
        """Run a specialist and return its review for state aggregation."""

        logger.info(
            "Running %s specialist agent",
            agent.agent_name,
        )

        review = await agent.review(
            state["context"],
        )

        logger.info(
            "%s agent reported %d findings",
            review.agent_name,
            len(review.findings),
        )

        return {
            "specialist_reviews": [review],
        }

    async def _validate_review(
        self,
        state: ReviewGraphState,
    ) -> dict[str, FinalReview]:
        """Validate and consolidate all specialist findings."""

        logger.info(
            "Running final validator with %d specialist reviews",
            len(state["specialist_reviews"]),
        )

        final_review = await self._validator.validate(
            state["context"],
            state["specialist_reviews"],
        )

        return {
            "final_review": final_review,
        }

    async def _write_review(
        self,
        state: ReviewGraphState,
    ) -> dict[str, ClientReview]:
        """Write the final client-facing review."""

        logger.info("Writing client-facing review")

        client_review = await self._review_writer.write(
            state["context"].pull_request,
            state["final_review"],
        )

        return {
            "client_review": client_review,
        }