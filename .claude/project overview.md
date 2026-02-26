 # Portfolio Navigator Wizard — Project Overview

  > **Last Updated:** February 2026
  > **Version:** 1.0
  > **Author:** Brook (with AI assistance)

  ---

  ## TL;DR

  **Portfolio Navigator Wizard** is a full-stack application that uses behavioral finance (Modern Portfolio
  Theory + Prospect Theory) to generate personalized investment portfolios for Swedish investors.

  | Component | Technology | Port |
  |-----------|------------|------|
  | Frontend | React + TypeScript + Vite | 8080 |
  | Backend | FastAPI + Python | 8000 |
  | Cache/Store | Redis | 6379 |
  | Market Data | Alpha Vantage + Yahoo Finance | — |
  | Notifications | SMTP (Gmail) | 587 |

  **Key Flow:**
  `Risk Profile → Capital Input → Portfolio Selection → Optimization → Stress Test → Export PDF`

  ---

  ## Quick Start

  ```bash
  # 1. Start Redis
  redis-server

  # 2. Start Backend
  cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

  # 3. Start Frontend
  cd frontend && npm install && npm run dev

  Open http://localhost:8080 in your browser.

  ---
  System Architecture

  Actors & Systems

  graph TB
      subgraph Users
          Investor[Investor/End User]
          Admin[Admin]
      end

      subgraph Frontend
          React[React App<br/>:8080]
      end

      subgraph Backend
          FastAPI[FastAPI Server<br/>:8000]
      end

      subgraph Storage
          Redis[(Redis<br/>:6379)]
      end

      subgraph ExternalAPIs
          AlphaVantage[Alpha Vantage<br/>Market Data]
          Yahoo[Yahoo Finance<br/>Prices & FX]
          SMTP[Gmail SMTP<br/>Notifications]
      end

      Investor -->|Browser| React
      Admin -->|X-Admin-Key| FastAPI
      React -->|/api/v1/*| FastAPI
      FastAPI -->|Cache/Store| Redis
      FastAPI -->|Fetch Data| AlphaVantage
      FastAPI -->|Prices/FX| Yahoo
      FastAPI -->|Alerts| SMTP

  Request Flow

  sequenceDiagram
      participant Browser
      participant Vite as Vite Proxy
      participant FastAPI
      participant Redis
      participant External as Alpha Vantage/Yahoo

      Browser->>Vite: GET /api/v1/portfolio/recommendations
      Vite->>FastAPI: Proxy to :8000
      FastAPI->>Redis: Check cache
      alt Cache Hit
          Redis-->>FastAPI: Return cached data
      else Cache Miss
          FastAPI->>External: Fetch market data
          External-->>FastAPI: Return data
          FastAPI->>Redis: Store in cache
      end
      FastAPI-->>Vite: JSON response
      Vite-->>Browser: Display to user

  ---
  Features (WHAT)

  Core Capabilities

  ┌──────────────────────┬──────────────────────────────────────────────────────────────────┐
  │       Feature        │                           Description                            │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Risk Profiling       │ 8-question behavioral assessment combining MPT + Prospect Theory │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Portfolio Generation │ 60+ pre-computed portfolios across 5 risk categories             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Triple Optimization  │ Current, weights-only, and market-optimized variants             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Stress Testing       │ 2008 Financial Crisis + COVID-19 crash simulations               │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ PDF Export           │ Publication-quality reports (300 DPI, professional charts)       │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Swedish Tax          │ ISK/KF schablonbeskattning calculations                          │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ 5-Year Projections   │ Optimistic/base/pessimistic scenarios                            │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Shareable Links      │ Generate links to share portfolio analysis                       │
  └──────────────────────┴──────────────────────────────────────────────────────────────────┘

  Component Diagram

  graph TB
      subgraph FrontendComponents[Frontend - React]
          App[App.tsx<br/>Routes]
          Wizard[PortfolioWizard.tsx<br/>Orchestrator]

          subgraph Steps[Wizard Steps]
              Welcome[WelcomeStep]
              Risk[RiskProfiler]
              Capital[CapitalInput]
              Stocks[StockSelection]
              Optimize[PortfolioOptimization]
              Stress[StressTest]
              Finalize[FinalizePortfolio]
              ThankYou[ThankYouStep]
          end

          App --> Wizard
          Wizard --> Steps
      end

      subgraph BackendComponents[Backend - FastAPI]
          Main[main.py<br/>Lifespan & CORS]

          subgraph Routers
              PortfolioRouter[portfolio.py]
              StrategyRouter[strategy_buckets.py]
              AdminRouter[admin.py]
          end

          subgraph Utils[Services]
              RedisService[redis_first_data_service]
              PortfolioManager[redis_portfolio_manager]
              DataFetcher[enhanced_data_fetcher]
              Optimizer[portfolio_mvo_optimizer]
              StressAnalyzer[stress_test_analyzer]
              PDFGenerator[pdf_report_generator]
              EmailNotifier[email_notifier]
          end

          Main --> Routers
          Routers --> Utils
      end

      FrontendComponents -->|HTTP| BackendComponents

  ---
  User Journey (WHEN)

  Wizard Flow

  flowchart LR
      subgraph Phase1[Discovery]
          S1[Welcome] --> S2[Risk Profile]
          S2 --> S3[Capital Input]
      end

      subgraph Phase2[Selection]
          S3 --> S4[Stock Selection]
          S4 --> S5[Optimization]
      end

      subgraph Phase3[Analysis]
          S5 --> S6[Stress Test]
          S6 --> S7[Finalize]
      end

      subgraph Phase4[Export]
          S7 --> S8[Thank You]
      end

  ┌────────────────────┬────────────────────────────────────┬────────────────────────────────────┐
  │        Step        │             API Calls              │            User Action             │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 1. Welcome         │ None                               │ Click "Start"                      │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 2. Risk Profile    │ None (client-side scoring)         │ Answer 8 questions                 │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 3. Capital Input   │ None                               │ Enter investment amount            │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 4. Stock Selection │ GET /recommendations               │ Pick pre-built or custom portfolio │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 5. Optimization    │ POST /optimize/triple              │ Review optimized variants          │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 6. Stress Test     │ POST /stress-test                  │ Analyze crisis scenarios           │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 7. Finalize        │ POST /export/pdf, POST /export/csv │ Download reports                   │
  ├────────────────────┼────────────────────────────────────┼────────────────────────────────────┤
  │ 8. Thank You       │ None                               │ Share or restart                   │
  └────────────────────┴────────────────────────────────────┴────────────────────────────────────┘

  ---
  Design Decisions (WHY)

  Why Redis Only (No PostgreSQL)?

  - Speed: Sub-5ms cache hits for portfolio lookups
  - Simplicity: Single persistence layer reduces complexity
  - Fit: Portfolio data is key-value shaped, not relational

  Why MPT + Prospect Theory?

  - MPT (Markowitz): Mathematically optimal risk/return trade-offs
  - Prospect Theory (Kahneman): Accounts for loss aversion and behavioral biases

  Why Only 2 Stress Scenarios?

  The PDF shows only 2008 Financial Crisis and 2020 COVID-19 crash:
  - They represent different crisis types (slow systemic vs. fast V-shaped)
  - Most recognized and relatable to investors

  ---
  Integration Guide (HOW)

  API Examples

  Get Portfolio Recommendations

  GET /api/v1/portfolio/recommendations?risk_profile=moderate&capital=100000

  Run Stress Test

  POST /api/v1/portfolio/stress-test
  Content-Type: application/json

  {
    "portfolio": [...],
    "scenarios": ["2008_financial_crisis", "2020_covid_crash"]
  }

  Export PDF Report

  POST /api/v1/portfolio/export/pdf
  Content-Type: application/json

  {
    "portfolio": [...],
    "portfolioName": "My Portfolio",
    "portfolioValue": 500000,
    "accountType": "ISK"
  }

  Redis Key Patterns

  ┌───────────────────────────┬───────────────────────────────┬───────────────────────────┐
  │          Pattern          │            Example            │          Purpose          │
  ├───────────────────────────┼───────────────────────────────┼───────────────────────────┤
  │ ticker:{symbol}           │ ticker:AAPL                   │ Cached stock data         │
  ├───────────────────────────┼───────────────────────────────┼───────────────────────────┤
  │ portfolio_bucket:{risk}:* │ portfolio_bucket:moderate:001 │ Pre-computed portfolios   │
  ├───────────────────────────┼───────────────────────────────┼───────────────────────────┤
  │ shareable_link:{hash}     │ shareable_link:abc123         │ Shareable portfolio links │
  └───────────────────────────┴───────────────────────────────┴───────────────────────────┘

  Environment Variables

  # Backend (.env)
  REDIS_HOST=localhost
  REDIS_PORT=6379
  ALPHA_VANTAGE_API_KEY=your_key
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your_email@gmail.com
  SMTP_PASSWORD=your_app_password
  TTL_EMAIL_NOTIFICATIONS=true
  TTL_NOTIFICATION_EMAIL=alerts@example.com
  ADMIN_API_KEY=your_secret

  # Frontend (.env)
  VITE_API_BASE_URL=
  VITE_ADMIN_API_KEY=your_secret

  ---
  Security & Error Handling

  ┌──────────────────┬─────────────────────────────┐
  │     Measure      │       Implementation        │
  ├──────────────────┼─────────────────────────────┤
  │ Admin Protection │ X-Admin-Key header required │
  ├──────────────────┼─────────────────────────────┤
  │ Rate Limiting    │ SlowAPI middleware          │
  ├──────────────────┼─────────────────────────────┤
  │ CORS             │ ALLOWED_ORIGINS whitelist   │
  ├──────────────────┼─────────────────────────────┤
  │ Input Validation │ Pydantic models             │
  └──────────────────┴─────────────────────────────┘

  ---
  Recent Enhancements (2026)

  ┌──────────────────┬────────────────────────────────────┐
  │      Change      │              Details               │
  ├──────────────────┼────────────────────────────────────┤
  │ Chart Quality    │ 300 DPI with unified color palette │
  ├──────────────────┼────────────────────────────────────┤
  │ Stress Scenarios │ Limited to 2008 + COVID-19 only    │
  ├──────────────────┼────────────────────────────────────┤
  │ Email Sender     │ Shows "Portfolio-wizard App"       │
  ├──────────────────┼────────────────────────────────────┤
  │ SVG Export       │ ZIP includes SVG chart versions    │
  └──────────────────┴────────────────────────────────────┘

  ---
  File Reference

  Backend

  ┌───────────────────────────────────────┬────────────────────────────────┐
  │                 File                  │            Purpose             │
  ├───────────────────────────────────────┼────────────────────────────────┤
  │ backend/main.py                       │ App lifespan, CORS, middleware │
  ├───────────────────────────────────────┼────────────────────────────────┤
  │ backend/routers/portfolio.py          │ Main API endpoints             │
  ├───────────────────────────────────────┼────────────────────────────────┤
  │ backend/utils/pdf_report_generator.py │ PDF generation                 │
  ├───────────────────────────────────────┼────────────────────────────────┤
  │ backend/utils/email_notifier.py       │ SMTP notifications             │
  └───────────────────────────────────────┴────────────────────────────────┘

  Frontend

  ┌─────────────────────────────────────────────┬─────────────────────┐
  │                    File                     │       Purpose       │
  ├─────────────────────────────────────────────┼─────────────────────┤
  │ frontend/src/App.tsx                        │ Route definitions   │
  ├─────────────────────────────────────────────┼─────────────────────┤
  │ frontend/src/components/PortfolioWizard.tsx │ Wizard orchestrator │
  ├─────────────────────────────────────────────┼─────────────────────┤
  │ frontend/src/config/api.ts                  │ API endpoints       │
  └─────────────────────────────────────────────┴─────────────────────┘

---

## DETAILED WIZARD STEP OPERATIONS

### Step 1: Welcome (WelcomeStep.tsx)

**What Happens:**
- Static welcome page with no API calls
- Displays feature highlights and wizard overview
- User clicks "Start" → triggers `nextStep()` in PortfolioWizard.tsx

**Systems Used:** Frontend only (no backend interaction)

**Data Flow:**
```
User clicks "Start"
       ↓
PortfolioWizard.nextStep()
       ↓
currentStep: 0 → 1
       ↓
RiskProfiler component mounts
```

---

### Step 2: Risk Profiler (RiskProfiler.tsx)

**What Happens:**
1. User answers 3 screening questions (age, experience, knowledge)
2. User answers 8 scored questions (MPT + Prospect Theory)
3. Client-side scoring engine calculates risk profile
4. Safeguards check for contradictory answers

**Systems Used:**
- Frontend scoring engine (pure TypeScript, no API calls)
- Question bank embedded in component
- Scoring algorithms for MPT and Prospect Theory

**Scoring Process:**
```typescript
// Each question has a score (1-5) and belongs to a group
questions = [
  { id: 'q1', group: 'MPT', maxScore: 5, construct: 'time_horizon' },
  { id: 'q2', group: 'PROSPECT', maxScore: 5, construct: 'loss_aversion' },
  // ... 8 total scored questions
]

// Scoring calculation
mptScore = sum(mpt_answers) / sum(mpt_maxScores) * 100;        // 0-100
prospectScore = sum(prospect_answers) / sum(prospect_maxScores) * 100;  // 0-100

// Combined with behavioral weight
combinedScore = (mptScore * 0.6) + (prospectScore * 0.4);

// Map to risk category
if (combinedScore < 25) → 'very-conservative'
if (combinedScore < 40) → 'conservative'
if (combinedScore < 60) → 'moderate'
if (combinedScore < 75) → 'aggressive'
else → 'very-aggressive'
```

**Safeguards Applied:**
- Short time horizon + high risk → cap to moderate
- Low income + aggressive → show warning
- Contradictory answers → widen confidence band

**Output:**
```typescript
{
  riskProfile: 'moderate',
  riskAnalysis: {
    mptScore: 62,
    prospectScore: 55,
    combinedScore: 59.2,
    confidenceBand: { lower: 'conservative', upper: 'aggressive' },
    safeguards: ['income_cap_applied']
  }
}
```

---

### Step 3: Capital Input (CapitalInput.tsx)

**What Happens:**
1. User enters investment amount in SEK
2. Input validation (minimum: 10,000 SEK)
3. Number formatting with thousands separator
4. Capital stored in wizard state

**Systems Used:** Frontend only (no backend interaction)

**Validation Rules:**
```typescript
const MIN_CAPITAL = 10000;  // 10,000 SEK minimum
const MAX_CAPITAL = 100000000;  // 100M SEK maximum

// Validation
if (capital < MIN_CAPITAL) showError("Minimum 10,000 SEK");
if (isNaN(capital)) showError("Enter a valid number");
```

**Output:** `wizardData.capital = 500000`

---

### Step 4: Stock Selection (StockSelection.tsx)

**What Happens:**
This step has THREE modes (tabs):

#### Mode A: Recommended Portfolios
```
1. Component mounts
       ↓
2. Fetch: GET /api/v1/portfolio/recommendations/{riskProfile}
       ↓
3. Backend checks Redis: keys("portfolio_bucket:moderate:*")
       ↓
4. If CACHE HIT → return 5-10 pre-built portfolios
   If CACHE MISS → EnhancedPortfolioGenerator creates new ones
       ↓
5. Frontend displays portfolio cards
       ↓
6. User clicks "Select This Portfolio"
       ↓
7. Portfolio stored in wizardData.selectedStocks
```

#### Mode B: Custom Portfolio
```
1. User types ticker in search box
       ↓
2. Fetch: GET /api/v1/portfolio/search-tickers?q={query}
       ↓
3. Backend searches Redis ticker index
       ↓
4. Return matching tickers with metadata
       ↓
5. User adds ticker, sets allocation %
       ↓
6. Repeat until allocations sum to 100%
       ↓
7. Fetch: POST /api/v1/portfolio/calculate-metrics
   Body: { tickers: ['AAPL','MSFT'], weights: {AAPL:0.6, MSFT:0.4} }
       ↓
8. Backend calculates:
   - Expected return (weighted average)
   - Risk (portfolio volatility using covariance matrix)
   - Sharpe ratio (return - risk_free) / risk
   - Diversification score
       ↓
9. Display metrics to user
```

#### Mode C: Two-Asset Comparison (Educational)
```
1. User selects two tickers
       ↓
2. Fetch: GET /api/v1/portfolio/two-asset-analysis?ticker1=X&ticker2=Y
       ↓
3. Backend calculates correlation, combined metrics
       ↓
4. Display educational visualization
```

**Systems Used:**
- Frontend: StockSelection.tsx, StockSearchBar.tsx
- Backend: portfolio.py router
- Services: redis_first_data_service, port_analytics
- External: Redis cache

**Backend Services Involved:**
```python
# portfolio.py
@portfolios_router.get("/recommendations/{risk_profile}")
def get_recommendations(risk_profile: str):
    # 1. Check Redis for cached portfolios
    cached = redis_client.keys(f"portfolio_bucket:{risk_profile}:*")

    if cached:
        # Return cached portfolios
        return [json.loads(redis_client.get(key)) for key in cached]

    # 2. Generate new portfolios
    generator = EnhancedPortfolioGenerator(redis_first_data_service, portfolio_analytics)
    portfolios = generator.generate_portfolio_bucket(risk_profile, count=10)

    # 3. Cache for 24 hours
    for p in portfolios:
        redis_client.setex(f"portfolio_bucket:{risk_profile}:{p['id']}", 86400, json.dumps(p))

    return portfolios
```

---

### Step 5: Portfolio Optimization (PortfolioOptimization.tsx)

**What Happens:**
```
1. Component mounts with selected portfolio
       ↓
2. Fetch: POST /api/v1/portfolio/optimization/mvo
   Body: {
     tickers: ['AAPL','MSFT','JNJ'],
     weights: {AAPL:0.4, MSFT:0.35, JNJ:0.25},
     optimization_target: 'max_sharpe'
   }
       ↓
3. Backend runs THREE optimizations:

   a) CURRENT (no changes)
      - Just calculate metrics for comparison

   b) WEIGHTS OPTIMIZED
      - Same tickers, optimize weights only
      - Uses Markowitz mean-variance optimization
      - Maximizes Sharpe ratio

   c) MARKET OPTIMIZED
      - Can use ANY eligible tickers
      - Full optimization from 200+ stock universe
      - May suggest completely different portfolio
       ↓
4. Backend also generates:
   - Efficient frontier curve (100 points)
   - Random portfolios for scatter plot (500 points)
       ↓
5. Frontend displays:
   - Comparison table (3 columns)
   - Efficient frontier chart with all 3 portfolios marked
       ↓
6. User selects which variant to proceed with
```

**Systems Used:**
- Frontend: PortfolioOptimization.tsx, Recharts
- Backend: portfolio.py, portfolio_mvo_optimizer.py
- Library: PyPortfolioOpt (Markowitz optimization)
- Data: Redis (cached prices, covariance matrices)

**Backend Optimization Process:**
```python
# portfolio_mvo_optimizer.py
class PortfolioMVOptimizer:
    def optimize_triple(self, portfolio: Dict) -> Dict:
        tickers = portfolio['tickers']
        current_weights = portfolio['weights']

        # Fetch 5 years of historical prices
        prices = self._get_historical_prices(tickers)

        # Calculate expected returns and covariance matrix
        mu = expected_returns.mean_historical_return(prices)
        S = risk_models.sample_cov(prices)

        # CURRENT: Just calculate metrics
        current_metrics = self._calculate_metrics(current_weights, mu, S)

        # WEIGHTS OPTIMIZED: Same stocks, optimal weights
        ef = EfficientFrontier(mu, S)
        ef.max_sharpe()
        weights_opt = ef.clean_weights()
        weights_metrics = self._calculate_metrics(weights_opt, mu, S)

        # MARKET OPTIMIZED: Full universe optimization
        all_tickers = self._get_eligible_tickers()  # 200+ stocks
        all_prices = self._get_historical_prices(all_tickers)
        mu_all = expected_returns.mean_historical_return(all_prices)
        S_all = risk_models.sample_cov(all_prices)

        ef_market = EfficientFrontier(mu_all, S_all)
        ef_market.max_sharpe()
        market_opt = ef_market.clean_weights()
        market_metrics = self._calculate_metrics(market_opt, mu_all, S_all)

        return {
            'current': {'weights': current_weights, 'metrics': current_metrics},
            'weights_optimized': {'weights': weights_opt, 'metrics': weights_metrics},
            'market_optimized': {'weights': market_opt, 'metrics': market_metrics},
            'efficient_frontier': self._generate_frontier(mu, S),
            'random_portfolios': self._generate_random(mu, S, 500)
        }
```

---

### Step 6: Stress Test (StressTest.tsx)

**What Happens:**
```
1. Component mounts with selected portfolio
       ↓
2. Fetch: POST /api/v1/portfolio/stress-test
   Body: {
     portfolio: { tickers: [...], weights: {...} },
     scenarios: ['2008_financial_crisis', '2020_covid_crash']
   }
       ↓
3. Backend processes each scenario:

   FOR '2008_financial_crisis':
   ├── Period: 2007-10-01 to 2009-03-31
   ├── Fetch historical prices for all tickers
   ├── Calculate portfolio value at each date:
   │   portfolio_value[date] = Σ(weight[i] × price[i][date])
   ├── Find peak (highest value before crash)
   ├── Find trough (lowest value during crash)
   ├── Calculate max_drawdown = (trough - peak) / peak
   ├── Calculate monthly returns
   └── Generate monthly_performance array

   FOR '2020_covid_crash':
   ├── Period: 2020-01-01 to 2020-08-31
   └── (same process)
       ↓
4. Calculate resilience_score (0-100):
   - Based on average max_drawdown across scenarios
   - Drawdown < 15% → score 80+
   - Drawdown 15-30% → score 50-80
   - Drawdown > 30% → score < 50
       ↓
5. Frontend displays:
   - Portfolio value over time chart (line chart)
   - Peak-to-trough drawdown comparison (bar chart)
   - Resilience score gauge
   - Scenario details expandable
```

**Systems Used:**
- Frontend: StressTest.tsx, Recharts
- Backend: portfolio.py, stress_test_analyzer.py
- Data: Redis (historical prices), Yahoo Finance (fallback)

**Backend Stress Analysis:**
```python
# stress_test_analyzer.py
class StressTestAnalyzer:
    SCENARIOS = {
        '2008_financial_crisis': {
            'name': '2008 Financial Crisis',
            'start': '2007-10-01',
            'end': '2009-03-31',
            'peak_date': '2007-10-09',  # Market peak
            'trough_date': '2009-03-09'  # Market bottom
        },
        '2020_covid_crash': {
            'name': '2020 COVID-19 Crash',
            'start': '2020-01-01',
            'end': '2020-08-31',
            'peak_date': '2020-02-19',
            'trough_date': '2020-03-23'
        }
    }

    def analyze_portfolio(self, portfolio: Dict, scenarios: List[str]) -> Dict:
        results = {}

        for scenario_id in scenarios:
            scenario = self.SCENARIOS[scenario_id]

            # Get prices for the period
            prices = self._get_prices_for_period(
                portfolio['tickers'],
                scenario['start'],
                scenario['end']
            )

            # Calculate daily portfolio values
            values = self._calculate_portfolio_values(portfolio, prices)

            # Find drawdown
            peak_value = max(values)
            trough_value = min(values)
            max_drawdown = (trough_value - peak_value) / peak_value

            # Monthly performance
            monthly = self._aggregate_monthly(values)

            results[scenario_id] = {
                'metrics': {
                    'max_drawdown': max_drawdown,
                    'total_return': (values[-1] - values[0]) / values[0],
                    'worst_month_return': min(monthly['returns'])
                },
                'monthly_performance': monthly['data']
            }

        # Calculate resilience score
        avg_drawdown = abs(np.mean([r['metrics']['max_drawdown'] for r in results.values()]))
        resilience_score = max(0, min(100, 100 - (avg_drawdown * 200)))

        return {
            'scenarios': results,
            'resilience_score': int(resilience_score)
        }
```

---

### Step 7: Finalize Portfolio (FinalizePortfolio.tsx)

**What Happens:**
This step has FOUR tabs:

#### Tab A: Overview
- Display final portfolio composition
- Show key metrics (return, risk, Sharpe)
- No API calls (uses cached data from previous steps)

#### Tab B: Tax Analysis
```
1. Fetch: POST /api/v1/portfolio/tax/calculate
   Body: {
     portfolio: {...},
     capital: 500000,
     accountType: 'ISK',  // or 'KF'
     taxYear: 2025
   }
       ↓
2. Backend calculates Swedish taxes:

   FOR ISK (Investeringssparkonto):
   ├── Get government lending rate (statslåneränta)
   ├── Add 1% to get schablonränta
   ├── Multiply by average account value
   ├── Tax = schablonbelopp × 30% (capital gains tax)
   └── Example: 500,000 × 2.94% × 30% = 4,410 SEK

   FOR KF (Kapitalförsäkring):
   ├── Similar calculation but different base
   └── Usually slightly higher than ISK
       ↓
3. Display comparison table ISK vs KF
```

#### Tab C: Export
```
PDF Export:
├── Fetch: POST /api/v1/portfolio/export/pdf
├── Body: { portfolio, portfolioName, portfolioValue, ... }
├── Backend generates PDF with ReportLab:
│   ├── Title page with key metrics
│   ├── Holdings table
│   ├── Sector allocation pie chart (300 DPI)
│   ├── Efficient frontier chart (300 DPI)
│   ├── Stress test charts (Peak-to-Trough Drawdown)
│   ├── Tax analysis table
│   └── 5-year projection chart
└── Return binary PDF

CSV Export:
├── Fetch: POST /api/v1/portfolio/export/csv
└── Return CSV with all data

ZIP Export:
├── Fetch: POST /api/v1/portfolio/export/zip
└── Return ZIP containing PDF + CSV + SVG charts

Shareable Link:
├── Fetch: POST /api/v1/portfolio/shareable-link
├── Backend generates unique hash
├── Store portfolio in Redis with 30-day TTL
└── Return URL: https://app.com/share/{hash}
```

#### Tab D: 5-Year Projection
```
1. Fetch: POST /api/v1/portfolio/projection
   Body: { portfolio, capital, taxRate }
       ↓
2. Backend calculates three scenarios:

   OPTIMISTIC (expected_return + 2%):
   Year 1: 500,000 × 1.12 = 560,000
   Year 2: 560,000 × 1.12 = 627,200
   ... (compound annually, subtract taxes)

   BASE CASE (expected_return):
   Year 1: 500,000 × 1.10 = 550,000
   ...

   PESSIMISTIC (expected_return - 2%):
   Year 1: 500,000 × 1.08 = 540,000
   ...
       ↓
3. Display line chart with three lines
```

**Systems Used:**
- Frontend: FinalizePortfolio.tsx, Recharts
- Backend: portfolio.py, pdf_report_generator.py, csv_export_generator.py
- Services: swedish_tax_calculator.py, five_year_projection.py
- Storage: Redis (shareable links)

---

### Step 8: Thank You (ThankYouStep.tsx)

**What Happens:**
- Static completion page
- Options: Start over, download report, share link
- No API calls

---

## BACKEND SERVICES DEEP DIVE

### redis_first_data_service.py

**Purpose:** Central data access layer. ALL data goes through Redis first.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    RedisFirstDataService                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Redis Cache                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │  │ ticker_data: │  │ portfolio_   │  │ eligible_    │   │    │
│  │  │ {symbol}     │  │ bucket:*     │  │ tickers      │   │    │
│  │  │ TTL: 4h      │  │ TTL: 24h     │  │ TTL: 12h     │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                    CACHE MISS ↓                                 │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  EnhancedDataFetcher                      │    │
│  │  ┌──────────────┐       ┌──────────────┐                 │    │
│  │  │ Alpha        │       │ Yahoo        │                 │    │
│  │  │ Vantage      │       │ Finance      │                 │    │
│  │  │ (overview)   │       │ (prices)     │                 │    │
│  │  └──────────────┘       └──────────────┘                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Methods:**
```python
class RedisFirstDataService:
    def __init__(self):
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.data_fetcher = EnhancedDataFetcher()

    def get_ticker_data(self, ticker: str) -> Dict:
        """Get all data for a single ticker."""
        # 1. Check Redis cache
        cache_key = f"ticker_data:{ticker}"
        cached = self.redis_client.get(cache_key)

        if cached:
            return json.loads(cached)

        # 2. Fetch from external APIs
        data = self.data_fetcher.fetch_complete_data(ticker)

        # 3. Store in Redis with TTL
        self.redis_client.setex(cache_key, 14400, json.dumps(data))  # 4 hours

        return data

    def get_historical_prices(self, ticker: str, years: int = 5) -> pd.DataFrame:
        """Get price history for a ticker."""
        cache_key = f"ticker_data:prices:{ticker}"
        cached = self.redis_client.get(cache_key)

        if cached:
            return pd.read_json(cached)

        # Fetch from Yahoo Finance
        prices = yf.download(ticker, period=f"{years}y")

        # Cache
        self.redis_client.setex(cache_key, 14400, prices.to_json())

        return prices

    def get_eligible_tickers(self) -> List[str]:
        """Get list of tickers with sufficient data quality."""
        cached = self.redis_client.get("eligible_tickers")

        if cached:
            return json.loads(cached)

        # Generate from master list
        eligible = self._filter_by_data_quality(MASTER_TICKERS)

        self.redis_client.setex("eligible_tickers", 43200, json.dumps(eligible))

        return eligible
```

---

### enhanced_portfolio_generator.py

**Purpose:** Generate portfolio buckets for each risk category.

**Process:**
```
generate_portfolio_bucket(risk_profile='moderate', count=10)
       ↓
1. Load risk parameters from risk_profile_config.py:
   moderate = {
       target_return: 0.08-0.10,
       max_volatility: 0.18,
       min_stocks: 8,
       max_stocks: 15,
       sector_constraints: { max_per_sector: 0.30 }
   }
       ↓
2. Get eligible tickers (200+) from Redis
       ↓
3. Filter by volatility and return targets
       ↓
4. Run diversification algorithm:
   - Start with highest Sharpe ratio stocks
   - Add stocks that reduce correlation
   - Enforce sector limits
       ↓
5. Optimize weights using SLSQP optimizer:
   - Objective: maximize Sharpe ratio
   - Constraints: weights sum to 1, sector limits, position limits
       ↓
6. Validate portfolio:
   - Check risk is within bounds
   - Check diversification score
   - Check all constraints met
       ↓
7. Repeat 10 times with different seeds
       ↓
8. Store all 10 portfolios in Redis
```

---

### stress_test_analyzer.py

**Purpose:** Simulate portfolio performance during historical crises.

**Scenario Definitions:**
```python
SCENARIOS = {
    '2008_financial_crisis': {
        'name': '2008 Financial Crisis',
        'description': 'Global financial meltdown triggered by subprime mortgage crisis',
        'period': {
            'analysis_start': '2007-10-01',
            'crisis_start': '2008-09-15',  # Lehman Brothers collapse
            'trough': '2009-03-09',
            'analysis_end': '2009-06-30'
        },
        'market_drop': -0.57,  # S&P 500 peak-to-trough
        'recovery_months': 48
    },
    '2020_covid_crash': {
        'name': '2020 COVID-19 Crash',
        'description': 'Fastest 30% drop in history due to pandemic',
        'period': {
            'analysis_start': '2020-01-01',
            'crisis_start': '2020-02-20',
            'trough': '2020-03-23',
            'analysis_end': '2020-08-31'
        },
        'market_drop': -0.34,
        'recovery_months': 5  # V-shaped recovery
    }
}
```

**Analysis Process:**
```python
def analyze_scenario(self, portfolio, scenario_id):
    scenario = SCENARIOS[scenario_id]

    # 1. Fetch historical prices for analysis period
    prices = {}
    for ticker in portfolio['tickers']:
        prices[ticker] = self.get_prices(
            ticker,
            scenario['period']['analysis_start'],
            scenario['period']['analysis_end']
        )

    # 2. Calculate portfolio value at each date
    dates = sorted(set.intersection(*[set(p.keys()) for p in prices.values()]))
    portfolio_values = []

    for date in dates:
        value = sum(
            portfolio['weights'][ticker] * prices[ticker][date]
            for ticker in portfolio['tickers']
        )
        portfolio_values.append({'date': date, 'value': value})

    # 3. Detect peak and trough
    values_only = [pv['value'] for pv in portfolio_values]
    peak_idx = np.argmax(values_only[:len(values_only)//2])  # Peak before crash
    trough_idx = peak_idx + np.argmin(values_only[peak_idx:])  # Trough after peak

    peak_value = values_only[peak_idx]
    trough_value = values_only[trough_idx]

    # 4. Calculate metrics
    max_drawdown = (trough_value - peak_value) / peak_value  # Negative number
    total_return = (values_only[-1] - values_only[0]) / values_only[0]

    # 5. Aggregate to monthly
    monthly_performance = self._aggregate_monthly(portfolio_values)

    return {
        'max_drawdown': max_drawdown,
        'total_return': total_return,
        'peak_date': dates[peak_idx],
        'trough_date': dates[trough_idx],
        'recovery_date': self._find_recovery_date(portfolio_values, peak_value),
        'monthly_performance': monthly_performance
    }
```

---

### pdf_report_generator.py

**Purpose:** Generate publication-quality PDF reports.

**Report Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│ PAGE i: TITLE PAGE                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Portfolio Analysis Report                                │ │
│ │ {Portfolio Name}                                         │ │
│ │ Report Date: February 26, 2026                          │ │
│ │                                                          │ │
│ │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │ │
│ │ │ Value    │ │ Return   │ │ Risk     │ │ Sharpe   │    │ │
│ │ │ 500,000  │ │ 8.92%    │ │ 18.45%   │ │ 0.483    │    │ │
│ │ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │ │
│ │                                                          │ │
│ │ [Sector Allocation Pie Chart - 300 DPI]                 │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ PAGE ii: TABLE OF CONTENTS                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1. Executive Summary.......................... 3         │ │
│ │ 2. Methodology & Assumptions.................. 3         │ │
│ │ 3. Portfolio Composition...................... 4         │ │
│ │ 4. Swedish Tax Analysis....................... 4         │ │
│ │ 5. Optimization Results....................... 5         │ │
│ │ 6. Transaction Costs.......................... 6         │ │
│ │ 7. Five-Year Projection....................... 7         │ │
│ │ 8. Risk Analysis.............................. 8         │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ PAGE iii: DISCLAIMER & DEFINITIONS                           │
├─────────────────────────────────────────────────────────────┤
│ PAGES 1-8: BODY CONTENT                                      │
│ - Holdings table                                             │
│ - Efficient frontier chart                                   │
│ - Stress test: Peak-to-Trough Drawdown chart                │
│ - Tax comparison table                                       │
│ - 5-year projection chart                                    │
└─────────────────────────────────────────────────────────────┘
```

**Chart Quality Settings:**
```python
# Class constants
CHART_COLORS = {
    'primary': '#2563eb',    # Blue
    'positive': '#059669',   # Green
    'negative': '#dc2626',   # Red
    'neutral': '#6b7280',    # Gray
    'text': '#1f2937',       # Dark gray
}

# Matplotlib configuration (set in __init__)
matplotlib.rcParams.update({
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'font.family': ['Helvetica', 'Arial', 'DejaVu Sans'],
    'lines.linewidth': 1.5,
    'axes.linewidth': 1.0,
    'text.antialiased': True,
})

# Generate plot
def _generate_plot(self, plt_obj) -> Image:
    img_buffer = BytesIO()
    plt_obj.savefig(
        img_buffer,
        format='png',
        bbox_inches='tight',
        dpi=300,
        facecolor='white',
        edgecolor='none',
        pad_inches=0.1,
        transparent=False
    )
    img_buffer.seek(0)
    plt_obj.close()
    return Image(img_buffer, width=6.2*inch, height=2.8*inch)
```

---

## SYSTEM INTEGRATION MAP

### How Systems Cooperate

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React Application)                          │
│                                                                               │
│  PortfolioWizard.tsx (State Machine)                                         │
│       │                                                                       │
│       ├── RiskProfiler ──────────────────── Client-side only (no API)        │
│       │                                                                       │
│       ├── StockSelection ─┬─ GET /recommendations ─────────────────────┐     │
│       │                   ├─ GET /search-tickers                       │     │
│       │                   └─ POST /calculate-metrics                   │     │
│       │                                                                │     │
│       ├── PortfolioOptimization ─── POST /optimization/mvo ────────────┤     │
│       │                                                                │     │
│       ├── StressTest ───────────── POST /stress-test ──────────────────┤     │
│       │                                                                │     │
│       └── FinalizePortfolio ───┬─ POST /export/pdf ────────────────────┤     │
│                                ├─ POST /export/csv                     │     │
│                                ├─ POST /shareable-link                 │     │
│                                └─ POST /tax/calculate                  │     │
└────────────────────────────────────────────────────────────────────────┼─────┘
                                                                         │
                                        HTTP via Vite Proxy (dev)        │
                                        or direct (production)           │
                                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI Server)                              │
│                                                                               │
│  main.py                                                                      │
│       │                                                                       │
│       ├── MIDDLEWARE                                                          │
│       │   ├── CORSMiddleware (allowed origins)                               │
│       │   ├── SecurityHeadersMiddleware (CSP, X-Frame-Options)              │
│       │   └── RateLimitMiddleware (SlowAPI)                                  │
│       │                                                                       │
│       ├── ROUTERS                                                             │
│       │   ├── portfolio.py ─────────────────────────────────────────────┐    │
│       │   ├── admin.py (cache control, requires X-Admin-Key)            │    │
│       │   └── strategy_buckets.py                                       │    │
│       │                                                                 │    │
│       └── BACKGROUND TASKS                                              │    │
│           ├── TTL Monitor (every 6h) ───────────────────────────────────┤    │
│           ├── Cache Supervisor (every 30min) ───────────────────────────┤    │
│           └── Redis Watchdog (every 60s) ───────────────────────────────┤    │
│                                                                         │    │
├─────────────────────────────────────────────────────────────────────────┼────┤
│                           UTILITY SERVICES                               │    │
│                                                                         │    │
│  ┌─────────────────────────────────────────────────────────────────┐   │    │
│  │              redis_first_data_service.py                         │   │    │
│  │  Central data access layer - ALL data goes through here         │◄──┘    │
│  │                                                                   │       │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │       │
│  │  │ get_ticker_data │  │ get_prices      │  │ get_eligible_   │  │       │
│  │  │                 │  │                 │  │ tickers         │  │       │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │       │
│  │           │                    │                    │           │       │
│  │           └────────────────────┼────────────────────┘           │       │
│  │                                │                                │       │
│  │                    ┌───────────▼───────────┐                    │       │
│  │                    │ enhanced_data_fetcher │                    │       │
│  │                    │ (Alpha Vantage+Yahoo) │                    │       │
│  │                    └───────────────────────┘                    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              portfolio_mvo_optimizer.py                          │       │
│  │  Mean-variance optimization using PyPortfolioOpt                │       │
│  │  - optimize_weights()                                            │       │
│  │  - get_efficient_frontier()                                      │       │
│  │  - optimize_triple() → current, weights, market                 │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              stress_test_analyzer.py                             │       │
│  │  Historical crisis simulation                                    │       │
│  │  - analyze_portfolio()                                           │       │
│  │  - calculate_max_drawdown()                                      │       │
│  │  - calculate_resilience_score()                                  │       │
│  │  Scenarios: 2008 Financial Crisis, 2020 COVID Crash             │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              pdf_report_generator.py                             │       │
│  │  Publication-quality PDF generation (300 DPI)                   │       │
│  │  - generate_portfolio_report()                                   │       │
│  │  - Charts: sector, frontier, stress test, projection            │       │
│  │  - Tables: holdings, metrics, tax comparison                    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              email_notifier.py                                   │       │
│  │  SMTP notifications (Gmail)                                      │       │
│  │  - Cold start alerts                                             │       │
│  │  - TTL expiration warnings                                       │       │
│  │  - Sender: "Portfolio-wizard App"                               │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SYSTEMS                                    │
│                                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │       REDIS         │  │   ALPHA VANTAGE     │  │   YAHOO FINANCE     │  │
│  │                     │  │                     │  │                     │  │
│  │ • Primary data store│  │ • Stock fundamentals│  │ • Price history     │  │
│  │ • Portfolio buckets │  │ • Sector data       │  │ • FX rates          │  │
│  │ • Ticker cache      │  │ • Company overview  │  │ • Real-time quotes  │  │
│  │ • Shareable links   │  │                     │  │                     │  │
│  │ • Rate limiting     │  │ Rate: 5/min (free)  │  │ Rate: Fair use      │  │
│  │                     │  │                     │  │                     │  │
│  │ Port: 6379          │  │ API Key required    │  │ No API key          │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                               │
│  ┌─────────────────────┐                                                     │
│  │    GMAIL SMTP       │                                                     │
│  │                     │                                                     │
│  │ • Alert emails      │                                                     │
│  │ • Port: 587 (TLS)   │                                                     │
│  │ • App password req. │                                                     │
│  └─────────────────────┘                                                     │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## END OF DETAILED DOCUMENTATION