"""Base implementation for specialized pull request review agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

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
    """Common behavior for specialized pull request review agents."""

    agent_name: str

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize the agent with its configured LangChain chat model."""

        self._llm = llm

    @property
    @abstractmethod
    def focus_description(self) -> str:
        """Return a short description of the agent's review focus."""

        raise NotImplementedError

    @property
    @abstractmethod
    def retrieval_query(self) -> str:
        """Return the semantic query used to retrieve supporting context."""

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
            "The pull request diff is the primary review target. Supporting "
            "repository context may be used to understand dependencies, behavior, "
            "and architecture, but do not report pre-existing issues in unchanged "
            "supporting files unless the pull request directly introduces or "
            "causes the problem.\n\n"
            + _OUTPUT_FORMAT_INSTRUCTIONS
        )

    def build_user_prompt(
        self,
        context: AgentContext,
    ) -> str:
        """Build the pull request and agent-specific repository context."""

        pr = context.pull_request

        diff_sections = "\n\n".join(
            f"### File: {changed_file.filename} "
            f"({changed_file.status}, "
            f"+{changed_file.additions}/-{changed_file.deletions})\n"
            f"{changed_file.patch or '(no patch available)'}"
            for changed_file in pr.changed_files
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
            "These are the actual changes introduced by the pull request. "
            "Review these changes as the primary source of evidence.\n\n"
            f"{diff_sections or '(no changed files)'}\n\n"
            "## Supporting Repository Context\n"
            "These chunks were retrieved specifically for your area of review. "
            "Use them to understand dependencies, behavior, architecture, and "
            "surrounding implementation patterns.\n\n"
            f"{supporting_sections or '(no supporting context retrieved)'}\n"
        )

    async def review(
        self,
        context: AgentContext,
    ) -> AgentReview:
        """Run this agent's review.

        LLM failures or invalid responses degrade to an empty finding set so
        one specialist failure does not sink the entire pull request review.
        """

        messages = [
            SystemMessage(content=self.build_system_prompt()),
            HumanMessage(content=self.build_user_prompt(context)),
        ]

        try:
            response = await self._llm.ainvoke(messages)
        except Exception:
            logger.exception(
                "%s agent failed to invoke the LLM.",
                self.agent_name,
            )
            return self._empty_review()

        if not isinstance(response.content, str):
            logger.error(
                "%s agent returned non-text content.",
                self.agent_name,
            )
            return self._empty_review()

        try:
            result = AgentReview.model_validate_json(
                self._strip_code_fences(response.content)
            )
        except Exception:
            logger.exception(
                "%s agent returned an invalid structured response.",
                self.agent_name,
            )
            return self._empty_review()

        result.agent_name = self.agent_name

        for finding in result.findings:
            if self.agent_name not in finding.source_agents:
                finding.source_agents.append(self.agent_name)

        return result

    def _empty_review(self) -> AgentReview:
        """Return an empty review for this specialist agent."""

        return AgentReview(
            agent_name=self.agent_name,
            findings=[],
        )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove optional Markdown code fences from an LLM response."""

        stripped = text.strip()

        if not stripped.startswith("```"):
            return stripped

        lines = stripped.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()