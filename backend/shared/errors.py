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
