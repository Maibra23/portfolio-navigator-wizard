# Redis Configuration Guide
## Production-Ready Redis Setup for Portfolio Navigator Wizard

**Last Updated:** February 12, 2026
**Target Environment:** Railway / Cloud Infrastructure
**Redis Version:** 5.0+
**Application:** Portfolio Navigator Wizard Backend

---

## 📋 Table of Contents

1. [Critical Configuration](#critical-configuration)
2. [Railway Redis Setup](#railway-redis-setup)
3. [Memory Management](#memory-management)
4. [Persistence Configuration](#persistence-configuration)
5. [Connection Pooling](#connection-pooling)
6. [TTL Strategy](#ttl-strategy)
7. [Monitoring & Metrics](#monitoring--metrics)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)
10. [Quick Reference](#quick-reference)

---

## 🚨 Critical Configuration

### ⚠️ MUST CONFIGURE BEFORE PRODUCTION

These settings are **critical** for production stability:

```ini
# Memory Limits (CRITICAL - prevents OOM crashes)
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (CRITICAL - prevents data loss on restart)
appendonly yes
appendfsync everysec

# Connection Limits
maxclients 10000
timeout 300
tcp-keepalive 60
```

**Why This Matters:**
- ❌ Without memory limits → Container crashes → ALL data lost → 50-min recovery
- ❌ Without persistence → Container restart → Cold start required
- ❌ Without connection limits → Connection exhaustion → Service unavailable

---

## 🚂 Railway Redis Setup

### Step 1: Add Redis Service

**Via Railway Dashboard:**
1. Go to Railway Dashboard → Your Project
2. Click "New" → "Database" → "Add Redis"
3. Railway provisions Redis instance automatically

**Via Railway CLI:**
```bash
railway add
# Select "Redis" from list
```

### Step 2: Configure Redis Variables

Railway Dashboard → Redis Service → Variables tab:

```bash
# Memory Configuration
REDIS_MAXMEMORY=256mb
REDIS_MAXMEMORY_POLICY=allkeys-lru
REDIS_MAXMEMORY_SAMPLES=5

# Persistence
REDIS_APPENDONLY=yes
REDIS_APPENDFSYNC=everysec
REDIS_AUTO_AOF_REWRITE_PERCENTAGE=100
REDIS_AUTO_AOF_REWRITE_MIN_SIZE=64mb

# Connections
REDIS_MAXCLIENTS=10000
REDIS_TIMEOUT=300
REDIS_TCP_KEEPALIVE=60

# Logging
REDIS_LOGLEVEL=notice
```

### Step 3: Verify Connection

```bash
# Test connection
railway run --service backend python -c "import redis, os; r = redis.from_url(os.getenv('REDIS_URL')); print('✅ Connected!' if r.ping() else '❌ Failed')"
```

---

## 💾 Memory Management

### Memory Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Ticker Prices | ~30 MB | 600 tickers × 15 years daily |
| Sector Data | ~5 MB | Classifications |
| Metrics | ~5 MB | Returns, volatility |
| Portfolios | ~1 MB | 60 pre-computed |
| Strategies | ~1 MB | Recommendations |
| Other | ~8 MB | Keys, metadata |
| **Current Usage** | **~50 MB** | Estimated |
| **Buffer (5x)** | **+200 MB** | Growth headroom |
| **Total Limit** | **256 MB** | ✅ Recommended |

### Eviction Policies

| Policy | Use Case | Recommendation |
|--------|----------|----------------|
| `noeviction` | Never evict | ❌ NOT RECOMMENDED (crashes) |
| `allkeys-lru` | General caching | ✅ **RECOMMENDED** |
| `allkeys-lfu` | Analytics | ⚠️ May evict portfolios |
| `volatile-lru` | Mixed workload | ⚠️ Only if all have TTL |

**Configuration:**
```ini
maxmemory-policy allkeys-lru
maxmemory-samples 5
```

### Memory Monitoring

```bash
# Current usage
redis-cli INFO memory | grep used_memory_human

# Fragmentation (ideal: 1.0-1.5)
redis-cli INFO memory | grep mem_fragmentation_ratio

# Evictions (should be 0!)
redis-cli INFO stats | grep evicted_keys
```

**Alert Thresholds:**
- Memory > 80% → ⚠️ Warning
- Memory > 90% → 🚨 Critical
- Evictions > 0 → 🔴 Emergency

---

## 💽 Persistence Configuration

### Why Persistence Matters

**Without Persistence:**
```
Container restart → ALL data lost → 50-min warm-up → Poor UX
```

**With Persistence:**
```
Container restart → Data restored in 5-10 sec → Seamless
```

### AOF Configuration (RECOMMENDED)

```ini
# Enable AOF
appendonly yes
appendfsync everysec  # Sync every second

# Auto-rewrite
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Mixed persistence (best of both)
aof-use-rdb-preamble yes
```

**Data Loss:**
- `appendfsync always` → 0 data loss (slow)
- `appendfsync everysec` → ≤1 sec loss (balanced) ✅
- `appendfsync no` → Minutes loss (fast but risky)

### Testing Persistence

```bash
# Set test key
redis-cli SET test_persistence "should survive restart"

# Restart container (Railway Dashboard)

# Verify after restart
redis-cli GET test_persistence
# Should return: "should survive restart"
```

---

## 🔌 Connection Pooling

### Problem Without Pooling

```
1000 req/sec × no pooling = 4000 connections
→ Redis maxclients exceeded
→ Backend crashes
```

### Solution: Connection Pool

**Backend Implementation** (already done):

```python
# backend/utils/redis_first_data_service.py
from redis.connection import ConnectionPool

pool = ConnectionPool.from_url(
    redis_url,
    max_connections=50,  # Per worker
    socket_connect_timeout=5,
    socket_timeout=5
)

redis_client = redis.Redis(connection_pool=pool)
```

**Sizing:**
```
4 workers × 50 connections = 200 total
Redis maxclients = 10,000
Utilization = 2% ✅ Safe
```

---

## ⏱️ TTL Strategy

### Current Problem

```python
# All keys use 28-day TTL
self.CACHE_TTL_DAYS = 28  # ❌ Too long for prices!
```

**Issues:**
- 28-day-old stock prices → Wrong calculations
- All 600 tickers expire simultaneously → Cache stampede

### Recommended Strategy

```python
# backend/utils/redis_ttl_config.py (NEW FILE)
from datetime import timedelta

class RedisTTLConfig:
    """TTL by data volatility"""

    PRICE_TTL_SECONDS = int(timedelta(days=1).total_seconds())      # Daily
    SECTOR_TTL_SECONDS = int(timedelta(days=7).total_seconds())     # Weekly
    METRICS_TTL_SECONDS = int(timedelta(days=1).total_seconds())    # Daily
    PORTFOLIO_TTL_SECONDS = int(timedelta(days=7).total_seconds())  # Weekly
    STRATEGY_TTL_SECONDS = int(timedelta(days=7).total_seconds())   # Weekly
    MASTER_LIST_TTL_SECONDS = int(timedelta(days=30).total_seconds()) # Monthly
```

### Prevent Cache Stampede with Jitter

```python
# backend/utils/redis_ttl_utils.py (NEW FILE)
import random

def set_with_jittered_ttl(redis_client, key, value, base_ttl, jitter=0.1):
    """Add ±10% random offset to prevent simultaneous expirations"""
    jitter_factor = random.uniform(1.0 - jitter, 1.0 + jitter)
    actual_ttl = int(base_ttl * jitter_factor)
    redis_client.setex(key, actual_ttl, value)
    return actual_ttl

# Usage:
# set_with_jittered_ttl(redis_client, "ticker_data:prices:AAPL", data, 86400)
# TTL will be 77,760 - 95,040 seconds (1 day ± 10%)
```

**Result:**
- Expirations spread over 4.8 hours (not simultaneous)
- Smooth distributed load
- No cache stampede

---

## 📊 Monitoring & Metrics

### Essential Metrics

```bash
# Memory
redis-cli INFO memory | grep used_memory_human

# Cache hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses
# hit_rate = hits / (hits + misses) × 100%

# Connections
redis-cli INFO clients | grep connected_clients

# Operations/sec
redis-cli INFO stats | grep instantaneous_ops_per_sec
```

### Prometheus Integration

```python
# backend/utils/redis_metrics.py (NEW FILE)
from prometheus_client import Gauge, Counter

REDIS_MEMORY_USED = Gauge('redis_memory_used_bytes', 'Memory usage')
REDIS_CACHE_HIT_RATE = Gauge('redis_cache_hit_rate_percent', 'Hit rate %')
REDIS_KEYS_TOTAL = Gauge('redis_keys_total', 'Total keys')
REDIS_EVICTED_KEYS = Counter('redis_evicted_keys_total', 'Evictions')

def collect_redis_metrics(redis_client):
    """Collect metrics every 60 seconds"""
    info = redis_client.info()
    memory = redis_client.info('memory')
    stats = redis_client.info('stats')

    REDIS_MEMORY_USED.set(memory['used_memory'])

    hits = stats.get('keyspace_hits', 0)
    misses = stats.get('keyspace_misses', 0)
    hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0
    REDIS_CACHE_HIT_RATE.set(hit_rate)

    REDIS_KEYS_TOTAL.set(redis_client.dbsize())
    REDIS_EVICTED_KEYS.inc(stats.get('evicted_keys', 0))
```

**Add to main.py:**

```python
# backend/main.py
from utils.redis_metrics import collect_redis_metrics

async def redis_metrics_task():
    """Background task - collect every 60 sec"""
    while True:
        try:
            await asyncio.to_thread(
                collect_redis_metrics,
                redis_first_data_service.redis_client
            )
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            await asyncio.sleep(60)

# In lifespan():
asyncio.create_task(redis_metrics_task())
```

### Grafana Dashboards

See [PROMETHEUS_GRAFANA_SETUP.md](./PROMETHEUS_GRAFANA_SETUP.md) for:
- Memory Usage panel
- Cache Hit Rate gauge
- Keys by Type pie chart
- Eviction Rate counter
- Command Latency heatmap

---

## 🔧 Troubleshooting

### Issue 1: OOM Error

**Error:** "OOM command not allowed"

**Solution:**
```bash
# Quick fix
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Permanent (Railway)
REDIS_MAXMEMORY_POLICY=allkeys-lru
```

### Issue 2: Max Clients Reached

**Error:** "ERR max number of clients reached"

**Solution:**
```bash
# Check connections
redis-cli CLIENT LIST | wc -l

# Increase limit
REDIS_MAXCLIENTS=20000

# Verify connection pooling enabled (already done)
```

### Issue 3: Data Loss After Restart

**Problem:** Cache empty after deployment

**Solution:**
```bash
# Enable persistence
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec

# Make permanent
REDIS_APPENDONLY=yes
REDIS_APPENDFSYNC=everysec
```

### Issue 4: Low Cache Hit Rate (<90%)

**Problem:** Slow responses, high API usage

**Solution:**
```bash
# Check hit rate
redis-cli INFO stats | grep keyspace

# Check TTLs
redis-cli --scan --pattern "ticker_data:*" | while read key; do
  echo "$key: $(redis-cli TTL $key)s"
done | head -10

# Implement differentiated TTL strategy (see above)
```

---

## ✅ Production Checklist

**Before Deployment:**

### Configuration
- [ ] `REDIS_MAXMEMORY=256mb`
- [ ] `REDIS_MAXMEMORY_POLICY=allkeys-lru`
- [ ] `REDIS_APPENDONLY=yes`
- [ ] `REDIS_APPENDFSYNC=everysec`
- [ ] Connection pool configured (✅ done)

### TTL Strategy
- [ ] Differentiated TTL implemented
- [ ] Jitter enabled (prevent stampede)
- [ ] TTLs verified

### Monitoring
- [ ] Prometheus metrics enabled
- [ ] Grafana dashboard created
- [ ] Alerts configured:
  - [ ] Memory > 80% → Warning
  - [ ] Memory > 90% → Critical
  - [ ] Hit rate < 90% → Warning
  - [ ] Evictions > 0 → Critical

### Testing
- [ ] Persistence tested (survives restart)
- [ ] Connection pool tested (100 req/sec)
- [ ] Memory limits tested
- [ ] Cache hit rate > 95%
- [ ] TTL jitter working

---

## 📚 Quick Reference

### Essential Commands

```bash
# Health
redis-cli PING

# Memory
redis-cli INFO memory

# Keys
redis-cli DBSIZE
redis-cli --scan --pattern "ticker_data:*"

# Get/Set
redis-cli GET "key"
redis-cli SET "key" "value"
redis-cli TTL "key"
redis-cli DEL "key"

# Danger
redis-cli FLUSHALL  # Clear ALL data!

# Monitoring
redis-cli MONITOR
redis-cli CLIENT LIST
```

### Railway Configuration

```bash
# Complete Railway Redis setup
REDIS_MAXMEMORY=256mb
REDIS_MAXMEMORY_POLICY=allkeys-lru
REDIS_APPENDONLY=yes
REDIS_APPENDFSYNC=everysec
REDIS_MAXCLIENTS=10000
REDIS_TIMEOUT=300
```

---

## 🚀 Next Steps

1. ✅ Configure Redis (this guide)
2. ⏭️ Set up Prometheus + Grafana
3. ⏭️ Implement TTL strategy
4. ⏭️ Create dashboards
5. ⏭️ Configure alerts
6. ⏭️ Deploy to production

**Related Docs:**
- [Prometheus + Grafana Setup](./PROMETHEUS_GRAFANA_SETUP.md)
- [Supabase Integration](./SUPABASE_INTEGRATION_PLAN.md)

---

**Questions?** Review [Troubleshooting](#troubleshooting) or contact DevOps team.
