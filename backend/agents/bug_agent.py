from __future__ import annotations

from agents.base import BaseReviewAgent


class BugAgent(BaseReviewAgent):
    agent_name = "bug"

    @property
    def focus_description(self) -> str:
        return (
            "- Logic errors\n"
            "- Edge cases\n"
            "- Incorrect conditions\n"
            "- Error handling problems\n"
            "- Null/None handling problems\n"
            "- Regression risks\n"
            "Use the repository context to understand surrounding behavior before reporting."
        )
    @property
    def context_keywords(self) -> set[str]:
        """Return keywords for retrieving correctness related context"""

        return {
            "bug",
            "error",
            "exception",
            "try",
            "except",
            "condition",
            "if",
            "else",
            "return",
            "state",
            "logic",
            "validation",
            "null",
            "none",
            "async",
            "await",
            "transaction",
        }
    @property
    def retrieval_query(self) -> str:
        """Return the semantic query used to retrieve bug related context"""

        return (
            "Find repository code relevant to detecting correctness problems "
            "introduced by this pull request, including control flow, state "
            "changes, edge cases, validation, error handling, null handling, "
            "exceptions, and interactions with existing behavior."
        )