import json
import logging
from datetime import datetime, timezone

from observability.context import get_request_id


class JsonFormatter(logging.Formatter):
    """Format application logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }

        # Include custom observability fields when present.
        for field in (
            "event",
            "duration_seconds",
            "agent",
            "findings",
            "chunks",
            "changed_file_chunks",
            "supporting_chunks",
        ):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data)