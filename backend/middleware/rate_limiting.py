"""
Rate Limiting Configuration and Middleware
Implements tiered rate limiting for different endpoint types
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps
import os

# Initialize limiter with Redis backend for distributed rate limiting
def get_redis_url():
    """Get Redis URL for distributed rate limiting"""
    return os.getenv('REDIS_URL', 'redis://localhost:6379')

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_redis_url(),
    strategy="fixed-window",  # or "moving-window" for more accurate limiting
    default_limits=["200/minute"]  # Global default fallback
)

# Tiered rate limits for different endpoint types
class RateLimits:
    """Centralized rate limit definitions"""

    # Search and read-only operations (higher limits)
    SEARCH = "60/minute"  # Ticker search, autocomplete
    READ = "100/minute"   # Get ticker info, cache status

    # Moderate computational operations
    CALCULATE = "30/minute"  # Portfolio metrics calculation
    RECOMMENDATIONS = "20/minute"  # Portfolio recommendations

    # Heavy computational operations (strict limits)
    OPTIMIZE_SINGLE = "10/minute"  # Single optimization
    OPTIMIZE_DUAL = "5/minute"     # Dual optimization
    OPTIMIZE_TRIPLE = "3/minute"   # Triple optimization (most expensive)

    # Data modification operations
    GENERATE = "10/minute"  # Portfolio generation
    EXPORT = "20/minute"    # PDF/CSV export

    # Admin operations (very restrictive)
    ADMIN_WRITE = "5/hour"   # Cache clear, regenerate
    ADMIN_REFRESH = "10/hour"  # Cache warm, refresh operations

    # Background job triggers
    BACKGROUND_JOB = "2/hour"  # Trigger background generation

# Helper decorator for applying rate limits with custom error messages
def rate_limit(limit: str, error_message: str = None):
    """
    Custom rate limit decorator with better error messages

    Args:
        limit: Rate limit string (e.g., "10/minute")
        error_message: Custom error message for rate limit exceeded
    """
    def decorator(func):
        @wraps(func)
        @limiter.limit(limit)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # Store custom error message as function attribute
        if error_message:
            wrapper._rate_limit_message = error_message

        return wrapper
    return decorator

# Rate limit exceeded handler with helpful messages
def rate_limit_exceeded_handler(request, exc):
    """
    Custom handler for rate limit exceeded errors
    Returns helpful error message with retry-after header
    """
    from fastapi.responses import JSONResponse

    # Get endpoint-specific message if available
    endpoint_name = request.url.path.split('/')[-1]

    messages = {
        'optimize': 'Portfolio optimization is resource-intensive. Please wait before retrying.',
        'calculate-metrics': 'Metrics calculation rate limit reached. Please slow down.',
        'search': 'Search rate limit exceeded. Please wait a moment.',
        'recommendations': 'Too many recommendation requests. Please retry in a minute.',
    }

    custom_message = messages.get(endpoint_name, 'Rate limit exceeded. Please try again later.')

    # Calculate retry-after time (seconds)
    retry_after = getattr(exc, 'retry_after', 60)

    return JSONResponse(
        status_code=429,
        headers={
            'Retry-After': str(retry_after),
            'X-RateLimit-Limit': str(getattr(exc, 'limit', 'unknown')),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(getattr(exc, 'reset_time', 0))
        },
        content={
            'error': 'rate_limit_exceeded',
            'message': custom_message,
            'retry_after_seconds': retry_after,
            'suggestion': 'Consider caching results on the client side to reduce API calls.'
        }
    )

# IP-based exemptions for internal services (optional)
def is_internal_ip(request):
    """Check if request is from internal network"""
    client_ip = request.client.host
    internal_ips = os.getenv('INTERNAL_IPS', '127.0.0.1,localhost').split(',')
    return client_ip in internal_ips

# Custom limiter that exempts internal IPs
def smart_limiter(limit: str):
    """
    Rate limiter that exempts internal IPs
    Useful for internal services that shouldn't be rate limited
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if is_internal_ip(request):
                # Skip rate limiting for internal IPs
                return await func(request, *args, **kwargs)
            else:
                # Apply rate limiting
                return await limiter.limit(limit)(func)(request, *args, **kwargs)
        return wrapper
    return decorator
