"""
Prometheus metrics for request latency, count, errors, Redis, and business events.
"""
from prometheus_client import Counter, Histogram, Gauge, REGISTRY

# HTTP Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),  # Custom buckets for API latency
    registry=REGISTRY,
)

# Redis Metrics
REDIS_MEMORY_USAGE = Gauge(
    "redis_memory_usage_bytes",
    "Redis memory usage in bytes",
    registry=REGISTRY,
)

REDIS_KEYS_COUNT = Gauge(
    "redis_keys_total",
    "Total number of keys in Redis",
    ["key_type"],  # prices, portfolios, strategy, etc.
    registry=REGISTRY,
)

REDIS_CACHE_HIT_RATE = Gauge(
    "redis_cache_hit_rate",
    "Redis cache hit rate (0-1)",
    ["cache_type"],
    registry=REGISTRY,
)

REDIS_EVICTED_KEYS = Counter(
    "redis_evicted_keys_total",
    "Total number of keys evicted from Redis",
    registry=REGISTRY,
)

REDIS_CONNECTED_CLIENTS = Gauge(
    "redis_connected_clients",
    "Number of connected Redis clients",
    registry=REGISTRY,
)

# Business Metrics
PORTFOLIO_OPTIMIZATIONS = Counter(
    "portfolio_optimizations_total",
    "Total portfolio optimizations performed",
    ["strategy"],  # equal_weight, max_sharpe, min_variance, efficient_risk
    registry=REGISTRY,
)

PORTFOLIO_OPTIMIZATION_DURATION = Histogram(
    "portfolio_optimization_duration_seconds",
    "Portfolio optimization duration in seconds",
    ["strategy"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

TICKER_SEARCHES = Counter(
    "ticker_searches_total",
    "Total ticker searches performed",
    registry=REGISTRY,
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # prices, portfolios, strategy, eligible_tickers
    registry=REGISTRY,
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=REGISTRY,
)

# Analytics Metrics (Anonymous)
ANONYMOUS_SESSIONS = Gauge(
    "anonymous_sessions_active",
    "Number of active anonymous sessions",
    registry=REGISTRY,
)

PORTFOLIO_TICKERS_COUNT = Histogram(
    "portfolio_tickers_count",
    "Distribution of ticker count in portfolios",
    buckets=(3, 5, 10, 15, 20, 25, 30),
    registry=REGISTRY,
)
