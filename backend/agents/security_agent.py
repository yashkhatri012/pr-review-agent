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
    @property
    def context_keywords(self) -> set[str]:
        """Return keywords for retrieving security-related repository context """

        return {
            "auth",
            "authentication",
            "authorization",
            "permission",
            "permissions",
            "role",
            "roles",
            "credential",
            "credentials",
            "password",
            "secret",
            "token",
            "jwt",
            "oauth",
            "session",
            "cookie",
            "csrf",
            "cors",
            "sql",
            "query",
            "injection",
            "input",
            "sanitize",
            "validation",
            "escape",
            "encrypt",
            "encryption",
            "decrypt",
            "security",
            "api",
        }
    @property
    def retrieval_query(self) -> str:
        """Return the semantic query used to retrieve security related context"""

        return (
            "Find repository code relevant to detecting security vulnerabilities "
            "introduced by this pull request, including authentication, "
            "authorization, permissions, secrets, input handling, validation, "
            "injection, sensitive data, sessions, tokens, and unsafe APIs."
        )