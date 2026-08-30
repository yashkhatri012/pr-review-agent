"""Final Validator Agent.

Acts as a senior engineer reviewing the output of the specialist agents:
verifies findings against the actual PR, drops false positives and
duplicates, merges related findings, prioritizes serious issues, and
produces the final, validated review. See DECISIONS.md, decision 014.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from llm.base import BaseLLM, LLMProviderError
from models.agent import AgentContext, AgentReview
from models.finding import ReviewFinding, Severity
from models.review import FinalReview, ReviewDecision, ReviewSummary

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are the Final Validator Agent, a senior software engineer responsible
for producing the definitive review of a pull request.

You receive the pull request, its diffs, retrieved repository context, and
the raw findings reported by several specialist agents (quality, security,
bug, performance, architecture). Those specialists sometimes hallucinate,
duplicate each other, or report unsupported issues.

Your job:
1. Verify every finding against the actual PR diff and repository context.
2. Remove false positives and findings that are not actually supported.
3. Remove duplicate findings.
4. Merge findings that describe the same underlying issue, combining their
   "source_agents".
5. Prioritize serious issues (order findings by severity, most severe first).
6. Ensure every remaining finding's suggestion is concrete and actionable.
7. Decide an overall review decision:
   - "changes_requested" if any critical or high severity finding remains,
   - "approved_with_suggestions" if only medium/low/info findings remain,
   - "approved" if no findings remain.
8. Write a short (1-3 sentence) human-readable summary of the review.

Respond with ONLY a JSON object matching this exact schema, and nothing else
(no markdown fences, no commentary):

{
  "summary": {
    "decision": "approved" | "approved_with_suggestions" | "changes_requested",
    "summary": "<short human readable summary>",
    "total_findings": <integer, number of findings in the findings list>
  },
  "findings": [
    {
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "file": "<path>",
      "line": <line number or null>,
      "title": "<short title>",
      "description": "<description>",
      "evidence": "<supporting evidence>",
      "suggestion": "<concrete, actionable fix>",
      "source_agents": ["<agent1>", "<agent2>"]
    }
  ]
}
"""


class FinalValidatorAgent:
    agent_name = "final_validator"

    def __init__(self, llm: BaseLLM) -> None:
        self._llm = llm

    def _build_user_prompt(self, context: AgentContext, specialist_reviews: list[AgentReview]) -> str:
        pr = context.pull_request
        diff_sections = "\n\n".join(
            f"### File: {f.filename} ({f.status}, +{f.additions}/-{f.deletions})\n"
            f"{f.patch or '(no patch available)'}"
            for f in pr.changed_files
        )
        context_sections = "\n\n".join(
            f"### Repository context: {chunk.file_path} (chunk {chunk.chunk_index})\n{chunk.content}"
            for chunk in context.repository_context
        )
        findings_sections = "\n\n".join(
            f"#### {review.agent_name} agent findings\n{review.model_dump_json(indent=2)}"
            for review in specialist_reviews
        )

        return (
            f"Pull Request: {pr.title}\n"
            f"Description: {pr.description or '(no description)'}\n"
            f"Author: {pr.author}\n"
            f"Base branch: {pr.base_branch} <- Head branch: {pr.head_branch}\n\n"
            f"## Changed files (diffs)\n{diff_sections or '(no changed files)'}\n\n"
            f"## Relevant repository context\n{context_sections or '(no additional context)'}\n\n"
            f"## Raw specialist findings\n{findings_sections or '(no findings reported)'}\n"
        )

    async def validate(
        self,
        context: AgentContext,
        specialist_reviews: list[AgentReview],
    ) -> FinalReview:
        """Produce the final, validated review."""
        try:
            raw = await self._llm.generate(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=self._build_user_prompt(context, specialist_reviews),
                response_model=None,
            )
            data = json.loads(_strip_code_fences(raw))
            summary = ReviewSummary.model_validate(data["summary"])
            findings = [ReviewFinding.model_validate(f) for f in data.get("findings", [])]
        except (LLMProviderError, KeyError, ValueError, ValidationError) as exc:
            logger.error("Final validator failed, falling back to raw findings: %s", exc)
            findings, summary = _fallback_merge(specialist_reviews)

        return FinalReview(
            pull_request=context.pull_request.reference,
            summary=summary,
            findings=findings,
        )


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _fallback_merge(specialist_reviews: list[AgentReview]):
    """If the validator LLM call fails, fall back to a naive merge of all
    specialist findings rather than losing the review entirely."""
    all_findings = [f for review in specialist_reviews for f in review.findings]
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }
    all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

    has_serious = any(f.severity in (Severity.CRITICAL, Severity.HIGH) for f in all_findings)
    if not all_findings:
        decision = ReviewDecision.APPROVED
        summary_text = "No issues were found by the review agents."
    elif has_serious:
        decision = ReviewDecision.CHANGES_REQUESTED
        summary_text = "The review agents identified issues that should be addressed before merging."
    else:
        decision = ReviewDecision.APPROVED_WITH_SUGGESTIONS
        summary_text = "The review agents identified minor suggestions."

    summary = ReviewSummary(decision=decision, summary=summary_text, total_findings=len(all_findings))
    return all_findings, summary
