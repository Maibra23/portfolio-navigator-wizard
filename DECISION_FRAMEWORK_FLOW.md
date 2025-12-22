# Decision Framework Flow Diagram

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Clicks "Optimize"                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Calculate Current Portfolio (ACTUAL weights)            │
│  Input:  CTAS 52%, AMAT 32%, LLY 16%                           │
│  Output: Return: 25.4%, Risk: 22.7%, Sharpe: 0.95             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Weights-Only Optimization (ALWAYS RUN)                │
│  Input:  Same tickers (CTAS, AMAT, LLY)                        │
│  Process: Optimize weights to maximize Sharpe                   │
│  Output: Return: 24.8%, Risk: 21.5%, Sharpe: 0.97              │
│  Result: ✅ Improvement (+0.02 Sharpe)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Market Exploration (ALWAYS RUN - NO CONDITIONS)      │
│  Input:  User tickers + Risk profile constraints                │
│  Process: Search 700+ eligible market tickers                   │
│           Find best portfolio matching risk profile              │
│  Output: Return: 17.5%, Risk: 25.4%, Sharpe: 0.53              │
│  Result: ⚠️ Worse than weights (-0.44 Sharpe)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Decision Framework (FOR RECOMMENDATION ONLY)           │
│                                                                  │
│  Compare all three portfolios:                                  │
│  ┌──────────────┬──────────────┬──────────────┐                │
│  │   Current    │   Weights    │   Market     │                │
│  ├──────────────┼──────────────┼──────────────┤                │
│  │ Sharpe: 0.95 │ Sharpe: 0.97 │ Sharpe: 0.53 │                │
│  │ Risk: 22.7%  │ Risk: 21.5%  │ Risk: 25.4%  │                │
│  └──────────────┴──────────────┴──────────────┘                │
│                                                                  │
│  Decision Logic:                                                │
│  1. Market vs Weights: 0.53 - 0.97 = -0.44 (WORSE)             │
│  2. Weights vs Current: 0.97 - 0.95 = +0.02 (BETTER)           │
│  3. Risk increase: 25.4% - 21.5% = +3.9% (TOO HIGH)            │
│                                                                  │
│  ✅ Recommendation: "weights"                                   │
│  (Weights-optimized is best)                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Return All Three Portfolios                            │
│                                                                  │
│  Response:                                                      │
│  {                                                              │
│    "current_portfolio": {...},          ← Always present       │
│    "weights_optimized_portfolio": {...}, ← Always present      │
│    "market_optimized_portfolio": {...},  ← Always present      │
│    "recommendation": "weights",          ← Decision framework   │
│    "comparison": {...}                   ← All comparisons      │
│  }                                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: Display Three-Column Table                             │
│                                                                  │
│  ┌──────────────┬──────────────┬──────────────┐                │
│  │   Current    │   Weights    │   Market     │                │
│  │   Sharpe:    │   Sharpe:    │   Sharpe:    │                │
│  │   0.95       │   0.97 ⭐    │   0.53       │                │
│  │              │   [REC]      │              │                │
│  │ [SELECT]     │ [SELECT]     │ [SELECT]     │                │
│  └──────────────┴──────────────┴──────────────┘                │
│                                                                  │
│  ⭐ = Recommended by decision framework                          │
│  All 3 columns always visible                                    │
│  User can select any portfolio                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Framework Logic (Detailed)

### Inputs:
- `current`: Current portfolio metrics
- `weights_opt`: Weights-optimized portfolio metrics
- `market_opt`: Market-optimized portfolio metrics
- `risk_profile`: User's risk profile

### Process:

```python
def decide_best_portfolio(current, weights_opt, market_opt, risk_profile):
    # Calculate improvements
    weights_improvement = weights_opt.sharpe - current.sharpe
    market_vs_current = market_opt.sharpe - current.sharpe
    market_vs_weights = market_opt.sharpe - weights_opt.sharpe
    
    # Risk changes
    weights_risk_change = weights_opt.risk - current.risk
    market_risk_change = market_opt.risk - weights_opt.risk
    
    # Risk tolerance
    max_risk_increase = RISK_TOLERANCE[risk_profile]  # e.g., 0.05 for aggressive
    
    # Decision Tree:
    
    # 1. Is market better than weights?
    if (market_vs_weights >= 0.20 and  # Clear Sharpe improvement
        market_risk_change <= max_risk_increase):  # Risk acceptable
        return 'market'  # Recommend market
    
    # 2. Is weights better than current?
    if (weights_improvement >= 0.05 and  # Small improvement
        weights_risk_change <= max_risk_increase):  # Risk acceptable
        return 'weights'  # Recommend weights
    
    # 3. Current is best
    return 'current'  # Recommend keeping current
```

---

## Example Scenarios

### Scenario 1: Market is Best (Very-Conservative)

```
Current:      Sharpe 0.06, Risk 20.2%
Weights-Opt:  Sharpe 0.07, Risk 19.8%  (+0.01 improvement)
Market-Opt:   Sharpe 0.72, Risk 12.7%  (+0.65 vs weights!)

Decision:
  ✅ Market vs Weights: +0.65 (HUGE improvement)
  ✅ Risk decreased (even better!)
  ✅ Recommendation: "market"

UI:
  Market column: ⭐ Recommended (green border)
  Weights column: Standard
  Current column: Standard
```

### Scenario 2: Weights is Best (Aggressive)

```
Current:      Sharpe 0.95, Risk 22.7%
Weights-Opt:  Sharpe 0.97, Risk 21.5%  (+0.02 improvement)
Market-Opt:   Sharpe 0.53, Risk 25.4%  (-0.44 vs weights!)

Decision:
  ❌ Market vs Weights: -0.44 (WORSE)
  ❌ Risk increased too much
  ✅ Recommendation: "weights"

UI:
  Weights column: ⭐ Recommended (blue border)
  Market column: Standard (shows negative comparison)
  Current column: Standard
```

### Scenario 3: Current is Best (Edge Case)

```
Current:      Sharpe 1.20, Risk 20.1%  (Already excellent!)
Weights-Opt:  Sharpe 1.18, Risk 20.5%  (-0.02, worse!)
Market-Opt:   Sharpe 0.90, Risk 22.0%  (-0.30, worse!)

Decision:
  ❌ Weights worse than current
  ❌ Market worse than current
  ✅ Recommendation: "current"

UI:
  Current column: ⭐ Recommended (red border)
  Weights column: Standard
  Market column: Standard
```

---

## Key Takeaways

1. **Market Exploration Always Runs**: No conditions, no skipping
2. **All 3 Portfolios Always Returned**: Even if market is worse
3. **Decision Framework Only Affects Recommendation**: Visual highlighting, not data availability
4. **User Has Full Control**: Can select any portfolio regardless of recommendation

---

## Implementation Guarantee

```python
# This is ALWAYS true:
assert response.current_portfolio is not None
assert response.weights_optimized_portfolio is not None
assert response.market_optimized_portfolio is not None  # (unless optimization fails)

# Decision framework only affects:
assert response.recommendation in ['current', 'weights', 'market']
# This determines which column gets the ⭐ badge
```

