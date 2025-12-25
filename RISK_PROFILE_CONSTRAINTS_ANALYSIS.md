# Risk Profile Constraints Analysis - Complete Evaluation

## Executive Summary

**CRITICAL FINDING**: Risk profile constraints are **NOT consistent** across the project. There are **5 different constraint definitions** with significant variations that can cause:
- Portfolio generation inconsistencies
- Optimization failures
- Incorrect efficient frontier calculations
- Misleading chart visualizations
- User trust issues

---

## 1. Current Risk Profile Constraint Definitions

### Definition 1: MVO Optimizer (`portfolio_mvo_optimizer.py`)
**Location**: `_get_max_risk_for_profile()` method
**Purpose**: Maximum risk constraint for portfolio optimization

```python
risk_constraints = {
    'very-conservative': 0.08,    # 8%
    'conservative': 0.12,         # 12%
    'moderate': 0.16,             # 16%
    'aggressive': 0.22,            # 22%
    'very-aggressive': 0.28       # 28%
}
```

**Used in**: Portfolio optimization, efficient frontier generation, CML calculation

---

### Definition 2: Dual Optimization (`routers/portfolio.py`)
**Location**: `optimize_dual_portfolio()` function
**Purpose**: Filtering eligible tickers for best available portfolio

```python
risk_profile_max_risk = {
    'very-conservative': 0.08,    # 8%
    'conservative': 0.12,         # 12%
    'moderate': 0.16,             # 16%
    'aggressive': 0.22,            # 22%
    'very-aggressive': 0.28       # 28%
}
```

**Used in**: Dual optimization endpoint, eligible ticker filtering

---

### Definition 3: Stock Selector Volatility Ranges (`portfolio_stock_selector.py`)
**Location**: `RISK_PROFILE_VOLATILITY` class attribute
**Purpose**: Stock filtering by volatility range for portfolio generation

```python
RISK_PROFILE_VOLATILITY = {
    'very-conservative': (0.05, 0.18),    # 5-18% range
    'conservative': (0.15, 0.25),         # 15-25% range
    'moderate': (0.22, 0.32),             # 22-32% range
    'aggressive': (0.28, 0.45),           # 28-45% range
    'very-aggressive': (0.38, 1.00)       # 38-100% range
}
```

**Used in**: Stock selection for portfolio generation, pre-generated portfolios

---

### Definition 4: Strategy Portfolio Optimizer (`strategy_portfolio_optimizer.py`)
**Location**: `RISK_PROFILE_CONSTRAINTS` class attribute
**Purpose**: Strategy-specific portfolio generation constraints

```python
RISK_PROFILE_CONSTRAINTS = {
    'very-conservative': {'max_volatility': 0.22, 'max_single_stock_weight': 0.30, 'min_sectors': 4},
    'conservative': {'max_volatility': 0.26, 'max_single_stock_weight': 0.35, 'min_sectors': 4},
    'moderate': {'max_volatility': 0.32, 'max_single_stock_weight': 0.40, 'min_sectors': 3},
    'aggressive': {'max_volatility': 0.42, 'max_single_stock_weight': 0.45, 'min_sectors': 3},
    'very-aggressive': {'max_volatility': 1.0, 'max_single_stock_weight': 0.50, 'min_sectors': 3}
}
```

**Used in**: Strategy portfolio generation (diversification, risk, return strategies)

---

### Definition 5: Portfolio Analytics (`port_analytics.py`)
**Location**: `_filter_assets_by_risk_profile()` method
**Purpose**: Asset filtering for analytics

```python
risk_constraints = {
    'very-conservative': {'max_risk': 0.15, 'min_return': 0.05, 'max_return': 0.12},
    'conservative': {'max_risk': 0.20, 'min_return': 0.08, 'max_return': 0.15},
    'moderate': {'max_risk': 0.25, 'min_return': 0.10, 'max_return': 0.20},
    'aggressive': {'max_risk': 0.35, 'min_return': 0.15, 'max_return': 0.30},
    'very-aggressive': {'max_risk': 0.50, 'min_return': 0.20, 'max_return': 0.40}
}
```

**Used in**: Portfolio analytics, asset filtering

---

### Definition 6: Enhanced Portfolio Config (`enhanced_portfolio_config.py`)
**Location**: `ENHANCED_QUALITY_CONTROL` class attribute
**Purpose**: Quality control ranges for portfolio generation

```python
ENHANCED_QUALITY_CONTROL = {
    'very-conservative': {
        'return_range': (0.04, 0.14),
        'risk_range': (0.128, 0.179),    # 12.8-17.9%
    },
    'conservative': {
        'return_range': (0.12, 0.22),
        'risk_range': (0.151, 0.250),    # 15.1-25.0%
    },
    'moderate': {
        'return_range': (0.18, 0.32),
        'risk_range': (0.220, 0.320),    # 22.0-32.0%
    },
    'aggressive': {
        'return_range': (0.26, 0.52),
        'risk_range': (0.281, 0.449),    # 28.1-44.9%
    },
    'very-aggressive': {
        'return_range': (0.26, 0.65),
        'risk_range': (0.381, 0.990),    # 38.1-99.0%
    }
}
```

**Used in**: Enhanced portfolio generation quality checks

---

## 2. Constraint Comparison Matrix

| Risk Profile | MVO Optimizer | Dual Opt | Stock Selector (Max) | Strategy Opt (Max) | Analytics (Max) | Enhanced Config (Max) |
|--------------|---------------|----------|---------------------|-------------------|-----------------|---------------------|
| **very-conservative** | 0.08 (8%) | 0.08 (8%) | 0.18 (18%) | 0.22 (22%) | 0.15 (15%) | 0.179 (17.9%) |
| **conservative** | 0.12 (12%) | 0.12 (12%) | 0.25 (25%) | 0.26 (26%) | 0.20 (20%) | 0.250 (25.0%) |
| **moderate** | 0.16 (16%) | 0.16 (16%) | 0.32 (32%) | 0.32 (32%) | 0.25 (25%) | 0.320 (32.0%) |
| **aggressive** | 0.22 (22%) | 0.22 (22%) | 0.45 (45%) | 0.42 (42%) | 0.35 (35%) | 0.449 (44.9%) |
| **very-aggressive** | 0.28 (28%) | 0.28 (28%) | 1.00 (100%) | 1.00 (100%) | 0.50 (50%) | 0.990 (99.0%) |

### Key Observations:

1. **MVO Optimizer & Dual Optimization**: ✅ **CONSISTENT** (0.08, 0.12, 0.16, 0.22, 0.28)
2. **Stock Selector**: Uses **RANGES** not single values - max values are 2.25x higher than MVO
3. **Strategy Optimizer**: Max volatility is 2.75x higher than MVO for very-conservative
4. **Analytics**: Intermediate values between MVO and Stock Selector
5. **Enhanced Config**: Uses ranges similar to Stock Selector but slightly different

---

## 3. Impact Analysis - How Deviations Cause Harm

### 3.1 Portfolio Generation Impact

#### Problem: Stock Selection vs Optimization Mismatch

**Scenario**: User selects "very-conservative" profile

1. **Stock Selection Phase** (`portfolio_stock_selector.py`):
   - Allows stocks with volatility up to **18%** (0.18)
   - User sees portfolios with stocks that have 15-18% volatility
   - User selects a portfolio with 16% volatility stocks

2. **Optimization Phase** (`portfolio_mvo_optimizer.py`):
   - Applies maximum risk constraint of **8%** (0.08)
   - Optimization **FAILS** or produces suboptimal results
   - Portfolio with 16% volatility stocks cannot be optimized to 8% risk

**Result**: 
- ❌ Optimization fails or produces unrealistic results
- ❌ User confusion: "Why can't I optimize my selected portfolio?"
- ❌ Inconsistent user experience

#### Example Calculation:

**Portfolio with 3 stocks**:
- Stock A: 15% volatility, weight 33%
- Stock B: 16% volatility, weight 33%
- Stock C: 17% volatility, weight 34%

**Portfolio Risk** (simplified, assuming correlation = 0.5):
```
Portfolio Risk ≈ √(0.33²×0.15² + 0.33²×0.16² + 0.34²×0.17² + 2×0.33×0.33×0.15×0.16×0.5 + ...)
Portfolio Risk ≈ 14-16%
```

**MVO Constraint**: 8% maximum
**Result**: ❌ **CONSTRAINT VIOLATION** - Cannot optimize this portfolio

---

### 3.2 Efficient Frontier Impact

#### Problem: Frontier Truncation and Inconsistency

**Scenario**: Efficient frontier generation with inconsistent constraints

1. **Frontier Generation** (`portfolio_mvo_optimizer.py`):
   - Uses max risk = 8% for very-conservative
   - Generates frontier points up to 8% risk
   - Frontier shows limited range

2. **Random Portfolios** (`portfolio_stock_selector.py`):
   - Uses stocks with volatility up to 18%
   - Random portfolios can have risk up to 18%
   - Many random portfolios exceed the efficient frontier's maximum risk

**Result**:
- ❌ Efficient frontier appears "cut off" - doesn't cover all random portfolios
- ❌ Charts show random portfolios above the frontier (impossible!)
- ❌ Visual inconsistency confuses users
- ❌ CML calculation may be incorrect (tangent portfolio might be constrained)

#### Example Visualization Issue:

```
Risk-Return Chart:
                    │
        18% Risk    │  ●●●●●  ← Random portfolios (allowed by stock selector)
                    │   ●●●
        12% Risk    │    ●●
                    │     ●
         8% Risk    │───────  ← Efficient frontier (cut off by MVO constraint)
                    │
                    └─────────────────
```

**User sees**: Random portfolios above efficient frontier (impossible!)
**Reality**: Constraint mismatch causes visualization error

---

### 3.3 Optimization Impact

#### Problem: Constraint Violations and Failures

**Scenario**: User runs optimization with selected stocks

1. **Stock Selection**: Stocks selected with volatility up to 18% (very-conservative)
2. **Optimization Request**: User requests optimization with very-conservative profile
3. **MVO Optimizer**: Applies 8% max risk constraint
4. **Result**: 
   - Optimization **FAILS** (no feasible solution)
   - OR produces unrealistic weights (e.g., 90% in one low-volatility stock)
   - OR ignores constraint and produces 15% risk portfolio

**Impact**:
- ❌ Optimization errors/failures
- ❌ Unrealistic portfolio allocations
- ❌ User frustration
- ❌ System reliability issues

---

### 3.4 Chart Visualization Impact

#### Problem: Misleading Risk Profile Zones

**Frontend Display** (`PortfolioOptimization.tsx`):

```typescript
const riskProfileMaxRisk = {
  'very-conservative': 0.08,
  'conservative': 0.12,
  'moderate': 0.16,
  'aggressive': 0.22,
  'very-aggressive': 0.28
};
```

**Display Message**: "Risk profile constraint: Maximum risk 8%"

**But**:
- Random portfolios show risk up to 18% (from stock selector)
- Efficient frontier only goes to 8%
- User's selected portfolio might have 15% risk

**Result**:
- ❌ Confusing visualization
- ❌ Misleading risk profile indicator
- ❌ User doesn't understand why their portfolio exceeds "maximum risk"

---

### 3.5 Dual Optimization Impact

#### Problem: Best Available Portfolio Filtering

**Scenario**: Dual optimization for very-conservative profile

1. **Eligible Ticker Filtering** (`routers/portfolio.py`):
   ```python
   max_risk = 0.08  # very-conservative
   filtered_tickers = [t for t in eligible_tickers_data
                      if t.get('volatility', 1.0) <= max_risk * 1.2]  # 9.6%
   ```

2. **Stock Selector** (`portfolio_stock_selector.py`):
   - Allows stocks up to 18% volatility

**Result**:
- ❌ Best available portfolio uses only 8-9.6% volatility stocks
- ❌ Misses better opportunities in 10-18% range
- ❌ Suboptimal "best available" portfolio
- ❌ Unfair comparison with user's portfolio (which may use 15% stocks)

---

## 4. Root Cause Analysis

### Why These Inconsistencies Exist:

1. **Different Purposes**:
   - **MVO Optimizer**: Portfolio-level risk constraint (final portfolio risk)
   - **Stock Selector**: Individual stock volatility range (component selection)
   - **Strategy Optimizer**: Strategy-specific constraints (different strategies)

2. **Historical Evolution**:
   - Constraints evolved over time
   - Different developers/modules added constraints independently
   - No centralized constraint definition

3. **Conceptual Confusion**:
   - **Portfolio Risk** ≠ **Stock Volatility**
   - Portfolio risk is typically **lower** than individual stock volatility (diversification)
   - But constraints don't account for this relationship

4. **Missing Relationship**:
   - No formula linking stock volatility ranges to portfolio risk constraints
   - No validation that selected stocks can form portfolios meeting risk constraints

---

## 5. Mathematical Relationship

### Portfolio Risk vs Stock Volatility

**Key Formula**:
```
Portfolio Risk = √(wᵀ × Σ × w)
```

Where:
- `w` = weight vector
- `Σ` = covariance matrix
- Portfolio risk ≤ max(stock volatilities) due to diversification

**Example**:
- 3 stocks: 15%, 16%, 17% volatility
- Equal weights (33.3% each)
- Correlation = 0.5
- **Portfolio Risk** ≈ 12-13% (less than max stock volatility)

**Rule of Thumb**:
- Well-diversified portfolio risk ≈ 0.7-0.9 × max(stock volatilities)
- For very-conservative: If max portfolio risk = 8%, max stock volatility ≈ 10-12%

**Current Mismatch**:
- MVO constraint: 8% portfolio risk
- Stock selector: 18% stock volatility
- **Gap**: 18% stocks cannot form 8% risk portfolio (even with perfect diversification)

---

## 6. Impact Severity Assessment

### Critical Issues (Must Fix):

1. **Optimization Failures** ⚠️ **HIGH**
   - Users cannot optimize selected portfolios
   - System reliability compromised
   - User frustration high

2. **Visual Inconsistencies** ⚠️ **HIGH**
   - Charts show impossible scenarios (random portfolios above frontier)
   - Misleading risk profile indicators
   - User confusion

3. **Suboptimal Results** ⚠️ **MEDIUM**
   - Best available portfolios miss opportunities
   - Unfair comparisons
   - Reduced system value

### Moderate Issues:

4. **Inconsistent User Experience** ⚠️ **MEDIUM**
   - Different constraints in different parts of system
   - User doesn't know what to expect
   - Trust issues

5. **Maintenance Burden** ⚠️ **LOW**
   - Multiple constraint definitions to maintain
   - Risk of further divergence
   - Code complexity

---

## 7. Recommended Solution

### Option 1: Unified Constraint System (Recommended)

**Create centralized risk profile configuration**:

```python
# backend/config/risk_profiles.py
RISK_PROFILE_CONFIG = {
    'very-conservative': {
        'max_portfolio_risk': 0.08,           # For optimization
        'max_stock_volatility': 0.12,         # For stock selection (1.5x portfolio risk)
        'min_stock_volatility': 0.05,         # Minimum for diversification
        'max_single_stock_weight': 0.30,
        'min_sectors': 4
    },
    'conservative': {
        'max_portfolio_risk': 0.12,
        'max_stock_volatility': 0.18,         # 1.5x portfolio risk
        'min_stock_volatility': 0.10,
        'max_single_stock_weight': 0.35,
        'min_sectors': 4
    },
    'moderate': {
        'max_portfolio_risk': 0.16,
        'max_stock_volatility': 0.24,         # 1.5x portfolio risk
        'min_stock_volatility': 0.15,
        'max_single_stock_weight': 0.40,
        'min_sectors': 3
    },
    'aggressive': {
        'max_portfolio_risk': 0.22,
        'max_stock_volatility': 0.33,         # 1.5x portfolio risk
        'min_stock_volatility': 0.22,
        'max_single_stock_weight': 0.45,
        'min_sectors': 3
    },
    'very-aggressive': {
        'max_portfolio_risk': 0.28,
        'max_stock_volatility': 0.42,         # 1.5x portfolio risk
        'min_stock_volatility': 0.30,
        'max_single_stock_weight': 0.50,
        'min_sectors': 3
    }
}
```

**Benefits**:
- ✅ Single source of truth
- ✅ Consistent across all modules
- ✅ Mathematical relationship maintained (stock volatility ≈ 1.5x portfolio risk)
- ✅ Easy to maintain and update

**Implementation**:
1. Create `backend/config/risk_profiles.py`
2. Update all modules to import from this file
3. Add validation to ensure stock selections can form valid portfolios
4. Update frontend to use same constraints

---

### Option 2: Constraint Validation Layer

**Add validation before optimization**:

```python
def validate_portfolio_for_risk_profile(stocks: List[Dict], risk_profile: str) -> bool:
    """Validate that selected stocks can form portfolio meeting risk profile"""
    config = RISK_PROFILE_CONFIG[risk_profile]
    max_stock_vol = max(s['volatility'] for s in stocks)
    
    # Estimate minimum possible portfolio risk
    min_portfolio_risk = estimate_min_portfolio_risk(stocks)
    
    if min_portfolio_risk > config['max_portfolio_risk']:
        return False, f"Selected stocks cannot form portfolio with risk ≤ {config['max_portfolio_risk']}"
    
    return True, None
```

**Benefits**:
- ✅ Prevents optimization failures
- ✅ Better error messages
- ✅ User guidance

---

## 8. Migration Plan

### Phase 1: Analysis & Documentation ✅ (Current)
- Document all constraint definitions
- Identify inconsistencies
- Assess impact

### Phase 2: Create Unified Config
- Create `backend/config/risk_profiles.py`
- Define unified constraints with mathematical relationships
- Add validation functions

### Phase 3: Update Backend Modules
- Update `portfolio_mvo_optimizer.py`
- Update `portfolio_stock_selector.py`
- Update `strategy_portfolio_optimizer.py`
- Update `port_analytics.py`
- Update `routers/portfolio.py`

### Phase 4: Update Frontend
- Update `PortfolioOptimization.tsx`
- Update risk profile displays
- Add validation messages

### Phase 5: Testing & Validation
- Test portfolio generation
- Test optimization
- Test efficient frontier
- Test charts
- Validate consistency

### Phase 6: Regenerate Portfolios
- Regenerate all pre-generated portfolios with new constraints
- Update Redis cache
- Verify quality

---

## 9. Immediate Actions Required

### Critical Fixes (Do First):

1. **Fix Stock Selector Volatility Ranges**:
   - Very-conservative: Change max from 18% to 12%
   - Conservative: Change max from 25% to 18%
   - Moderate: Change max from 32% to 24%
   - Aggressive: Change max from 45% to 33%
   - Very-aggressive: Change max from 100% to 42%

2. **Add Validation**:
   - Validate stock selections can form portfolios meeting risk constraints
   - Show error messages if validation fails

3. **Update Frontend Display**:
   - Show both stock volatility range AND portfolio risk constraint
   - Clarify the relationship

### Medium Priority:

4. **Create Unified Config**:
   - Implement Option 1 solution
   - Migrate all modules

5. **Update Documentation**:
   - Document constraint relationships
   - Add developer guidelines

---

## 10. Conclusion

**Current State**: ⚠️ **INCONSISTENT** - Multiple constraint definitions causing:
- Optimization failures
- Visual inconsistencies
- User confusion
- Suboptimal results

**Required Action**: **IMMEDIATE** - Fix stock selector volatility ranges to align with MVO optimizer constraints

**Long-term Solution**: Implement unified constraint system with mathematical relationships

**Impact if Not Fixed**: 
- Continued user frustration
- System reliability issues
- Trust degradation
- Potential regulatory concerns (misleading risk profiles)

---

## Appendix: Constraint Usage Map

| Module | Constraint Type | Current Value (very-conservative) | Should Be |
|--------|----------------|----------------------------------|-----------|
| `portfolio_mvo_optimizer.py` | Portfolio Risk Max | 0.08 (8%) | ✅ Correct |
| `routers/portfolio.py` (dual opt) | Portfolio Risk Max | 0.08 (8%) | ✅ Correct |
| `portfolio_stock_selector.py` | Stock Volatility Max | 0.18 (18%) | ❌ Should be 0.12 (12%) |
| `strategy_portfolio_optimizer.py` | Stock Volatility Max | 0.22 (22%) | ❌ Should be 0.12 (12%) |
| `port_analytics.py` | Portfolio Risk Max | 0.15 (15%) | ⚠️ Should be 0.08 (8%) |
| `enhanced_portfolio_config.py` | Portfolio Risk Max | 0.179 (17.9%) | ❌ Should be 0.08 (8%) |
| `PortfolioOptimization.tsx` | Portfolio Risk Max | 0.08 (8%) | ✅ Correct |

**Consistency Score**: 2/7 modules correct = **28.6% consistency** ⚠️

---

## Appendix B: Ticker Distribution Analysis (Redis Data)

### Actual Ticker Counts in Redis

**Total tickers with metrics**: 1,428
**Tickers with valid volatility/return (>=12 months)**: 1,418

### Volatility Distribution

| Metric | Value |
|--------|-------|
| Min | 0.27% |
| Max | 151.79% |
| Mean | 30.48% |
| Median | 27.76% |
| 25th percentile | 22.42% |
| 75th percentile | 35.32% |

### Detailed Volatility Buckets

| Volatility Range | Ticker Count | % of Total | Positive Returns |
|-----------------|--------------|------------|------------------|
| 0%-5% | 17 | 1.2% | 7 (41%) |
| 5%-8% | 4 | 0.3% | 3 (75%) |
| 8%-10% | 1 | 0.1% | 0 (0%) |
| 10%-12% | 2 | 0.1% | 2 (100%) |
| 12%-15% | 42 | 2.9% | 42 (100%) |
| 15%-18% | 95 | 6.7% | 94 (99%) |
| 18%-20% | 76 | 5.3% | 76 (100%) |
| 20%-22% | 99 | 6.9% | 95 (96%) |
| 22%-25% | 200 | 14.0% | 189 (94%) |
| 25%-28% | 183 | 12.8% | 174 (95%) |
| 28%-32% | 222 | 15.5% | 208 (94%) |
| 32%-38% | 208 | 14.6% | 196 (94%) |
| 38%-45% | 117 | 8.2% | 106 (91%) |
| 45%-50% | 50 | 3.5% | 43 (86%) |
| 50%-100% | 96 | 6.7% | 81 (84%) |

### Why Current Settings Exist

**Key Insight**: MVO constraints are for PORTFOLIO RISK, not STOCK VOLATILITY.

| Profile | MVO Constraint | Stock Selector Max | Multiplier |
|---------|---------------|-------------------|------------|
| very-conservative | 8% | 18% | 2.2x |
| conservative | 12% | 25% | 2.1x |
| moderate | 16% | 32% | 2.0x |
| aggressive | 22% | 45% | 2.0x |
| very-aggressive | 28% | 100% | 3.6x |

**Reason**: Stock selector needs enough stocks to build diverse portfolios:
- If we only use stocks with volatility <= 8%, we get only 21 stocks
- That's not enough for 6 diverse portfolios with 3-5 stocks each
- So stock selector uses WIDER ranges to have enough stocks

### Realistic Portfolio Risk Analysis

With 4 stocks and correlation ~0.4, diversification factor ≈ 0.72:

| Profile | Stock Pool | Avg Stock Vol | Realistic Portfolio Risk | MVO Constraint | Gap |
|---------|-----------|---------------|-------------------------|----------------|-----|
| very-conservative | 141 stocks | 15.6% | 11.2% | 8% | +3.2% ❌ |
| conservative | 454 stocks | 20.9% | 15.0% | 12% | +3.0% ❌ |
| moderate | 571 stocks | 26.8% | 19.3% | 16% | +3.3% ❌ |
| aggressive | 510 stocks | 34.1% | 24.6% | 22% | +2.6% ❌ |
| very-aggressive | 230 stocks | 49.9% | 35.9% | 28% | +7.9% ❌ |

### Option Analysis

#### Option A: Increase MVO Constraints (RECOMMENDED)

| Profile | Current MVO | Suggested MVO | Change |
|---------|------------|---------------|--------|
| very-conservative | 8% | 12% | +4% |
| conservative | 12% | 16% | +4% |
| moderate | 16% | 20% | +4% |
| aggressive | 22% | 26% | +4% |
| very-aggressive | 28% | 36% | +8% |

**Pros**: Keeps current stock pools, optimization works, charts consistent
**Cons**: Risk profiles become less "conservative" in name

#### Option B: Tighten Stock Selector Ranges

| Profile | Current Range | Tighter Range | Current Count | New Count |
|---------|--------------|---------------|---------------|-----------|
| very-conservative | 5%-18% | 4%-12% | 141 | 8 ❌ |
| conservative | 15%-25% | 8%-18% | 454 | 138 ✅ |
| moderate | 22%-32% | 12%-24% | 571 | 429 ✅ |
| aggressive | 28%-45% | 18%-33% | 510 | 778 ✅ |
| very-aggressive | 38%-100% | 22%-42% | 230 | 839 ✅ |

**Problem**: Only 8 stocks for very-conservative (need 15+ for diverse portfolios)

#### Option C: Hybrid Approach (BEST)

1. Keep current stock selector ranges (sufficient stock pools)
2. Update MVO constraints to realistic values
3. Update frontend to show accurate risk levels
4. Add validation to warn users if portfolio exceeds risk profile

### Conclusion

The current settings exist because:
1. **Stock selector** was designed to have enough stocks for portfolio generation
2. **MVO optimizer** was designed with theoretical portfolio risk targets
3. These were designed **independently** without considering each other

**Recommended Action**: Implement Option A (increase MVO constraints) or Option C (hybrid approach) because:
- Only 8 low-volatility stocks available for very-conservative
- Cannot tighten stock selector without breaking portfolio generation
- MVO constraints should reflect realistic portfolio risk from available stocks

