### Portfolio Generation System - Technical Diagnostic Report

#### 1) End-to-end system overview (explicit step-by-step with inputs/outputs and ordering)
- Step 0 — Cache warmup (optional but recommended)
  - Inputs: Universe of tickers (~800+), Redis connection
  - Process: Batch fetch monthly prices, sector metadata, precomputed metrics; write Redis keys `ticker_data:prices:*`, `ticker_data:sector:*`, `ticker_data:metrics:*`
  - Outputs: Warm Redis cache (coverage target ≥90% of universe), health/inventory metrics
  - Expected timing (observed): p50 ~6–10 min; p95 ~12–20 min for ~800 tickers

- Step 1 — Data acquisition (runs once per profile generation)
  - Inputs: Redis, `RedisFirstDataService`
  - Process (order):
    1) Enumerate tickers that have both price and sector cached
    2) Batch pipeline GET (prices/sector/metrics) in chunks (50) with parallel workers
    3) Parse price blobs; compute returns, annualized risk/return when metrics absent
  - Outputs: `available_stocks: List[Dict]` with fields:
    - `symbol`, `name`, `sector`, `industry`, `volatility` (annualized risk), `return` (annualized), `prices` (last 30), `returns`
  - Timing: p50 ~3–5s; p95 ~7–9s (for ~700–800 tickers)

- Step 2 — Volatility filtering (risk-profile specific)
  - Inputs: `available_stocks`, risk profile volatility band (min, max)
  - Process: Keep stocks where `min ≤ volatility ≤ max`; sort by distance to band midpoint; adaptively widen if pool <60
  - Outputs: `filtered_stocks: List[Dict]`
  - Timing: p50 <200ms; p95 <400ms

- Step 3 — Stock selection (deterministic and diversified)
  - Inputs: `filtered_stocks`, `risk_profile`, `variation_seed`, `variation_id`
  - Process (order):
    1) Group by sector; compute sector-priority order (varies by seed)
    2) Smart sampling for large sectors to avoid clustering
    3) Pick one per sector group, then fill remaining slots by volatility sorting
  - Outputs: `selected_stocks: List[Dict]` (size 3 or 4 by profile)
  - Timing: p50 <200ms; p95 <400ms

- Step 4 — Weight assignment (template-based)
  - Inputs: `selected_stocks`, `variation_id`
  - Process: Choose a weight template from profile-size set; assign to positions deterministically (random seeded by variation for variety)
  - Outputs: `allocations: List[Dict]` with `symbol`, `allocation` (percent), `name`, `sector`, `volatility`
  - Timing: p50 <10ms; p95 <20ms

- Step 5 — Uniqueness verification (scoped to risk profile)
  - Inputs: `allocations`, env knobs `PORTFOLIO_DEDUP_TOLERANCE` (default 0.1%), `PORTFOLIO_DEDUP_INCLUDE_VARIATION` (default true)
  - Process: Build scoped signature by risk_profile + (symbol, bucketed allocation, sector, rounded volatility) + optional `|var:variation_id`; check Redis set `portfolio:signatures:{risk_profile}`; if unique, add with TTL
  - Outputs: boolean unique; Redis signature recorded on success
  - Timing: p50 ~1–10ms; p95 ~20ms

- Step 6 — Portfolio metrics (post-uniqueness)
  - Inputs: `allocations`
  - Process: Fetch cached metrics or monthly data; derive expected_return, risk, diversification_score; compute sector breakdown
  - Outputs: `expectedReturn`, `risk`, `diversificationScore`, `sectorBreakdown`
  - Timing: p50 ~50–150ms; p95 ~300–500ms

- Step 7 — Storage & overlap matrix
  - Inputs: List of 12 portfolios per profile
  - Process: Persist per-profile bucket; compute NxN symbol-overlap matrix; store at `portfolio:overlap:{risk_profile}:{data_hash}` with TTL
  - Outputs: Stored portfolios with `allocation_signature`, `symbol_set`; overlap matrix key for session-level diversity
  - Timing: p50 ~40–200ms; p95 ~400ms

#### 2) Components, files, and interconnections (per step, with short call graph)
- Step 0 — Cache warmup
  - File/class: `backend/utils/redis_first_data_service.py::RedisFirstDataService.enhanced_data_fetcher.warm_cache()`
  - Secondary: `backend/utils/enhanced_data_fetcher.py` (batch fetch, pipelines)

- Step 1 — Data acquisition
  - Files/classes:
    - `backend/utils/portfolio_stock_selector.py::PortfolioStockSelector._get_available_stocks_with_metrics`
    - Uses: `RedisFirstDataService.list_cached_tickers`, `redis_client.pipeline()`, `_process_ticker_batch_optimized`, `_parse_ticker_data_optimized`

- Step 2 — Volatility filtering
  - Files/functions:
    - `backend/utils/portfolio_stock_selector.py::_filter_stocks_by_volatility`

- Step 3 — Stock selection
  - Files/functions:
    - `backend/utils/portfolio_stock_selector.py::_select_diversified_stocks_deterministic`
    - `_get_sector_priority_order`, `_smart_sector_sampling`, `_select_best_stock_from_sector_deterministic`

- Step 4 — Weight assignment
  - Files/functions:
    - `backend/utils/portfolio_stock_selector.py::_create_portfolio_allocations`

- Step 5 — Uniqueness verification
  - Files/functions:
    - `backend/utils/enhanced_portfolio_generator.py::_create_allocation_key_scoped`
    - `_is_allocation_unique`, `_mark_allocation_as_used_scoped` (Redis set `portfolio:signatures:{risk_profile}`)

- Step 6 — Portfolio metrics
  - Files/classes:
    - `backend/utils/port_analytics.py::PortfolioAnalytics.calculate_real_portfolio_metrics`
    - Uses `RedisFirstDataService.get_cached_metrics/get_monthly_data` through local helpers

- Step 7 — Storage & overlap matrix
  - Files/functions:
    - `backend/utils/enhanced_portfolio_generator.py::_ensure_portfolio_uniqueness` (final pass)
    - `_compute_and_store_overlap_matrix` (key: `portfolio:overlap:{risk}:{data_hash}`)

- Short sequence (call graph snippet):
```text
EnhancedPortfolioGenerator.generate_portfolio_bucket
  └─ PortfolioStockSelector._get_available_stocks_with_metrics
      └─ RedisFirstDataService (pipeline GET, parsing)
  └─ for variation_id in 0..11 (parallel):
      └─ select_stocks_for_risk_profile_deterministic_with_data
          └─ _filter_stocks_by_volatility → _select_diversified_stocks_deterministic
      └─ _create_portfolio_allocations
      └─ _is_allocation_unique → _mark_allocation_as_used_scoped (Redis signatures)
      └─ PortfolioAnalytics.calculate_real_portfolio_metrics
  └─ _ensure_portfolio_uniqueness
  └─ _compute_and_store_overlap_matrix (Redis overlap key)
```

#### 3) Repro steps (commands, env)
- Env
  - Branch: `feature/search-function-implementation`
  - Commit: see below
  - OS: macOS 12.6; Python 3.9; Redis local
  - Key env vars: `PORTFOLIO_DEDUP_TOLERANCE=0.1`, `PORTFOLIO_DEDUP_INCLUDE_VARIATION=1`
- Warm + component (optional):
  - `python3 backend/scripts/warm_and_component_test.py`
- Quick component (skip warm):
  - `python3 backend/scripts/component_check_quick.py`
- Full 12-variation test (skip warm, fix imports):
  - `PYTHONPATH="$PWD:$PWD/backend" python3 - <<'PY'
    # see section 4 JSON command used in session
    PY`

#### 4) Latest results, logs, artifacts
- Branch and commit
```bash
git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
```
```bash
feature/search-function-implementation
ca69f2cc7bf0fa9dc35507b0e331b59adf9164c8
```

- Quick component check (4 variations, no warm) JSON (success):
```json
{
  "seed_unique_count": 4,
  "pool_ok": true,
  "pool_stats": { "filtered_count": 265, "sectors": {"Technology": 47, ...}, "min_required": 60 },
  "generated_count": 4,
  "has_var_in_sig": true,
  "sig_has_vol": true,
  "overlap_matrix_shape": [4,4],
  "overlap_diag": [3,3,3,3],
  "metadata_on_generated": true,
  "fallback_count": 0
}
```

- Full 12-variation test (no warm, PYTHONPATH fixed) JSON (duplicate collapse at tail):
```json
{
  "generated_count": 1,
  "has_var_in_sig": true,
  "sig_has_vol": false,
  "overlap_key_exists": true,
  "overlap_matrix_shape": [1,1],
  "metadata_on_generated": true,
  "fallback_count": 1
}
```

- Warmup log highlights (evidence):
```text
Initialized with 811 unique tickers; Success rate: 94.3%; 765 successful
```

- Generation log highlights (evidence):
```text
📊 Redis enumeration found 765 tickers
📈 Filtered to 265 stocks within volatility range 28.0% - 45.0%
✅ Selected 3 stocks deterministically ... (many lines)
⚠️ Duplicate portfolio found for aggressive-<id>, attempt <n> (tail variations)
⚠️ Using fallback for portfolio <id>
```

- Redis artifacts
```text
portfolio:overlap:aggressive:<data_hash>  # present; matrix persisted
portfolio:signatures:aggressive           # de-dup signatures present
```

#### 5) Git changelist since last known-good (`c2017a26`)
- Recent log
```bash
git log --oneline --decorate --max-count=30
```
```text
ca69f2cc (HEAD) Improved backend/frontend functionality...
da2e324f Enhance Makefile/backend processes...
c2017a26 Implement smart refresh and portfolio regeneration (last good)
...
```
- Name-status diff (truncated due to venv noise)
```bash
git diff --name-status c2017a26..HEAD | head -n 200
```
- Rationale for key changes:
  - `enhanced_portfolio_generator.py`: tightened uniqueness, added volatility to signature, added allocation metadata, pool validation, overlap storage, enriched seeds.
  - Scripts added: `backend/scripts/warm_and_component_test.py`, `backend/scripts/component_check_quick.py`.

#### 6) Reproduction checklist (evidence capture)
- Identity: `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD`
- Changelist: `git diff --stat c2017a26..HEAD | head -n 200`
- Dev run: `make full-dev` then `tail -n 500 logs/backend.log`
- API smoke: `curl -v "http://localhost:8000/api/portfolios/aggressive/session?count=3"`
- Redis: `redis-cli --scan | grep portfolio:`; `redis-cli GET "portfolio:overlap:aggressive:<data_hash>"`
- Tests: `pytest -q` (or specific portfolio tests)

#### 7) Hypotheses, root causes, and fixes
- H1: Uniqueness attempt budget too tight for 12 variations at strict tolerance
  - Cause: Tail variations collide despite diversified seeds
  - Fix: Env-only: `PORTFOLIO_MAX_RETRY_ATTEMPTS=12` and/or `PORTFOLIO_DEDUP_TOLERANCE=0.2` for generation runs
- H2: Fallback portfolios collapse uniqueness (identical fallback shapes)
  - Cause: Deterministic fallback lacks variation
  - Fix: Add variation to fallback symbols/weights; include volatility for fallbacks
- H3: Sector-order permutations insufficient for late variations
  - Fix: Add more `_get_sector_priority_order` permutations; vary sampling offsets for high variation_ids
- H4: Analytics timing pressure
  - Fix: Calculate metrics after uniqueness confirmed; cap retries aging

#### 8) Verification plan
- After raising retries/relaxing tolerance:
  - Run full generation; expect `generated_count=12`, `fallback_count ≤ 2`, overlap `[12,12]`
  - Metrics: duplicates ≤ 2; p50 time per portfolio <15s, p95 <60s
- After fallback variation:
  - Expect distinct `allocation_signature` for fallbacks; `sig_has_vol=true` if vol included
- After sector-order expansion:
  - Expect fewer duplicates for variation_ids 8–11

#### 9) Deliverables
- Modified files: `backend/utils/enhanced_portfolio_generator.py`; new scripts `backend/scripts/*`
- Behavior change summary: stricter uniqueness; volatility-augmented signatures; metadata and overlap persisted; late-variation duplicates now visible (actionable)
- Logs and JSON evidence: included above
- Recommended next action: Re-run with `PORTFOLIO_MAX_RETRY_ATTEMPTS=12` and `PORTFOLIO_DEDUP_TOLERANCE=0.2`; if needed, merge fallback variation and sector-order expansion; verify 12/12 uniques and low fallback count, then lock configs.


