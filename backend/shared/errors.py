"""
Consistent error response schema and helpers.
"""
import os
import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response body."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a standard error response dict."""
    return {
        "code": code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }


def is_production() -> bool:
    """Return True if running in production (do not expose internal errors)."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def safe_error_message(error: Exception, generic_message: str = "An error occurred") -> str:
    """
    Return a safe error message for HTTP responses.

    In production: Returns the generic message to avoid leaking internal details.
    In development: Returns the actual error message for debugging.

    Args:
        error: The exception that occurred
        generic_message: Message to show in production

    Returns:
        Safe error message string
    """
    if is_production():
        return generic_message
    return str(error)


def generate_request_id() -> str:
    """Generate a unique request ID for error correlation."""
    return str(uuid.uuid4())[:8]


def safe_error_detail(
    error: Exception,
    generic_message: str = "An error occurred",
    include_request_id: bool = True
) -> str:
    """
    Build a safe error detail string with optional request ID.

    Args:
        error: The exception that occurred
        generic_message: Message to show in production
        include_request_id: Whether to include a request ID for correlation

    Returns:
        Safe error detail string with optional request ID
    """
    message = safe_error_message(error, generic_message)
    if include_request_id:
        request_id = generate_request_id()
        return f"{message} (ref: {request_id})"
    return message
