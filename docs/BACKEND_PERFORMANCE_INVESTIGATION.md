# Backend Performance, Health Check, and Mobile UX Investigation

This document provides a technical investigation of backend performance issues, health check failures, and mobile UX improvements for the Portfolio Navigator Wizard application.

---

## Table of Contents

1. [Backend Health Check Failures](#1-backend-health-check-failures)
2. [Backend Lag During Rapid User Interaction](#2-backend-lag-during-rapid-user-interaction)
3. [Continuous Health Checks](#3-continuous-health-checks)
4. [Mobile UX Improvement for Graphs](#4-mobile-ux-improvement-for-graphs)

---

## 1. Backend Health Check Failures

### Observed Behavior

```
Health check servicecheck-00-http-8080 on port 8080 has failed.
Your app is not responding properly.
Services exposed on ports [80, 443] will have intermittent failures until the health check passes.
```

### Current Configuration

```toml
# fly.toml
[[http_service.checks]]
  grace_period = "30s"
  interval     = "30s"
  method       = "GET"
  path         = "/healthz"
  timeout      = "5s"
```

| Setting | Value | Meaning |
|---------|-------|---------|
| `grace_period` | 30s | Time after startup before checks begin |
| `interval` | 30s | Time between health checks |
| `timeout` | 5s | Maximum time for health check response |
| `path` | `/healthz` | Endpoint being checked |

### Root Cause Analysis

The health check failure occurs because the `/healthz` endpoint performs **multiple Redis operations** that can exceed the 5-second timeout:

```python
# backend/main.py (lines 1215-1226)
async def _health_response():
    if redis_manager:
        # This calls get_all_portfolio_buckets_status() which:
        # - Iterates 5 risk profiles
        # - For each: get_portfolio_metadata() + get_portfolio_count()
        # - Each involves multiple Redis SCAN/GET operations
        portfolio_status = redis_manager.get_all_portfolio_buckets_status()
        available_buckets = sum(1 for status in portfolio_status.values() if status.get("available"))
```

**Why it fails:**

1. **Redis Network Latency**: Redis Cloud is in `eu-north-1` (Stockholm), backend is in `ams` (Amsterdam). Round-trip latency: ~20-50ms per Redis call.

2. **Health Check Overhead**: Each health check performs:
   - 5 risk profiles x (1 metadata GET + 1 SCAN for count) = ~10+ Redis operations
   - Total latency: 10 x 50ms = ~500ms minimum
   - Under load, this can spike to 2-5 seconds

3. **Timeout Boundary**: The 5-second timeout is tight when:
   - Redis is under load from user requests
   - Network latency spikes
   - The shared-cpu-1x VM is context-switching

### Is the Backend Actually Failing?

**No.** The backend is NOT failing — it's responding slowly. The health check timeout is too aggressive for the current implementation.

Evidence:
- Direct `curl` to `/healthz` returns successfully (verified: 0.7-1.5s)
- API endpoints work normally
- Health checks recover after transient spikes

### Solutions

#### Solution 1: Simplify Health Check (Recommended)

Create a lightweight `/healthz` that only checks Redis connectivity:

```python
# Lightweight health check - NO portfolio status enumeration
@app.get("/healthz")
async def healthz():
    """Lightweight health check for load balancers."""
    try:
        if redis_first_data_service and redis_first_data_service.redis_client:
            redis_first_data_service.redis_client.ping()
            return {"status": "healthy"}
        return {"status": "degraded", "reason": "redis_unavailable"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

Keep the detailed status on a separate endpoint:
```python
@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with portfolio status."""
    return await _health_response()  # Current implementation
```

#### Solution 2: Increase Timeout

```toml
# fly.toml
[[http_service.checks]]
  grace_period = "30s"
  interval     = "30s"
  method       = "GET"
  path         = "/healthz"
  timeout      = "10s"  # Increased from 5s
```

#### Solution 3: Cache Health Status

```python
# Cache portfolio status for 30 seconds
_health_cache = {"status": None, "timestamp": 0}
HEALTH_CACHE_TTL = 30

async def _health_response():
    import time
    now = time.time()

    if _health_cache["status"] and (now - _health_cache["timestamp"]) < HEALTH_CACHE_TTL:
        return _health_cache["status"]

    # ... compute status ...
    _health_cache["status"] = status
    _health_cache["timestamp"] = now
    return status
```

### Recommendation

**Implement Solution 1** (lightweight health check). This is the industry standard approach:
- `/healthz` or `/health/live`: Fast, checks only essential connectivity
- `/health/ready`: Checks if app can serve traffic
- `/health/detailed`: Full diagnostic information

---

## 2. Backend Lag During Rapid User Interaction

### Observed Behavior

When users click or navigate rapidly:
- Backend responses arrive noticeably slower
- UI feels "laggy" despite frontend being responsive
- Multiple API calls queue up

### Root Cause Analysis

#### 2.1 Concurrency Configuration

```toml
# fly.toml
[http_service.concurrency]
  type       = "requests"
  soft_limit = 50
  hard_limit = 100
```

| Limit | Value | Effect |
|-------|-------|--------|
| `soft_limit` | 50 | Start queueing requests after 50 concurrent |
| `hard_limit` | 100 | Reject requests after 100 concurrent |

**Issue**: These limits are generous, but the single `shared-cpu-1x` VM with 1GB RAM can become CPU-bound under rapid requests.

#### 2.2 Rate Limiting

```python
# middleware/rate_limiting.py
default_limits=["200/minute"]  # Global default

class RateLimits:
    SEARCH = "60/minute"
    READ = "100/minute"
    CALCULATE = "30/minute"
    OPTIMIZE_SINGLE = "10/minute"
```

**Issue**: Rate limiting is per-IP, so a single user rapidly clicking can hit limits:
- 60 searches/minute = 1 per second max
- If user clicks faster, requests queue

#### 2.3 Single Worker Architecture

```python
# ASGI server configuration (uvicorn)
# Default: 1 worker process on Fly.io

# Each request is handled sequentially if blocking operations exist
```

**Issue**: The backend uses FastAPI (async), but some operations are synchronous:
- Redis operations (redis-py is sync by default)
- Heavy calculations (numpy/scipy)
- JSON serialization of large responses

#### 2.4 Redis as Bottleneck

```python
# Multiple Redis calls per request:
# - get_ticker_data(): 4 keys (prices, meta, metrics, sector)
# - get_portfolio(): 1 GET + deserialization
# - Each with ~20-50ms latency to Redis Cloud
```

### Why "Always-On" Doesn't Solve This

Having both frontend and backend "always running" prevents **cold starts**, but doesn't address:

1. **Single CPU**: `shared-cpu-1x` means one virtual CPU, shared with other tenants
2. **Single Process**: One worker handles all requests
3. **Network Latency**: Redis is remote, not local
4. **Synchronous Blocking**: Redis calls block the event loop

### Solutions

#### Solution 1: Enable Async Redis (Recommended)

Use `redis.asyncio` for non-blocking Redis operations:

```python
# backend/utils/redis_first_data_service.py
from redis.asyncio import Redis as AsyncRedis

class RedisFirstDataService:
    def __init__(self):
        self._async_client = AsyncRedis.from_url(redis_url)

    async def get_ticker_data_async(self, ticker: str) -> dict:
        # Non-blocking Redis calls
        prices, meta, metrics, sector = await asyncio.gather(
            self._async_client.get(f"ticker_data:prices:{ticker}"),
            self._async_client.get(f"ticker_data:meta:{ticker}"),
            self._async_client.get(f"ticker_data:metrics:{ticker}"),
            self._async_client.get(f"ticker_data:sector:{ticker}"),
        )
        return {...}
```

**Impact**: Concurrent requests don't block each other waiting for Redis.

#### Solution 2: Request Debouncing (Frontend)

Prevent rapid-fire API calls:

```typescript
// frontend/src/hooks/useDebounce.ts
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

// Usage in search
const debouncedQuery = useDebounce(searchQuery, 300);
useEffect(() => {
  if (debouncedQuery) fetchResults(debouncedQuery);
}, [debouncedQuery]);
```

#### Solution 3: Connection Pooling Optimization

```python
# Increase connection pool for parallel requests
self.redis_client = redis.from_url(
    redis_url,
    max_connections=100,  # Up from 50
    socket_connect_timeout=3,
    socket_timeout=3,
)
```

#### Solution 4: Response Caching

Add short-term caching for frequently-accessed data:

```python
from functools import lru_cache
from cachetools import TTLCache

# In-memory cache for hot paths
_ticker_cache = TTLCache(maxsize=1000, ttl=60)

async def get_ticker_data(ticker: str):
    if ticker in _ticker_cache:
        return _ticker_cache[ticker]
    data = await fetch_from_redis(ticker)
    _ticker_cache[ticker] = data
    return data
```

#### Solution 5: Upgrade VM Size

```toml
# fly.toml
[[vm]]
  memory = '2gb'       # Up from 1gb
  cpu_kind = 'shared'
  cpus = 2             # Up from 1
```

**Cost**: ~$10-15/month additional

### Recommendation

1. **Immediate**: Implement frontend debouncing (300ms delay)
2. **Short-term**: Switch to async Redis operations
3. **Medium-term**: Add in-memory caching for hot paths
4. **If needed**: Upgrade to 2 CPUs

---

## 3. Continuous Health Checks

### Observed Behavior

Logs show constant health check requests every 30 seconds.

### Explanation

This is **normal and expected behavior** for cloud deployments.

#### Who Performs Health Checks?

| Source | Purpose | Frequency |
|--------|---------|-----------|
| **Fly.io Proxy** | Route traffic to healthy machines | Every 30s (configured) |
| **Load Balancer** | Remove unhealthy backends | Every 30s |
| **Prometheus** | Metrics collection | Every 15s (if configured) |

#### Why Frequent Checks?

1. **Fast Failure Detection**: 30-second intervals mean unhealthy instances are detected within 1 minute
2. **Zero-Downtime Deploys**: New instances must pass health checks before receiving traffic
3. **Auto-Recovery**: Failed machines are automatically restarted

#### Industry Standards

| Provider | Default Interval | Timeout |
|----------|------------------|---------|
| Fly.io | 30s | 5s |
| AWS ALB | 30s | 5s |
| Kubernetes | 10s | 1s |
| Google Cloud Run | 10s | 2s |

**Your 30-second interval is industry standard.**

### Configuration Options

To reduce log noise without reducing reliability:

```toml
# fly.toml - Less frequent checks (only if stable)
[[http_service.checks]]
  grace_period = "30s"
  interval     = "60s"  # Up from 30s
  timeout      = "10s"
```

To suppress health check logging:

```python
# backend/main.py
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Skip logging for health checks
    if request.url.path in ("/healthz", "/health", "/metrics"):
        return await call_next(request)
    # ... normal logging ...
```

### Recommendation

**Keep the current 30-second interval** — it's appropriate. Add log filtering if the noise is bothersome.

---

## 4. Mobile UX Improvement for Graphs

### Current Implementation Status

**Good news: The feature already exists!**

The application already has a `LandscapeHint` component:

```
frontend/src/components/ui/landscape-hint.tsx
frontend/src/hooks/use-orientation.tsx
```

It's currently used in:
```
frontend/src/components/wizard/EfficientFrontierChart.tsx
```

### How It Works

#### Component: `LandscapeHint`

```tsx
// frontend/src/components/ui/landscape-hint.tsx
export function LandscapeHint({ storageKey, children }) {
  const isMobile = useIsMobile();
  const { isPortrait } = useOrientation();
  const [isDismissed, setIsDismissed] = useState(true);

  // Show hint if: mobile + portrait + not dismissed
  useEffect(() => {
    if (isMobile && isPortrait && !isDismissed) {
      setShowHint(true);
    }
  }, [isMobile, isPortrait, isDismissed]);

  // Persist dismissal in localStorage
  const handleDismiss = () => {
    localStorage.setItem(storageKey, "true");
    setIsDismissed(true);
  };

  return (
    <div className="relative">
      {children}
      {showHint && <HintOverlay />}
    </div>
  );
}
```

#### Hook: `useOrientation`

```tsx
// frontend/src/hooks/use-orientation.tsx
export function useOrientation() {
  const getOrientation = () => ({
    isLandscape: window.matchMedia("(orientation: landscape)").matches,
    isPortrait: !isLandscape,
    angle: window.screen?.orientation?.angle ?? 0,
  });

  // Listen to orientation changes
  useEffect(() => {
    window.addEventListener("orientationchange", handleChange);
    window.addEventListener("resize", handleChange);
    // ...
  }, []);

  return orientation;
}
```

### Current Usage

```tsx
// EfficientFrontierChart.tsx (line 493)
<LandscapeHint storageKey="efficient-frontier-landscape-hint">
  <Card>
    {/* Chart content */}
  </Card>
</LandscapeHint>
```

### Extension Plan: Apply to All Charts

To apply the landscape hint to all chart components:

#### Charts That Should Use LandscapeHint

| Component | File | Status |
|-----------|------|--------|
| EfficientFrontierChart | `EfficientFrontierChart.tsx` | Implemented |
| PortfolioOptimization | `PortfolioOptimization.tsx` | Needs addition |
| StressTest | `StressTest.tsx` | Needs addition |
| PortfolioBuilder | `PortfolioBuilder.tsx` | Needs addition |
| SectorDistribution | Various | Needs addition |

#### Implementation Steps

1. **Identify chart sections** in each component
2. **Wrap with LandscapeHint** using unique storage keys:

```tsx
// Example: PortfolioOptimization.tsx
import { LandscapeHint } from "@/components/ui/landscape-hint";

// Wrap the chart section
<LandscapeHint storageKey="portfolio-optimization-landscape-hint">
  <div className="chart-container">
    <ResponsiveContainer>
      <LineChart ... />
    </ResponsiveContainer>
  </div>
</LandscapeHint>
```

#### Edge Cases Handled

| Case | Behavior |
|------|----------|
| Tablet | `useIsMobile()` uses 768px breakpoint; tablets may show hint |
| Already Landscape | `isPortrait` check prevents showing hint |
| Very Small Screens | Hint overlay is responsive; fits small screens |
| User Dismissed | Persisted in localStorage per-component |

### UI Behavior Summary

| Condition | Behavior |
|-----------|----------|
| Desktop | Never shown |
| Mobile + Landscape | Never shown |
| Mobile + Portrait + First view | Shown after 500ms |
| User clicks "Continue anyway" | Hidden for current session |
| User clicks "Don't show again" | Hidden permanently (localStorage) |

### Message Copy

Current message:
```
Title: "Rotate for better view"
Body: "Turn your phone sideways to see the full chart"

Buttons:
- "Continue anyway" (dismisses once)
- "Don't show again" (dismisses permanently)
```

---

## Summary of Recommendations

### Immediate Actions (Low Effort, High Impact)

1. **Simplify `/healthz` endpoint** — Remove portfolio status enumeration
2. **Add frontend debouncing** — 300ms delay on search/filter inputs
3. **Extend health check timeout** — 5s to 10s as a quick fix

### Short-Term Actions (Medium Effort)

1. **Switch to async Redis** — Use `redis.asyncio` for non-blocking operations
2. **Apply LandscapeHint** to all chart components
3. **Add request logging filter** — Suppress health check noise

### Medium-Term Actions (Higher Effort)

1. **Implement response caching** — TTL cache for hot ticker data
2. **Connection pool tuning** — Increase max connections
3. **Consider VM upgrade** — If load increases significantly

---

*Investigation completed: 2026-03-06*
