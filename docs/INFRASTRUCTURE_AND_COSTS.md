# Infrastructure & Cost Analysis

**Last Updated:** 2026-03-06
**Status:** Production

---

## Current Infrastructure

### Fly.io Machines

| Component | App Name | Region | vCPU | Memory | State | Purpose |
|-----------|----------|--------|------|--------|-------|---------|
| **Backend** | portfolio-navigator-wizard | ams (Amsterdam) | 1 shared | 2GB | Always running | FastAPI + 2 uvicorn workers |
| **Frontend** | portfolio-navigator | arn (Stockholm) | 1 shared | 256MB | Always running | React SPA via nginx |

### External Services

| Service | Provider | Tier | Capacity | Purpose |
|---------|----------|------|----------|---------|
| **Redis** | Redis Cloud | Free | 30MB, unlimited commands | Caching, session storage, search index |
| **Email** | Gmail SMTP | Free | ~500/day | Notifications, alerts |

---

## Monthly Cost Breakdown

### Fly.io Pricing (as of March 2026)

| Resource | Unit Price | Our Usage | Monthly Cost |
|----------|------------|-----------|--------------|
| **Shared CPU (1x)** | $1.94/mo | 2 machines | $3.88 |
| **Memory (256MB)** | $0.97/mo | 256MB (frontend) | $0.97 |
| **Memory (2GB)** | $7.76/mo | 2GB (backend) | $7.76 |
| **Outbound Transfer** | $0.02/GB (after 100GB free) | ~5-10GB/mo | $0.00 |
| **Persistent Storage** | N/A | None used | $0.00 |

### Total Monthly Costs

| Item | Cost |
|------|------|
| Backend (2GB, shared CPU) | $9.70 |
| Frontend (256MB, shared CPU) | $2.91 |
| Redis Cloud (Free Tier) | $0.00 |
| Gmail SMTP | $0.00 |
| Domain/SSL | $0.00 (Fly provides) |
| **Total** | **~$12.61/month** |

---

## What You're Paying For

### Backend ($9.70/mo)

| Feature | Why 2GB? |
|---------|----------|
| **2 Uvicorn Workers** | Prevents event loop blocking during heavy operations |
| **NumPy/SciPy Operations** | Portfolio optimization requires ~500MB per calculation |
| **In-Memory Search Index** | 1415 tickers + 8309 prefixes (~50MB) |
| **Concurrent Requests** | Handle multiple users without queuing |

The 2GB allocation allows:
- 2 workers x ~750MB each = ~1.5GB baseline
- ~500MB headroom for numpy operations and spikes

### Frontend ($2.91/mo)

| Feature | Why 256MB? |
|---------|------------|
| **Static File Serving** | nginx serves pre-built React bundles |
| **No Server-Side Logic** | All computation happens on client or backend |
| **Minimal Memory** | 256MB is sufficient for nginx + static files |

### Redis Cloud (Free)

| Feature | Usage |
|---------|-------|
| **30MB Storage** | Currently using ~15-20MB |
| **Ticker Cache** | 1415 tickers with prices, metrics, sector data |
| **Portfolio Cache** | Pre-generated portfolio recommendations |
| **Search Index** | Stored in memory (not Redis) for speed |

---

## Capacity Analysis: 300-400 Monthly Users

### Traffic Estimation

Assuming:
- 400 monthly active users
- 3 sessions per user per month
- 5 minutes per session
- Peak: 20% of traffic in 4 hours (evening)

| Metric | Calculation | Result |
|--------|-------------|--------|
| Total sessions/month | 400 x 3 | 1,200 |
| Avg sessions/day | 1,200 / 30 | 40 |
| Peak sessions/hour | 40 x 0.2 / 4 | 2 |
| Peak concurrent users | 2 x 5min / 60min | ~0.17 |

**Conclusion:** With ~0.17 concurrent users at peak, traffic is extremely low.

### Backend Capacity

| Metric | Current Capacity | 400 Users Need |
|--------|------------------|----------------|
| **Concurrent Requests** | 50 soft / 100 hard | < 5 |
| **Workers** | 2 | 1 would suffice |
| **Memory** | 2GB | 1GB would work |
| **Search Latency** | 23ms | Unchanged |

**Verdict: OVER-PROVISIONED**

The current setup could handle **10x more traffic** (3,000-4,000 monthly users) before needing upgrades.

### Frontend Capacity

| Metric | Current | Assessment |
|--------|---------|------------|
| **Concurrency** | 200 soft / 250 hard | Far exceeds need |
| **Memory** | 256MB | Sufficient |
| **Static Assets** | CDN-like serving | Scales automatically |

**Verdict: ADEQUATE**

### Redis Capacity

| Metric | Current | 400 Users |
|--------|---------|-----------|
| **Storage** | ~18MB / 30MB | ~20MB (users don't add data) |
| **Commands/sec** | Unlimited | < 10/sec typical |
| **Connections** | 30 max | < 5 active |

**Verdict: ADEQUATE** (users don't store data, only read cached portfolios)

---

## Performance Characteristics

### Current Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Health check | ~100ms | Proxy + backend |
| Stock search (company name) | **23ms server** | In-memory index |
| Portfolio generation | 2-5s | Pre-generated, instant if cached |
| Page load (frontend) | ~500ms | Static assets |

### Bottlenecks at Scale

| Users | Bottleneck | Solution |
|-------|------------|----------|
| 400 | None | Current setup handles easily |
| 2,000 | Redis free tier limits | Upgrade to paid ($7/mo) |
| 5,000 | Backend memory | Add second machine |
| 10,000+ | Need load balancer | Multiple machines + Redis cluster |

---

## Cost Optimization Options

### If Budget is Tight

| Change | Savings | Trade-off |
|--------|---------|-----------|
| Reduce backend to 1GB | -$3.88/mo | Risk of OOM during heavy operations |
| Use 1 worker | -$0 (same cost) | Event loop blocking risk |
| Stop frontend when idle | -$1/mo max | Cold start delay |

**Not Recommended:** Current costs are already minimal ($12.61/mo).

### If Scaling Up

| Users | Recommended Changes | Additional Cost |
|-------|---------------------|-----------------|
| 1,000 | No changes needed | $0 |
| 2,000 | Upgrade Redis to $7/mo tier | +$7 |
| 5,000 | Add second backend machine | +$9.70 |
| 10,000 | Redis cluster + 3 backends | +$40-50 |

---

## Summary

| Question | Answer |
|----------|--------|
| **Can current setup handle 300-400 users?** | Yes, easily (10x headroom) |
| **Monthly cost** | ~$12.61 |
| **Biggest expense** | Backend memory (2GB = $7.76) |
| **Free tier dependencies** | Redis Cloud (30MB) |
| **When to upgrade** | At ~2,000+ monthly users |

The current infrastructure is well-optimized for a portfolio management application with moderate traffic. The 2GB backend is the right choice for numpy/scipy operations, and the 256MB frontend is minimal for static serving.
