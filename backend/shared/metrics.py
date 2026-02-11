"""
Prometheus metrics for request latency, count, and errors.
"""
from prometheus_client import Counter, Histogram, REGISTRY

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
    registry=REGISTRY,
)
