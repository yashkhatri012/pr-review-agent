"""Shared base class for all specialized review agents.

Agents never talk to a provider SDK directly -- they hold a ``BaseLLM``
instance (injected) and call ``generate`` on it. See DECISIONS.md,
decision 006.
"""
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
        self._llm = llm

    @property
    @abstractmethod
    def focus_description(self) -> str:
        """A short description of what this agent should look for."""
        raise NotImplementedError

    def build_system_prompt(self) -> str:
        return (
            f"You are the {self.agent_name} agent, a specialized senior software "
            f"engineer reviewing a GitHub pull request.\n\n"
            f"Your ONLY focus is:\n{self.focus_description}\n\n"
            "Only report issues you are reasonably confident about, supported by "
            "the code shown to you. Do not report generic style preferences or "
            "speculative concerns outside your focus area."
            + _OUTPUT_FORMAT_INSTRUCTIONS
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        pr = context.pull_request
        diff_sections = "\n\n".join(
            f"### File: {f.filename} ({f.status}, +{f.additions}/-{f.deletions})\n"
            f"{f.patch or '(no patch available)'}"
            for f in pr.changed_files
        )
        context_sections = "\n\n".join(
            f"### Repository context: {chunk.file_path} (chunk {chunk.chunk_index})\n"
            f"{chunk.content}"
            for chunk in context.repository_context
        )
        return (
            f"Pull Request: {pr.title}\n"
            f"Description: {pr.description or '(no description)'}\n"
            f"Author: {pr.author}\n"
            f"Base branch: {pr.base_branch} <- Head branch: {pr.head_branch}\n\n"
            f"## Changed files (diffs)\n{diff_sections or '(no changed files)'}\n\n"
            f"## Relevant repository context\n{context_sections or '(no additional context retrieved)'}\n"
        )

    async def review(self, context: AgentContext) -> AgentReview:
        """Run this agent's review. Never raises -- failures degrade to an
        empty finding set so one agent's failure doesn't sink the whole
        review."""
        try:
            result = await self._llm.generate(
                system_prompt=self.build_system_prompt(),
                user_prompt=self.build_user_prompt(context),
                response_model=AgentReview,
            )
        except LLMProviderError as exc:
            logger.error("%s agent failed: %s", self.agent_name, exc)
            return AgentReview(agent_name=self.agent_name, findings=[])

        if not isinstance(result, AgentReview):
            logger.error("%s agent returned an unexpected type: %s", self.agent_name, type(result))
            return AgentReview(agent_name=self.agent_name, findings=[])

        for finding in result.findings:
            if self.agent_name not in finding.source_agents:
                finding.source_agents.append(self.agent_name)

        return result
