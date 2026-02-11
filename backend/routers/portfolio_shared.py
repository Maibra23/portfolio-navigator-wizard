"""
Shared state, models, and helpers for portfolio domain routers.
Used by: portfolios, optimization, analytics, export, admin.
"""
from fastapi import Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import math
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.port_analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
portfolio_analytics = PortfolioAnalytics()

# Set by main.py via set_redis_manager()
redis_manager = None


def set_redis_manager(manager):
    """Set Redis manager from main application."""
    global redis_manager
    redis_manager = manager


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
