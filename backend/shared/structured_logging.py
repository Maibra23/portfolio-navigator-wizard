"""
Structured JSON logging with optional request correlation ID.
Set request_id via set_request_id() in middleware; it is included in all log records.
"""
import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone

# Context variable for request ID (set by middleware)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(value: str) -> None:
    """Set the request ID for the current context."""
    request_id_ctx.set(value)


def get_request_id() -> str:
    """Get the request ID for the current context."""
    return request_id_ctx.get()


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            log_obj["request_id"] = rid
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, default=str)


def configure_structured_logging(use_json: bool = None) -> None:
    """
    Configure root logger to use structured JSON format.
    If use_json is None, use JSON when ENVIRONMENT=production.
    """
    if use_json is None:
        use_json = os.getenv("ENVIRONMENT", "development").lower() == "production"
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
    root.addHandler(handler)
