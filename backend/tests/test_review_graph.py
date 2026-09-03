
"""Tests for the LangGraph pull request review pipeline."""

from __future__ import annotations

import pytest
import asyncio
import time
from graph.review_graph import ReviewGraph

class SlowFakeSpecialistAgent:
    """Fake specialist agent with an artificial execution delay."""

    def __init__(
        self,
        agent_name: str,
        delay: float = 0.5,
    ) -> None:
        """Initialize the slow fake agent."""

        self.agent_name = agent_name
        self.delay = delay

    async def review(self, context):
        """Wait for the configured delay before returning a review."""

        await asyncio.sleep(self.delay)

        return FakeAgentReview(
            agent_name=self.agent_name,
            findings=[],
        )

    @pytest.mark.asyncio
    async def test_specialist_agents_run_in_parallel() -> None:
        """Verify independent specialist nodes execute concurrently."""

        delay = 0.5

        graph = ReviewGraph(
            quality_agent=SlowFakeSpecialistAgent("quality", delay),
            security_agent=SlowFakeSpecialistAgent("security", delay),
            bug_agent=SlowFakeSpecialistAgent("bug", delay),
            performance_agent=SlowFakeSpecialistAgent("performance", delay),
            validator=FakeValidator(),
            review_writer=FakeReviewWriter(),
        )

        context = FakeContext()

        start_time = time.perf_counter()

        await graph.run(context)

        elapsed_time = time.perf_counter() - start_time

        assert elapsed_time < 1.0
    
class FakeSpecialistAgent:
    """Fake specialist agent used to test graph orchestration."""

    def __init__(self, agent_name: str) -> None:
        """Initialize the fake agent."""

        self.agent_name = agent_name
        self.was_called = False

    async def review(self, context):
        """Record execution and return a deterministic review."""

        self.was_called = True

        return FakeAgentReview(
            agent_name=self.agent_name,
            findings=[],
        )


class FakeAgentReview:
    """Minimal review object used by fake specialist agents."""

    def __init__(
        self,
        agent_name: str,
        findings: list,
    ) -> None:
        """Initialize a fake agent review."""

        self.agent_name = agent_name
        self.findings = findings


class FakeValidator:
    """Fake validator used to test graph orchestration."""

    def __init__(self) -> None:
        """Initialize the fake validator."""

        self.was_called = False
        self.received_reviews = []

    async def validate(
        self,
        context,
        specialist_reviews,
    ):
        """Record the received reviews and return a fake final review."""

        self.was_called = True
        self.received_reviews = specialist_reviews

        return FakeFinalReview()


class FakeFinalReview:
    """Minimal final review object used by the fake validator."""

    def __init__(self) -> None:
        """Initialize a fake final review."""

        self.findings = []


class FakeReviewWriter:
    """Fake review writer used to test graph orchestration."""

    def __init__(self) -> None:
        """Initialize the fake review writer."""

        self.was_called = False
        self.received_pull_request = None
        self.received_final_review = None

    async def write(
        self,
        pull_request,
        final_review,
    ):
        """Record inputs and return a fake client review."""

        self.was_called = True
        self.received_pull_request = pull_request
        self.received_final_review = final_review

        return FakeClientReview()


class FakeClientReview:
    """Minimal client review returned by the fake review writer."""

    pass


class FakeContext:
    """Minimal agent context used for graph tests."""

    def __init__(self) -> None:
        """Initialize fake pull request context."""

        self.pull_request = object()


@pytest.mark.asyncio
async def test_review_graph_runs_all_specialist_agents() -> None:
    """Verify that all specialist agents execute."""

    quality_agent = FakeSpecialistAgent("quality")
    security_agent = FakeSpecialistAgent("security")
    bug_agent = FakeSpecialistAgent("bug")
    performance_agent = FakeSpecialistAgent("performance")

    validator = FakeValidator()
    review_writer = FakeReviewWriter()

    graph = ReviewGraph(
        quality_agent=quality_agent,
        security_agent=security_agent,
        bug_agent=bug_agent,
        performance_agent=performance_agent,
        validator=validator,
        review_writer=review_writer,
    )

    context = FakeContext()

    await graph.run(context)

    assert quality_agent.was_called
    assert security_agent.was_called
    assert bug_agent.was_called
    assert performance_agent.was_called


@pytest.mark.asyncio
async def test_review_graph_passes_all_specialist_reviews_to_validator() -> None:
    """Verify that all specialist results reach the validator."""

    quality_agent = FakeSpecialistAgent("quality")
    security_agent = FakeSpecialistAgent("security")
    bug_agent = FakeSpecialistAgent("bug")
    performance_agent = FakeSpecialistAgent("performance")

    validator = FakeValidator()
    review_writer = FakeReviewWriter()

    graph = ReviewGraph(
        quality_agent=quality_agent,
        security_agent=security_agent,
        bug_agent=bug_agent,
        performance_agent=performance_agent,
        validator=validator,
        review_writer=review_writer,
    )

    context = FakeContext()

    await graph.run(context)

    received_agent_names = {
        review.agent_name
        for review in validator.received_reviews
    }

    assert received_agent_names == {
        "quality",
        "security",
        "bug",
        "performance",
    }


@pytest.mark.asyncio
async def test_review_graph_runs_validator() -> None:
    """Verify that the validator runs after specialist reviews."""

    quality_agent = FakeSpecialistAgent("quality")
    security_agent = FakeSpecialistAgent("security")
    bug_agent = FakeSpecialistAgent("bug")
    performance_agent = FakeSpecialistAgent("performance")

    validator = FakeValidator()
    review_writer = FakeReviewWriter()

    graph = ReviewGraph(
        quality_agent=quality_agent,
        security_agent=security_agent,
        bug_agent=bug_agent,
        performance_agent=performance_agent,
        validator=validator,
        review_writer=review_writer,
    )

    context = FakeContext()

    await graph.run(context)

    assert validator.was_called


@pytest.mark.asyncio
async def test_review_graph_runs_review_writer() -> None:
    """Verify that the review writer runs after validation."""

    quality_agent = FakeSpecialistAgent("quality")
    security_agent = FakeSpecialistAgent("security")
    bug_agent = FakeSpecialistAgent("bug")
    performance_agent = FakeSpecialistAgent("performance")

    validator = FakeValidator()
    review_writer = FakeReviewWriter()

    graph = ReviewGraph(
        quality_agent=quality_agent,
        security_agent=security_agent,
        bug_agent=bug_agent,
        performance_agent=performance_agent,
        validator=validator,
        review_writer=review_writer,
    )

    context = FakeContext()

    await graph.run(context)

    assert review_writer.was_called


@pytest.mark.asyncio
async def test_review_graph_returns_final_client_review() -> None:
    """Verify that the completed graph returns a client review."""

    quality_agent = FakeSpecialistAgent("quality")
    security_agent = FakeSpecialistAgent("security")
    bug_agent = FakeSpecialistAgent("bug")
    performance_agent = FakeSpecialistAgent("performance")

    validator = FakeValidator()
    review_writer = FakeReviewWriter()

    graph = ReviewGraph(
        quality_agent=quality_agent,
        security_agent=security_agent,
        bug_agent=bug_agent,
        performance_agent=performance_agent,
        validator=validator,
        review_writer=review_writer,
    )

    context = FakeContext()

    result = await graph.run(context)

    assert "specialist_reviews" in result
    assert "final_review" in result
    assert "client_review" in result

    assert len(result["specialist_reviews"]) == 4
    assert result["final_review"] is not None
    assert result["client_review"] is not None

@pytest.mark.asyncio
async def test_validator_waits_for_all_specialists() -> None:
    """Verify the validator runs only after every specialist completes."""

    events: list[str] = []

    class TrackingAgent(SlowFakeSpecialistAgent):
        """Specialist agent that records when it completes."""

        async def review(self, context):
            await asyncio.sleep(self.delay)
            events.append(f"{self.agent_name}_completed")

            return FakeAgentReview(
                agent_name=self.agent_name,
                findings=[],
            )

    class TrackingValidator(FakeValidator):
        """Validator that records when validation begins."""

        async def validate(
            self,
            context,
            specialist_reviews,
        ):
            events.append("validator_started")

            return await super().validate(
                context,
                specialist_reviews,
            )

    delay = 0.1

    graph = ReviewGraph(
        quality_agent=TrackingAgent("quality", delay),
        security_agent=TrackingAgent("security", delay),
        bug_agent=TrackingAgent("bug", delay),
        performance_agent=TrackingAgent("performance", delay),
        validator=TrackingValidator(),
        review_writer=FakeReviewWriter(),
    )

    await graph.run(FakeContext())

    validator_index = events.index("validator_started")

    for agent_name in (
        "quality",
        "security",
        "bug",
        "performance",
    ):
        completion_index = events.index(
            f"{agent_name}_completed"
        )

        assert completion_index < validator_index


@pytest.mark.asyncio
async def test_review_writer_waits_for_validator() -> None:
    """Verify the review writer runs only after validation completes."""

    events: list[str] = []

    class TrackingValidator(FakeValidator):
        """Validator that records completion."""

        async def validate(
            self,
            context,
            specialist_reviews,
        ):
            events.append("validator_started")

            result = await super().validate(
                context,
                specialist_reviews,
            )

            events.append("validator_completed")

            return result

    class TrackingReviewWriter(FakeReviewWriter):
        """Review writer that records when writing begins."""

        async def write(
            self,
            pull_request,
            final_review,
        ):
            events.append("writer_started")

            return await super().write(
                pull_request,
                final_review,
            )

    graph = ReviewGraph(
        quality_agent=FakeSpecialistAgent("quality"),
        security_agent=FakeSpecialistAgent("security"),
        bug_agent=FakeSpecialistAgent("bug"),
        performance_agent=FakeSpecialistAgent("performance"),
        validator=TrackingValidator(),
        review_writer=TrackingReviewWriter(),
    )

    await graph.run(FakeContext())

    assert events.index(
        "validator_completed"
    ) < events.index(
        "writer_started"
    )