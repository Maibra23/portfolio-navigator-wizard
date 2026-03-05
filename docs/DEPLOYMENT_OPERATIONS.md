# Portfolio Navigator Wizard - Deployment Operations Guide

## Table of Contents
1. [Current Deployment Status](#current-deployment-status)
2. [How the System Works](#how-the-system-works)
3. [Master List → Redis Data Flow](#master-list--redis-data-flow)
   - [Master List Generation](#master-list-generation)
   - [Loading Hierarchy](#loading-hierarchy)
   - [Yahoo Finance Fetching](#yahoo-finance-fetching)
   - [Redis Storage Schema](#redis-storage-schema)
4. [System Autonomy Assessment](#system-autonomy-assessment)
   - [What IS Fully Automated](#what-is-fully-automated)
   - [What Requires Manual Intervention](#what-requires-manual-intervention)
   - [Critical Gaps](#critical-gaps)
5. [Gap Resolution Plans](#gap-resolution-plans)
   - [Gap 1: Redis Data Persistence](#gap-1-redis-data-persistence)
   - [Gap 2: Scheduled Jobs](#gap-2-scheduled-jobs)
   - [Gap 3: Master List Auto-Refresh](#gap-3-master-list-auto-refresh)
6. [Redis Data Lifecycle](#redis-data-lifecycle)
   - [When to Worry About Redis Data Loss](#when-to-worry-about-redis-data-loss)
7. [Auto-Stop Behavior (Why Frontend Shows "Suspended")](#auto-stop-behavior)
8. [Manual Data Population](#manual-data-population)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)
10. [Quick Deploy Guide: After Committing Changes](#quick-deploy-guide-after-committing-changes)

---

## Current Deployment Status

| Service | URL | Always Running? |
|---------|-----|-----------------|
| **Frontend** | https://portfolio-navigator.fly.dev | No (auto-stops when idle) |
| **Backend** | https://portfolio-navigator-wizard.fly.dev | Yes (always on) |
| **API Docs** | https://portfolio-navigator-wizard.fly.dev/docs | Yes |

### Configured Secrets (Fly.io Dashboard)
- `ADMIN_API_KEY` - For admin endpoints (cache warming, etc.)
- `SMTP_USER` - Gmail address for notifications
- `SMTP_PASSWORD` - Gmail App Password
- `TTL_NOTIFICATION_EMAIL` - Where to send alerts
- `SMTP_HOST` / `SMTP_PORT` - Email server config

---

## How the System Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FLY.IO CLOUD                                │
│                                                                     │
│   ┌─────────────────────┐         ┌─────────────────────────────┐  │
│   │     FRONTEND        │         │         BACKEND             │  │
│   │  (nginx + React)    │  HTTP   │    (FastAPI + Redis)        │  │
│   │                     │ ──────► │                             │  │
│   │  - Static files     │  API    │  - /api/v1/portfolio/*      │  │
│   │  - SPA routing      │  calls  │  - /healthz                 │  │
│   │  - Auto-stops       │         │  - Bundled Redis            │  │
│   │    when idle        │         │  - Always running           │  │
│   └─────────────────────┘         └─────────────────────────────┘  │
│          │                                    │                     │
│          │                                    │                     │
│   ┌──────▼──────┐                     ┌───────▼───────┐            │
│   │  256 MB VM  │                     │  1 GB VM      │            │
│   │  (minimal)  │                     │  (Redis+API)  │            │
│   └─────────────┘                     └───────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

### Request Flow Example

1. **User opens** `https://portfolio-navigator.fly.dev`
2. **Frontend serves** React SPA (index.html, JS, CSS)
3. **User clicks** "Get Portfolio Recommendations"
4. **Frontend calls** `https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/recommendations/moderate`
5. **Backend checks** Redis cache for pre-generated portfolios
6. **Backend returns** portfolio data (or generates on-demand if lazy_generation=true)
7. **Frontend displays** the portfolio to the user

---

## Master List → Redis Data Flow

This section documents the complete data pipeline from source ticker lists to Redis storage.

### Master List Generation

The system uses a **validated ticker list** approach - only stocks confirmed to return valid Yahoo Finance data are included.

**Primary Source File:**
```
backend/scripts/reports/fetchable_master_list_validated_latest.csv
```

| Property | Value |
|----------|-------|
| Format | CSV with columns: `ticker`, `validated_date` |
| Ticker Count | ~1,432 validated tickers |
| Last Validated | Check file for latest date |
| Coverage | S&P 500 + NASDAQ 100 + Top 15 ETFs |

**Three-Tier Source Strategy:**

| Source | Method | Code Location |
|--------|--------|---------------|
| S&P 500 | Wikipedia scrape | `enhanced_data_fetcher.py:269-287` |
| NASDAQ 100 | Wikipedia scrape | `enhanced_data_fetcher.py:289-326` |
| Top 15 ETFs | Hardcoded list | `enhanced_data_fetcher.py:330-347` |

```
┌────────────────────────────────────────────────────────────────────┐
│                    MASTER LIST GENERATION                          │
│                                                                    │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐         │
│   │   S&P 500     │  │  NASDAQ 100   │  │  Top 15 ETFs  │         │
│   │  (Wikipedia)  │  │  (Wikipedia)  │  │  (Hardcoded)  │         │
│   └───────┬───────┘  └───────┬───────┘  └───────┬───────┘         │
│           └──────────────────┼──────────────────┘                  │
│                              ▼                                     │
│              ┌────────────────────────────┐                        │
│              │  Validation Process        │                        │
│              │  (Test each ticker on      │                        │
│              │   Yahoo Finance API)       │                        │
│              └────────────┬───────────────┘                        │
│                           ▼                                        │
│     ┌─────────────────────────────────────────────────────┐       │
│     │  fetchable_master_list_validated_latest.csv         │       │
│     │  Location: backend/scripts/reports/                 │       │
│     └─────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────────┘
```

### Loading Hierarchy

When the application needs the master ticker list, it checks sources in this order (`redis_first_data_service.py:219-311`):

```
┌────────────────────────────────────────────────────────────────────┐
│                    LOADING HIERARCHY                               │
│                                                                    │
│   1. Redis "master_ticker_list" ──────────► ✓ Use if found        │
│              │ not found                                           │
│              ▼                                                     │
│   2. Redis "master_ticker_list_validated" ─► ✓ Use if found       │
│              │ not found                                           │
│              ▼                                                     │
│   3. Redis "ticker_list:master" ──────────► ✓ Use if found        │
│              │ not found                                           │
│              ▼                                                     │
│   4. CSV File (PRIMARY FALLBACK) ─────────► ✓ Load & SEED Redis   │
│      fetchable_master_list_validated...     │ (365-day TTL)        │
│              │ not found                    │                      │
│              ▼                              │                      │
│   5. Cached tickers from price keys ──────► ✓ Use if found        │
│      (secondary fallback)                   │                      │
│              │ not found                                           │
│              ▼                                                     │
│   6. EnhancedDataFetcher (live scrape) ───► ✓ Scrape & seed Redis │
│      (last resort - S&P 500 + NASDAQ + ETFs)                       │
└────────────────────────────────────────────────────────────────────┘
```

**Key Design Decision**: The CSV master list is the **primary fallback** when Redis is empty, taking priority over cached price tickers. This ensures:
1. The authoritative validated ticker list is always used
2. Incomplete price cache data doesn't override the full master list
3. Consistent behavior across deployments

**Auto-Seeding Behavior**: When the CSV is loaded (step 4), the system automatically seeds Redis with a 365-day TTL, ensuring future loads use Redis cache.

### Yahoo Finance Fetching

**Data Source:** Yahoo Finance (free, no API key required)

| Library | Purpose | Fallback |
|---------|---------|----------|
| `yahooquery` | Primary data fetcher | Yes |
| `yfinance` | Backup if yahooquery fails | - |

**Fetching Parameters:**
```python
yq_ticker.history(
    start = 20 years ago,
    end = current month,
    interval = '1mo'  # Monthly data points
)
```

**Rate Limiting Configuration:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| BATCH_SIZE | 20 | Tickers per batch |
| RATE_LIMIT_DELAY | 4 seconds | Between batches |
| REQUEST_DELAY | 1.3-4.0 seconds | Random jitter |
| DAILY_REQUEST_LIMIT | 2000 | Avoid throttling |

### Redis Storage Schema

| Key Pattern | TTL | Content | Compression |
|-------------|-----|---------|-------------|
| `master_ticker_list` | 24 hours | Ticker list JSON | gzip |
| `master_ticker_list_validated` | 365 days | Validated list | gzip |
| `ticker_data:prices:{TICKER}` | 1 day ±10% | Monthly prices | gzip |
| `ticker_data:metrics:{TICKER}` | 1 day | Return, vol, sharpe | JSON |
| `ticker_data:sector:{TICKER}` | 7 days | Sector, company | JSON |
| `fx_rates:{CURRENCY}:USD` | 24 hours | Exchange rate | JSON |
| `portfolio_bucket:{profile}:{N}` | 3 days | Pre-generated portfolio | JSON |
| `strategy_portfolios:{profile}` | 2 days | Strategy results | JSON |

**Memory Configuration:**
```
MAX_MEMORY = 256mb
MAX_MEMORY_POLICY = allkeys-lru
TTL_JITTER_PERCENT = 10-15%  # Prevents cache stampede
```

---

## System Autonomy Assessment

### What IS Fully Automated

| Component | How It Works | Status |
|-----------|--------------|--------|
| **Cold Start Detection** | Checks Redis `dbsize()` on startup | ✅ Automatic |
| **Ticker List Loading** | Falls back through 6 sources (see hierarchy above) | ✅ Automatic |
| **CSV → Redis Seeding** | When CSV loaded, auto-seeds Redis with 365-day TTL | ✅ Automatic |
| **Price Data Fetching** | On-demand when cache miss occurs | ✅ Automatic |
| **TTL-Based Expiry** | Redis auto-expires keys per configured TTL | ✅ Automatic |
| **Cache Warm Endpoint** | `/api/v1/portfolio/warm-cache` available | ✅ Available |

### What Requires Manual Intervention

| Component | Current State | Impact |
|-----------|---------------|--------|
| **Redis Persistence** | ❌ Disabled (`--save ""`) | ALL DATA LOST on restart/deploy |
| **Scheduled Regeneration** | ❌ Script exists, no cron | Portfolios won't auto-regenerate |
| **Master List Refresh** | ❌ Static CSV | New IPOs/delistings not captured |
| **Post-Deploy Population** | ❌ Manual SSH required | 45 min - 2 hours manual work |

### Critical Gaps

**Gap 1: No Redis Persistence**
- Current Dockerfile: `--save "" --appendonly no`
- Impact: Every restart = complete data loss
- Severity: **CRITICAL**

**Gap 2: No Scheduled Jobs**
- Script exists: `backend/scripts/scheduled_regen.py`
- But: No cron, no timer, no scheduled Fly.io machine
- Impact: Portfolios become stale, no automatic refresh
- Severity: **HIGH**

**Gap 3: Static Master List**
- CSV is manually generated and committed
- No automated refresh for market changes
- Impact: Missing new listings, keeping delisted tickers
- Severity: **MEDIUM**

---

## Gap Resolution Plans

### Gap 1: Redis Data Persistence

**Problem:** Redis data is lost on every container restart because persistence is disabled.

**Current Configuration (Dockerfile):**
```dockerfile
CMD redis-server --daemonize yes \
        --save "" \              # ← No RDB snapshots
        --appendonly no \        # ← No AOF logging
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru
```

#### Solution Option A: Enable RDB Snapshots (Recommended for Fly.io)

**What it does:** Periodically saves Redis data to disk (`dump.rdb`).

**Modified Dockerfile CMD:**
```dockerfile
CMD redis-server --daemonize yes \
        --save 900 1 \
        --save 300 10 \
        --save 60 10000 \
        --dir /data \
        --dbfilename dump.rdb \
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru \
        --loglevel warning \
    && exec uvicorn main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8080}" \
        --workers 1
```

**Save intervals explained:**
| Interval | Condition | Meaning |
|----------|-----------|---------|
| `900 1` | After 900 sec (15 min) if at least 1 key changed | Infrequent changes |
| `300 10` | After 300 sec (5 min) if at least 10 keys changed | Moderate activity |
| `60 10000` | After 60 sec if at least 10000 keys changed | High activity |

**Required Fly.io Volume:**
```bash
# Create a persistent volume
fly volumes create redis_data --region arn --size 1

# Update fly.toml to mount the volume
[[mounts]]
  source = "redis_data"
  destination = "/data"
```

**Pros:** Simple, low overhead, survives restarts
**Cons:** May lose up to 15 minutes of data on crash

#### Solution Option B: Enable AOF (Append-Only File)

**What it does:** Logs every write operation to disk for full durability.

**Modified Dockerfile CMD:**
```dockerfile
CMD redis-server --daemonize yes \
        --appendonly yes \
        --appendfsync everysec \
        --dir /data \
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru \
        --loglevel warning \
    && exec uvicorn main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8080}" \
        --workers 1
```

**fsync options:**
| Option | Durability | Performance |
|--------|------------|-------------|
| `always` | Every write | Slowest |
| `everysec` | Every second | Balanced (recommended) |
| `no` | OS decides | Fastest, least durable |

**Pros:** Near-zero data loss
**Cons:** Slightly higher disk I/O, larger files

#### Solution Option C: Use Managed Redis (Upstash) ✅ IMPLEMENTED

**Status:** This option has been implemented as the production solution.

**What it does:** External managed Redis service with built-in persistence.

**Pricing (as of March 2025):**
| Component | Free Tier | Pay-As-You-Go |
|-----------|-----------|---------------|
| Commands | 500K/month | $0.20 per 100K |
| Storage | 256 MB | $0.25/GB |
| Bandwidth | 200 GB/month | $0.03/GB |

**Cost Estimate:**
- 300 users/month: **$0.00** (within free tier)
- 1,000 users/month: **$0.00** (within free tier)
- 2,000 users/month: **~$0.16** (80K commands overage)

**Setup Instructions:**

1. **Create Upstash Database:**
   - Go to https://console.upstash.com
   - Create new Redis database
   - **Region:** Choose `eu-central-1` (Frankfurt) — closest to `arn` (Stockholm)
   - **Type:** Regional (single region is sufficient)

2. **Copy Connection URL:**
   - Format: `rediss://default:xxxxxxxx@eu1-xxxxx.upstash.io:6379`
   - Note: Uses `rediss://` (with double 's') for TLS

3. **Set Fly.io Secret:**
   ```bash
   fly secrets set REDIS_URL="rediss://default:xxxxxxxx@eu1-xxxxx.upstash.io:6379"
   ```

4. **Deploy:**
   ```bash
   fly deploy --remote-only
   ```

5. **Verify:**
   ```bash
   curl https://portfolio-navigator-wizard.fly.dev/healthz
   ```

**Files Modified:**
- `Dockerfile` — Removed bundled Redis, connects to external Upstash
- `fly.toml` — Removed hardcoded REDIS_URL (now via secrets)
- `Dockerfile.local` — Created for local development with bundled Redis

**Pros:**
- Zero maintenance, automatic backups
- Data survives all restarts and deploys
- Scales automatically
- 99.99% SLA
- Free tier covers 300+ users/month

**Cons:**
- External dependency (+10-20ms latency)
- Free tier may archive after 14+ days of inactivity (data preserved, just needs wake-up request)

#### Recommended Approach

**Option C (Upstash)** is now the production configuration because:
1. **Persistent data** — Survives all restarts and deploys
2. **Zero cost** — Free tier covers expected usage (300 users/month)
3. **Zero maintenance** — No volumes, snapshots, or backup scripts needed
4. **Already implemented** — Dockerfile and fly.toml are configured

**Local Development:**
Use `Dockerfile.local` for local development with bundled Redis:
```bash
docker build -f Dockerfile.local -t portfolio-wizard-local .
docker run -p 8080:8080 portfolio-wizard-local
```

#### Assessment: How Each Solution Works on Fly.io and What It Costs

**Option A: RDB snapshots + Fly Volume**

How it works in practice:
- You add a Fly Volume (e.g. 1 GB) to the app and mount it at `/data`. Redis is started with `--dir /data` and RDB save rules so it writes `dump.rdb` to the volume.
- The volume is local NVMe on the same host as the Machine, one volume per Machine, one Machine per volume. It persists across process restarts (same Machine).
- On `fly deploy`: the current Machine is typically replaced by a new one. The old Machine’s volume is left unattached (volumes are not destroyed with the Machine). The new Machine needs a volume; Fly may attach an existing unattached volume in the region or create a new one. If the new Machine attaches the same volume, Redis will load the existing `dump.rdb` and data persists. If a new empty volume is attached, Redis starts empty and you must repopulate. So persistence across deploys is best-effort unless you use clone/attach explicitly.
- During deploy there is brief downtime (old Machine gone, new Machine starting). Fly recommends at least two Machines with volumes for production; with one Machine you accept downtime on deploy and hardware failure.
- Daily snapshots (default 5 days) are taken by Fly; from Jan 2026 snapshot storage is billed (first 10 GB free, then $0.08/GB/month). You can disable snapshots or reduce retention to lower cost.

Cost (Fly.io, approximate):
- Volume: **$0.15/GB per month** (pro-rated hourly). For 1 GB: about **$0.15/month**. You are charged whether the volume is attached or not.
- Snapshots (from Jan 2026): Redis uses ~30–50 MB; snapshot size is similar. Well under 10 GB, so **$0** with the free 10 GB.
- No extra compute: Redis runs in the same 1 GB VM as today. **Total extra: about $0.15/month** for 1 GB volume.

**Option B: AOF + Fly Volume**

How it works in practice:
- Same volume and mount as Option A. Redis runs with `--appendonly yes` and `--appendfsync everysec`, writing to `/data`. Every write is logged; on restart Redis replays the log.
- Same Fly volume behaviour as Option A: survives restarts on the same Machine; across deploys persistence depends on whether the new Machine gets the same volume.
- Better durability: at most about one second of writes can be lost. Slightly more disk I/O and larger on-disk size than RDB.

Cost:
- Same as Option A: **~$0.15/month** for 1 GB volume plus snapshot pricing from 2026 (still $0 for your size).

**Option C: Upstash (managed Redis)**

How it works in practice:
- Redis runs outside Fly.io. You create a Redis database at Upstash, get a URL (`rediss://...`), and set `REDIS_URL` in Fly secrets. The app connects over the internet to Upstash; no volume and no in-container Redis.
- Data is persistent and managed by Upstash (backups, durability). Survives Fly deploys and Machine restarts. You add an external dependency and network latency (Fly app in e.g. Stockholm to Upstash region you choose).
- Fly bills you for **egress to the internet** (and to extensions like Upstash) at data transfer rates (e.g. $0.02/GB for North America/Europe). Commands and responses count as egress from the app to Upstash.

Cost:
- Upstash free tier (as of 2024–2025): **$0/month**; 1 database, 256 MB, **500,000 commands/month**, 10 GB bandwidth. Inactivity (e.g. 14+ days) can lead to archival unless upgraded.
- If you exceed free tier: pay-as-you-go about **$0.20 per 100K commands**; or fixed plans from about **$10/month**.
- Fly.io: you pay **egress** to Upstash (e.g. $0.02/GB for NA/EU). Typical Redis traffic for this app is small (MB scale), so **well under $1/month** unless traffic grows.
- So: **$0/month** if within Upstash free tier and low egress; possible small egress charges on Fly; over free tier, Upstash cost can grow.

**Summary comparison**

| Criterion        | Option A (RDB + volume) | Option B (AOF + volume) | Option C (Upstash)        |
|-----------------|--------------------------|--------------------------|---------------------------|
| Persists on restart (same Machine) | Yes | Yes | N/A (always persistent) |
| Persists across deploy           | Best-effort (same volume reattach) | Same | Yes |
| Extra Fly cost (approx)          | ~$0.15/mo (1 GB volume) | ~$0.15/mo (1 GB volume) | Egress only (often &lt;$1) |
| External dependency              | No | No | Yes (Upstash + network) |
| Durability                       | Up to ~15 min loss (RDB) | ~1 s (AOF everysec) | Managed |
| Free tier / zero extra           | No (volume has a cost) | No (volume has a cost) | Yes (Upstash free tier) |

**Practical recommendation**

- If you want **lowest cost and can repopulate from CSV**: keep **no persistence** (current setup) and repopulate after each deploy; **$0** extra.
- If you want **persistence on Fly with minimal cost and no external service**: use **Option A** (RDB + 1 GB volume). Accept possible empty Redis after a deploy if a new volume is attached; then repopulate or restore from snapshot. **~$0.15/month**.
- If you want **persistence without caring about Fly volumes** and are fine with an external provider: use **Option C** (Upstash free tier). **$0** if within 500K commands/month and low egress; verify command usage and inactivity policy.

#### Option C (Upstash) in Detail: Webapp Impact, Users, Population, and Cost

If you choose Upstash, below is what it means for the webapp, how population works, what size and capacity you need, and what it costs (per operation and monthly).

**1. What it means for the webapp and for users**

- **Behaviour:** The app does not change. You only set `REDIS_URL` to the Upstash URL (`rediss://...`). The backend already supports TLS and `rediss://`; no code changes are required. All features (recommendations, strategy portfolios, search, optimization, exports) work the same.
- **For users:** From a user’s point of view nothing changes. Same UI, same flows, same data. The only possible difference is **latency**: each Redis call goes over the internet to Upstash instead of localhost. For a typical recommendation request that is a few dozen Redis round-trips, adding ~1–3 ms per round-trip can mean **roughly 50–150 ms extra** end-to-end, depending on Upstash region. Choosing an Upstash region close to your Fly region (e.g. EU) keeps this small.
- **Availability:** If Upstash is down or unreachable, Redis-dependent endpoints will fail (e.g. recommendations, cache-backed search). The app will log connection errors; you depend on Upstash’s SLA (and optional paid tier for higher SLA).
- **Data:** Data is stored in Upstash’s cloud, not on Fly. It persists across Fly deploys and restarts. No need to repopulate after a deploy.

**2. How population works with Upstash**

- **Same process as today.** Population is “your backend writes into whatever Redis `REDIS_URL` points to.” With Upstash, `REDIS_URL` points to Upstash, so all population goes there.
- **Ways to populate:**
  - **From your machine (HTTP):** Call the warm-cache endpoint. Your backend (on Fly) uses `REDIS_URL` (Upstash), so the cache is warmed **into Upstash**.  
    `curl -X POST https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/warm-cache -H "X-Admin-Key: YOUR_ADMIN_API_KEY"`  
    That only warms **ticker data**; it does **not** generate the 60 portfolio buckets.
  - **Full population (ticker data + 60 portfolios):** SSH into the Fly backend and run the manual population script (see “Manual Data Population” in this doc). The script runs on the Fly Machine and uses `REDIS_URL` from the environment, so it reads/writes **Upstash**. So you run the same script; only the Redis instance (Upstash) is different. Progress and behaviour are the same; runtime is similar (network latency to Upstash may add a few minutes over a full run).
- **After switching:** Set `REDIS_URL` to Upstash, deploy, then run one full population (SSH script or warm-cache + a way to generate portfolios). After that, data lives in Upstash and persists.

**3. Database size you need (storage)**

- **Current usage:** With ~1,432 tickers and 60 portfolios, Redis uses about **15–20 MB** in memory (see REDIS_MEMORY_ANALYSIS.md). Ticker data dominates (prices, sector, metrics); then master list, portfolio buckets, strategy/eligible caches.
- **Upstash free tier:** **256 MB** max data size. Your dataset fits easily; you have large headroom (e.g. up to ~20k–25k tickers before approaching 256 MB).
- **If you grow:** Upstash pay-as-you-go allows up to 100 GB; fixed plans start at 250 MB ($10/month). For the foreseeable scale of this app, **256 MB (free) is enough**.

**4. Operations (commands) and cost**

Upstash counts **every Redis command** (GET, SET, SETEX, KEYS, etc.) as one “command.”

- **One full population (ticker data + 60 portfolios):**
  - Ticker phase: ~1,432 tickers × ~4 commands per ticker (e.g. SETEX for prices, sector, metrics, info) ≈ **5,700–6,000** commands.
  - Master list and metadata: on the order of **10–20** commands.
  - Portfolio phase: 60 portfolios × a few commands each (e.g. SETEX per stored portfolio) ≈ **120–200** commands.
  - **Total per full population: ~6,000–8,000 commands.**
- **Per user request (e.g. one recommendation view):**
  - Recommendation path: metadata GET + a few portfolio GETs + optional ticker warming in background. Typical **~20–50** commands per recommendation view (depending on cache hits and background warming).
  - Search, strategy, optimization, etc. add more GETs/SETs; **~30–80** commands per “heavier” user action is a reasonable range.
- **Rough monthly command budget (free tier 500K):**
  - One full population: **~7,000** commands.
  - Remaining for traffic: 500,000 − 7,000 = **493,000** commands.
  - At 40 commands per “recommendation-style” request: **~12,300** such requests per month (~400/day).
  - At 80 commands per “heavier” action: **~6,100** such actions per month (~200/day).
  - So free tier supports **one full population per month** plus on the order of **hundreds of requests per day** (exact number depends on mix of endpoints and cache hits).

**5. Cost per operation and monthly**

- **Upstash free tier:** **$0/month.** Includes 256 MB, 500K commands/month, 10 GB bandwidth. No per-operation charge.
- **Upstash pay-as-you-go (if you exceed free):** **$0.20 per 100K commands.** So:
  - 1 command ≈ **$0.000002** (0.0002 cents).
  - One full population (~7K commands) ≈ **$0.014**.
  - 100K extra commands (e.g. extra traffic) = **$0.20**.
- **Monthly (ballpark):**
  - **Within free tier:** **$0** (Upstash). You may have a small **Fly egress** charge (data to Upstash), often **&lt;$1/month** for this app.
  - **Over free tier:** Example: 1M commands/month → 500K over free → **$1.00** on Upstash (plus Fly egress). Fixed 250 MB plan is **$10/month** with no per-command cost if you prefer predictable billing.
- **Storage (pay-as-you-go):** **$0.25/GB/month** for data over free; at 20–50 MB you stay within free 256 MB, so **$0** for storage at current scale.

**6. Summary before you proceed with Option C**

| Topic | Answer |
|-------|--------|
| Webapp / users | No change in features or UI; possible small latency increase (tens–low hundreds of ms) if Upstash is far from Fly. |
| Population | Same as now: set `REDIS_URL` to Upstash, then warm-cache and/or run the full population script (SSH). Data goes to Upstash. |
| Database size | 256 MB (free) is enough; you use ~15–20 MB today. |
| Commands | One full population ≈ 6K–8K; one recommendation-style request ≈ 20–50. Free tier 500K/month ≈ one population + hundreds of requests/day. |
| Cost per operation | Free tier: $0. Pay-as-you-go: $0.20/100K commands (~$0.000002 per command). |
| Monthly cost | Free: $0 (Upstash) + small Fly egress. Over free: e.g. $1 per 500K extra commands + Fly egress. |

You can proceed with Option C by creating an Upstash Redis database, copying the `rediss://` URL, and setting `REDIS_URL` in Fly secrets; then run one full population and monitor command usage in the Upstash console.

#### Upstash Cost Estimate for 300 Users/Month

Upstash pricing structure (as of March 2025):

| Component | Free Tier | Pay-As-You-Go |
|-----------|-----------|----------------|
| Commands | 500K/month | $0.20 per 100K beyond free |
| Storage | 256 MB | $0.25/GB |
| Bandwidth | 200 GB/month | $0.03/GB beyond free |

Your usage estimate:

| Metric | Your Usage | Free Tier | Overage |
|--------|------------|-----------|---------|
| Commands | ~87,000/month | 500,000 | $0.00 (within free) |
| Storage | ~20 MB | 256 MB | $0.00 (within free) |
| Bandwidth | ~2-3 GB/month | 200 GB | $0.00 (within free) |

Monthly cost breakdown (300 users/month):

- Commands: 87,000 / 500,000 free = $0.00
- Storage: 20 MB / 256 MB free = $0.00
- Bandwidth: 3 GB / 200 GB free = $0.00
- **TOTAL MONTHLY COST: $0.00** (covered by free tier)

With 300 users/month generating ~87K operations, you are well within Upstash's free tier of 500K commands. You could handle ~1,700 users/month before exceeding the free tier.

Scaling scenarios:

| Users/Month | Commands | Storage | Cost |
|-------------|----------|---------|------|
| 300 | 87K | 20 MB | $0.00 (free tier) |
| 500 | 145K | 20 MB | $0.00 (free tier) |
| 1,000 | 290K | 25 MB | $0.00 (free tier) |
| 1,700 | 500K | 30 MB | $0.00 (free tier limit) |
| 2,000 | 580K | 30 MB | $0.16 (80K overage) |
| 5,000 | 1.45M | 40 MB | $1.90 |
| 10,000 | 2.9M | 50 MB | $4.80 |

#### How Data Population Works with Upstash

**Current flow (bundled Redis):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                         │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              FLY.IO CONTAINER (1 GB VM)                 │  │
│   │                                                         │  │
│   │   ┌─────────────┐         ┌─────────────┐              │  │
│   │   │   FastAPI   │ ◄────► │   Redis     │              │  │
│   │   │   Backend   │  local  │  (bundled)  │              │  │
│   │   └─────────────┘         └─────────────┘              │  │
│   │                                                         │  │
│   │   Problem: Redis data lost on restart/deploy            │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**New flow (Upstash):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    UPSTASH ARCHITECTURE                         │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              FLY.IO CONTAINER (1 GB VM)                 │  │
│   │                                                         │  │
│   │   ┌─────────────┐                                       │  │
│   │   │   FastAPI   │                                       │  │
│   │   │   Backend   │                                       │  │
│   │   └──────┬──────┘                                       │  │
│   └──────────┼──────────────────────────────────────────────┘  │
│              │ TLS (rediss://)                                  │
│              ▼                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              UPSTASH REDIS (Managed)                    │  │
│   │                                                         │  │
│   │   ✓ Persistent storage                                  │  │
│   │   ✓ Automatic backups                                   │  │
│   │   ✓ Survives container restarts                         │  │
│   │   ✓ Global replication available                        │  │
│   │   ✓ REST API + Native Redis Protocol                    │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Population process with Upstash:**

1. **Initial setup (one-time):** Create Upstash database at https://console.upstash.com. Choose region eu-central-1 (Frankfurt), closest to arn (Stockholm). Get connection URL: `rediss://default:xxxxxxxx@eu1-xxxxx.upstash.io:6379`
2. **Configure Fly.io:** Set the Upstash URL as a secret: `fly secrets set REDIS_URL="rediss://default:xxxxxxxx@eu1-xxxxx.upstash.io:6379" -a portfolio-navigator-wizard`
3. **Modify Dockerfile (remove bundled Redis):** Change CMD from `redis-server --daemonize yes ... && exec uvicorn main:app ...` to `CMD exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1`
4. **Population on first startup:** App detects empty Redis, cold start triggers, CSV master list (1,432 tickers) loads, master list seeded to Upstash (365-day TTL), user requests trigger on-demand price fetching, ticker data cached as accessed. Timeline: master list seed ~2 seconds; full cache warm (all 1,432 tickers) ~45-90 minutes (rate limited); typical user flow works immediately (on-demand fetching).

#### What Option C (Upstash) Means: Before vs After

**For the webapp:**

| Aspect | Before (Bundled) | After (Upstash) |
|--------|------------------|-----------------|
| Data Persistence | Lost on restart | Permanent |
| Deploy Impact | Must repopulate | Zero downtime |
| Cold Start | 45-90 min warmup | Instant (data exists) |
| Maintenance | Manual monitoring | Managed by Upstash |
| Backups | None | Automatic daily |
| Scaling | 256 MB hard limit | Auto-scales |
| Latency | ~0.1 ms (local) | ~5-15 ms (network) |

**For users:**

| User Experience | Before | After (Upstash) |
|-----------------|--------|-----------------|
| First visit after deploy | Slow (data missing) | Fast (data persisted) |
| Portfolio generation | May fail if cache cold | Always works |
| Response time | ~50-100 ms | ~60-120 ms (+10-20 ms) |
| Availability | Dependent on container | 99.99% SLA |
| Data freshness | Resets on restart | Consistent TTL behavior |

Moving from local Redis to Upstash adds ~10-20 ms latency per operation. For portfolio generation (30-35 operations), that is ~300-700 ms additional time. Users typically do not notice because operations run in parallel where possible, total response time stays under 2 seconds, and the benefit of persistent data outweighs the latency cost.

#### Recommended Database Size (Upstash)

| Plan | Size | Price | Your fit |
|------|------|-------|----------|
| Free (Pay-as-you-go) | 256 MB | $0/month | Recommended |
| Fixed 250 MB | 250 MB | $10/month | Overkill for your usage |
| Fixed 1 GB | 1 GB | $20/month | Future scaling option |

Start with the Free Pay-as-you-go plan. You stay within free limits with 300 users/month; even at 2,000 users you would pay only ~$0.16/month.

#### Option C Implementation Checklist

- [ ] 1. Create Upstash account at https://console.upstash.com
- [ ] 2. Create Redis database (choose eu-central-1 region)
- [ ] 3. Copy connection URL (rediss://...)
- [ ] 4. Set Fly.io secret: `fly secrets set REDIS_URL="rediss://..." -a portfolio-navigator-wizard`
- [ ] 5. Update Dockerfile (remove redis-server command)
- [ ] 6. Deploy: `fly deploy -a portfolio-navigator-wizard`
- [ ] 7. Verify: `curl https://portfolio-navigator-wizard.fly.dev/healthz`
- [ ] 8. Trigger initial population via admin endpoint or let it auto-populate

#### Option C Summary (Quick Reference)

| Question | Answer |
|----------|--------|
| Monthly cost for 300 users? | $0.00 (free tier covers it) |
| When do you start paying? | ~1,700+ users/month |
| Database size needed? | 256 MB (free tier) is plenty |
| Data persistence? | Yes – survives all restarts |
| User impact? | Faster first-load, consistent experience |
| Implementation effort? | ~30 minutes (config change only) |

### Gap 2: Scheduled Jobs

**Problem:** Portfolio regeneration script exists but is never automatically invoked.

#### Solution Option A: Fly.io Scheduled Machine (Recommended)

**Create a separate scheduled machine that runs weekly:**

**1. Create `fly.scheduled.toml`:**
```toml
app = "portfolio-navigator-scheduler"
primary_region = "arn"

[build]
  dockerfile = "Dockerfile.scheduler"

[env]
  REDIS_URL = "redis://portfolio-navigator-wizard.internal:6379"
  PYTHONPATH = "/app"

# No HTTP service - this is a one-shot job
[[services]]
  # Empty - no HTTP service needed

[processes]
  scheduler = "python scripts/scheduled_regen.py"
```

**2. Create `Dockerfile.scheduler`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV PYTHONPATH=/app

CMD ["python", "scripts/scheduled_regen.py"]
```

**3. Deploy and schedule:**
```bash
# Deploy the scheduler app
fly launch --config fly.scheduled.toml --no-deploy
fly deploy --config fly.scheduled.toml

# Schedule to run every Sunday at 2 AM UTC
fly machines run \
  --app portfolio-navigator-scheduler \
  --schedule "0 2 * * 0" \
  --restart on-failure
```

#### Solution Option B: External Cron Service (cron-job.org)

**Free external cron service that hits your API:**

**1. Create a regeneration endpoint (add to `backend/routers/admin.py`):**
```python
@router.post("/regenerate-all")
async def regenerate_all_portfolios(
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """Regenerate all portfolio buckets (admin only)"""
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from utils.portfolio_auto_regeneration_service import PortfolioAutoRegenerationService
    service = PortfolioAutoRegenerationService()
    result = service.regenerate_all()
    return {"status": "success", "result": result}
```

**2. Set up cron-job.org:**
- URL: `https://portfolio-navigator-wizard.fly.dev/api/v1/admin/regenerate-all`
- Method: POST
- Headers: `X-Admin-Key: YOUR_ADMIN_API_KEY`
- Schedule: Weekly (e.g., Sunday 02:00 UTC)

**Pros:** No infrastructure changes needed
**Cons:** Requires admin endpoint, external dependency

#### Solution Option C: Startup Hook with Age Check

**Auto-regenerate on startup if portfolios are stale:**

**Add to `backend/main.py` (in the lifespan function):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing cold start detection...

    # Check portfolio age and regenerate if stale
    try:
        from utils.portfolio_auto_regeneration_service import PortfolioAutoRegenerationService

        # Check if portfolios are older than 7 days
        stats_key = "portfolio:stats:moderate"
        stats_raw = redis_first_data_service.redis_client.get(stats_key)

        should_regenerate = False
        if not stats_raw:
            should_regenerate = True
        else:
            stats = json.loads(stats_raw)
            generated_at = datetime.fromisoformat(stats.get('generated_at', '').replace('Z', '+00:00'))
            age_days = (datetime.now(timezone.utc) - generated_at).days
            if age_days > 7:
                should_regenerate = True
                logger.info(f"📅 Portfolios are {age_days} days old, regenerating...")

        if should_regenerate:
            service = PortfolioAutoRegenerationService()
            asyncio.create_task(service.regenerate_all_async())
            logger.info("🔄 Background portfolio regeneration started")
    except Exception as e:
        logger.warning(f"⚠️ Portfolio age check failed: {e}")

    yield
    # Shutdown...
```

**Pros:** No external dependencies, self-healing
**Cons:** Regeneration only happens on restart, not on schedule

#### Recommended Approach

Use **Option C (Startup Hook)** combined with **Option B (External Cron)** for best coverage:
1. Startup hook ensures freshness after restarts
2. External cron ensures weekly refresh even if no restarts occur

### Gap 3: Master List Auto-Refresh

**Problem:** The CSV master list is static and doesn't adapt to market changes.

#### Solution: Monthly Validation Job

**Create `backend/scripts/refresh_master_list.py`:**
```python
#!/usr/bin/env python3
"""
Monthly master list refresh script.
- Re-scrapes S&P 500 and NASDAQ 100 from Wikipedia
- Validates each ticker against Yahoo Finance
- Updates the CSV file
- Seeds Redis with new validated list
"""

import os
import sys
import csv
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.enhanced_data_fetcher import EnhancedDataFetcher

def refresh_master_list():
    print(f"🔄 Starting master list refresh at {datetime.now().isoformat()}")

    fetcher = EnhancedDataFetcher()

    # Get fresh tickers from sources
    all_tickers = fetcher.all_tickers
    print(f"📋 Found {len(all_tickers)} tickers from sources")

    # Validate each ticker
    validated = []
    for ticker in all_tickers:
        try:
            prices = fetcher.fetch_ticker_data(ticker)
            if prices and len(prices) >= 12:
                validated.append({
                    'ticker': ticker,
                    'validated_date': datetime.now().isoformat()
                })
        except Exception:
            pass

    print(f"✅ Validated {len(validated)} tickers")

    # Write to CSV
    csv_path = os.path.join(
        os.path.dirname(__file__),
        "reports",
        "fetchable_master_list_validated_latest.csv"
    )

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ticker', 'validated_date'])
        writer.writeheader()
        writer.writerows(validated)

    print(f"📝 Written to {csv_path}")

    # Seed Redis
    from utils.redis_first_data_service import redis_first_data_service
    import gzip
    import json

    tickers_list = [v['ticker'] for v in validated]
    compressed = gzip.compress(json.dumps(tickers_list).encode())
    redis_first_data_service.redis_client.setex(
        "master_ticker_list_validated",
        365 * 24 * 3600,
        compressed
    )
    print("✅ Redis seeded with new master list")

if __name__ == '__main__':
    refresh_master_list()
```

**Schedule:** Run monthly via cron-job.org or Fly.io scheduled machine.

---

## Redis Data Lifecycle

### What Happens When You Populate Data

```
BEFORE POPULATION:
┌─────────────────────────────────────────┐
│              REDIS (Empty)              │
│                                         │
│   Keys: 0                               │
│   Memory: ~1 MB                         │
│   Portfolios: 0/60                      │
└─────────────────────────────────────────┘

AFTER POPULATION:
┌─────────────────────────────────────────┐
│           REDIS (Populated)             │
│                                         │
│   ticker_data:prices:AAPL    (28 days)  │
│   ticker_data:prices:MSFT    (28 days)  │
│   ticker_data:metrics:AAPL   (28 days)  │
│   portfolio_bucket:moderate:1 (28 days) │
│   portfolio_bucket:moderate:2 (28 days) │
│   ... (hundreds of keys)                │
│                                         │
│   Keys: ~500-1000                       │
│   Memory: ~30-50 MB                     │
│   Portfolios: 60/60                     │
└─────────────────────────────────────────┘
```

### Data Persistence: The Critical Point

**Redis data is NOT persistent by default in your Fly.io setup.**

The Dockerfile configures Redis with:
```bash
redis-server --daemonize yes \
    --save "" \              # No disk persistence
    --appendonly no \        # No AOF persistence
    --maxmemory 256mb \
    --maxmemory-policy allkeys-lru
```

For a full breakdown of key namespaces, sizes, and why 256 MB is suitable, see [REDIS_MEMORY_ANALYSIS.md](REDIS_MEMORY_ANALYSIS.md).

#### What This Means:

| Event | What Happens to Redis Data |
|-------|---------------------------|
| Normal operation | Data stays in memory ✅ |
| Machine restart | **ALL DATA LOST** ❌ |
| Deployment (fly deploy) | **ALL DATA LOST** ❌ |
| Machine crash | **ALL DATA LOST** ❌ |
| Fly.io maintenance | **ALL DATA LOST** ❌ |

#### Example Scenario:

```
Day 1, 10:00 AM: You populate Redis with 60 portfolios
Day 1, 10:30 AM: Users happily use the app ✅
Day 2, 02:00 AM: Fly.io does maintenance, machine restarts
Day 2, 02:01 AM: Redis starts fresh, 0 portfolios
Day 2, 08:00 AM: User visits, sees empty data ❌
```

#### How the App Handles This (Cold Start Detection):

The backend detects empty Redis on startup and:
1. Logs a warning: "🧊 COLD START DETECTED - Redis is empty"
2. Sends email notification (if configured)
3. Can auto-regenerate portfolios (if MANUAL_REGENERATION_REQUIRED=false)

```python
# From main.py - Cold start detection
if db_size == 0 or (price_key_count == 0 and portfolio_key_count == 0):
    is_cold_start = True
    logger.warning("🧊 COLD START DETECTED - Redis is empty")
    send_notification(
        title="Cold start detected - Redis empty",
        severity="CRITICAL",
        message="Container restarted and Redis has no data..."
    )
```

### When to Worry About Redis Data Loss

**Only worry about the BACKEND restarting** — the frontend has nothing to do with Redis.

Redis lives INSIDE the backend container:

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│         FRONTEND                │     │          BACKEND                │
│    (nginx + static files)       │     │  ┌─────────────────────────┐   │
│                                 │     │  │       REDIS             │   │
│    No Redis here!               │     │  │   (data lives here)     │   │
│    Can restart freely ✅        │     │  └─────────────────────────┘   │
│                                 │     │  ┌─────────────────────────┐   │
│                                 │     │  │      FastAPI            │   │
│                                 │     │  └─────────────────────────┘   │
└─────────────────────────────────┘     └─────────────────────────────────┘
     Restart = No data loss                 Restart = ALL DATA LOST
```

#### Quick Reference: When to Worry

| Event | Redis Data | Worry? |
|-------|------------|--------|
| Frontend stops/restarts | **Safe** ✅ | No |
| Frontend suspended (idle) | **Safe** ✅ | No |
| `fly deploy` frontend | **Safe** ✅ | No |
| Backend keeps running normally | **Safe** ✅ | No |
| `fly deploy` backend | **LOST** ❌ | **YES** |
| Backend machine restarts | **LOST** ❌ | **YES** |
| Backend crashes | **LOST** ❌ | **YES** |
| Fly.io maintenance on backend | **LOST** ❌ | **YES** |

#### Practical Implication:

- **Deploy frontend anytime** — no impact on data
- **Deploy backend carefully** — repopulate Redis after each deploy
- Your `min_machines_running = 1` on backend helps prevent unnecessary restarts

---

## Auto-Stop Behavior

### Why Frontend Shows "Suspended" or "Stopped"

This is **intentional and saves you money**.

#### Frontend Configuration (fly.toml):
```toml
[http_service]
  auto_stop_machines   = true    # ← Stop when no traffic
  auto_start_machines  = true    # ← Start when request comes
  min_machines_running = 0       # ← Can stop all machines
```

#### Backend Configuration (fly.toml):
```toml
[http_service]
  auto_stop_machines   = false   # ← Never stop
  auto_start_machines  = true
  min_machines_running = 1       # ← Always keep 1 running
```

### Timeline Example:

```
12:00 PM - User visits frontend
           └─ Frontend machine: STARTING → STARTED (2-3 seconds)
           └─ User sees the app

12:05 PM - User leaves
           └─ Frontend still running (grace period)

12:35 PM - No traffic for 30 minutes
           └─ Frontend machine: STARTED → STOPPING → STOPPED
           └─ Frontend shows "suspended" in Fly.io dashboard

01:00 PM - Another user visits
           └─ Frontend machine: STOPPED → STARTING → STARTED (2-3 seconds)
           └─ User sees the app (small delay on first request)

MEANWHILE, BACKEND:
           └─ Always STARTED
           └─ Never stops
           └─ No cold start delays for API calls
```

### Cost Implications:

| Service | Running Hours/Day | Approximate Cost |
|---------|-------------------|------------------|
| Frontend (auto-stop) | ~2-4 hours (when used) | ~$0.50-1/month |
| Backend (always on) | 24 hours | ~$5-7/month |

---

## Manual Data Population

> **Note (Upstash):** With Upstash configured, data persists across restarts. You only need to run manual population **once** after initial Upstash setup, or if you want to refresh all ticker data. The scripts below work identically whether using bundled Redis or Upstash.

### SSH Into the Backend Machine

```bash
fly ssh console -a portfolio-navigator-wizard
```

### Option 1: Run the Fetch Script with Progress Logging

Once inside the machine, create and run this script:

```python
#!/usr/bin/env python3
"""
Manual Data Population Script with Progress Logging
Run this inside the Fly.io machine via: fly ssh console -a portfolio-navigator-wizard
"""

import sys
import time
import logging
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def log_progress(step: int, total: int, message: str):
    """Log progress with percentage"""
    pct = (step / total) * 100
    bar_len = 30
    filled = int(bar_len * step / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"\r[{bar}] {pct:5.1f}% | Step {step}/{total} | {message}", end='', flush=True)

def main():
    start_time = time.time()
    print("=" * 70)
    print("PORTFOLIO NAVIGATOR WIZARD - DATA POPULATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Step 1: Initialize services
    print("\n📦 STEP 1/5: Initializing services...")
    from utils.redis_first_data_service import RedisFirstDataService
    rds = RedisFirstDataService()

    if not rds.redis_client:
        print("❌ ERROR: Cannot connect to Redis!")
        sys.exit(1)

    db_size = rds.redis_client.dbsize()
    print(f"   ✅ Redis connected. Current keys: {db_size}")

    # Step 2: Get ticker list (property: all_tickers; may load from Redis, CSV, or EnhancedDataFetcher)
    print("\n📋 STEP 2/5: Loading ticker list...")
    tickers = rds.all_tickers
    if not tickers:
        print("   ⚠️  No tickers found. Ensure master list exists in Redis, or CSV at data/ticker_backup.csv, or EnhancedDataFetcher will provide defaults.")
    print(f"   ✅ Found {len(tickers)} tickers to process")

    # Step 3: Fetch ticker data
    print("\n📊 STEP 3/5: Fetching ticker data...")
    total = len(tickers)
    success = 0
    failed = []

    for i, ticker in enumerate(tickers, 1):
        try:
            log_progress(i, total, f"Fetching {ticker}...")
            rds.get_monthly_data(ticker)
            rds.get_ticker_info(ticker)
            try:
                rds.get_cached_metrics(ticker)
            except:
                pass
            success += 1
        except Exception as e:
            failed.append(ticker)

    print(f"\n   ✅ Fetched {success}/{total} tickers")
    if failed:
        print(f"   ⚠️  Failed: {failed[:10]}{'...' if len(failed) > 10 else ''}")

    # Step 4: Generate portfolios
    print("\n🎯 STEP 4/5: Generating portfolios...")
    from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
    from utils.redis_portfolio_manager import RedisPortfolioManager

    generator = EnhancedPortfolioGenerator()
    manager = RedisPortfolioManager()

    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    portfolios_per_profile = 12

    total_portfolios = len(risk_profiles) * portfolios_per_profile
    generated = 0

    for profile in risk_profiles:
        print(f"\n   Generating {portfolios_per_profile} portfolios for '{profile}'...")
        for j in range(portfolios_per_profile):
            try:
                log_progress(generated + 1, total_portfolios, f"{profile} #{j+1}")
                portfolio = generator.generate_portfolio(risk_profile=profile)
                if portfolio:
                    manager.store_portfolio(profile, portfolio)
                    generated += 1
            except Exception as e:
                print(f"\n   ⚠️  Failed to generate {profile} #{j+1}: {e}")

    print(f"\n   ✅ Generated {generated}/{total_portfolios} portfolios")

    # Step 5: Verify
    print("\n✅ STEP 5/5: Verification...")
    final_db_size = rds.redis_client.dbsize()
    price_keys = len(rds.redis_client.keys("ticker_data:prices:*"))
    portfolio_keys = len(rds.redis_client.keys("portfolio_bucket:*"))

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("POPULATION COMPLETE")
    print("=" * 70)
    print(f"   Total Redis keys: {final_db_size}")
    print(f"   Price data keys:  {price_keys}")
    print(f"   Portfolio keys:   {portfolio_keys}")
    print(f"   Time elapsed:     {elapsed:.1f} seconds")
    print("=" * 70)

if __name__ == "__main__":
    main()
```

### Option 2: Use Existing Admin Endpoints

From your local machine (with ADMIN_API_KEY). Use a **single-line** curl so the URL is not broken by copy-paste:

```bash
# Warm the cache (fetches ticker data). Replace YOUR_ADMIN_API_KEY with the value from Fly secrets.
curl -X POST "https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/warm-cache" -H "X-Admin-Key: YOUR_ADMIN_API_KEY"
```

The request can take 45–90 minutes; curl will not show progress until it finishes. To see progress, run in another terminal: `fly logs -a portfolio-navigator-wizard`.

```bash
# Check status
curl https://portfolio-navigator-wizard.fly.dev/api/v1/enhanced-portfolio/buckets
```

### Option 3: Simple Commands via SSH

```bash
# SSH into the machine
fly ssh console -a portfolio-navigator-wizard

# Inside the machine, run Python
python3 << 'EOF'
from utils.redis_first_data_service import RedisFirstDataService
rds = RedisFirstDataService()
print(f"Redis keys: {rds.redis_client.dbsize()}")
result = rds.warm_cache()
print(f"Warm cache result: {result}")
EOF
```

### Populate Redis on Fly.io: Step-by-Step (with progress and time estimate)

Use this when the backend has just been deployed or restarted and Redis is empty. The app runs in `/app` with `PYTHONPATH=/app`; the script below must run in that environment.

**1. Open an SSH session to the backend app**

From your local machine (with Fly CLI installed and logged in):

```bash
fly ssh console -a portfolio-navigator-wizard
```

**2. Ensure you are in the app directory**

Inside the SSH session:

```bash
cd /app
export PYTHONPATH=/app
```

**3. Run the full population script (ticker data + 60 portfolios)**

Paste and run the full Python script from Option 1 above (the "Manual Data Population Script with Progress Logging"). It will:

- Step 1/5: Connect to Redis and report current key count.
- Step 2/5: Load ticker list (`rds.all_tickers`); if Redis is empty, tickers come from CSV or EnhancedDataFetcher.
- Step 3/5: For each ticker, fetch monthly data, ticker info, and metrics; a progress bar shows "Step i/N" and percentage.
- Step 4/5: Generate 60 portfolios (5 risk profiles × 12 each) with a progress bar per profile.
- Step 5/5: Print final Redis key counts and elapsed time.

**4. Follow progress**

- Progress bars: `[████████░░░░...] 40.0% | Step 120/300 | Fetching AAPL...` (tickers) and similar for portfolios.
- Do not close the SSH session until the script exits and prints "POPULATION COMPLETE".
- To only warm ticker data (no portfolios) from outside the machine, use Option 2:  
  `curl -X POST https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/warm-cache -H "X-Admin-Key: YOUR_ADMIN_API_KEY"`  
  That does not generate the 60 portfolio buckets; for a full website you need the SSH script (Option 1).

**5. Verify after the script finishes**

From your machine:

```bash
curl https://portfolio-navigator-wizard.fly.dev/api/v1/enhanced-portfolio/buckets
curl https://portfolio-navigator-wizard.fly.dev/healthz
```

You should see bucket counts (e.g. 12 per profile) and a healthy status.

**Time estimate**

| Phase | Typical duration |
|-------|-------------------|
| Ticker data (Step 3) | 30–90 minutes (depends on ticker count and Yahoo/API rate limits) |
| Portfolio generation (Step 4) | 5–15 minutes (60 portfolios, MVO and metrics) |
| **Total** | **About 45 minutes to 2 hours** |

If the ticker list is small (e.g. from a minimal CSV) or you only run warm-cache (tickers only), ticker phase can be as short as 10–20 minutes. The 1–2 hour range is for a full ticker set (hundreds of symbols) and all 60 portfolios.

---

## Monitoring and Maintenance

### Check System Health

```bash
# Health check
curl https://portfolio-navigator-wizard.fly.dev/healthz

# Portfolio bucket status
curl https://portfolio-navigator-wizard.fly.dev/api/v1/enhanced-portfolio/buckets

# View logs
fly logs -a portfolio-navigator-wizard
```

### Verify Redis population (one-off SSH)

To confirm Upstash Redis is connected and fully populated from the backend machine:

```bash
fly ssh console -a portfolio-navigator-wizard -C '/bin/sh -c "cd /app && PYTHONPATH=/app python3 -c \"from utils.redis_first_data_service import RedisFirstDataService; rds = RedisFirstDataService(); print(\\\"Redis keys:\\\", rds.redis_client.dbsize() if rds.redis_client else \\\"no redis\\\"); st = rds.get_cache_status() if rds.redis_client else {}; print(\\\"Cache status:\\\", st)\""'
```

Interpretation: `redis: available`, `price_cache_coverage: 100.0`, `sector_cache_coverage: 100.0`, `metrics_cache_coverage: 100.0`, and `cached_tickers_*` close to `total_tickers` means Redis is fully populated. Alternatively use the admin endpoint (with X-Admin-Key): `GET /api/v1/portfolio/cache-status`.

### Email Notifications

With your SMTP configured, you'll receive emails for:
- Cold start detection (Redis empty after restart)
- HTTP 5xx errors
- Cache expiration warnings
- Critical system events

### Scheduled Maintenance

Consider setting up a cron job or Fly.io scheduled machine to:
1. Refresh ticker data weekly
2. Regenerate portfolios monthly
3. Monitor Redis memory usage

---

## Quick Reference Commands

```bash
# View backend logs
fly logs -a portfolio-navigator-wizard

# View frontend logs
fly logs -a portfolio-navigator

# SSH into backend
fly ssh console -a portfolio-navigator-wizard

# Restart backend
fly machines restart -a portfolio-navigator-wizard --force

# Check secrets
fly secrets list -a portfolio-navigator-wizard

# Deploy backend
cd /path/to/project && fly deploy -a portfolio-navigator-wizard

# Deploy frontend
cd /path/to/project/frontend && fly deploy -a portfolio-navigator
```

---

## Quick Deploy Guide: After Committing Changes

This is the step-by-step process to deploy your changes and see them live immediately.

### Prerequisites

- Fly CLI installed (`brew install flyctl` or see https://fly.io/docs/hands-on/install-flyctl/)
- Logged in to Fly.io (`fly auth login`)
- Changes committed to git (recommended but not required for deploy)

### Step 1: Determine What Changed

| If you changed... | Deploy... |
|-------------------|-----------|
| Frontend only (`frontend/src/`, `frontend/public/`) | Frontend only |
| Backend only (`backend/`, `Dockerfile`, `fly.toml`) | Backend only |
| Both frontend and backend | Both (backend first recommended) |

### Step 2: Deploy

**Frontend only:**
```bash
cd frontend
fly deploy --remote-only
```

**Backend only:**
```bash
cd /path/to/portfolio-navigator-wizard
fly deploy --remote-only
```

**Both (run in sequence):**
```bash
# Backend first (contains API changes)
fly deploy --remote-only

# Then frontend
cd frontend
fly deploy --remote-only
```

### Step 3: Verify Deployment

```bash
# Check backend status and health
fly status -a portfolio-navigator-wizard
curl https://portfolio-navigator-wizard.fly.dev/healthz

# Check frontend status
fly status -a portfolio-navigator

# Visit the app
open https://portfolio-navigator.fly.dev
```

### Step 4: Monitor (if needed)

```bash
# Watch backend logs in real-time
fly logs -a portfolio-navigator-wizard

# Watch frontend logs
fly logs -a portfolio-navigator
```

### Complete Example Workflow

```bash
# 1. Make your code changes
# 2. Test locally (optional but recommended)
npm run dev  # frontend
uvicorn main:app --reload  # backend

# 3. Commit changes
git add .
git commit -m "feat: add new portfolio feature"

# 4. Deploy backend (if changed)
cd /path/to/portfolio-navigator-wizard
fly deploy --remote-only

# 5. Deploy frontend (if changed)
cd frontend
fly deploy --remote-only

# 6. Verify
curl https://portfolio-navigator-wizard.fly.dev/healthz
open https://portfolio-navigator.fly.dev

# 7. (Optional) Push to GitHub
git push origin main
```

### Deployment Times

| Service | Typical Deploy Time |
|---------|---------------------|
| Frontend | 1-2 minutes |
| Backend | 2-3 minutes |

### Troubleshooting

**Deploy fails with build error:**
```bash
# Check build logs in detail
fly logs -a portfolio-navigator-wizard

# Try rebuilding without cache
fly deploy --remote-only --no-cache
```

**App shows "stopped" or "suspended" after deploy:**

This is normal for the **frontend** (auto-stops when idle). It will auto-start on first request.

For the **backend**, it should always be running. If stopped:
```bash
fly machine start -a portfolio-navigator-wizard
```

**Health check failing:**
```bash
# Check what's happening
fly logs -a portfolio-navigator-wizard

# SSH in to debug
fly ssh console -a portfolio-navigator-wizard
```

**Changes not visible in browser:**
1. Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. Clear browser cache
3. Check the correct version deployed: `fly releases -a portfolio-navigator`

### Configuration Reference

The deployment behavior is controlled by `fly.toml`:

**Backend (`fly.toml`):**
```toml
[http_service]
  auto_stop_machines = 'off'    # Never stops
  min_machines_running = 1      # Always keep 1 running
```

**Frontend (`frontend/fly.toml`):**
```toml
[http_service]
  auto_stop_machines = true     # Stops when idle (saves money)
  min_machines_running = 0      # Can stop all machines
```

---

## Summary: What Happens When...

| Scenario | Frontend | Backend | Redis Data |
|----------|----------|---------|------------|
| No visitors for 30 min | Stops (suspended) | Keeps running | Preserved (Upstash) |
| User visits after idle | Auto-starts (2-3s delay) | Already running | Preserved |
| You run `fly deploy` frontend | Restarts | Unaffected | Preserved |
| You run `fly deploy` backend | Unaffected | Restarts | Preserved (Upstash) |
| Machine crashes | Auto-restarts | Auto-restarts | Preserved (Upstash) |
| Memory limit hit | N/A | LRU eviction | Oldest keys removed |

---

*Last Updated: 2026-03-04*
