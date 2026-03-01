---
name: Fly.io Pre-Deployment Audit
overview: "Structured pre-deployment audit for deploying the Portfolio Navigator Wizard on Fly.io via GitHub, covering architecture, backend/frontend readiness, Docker/Fly config, secrets, Redis, branch strategy, security, and runtime risks. Conclusion: backend-only deployment is viable; single-app (frontend + backend) requires additional Docker and backend changes."
todos: []
isProject: false
---

# Fly.io Pre-Deployment Audit Report

## Executive Summary

- **Backend-only deployment on Fly.io**: Viable with current root [Dockerfile](Dockerfile) and [fly.toml](fly.toml). Fix port alignment, set ALLOWED_ORIGINS and optional secrets, add explicit HTTP health check.
- **Single-app (frontend + backend in one Fly app)**: Not implemented. Backend does not build or serve the frontend; one production port is used (8080) but only for the API. Structural and Docker changes are required if you want a true single-app.
- **Alpha Vantage**: Excluded per your request. Backend uses [config/settings.py](backend/config/settings.py) (optional key with placeholder); [config/api_config.py](backend/config/api_config.py) is not imported anywhere and would raise if imported without the key—no change needed for current code path.

---

## Phase 1: Architecture and Deployment Strategy

### Current state

- **Does the backend serve the frontend production build?** No. There is no `StaticFiles` mount or any route serving `frontend/dist` in [backend/main.py](backend/main.py).
- **Is the frontend built during Docker build?** No. The root [Dockerfile](Dockerfile) only copies `backend/` and installs Python deps; it does not run `npm run build` or copy frontend assets.
- **Is only one production port exposed?** Yes. The app listens on `PORT` (8080 on Fly); Redis is in-process, not a separate port.
- **Are dev servers disabled in production?** N/A for backend (uvicorn only). Frontend is not in the image.

**Conclusion**: The repo is set up for **backend-only** on Fly (API + bundled Redis). Single-app deployment (one Fly app serving both UI and API) is **not** currently viable.

### Changes required for single-app deployment

If you want one Fly app to serve both frontend and backend:

1. **Multi-stage Dockerfile** (conceptual):
  - Stage 1: Node 20, build frontend with `VITE_API_BASE_URL` set to `""` (same-origin) or to the Fly app URL.
  - Stage 2: Copy `frontend/dist` into the Python image and mount it in FastAPI via `StaticFiles`.
  - Single CMD: start Redis, then uvicorn (no separate frontend process).
2. **Backend**:
  - Mount static files, e.g. `app.mount("/", StaticFiles(directory="dist", html=True), name="frontend")` for SPA (only in production when `dist` exists).
  - Keep API under `/api` so same-origin requests need no CORS for the app origin.
3. **Frontend**:
  - Build with `VITE_API_BASE_URL=""` so API calls are same-origin (e.g. `/api/v1/portfolio/...`).
4. **fly.toml**:
  - No change to `internal_port`; single port still serves both static and API.

---

## Phase 2: Backend Production Readiness


| Check                              | Status   | Notes                                                                                                                    |
| ---------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| Bind to 0.0.0.0                    | OK       | [backend/main.py](backend/main.py) and Dockerfile use `--host 0.0.0.0`.                                                  |
| Dynamic PORT                       | OK       | `port = int(os.getenv("PORT", "8000"))` in `__main`__; CMD uses `--port ${PORT:-8000}`.                                  |
| Debug disabled                     | OK       | No `debug=True`; ENVIRONMENT controls error exposure.                                                                    |
| CORS from env                      | OK       | `ALLOWED_ORIGINS` from env in [backend/main.py](backend/main.py) (lines 1168–1175).                                      |
| No localhost hardcoding for server | OK       | Bind is 0.0.0.0; REDIS_URL is env (localhost in Docker is intentional for bundled Redis).                                |
| No dev-only middleware in prod     | OK       | TrustedHost, security headers, CORS are env/production-aware.                                                            |
| Sensitive data / error leakage     | OK       | [backend/main.py](backend/main.py) `is_production()` hides 5xx details (lines 882–885, 906–908).                         |
| Admin 500 details                  | Low risk | Admin routes in [backend/routers/admin.py](backend/routers/admin.py) return `str(e)` in 500; protected by ADMIN_API_KEY. |


**Port mismatch (must fix)**  
[fly.toml](fly.toml) sets `PORT=8080` and `internal_port = 8080`. The root [Dockerfile](Dockerfile) sets `ENV PORT=8000` and `EXPOSE 8000`. At runtime Fly injects PORT=8080, so the app will listen on 8080—correct. The only fix needed is to make the **image** default match Fly so local runs and healthchecks are consistent: e.g. in Dockerfile use `ENV PORT=8080` and `EXPOSE 8080`, or drop default and rely on Fly’s PORT (healthcheck already uses `os.environ.get('PORT', '8000')`; change default to `8080` if you standardize on 8080).

**Recommendation**: Set Dockerfile `ENV PORT=8080` and `EXPOSE 8080` so build and fly.toml are aligned.

---

## Phase 3: Frontend Production Readiness

- **Production build**: `vite build` in [frontend/package.json](frontend/package.json); no dev flags in production build.
- **API URL**: [frontend/src/config/api.ts](frontend/src/config/api.ts) uses `import.meta.env.VITE_API_BASE_URL || ""`. Empty string relies on Vite dev proxy in development; in production (if frontend is deployed separately) `VITE_API_BASE_URL` must be set at **build time** to the backend URL.
- **Secrets**: `VITE_ADMIN_API_KEY` is optional and, if set, is embedded in the client bundle; use only for admin/cache-warming from trusted environments.
- **Build for container**: Standard Vite build; no blocker for containerization.

If you move to single-app (backend serves frontend): build with `VITE_API_BASE_URL=""` so all API calls are same-origin.

---

## Phase 4: Docker and Fly.io Configuration

**Dockerfile (root)**  

- Structure: Single stage, backend + Redis, no frontend.  
- Port: EXPOSE 8000 and ENV PORT=8000; at runtime Fly overrides to 8080. Align Dockerfile to 8080 as above.  
- CMD: `redis-server --daemonize yes ... && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`. Use `8080` in default if you standardize: `--port ${PORT:-8080}`.  
- Healthcheck: Uses `os.environ.get('PORT', '8000')` and `/healthz`. Update default to `8080` if you align on 8080.

**fly.toml**  

- [build] dockerfile = "Dockerfile" — correct.  
- [env] PORT=8080, REDIS_URL, ENVIRONMENT, USE_LIVE_DATA, etc. — good.  
- [http_service] internal_port 8080, force_https true — correct.  
- **Missing**: Explicit HTTP health check. Default may be TCP; an HTTP check to `/healthz` improves deployment reliability (especially with long cold starts).

**Suggested addition to fly.toml** (after `[http_service]`):

```toml
  [[http_service.checks]]
    grace_period = "30s"
    interval     = "30s"
    method       = "GET"
    path         = "/healthz"
    timeout      = "5s"
```

**Stateless vs stateful**  

- App is stateless; Redis is in-container with `--save ""` and `--appendonly no`, so data is ephemeral. Cold start after each deploy is expected; startup logic already handles empty Redis and background warm-up.

**Resource**  

- 1 GB memory, 1 shared CPU in [fly.toml](fly.toml) is reasonable for one backend + in-process Redis.

---

## Phase 5: Secrets and Environment Variable Audit

**Sources**: [backend/.env.example](backend/.env.example), [fly.toml](fly.toml), [frontend/.env.example](frontend/.env.example). Alpha Vantage excluded.

**Required for production (Fly)**

- **ALLOWED_ORIGINS** — Must include the Fly app URL (e.g. `https://portfolio-navigator-wizard.fly.dev`) and, if you use a separate frontend, that origin. Set in fly.toml [env] or Fly secrets.
- **ENVIRONMENT** — Set to `production` (already in fly.toml).
- **REDIS_URL** — Set in fly.toml to `redis://localhost:6379` (bundled Redis).
- **PORT** — Set in fly.toml to 8080.

**Recommended (Fly secrets)**

- **ADMIN_API_KEY** — Strong random value; required for admin endpoints (warm-cache, clear-cache, etc.). Without it, admin returns 503.
- **SMTP_USER**, **SMTP_PASSWORD**, **TTL_NOTIFICATION_EMAIL** — If you enable TTL email notifications.
- **METRICS_SECRET** — If you want to restrict `/metrics` (optional).
- **SENTRY_DSN**, **SENTRY_ENVIRONMENT** — Optional; for error tracking.

**Optional / non-secret (fly.toml [env])**

- USE_LIVE_DATA, MANUAL_REGENERATION_REQUIRED (already set).
- CACHE_REGEN_*, ENABLE_HTTPS_REDIRECT, ALLOWED_HOSTS, LOG_LEVEL, ENABLE_DEBUG_LOGS, etc., as needed.

**Do not deploy**

- Alpha Vantage keys (excluded per request).
- Development-only values (e.g. ENVIRONMENT=development, localhost-only ALLOWED_ORIGINS) in production.

**Final Fly secrets list (production, Alpha Vantage excluded)**

- `ADMIN_API_KEY` (recommended)
- `SMTP_USER`, `SMTP_PASSWORD`, `TTL_NOTIFICATION_EMAIL` (if using email alerts)
- `METRICS_SECRET` (optional)
- `SENTRY_DSN` (optional)

**Variables to set in fly.toml [env] (non-secret)**  

- `ALLOWED_ORIGINS` = `https://portfolio-navigator-wizard.fly.dev` (and other allowed origins if any).
- Already present: ENVIRONMENT, PORT, REDIS_URL, USE_LIVE_DATA, MANUAL_REGENERATION_REQUIRED.

**Security note**  

- Do not put ALLOWED_ORIGINS in secrets unless it contains sensitive URLs; [env] is fine. Keep ADMIN_API_KEY and SMTP credentials in Fly secrets only.

---

## Phase 6: Database and Redis Connectivity

- **Database**: No PostgreSQL or other SQL; application uses Redis only.
- **Redis**: [backend/utils/redis_first_data_service.py](backend/utils/redis_first_data_service.py) uses `REDIS_URL` (default `redis://localhost:6379`). In Fly, Redis runs in the same container; REDIS_URL in fly.toml is correct.
- **No embedded credentials**: Redis URL from env; no credentials in code.
- **Persistence**: In-container Redis is configured with no persistence (`--save ""`, `--appendonly no`). Data is lost on restart; no volume required. Startup logic handles cold start and background regeneration.

**Connection risk**  

- If Redis fails to start or is slow, the app may log and run with degraded behavior; health check can return degraded. Consider making `/healthz` depend on Redis ping and return 503 when Redis is down, so Fly can treat the instance as unhealthy (optional refinement).

---

## Phase 7: GitHub and Branch Deployment Readiness

- **Current branch**: `final-testing-visuals` (with uncommitted changes in backend and frontend).
- **CI**: [.github/workflows/ci.yml](.github/workflows/ci.yml) runs on push and PRs to `main` (backend tests, frontend lint). No Fly deploy step yet.
- **Merge recommendation**: Merge to `main` when tests and lint pass and you are satisfied with the branch. Deploy from `main` (or a release branch) so Fly GitHub integration tracks a single, stable branch.
- **CI/CD for Fly**: Add a workflow that runs on push to `main` (e.g. `fly deploy --remote-only`) with `FLY_API_TOKEN` in GitHub secrets. Ensure required Fly secrets and [env] (e.g. ALLOWED_ORIGINS) are set in the Fly app before first deploy.

**Pre-merge**  

- Run backend tests and frontend lint locally or via PR to `main`. Resolve any failures before merging.

---

## Phase 8: Security Review

- **Admin auth**: [backend/routers/portfolio_shared.py](backend/routers/portfolio_shared.py) uses `hmac.compare_digest` and fail-closed when ADMIN_API_KEY is unset — good.
- **CORS**: Env-based ALLOWED_ORIGINS; restrict to production origins in prod.
- **TrustedHost**: Enabled in production with ALLOWED_HOSTS including `*.fly.dev` in [backend/main.py](backend/main.py).
- **Security headers**: [backend/middleware/security.py](backend/middleware/security.py) sets CSP, HSTS (when redirect enabled), X-Frame-Options, etc. CSP includes `unsafe-inline`/`unsafe-eval` for React — acceptable; tighten if possible later.
- **Input validation**: [backend/middleware/validation.py](backend/middleware/validation.py) validates tickers and other inputs; ValidationError handled in main.
- **Rate limiting**: slowapi with Redis backend in [backend/middleware/rate_limiting.py](backend/middleware/rate_limiting.py).
- **5xx handling**: Production does not expose internal error details to clients.
- **Dependencies**: Run `pip audit` or similar before release; no automated scan was run in this audit.

**Findings**  

- **Low**: Admin 500 responses expose exception messages (admin-only, behind key).  
- **Low**: CSP allows `unsafe-inline`/`unsafe-eval` for React.  
- **Informational**: Ensure ALLOWED_ORIGINS and ALLOWED_HOSTS do not include wildcards or unnecessary origins in production.

---

## Phase 9: Deployment Simulation and Runtime Risk Forecast

Assumptions: stateless container, Fly secrets set, external DB none (Redis in-container), ENVIRONMENT=production.


| Risk                       | Likelihood          | Severity | Mitigation                                                                                     |
| -------------------------- | ------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| Port binding failure       | Low                 | High     | PORT=8080 in fly.toml and app; align Dockerfile default to 8080.                               |
| CORS blocking browser      | High if wrong       | Medium   | Set ALLOWED_ORIGINS to Fly app URL (and frontend origin if separate).                          |
| Missing ALLOWED_ORIGINS    | Medium              | High     | Add ALLOWED_ORIGINS to fly.toml [env] before first deploy.                                     |
| Admin endpoints 503        | Expected if no key  | Low      | Set ADMIN_API_KEY in Fly secrets if you use admin features.                                    |
| Health check failure       | Medium (cold start) | High     | Add explicit `[[http_service.checks]]` for `/healthz` with grace_period ≥ 30s.                 |
| Build failure              | Low                 | High     | CI already runs backend tests and frontend lint; run on main before deploy.                    |
| Redis not ready at startup | Low                 | Medium   | Redis started before uvicorn in CMD; if needed, add retry or health dependency.                |
| Cold start timeout         | Medium              | Medium   | Startup does heavy work in background; grace_period 30s and timeout 5s for checks should help. |


**Highest-impact fixes**: Set ALLOWED_ORIGINS; add HTTP health check in fly.toml; align Dockerfile PORT/EXPOSE to 8080.

---

## Required Deliverables Summary

**Deployment blockers**  

1. **ALLOWED_ORIGINS** not set for production — set to Fly app URL (and any separate frontend origin).
2. **Single-app** — not supported without adding frontend build and StaticFiles mount (see Phase 1).

**Security vulnerabilities**  

- No critical or high issues identified. Low: admin 500 details; CSP relaxations for React.

**Required code/infra adjustments**  

1. **fly.toml**: Add `ALLOWED_ORIGINS` to [env]; add `[[http_service.checks]]` for GET `/healthz` (grace_period 30s, timeout 5s).
2. **Dockerfile**: Set `ENV PORT=8080`, `EXPOSE 8080`, and use `--port ${PORT:-8080}` and healthcheck default `8080` for consistency.
3. **Single-app (optional)**: Multi-stage Dockerfile, build frontend with VITE_API_BASE_URL="", mount `dist` in FastAPI, serve SPA at `/`.

**Required Fly secrets list (Alpha Vantage excluded)**  

- ADMIN_API_KEY (recommended)  
- SMTP_USER, SMTP_PASSWORD, TTL_NOTIFICATION_EMAIL (if using email)  
- METRICS_SECRET, SENTRY_DSN (optional)

**Docker/Fly config corrections**  

- Dockerfile: PORT 8080, EXPOSE 8080, healthcheck default 8080.  
- fly.toml: ALLOWED_ORIGINS in [env]; [[http_service.checks]] for /healthz.

**Merge strategy**  

- Merge `final-testing-visuals` into `main` after tests and lint pass. Connect Fly to GitHub and deploy from `main`. Ensure Fly secrets and ALLOWED_ORIGINS are set before first deploy.

**Runtime risk assessment**  

- Main risks: CORS (wrong ALLOWED_ORIGINS), health check too aggressive during cold start, missing ALLOWED_ORIGINS. Addressed by the changes above.

**Final go/no-go**  

- **Go for backend-only deployment** after: (1) setting ALLOWED_ORIGINS, (2) adding HTTP health check in fly.toml, (3) aligning Dockerfile to port 8080, (4) setting ADMIN_API_KEY (and optional SMTP/Sentry) in Fly secrets.  
- **No-go for single-app** until frontend build and static serving are added as in Phase 1.

