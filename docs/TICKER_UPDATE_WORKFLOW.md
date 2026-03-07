# Ticker Data Update & Refresh Workflow
## Portfolio Navigator Wizard - Complete Guide

**Last Updated**: 2026-02-05

---

## Table of Contents

1. [Overview](#overview)
2. [Available Update Commands](#available-update-commands)
3. [Practical Workflow](#practical-workflow)
4. [Deployment Usage](#deployment-usage)
5. [Automation Strategies](#automation-strategies)
6. [Enhanced Email Notifications](#enhanced-slack-notifications)

---

## Overview

Your application has a sophisticated ticker data management system with multiple update strategies:

### Data Types Managed

1. **Price Data** (`ticker_data:prices:TICKER`)
   - 15 years of daily historical prices
   - Compressed gzip format (~4-5 KB per ticker)
   - TTL: 28 days

2. **Sector Data** (`ticker_data:sector:TICKER`)
   - Sector, industry, description
   - ~200 bytes per ticker
   - TTL: 28 days

3. **Metrics Data** (`ticker_data:metrics:TICKER`)
   - Expected return, volatility, Sharpe ratio
   - ~500 bytes per ticker
   - TTL: 28 days

4. **Master Ticker List** (`master_ticker_list`)
   - List of all available tickers (1,432 tickers)
   - Compressed
   - TTL: 24 hours

---

## Available Update Commands

### 1. Warm Cache (Initial Population)

**Endpoint**: `POST /api/v1/portfolio/warm-cache`

**Purpose**: Populate empty cache with all tickers

**When to use**:
- First deployment (empty cache)
- After cache clear
- After Redis restart

**Rate Limit**: 2/hour

**Example**:
```bash
# Local
curl -X POST http://localhost:8000/api/v1/portfolio/warm-cache

# Production (Railway)
curl -X POST https://your-backend.railway.app/api/v1/portfolio/warm-cache
```

**What it does**:
- Fetches all 1,432 tickers from Yahoo Finance
- Stores prices, sectors, and metrics
- Takes ~90 minutes
- No TTL checks (always fetches)

**Output**:
```json
{
  "message": "Cache warming completed",
  "results": {
    "total": 1432,
    "success": 1420,
    "failed": 12
  }
}
```

---

### 2. Warm Specific Tickers

**Endpoint**: `POST /api/v1/portfolio/warm-tickers`

**Purpose**: Warm specific tickers only

**When to use**:
- Add new tickers to cache
- Refresh specific tickers
- Populate popular tickers first

**Rate Limit**: No limit (use carefully)

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/warm-tickers \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
  }'
```

**Output**:
```json
{
  "status": "success",
  "warmed": 5,
  "total": 5,
  "failed": []
}
```

---

### 3. Refresh Expiring Tickers (TTL-Based)

**Endpoint**: `POST /api/v1/portfolio/cache/refresh-expiring?days_threshold=7`

**Purpose**: Auto-refresh tickers expiring soon

**When to use**:
- Maintenance (keep cache fresh)
- Before TTL expires
- Automated via TTL monitoring

**Rate Limit**: 2/hour

**Example**:
```bash
# Refresh tickers expiring within 7 days
curl -X POST "http://localhost:8000/api/v1/portfolio/cache/refresh-expiring?days_threshold=7"

# Refresh critical tickers only (< 1 day)
curl -X POST "http://localhost:8000/api/v1/portfolio/cache/refresh-expiring?days_threshold=1"
```

**Output**:
```json
{
  "success": true,
  "message": "Refreshed 45 out of 50 tickers",
  "total_expiring": 50,
  "refreshed": 45,
  "failed": 5,
  "failed_tickers": ["BAD.TICKER", ...]
}
```

**What it does**:
1. Checks TTL of all tickers
2. Identifies tickers expiring within threshold
3. Re-fetches data from Yahoo Finance
4. Resets TTL to 28 days

---

### 4. Smart Monthly Refresh

**Endpoint**: `POST /api/v1/portfolio/ticker-table/smart-refresh`

**Purpose**: Efficiently update only new monthly data

**When to use**:
- Monthly maintenance
- Extend time series incrementally
- Minimal API calls

**Example**:
```bash
# Refresh all tickers (smart - only new months)
curl -X POST http://localhost:8000/api/v1/portfolio/ticker-table/smart-refresh

# Refresh specific tickers
curl -X POST http://localhost:8000/api/v1/portfolio/ticker-table/smart-refresh \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT"]}'
```

**Output**:
```json
{
  "status": "success",
  "message": "Smart refresh completed - all tickers processed",
  "changed_count": 120,
  "timestamp": "2026-02-05T..."
}
```

**How it works**:
- Only fetches data from last cached date to today
- Appends new data to existing cache
- Doesn't re-download entire 15-year history
- Very efficient (saves ~90% API calls)

---

### 5. Force Refresh Expired Data

**Endpoint**: `POST /api/v1/portfolio/ticker-table/refresh`

**Purpose**: Force refresh of expired ticker data

**When to use**:
- After TTL expires
- Emergency refresh
- Fix stale data

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/ticker-table/refresh
```

**Output**:
```json
{
  "status": "success",
  "message": "Ticker table refresh completed",
  "summary": {
    "refreshed": 45,
    "skipped": 1387
  }
}
```

---

### 6. Refresh Master Ticker List

**Endpoint**: `POST /api/v1/portfolio/tickers/refresh`

**Purpose**: Reload master ticker list from Redis

**When to use**:
- After master list update
- Cache inconsistency
- Rarely needed

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/tickers/refresh
```

---

### 7. Get Expiring Tickers List

**Endpoint**: `GET /api/v1/portfolio/cache/expiring-list?days_threshold=7`

**Purpose**: Check which tickers need refreshing

**When to use**:
- Planning maintenance
- Manual review before refresh
- Monitoring

**Example**:
```bash
curl "http://localhost:8000/api/v1/portfolio/cache/expiring-list?days_threshold=7"
```

**Output**:
```json
{
  "success": true,
  "days_threshold": 7,
  "count": 120,
  "tickers": ["AAPL", "MSFT", "GOOGL", ...],
  "message": "Found 120 tickers expiring within 7 days"
}
```

---

## Practical Workflow

### Scenario 1: Initial Deployment (Empty Cache)

**Timeline**: ~2 hours

```bash
BACKEND_URL="https://your-backend.railway.app"

# Step 1: Verify cache is empty
curl "$BACKEND_URL/api/v1/portfolio/cache-status"
# Output: { "total_tickers": 0 }

# Step 2: Start full cache warming
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-cache"

# Step 3: Monitor progress (every 5 minutes)
watch -n 300 "curl $BACKEND_URL/api/v1/portfolio/cache-status"
# Watch total_tickers increase: 0 → 100 → 500 → 1000 → 1432

# Step 4: Verify completion
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-status"
# All tickers should have "healthy" TTL (~28 days)
```

**Automated Alternative** (recommended):
- Just deploy and wait
- TTL monitoring background task runs automatically
- email notification confirms completion
- No manual intervention needed

---

### Scenario 2: Regular Maintenance (Monthly)

**Timeline**: ~10-20 minutes

**Option A: Automated (Recommended)**
```
Nothing to do!
- TTL monitoring runs every 24 hours automatically
- Auto-refreshes critical/expired tickers
- email notifications keep you informed
```

**Option B: Manual Monthly Refresh**
```bash
BACKEND_URL="https://your-backend.railway.app"

# Day 1 of month: Check status
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-status"

# If tickers expiring soon, do smart refresh
curl -X POST "$BACKEND_URL/api/v1/portfolio/ticker-table/smart-refresh"

# Verify
curl "$BACKEND_URL/api/v1/portfolio/cache-status"
```

---

### Scenario 3: Emergency Refresh (Cache Issues)

**Timeline**: ~5 minutes

```bash
BACKEND_URL="https://your-backend.railway.app"

# Scenario: Some tickers showing stale data

# Step 1: Check which tickers are expired
curl "$BACKEND_URL/api/v1/portfolio/cache/expiring-list?days_threshold=0"

# Step 2: Refresh only expired tickers
curl -X POST "$BACKEND_URL/api/v1/portfolio/cache/refresh-expiring?days_threshold=1"

# Step 3: Verify fix
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-status"
```

---

### Scenario 4: Add New Tickers

**Timeline**: ~1 minute

```bash
BACKEND_URL="https://your-backend.railway.app"

# Add 5 new tickers to cache
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-tickers" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["NVDA", "AMD", "INTC", "QCOM", "MU"]
  }'

# Verify they're cached
curl "$BACKEND_URL/api/v1/portfolio/cache-status"
```

---

### Scenario 5: Weekly Maintenance Check

**Timeline**: ~2 minutes

```bash
BACKEND_URL="https://your-backend.railway.app"

# Check overall health
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-report"

# If warnings, refresh expiring
curl -X POST "$BACKEND_URL/api/v1/portfolio/cache/refresh-expiring?days_threshold=7"
```

---

## Deployment Usage

### During Railway Deployment

**Phase 1: Deploy Services (30 mins)**
```bash
# 1. Deploy Redis, Backend, Frontend
# 2. Configure environment variables
# 3. Generate domains
```

**Phase 2: Initial Cache Warming (90 mins)**
```bash
BACKEND_URL="https://your-backend.railway.app"

# Trigger cache warming
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-cache"

# Go grab coffee ☕
# Background task fetches all 1,432 tickers
```

**Phase 3: Verify (5 mins)**
```bash
# Check email for TTL status notification
# Or manually check:
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-status"

# Should show:
# {
#   "categories": {
#     "healthy": 1432,
#     "critical": 0,
#     "warning": 0
#   }
# }
```

---

### Automated TTL Monitoring

**Already implemented in your backend!**

The background task in `backend/main.py` automatically:

1. **Runs every 24 hours**
2. **Checks TTL status** of all tickers
3. **Sends email notification** with:
   - TTL status breakdown
   - Redis storage statistics (NEW!)
   - Key distribution
   - Memory usage
   - Ticker completeness
4. **Auto-refreshes** critical/expired tickers
5. **Logs** detailed status

**Configuration** (already in .env.example):
```bash
TTL_EMAIL_NOTIFICATIONS=true
TTL_NOTIFICATION_EMAIL=your@email.com, SMTP_USER, SMTP_PASSWORD (see .env.example)
TTL_NOTIFICATION_EMAIL=#redis-alerts
```

---

## Automation Strategies

### Strategy 1: Fully Automated (Recommended)

**Setup**: Deploy and forget

**How it works**:
- TTL monitoring runs every 24 hours
- Auto-refreshes tickers when needed
- email alerts if issues
- No manual intervention

**Pros**:
- Zero maintenance
- Always fresh data
- Proactive alerts

**Cons**:
- Uses more API calls
- Potential rate limit issues if many tickers expire at once

**Best for**: Production deployment

---

### Strategy 2: Scheduled Maintenance

**Setup**: Monthly cron job

**Example with GitHub Actions**:
```yaml
# .github/workflows/monthly-refresh.yml
name: Monthly Ticker Refresh

on:
  schedule:
    # First day of month at 2 AM UTC
    - cron: '0 2 1 * *'
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - name: Smart Monthly Refresh
        run: |
          curl -X POST "${{ secrets.BACKEND_URL }}/api/v1/portfolio/ticker-table/smart-refresh"
```

**Pros**:
- Predictable API usage
- Control over timing
- Efficient (smart refresh only)

**Cons**:
- Requires setup
- Manual trigger if missed

**Best for**: Cost-conscious deployment

---

### Strategy 3: On-Demand Manual

**Setup**: Manual curl commands

**Workflow**:
1. Check email for TTL alerts
2. If warning, run refresh command
3. Verify via TTL status

**Pros**:
- Full control
- Minimal API usage
- No automation overhead

**Cons**:
- Requires manual monitoring
- Risk of forgetting
- Potential stale data

**Best for**: Development/testing

---

## Enhanced Email Notifications

### What You'll Receive

**Every 24 hours, you'll get a Slack message like this:**

```
🔔 Redis Cache TTL Alert - INFO

All tickers have healthy TTL status

📊 TTL Status
Total Tickers: 1,432          Timestamp: 2026-02-05T10:30:00
Expired: 0 tickers            Critical (<1 day): 0 tickers
Warning (<7 days): 120 tickers Healthy: 1,312 tickers

───────────────────────────────────────

💾 Redis Storage Overview
Total Keys: 4,991             Memory Used: 7.37 MB
Peak Memory: 8.79 MB          Memory Limit: unlimited

🔑 Key Distribution
Price Data: 1,432 keys        Sector Data: 1,432 keys
Metrics: 1,413 keys           Portfolios: 156 keys
Strategy Portfolios: 45 keys Other: 513 keys

📈 Ticker Data Completeness
Total Unique Tickers: 1,432  With Prices: 1,432
With Sectors: 1,432           With Metrics: 1,413
Complete Data: 1,432          Missing Metrics: 19

📦 Estimated Storage by Type (Total: ~7.2 MB)
Prices: ~6.8 MB               Sectors: ~0.28 MB
Metrics: ~0.70 MB             Portfolios: ~0.15 MB
Strategy: ~0.05 MB            Fragmentation: 1.12

───────────────────────────────────────
Portfolio Navigator Wizard | Redis TTL Monitoring System
```

### Alert Levels

**🔔 INFO** (Green):
- All healthy, no action needed
- Just status update

**⚠️ WARNING** (Orange):
- Tickers expiring within 7 days
- Plan refresh soon

**🚨 CRITICAL** (Red):
- Tickers expiring within 1 day
- Auto-refresh triggered
- Immediate attention if auto-refresh fails

**❌ EXPIRED** (Red):
- Some tickers already expired
- Auto-refresh triggered
- Check for issues

---

## Best Practices

### 1. Monitor Slack Alerts
- Set up #redis-alerts channel
- Review daily notifications
- Act on CRITICAL alerts

### 2. Monthly Review
- First day of month: Review TTL report
- Optional: Trigger smart refresh
- Check Railway usage ($3-5/month expected)

### 3. Before Major Updates
- Warm cache of new tickers before release
- Test with specific tickers first
- Monitor TTL after deployment

### 4. API Rate Limiting
- Yahoo Finance: No public limit, but be reasonable
- Alpha Vantage: 500/day (free tier) - rarely used
- Cache warming: ~1,432 API calls
- Smart refresh: ~120 API calls/month

### 5. Cost Optimization
- Use smart refresh over full re-warming
- Let TTL monitoring handle auto-refresh
- Only warm cache when needed

---

## Quick Reference

| Task | Command | Frequency |
|------|---------|-----------|
| Initial deploy | `POST /warm-cache` | Once |
| Monthly refresh | `POST /ticker-table/smart-refresh` | Monthly |
| Emergency refresh | `POST /cache/refresh-expiring?days_threshold=1` | As needed |
| Check status | `GET /cache/ttl-status` | Anytime |
| Check expiring | `GET /cache/expiring-list?days_threshold=7` | Anytime |
| Add new tickers | `POST /warm-tickers` | As needed |

---

## Troubleshooting

### Issue: Some tickers not refreshing

**Check**:
```bash
curl "$BACKEND_URL/api/v1/portfolio/cache/expiring-list?days_threshold=0"
```

**Fix**:
```bash
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-tickers" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["FAILED_TICKER_1", "FAILED_TICKER_2"]}'
```

---

### Issue: Cache warming taking too long

**Expected**: 90 minutes for 1,432 tickers

**If slower**:
- Check Yahoo Finance API status
- Check Railway network latency
- Review backend logs for errors
- Try batch warming (warm-tickers with 100 at a time)

---

### Issue: No email notifications

**Check**:
1. Environment variables set correctly
2. Webhook URL valid
3. Backend logs for "email notification sent"
4. email inbox permissions

**Test**:
```bash
curl "$BACKEND_URL/api/v1/portfolio/cache/ttl-status"
# Should trigger notification
```

---

## Summary

Your ticker update system is:

✅ **Automated** - Background TTL monitoring
✅ **Intelligent** - Smart refresh only fetches new data
✅ **Monitored** - email notifications with detailed stats
✅ **Flexible** - Multiple update strategies
✅ **Efficient** - Minimal API usage
✅ **Self-healing** - Auto-refresh of critical tickers

**In practice**: After initial deployment, the system maintains itself with minimal intervention.

---

**Questions?** Check the [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) or [RAILWAY_DEPLOYMENT_GUIDE.md](RAILWAY_DEPLOYMENT_GUIDE.md) for more details.
