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
    """State shared across the pull request review graph."""

    context: AgentContext

    specialist_reviews: Annotated[
        list[AgentReview],
        operator.add,
    ]

    final_review: FinalReview

    client_review: ClientReview

    progress_callback: ProgressCallback