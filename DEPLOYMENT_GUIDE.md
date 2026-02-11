# Deployment Guide – Railway Only

This guide covers deploying Portfolio Navigator Wizard to Railway and whether the project is production-ready. It also explains how deployment affects performance, especially ticker search and Redis.

---

## Deployment architecture (intended for user)

What runs where and how traffic flows after a successful deploy:

```
  User browser
       |
       v
  [ Frontend ]  (Railway service: root=frontend, serve dist on $PORT)
  https://<your-frontend>.up.railway.app
       |
       |  VITE_API_BASE_URL = backend URL (set at build time)
       |  ALLOWED_ORIGINS on backend must include this exact origin
       v
  [ Backend ]   (Railway service: root=backend, uvicorn on $PORT)
  https://<your-backend>.up.railway.app
       |
       |  REDIS_URL from Railway Redis (same project)
       v
  [ Redis ]     (Railway Database: Redis)
  Private/internal URL linked to backend

  GitHub (repo) --> Railway project: 3 services
    - 1x Redis (add from template)
    - 1x Backend (deploy from repo, root=backend)
    - 1x Frontend (deploy from repo, root=frontend)
```

Important: The frontend talks only to the backend (same-origin or CORS). The backend talks to Redis. There is no browser-to-Redis connection. Health checks: use backend `/health` or `/api/v1/portfolio/health`; do not expose Redis publicly.

---

## Table of Contents

1. [Overview](#overview)
2. [Production Readiness Review](#production-readiness-review)
3. [Railway Deployment Steps](#railway-deployment-steps)
4. [Environment Variables](#environment-variables)
5. [Performance: Will Deployment Be Faster?](#performance-will-deployment-be-faster)
6. [Post-Deployment](#post-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The app has three parts:

- **Frontend**: React + Vite (static build served by `serve` or similar).
- **Backend**: FastAPI (Python), single service.
- **Redis**: Used for ticker cache, master list, metrics, and session-like data.

Railway runs backend and Redis in the same project (and usually same region). The frontend can be on Railway or another host; only CORS and `VITE_API_BASE_URL` must match.

---

## Production Readiness Review

### What Is Already Production-Ready

- **Redis**
  - Uses `REDIS_URL` (no localhost hardcode). See `backend/utils/redis_first_data_service.py`: `redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')`, and `_init_redis_from_url()` supports `redis://` and `rediss://`.
  - Connection timeouts and optional TLS are in place.

- **CORS**
  - Driven by env: `ALLOWED_ORIGINS` in `backend/main.py` (comma-separated list). Add your production frontend URL(s) in Railway.

- **Frontend API URL**
  - `frontend/src/config/api.ts` uses `import.meta.env.VITE_API_BASE_URL || ''`. Set `VITE_API_BASE_URL` at build time to your backend URL.

- **Backend structure**
  - `backend/main.py` uses lifespan, structured logging, and initializes Redis-first data service. No hardcoded dev-only assumptions that block production.

- **Docker**
  - `backend/Dockerfile` and `docker-compose.yml` exist if you want to run the backend as a container on Railway.

### What You Must Set for Production

| Item | Where | Notes |
|------|--------|------|
| `REDIS_URL` | Railway (from Redis service) | Railway provides this when you add Redis. |
| `ALLOWED_ORIGINS` | Railway backend env | Include your real frontend URL, e.g. `https://your-app.railway.app`. |
| `VITE_API_BASE_URL` | Railway frontend env (build) | Backend URL, e.g. `https://your-backend.railway.app`. |
| `ALPHA_VANTAGE_API_KEY` | Railway backend env | Optional but recommended; app works with Yahoo Finance only if unset. |
| `ENVIRONMENT` | Railway backend env | Set to `production` for production. |

### Optional but Recommended

- Rate limiting: already used in the app (e.g. slowapi). Ensure it’s enabled in production.
- Health checks: use `/health` or `/api/v1/portfolio/health` for Railway’s health checks.
- TTL monitoring: background task in main.py; ensure it doesn’t overwhelm Redis in production.

### Verdict

**Production-ready from a configuration perspective** provided you:

1. Set the variables above on Railway.
2. Point the frontend build at the correct backend URL.
3. Warm or populate Redis (see Post-Deployment) so search and recommendations work well.

---

## Railway Deployment Steps

### 1. Railway account and project

- Sign up at https://railway.app (e.g. with GitHub).
- Create a new project and connect the repo (or use CLI).

### 2. Add Redis

- In the project: **New → Database → Redis**.
- After creation, open the Redis service → **Variables** (or **Connect**) and copy **REDIS_URL**. You will give this to the backend.

### 3. Deploy backend

- **New → GitHub Repo** (or “Empty” and connect later). Select the same repo.
- Configure the service:
  - **Root directory**: `backend`
  - **Build command**: `pip install -r requirements.txt` (or leave default if it already does this).
  - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - **Watch paths**: `backend/**` if available.
- **Variables**: Add at least:
  - `REDIS_URL` = value from Redis service (Railway can reference it as `$REDIS_URL` from the Redis service if linked).
  - `ALLOWED_ORIGINS` = your frontend URL(s), e.g. `https://your-frontend.railway.app`
  - `ENVIRONMENT` = `production`
  - `ALPHA_VANTAGE_API_KEY` = your key (optional).
- **Settings → Networking**: Generate a public domain and note the URL (e.g. `https://your-backend.railway.app`).

### 4. Deploy frontend

- **New → GitHub Repo** (same repo, second service).
- Configure:
  - **Root directory**: `frontend`
  - **Build command**: `npm ci && npm run build` (or `npm install && npm run build`).
  - **Start command**: `npx serve -s dist -l $PORT` (or `serve -s dist -p $PORT` if `serve` is in dependencies).
- **Variables** (must be set at build time):
  - `VITE_API_BASE_URL` = backend URL from step 3 (e.g. `https://your-backend.railway.app`).
- **Settings → Networking**: Generate a domain (e.g. `https://your-frontend.railway.app`).

### 5. CORS

- Ensure `ALLOWED_ORIGINS` on the backend includes the exact frontend URL (and any custom domain). No trailing slash. Example: `https://your-frontend.railway.app`.

---

## Environment Variables

### Backend (Railway)

| Variable | Required | Example / Notes |
|----------|----------|------------------|
| `REDIS_URL` | Yes | From Railway Redis service |
| `ALLOWED_ORIGINS` | Yes | `https://your-frontend.railway.app` |
| `ENVIRONMENT` | Recommended | `production` |
| `ALPHA_VANTAGE_API_KEY` | Optional | Improves data options; app works without it |
| `PORT` | Set by Railway | Usually provided automatically |

### Frontend (Railway, build-time)

| Variable | Required | Example / Notes |
|----------|----------|------------------|
| `VITE_API_BASE_URL` | Yes | `https://your-backend.railway.app` |

---

## Performance: Will Deployment Be Faster?

### Short answer

Yes. Once Redis and the backend run on Railway (same region/network), anything that talks to Redis tends to get faster: lower latency per Redis call and no home/office network in the path. Ticker search and all Redis-backed features benefit.

### Why ticker search is slow locally

From your logs, search does things like:

- “Searching 'baba' through 1432 cached tickers”
- “Searching 'm' through 1432 cached tickers” → 294 candidates
- “Searching 'msft' through 1432 cached tickers”

Current implementation (in `backend/utils/redis_first_data_service.py`):

1. **Build “cached” list**: For each of the master tickers (e.g. 1432), it calls Redis twice (`_is_cached(t, 'prices')` and `_is_cached(t, 'sector')`). So each search does on the order of **2 × N Redis round-trips** (N = number of master tickers) just to see which tickers are cached.
2. **Pre-filter**: Iterates that list for symbol/prefix and optionally company-name matches; for company name it may load sector data from Redis for many tickers.
3. **Score and return**: For each candidate it may call `get_ticker_info(ticker)` (more Redis).

So locally you see high latency because:

- Many sequential Redis round-trips (network latency per call).
- Possible CPU/contention on your machine.

### Why it will be faster on Railway

- **Redis and backend on the same provider/region**: Redis round-trip time drops (often to well under 1 ms per call instead of a few ms over your local network). Same number of calls, but total time for “build cached list + candidates + ticker_info” goes down.
- **Dedicated CPU/memory**: The backend process isn’t competing with your IDE and other local apps, so request handling can be faster.
- **No cold start from “sleep”**: If you use Railway’s always-on plan, there’s no 30s wake-up like on some free tiers elsewhere.

So:

- **Ticker search**: Same code, but faster (often noticeably: e.g. 30–50 s locally → much lower on Railway, depending on query and cache state). Exact numbers depend on Redis plan and region.
- **Anything that uses Redis** (recommendations, stress test, metrics, cache warming, etc.): Same idea — fewer ms per Redis call and more stable performance.

### Making search even faster later (optional)

The current design does **O(N)** Redis `EXISTS` (and possibly more) per search. To improve further without changing UX:

- **Cache the list of “cached tickers”**: Maintain one structure (e.g. a Redis set or a key listing ticker symbols) that is updated when tickers are added/refreshed/expired. Then search can use that list instead of 2×N `_is_cached` calls per request.
- **In-memory cache**: Cache the “cached tickers” list in the backend process with a short TTL (e.g. 60 s) so repeated searches don’t hit Redis for the same list every time.

Those are optimizations; deployment alone should already make search and all Redis-related flows faster.

---

## Post-Deployment

### 1. Health check

- Backend: `GET https://your-backend.railway.app/health` or `GET https://your-backend.railway.app/api/v1/portfolio/health`.
- Confirm Redis is up (backend logs and health response).

### 2. Redis cache warming

- New Redis starts empty. Either:
  - Let it fill as users search and use features, or
  - Call your cache-warming endpoint if you have one (e.g. `GET /api/v1/portfolio/cache/warm` or similar), or
  - Run any backend script you use to preload master list and key tickers.
- Until Redis is populated, first searches and recommendations may be slower or depend on live fetches.

### 3. Frontend

- Open the frontend URL, try search and a full flow. If you see CORS errors, double-check `ALLOWED_ORIGINS` and that `VITE_API_BASE_URL` was set when the frontend was built.

### 4. Monitoring

- Use Railway logs for backend and Redis.
- Watch Redis memory; upgrade plan if you approach limits with your ticker set and TTLs.

---

## Troubleshooting

### Frontend cannot reach backend (CORS / network)

- Confirm `ALLOWED_ORIGINS` includes the exact frontend origin (no trailing slash).
- Confirm `VITE_API_BASE_URL` was set at **build** time and matches the backend URL.
- Test backend directly: `curl https://your-backend.railway.app/health`.

### Redis connection errors

- Ensure backend has `REDIS_URL` from the Redis service (copy from Redis service Variables in Railway).
- If Redis is in the same project, use Railway’s internal URL if documented (sometimes faster and more reliable than public URL).

### Ticker search still slow after deploy

- Check Redis and backend are in the same region.
- Confirm Redis has enough memory and isn’t evicting keys under load.
- Consider adding the “cached tickers list” cache (or in-memory cache) described above for further gains.

### Build or start command fails

- Backend: Ensure `backend/requirements.txt` exists and `uvicorn main:app` runs from `backend` (root directory set to `backend`).
- Frontend: Ensure `VITE_API_BASE_URL` is set in Railway for the frontend service so the build embeds the correct API URL.

---

## Summary

- **Deployment target**: Railway only (this guide).
- **Production readiness**: Configuration is production-ready; set `REDIS_URL`, `ALLOWED_ORIGINS`, `VITE_API_BASE_URL`, and `ENVIRONMENT` correctly.
- **Performance**: Deployment will make Redis-bound work (including ticker search) faster due to lower Redis latency and dedicated resources; for even faster search, add a cached list of cached tickers or an in-memory cache later.
