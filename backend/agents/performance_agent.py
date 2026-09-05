from __future__ import annotations

from agents.base import BaseReviewAgent


class PerformanceAgent(BaseReviewAgent):
    agent_name = "performance"

    @property
    def focus_description(self) -> str:
        return (
            "- Expensive operations\n"
            "- Inefficient loops\n"
            "- N+1 query patterns\n"
            "- Repeated database queries\n"
            "- Repeated API calls\n"
            "- Memory problems\n"
            "- Obvious scalability problems\n"
            "Only report meaningful performance concerns."
        )

    @property
    def context_keywords(self) -> set[str]:
        """Return keywords for retrieving performance related context """

        return {
            "performance",
            "database",
            "query",
            "sql",
            "cache",
            "caching",
            "async",
            "await",
            "thread",
            "threading",
            "process",
            "memory",
            "cpu",
            "loop",
            "batch",
            "pagination",
            "network",
            "request",
            "io",
        }

    @property
    def retrieval_query(self) -> str:
        """Return the semantic query used to retrieve performance related context"""

        return (
            "Find repository code relevant to detecting performance and "
            "scalability problems introduced by this pull request, including "
            "database access, repeated queries, API calls, loops, memory usage, "
            "caching, I/O, concurrency, and expensive operations."
        )