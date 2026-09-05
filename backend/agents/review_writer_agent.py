"""

Converts the validated internal PR review into a clear, humanreadable
review for the API client. This agent must not discover new issues or
change the validator's decisions.
"""
from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from models.client_review import ClientReview
from models.pr import PullRequest
from models.review import FinalReview
logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """
You are the Review Writer Agent.

Your job is to transform the validated internal PR review into a clear,
professional, client-facing code review.

Do not expose internal agent names, raw orchestration details, or
implementation-specific JSON processing.

Respond with ONLY valid JSON matching this exact schema:

{
  "summary": {
    "decision": "approved" | "approved_with_suggestions" | "changes_requested",
    "overview": "<concise overall assessment of the pull request>",
    "key_points": [
      {
        "text": "<a concise key insight>"
      }
    ],
    "total_findings": <integer>
  },
  "code_review": [
    {
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "file": "<file path>",
      "line": <line number or null>,
      "title": "<short title>",
      "review_comment": "<clear human-readable explanation of the issue>",
      "why_it_matters": "<explain the practical impact or risk>",
      "suggested_fix": "<concrete actionable recommendation>"
    }
  ]
}

STRICT RULES:

1. "summary.decision" is required.
2. "summary.overview" is required.
3. "summary.total_findings" is required.
4. Every "summary.key_points" item MUST contain exactly a "text" field.
5. Do NOT use "title" or "description" inside "key_points".
6. Every item in "code_review" must contain all required fields.
7. "summary.total_findings" MUST equal the number of items in "code_review".
8. Do not invent findings that are not present in the validated review.
9. Do not change the severity, file, or line information of validated findings.
10. The decision MUST match the validated review's decision.
11. Return ONLY the JSON object.
"""

class ReviewWriterAgent:
    """Produce the final client facing pull request review"""

    agent_name = "review_writer"

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize the review writer with its injected chat model"""

        self._llm = llm

    async def write(
        self,
        pull_request: PullRequest,
        review: FinalReview,
    ) -> ClientReview:
        """Convert a validated review into a human readable client review"""

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=self._build_user_prompt(
                    pull_request,
                    review,
                )
            ),
        ]

        try:
            response = await self._llm.ainvoke(messages)
        except Exception as exc:
            logger.error(
                "Review writer failed to invoke the LLM: %s",
                exc,
            )
            raise

        if not isinstance(response.content, str):
            raise TypeError(
                "Review writer returned non-text content."
            )

        try:
            result = ClientReview.model_validate_json(
                response.content,
            )
        except Exception as exc:
            logger.error(
                "Review writer returned invalid structured output: %s",
                exc,
            )
            raise ValueError(
                "Review writer returned an invalid response."
            ) from exc

        return result

    def _build_user_prompt(
        self,
        pull_request: PullRequest,
        review: FinalReview,
    ) -> str:
        """Build the input containing only trusted review information"""

        return (
            f"Pull Request: {pull_request.title}\n"
            f"Description: {pull_request.description or '(no description)'}\n"
            f"Author: {pull_request.author}\n"
            f"Base branch: {pull_request.base_branch}\n"
            f"Head branch: {pull_request.head_branch}\n\n"
            "## Validated Review\n"
            f"{review.model_dump_json(indent=2)}"
        )