


from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from llm.base import BaseLLM, LLMProviderError
from models.agent import AgentContext, AgentReview

logger = logging.getLogger(__name__)

_OUTPUT_FORMAT_INSTRUCTIONS = """
Respond with ONLY a JSON object matching this exact schema, and nothing else
(no markdown fences, no commentary):

{
  "agent_name": "<your agent name>",
  "findings": [
    {
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "file": "<path to the file>",
      "line": <line number or null>,
      "title": "<short title>",
      "description": "<what the issue is>",
      "evidence": "<the specific code/pattern that supports this finding>",
      "suggestion": "<concrete, actionable fix>",
      "source_agents": ["<your agent name>"]
    }
  ]
}

If you find no meaningful issues in your area of focus, return an empty
"findings" list. Do not invent issues to have something to report.
"""


class BaseReviewAgent(ABC):
    """Common behavior for a specialized PR review agent."""

    agent_name: str

    def __init__(self, llm: BaseLLM) -> None:
        """Initialize the agent with its injected LLM implementation."""

        self._llm = llm

    @property
    @abstractmethod
    def focus_description(self) -> str:
        """Return a short description of the agent's review focus."""

        raise NotImplementedError

    def build_system_prompt(self) -> str:
        """Build the system prompt defining the agent's review responsibility."""

        return (
            f"You are the {self.agent_name} agent, a specialized senior software "
            f"engineer reviewing a GitHub pull request.\n\n"
            f"Your ONLY focus is:\n{self.focus_description}\n\n"
            "Only report issues you are reasonably confident about and that are "
            "supported by the code shown to you. Do not report generic style "
            "preferences or speculative concerns outside your focus area.\n\n"
            "The pull request diffs and changed-file context are the primary "
            "review targets. Supporting repository context may be used to "
            "understand dependencies, behavior, and architecture, but do not "
            "report pre-existing issues in unchanged supporting files unless "
            "the pull request directly introduces or causes the problem.\n"
            + _OUTPUT_FORMAT_INSTRUCTIONS
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the pull request and repository context for this agent."""

        pr = context.pull_request

        diff_sections = "\n\n".join(
            f"### File: {changed_file.filename} "
            f"({changed_file.status}, "
            f"+{changed_file.additions}/-{changed_file.deletions})\n"
            f"{changed_file.patch or '(no patch available)'}"
            for changed_file in pr.changed_files
        )

        changed_file_sections = "\n\n".join(
            f"### Changed file: {chunk.file_path} "
            f"(chunk {chunk.chunk_index})\n"
            f"{chunk.content}"
            for chunk in context.changed_file_context
        )

        supporting_sections = "\n\n".join(
            f"### Supporting file: {chunk.file_path} "
            f"(chunk {chunk.chunk_index})\n"
            f"{chunk.content}"
            for chunk in context.supporting_context
        )

        return (
            f"Pull Request: {pr.title}\n"
            f"Description: {pr.description or '(no description)'}\n"
            f"Author: {pr.author}\n"
            f"Base branch: {pr.base_branch} <- "
            f"Head branch: {pr.head_branch}\n\n"
            "## Pull Request Diffs\n"
            "These are the actual changes introduced by the pull request.\n\n"
            f"{diff_sections or '(no changed files)'}\n\n"
            "## Full Changed-File Context\n"
            "These are full contents of files modified by the pull request. "
            "They are the primary code-review target.\n\n"
            f"{changed_file_sections or '(no changed-file context available)'}\n\n"
            "## Supporting Repository Context\n"
            "These chunks come from related repository files that may not have "
            "been modified by this pull request. Use them to understand "
            "dependencies and behavior. Do not report unrelated pre-existing "
            "issues in this supporting code.\n\n"
            f"{supporting_sections or '(no supporting context retrieved)'}\n"
        )

    async def review(self, context: AgentContext) -> AgentReview:
        """Run this agent's review.

        Provider failures degrade to an empty finding set so one agent's
        failure does not sink the entire review.
        """

        try:
            result = await self._llm.generate(
                system_prompt=self.build_system_prompt(),
                user_prompt=self.build_user_prompt(context),
                response_model=AgentReview,
            )
        except LLMProviderError as exc:
            logger.error(
                "%s agent failed: %s",
                self.agent_name,
                exc,
            )
            return AgentReview(
                agent_name=self.agent_name,
                findings=[],
            )

        if not isinstance(result, AgentReview):
            logger.error(
                "%s agent returned an unexpected type: %s",
                self.agent_name,
                type(result),
            )
            return AgentReview(
                agent_name=self.agent_name,
                findings=[],
            )

        for finding in result.findings:
            if self.agent_name not in finding.source_agents:
                finding.source_agents.append(self.agent_name)

        return result

