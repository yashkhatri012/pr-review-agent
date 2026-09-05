"""State definitions for the pull request review graph."""

from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, TypedDict

from models.agent import AgentContext, AgentReview
from models.client_review import ClientReview
from models.review import FinalReview


ProgressCallback = Callable[
    [str, str, str],
    Awaitable[None],
]


class ReviewGraphState(TypedDict, total=False):
    """State shared across the pull request review graph"""

    # Common context used by the validator and review writer
    context: AgentContext

    # Each specialist receives its own agent-specific context
    agent_contexts: dict[str, AgentContext]

    # Callback used to stream progress events to the client
    progress_callback: ProgressCallback | None

    # Specialist results are accumulated as the parallel nodes complete
    specialist_reviews: Annotated[
        list[AgentReview],
        operator.add,
    ]

    final_review: FinalReview

    client_review: ClientReview