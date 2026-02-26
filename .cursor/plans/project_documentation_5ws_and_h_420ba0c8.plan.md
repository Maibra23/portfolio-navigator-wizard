---
name: Project documentation 5Ws and H
overview: Create a single markdown file that documents the entire Portfolio Navigator Wizard project using the 5 W's and H format (Who, What, Where, When, Why, How), including system components, integrations, frontend features, and clear flowcharts/examples.
todos: []
isProject: false
---

# Project Documentation: 5 W's and H

## Objective

Produce one new markdown file that serves as the single source of truth for the project. The document will be structured around **Who, What, Where, When, Why, and How**, and will include flowcharts (mermaid) and concrete examples.

## File to Create

- **Path:** [docs/PROJECT_OVERVIEW_5W1H.md](docs/PROJECT_OVERVIEW_5W1H.md) (or root-level if you prefer; docs/ keeps it with existing guides like RISK_PROFILING_QUESTIONNAIRE_AND_LOGIC.md, PORTFOLIOS_IN_REDIS.md).

## Content Structure (5 W's and H)

### 1. WHO

- **Actors:** End users (investors), optional admins (warm-cache, cache clear via X-Admin-Key).
- **Systems:** Frontend (React app), Backend (FastAPI), Redis (cache and rate limiting), Alpha Vantage (market data), Yahoo Finance (prices, FX), SMTP (email alerts). No Postgres/Supabase in current code.
- **Mermaid:** High-level actor/system diagram (Browser, React, FastAPI, Redis, Alpha Vantage, Yahoo, SMTP).

### 2. WHAT

- **Product:** Full-stack Portfolio Navigator Wizard: behavioral risk profiling + portfolio recommendations + optimization + stress testing + finalize/export.
- **Main features (concise list):** 8-step wizard (Welcome, Risk, Capital, Stock Selection, Optimization, Stress Test, Finalize, Thank You); risk profiling (MPT + Prospect Theory, 5 categories, safeguards); 60+ pre-computed portfolios in Redis; triple optimization (current, weights-only, market); 15 stress scenarios + Monte Carlo; PDF/CSV export, shareable links, Swedish tax, 5-year projections.
- **System components:**
  - **Backend:** [backend/main.py](backend/main.py) (lifespan, CORS, middleware), [backend/routers/portfolio.py](backend/routers/portfolio.py) (main API), [backend/routers/strategy_buckets.py](backend/routers/strategy_buckets.py), [backend/routers/admin.py](backend/routers/admin.py); services in [backend/utils/](backend/utils/) (redis_first_data_service, redis_portfolio_manager, enhanced_data_fetcher, portfolio_mvo_optimizer, strategy_portfolio_optimizer, stress_test_analyzer, pdf_report_generator, shareable_link_generator, email_notifier, redis_ttl_monitor, etc.).
  - **Frontend:** [frontend/src/App.tsx](frontend/src/App.tsx) (routes), [frontend/src/components/PortfolioWizard.tsx](frontend/src/components/PortfolioWizard.tsx) (orchestrator, wizard state), steps under [frontend/src/components/wizard/](frontend/src/components/wizard/) (WelcomeStep, RiskProfiler, CapitalInput, StockSelection, PortfolioOptimization, StressTest, FinalizePortfolio, ThankYouStep); [frontend/src/config/api.ts](frontend/src/config/api.ts) (API base and endpoints).
- **Mermaid:** Component block diagram (Frontend blocks, Backend routers + utils, Redis, external APIs).

### 3. WHERE

- **Locations:** Frontend dev port 8080, backend 8000; production: VITE_API_BASE_URL and ALLOWED_ORIGINS.
- **Code:** frontend/src (pages, components, contexts, hooks, config), backend (routers, utils, models, middleware, config).
- **API surface:** `/api/v1/portfolio/`* (and legacy `/api/portfolio/`*), `/api/v1/strategy-buckets/`*, `/health`, `/metrics`. Key endpoints from [frontend/src/config/api.ts](frontend/src/config/api.ts): RECOMMENDATIONS, CALCULATE_METRICS, ELIGIBLE_TICKERS, TICKER_METRICS, CACHE_*, etc.; admin under same router with Depends(require_admin_key).
- **Redis:** Used for ticker cache, portfolio buckets, strategy portfolios, eligible-tickers cache, rate-limit state, shareable links; keys/patterns as in redis_first_data_service and redis_portfolio_manager.
- **Mermaid:** Request path (Browser -> Vite proxy /api -> Backend:8000 -> Redis or external API).

### 4. WHEN

- **Wizard sequence:** Welcome -> Risk Profile -> Capital -> Stock Selection -> Optimization -> Stress Test -> Finalize -> Thank You (defined in PortfolioWizard STEPS).
- **Background tasks (main.py lifespan):** Cold-start check and optional full cache warm-up + email; TTL monitoring (first run after 5 min, then every 6 h); cache regeneration supervisor (after 10 min, every 30 min); Redis health watchdog (after 2 min, every 60 s); eligible-tickers and portfolio pre-generation on cold start.
- **When features run:** Risk profiling runs in-browser (scoring-engine, safeguards) then results shown; recommendations/optimization/stress-test when user reaches those steps and frontend calls backend; export/finalize when user completes FinalizePortfolio tabs.
- **Mermaid:** Simple timeline or flowchart: App start -> Cold start? -> Background tasks; User flow -> Step 1..8.

### 5. WHY

- **Goals:** Personalized, theory-grounded portfolio recommendations; combine MPT and behavioral finance (Prospect Theory); high performance (Redis-first, sub-5ms cached); accessibility (WCAG); dual theme; production-ready (health, metrics, alerts).
- **Why Redis:** Single persistence/cache layer for speed and simplicity; no relational DB in current design.
- **Why admin key:** Protect warm-cache and cache-clear from public; optional.

### 6. HOW

- **Integration:** CORS via ALLOWED_ORIGINS; dev proxy in [frontend/vite.config.ts](frontend/vite.config.ts) (/api -> 127.0.0.1:8000); frontend uses API_BASE_URL (empty in dev) and API_ENDPOINTS; admin requests send X-Admin-Key when VITE_ADMIN_API_KEY is set.
- **Data flows (with mermaid):**
  - Risk: User answers -> scoring-engine -> safeguards -> confidence band -> risk category.
  - Portfolio: Risk + capital -> recommendations from Redis -> user picks or builds -> calculate-metrics / optimization/triple.
  - Backend request: Client -> FastAPI -> Router -> Redis or EnhancedDataFetcher (Alpha Vantage / Yahoo) -> response.
- **Examples (in the MD):**
  - One API example: e.g. GET recommendations (risk_profile=moderate) request and sample JSON response.
  - One wizard flow example: e.g. "User on Stock Selection step -> calls RECOMMENDATIONS(moderate) -> receives 3–5 portfolios -> selects one -> next step."
  - One Redis key example: e.g. portfolio_bucket:moderate:* or ticker:AAPL (no deletion; describe only).

## Flowcharts and Diagrams (Mermaid)

- **System context:** Who (actors + external systems) and Where (ports, API prefix).
- **Component view:** What (frontend components, backend routers/utils).
- **Request flow:** How (browser -> frontend -> proxy -> backend -> Redis or external API).
- **Wizard flow:** When (step order) and How (risk -> capital -> stocks -> optimization -> stress -> finalize).
- **Background tasks:** When (startup and intervals) and How (cold start, TTL, supervisor, watchdog).

Use valid mermaid syntax: camelCase/PascalCase node IDs, quoted edge labels if needed, no spaces in node IDs, no style/color overrides (per workspace mermaid rules).

## Implementation Notes

- **Single file:** All content in one MD; no creation of extra txt or other MD unless needed for this deliverable.
- **Factual basis:** Use only what exists in the repo (README, backend routers, frontend config, explore results); do not document planned-but-unimplemented features (e.g. Supabase) as current behavior.
- **References:** Link to key files (main.py, portfolio.py, PortfolioWizard.tsx, api.ts, etc.) with relative paths from repo root.
- **Tone:** Clear, factual, suitable for onboarding and handover; examples kept short.

## Verification

- After the file is created (post-plan): confirm all links resolve, mermaid renders in the intended viewer, and the 5 W's and H sections are complete with no placeholder "TBD" left.

