/**
 * ============================================================================
 * RECOMMENDATIONS TAB - CODE REVIEW FILE
 * ============================================================================
 * 
 * This file contains the complete code for the "Recommendations" tab from 
 * PortfolioOptimization.tsx (lines ~4094-5200+).
 * 
 * PURPOSE: For your review to decide what to keep, remove, or improve.
 * 
 * ============================================================================
 * CURRENT STRUCTURE:
 * ============================================================================
 * 
 * 1. PRIMARY RECOMMENDATION CARD (lines 4105-4283)
 *    - Shows "Significant Improvement Opportunity" (amber) if Sharpe diff > 20%
 *    - Shows "Moderate Improvement Available" (blue) if Sharpe diff > 10%
 *    - Shows "Excellent Portfolio Performance!" (green) otherwise
 *    - Displays top 5 tickers from optimized portfolio
 *    
 *    QUESTION: Do we need this? It duplicates info from the comparison table.
 * 
 * 2. RECOMMENDED ACTIONS CARD (lines 4286-4355)
 *    - "Apply Optimized Weights" if Sharpe improvement > 0
 *    - "Reduced Risk Profile" if risk improvement > 0
 *    - "Enhanced Returns" if return improvement > 0
 *    - "Optimized Portfolio Tickers" list
 *    
 *    QUESTION: Do we need this? It's based on mvoResults.improvements which
 *    may not be accurate for triple optimization.
 * 
 * 3. PERFORMANCE SUMMARY CARD (lines 4357-4431)
 *    - "Current → Optimized" comparison (Return, Risk, Sharpe differences)
 *    - "Risk Profile Compliance" check
 *    
 *    ISSUE: Uses dualOptimizationResults which may not reflect the SELECTED
 *    portfolio (current/weights/market). Should use tripleOptimizationResults
 *    and show metrics for the SELECTED portfolio.
 * 
 * 4. MULTI-FACTOR QUALITY SCORE CARD (lines 4433-4933)
 *    - Shows composite quality score (0-100)
 *    - Factor breakdown: Risk Alignment, Downside Protection, Diversification, Consistency
 *    - Compares selected vs best alternative portfolio
 *    
 *    IMPROVEMENT IDEAS:
 *    - Add gauge/meter visualization for composite score
 *    - Add explanations for each factor
 *    - Show trend arrows for improvement potential
 * 
 * 5. MONTE CARLO SIMULATION CARD (lines 4935-5200+)
 *    - Probability of positive returns
 *    - Return distribution histogram
 *    - Percentile ranges (5th, 25th, 50th, 75th, 95th)
 *    - Loss probability thresholds
 *    
 *    IMPROVEMENT IDEAS:
 *    - Add confidence interval visualization
 *    - Add VaR (Value at Risk) display
 *    - Add scenario analysis (best/worst/expected)
 * 
 * ============================================================================
 * RECOMMENDATIONS FOR CLEANUP:
 * ============================================================================
 * 
 * REMOVE OR SIMPLIFY:
 * - Primary Recommendation Card: Redundant with comparison table
 * - Recommended Actions Card: Based on old mvoResults, not accurate
 * 
 * KEEP AND FIX:
 * - Performance Summary: Fix to use selected portfolio from tripleOptimizationResults
 * - Quality Score Card: Keep, it's valuable
 * - Monte Carlo Card: Keep, it's valuable
 * 
 * ============================================================================
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Target,
  CheckCircle,
  AlertTriangle,
  Info,
  Shield,
  TrendingUp,
  Lightbulb,
  Award,
  BarChart3,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
  Line,
} from 'recharts';

// ============================================================================
// TYPES (from PortfolioOptimization.tsx)
// ============================================================================

interface QualityScoreResult {
  composite_score: number;
  rating: string;
  rating_color: string;
  factor_breakdown?: {
    risk_alignment?: { score: number };
    downside_protection?: { score: number };
    diversification?: { score: number };
    consistency?: { score: number };
    risk_profile_compliance?: { score: number };
    sortino_ratio?: { score: number };
  };
}

interface MonteCarloResult {
  probability_positive: number;
  percentiles: {
    p5: number;
    p25: number;
    p50: number;
    p75: number;
    p95: number;
  };
  probability_loss_thresholds: {
    loss_5pct: number;
    loss_10pct: number;
    loss_20pct: number;
    loss_30pct: number;
  };
  histogram_data: Array<{
    return: number;
    return_pct: number;
    count: number;
    frequency: number;
  }>;
  statistics: {
    mean: number;
    std: number;
    min: number;
    max: number;
    median: number;
  };
  probability_statements: string[];
  parameters: {
    expected_return: number;
    risk: number;
    num_simulations: number;
    time_horizon_years: number;
  };
}

interface TripleOptimizationResponse {
  current_portfolio: {
    tickers: string[];
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      risk: number;
      sharpe_ratio: number;
    };
  };
  weights_optimized_portfolio: {
    optimized_portfolio: {
      tickers: string[];
      weights: Record<string, number>;
      metrics: {
        expected_return: number;
        risk: number;
        sharpe_ratio: number;
      };
    };
  };
  market_optimized_portfolio: {
    optimized_portfolio: {
      tickers: string[];
      weights: Record<string, number>;
      metrics: {
        expected_return: number;
        risk: number;
        sharpe_ratio: number;
      };
    };
  } | null;
  comparison: {
    monte_carlo?: {
      current: MonteCarloResult;
      weights: MonteCarloResult;
      market: MonteCarloResult | null;
    };
    quality_scores?: {
      current: QualityScoreResult;
      weights: QualityScoreResult;
      market: QualityScoreResult | null;
    };
  };
  optimization_metadata: {
    recommendation: 'current' | 'weights' | 'market';
    market_exploration_successful: boolean;
  };
}

// ============================================================================
// SECTION 1: PRIMARY RECOMMENDATION CARD
// ============================================================================
// 
// VERDICT: Consider REMOVING or SIMPLIFYING
// - Duplicates information already shown in the comparison table
// - The "Action Plan" and "Top Opportunities" are helpful but could be
//   integrated into the comparison table or a simpler summary
//
// If keeping, should:
// - Use selectedPortfolio to show the RIGHT comparison
// - Not hardcode "market tickers" language when weights-opt is selected

const PrimaryRecommendationCard = ({
  tripleOptimizationResults,
  selectedPortfolio,
  riskProfile,
}: {
  tripleOptimizationResults: TripleOptimizationResponse | null;
  selectedPortfolio: 'current' | 'weights' | 'market';
  riskProfile: string;
}) => {
  if (!tripleOptimizationResults) return null;

  const currentSharpe = tripleOptimizationResults.current_portfolio?.metrics?.sharpe_ratio ?? 0;
  
  let optimizedSharpe = 0;
  let optimizedWeights: Record<string, number> = {};
  
  if (selectedPortfolio === 'weights') {
    optimizedSharpe = tripleOptimizationResults.weights_optimized_portfolio?.optimized_portfolio?.metrics?.sharpe_ratio ?? 0;
    optimizedWeights = tripleOptimizationResults.weights_optimized_portfolio?.optimized_portfolio?.weights || {};
  } else if (selectedPortfolio === 'market' && tripleOptimizationResults.market_optimized_portfolio) {
    optimizedSharpe = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio?.metrics?.sharpe_ratio ?? 0;
    optimizedWeights = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio?.weights || {};
  }
  
  const sharpeDiffFromCurrent = optimizedSharpe - currentSharpe;
  const sharpeDiffPercent = currentSharpe > 0 ? (sharpeDiffFromCurrent / currentSharpe) * 100 : 0;
  
  const topTickers = Object.entries(optimizedWeights)
    .sort(([,a], [,b]) => (b as number) - (a as number))
    .slice(0, 5)
    .map(([ticker, weight]) => ({ ticker, weight: weight as number }));

  // ... rest of the rendering logic
  return (
    <Card className="border border-border bg-muted">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2 text-blue-900">
          <Target className="h-5 w-5" />
          Primary Recommendation
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Content based on sharpeDiffPercent thresholds */}
        <div className="text-sm text-gray-600">
          Current Sharpe: {currentSharpe.toFixed(2)} → Selected: {optimizedSharpe.toFixed(2)} 
          ({sharpeDiffPercent > 0 ? '+' : ''}{sharpeDiffPercent.toFixed(0)}%)
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// SECTION 2: RECOMMENDED ACTIONS CARD
// ============================================================================
//
// VERDICT: Consider REMOVING
// - Based on mvoResults.improvements which is from the OLD dual optimization
// - Not accurate for triple optimization where we have 3 portfolios
// - The information is redundant with the comparison table

const RecommendedActionsCard = ({
  mvoResults,
  riskProfile,
}: {
  mvoResults: any;
  riskProfile: string;
}) => {
  if (!mvoResults?.improvements) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Recommended Actions</CardTitle>
        <p className="text-muted-foreground">Based on your {riskProfile} risk profile</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* This card uses mvoResults.improvements which may not be accurate */}
        {/* Consider removing or updating to use tripleOptimizationResults */}
      </CardContent>
    </Card>
  );
};

// ============================================================================
// SECTION 3: PERFORMANCE SUMMARY CARD
// ============================================================================
//
// VERDICT: KEEP but FIX
// - Currently uses dualOptimizationResults which is wrong
// - Should use tripleOptimizationResults and show the SELECTED portfolio
// - Risk Profile Compliance is useful

const PerformanceSummaryCard = ({
  tripleOptimizationResults,
  selectedPortfolio,
  riskProfile,
}: {
  tripleOptimizationResults: TripleOptimizationResponse | null;
  selectedPortfolio: 'current' | 'weights' | 'market';
  riskProfile: string;
}) => {
  if (!tripleOptimizationResults) return null;

  const current = tripleOptimizationResults.current_portfolio?.metrics;
  
  let selected;
  let selectedLabel = 'Selected';
  
  if (selectedPortfolio === 'weights') {
    selected = tripleOptimizationResults.weights_optimized_portfolio?.optimized_portfolio?.metrics;
    selectedLabel = 'Weights-Optimized';
  } else if (selectedPortfolio === 'market' && tripleOptimizationResults.market_optimized_portfolio) {
    selected = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio?.metrics;
    selectedLabel = 'Market-Optimized';
  } else {
    selected = current;
    selectedLabel = 'Current';
  }

  const returnDiff = (selected?.expected_return ?? 0) - (current?.expected_return ?? 0);
  const riskDiff = (selected?.risk ?? 0) - (current?.risk ?? 0);
  const sharpeDiff = (selected?.sharpe_ratio ?? 0) - (current?.sharpe_ratio ?? 0);

  // Risk limits by profile
  const riskProfileMaxRisk: Record<string, number> = {
    'very-conservative': 0.18,
    'conservative': 0.25,
    'moderate': 0.32,
    'aggressive': 0.35,
    'very-aggressive': 0.47
  };
  const maxRisk = riskProfileMaxRisk[riskProfile] || 0.32;
  const selectedRisk = selected?.risk ?? 0;
  const isCompliant = selectedRisk <= maxRisk;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Performance Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Current → Selected Comparison */}
          <div className="p-4 rounded-lg bg-muted border border-border">
            <div className="text-sm font-medium text-gray-600 mb-2">
              Current → {selectedLabel}
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Return</span>
                <span className={`font-semibold ${returnDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {returnDiff >= 0 ? '+' : ''}{(returnDiff * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Risk</span>
                <span className={`font-semibold ${riskDiff <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {riskDiff <= 0 ? '' : '+'}{(riskDiff * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Sharpe</span>
                <span className={`font-semibold ${sharpeDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {sharpeDiff >= 0 ? '+' : ''}{sharpeDiff.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
          
          {/* Risk Profile Compliance */}
          <div className="p-4 rounded-lg bg-muted border border-border">
            <div className="text-sm font-medium text-gray-600 mb-2">Risk Profile Compliance</div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Max Allowed</span>
                <span className="font-semibold text-indigo-600">{(maxRisk * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Your Risk</span>
                <span className={`font-semibold ${isCompliant ? 'text-green-600' : 'text-red-600'}`}>
                  {(selectedRisk * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Status</span>
                <Badge variant={isCompliant ? 'default' : 'destructive'} className={isCompliant ? 'bg-green-500' : ''}>
                  {isCompliant ? '✓ Compliant' : '⚠ Over Limit'}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// SECTION 4: MULTI-FACTOR QUALITY SCORE CARD
// ============================================================================
//
// VERDICT: KEEP - This is valuable
// 
// IMPROVEMENT IDEAS:
// 1. Add a circular gauge/meter for the composite score
// 2. Add tooltips explaining each factor
// 3. Show improvement arrows (↑/↓) for each factor
// 4. Add color-coded thresholds (e.g., 80+ = Excellent, 60-80 = Good, etc.)

const QualityScoreCard = ({
  qualityData,
  selectedPortfolio,
  isTriple,
}: {
  qualityData: {
    current: QualityScoreResult;
    weights?: QualityScoreResult;
    market?: QualityScoreResult | null;
    optimized?: QualityScoreResult;
  };
  selectedPortfolio: 'current' | 'weights' | 'market';
  isTriple: boolean;
}) => {
  // ... implementation
  return (
    <Card className="border-2 border-purple-200">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Award className="h-5 w-5 text-purple-600" />
          Multi-Factor Quality Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Factor breakdown with progress bars */}
      </CardContent>
    </Card>
  );
};

// ============================================================================
// SECTION 5: MONTE CARLO SIMULATION CARD
// ============================================================================
//
// VERDICT: KEEP - This is valuable
//
// IMPROVEMENT IDEAS:
// 1. Add VaR (Value at Risk) at 95% confidence
// 2. Add Expected Shortfall (CVaR)
// 3. Add scenario boxes: "Best Case", "Expected", "Worst Case"
// 4. Add time horizon selector (1 year, 3 years, 5 years)
// 5. Improve histogram visualization with area chart

const MonteCarloCard = ({
  monteCarloData,
  selectedPortfolio,
  isTriple,
}: {
  monteCarloData: {
    current: MonteCarloResult;
    weights?: MonteCarloResult;
    market?: MonteCarloResult | null;
    optimized?: MonteCarloResult;
  };
  selectedPortfolio: 'current' | 'weights' | 'market';
  isTriple: boolean;
}) => {
  // ... implementation
  return (
    <Card className="border-2 border-blue-200">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-600" />
          Monte Carlo Simulation
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Probability comparison and histogram */}
      </CardContent>
    </Card>
  );
};

// ============================================================================
// SUMMARY OF RECOMMENDATIONS
// ============================================================================
/*

1. REMOVE: Primary Recommendation Card
   - Redundant with comparison table
   - If keeping, simplify to just show the recommendation text

2. REMOVE: Recommended Actions Card
   - Uses old mvoResults.improvements data
   - Not accurate for triple optimization

3. FIX: Performance Summary Card
   - Change from dualOptimizationResults to tripleOptimizationResults
   - Show metrics for the SELECTED portfolio, not just "optimized"

4. KEEP: Quality Score Card
   - Valuable multi-factor analysis
   - Consider adding gauge visualization

5. KEEP: Monte Carlo Card
   - Valuable probability analysis
   - Consider adding VaR/CVaR metrics

*/

export {
  PrimaryRecommendationCard,
  RecommendedActionsCard,
  PerformanceSummaryCard,
  QualityScoreCard,
  MonteCarloCard,
};

