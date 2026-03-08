/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * 5-Year Projection with Tax Drag and Monte Carlo Confidence Bands
 *
 * Features:
 * - Monte Carlo simulation with GBM (Geometric Brownian Motion)
 * - Confidence bands showing probability ranges (p5-p95, p25-p75)
 * - Shock scenario selector for adverse market conditions
 * - Swedish tax (ISK/KF/AF) and transaction cost modeling
 *
 * X-axis: Year (0-5) or monthly resolution for smooth charts
 * Y-axis: Portfolio value in SEK with confidence bands
 */
import React, { useEffect, useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  ReferenceLine,
} from "recharts";
import { Loader2, TrendingUp, Info, TrendingDown, Minus, AlertTriangle } from "lucide-react";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useTheme } from "@/hooks/useTheme";
import { getChartTheme } from "@/utils/chartThemes";
import { LandscapeHint } from "@/components/ui/landscape-hint";
import { DataSourceAttribution } from "./DataSourceAttribution";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

interface FiveYearProjectionChartProps {
  weights: Record<string, number>;
  capital: number;
  accountType: string | null;
  taxYear: 2025 | 2026;
  courtageClass: string | null;
  expectedReturn: number;
  risk: number;
  rebalancingFrequency?: string;
}

interface ProjectionDataPoint {
  year: number;
  time?: number; // For monthly resolution
  optimistic: number; // p75
  base: number; // p50
  pessimistic: number; // p25
  p5?: number;
  p10?: number;
  p90?: number;
  p95?: number;
  // For confidence band rendering (area between values)
  band_90?: number; // p95 - p5
  band_80?: number; // p90 - p10
  band_50?: number; // p75 - p25
}

interface ShockScenario {
  id: string;
  name: string;
  description: string;
  severity: string;
  duration_months: number;
  return_impact: string;
}

interface ProjectionResponse {
  years: number[];
  optimistic: number[];
  base: number[];
  pessimistic: number[];
  confidence_bands?: {
    p5: number[];
    p10: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p90: number[];
    p95: number[];
  };
  monthly_points?: number[];
  probability_loss?: number;
  probability_loss_20pct?: number;
  mode: string;
  shock_scenario?: string | null;
  statistics?: {
    mean_final: number;
    median_final: number;
    p5_final: number;
    p95_final: number;
  };
}

export const FiveYearProjectionChart: React.FC<FiveYearProjectionChartProps> = ({
  weights,
  capital,
  accountType,
  taxYear,
  courtageClass,
  expectedReturn,
  risk,
  rebalancingFrequency = "quarterly",
}) => {
  const { theme } = useTheme();
  const chartTheme = getChartTheme(theme);
  const [data, setData] = useState<ProjectionDataPoint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectionMode, setProjectionMode] = useState<string>("monte_carlo");
  const [probabilityLoss, setProbabilityLoss] = useState<number | null>(null);
  const [probabilityLoss20, setProbabilityLoss20] = useState<number | null>(null);
  const [statistics, setStatistics] = useState<ProjectionResponse["statistics"] | null>(null);

  // Shock scenario state
  const [shockScenarios, setShockScenarios] = useState<ShockScenario[]>([]);
  const [selectedShock, setSelectedShock] = useState<string>("none");

  const canFetch = Boolean(
    accountType &&
    courtageClass &&
    capital > 0 &&
    Object.keys(weights).length > 0 &&
    typeof expectedReturn === "number" &&
    typeof risk === "number",
  );

  // Fetch available shock scenarios on mount
  useEffect(() => {
    fetch("/api/v1/portfolio/projection/shock-scenarios")
      .then((res) => res.json())
      .then((json) => {
        if (json.scenarios) {
          setShockScenarios(json.scenarios);
        }
      })
      .catch(() => {
        // Silently fail - shock scenarios are optional
      });
  }, []);

  // Fetch projection data
  useEffect(() => {
    if (!canFetch) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);

    const requestBody: any = {
      weights,
      capital,
      accountType,
      taxYear,
      courtageClass,
      expectedReturn,
      risk,
      rebalancingFrequency,
      mode: "monte_carlo", // Always request Monte Carlo for confidence bands
    };

    // Add shock scenario if selected
    if (selectedShock && selectedShock !== "none") {
      requestBody.shockScenario = selectedShock;
    }

    fetch("/api/v1/portfolio/projection/five-year", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((json: ProjectionResponse) => {
        setProjectionMode(json.mode || "deterministic");
        setProbabilityLoss(json.probability_loss ?? null);
        setProbabilityLoss20(json.probability_loss_20pct ?? null);
        setStatistics(json.statistics ?? null);

        // Check if we have confidence bands (Monte Carlo mode)
        if (json.confidence_bands && json.monthly_points) {
          // Use monthly resolution for smooth charts
          const points: ProjectionDataPoint[] = json.monthly_points.map((time, i) => ({
            time,
            year: Math.floor(time),
            optimistic: json.confidence_bands!.p75[i] ?? 0,
            base: json.confidence_bands!.p50[i] ?? 0,
            pessimistic: json.confidence_bands!.p25[i] ?? 0,
            p5: json.confidence_bands!.p5[i] ?? 0,
            p10: json.confidence_bands!.p10[i] ?? 0,
            p90: json.confidence_bands!.p90[i] ?? 0,
            p95: json.confidence_bands!.p95[i] ?? 0,
          }));
          setData(points);
        } else {
          // Fallback to annual data (deterministic mode)
          const points: ProjectionDataPoint[] = json.years.map((year, i) => ({
            year,
            time: year,
            optimistic: json.optimistic[i] ?? 0,
            base: json.base[i] ?? 0,
            pessimistic: json.pessimistic[i] ?? 0,
          }));
          setData(points);
        }
      })
      .catch((e) => {
        setError(e.message || "Failed to load projection");
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [
    canFetch,
    weights,
    capital,
    accountType,
    taxYear,
    courtageClass,
    expectedReturn,
    risk,
    rebalancingFrequency,
    selectedShock,
  ]);

  // Check if we have Monte Carlo confidence band data
  const hasConfidenceBands = useMemo(() => {
    return data && data.length > 0 && data[0].p5 !== undefined;
  }, [data]);

  if (!canFetch) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Select account type and courtage class above to see 5-year
            projections with confidence bands and Swedish tax/costs.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
            Running Monte Carlo simulation...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error || "No projection data"}</p>
        </CardContent>
      </Card>
    );
  }

  // Y-axis formatter
  const formatSEK = (value: number) =>
    value >= 1e6
      ? `${(value / 1e6).toFixed(1)}M`
      : value >= 1e3
        ? `${(value / 1e3).toFixed(0)}k`
        : value.toFixed(0);

  // Calculate summary metrics
  const initialValue = data[0]?.base || capital;
  const finalData = data[data.length - 1];
  const finalBaseValue = finalData?.base || capital;
  const finalOptimisticValue = finalData?.optimistic || capital;
  const finalPessimisticValue = finalData?.pessimistic || capital;
  const finalP5 = finalData?.p5 ?? finalPessimisticValue;
  const finalP95 = finalData?.p95 ?? finalOptimisticValue;

  const totalGrowthBase = finalBaseValue - initialValue;
  const totalGrowthPercentBase = (finalBaseValue / initialValue - 1) * 100;
  const annualizedReturnBase = (Math.pow(finalBaseValue / initialValue, 1 / 5) - 1) * 100;

  const totalGrowthPercentOptimistic = (finalOptimisticValue / initialValue - 1) * 100;
  const totalGrowthPercentPessimistic = (finalPessimisticValue / initialValue - 1) * 100;

  // Get selected shock scenario details
  const activeShock = shockScenarios.find((s) => s.id === selectedShock);

  // Custom tooltip with detailed breakdown
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const point = payload[0]?.payload as ProjectionDataPoint;
    const yearLabel = point?.time !== undefined ? `Year ${point.time.toFixed(1)}` : `Year ${label}`;

    return (
      <div className="bg-popover text-popover-foreground border border-border rounded-lg shadow-lg p-4 space-y-2 max-w-xs">
        <p className="font-semibold text-sm border-b pb-2">{yearLabel}</p>

        {/* Confidence bands info */}
        {point?.p95 !== undefined && (
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-green-600 dark:text-green-400">95th percentile:</span>
              <span className="font-medium">{formatSEK(point.p95)} SEK</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-500">75th percentile:</span>
              <span className="font-medium">{formatSEK(point.optimistic)} SEK</span>
            </div>
            <div className="flex justify-between font-semibold">
              <span className="text-blue-600 dark:text-blue-400">Median (50th):</span>
              <span>{formatSEK(point.base)} SEK</span>
            </div>
            <div className="flex justify-between">
              <span className="text-orange-500">25th percentile:</span>
              <span className="font-medium">{formatSEK(point.pessimistic)} SEK</span>
            </div>
            <div className="flex justify-between">
              <span className="text-red-600 dark:text-red-400">5th percentile:</span>
              <span className="font-medium">{formatSEK(point.p5!)} SEK</span>
            </div>
          </div>
        )}

        {/* Growth from initial */}
        <div className="border-t pt-2 mt-2">
          <p className="text-xs text-muted-foreground">
            Growth from initial:{" "}
            <span className={totalGrowthBase >= 0 ? "text-green-600" : "text-red-600"}>
              {((point.base / initialValue - 1) * 100).toFixed(1)}%
            </span>
          </p>
        </div>
      </div>
    );
  };

  return (
    <LandscapeHint storageKey="five-year-projection-landscape-hint">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection (Tax & Cost Adjusted)
            {projectionMode === "monte_carlo" && (
              <Badge variant="outline" className="text-[10px] ml-2">
                Monte Carlo
              </Badge>
            )}
            <UITooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                  <Info className="h-4 w-4" />
                </span>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-sm">
                <p className="font-semibold mb-2">Monte Carlo Projection</p>
                <div className="space-y-2 text-xs">
                  <p>
                    Based on <strong>5,000 simulated paths</strong> using Geometric
                    Brownian Motion (GBM) with your portfolio's expected return (
                    {(expectedReturn * 100).toFixed(1)}%) and volatility (
                    {(risk * 100).toFixed(1)}%).
                  </p>
                  <p>
                    <strong>Confidence Bands:</strong>
                  </p>
                  <ul className="list-disc ml-4">
                    <li>Dark band: 50% of outcomes (25th-75th percentile)</li>
                    <li>Medium band: 80% of outcomes (10th-90th percentile)</li>
                    <li>Light band: 90% of outcomes (5th-95th percentile)</li>
                  </ul>
                  <p className="text-muted-foreground italic mt-2">
                    All values are NET after Swedish taxes and transaction costs.
                  </p>
                </div>
              </TooltipContent>
            </UITooltip>
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            {hasConfidenceBands
              ? "Shaded bands show probability ranges of possible outcomes"
              : "Three scenarios showing portfolio growth after taxes and costs"}
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Shock Scenario Selector */}
          {shockScenarios.length > 0 && (
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">Stress scenario:</span>
              <Select value={selectedShock} onValueChange={setSelectedShock}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No shock (base case)</SelectItem>
                  {shockScenarios.map((scenario) => (
                    <SelectItem key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {activeShock && (
                <Badge variant="destructive" className="text-xs">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  {activeShock.return_impact}
                </Badge>
              )}
            </div>
          )}

          {activeShock && (
            <Alert className="bg-orange-50 dark:bg-orange-950/40 border-orange-200 dark:border-orange-800">
              <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
              <AlertDescription className="text-xs text-orange-900 dark:text-orange-100">
                <strong>{activeShock.name}:</strong> {activeShock.description}
                <br />
                Duration: {activeShock.duration_months} months | Severity:{" "}
                {activeShock.severity}
              </AlertDescription>
            </Alert>
          )}

          {accountType === "AF" && (
            <p className="text-xs text-muted-foreground rounded-lg border border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800 px-3 py-2">
              We assume gains are realized each year (e.g. rebalancing); actual AF tax
              depends on when you sell.
            </p>
          )}

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Card className="border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/40">
              <CardContent className="pt-4 pb-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <TrendingUp className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                  <p className="text-xs font-medium text-green-700 dark:text-green-400">
                    {hasConfidenceBands ? "75th Percentile" : "Optimistic"}
                  </p>
                </div>
                <p className="text-xl font-bold text-green-700 dark:text-green-400">
                  {finalOptimisticValue.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK
                </p>
                <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                  +{totalGrowthPercentOptimistic.toFixed(1)}% over 5 years
                </p>
              </CardContent>
            </Card>

            <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/40">
              <CardContent className="pt-4 pb-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Minus className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                  <p className="text-xs font-medium text-blue-700 dark:text-blue-400">
                    {hasConfidenceBands ? "Median (50th)" : "Base Scenario"}
                  </p>
                </div>
                <p className="text-xl font-bold text-blue-700 dark:text-blue-400">
                  {finalBaseValue.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
                  {totalGrowthPercentBase >= 0 ? "+" : ""}
                  {totalGrowthPercentBase.toFixed(1)}% ({annualizedReturnBase.toFixed(1)}%/yr)
                </p>
              </CardContent>
            </Card>

            <Card className="border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-950/40">
              <CardContent className="pt-4 pb-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <TrendingDown className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                  <p className="text-xs font-medium text-red-700 dark:text-red-400">
                    {hasConfidenceBands ? "25th Percentile" : "Pessimistic"}
                  </p>
                </div>
                <p className="text-xl font-bold text-red-700 dark:text-red-400">
                  {finalPessimisticValue.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK
                </p>
                <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
                  {totalGrowthPercentPessimistic >= 0 ? "+" : ""}
                  {totalGrowthPercentPessimistic.toFixed(1)}% over 5 years
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Probability metrics (Monte Carlo only) */}
          {probabilityLoss !== null && (
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Probability of loss:</span>
                <Badge variant={probabilityLoss > 30 ? "destructive" : "outline"}>
                  {probabilityLoss.toFixed(0)}%
                </Badge>
              </div>
              {probabilityLoss20 !== null && probabilityLoss20 > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Probability of 20%+ loss:</span>
                  <Badge variant={probabilityLoss20 > 10 ? "destructive" : "outline"}>
                    {probabilityLoss20.toFixed(0)}%
                  </Badge>
                </div>
              )}
              {statistics?.p5_final && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">5th percentile (worst case):</span>
                  <span className="font-medium">
                    {statistics.p5_final.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Chart */}
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {hasConfidenceBands ? (
                <ComposedChart
                  data={data}
                  margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis
                    dataKey="time"
                    type="number"
                    domain={[0, 5]}
                    ticks={[0, 1, 2, 3, 4, 5]}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `Year ${v}`}
                    label={{
                      value: "Time Horizon",
                      position: "insideBottom",
                      offset: -4,
                      style: { fontSize: 11 },
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={formatSEK}
                    domain={["auto", "auto"]}
                    label={{
                      value: "Portfolio Value (SEK)",
                      angle: -90,
                      position: "insideLeft",
                      style: { fontSize: 11 },
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />

                  {/* Reference line for initial capital */}
                  <ReferenceLine
                    y={capital}
                    stroke="#666"
                    strokeDasharray="3 3"
                    label={{ value: "Initial", position: "right", fontSize: 10 }}
                  />

                  {/* 90% confidence band (p5 to p95) - lightest */}
                  <Area
                    type="monotone"
                    dataKey="p5"
                    stackId="band90"
                    fill="transparent"
                    stroke="none"
                  />
                  <Area
                    type="monotone"
                    dataKey={(d: ProjectionDataPoint) => (d.p95 ?? 0) - (d.p5 ?? 0)}
                    stackId="band90"
                    fill="#3b82f6"
                    fillOpacity={0.08}
                    stroke="none"
                    name="90% range"
                  />

                  {/* 80% confidence band (p10 to p90) */}
                  <Area
                    type="monotone"
                    dataKey="p10"
                    stackId="band80"
                    fill="transparent"
                    stroke="none"
                  />
                  <Area
                    type="monotone"
                    dataKey={(d: ProjectionDataPoint) => (d.p90 ?? 0) - (d.p10 ?? 0)}
                    stackId="band80"
                    fill="#3b82f6"
                    fillOpacity={0.12}
                    stroke="none"
                    name="80% range"
                  />

                  {/* 50% confidence band (p25 to p75) - darkest */}
                  <Area
                    type="monotone"
                    dataKey="pessimistic"
                    stackId="band50"
                    fill="transparent"
                    stroke="none"
                  />
                  <Area
                    type="monotone"
                    dataKey={(d: ProjectionDataPoint) => d.optimistic - d.pessimistic}
                    stackId="band50"
                    fill="#3b82f6"
                    fillOpacity={0.2}
                    stroke="none"
                    name="50% range"
                  />

                  {/* Median line */}
                  <Line
                    type="monotone"
                    dataKey="base"
                    name="Median"
                    stroke="#3b82f6"
                    strokeWidth={2.5}
                    dot={false}
                  />

                  <Legend
                    wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
                    formatter={(value) => {
                      if (value === "Median") return "Median (50th percentile)";
                      return value;
                    }}
                  />
                </ComposedChart>
              ) : (
                // Fallback to simple line chart for deterministic mode
                <LineChart
                  data={data}
                  margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis
                    dataKey="year"
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "Year",
                      position: "insideBottom",
                      offset: -4,
                      style: { fontSize: 11 },
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickFormatter={formatSEK}
                    label={{
                      value: "Portfolio Value (SEK)",
                      angle: -90,
                      position: "insideLeft",
                      style: { fontSize: 11 },
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Line
                    type="monotone"
                    dataKey="optimistic"
                    name="Optimistic"
                    stroke="#22c55e"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="base"
                    name="Base"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="pessimistic"
                    name="Pessimistic"
                    stroke="#ef4444"
                    strokeWidth={2.5}
                    dot={false}
                  />
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>

          {/* Explanatory text */}
          <div className="text-xs text-muted-foreground space-y-2 border-t pt-3">
            {hasConfidenceBands ? (
              <>
                <p>
                  This chart uses <strong>Monte Carlo simulation</strong> (5,000 paths) to
                  show the range of possible portfolio values. The shaded bands represent
                  confidence intervals — the darker the shade, the more likely those
                  outcomes.
                </p>
                <p>
                  <strong>How to read:</strong> The solid blue line is the median (50%
                  chance of being above or below). There's a 90% chance your portfolio
                  will end up within the lightest band, and 50% chance within the darkest.
                </p>
              </>
            ) : (
              <p>
                This chart shows three deterministic scenarios based on your portfolio's
                expected return and volatility. The base scenario uses your expected return
                directly.
              </p>
            )}
            <p>
              <strong>Included costs:</strong>
            </p>
            <ul className="list-disc ml-5 space-y-0.5">
              <li>Annual {accountType} tax based on {taxYear} rates</li>
              <li>Transaction costs ({courtageClass} courtage class)</li>
              <li>Quarterly rebalancing costs</li>
            </ul>
          </div>
          <DataSourceAttribution />
        </CardContent>
      </Card>
    </LandscapeHint>
  );
};
