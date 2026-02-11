# Guide to Production – Portfolio Navigator Wizard

This is the single guide for taking the app to production on Railway. It states what is already in place, what you must do next, and how to deploy and operate safely.

---

## Table of Contents

1. [Deployment architecture](#deployment-architecture-intended-for-production)
2. [What we have already](#what-we-have-already)
3. [Next steps to production](#next-steps-to-production)
4. [Railway deployment steps](#railway-deployment-steps)
5. [Environment variables](#environment-variables)
6. [Post-deployment](#post-deployment)
7. [Troubleshooting](#troubleshooting)
8. [Performance expectations](#performance-expectations)

---

## Deployment architecture (intended for production)

What runs where and how traffic flows:

```
  User browser
       |
       v
  [ Frontend ]  (Railway: root=frontend, serve dist on $PORT)
  https://<your-frontend>.up.railway.app
       |
       |  VITE_API_BASE_URL = backend URL (set at build time)
       |  ALLOWED_ORIGINS on backend must include this exact origin
       v
  [ Backend ]   (Railway: root=backend, uvicorn on $PORT)
  https://<your-backend>.up.railway.app
       |
       |  REDIS_URL from Railway Redis (same project)
       v
  [ Redis ]     (Railway Database: Redis)

  GitHub (repo) --> Railway project: 3 services
    - 1x Redis (add from template)
    - 1x Backend (deploy from repo, root=backend)
    - 1x Frontend (deploy from repo, root=frontend)
```

- The frontend talks only to the backend (CORS). The backend talks to Redis. No browser-to-Redis connection.
- Health checks use the backend: `/health` or `/api/v1/portfolio/health`. Do not expose Redis publicly.

---

## What we have already

Verified in the codebase; no code changes required for a standard Railway deploy.

**Backend**

- **Redis**: Uses `REDIS_URL` everywhere (`backend/utils/redis_first_data_service.py`, `enhanced_data_fetcher.py`, `shareable_link_generator.py`). Default `redis://localhost:6379` for local only; production must set `REDIS_URL`. Supports `redis://` and `rediss://` with timeouts.
- **CORS**: `backend/main.py` reads `ALLOWED_ORIGINS` (comma-separated), trims whitespace, no hardcoded production URLs.
- **Port**: Start command uses `$PORT`; `backend/Dockerfile` uses `$PORT` and PORT-aware HEALTHCHECK for container deploys.
- **Health**: `/health` and `/healthz` in main; `/api/v1/portfolio/health` in admin router (Redis ping + cache status). Both safe when Redis is down (no crash).
- **Lifespan**: Redis-first data service, portfolio manager, strategy optimizer; lazy/background init where heavy. No blocking production-only assumptions.

**Frontend**

- **API base URL**: `frontend/src/config/api.ts` uses `import.meta.env.VITE_API_BASE_URL || ''`. Build-time only; no hardcoded backend URL. Dev uses Vite proxy; production must set `VITE_API_BASE_URL` when building.
- **Build**: `npm run build` produces `dist/`. No dev-only assumptions in build output.

**Config and docs**

- **backend/.env.example**: Documents `REDIS_URL`, `ALLOWED_ORIGINS`, `ENVIRONMENT`, `ALPHA_VANTAGE_API_KEY`, and optional TTL/Redis/API options.
- **frontend/.env.example**: Documents `VITE_API_BASE_URL` and Railway notes.
- **backend/Dockerfile**: Uses `$PORT` and health check on same port; suitable for Railway (and other hosts that set `PORT`).

**Not present / you must provide**

- No `.env` or production secrets in repo (correct). You set variables in Railway.
- No hardcoded production URLs; you set `ALLOWED_ORIGINS` and `VITE_API_BASE_URL` to your real URLs.

---

## Next steps to production

Do these in order.

1. **Railway and GitHub**
   - Ensure the repo is connected to Railway (or connect it).
   - You will create one project with three services: Redis, Backend, Frontend.

2. **Create Redis**
   - In the project: New → Database → Redis.
   - Copy `REDIS_URL` from the Redis service (Variables or Connect). You will add it to the Backend service.

3. **Deploy backend first**
   - New service from GitHub repo; root directory **backend**.
   - Set build/start and variables (see [Railway deployment steps](#railway-deployment-steps)).
   - Set `REDIS_URL` and `ALLOWED_ORIGINS` (you can use a placeholder for the frontend URL and update it after step 5).
   - Generate a public domain for the backend and note the URL.

4. **Deploy frontend**
   - New service from same repo; root directory **frontend**.
   - Set `VITE_API_BASE_URL` to the **exact** backend URL from step 3 (must be set before build).
   - Build and start as in the guide; generate a public domain and note the frontend URL.

5. **Point CORS at real frontend**
   - In the Backend service variables, set `ALLOWED_ORIGINS` to your real frontend URL (e.g. `https://your-frontend.up.railway.app`). No trailing slash. If you used a placeholder in step 3, update it and redeploy the backend.

6. **Smoke test**
   - Open the frontend URL; try search or recommendations; confirm no CORS errors in the browser console.
   - Optionally warm Redis (see [Post-deployment](#post-deployment)).

---

## Railway deployment steps

### 1. Railway account and project

- Sign in at https://railway.app (e.g. with GitHub).
- Create a new project; connect the GitHub repo if not already connected.

### 2. Add Redis

- In the project: **New → Database → Redis**.
- Open the Redis service → **Variables** (or **Connect**) and copy **REDIS_URL**. Use this in the Backend service.

### 3. Deploy backend

- **New → GitHub Repo** (or equivalent). Select this repository.
- **Root directory**: `backend`
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Variables** (required):
  - `REDIS_URL` = value from Redis service (or reference from Redis service if Railway supports it).
  - `ALLOWED_ORIGINS` = your frontend URL, e.g. `https://your-frontend.up.railway.app` (no trailing slash). You can set this after the frontend is deployed; then redeploy backend.
  - `ENVIRONMENT` = `production`
- **Variables** (optional): `ALPHA_VANTAGE_API_KEY` = your key (app works without it; uses Yahoo Finance).
- **Settings → Networking**: Generate a public domain. Note the backend URL for the frontend and CORS.

### 4. Deploy frontend

- **New → GitHub Repo** (same repo, second service).
- **Root directory**: `frontend`
- **Build command**: `npm ci && npm run build` (or `npm install && npm run build`)
- **Start command**: `npx serve -s dist -l $PORT`
- **Variables** (required, build-time): `VITE_API_BASE_URL` = backend URL from step 3 (e.g. `https://your-backend.up.railway.app`)
- **Settings → Networking**: Generate a public domain. Note the frontend URL.

### 5. CORS

- In Backend variables, set `ALLOWED_ORIGINS` to the exact frontend origin (e.g. `https://your-frontend.up.railway.app`). No trailing slash. Redeploy backend if you changed it.

---

## Environment variables

### Backend (Railway)

| Variable | Required | Example / notes |
|----------|----------|------------------|
| `REDIS_URL` | Yes | From Railway Redis service |
| `ALLOWED_ORIGINS` | Yes | `https://your-frontend.up.railway.app` (exact origin) |
| `ENVIRONMENT` | Recommended | `production` |
| `ALPHA_VANTAGE_API_KEY` | No | Improves data options; app works with Yahoo only without it |
| `PORT` | Injected by Railway | Do not set manually; start command uses `$PORT` |

### Frontend (Railway, build-time)

| Variable | Required | Example / notes |
|----------|----------|------------------|
| `VITE_API_BASE_URL` | Yes | `https://your-backend.up.railway.app` |

---

## Post-deployment

1. **Health**
   - `GET https://<backend>/health` or `GET https://<backend>/api/v1/portfolio/health`. Both should return 200. Portfolio health includes `dependencies.redis` (e.g. `"healthy"` when Redis is up).

2. **Redis cache**
   - New Redis is empty. Either let it fill via normal use or call a warm endpoint if you have one (e.g. `POST /api/v1/portfolio/warm-cache` if available and rate-limited). First searches may be slow until cache is populated.

3. **Frontend**
   - Open the frontend URL; run a full flow (e.g. search, recommendations). If you see CORS errors, fix `ALLOWED_ORIGINS` and redeploy backend.

4. **Monitoring**
   - Use Railway logs for backend and Redis. Watch Redis memory and adjust plan if needed.

---

## Troubleshooting

| Problem | Fix |
|--------|-----|
| CORS errors in browser | Set `ALLOWED_ORIGINS` to exact frontend origin (https, no trailing slash). Redeploy backend. |
| Frontend gets 404 on /api/... | Set `VITE_API_BASE_URL` in frontend service and **rebuild** (and redeploy) frontend. |
| Backend "Redis connection failed" | Set `REDIS_URL` from Redis service; ensure Redis is in same project and running. |
| Backend 502 or unreachable | Start command must use `$PORT`. If using Dockerfile, ensure it uses `$PORT` (current Dockerfile does). |
| Health check fails | Use `/health` or `/healthz`; allow ~30–60 s start period. |

---

## Performance expectations

- **Will improve on Railway**: Redis latency (backend and Redis in same region); ticker search and all Redis-heavy flows get faster. No cold sleep if the plan is always-on.
- **Will not change by default**: Algorithm still does many Redis calls per search; improvement is from lower latency per call. First requests on empty Redis can still be slow until cache is warm.
- **Optional later**: Cache the list of “cached tickers” (e.g. Redis set or in-memory with TTL) to reduce Redis round-trips per search.

---

## Summary

- **What we have**: Production-ready configuration (REDIS_URL, ALLOWED_ORIGINS, VITE_API_BASE_URL, PORT in Dockerfile, health endpoints, env examples). No code change needed for a standard Railway deploy.
- **Next steps**: Create Redis → deploy backend with REDIS_URL and ALLOWED_ORIGINS → deploy frontend with VITE_API_BASE_URL → set ALLOWED_ORIGINS to real frontend URL → smoke test and optionally warm Redis.
