# Search Optimization Implementation

**Date:** 2026-03-06
**Status:** Implemented, Tested Locally
**Impact:** Backend performance, Infrastructure costs

## Overview

This document describes the search optimization changes made to address the 40+ second search latency for company name queries. The optimization reduces search time from ~40 seconds to <100ms.

---

## Problem Statement

### Original Issue
- **Exact ticker search** (e.g., "AAPL"): ~1 second
- **Company name search** (e.g., "Apple"): **40+ seconds**
- **Partial search** (e.g., "goo"): **40+ seconds**

### Root Cause
The original `search_tickers()` implementation performed O(n) Redis GET calls for company name searches:
1. Phase 1: Check exact ticker match (fast)
2. Phase 2: If no exact match, loop through ALL ~1400 tickers with individual Redis calls
3. Each Redis call = ~25-30ms network latency
4. 1400 tickers x 30ms = **42 seconds**

---

## Solution: In-Memory Search Index

### Architecture

```
                    STARTUP                           RUNTIME
                    -------                           -------

Redis Cloud    -->  Pipeline Fetch   -->  In-Memory   -->  O(1) Lookup
(1400 tickers)      (single batch)        Index            (<100ms)

                    ~2-5 seconds          Persists in      All queries
                    one-time cost         memory           use index
```

### Data Structures

```python
# Primary index: ticker -> metadata
_search_index: Dict[str, Dict[str, str]] = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "industry": "..."},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "industry": "..."},
    # ... 1400 entries
}

# Prefix index: 2-char prefix -> list of tickers (for autocomplete)
_name_prefix_index: Dict[str, List[str]] = {
    "ap": ["AAPL", "APD", "APTV", ...],
    "go": ["GOOGL", "GOOG", "GD", ...],
    # ... all 2-char prefixes
}

# Sector index: sector -> list of tickers (for browsing)
_sector_index: Dict[str, List[str]] = {
    "technology": ["AAPL", "GOOGL", "MSFT", ...],
    "healthcare": ["JNJ", "PFE", "UNH", ...],
    # ... 12 sectors
}

# Popular tickers (pre-sorted by volume/market cap)
_popular_tickers: List[str] = ["AAPL", "MSFT", "GOOGL", ...]
```

---

## Files Changed

### Backend

| File | Changes |
|------|---------|
| `backend/utils/redis_first_data_service.py` | Added search index, `build_search_index()`, `search_instant()`, prefix/sector indexes |
| `backend/routers/portfolio.py` | Added `/popular-tickers`, `/sectors`, `/sectors/{id}/tickers` endpoints |
| `backend/main.py` | Call `build_search_index()` at startup |
| `Dockerfile` | Changed from 1 worker to 2 workers |
| `fly.toml` | Updated health check timeouts, VM memory |

### Frontend

| File | Changes |
|------|---------|
| `frontend/src/components/wizard/EnhancedStockSearch.tsx` | New component with popular tickers, sector browsing, autocomplete |

---

## New API Endpoints

### GET /api/v1/portfolio/popular-tickers
Returns pre-computed popular tickers for quick selection.

```json
{
  "success": true,
  "total": 12,
  "tickers": [
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology"},
    ...
  ]
}
```

### GET /api/v1/portfolio/sectors
Returns available sectors with icons.

```json
{
  "success": true,
  "total": 12,
  "sectors": [
    {"id": "technology", "name": "Technology", "icon": "💻"},
    ...
  ]
}
```

### GET /api/v1/portfolio/sectors/{sector_id}/tickers
Returns tickers for a specific sector.

```json
{
  "success": true,
  "total": 50,
  "tickers": [
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology"},
    ...
  ]
}
```

---

## Performance Results

| Query Type | Before | After | Improvement |
|------------|--------|-------|-------------|
| Company name ("Apple") | 40+ sec | **67ms** | ~600x faster |
| Partial match ("goo") | 40+ sec | **72ms** | ~600x faster |
| Exact ticker ("AAPL") | ~1 sec | **150ms** | ~6x faster |
| Popular tickers | N/A | **362ms** | NEW |
| Sectors list | N/A | **35ms** | NEW |
| Sector tickers | N/A | **79ms** | NEW |

---

## Infrastructure Changes

### Before
```toml
# fly.toml
[[http_service.checks]]
  grace_period = "30s"
  timeout = "10s"

[[vm]]
  memory = '1gb'
  cpus = 1

# Dockerfile
CMD uvicorn main:app --workers 1
```

### After
```toml
# fly.toml
[[http_service.checks]]
  grace_period = "60s"
  interval = "30s"
  timeout = "20s"

[[vm]]
  memory = '2gb'
  cpus = 1
  memory_mb = 2048

# Dockerfile
CMD uvicorn main:app --workers 2
```

### Cost Impact

| Resource | Before | After | Delta |
|----------|--------|-------|-------|
| VM Memory | 1GB | 2GB | +$5.19/mo |
| Workers | 1 | 2 | (included in memory) |
| **Total Backend** | ~$7.94/mo | ~$13.13/mo | **+$5.19/mo** |

---

## Rollback Procedures

### If Search Breaks

#### Option 1: Disable In-Memory Index (Quick)
Edit `backend/utils/redis_first_data_service.py`:

```python
def search_instant(self, query: str, limit: int = 10, filters: Dict = None) -> List[Dict[str, Any]]:
    # ROLLBACK: Bypass in-memory index, use original Redis-based search
    return self._search_tickers_legacy(query, limit, filters)
```

#### Option 2: Revert to Previous Code (Full)
```bash
# Find the commit before search optimization
git log --oneline -10

# Revert the specific files
git checkout <commit-before-optimization> -- \
  backend/utils/redis_first_data_service.py \
  backend/routers/portfolio.py \
  backend/main.py

# Deploy
fly deploy
```

### If Infrastructure Costs Too High

#### Reduce Workers Back to 1
Edit `Dockerfile`:
```dockerfile
CMD exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1
```

Edit `fly.toml`:
```toml
[[vm]]
  memory = '1gb'
  cpus = 1
  memory_mb = 1024
```

Deploy:
```bash
fly deploy
```

**Note:** With 1 worker, heavy sector-loading operations may block the event loop and cause health check failures during high load.

---

## Key Code Locations

### Search Index Building
`backend/utils/redis_first_data_service.py:122-230`
- `build_search_index()`: Builds all indexes from Redis data
- Uses Redis pipeline for batch fetching (1 round-trip instead of 1400)

### Index Refresh (NEW)
`backend/utils/redis_first_data_service.py:234-270`
- `refresh_search_index()`: Clears and rebuilds the index
- `get_search_index_stats()`: Returns index statistics for monitoring

### Instant Search
`backend/utils/redis_first_data_service.py:272-380`
- `search_instant()`: O(1) lookup using in-memory index
- Falls back to fuzzy matching if no exact/prefix match

### Startup Integration & Periodic Refresh
`backend/main.py:134-165`
```python
# Build initial index
redis_first_data_service.build_search_index()

# Schedule 24h periodic refresh
async def periodic_search_index_refresh():
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 hours
        redis_first_data_service.refresh_search_index()

asyncio.create_task(periodic_search_index_refresh())
```

### New Endpoints
`backend/routers/portfolio.py:624-700`
- `/popular-tickers`: Returns pre-sorted popular stocks
- `/sectors`: Returns sector list with icons
- `/sectors/{id}/tickers`: Returns stocks by sector

---

## Monitoring

### Check Index Status
```bash
curl http://localhost:8000/healthz
# Should return {"status": "healthy"} after index is built

# Check logs for index building
fly logs | grep "Search index"
# Expected: "Search index built: 1400 tickers, 500 prefixes, 12 sectors"
```

### Measure Search Latency
```bash
# Company name search (should be <100ms)
time curl -s "http://localhost:8000/api/v1/portfolio/search-tickers?q=Apple&limit=5"

# Partial search (should be <100ms)
time curl -s "http://localhost:8000/api/v1/portfolio/search-tickers?q=micro&limit=5"
```

---

## Implemented Improvements (2026-03-06)

### 1. TTL-Aware Index Refresh (IMPLEMENTED)
The search index refreshes automatically in three scenarios:

| Trigger | When | Why |
|---------|------|-----|
| **TTL Data Refresh** | After `refresh_expiring_tickers()` | Ticker data changed in Redis |
| **Cold Start Recovery** | After eligible tickers pre-computation | Data now available after empty Redis |
| **24h Safety Net** | Every 24 hours | Catch any missed updates |

**Implementation:**
- `redis_first_data_service.py`: Added `refresh_search_index()` and `get_search_index_stats()` methods
- `main.py:700-716`: Refresh index after TTL monitoring refreshes ticker data
- `main.py:403-412`: Build index after cold start data load completes
- `main.py:141-163`: Background task runs `periodic_search_index_refresh()` every 24h

**How it works:**
```
Redis TTL Expiring → TTL Monitor Refreshes Data → Search Index Refreshed
                                                          ↓
Cold Start (empty Redis) → Data Pre-computation → Search Index Built
                                                          ↓
Safety Net: Every 24 hours → Periodic Refresh → Search Index Refreshed
```

**Monitoring:**
```bash
# Check logs for index refresh triggers
fly logs | grep "Search index"

# Expected patterns:
# "Search index built: 1415 tickers, 8309 prefixes in 0.25s"  (startup)
# "Refreshing search index after ticker data update..."       (TTL trigger)
# "Search index built (cold start): 1415 tickers"            (cold start)
# "Periodic search index refresh starting..."                 (24h safety)
```

### 2. Redis Caching for Search Results (ASSESSED - NOT IMPLEMENTED)
**Decision:** Skip this optimization.

**Rationale:**
- Current in-memory search: **<100ms**
- Redis cache lookup overhead: **+25-30ms per query**
- Adding Redis cache would actually **slow down** search by 25-30%
- The in-memory index IS already the cache

**Conclusion:** The in-memory index provides better performance than Redis for this use case because it eliminates network latency entirely.

### 3. Frontend Debouncing (ASSESSED - ALREADY OPTIMAL)
**Current implementation:**
| Component | Debounce | Use Case |
|-----------|----------|----------|
| `PortfolioBuilder.tsx` | 300ms | Full search on keystroke |
| `EnhancedStockSearch.tsx` | 150ms | Autocomplete suggestions |

**Industry benchmarks:**
- Google Instant Search: ~100-150ms
- Algolia recommendation: 200-300ms for full search
- Material UI Autocomplete default: 200ms

**Conclusion:** Current values are optimal. No changes needed.

---

## Future Improvements (Not Yet Implemented)

1. **Elasticsearch Integration**: For very large ticker sets (>10k), consider Elasticsearch for full-text search with fuzzy matching and relevance scoring.

2. **Search Analytics**: Track popular queries to pre-warm cache or suggest trending searches.

3. **Personalized Results**: Rank search results based on user's portfolio history or preferences.

---

## Appendix: Original Slow Search Code

For reference, the original O(n) implementation that was replaced:

```python
# BEFORE: O(n) Redis calls
async def search_tickers_legacy(self, query: str, limit: int = 10):
    results = []
    # Phase 1: Exact ticker match (fast)
    ticker_data = await self.redis.get(f"ticker:{query.upper()}")
    if ticker_data:
        results.append(ticker_data)

    # Phase 2: Company name search (SLOW - O(n) Redis calls)
    if len(results) < limit:
        all_tickers = await self.redis.smembers("all_tickers")  # ~1400 tickers
        for ticker in all_tickers:
            data = await self.redis.get(f"ticker:{ticker}")  # 25-30ms each!
            if query.lower() in data.get("name", "").lower():
                results.append(data)
    return results[:limit]
```
