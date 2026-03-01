"""
Security Middleware
HTTPS enforcement, security headers, and other security-related middleware
"""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.datastructures import Headers
import logging

logger = logging.getLogger(__name__)

def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to all responses
    Protects against XSS, clickjacking, MIME sniffing, and other attacks
    """

    def __init__(self, app, enable_csp: bool = True, enable_hsts: bool = True):
        super().__init__(app)
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts and is_production()

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Forces HTTPS for all future requests (1 year)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content-Security-Policy (CSP)
        # Prevents XSS by controlling allowed content sources
        if self.enable_csp:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # React needs unsafe-inline/eval
                "style-src 'self' 'unsafe-inline'",  # Tailwind/shadcn needs unsafe-inline
                "img-src 'self' data: https:",  # Allow images from HTTPS and data URLs
                "font-src 'self' data:",  # Allow fonts from self and data URLs
                "connect-src 'self' https://query1.finance.yahoo.com",  # External APIs
                "frame-ancestors 'none'",  # Equivalent to X-Frame-Options: DENY
                "base-uri 'self'",  # Prevent base tag injection
                "form-action 'self'",  # Forms can only submit to same origin
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # X-Content-Type-Options
        # Prevents MIME sniffing (browser must respect declared content-type)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevents clickjacking by disallowing embedding in iframes
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        # Legacy XSS protection (mostly replaced by CSP, but still useful for old browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Controls how much referrer information is sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        # Disables unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), "
            "usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
        )

        # X-Permitted-Cross-Domain-Policies
        # Prevents Adobe Flash/PDF from loading data cross-domain
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Cache-Control for sensitive endpoints
        # Prevent caching of sensitive data (applied selectively below)
        if request.url.path.startswith("/api/v1/portfolio/optimization"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect all HTTP requests to HTTPS in production
    Only active when ENVIRONMENT=production
    """

    def __init__(self, app, force_https: bool = None):
        super().__init__(app)
        # Only force HTTPS in production by default
        if force_https is None:
            force_https = is_production()
        self.force_https = force_https

    async def dispatch(self, request: Request, call_next):
        # Skip HTTPS redirect if disabled or already HTTPS
        if not self.force_https or request.url.scheme == "https":
            return await call_next(request)

        # Check for X-Forwarded-Proto header (set by load balancers/proxies)
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        if forwarded_proto == "https":
            # Already HTTPS at the load balancer level
            return await call_next(request)

        # Redirect HTTP to HTTPS
        https_url = request.url.replace(scheme="https")
        logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
        return RedirectResponse(url=str(https_url), status_code=301)  # Permanent redirect

class RateLimitByIPMiddleware(BaseHTTPMiddleware):
    """
    Simple IP-based rate limiting middleware
    Note: This is a backup; primary rate limiting uses SlowAPI with Redis
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # IP -> (timestamp, count)
        self.window_size = 60  # 60 seconds

    async def dispatch(self, request: Request, call_next):
        from time import time

        client_ip = request.client.host
        current_time = time()

        # Clean old entries (older than window_size)
        self.request_counts = {
            ip: (ts, count)
            for ip, (ts, count) in self.request_counts.items()
            if current_time - ts < self.window_size
        }

        # Check current IP
        if client_ip in self.request_counts:
            timestamp, count = self.request_counts[client_ip]
            if current_time - timestamp < self.window_size:
                if count >= self.requests_per_minute:
                    # Rate limit exceeded
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": "Too many requests. Please slow down.",
                            "retry_after": int(self.window_size - (current_time - timestamp))
                        }
                    )
                # Increment count
                self.request_counts[client_ip] = (timestamp, count + 1)
            else:
                # Reset window
                self.request_counts[client_ip] = (current_time, 1)
        else:
            # First request from this IP
            self.request_counts[client_ip] = (current_time, 1)

        return await call_next(request)

def add_security_headers(app, enable_hsts: bool = True, enable_csp: bool = True):
    """
    Convenience function to add all security middleware to a FastAPI app

    Args:
        app: FastAPI application instance
        enable_hsts: Enable HSTS header (HTTPS enforcement)
        enable_csp: Enable Content Security Policy header

    Usage:
        from middleware.security import add_security_headers
        add_security_headers(app)
    """
    # Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_csp=enable_csp,
        enable_hsts=enable_hsts
    )

    # Add HTTPS redirect middleware (production only)
    if is_production():
        app.add_middleware(HTTPSRedirectMiddleware)
        logger.info("✅ HTTPS redirect enabled (production mode)")

        # Add trusted host middleware
        allowed_hosts = os.getenv(
            "ALLOWED_HOSTS",
            "*.railway.app,localhost,127.0.0.1"
        ).split(",")
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[host.strip() for host in allowed_hosts if host.strip()]
        )
        logger.info(f"✅ Trusted hosts configured: {allowed_hosts}")

    logger.info("✅ Security headers middleware enabled")

# Security utilities

def get_client_ip(request: Request) -> str:
    """
    Get client IP address, considering proxies and load balancers

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
        # The first one is the client IP
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (set by Nginx and other proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    return request.client.host

def is_safe_redirect_url(url: str, allowed_domains: list = None) -> bool:
    """
    Check if a redirect URL is safe (prevents open redirect vulnerabilities)

    Args:
        url: URL to validate
        allowed_domains: List of allowed domains for redirection

    Returns:
        True if URL is safe, False otherwise
    """
    from urllib.parse import urlparse

    if not url:
        return False

    # Parse URL
    parsed = urlparse(url)

    # Relative URLs are safe (start with /)
    if not parsed.scheme and not parsed.netloc:
        if url.startswith("/"):
            return True
        return False

    # Check scheme (only allow http/https)
    if parsed.scheme not in ["http", "https"]:
        return False

    # Check domain if allowed_domains specified
    if allowed_domains:
        return parsed.netloc in allowed_domains

    # If no allowed_domains specified, only allow relative URLs
    return False

def sanitize_redirect_url(url: str, fallback: str = "/") -> str:
    """
    Sanitize a redirect URL or return fallback if unsafe

    Args:
        url: URL to sanitize
        fallback: Fallback URL if original is unsafe

    Returns:
        Safe URL or fallback
    """
    if is_safe_redirect_url(url):
        return url
    return fallback
