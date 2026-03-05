# Upstash to Redis Cloud Migration Guide

This document is a step-by-step plan to migrate from Upstash to Redis Cloud (free tier). Follow it manually in order. The recommended migration method is the Python script (Method 3); the other two methods are documented as alternatives.

---

## 1. Why Migrate

- **Upstash**: Free tier is 500K commands/month. This project uses ~630K commands/week, so you exceed the free tier and incur cost (~$0.80+/month).
- **Redis Cloud**: Free tier is 30 MB storage and **unlimited commands**. Your current data fits in ~11.3 MB, so you stay within the free tier at $0/month.

Key difference: Redis Cloud limits **storage**, not commands. Your usage is command-heavy and storage-light, so Redis Cloud free tier is a better fit.

---

## 2. Redis Cloud Free Tier Specifications

| Feature        | Value                                                |
|----------------|------------------------------------------------------|
| Storage        | 30 MB                                                |
| Commands       | Unlimited                                            |
| Connections    | 30 concurrent                                        |
| Persistence    | Yes (RDB snapshots)                                  |
| Regions        | AWS: eu-west-1, us-east-1, ap-southeast-1            |
| Availability   | 99.9% SLA                                            |
| Data eviction  | None (hard limit at 30 MB)                           |

Insight: Your ~630K commands/week cost $0 on Redis Cloud. The only constraint is the 30 MB storage limit.

---

## 3. Storage Analysis for This Project

Estimated usage based on the codebase (redis_first_data_service, redis_portfolio_manager, strategy_portfolio_optimizer, etc.):

### 3.1 Ticker data (largest part)

| Key pattern                    | Per-ticker size   | Ticker count | Total   |
|--------------------------------|-------------------|-------------|---------|
| ticker_data:prices:{ticker}    | ~3–5 KB (gzipped) | 1,432       | ~5.7 MB |
| ticker_data:sector:{ticker}    | ~0.5–1 KB (JSON)  | 1,432       | ~1.1 MB |
| ticker_data:metrics:{ticker}   | ~0.5–1 KB (JSON)  | 1,432       | ~1.1 MB |
| ticker_data:meta:{ticker}      | ~0.3 KB (JSON)    | 1,432       | ~0.4 MB |
| **Subtotal**                    | ~5–7 KB average   | 1,432       | **~8.3 MB** |

### 3.2 Portfolio buckets (5 risk profiles × 12 portfolios)

| Key pattern                         | Per-item size  | Count | Total   |
|-------------------------------------|----------------|-------|---------|
| portfolio_bucket:{profile}:{0–11}   | ~8–12 KB (JSON)| 60    | ~600 KB |
| portfolio_bucket:{profile}:metadata | ~0.5 KB        | 5     | ~2.5 KB |
| **Subtotal**                         |                |       | **~0.6 MB** |

### 3.3 Strategy portfolios

| Key pattern                                | Per-item size | Count        | Total   |
|--------------------------------------------|---------------|-------------|---------|
| strategy_portfolios:pure:{strategy}         | ~30–50 KB     | 6 strategies| ~250 KB |
| strategy_portfolios:personalized:{strategy}:{profile} | ~20–40 KB | 30 combos   | ~900 KB |
| **Subtotal**                                |               |             | **~1.2 MB** |

### 3.4 Master ticker lists

| Key                         | Size              |
|-----------------------------|--------------------|
| master_ticker_list          | ~200 KB (gzipped)  |
| master_ticker_list_validated| ~200 KB (gzipped)  |
| **Subtotal**                 | **~0.4 MB**        |

### 3.5 Rate limiting (if using Redis)

| Key pattern              | Per-user size | Est. active users | Total   |
|---------------------------|---------------|-------------------|---------|
| LIMITER:{ip}:{endpoint}   | ~50 bytes     | 100               | ~50 KB  |
| **Subtotal**               |               |                   | **~0.05 MB** |

### 3.6 Eligible tickers cache

- Key pattern: `optimization:eligible_tickers:{hash}`
- Size: ~200 KB–1 MB, 1–3 keys → **~0.5 MB**

### 3.7 Other caches

| Key                         | Size                      |
|-----------------------------|---------------------------|
| fx:rates                    | ~5 KB                     |
| portfolio:top_pick:{profile}| ~50 KB total              |
| Shareable links             | ~100 KB (usage-dependent) |
| **Subtotal**                 | **~0.2 MB**               |

### 3.8 Total storage summary

| Category                | Size    | % of 30 MB |
|-------------------------|---------|------------|
| Ticker data (1,432)     | 8.3 MB  | 27.7%      |
| Strategy portfolios     | 1.2 MB  | 4.0%       |
| Portfolio buckets      | 0.6 MB  | 2.0%       |
| Eligible tickers cache | 0.5 MB  | 1.7%       |
| Master ticker lists    | 0.4 MB  | 1.3%       |
| Other caches           | 0.2 MB  | 0.7%       |
| Rate limiting          | 0.05 MB | 0.2%       |
| **TOTAL**               | **~11.3 MB** | **37.7%** |

You use ~11.3 MB of 30 MB; there is enough headroom for growth (e.g. up to ~3,500 tickers before hitting the limit).

---

## 4. Growth projections

| Scenario      | Ticker count | Storage  | Fits in 30 MB?        |
|---------------|-------------|----------|------------------------|
| Current       | 1,432       | ~11.3 MB | Yes (~62% free)       |
| +500 tickers  | 1,932       | ~15 MB   | Yes (~50% free)       |
| +1,000 tickers| 2,432       | ~19 MB   | Yes (~37% free)       |
| +2,000 tickers| 3,432       | ~27 MB   | Tight (~10% free)     |
| +2,500 tickers| 3,932       | ~31 MB   | No (over limit)       |

---

## 5. Persistence on Redis Cloud

Redis Cloud free tier includes persistence:

| Feature           | Details                                  |
|-------------------|------------------------------------------|
| Persistence type  | RDB (point-in-time snapshots)            |
| Snapshot frequency| Every 12 hours (free tier)              |
| Durability        | Data survives restarts and redeployments|
| Recovery          | Automatic on startup                    |

Your ticker and portfolio data will not be lost on restart.

---

## 6. Step-by-step implementation plan

Do these steps in order. You can migrate data (Step 6) with any of the three methods; the Python script (Method 3) is recommended.

**Your Redis Cloud database (current):** Database name: database-Wizard. Host: `redis-14204.crce175.eu-north-1-1.ec2.cloud.redislabs.com`, port: `14204`, region: eu-north-1 (Stockholm). URL format: `redis://default:YOUR_PASSWORD@redis-14204.crce175.eu-north-1-1.ec2.cloud.redislabs.com:14204`

### Step 1: Create a Redis Cloud account and database

1. Open https://redis.com/try-free/
2. Sign up with your email.
3. Create a **free** database:
   - Choose a region: **eu-west-1** (closest to Amsterdam / EU users) or another region if you prefer.
   - Select the free tier (30 MB).
   - Set a strong password and save it securely.
4. Wait until the database is **Active**.

### Step 2: Get the Redis Cloud connection string

1. In the Redis Cloud console, open your database.
2. Find the **Public endpoint** or **Connection** section.
3. Copy the connection URL. It looks like:
   - `redis://default:YOUR_PASSWORD@redis-12345.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345`
   - Or with TLS: `rediss://default:YOUR_PASSWORD@...` (use the one shown in the UI).
4. Replace `YOUR_PASSWORD` with the actual password if it is not already in the string.
5. Keep this URL for the next steps (and for Fly.io).

Note: The app accepts both `redis://` and `rediss://` via `REDIS_URL`. Use the exact URL provided by Redis Cloud.

### Step 3: (Optional) Test the connection locally

Before changing production, you can test from your machine:

1. Set the new URL in your environment (no spaces, one line):
   ```bash
   export REDIS_URL="redis://default:YOUR_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345"
   ```
2. From the project root (backend able to load `utils`):
   ```bash
   cd backend
   python -c "from utils.redis_first_data_service import redis_first_data_service as rds; print('Connected:', rds.redis_client.ping())"
   ```
   You should see `Connected: True`. If the app uses a different entrypoint, run the same `REDIS_URL` and the same `redis_first_data_service` import from that context.

### Step 4: Migrate data from Upstash to Redis Cloud

You have three options. **Recommended: Method 3 (Python script)** — no extra tools, works on any OS, preserves TTLs, and you can add progress reporting.

- **Method 1**: RIOT (Redis Input/Output Tools) — good if you already use CLI tools and want a file-based backup.
- **Method 2**: Key-by-key with redis-cli — good if you want to migrate only certain key patterns (e.g. `ticker_data:*`) and have redis-cli installed.
- **Method 3**: Python script — recommended; uses the same `redis` library as the app, runs in one go, and is easy to adapt (e.g. progress bar, retries).

#### Method 1: RIOT (Redis Input/Output Tools)

1. Install RIOT (macOS with Homebrew):
   ```bash
   brew install redis-riot
   ```
2. Get your Upstash URL from the Upstash console (e.g. `rediss://default:xxx@xxx.upstash.io:6379`).
3. Export from Upstash (creates a local file):
   ```bash
   riot-redis -u "rediss://default:YOUR_UPSTASH_PASSWORD@YOUR_UPSTASH_HOST.upstash.io:6379" \
     dump --type RDB -o upstash_backup.rdb
   ```
   Replace `YOUR_UPSTASH_PASSWORD` and `YOUR_UPSTASH_HOST` with your real Upstash credentials.
4. Import into Redis Cloud:
   ```bash
   riot-redis -u "redis://default:YOUR_REDIS_CLOUD_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345" \
     load -f upstash_backup.rdb
   ```
   Replace with your Redis Cloud URL.
5. If the tool uses a different format (e.g. JSON instead of RDB), follow the RIOT docs for your version; the idea is dump from Upstash, then load into Redis Cloud.

Note: RDB format can vary between Redis providers. If RIOT or the server reports compatibility issues, use Method 3 instead.

#### Method 2: Key-by-key migration with redis-cli

This example migrates keys matching `ticker_data:*`. You can change the pattern or run multiple times for different patterns (e.g. `portfolio_bucket:*`, `strategy_portfolios:*`).

1. Install Redis CLI if needed (e.g. `brew install redis` on macOS).
2. Set variables (no line breaks in the URLs):
   ```bash
   UPSTASH_URL="rediss://default:YOUR_UPSTASH_PASSWORD@YOUR_UPSTASH_HOST.upstash.io:6379"
   REDIS_CLOUD_URL="redis://default:YOUR_REDIS_CLOUD_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345"
   ```
3. Migrate keys for one pattern:
   ```bash
   redis-cli -u "$UPSTASH_URL" --scan --pattern "ticker_data:*" | while read key; do
     value=$(redis-cli -u "$UPSTASH_URL" DUMP "$key")
     ttl=$(redis-cli -u "$UPSTASH_URL" TTL "$key")
     if [ "$ttl" = "-1" ]; then ttl_ms=0; else ttl_ms=$((ttl * 1000)); fi
     echo "$value" | redis-cli -u "$REDIS_CLOUD_URL" -x RESTORE "$key" "$ttl_ms" replace
   done
   ```
4. Repeat for other patterns, e.g.:
   - `portfolio_bucket:*`
   - `strategy_portfolios:*`
   - `master_ticker_list*`
   - `optimization:*`
   - `fx:*`
   - `portfolio:top_pick:*`
   Or use pattern `*` to migrate everything (slower; may include ephemeral keys).

Limitation: RESTORE over the pipe can be fiddly with binary DUMP output on some systems; Method 3 avoids that.

#### Method 3: Python script (recommended)

1. Create a script (e.g. `backend/scripts/migrate_upstash_to_redis_cloud.py` or a one-off file in the repo root). Example:

```python
"""
One-off migration: Upstash -> Redis Cloud.
Uses REDIS_URL_SOURCE (Upstash) and REDIS_URL_TARGET (Redis Cloud).
Run from repo root with backend on PYTHONPATH, or from backend/ with PYTHONPATH=.
"""
import os
import sys

# Ensure backend utils are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import redis

def main():
    source_url = os.getenv("REDIS_URL_SOURCE")
    target_url = os.getenv("REDIS_URL_TARGET")
    if not source_url or not target_url:
        print("Set REDIS_URL_SOURCE (Upstash) and REDIS_URL_TARGET (Redis Cloud)")
        sys.exit(1)
    if source_url == target_url:
        print("Source and target must differ")
        sys.exit(1)

    upstash = redis.from_url(source_url, decode_responses=False)
    redis_cloud = redis.from_url(target_url, decode_responses=False)

    keys = upstash.keys("*")
    n = len(keys)
    print(f"Migrating {n} keys...")

    for i, key in enumerate(keys):
        try:
            ttl = upstash.ttl(key)
            value = upstash.dump(key)
            if value is None:
                continue
            restore_ttl = (ttl * 1000) if ttl > 0 else 0
            redis_cloud.restore(key, restore_ttl, value, replace=True)
        except Exception as e:
            print(f"Error on key {key}: {e}")
        if (i + 1) % 500 == 0 or i == 0 or i == n - 1:
            print(f"  Progress: {i + 1}/{n}")

    print("Migration complete.")

if __name__ == "__main__":
    main()
```

2. Install dependency if needed: `pip install redis`
3. Set URLs (no spaces; use your real Upstash and Redis Cloud URLs):
   ```bash
   export REDIS_URL_SOURCE="rediss://default:YOUR_UPSTASH_PASSWORD@YOUR_UPSTASH_HOST.upstash.io:6379"
   export REDIS_URL_TARGET="redis://default:YOUR_REDIS_CLOUD_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345"
   ```
4. Run from the directory that allows `import redis` and where the script lives, e.g.:
   ```bash
   cd backend
   python scripts/migrate_upstash_to_redis_cloud.py
   ```
   Or from repo root:
   ```bash
   PYTHONPATH=backend python backend/scripts/migrate_upstash_to_redis_cloud.py
   ```
5. When it finishes, proceed to Step 5 to verify.

Migration cost on Upstash: KEYS + TTL + DUMP per key is about 3 commands per key. For ~5,000 keys that is ~15,000 commands, still within a typical free-tier allowance for a one-off run. If you are already over limit, run during a low-traffic window.

### Step 5: Verify data on Redis Cloud

1. Point the app at Redis Cloud only:
   ```bash
   export REDIS_URL="redis://default:YOUR_REDIS_CLOUD_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345"
   ```
2. From the backend (or wherever your app runs):
   ```bash
   python -c "from utils.redis_first_data_service import redis_first_data_service as rds; print('Ping:', rds.redis_client.ping()); print('DBSize:', rds.redis_client.dbsize())"
   ```
   You should see `Ping: True` and a key count in the same ballpark as before (~5,000+).
3. Optionally run your existing app or scripts (e.g. warm_cache, API) against this `REDIS_URL` and confirm ticker/portfolio responses look correct.

### Step 6: Update production (Fly.io) to use Redis Cloud

1. Set the Fly.io secret to the Redis Cloud URL (single line, no spaces):
   ```bash
   fly secrets set REDIS_URL="redis://default:YOUR_REDIS_CLOUD_PASSWORD@redis-xxxxx.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345" -a portfolio-navigator-wizard
   ```
   Use your real Redis Cloud host and password. If Redis Cloud gives you a `rediss://` URL, use that instead of `redis://`.
2. Redeploy or let the app restart so it picks up the new secret.
3. Verify in production:
   ```bash
   fly ssh console -a portfolio-navigator-wizard
   ```
   Then in the console:
   ```bash
   python -c "from utils.redis_first_data_service import redis_first_data_service as rds; print('Connected:', rds.redis_client.ping())"
   ```
   You should see `Connected: True`.

After this, the app uses Redis Cloud only. You can keep the Upstash database for a while as a backup, then remove it when you are confident.

---

## 7. Migration command cost (Upstash)

Rough one-off cost when using the Python script (or key-by-key):

| Operation        | Commands (approx) | Note              |
|------------------|-------------------|--------------------|
| KEYS *            | 1                 | Included           |
| TTL per key       | ~5,000            | If you have ~5K keys |
| DUMP per key      | ~5,000            | Same               |
| **Total**         | **~10,000**       | Usually within free tier for a single run |

If you are already over the Upstash free tier, run the migration during low traffic.

---

## 8. If storage ever exceeds 30 MB

### 8.1 Redis Cloud paid tiers (for reference)

| Plan        | Storage | Price/month |
|-------------|---------|-------------|
| Free        | 30 MB   | $0          |
| Essentials  | 250 MB  | $5          |
| Essentials  | 1 GB    | $10         |
| Essentials  | 2.5 GB  | $22         |

### 8.2 Mitigation strategies (stay on free tier)

These are **not** required to implement in the current state (~11.3 MB). Use them only if you approach the 30 MB limit later:

1. **Compress more**: Prices are already gzipped; consider compressing sector/metrics (or other large JSON) to reduce size.
2. **Reduce ticker set**: e.g. S&P 500 + top ETFs (~600 tickers) can bring total to ~5 MB.
3. **Shorter TTLs**: More aggressive expiration so less data is stored at once.
4. **Rate limiting in memory**: Move rate-limiting state out of Redis to save ~50 KB per 100 concurrent users (only if you need to free space).

No code changes are needed for these until you actually need to stay under 30 MB.

---

## 9. Redis Cloud vs Upstash (quick comparison)

| Feature    | Upstash free   | Redis Cloud free |
|------------|----------------|-------------------|
| Commands   | 500K/month     | Unlimited         |
| Storage    | 256 MB         | 30 MB             |
| Persistence| Yes            | Yes               |
| Connections| 100            | 30                |
| Your usage | Exceeded       | Fits (~11.3 MB)   |
| Cost for you | ~$0.80+/month | $0                |

---

## 10. Checklist (manual follow-up)

- [x] Create Redis Cloud account and free database (eu-north-1, database-Wizard).
- [x] Save Redis Cloud connection URL and password.
- [x] (Skipped) Test `REDIS_URL` locally — network restrictions, tested via Fly.io SSH.
- [x] Set `REDIS_URL_SOURCE` (Upstash) and `REDIS_URL_TARGET` (Redis Cloud).
- [x] Run migration (Python script — Method 3, via Fly.io SSH). **Result: 5749 keys, 0 errors.**
- [x] Verify: ping and dbsize on Redis Cloud with `REDIS_URL` set. **5749 keys confirmed.**
- [x] Set Fly.io secret: `fly secrets set REDIS_URL="..."` for the app.
- [x] Redeploy/restart app and verify in `fly ssh console`. **Health check passed.**
- [ ] Keep Upstash as backup for a while, then remove when no longer needed.

**Migration completed: 2026-03-05**

---

## 11. Post-migration: what happens and how to verify

After you set `REDIS_URL` on Fly.io to the Redis Cloud connection string, no code changes are required. The backend already reads `REDIS_URL` from the environment; Fly.io restarts the app with the new secret automatically.

### 11.1 What uses the new Redis automatically

| Component                    | Action |
|-----------------------------|--------|
| redis_first_data_service.py | Reads `REDIS_URL` from env, connects to Redis Cloud |
| rate_limiting.py            | Uses same `REDIS_URL` for rate limiting |
| All Redis operations        | Use the new connection automatically |

### 11.2 Verify connection (Fly.io production)

1. SSH into the backend:
   ```bash
   fly ssh console -a portfolio-navigator-wizard
   ```
2. Test Redis connection and key count:
   ```bash
   python -c "
   from utils.redis_first_data_service import redis_first_data_service as rds
   print('Connected:', rds.redis_client.ping())
   print('Keys:', rds.redis_client.dbsize())
   "
   ```
   You should see `Connected: True` and a key count (e.g. ~5,000+ if you migrated).

### 11.3 Verify data (if you migrated)

Check that ticker cache is populated:
   ```bash
   python -c "
   from utils.redis_first_data_service import redis_first_data_service as rds
   tickers = rds.list_cached_tickers()
   print('Tickers in cache:', len(tickers))
   "
   ```
   Expect a count in the same ballpark as before (e.g. 1,432).

### 11.4 If you did not migrate: repopulate from scratch

If you switched to Redis Cloud without migrating data, you can refill the cache from Yahoo Finance:

1. SSH into the backend:
   ```bash
   fly ssh console -a portfolio-navigator-wizard
   ```
2. Run the full refetch script:
   ```bash
   cd /app
   python scripts/full_refetch_with_gate.py
   ```
   This repopulates all 1,432 tickers and typically takes about 30–60 minutes.

### 11.5 Architecture after migration

```
                    FLY.IO
   ┌─────────────────────┐         ┌─────────────────────────┐
   │  portfolio-navigator │         │ portfolio-navigator-   │
   │  (Frontend)          │  ───►   │ wizard (Backend)       │
   │  nginx + React       │  API    │ FastAPI + Python       │
   └─────────────────────┘         └───────────┬─────────────┘
                                                │
                                                │ REDIS_URL
                                                ▼
                               ┌────────────────────────────┐
                               │       REDIS CLOUD           │
                               │  (eu-west-1, AWS)           │
                               │  • 30 MB free storage       │
                               │  • Unlimited commands      │
                               │  • Persistent (RDB)         │
                               │  • 30 connections           │
                               └────────────────────────────┘
```

### 11.6 Quick reference: post-migration commands

```bash
# 1. Create Redis Cloud account at https://redis.com/try-free/
#    Region: eu-west-1 (Ireland) — closest to Amsterdam (ams)

# 2. Update Fly.io secret
fly secrets set REDIS_URL="redis://default:xxx@redis-xxx.cloud.redislabs.com:xxx" \
  -a portfolio-navigator-wizard

# 3. (Optional) Migrate data from Upstash using the Python script (Method 3)
#    Then verify locally before updating the secret.

# 4. Verify in production
fly ssh console -a portfolio-navigator-wizard
python -c "from utils.redis_first_data_service import redis_first_data_service as rds; print('Ping:', rds.redis_client.ping()); print('Keys:', rds.redis_client.dbsize())"

# 5. (If you did not migrate) Repopulate data on the backend
#    Inside fly ssh console:
cd /app && python scripts/full_refetch_with_gate.py
```

### 11.7 Post-migration status (reference)

| Item              | Status / note |
|-------------------|----------------|
| Frontend          | portfolio-navigator.fly.dev (or your configured host) |
| Backend CORS      | Ensure it accepts your frontend origin |
| Redis Cloud       | Create account, set `REDIS_URL`, then verify with steps above |
| No migration path | Use `scripts/full_refetch_with_gate.py` to repopulate (~30–60 min) |

---

End of guide. For questions or issues, check Redis Cloud status and the app logs (backend and Fly.io) and ensure `REDIS_URL` has no extra spaces or line breaks.
