### Portfolio Generation System Overview

#### Part 1 — User Perspective (no code)
- Objective
  - Deliver a small set of high‑quality, diverse stock portfolios matched to a user’s risk profile, minimizing overlap and reflecting sector balance and realistic risk.

- How it starts
  - Triggered when the user selects a risk profile or opens a page that requests portfolio recommendations. If pre-generated portfolios exist, they are served immediately; otherwise the system generates them.

- What the user does and sees
  - Choose a risk profile (e.g., conservative, moderate, aggressive).
  - Brief wait while the system reads from its local cache and composes portfolios (typically seconds if pre-generated; longer only for a fresh build).
  - Receive 3 recommendations (from a pool of 12 stored for the profile):
    - Each portfolio has 3–4 stocks with percentage weights, sector tags, risk/return metrics.
    - The 3 are diversified against each other to reduce symbol overlap.

- Expected end result
  - Session-aware diversity: the user sees non-repeating combinations per session/day.
  - Risk alignment: each portfolio is filtered to the profile’s volatility band and sector-balanced.
  - Clear outputs: names, descriptions, allocations, sector breakdown, risk/return metrics.

- Fallbacks and errors
  - If unique generation is temporarily not possible or data is missing, a fallback portfolio with broad, stable symbols and reasonable weights is shown. The system recovers automatically once data and generation complete.


#### Part 2 — Developer Perspective (workflow and architecture)
- Startup and resource initialization
  - Redis-first design: cached data in Redis; lazy external data fetcher only when required.
  - Orchestration by `EnhancedPortfolioGenerator` for 12 variations per risk profile.

- Phases (what, why, who)
  1) Cache warmup (optional)
     - Why: Prime Redis with prices/sector/metrics for fast, deterministic generation.
     - Who: `RedisFirstDataService.enhanced_data_fetcher.warm_cache()`.
  2) Data acquisition (shared for all 12)
     - Why: Build the candidate pool of stocks with basic metrics.
     - Who: `PortfolioStockSelector._get_available_stocks_with_metrics` (pipelines, parsing, lightweight metrics).
  3) Volatility filtering
     - Why: Restrict candidates to the profile’s risk (volatility) band; adaptively widen if too small.
     - Who: `PortfolioStockSelector._filter_stocks_by_volatility`.
  4) Stock selection (per variation, deterministic & diversified)
     - Why: Ensure sector diversity and variation across the 12 portfolios.
     - Who: `PortfolioStockSelector._select_diversified_stocks_deterministic`, `_get_sector_priority_order`, `_smart_sector_sampling`.
  5) Weight assignment
     - Why: Assign realistic percentage weights from profile-size templates; vary by variation.
     - Who: `PortfolioStockSelector._create_portfolio_allocations`.
  6) Uniqueness verification
     - Why: Eliminate duplicates (symbols/weights/sector/volatility) within a profile.
     - Who: `EnhancedPortfolioGenerator._create_allocation_key_scoped`, `_is_allocation_unique`, `_mark_allocation_as_used_scoped` (Redis set `portfolio:signatures:{profile}`); env knobs control tolerance/variation/retry budget.
  7) Portfolio metrics
     - Why: Compute `expectedReturn`, `risk`, `diversificationScore`, `sectorBreakdown` for finalized allocations.
     - Who: `PortfolioAnalytics.calculate_real_portfolio_metrics` (uses cached metrics or monthly series).
  8) Storage & overlap matrix
     - Why: Persist the 12 portfolios and accelerate session-level diversity selection with a precomputed NxN overlap matrix.
     - Who: `EnhancedPortfolioGenerator._ensure_portfolio_uniqueness` (final pass) and `_compute_and_store_overlap_matrix` (key: `portfolio:overlap:{risk}:{data_hash}`).

- Files and functions (by stage)
  - Orchestrator: `backend/utils/enhanced_portfolio_generator.py`
    - `generate_portfolio_bucket`, `_generate_portfolios_parallel`, `_generate_single_portfolio_deterministic`, `_create_allocation_key_scoped`, `_is_allocation_unique`, `_mark_allocation_as_used_scoped`, `_validate_stock_pool_sufficiency`, `_compute_and_store_overlap_matrix`.
  - Selection: `backend/utils/portfolio_stock_selector.py`
    - `_get_available_stocks_with_metrics`, `_filter_stocks_by_volatility`, `_select_diversified_stocks_deterministic`, `_smart_sector_sampling`, `_create_portfolio_allocations`.
  - Analytics: `backend/utils/port_analytics.py`
    - `PortfolioAnalytics.calculate_real_portfolio_metrics` + helpers.
  - Data service: `backend/utils/redis_first_data_service.py`
    - `list_cached_tickers`, `get_monthly_data`, `get_cached_metrics`, `warm_cache`, `get_cache_inventory`.


### Workflow Process (from trigger to stored results)
1) Trigger: UI requests portfolios for a risk profile (or regeneration timer fires).
2) Acquire data once: `PortfolioStockSelector._get_available_stocks_with_metrics` builds the candidate pool from Redis.
3) Pre-flight check: `_validate_stock_pool_sufficiency` logs if pool might be too small for uniqueness.
4) For each variation (0..11, parallel):
   - Filter by volatility → select diversified stocks → assign weights.
   - Create a scoped signature and check uniqueness; retry if duplicate within the configured attempt budget.
   - Compute portfolio metrics for unique allocations.
5) Finalize: `_ensure_portfolio_uniqueness` removes any residual duplicates across the 12.
6) Persist: store the 12 results and compute the NxN symbol-overlap matrix in Redis for fast session-level diversity.
7) Serve: the API/session layer selects 3 low-overlap portfolios per request, avoiding repeats per session/day.


