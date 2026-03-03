# Backend Utils Reference Guide

Complete documentation of all utility modules in `backend/utils/`.

---

## Table of Contents

1. [Core Portfolio Systems](#core-portfolio-systems)
2. [Data Services](#data-services)
3. [Redis Management](#redis-management)
4. [Export & Reporting](#export--reporting)
5. [Financial Calculations](#financial-calculations)
6. [Configuration & Utilities](#configuration--utilities)

---

## Core Portfolio Systems

### 1. portfolio_mvo_optimizer.py

**Purpose:** Mean-variance optimization using PyPortfolioOpt.

**Main Class:** `PortfolioMVOptimizer`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `optimize_portfolio()` | Optimize portfolio weights for max Sharpe, min variance, or target return/risk |
| `generate_efficient_frontier()` | Generate points along the efficient frontier |
| `generate_inefficient_frontier()` | Generate points below the efficient frontier |
| `generate_random_portfolios()` | Generate random portfolio combinations for visualization |
| `calculate_portfolio_metrics()` | Calculate return, risk, Sharpe for given weights |
| `calculate_capital_market_line()` | Calculate the tangent line from risk-free rate |

**Inputs:**
- `tickers`: List of stock symbols
- `optimization_type`: 'max_sharpe', 'min_variance', 'target_return', 'target_risk'
- `constraints`: Optional weight bounds

**Outputs:**
- Optimal weights dictionary
- Expected return (decimal)
- Risk/volatility (decimal)
- Sharpe ratio

**Configuration:**
```python
risk_free_rate = 0.038
MAX_REALISTIC_RETURN = 0.50
MAX_REALISTIC_SHARPE = 2.5
```

**Dependencies:** pypfopt, numpy, pandas, scipy, risk_profile_config

---

### 2. port_analytics.py

**Purpose:** Comprehensive portfolio analytics using QuantStats and PyPortfolioOpt.

**Main Class:** `PortfolioAnalytics`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `calculate_asset_metrics()` | Calculate metrics for individual assets |
| `two_asset_analysis()` | Analyze two-asset portfolio combinations |
| `generate_risk_portfolios()` | Generate portfolios across risk spectrum |
| `calculate_portfolio_metrics()` | Full portfolio metrics calculation |
| `simple_range_estimates()` | Quick return/risk estimates |
| `get_efficient_frontier_points()` | Generate frontier for visualization |

**Inputs:**
- Price series (pandas DataFrame/Series)
- Portfolio weights
- Ticker lists
- Risk profile string

**Outputs:**
- Return, risk, Sharpe ratio
- Maximum drawdown
- Efficient frontier points
- Risk-adjusted metrics

**Configuration:**
```python
risk_free_rate = 0.038
```

**Dependencies:** quantstats, pypfopt, numpy, pandas

---

### 3. enhanced_portfolio_generator.py

**Purpose:** Generates 12 compliant portfolios per risk profile and stores them in Redis.

**Main Class:** `EnhancedPortfolioGenerator`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `generate_portfolio_bucket()` | Generate 12 portfolios for a risk profile |
| `set_diversification_strategy()` | Configure diversification approach |
| `_validate_portfolio_compliance()` | Check return/risk bounds |
| `_store_to_redis()` | Save portfolios to Redis |

**Inputs:**
- Data service instance
- PortfolioAnalytics instance
- Risk profile string

**Outputs:**
- List of 12 portfolios with:
  - Name and description
  - Ticker allocations
  - Expected return, risk, Sharpe
  - Diversification score

**Configuration:**
```python
PORTFOLIOS_PER_PROFILE = 12
PORTFOLIO_TTL_DAYS = 7
MAX_QUALITY_RETRIES = 10
```

**Dependencies:** portfolio_stock_selector, enhanced_stock_selector, port_analytics, enhanced_portfolio_config

---

### 4. portfolio_stock_selector.py

**Purpose:** Select stocks by sector diversification, volatility, and risk profile.

**Main Class:** `PortfolioStockSelector`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `select_stocks_for_risk_profile()` | Random selection with sector balance |
| `select_stocks_for_risk_profile_deterministic()` | Deterministic selection for consistency |
| `_get_available_stocks_with_metrics()` | Fetch eligible stocks from cache |
| `_filter_stocks_by_volatility()` | Apply risk profile volatility bounds |
| `_select_diversified_stocks()` | Ensure sector diversification |

**Inputs:**
- Risk profile string
- Variation seed (for deterministic selection)
- Optional pre-fetched stock data

**Outputs:**
- List of allocations: `[{symbol, allocation, sector}, ...]`

**Configuration:**
```python
SECTOR_CATEGORIES = [...]
RISK_PROFILE_VOLATILITY = {...}
STOCK_COUNT_RANGES = {...}
PREFERRED_SECTORS = {...}
```

**Dependencies:** redis_first_data_service, volatility_weighted_sector, risk_profile_config

---

### 5. enhanced_stock_selector.py

**Purpose:** Extended stock selector with return and diversification targets.

**Main Class:** `EnhancedStockSelector`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `select_stocks_for_portfolio()` | Enhanced selection with targets |
| `_enhanced_stock_filtering()` | Filter by return potential |
| `_create_dynamic_allocations()` | Dynamic weight assignment |
| `_validate_selected_stocks()` | Validate against targets |
| `_prioritize_stocks_by_return_potential()` | Sort by expected return |

**Inputs:**
- Risk profile
- Portfolio size
- Available stocks
- Return/diversification targets

**Outputs:**
- Stock allocations optimized for targets

**Configuration:**
```python
SECTOR_RETURN_POTENTIAL = {...}
PORTFOLIO_SIZE = {...}
FALLBACK_TICKERS = [...]
```

**Dependencies:** portfolio_stock_selector, dynamic_weighting_system, risk_profile_config

---

### 6. strategy_portfolio_optimizer.py

**Purpose:** Generate strategy-specific portfolios (diversification, risk, return focus).

**Main Class:** `StrategyPortfolioOptimizer`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `generate_strategy_portfolio_buckets()` | Generate all strategy portfolios |
| `_generate_pure_strategy_portfolios()` | Single-strategy focus |
| `_generate_personalized_strategy_portfolios()` | Risk-profile adjusted |
| `_select_stocks_for_strategy_pure()` | Pure strategy stock selection |
| `get_cache_status_detailed()` | Check strategy cache status |

**Inputs:**
- Strategy name: 'diversification', 'risk', 'return'
- Risk profiles
- Data service and Redis manager

**Outputs:**
- Pure portfolios (strategy-focused)
- Personalized portfolios (risk-adjusted)

**Configuration:**
```python
STRATEGIES = ['diversification', 'risk', 'return']
PORTFOLIOS_PER_STRATEGY = 6
RISK_PROFILE_CONSTRAINTS = {...}
```

**Dependencies:** portfolio_stock_selector, port_analytics, redis_portfolio_manager

---

### 7. conservative_portfolio_generator.py

**Purpose:** Conservative portfolio generation with asymmetric return tolerance for aggressive profiles.

**Main Class:** `ConservativePortfolioGenerator`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `should_use_conservative()` | Check if profile needs conservative approach |
| `apply_conservative_config()` | Apply conservative parameters |
| `restore_original_config()` | Restore default parameters |
| `assess_portfolio_quality_asymmetric()` | Quality check with asymmetric tolerance |

**Inputs:**
- Risk profile
- Portfolio metrics
- Return target

**Outputs:**
- Quality assessment: ACCEPT, REJECT, ACCEPTABLE, COMPLIANT

**Configuration:**
```python
CONSERVATIVE_CONFIG = {
    'aggressive': {...},
    'very-aggressive': {...}
}
```

**Dependencies:** risk_profile_config

---

### 8. dynamic_weighting_system.py

**Purpose:** Multi-objective portfolio weighting with return and risk targets.

**Main Class:** `DynamicWeightingSystem`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `calculate_optimal_weights()` | Optimize weights for targets |
| `_estimate_correlation_matrix()` | Estimate correlations from volatility |
| `validate_weights()` | Validate sum and bounds |

**Inputs:**
- Stock dictionaries with return, volatility, sector
- Target return
- Optional risk range

**Outputs:**
- Optimal weights dictionary
- Optimization result details

**Configuration:**
```python
min_weight = 0.05  # 5%
max_weight = 0.50  # 50%
return_tolerance = 0.07  # 7%
```

**Dependencies:** numpy, pandas, scipy.optimize

---

## Data Services

### 9. redis_first_data_service.py

**Purpose:** Redis-first data access with external fallback.

**Main Class:** `RedisFirstDataService`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get_monthly_data()` | Get monthly price data for ticker |
| `get_ticker_info()` | Get ticker metadata |
| `list_cached_tickers()` | List all cached ticker keys |
| `jittered_ttl()` | Apply random jitter to TTL |
| `_configure_redis_memory()` | Set Redis memory policy |

**Inputs:**
- Ticker symbol
- Optional force_refresh flag
- Redis URL

**Outputs:**
- Price data (DataFrame or dict)
- Ticker info dictionary
- Cached ticker list

**Configuration:**
```python
MAX_MEMORY = '48mb'
EVICTION_POLICY = 'volatile-lru'
TTL_JITTER_PERCENT = 15
CACHE_TTL_DAYS = 28
```

**Dependencies:** redis, pandas, timestamp_utils, EnhancedDataFetcher (lazy import)

---

### 10. enhanced_data_fetcher.py

**Purpose:** Fetch and cache price and sector data from Yahoo Finance.

**Main Class:** `EnhancedDataFetcher`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `fetch_prices()` | Fetch historical prices |
| `fetch_sector_info()` | Fetch sector/industry data |
| `validate_ticker()` | Check if ticker is valid |
| `batch_fetch()` | Fetch multiple tickers |
| `_handle_rate_limits()` | Manage API quotas |

**Inputs:**
- Ticker list
- Date range
- Configuration flags

**Outputs:**
- Price dictionaries
- Sector information
- Validation results

**Configuration:**
```python
BATCH_SIZE = 20
MAX_WORKERS = 1
CACHE_TTL_DAYS = 90
LOOKBACK_YEARS = 20
```

**Dependencies:** pandas, yfinance, yahooquery, redis, timestamp_utils, fx_fetcher

---

### 11. fx_fetcher.py

**Purpose:** Fetch and cache FX rates for USD normalization.

**Main Class:** `FXRateFetcher`

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get_fx_rates()` | Get FX rates for currency |
| `convert_series()` | Convert price series to USD |
| `_forward_fill_rates()` | Handle missing rate dates |
| `_load_from_cache()` | Load cached rates |
| `_save_to_cache()` | Cache new rates |

**Inputs:**
- Currency code (EUR, GBP, SEK, etc.)
- Date range
- Optional Redis client

**Outputs:**
- Dictionary of date->rate
- Converted pandas Series

**Configuration:**
```python
CURRENCY_TO_YAHOO_TICKER = {
    'EUR': 'EURUSD=X',
    'GBP': 'GBPUSD=X',
    'SEK': 'SEKUSD=X',
    ...
}
FX_CACHE_TTL_SECONDS = 86400
```

**Dependencies:** pandas, yahooquery

---

### 12. timestamp_utils.py

**Purpose:** Timestamp normalization and ticker format handling.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `normalize_timestamp()` | Convert to ISO format |
| `detect_timestamp_format()` | Identify timestamp type |
| `validate_timestamp_range()` | Check valid date range |
| `get_date_range_info()` | Get range metadata |
| `normalize_ticker_format()` | Normalize ticker symbols |
| `detect_ticker_exchange()` | Identify exchange from suffix |
| `get_ticker_country_exchange_currency()` | Full ticker metadata |

**Inputs:**
- Timestamp in various formats
- Ticker strings with suffixes

**Outputs:**
- ISO formatted timestamps
- Normalized ticker symbols
- Exchange/country/currency info

**Configuration:**
```python
TICKER_FORMAT_MAP = {...}
SUFFIX_COUNTRY_EXCHANGE_CURRENCY = {
    '.L': ('UK', 'LSE', 'GBP'),
    '.SW': ('Switzerland', 'SIX', 'CHF'),
    ...
}
```

**Dependencies:** pandas, numpy, datetime, re

---

## Redis Management

### 13. redis_config.py

**Purpose:** Redis TTL, jitter, and connection settings.

**Main Class:** `RedisConfig`

**Key Functions:**

| Function | Description |
|----------|-------------|
| `apply_jitter()` | Add random variation to TTL |
| `get_ttl_for_data_type()` | Get configured TTL |
| `set_with_jittered_ttl()` | Store with jittered expiry |
| `get_redis_connection_pool_config()` | Get pool settings |
| `get_redis_config_summary()` | Get config overview |

**Inputs:**
- TTL in seconds
- Data type string
- Optional jitter percentage

**Outputs:**
- Jittered TTL value
- Connection configuration dict

**Configuration:**
```python
TTL_PRICES = 86400      # 1 day
TTL_SECTORS = 604800    # 7 days
TTL_PORTFOLIOS = 259200 # 3 days
DEFAULT_JITTER = 0.10   # ±10%
```

**Dependencies:** random, json, logging

---

### 14. redis_portfolio_manager.py

**Purpose:** Store and retrieve portfolio buckets in Redis.

**Main Class:** `RedisPortfolioManager`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `store_portfolio_bucket()` | Save portfolios to Redis |
| `get_portfolio_bucket()` | Retrieve portfolios |
| `clear_portfolio_bucket()` | Delete portfolio cache |
| `get_all_portfolio_buckets_status()` | Check all buckets |
| `get_portfolio_ttl_info()` | Get TTL status |
| `_validate_portfolio_compliance()` | Check return/risk bounds |

**Inputs:**
- Risk profile string
- Portfolio list

**Outputs:**
- Stored confirmation
- Retrieved portfolio list
- Status dictionary

**Configuration:**
```python
PORTFOLIO_TTL_DAYS = 7
PORTFOLIOS_PER_PROFILE = 12
KEY_PREFIX = 'portfolio_bucket:'
```

**Dependencies:** redis, risk_profile_config, conservative_portfolio_generator

---

### 15. redis_ttl_monitor.py

**Purpose:** Monitor Redis TTL and send alerts when data approaches expiry.

**Main Class:** `RedisTTLMonitor`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `check_ttl_status()` | Scan and categorize keys by TTL |
| `get_expiring_tickers()` | Get tickers near expiry |
| `generate_ttl_report()` | Generate human-readable report |
| `refresh_expiring_tickers()` | Refresh expiring data |
| `get_detailed_redis_stats()` | Get key counts and memory |
| `email_notification_callback()` | Send TTL alerts via email |

**Inputs:**
- Redis client
- Optional notification callback
- Threshold days

**Outputs:**
- TTL status dictionary
- Report string
- Refresh results

**Configuration:**
```python
CRITICAL_THRESHOLD = 86400    # 1 day
WARNING_THRESHOLD = 604800    # 7 days
INFO_THRESHOLD = 1209600      # 14 days
```

**Dependencies:** redis, email_notifier

---

### 16. redis_metrics.py

**Purpose:** Collect Redis metrics for Prometheus.

**Main Class:** `RedisMetricsCollector`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `update_metrics()` | Update all Prometheus gauges |
| `_update_key_counts()` | Count keys by type |
| `_update_cache_hit_rate()` | Calculate hit rate |
| `get_redis_info_summary()` | Get info summary |

**Inputs:**
- Redis client

**Outputs:**
- Prometheus gauges updated
- Summary dictionary

**Metrics:**
- `redis_memory_used_bytes`
- `redis_connected_clients`
- `redis_evicted_keys`
- `redis_keys_by_type`
- `redis_cache_hit_rate`

**Dependencies:** redis, shared.metrics (Prometheus)

---

### 17. portfolio_auto_regeneration_service.py

**Purpose:** Manually triggered service to regenerate portfolios.

**Main Class:** `PortfolioAutoRegenerationService`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `trigger_regeneration()` | Start regeneration for profile |
| `force_regeneration()` | Force immediate regeneration |
| `emergency_regeneration()` | Emergency regeneration with alerts |
| `get_service_status()` | Get service state |
| `get_regeneration_history()` | Get past regenerations |

**Inputs:**
- Data service
- Enhanced generator
- Redis portfolio manager
- Optional risk profile

**Outputs:**
- Success/failure status
- Statistics
- History log

**Configuration:**
```python
REGENERATION_INTERVAL_DAYS = 7
MAX_RETRY_ATTEMPTS = 3
```

**Dependencies:** redis_portfolio_manager, volatility_weighted_sector

---

## Export & Reporting

### 18. pdf_report_generator.py

**Purpose:** Generate academic-style PDF reports.

**Main Class:** `PDFReportGenerator`

**Key Sections:**
1. Title Page
2. Table of Contents
3. Disclaimer
4. Executive Summary
5. Portfolio Holdings
6. Risk Analysis
7. Tax Analysis
8. Stress Test Results
9. Methodology
10. Glossary

**Key Methods:**

| Method | Description |
|----------|-------------|
| `generate_report()` | Generate complete PDF |
| `_add_title_page()` | Create title page |
| `_add_holdings_table()` | Add portfolio table |
| `_add_pie_chart()` | Add allocation chart |
| `_add_stress_test_table()` | Add scenario results |

**Inputs:**
- Portfolio data
- Metrics dictionary
- Tax calculations
- Costs
- Stress test results
- Optimization results

**Outputs:**
- PDF bytes (BytesIO)

**Configuration:**
```python
PAGE_SIZE = A4
MARGINS = (72, 72, 72, 72)
CHART_COLORS = [...]
ALLOWED_STRESS_SCENARIOS = [...]
```

**Dependencies:** reportlab, matplotlib, five_year_projection

---

### 19. csv_export_generator.py

**Purpose:** Export portfolio and analysis data to CSV.

**Main Class:** `CSVExportGenerator`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `generate_portfolio_holdings_csv()` | Holdings export |
| `generate_tax_analysis_csv()` | Tax breakdown |
| `generate_transaction_costs_csv()` | Courtage costs |
| `generate_portfolio_metrics_csv()` | Performance metrics |
| `generate_stress_test_csv()` | Scenario results |
| `generate_optimization_comparison_csv()` | Triple optimization |
| `generate_monte_carlo_csv()` | Simulation results |
| `generate_five_year_projection_csv()` | Projections |
| `generate_methodology_csv()` | Methodology description |
| `generate_glossary_csv()` | Terms and definitions |

**Inputs:**
- Portfolios
- Tax/transaction data
- Metrics
- Stress results

**Outputs:**
- CSV strings

**Dependencies:** csv, io.StringIO, datetime

---

### 20. shareable_link_generator.py

**Purpose:** Shareable links for portfolio data with expiry and password protection.

**Main Class:** `ShareableLinkGenerator`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `generate_link()` | Create shareable link |
| `get_link_data()` | Retrieve link data |
| `validate_link()` | Validate link and password |
| `delete_link()` | Remove link |
| `get_link_info()` | Get link metadata |

**Inputs:**
- Portfolio dictionary
- Expiry days
- Optional password

**Outputs:**
- Link ID (UUID)
- Link data
- Validation result

**Configuration:**
```python
LINK_PREFIX = 'share:'
PASSWORD_PREFIX = 'share_pw:'
DEFAULT_EXPIRY_DAYS = 7
```

**Dependencies:** redis, argon2 (optional), hashlib, secrets, json

---

## Financial Calculations

### 21. swedish_tax_calculator.py

**Purpose:** Swedish tax calculations for ISK, KF, and AF accounts.

**Main Class:** `SwedishTaxCalculator`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `calculate_isk_tax_2025()` | ISK tax for 2025 |
| `calculate_isk_tax_2026()` | ISK tax for 2026 |
| `calculate_tax()` | Unified tax calculation |
| `calculate_tax_free_breakdown()` | Tax-free thresholds |

**Inputs:**
- Account type: 'ISK', 'KF', 'AF'
- Tax year: 2025 or 2026
- Capital underlag (ISK/KF)
- Realized gains, dividends (AF)

**Outputs:**
- Tax breakdown:
  - `annual_tax`
  - `effective_tax_rate`
  - `tax_free_amount`
  - `taxable_amount`

**Configuration:**
```python
# 2025
ISK_TAX_FREE_2025 = 150_000
ISK_SCHABLONRANTA_2025 = 0.0326

# 2026
ISK_TAX_FREE_2026 = 150_000
ISK_SCHABLONRANTA_2026 = 0.0308

# AF rates
CAPITAL_GAINS_RATE = 0.30
DIVIDEND_RATE = 0.30

PARAMETERS_AS_OF = "2025-01"
```

**Dependencies:** None

---

### 22. transaction_cost_calculator.py

**Purpose:** Avanza courtage calculations for Swedish trading.

**Main Class:** `AvanzaCourtageCalculator`

**Enum:** `CourtageClass`
- START, MINI, SMALL, MEDIUM, FAST_PRIS

**Key Methods:**

| Method | Description |
|----------|-------------|
| `calculate_courtage()` | Calculate single trade cost |
| `estimate_setup_cost()` | Initial portfolio cost |
| `estimate_rebalancing_cost()` | Periodic rebalancing cost |
| `estimate_total_costs()` | Total annual costs |
| `find_optimal_courtage_class()` | Recommend best class |

**Inputs:**
- Order value (SEK)
- Courtage class
- Portfolio positions
- Rebalancing frequency

**Outputs:**
- Cost breakdowns (SEK)

**Configuration:**
```python
COURTAGE_RULES = {
    'start': {'percentage': 0.0025, 'min': 1, 'max': None},
    'mini': {'percentage': 0.0015, 'min': 9, 'max': None},
    'small': {'percentage': 0.0006, 'min': 39, 'max': None},
    'medium': {'percentage': 0.0004, 'min': 69, 'max': None},
    'fastPris': {'percentage': 0, 'min': 99, 'max': 99}
}
PARAMETERS_AS_OF = "2025-01"
```

**Dependencies:** logging

---

### 23. five_year_projection.py

**Purpose:** Five-year portfolio projection with tax and costs.

**Main Function:** `run_five_year_projection()`

**Inputs:**
- `initial_capital`: Starting investment
- `weights`: Portfolio weights
- `expected_return`: Annual return
- `risk`: Volatility
- `account_type`: ISK, KF, AF
- `tax_year`: 2025 or 2026
- `courtage_class`: Avanza class
- `rebalancing_frequency`: annual, quarterly, etc.

**Outputs:**
- Dictionary with:
  - `years`: [0, 1, 2, 3, 4, 5]
  - `optimistic`: Values at 75th percentile
  - `base`: Values at 50th percentile
  - `pessimistic`: Values at 25th percentile

**Dependencies:** swedish_tax_calculator, transaction_cost_calculator

---

### 24. stress_test_analyzer.py

**Purpose:** Stress test portfolios against historical crises.

**Main Class:** `StressTestAnalyzer`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `filter_prices_by_date_range()` | Get prices for crisis period |
| `detect_peaks_and_troughs()` | Find local extremes |
| `run_scenario()` | Run single stress scenario |
| `run_all_scenarios()` | Run all 15 scenarios |
| `calculate_recovery_metrics()` | Compute recovery time/path |

**Scenarios:**
1. 2008 Financial Crisis
2. 2020 COVID-19 Crash
3. 2022 Inflation Shock
4. Tech Bubble (2000)
5. Flash Crash (2010)
6. European Debt Crisis
7. Oil Price Collapse
8. Trade War
9. Brexit
10. Rate Hike Cycle
11. Geopolitical Risk
12. Black Swan Event
13. Mild Recession
14. Sector Rotation
15. Liquidity Crisis

**Inputs:**
- Price dictionaries
- Date ranges
- Portfolio weights

**Outputs:**
- Crisis impact percentage
- Maximum drawdown
- Recovery days
- Trajectory data

**Dependencies:** pandas, numpy, redis_first_data_service

---

## Configuration & Utilities

### 25. risk_profile_config.py

**Purpose:** Single source of truth for risk profile parameters.

**Main Exports:**

| Export | Description |
|--------|-------------|
| `UNIFIED_RISK_PROFILE_CONFIG` | Complete config for all profiles |
| `RISK_PROFILE_VOLATILITY` | Volatility bounds |
| `RISK_PROFILE_RETURN_RANGES` | Return targets |

**Key Functions:**

| Function | Description |
|----------|-------------|
| `get_unified_config_for_profile()` | Get full config |
| `get_max_risk_for_profile()` | Get max allowed risk |
| `get_volatility_range_for_profile()` | Get volatility bounds |
| `get_return_range_for_profile()` | Get return targets |
| `get_quality_risk_range_for_profile()` | Get quality check bounds |
| `get_fallback_metrics_for_profile()` | Get default metrics |
| `validate_risk_profile()` | Check profile validity |

**Configuration:**
```python
UNIFIED_RISK_PROFILE_CONFIG = {
    'very-conservative': {
        'volatility_range': (0.05, 0.15),
        'return_target': (0.04, 0.12),
        'max_risk': 0.20,
        ...
    },
    'conservative': {...},
    'moderate': {...},
    'aggressive': {...},
    'very-aggressive': {...}
}
```

**Dependencies:** None

---

### 26. enhanced_portfolio_config.py

**Purpose:** Wraps risk profile config for enhanced portfolio generation.

**Main Class:** `EnhancedPortfolioConfig`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `get_return_target()` | Get target for portfolio index |
| `get_diversification_score()` | Get target diversification |
| `get_stock_count()` | Get number of stocks |
| `get_adaptive_return_target()` | Dynamic target based on context |
| `get_enhanced_targets()` | Get all targets as dict |

**Configuration:**
```python
ENHANCED_RETURN_RANGES = {...}
DIVERSIFICATION_VARIATION = {...}
STOCK_COUNT_RANGES = {...}
RETURN_TARGET_GRADATION = {...}
ENHANCED_QUALITY_CONTROL = {...}
```

**Dependencies:** risk_profile_config

---

### 27. volatility_weighted_sector.py

**Purpose:** Compute volatility-weighted sector weights.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `get_volatility_weighted_sector_weights()` | Calculate sector weights |
| `invalidate_volatility_sector_weights_cache()` | Clear cache (no-op) |

**Inputs:**
- Risk profile
- Stock list with volatility
- Minimum sectors

**Outputs:**
- Dictionary of sector -> weight (sum = 1.0)

**Dependencies:** None (pure logic)

---

### 28. diversification_experiments.py

**Purpose:** Diversification strategies for aggressive profiles.

**Main Class:** `Strategy5_ReturnTargetBasedDiversification`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `get_diversification_range()` | Get min/max diversification |
| `should_enforce_diversification()` | Check if enforcement needed |

**Configuration:**
```python
DIVERSIFICATION_STRATEGIES = {...}
DEFAULT_STRATEGY = 'strategy5_return_target_based'
```

**Dependencies:** risk_profile_config

---

### 29. email_notifier.py

**Purpose:** SMTP email notifications.

**Main Parts:**

| Component | Description |
|-----------|-------------|
| `NotificationMessage` | Dataclass for notification |
| `send_notification()` | Send email with throttling |

**NotificationMessage Fields:**
- `title`: Email subject
- `message`: Email body
- `severity`: INFO, WARNING, CRITICAL, SUCCESS
- `fields`: Optional additional data

**Inputs:**
- NotificationMessage instance
- Optional throttle_key
- Optional min_interval_seconds

**Configuration (Environment):**
```
TTL_EMAIL_NOTIFICATIONS=true
TTL_NOTIFICATION_EMAIL=recipient@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=sender@gmail.com
SMTP_PASSWORD=app_password
```

**Dependencies:** smtplib, email.mime

---

### 30. logging_utils.py

**Purpose:** Configure job loggers with file output.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `get_job_log_path()` | Get log file path |
| `get_job_logger()` | Get configured logger |

**Inputs:**
- Logger name
- Optional log file name

**Outputs:**
- Path object
- Logger instance

**Configuration:**
- Logs directory: `backend/logs/`
- Uses `FlushingFileHandler` for immediate writes

**Dependencies:** logging, sys, pathlib

---

### 31. anonymous_analytics.py

**Purpose:** Backend performance metrics for Prometheus.

**Main Class:** `BackendMetrics`

**Key Methods:**

| Method | Description |
|----------|-------------|
| `track_optimization()` | Track optimization runs |
| `track_search()` | Track ticker searches |
| `track_cache_hit()` | Track cache hits |
| `track_cache_miss()` | Track cache misses |

**Metrics:**
- `PORTFOLIO_OPTIMIZATIONS` (Counter)
- `PORTFOLIO_OPTIMIZATION_DURATION` (Histogram)
- `TICKER_SEARCHES` (Counter)
- `CACHE_HITS` (Counter)
- `CACHE_MISSES` (Counter)

**Dependencies:** shared.metrics (Prometheus)

---

## Quick Reference

### File by Purpose

| Category | Files |
|----------|-------|
| **Optimization** | portfolio_mvo_optimizer, port_analytics, dynamic_weighting_system |
| **Generation** | enhanced_portfolio_generator, portfolio_stock_selector, enhanced_stock_selector, strategy_portfolio_optimizer |
| **Data** | redis_first_data_service, enhanced_data_fetcher, fx_fetcher, timestamp_utils |
| **Redis** | redis_config, redis_portfolio_manager, redis_ttl_monitor, redis_metrics |
| **Export** | pdf_report_generator, csv_export_generator, shareable_link_generator |
| **Finance** | swedish_tax_calculator, transaction_cost_calculator, five_year_projection, stress_test_analyzer |
| **Config** | risk_profile_config, enhanced_portfolio_config |
| **Monitoring** | email_notifier, logging_utils, anonymous_analytics |

### Key Constants

| Constant | Value | File |
|----------|-------|------|
| Risk-free rate | 3.8% | portfolio_mvo_optimizer |
| Portfolio TTL | 7 days | redis_portfolio_manager |
| Portfolios per profile | 12 | enhanced_portfolio_generator |
| ISK tax-free (2026) | 150,000 SEK | swedish_tax_calculator |
| Cache TTL (prices) | 1 day | redis_config |

---

*Documentation generated on 2026-03-01*
