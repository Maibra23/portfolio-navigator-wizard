# Portfolio Navigator Wizard

Step-by-step wizard to build investment portfolios: risk profiling, stock selection, optimization, and stress testing, backed by behavioral finance and modern portfolio theory.

![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-5.0+-DC382D?style=flat&logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

**Live API:** [portfolio-navigator-wizard.fly.dev](https://portfolio-navigator-wizard.fly.dev)

## Table of Contents

- [Portfolio Navigator Wizard](#portfolio-navigator-wizard)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Key Features](#key-features)
  - [Project Architecture](#project-architecture)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [Project Structure](#project-structure)
  - [Development](#development)
  - [Testing](#testing)
  - [Deployment](#deployment)
  - [Contributing](#contributing)
  - [License](#license)
  - [Documentation](#documentation)

## Overview

Portfolio Navigator Wizard helps users build and analyze investment portfolios through a guided, step-by-step flow. It addresses the need for a single place to assess risk tolerance (using behavioral finance and Modern Portfolio Theory), choose or build a portfolio, compare optimized strategies, stress-test outcomes, and export reports.

**The** goal is to help young users and newcomers to investing learn the basics of building portfolios in a guided, low-friction way—from risk tolerance and asset selection to optimization and stress testing. The project is aimed at students, educators, and anyone exploring portfolio construction and risk profiling in a structured way. It is developed as part of coursework at Linnaeus University, Sweden.

The app guides users through eight steps: welcome, risk profiling (including an in-step results view with confidence bands and category), capital input, stock selection and portfolio builder, portfolio optimization (triple comparison and efficient frontier), stress testing, finalization (projections, tax, export), and a thank-you step. The backend serves portfolio data, optimization, and analytics via a FastAPI API with Redis-backed caching for low-latency responses.

## Key Features

- **Behavioral risk profiling** — Questionnaire combining Modern Portfolio Theory and Prospect Theory; adaptive question selection and safeguards; risk results shown within the risk step.
- **Portfolio optimization** — Triple comparison (current, weights-optimized, market-optimized), efficient frontier visualization, and pre-computed recommendations per risk profile.
- **Stress testing** — Multiple market scenarios and resilience metrics.
- **Redis-backed performance** — Caching for portfolio and ticker data; lazy loading for fast startup.
- **Export and reporting** — PDF reports, CSV export, 5-year projections, Swedish tax and courtage (e.g. Avanza) considerations, shareable links.
- **Dual theme** — Classic and dark themes with persisted preference.
- **Accessibility** — WCAG-oriented design and responsive layout.
- **Testing** — Frontend and backend test suites; run via Make targets.

## Project Architecture

The frontend (React + TypeScript, Vite) runs on port 8080 and talks to the FastAPI backend on port 8000. The backend uses a Redis-first data layer for caching; production on Fly.io uses Redis Cloud (external), not in-container Redis.

```
Browser  <->  React (port 8080)  <->  FastAPI (port 8000)  <->  Redis
```

Frontend state is managed with React Context for wizard data and TanStack Query for server state. The backend exposes portfolio, optimization, analytics, and admin endpoints under `/api/v1/portfolio` and related routers; health checks are at `/health` and `/healthz`.

For deeper architecture and Redis key design, see [docs/REDIS_ARCHITECTURE.md](docs/REDIS_ARCHITECTURE.md) and [docs/BACKEND_UTILS_REFERENCE.md](docs/BACKEND_UTILS_REFERENCE.md).

## Installation

**Prerequisites:** Node.js 18+, Python 3.8+, Redis 5.0+, Git.

- **macOS:** `brew install redis && brew services start redis`
- **Ubuntu/Debian:** `sudo apt install redis-server`
- **Windows:** Use WSL or install Redis from [redis.io](https://redis.io/download).

```bash
git clone https://github.com/your-username/portfolio-navigator-wizard.git
cd portfolio-navigator-wizard

make install
# Ensure Redis is running (e.g. brew services start redis), then:
make dev
```

The frontend is at **http://localhost:8080** and the API at **http://localhost:8000**.

**Troubleshooting:** If the backend fails to start, run `make check-redis`. If a port is in use, stop other processes on 8000/8080 or use `make stop` then `make dev`. If you see `[vite] Pre-transform error: [postcss] ETIMEDOUT: connection timed out, read` when running `make full-dev` or `make dev`, it is often transient (e.g. OneDrive sync or a slow read). Retry the command; the project uses a local `browserslist` in `frontend/package.json` so autoprefixer does not need the network. If it persists, run the frontend from a local non-synced copy of the repo. More detail: [docs/DEPLOYMENT_OPERATIONS.md](docs/DEPLOYMENT_OPERATIONS.md).

## Usage

After `make dev`, use:

| Resource | URL |
|----------|-----|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API docs (ReDoc) | http://localhost:8000/redoc |
| Health | http://localhost:8000/health or http://localhost:8000/healthz |
| Portfolio bucket status | http://localhost:8000/api/v1/enhanced-portfolio/buckets |

Run `make help` for all Make targets (e.g. `make backend`, `make frontend`, `make regenerate-portfolios`, `make test-backend`, `make test-frontend`).

## Configuration

Backend configuration is via environment variables or a `.env` file in `backend/`. Common options:

- **Redis:** `REDIS_HOST`, `REDIS_PORT`, or `REDIS_URL` (production).
- **API:** `API_HOST`, `API_PORT` (default 8000).
- **Cache:** `TICKER_CACHE_TTL`, `PORTFOLIO_CACHE_TTL`; optional cache warming and TTL notifications.
- **Production (Fly.io):** Set `REDIS_URL`, `ADMIN_API_KEY`, and optionally SMTP/notification vars via `fly secrets set`. See [docs/DEPLOYMENT_OPERATIONS.md](docs/DEPLOYMENT_OPERATIONS.md) for production and monitoring.

## Project Structure

```
portfolio-navigator-wizard/
├── frontend/                 # React + TypeScript (Vite)
│   ├── src/
│   │   ├── components/       # UI and wizard step components
│   │   │   ├── ui/           # Reusable UI (e.g. shadcn/ui)
│   │   │   └── wizard/       # Wizard steps (RiskProfiler, StockSelection, etc.)
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
├── backend/                  # FastAPI + Python
│   ├── routers/              # portfolio, strategy_buckets, admin, portfolio_shared
│   ├── models/
│   ├── utils/                # Redis, optimization, stress test, PDF/CSV, etc.
│   ├── main.py
│   └── requirements.txt
├── docs/                     # Project documentation
├── Makefile
└── README.md
```

Wizard steps are defined in `frontend/src/components/PortfolioWizard.tsx`; API routes are in `backend/routers/` and `backend/main.py`.

## Development

- **Run app:** `make dev` (backend + frontend). Backend only: `make backend`; frontend only: `make frontend`.
- **Tests:** See [Testing](#testing). Before submitting changes, run `make test-frontend` and `make test-backend`.
- **Portfolio data:** `make regenerate-portfolios` regenerates pre-computed portfolios; `make verify-portfolios` checks counts. Use `make help` for other targets.

For adding wizard steps or API endpoints, see the existing components in `frontend/src/components/wizard/` and routers in `backend/routers/`; detailed backend modules are described in [docs/BACKEND_UTILS_REFERENCE.md](docs/BACKEND_UTILS_REFERENCE.md).

## Testing

- **Frontend:** `make test-frontend` or `cd frontend && npm run test`. Tests live in `frontend/src/components/wizard/__tests__/` and elsewhere under `frontend/src`.
- **Backend:** `make test-backend` or `cd backend && pytest` (with venv activated).
- **System checks:** `make test-systems` for broader verification.

No copy-paste test snippets are included here; refer to the test files in the repo.

## Deployment

Production runs on **Fly.io** in the **ams** (Amsterdam) region. The app listens on internal port **8080**; health checks use **/healthz**. Production uses **Redis Cloud** (managed Redis); set `REDIS_URL` and other secrets via `fly secrets set`. See `fly.toml` and [docs/DEPLOYMENT_OPERATIONS.md](docs/DEPLOYMENT_OPERATIONS.md) for the full runbook, including optional SMTP/notifications and monitoring. For Docker or VPS, use the backend and frontend Dockerfiles and refer to the deployment doc.

## Contributing

Fork the repository, create a branch, make your changes, run tests (`make test-frontend`, `make test-backend`), and open a pull request. Keep changes focused and document behavior where relevant. For clone URL when contributing, use your fork: `git clone https://github.com/your-username/portfolio-navigator-wizard.git`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Documentation

| Document | Description |
|----------|-------------|
| [BACKEND_UTILS_REFERENCE.md](docs/BACKEND_UTILS_REFERENCE.md) | Backend modules and utilities |
| [DATA_SOURCES_AND_METHODOLOGY.md](docs/DATA_SOURCES_AND_METHODOLOGY.md) | Data sources and methodology |
| [DEPLOYMENT_OPERATIONS.md](docs/DEPLOYMENT_OPERATIONS.md) | Deployment and operations runbook |
| [REDIS_ARCHITECTURE.md](docs/REDIS_ARCHITECTURE.md) | Redis data flow and usage |
| [PURE_STRATEGY_PORTFOLIOS.md](docs/PURE_STRATEGY_PORTFOLIOS.md) | Strategy portfolio logic |
| [DOCUMENTATION_REVIEW.md](docs/DOCUMENTATION_REVIEW.md) | Documentation inventory and cleanup notes |

API documentation is available at http://localhost:8000/docs and http://localhost:8000/redoc when the backend is running.
