from __future__ import annotations

from agents.base import BaseReviewAgent


class SecurityAgent(BaseReviewAgent):
    agent_name = "security"

    @property
    def focus_description(self) -> str:
        return (
            "- Authentication issues\n"
            "- Authorization issues\n"
            "- Injection vulnerabilities\n"
            "- Unsafe input handling\n"
            "- Hardcoded secrets\n"
            "- Sensitive data exposure\n"
            "- Unsafe APIs\n"
            "- Other dangerous patterns\n"
            "Only report realistic issues supported by the code. Avoid speculative findings."
        )
