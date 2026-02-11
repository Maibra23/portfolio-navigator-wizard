# Optimize Button: End-to-End Flow

This document describes how the Optimize button works on the Portfolio Optimization page: user interaction, risk profiles, math, backend workflow, and UI, plus the code involved at each step.

---

## 1. Concise End-to-End Picture

1. User is on the Portfolio Optimization step with a built portfolio and a selected risk profile.
2. User clicks **Optimize** → frontend calls `POST /api/v1/portfolio/optimization/triple` with tickers, actual weights, and risk profile.
3. Backend: (a) computes current portfolio metrics, (b) runs weights-only optimization (same tickers, max Sharpe), (c) runs market exploration (new ticker set, max Sharpe with risk cap from profile), (d) decides recommendation, (e) builds comparison and returns triple response.
4. Frontend stores the triple result, fills efficient frontier / random / CML from the response, updates chart and comparison table, and switches to the Analysis tab.
5. Risk profile sets the **maximum volatility** for the market path and drives **which of the three portfolios is recommended**; the math (max Sharpe, frontier, CML) is the same for all profiles.

---

## 2. User Interaction

- **Where**: Wizard step "Portfolio Optimization" (Optimization tab). The Optimize button is in that tab.
- **What happens on click**: `runOptimization()` runs: validates tickers (≥2) and risk profile, sets loading/clears error, POSTs to `/api/v1/portfolio/optimization/triple` with payload below, then on success updates state (triple results, frontier, random, CML, optimized portfolio) and switches to Analysis tab; on error shows a user-friendly message.
- **Risk profile**: Passed in the request; used on the backend to cap max volatility (market path), size the market basket, and choose the recommended portfolio (current / weights / market).

---

## 3. Risk Profiles: Objective, Constraints, Risk Tolerance

| Profile             | Max portfolio risk (volatility) | Source config key   |
|---------------------|----------------------------------|---------------------|
| Very Conservative  | 18%                              | max_portfolio_risk  |
| Conservative       | 25%                              | max_portfolio_risk  |
| Moderate           | 32%                              | max_portfolio_risk  |
| Aggressive         | 42%                              | max_portfolio_risk  |
| Very Aggressive    | 55%                              | max_portfolio_risk  |

- **Objective**: Same for all profiles — maximize Sharpe ratio (risk-adjusted return).
- **Constraints**: Weights sum to 1; no short selling (weights ≥ 0). For the **market** path only: portfolio volatility ≤ profile max (from `risk_profile_config`).
- **Risk tolerance**: Defined by that max volatility; recommendation logic also uses a 10% buffer on the limit.

Config lives in: `backend/utils/risk_profile_config.py` (`UNIFIED_RISK_PROFILE_CONFIG`, `RISK_PROFILE_MAX_RISK`, `get_max_risk_for_profile`).

---

## 4. Math and Logic

- **Objective**: max (μ − r_f) / σ with μ = w'μ, σ = √(w'Σw), ∑w = 1, w ≥ 0. Implemented as PyPortfolioOpt `max_sharpe(risk_free_rate)`.
- **Efficient frontier**: For each target return, minimize w'Σw s.t. w'μ = μ_target, ∑w = 1, w ≥ 0. Built by min-variance point plus `ef.efficient_return(target_return)` over a return range. Outputs (risk, return, sharpe_ratio, weights) per point.
- **Optimal portfolio**: The max-Sharpe (tangent) portfolio on the frontier. When a risk cap is applied (market path), solver uses `efficient_risk(max_risk)` so the chosen portfolio is the highest-return (and thus max-Sharpe) portfolio with σ ≤ max_risk.
- **Inefficient frontier**: For each target risk, minimize return (w'μ) s.t. σ = target_risk, ∑w = 1, w ≥ 0 (scipy minimize). Used only for visualization.
- **Random portfolios**: Dirichlet random weights; (σ, μ) and Sharpe computed for each.
- **Capital Market Line**: Return = r_f + Sharpe_market × σ, with the market-optimized portfolio used as the tangent point so the CML passes through it.

Safeguards: return capped at 50%, risk floored at 8%, Sharpe capped at 2.5.

---

## 5. System Workflow

### 5.1 Frontend

- **Entry**: User clicks Optimize → `runOptimization()` in `PortfolioOptimization.tsx`.
- **Request**: POST `/api/v1/portfolio/optimization/triple` with:
  - `user_tickers`, `user_weights` (allocation/100 per symbol)
  - `risk_profile`, `optimization_type: 'max_sharpe'`
  - `include_efficient_frontier: true`, `include_random_portfolios: true`
  - `num_frontier_points: 20`, `num_random_portfolios: 300`
  - `use_combined_strategy: true`, `attempt_market_exploration: true`
- **Response**: `TripleOptimizationResponse`: `current_portfolio`, `weights_optimized_portfolio`, `market_optimized_portfolio` (optional), `comparison`, `optimization_metadata`.
- **State updates**: Triple results, MVO result (primary = market or weights), optimized allocations, efficient frontier, inefficient frontier, random portfolios, success message; then switch to Analysis tab.

### 5.2 Backend

- **Endpoint**: `POST /api/v1/portfolio/optimization/triple` → `optimize_triple_portfolio` in `backend/routers/portfolio.py`.
- **Steps**:
  1. **Current portfolio**: Try Redis for precomputed metrics for same tickers+weights; else `compute_portfolio_metrics_with_weights(tickers, weights, optimizer)`.
  2. **Weights-only**: `optimize_weights_only(user_tickers, risk_profile, optimizer, optimization_type)` — same tickers, max_sharpe (or min_volatility), no risk cap. Then generate efficient frontier, inefficient frontier, random portfolios, CML for that universe.
  3. **Market exploration**: Get eligible tickers, build candidate pool with overlap validation (e.g. 96 months), choose basket size by profile. Call `optimizer.optimize_portfolio(..., risk_profile=request.risk_profile)` (applies profile max_risk). Generate frontier, random, inefficient frontier, CML from market-optimized portfolio.
  4. **Recommendation**: `decide_best_portfolio_v2(current, weights_opt, market_opt, risk_profile)` using profile max risk (with buffer) and Sharpe/risk deltas.
  5. **Comparison**: `build_triple_comparison(...)` → return/risk/Sharpe differences (weights vs current, market vs current), best_sharpe. Optionally add Monte Carlo and quality scores.
  6. Return `TripleOptimizationResponse`.

### 5.3 Optimization Engine

- **Module**: `backend/utils/portfolio_mvo_optimizer.py` — `PortfolioMVOptimizer`.
- **Data**: μ and Σ from `get_ticker_metrics_func` (ticker-metrics pipeline).
- **Solver**: PyPortfolioOpt `EfficientFrontier`; scipy for inefficient frontier.
- **Risk profile**: Only used in `optimize_portfolio` via `_get_max_risk_for_profile(risk_profile)` to set max_risk and, if needed, `efficient_risk(max_risk)` or fallbacks (relaxed risk, then min_volatility).

---

## 6. Results Visualization

- **Efficient frontier graph**: Built from `efficient_frontier` and `inefficient_frontier` (and optionally random portfolios and CML) in the triple response. Risk = x, return = y. Current, Weights-Optimized, and Market-Optimized are plotted as distinct points (with jitter if overlapping). Chart is in the Analysis tab (zoom/box-zoom supported).
- **Optimized portfolios on graph**: Shown as Weights-Optimized and Market-Optimized points; the **recommended** one is indicated in the Portfolio Comparison table (and in metadata), not by a separate chart marker.
- **Portfolio comparison**: Backend `build_triple_comparison` computes return_difference, risk_difference, sharpe_difference (weights vs current, market vs current) and best_sharpe. Frontend `PortfolioComparisonTable` shows a table (Current | Weights-Opt | Market-Opt) with metrics and marks the recommended column.

---

## 7. Code Involved and What Each Does

### 7.1 Frontend

| File | Symbol / region | What it does |
|------|------------------|---------------|
| `frontend/src/components/wizard/PortfolioOptimization.tsx` | `runOptimization` (approx. 1893–2118) | Validates tickers and risk profile; builds `currentWeights`; POSTs to `/api/v1/portfolio/optimization/triple` with request payload; 60s timeout; on success: sets triple results, MVO result, optimized allocations, efficient/inefficient frontier, random portfolios, success, then switches to Analysis tab; on error: parses and sets user-facing error. |
| Same file | Request payload (approx. 1928–1941) | `user_tickers`, `user_weights`, `risk_profile`, `optimization_type: 'max_sharpe'`, frontier/random flags and counts, `use_combined_strategy`, `attempt_market_exploration`. |
| Same file | State after success (approx. 2070–2195) | `setTripleOptimizationResults`, `setMvoResults`, `setOptimizedPortfolio`, `setOptimizationResults`, `setEfficientFrontier`, `setInefficientFrontier`, `setRandomPortfolios` from triple response; frontier source = market_optimized_portfolio or weights_optimized_portfolio. |
| Same file | `portfolioPointsWithJitter` (approx. 664–709) | Builds chart points for Current, Weights-Optimized, Market-Optimized from `tripleOptimizationResults` and applies jitter for overlapping points. |
| `frontend/src/components/wizard/FinalizePortfolio.tsx` | `handleOptimize` (approx. 118–170) | Same pattern: POST to `/api/v1/portfolio/optimization/triple` with similar payload; on success calls `updateOptimizedPortfolio(data)` and `markTabComplete('optimize')`. Used on the Finalize step’s Optimize tab. |
| `frontend/src/components/wizard/EfficientFrontierChart.tsx` | Component | Renders risk–return chart: efficient frontier, inefficient frontier, random portfolios, CML, and portfolio points (current, weights-optimized, market-optimized). |
| `frontend/src/components/wizard/PortfolioComparisonTable.tsx` | Component | Renders comparison table (Current | Weights-Opt | Market-Opt), shows recommendation from `optimization_metadata.recommendation`, displays metrics and optional Monte Carlo/quality. |

### 7.2 Backend Router (`backend/routers/portfolio.py`)

| Symbol / region | What it does |
|-----------------|---------------|
| `TripleOptimizationRequest` (approx. 2322–2335) | Pydantic model: `user_tickers`, `user_weights`, `risk_profile`, `optimization_type`, `max_eligible_tickers`, `include_efficient_frontier`, `include_random_portfolios`, `num_frontier_points`, `num_random_portfolios`, `use_combined_strategy`, `attempt_market_exploration`. |
| `TripleOptimizationResponse` (approx. 2336–2342) | Response model: `current_portfolio`, `weights_optimized_portfolio`, `market_optimized_portfolio`, `comparison`, `optimization_metadata`. |
| `optimize_triple_portfolio` (approx. 3471–4006) | POST handler: validates input; gets MVO optimizer; Step 1 current metrics (Redis or `compute_portfolio_metrics_with_weights`); Step 2 `optimize_weights_only` and frontier/random/CML for weights universe; Step 3 market exploration (eligible tickers, overlap, `optimizer.optimize_portfolio` with risk_profile, frontier/random/CML); Step 4 `decide_best_portfolio_v2`; Step 5 `build_triple_comparison`; optional Monte Carlo/quality; returns triple response. |
| `get_mvo_optimizer` (approx. 2110–2139) | Singleton MVO optimizer; uses internal `get_ticker_metrics_internal` calling `get_ticker_metrics_batch`. |
| `compute_portfolio_metrics_with_weights` (approx. 2365–2444) | Aligns tickers with metrics, normalizes weights, computes expected_return = w'μ, risk = √(w'Σw), sharpe_ratio; recursion guard with equal-weight fallback. |
| `find_matching_portfolio_in_redis` (approx. 2446–2532) | Looks up precomputed portfolio metrics in Redis by risk_profile bucket and ticker+allocation match (1% tolerance). |
| `optimize_weights_only` (approx. 2534–2598) | Gets μ, Σ; aligns tickers; builds PyPortfolioOpt `EfficientFrontier`; calls `max_sharpe` or `min_volatility` (no risk cap); returns tickers, weights, metrics (expected_return, risk, sharpe_ratio). |
| `decide_best_portfolio_v2` (approx. 2658–2734) | Uses `RISK_PROFILE_MAX_RISK_WITH_BUFFER`; compares current, weights, market by Sharpe and risk; enforces risk compliance; returns "market" / "weights" / "current" per rules (e.g. significant Sharpe improvement, moderate risk increase). |
| `build_triple_comparison` (approx. 2736–2790+) | Computes `weights_vs_current` and `market_vs_current` (return_difference, risk_difference, sharpe_difference), best_sharpe; returns comparison dict. |
| `_postprocess_weights` (approx. 2344–2363) | Trims tiny weights, keeps top N assets, renormalizes; used for market-optimized portfolio. |

### 7.3 MVO Optimizer (`backend/utils/portfolio_mvo_optimizer.py`)

| Symbol / region | What it does |
|-----------------|---------------|
| `PortfolioMVOptimizer` | Class: holds `get_ticker_metrics_func`, `risk_free_rate`. |
| `get_ticker_metrics` | Calls `get_ticker_metrics_func(tickers, ...)`, maps response to μ dict and Σ DataFrame; validates and returns (mu_dict, sigma_df). |
| `optimize_portfolio` (approx. 96–321) | Gets μ, Σ; builds `EfficientFrontier`; if risk_profile, sets max_risk from `_get_max_risk_for_profile`; for max_sharpe: runs `ef.max_sharpe`, then if portfolio risk > max_risk re-optimizes with `efficient_risk(max_risk)`; fallbacks (relaxed risk, then min_volatility); other types: min_volatility, efficient_return, efficient_risk; cleans weights; applies return/risk/Sharpe safeguards; returns weights, tickers, expected_return, risk, sharpe_ratio. |
| `_get_max_risk_for_profile` (approx. 434–443) | Delegates to `risk_profile_config.get_max_risk_for_profile(risk_profile)`. |
| `generate_efficient_frontier` (approx. 323–424) | Gets μ, Σ; adds min-variance point; sweeps target returns with `ef.efficient_return(target_return)`; returns list of {return, risk, sharpe_ratio, weights, weights_list, type}. |
| `generate_inefficient_frontier` (approx. 426–541) | For each target risk, minimizes return (w'μ) s.t. σ = target_risk, ∑w = 1, w ≥ 0 via scipy minimize; returns list of points. |
| `generate_random_portfolios` (approx. 423–441) | Dirichlet random weights; computes return, risk, Sharpe for each; returns list of points. |
| `calculate_capital_market_line` (approx. 469–551) | If market_portfolio given, CML from (0, r_f) through that point; else tangent from efficient frontier; returns list of (risk, return) points. |
| `calculate_portfolio_metrics` (approx. 445–497) | Given weights, computes portfolio return, risk, Sharpe with same safeguards. |

### 7.4 Risk Profile Config (`backend/utils/risk_profile_config.py`)

| Symbol / region | What it does |
|-----------------|---------------|
| `UNIFIED_RISK_PROFILE_CONFIG` | Dict per profile: volatility_range, max_portfolio_risk, return_range, quality_risk_range, fallback_return, fallback_risk, etc. |
| `RISK_PROFILE_MAX_RISK` | Derived: profile → max_portfolio_risk (18%, 25%, 32%, 42%, 55% for the five profiles). |
| `RISK_PROFILE_MAX_RISK_WITH_BUFFER` | max_portfolio_risk × 1.10 per profile; used in recommendation logic. |
| `get_max_risk_for_profile(risk_profile, use_buffer=False)` | Returns max allowed portfolio volatility for the profile (from RISK_PROFILE_MAX_RISK or WITH_BUFFER). |

### 7.5 API Contract

- **Request**: `POST /api/v1/portfolio/optimization/triple`  
  Body: `TripleOptimizationRequest` (user_tickers, user_weights, risk_profile, optimization_type, frontier/random options, use_combined_strategy, attempt_market_exploration).
- **Response**: `TripleOptimizationResponse`: current_portfolio (tickers, weights, metrics), weights_optimized_portfolio (optimized_portfolio + efficient_frontier, inefficient_frontier, random_portfolios, capital_market_line, metadata), market_optimized_portfolio (same shape, optional), comparison (weights_vs_current, market_vs_current, best_sharpe, optional monte_carlo/quality_scores), optimization_metadata (recommendation, processing_time_seconds, etc.).

---

## 8. Mapping: Backend → Frontend

| Backend | Frontend |
|---------|----------|
| `weights_optimized_portfolio.efficient_frontier` or `market_optimized_portfolio.efficient_frontier` | Efficient frontier curve (market preferred if present). |
| `current_portfolio.metrics`, `weights_optimized_portfolio.optimized_portfolio.metrics`, `market_optimized_portfolio.optimized_portfolio.metrics` | Current, Weights-Optimized, Market-Optimized points on chart. |
| `comparison.weights_vs_current`, `comparison.market_vs_current`, `comparison.best_sharpe` | Portfolio comparison table (deltas and best Sharpe). |
| `optimization_metadata.recommendation` | Which column is “Recommended” in the comparison table. |

---

## 9. Summary

- One click sends current tickers, actual weights, and risk profile to the triple endpoint.
- Backend returns three portfolios (current, weights-optimized, market-optimized) plus frontier data and a recommendation.
- Risk profile only changes the **volatility cap** for the market path and **recommendation**; the objective (max Sharpe) and frontier/CML math are the same for all profiles.
- All code paths above implement this flow; the listed files and symbols are the ones involved in the Optimize button behavior and the resulting UI.
