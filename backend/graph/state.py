

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from models.agent import AgentContext, AgentReview
from models.client_review import ClientReview
from models.review import FinalReview


class ReviewGraphState(TypedDict, total=False):
    """State shared across the pull request review graph."""

    context: AgentContext

    specialist_reviews: Annotated[
        list[AgentReview],
        operator.add,
    ]

    final_review: FinalReview

    client_review: ClientReview