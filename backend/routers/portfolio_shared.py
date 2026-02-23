"""
Shared state, models, and helpers for portfolio domain routers.
Used by: portfolios, optimization, analytics, export, admin.
"""
import hmac
import os
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import math
from slowapi import Limiter

from middleware.security import get_client_ip
from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.port_analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_client_ip)
portfolio_analytics = PortfolioAnalytics()

# Set by main.py via set_redis_manager()
redis_manager = None


def set_redis_manager(manager):
    """Set Redis manager from main application."""
    global redis_manager
    redis_manager = manager


# ---------------------------------------------------------------------------
# Admin authentication dependency
# ---------------------------------------------------------------------------

_ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


def require_admin_key(request: Request) -> None:
    """Require X-Admin-Key or Authorization Bearer to match ADMIN_API_KEY.

    Fail-closed: if ADMIN_API_KEY is not set, all admin requests are rejected
    (prevents open admin access on misconfigured deployments).
    Uses constant-time comparison to prevent timing-oracle attacks.
    """
    if not _ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    key_header = request.headers.get("X-Admin-Key", "").strip()
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        key_header = key_header or auth[7:].strip()
    if not key_header or not hmac.compare_digest(key_header, _ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Admin authentication required")


def _sanitize_number(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Return a JSON-safe float (no NaN/Inf)."""
    try:
        if value is None:
            return default
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Request/response models used across routers
# ---------------------------------------------------------------------------

class WarmTickersRequest(BaseModel):
    """Request body for warm-tickers endpoint."""
    tickers: List[str]
