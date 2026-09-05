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
        """Return keywords for retrieving correctness-related context"""

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
