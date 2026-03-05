# Redis Architecture in Portfolio Navigator Wizard

This document explains how Redis is integrated into the Portfolio Navigator Wizard application, including data flow, key patterns, fetching system, and the interaction between frontend, backend, and Redis.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Redis Connection Configuration](#3-redis-connection-configuration)
4. [Key Files and Their Roles](#4-key-files-and-their-roles)
5. [Redis Key Patterns](#5-redis-key-patterns)
6. [Data Flow Workflows](#6-data-flow-workflows)
7. [Fetching System](#7-fetching-system)
8. [TTL and Cache Management](#8-ttl-and-cache-management)
9. [Examples](#9-examples)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

The application uses a **Redis-first architecture** where:

- **Redis is the primary data source** for all ticker and portfolio data
- **Yahoo Finance (yfinance/yahooquery)** is only called when data is missing or expired
- **No database** is used — Redis serves as both cache and persistent storage
- **Data persists** via Redis Cloud's RDB snapshots (every 12 hours)

### Why Redis-First?

1. **Speed**: Redis serves data in <1ms vs 2-5 seconds for Yahoo Finance API
2. **Rate Limits**: Yahoo Finance has strict rate limits (~2000 requests/day)
3. **Cost**: Reduces API calls, stays within free tier limits
4. **Reliability**: Cached data is always available, even if Yahoo is down

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER'S BROWSER                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (portfolio-navigator.fly.dev)                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  React SPA + Vite                                                    │    │
│  │  - Served via nginx                                                  │    │
│  │  - API calls to backend via VITE_API_BASE_URL                        │    │
│  │  - No direct Redis access                                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ API Calls (/api/v1/portfolio/*)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   BACKEND (portfolio-navigator-wizard.fly.dev)               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Application                                                 │    │
│  │                                                                      │    │
│  │  main.py                                                             │    │
│  │    └── Initializes RedisFirstDataService (singleton)                 │    │
│  │    └── Initializes RedisPortfolioManager                             │    │
│  │    └── Initializes StrategyPortfolioOptimizer                        │    │
│  │                                                                      │    │
│  │  routers/portfolio.py                                                │    │
│  │    └── Handles all /api/v1/portfolio/* endpoints                     │    │
│  │    └── Calls RedisFirstDataService for data                          │    │
│  │                                                                      │    │
│  │  utils/redis_first_data_service.py  ◄── CENTRAL DATA SERVICE         │    │
│  │    └── get_ticker_data() - prices, metrics, meta, sector             │    │
│  │    └── list_cached_tickers() - all available tickers                 │    │
│  │    └── Lazy-loads EnhancedDataFetcher only when needed               │    │
│  │                                                                      │    │
│  │  utils/enhanced_data_fetcher.py                                      │    │
│  │    └── Fetches from Yahoo Finance when cache miss                    │    │
│  │    └── Writes fetched data back to Redis                             │    │
│  │                                                                      │    │
│  │  utils/redis_portfolio_manager.py                                    │    │
│  │    └── Stores/retrieves portfolio buckets                            │    │
│  │    └── Validates portfolios before storage                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ redis:// or rediss://
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REDIS CLOUD (eu-north-1, Stockholm)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  database-Wizard (30MB free tier)                                    │    │
│  │                                                                      │    │
│  │  Key Categories:                                                     │    │
│  │  ├── ticker_data:prices:{TICKER}    (1,415 keys, ~5.7 MB)           │    │
│  │  ├── ticker_data:meta:{TICKER}      (1,415 keys, ~0.4 MB)           │    │
│  │  ├── ticker_data:metrics:{TICKER}   (1,415 keys, ~1.1 MB)           │    │
│  │  ├── ticker_data:sector:{TICKER}    (1,415 keys, ~1.1 MB)           │    │
│  │  ├── portfolio_bucket:{profile}:{n} (65 keys, ~0.6 MB)              │    │
│  │  ├── strategy_portfolios:*          (5 keys, ~1.2 MB)               │    │
│  │  ├── master_ticker_list_validated   (1 key, ~0.2 MB)                │    │
│  │  └── optimization:eligible_tickers  (3 keys, ~0.5 MB)               │    │
│  │                                                                      │    │
│  │  Total: ~5,749 keys, ~11.3 MB                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Only on cache miss
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         YAHOO FINANCE API                                    │
│  - yfinance library (historical prices)                                      │
│  - yahooquery library (fundamentals, sector info)                            │
│  - Rate limited: ~2000 requests/day                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Redis Connection Configuration

### Environment Variable

The application uses a single environment variable for Redis connection:

```bash
REDIS_URL="redis://default:PASSWORD@HOST:PORT"
```

### Connection Flow

```python
# backend/utils/redis_first_data_service.py (lines 43-57)

class RedisFirstDataService:
    def __init__(self, redis_url: str = None):
        # 1. Get URL from parameter, env var, or default
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

        # 2. Initialize connection with pool
        self.redis_client = self._init_redis_from_url(redis_url)

        # 3. Lazy-load EnhancedDataFetcher (only when needed)
        self._enhanced_data_fetcher = None
```

### Connection Pool Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `max_connections` | 50 | Connection pool ceiling |
| `socket_connect_timeout` | 5s | Connection timeout |
| `socket_timeout` | 5s | Operation timeout |
| `retry_on_timeout` | True | Auto-retry on timeout |
| `decode_responses` | False | Return raw bytes (for gzip) |

### TLS Support

The service automatically detects `rediss://` scheme and enables TLS:

```python
# Supports both:
# - redis://... (standard)
# - rediss://... (TLS encrypted)
use_ssl = parsed.scheme == 'rediss'
```

---

## 4. Key Files and Their Roles

### Core Redis Files

| File | Role | Description |
|------|------|-------------|
| `utils/redis_first_data_service.py` | **Central Data Service** | Singleton that handles all ticker data operations. Entry point for all data access. |
| `utils/redis_portfolio_manager.py` | **Portfolio Storage** | Stores/retrieves portfolio buckets, validates compliance before storage. |
| `utils/redis_config.py` | **Configuration** | Redis connection settings and constants. |
| `utils/redis_ttl_monitor.py` | **TTL Monitoring** | Monitors expiring keys, triggers background refresh. |
| `utils/redis_metrics.py` | **Prometheus Metrics** | Exposes Redis stats to Prometheus for monitoring. |

### Data Fetching Files

| File | Role | Description |
|------|------|-------------|
| `utils/enhanced_data_fetcher.py` | **Yahoo Finance Fetcher** | Fetches from Yahoo Finance API when cache miss occurs. |
| `utils/fx_fetcher.py` | **FX Rates** | Fetches currency exchange rates for international stocks. |
| `utils/portfolio_stock_selector.py` | **Stock Selection** | Reads ticker data from Redis, builds stock dictionaries for portfolio generation. |

### Portfolio Generation Files

| File | Role | Description |
|------|------|-------------|
| `utils/enhanced_portfolio_generator.py` | **Portfolio Generator** | Orchestrates portfolio generation using Redis data. |
| `utils/dynamic_weighting_system.py` | **Weight Optimizer** | SLSQP optimizer for portfolio weight allocation. |
| `utils/strategy_portfolio_optimizer.py` | **Strategy Portfolios** | Generates strategy-based portfolios (momentum, value, etc.). |

---

## 5. Redis Key Patterns

### Ticker Data Keys

```
ticker_data:prices:{TICKER}
ticker_data:meta:{TICKER}
ticker_data:metrics:{TICKER}
ticker_data:sector:{TICKER}
```

**Example:**
```
ticker_data:prices:AAPL     → gzip-compressed JSON of 20 years monthly prices
ticker_data:meta:AAPL       → {"name": "Apple Inc.", "currency": "USD", ...}
ticker_data:metrics:AAPL    → {"expected_return": 0.15, "volatility": 0.28, ...}
ticker_data:sector:AAPL     → {"sector": "Technology", "industry": "Consumer Electronics"}
```

### Portfolio Bucket Keys

```
portfolio_bucket:{risk_profile}:{index}
portfolio_bucket:{risk_profile}:metadata
```

**Risk Profiles:**
- `conservative`
- `very-conservative`
- `moderate`
- `aggressive`
- `very-aggressive`

**Example:**
```
portfolio_bucket:moderate:0     → {"allocations": [...], "expectedReturn": 0.12, "risk": 0.18}
portfolio_bucket:moderate:12    → (13 portfolios per profile: 0-12)
portfolio_bucket:moderate:metadata → {"count": 13, "lastUpdated": "2026-03-05T..."}
```

### Strategy Portfolio Keys

```
strategy_portfolios:pure:{strategy}
strategy_portfolios:personalized:{strategy}:{profile}
```

**Strategies:** momentum, value, quality, low_volatility, dividend, growth

### Master Ticker List

```
master_ticker_list              → Full list of all tickers (may include untested)
master_ticker_list_validated    → Only tickers confirmed to work with Yahoo Finance
```

### Optimization Cache

```
optimization:eligible_tickers:{hash}    → Cached eligible tickers for optimization
```

### Other Keys

```
fx:rates                                → Currency exchange rates
LIMITER:{ip}:{endpoint}                → Rate limiting state
shareable_link:{code}                  → Shareable portfolio links
```

---

## 6. Data Flow Workflows

### Workflow 1: User Requests Ticker Data

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. Frontend calls: GET /api/v1/portfolio/ticker-table/data                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. Backend (routers/portfolio.py) receives request                           │
│    └── Calls redis_first_data_service.get_ticker_data(ticker)                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. RedisFirstDataService.get_ticker_data(ticker)                             │
│    ├── Check Redis: ticker_data:prices:{ticker}                              │
│    ├── Check Redis: ticker_data:metrics:{ticker}                             │
│    ├── Check Redis: ticker_data:sector:{ticker}                              │
│    └── Check Redis: ticker_data:meta:{ticker}                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              CACHE HIT                            CACHE MISS
                    │                                   │
                    ▼                                   ▼
┌─────────────────────────────┐     ┌─────────────────────────────────────────┐
│ Return cached data          │     │ 4. Lazy-load EnhancedDataFetcher        │
│ (decompress if gzipped)     │     │    └── Fetch from Yahoo Finance         │
└─────────────────────────────┘     │    └── Store in Redis with TTL          │
                                    │    └── Return freshly fetched data      │
                                    └─────────────────────────────────────────┘
```

### Workflow 2: Portfolio Generation

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. User selects risk profile (e.g., "moderate")                              │
│    Frontend calls: GET /api/v1/portfolio/recommendations/moderate            │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. Backend checks Redis: portfolio_bucket:moderate:*                         │
│    └── If exists: Return cached portfolio                                    │
│    └── If missing: Generate new portfolio                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                        (if generation needed)
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. EnhancedPortfolioGenerator.generate_portfolios()                          │
│    ├── PortfolioStockSelector.get_eligible_stocks()                          │
│    │   └── Reads ticker_data:* from Redis                                    │
│    │   └── Filters by volatility, return, sector                             │
│    ├── DynamicWeightingSystem.optimize()                                     │
│    │   └── SLSQP optimization for weights                                    │
│    └── PortAnalytics.validate()                                              │
│        └── Validates risk/return compliance                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4. RedisPortfolioManager.store_portfolio()                                   │
│    └── Validates portfolio compliance                                        │
│    └── Stores to Redis: portfolio_bucket:moderate:{index}                    │
│    └── Sets TTL: 7 days                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Workflow 3: Background Data Refresh

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. RedisTTLMonitor runs periodically (or triggered by admin)                 │
│    └── Scans for keys with TTL < 7 days                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. For each expiring ticker:                                                 │
│    └── EnhancedDataFetcher.fetch_ticker_data()                               │
│    └── Updates Redis with fresh data                                         │
│    └── Resets TTL to 28 days                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. For expiring portfolios:                                                  │
│    └── EnhancedPortfolioGenerator.regenerate()                               │
│    └── Stores new portfolios to Redis                                        │
│    └── Resets TTL to 7 days                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Fetching System

### Master Ticker List Reference

The fetching system uses `master_ticker_list_validated` as the authoritative source:

```python
# backend/utils/enhanced_data_fetcher.py (lines 83-100)

class EnhancedDataFetcher:
    def __init__(self):
        # Use validated master list (only tickers confirmed to work)
        self.use_validated_master_list = config.use_validated_master_list

        if self.use_validated_master_list:
            validated_key = "master_ticker_list_validated"
            validated_data = self.r.get(validated_key)
            self.all_tickers = json.loads(validated_data.decode())
```

### Fetch Priority Order

1. **Redis Cache** (always checked first)
2. **yfinance** (primary Yahoo Finance library)
3. **yahooquery** (fallback for sector/fundamental data)

### Rate Limiting Configuration

```python
# backend/utils/enhanced_data_fetcher.py (lines 36-57)

BATCH_SIZE = 20                    # Tickers per batch
MAX_WORKERS = 1                    # Single worker (avoids rate limits)
RATE_LIMIT_DELAY = 4               # Seconds between batches
REQUEST_DELAY = (1.3, 4.0)         # Random delay per request
DAILY_REQUEST_LIMIT = 2000         # Yahoo Finance daily limit
MAX_RETRIES = 1                    # Single retry on failure
```

### Data Compression

Price data is gzip-compressed to reduce storage:

```python
# Writing compressed data
compressed = gzip.compress(json.dumps(prices).encode())
redis_client.set(f"ticker_data:prices:{ticker}", compressed, ex=ttl)

# Reading compressed data
compressed = redis_client.get(f"ticker_data:prices:{ticker}")
prices = json.loads(gzip.decompress(compressed))
```

---

## 8. TTL and Cache Management

### TTL Configuration

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Ticker prices | 28 days | Monthly data, doesn't change frequently |
| Ticker metrics | 28 days | Calculated from prices |
| Ticker meta | 28 days | Company info rarely changes |
| Ticker sector | 28 days | Sector classification stable |
| Portfolio buckets | 7 days | Regenerated weekly for freshness |
| Optimization cache | 24 hours | Short-lived computation cache |
| Rate limiting | 1-60 seconds | Per-endpoint limits |

### TTL Jitter

To prevent cache stampede (all keys expiring at once):

```python
# backend/utils/redis_first_data_service.py (lines 102-109)

@staticmethod
def jittered_ttl(base_seconds: int) -> int:
    """Add +/- 15% random jitter to TTL"""
    jitter_range = base_seconds * 0.15
    return int(base_seconds + random.uniform(-jitter_range, jitter_range))

# Example: 28 days base = 2,419,200 seconds
# With jitter: 2,056,320 to 2,782,080 seconds (23.8 to 32.2 days)
```

### Cache Eviction Policy

```python
MAX_MEMORY = "256mb"
MAX_MEMORY_POLICY = "volatile-lru"  # Evict least-recently-used keys with TTL
```

Note: Redis Cloud manages this setting server-side (CONFIG SET blocked).

---

## 9. Examples

### Example 1: Get Ticker Data (Python)

```python
from utils.redis_first_data_service import redis_first_data_service as rds

# Get complete ticker data
ticker_data = rds.get_ticker_data("AAPL")
# Returns: {
#     "prices": {monthly price data},
#     "metrics": {"expected_return": 0.15, "volatility": 0.28, ...},
#     "sector": {"sector": "Technology", "industry": "..."},
#     "meta": {"name": "Apple Inc.", "currency": "USD", ...}
# }

# List all cached tickers
tickers = rds.list_cached_tickers()
# Returns: ["AAPL", "MSFT", "GOOGL", ...]
```

### Example 2: Store Portfolio (Python)

```python
from utils.redis_portfolio_manager import RedisPortfolioManager

manager = RedisPortfolioManager(redis_client)

portfolio = {
    "allocations": [
        {"symbol": "AAPL", "allocation": 30.5, "sector": "Technology"},
        {"symbol": "MSFT", "allocation": 25.0, "sector": "Technology"},
        {"symbol": "JNJ", "allocation": 44.5, "sector": "Healthcare"}
    ],
    "expectedReturn": 0.12,
    "risk": 0.18,
    "sharpe": 0.67
}

# Store portfolio bucket
manager.store_portfolio("moderate", 0, portfolio)
# Stored to Redis: portfolio_bucket:moderate:0
```

### Example 3: Frontend API Call (TypeScript)

```typescript
// frontend/src/config/api.ts

// Get recommendations for a risk profile
const response = await fetch(API_ENDPOINTS.RECOMMENDATIONS("moderate"));
const portfolios = await response.json();

// Search for tickers
const searchResponse = await fetch(API_ENDPOINTS.TICKER_SEARCH("apple", 10));
const tickers = await searchResponse.json();
```

### Example 4: Direct Redis Commands (CLI)

```bash
# Connect to Redis Cloud
redis-cli -u "redis://default:PASSWORD@redis-14204.crce175.eu-north-1-1.ec2.cloud.redislabs.com:14204"

# Count all keys
DBSIZE

# List ticker data keys for AAPL
KEYS ticker_data:*:AAPL

# Check TTL on a key
TTL ticker_data:prices:AAPL

# Get portfolio bucket
GET portfolio_bucket:moderate:0

# Scan for all portfolio buckets
SCAN 0 MATCH portfolio_bucket:* COUNT 100
```

---

## 10. Troubleshooting

### Issue: "Cache miss triggering fetch"

**Symptom:** API response slow (2-5 seconds)

**Cause:** Data not in Redis, fetching from Yahoo Finance

**Solution:**
1. Run `scripts/full_refetch_with_gate.py` to warm cache
2. Check Redis key exists: `EXISTS ticker_data:prices:{TICKER}`

### Issue: "Too many keys to fetch"

**Symptom:** `redis.exceptions.ResponseError: too many keys to fetch`

**Cause:** Using `KEYS *` on large Redis instance

**Solution:** Use `SCAN` instead of `KEYS`:
```python
cursor = 0
while True:
    cursor, keys = redis_client.scan(cursor=cursor, count=500)
    # process keys
    if cursor == 0:
        break
```

### Issue: "CONFIG SET not allowed"

**Symptom:** Warning about managed Redis blocking CONFIG

**Cause:** Redis Cloud free tier doesn't allow CONFIG commands

**Impact:** None — Redis Cloud manages settings server-side

### Issue: "Connection timeout"

**Symptom:** `redis.exceptions.TimeoutError`

**Check:**
1. Network connectivity to Redis Cloud
2. Correct REDIS_URL in environment
3. Password correct
4. Port open (not blocked by firewall)

---

## Appendix: Current Redis Cloud Configuration

| Setting | Value |
|---------|-------|
| Provider | Redis Cloud |
| Database | database-Wizard (ID: 14065227) |
| Region | eu-north-1 (Stockholm) |
| Host | redis-14204.crce175.eu-north-1-1.ec2.cloud.redislabs.com |
| Port | 14204 |
| Storage Limit | 30 MB |
| Current Usage | ~11.3 MB (37.7%) |
| Commands | Unlimited |
| Persistence | RDB snapshots (every 12 hours) |
| Connection Limit | 30 concurrent |

---

*Last updated: 2026-03-05*


## Costs 

Actual Fly.io Billing Model

  Fly.io charges for VM time (shared-cpu-1x), not just memory:

  ┌──────────────┬────────────────┬─────────────────────────┐
  │     Plan     │ Free Machines  │    Cost Per Machine     │
  ├──────────────┼────────────────┼─────────────────────────┤
  │ Hobby (Free) │ 3 shared VMs   │ $0                      │
  ├──────────────┼────────────────┼─────────────────────────┤
  │ After free   │ Additional VMs │ ~$1.94/month per 256 MB │
  └──────────────┴────────────────┴─────────────────────────┘

  Corrected calculation:

  Frontend (256 MB):
    - Uses 1 of 3 free VMs
    - Cost: $0/month

  Backend (1024 MB):
    - Uses 1 of 3 free VMs (base)
    - Extra 768 MB: ~$5.80/month

  Total estimated: ~$5-6/month

  Comparison: Always-On vs Auto-Stop

  ┌─────────────────────┬───────────────┬──────────────────┬───────────────────────────┐
  │    Configuration    │   Frontend    │     Backend      │       Monthly Cost        │
  ├─────────────────────┼───────────────┼──────────────────┼───────────────────────────┤
  │ Current (always-on) │ 1 VM, 256 MB  │ 1 VM, 1024 MB    │ ~$5-6/month               │
  ├─────────────────────┼───────────────┼──────────────────┼───────────────────────────┤
  │ With auto-stop      │ 0-1 VM (idle) │ 1 VM (always on) │ ~$5/month                 │
  ├─────────────────────┼───────────────┼──────────────────┼───────────────────────────┤
  │ Both auto-stop      │ 0-1 VM        │ 0-1 VM           │ ~$0-2/month (usage-based) │
  └─────────────────────┴───────────────┴──────────────────┴───────────────────────────┘