# Diversification Score Mathematics 📊

## Overview

The diversification score is a key metric that measures how well a portfolio's assets are diversified based on their correlation relationships. This document explains the mathematical foundation and implementation details.

## Mathematical Foundation

### 1. Correlation Analysis

**Correlation Coefficient (ρ)**
```
ρ = Cov(X,Y) / (σx × σy)
```

Where:
- `Cov(X,Y)` = Covariance between assets X and Y
- `σx, σy` = Standard deviations of assets X and Y
- `ρ` ranges from -1 to +1

### 2. Portfolio Diversification Score Formula

**Primary Formula:**
```
Diversification Score = 100% - (Average Correlation × 100%)
```

**Detailed Implementation:**
```python
def calculate_diversification_score(asset_returns, weights):
    # 1. Create correlation matrix
    returns_df = pd.concat(asset_returns, axis=1)
    corr_matrix = returns_df.corr()
    
    # 2. Calculate weighted average correlation
    total_weight_pairs = 0
    weighted_correlation = 0
    
    for i in range(len(weights)):
        for j in range(i + 1, len(weights)):
            weight_pair = weights[i] * weights[j]
            correlation = corr_matrix.iloc[i, j]
            
            if not pd.isna(correlation):
                weighted_correlation += weight_pair * abs(correlation)
                total_weight_pairs += weight_pair
    
    # 3. Calculate average correlation
    avg_correlation = weighted_correlation / total_weight_pairs if total_weight_pairs > 0 else 0
    
    # 4. Convert to diversification score
    diversification_score = max(0, 100 - (avg_correlation * 100))
    
    return round(diversification_score, 1)
```

## Interpretation Guide

### Score Ranges

| Score Range | Interpretation | Portfolio Characteristics |
|-------------|----------------|---------------------------|
| **90-100%** | Excellent | Very low correlation, maximum diversification benefits |
| **80-89%** | Very Good | Low correlation, strong diversification |
| **70-79%** | Good | Moderate correlation, decent diversification |
| **60-69%** | Fair | Some correlation, limited diversification |
| **50-59%** | Poor | High correlation, minimal diversification |
| **0-49%** | Very Poor | Very high correlation, no diversification benefits |

### Examples

#### High Diversification (Score: 85%)
```
Portfolio: AAPL (Tech) + JNJ (Healthcare) + VZ (Telecom)
Correlations: AAPL-JNJ: 0.2, AAPL-VZ: 0.15, JNJ-VZ: 0.1
Average: 0.15 → Score: 100% - 15% = 85%
```

#### Low Diversification (Score: 35%)
```
Portfolio: AAPL (Tech) + MSFT (Tech) + GOOGL (Tech)
Correlations: AAPL-MSFT: 0.8, AAPL-GOOGL: 0.7, MSFT-GOOGL: 0.75
Average: 0.75 → Score: 100% - 75% = 25%
```

## Implementation Details

### Backend Implementation

**File:** `backend/utils/port_analytics.py`

```python
def _calculate_portfolio_diversification_score(self, asset_returns: List[pd.Series], weights: List[float]) -> float:
    """Calculate diversification score for portfolio"""
    try:
        if len(asset_returns) < 2:
            return 0.0
        
        # Create correlation matrix
        returns_df = pd.concat(asset_returns, axis=1)
        corr_matrix = returns_df.corr()
        
        # Calculate weighted average correlation
        total_weight_pairs = 0
        weighted_correlation = 0
        
        for i in range(len(weights)):
            for j in range(i + 1, len(weights)):
                weight_pair = weights[i] * weights[j]
                correlation = corr_matrix.iloc[i, j]
                
                if not pd.isna(correlation):
                    weighted_correlation += weight_pair * abs(correlation)
                    total_weight_pairs += weight_pair
        
        avg_correlation = weighted_correlation / total_weight_pairs if total_weight_pairs > 0 else 0
        
        # Convert to diversification score (0-100)
        diversification_score = max(0, 100 - (avg_correlation * 100))
        
        return round(diversification_score, 1)
        
    except Exception as e:
        logger.error(f"Error calculating portfolio diversification score: {e}")
        return 50.0
```

### Frontend Display

**File:** `frontend/src/components/wizard/StockSelection.tsx`

```typescript
<div>
  <div className="flex justify-between text-sm mb-1">
    <span>Diversification Score</span>
    <span>{recommendation.diversificationScore}%</span>
  </div>
  <Progress value={recommendation.diversificationScore} className="h-2" />
  <p className="text-xs text-muted-foreground mt-1">
    Based on correlation analysis between assets
  </p>
  <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
    <strong>How it works:</strong> The diversification score measures how uncorrelated your assets are. 
    Lower correlation = higher diversification = better risk reduction. 
    Formula: 100% - (Average Correlation × 100%)
  </div>
</div>
```

## Data Requirements

### Minimum Data Points
- **Monthly returns**: At least 12 months (1 year)
- **Daily returns**: At least 252 trading days (1 year)
- **Recommended**: 60+ months for stable correlation estimates

### Data Quality Checks
```python
def _validate_price_data(self, data: pd.Series, ticker: str) -> bool:
    """Validate price data quality"""
    if len(data) < 12:  # Minimum 12 months
        return False
    
    if data.isnull().sum() > len(data) * 0.1:  # Max 10% missing data
        return False
    
    if data.std() == 0:  # No volatility
        return False
    
    return True
```

## Educational Benefits

### Why This Matters

1. **Risk Reduction**: Lower correlation means assets don't move together, reducing portfolio volatility
2. **Return Enhancement**: Diversified portfolios can achieve better risk-adjusted returns
3. **Market Protection**: During market downturns, uncorrelated assets provide protection

### Learning Objectives

- **Understanding Correlation**: How assets move relative to each other
- **Diversification Benefits**: Why spreading investments reduces risk
- **Portfolio Construction**: How to build portfolios with optimal diversification

## Limitations

### Current Implementation Limitations

1. **Historical Focus**: Based on past correlations, not future predictions
2. **Linear Relationships**: Assumes linear correlation, may miss non-linear relationships
3. **Static Analysis**: Doesn't account for changing market conditions
4. **Sector Blind**: Doesn't explicitly consider sector diversification

### Future Enhancements

1. **Dynamic Correlations**: Rolling correlation windows
2. **Sector Analysis**: Explicit sector diversification scoring
3. **Regime Detection**: Different correlation regimes (bull/bear markets)
4. **Non-linear Relationships**: Copula-based dependency modeling

## Testing and Validation

### Test Cases

```python
def test_diversification_score():
    # Test case 1: Perfect diversification (uncorrelated assets)
    returns1 = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])  # Asset 1
    returns2 = pd.Series([-0.01, 0.02, -0.03, 0.01, -0.02])  # Asset 2 (negative correlation)
    weights = [0.5, 0.5]
    
    score = calculate_diversification_score([returns1, returns2], weights)
    assert score > 80  # Should be high
    
    # Test case 2: Poor diversification (highly correlated assets)
    returns3 = pd.Series([0.01, 0.02, 0.03, 0.01, 0.02])  # Asset 3
    returns4 = pd.Series([0.015, 0.025, 0.035, 0.015, 0.025])  # Asset 4 (high correlation)
    
    score = calculate_diversification_score([returns3, returns4], weights)
    assert score < 50  # Should be low
```

## Conclusion

The diversification score provides a quantitative measure of portfolio diversification based on correlation analysis. While it has limitations, it serves as a valuable educational tool for understanding portfolio construction principles and risk management.

The implementation prioritizes:
- **Educational clarity**: Simple, understandable formula
- **Computational efficiency**: Fast calculation using cached data
- **Robust error handling**: Graceful fallbacks for edge cases
- **User-friendly display**: Clear visual indicators and explanations
