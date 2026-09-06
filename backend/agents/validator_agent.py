"""Final validator for specialist pull request review findings. It
checks specialist findings against the pull request evidence, removes weak
or duplicate findings, and produces the final review decision.
"""

from __future__ import annotations

import json
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from utils.structured_output import _strip_code_fences
from models.agent import AgentContext, AgentReview
from models.finding import ReviewFinding, Severity
from models.review import FinalReview, ReviewDecision, ReviewSummary


logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """
You are the Final Validator Agent, a senior software engineer responsible
for producing the definitive review of a pull request.

You receive:
1. The pull request diffs.
2. Full context for files changed by the pull request.
3. Supporting context retrieved from related repository files.
4. Raw findings reported by specialist agents.

Specialist agents may hallucinate, duplicate each other, misjudge severity,
or report issues that are not actually introduced by the pull request.

Evidence hierarchy:

- Pull request diffs show the actual changes introduced by the PR.
- Full changed-file context provides additional context for modified files.
- Supporting repository context helps explain dependencies, behavior, and
  architecture, but may contain unchanged pre-existing code.

Your job:

1. Verify every finding against the actual PR diff, changed-file context,
   and supporting repository context.

2. Remove findings that are unsupported, speculative, or unrelated to the
   changes introduced by the pull request.

3. Do not preserve findings about pre-existing problems in unchanged
   supporting files unless the pull request directly introduces, triggers,
   or makes that problem reachable.

4. Remove duplicate findings.

5. Merge findings that describe the same underlying issue, combining their
   "source_agents".

6. Prioritize serious issues by ordering findings from most severe to least
   severe.

7. Ensure every remaining finding has specific evidence and a concrete,
   actionable suggestion.

8. Decide the overall review decision:
   - "changes_requested" if any critical or high severity finding remains.
   - "approved_with_suggestions" if only medium, low, or info findings
     remain.
   - "approved" if no findings remain.

9. Write a short, factual, human-readable summary of the review in one to
   three sentences.

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
      "evidence": "<specific code or behavior supporting the finding>",
      "suggestion": "<concrete, actionable fix>",
      "source_agents": ["<agent1>", "<agent2>"]
    }
  ]
}
"""


class FinalValidatorAgent:
    """Validate specialist findings and produce the final PR review"""

    agent_name = "final_validator"

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize the validator with its injected chat model"""

        self._llm = llm

    def _build_user_prompt(
        self,
        context: AgentContext,
        specialist_reviews: list[AgentReview],
    ) -> str:
        """Build the evidence and specialist findings prompt"""

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

        findings_sections = "\n\n".join(
            f"#### {review.agent_name} agent findings\n"
            f"{review.model_dump_json(indent=2)}"
            for review in specialist_reviews
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
            "These are full contents of files modified by the pull request.\n\n"
            f"{changed_file_sections or '(no changed-file context available)'}\n\n"
            "## Supporting Repository Context\n"
            "These chunks come from related repository files that may not have "
            "been changed by the pull request. Use them to understand behavior "
            "and dependencies, but do not preserve unrelated pre-existing "
            "issues in these files.\n\n"
            f"{supporting_sections or '(no supporting context retrieved)'}\n\n"
            "## Raw Specialist Findings\n"
            "Treat these as hypotheses to verify, not as established facts.\n\n"
            f"{findings_sections or '(no findings reported)'}\n"
        )

    async def validate(
        self,
        context: AgentContext,
        specialist_reviews: list[AgentReview],
    ) -> FinalReview:
        """Produce the final validated pull request review.

        If the validator model fails or returns invalid data, the method
        falls back to a deterministic merge of specialist findings so the
        review pipeline still returns useful output.
        """

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=self._build_user_prompt(
                    context,
                    specialist_reviews,
                )
            ),
        ]

        try:
            response = await self._llm.ainvoke(messages)

            if not isinstance(response.content, str):
                raise TypeError(
                    "Validator returned non-text content."
                )

            data = json.loads(
                _strip_code_fences(response.content),
            )

            summary = ReviewSummary.model_validate(
                data["summary"],
            )

            findings = [
                ReviewFinding.model_validate(finding)
                for finding in data.get("findings", []) # same as data["findings"] but safer, if "findings" key is missing returns []
            ]

        except (
            KeyError,
            ValueError,
            ValidationError,
            TypeError,
        ) as exc:
            logger.error(
                "Final validator failed; falling back to specialist findings: %s",
                exc,
            )

            findings, summary = _fallback_merge(
                specialist_reviews,
            )

        return FinalReview(
            pull_request=context.pull_request.reference,
            summary=summary,
            findings=findings,
        )



def _fallback_merge(
    specialist_reviews: list[AgentReview],
) -> tuple[list[ReviewFinding], ReviewSummary]:
    """Return specialist findings when final validation is unavailable

    This fallback intentionally performs only deterministic aggregation and
    severity ordering. It does not claim that the findings were independently
    validated.
    """

    all_findings = [
        finding
        for review in specialist_reviews
        for finding in review.findings
    ]

    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }

    all_findings.sort(
        key=lambda finding: severity_order.get(
            finding.severity,
            99,
        )
    )

    has_serious_finding = any(
        finding.severity in (
            Severity.CRITICAL,
            Severity.HIGH,
        )
        for finding in all_findings
    )

    if not all_findings:
        decision = ReviewDecision.APPROVED
        summary_text = (
            "No findings were reported by the specialist review agents."
        )

    elif has_serious_finding:
        decision = ReviewDecision.CHANGES_REQUESTED
        summary_text = (
            "The specialist review agents reported findings that should be "
            "addressed before merging. Final LLM validation was unavailable."
        )

    else:
        decision = ReviewDecision.APPROVED_WITH_SUGGESTIONS
        summary_text = (
            "The specialist review agents reported suggestions. "
            "Final LLM validation was unavailable."
        )

    summary = ReviewSummary(
        decision=decision,
        summary=summary_text,
        total_findings=len(all_findings),
    )

    return all_findings, summary