## Portfolio Optimization Button & Tabs – End‑to‑End Workflow

**Scope**: This document explains how the **Optimize** button works and how the **Optimization**, **Analysis**, and **Recommendations** tabs behave, based on the current implementation (frontend + backend).

### Progress overview (user journey)

- [x] **Step 1 – Risk profile & capital** (set in `RiskProfiler` and `CapitalInput`)
- [x] **Step 2 – Stock selection** (choose tickers + allocations in `StockSelection`)
- [ ] **Step 3 – Run optimization** (click **Optimize** in the Optimization tab)
- [ ] **Step 4 – Review analysis** (Efficient Frontier & visualization tab)
- [ ] **Step 5 – Review recommendations** (Recommendations tab, quality scores, Monte Carlo)

---

## 1. What happens when you click “Optimize”

### 1.1 Inputs the Optimize button uses

From `PortfolioWizard`:
- **Risk profile**: one of `very-conservative` … `very-aggressive`.
- **Capital**: numeric amount in SEK.
- **Selected stocks**: list of `{ symbol, allocation, name?, assetType? }`, where:
  - `allocation` is a percentage (0–100) and the list is expected to sum to ~100%.

Inside `PortfolioOptimization`:
- `currentPortfolio` is initialized from `selectedStocks`.
- When you click **Optimize**, `runOptimization`:
  - Builds `user_tickers` = ordered list of ticker symbols.
  - Builds `user_weights` = `{ [ticker]: allocation / 100 }` (true weights as decimals).
  - Uses the current **riskProfile** string.

### 1.2 API call and request payload

The Optimize button triggers `runOptimization`, which:
- Performs a quick backend health check (`GET /health`, non‑blocking).
- Builds a **TripleOptimizationRequest** payload:
  - `user_tickers`: list of tickers from the current portfolio.
  - `user_weights`: map of ticker → weight (0–1, sums to 1).
  - `risk_profile`: selected user risk profile.
  - `optimization_type`: `"max_sharpe"` (maximize risk‑adjusted return).
  - `max_eligible_tickers`: 20 (upper bound on market exploration pool).
  - `include_efficient_frontier`: `true`.
  - `include_random_portfolios`: `true`.
  - `num_frontier_points`: 20.
  - `num_random_portfolios`: 300.
  - `use_combined_strategy`: `true` (weights‑first + market exploration).
  - `attempt_market_exploration`: `true`.
- Sends `POST /api/v1/portfolio/optimization/triple` with a **60s timeout**.

If the call fails, `runOptimization`:
- Maps backend errors to user‑friendly messages (e.g. timeout, connectivity problems, volatility constraints, bad requests).
- Shows the error in a red `Alert` under the Optimize button.

If it succeeds, the frontend:
- Parses a **TripleOptimizationResponse** with three portfolios plus a `comparison` and `optimization_metadata` block.
- Stores it in `tripleOptimizationResults`.
- Sets `mvoResults` to the **market‑optimized** result if available, otherwise the **weights‑optimized** result (for charts/backward‑compat).
- Builds a new `optimizedPortfolio` list (top tickers and allocations) for display.
- Populates:
  - `efficientFrontier` (for the Efficient Frontier chart),
  - `randomPortfolios` (for scatter cloud),
  - and related visualization series.

---

## 2. Backend optimization logic (triple optimization)

Endpoint: `POST /api/v1/portfolio/optimization/triple` in `backend/routers/portfolio.py`.

### 2.1 High‑level steps

For a given `(user_tickers, user_weights, risk_profile)` the endpoint:
1. **Validates inputs**
   - Requires at least 2 tickers.
   - Requires a non‑empty `user_weights` map.
2. **Builds an MVO optimizer**
   - Uses `PortfolioMVOptimizer` with a **risk‑free rate ~3.8%**.
   - MVO engine pulls mean returns (μ) and covariance (Σ) from the data layer via a `get_ticker_metrics` function.
3. **Current portfolio metrics (actual weights)**
   - `compute_portfolio_metrics_with_weights` computes:
     - \( \mu_p = w^\top \mu \) (expected annualized return),
     - \( \sigma_p = \sqrt{w^\top \Sigma w} \) (annualized risk / volatility),
     - Sharpe ratio \( = (\mu_p - r_f) / \sigma_p \).
   - Result saved as `current_portfolio.metrics`.
4. **Weights‑only optimization (current universe)**
   - Runs MVO on **the same tickers** but re‑allocates weights:
     - Primary objective: **max Sharpe** (`optimization_type="max_sharpe"`).
     - Uses centralized risk limits from `risk_profile_config.py`:
       - `get_max_risk_for_profile(risk_profile)` → e.g. 18%, 25%, 32%, 42%, 55%.
     - If unconstrained max‑Sharpe risk **exceeds** the profile limit, it re‑optimizes with an **efficient risk** constraint at that max‑risk level.
   - Also generates:
     - Efficient frontier (`generate_efficient_frontier`),
     - Inefficient frontier (lower branch, “worst‑return for given risk”),
     - Random portfolios (Dirichlet‑sampled weights),
     - Capital Market Line (CML) from the tangent portfolio.
5. **Market‑optimized portfolio (market exploration)**
   - If permitted and feasible, the backend:
     - Selects an eligible universe of tickers for the given risk profile (using volatility bands and eligibility filters).
     - Runs MVO on this **larger universe**, again max‑Sharpe with risk‑profile constraints.
     - Produces a second optimized portfolio plus its own frontier / random points / CML.
   - If market exploration fails (e.g. insufficient data), it gracefully returns `market_optimized_portfolio = null`.
6. **Analytics: Monte Carlo & quality scores**
   - Uses `PortfolioAnalytics` for:
     - **Monte Carlo** (see §3.1).
     - **Quality scores** (see §3.2).
7. **Decision engine: recommendation**
   - Compares **current**, **weights**, and (if available) **market** portfolios on:
     - Expected return,
     - Risk,
     - Sharpe ratio,
     - Quality score,
     - Risk‑profile compliance.
   - Computes `comparison`:
     - `weights_vs_current`, `market_vs_current`, `market_vs_weights`.
     - `best_return`, `best_risk`, `best_sharpe` flags.
     - `monte_carlo` and `quality_scores` for all three portfolios.
   - Chooses a final **recommendation** (`'current' | 'weights' | 'market'`) written to `optimization_metadata.recommendation`.

---

## 3. Math & metrics used under the hood

### 3.1 Core portfolio metrics

Given **weights** \( w \), **returns vector** \( \mu \), and **covariance matrix** \( \Sigma \):
- **Expected return**:
  \[
  \mu_p = w^\top \mu
  \]
- **Risk (volatility)**:
  \[
  \sigma_p = \sqrt{w^\top \Sigma w}
  \]
- **Sharpe ratio** (risk‑adjusted return, with risk‑free rate \( r_f \approx 3.8\% \)):
  \[
  \text{Sharpe} = \frac{\mu_p - r_f}{\sigma_p}
  \]

These are computed in `PortfolioMVOptimizer` and `PortfolioAnalytics` and surfaced both in the backend response and frontend UI.

### 3.2 Efficient frontier and Capital Market Line (CML)

- **Efficient frontier**:
  - For a range of target returns, MVO solves for weights that **minimize risk** subject to that target return.
  - Each frontier point contains:
    - `risk`, `return`, `sharpe_ratio`, `weights`, `weights_list`, `type: 'frontier'`.
- **Inefficient frontier**:
  - Symmetric lower branch: for a range of target risks, it **minimizes return** for that risk, using constrained optimization.
- **Capital Market Line (CML)**:
  - Finds the **tangent portfolio** on the frontier with maximum Sharpe.
  - For a range of risk values:
    \[
    \text{Return}_{\text{CML}}(\sigma) = r_f + \text{Sharpe}_\text{tangent} \times \sigma
    \]
  - Returned as a set of `{'risk', 'return', 'type': 'cml'}` points.

### 3.3 Monte Carlo simulation

From `PortfolioAnalytics.run_monte_carlo_simulation`:
- Inputs:
  - `expected_return` (annualized),
  - `risk` (annualized volatility),
  - `num_simulations` (10,000),
  - `time_horizon_years` (currently 1 year).
- Assumes log‑normal or normalised returns process per period based on those inputs.
- For each simulation:
  - Draws a stochastic return path over the time horizon.
  - Records final portfolio return.
- Outputs for UI:
  - `probability_positive`: probability(final return > 0).
  - `percentiles`: `{ p5, p25, p50, p75, p95 }` of final return.
  - `probability_loss_thresholds`: probability of losing more than 5%, 10%, 20%, 30%.
  - `histogram_data`: binned distribution (`return`, `return_pct`, `frequency`).
  - `statistics`: mean, std, min, max, median.
  - `probability_statements`: human‑readable bullet points.

### 3.4 Quality score (0–100 composite)

From `PortfolioAnalytics.calculate_quality_score`:
- Factors:
  - **Risk profile compliance**:
    - Measures how well portfolio risk aligns with the allowed band for the user’s risk profile.
  - **Sortino / downside protection**:
    - Focused on downside volatility (negative returns) vs. total volatility.
  - **Diversification**:
    - Evaluates spread across sectors and correlations (via `_calculate_sophisticated_diversification_score`).
  - **Consistency**:
    - Stability of returns over time.
- Each factor is normalized to a 0–100 **score**, then combined with weights:
  \[
  \text{Composite} = \sum_{\text{factor}} \text{score}_i \times \text{weight}_i
  \]
- Output structure (per portfolio):
  - `composite_score` (0–100),
  - `rating` (`Excellent`, `Good`, `Fair`, `Needs Improvement`),
  - `rating_color` (`green`, `blue`, `yellow`, `red`),
  - `factor_breakdown` with `score`, `label`, `description` for each factor.

---

## 4. Optimization tab – what the user sees

### 4.1 Eligible tickers & Optimize panel

In the **Optimization** tab:
- Left side:
  - **Eligible Tickers scatter plot**:
    - X‑axis: risk (volatility).
    - Y‑axis: expected return.
    - Shows:
      - User’s selected portfolio tickers (highlighted),
      - Eligible market tickers that match the risk profile.
    - Supports **box zoom** and series filtering.
- Bottom:
  - **Info bar** explaining that optimization uses **eligible market tickers** matching your risk profile.
  - **Optimize button**:
    - Disabled until there are at least 2 stocks.
    - On click → `runOptimization` (triple optimization call).
  - Error/success alerts for the optimization request.

### 4.2 Post‑optimization charts (Efficient Frontier)

The **Analysis** tab and the lower parts of the Optimization tab re‑use:
- `efficientFrontier`, `inefficientFrontier`, `randomPortfolios`, and the selected **optimized portfolio point**:
  - **Random portfolios**: grey scatter cloud (risk‑return samples).
  - **Efficient frontier**: main frontier curve (upper branch).
  - **Inefficient frontier**: lower branch for teaching purposes.
  - **CML** (optional): straight line from risk‑free rate through tangent portfolio.
  - **Portfolio points**:
    - Current portfolio.
    - Weights‑optimized portfolio.
    - Market‑optimized portfolio.
- Users can:
  - Zoom in/out via box zoom or buttons.
  - Toggle each series (random, efficient, inefficient, CML, specific portfolios) via an interactive legend.

---

## 5. Analysis tab – Efficient Frontier & correlation/sector views

The **Analysis** tab (inside `PortfolioOptimization`) provides three main analytic views:

1. **Return vs. Risk scatter (Efficient Frontier view)**  
   - Visualizes:
     - Efficient frontier (+ inefficient frontier),
     - Random portfolios,
     - Current vs optimized portfolios,
     - CML line.
   - Interaction:
     - Hover for tooltips,
     - Toggle series visibility,
     - Brush/zoom with reset controls.

2. **Correlation Matrix**  
   - Built from correlation of ticker return series for the selected portfolio (and related portfolios).
   - Color scale:
     - Strong negative correlation → deep red,
     - Near zero → yellow/grey,
     - Strong positive → deep green.
   - Shows:
     - Symmetric matrix with tickers on both axes,
     - Correlation values in each cell,
     - Optional portfolio label per ticker row.

3. **Sector Allocation pie**  
   - Uses the **selected portfolio only**:
     - Computes sector allocation from tickers and their sectors.
     - Summarizes total weight per sector.
   - Shows:
     - Sector slice (% of portfolio),
     - Tooltip with sector total and per‑stock allocations.
     - Optional diversification score badge (from backend).

---

## 6. Recommendations tab – how results are presented

The **Recommendations** tab consumes `tripleOptimizationResults` and `comparison`:

### 6.1 Performance summary

- Uses either **triple** or **dual** optimization data:
  - For triple:
    - Computes diffs between **current portfolio** and the **recommended portfolio**:
      - Δ Expected return,
      - Δ Risk,
      - Δ Sharpe ratio.
  - For dual (fallback):
    - Uses `comparison.return_difference`, `risk_difference`, `sharpe_difference`.
- Shows:
  - Green/red deltas for each metric,
  - A **Risk Profile Compliance** box:
    - Max allowed risk for the selected risk profile (e.g. 18%, 25%, 32%, 42%, 55%),
    - Recommended portfolio’s risk vs limit,
    - Status badge (`✓ Compliant` / `⚠ Over Limit`).

### 6.2 System recommendation

- Reads `optimization_metadata.recommendation`:
  - `'current'`: keep your current allocation.
  - `'weights'`: adopt **weights‑optimized** portfolio.
  - `'market'`: adopt **market‑optimized** portfolio.
- Shows:
  - Recommended label and color (red/blue/green),
  - Status of **market exploration** (successful/failed).

### 6.3 Quality score card

- Uses `comparison.quality_scores`:
  - `current`, `weights`, `market` (or `optimized` in dual mode).
- UI elements:
  - **Circular gauge** for composite score (0–100).
  - Badge showing rating (`Excellent`, `Good`, etc.).
  - Factor breakdown:
    - Risk profile match,
    - Downside protection (Sortino),
    - Diversification,
    - Consistency,
    - Each with its score bar and explanatory text.
  - Comparison tiles:
    - Current vs Weights‑Opt vs Market‑Opt scores side‑by‑side.

### 6.4 Monte Carlo card

- Uses `comparison.monte_carlo`:
  - `current`, `weights`, `market`.
- UI elements:
  - Summary tiles:
    - **Positive return probability** (e.g. “75% probability”),
    - **Median expected return** (50th percentile),
    - **Value at Risk (95%)** (5th percentile),
    - **Best case (95th percentile)**.
  - **Return distribution chart**:
    - Area charts showing probability distribution per portfolio.
    - Optional highlights for chosen percentiles (p5, p25, p50, p75, p95) across portfolios.
  - **Loss probability** grid:
    - Probability of losing more than 5%, 10%, 20%, 30%.
  - **Narrative bullets** explaining:
    - VaR interpretation,
    - Probability of gain,
    - Typical outcome range (e.g. 25th–75th percentile band).

---

## 7. How the three tabs fit together

- **Optimization tab**:
  - Lets the user **run the engine** (Optimize button),
  - Surfaces core metrics and the efficient frontier around the chosen optimized portfolio.
- **Analysis tab**:
  - Deep‑dives into **risk/return geometry**, **correlations**, and **sector exposure**,
  - Helps explain *why* the optimized portfolio looks the way it does.
- **Recommendations tab**:
  - Interprets everything in **plain language**:
    - Which portfolio is recommended,
    - How much improvement you get,
    - Whether it respects your risk profile,
    - How robust it is across Monte Carlo scenarios and quality factors.

Together, these three views turn the optimization engine into a full **decision‑support workflow**: from user inputs → optimization engine → risk/return analytics → clear, risk‑aware recommendations.


