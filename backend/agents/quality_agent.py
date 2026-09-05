from __future__ import annotations

from agents.base import BaseReviewAgent


class QualityAgent(BaseReviewAgent):
    agent_name = "quality"

    @property
    def focus_description(self) -> str:
        return (
            "- Readability\n"
            "- Duplication\n"
            "- Unnecessary complexity\n"
            "- Poor naming\n"
            "- Maintainability\n"
            "- Opportunities for meaningful simplification\n"
        )
    @property
    def context_keywords(self) -> set[str]:
        """Return keywords for retrieving code quality related context."""

        return {
            "class",
            "function",
            "method",
            "module",
            "import",
            "duplicate",
            "complexity",
            "dependency",
            "interface",
            "abstract",
            "inheritance",
            "type",
            "typing",
            "exception",
            "logging",
            "configuration",
        }

    @property
    def retrieval_query(self) -> str:
        """Return the semantic query used to retrieve code quality context"""

        return (
            "Find repository code relevant to evaluating maintainability and "
            "code quality of this pull request, including abstractions, "
            "dependencies, duplication, complexity, naming, interfaces, "
            "structure, and surrounding implementation patterns."
        )