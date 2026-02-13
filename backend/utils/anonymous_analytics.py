"""
Backend Metrics Tracking for Prometheus
Lightweight event tracking for performance monitoring only.

Frontend analytics handled by Plausible Analytics.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request

# Import Prometheus metrics
from shared.metrics import (
    PORTFOLIO_OPTIMIZATIONS,
    PORTFOLIO_OPTIMIZATION_DURATION,
    TICKER_SEARCHES,
    CACHE_HITS,
    CACHE_MISSES,
    PORTFOLIO_TICKERS_COUNT,
)

logger = logging.getLogger(__name__)


class BackendMetrics:
    """
    Backend metrics tracking for Prometheus only.

    This class tracks backend-specific metrics like:
    - Portfolio optimization counts and duration
    - Ticker search counts
    - Cache hit/miss rates

    Frontend analytics (page views, user behavior, traffic sources)
    are handled by Plausible Analytics in the frontend.
    """

    def __init__(self, redis_client=None):
        """
        Initialize backend metrics tracker.

        Args:
            redis_client: Optional Redis client (not used, kept for compatibility)
        """
        self.redis_client = redis_client

    def track_optimization(
        self,
        strategy: str,
        ticker_count: int,
        processing_time_seconds: float,
        success: bool = True
    ) -> None:
        """
        Track portfolio optimization in Prometheus.

        Args:
            strategy: Optimization strategy used
            ticker_count: Number of tickers in portfolio
            processing_time_seconds: Processing time in seconds
            success: Whether optimization succeeded
        """
        try:
            if success:
                # Increment optimization counter
                PORTFOLIO_OPTIMIZATIONS.labels(strategy=strategy).inc()

                # Record processing duration
                PORTFOLIO_OPTIMIZATION_DURATION.labels(strategy=strategy).observe(
                    processing_time_seconds
                )

                # Record ticker count distribution
                PORTFOLIO_TICKERS_COUNT.observe(ticker_count)

                logger.debug(
                    f"Metrics: portfolio_optimized | strategy={strategy} | "
                    f"tickers={ticker_count} | duration={processing_time_seconds:.2f}s"
                )

        except Exception as e:
            logger.error(f"Failed to track optimization metrics: {e}")

    def track_search(self, results_count: int) -> None:
        """
        Track ticker search in Prometheus.

        Args:
            results_count: Number of results returned
        """
        try:
            TICKER_SEARCHES.inc()
            logger.debug(f"Metrics: ticker_searched | results={results_count}")
        except Exception as e:
            logger.error(f"Failed to track search metrics: {e}")

    def track_cache_hit(self, cache_type: str) -> None:
        """
        Track cache hit in Prometheus.

        Args:
            cache_type: Type of cache (prices, portfolios, strategy, etc.)
        """
        try:
            CACHE_HITS.labels(cache_type=cache_type).inc()
        except Exception as e:
            logger.error(f"Failed to track cache hit: {e}")

    def track_cache_miss(self, cache_type: str) -> None:
        """
        Track cache miss in Prometheus.

        Args:
            cache_type: Type of cache (prices, portfolios, strategy, etc.)
        """
        try:
            CACHE_MISSES.labels(cache_type=cache_type).inc()
        except Exception as e:
            logger.error(f"Failed to track cache miss: {e}")


# Global metrics tracker instance
_metrics_tracker: Optional[BackendMetrics] = None


def init_backend_metrics(redis_client=None) -> BackendMetrics:
    """
    Initialize global backend metrics tracker.

    Args:
        redis_client: Optional Redis client (not used, kept for compatibility)

    Returns:
        BackendMetrics instance
    """
    global _metrics_tracker
    _metrics_tracker = BackendMetrics(redis_client)
    logger.info("Backend metrics tracker initialized")
    return _metrics_tracker


def get_backend_metrics() -> Optional[BackendMetrics]:
    """
    Get global backend metrics tracker instance.

    Returns:
        BackendMetrics instance or None if not initialized
    """
    return _metrics_tracker


# Convenience functions for quick metric tracking
def track_optimization(strategy: str, ticker_count: int, processing_time: float):
    """Quick function to track optimization metrics"""
    if _metrics_tracker:
        _metrics_tracker.track_optimization(strategy, ticker_count, processing_time)


def track_search(results_count: int):
    """Quick function to track search metrics"""
    if _metrics_tracker:
        _metrics_tracker.track_search(results_count)


def track_cache_hit(cache_type: str):
    """Quick function to track cache hit"""
    if _metrics_tracker:
        _metrics_tracker.track_cache_hit(cache_type)


def track_cache_miss(cache_type: str):
    """Quick function to track cache miss"""
    if _metrics_tracker:
        _metrics_tracker.track_cache_miss(cache_type)


# Example usage
if __name__ == "__main__":
    print("Backend Metrics Tracker (Prometheus)")
    print("=" * 80)
    print("\nPurpose:")
    print("- Lightweight backend metrics for Prometheus")
    print("- Portfolio optimization tracking")
    print("- Search and cache performance metrics")
    print("\nFrontend Analytics:")
    print("- Use Plausible Analytics for page views, user behavior, traffic sources")
    print("- Add Plausible script to frontend index.html")
    print("- Track custom events with window.plausible()")
    print("\nPrometheus Metrics Exposed:")
    print("- portfolio_optimizations_total{strategy}")
    print("- portfolio_optimization_duration_seconds{strategy}")
    print("- ticker_searches_total")
    print("- cache_hits_total{cache_type}")
    print("- cache_misses_total{cache_type}")
    print("=" * 80)
