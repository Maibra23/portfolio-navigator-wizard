# Pure Strategy Portfolios - Technical Reference

This document provides a comprehensive technical reference for the Pure Strategy Portfolios feature, including architecture, implementation details, strengths, limitations, and improvement suggestions.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Files](#key-files)
4. [Implementation Details](#implementation-details)
5. [Strengths](#strengths)
6. [Limitations](#limitations)
7. [Improvement Suggestions](#improvement-suggestions)
8. [API Endpoints](#api-endpoints)
9. [Configuration](#configuration)

---

## Overview

The Pure Strategy Portfolios feature generates strategy-specific portfolios with two variants:

| Variant | Description | Use Case |
|---------|-------------|----------|
| **Pure** | Unconstrained portfolios focused solely on the strategy | Educational - shows "textbook ideal" |
| **Personalized** | Risk-profile-adjusted portfolios | Practical - real-world application |

### Strategies Supported

| Strategy | Focus | Allocation Method |
|----------|-------|-------------------|
| **Diversification** | Low correlation, balanced sector exposure | Sector-balanced (equal weight per sector) |
| **Risk** | Low volatility, defensive positioning | Inverse-volatility weighting |
| **Return** | High expected return, growth focus | Return-proportional weighting |

### Portfolio Generation Scale

- **3 strategies** × **6 portfolios per strategy** × **(1 pure + 5 risk profiles)** = **108 total portfolios**
- All portfolios are pre-generated and cached in Redis with 7-day TTL

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (StockSelection.tsx)               │
│  - Strategy tabs (diversification, risk, return)                │
│  - Pure vs Personalized comparison display                      │
│  - Generation limit tracking (max 2 per strategy)               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (portfolio.py)                     │
│  Endpoints:                                                     │
│  - POST /strategy-portfolios/generate                           │
│  - GET  /strategy-portfolios/pure                               │
│  - POST /strategy-portfolios/pre-generate (admin)               │
│  - GET  /strategy-portfolios/cache-status                       │
│  - POST /strategy-portfolios/clear-cache (admin)                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              StrategyPortfolioOptimizer                         │
│  (strategy_portfolio_optimizer.py)                              │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ Pure Generation  │    │ Personalized Gen │                  │
│  │ (unconstrained)  │    │ (risk-adjusted)  │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌──────────────────────────────────────────┐                  │
│  │         Stock Selection Pipeline         │                  │
│  │  1. Get available stocks                 │                  │
│  │  2. Filter negative returns (STRICT)     │                  │
│  │  3. Apply strategy-specific filtering    │                  │
│  │  4. Create strategy allocations          │                  │
│  │  5. Calculate portfolio metrics          │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redis Cache Layer                            │
│  Keys:                                                          │
│  - strategy_portfolios:pure:{strategy}                          │
│  - strategy_portfolios:personalized:{strategy}:{risk_profile}   │
│  TTL: 7 days                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/utils/strategy_portfolio_optimizer.py` | Core optimizer class, stock selection, allocation algorithms |
| `backend/routers/portfolio.py` | API endpoints for strategy portfolios |
| `backend/utils/redis_portfolio_manager.py` | Redis storage/retrieval, validation logic |
| `backend/utils/portfolio_stock_selector.py` | Stock selection, correlation analysis |
| `backend/utils/port_analytics.py` | Portfolio metrics calculation |
| `backend/scripts/regenerate_strategy_portfolios.py` | CLI for regenerating all portfolios |
| `frontend/src/components/wizard/StockSelection.tsx` | UI for strategy portfolio display |

---

## Implementation Details

### Stock Selection Pipeline

```python
# Three-stage filtering (strategy_portfolio_optimizer.py:191-239)
def _select_stocks_for_strategy_pure(strategy, portfolio_id):
    1. available_stocks = _get_available_stocks()           # Get all stocks
    2. available_stocks = _filter_negative_returns(stocks)  # STRICT: No negative returns
    3. return _filter_for_{strategy}_pure(stocks)           # Strategy-specific filtering
```

### Strategy-Specific Filtering

**Diversification (Pure):**
- Filter volatility ≤ 0.8
- Select stocks from maximum number of sectors
- Sector-balanced selection

**Risk (Pure):**
- Filter to lowest 30% volatility (quantile)
- Prioritize defensive sectors: utilities, consumer_staples, healthcare, real_estate
- Sort by defensive_score DESC, volatility ASC

**Return (Pure):**
- Filter to top 40% expected return (quantile 0.6)
- Prioritize growth sectors: technology, healthcare, consumer_discretionary, communication
- Sort by growth_score DESC, expected_return DESC

### Allocation Algorithms

```python
# strategy_portfolio_optimizer.py:486-599

# Diversification: Sector-balanced
sector_weight = 1.0 / num_sectors
stock_weight = sector_weight / stocks_in_sector

# Risk: Inverse-volatility weighting
inverse_vol = 1.0 / max(stock.volatility, 0.01)
weight = inverse_vol / total_inverse_vol

# Return: Return-proportional weighting
weight = stock.expected_return / total_expected_return
```

### Duplicate Prevention

```python
# strategy_portfolio_optimizer.py:102, 119-122
used_compositions = set()
comp = tuple(sorted(a.get('symbol') for a in allocations))
if comp not in used_compositions and len(comp) >= 2:
    used_compositions.add(comp)
```

### Deterministic Variety

```python
# strategy_portfolio_optimizer.py:109, 159
seed = _generate_strategy_seed(strategy, portfolio_id, is_pure, risk_profile)
random.seed(seed)
# Same inputs → same portfolios (reproducibility)
# Different portfolio_id → different but stable portfolios
```

---

## Strengths

### 1. Robust Negative Return Filtering
Multiple checkpoints prevent negative-return stocks from appearing:
- `_filter_negative_returns()` at line 391-411
- Secondary check in `_filter_for_return_pure()` at lines 286-291
- Tertiary check in `_filter_for_return_personalized()` at lines 361-366

### 2. ETF/Unknown Sector Filtering
```python
# Line 118: Defensive filtering
allocations = [a for a in allocations if a.get('sector') not in (None, 'Unknown')]
```

### 3. Comprehensive Risk Profile Constraints
```python
# Lines 48-54
RISK_PROFILE_CONSTRAINTS = {
    'very-conservative': {'max_volatility': 0.22, 'max_single_stock_weight': 0.30, 'min_sectors': 4},
    'conservative':      {'max_volatility': 0.26, 'max_single_stock_weight': 0.35, 'min_sectors': 4},
    'moderate':          {'max_volatility': 0.32, 'max_single_stock_weight': 0.40, 'min_sectors': 3},
    'aggressive':        {'max_volatility': 0.42, 'max_single_stock_weight': 0.45, 'min_sectors': 3},
    'very-aggressive':   {'max_volatility': 1.0,  'max_single_stock_weight': 0.50, 'min_sectors': 3}
}
```

### 4. Stock Pool Caching
```python
# Line 61: 1-hour TTL for stock pool
self._cache_ttl_seconds = 3600
```

### 5. Pre-Generation Support
All 108 portfolios can be pre-generated via admin endpoint, ensuring instant responses for users.

### 6. Allocation Validation
```python
# Line 525: Validates allocations sum to 1.0 and respect constraints
if not self._validate_allocations(allocations, risk_profile):
    return self._create_equal_allocations(normalized_stocks)  # Fallback
```

---

## Limitations

### 1. Hardcoded Strategy Configurations
```python
# Lines 41-45: Static strategy definitions
self.STRATEGIES = {
    'diversification': {...},
    'risk': {...},
    'return': {...}
}
```
**Impact:** Adding new strategies requires code changes.

### 2. Fixed Portfolio Count
```python
# Line 56
PORTFOLIOS_PER_STRATEGY = 6
```
**Impact:** Not configurable at runtime.

### 3. Basic Sector Categorization
```python
# Lines 267-269, 297-299
defensive_sectors = ['utilities', 'consumer_staples', 'healthcare', 'real_estate']
growth_sectors = ['technology', 'healthcare', 'consumer_discretionary', 'communication']
```
**Impact:** Case-sensitive string matching; sector names must match exactly.

### 4. Missing Correlation-Based Selection for Pure Portfolios
The `portfolio_stock_selector.py` has sophisticated correlation-based selection via `least_correlation_portfolio`, but Pure strategy portfolios use simpler sector-based selection.

### 5. Fixed Quantile Thresholds
```python
# Line 294
return_threshold = df['expected_return'].quantile(0.6)
# Line 264
volatility_threshold = df['volatility'].quantile(0.3)
```
**Impact:** No dynamic adjustment based on market conditions.

---

## Improvement Suggestions

### Priority 1: Add Return Cap to Pure Strategy Portfolios
```python
# In _filter_for_return_pure, add after line 295:
MAX_PURE_RETURN_CAP = 0.90  # 90% annual return cap
if 'expected_return' in df.columns:
    df = df[df['expected_return'] <= MAX_PURE_RETURN_CAP]
```
**Rationale:** Prevents showing unrealistically high return expectations.

### Priority 2: Configuration Externalization
```python
# strategy_config.py
STRATEGY_SETTINGS = {
    'portfolios_per_strategy': int(os.getenv('STRATEGY_PORTFOLIOS_COUNT', 6)),
    'defensive_sectors': os.getenv('DEFENSIVE_SECTORS', 'utilities,consumer_staples,healthcare,real_estate').split(','),
    'growth_sectors': os.getenv('GROWTH_SECTORS', 'technology,healthcare,consumer_discretionary,communication').split(','),
}
```
**Rationale:** Enables runtime configuration without code changes.

### Priority 3: Leverage Correlation-Based Selection
Integrate the existing `least_correlation_portfolio` algorithm from `portfolio_stock_selector.py` for pure portfolios to create truly optimal diversification.

### Priority 4: Add Portfolio Quality Metrics Logging
```python
# After generating each portfolio:
logger.info(f"Portfolio quality - Sharpe: {metrics.get('sharpe_ratio'):.2f}, "
            f"Diversification: {metrics.get('diversification_score'):.2f}")
```
**Rationale:** Helps monitor portfolio generation quality in production.

### Priority 5: Dynamic Quantile Adjustment
```python
# Adjust thresholds based on market conditions:
market_volatility = df['volatility'].median()
if market_volatility > 0.35:  # High volatility market
    volatility_threshold = df['volatility'].quantile(0.5)  # More lenient
else:
    volatility_threshold = df['volatility'].quantile(0.3)  # Standard
```
**Rationale:** Adapts to varying market conditions.

---

## API Endpoints

### Generate Strategy Portfolios
```http
POST /api/v1/portfolio/strategy-portfolios/generate
Content-Type: application/json

{
  "strategy": "diversification",
  "risk_profile": "moderate"
}
```
**Response:** List of strategy portfolios (mix of pure and personalized)

### Get Pure Strategy Portfolios
```http
GET /api/v1/portfolio/strategy-portfolios/pure?strategy=diversification
```
**Response:** Pure strategy portfolios only

### Pre-Generate All (Admin)
```http
POST /api/v1/portfolio/strategy-portfolios/pre-generate
X-Admin-API-Key: <ADMIN_API_KEY>
```
**Response:** Generation summary for all 108 portfolios

### Cache Status
```http
GET /api/v1/portfolio/strategy-portfolios/cache-status
```
**Response:** Status of all cached strategy portfolios

### Clear Cache (Admin)
```http
POST /api/v1/portfolio/strategy-portfolios/clear-cache
X-Admin-API-Key: <ADMIN_API_KEY>
```
**Response:** Confirmation of cache clearing

---

## Configuration

### Risk Profile Constraints

| Profile | Max Volatility | Max Single Stock | Min Sectors |
|---------|----------------|------------------|-------------|
| Very Conservative | 22% | 30% | 4 |
| Conservative | 26% | 35% | 4 |
| Moderate | 32% | 40% | 3 |
| Aggressive | 42% | 45% | 3 |
| Very Aggressive | 100% | 50% | 3 |

### Cache Settings

| Setting | Value |
|---------|-------|
| Portfolio TTL | 7 days |
| Stock Pool Cache TTL | 1 hour |
| Portfolios per Strategy | 6 |

### Sector Classifications

**Defensive Sectors:**
- Utilities
- Consumer Staples
- Healthcare
- Real Estate

**Growth Sectors:**
- Technology
- Healthcare
- Consumer Discretionary
- Communication

---

## Assessment Summary

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Value** | ⭐⭐⭐⭐ | High educational and practical value |
| **Code Quality** | ⭐⭐⭐⭐ | Well-structured, defensive programming |
| **Maintainability** | ⭐⭐⭐ | Some hardcoding, but readable |
| **Performance** | ⭐⭐⭐⭐ | Good caching strategy |
| **Test Coverage** | ⭐⭐⭐ | Verification script exists |

**Overall Status: Production Ready** ✅
