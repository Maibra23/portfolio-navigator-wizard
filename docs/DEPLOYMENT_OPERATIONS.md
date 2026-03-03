# Portfolio Navigator Wizard - Deployment Operations Guide

## Table of Contents
1. [Current Deployment Status](#current-deployment-status)
2. [How the System Works](#how-the-system-works)
3. [Redis Data Lifecycle](#redis-data-lifecycle)
4. [Auto-Stop Behavior (Why Frontend Shows "Suspended")](#auto-stop-behavior)
5. [Manual Data Population](#manual-data-population)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Current Deployment Status

| Service | URL | Always Running? |
|---------|-----|-----------------|
| **Frontend** | https://portfolio-navigator-frontend.fly.dev | No (auto-stops when idle) |
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

1. **User opens** `https://portfolio-navigator-frontend.fly.dev`
2. **Frontend serves** React SPA (index.html, JS, CSS)
3. **User clicks** "Get Portfolio Recommendations"
4. **Frontend calls** `https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/recommendations/moderate`
5. **Backend checks** Redis cache for pre-generated portfolios
6. **Backend returns** portfolio data (or generates on-demand if lazy_generation=true)
7. **Frontend displays** the portfolio to the user

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
    --maxmemory 128mb \
    --maxmemory-policy allkeys-lru
```

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

    # Step 2: Get ticker list
    print("\n📋 STEP 2/5: Loading ticker list...")
    tickers = rds.get_ticker_list()
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

From your local machine (with ADMIN_API_KEY):

```bash
# Warm the cache (fetches ticker data)
curl -X POST https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/warm-cache \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY"

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
fly logs -a portfolio-navigator-frontend

# SSH into backend
fly ssh console -a portfolio-navigator-wizard

# Restart backend
fly machines restart -a portfolio-navigator-wizard --force

# Check secrets
fly secrets list -a portfolio-navigator-wizard

# Deploy backend
cd /path/to/project && fly deploy -a portfolio-navigator-wizard

# Deploy frontend
cd /path/to/project/frontend && fly deploy -a portfolio-navigator-frontend
```

---

## Summary: What Happens When...

| Scenario | Frontend | Backend | Redis Data |
|----------|----------|---------|------------|
| No visitors for 30 min | Stops (suspended) | Keeps running | Preserved |
| User visits after idle | Auto-starts (2-3s delay) | Already running | Preserved |
| You run `fly deploy` | Restarts | Restarts | **LOST** |
| Machine crashes | Auto-restarts | Auto-restarts | **LOST** |
| Memory limit hit | N/A | LRU eviction | Oldest keys removed |

---

*Last Updated: 2026-03-03*
