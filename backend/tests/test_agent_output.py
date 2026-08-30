import pytest

from agents.quality_agent import QualityAgent
from llm.base import BaseLLM, LLMProviderError
from models.agent import AgentContext, AgentReview
from models.finding import ReviewFinding, Severity
from models.pr import PullRequest, PullRequestReference


def _make_context() -> AgentContext:
    reference = PullRequestReference(owner="o", repository="r", number=1, url="https://github.com/o/r/pull/1")
    pr = PullRequest(
        reference=reference,
        title="Refactor helper",
        author="octocat",
        base_branch="main",
        head_branch="feature",
        changed_files=[],
    )
    return AgentContext(pull_request=pr, repository_context=[])


class _FakeSuccessLLM(BaseLLM):
    provider_name = "fake"

    async def generate(self, system_prompt, user_prompt, response_model=None):
        return AgentReview(
            agent_name="quality",
            findings=[
                ReviewFinding(
                    severity=Severity.LOW,
                    file="a.py",
                    title="Long function",
                    description="Function does too much.",
                    evidence="50-line function.",
                    suggestion="Split into smaller functions.",
                )
            ],
        )


class _FakeFailingLLM(BaseLLM):
    provider_name = "fake"

    async def generate(self, system_prompt, user_prompt, response_model=None):
        raise LLMProviderError("boom")


@pytest.mark.asyncio
async def test_agent_tags_source_agent_on_findings():
    agent = QualityAgent(_FakeSuccessLLM())
    result = await agent.review(_make_context())
    assert result.agent_name == "quality"
    assert result.findings[0].source_agents == ["quality"]


@pytest.mark.asyncio
async def test_agent_degrades_gracefully_on_provider_failure():
    agent = QualityAgent(_FakeFailingLLM())
    result = await agent.review(_make_context())
    assert result.agent_name == "quality"
    assert result.findings == []
