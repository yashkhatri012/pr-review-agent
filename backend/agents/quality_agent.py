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
