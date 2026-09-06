import logging

from observability.context import get_request_id


class RequestIdFilter(logging.Filter):
    """Add the current request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True