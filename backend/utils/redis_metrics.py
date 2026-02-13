"""
Redis Metrics Collection for Prometheus
Updates Prometheus gauges with Redis statistics
"""

import logging
from typing import Optional
import redis

from shared.metrics import (
    REDIS_MEMORY_USAGE,
    REDIS_KEYS_COUNT,
    REDIS_CONNECTED_CLIENTS,
    REDIS_EVICTED_KEYS,
    REDIS_CACHE_HIT_RATE,
)

logger = logging.getLogger(__name__)


class RedisMetricsCollector:
    """
    Collects Redis statistics and exposes them to Prometheus.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize metrics collector.

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self._last_keyspace_hits = 0
        self._last_keyspace_misses = 0

    def update_metrics(self) -> None:
        """
        Update all Redis metrics for Prometheus.
        Should be called periodically (e.g., every 30 seconds).
        """
        if not self.redis_client:
            logger.warning("Redis client not configured, skipping metrics update")
            return

        try:
            # Get Redis INFO
            info = self.redis_client.info()

            # Memory metrics
            memory_used = info.get('used_memory', 0)
            REDIS_MEMORY_USAGE.set(memory_used)

            # Connected clients
            connected_clients = info.get('connected_clients', 0)
            REDIS_CONNECTED_CLIENTS.set(connected_clients)

            # Evicted keys
            evicted_keys = info.get('evicted_keys', 0)
            REDIS_EVICTED_KEYS.inc(evicted_keys - REDIS_EVICTED_KEYS._value._value)

            # Key count by type
            self._update_key_counts()

            # Cache hit rate
            self._update_cache_hit_rate(info)

            logger.debug(
                f"Redis metrics updated: "
                f"memory={memory_used/1024/1024:.2f}MB, "
                f"clients={connected_clients}, "
                f"evicted={evicted_keys}"
            )

        except redis.RedisError as e:
            logger.error(f"Failed to update Redis metrics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating Redis metrics: {e}")

    def _update_key_counts(self) -> None:
        """
        Update key counts by type for Prometheus.
        """
        try:
            # Count keys by pattern
            key_types = {
                'prices': 'ticker_data:prices:*',
                'sectors': 'ticker_data:sector:*',
                'portfolios': 'portfolio_bucket:*',
                'strategy': 'strategy_portfolios:*',
                'eligible_tickers': 'optimization:eligible_tickers:*',
                'sessions': 'analytics:session:*',
            }

            for key_type, pattern in key_types.items():
                # Use SCAN instead of KEYS for production safety
                count = 0
                cursor = 0

                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )
                    count += len(keys)

                    if cursor == 0:
                        break

                REDIS_KEYS_COUNT.labels(key_type=key_type).set(count)

        except Exception as e:
            logger.debug(f"Failed to update key counts: {e}")

    def _update_cache_hit_rate(self, info: dict) -> None:
        """
        Calculate and update cache hit rate.

        Args:
            info: Redis INFO dict
        """
        try:
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)

            # Calculate incremental hit rate
            hits_delta = keyspace_hits - self._last_keyspace_hits
            misses_delta = keyspace_misses - self._last_keyspace_misses

            total_requests = hits_delta + misses_delta

            if total_requests > 0:
                hit_rate = hits_delta / total_requests
                REDIS_CACHE_HIT_RATE.labels(cache_type="all").set(hit_rate)

            # Update last values
            self._last_keyspace_hits = keyspace_hits
            self._last_keyspace_misses = keyspace_misses

        except Exception as e:
            logger.debug(f"Failed to update cache hit rate: {e}")

    def get_redis_info_summary(self) -> dict:
        """
        Get human-readable Redis info summary.

        Returns:
            Dict with Redis statistics
        """
        if not self.redis_client:
            return {"error": "Redis not configured"}

        try:
            info = self.redis_client.info()

            return {
                "memory": {
                    "used_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2),
                    "peak_mb": round(info.get('used_memory_peak', 0) / 1024 / 1024, 2),
                    "fragmentation_ratio": round(info.get('mem_fragmentation_ratio', 0), 2),
                },
                "clients": {
                    "connected": info.get('connected_clients', 0),
                    "blocked": info.get('blocked_clients', 0),
                },
                "stats": {
                    "total_commands": info.get('total_commands_processed', 0),
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0),
                    "evicted_keys": info.get('evicted_keys', 0),
                    "expired_keys": info.get('expired_keys', 0),
                },
                "persistence": {
                    "rdb_last_save_time": info.get('rdb_last_save_time', 0),
                    "aof_enabled": info.get('aof_enabled', 0),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get Redis info summary: {e}")
            return {"error": str(e)}


# Global metrics collector instance
_metrics_collector: Optional[RedisMetricsCollector] = None


def init_redis_metrics_collector(redis_client: redis.Redis) -> RedisMetricsCollector:
    """
    Initialize global Redis metrics collector.

    Args:
        redis_client: Redis client instance

    Returns:
        RedisMetricsCollector instance
    """
    global _metrics_collector
    _metrics_collector = RedisMetricsCollector(redis_client)
    logger.info("Redis metrics collector initialized")
    return _metrics_collector


def get_redis_metrics_collector() -> Optional[RedisMetricsCollector]:
    """
    Get global Redis metrics collector instance.

    Returns:
        RedisMetricsCollector instance or None if not initialized
    """
    return _metrics_collector


def update_redis_metrics() -> None:
    """
    Update Redis metrics (callable from background task).
    """
    if _metrics_collector:
        _metrics_collector.update_metrics()
    else:
        logger.warning("Redis metrics collector not initialized")


# Example usage
if __name__ == "__main__":
    import pprint

    print("Redis Metrics Collector")
    print("=" * 80)
    print("\nMetrics collected:")
    print("- redis_memory_usage_bytes")
    print("- redis_keys_total{key_type}")
    print("- redis_connected_clients")
    print("- redis_evicted_keys_total")
    print("- redis_cache_hit_rate{cache_type}")
    print("\nUsage:")
    print("1. Initialize: init_redis_metrics_collector(redis_client)")
    print("2. Update periodically: update_redis_metrics()")
    print("3. View in Prometheus: http://localhost:8000/metrics")
    print("=" * 80)
