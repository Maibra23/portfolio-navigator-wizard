# Redis Memory Analysis

This document summarizes how Redis is used in Portfolio Navigator Wizard and whether the 256 MB memory limit is suitable.

## Where the 256 MB Limit Is Set

1. **Dockerfile** – Redis is started with `--maxmemory 256mb` and `--maxmemory-policy allkeys-lru`. This is the initial limit before the app runs.
2. **backend/utils/redis_first_data_service.py** – On startup, the app calls `CONFIG SET maxmemory 256mb` and `CONFIG SET maxmemory-policy volatile-lru`. So the effective runtime limit is 256 MB, and only keys with a TTL are evicted when full (volatile-lru).

Both must stay in sync; if you change one, change the other.

---

## Redis Key Namespaces and Estimated Usage

### 1. Ticker data (largest share)

| Key pattern | Description | TTL | Est. size per key | Count | Est. total |
|------------|-------------|-----|-------------------|-------|------------|
| `ticker_data:prices:{ticker}` | Gzip-compressed OHLCV series (e.g. 15 years daily) | 28–90 days | ~3–6 KB | N tickers | ~5 KB × N |
| `ticker_data:sector:{ticker}` | Sector/industry JSON | 28–90 days | ~0.5–2 KB | N | ~1 KB × N |
| `ticker_data:metrics:{ticker}` | Risk/return metrics JSON | 28 days | ~0.5–2 KB | N | ~1 KB × N |

Approximate per ticker: ~7–9 KB (prices dominate). References (e.g. REDIS_SECURITY_ASSESSMENT.md) use ~5 KB/ticker for a 1,432-ticker cache ≈ 7.4 MB; with sector and metrics, 1,432 tickers ≈ 10–13 MB.

### 2. Master ticker lists

| Key | Description | TTL | Est. size |
|-----|-------------|-----|-----------|
| `master_ticker_list` | Full ticker list JSON | 1 year | ~200–500 KB |
| `master_ticker_list_validated` | Validated list (fallback) | 1 year | ~200–500 KB |

Total: under ~1 MB.

### 3. Portfolio buckets (recommendations)

| Key pattern | Description | TTL | Est. size |
|------------|-------------|-----|-----------|
| `portfolio_bucket:{profile}:0` … `:11` | 12 portfolios per risk profile (conservative, moderate, aggressive) | 7 days | ~5–15 KB each |
| `portfolio_bucket:{profile}:metadata` | Count, generated_at, etc. | 7 days | &lt;1 KB |

Rough total: 3 profiles × (12 × ~10 KB + metadata) ≈ 400 KB–500 KB.

### 4. Strategy portfolios

| Key pattern | Description | TTL | Est. size |
|------------|-------------|-----|-----------|
| `strategy_portfolios:pure:{strategy}` | Pure strategy portfolios (one per strategy) | 7 days | ~20–100 KB each |
| `strategy_portfolios:personalized:{strategy}:{profile}` | Per-strategy, per-profile | 7 days | ~20–80 KB each |

Number of strategies and profiles is finite; total typically well under 2 MB.

### 5. Eligible tickers cache (optimization)

| Key pattern | Description | TTL | Est. size |
|------------|-------------|-----|-----------|
| `optimization:eligible_tickers:{hash}` | Cached eligible tickers list for optimization UI | 7 days | ~200 KB–2 MB (depends on filters and list size) |

Usually 1–2 keys; total under ~2–4 MB.

### 6. Other caches

| Key / pattern | Description | TTL | Est. size |
|--------------|-------------|-----|-----------|
| Search result cache | Short-lived search cache | 90 s | Small, ephemeral |
| `fx:*` (FX cache) | FX rates | 24 h | &lt;50 KB |
| Shareable links | Link payloads | Configurable | Small |
| One-off metrics/cache keys | Various endpoint caches | 1 h – 7 days | Small |

Total: under ~1 MB in normal operation.

---

## Total Estimated Usage

| Scenario | Ticker count N | Ticker data | Other (portfolios, strategy, eligible, misc) | Total | % of 256 MB |
|----------|----------------|-------------|---------------------------------------------|-------|-------------|
| Current (1,432 tickers) | 1,432 | ~10–13 MB | ~4–6 MB | ~15–20 MB | ~6–8% |
| 2,500 tickers | 2,500 | ~18–22 MB | ~5–7 MB | ~25–30 MB | ~10–12% |
| 5,000 tickers | 5,000 | ~35–45 MB | ~6–8 MB | ~42–55 MB | ~16–22% |
| 10,000 tickers | 10,000 | ~70–90 MB | ~8–10 MB | ~80–100 MB | ~31–39% |
| 20,000 tickers | 20,000 | ~140–180 MB | ~10–12 MB | ~150–195 MB | ~59–76% |
| 30,000+ tickers | 30,000+ | 210+ MB | ~12 MB | 220+ MB | 86%+ |

Eviction policy is volatile-lru: when the limit is reached, Redis evicts keys that have a TTL (all of the above do). So 256 MB is a hard cap; usage will stay at or below that, with eviction as a safety valve.

---

## Is 256 MB Suitable?

Yes, for the current and near-term design:

1. **Current scale** – With ~1,432 tickers, usage is on the order of 15–20 MB (~6–8% of 256 MB). There is ample headroom for growth and temporary spikes.
2. **Growth** – 256 MB comfortably supports roughly 20,000–25,000 cached tickers (with portfolios, strategy, and eligible-tickers caches). Beyond that, eviction will drop less recently used ticker data; the app repopulates from external APIs, so behavior remains correct, with more cache misses.
3. **VM size** – The Fly.io backend machine has 1 GB RAM. Allocating 256 MB to Redis leaves ~750 MB for the OS, Python, FastAPI, and numpy/pandas; that is a reasonable balance.
4. **Previous limit** – The app was effectively using 48 MB (set in redis_first_data_service), which was tight for anything beyond a small ticker set. 256 MB removes that bottleneck and aligns with the Dockerfile’s intended cap.
5. **Eviction** – volatile-lru ensures that only cacheable, TTL-backed data is evicted; no permanent user data is stored only in Redis.

Recommendation: keep the 256 MB limit. If you later scale to very large ticker sets (e.g. 30,000+) and want to reduce eviction, consider increasing to 512 MB and raising the Fly machine size, or moving to a managed Redis instance with a higher limit.

---

## Summary Table

| Setting | Value | Location |
|---------|--------|----------|
| maxmemory | 256mb | Dockerfile CMD, redis_first_data_service.MAX_MEMORY |
| maxmemory-policy (runtime) | volatile-lru | redis_first_data_service._configure_redis_memory() |
| maxmemory-policy (Redis default before app) | allkeys-lru | Dockerfile CMD |

For more on persistence and data loss, see DEPLOYMENT_OPERATIONS.md (Redis Data Lifecycle) and the main README.
