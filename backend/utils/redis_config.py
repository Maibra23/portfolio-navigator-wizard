"""
Redis Configuration and TTL Management with Jitter
Prevents cache stampede by distributing expiration times
"""

import random
import logging
from typing import Any, Optional
import json

logger = logging.getLogger(__name__)


class RedisConfig:
    """
    Redis configuration constants and TTL strategies
    """

    # TTL values in seconds (base values, jitter will be applied)
    TTL_PRICES = 86400  # 1 day for ticker prices
    TTL_SECTORS = 604800  # 7 days for sector mappings
    TTL_PORTFOLIOS = 259200  # 3 days for cached portfolios
    TTL_STRATEGY = 172800  # 2 days for strategy portfolios
    TTL_ELIGIBLE_TICKERS = 604800  # 7 days for eligible tickers cache
    TTL_SEARCH_RESULTS = 3600  # 1 hour for search results
    TTL_USER_SESSION = 1800  # 30 minutes for anonymous user sessions

    # Connection pool settings (for 4 Uvicorn workers)
    MAX_CONNECTIONS_PER_WORKER = 50
    TOTAL_WORKERS = 4
    TOTAL_MAX_CONNECTIONS = MAX_CONNECTIONS_PER_WORKER * TOTAL_WORKERS  # 200

    # Jitter percentage (default ±10%)
    DEFAULT_JITTER = 0.1

    @staticmethod
    def apply_jitter(ttl_seconds: int, jitter: float = DEFAULT_JITTER) -> int:
        """
        Apply jitter to TTL to prevent cache stampede.

        Cache stampede occurs when many cache entries expire simultaneously,
        causing a thundering herd of requests to backend services.

        Example:
            Without jitter: 100 portfolios expire at exactly 00:00:00
            With ±10% jitter: Expirations spread over 43.2 minutes (4.8 hours for daily cache)

        Args:
            ttl_seconds: Base TTL in seconds
            jitter: Jitter percentage (0.1 = ±10%)

        Returns:
            TTL with jitter applied
        """
        if ttl_seconds <= 0:
            return ttl_seconds

        # Calculate jitter bounds: base_ttl * (1 ± jitter)
        jitter_factor = random.uniform(1.0 - jitter, 1.0 + jitter)
        jittered_ttl = int(ttl_seconds * jitter_factor)

        return max(1, jittered_ttl)  # Ensure TTL is at least 1 second

    @staticmethod
    def get_ttl_for_data_type(data_type: str, apply_jitter_flag: bool = True) -> int:
        """
        Get TTL for specific data type with optional jitter.

        Args:
            data_type: Type of data ('prices', 'sectors', 'portfolios', etc.)
            apply_jitter_flag: Whether to apply jitter (default: True)

        Returns:
            TTL in seconds
        """
        ttl_mapping = {
            'prices': RedisConfig.TTL_PRICES,
            'sectors': RedisConfig.TTL_SECTORS,
            'portfolios': RedisConfig.TTL_PORTFOLIOS,
            'strategy': RedisConfig.TTL_STRATEGY,
            'eligible_tickers': RedisConfig.TTL_ELIGIBLE_TICKERS,
            'search': RedisConfig.TTL_SEARCH_RESULTS,
            'session': RedisConfig.TTL_USER_SESSION,
        }

        base_ttl = ttl_mapping.get(data_type, 3600)  # Default 1 hour

        if apply_jitter_flag:
            return RedisConfig.apply_jitter(base_ttl)
        else:
            return base_ttl


def set_with_jittered_ttl(
    redis_client,
    key: str,
    value: Any,
    data_type: str = 'prices',
    custom_ttl: Optional[int] = None,
    jitter: float = RedisConfig.DEFAULT_JITTER
) -> int:
    """
    Set Redis key with jittered TTL to prevent cache stampede.

    Args:
        redis_client: Redis client instance
        key: Redis key
        value: Value to store (will be JSON encoded if dict/list)
        data_type: Data type for default TTL ('prices', 'sectors', etc.)
        custom_ttl: Custom TTL in seconds (overrides data_type)
        jitter: Jitter percentage (default: 0.1 = ±10%)

    Returns:
        Actual TTL set (with jitter applied)

    Example:
        >>> set_with_jittered_ttl(redis, 'ticker:AAPL', price_data, 'prices')
        >>> # Sets TTL to 86400 ± 10% = random value between 77,760 and 95,040 seconds
    """
    try:
        # Determine base TTL
        if custom_ttl is not None:
            base_ttl = custom_ttl
        else:
            base_ttl = RedisConfig.get_ttl_for_data_type(data_type, apply_jitter_flag=False)

        # Apply jitter
        actual_ttl = RedisConfig.apply_jitter(base_ttl, jitter)

        # Serialize value if needed
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        # Set with TTL
        redis_client.setex(key, actual_ttl, value)

        logger.debug(
            f"Set Redis key '{key}' with jittered TTL: {actual_ttl}s "
            f"(base: {base_ttl}s, jitter: ±{jitter*100}%)"
        )

        return actual_ttl

    except Exception as e:
        logger.error(f"Failed to set Redis key '{key}' with jittered TTL: {e}")
        raise


def get_redis_connection_pool_config() -> dict:
    """
    Get Redis connection pool configuration for production.

    Based on Railway deployment with 4 Uvicorn workers.

    Returns:
        Dict with connection pool configuration
    """
    return {
        'max_connections': RedisConfig.MAX_CONNECTIONS_PER_WORKER,
        'socket_connect_timeout': 5,  # 5 seconds
        'socket_timeout': 5,  # 5 seconds
        'retry_on_timeout': True,
        'health_check_interval': 30,  # Check connection health every 30 seconds
        'decode_responses': False,  # Keep as bytes for flexibility
    }


def get_redis_config_summary() -> dict:
    """
    Get summary of Redis configuration for monitoring/debugging.

    Returns:
        Dict with configuration summary
    """
    return {
        'connection_pool': {
            'max_connections_per_worker': RedisConfig.MAX_CONNECTIONS_PER_WORKER,
            'total_workers': RedisConfig.TOTAL_WORKERS,
            'total_max_connections': RedisConfig.TOTAL_MAX_CONNECTIONS,
        },
        'ttl_seconds': {
            'prices': f"{RedisConfig.TTL_PRICES}s (1 day)",
            'sectors': f"{RedisConfig.TTL_SECTORS}s (7 days)",
            'portfolios': f"{RedisConfig.TTL_PORTFOLIOS}s (3 days)",
            'strategy': f"{RedisConfig.TTL_STRATEGY}s (2 days)",
            'eligible_tickers': f"{RedisConfig.TTL_ELIGIBLE_TICKERS}s (7 days)",
            'search_results': f"{RedisConfig.TTL_SEARCH_RESULTS}s (1 hour)",
            'user_session': f"{RedisConfig.TTL_USER_SESSION}s (30 minutes)",
        },
        'jitter': {
            'percentage': f"±{RedisConfig.DEFAULT_JITTER * 100}%",
            'example_prices_range': f"{int(RedisConfig.TTL_PRICES * 0.9)}s - {int(RedisConfig.TTL_PRICES * 1.1)}s",
        },
        'benefits': {
            'cache_stampede_prevention': 'TTL jitter distributes expirations over time',
            'connection_pooling': 'Prevents "too many connections" errors',
            'predictable_costs': 'Memory limits prevent runaway Redis costs',
        }
    }


# Example usage
if __name__ == "__main__":
    # Print configuration summary
    import pprint

    config = get_redis_config_summary()
    print("Redis Configuration Summary:")
    print("=" * 80)
    pprint.pprint(config, width=80)
    print("=" * 80)

    # Demonstrate jitter
    print("\nTTL Jitter Demonstration (100 samples):")
    print("=" * 80)

    base_ttl = 86400  # 1 day
    ttls = [RedisConfig.apply_jitter(base_ttl) for _ in range(100)]

    print(f"Base TTL: {base_ttl}s (1 day)")
    print(f"Min TTL: {min(ttls)}s ({min(ttls)/3600:.2f} hours)")
    print(f"Max TTL: {max(ttls)}s ({max(ttls)/3600:.2f} hours)")
    print(f"Avg TTL: {sum(ttls)/len(ttls):.0f}s ({sum(ttls)/len(ttls)/3600:.2f} hours)")
    print(f"Spread: {max(ttls) - min(ttls)}s ({(max(ttls) - min(ttls))/3600:.2f} hours)")
    print("=" * 80)

    print("\nBenefit: Instead of 100 caches expiring at the same time,")
    print(f"they expire over a {(max(ttls) - min(ttls))/3600:.2f} hour window,")
    print("preventing cache stampede and reducing backend load spikes.")
