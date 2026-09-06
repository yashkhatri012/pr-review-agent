from contextvars import ContextVar
from uuid import uuid4


request_id: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


def create_request_id() -> str:
    return str(uuid4())


def set_request_id(value: str) -> None:
    request_id.set(value)


def get_request_id() -> str:
    return request_id.get() or "unknown"