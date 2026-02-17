/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import {
  LineChart,
  AreaChart,
  BarChart,
  ComposedChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Line,
  Area,
  Bar,
  ReferenceDot,
  ReferenceLine,
} from "recharts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Shield,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Info,
  BarChart3,
  Activity,
  AlertCircle,
  Building2,
  Calendar,
  FileText,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import { ScenarioSelector, type ScenarioId } from "./ScenarioSelector";
import { ResilienceScore } from "./ResilienceScore";
import { TimelineScrollReveal } from "./TimelineScrollReveal";

interface SelectedPortfolioData {
  source: "current" | "weights" | "market";
  tickers: string[];
  weights: Record<string, number>;
  metrics: {
    expected_return: number;
    risk: number;
    sharpe_ratio: number;
  };
}

interface StressTestProps {
  onNext: () => void;
  onPrev: () => void;
  selectedPortfolio: SelectedPortfolioData | null;
  capital: number;
  riskProfile: string;
}

export const StressTest: React.FC<StressTestProps> = ({
  onNext,
  onPrev,
  selectedPortfolio,
  capital,
  riskProfile,
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(
    "covid19",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStep, setLoadingStep] = useState("");
  const [stressTestResults, setStressTestResults] = useState<{
    portfolio_summary: any;
    scenarios: {
      covid19?: any;
      "2008_crisis"?: any;
    };
    resilience_score: number;
    overall_assessment: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [hypotheticalParams, setHypotheticalParams] = useState({
    scenario_type: "tech_crash",
    market_decline: -30,
    sector_impact: "technology",
    duration_months: 6,
    recovery_rate: "moderate",
  });
  const [marketDeclineInput, setMarketDeclineInput] = useState<string | null>(
    null,
  );
  const [hypotheticalResults, setHypotheticalResults] = useState<any>(null);
  const [hypotheticalLoading, setHypotheticalLoading] = useState(false);
  const [activeView, setActiveView] = useState<
    "overview" | "timeline" | "monte-carlo" | "hypothetical"
  >("overview");
  const [selectedTimelineEvent, setSelectedTimelineEvent] = useState<any>(null);
  // Toggle states for Monte Carlo percentile lines
  const [visiblePercentiles, setVisiblePercentiles] = useState({
    p5: true,
    p25: true,
    p50: true,
    p75: true,
    p95: true,
  });
  // Toggle states for Interactive Timeline legend
  const [visibleEventTypes, setVisibleEventTypes] = useState<{
    crisis: boolean;
    policy: boolean;
    recovery: boolean;
    warning: boolean;
  }>({
    crisis: true,
    policy: true,
    recovery: true,
    warning: true,
  });
  const [showRecoveryThresholds, setShowRecoveryThresholds] = useState(true);
  // Keep Stress Test focused on 4 tabs: Overview, Timeline, Monte Carlo, Scenarios.

  // Cache warm-up: Pre-warm Redis cache when portfolio is available
  React.useEffect(() => {
    if (
      selectedPortfolio &&
      selectedPortfolio.tickers &&
      selectedPortfolio.tickers.length > 0
    ) {
      // Warm cache in background (non-blocking)
      fetch("/api/v1/portfolio/warm-tickers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: selectedPortfolio.tickers }),
      }).catch(() => {
        // Silently fail - cache warm-up is optional
      });
    }
  }, [selectedPortfolio]);

  // Key market events for interactive timeline annotations
  const crisisEvents = {
    covid19: [
      {
        date: "2020-02",
        event: "WHO declares COVID-19 pandemic concerns",
        type: "warning",
      },
      {
        date: "2020-03",
        event: "Fed emergency rate cut to 0%",
        type: "policy",
      },
      {
        date: "2020-03",
        event: "Market circuit breakers triggered 4x",
        type: "crisis",
      },
      {
        date: "2020-04",
        event: "Fed launches $2.3T lending programs",
        type: "policy",
      },
      {
        date: "2020-06",
        event: "Markets recover to pre-crisis levels",
        type: "recovery",
      },
    ],
    "2008_crisis": [
      { date: "2008-03", event: "Bear Stearns collapse", type: "crisis" },
      { date: "2008-09", event: "Lehman Brothers bankruptcy", type: "crisis" },
      {
        date: "2008-10",
        event: "Fed slashes rates, TARP announced",
        type: "policy",
      },
      { date: "2009-03", event: "Market bottom reached", type: "bottom" },
      { date: "2009-06", event: "Recovery begins", type: "recovery" },
    ],
  };

  const handleRunStressTest = async () => {
    if (!selectedPortfolio || !selectedScenario) return;

    // Validation
    if (!selectedPortfolio.tickers || selectedPortfolio.tickers.length < 2) {
      setError("Portfolio must contain at least 2 tickers for stress testing");
      return;
    }

    if (
      !selectedPortfolio.weights ||
      Object.keys(selectedPortfolio.weights).length === 0
    ) {
      setError("Portfolio weights are required for stress testing");
      return;
    }

    setIsLoading(true);
    setError(null);
    setLoadingProgress(0);
    setLoadingStep("Initializing analysis...");

    // Simulate progress updates
    let progressInterval: NodeJS.Timeout | null = setInterval(() => {
      setLoadingProgress((prev) => {
        if (prev < 90) {
          const steps = [
            "Fetching historical data...",
            "Calculating portfolio values...",
            "Analyzing crisis period...",
            "Computing risk metrics...",
            "Running Monte Carlo simulation...",
            "Finalizing results...",
          ];
          const stepIndex = Math.floor((prev / 90) * steps.length);
          setLoadingStep(steps[stepIndex] || "Processing...");
          return prev + 10;
        }
        return prev;
      });
    }, 500);

    try {
      const response = await fetch("/api/v1/portfolio/stress-test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tickers: selectedPortfolio.tickers,
          weights: selectedPortfolio.weights,
          scenarios: [selectedScenario],
          capital: capital,
          risk_profile: riskProfile,
        }),
      });

      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setLoadingProgress(100);
      setLoadingStep("Complete!");

      if (!response.ok) {
        let errorMessage = "Failed to run stress test";
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();

      // Validate response structure
      if (
        !data ||
        !data.scenarios ||
        Object.keys(data.scenarios).length === 0
      ) {
        throw new Error("No scenario results returned from server");
      }

      setStressTestResults(data);
      setActiveScenario(selectedScenario);
    } catch (err: any) {
      console.error("Stress test error:", err);
      setError(
        err.message ||
          "An error occurred while running stress tests. Please try again.",
      );
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setLoadingProgress(0);
      setLoadingStep("");
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        setLoadingProgress(0);
        setLoadingStep("");
      }, 500);
    }
  };

  // Export removed - not needed for one-time stress test flow

  return (
    <div className="max-w-6xl mx-auto p-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            Portfolio Stress Test
          </CardTitle>
          <p className="text-muted-foreground text-sm">
            {stressTestResults
              ? "Results from your stress test analysis"
              : "Select a historical crisis scenario to test your portfolio's resilience"}
          </p>
        </CardHeader>
        <CardContent className="p-4 pt-0 space-y-4 w-full min-w-0">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Scenario Selection */}
          {!stressTestResults && (
            <>
              <ScenarioSelector
                selectedScenario={selectedScenario as ScenarioId | null}
                onSelectScenario={(id) => setSelectedScenario(id)}
                onRunTest={handleRunStressTest}
                isLoading={isLoading}
                loadingProgress={loadingProgress}
                loadingStep={loadingStep}
                runDisabled={!selectedPortfolio}
              />

              {!selectedPortfolio && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Please select a portfolio in the Optimization step before
                    running stress tests.
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}

          {/* Results Display */}
          {stressTestResults && (
            <div className="space-y-6">
              {/* View Tabs */}
              <Tabs
                value={activeView}
                onValueChange={(v) => setActiveView(v as any)}
              >
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger
                    value="overview"
                    className="flex items-center gap-1 text-xs"
                  >
                    <FileText className="h-3 w-3" />
                    Overview
                  </TabsTrigger>
                  <TabsTrigger
                    value="timeline"
                    className="flex items-center gap-1 text-xs"
                  >
                    <Calendar className="h-3 w-3" />
                    Timeline
                  </TabsTrigger>
                  <TabsTrigger
                    value="monte-carlo"
                    className="flex items-center gap-1 text-xs"
                  >
                    <BarChart3 className="h-3 w-3" />
                    Monte Carlo
                  </TabsTrigger>
                  <TabsTrigger
                    value="hypothetical"
                    className="flex items-center gap-1 text-xs"
                  >
                    <AlertTriangle className="h-3 w-3" />
                    Scenarios
                  </TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview" className="space-y-6 mt-6">
                  {/* Portfolio Summary Card */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center justify-between">
                        <span>Portfolio Summary</span>
                        <Badge variant="outline" className="text-xs">
                          {selectedPortfolio!.source === "current"
                            ? "Current Portfolio"
                            : selectedPortfolio!.source === "weights"
                              ? "Weights-Optimized"
                              : "Market-Optimized"}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="mb-4">
                        <div className="text-sm text-gray-600 mb-2">
                          <strong>Tickers:</strong>{" "}
                          {selectedPortfolio!.tickers.join(", ")}
                        </div>
                        <div className="text-xs text-gray-500">
                          Portfolio forwarded from Recommendations tab (
                          {selectedPortfolio!.tickers.length} holdings)
                        </div>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                        {/* Expected Return - same style as mini-lesson (StockSelection) */}
                        <div className="relative overflow-hidden rounded-lg bg-muted p-4 border border-border min-w-0">
                          <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-200 rounded-full -translate-y-8 translate-x-8 opacity-20" />
                          <div className="relative z-10">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <TrendingUp className="h-4 w-4 text-emerald-600" />
                              <span className="text-xs font-medium text-emerald-700">
                                Expected Return
                              </span>
                            </div>
                            <div className="text-2xl font-bold text-emerald-800 mb-0.5">
                              {(
                                selectedPortfolio!.metrics.expected_return * 100
                              ).toFixed(1)}
                              %
                            </div>
                            <div className="text-xs text-emerald-600">
                              Annualized projection
                            </div>
                          </div>
                        </div>
                        {/* Risk Level - same style as mini-lesson */}
                        <div className="relative overflow-hidden rounded-lg bg-muted p-4 border border-border min-w-0">
                          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-200 rounded-full -translate-y-8 translate-x-8 opacity-20" />
                          <div className="relative z-10">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <Shield className="h-4 w-4 text-amber-600" />
                              <span className="text-xs font-medium text-amber-700">
                                Risk (Volatility)
                              </span>
                            </div>
                            <div className="text-2xl font-bold text-amber-800 mb-0.5">
                              {(selectedPortfolio!.metrics.risk * 100).toFixed(
                                1,
                              )}
                              %
                            </div>
                            <div className="text-xs text-amber-600">
                              Volatility measure
                            </div>
                          </div>
                        </div>
                        {/* Sharpe Ratio - same card style, violet */}
                        <div className="relative overflow-hidden rounded-lg bg-muted p-4 border border-border min-w-0">
                          <div className="absolute top-0 right-0 w-16 h-16 bg-violet-200 rounded-full -translate-y-8 translate-x-8 opacity-20" />
                          <div className="relative z-10">
                            <div className="flex items-center gap-1.5 mb-1.5">
                              <BarChart3 className="h-4 w-4 text-violet-600" />
                              <span className="text-xs font-medium text-violet-700">
                                Sharpe Ratio
                              </span>
                            </div>
                            <div className="text-2xl font-bold text-violet-800 mb-0.5">
                              {selectedPortfolio!.metrics.sharpe_ratio.toFixed(
                                2,
                              )}
                            </div>
                            <div className="text-xs text-violet-600">
                              Risk-adjusted return
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <ResilienceScore
                    score={stressTestResults.resilience_score}
                    assessment={stressTestResults.overall_assessment}
                  />

                  {/* Scenario Results - Show based on selected scenario */}
                  {selectedScenario === "covid19" &&
                    stressTestResults.scenarios.covid19 && (
                      <Card className="border-2 border-blue-200">
                        <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <Activity className="h-5 w-5 text-blue-600" />
                            2020 COVID-19 Crash Analysis
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            Period:{" "}
                            {stressTestResults.scenarios.covid19.period.start}{" "}
                            to {stressTestResults.scenarios.covid19.period.end}
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          {/* Key Metrics - Compact Horizontal Layout */}
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-red-50 border border-red-200">
                              <span className="text-xs text-red-700 font-medium">
                                Total Return
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-red-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Total return over the entire crisis period
                                  (from start to end date). Positive values
                                  indicate portfolio growth despite the crisis.
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-red-800">
                                {(
                                  stressTestResults.scenarios.covid19.metrics
                                    .total_return * 100
                                ).toFixed(1)}
                                %
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-orange-50 border border-orange-200">
                              <span className="text-xs text-orange-700 font-medium">
                                Max Drawdown
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-orange-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-sm">
                                  <div className="font-semibold mb-1">
                                    Maximum Drawdown
                                  </div>
                                  <div className="mb-2">
                                    Maximum decline from pre-crisis peak to
                                    crisis trough.
                                  </div>
                                  <div className="mb-1">
                                    <strong>Calculation:</strong> (Trough Value
                                    - Peak Value) / Peak Value
                                  </div>
                                  <div className="mb-1">
                                    <strong>Peak:</strong> Portfolio value at
                                    crisis start (or max before crisis)
                                  </div>
                                  <div className="mb-1">
                                    <strong>Trough:</strong> Minimum value
                                    during crisis period
                                  </div>
                                  <div className="text-muted-foreground italic mt-2">
                                    Only shown if drawdown exceeds 3% threshold
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-orange-800">
                                {(
                                  stressTestResults.scenarios.covid19.metrics
                                    .max_drawdown * 100
                                ).toFixed(1)}
                                %
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-blue-50 border border-blue-200">
                              <span className="text-xs text-blue-700 font-medium">
                                Recovery Time
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-blue-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-sm">
                                  <div className="font-semibold mb-1">
                                    Recovery Time to Peak
                                  </div>
                                  <div className="mb-2">
                                    Time to recover to 100% of pre-crisis peak
                                    value (full recovery).
                                  </div>
                                  <div className="mb-1">
                                    <strong>If Recovered:</strong> Actual months
                                    from trough to peak
                                  </div>
                                  <div className="mb-1">
                                    <strong>If Not Recovered:</strong> Projected
                                    months based on current trajectory
                                    (realistic scenario)
                                  </div>
                                  <div className="mb-1">
                                    <strong>Target:</strong> 100% of peak (full
                                    recovery)
                                  </div>
                                  <div className="text-muted-foreground italic mt-2">
                                    Only calculated if drawdown exceeds 3%
                                    threshold
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-blue-800">
                                {stressTestResults.scenarios.covid19.metrics
                                  .max_drawdown_data?.is_significant
                                  ? stressTestResults.scenarios.covid19.metrics
                                      .recovered
                                    ? `${stressTestResults.scenarios.covid19.metrics.recovery_months} mo`
                                    : stressTestResults.scenarios.covid19
                                          .metrics.trajectory_projections
                                          ?.moderate_months
                                      ? `${stressTestResults.scenarios.covid19.metrics.trajectory_projections.moderate_months.toFixed(1)} mo (proj)`
                                      : "N/A"
                                  : "N/A"}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-purple-50 border border-purple-200">
                              <span className="text-xs text-purple-700 font-medium">
                                Pattern
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-purple-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  V-shaped: Quick recovery (&lt;6 months).
                                  U-shaped: Moderate recovery (6-12 months).
                                  L-shaped: Slow or no recovery (&gt;12 months).
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-purple-800">
                                {stressTestResults.scenarios.covid19.metrics
                                  .max_drawdown_data?.is_significant
                                  ? stressTestResults.scenarios.covid19.metrics.recovery_pattern.replace(
                                      " (projected)",
                                      "",
                                    )
                                  : "N/A"}
                              </span>
                            </div>

                            {stressTestResults.scenarios.covid19.metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios.covid19.metrics
                                .recovery_needed_pct !== undefined && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-amber-50 border border-amber-200">
                                  <span className="text-xs text-amber-700 font-medium">
                                    Recovery Needed
                                  </span>
                                  <UITooltip>
                                    <TooltipTrigger asChild>
                                      <Info className="h-3 w-3 text-amber-500 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-sm">
                                      <div className="font-semibold mb-1">
                                        Recovery Needed
                                      </div>
                                      <div className="mb-2">
                                        Percentage increase needed to restore
                                        portfolio to pre-crisis peak value.
                                      </div>
                                      <div className="mb-1">
                                        <strong>Calculation:</strong> ((Peak
                                        Value - Current Value) / Peak Value) ×
                                        100
                                      </div>
                                      <div className="mb-1">
                                        <strong>Peak:</strong> Portfolio value
                                        at crisis start
                                      </div>
                                      <div className="mb-1">
                                        <strong>Current:</strong> Latest
                                        portfolio value
                                      </div>
                                      <div className="text-muted-foreground italic mt-2">
                                        Only shown if drawdown exceeds 3%
                                        threshold
                                      </div>
                                    </TooltipContent>
                                  </UITooltip>
                                  <span className="text-sm font-bold text-amber-800">
                                    {stressTestResults.scenarios.covid19.metrics.recovery_needed_pct.toFixed(
                                      1,
                                    )}
                                    %
                                  </span>
                                </div>
                              )}

                            {/* Projections - Only show if recovery is needed (recovery_needed_pct > 0) */}
                            {stressTestResults.scenarios.covid19.metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios.covid19.metrics
                                .recovery_needed_pct > 0 &&
                              stressTestResults.scenarios.covid19.metrics
                                .trajectory_projections && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-indigo-50 border border-indigo-200">
                                  <span className="text-xs text-indigo-700 font-medium">
                                    Projections
                                  </span>
                                  <UITooltip>
                                    <TooltipTrigger asChild>
                                      <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-sm">
                                      <div className="font-semibold mb-2">
                                        Trajectory Projections
                                      </div>
                                      <div className="mb-3">
                                        Forward-looking scenarios showing
                                        potential portfolio recovery paths based
                                        on current trends.
                                      </div>

                                      <div className="mb-2">
                                        <strong>📈 Projection Types:</strong>
                                      </div>
                                      <div className="mb-1 text-green-600">
                                        <strong>Positive Values:</strong>{" "}
                                        Portfolio trending upward - expected
                                        growth
                                      </div>
                                      <div className="mb-1 text-red-400">
                                        <strong>Negative Values:</strong>{" "}
                                        Portfolio trending downward - potential
                                        continued decline
                                      </div>
                                      <div className="mb-3 text-muted-foreground">
                                        ⚠️ Negative projections indicate the
                                        portfolio may lose value at this
                                        annualized rate if current trends
                                        continue
                                      </div>

                                      <div className="mb-2">
                                        <strong>🎯 Scenarios:</strong>
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-green-600">
                                          Aggressive (A):
                                        </strong>{" "}
                                        Best-case recovery (fastest)
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-blue-600">
                                          Moderate (M):
                                        </strong>{" "}
                                        Realistic scenario (typical)
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-orange-600">
                                          Conservative (C):
                                        </strong>{" "}
                                        Worst-case recovery (slowest)
                                      </div>

                                      <div className="text-muted-foreground italic mt-3 border-t border-border pt-2">
                                        <strong>💡 Insight:</strong> Use these
                                        projections to understand risk and plan
                                        rebalancing. Negative trends may signal
                                        need for portfolio adjustments.
                                      </div>
                                    </TooltipContent>
                                  </UITooltip>
                                  <span className="text-xs text-green-600 font-medium">
                                    {stressTestResults.scenarios.covid19.metrics
                                      .trajectory_projections.aggressive_months
                                      ? `A:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.aggressive_months.toFixed(1)}`
                                      : "A:N/A"}
                                  </span>
                                  <span className="text-xs text-blue-700 font-bold">
                                    {stressTestResults.scenarios.covid19.metrics
                                      .trajectory_projections.moderate_months
                                      ? `M:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.moderate_months.toFixed(1)}`
                                      : "M:N/A"}
                                  </span>
                                  <span className="text-xs text-orange-600 font-medium">
                                    {stressTestResults.scenarios.covid19.metrics
                                      .trajectory_projections
                                      .conservative_months
                                      ? `C:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.conservative_months.toFixed(1)}`
                                      : "C:N/A"}
                                  </span>
                                </div>
                              )}
                            {/* Show message when portfolio already recovered above peak */}
                            {stressTestResults.scenarios.covid19.metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios.covid19.metrics
                                .recovery_needed_pct <= 0 && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-green-50 border border-green-200">
                                  <CheckCircle className="h-4 w-4 text-green-600" />
                                  <span className="text-xs text-green-700 font-medium">
                                    Already above peak - projections N/A
                                  </span>
                                </div>
                              )}
                          </div>

                          {/* Portfolio Value Timeline Chart */}
                          {stressTestResults.scenarios.covid19
                            .monthly_performance &&
                            stressTestResults.scenarios.covid19
                              .monthly_performance.length > 0 && (
                              <div className="space-y-2">
                                <div className="text-sm font-medium text-center">
                                  Portfolio Value Over Time
                                </div>
                                <div className="text-xs text-muted-foreground text-center">
                                  Value indexed to 100 at scenario start (crisis
                                  and recovery window)
                                </div>
                                <div className="h-64 w-full -ml-4">
                                  <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                  >
                                    {(() => {
                                      // Normalize data so January 2020 starts at 100%
                                      const jan2020Value =
                                        stressTestResults.scenarios.covid19.monthly_performance.find(
                                          (m: any) => m.month === "2020-01",
                                        )?.value || 1.0;
                                      const normalizationFactor =
                                        1.0 / jan2020Value;

                                      // Store recovery peak info for rendering (if it exists)
                                      let recoveryPeakInfo: {
                                        date: string;
                                        value: number;
                                      } | null = null;

                                      let baseData =
                                        stressTestResults.scenarios.covid19.monthly_performance.map(
                                          (m: any) => ({
                                            date: m.month,
                                            value:
                                              (m.value || 0) *
                                              normalizationFactor *
                                              100,
                                            return: (m.return || 0) * 100,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          }),
                                        );

                                      // Find recovery point and truncate chart to show only relevant period
                                      // This prevents showing long periods of stable post-recovery data
                                      const peakValue = 100; // Normalized peak (January 2020 = 100%)
                                      const recoveryIndex = baseData.findIndex(
                                        (d: any) => d.value >= peakValue,
                                      );

                                      // Check if recovery peak exists and find its index
                                      let recoveryPeakIndex = -1;
                                      if (
                                        stressTestResults.scenarios.covid19
                                          .peaks_troughs?.recovery_peak
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios.covid19
                                            .peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        recoveryPeakIndex = baseData.findIndex(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                      }

                                      if (recoveryIndex !== -1) {
                                        // Portfolio recovered - show 3 months after recovery, or up to recovery peak, or up to 24 months total.
                                        // Use at least 12 months when available so the chart doesn't look half-empty.
                                        const minMonths = 12;
                                        const rawEndIndex = Math.min(
                                          recoveryIndex + 3,
                                          recoveryPeakIndex !== -1
                                            ? recoveryPeakIndex + 1
                                            : baseData.length - 1,
                                          baseData.length - 1,
                                          24,
                                        );
                                        const endIndex = Math.max(
                                          rawEndIndex,
                                          Math.min(
                                            minMonths - 1,
                                            baseData.length - 1,
                                          ),
                                        );
                                        baseData = baseData.slice(
                                          0,
                                          Math.min(
                                            endIndex + 1,
                                            baseData.length,
                                          ),
                                        );
                                      } else {
                                        // No recovery found - limit to reasonable length anyway, but include recovery peak if it exists
                                        const maxIndex =
                                          recoveryPeakIndex !== -1
                                            ? Math.max(
                                                recoveryPeakIndex + 1,
                                                Math.min(baseData.length, 24),
                                              )
                                            : Math.min(baseData.length, 24);
                                        baseData = baseData.slice(0, maxIndex);
                                      }

                                      // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                      // This handles cases where dates might be slightly off or missing
                                      if (
                                        stressTestResults.scenarios.covid19
                                          .peaks_troughs?.peak
                                      ) {
                                        const peakDate =
                                          stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(
                                            0,
                                            7,
                                          ) || "";
                                        if (
                                          peakDate &&
                                          !baseData.find(
                                            (d: any) => d.date === peakDate,
                                          )
                                        ) {
                                          // Peak date not in data - find closest month or insert
                                          const peakValue =
                                            (stressTestResults.scenarios.covid19
                                              .peaks_troughs.peak.value || 0) *
                                            normalizationFactor *
                                            100;
                                          baseData.push({
                                            date: peakDate,
                                            value: peakValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }
                                      }

                                      if (
                                        stressTestResults.scenarios.covid19
                                          .peaks_troughs?.trough
                                      ) {
                                        const troughDate =
                                          stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(
                                            0,
                                            7,
                                          ) || "";
                                        if (
                                          troughDate &&
                                          !baseData.find(
                                            (d: any) => d.date === troughDate,
                                          )
                                        ) {
                                          const troughValue =
                                            (stressTestResults.scenarios.covid19
                                              .peaks_troughs.trough.value ||
                                              0) *
                                            normalizationFactor *
                                            100;
                                          baseData.push({
                                            date: troughDate,
                                            value: troughValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }
                                      }

                                      // Ensure recovery peak date exists in chart data for ReferenceDot rendering
                                      if (
                                        stressTestResults.scenarios.covid19
                                          .peaks_troughs?.recovery_peak
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios.covid19
                                            .peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        const recoveryValue =
                                          (stressTestResults.scenarios.covid19
                                            .peaks_troughs.recovery_peak
                                            .value || 0) *
                                          normalizationFactor *
                                          100;

                                        if (
                                          recoveryDate &&
                                          !baseData.find(
                                            (d: any) => d.date === recoveryDate,
                                          )
                                        ) {
                                          // Recovery peak date not in data - insert it
                                          baseData.push({
                                            date: recoveryDate,
                                            value: recoveryValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }

                                        // Store recovery peak info for rendering (check if it's in visible range after truncation)
                                        const recoveryDataPoint = baseData.find(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                        if (recoveryDataPoint) {
                                          recoveryPeakInfo = {
                                            date: recoveryDate,
                                            value: recoveryValue,
                                          };
                                        }
                                      }

                                      // Add trajectory data if available
                                      // Projection lines should start from the end of the portfolio value line
                                      // Convert backend's cumulative values to frontend's normalized percentage format
                                      if (
                                        stressTestResults.scenarios.covid19
                                          .metrics.max_drawdown_data
                                          ?.is_significant &&
                                        stressTestResults.scenarios.covid19
                                          .metrics.trajectory_projections
                                          ?.trajectory_data &&
                                        stressTestResults.scenarios.covid19
                                          .metrics.trajectory_projections
                                          .trajectory_data.length > 0
                                      ) {
                                        const lastDataPoint =
                                          baseData[baseData.length - 1];
                                        const lastDate = lastDataPoint?.date;
                                        const lastValue = lastDataPoint?.value; // This is the last actual portfolio value (already normalized to %)

                                        if (
                                          lastDate &&
                                          lastValue !== null &&
                                          lastValue !== undefined
                                        ) {
                                          const [year, month] = lastDate
                                            .split("-")
                                            .map(Number);

                                          // Get the backend's last value (current_value used for trajectory calculations)
                                          // Backend values are in decimal form (0.95 = 95%), need to normalize to match frontend
                                          const lastBackendValue =
                                            stressTestResults.scenarios.covid19
                                              .monthly_performance[
                                              stressTestResults.scenarios
                                                .covid19.monthly_performance
                                                .length - 1
                                            ]?.value || 1.0;
                                          const backendNormalizedLastValue =
                                            lastBackendValue *
                                            normalizationFactor *
                                            100; // Convert to frontend's normalized %

                                          // Calculate offset to align backend's trajectory starting point with frontend's lastValue
                                          // Backend's trajectory values are cumulative from backend's current_value
                                          // We need to adjust them to start from frontend's lastValue
                                          const valueOffset =
                                            lastValue -
                                            backendNormalizedLastValue;

                                          // Attach trajectory to last actual point so projection lines connect smoothly (no duplicate date)
                                          const lastIdx = baseData.length - 1;
                                          if (lastIdx >= 0) {
                                            baseData[lastIdx].aggressive =
                                              lastValue;
                                            baseData[lastIdx].moderate =
                                              lastValue;
                                            baseData[lastIdx].conservative =
                                              lastValue;
                                          }

                                          // Add future projection points only (backend trajectory_data[0] = 1 month ahead, etc.)
                                          stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.forEach(
                                            (point: any, idx: number) => {
                                              if (idx === 0) return; // First backend point = 1 month ahead; connector is last actual point

                                              const futureMonth = month + idx;
                                              const futureYear =
                                                year +
                                                Math.floor(
                                                  (futureMonth - 1) / 12,
                                                );
                                              const futureMonthNormalized =
                                                ((futureMonth - 1) % 12) + 1;
                                              const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, "0")}`;

                                              // Convert backend values to frontend normalized percentage
                                              // Backend values are cumulative from its current_value in decimal form
                                              // Normalize them the same way as the actual data, then adjust by offset
                                              const backendAggressive =
                                                (point.aggressive || 0) *
                                                normalizationFactor *
                                                100;
                                              const backendModerate =
                                                (point.moderate || 0) *
                                                normalizationFactor *
                                                100;
                                              const backendConservative =
                                                (point.conservative || 0) *
                                                normalizationFactor *
                                                100;

                                              // Apply offset to align with frontend's lastValue
                                              const aggressiveValue =
                                                backendAggressive + valueOffset;
                                              const moderateValue =
                                                backendModerate + valueOffset;
                                              const conservativeValue =
                                                backendConservative +
                                                valueOffset;

                                              baseData.push({
                                                date: futureDate,
                                                value: null, // No actual value, only projections
                                                return: null,
                                                aggressive: aggressiveValue,
                                                moderate: moderateValue,
                                                conservative: conservativeValue,
                                              });
                                            },
                                          );
                                        }
                                      }

                                      // Update recovery peak info after all data processing to ensure it's in visible range
                                      if (
                                        stressTestResults.scenarios.covid19
                                          .peaks_troughs?.recovery_peak &&
                                        !recoveryPeakInfo
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios.covid19
                                            .peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        const recoveryValue =
                                          (stressTestResults.scenarios.covid19
                                            .peaks_troughs.recovery_peak
                                            .value || 0) *
                                          normalizationFactor *
                                          100;

                                        // Check if recovery date exists in the final chart data (after truncation and projection additions)
                                        const recoveryDataPoint = baseData.find(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                        if (recoveryDataPoint) {
                                          recoveryPeakInfo = {
                                            date: recoveryDate,
                                            value: recoveryValue,
                                          };
                                        }
                                      }

                                      // Calculate dynamic domain based on all data (including projection lines)
                                      // Find min and max from all values: value, aggressive, moderate, conservative
                                      let minValue = Infinity;
                                      let maxValue = -Infinity;

                                      baseData.forEach((d: any) => {
                                        // Check all possible value fields
                                        const values = [
                                          d.value,
                                          d.aggressive,
                                          d.moderate,
                                          d.conservative,
                                        ].filter(
                                          (v) =>
                                            v !== null &&
                                            v !== undefined &&
                                            !isNaN(v),
                                        );

                                        values.forEach((v) => {
                                          if (v < minValue) minValue = v;
                                          if (v > maxValue) maxValue = v;
                                        });
                                      });

                                      // Add padding (10% on each side) and ensure minimum range
                                      const padding = Math.max(
                                        (maxValue - minValue) * 0.1,
                                        5,
                                      );
                                      const calculatedMin = Math.max(
                                        0,
                                        Math.floor(minValue - padding),
                                      );
                                      const calculatedMax = Math.ceil(
                                        maxValue + padding,
                                      );

                                      const calculatedDomain: [number, number] =
                                        [calculatedMin, calculatedMax];

                                      return (
                                        <ComposedChart
                                          data={baseData}
                                          margin={{
                                            left: 10,
                                            right: 10,
                                            top: 10,
                                            bottom: 10,
                                          }}
                                        >
                                          <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="#e5e7eb"
                                            horizontal={false}
                                          />
                                          <XAxis
                                            dataKey="date"
                                            tick={{ fontSize: 10 }}
                                            label={{
                                              value: "Month",
                                              position: "insideBottom",
                                              offset: -5,
                                            }}
                                          />
                                          <YAxis
                                            type="number"
                                            tick={{ fontSize: 10 }}
                                            tickFormatter={(value) =>
                                              `${value.toFixed(0)}%`
                                            }
                                            label={{
                                              value: "Portfolio Value (%)",
                                              angle: -90,
                                              position: "left",
                                              offset: 0,
                                              style: { textAnchor: "middle" },
                                            }}
                                            domain={calculatedDomain}
                                            allowDataOverflow={false}
                                            allowDecimals={false}
                                            width={70}
                                          />
                                          <Tooltip
                                            formatter={(
                                              value: number,
                                              name: string,
                                            ) => {
                                              if (
                                                name === "Aggressive" ||
                                                name === "Moderate" ||
                                                name === "Conservative"
                                              ) {
                                                // Trajectory value = portfolio value as % of scenario start (Y-axis), not annualized return
                                                return [
                                                  `${value.toFixed(1)}%`,
                                                  `${name} Trajectory`,
                                                ];
                                              }
                                              return [
                                                `${value.toFixed(1)}%`,
                                                "Portfolio Value",
                                              ];
                                            }}
                                            labelFormatter={(label) =>
                                              `Month: ${label}`
                                            }
                                            content={({
                                              active,
                                              payload,
                                              label,
                                            }) => {
                                              if (
                                                !active ||
                                                !payload ||
                                                !payload.length
                                              )
                                                return null;

                                              return (
                                                <div className="bg-background border rounded-lg p-3 shadow-lg max-w-xs">
                                                  <p className="font-medium text-sm mb-2">{`Month: ${label}`}</p>
                                                  {payload.map(
                                                    (entry, index) => {
                                                      const isTrajectory =
                                                        entry.dataKey ===
                                                          "aggressive" ||
                                                        entry.dataKey ===
                                                          "moderate" ||
                                                        entry.dataKey ===
                                                          "conservative";
                                                      const value =
                                                        entry.value as number;
                                                      const name =
                                                        entry.name as string;

                                                      if (isTrajectory) {
                                                        const belowPeak =
                                                          value < 100;
                                                        return (
                                                          <div
                                                            key={index}
                                                            className="mb-2 last:mb-0"
                                                          >
                                                            <div className="flex items-center gap-2">
                                                              <div
                                                                className="w-3 h-3 rounded-full"
                                                                style={{
                                                                  backgroundColor:
                                                                    entry.color,
                                                                }}
                                                              />
                                                              <span className="font-medium text-sm capitalize">
                                                                {name}{" "}
                                                                Trajectory:
                                                              </span>
                                                              <span
                                                                className={`font-bold ${belowPeak ? "text-amber-600" : "text-green-600"}`}
                                                              >
                                                                {value.toFixed(
                                                                  1,
                                                                )}
                                                                %
                                                              </span>
                                                            </div>
                                                            <div className="text-xs mt-1 text-muted-foreground">
                                                              Projected
                                                              portfolio value at
                                                              this date (100% =
                                                              scenario start).
                                                              {belowPeak
                                                                ? " Below peak."
                                                                : " At or above peak."}
                                                            </div>
                                                          </div>
                                                        );
                                                      } else {
                                                        return (
                                                          <div
                                                            key={index}
                                                            className="flex items-center gap-2"
                                                          >
                                                            <div
                                                              className="w-3 h-3 rounded-full"
                                                              style={{
                                                                backgroundColor:
                                                                  entry.color,
                                                              }}
                                                            />
                                                            <span className="font-medium text-sm">
                                                              {name}:
                                                            </span>
                                                            <span className="font-bold">
                                                              {value.toFixed(1)}
                                                              %
                                                            </span>
                                                          </div>
                                                        );
                                                      }
                                                    },
                                                  )}
                                                </div>
                                              );
                                            }}
                                          />
                                          <Area
                                            type="monotone"
                                            dataKey="value"
                                            stroke="#3b82f6"
                                            strokeWidth={3}
                                            fill="#3b82f6"
                                            fillOpacity={0.35}
                                          />
                                          {/* Recovery Threshold Lines removed from Portfolio Value Over Time - only show in Interactive Timeline */}
                                          {/* Trajectory Projection Lines - Smooth lines starting from end of portfolio value */}
                                          {stressTestResults.scenarios.covid19
                                            .metrics.trajectory_projections
                                            ?.trajectory_data &&
                                            stressTestResults.scenarios.covid19
                                              .metrics.trajectory_projections
                                              .trajectory_data.length > 0 && (
                                              <>
                                                {/* Aggressive Trajectory - Green (fastest recovery) */}
                                                <Line
                                                  dataKey="aggressive"
                                                  stroke="#22c55e"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={1.5}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Aggressive"
                                                />
                                                {/* Moderate Trajectory - Blue (realistic recovery) */}
                                                <Line
                                                  dataKey="moderate"
                                                  stroke="#3b82f6"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={2}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Moderate"
                                                />
                                                {/* Conservative Trajectory - Orange (slowest recovery) */}
                                                <Line
                                                  dataKey="conservative"
                                                  stroke="#f59e0b"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={1.5}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Conservative"
                                                />
                                              </>
                                            )}
                                          {(() => {
                                            // Calculate both peak and trough values first to detect overlap
                                            const jan2020Value =
                                              stressTestResults.scenarios.covid19.monthly_performance.find(
                                                (m: any) =>
                                                  m.month === "2020-01",
                                              )?.value || 1.0;
                                            const normalizationFactor =
                                              1.0 / jan2020Value;

                                            const peak =
                                              stressTestResults.scenarios
                                                .covid19.peaks_troughs?.peak;
                                            const trough =
                                              stressTestResults.scenarios
                                                .covid19.peaks_troughs?.trough;

                                            if (!peak && !trough) return null;

                                            let peakValue = 0;
                                            let troughValue = 0;
                                            let peakDate = "";
                                            let troughDate = "";

                                            if (peak) {
                                              const peakDateFull =
                                                peak.date || "";
                                              peakDate =
                                                peakDateFull.length >= 7
                                                  ? peakDateFull.substring(0, 7)
                                                  : peakDateFull;
                                              // Peak is always at 100% since we normalize to Jan 2020 = 100%
                                              peakValue = 100.0;
                                            }

                                            if (trough) {
                                              const troughDateFull =
                                                trough.date || "";
                                              troughDate =
                                                troughDateFull.length >= 7
                                                  ? troughDateFull.substring(
                                                      0,
                                                      7,
                                                    )
                                                  : troughDateFull;
                                              troughValue =
                                                (trough.value || 0) *
                                                normalizationFactor *
                                                100;
                                            }

                                            return (
                                              <>
                                                {peak && (
                                                  <ReferenceDot
                                                    x={peakDate}
                                                    y={peakValue}
                                                    r={5}
                                                    fill="#22c55e"
                                                    stroke="#fff"
                                                    strokeWidth={2}
                                                  />
                                                )}
                                                {trough && (
                                                  <ReferenceDot
                                                    x={troughDate}
                                                    y={troughValue}
                                                    r={5}
                                                    fill="#ef4444"
                                                    stroke="#fff"
                                                    strokeWidth={2}
                                                  />
                                                )}
                                              </>
                                            );
                                          })()}
                                          {recoveryPeakInfo && (
                                            <ReferenceDot
                                              x={recoveryPeakInfo.date}
                                              y={recoveryPeakInfo.value}
                                              r={5}
                                              fill="#9333ea"
                                              stroke="#fff"
                                              strokeWidth={2}
                                            />
                                          )}
                                        </ComposedChart>
                                      );
                                    })()}
                                  </ResponsiveContainer>
                                </div>
                                {stressTestResults.scenarios.covid19
                                  .peaks_troughs && (
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-center gap-4 text-xs">
                                      {stressTestResults.scenarios.covid19
                                        .peaks_troughs.peak && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow-sm"></div>
                                              <span className="font-medium">
                                                Peak (
                                                {stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Pre-Crisis Peak
                                            </div>
                                            <div className="mb-2">
                                              The highest portfolio value before
                                              the crisis started. This
                                              represents your portfolio's value
                                              at its best point before market
                                              conditions deteriorated.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              Used as baseline for calculating
                                              drawdown and recovery metrics.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                      {stressTestResults.scenarios.covid19
                                        .peaks_troughs.trough && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow-sm"></div>
                                              <span className="font-medium">
                                                Trough (
                                                {stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Crisis Trough
                                            </div>
                                            <div className="mb-2">
                                              The lowest portfolio value during
                                              the crisis period. This is the
                                              worst point your portfolio reached
                                              when market conditions were at
                                              their most adverse.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              The difference between Peak and
                                              Trough determines your Maximum
                                              Drawdown.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                      {stressTestResults.scenarios.covid19
                                        .peaks_troughs.recovery_peak && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div
                                                className="w-4 h-4 rounded-full border-2 border-white shadow-sm"
                                                style={{
                                                  backgroundColor: "#9333ea",
                                                }}
                                              ></div>
                                              <span className="font-medium">
                                                Recovery Peak (
                                                {stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Recovery Peak
                                            </div>
                                            <div className="mb-2">
                                              The highest portfolio value after
                                              the crisis trough, indicating full
                                              recovery. This shows when your
                                              portfolio returned to or exceeded
                                              its pre-crisis peak value.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              Recovery Time is measured from
                                              Trough to Recovery Peak.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                    </div>
                                    <div className="text-xs text-gray-500 text-center italic">
                                      Hover over markers above for detailed
                                      definitions
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                          {/* Understanding this section - explanatory text like Monte Carlo */}
                          <Collapsible className="rounded-lg border border-border bg-muted/30">
                            <CollapsibleTrigger asChild>
                              <button
                                type="button"
                                className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm font-medium hover:bg-muted/50 rounded-lg transition-colors group"
                              >
                                <span className="flex items-center gap-2">
                                  <BookOpen className="h-3.5 w-3.5" />
                                  Understanding this section
                                </span>
                                <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                              </button>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground space-y-2">
                                <p>
                                  <strong className="text-foreground">
                                    What this section shows:
                                  </strong>{" "}
                                  How your current portfolio would have behaved
                                  during the 2020 COVID-19 crash: total return
                                  over the period, maximum drawdown (peak to
                                  trough), recovery time and pattern, and a
                                  month-by-month value chart. Values are
                                  normalized so the start of the scenario (e.g.
                                  Jan 2020) equals 100%.
                                </p>
                                <p>
                                  <strong className="text-foreground">
                                    What the chart is for:
                                  </strong>{" "}
                                  The &quot;Portfolio Value Over Time&quot;
                                  chart shows the crisis and recovery window
                                  only. When recovery was quick, the chart may
                                  show only part of the full width (the rest is
                                  intentionally empty) so you focus on the
                                  drawdown and rebound, not long flat periods
                                  after recovery.
                                </p>
                                <p>
                                  <strong className="text-foreground">
                                    Limitations:
                                  </strong>{" "}
                                  This is a single historical scenario, not a
                                  forecast. Past performance does not guarantee
                                  future results. The Monte Carlo tab
                                  illustrates a range of possible outcomes under
                                  assumed volatility.
                                </p>
                              </div>
                            </CollapsibleContent>
                          </Collapsible>

                          {/* Sector Impact */}
                          {stressTestResults.scenarios.covid19.sector_impact &&
                            stressTestResults.scenarios.covid19.sector_impact
                              .sector_returns &&
                            Object.keys(
                              stressTestResults.scenarios.covid19.sector_impact
                                .sector_returns,
                            ).length > 0 && (
                              <div className="space-y-2">
                                <div className="text-sm font-medium">
                                  Sector Performance During Crisis
                                </div>
                                <div className="h-48 w-full">
                                  <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                  >
                                    <BarChart
                                      data={Object.entries(
                                        stressTestResults.scenarios.covid19
                                          .sector_impact.sector_returns,
                                      ).map(
                                        ([sector, return_pct]: [
                                          string,
                                          any,
                                        ]) => ({
                                          sector:
                                            sector.length > 15
                                              ? sector.substring(0, 15) + "..."
                                              : sector,
                                          return: return_pct * 100,
                                        }),
                                      )}
                                    >
                                      <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#e5e7eb"
                                        horizontal={false}
                                      />
                                      <XAxis
                                        dataKey="sector"
                                        tick={{ fontSize: 10 }}
                                        angle={-45}
                                        textAnchor="end"
                                        height={80}
                                      />
                                      <YAxis
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(value) =>
                                          `${value.toFixed(0)}%`
                                        }
                                      />
                                      <Tooltip
                                        formatter={(value: number) => [
                                          `${value.toFixed(1)}%`,
                                          "Return",
                                        ]}
                                      />
                                      <Bar
                                        dataKey="return"
                                        fill={(entry: any) =>
                                          entry.return >= 0
                                            ? "#22c55e"
                                            : "#ef4444"
                                        }
                                      />
                                    </BarChart>
                                  </ResponsiveContainer>
                                </div>
                              </div>
                            )}
                        </CardContent>
                      </Card>
                    )}

                  {/* 2008 Crisis Scenario Results */}
                  {selectedScenario === "2008_crisis" &&
                    stressTestResults.scenarios["2008_crisis"] && (
                      <Card className="border-2 border-amber-200">
                        <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <Building2 className="h-5 w-5 text-amber-600" />
                            2008 Financial Crisis Analysis
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            Period:{" "}
                            {
                              stressTestResults.scenarios["2008_crisis"].period
                                .start
                            }{" "}
                            to{" "}
                            {
                              stressTestResults.scenarios["2008_crisis"].period
                                .end
                            }
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          {/* Key Metrics - Compact Horizontal Layout (matching COVID-19) */}
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-red-50 border border-red-200">
                              <span className="text-xs text-red-700 font-medium">
                                Total Return
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-red-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Total return over the entire crisis period
                                  (from start to end date). Positive values
                                  indicate portfolio growth despite the crisis.
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-red-800">
                                {(
                                  stressTestResults.scenarios["2008_crisis"]
                                    .metrics.total_return * 100
                                ).toFixed(1)}
                                %
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-orange-50 border border-orange-200">
                              <span className="text-xs text-orange-700 font-medium">
                                Max Drawdown
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-orange-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-sm">
                                  <div className="font-semibold mb-1">
                                    Maximum Drawdown
                                  </div>
                                  <div className="mb-2">
                                    Maximum decline from pre-crisis peak to
                                    crisis trough.
                                  </div>
                                  <div className="mb-1">
                                    <strong>Calculation:</strong> (Trough Value
                                    - Peak Value) / Peak Value
                                  </div>
                                  <div className="mb-1">
                                    <strong>Peak:</strong> Portfolio value at
                                    crisis start (or max before crisis)
                                  </div>
                                  <div className="mb-1">
                                    <strong>Trough:</strong> Minimum value
                                    during crisis period
                                  </div>
                                  <div className="text-muted-foreground italic mt-2">
                                    Only shown if drawdown exceeds 3% threshold
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-orange-800">
                                {(
                                  stressTestResults.scenarios["2008_crisis"]
                                    .metrics.max_drawdown * 100
                                ).toFixed(1)}
                                %
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-blue-50 border border-blue-200">
                              <span className="text-xs text-blue-700 font-medium">
                                Recovery Time
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-blue-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-sm">
                                  <div className="font-semibold mb-1">
                                    Recovery Time to Peak
                                  </div>
                                  <div className="mb-2">
                                    Time to recover to 100% of pre-crisis peak
                                    value (full recovery).
                                  </div>
                                  <div className="mb-1">
                                    <strong>If Recovered:</strong> Actual months
                                    from trough to peak
                                  </div>
                                  <div className="mb-1">
                                    <strong>If Not Recovered:</strong> Projected
                                    months based on current trajectory
                                    (realistic scenario)
                                  </div>
                                  <div className="mb-1">
                                    <strong>Target:</strong> 100% of peak (full
                                    recovery)
                                  </div>
                                  <div className="text-muted-foreground italic mt-2">
                                    Only calculated if drawdown exceeds 3%
                                    threshold
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-blue-800">
                                {stressTestResults.scenarios["2008_crisis"]
                                  .metrics.max_drawdown_data?.is_significant
                                  ? stressTestResults.scenarios["2008_crisis"]
                                      .metrics.recovered
                                    ? `${stressTestResults.scenarios["2008_crisis"].metrics.recovery_months} mo`
                                    : stressTestResults.scenarios["2008_crisis"]
                                          .metrics.trajectory_projections
                                          ?.moderate_months
                                      ? `${stressTestResults.scenarios["2008_crisis"].metrics.trajectory_projections.moderate_months.toFixed(1)} mo (proj)`
                                      : "N/A"
                                  : "N/A"}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-purple-50 border border-purple-200">
                              <span className="text-xs text-purple-700 font-medium">
                                Pattern
                              </span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-purple-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  V-shaped: Quick recovery (&lt;6 months).
                                  U-shaped: Moderate recovery (6-12 months).
                                  L-shaped: Slow or no recovery (&gt;12 months).
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-purple-800">
                                {stressTestResults.scenarios["2008_crisis"]
                                  .metrics.max_drawdown_data?.is_significant
                                  ? stressTestResults.scenarios[
                                      "2008_crisis"
                                    ].metrics.recovery_pattern.replace(
                                      " (projected)",
                                      "",
                                    )
                                  : "N/A"}
                              </span>
                            </div>

                            {stressTestResults.scenarios["2008_crisis"].metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios["2008_crisis"].metrics
                                .recovery_needed_pct !== undefined && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-amber-50 border border-amber-200">
                                  <span className="text-xs text-amber-700 font-medium">
                                    Recovery Needed
                                  </span>
                                  <UITooltip>
                                    <TooltipTrigger asChild>
                                      <Info className="h-3 w-3 text-amber-500 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-sm">
                                      <div className="font-semibold mb-1">
                                        Recovery Needed
                                      </div>
                                      <div className="mb-2">
                                        Percentage increase needed to restore
                                        portfolio to pre-crisis peak value.
                                      </div>
                                      <div className="mb-1">
                                        <strong>Calculation:</strong> ((Peak
                                        Value - Current Value) / Peak Value) ×
                                        100
                                      </div>
                                      <div className="mb-1">
                                        <strong>Peak:</strong> Portfolio value
                                        at crisis start
                                      </div>
                                      <div className="mb-1">
                                        <strong>Current:</strong> Latest
                                        portfolio value
                                      </div>
                                      <div className="text-muted-foreground italic mt-2">
                                        Only shown if drawdown exceeds 3%
                                        threshold
                                      </div>
                                    </TooltipContent>
                                  </UITooltip>
                                  <span className="text-sm font-bold text-amber-800">
                                    {stressTestResults.scenarios[
                                      "2008_crisis"
                                    ].metrics.recovery_needed_pct.toFixed(1)}
                                    %
                                  </span>
                                </div>
                              )}

                            {/* Projections - Only show if recovery is needed (recovery_needed_pct > 0) */}
                            {stressTestResults.scenarios["2008_crisis"].metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios["2008_crisis"].metrics
                                .recovery_needed_pct > 0 &&
                              stressTestResults.scenarios["2008_crisis"].metrics
                                .trajectory_projections && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-indigo-50 border border-indigo-200">
                                  <span className="text-xs text-indigo-700 font-medium">
                                    Projections
                                  </span>
                                  <UITooltip>
                                    <TooltipTrigger asChild>
                                      <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-sm">
                                      <div className="font-semibold mb-2">
                                        Trajectory Projections
                                      </div>
                                      <div className="mb-3">
                                        Forward-looking scenarios showing
                                        potential portfolio recovery paths based
                                        on current trends.
                                      </div>

                                      <div className="mb-2">
                                        <strong>📈 Projection Types:</strong>
                                      </div>
                                      <div className="mb-1 text-green-600">
                                        <strong>Positive Values:</strong>{" "}
                                        Portfolio trending upward - expected
                                        growth
                                      </div>
                                      <div className="mb-1 text-red-400">
                                        <strong>Negative Values:</strong>{" "}
                                        Portfolio trending downward - potential
                                        continued decline
                                      </div>
                                      <div className="mb-3 text-muted-foreground">
                                        ⚠️ Negative projections indicate the
                                        portfolio may lose value at this
                                        annualized rate if current trends
                                        continue
                                      </div>

                                      <div className="mb-2">
                                        <strong>🎯 Scenarios:</strong>
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-green-600">
                                          Aggressive (A):
                                        </strong>{" "}
                                        Best-case recovery (fastest)
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-blue-600">
                                          Moderate (M):
                                        </strong>{" "}
                                        Realistic scenario (typical)
                                      </div>
                                      <div className="mb-1">
                                        <strong className="text-orange-600">
                                          Conservative (C):
                                        </strong>{" "}
                                        Worst-case recovery (slowest)
                                      </div>

                                      <div className="text-muted-foreground italic mt-3 border-t border-border pt-2">
                                        <strong>💡 Insight:</strong> Use these
                                        projections to understand risk and plan
                                        rebalancing. Negative trends may signal
                                        need for portfolio adjustments.
                                      </div>
                                    </TooltipContent>
                                  </UITooltip>
                                  <span className="text-xs text-green-600 font-medium">
                                    {stressTestResults.scenarios["2008_crisis"]
                                      .metrics.trajectory_projections
                                      .aggressive_months
                                      ? `A:${stressTestResults.scenarios["2008_crisis"].metrics.trajectory_projections.aggressive_months.toFixed(1)}`
                                      : "A:N/A"}
                                  </span>
                                  <span className="text-xs text-blue-700 font-bold">
                                    {stressTestResults.scenarios["2008_crisis"]
                                      .metrics.trajectory_projections
                                      .moderate_months
                                      ? `M:${stressTestResults.scenarios["2008_crisis"].metrics.trajectory_projections.moderate_months.toFixed(1)}`
                                      : "M:N/A"}
                                  </span>
                                  <span className="text-xs text-orange-600 font-medium">
                                    {stressTestResults.scenarios["2008_crisis"]
                                      .metrics.trajectory_projections
                                      .conservative_months
                                      ? `C:${stressTestResults.scenarios["2008_crisis"].metrics.trajectory_projections.conservative_months.toFixed(1)}`
                                      : "C:N/A"}
                                  </span>
                                </div>
                              )}
                            {/* Show message when portfolio already recovered above peak */}
                            {stressTestResults.scenarios["2008_crisis"].metrics
                              .max_drawdown_data?.is_significant &&
                              stressTestResults.scenarios["2008_crisis"].metrics
                                .recovery_needed_pct <= 0 && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-green-50 border border-green-200">
                                  <CheckCircle className="h-4 w-4 text-green-600" />
                                  <span className="text-xs text-green-700 font-medium">
                                    Already above peak - projections N/A
                                  </span>
                                </div>
                              )}
                          </div>

                          {/* Portfolio Value Timeline Chart */}
                          {stressTestResults.scenarios["2008_crisis"]
                            .monthly_performance &&
                            stressTestResults.scenarios["2008_crisis"]
                              .monthly_performance.length > 0 && (
                              <div className="space-y-2">
                                <div className="text-sm font-medium text-center">
                                  Portfolio Value Over Time
                                </div>
                                <div className="h-64 w-full -ml-4">
                                  <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                  >
                                    {(() => {
                                      // Normalize data so August 2008 starts at 100% (pre-crisis baseline)
                                      const aug2008Value =
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].monthly_performance.find(
                                          (m: any) => m.month === "2008-08",
                                        )?.value || 1.0;
                                      const normalizationFactor =
                                        1.0 / aug2008Value;

                                      // Store recovery peak info for rendering (if it exists)
                                      let recoveryPeakInfo: {
                                        date: string;
                                        value: number;
                                      } | null = null;

                                      let baseData =
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].monthly_performance.map((m: any) => ({
                                          date: m.month,
                                          value:
                                            (m.value || 0) *
                                            normalizationFactor *
                                            100,
                                          return: (m.return || 0) * 100,
                                          aggressive: null,
                                          moderate: null,
                                          conservative: null,
                                        }));

                                      // Find recovery point and truncate chart to show only relevant period
                                      // CRITICAL: Always show the full crisis period (Sep 2008 - Mar 2010 = 18 months from Aug 2008 baseline)
                                      const peakValue = 100; // Normalized peak (August 2008 = 100%)

                                      // Find crisis end date (2010-03) to ensure we always show full crisis period
                                      const crisisEndDate = "2010-03";
                                      const crisisEndIndex = baseData.findIndex(
                                        (d: any) => d.date === crisisEndDate,
                                      );

                                      // Check if recovery peak exists and find its index
                                      let recoveryPeakIndex = -1;
                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].peaks_troughs?.recovery_peak
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        recoveryPeakIndex = baseData.findIndex(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                      }

                                      const recoveryIndex = baseData.findIndex(
                                        (d: any) => d.value >= peakValue,
                                      );

                                      // Calculate end index ensuring we show at least the full crisis period
                                      let endIndex: number;
                                      if (recoveryIndex !== -1) {
                                        // Portfolio recovered - show recovery + 3 months, but ensure we show full crisis period
                                        const recoveryEndIndex = Math.min(
                                          recoveryIndex + 3, // 3 months after recovery
                                          recoveryPeakIndex !== -1
                                            ? recoveryPeakIndex + 1
                                            : baseData.length - 1, // Include recovery peak if it exists
                                          baseData.length - 1, // Don't exceed available data
                                        );
                                        // Ensure we show at least until crisis end (2010-03) + 3 months for recovery context
                                        const minEndIndex =
                                          crisisEndIndex !== -1
                                            ? crisisEndIndex + 3
                                            : 20; // At least 20 months (crisis + recovery)
                                        endIndex = Math.max(
                                          recoveryEndIndex,
                                          minEndIndex,
                                          20,
                                        ); // Always show at least 20 months
                                        endIndex = Math.min(
                                          endIndex,
                                          baseData.length - 1,
                                          32,
                                        ); // Cap at 32 months (crisis + full recovery period)
                                      } else {
                                        // No recovery found - ensure we show full crisis period + recovery tracking period
                                        const minEndIndex =
                                          crisisEndIndex !== -1
                                            ? crisisEndIndex + 6
                                            : 24; // Crisis end + 6 months recovery tracking
                                        const maxIndex =
                                          recoveryPeakIndex !== -1
                                            ? Math.max(
                                                recoveryPeakIndex + 1,
                                                minEndIndex,
                                              )
                                            : minEndIndex;
                                        endIndex = Math.min(
                                          maxIndex,
                                          baseData.length - 1,
                                          32,
                                        ); // Cap at 32 months
                                      }

                                      baseData = baseData.slice(
                                        0,
                                        endIndex + 1,
                                      );

                                      // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].peaks_troughs?.peak
                                      ) {
                                        const peakDateFull =
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.peak.date || "";
                                        const peakDate =
                                          peakDateFull.length >= 7
                                            ? peakDateFull.substring(0, 7)
                                            : peakDateFull;
                                        if (
                                          peakDate &&
                                          !baseData.find(
                                            (d: any) => d.date === peakDate,
                                          )
                                        ) {
                                          // Peak is always at 100% since we normalize to Aug 2008 = 100%
                                          const peakValue = 100.0;
                                          baseData.push({
                                            date: peakDate,
                                            value: peakValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }
                                      }

                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].peaks_troughs?.trough
                                      ) {
                                        const troughDateFull =
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.trough.date || "";
                                        const troughDate =
                                          troughDateFull.length >= 7
                                            ? troughDateFull.substring(0, 7)
                                            : troughDateFull;
                                        if (
                                          troughDate &&
                                          !baseData.find(
                                            (d: any) => d.date === troughDate,
                                          )
                                        ) {
                                          const troughValue =
                                            (stressTestResults.scenarios[
                                              "2008_crisis"
                                            ].peaks_troughs.trough.value || 0) *
                                            normalizationFactor *
                                            100;
                                          baseData.push({
                                            date: troughDate,
                                            value: troughValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }
                                      }

                                      // Ensure recovery peak date exists in chart data for ReferenceDot rendering
                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].peaks_troughs?.recovery_peak
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        const recoveryValue =
                                          (stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.recovery_peak.value ||
                                            0) *
                                          normalizationFactor *
                                          100;

                                        if (
                                          recoveryDate &&
                                          !baseData.find(
                                            (d: any) => d.date === recoveryDate,
                                          )
                                        ) {
                                          // Recovery peak date not in data - insert it
                                          baseData.push({
                                            date: recoveryDate,
                                            value: recoveryValue,
                                            return: null,
                                            aggressive: null,
                                            moderate: null,
                                            conservative: null,
                                          });
                                          baseData.sort((a: any, b: any) =>
                                            a.date.localeCompare(b.date),
                                          );
                                        }

                                        // Store recovery peak info for rendering (check if it's in visible range after truncation)
                                        const recoveryDataPoint = baseData.find(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                        if (recoveryDataPoint) {
                                          recoveryPeakInfo = {
                                            date: recoveryDate,
                                            value: recoveryValue,
                                          };
                                        }
                                      }

                                      // Add trajectory data if available
                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.max_drawdown_data
                                          ?.is_significant &&
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.trajectory_projections
                                          ?.trajectory_data &&
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.trajectory_projections
                                          .trajectory_data.length > 0
                                      ) {
                                        const lastDataPoint =
                                          baseData[baseData.length - 1];
                                        const lastDate = lastDataPoint?.date;
                                        const lastValue = lastDataPoint?.value;

                                        if (
                                          lastDate &&
                                          lastValue !== null &&
                                          lastValue !== undefined
                                        ) {
                                          const [year, month] = lastDate
                                            .split("-")
                                            .map(Number);

                                          // Get the backend's last value to calculate the offset
                                          // Backend values are in decimal form (0.95 = 95%), need to normalize to match frontend
                                          const lastBackendValue =
                                            stressTestResults.scenarios[
                                              "2008_crisis"
                                            ].monthly_performance[
                                              stressTestResults.scenarios[
                                                "2008_crisis"
                                              ].monthly_performance.length - 1
                                            ]?.value || 1.0;
                                          const backendNormalizedLastValue =
                                            lastBackendValue *
                                            normalizationFactor *
                                            100; // Convert to frontend's normalized %

                                          // Calculate offset to align backend's trajectory starting point with frontend's lastValue
                                          // Backend's trajectory values are cumulative from backend's current_value
                                          // We need to adjust them to start from frontend's lastValue
                                          const valueOffset =
                                            lastValue -
                                            backendNormalizedLastValue;

                                          // Attach trajectory to last actual point so projection lines connect smoothly (same as COVID-19 chart)
                                          const lastIdx = baseData.length - 1;
                                          if (lastIdx >= 0) {
                                            baseData[lastIdx].aggressive =
                                              lastValue;
                                            baseData[lastIdx].moderate =
                                              lastValue;
                                            baseData[lastIdx].conservative =
                                              lastValue;
                                          }

                                          // Add future projection points only (backend trajectory_data[0] = 1 month ahead, etc.)
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].metrics.trajectory_projections.trajectory_data.forEach(
                                            (point: any, idx: number) => {
                                              if (idx === 0) return; // First backend point = 1 month ahead; connector is last actual point

                                              const futureMonth = month + idx;
                                              const futureYear =
                                                year +
                                                Math.floor(
                                                  (futureMonth - 1) / 12,
                                                );
                                              const futureMonthNormalized =
                                                ((futureMonth - 1) % 12) + 1;
                                              const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, "0")}`;

                                              // Convert backend values to frontend normalized percentage
                                              // Backend values are cumulative from its current_value in decimal form
                                              // Normalize them the same way as the actual data, then adjust by offset
                                              const backendAggressive =
                                                (point.aggressive || 0) *
                                                normalizationFactor *
                                                100;
                                              const backendModerate =
                                                (point.moderate || 0) *
                                                normalizationFactor *
                                                100;
                                              const backendConservative =
                                                (point.conservative || 0) *
                                                normalizationFactor *
                                                100;

                                              // Apply offset to align with frontend's lastValue
                                              const aggressiveValue =
                                                backendAggressive + valueOffset;
                                              const moderateValue =
                                                backendModerate + valueOffset;
                                              const conservativeValue =
                                                backendConservative +
                                                valueOffset;

                                              baseData.push({
                                                date: futureDate,
                                                value: null, // No actual value, only projections
                                                return: null,
                                                aggressive: aggressiveValue,
                                                moderate: moderateValue,
                                                conservative: conservativeValue,
                                              });
                                            },
                                          );
                                        }
                                      }

                                      // Update recovery peak info after all data processing to ensure it's in visible range
                                      if (
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].peaks_troughs?.recovery_peak &&
                                        !recoveryPeakInfo
                                      ) {
                                        const recoveryDateFull =
                                          stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.recovery_peak.date ||
                                          "";
                                        const recoveryDate =
                                          recoveryDateFull.length >= 7
                                            ? recoveryDateFull.substring(0, 7)
                                            : recoveryDateFull;
                                        const recoveryValue =
                                          (stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].peaks_troughs.recovery_peak.value ||
                                            0) *
                                          normalizationFactor *
                                          100;

                                        // Check if recovery date exists in the final chart data (after truncation and projection additions)
                                        const recoveryDataPoint = baseData.find(
                                          (d: any) => d.date === recoveryDate,
                                        );
                                        if (recoveryDataPoint) {
                                          recoveryPeakInfo = {
                                            date: recoveryDate,
                                            value: recoveryValue,
                                          };
                                        }
                                      }

                                      // Calculate dynamic domain based on all data (including projection lines)
                                      // Find min and max from all values: value, aggressive, moderate, conservative
                                      let minValue = Infinity;
                                      let maxValue = -Infinity;

                                      baseData.forEach((d: any) => {
                                        // Check all possible value fields
                                        const values = [
                                          d.value,
                                          d.aggressive,
                                          d.moderate,
                                          d.conservative,
                                        ].filter(
                                          (v) =>
                                            v !== null &&
                                            v !== undefined &&
                                            !isNaN(v),
                                        );

                                        values.forEach((v) => {
                                          if (v < minValue) minValue = v;
                                          if (v > maxValue) maxValue = v;
                                        });
                                      });

                                      // Add padding (10% on each side) and ensure minimum range
                                      const padding = Math.max(
                                        (maxValue - minValue) * 0.1,
                                        5,
                                      );
                                      const calculatedMin = Math.max(
                                        0,
                                        Math.floor(minValue - padding),
                                      );
                                      const calculatedMax = Math.ceil(
                                        maxValue + padding,
                                      );

                                      const calculatedDomain: [number, number] =
                                        [calculatedMin, calculatedMax];

                                      return (
                                        <ComposedChart
                                          data={baseData}
                                          margin={{
                                            left: 10,
                                            right: 10,
                                            top: 10,
                                            bottom: 10,
                                          }}
                                        >
                                          <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="#e5e7eb"
                                            horizontal={false}
                                          />
                                          <XAxis
                                            dataKey="date"
                                            tick={{ fontSize: 10 }}
                                            label={{
                                              value: "Month",
                                              position: "insideBottom",
                                              offset: -5,
                                            }}
                                          />
                                          <YAxis
                                            type="number"
                                            tick={{ fontSize: 10 }}
                                            tickFormatter={(value) =>
                                              `${value.toFixed(0)}%`
                                            }
                                            label={{
                                              value: "Portfolio Value (%)",
                                              angle: -90,
                                              position: "left",
                                              offset: 0,
                                              style: { textAnchor: "middle" },
                                            }}
                                            domain={calculatedDomain}
                                            allowDataOverflow={false}
                                            allowDecimals={false}
                                            width={70}
                                          />
                                          <Tooltip
                                            formatter={(
                                              value: number,
                                              name: string,
                                            ) => {
                                              if (
                                                name === "Aggressive" ||
                                                name === "Moderate" ||
                                                name === "Conservative"
                                              ) {
                                                // Trajectory value = portfolio value as % of scenario start (Y-axis), not annualized return
                                                return [
                                                  `${value.toFixed(1)}%`,
                                                  `${name} Trajectory`,
                                                ];
                                              }
                                              return [
                                                `${value.toFixed(1)}%`,
                                                "Portfolio Value",
                                              ];
                                            }}
                                            labelFormatter={(label) =>
                                              `Month: ${label}`
                                            }
                                            content={({
                                              active,
                                              payload,
                                              label,
                                            }) => {
                                              if (
                                                !active ||
                                                !payload ||
                                                !payload.length
                                              )
                                                return null;

                                              return (
                                                <div className="bg-background border rounded-lg p-3 shadow-lg max-w-xs">
                                                  <p className="font-medium text-sm mb-2">{`Month: ${label}`}</p>
                                                  {payload.map(
                                                    (entry, index) => {
                                                      const isTrajectory =
                                                        entry.dataKey ===
                                                          "aggressive" ||
                                                        entry.dataKey ===
                                                          "moderate" ||
                                                        entry.dataKey ===
                                                          "conservative";
                                                      const value =
                                                        entry.value as number;
                                                      const name =
                                                        entry.name as string;

                                                      if (isTrajectory) {
                                                        const belowPeak =
                                                          value < 100;
                                                        return (
                                                          <div
                                                            key={index}
                                                            className="mb-2 last:mb-0"
                                                          >
                                                            <div className="flex items-center gap-2">
                                                              <div
                                                                className="w-3 h-3 rounded-full"
                                                                style={{
                                                                  backgroundColor:
                                                                    entry.color,
                                                                }}
                                                              />
                                                              <span className="font-medium text-sm capitalize">
                                                                {name}{" "}
                                                                Trajectory:
                                                              </span>
                                                              <span
                                                                className={`font-bold ${belowPeak ? "text-amber-600" : "text-green-600"}`}
                                                              >
                                                                {value.toFixed(
                                                                  1,
                                                                )}
                                                                %
                                                              </span>
                                                            </div>
                                                            <div className="text-xs mt-1 text-muted-foreground">
                                                              Projected
                                                              portfolio value at
                                                              this date (100% =
                                                              scenario start).
                                                              {belowPeak
                                                                ? " Below peak."
                                                                : " At or above peak."}
                                                            </div>
                                                          </div>
                                                        );
                                                      } else {
                                                        return (
                                                          <div
                                                            key={index}
                                                            className="flex items-center gap-2"
                                                          >
                                                            <div
                                                              className="w-3 h-3 rounded-full"
                                                              style={{
                                                                backgroundColor:
                                                                  entry.color,
                                                              }}
                                                            />
                                                            <span className="font-medium text-sm">
                                                              {name}:
                                                            </span>
                                                            <span className="font-bold">
                                                              {value.toFixed(1)}
                                                              %
                                                            </span>
                                                          </div>
                                                        );
                                                      }
                                                    },
                                                  )}
                                                </div>
                                              );
                                            }}
                                          />
                                          <Area
                                            type="monotone"
                                            dataKey="value"
                                            stroke="#3b82f6"
                                            strokeWidth={3}
                                            fill="#3b82f6"
                                            fillOpacity={0.35}
                                          />
                                          {/* Recovery Threshold Lines removed from Portfolio Value Over Time - only show in Interactive Timeline */}
                                          {/* Trajectory Projection Lines - Smooth lines starting from end of portfolio value */}
                                          {stressTestResults.scenarios[
                                            "2008_crisis"
                                          ].metrics.trajectory_projections
                                            ?.trajectory_data &&
                                            stressTestResults.scenarios[
                                              "2008_crisis"
                                            ].metrics.trajectory_projections
                                              .trajectory_data.length > 0 && (
                                              <>
                                                {/* Aggressive Trajectory - Green (fastest recovery) */}
                                                <Line
                                                  dataKey="aggressive"
                                                  stroke="#22c55e"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={1.5}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Aggressive"
                                                />
                                                {/* Moderate Trajectory - Blue (realistic recovery) */}
                                                <Line
                                                  dataKey="moderate"
                                                  stroke="#3b82f6"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={2}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Moderate"
                                                />
                                                {/* Conservative Trajectory - Orange (slowest recovery) */}
                                                <Line
                                                  dataKey="conservative"
                                                  stroke="#f59e0b"
                                                  strokeDasharray="4 4"
                                                  strokeWidth={1.5}
                                                  dot={false}
                                                  connectNulls={true}
                                                  type="monotone"
                                                  isAnimationActive={true}
                                                  animationDuration={1200}
                                                  animationEasing="ease-out"
                                                  name="Conservative"
                                                />
                                              </>
                                            )}
                                          {(() => {
                                            // Calculate both peak and trough values first to detect overlap
                                            const aug2008Value =
                                              stressTestResults.scenarios[
                                                "2008_crisis"
                                              ].monthly_performance.find(
                                                (m: any) =>
                                                  m.month === "2008-08",
                                              )?.value || 1.0;
                                            const normalizationFactor =
                                              1.0 / aug2008Value;

                                            const peak =
                                              stressTestResults.scenarios[
                                                "2008_crisis"
                                              ].peaks_troughs?.peak;
                                            const trough =
                                              stressTestResults.scenarios[
                                                "2008_crisis"
                                              ].peaks_troughs?.trough;

                                            if (!peak && !trough) return null;

                                            let peakValue = 0;
                                            let troughValue = 0;
                                            let peakDate = "";
                                            let troughDate = "";

                                            if (peak) {
                                              const peakDateFull =
                                                peak.date || "";
                                              peakDate =
                                                peakDateFull.length >= 7
                                                  ? peakDateFull.substring(0, 7)
                                                  : peakDateFull;
                                              // Peak is always at 100% since we normalize to Aug 2008 = 100%
                                              peakValue = 100.0;
                                            }

                                            if (trough) {
                                              const troughDateFull =
                                                trough.date || "";
                                              troughDate =
                                                troughDateFull.length >= 7
                                                  ? troughDateFull.substring(
                                                      0,
                                                      7,
                                                    )
                                                  : troughDateFull;
                                              troughValue =
                                                (trough.value || 0) *
                                                normalizationFactor *
                                                100;
                                            }

                                            // Detect if peak and trough are visually close (within 5% on the chart)
                                            return (
                                              <>
                                                {peak && (
                                                  <ReferenceDot
                                                    x={peakDate}
                                                    y={peakValue}
                                                    r={5}
                                                    fill="#22c55e"
                                                    stroke="#fff"
                                                    strokeWidth={2}
                                                  />
                                                )}
                                                {trough && (
                                                  <ReferenceDot
                                                    x={troughDate}
                                                    y={troughValue}
                                                    r={5}
                                                    fill="#ef4444"
                                                    stroke="#fff"
                                                    strokeWidth={2}
                                                  />
                                                )}
                                              </>
                                            );
                                          })()}
                                          {recoveryPeakInfo && (
                                            <ReferenceDot
                                              x={recoveryPeakInfo.date}
                                              y={recoveryPeakInfo.value}
                                              r={5}
                                              fill="#9333ea"
                                              stroke="#fff"
                                              strokeWidth={2}
                                            />
                                          )}
                                        </ComposedChart>
                                      );
                                    })()}
                                  </ResponsiveContainer>
                                </div>
                                {stressTestResults.scenarios["2008_crisis"]
                                  .peaks_troughs && (
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-center gap-4 text-xs">
                                      {stressTestResults.scenarios[
                                        "2008_crisis"
                                      ].peaks_troughs.peak && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow-sm"></div>
                                              <span className="font-medium">
                                                Peak (
                                                {stressTestResults.scenarios[
                                                  "2008_crisis"
                                                ].peaks_troughs.peak.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Pre-Crisis Peak
                                            </div>
                                            <div className="mb-2">
                                              The highest portfolio value before
                                              the crisis started. This
                                              represents your portfolio's value
                                              at its best point before market
                                              conditions deteriorated.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              Used as baseline for calculating
                                              drawdown and recovery metrics.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                      {stressTestResults.scenarios[
                                        "2008_crisis"
                                      ].peaks_troughs.trough && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow-sm"></div>
                                              <span className="font-medium">
                                                Trough (
                                                {stressTestResults.scenarios[
                                                  "2008_crisis"
                                                ].peaks_troughs.trough.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Crisis Trough
                                            </div>
                                            <div className="mb-2">
                                              The lowest portfolio value during
                                              the crisis period. This is the
                                              worst point your portfolio reached
                                              when market conditions were at
                                              their most adverse.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              The difference between Peak and
                                              Trough determines your Maximum
                                              Drawdown.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                      {stressTestResults.scenarios[
                                        "2008_crisis"
                                      ].peaks_troughs.recovery_peak && (
                                        <UITooltip>
                                          <TooltipTrigger asChild>
                                            <div className="flex items-center gap-2 cursor-help">
                                              <div
                                                className="w-4 h-4 rounded-full border-2 border-white shadow-sm"
                                                style={{
                                                  backgroundColor: "#9333ea",
                                                }}
                                              ></div>
                                              <span className="font-medium">
                                                Recovery Peak (
                                                {stressTestResults.scenarios[
                                                  "2008_crisis"
                                                ].peaks_troughs.recovery_peak.date?.substring(
                                                  0,
                                                  7,
                                                ) || "N/A"}
                                                )
                                              </span>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <div className="font-semibold mb-1">
                                              Recovery Peak
                                            </div>
                                            <div className="mb-2">
                                              The highest portfolio value after
                                              the crisis trough, indicating full
                                              recovery. This shows when your
                                              portfolio returned to or exceeded
                                              its pre-crisis peak value.
                                            </div>
                                            <div className="text-muted-foreground italic mt-2">
                                              Recovery Time is measured from
                                              Trough to Recovery Peak.
                                            </div>
                                          </TooltipContent>
                                        </UITooltip>
                                      )}
                                    </div>
                                    <div className="text-xs text-gray-500 text-center italic">
                                      Hover over markers above for detailed
                                      definitions
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                          {/* Sector Impact */}
                          {stressTestResults.scenarios["2008_crisis"]
                            .sector_impact &&
                            stressTestResults.scenarios["2008_crisis"]
                              .sector_impact.sector_returns &&
                            Object.keys(
                              stressTestResults.scenarios["2008_crisis"]
                                .sector_impact.sector_returns,
                            ).length > 0 && (
                              <div className="space-y-2">
                                <div className="text-sm font-medium">
                                  Sector Performance During Crisis
                                </div>
                                <div className="h-48 w-full">
                                  <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                  >
                                    <BarChart
                                      data={Object.entries(
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].sector_impact.sector_returns,
                                      ).map(
                                        ([sector, return_pct]: [
                                          string,
                                          any,
                                        ]) => ({
                                          sector:
                                            sector.length > 15
                                              ? sector.substring(0, 15) + "..."
                                              : sector,
                                          return: return_pct * 100,
                                        }),
                                      )}
                                    >
                                      <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#e5e7eb"
                                      />
                                      <XAxis
                                        dataKey="sector"
                                        tick={{ fontSize: 10 }}
                                        angle={-45}
                                        textAnchor="end"
                                        height={80}
                                      />
                                      <YAxis
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(value) =>
                                          `${value.toFixed(0)}%`
                                        }
                                      />
                                      <Tooltip
                                        formatter={(value: number) => [
                                          `${value.toFixed(1)}%`,
                                          "Return",
                                        ]}
                                      />
                                      <Bar
                                        dataKey="return"
                                        fill={(entry: any) =>
                                          entry.return >= 0
                                            ? "#22c55e"
                                            : "#ef4444"
                                        }
                                      />
                                    </BarChart>
                                  </ResponsiveContainer>
                                </div>
                              </div>
                            )}

                          {/* Detailed Metrics Table */}
                          <div className="space-y-2">
                            <div className="text-sm font-medium">
                              Detailed Metrics
                            </div>
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="border-b">
                                    <th className="text-left py-2 px-2">
                                      Metric
                                    </th>
                                    <th className="text-right py-2 px-2">
                                      Value
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  <tr className="border-b">
                                    <td className="py-2 px-2">
                                      Worst Month Return
                                    </td>
                                    <td className="text-right py-2 px-2 text-red-700 font-medium">
                                      {(
                                        (stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.worst_month_return || 0) * 100
                                      ).toFixed(1)}
                                      %
                                    </td>
                                  </tr>
                                  <tr className="border-b">
                                    <td className="py-2 px-2">
                                      Volatility During Crisis
                                    </td>
                                    <td className="text-right py-2 px-2">
                                      {(
                                        (stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.volatility_during_crisis ||
                                          0) * 100
                                      ).toFixed(1)}
                                      %
                                    </td>
                                  </tr>
                                  <tr className="border-b">
                                    <td className="py-2 px-2">
                                      Volatility Ratio (vs Normal)
                                    </td>
                                    <td className="text-right py-2 px-2">
                                      {(
                                        stressTestResults.scenarios[
                                          "2008_crisis"
                                        ].metrics.volatility_ratio || 1.0
                                      ).toFixed(2)}
                                      x
                                    </td>
                                  </tr>
                                  <tr>
                                    <td className="py-2 px-2">Recovery Date</td>
                                    <td className="text-right py-2 px-2">
                                      {stressTestResults.scenarios[
                                        "2008_crisis"
                                      ].metrics.recovery_date ||
                                        "Not recovered"}
                                    </td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}

                  {/* Advanced Risk Metrics */}
                  {stressTestResults.scenarios[selectedScenario || "covid19"]
                    ?.metrics?.advanced_risk && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Activity className="h-5 w-5 text-purple-600" />
                          Advanced Risk Metrics
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                          <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                            <div className="text-xs text-red-700 mb-1 flex items-center gap-1">
                              VaR (95%)
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-red-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Value at Risk: The maximum expected loss at
                                  95% confidence level. Represents the 5%
                                  worst-case scenario return.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-red-800">
                              {(
                                stressTestResults.scenarios[
                                  selectedScenario || "covid19"
                                ].metrics.advanced_risk.var_95 * 100
                              ).toFixed(1)}
                              %
                            </div>
                            <div className="text-xs text-red-600 mt-1">
                              5% worst case
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                            <div className="text-xs text-orange-700 mb-1 flex items-center gap-1">
                              CVaR (95%)
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-orange-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Conditional Value at Risk: Expected loss
                                  beyond VaR threshold. Average of losses in the
                                  worst 5% of scenarios.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-orange-800">
                              {(
                                stressTestResults.scenarios[
                                  selectedScenario || "covid19"
                                ].metrics.advanced_risk.cvar_95 * 100
                              ).toFixed(1)}
                              %
                            </div>
                            <div className="text-xs text-orange-600 mt-1">
                              Expected tail loss
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="text-xs text-blue-700 mb-1 flex items-center gap-1">
                              Beta
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-blue-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Beta measures portfolio sensitivity to market
                                  movements. 1.0 = moves with market, &gt;1.0 =
                                  more volatile, &lt;1.0 = less volatile.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-blue-800">
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].metrics.advanced_risk.beta.toFixed(2)}
                            </div>
                            <div className="text-xs text-blue-600 mt-1">
                              Market correlation
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                            <div className="text-xs text-purple-700 mb-1 flex items-center gap-1">
                              Tail Risk
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-purple-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Probability of extreme losses beyond 2
                                  standard deviations. Higher percentage
                                  indicates greater risk of severe losses.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-purple-800">
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].metrics.advanced_risk.tail_risk.toFixed(1)}
                              %
                            </div>
                            <div className="text-xs text-purple-600 mt-1">
                              Extreme loss prob
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200">
                            <div className="text-xs text-indigo-700 mb-1 flex items-center gap-1">
                              Downside Dev
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  Downside Deviation: Standard deviation of
                                  negative returns only. Measures volatility of
                                  losses, ignoring gains.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-indigo-800">
                              {(
                                stressTestResults.scenarios[
                                  selectedScenario || "covid19"
                                ].metrics.advanced_risk.downside_deviation * 100
                              ).toFixed(1)}
                              %
                            </div>
                            <div className="text-xs text-indigo-600 mt-1">
                              Negative volatility
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Monte Carlo Tab */}
                <TabsContent value="monte-carlo" className="space-y-6 mt-6">
                  {stressTestResults.scenarios[selectedScenario || "covid19"]
                    ?.monte_carlo ? (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <BarChart3 className="h-5 w-5 text-blue-600" />
                          Monte Carlo Simulation Results
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          Probabilistic analysis showing range of possible
                          outcomes (5,000 simulations)
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        {/* Histogram */}
                        {stressTestResults.scenarios[
                          selectedScenario || "covid19"
                        ].monte_carlo.histogram_data &&
                          stressTestResults.scenarios[
                            selectedScenario || "covid19"
                          ].monte_carlo.histogram_data.length > 0 && (
                            <div className="space-y-2">
                              <div className="text-sm font-medium">
                                Return Distribution
                              </div>
                              {/* Compact percentile toggles; click to show that percentile on the distribution */}
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].monte_carlo.percentiles && (
                                <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground text-center">
                                    Click a percentile to show it on the
                                    distribution chart
                                  </p>
                                  <div className="flex flex-wrap gap-2 justify-center py-2 border rounded-lg bg-muted/30 px-3">
                                    <span className="text-xs text-muted-foreground self-center mr-1">
                                      Percentiles:
                                    </span>
                                    {(
                                      [
                                        {
                                          key: "p5" as const,
                                          label: "5th",
                                          color: "#ef4444",
                                        },
                                        {
                                          key: "p25" as const,
                                          label: "25th",
                                          color: "#f97316",
                                        },
                                        {
                                          key: "p50" as const,
                                          label: "50th",
                                          color: "#3b82f6",
                                        },
                                        {
                                          key: "p75" as const,
                                          label: "75th",
                                          color: "#22c55e",
                                        },
                                        {
                                          key: "p95" as const,
                                          label: "95th",
                                          color: "#9333ea",
                                        },
                                      ] as const
                                    ).map((p) => {
                                      const val =
                                        stressTestResults.scenarios[
                                          selectedScenario || "covid19"
                                        ].monte_carlo.percentiles[p.key];
                                      return (
                                        <button
                                          key={p.key}
                                          onClick={() =>
                                            setVisiblePercentiles((prev) => ({
                                              ...prev,
                                              [p.key]: !prev[p.key],
                                            }))
                                          }
                                          className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                                            visiblePercentiles[p.key]
                                              ? "border-border bg-card hover:bg-accent text-foreground"
                                              : "border-border bg-muted/50 text-muted-foreground opacity-50"
                                          }`}
                                          title={
                                            visiblePercentiles[p.key]
                                              ? `Hide ${p.label} percentile`
                                              : `Show ${p.label} percentile`
                                          }
                                        >
                                          <div
                                            className="w-3 h-0.5"
                                            style={{
                                              backgroundColor: p.color,
                                              opacity: visiblePercentiles[p.key]
                                                ? 1
                                                : 0.3,
                                            }}
                                          />
                                          <span className="font-medium">
                                            {p.label}
                                          </span>
                                          <span className="text-muted-foreground">
                                            ({(val * 100).toFixed(1)}%)
                                          </span>
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                              <div className="h-64 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <AreaChart
                                    margin={{
                                      top: 10,
                                      right: 20,
                                      bottom: 30,
                                      left: 10,
                                    }}
                                    data={stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].monte_carlo.histogram_data.map(
                                      (h: any) => ({
                                        return_pct: h.return_pct,
                                        frequency: h.frequency,
                                      }),
                                    )}
                                  >
                                    <defs>
                                      <linearGradient
                                        id="colorGradient-blue-stress"
                                        x1="0"
                                        y1="0"
                                        x2="0"
                                        y2="1"
                                      >
                                        <stop
                                          offset="5%"
                                          stopColor="#3b82f6"
                                          stopOpacity={0.8}
                                        />
                                        <stop
                                          offset="95%"
                                          stopColor="#3b82f6"
                                          stopOpacity={0.1}
                                        />
                                      </linearGradient>
                                    </defs>
                                    <CartesianGrid
                                      strokeDasharray="3 3"
                                      stroke="#e5e7eb"
                                    />
                                    <XAxis
                                      dataKey="return_pct"
                                      type="number"
                                      tickFormatter={(value) => {
                                        const n =
                                          typeof value === "number"
                                            ? value
                                            : Number(value);
                                        return Number.isFinite(n)
                                          ? `${n.toFixed(0)}%`
                                          : String(value);
                                      }}
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
                                      tickFormatter={(value) =>
                                        `${value.toFixed(0)}%`
                                      }
                                      label={{
                                        value: "Frequency (%)",
                                        angle: -90,
                                        position: "insideLeft",
                                        offset: 5,
                                        fontSize: 11,
                                      }}
                                    />
                                    <Tooltip
                                      formatter={(value: number) => [
                                        `${value.toFixed(1)}%`,
                                        "Frequency",
                                      ]}
                                      labelFormatter={(label) => {
                                        const n =
                                          typeof label === "number"
                                            ? label
                                            : Number(label);
                                        return Number.isFinite(n)
                                          ? `Return: ${n.toFixed(1)}%`
                                          : `Return: ${label}%`;
                                      }}
                                    />
                                    <Area
                                      type="monotone"
                                      dataKey="frequency"
                                      name="Return Distribution"
                                      stroke="#3b82f6"
                                      strokeWidth={2}
                                      fill="url(#colorGradient-blue-stress)"
                                    />
                                    {/* Percentile Reference Lines */}
                                    {(() => {
                                      const mc =
                                        stressTestResults.scenarios[
                                          selectedScenario || "covid19"
                                        ].monte_carlo;
                                      if (!mc.percentiles) return null;
                                      const lines = [
                                        {
                                          key: "p5" as const,
                                          value: mc.percentiles.p5,
                                          color: "#ef4444",
                                          label: "P5",
                                        },
                                        {
                                          key: "p25" as const,
                                          value: mc.percentiles.p25,
                                          color: "#f97316",
                                          label: "P25",
                                        },
                                        {
                                          key: "p50" as const,
                                          value: mc.percentiles.p50,
                                          color: "#3b82f6",
                                          label: "P50",
                                        },
                                        {
                                          key: "p75" as const,
                                          value: mc.percentiles.p75,
                                          color: "#22c55e",
                                          label: "P75",
                                        },
                                        {
                                          key: "p95" as const,
                                          value: mc.percentiles.p95,
                                          color: "#9333ea",
                                          label: "P95",
                                        },
                                      ];
                                      return lines.map((line) =>
                                        visiblePercentiles[line.key] ? (
                                          <ReferenceLine
                                            key={line.key}
                                            x={line.value * 100}
                                            stroke={line.color}
                                            strokeWidth={1.5}
                                            strokeDasharray="4 3"
                                            label={{
                                              value: line.label,
                                              position: "top",
                                              fill: line.color,
                                              fontSize: 10,
                                              fontWeight: 600,
                                            }}
                                          />
                                        ) : null,
                                      );
                                    })()}
                                  </AreaChart>
                                </ResponsiveContainer>
                              </div>
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].monte_carlo.parameters && (
                                <p className="text-xs text-muted-foreground">
                                  Assumptions: expected return{" "}
                                  {(
                                    stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].monte_carlo.parameters.expected_return *
                                    100
                                  ).toFixed(1)}
                                  %, volatility{" "}
                                  {(
                                    stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].monte_carlo.parameters.risk * 100
                                  ).toFixed(1)}
                                  %,{" "}
                                  {stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.parameters
                                    .time_horizon_years === 1
                                    ? "1 year"
                                    : `${stressTestResults.scenarios[selectedScenario || "covid19"].monte_carlo.parameters.time_horizon_years} years`}
                                  ,{" "}
                                  {stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.parameters.num_simulations?.toLocaleString() ??
                                    "5,000"}{" "}
                                  simulations.
                                </p>
                              )}
                            </div>
                          )}

                        {/* How your portfolio would have performed in this scenario (below Return Distribution) */}
                        {stressTestResults.scenarios[
                          selectedScenario || "covid19"
                        ]?.metrics &&
                          (() => {
                            const scenarioKey = selectedScenario || "covid19";
                            const scenario =
                              stressTestResults.scenarios[scenarioKey];
                            const scenarioLabel =
                              scenarioKey === "2008_crisis"
                                ? "2008 crisis"
                                : "COVID-19";
                            const totalReturn =
                              scenario.metrics?.total_return != null
                                ? (scenario.metrics.total_return * 100).toFixed(
                                    1,
                                  )
                                : null;
                            const maxDrawdown =
                              scenario.metrics?.max_drawdown != null
                                ? (scenario.metrics.max_drawdown * 100).toFixed(
                                    1,
                                  )
                                : null;
                            const recovered =
                              scenario.metrics?.recovered === true;
                            const recoveryDate =
                              scenario.peaks_troughs?.recovery_peak?.date?.substring(
                                0,
                                7,
                              );
                            const recoveryMonths =
                              scenario.metrics?.recovery_months;
                            return (
                              <Collapsible className="group mt-2 rounded-md border border-border">
                                <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-muted/50">
                                  <span className="flex items-center gap-2">
                                    <BookOpen className="h-3.5 w-3.5" /> How
                                    your portfolio would have performed in the{" "}
                                    {scenarioLabel} scenario
                                  </span>
                                  <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                                </CollapsibleTrigger>
                                <CollapsibleContent>
                                  <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground space-y-2">
                                    <p>
                                      <strong className="text-foreground">
                                        Portfolio value over time in this
                                        scenario:
                                      </strong>{" "}
                                      {totalReturn != null &&
                                      maxDrawdown != null
                                        ? `In the ${scenarioLabel} scenario, your portfolio had a total return of ${totalReturn}% and a maximum drawdown of ${maxDrawdown}%.`
                                        : `Historical simulation of your portfolio during the ${scenarioLabel} period.`}
                                    </p>
                                    {recovered &&
                                      (recoveryDate ||
                                        recoveryMonths != null) && (
                                        <p>
                                          It recovered to its pre-crisis level
                                          {recoveryDate
                                            ? ` by ${recoveryDate}`
                                            : ""}
                                          {recoveryMonths != null &&
                                          !recoveryDate
                                            ? ` within ${recoveryMonths} months`
                                            : ""}
                                          .
                                        </p>
                                      )}
                                    <p className="text-muted-foreground">
                                      See the Overview and Timeline tabs for the
                                      full &quot;Portfolio Value Over Time&quot;
                                      chart and key events.
                                    </p>
                                  </div>
                                </CollapsibleContent>
                              </Collapsible>
                            );
                          })()}

                        {/* Percentiles */}
                        {stressTestResults.scenarios[
                          selectedScenario || "covid19"
                        ].monte_carlo.percentiles && (
                          <div className="grid grid-cols-5 gap-3">
                            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                              <div className="text-xs text-red-700 mb-1">
                                5th Percentile
                              </div>
                              <div className="text-lg font-bold text-red-800">
                                {(
                                  stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.percentiles.p5 * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-orange-50 border border-orange-200 text-center">
                              <div className="text-xs text-orange-700 mb-1">
                                25th Percentile
                              </div>
                              <div className="text-lg font-bold text-orange-800">
                                {(
                                  stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.percentiles.p25 * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-center">
                              <div className="text-xs text-blue-700 mb-1">
                                Median (50th)
                              </div>
                              <div className="text-lg font-bold text-blue-800">
                                {(
                                  stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.percentiles.p50 * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                              <div className="text-xs text-green-700 mb-1">
                                75th Percentile
                              </div>
                              <div className="text-lg font-bold text-green-800">
                                {(
                                  stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.percentiles.p75 * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-purple-50 border border-purple-200 text-center">
                              <div className="text-xs text-purple-700 mb-1">
                                95th Percentile
                              </div>
                              <div className="text-lg font-bold text-purple-800">
                                {(
                                  stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monte_carlo.percentiles.p95 * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                          </div>
                        )}
                        {stressTestResults.scenarios[
                          selectedScenario || "covid19"
                        ].monte_carlo && (
                          <p className="text-xs text-muted-foreground">
                            Based on a simplified normal-distribution model;
                            real returns can have fatter tails.
                          </p>
                        )}
                        {stressTestResults.scenarios[
                          selectedScenario || "covid19"
                        ].monte_carlo &&
                          (() => {
                            const mc =
                              stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].monte_carlo;
                            const n = mc.parameters?.num_simulations ?? 5000;
                            const horizon =
                              mc.parameters?.time_horizon_years === 1
                                ? "1-year"
                                : `${mc.parameters?.time_horizon_years}-year`;
                            const capital =
                              stressTestResults.portfolio_summary?.capital ??
                              500000;
                            const p5 = mc.percentiles?.p5 ?? -0.15;
                            const statements = mc.probability_statements || [];
                            return (
                              <Collapsible className="group mt-2 rounded-md border border-border">
                                <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-muted/50">
                                  <span className="flex items-center gap-2">
                                    <BookOpen className="h-3.5 w-3.5" /> Results
                                    Interpretation
                                  </span>
                                  <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                                </CollapsibleTrigger>
                                <CollapsibleContent>
                                  <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground space-y-3">
                                    {statements.length > 0 && (
                                      <div>
                                        <p className="font-medium text-foreground mb-1">
                                          Key Insights
                                        </p>
                                        <ul className="space-y-1">
                                          {statements.map(
                                            (stmt: string, idx: number) => (
                                              <li
                                                key={idx}
                                                className="flex items-start gap-2"
                                              >
                                                <CheckCircle className="h-3.5 w-3.5 text-blue-600 mt-0.5 flex-shrink-0" />
                                                <span>{stmt}</span>
                                              </li>
                                            ),
                                          )}
                                        </ul>
                                      </div>
                                    )}
                                    <p>
                                      <strong className="text-foreground">
                                        What this simulation shows:
                                      </strong>{" "}
                                      The chart shows a range of possible{" "}
                                      {horizon} returns based on{" "}
                                      {n.toLocaleString()} simulations, using
                                      the assumed expected return and
                                      volatility. Outcomes are hypothetical, not
                                      forecasts.
                                    </p>
                                    <p>
                                      <strong className="text-foreground">
                                        How to interpret:
                                      </strong>{" "}
                                      Each area is the share of simulations in
                                      that return range. The 5th percentile is
                                      worse than 5% of outcomes; the 95th is
                                      better than 95%. These illustrate
                                      uncertainty under the model.
                                    </p>
                                    <p>
                                      <strong className="text-foreground">
                                        Example:
                                      </strong>{" "}
                                      {p5 < 0
                                        ? `If your portfolio is ${capital.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, in about 1 in 20 runs you could see a loss of ${Math.round(capital * Math.abs(p5)).toLocaleString("sv-SE")} SEK or more over the period.`
                                        : `If your portfolio is ${capital.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, the worst 5% of outcomes still have a gain (no loss); the downside is a return of ${(p5 * 100).toFixed(1)}%.`}
                                    </p>
                                  </div>
                                </CollapsibleContent>
                              </Collapsible>
                            );
                          })()}
                      </CardContent>
                    </Card>
                  ) : (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        Monte Carlo simulation results are not available for the
                        selected scenario. Run a stress test to generate
                        probabilistic analysis.
                      </AlertDescription>
                    </Alert>
                  )}
                </TabsContent>

                {/* Interactive Timeline Tab */}
                <TabsContent value="timeline" className="space-y-6 mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-indigo-600" />
                        Interactive Crisis Timeline
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Key market events and their impact on your portfolio
                      </p>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Timeline Visualization */}
                      {stressTestResults.scenarios[
                        selectedScenario || "covid19"
                      ]?.monthly_performance && (
                        <div className="space-y-4">
                          <div className="h-64 w-full -ml-4">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart
                                data={(() => {
                                  // Normalize to match Portfolio Value Over Time graph (January 2020 = 100%)
                                  const jan2020Value =
                                    stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].monthly_performance.find(
                                      (m: any) => m.month === "2020-01",
                                    )?.value ||
                                    stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].monthly_performance[0]?.value ||
                                    1.0;
                                  const normalizationFactor =
                                    1.0 / jan2020Value;

                                  return stressTestResults.scenarios[
                                    selectedScenario || "covid19"
                                  ].monthly_performance.map((m: any) => ({
                                    date: m.month,
                                    value:
                                      (m.value || 0) *
                                      normalizationFactor *
                                      100,
                                    return: (m.return || 0) * 100,
                                  }));
                                })()}
                                margin={{
                                  left: 10,
                                  right: 10,
                                  top: 40,
                                  bottom: 10,
                                }}
                              >
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  stroke="#e5e7eb"
                                />
                                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                                <YAxis
                                  tick={{ fontSize: 10 }}
                                  tickFormatter={(value) =>
                                    `${value.toFixed(0)}%`
                                  }
                                  label={{
                                    value: "Portfolio Value (%)",
                                    angle: -90,
                                    position: "left",
                                    offset: 0,
                                    style: { textAnchor: "middle" },
                                  }}
                                  domain={["dataMin", "dataMax"]}
                                  width={70}
                                />
                                <Tooltip
                                  content={({ active, payload, label }) => {
                                    if (!active || !payload || !payload.length)
                                      return null;

                                    // Check if hovering near an event date
                                    const hoverDate = label as string;
                                    const nearbyEvent = crisisEvents[
                                      selectedScenario as keyof typeof crisisEvents
                                    ]?.find((event) => {
                                      const eventDate = event.date.substring(
                                        0,
                                        7,
                                      ); // YYYY-MM
                                      return eventDate === hoverDate;
                                    });

                                    if (nearbyEvent) {
                                      const eventColor =
                                        nearbyEvent.type === "crisis"
                                          ? "#ef4444"
                                          : nearbyEvent.type === "policy"
                                            ? "#3b82f6"
                                            : nearbyEvent.type === "recovery"
                                              ? "#22c55e"
                                              : "#f59e0b";
                                      return (
                                        <div className="bg-popover text-popover-foreground p-3 rounded-md shadow-md border text-xs">
                                          <div
                                            className="font-semibold mb-1"
                                            style={{ color: eventColor }}
                                          >
                                            {nearbyEvent.event}
                                          </div>
                                          <div className="text-muted-foreground">
                                            Date: {nearbyEvent.date}
                                          </div>
                                          <div className="mt-2 pt-2 border-t border-border">
                                            <div className="text-muted-foreground">
                                              Portfolio Value:{" "}
                                              {payload[0]?.value
                                                ? `${Number(payload[0].value).toFixed(1)}%`
                                                : "N/A"}
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    }

                                    // Default tooltip for portfolio value
                                    return (
                                      <div className="bg-popover text-popover-foreground p-2 rounded-md shadow-md border text-xs">
                                        <div className="font-semibold mb-1">
                                          Month: {label}
                                        </div>
                                        <div className="text-muted-foreground">
                                          Portfolio Value:{" "}
                                          {payload[0]?.value
                                            ? `${Number(payload[0].value).toFixed(1)}%`
                                            : "N/A"}
                                        </div>
                                      </div>
                                    );
                                  }}
                                />
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke="#6366f1"
                                  fill="#6366f1"
                                  fillOpacity={0.2}
                                />
                                {/* Recovery Threshold Lines removed - user requested no horizontal lines */}
                                {/* Event markers - Only show if event type is visible, no labels (use tooltips instead) */}
                                {crisisEvents[
                                  selectedScenario as keyof typeof crisisEvents
                                ]?.map((event, idx) => {
                                  const isSelected =
                                    selectedTimelineEvent === event;
                                  const isVisible =
                                    (event.type === "crisis" &&
                                      visibleEventTypes.crisis) ||
                                    (event.type === "policy" &&
                                      visibleEventTypes.policy) ||
                                    (event.type === "recovery" &&
                                      visibleEventTypes.recovery) ||
                                    ((event.type === "warning" ||
                                      event.type === "bottom") &&
                                      visibleEventTypes.warning);

                                  if (!isVisible) return null;

                                  return (
                                    <ReferenceLine
                                      key={idx}
                                      x={event.date}
                                      stroke={
                                        event.type === "crisis"
                                          ? "#ef4444"
                                          : event.type === "policy"
                                            ? "#3b82f6"
                                            : event.type === "recovery"
                                              ? "#22c55e"
                                              : "#f59e0b"
                                      }
                                      strokeDasharray={
                                        isSelected ? "3 3" : "5 5"
                                      }
                                      strokeWidth={isSelected ? 3 : 2}
                                    />
                                  );
                                })}
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>

                          {/* Interactive Legends */}
                          <div className="space-y-4">
                            {/* Recovery Thresholds Legend removed - user requested no horizontal lines */}

                            {/* Event Type Legend */}
                            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                              <div className="text-xs font-medium text-blue-700 mb-2">
                                Key Events Timeline
                              </div>
                              <div className="flex items-center justify-center gap-6 text-xs flex-wrap mb-3">
                                <button
                                  onClick={() =>
                                    setVisibleEventTypes({
                                      ...visibleEventTypes,
                                      crisis: !visibleEventTypes.crisis,
                                    })
                                  }
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.crisis
                                      ? "bg-red-100 border border-red-300 text-red-700 hover:bg-red-200"
                                      : "bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50"
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-red-500"></div>
                                  <span>Crisis Event</span>
                                </button>
                                <button
                                  onClick={() =>
                                    setVisibleEventTypes({
                                      ...visibleEventTypes,
                                      policy: !visibleEventTypes.policy,
                                    })
                                  }
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.policy
                                      ? "bg-blue-100 border border-blue-300 text-blue-700 hover:bg-blue-200"
                                      : "bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50"
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-blue-500"></div>
                                  <span>Policy Action</span>
                                </button>
                                <button
                                  onClick={() =>
                                    setVisibleEventTypes({
                                      ...visibleEventTypes,
                                      recovery: !visibleEventTypes.recovery,
                                    })
                                  }
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.recovery
                                      ? "bg-green-100 border border-green-300 text-green-700 hover:bg-green-200"
                                      : "bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50"
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-green-500"></div>
                                  <span>Recovery</span>
                                </button>
                                <button
                                  onClick={() =>
                                    setVisibleEventTypes({
                                      ...visibleEventTypes,
                                      warning: !visibleEventTypes.warning,
                                    })
                                  }
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.warning
                                      ? "bg-yellow-100 border border-yellow-300 text-yellow-700 hover:bg-yellow-200"
                                      : "bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50"
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-yellow-500"></div>
                                  <span>Warning</span>
                                </button>
                              </div>
                              <TimelineScrollReveal
                                className="space-y-2"
                                enabled={activeView === "timeline"}
                              >
                                {crisisEvents[
                                  selectedScenario as keyof typeof crisisEvents
                                ]?.map((event, idx) => (
                                  <div
                                    key={idx}
                                    className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                                      event.type === "crisis"
                                        ? "bg-red-50 border-red-200 hover:bg-red-100"
                                        : event.type === "policy"
                                          ? "bg-blue-50 border-blue-200 hover:bg-blue-100"
                                          : event.type === "recovery"
                                            ? "bg-green-50 border-green-200 hover:bg-green-100"
                                            : "bg-yellow-50 border-yellow-200 hover:bg-yellow-100"
                                    }`}
                                    onClick={() =>
                                      setSelectedTimelineEvent(event)
                                    }
                                  >
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3">
                                        <div
                                          className={`w-2 h-2 rounded-full ${
                                            event.type === "crisis"
                                              ? "bg-red-500"
                                              : event.type === "policy"
                                                ? "bg-blue-500"
                                                : event.type === "recovery"
                                                  ? "bg-green-500"
                                                  : "bg-yellow-500"
                                          }`}
                                        ></div>
                                        <span className="text-sm font-medium">
                                          {event.event}
                                        </span>
                                      </div>
                                      <span className="text-xs text-muted-foreground">
                                        {event.date}
                                      </span>
                                    </div>
                                    {selectedTimelineEvent === event && (
                                      <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-600">
                                        Click to view details on chart
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </TimelineScrollReveal>
                            </div>
                          </div>

                          {/* Peak/Trough Summary */}
                          {stressTestResults.scenarios[
                            selectedScenario || "covid19"
                          ]?.peaks_troughs && (
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t w-full">
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].peaks_troughs.peak && (
                                <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                                  <div className="text-xs text-green-700 mb-1">
                                    Peak
                                  </div>
                                  <div className="text-lg font-bold text-green-800">
                                    {(
                                      stressTestResults.scenarios[
                                        selectedScenario || "covid19"
                                      ].peaks_troughs.peak.value * 100
                                    ).toFixed(1)}
                                    %
                                  </div>
                                  <div className="text-xs text-green-600">
                                    {stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].peaks_troughs.peak.date?.substring(0, 7)}
                                  </div>
                                </div>
                              )}
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].peaks_troughs.trough && (
                                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center min-w-0">
                                  <div className="text-xs text-red-700 mb-1">
                                    Trough
                                  </div>
                                  <div className="text-lg font-bold text-red-800">
                                    {(
                                      stressTestResults.scenarios[
                                        selectedScenario || "covid19"
                                      ].peaks_troughs.trough.value * 100
                                    ).toFixed(1)}
                                    %
                                  </div>
                                  <div className="text-xs text-red-600">
                                    {stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].peaks_troughs.trough.date?.substring(
                                      0,
                                      7,
                                    )}
                                  </div>
                                </div>
                              )}
                              {stressTestResults.scenarios[
                                selectedScenario || "covid19"
                              ].peaks_troughs.recovery_peak && (
                                <div
                                  className="p-3 rounded-lg border text-center min-w-0"
                                  style={{
                                    backgroundColor: "#faf5ff",
                                    borderColor: "#e9d5ff",
                                  }}
                                >
                                  <div
                                    className="text-xs mb-1"
                                    style={{ color: "#9333ea" }}
                                  >
                                    Recovery Peak
                                  </div>
                                  <div
                                    className="text-lg font-bold"
                                    style={{ color: "#7e22ce" }}
                                  >
                                    {(
                                      stressTestResults.scenarios[
                                        selectedScenario || "covid19"
                                      ].peaks_troughs.recovery_peak.value * 100
                                    ).toFixed(1)}
                                    %
                                  </div>
                                  <div
                                    className="text-xs"
                                    style={{ color: "#a855f7" }}
                                  >
                                    {stressTestResults.scenarios[
                                      selectedScenario || "covid19"
                                    ].peaks_troughs.recovery_peak.date?.substring(
                                      0,
                                      7,
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Hypothetical Scenarios Tab */}
                <TabsContent value="hypothetical" className="space-y-6 mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                        Forward-Looking Stress Scenarios
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Test your portfolio against hypothetical market
                        scenarios
                      </p>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Predefined Scenarios */}
                      <div className="space-y-4">
                        <div className="text-sm font-medium">
                          Select Hypothetical Scenario
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                          <div
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === "tech_crash"
                                ? "border-purple-500 bg-purple-50"
                                : "border-gray-200 hover:border-purple-300"
                            }`}
                            onClick={() =>
                              setHypotheticalParams({
                                ...hypotheticalParams,
                                scenario_type: "tech_crash",
                                market_decline: -40,
                                sector_impact: "technology",
                              })
                            }
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <AlertCircle className="h-4 w-4 text-purple-600" />
                              <span className="font-medium">
                                Tech Bubble Burst
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              40% tech sector crash with spillover to broader
                              market
                            </p>
                          </div>

                          <div
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === "inflation"
                                ? "border-orange-500 bg-orange-50"
                                : "border-gray-200 hover:border-orange-300"
                            }`}
                            onClick={() =>
                              setHypotheticalParams({
                                ...hypotheticalParams,
                                scenario_type: "inflation",
                                market_decline: -25,
                                sector_impact: "bonds",
                              })
                            }
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingUp className="h-4 w-4 text-orange-600" />
                              <span className="font-medium">
                                Inflation Shock
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Sharp rate hikes causing bond crash and equity
                              correction
                            </p>
                          </div>

                          <div
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type ===
                              "geopolitical"
                                ? "border-red-500 bg-red-50"
                                : "border-gray-200 hover:border-red-300"
                            }`}
                            onClick={() =>
                              setHypotheticalParams({
                                ...hypotheticalParams,
                                scenario_type: "geopolitical",
                                market_decline: -35,
                                sector_impact: "energy",
                              })
                            }
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Shield className="h-4 w-4 text-red-600" />
                              <span className="font-medium">
                                Geopolitical Crisis
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Major conflict causing oil spike and global market
                              selloff
                            </p>
                          </div>

                          <div
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === "recession"
                                ? "border-gray-500 bg-gray-50"
                                : "border-gray-200 hover:border-gray-300"
                            }`}
                            onClick={() =>
                              setHypotheticalParams({
                                ...hypotheticalParams,
                                scenario_type: "recession",
                                market_decline: -30,
                                sector_impact: "cyclical",
                              })
                            }
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingDown className="h-4 w-4 text-gray-600" />
                              <span className="font-medium">
                                Deep Recession
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Prolonged economic contraction with high
                              unemployment
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Custom Parameters */}
                      <div className="space-y-4 pt-4 border-t w-full">
                        <div className="text-sm font-medium">
                          Adjust Scenario Parameters
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">
                              Market Decline (%)
                            </label>
                            <input
                              type="text"
                              inputMode="numeric"
                              value={
                                marketDeclineInput !== null
                                  ? marketDeclineInput
                                  : hypotheticalParams.market_decline
                              }
                              onFocus={() =>
                                setMarketDeclineInput(
                                  String(hypotheticalParams.market_decline),
                                )
                              }
                              onBlur={() => {
                                const raw = marketDeclineInput;
                                setMarketDeclineInput(null);
                                const num =
                                  raw !== null
                                    ? parseInt(raw, 10)
                                    : hypotheticalParams.market_decline;
                                if (!isNaN(num) && num >= -80 && num <= 0) {
                                  setHypotheticalParams((prev) => ({
                                    ...prev,
                                    market_decline: num,
                                  }));
                                }
                              }}
                              onChange={(e) => {
                                const raw = e.target.value;
                                setMarketDeclineInput(raw);
                                const num =
                                  raw === "" || raw === "-"
                                    ? null
                                    : parseInt(raw, 10);
                                if (
                                  num !== null &&
                                  !isNaN(num) &&
                                  num >= -80 &&
                                  num <= 0
                                ) {
                                  setHypotheticalParams((prev) => ({
                                    ...prev,
                                    market_decline: num,
                                  }));
                                }
                              }}
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">
                              Duration (months)
                            </label>
                            <input
                              type="number"
                              min="1"
                              max="36"
                              value={hypotheticalParams.duration_months}
                              onChange={(e) =>
                                setHypotheticalParams({
                                  ...hypotheticalParams,
                                  duration_months:
                                    parseInt(e.target.value) || 6,
                                })
                              }
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">
                              Recovery Rate
                            </label>
                            <select
                              value={hypotheticalParams.recovery_rate}
                              onChange={(e) =>
                                setHypotheticalParams({
                                  ...hypotheticalParams,
                                  recovery_rate: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            >
                              <option value="slow">Slow (L-shaped)</option>
                              <option value="moderate">
                                Moderate (U-shaped)
                              </option>
                              <option value="fast">Fast (V-shaped)</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      {/* Run Simulation Button */}
                      <Button
                        onClick={async () => {
                          if (!selectedPortfolio) {
                            setError("Please select a portfolio first");
                            return;
                          }
                          setHypotheticalLoading(true);
                          setError(null);
                          try {
                            // Use what-if endpoint with scenario_type for backward compatibility
                            const response = await fetch(
                              "/api/v1/portfolio/what-if-scenario",
                              {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                  tickers: selectedPortfolio.tickers,
                                  weights: selectedPortfolio.weights,
                                  scenario_type:
                                    hypotheticalParams.scenario_type,
                                  market_decline:
                                    hypotheticalParams.market_decline / 100,
                                  duration_months:
                                    hypotheticalParams.duration_months,
                                  recovery_rate:
                                    hypotheticalParams.recovery_rate,
                                  capital: capital,
                                }),
                              },
                            );
                            if (!response.ok) {
                              const errorData = await response.json();
                              throw new Error(
                                errorData.detail ||
                                  "Failed to run hypothetical scenario",
                              );
                            }
                            const data = await response.json();
                            setHypotheticalResults(data);
                          } catch (err: any) {
                            setError(
                              err.message ||
                                "Failed to run hypothetical scenario",
                            );
                          } finally {
                            setHypotheticalLoading(false);
                          }
                        }}
                        disabled={hypotheticalLoading || !selectedPortfolio}
                        className="w-full bg-primary hover:bg-primary/90"
                      >
                        {hypotheticalLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Running Scenario...
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="mr-2 h-4 w-4" />
                            Run Hypothetical Scenario
                          </>
                        )}
                      </Button>

                      {/* Results */}
                      {hypotheticalResults && (
                        <div className="space-y-6 mt-6 pt-6 border-t w-full">
                          {hypotheticalResults.scenario_type && (
                            <div className="text-sm text-muted-foreground">
                              <span className="font-medium">Scenario: </span>
                              {hypotheticalResults.scenario_type ===
                              "tech_crash"
                                ? "Tech Bubble Burst"
                                : hypotheticalResults.scenario_type ===
                                    "inflation"
                                  ? "Inflation Shock"
                                  : hypotheticalResults.scenario_type ===
                                      "geopolitical"
                                    ? "Geopolitical Crisis"
                                    : hypotheticalResults.scenario_type ===
                                        "recession"
                                      ? "Deep Recession"
                                      : hypotheticalResults.scenario_type}
                              {hypotheticalResults.parameters &&
                                (() => {
                                  const p = hypotheticalResults.parameters;
                                  const parts = [];
                                  if (p.market_decline != null)
                                    parts.push(
                                      `${(p.market_decline * 100).toFixed(0)}% decline`,
                                    );
                                  if (p.duration_months != null)
                                    parts.push(`${p.duration_months} mo`);
                                  if (p.recovery_rate)
                                    parts.push(`${p.recovery_rate} recovery`);
                                  return parts.length ? (
                                    <span className="ml-2">
                                      ({parts.join(", ")})
                                    </span>
                                  ) : null;
                                })()}
                            </div>
                          )}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                            <div className="p-4 rounded-lg bg-red-50 border border-red-200 min-w-0">
                              <div className="text-sm text-red-700 mb-1">
                                Estimated Loss
                              </div>
                              <div className="text-2xl font-bold text-red-800">
                                {(
                                  hypotheticalResults.estimated_loss * 100
                                ).toFixed(1)}
                                %
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 min-w-0">
                              <div className="text-sm text-blue-700 mb-1">
                                Portfolio Impact
                              </div>
                              <div className="text-2xl font-bold text-blue-800">
                                {hypotheticalResults.capital_at_risk
                                  ? hypotheticalResults.capital_at_risk.toLocaleString()
                                  : "N/A"}{" "}
                                SEK
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 min-w-0">
                              <div className="text-sm text-amber-700 mb-1">
                                Recovery Estimate
                              </div>
                              <div className="text-2xl font-bold text-amber-800">
                                {hypotheticalResults.estimated_recovery_months ||
                                  "N/A"}{" "}
                                months
                              </div>
                            </div>
                          </div>

                          {/* Monte Carlo Distribution */}
                          {hypotheticalResults.monte_carlo &&
                            hypotheticalResults.monte_carlo.histogram_data && (
                              <div className="space-y-2">
                                <div className="text-sm font-medium">
                                  Outcome Distribution
                                </div>
                                <div className="h-48 w-full">
                                  <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                  >
                                    <AreaChart
                                      margin={{
                                        top: 10,
                                        right: 20,
                                        bottom: 30,
                                        left: 10,
                                      }}
                                      data={hypotheticalResults.monte_carlo.histogram_data.map(
                                        (h: any) => ({
                                          return_pct: h.return_pct,
                                          frequency: h.frequency,
                                        }),
                                      )}
                                    >
                                      <defs>
                                        <linearGradient
                                          id="colorGradient-amber-stress"
                                          x1="0"
                                          y1="0"
                                          x2="0"
                                          y2="1"
                                        >
                                          <stop
                                            offset="5%"
                                            stopColor="#f59e0b"
                                            stopOpacity={0.8}
                                          />
                                          <stop
                                            offset="95%"
                                            stopColor="#f59e0b"
                                            stopOpacity={0.1}
                                          />
                                        </linearGradient>
                                      </defs>
                                      <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#e5e7eb"
                                      />
                                      <XAxis
                                        dataKey="return_pct"
                                        type="number"
                                        tickFormatter={(value) => {
                                          const n =
                                            typeof value === "number"
                                              ? value
                                              : Number(value);
                                          return Number.isFinite(n)
                                            ? `${n.toFixed(0)}%`
                                            : String(value);
                                        }}
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
                                        tickFormatter={(value) =>
                                          `${value.toFixed(0)}%`
                                        }
                                        label={{
                                          value: "Frequency (%)",
                                          angle: -90,
                                          position: "insideLeft",
                                          offset: 5,
                                          fontSize: 11,
                                        }}
                                      />
                                      <Tooltip
                                        formatter={(value: number) => [
                                          `${value.toFixed(1)}%`,
                                          "Frequency",
                                        ]}
                                        labelFormatter={(label) => {
                                          const n =
                                            typeof label === "number"
                                              ? label
                                              : Number(label);
                                          return Number.isFinite(n)
                                            ? `Return: ${n.toFixed(1)}%`
                                            : `Return: ${label}%`;
                                        }}
                                      />
                                      <Area
                                        type="monotone"
                                        dataKey="frequency"
                                        name="Outcome Distribution"
                                        stroke="#f59e0b"
                                        strokeWidth={2}
                                        fill="url(#colorGradient-amber-stress)"
                                      />
                                    </AreaChart>
                                  </ResponsiveContainer>
                                </div>
                                {hypotheticalResults.monte_carlo.parameters && (
                                  <p className="text-xs text-muted-foreground">
                                    Assumptions: expected return{" "}
                                    {(
                                      hypotheticalResults.monte_carlo.parameters
                                        .expected_return * 100
                                    ).toFixed(1)}
                                    %, volatility{" "}
                                    {(
                                      hypotheticalResults.monte_carlo.parameters
                                        .risk * 100
                                    ).toFixed(1)}
                                    %,{" "}
                                    {hypotheticalResults.monte_carlo.parameters
                                      .time_horizon_years === 1
                                      ? "1 year"
                                      : `${hypotheticalResults.monte_carlo.parameters.time_horizon_years} years`}
                                    ,{" "}
                                    {hypotheticalResults.monte_carlo.parameters.num_simulations?.toLocaleString() ??
                                      "5,000"}{" "}
                                    simulations.
                                  </p>
                                )}
                                <p className="text-xs text-muted-foreground">
                                  Based on a simplified normal-distribution
                                  model; real returns can have fatter tails.
                                </p>
                                <Collapsible className="group mt-2 rounded-md border border-border">
                                  <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-muted/50">
                                    <span className="flex items-center gap-2">
                                      <BookOpen className="h-3.5 w-3.5" />{" "}
                                      Results Interpretation
                                    </span>
                                    <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                                  </CollapsibleTrigger>
                                  <CollapsibleContent>
                                    <div className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground space-y-2">
                                      <p>
                                        <strong className="text-foreground">
                                          What this simulation shows:
                                        </strong>{" "}
                                        The chart shows possible outcomes for
                                        this scenario based on the assumed
                                        decline and volatility. Outcomes are
                                        hypothetical, not forecasts.
                                      </p>
                                      <p>
                                        <strong className="text-foreground">
                                          How to interpret:
                                        </strong>{" "}
                                        Each area is the share of simulations in
                                        that return range. The 5th percentile is
                                        worse than 5% of outcomes. These
                                        illustrate uncertainty under the model.
                                      </p>
                                      <p>
                                        <strong className="text-foreground">
                                          Example:
                                        </strong>{" "}
                                        {(() => {
                                          const p5 =
                                            hypotheticalResults.monte_carlo
                                              .percentiles?.p5 ?? -0.15;
                                          const cap = 500000;
                                          const isLoss = p5 < 0;
                                          return isLoss
                                            ? `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, in about 1 in 20 runs you could see a loss of ${Math.round(cap * Math.abs(p5)).toLocaleString("sv-SE")} SEK or more.`
                                            : `If your portfolio is ${cap.toLocaleString("sv-SE")} SEK and the 5th percentile is ${(p5 * 100).toFixed(1)}%, the worst 5% of outcomes still have a gain (no loss); the downside is a return of ${(p5 * 100).toFixed(1)}%.`;
                                        })()}
                                      </p>
                                    </div>
                                  </CollapsibleContent>
                                </Collapsible>
                              </div>
                            )}

                          {/* Sector Impact Analysis */}
                          {hypotheticalResults.sector_impact &&
                            Object.keys(hypotheticalResults.sector_impact)
                              .length > 0 && (
                              <div className="space-y-2 w-full">
                                <div className="text-sm font-medium">
                                  Sector Impact Analysis
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                                  {Object.entries(
                                    hypotheticalResults.sector_impact,
                                  ).map(([sector, impact]: [string, any]) => (
                                    <div
                                      key={sector}
                                      className="p-3 rounded-lg bg-gray-50 border"
                                    >
                                      <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium">
                                          {sector}
                                        </span>
                                        <span
                                          className={`text-sm font-bold ${impact < 0 ? "text-red-600" : "text-green-600"}`}
                                        >
                                          {(impact * 100).toFixed(1)}%
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-6 border-t">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button onClick={onNext} className="bg-primary hover:bg-primary/90">
              {stressTestResults ? "Complete & Proceed" : "Skip Stress Test"}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
