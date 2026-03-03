# Portfolio Navigator Wizard - Complete Project Analysis

Generated: 2026-03-01

---

## Task 1: Branch Merge Decision

### Current Branch Status

**Active Branch:** `Project-complete`

**Branch Comparison:**
- `Project-complete` is **67 commits ahead** of `main`
- `main` has **0 commits** not in `Project-complete`
- Total changes: **262 files changed, 99,697 insertions(+), 11,572 deletions(-)**

### Recent Commits in Project-complete (Latest 10)

1. `e6da4313` feat: enhance security and validation in portfolio management
2. `18e73f2c` refactor: update Dockerfile, fly.toml, and backend configurations
3. `e5d44bec` feat: enhance PortfolioBuilder and StockSelection components
4. `deedb3db` feat: enhance portfolio sector enrichment and PDF report generation
5. `8d152476` feat: enhance portfolio wizard and PDF report generation
6. `fcc7d142` chore: clean up README and update optionality rules
7. `b98c3e18` feat: enhance README and improve PDF report generation
8. `c7c97fbd` chore: remove test email notification script
9. `3085877e` feat: update portfolio configurations and enhance PDF report generation
10. `b9787a8c` feat: transition from Slack to email notifications for alerts

### Key Features Added Since main

1. **Security & Validation** - Enhanced portfolio management security
2. **Dockerfile & fly.toml** - Updated for Fly.io deployment
3. **PortfolioBuilder & StockSelection** - Enhanced UI components
4. **PDF Report Generation** - Academic-style reports with methodology
5. **Email Notifications** - Transitioned from Slack to email alerts
6. **Redis Optimization** - Improved configuration and monitoring
7. **Dual Theme System** - Classic and Dark themes
8. **Swedish Tax Calculator** - ISK, KF, AF account types
9. **Avanza Transaction Costs** - Courtage class calculations
10. **Stress Testing** - 15 market scenarios with Monte Carlo
11. **5-Year Projections** - With tax and cost integration

### Merge Recommendation

**RECOMMENDATION: Merge `Project-complete` into `main` before deploying to Fly.io**

**Reasoning:**

| Factor | Assessment | Details |
|--------|------------|---------|
| **Code Conflicts** | LOW RISK | Project-complete is strictly ahead of main; no divergent commits |
| **Deployment Stability** | HIGH | Dockerfile and fly.toml have been updated and configured |
| **Feature Completeness** | COMPLETE | All major features implemented and tested |
| **Blockers** | NONE | No outstanding blockers identified |

### Prerequisites Before Merge

1. **Environment Variables** - Ensure all required env vars are set in Fly.io:
   - `REDIS_URL` - Redis connection string
   - `TTL_EMAIL_NOTIFICATIONS` - Enable email alerts
   - `TTL_NOTIFICATION_EMAIL` - Recipient email
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` - Email configuration
   
2. **Redis Service** - Verify Redis is provisioned on Fly.io

3. **Health Checks** - Verify `/health` endpoint responds correctly

4. **Cache Warming** - Initial deployment will trigger cold-start cache warming

### Merge Commands

```bash
# Switch to main
git checkout main

# Merge Project-complete
git merge Project-complete

# Push to remote
git push origin main

# Deploy to Fly.io
fly deploy
```

---

## Task 2: Documentation Audit & Update

### Project Overview

**Portfolio Navigator Wizard** is a production-grade investment platform that combines behavioral finance principles with Modern Portfolio Theory to deliver personalized investment recommendations through an interactive, multi-step wizard interface.

**Purpose:** Help users build optimized investment portfolios based on their risk tolerance, investment goals, and behavioral preferences.

**Target Users:** Individual investors seeking data-driven portfolio recommendations with Swedish tax optimization.

### Major Components and Responsibilities

#### 1. Frontend (React + TypeScript)

| Component | Responsibility | Lines |
|-----------|---------------|-------|
| `PortfolioWizard.tsx` | Main orchestrator for 8-step wizard flow | ~500 |
| `RiskProfiler.tsx` | Behavioral risk assessment with MPT and Prospect Theory questions | 2,488 |
| `StockSelection.tsx` | Ticker search, portfolio recommendations, custom builder | 3,787 |
| `PortfolioOptimization.tsx` | Triple optimization analysis with efficient frontier | 8,827 |
| `StressTest.tsx` | 15 market scenarios, Monte Carlo simulation | 5,053 |
| `FinalizePortfolio.tsx` | Export, tax, costs, shareable links | 2,264 |
| `EfficientFrontierChart.tsx` | Interactive risk/return visualization | 1,758 |
| `Portfolio3PartVisualization.tsx` | Three-column portfolio comparison | 2,531 |

#### 2. Backend (FastAPI + Python)

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `main.py` | Application entry, lifespan events, middleware | ~800 |
| `routers/portfolio.py` | Main portfolio API endpoints | 11,659 |
| `routers/admin.py` | Admin authentication and management | 254 |
| `routers/strategy_buckets.py` | Strategy portfolio endpoints | 90 |

#### 3. Backend Utils (Detailed Breakdown)

##### Core Portfolio Systems

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `portfolio_mvo_optimizer.py` | Mean-variance optimization using PyPortfolioOpt | Tickers, optimization type, constraints | Optimal weights, return, risk, Sharpe | pypfopt, numpy, scipy |
| `port_analytics.py` | Portfolio analytics: metrics, efficient frontier, Monte Carlo | Price series, weights, tickers | Metrics, frontier points, risk profiles | quantstats, pypfopt |
| `enhanced_portfolio_generator.py` | Generates 12 portfolios per risk profile | Data service, risk profile | 12 compliant portfolios | portfolio_stock_selector, port_analytics |
| `portfolio_stock_selector.py` | Stock selection by sector, volatility, risk profile | Risk profile, variation seed | Stock allocations | redis_first_data_service, risk_profile_config |
| `enhanced_stock_selector.py` | Extended selector with return/diversification targets | Risk profile, targets | Dynamic allocations | portfolio_stock_selector, dynamic_weighting_system |
| `strategy_portfolio_optimizer.py` | Strategy-specific portfolios (diversification, risk, return) | Strategy name, risk profiles | Pure and personalized buckets | portfolio_stock_selector, port_analytics |
| `conservative_portfolio_generator.py` | Conservative generation for aggressive profiles | Risk profile, metrics | Quality assessment | risk_profile_config |
| `dynamic_weighting_system.py` | Multi-objective portfolio weighting | Stocks, target return, risk range | Optimal weights | numpy, scipy |

##### Data Services

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `redis_first_data_service.py` | Redis-first data access with external fallback | Ticker, force_refresh | Price data, ticker info | redis, pandas, EnhancedDataFetcher |
| `enhanced_data_fetcher.py` | Fetch/cache price and sector data from Yahoo | Ticker list | Price dicts, sector info | yfinance, yahooquery, redis |
| `fx_fetcher.py` | FX rates for USD normalization | Currency, date range | FX rates | yahooquery, redis |
| `timestamp_utils.py` | Timestamp and ticker normalization | Timestamps, tickers | Normalized formats | pandas, numpy |

##### Redis Management

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `redis_config.py` | TTL, jitter, connection settings | TTL, data type | Config, jittered TTL | redis |
| `redis_portfolio_manager.py` | Store/retrieve portfolio buckets | Risk profile, portfolios | Stored/retrieved portfolios | redis, risk_profile_config |
| `redis_ttl_monitor.py` | TTL monitoring and alerts | Redis client | TTL status, reports | redis, email_notifier |
| `redis_metrics.py` | Redis metrics for Prometheus | Redis client | Prometheus gauges | redis, shared.metrics |
| `portfolio_auto_regeneration_service.py` | Manual portfolio regeneration | Data service, generator | Success/failure status | redis_portfolio_manager |

##### Export & Reporting

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `pdf_report_generator.py` | Academic-style PDF reports | Portfolio data, metrics | PDF bytes | reportlab, matplotlib |
| `csv_export_generator.py` | CSV exports for various data types | Portfolios, metrics | CSV strings | csv, io |
| `shareable_link_generator.py` | Shareable links with expiry | Portfolio, expiry, password | Link ID, data | redis, argon2 |

##### Financial Calculations

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `swedish_tax_calculator.py` | ISK, KF, AF Swedish tax calculations | Account type, tax year, capital | Tax breakdown | None |
| `transaction_cost_calculator.py` | Avanza courtage calculations | Order value, courtage class | Cost breakdowns | None |
| `five_year_projection.py` | 5-year projections with tax and costs | Capital, weights, return, risk | Projection series | swedish_tax_calculator, transaction_cost_calculator |
| `stress_test_analyzer.py` | Historical crisis stress testing | Price dicts, weights | Crisis impact, recovery | pandas, numpy |

##### Configuration & Utilities

| File | Purpose | Inputs | Outputs | Dependencies |
|------|---------|--------|---------|--------------|
| `risk_profile_config.py` | Single source of truth for risk parameters | Risk profile | Config dicts | None |
| `enhanced_portfolio_config.py` | Enhanced portfolio generation config | Risk profile, index | Targets, config | risk_profile_config |
| `volatility_weighted_sector.py` | Volatility-weighted sector weights | Risk profile, stocks | Sector weights | None |
| `diversification_experiments.py` | Diversification strategies | Risk profile | Ranges, flags | risk_profile_config |
| `email_notifier.py` | SMTP email notifications | Message, throttle | Email sent | smtplib |
| `logging_utils.py` | Job loggers with file output | Logger name | Logger | logging |
| `anonymous_analytics.py` | Backend metrics for Prometheus | Strategy, counts | Prometheus metrics | shared.metrics |

### Features Implemented

#### 1. Risk Profiling System
- **Adaptive Questioning** - Questions adapt based on age, experience, knowledge
- **MPT Questions** - 15 questions covering time horizon, volatility, diversification
- **Prospect Theory Questions** - 12 questions covering loss aversion, certainty effect
- **Gamified Path** - Interactive scenarios for users under 19
- **5 Risk Categories** - Very Conservative to Very Aggressive (0-100 score)
- **Safeguards** - Loss sensitivity, pattern detection, extreme confirmations
- **Confidence Bands** - Uncertainty calculations for risk assessment

#### 2. Portfolio Generation
- **60+ Pre-computed Portfolios** - 12 per risk profile, cached in Redis
- **Stock Selection** - 600+ tickers (S&P 500 + Nasdaq 100 + European stocks)
- **Sector Diversification** - Intelligent sector allocation
- **Quality Controls** - Return and risk compliance checks
- **Automatic Regeneration** - TTL-based cache refresh

#### 3. Portfolio Optimization
- **Triple Optimization** - Current, Weights-Optimized, Market-Optimized
- **Efficient Frontier** - Interactive visualization with Capital Market Line
- **Decision Framework** - Automatic recommendation based on Sharpe improvement
- **Constraint Handling** - Risk profile-based bounds

#### 4. Stress Testing
- **15 Market Scenarios** - 2008 Crisis, COVID-19, Inflation, Bear Markets, etc.
- **Monte Carlo Simulation** - Statistical performance analysis
- **Historical Backtesting** - Performance against actual market data
- **Recovery Metrics** - Drawdown analysis and trajectory projections
- **Resilience Scoring** - Portfolio robustness assessment

#### 5. Export & Finalization
- **5-Year Projections** - Optimistic, base, pessimistic scenarios
- **Swedish Tax Integration** - ISK, KF, AF account calculations
- **Transaction Costs** - Avanza courtage for all classes
- **PDF Reports** - Academic-style with methodology, glossary, figures
- **CSV Export** - Holdings, tax, costs, metrics, Monte Carlo
- **Shareable Links** - Password-protected with expiry

#### 6. Monitoring System
- **Cold-Start Detection** - Triggers cache warming on empty Redis
- **TTL Monitoring** - Alerts when data approaches expiry
- **Cache Regeneration** - Proactive refresh before TTL
- **Redis Watchdog** - Connectivity monitoring with alerts
- **HTTP 5xx Alerts** - Email notifications on server errors

### Environment Setup

#### Prerequisites
```
Node.js >= 18
Python >= 3.8
Redis >= 5.0
```

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Frontend Setup
```bash
cd frontend
npm install
```

#### Environment Variables (backend/.env)
```env
# Redis
REDIS_URL=redis://localhost:6379

# Email Notifications
TTL_EMAIL_NOTIFICATIONS=true
TTL_NOTIFICATION_EMAIL=your@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app_password

# Cache Settings
TICKER_CACHE_TTL=3600
PORTFOLIO_CACHE_TTL=1800
```

#### Running Locally
```bash
# Start both frontend and backend
make dev

# Or separately
make backend  # Port 8000
make frontend # Port 8080
```

### Deployment Notes (Fly.io)

#### fly.toml Configuration
- Primary region configured
- Health check endpoint: `/health`
- Auto-scaling settings
- Redis addon required

#### Deployment Commands
```bash
fly deploy
fly status
fly logs
```

---

## Task 3: File Importance Ranking & Cleanup Recommendations

### Priority Tier Definitions

| Tier | Description |
|------|-------------|
| **Critical** | Core functionality; removal breaks the application |
| **Important** | Significant features; removal degrades functionality |
| **Nice-to-have** | Useful but not essential; could be simplified |
| **Redundant** | Should be removed or consolidated |

### Critical Files (Must Keep)

#### Backend Core

| File | Status | Reason |
|------|--------|--------|
| `backend/main.py` | KEEP | Application entry, lifespan, middleware |
| `backend/routers/portfolio.py` | KEEP | All portfolio API endpoints |
| `backend/utils/redis_first_data_service.py` | KEEP | Primary data access layer |
| `backend/utils/portfolio_mvo_optimizer.py` | KEEP | Core optimization algorithm |
| `backend/utils/port_analytics.py` | KEEP | Portfolio metrics calculations |
| `backend/utils/enhanced_portfolio_generator.py` | KEEP | Portfolio generation engine |
| `backend/utils/portfolio_stock_selector.py` | KEEP | Stock selection logic |
| `backend/utils/risk_profile_config.py` | KEEP | Risk profile configuration |
| `backend/utils/redis_config.py` | KEEP | Redis TTL and connection settings |
| `backend/utils/redis_portfolio_manager.py` | KEEP | Portfolio storage/retrieval |
| `backend/config/settings.py` | KEEP | Application settings |

#### Frontend Core

| File | Status | Reason |
|------|--------|--------|
| `frontend/src/App.tsx` | KEEP | Application root |
| `frontend/src/components/PortfolioWizard.tsx` | KEEP | Main wizard orchestrator |
| `frontend/src/components/wizard/RiskProfiler.tsx` | KEEP | Risk assessment |
| `frontend/src/components/wizard/StockSelection.tsx` | KEEP | Stock selection UI |
| `frontend/src/components/wizard/PortfolioOptimization.tsx` | KEEP | Optimization UI |
| `frontend/src/components/wizard/StressTest.tsx` | KEEP | Stress testing UI |
| `frontend/src/components/wizard/FinalizePortfolio.tsx` | KEEP | Finalization UI |
| `frontend/src/config/api.ts` | KEEP | API configuration |

#### Configuration

| File | Status | Reason |
|------|--------|--------|
| `Makefile` | KEEP | Build commands |
| `fly.toml` | KEEP | Fly.io deployment config |
| `Dockerfile` | KEEP | Container build |
| `backend/Dockerfile` | KEEP | Backend container |
| `docker-compose.yml` | KEEP | Local development |

### Important Files (Keep)

#### Backend Features

| File | Status | Reason |
|------|--------|--------|
| `backend/utils/stress_test_analyzer.py` | KEEP | Stress testing |
| `backend/utils/pdf_report_generator.py` | KEEP | PDF exports |
| `backend/utils/csv_export_generator.py` | KEEP | CSV exports |
| `backend/utils/swedish_tax_calculator.py` | KEEP | Swedish tax calculations |
| `backend/utils/transaction_cost_calculator.py` | KEEP | Avanza costs |
| `backend/utils/five_year_projection.py` | KEEP | Projections |
| `backend/utils/shareable_link_generator.py` | KEEP | Link sharing |
| `backend/utils/enhanced_data_fetcher.py` | KEEP | Data fetching |
| `backend/utils/fx_fetcher.py` | KEEP | FX rates |
| `backend/utils/email_notifier.py` | KEEP | Email alerts |
| `backend/utils/redis_ttl_monitor.py` | KEEP | TTL monitoring |
| `backend/routers/admin.py` | KEEP | Admin endpoints |

#### Frontend Features

| File | Status | Reason |
|------|--------|--------|
| `frontend/src/components/wizard/EfficientFrontierChart.tsx` | KEEP | Visualization |
| `frontend/src/components/wizard/Portfolio3PartVisualization.tsx` | KEEP | Comparison view |
| `frontend/src/components/wizard/PortfolioBuilder.tsx` | KEEP | Custom builder |
| `frontend/src/contexts/ThemeContext.tsx` | KEEP | Theme management |
| `frontend/src/lib/themeConfig.ts` | KEEP | Theme configuration |
| `frontend/src/utils/chartThemes.ts` | KEEP | Chart theming |

### Nice-to-have Files (Keep but Consider Simplification)

| File | Status | Reason |
|------|--------|--------|
| `backend/utils/enhanced_stock_selector.py` | KEEP | Extended selector |
| `backend/utils/strategy_portfolio_optimizer.py` | KEEP | Strategy portfolios |
| `backend/utils/conservative_portfolio_generator.py` | KEEP | Aggressive profile handling |
| `backend/utils/dynamic_weighting_system.py` | KEEP | Multi-objective optimization |
| `backend/utils/volatility_weighted_sector.py` | KEEP | Sector weighting |
| `backend/utils/diversification_experiments.py` | KEEP | Diversification strategies |
| `backend/utils/enhanced_portfolio_config.py` | KEEP | Enhanced config |
| `backend/utils/portfolio_auto_regeneration_service.py` | KEEP | Manual regeneration |
| `backend/utils/anonymous_analytics.py` | KEEP | Prometheus metrics |
| `backend/utils/redis_metrics.py` | KEEP | Redis metrics |
| `backend/utils/timestamp_utils.py` | KEEP | Timestamp utilities |

### Redundant Files (Recommend Removal)

#### Documentation Cleanup

| File | Status | Reason |
|------|--------|--------|
| `CURSOR_AI_PROMPTS.md` | REMOVE | Development artifact |
| `IMPLEMENTATION_PLAN.md` | REMOVE | Completed planning doc |
| `THEME_REDESIGN_TASKS.md` | REMOVE | Completed tasks |
| `THEMING_ANALYSIS.md` | REMOVE | Analysis complete |
| `risk-profiling-agent-tasks.md` | REMOVE | Completed agent tasks |
| `PORTFOLIO_WIZARD_REVIEW_AND_EXECUTION_PLAN.md` | REMOVE | Completed plan |
| `OPTIMIZATION_BUTTON_AND_TABS_WORKFLOW.md` | REMOVE | Documentation consolidated |
| `BEGINNER_GUIDE_TICKER_MANAGEMENT.md` | REMOVE | Merge into README |

#### Scripts Cleanup

| File | Status | Reason |
|------|--------|--------|
| `backend/scripts/reports/*.json` | REMOVE | Old audit reports |
| `backend/test_visualization_real_portfolios.py` | REMOVE | Test file in wrong location |
| `test_deployment.sh` | REMOVE | Deployment verified |
| `scripts/validate_env.py` | KEEP | Environment validation |
| `scripts/warm_cache.py` | KEEP | Cache warming |

#### Duplicate Documentation

| File | Status | Reason |
|------|--------|--------|
| `backend/PORTFOLIOS_IN_REDIS.md` | REMOVE | Duplicate of root |
| `backend/scripts/PORTFOLIOS_IN_REDIS.md` | REMOVE | Duplicate of root |
| `backend/scripts/README.md` | KEEP | Script documentation |

#### Everything Claude Code (External Tool)

| Path | Status | Reason |
|------|--------|--------|
| `everything-claude-code/` | REMOVE | External tool, not project code |

### Frontend Test Files

| File | Status | Reason |
|------|--------|--------|
| All `__tests__/*.test.ts(x)` files | KEEP | Test coverage |
| All `*.stories.tsx` files | KEEP | Storybook documentation |

### Summary Statistics

| Category | Count | Action |
|----------|-------|--------|
| Critical | 25 | Keep |
| Important | 30 | Keep |
| Nice-to-have | 15 | Keep (consider simplification) |
| Redundant | 15 | Remove |

### Recommended Cleanup Commands

```bash
# Remove completed planning docs
rm CURSOR_AI_PROMPTS.md
rm IMPLEMENTATION_PLAN.md
rm THEME_REDESIGN_TASKS.md
rm THEMING_ANALYSIS.md
rm risk-profiling-agent-tasks.md
rm PORTFOLIO_WIZARD_REVIEW_AND_EXECUTION_PLAN.md
rm OPTIMIZATION_BUTTON_AND_TABS_WORKFLOW.md

# Remove duplicate docs
rm backend/PORTFOLIOS_IN_REDIS.md
rm backend/scripts/PORTFOLIOS_IN_REDIS.md

# Remove old reports
rm -rf backend/scripts/reports/*.json

# Remove misplaced test files
rm backend/test_visualization_real_portfolios.py
rm test_deployment.sh

# Remove external tool directory
rm -rf everything-claude-code/
```

---

## Appendix: File Size Analysis

### Largest Backend Files

| File | Size |
|------|------|
| `port_analytics.py` | 116K |
| `enhanced_data_fetcher.py` | 112K |
| `enhanced_portfolio_generator.py` | 108K |
| `stress_test_analyzer.py` | 96K |
| `pdf_report_generator.py` | 92K |
| `strategy_portfolio_optimizer.py` | 84K |
| `portfolio_stock_selector.py` | 76K |
| `redis_first_data_service.py` | 56K |

### Largest Frontend Files

| File | Lines |
|------|-------|
| `PortfolioOptimization.tsx` | 8,827 |
| `StressTest.tsx` | 5,053 |
| `StockSelection.tsx` | 3,787 |
| `Portfolio3PartVisualization.tsx` | 2,531 |
| `RiskProfiler.tsx` | 2,488 |
| `FinalizePortfolio.tsx` | 2,264 |
| `EfficientFrontierChart.tsx` | 1,758 |

---

*Analysis generated by Claude on 2026-03-01*
