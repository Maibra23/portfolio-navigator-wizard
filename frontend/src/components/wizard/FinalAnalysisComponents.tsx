/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Shared Final Analysis components: Performance Summary, Quality Score, Monte Carlo.
 * Used in FinalizePortfolio Tab 3 (Final Analysis) and aligned with PortfolioOptimization Recommendations tab.
 */
import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  AlertTriangle,
  Info,
  Shield,
  TrendingUp,
  Award,
  BarChart3,
  Activity,
  AlertCircle,
  LineChart,
  TrendingDown,
  Eye,
  EyeOff,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
  Area,
  ReferenceLine,
} from "recharts";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// ---------------------------------------------------------------------------
// Types (aligned with PortfolioOptimization / triple optimization API)
// ---------------------------------------------------------------------------

export interface MonteCarloResult {
  simulated_returns?: number[];
  percentiles: {
    p5: number;
    p25: number;
    p50: number;
    p75: number;
    p95: number;
  };
  probability_positive?: number;
  probability_loss_thresholds?: {
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
  statistics?: {
    mean: number;
    std: number;
    min: number;
    max: number;
    median: number;
  };
  probability_statements?: string[];
  parameters?: {
    expected_return: number;
    risk: number;
    num_simulations: number;
    time_horizon_years: number;
  };
}

export interface QualityScoreResult {
  composite_score: number;
  rating: string;
  rating_color?: string;
  factor_breakdown?: {
    risk_profile_compliance?: {
      score: number;
      weight?: number;
      label?: string;
      description?: string;
    };
    sortino_ratio?: {
      score: number;
      raw_value?: number;
      weight?: number;
      label?: string;
      description?: string;
    };
    diversification?: {
      score: number;
      weight?: number;
      label?: string;
      description?: string;
    };
    consistency?: {
      score: number;
      weight?: number;
      label?: string;
      description?: string;
    };
  };
  weights_used?: Record<string, number>;
}

export interface TripleOptimizationResponse {
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
      metrics: { expected_return: number; risk: number; sharpe_ratio: number };
    };
  };
  market_optimized_portfolio: {
    optimized_portfolio: {
      tickers: string[];
      weights: Record<string, number>;
      metrics: { expected_return: number; risk: number; sharpe_ratio: number };
    };
  } | null;
  comparison?: {
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
  optimization_metadata?: {
    recommendation?: "current" | "weights" | "market";
    [key: string]: any;
  };
}

// ---------------------------------------------------------------------------
// Performance Summary Card
// ---------------------------------------------------------------------------

export const PerformanceSummaryCard = ({
  tripleOptimizationResults,
  selectedPortfolio,
  riskProfile,
}: {
  tripleOptimizationResults: TripleOptimizationResponse | null;
  selectedPortfolio: "current" | "weights" | "market";
  riskProfile: string;
}) => {
  if (!tripleOptimizationResults) return null;

  const current = tripleOptimizationResults.current_portfolio?.metrics;
  let selected:
    | { expected_return?: number; risk?: number; sharpe_ratio?: number }
    | undefined;
  let selectedLabel = "Selected";

  if (selectedPortfolio === "weights") {
    selected =
      tripleOptimizationResults.weights_optimized_portfolio?.optimized_portfolio
        ?.metrics;
    selectedLabel = "Weights-Optimized";
  } else if (
    selectedPortfolio === "market" &&
    tripleOptimizationResults.market_optimized_portfolio
  ) {
    selected =
      tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio
        ?.metrics;
    selectedLabel = "Market-Optimized";
  } else {
    selected = current;
    selectedLabel = "Current";
  }

  const returnDiff =
    (selected?.expected_return ?? 0) - (current?.expected_return ?? 0);
  const riskDiff = (selected?.risk ?? 0) - (current?.risk ?? 0);
  const sharpeDiff =
    (selected?.sharpe_ratio ?? 0) - (current?.sharpe_ratio ?? 0);

  const riskProfileMaxRisk: Record<string, number> = {
    "very-conservative": 0.18,
    conservative: 0.25,
    moderate: 0.32,
    aggressive: 0.35,
    "very-aggressive": 0.47,
  };
  const maxRisk = riskProfileMaxRisk[riskProfile] || 0.32;
  const selectedRisk = selected?.risk ?? 0;
  const isCompliant = selectedRisk <= maxRisk;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Performance Summary</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
          <div className="p-4 rounded-lg bg-muted/50 border border-border flex-1 min-w-0">
            <div className="text-sm font-medium text-muted-foreground mb-2">
              Current → {selectedLabel}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Return</span>
                <span
                  className={`font-semibold text-sm ${returnDiff >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                >
                  {returnDiff >= 0 ? "+" : ""}
                  {(returnDiff * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Risk</span>
                <span
                  className={`font-semibold text-sm ${riskDiff <= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                >
                  {riskDiff <= 0 ? "" : "+"}
                  {(riskDiff * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Sharpe</span>
                <span
                  className={`font-semibold text-sm ${sharpeDiff >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                >
                  {sharpeDiff >= 0 ? "+" : ""}
                  {sharpeDiff.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 border border-border flex-1 min-w-0">
            <div className="text-sm font-medium text-muted-foreground mb-2">
              Risk Profile Compliance
            </div>
            <div className="grid grid-cols-3 gap-3 items-center">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">
                  Max Allowed
                </span>
                <span className="font-semibold text-sm text-primary">
                  {(maxRisk * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Your Risk</span>
                <span
                  className={`font-semibold text-sm ${isCompliant ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                >
                  {(selectedRisk * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">Status</span>
                <Badge
                  variant={isCompliant ? "default" : "destructive"}
                  className={
                    isCompliant ? "bg-green-600 dark:bg-green-700" : ""
                  }
                >
                  {isCompliant ? "Compliant" : "Over Limit"}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ---------------------------------------------------------------------------
// Quality Score Card
// ---------------------------------------------------------------------------

const getScoreColor = (score: number) => {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
};

const getScoreBarColor = (score: number) => {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#3b82f6";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
};

export const QualityScoreCard = ({
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
  selectedPortfolio: "current" | "weights" | "market";
  isTriple: boolean;
}) => {
  const tripleQuality = qualityData as {
    current: QualityScoreResult;
    weights: QualityScoreResult;
    market?: QualityScoreResult | null;
  };
  const selectedData =
    selectedPortfolio === "market" && tripleQuality.market
      ? tripleQuality.market
      : selectedPortfolio === "weights"
        ? tripleQuality.weights
        : tripleQuality.current;

  const score = selectedData.composite_score;
  const rating = selectedData.rating || "N/A";

  const factors = [
    {
      name:
        selectedData.factor_breakdown?.risk_profile_compliance?.label ||
        "Risk Profile Compliance",
      score: selectedData.factor_breakdown?.risk_profile_compliance?.score ?? 0,
      description:
        selectedData.factor_breakdown?.risk_profile_compliance?.description ||
        "How well the portfolio matches your risk profile",
      icon: Shield,
    },
    {
      name:
        selectedData.factor_breakdown?.sortino_ratio?.label ||
        "Downside Protection",
      score: selectedData.factor_breakdown?.sortino_ratio?.score ?? 0,
      description:
        selectedData.factor_breakdown?.sortino_ratio?.description ||
        "Resilience during market downturns",
      icon: TrendingDown,
    },
    {
      name:
        selectedData.factor_breakdown?.diversification?.label ||
        "Diversification",
      score: selectedData.factor_breakdown?.diversification?.score ?? 0,
      description:
        selectedData.factor_breakdown?.diversification?.description ||
        "Spread of risk across different assets",
      icon: Activity,
    },
    {
      name: selectedData.factor_breakdown?.consistency?.label || "Consistency",
      score: selectedData.factor_breakdown?.consistency?.score ?? 0,
      description:
        selectedData.factor_breakdown?.consistency?.description ||
        "Stability and predictability of returns",
      icon: LineChart,
    },
  ];

  return (
    <Card className="border-2 border-purple-200">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Award className="h-5 w-5 text-purple-600" />
          Multi-Factor Quality Analysis
        </CardTitle>
        <p className="text-sm text-gray-500">
          Comprehensive portfolio quality assessment
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center gap-6">
          <div className="relative w-32 h-32">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="#e5e7eb"
                strokeWidth="12"
                fill="none"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke={getScoreBarColor(score)}
                strokeWidth="12"
                fill="none"
                strokeDasharray={`${(score / 100) * 351.86} 351.86`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
                  {score.toFixed(0)}
                </div>
                <div className="text-xs text-gray-500">out of 100</div>
              </div>
            </div>
          </div>
          <div className="flex-1">
            <div className="mb-2">
              <Badge
                className="text-sm px-3 py-1"
                style={{ backgroundColor: getScoreBarColor(score) }}
              >
                {rating}
              </Badge>
            </div>
            <h3 className="text-xl font-bold mb-1">Composite Quality Score</h3>
            <p className="text-sm text-gray-600">
              Your portfolio scores {score.toFixed(0)}/100 across all quality
              factors
            </p>
          </div>
        </div>
        <div className="space-y-4">
          <h4 className="font-semibold text-sm text-gray-700 flex items-center gap-2">
            <Info className="h-4 w-4" />
            Factor Breakdown
          </h4>
          {factors.map((factor) => {
            const Icon = factor.icon;
            return (
              <div key={factor.name} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 group relative">
                    <Icon className="h-4 w-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">
                      {factor.name}
                    </span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          {factor.description}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <span
                    className={`text-sm font-bold ${getScoreColor(factor.score)}`}
                  >
                    {factor.score.toFixed(0)}/100
                  </span>
                </div>
                <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="absolute top-0 left-0 h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${factor.score}%`,
                      backgroundColor: getScoreBarColor(factor.score),
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 italic">
                  {factor.description}
                </p>
              </div>
            );
          })}
        </div>
        {isTriple && tripleQuality.market != null && (
          <div className="pt-4 border-t border-gray-200">
            <h4 className="font-semibold text-sm text-gray-700 mb-3">
              Quality Score Comparison
            </h4>
            <div className="grid grid-cols-3 gap-3">
              <div
                className={`p-3 rounded-lg border-2 ${selectedPortfolio === "current" ? "border-red-500 bg-red-50" : "border-gray-200"}`}
              >
                <div className="text-xs text-gray-600 mb-1">Current</div>
                <div className="text-lg font-bold text-red-600">
                  {tripleQuality.current.composite_score.toFixed(0)}
                </div>
              </div>
              <div
                className={`p-3 rounded-lg border-2 ${selectedPortfolio === "weights" ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}
              >
                <div className="text-xs text-gray-600 mb-1">Weights-Opt</div>
                <div className="text-lg font-bold text-blue-600">
                  {tripleQuality.weights.composite_score.toFixed(0)}
                </div>
              </div>
              <div
                className={`p-3 rounded-lg border-2 ${selectedPortfolio === "market" ? "border-green-500 bg-green-50" : "border-gray-200"}`}
              >
                <div className="text-xs text-gray-600 mb-1">Market-Opt</div>
                <div className="text-lg font-bold text-green-600">
                  {tripleQuality.market.composite_score.toFixed(0)}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ---------------------------------------------------------------------------
// Monte Carlo Card (with internal state for visibility and scenario selection)
// ---------------------------------------------------------------------------

export const MonteCarloCard = ({
  monteCarloData,
  selectedPortfolio,
  isTriple,
}: {
  monteCarloData: {
    current: MonteCarloResult;
    weights: MonteCarloResult;
    market?: MonteCarloResult | null;
  };
  selectedPortfolio: "current" | "weights" | "market";
  isTriple: boolean;
}) => {
  const [returnScenarioVisibility, setReturnScenarioVisibility] = useState({
    current: true,
    weights: true,
    market: true,
  });
  const [selectedReturnScenario, setSelectedReturnScenario] = useState<
    string | null
  >(null);

  const selectedMonteCarlo =
    selectedPortfolio === "current"
      ? monteCarloData.current
      : selectedPortfolio === "weights"
        ? monteCarloData.weights
        : monteCarloData.market || monteCarloData.weights;

  const selectedLabel = isTriple
    ? selectedPortfolio === "current"
      ? "Current Portfolio"
      : selectedPortfolio === "weights"
        ? "Weights-Optimized"
        : "Market-Optimized"
    : selectedPortfolio === "current"
      ? "Current Portfolio"
      : "Optimized Portfolio";

  const selectedColor = isTriple
    ? selectedPortfolio === "current"
      ? "red"
      : selectedPortfolio === "weights"
        ? "blue"
        : "green"
    : selectedPortfolio === "current"
      ? "red"
      : "green";

  const selectedStroke =
    selectedColor === "red"
      ? "#ef4444"
      : selectedColor === "blue"
        ? "#3b82f6"
        : "#22c55e";

  const var95 = selectedMonteCarlo.percentiles?.p5 ?? 0;
  const expectedReturn = selectedMonteCarlo.percentiles?.p50 ?? 0;
  const bestCase = selectedMonteCarlo.percentiles?.p95 ?? 0;

  const tripleMonteCarlo = monteCarloData;

  let allData: Array<{ return_pct: number }> = [];
  if (isTriple) {
    if (
      returnScenarioVisibility.current &&
      tripleMonteCarlo.current.histogram_data
    ) {
      allData = allData.concat(tripleMonteCarlo.current.histogram_data);
    }
    if (
      returnScenarioVisibility.weights &&
      tripleMonteCarlo.weights.histogram_data
    ) {
      allData = allData.concat(tripleMonteCarlo.weights.histogram_data);
    }
    if (
      returnScenarioVisibility.market &&
      tripleMonteCarlo.market?.histogram_data
    ) {
      allData = allData.concat(tripleMonteCarlo.market.histogram_data);
    }
  } else {
    allData = selectedMonteCarlo.histogram_data || [];
  }
  const minReturn =
    allData.length > 0 ? Math.min(...allData.map((d) => d.return_pct)) : 0;
  const maxReturn =
    allData.length > 0 ? Math.max(...allData.map((d) => d.return_pct)) : 100;

  const toggleVisibility = (portfolio: "current" | "weights" | "market") => {
    setReturnScenarioVisibility((prev) => ({
      ...prev,
      [portfolio]: !prev[portfolio],
    }));
  };

  const scenarios = [
    { label: "Worst Case (5th percentile)", key: "p5", color: "#ef4444" },
    { label: "Pessimistic (25th percentile)", key: "p25", color: "#f59e0b" },
    { label: "Expected (50th percentile)", key: "p50", color: "#3b82f6" },
    { label: "Optimistic (75th percentile)", key: "p75", color: "#22c55e" },
    { label: "Best Case (95th percentile)", key: "p95", color: "#10b981" },
  ];

  return (
    <Card className="border-2 border-blue-200">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-600" />
          Monte Carlo Risk Analysis
        </CardTitle>
        <p className="text-sm text-gray-500">
          {selectedMonteCarlo.parameters?.num_simulations?.toLocaleString() ||
            "10,000"}{" "}
          simulations projecting{" "}
          {(selectedMonteCarlo.parameters?.time_horizon_years ?? 1) === 1
            ? "1-year"
            : `${selectedMonteCarlo.parameters?.time_horizon_years} year`}{" "}
          return distribution
        </p>
        {selectedMonteCarlo.parameters && (
          <p className="text-xs text-muted-foreground mt-1">
            Assumptions: expected return{" "}
            {(selectedMonteCarlo.parameters.expected_return * 100).toFixed(1)}%,
            volatility {(selectedMonteCarlo.parameters.risk * 100).toFixed(1)}%
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Return distribution comparison: same standard as Analysis tab (PortfolioOptimization) */}
        {isTriple &&
        tripleMonteCarlo.current?.percentiles != null &&
        tripleMonteCarlo.weights?.percentiles != null ? (
          <>
            <div className="text-sm font-medium text-gray-700 mb-2">
              Return distribution comparison (5th, 50th, 95th percentiles)
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border border-border rounded-lg">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left p-2 font-medium border-b border-border rounded-tl-lg">
                      Percentile
                    </th>
                    <th className="text-center p-2 font-medium border-b border-border text-red-700">
                      Current
                    </th>
                    <th className="text-center p-2 font-medium border-b border-border text-blue-700">
                      Weights-Opt
                    </th>
                    {tripleMonteCarlo.market?.percentiles != null && (
                      <th className="text-center p-2 font-medium border-b border-border text-green-700 rounded-tr-lg">
                        Market-Opt
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-border">
                    <td className="p-2 text-muted-foreground">
                      5th (worst 5%)
                    </td>
                    <td className="p-2 text-center font-medium text-red-800">
                      {(
                        (tripleMonteCarlo.current.percentiles?.p5 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    <td className="p-2 text-center font-medium text-blue-800">
                      {(
                        (tripleMonteCarlo.weights.percentiles?.p5 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    {tripleMonteCarlo.market?.percentiles != null && (
                      <td className="p-2 text-center font-medium text-green-800">
                        {(
                          (tripleMonteCarlo.market.percentiles?.p5 ?? 0) * 100
                        ).toFixed(1)}
                        %
                      </td>
                    )}
                  </tr>
                  <tr className="border-b border-border">
                    <td className="p-2 text-muted-foreground">50th (median)</td>
                    <td className="p-2 text-center font-medium text-red-800">
                      {(
                        (tripleMonteCarlo.current.percentiles?.p50 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    <td className="p-2 text-center font-medium text-blue-800">
                      {(
                        (tripleMonteCarlo.weights.percentiles?.p50 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    {tripleMonteCarlo.market?.percentiles != null && (
                      <td className="p-2 text-center font-medium text-green-800">
                        {(
                          (tripleMonteCarlo.market.percentiles?.p50 ?? 0) * 100
                        ).toFixed(1)}
                        %
                      </td>
                    )}
                  </tr>
                  <tr>
                    <td className="p-2 text-muted-foreground rounded-bl-lg">
                      95th (best 5%)
                    </td>
                    <td className="p-2 text-center font-medium text-red-800">
                      {(
                        (tripleMonteCarlo.current.percentiles?.p95 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    <td className="p-2 text-center font-medium text-blue-800">
                      {(
                        (tripleMonteCarlo.weights.percentiles?.p95 ?? 0) * 100
                      ).toFixed(1)}
                      %
                    </td>
                    {tripleMonteCarlo.market?.percentiles != null && (
                      <td className="p-2 text-center font-medium text-green-800 rounded-br-lg">
                        {(
                          (tripleMonteCarlo.market.percentiles?.p95 ?? 0) * 100
                        ).toFixed(1)}
                        %
                      </td>
                    )}
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              Same definitions as in the Example below: 5th = worst 5% of
              outcomes, 50th = median, 95th = best 5%. Expand &quot;How to read
              this&quot; for the 500,000 SEK example for each portfolio.
            </p>
          </>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-red-50 border border-red-200">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <span className="text-xs font-medium text-red-700">
                  5th percentile return (worst 5%)
                </span>
              </div>
              <div className="text-2xl font-bold text-red-800">
                {(var95 * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-red-600 mt-1">
                Worst 5% of simulated outcomes
              </div>
            </div>
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                <span className="text-xs font-medium text-blue-700">
                  Median return (50th percentile)
                </span>
              </div>
              <div className="text-2xl font-bold text-blue-800">
                {(expectedReturn * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-blue-600 mt-1">
                Center of simulated outcomes
              </div>
            </div>
            <div className="p-4 rounded-lg bg-green-50 border border-green-200">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-green-600" />
                <span className="text-xs font-medium text-green-700">
                  Best Case (95%)
                </span>
              </div>
              <div className="text-2xl font-bold text-green-800">
                {(bestCase * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-green-600 mt-1">
                Optimistic scenario
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700">
            Return Distribution
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                <defs>
                  <linearGradient
                    id="fa-colorGradient-red"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
                  </linearGradient>
                  <linearGradient
                    id="fa-colorGradient-blue"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                  </linearGradient>
                  <linearGradient
                    id="fa-colorGradient-green"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="return_pct"
                  type="number"
                  domain={[minReturn, maxReturn]}
                  tickFormatter={(value: number) => `${value.toFixed(0)}%`}
                  tick={{ fontSize: 10 }}
                  label={{
                    value: "Return (%)",
                    position: "bottom",
                    offset: 15,
                    fontSize: 11,
                  }}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickFormatter={(value: number) => `${value.toFixed(0)}%`}
                  label={{
                    value: "Frequency (%)",
                    angle: -90,
                    position: "insideLeft",
                    offset: 5,
                    fontSize: 11,
                  }}
                />
                <RechartsTooltip
                  formatter={(value: number) => [`${value.toFixed(1)}%`, ""]}
                  labelFormatter={(label: number) =>
                    `Return: ${Number(label).toFixed(1)}%`
                  }
                />
                <Legend verticalAlign="top" height={36} />
                {isTriple &&
                  returnScenarioVisibility.current &&
                  tripleMonteCarlo.current.histogram_data && (
                    <Area
                      type="monotone"
                      data={tripleMonteCarlo.current.histogram_data}
                      dataKey="frequency"
                      name="Current Portfolio"
                      stroke="#ef4444"
                      strokeWidth={2}
                      fill="url(#fa-colorGradient-red)"
                    />
                  )}
                {isTriple &&
                  returnScenarioVisibility.weights &&
                  tripleMonteCarlo.weights.histogram_data && (
                    <Area
                      type="monotone"
                      data={tripleMonteCarlo.weights.histogram_data}
                      dataKey="frequency"
                      name="Weights-Optimized"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="url(#fa-colorGradient-blue)"
                    />
                  )}
                {isTriple &&
                  returnScenarioVisibility.market &&
                  tripleMonteCarlo.market?.histogram_data && (
                    <Area
                      type="monotone"
                      data={tripleMonteCarlo.market.histogram_data}
                      dataKey="frequency"
                      name="Market-Optimized"
                      stroke="#22c55e"
                      strokeWidth={2}
                      fill="url(#fa-colorGradient-green)"
                    />
                  )}
                {!isTriple && selectedMonteCarlo.histogram_data && (
                  <Area
                    type="monotone"
                    data={selectedMonteCarlo.histogram_data}
                    dataKey="frequency"
                    name={selectedLabel}
                    stroke={selectedStroke}
                    strokeWidth={2}
                    fill={
                      selectedColor === "red"
                        ? "url(#fa-colorGradient-red)"
                        : selectedColor === "blue"
                          ? "url(#fa-colorGradient-blue)"
                          : "url(#fa-colorGradient-green)"
                    }
                  />
                )}
                {selectedReturnScenario && (
                  <ReferenceLine
                    x={
                      (selectedMonteCarlo.percentiles?.[
                        selectedReturnScenario as
                          | "p5"
                          | "p25"
                          | "p50"
                          | "p75"
                          | "p95"
                      ] ?? 0) * 100
                    }
                    stroke={selectedStroke}
                    strokeWidth={3}
                    strokeDasharray="5 5"
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-muted-foreground">
            Based on a simplified normal-distribution model; real returns can
            have fatter tails.
          </p>
          <Collapsible className="group mt-2 rounded-md border border-border">
            <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-muted/50">
              <span className="flex items-center gap-2">
                <BookOpen className="h-3.5 w-3.5" /> How to read this
              </span>
              <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground space-y-2">
                <p>
                  <strong className="text-foreground">
                    What this simulation shows:
                  </strong>{" "}
                  The chart shows a range of possible{" "}
                  {selectedMonteCarlo.parameters?.time_horizon_years === 1
                    ? "1-year"
                    : `${selectedMonteCarlo.parameters?.time_horizon_years}-year`}{" "}
                  returns based on{" "}
                  {(
                    selectedMonteCarlo.parameters?.num_simulations ?? 10000
                  ).toLocaleString()}{" "}
                  simulations. Outcomes are hypothetical, not forecasts.
                </p>
                <p>
                  <strong className="text-foreground">How to interpret:</strong>{" "}
                  Each area is the share of simulations in that return range.
                  The 5th percentile is worse than 5% of outcomes. These
                  illustrate uncertainty under the model.
                </p>
                {isTriple && (
                  <>
                    <p>
                      <strong className="text-foreground">
                        Why the distributions differ:
                      </strong>{" "}
                      Each portfolio has a different mix of expected return and
                      risk (volatility). Current Portfolio uses your actual
                      holdings; Weights-Optimized adjusts weights within your
                      chosen assets; Market-Optimized uses a different asset
                      mix. A curve shifted right means higher expected return; a
                      wider curve means more volatility and a wider range of
                      outcomes.
                    </p>
                    <p>
                      <strong className="text-foreground">
                        How to compare them:
                      </strong>{" "}
                      Compare the 5th percentile (downside) and the median to
                      see trade-offs: one portfolio may have higher average
                      return but worse downside, or the opposite. Use this to
                      see whether optimization improves expected return, reduces
                      risk, or both, relative to your current portfolio.
                    </p>
                  </>
                )}
                <p>
                  <strong className="text-foreground">Example:</strong> Using
                  500,000 SEK and the 5th percentile (worst 5% of outcomes) for
                  each portfolio:
                </p>
                {isTriple
                  ? (() => {
                      const rows = [
                        {
                          label: "Current portfolio",
                          p5: tripleMonteCarlo.current?.percentiles?.p5,
                        },
                        {
                          label: "Weights-Optimized",
                          p5: tripleMonteCarlo.weights?.percentiles?.p5,
                        },
                        {
                          label: "Market-Optimized",
                          p5: tripleMonteCarlo.market?.percentiles?.p5,
                        },
                      ].filter((r) => r.p5 !== undefined) as Array<{
                        label: string;
                        p5: number;
                      }>;
                      if (rows.length === 0) {
                        const p5 = selectedMonteCarlo.percentiles?.p5 ?? -0.15;
                        const isLoss = p5 < 0;
                        const cap = 500000;
                        return (
                          <p>
                            {isLoss
                              ? `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, in about 1 in 20 runs you could see a loss of ${Math.round(cap * Math.abs(p5)).toLocaleString("sv-SE")} SEK or more.`
                              : `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, the worst 5% of outcomes still have a gain (no loss); the downside is a return of ${(p5 * 100).toFixed(1)}%.`}
                          </p>
                        );
                      }
                      return (
                        <ul className="list-disc list-inside space-y-1 mt-1">
                          {rows.map(({ label, p5 }) => {
                            const isLoss = p5 < 0;
                            const cap = 500000;
                            return (
                              <li key={label}>
                                <strong className="text-foreground">
                                  {label}:
                                </strong>{" "}
                                {isLoss
                                  ? `5th percentile ${(p5 * 100).toFixed(1)}%. In about 1 in 20 runs you could see a loss of ${Math.round(cap * Math.abs(p5)).toLocaleString("sv-SE")} SEK or more.`
                                  : `5th percentile ${(p5 * 100).toFixed(1)}%. In the worst 5% of outcomes you would still have a gain (no loss); the downside is a return of ${(p5 * 100).toFixed(1)}%.`}
                              </li>
                            );
                          })}
                        </ul>
                      );
                    })()
                  : (() => {
                      const p5 = selectedMonteCarlo.percentiles?.p5 ?? -0.15;
                      const isLoss = p5 < 0;
                      const cap = 500000;
                      return (
                        <p>
                          {isLoss
                            ? `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, in about 1 in 20 runs you could see a loss of ${Math.round(cap * Math.abs(p5)).toLocaleString("sv-SE")} SEK or more.`
                            : `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, the worst 5% of outcomes still have a gain (no loss); the downside is a return of ${(p5 * 100).toFixed(1)}%.`}
                        </p>
                      );
                    })()}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>

        {isTriple && (
          <div className="flex flex-wrap gap-2 justify-center border-b pb-3">
            <button
              type="button"
              onClick={() => toggleVisibility("current")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                returnScenarioVisibility.current
                  ? "border-red-300 bg-red-50 hover:bg-red-100"
                  : "border-gray-200 bg-gray-100 opacity-50"
              }`}
              title={
                returnScenarioVisibility.current
                  ? "Hide Current Portfolio"
                  : "Show Current Portfolio"
              }
            >
              {returnScenarioVisibility.current ? (
                <Eye className="h-4 w-4 text-red-600" />
              ) : (
                <EyeOff className="h-4 w-4 text-gray-500" />
              )}
              <div className="w-3 h-3 rounded-full bg-red-600" />
              <span className="font-medium text-red-700">Current</span>
            </button>
            <button
              type="button"
              onClick={() => toggleVisibility("weights")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                returnScenarioVisibility.weights
                  ? "border-blue-300 bg-blue-50 hover:bg-blue-100"
                  : "border-gray-200 bg-gray-100 opacity-50"
              }`}
              title={
                returnScenarioVisibility.weights
                  ? "Hide Weights-Optimized"
                  : "Show Weights-Optimized"
              }
            >
              {returnScenarioVisibility.weights ? (
                <Eye className="h-4 w-4 text-blue-600" />
              ) : (
                <EyeOff className="h-4 w-4 text-gray-500" />
              )}
              <div className="w-3 h-3 rounded-full bg-blue-600" />
              <span className="font-medium text-blue-700">Weights-Opt</span>
            </button>
            {tripleMonteCarlo.market && (
              <button
                type="button"
                onClick={() => toggleVisibility("market")}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                  returnScenarioVisibility.market
                    ? "border-green-300 bg-green-50 hover:bg-green-100"
                    : "border-gray-200 bg-gray-100 opacity-50"
                }`}
                title={
                  returnScenarioVisibility.market
                    ? "Hide Market-Optimized"
                    : "Show Market-Optimized"
                }
              >
                {returnScenarioVisibility.market ? (
                  <Eye className="h-4 w-4 text-green-600" />
                ) : (
                  <EyeOff className="h-4 w-4 text-gray-500" />
                )}
                <div className="w-3 h-3 rounded-full bg-green-600" />
                <span className="font-medium text-green-700">Market-Opt</span>
              </button>
            )}
          </div>
        )}

        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700">
            Return Scenarios
          </div>
          <div className="space-y-2">
            {scenarios.map((scenario) => {
              const scenarioKey = scenario.key as
                | "p5"
                | "p25"
                | "p50"
                | "p75"
                | "p95";
              const value = selectedMonteCarlo.percentiles?.[scenarioKey] ?? 0;
              const isSelected = selectedReturnScenario === scenario.key;
              return (
                <button
                  key={scenario.key}
                  type="button"
                  onClick={() =>
                    setSelectedReturnScenario(isSelected ? null : scenario.key)
                  }
                  className={`w-full flex items-center gap-3 p-2 rounded-lg border-2 transition-all text-left ${
                    isSelected
                      ? "bg-blue-50 border-blue-400 shadow-md"
                      : "bg-gray-50 border-gray-200 hover:border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: scenario.color }}
                  />
                  <div className="flex-1 text-sm text-gray-700">
                    {scenario.label}
                  </div>
                  <div
                    className="text-sm font-bold"
                    style={{ color: scenario.color }}
                  >
                    {(value * 100).toFixed(1)}%
                  </div>
                  {isSelected && (
                    <div className="text-xs text-blue-600 font-semibold">
                      Selected
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700 flex items-center gap-1">
            Loss Probability Scenarios
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 text-gray-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  Probability of portfolio losses exceeding thresholds over 1
                  year (Monte Carlo).
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-red-50 border border-red-200">
              <div className="text-xs font-medium text-red-700 mb-2">
                10% Loss Threshold
              </div>
              <div className="text-2xl font-bold text-red-800">
                {selectedMonteCarlo.probability_loss_thresholds?.loss_10pct?.toFixed(
                  1,
                ) ?? 0}
                %
              </div>
              <div className="text-xs text-red-600 mt-1">
                Probability of 10%+ loss
              </div>
            </div>
            <div className="p-3 rounded-lg bg-red-50 border border-red-200">
              <div className="text-xs font-medium text-red-700 mb-2">
                20% Loss Threshold
              </div>
              <div className="text-2xl font-bold text-red-800">
                {selectedMonteCarlo.probability_loss_thresholds?.loss_20pct?.toFixed(
                  1,
                ) ?? 0}
                %
              </div>
              <div className="text-xs text-red-600 mt-1">
                Probability of 20%+ loss
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="font-medium text-blue-900 mb-2">
                Risk Assessment
              </div>
              <div className="text-sm text-blue-800 space-y-1">
                <p>
                  • Probability of positive returns:{" "}
                  <span className="font-semibold">
                    {selectedMonteCarlo.probability_positive?.toFixed(1) ?? 0}%
                  </span>
                </p>
                <p>
                  • Expected return range:{" "}
                  <span className="font-semibold">
                    {((selectedMonteCarlo.percentiles?.p25 ?? 0) * 100).toFixed(
                      1,
                    )}
                    %
                  </span>{" "}
                  to{" "}
                  <span className="font-semibold">
                    {((selectedMonteCarlo.percentiles?.p75 ?? 0) * 100).toFixed(
                      1,
                    )}
                    %
                  </span>
                </p>
                <p>
                  • 5th percentile return (worst 5% of outcomes):{" "}
                  <span className="font-semibold">
                    {(var95 * 100).toFixed(1)}%
                  </span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
