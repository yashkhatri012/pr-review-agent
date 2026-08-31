from __future__ import annotations

from agents.base import BaseReviewAgent


class ArchitectureAgent(BaseReviewAgent):
    agent_name = "architecture"

    @property
    def focus_description(self) -> str:
        return (
            "- Consistency with existing project patterns\n"
            "- Separation of responsibilities\n"
            "- Coupling between components\n"
            "- Overall architecture consistency\n"
            "- Repository conventions\n"
            "- Long term maintainability\n"
            "Avoid subjective recommendations unless there is a clear architectural concern."
        )
