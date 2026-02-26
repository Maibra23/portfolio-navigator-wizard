/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useMemo, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  TooltipProps,
  ReferenceArea,
} from "recharts";
import {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  BookOpen,
  ChevronDown,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useTheme } from "@/hooks/useTheme";
import {
  getChartTheme,
  getPortfolioColors,
  getRechartsTheme,
} from "@/utils/chartThemes";

interface PortfolioPoint {
  risk: number;
  return: number;
  name: string;
  type:
    | "current"
    | "market-optimized"
    | "weights-optimized"
    | "frontier"
    | "inefficient_frontier"
    | "cml"
    | "random";
  sharpe_ratio?: number;
}

// Portfolio point with clamped position for off-scale rendering
interface ClampedPortfolioPoint extends PortfolioPoint {
  displayReturn: number; // original (unclamped) return, used in tooltip
  isOffScaleHigh: boolean;
  isOffScaleLow: boolean;
}

interface EfficientFrontierPoint {
  risk: number;
  return: number;
  sharpe_ratio?: number;
  type?: string;
}

interface EfficientFrontierChartProps {
  currentPortfolio: PortfolioPoint | null;
  efficientFrontier?: Array<{
    risk: number;
    return: number;
    sharpe_ratio?: number;
  }>;
  inefficientFrontier?: Array<{
    risk: number;
    return: number;
    sharpe_ratio?: number;
  }>;
  randomPortfolios?: Array<{
    risk: number;
    return: number;
    sharpe_ratio?: number;
  }>;
  capitalMarketLine?: Array<{ risk: number; return: number }>;
  marketOptimizedPortfolio?: PortfolioPoint;
  weightsOptimizedPortfolio?: PortfolioPoint;
  className?: string;
  showControls?: boolean;
  showInteractiveLegend?: boolean;
  /** Optional ticker symbol from the weights-optimized portfolio for educational example (e.g. why weights-opt can outperform market-opt). */
  weightsOptimizedTickerExample?: string;
}

// Spacing and layout constants (theme-independent)
const layoutConstants = {
  spacing: {
    cardPadding: "28px",
    sectionGap: "28px",
  },
  radius: "18px",
  legend: {
    fontSize: 12,
  },
};

const formatPercent = (value: number): string => {
  if (value == null || typeof value !== "number" || !isFinite(value))
    return "N/A";
  return `${(value * 100).toFixed(2)}%`;
};

export const EfficientFrontierChart = ({
  currentPortfolio,
  efficientFrontier,
  inefficientFrontier,
  randomPortfolios,
  capitalMarketLine,
  marketOptimizedPortfolio,
  weightsOptimizedPortfolio,
  className,
  showControls = true,
  showInteractiveLegend = true,
  weightsOptimizedTickerExample,
}: EfficientFrontierChartProps) => {
  // Get current theme for dynamic colors
  const { theme } = useTheme();
  const chartTheme = getChartTheme(theme);
  const portfolioColors = getPortfolioColors(theme);
  const rechartsTheme = getRechartsTheme(theme);

  // Visibility toggles for chart series
  const [visibleSeries, setVisibleSeries] = useState({
    randomPortfolios: true,
    efficientFrontier: true,
    inefficientFrontier: true,
    cml: true,
    currentPortfolio: true,
    weightsOptimized: true,
    marketOptimized: true,
  });

  // Zoom state
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [currentDomain, setCurrentDomain] = useState<{
    x: [number, number];
    y: [number, number];
  } | null>(null);
  const [zoomHistory, setZoomHistory] = useState<
    Array<{ x: [number, number]; y: [number, number] }>
  >([]);

  // Box selection state
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<{
    x: number;
    y: number;
  } | null>(null);

  // Toggle visibility of a series
  const toggleSeriesVisibility = useCallback(
    (series: keyof typeof visibleSeries) => {
      setVisibleSeries((prev) => ({ ...prev, [series]: !prev[series] }));
    },
    [],
  );

  // Build portfolio comparison points (exact values — no jitter, preserves tooltip accuracy)
  const portfolioPoints: PortfolioPoint[] = useMemo(() => {
    const points: PortfolioPoint[] = [];

    if (currentPortfolio && visibleSeries.currentPortfolio) {
      points.push({
        ...currentPortfolio,
        type: "current",
      });
    }

    if (weightsOptimizedPortfolio && visibleSeries.weightsOptimized) {
      points.push({
        ...weightsOptimizedPortfolio,
        type: "weights-optimized",
      });
    }

    if (marketOptimizedPortfolio && visibleSeries.marketOptimized) {
      points.push({
        ...marketOptimizedPortfolio,
        type: "market-optimized",
      });
    }

    return points;
  }, [
    currentPortfolio,
    weightsOptimizedPortfolio,
    marketOptimizedPortfolio,
    visibleSeries,
  ]);

  // Sort efficient frontier by risk for smooth line rendering
  const sortedFrontier = useMemo(() => {
    if (!efficientFrontier || !visibleSeries.efficientFrontier) return [];
    return [...efficientFrontier]
      .sort((a, b) => (a.risk ?? 0) - (b.risk ?? 0))
      .filter(
        (p) =>
          p.risk != null &&
          typeof p.risk === "number" &&
          isFinite(p.risk) &&
          p.return != null &&
          typeof p.return === "number" &&
          isFinite(p.return),
      )
      .map((point, index) => ({
        ...point,
        type: "frontier" as const,
        name: `Frontier Point ${index + 1}`,
      }));
  }, [efficientFrontier, visibleSeries.efficientFrontier]);

  // Sort inefficient frontier
  const sortedInefficientFrontier = useMemo(() => {
    if (!inefficientFrontier || !visibleSeries.inefficientFrontier) return [];
    return [...inefficientFrontier]
      .sort((a, b) => (a.risk ?? 0) - (b.risk ?? 0))
      .filter(
        (p) =>
          p.risk != null &&
          typeof p.risk === "number" &&
          isFinite(p.risk) &&
          p.return != null &&
          typeof p.return === "number" &&
          isFinite(p.return),
      )
      .map((point) => ({
        ...point,
        type: "inefficient_frontier" as const,
      }));
  }, [inefficientFrontier, visibleSeries.inefficientFrontier]);

  // Filter random portfolios
  const filteredRandomPortfolios = useMemo(() => {
    if (!randomPortfolios || !visibleSeries.randomPortfolios) return [];
    return randomPortfolios.filter(
      (p) =>
        p.risk != null &&
        typeof p.risk === "number" &&
        isFinite(p.risk) &&
        p.return != null &&
        typeof p.return === "number" &&
        isFinite(p.return),
    );
  }, [randomPortfolios, visibleSeries.randomPortfolios]);

  // Calculate domain from all data points
  const calculatedDomain = useMemo(() => {
    const allPoints: Array<{ risk: number; return: number }> = [];

    if (sortedFrontier.length > 0) {
      allPoints.push(...sortedFrontier);
    }
    if (sortedInefficientFrontier.length > 0) {
      allPoints.push(...sortedInefficientFrontier);
    }
    if (filteredRandomPortfolios.length > 0) {
      allPoints.push(...filteredRandomPortfolios);
    }
    // Portfolio comparison points are intentionally excluded from domain scaling.
    // The chart frames the frontier; portfolio points outside the range get
    // off-scale arrow indicators instead of stretching the axes.
    if (capitalMarketLine && visibleSeries.cml) {
      allPoints.push(...capitalMarketLine);
    }

    if (allPoints.length === 0) {
      return {
        x: [0, 0.5] as [number, number],
        y: [0, 0.3] as [number, number],
      };
    }

    const risks = allPoints.map((p) => p.risk).filter((r) => isFinite(r));
    const returns = allPoints.map((p) => p.return).filter((r) => isFinite(r));

    const minRisk = Math.min(...risks);
    const maxRisk = Math.max(...risks);
    const minReturn = Math.min(...returns);
    const maxReturn = Math.max(...returns);

    // Add padding
    const riskPadding = (maxRisk - minRisk) * 0.1 || 0.05;
    const returnPadding = (maxReturn - minReturn) * 0.1 || 0.05;

    return {
      x: [Math.max(0, minRisk - riskPadding), maxRisk + riskPadding] as [
        number,
        number,
      ],
      y: [
        Math.max(0, minReturn - returnPadding),
        maxReturn + returnPadding,
      ] as [number, number],
    };
  }, [
    sortedFrontier,
    sortedInefficientFrontier,
    filteredRandomPortfolios,
    capitalMarketLine,
    visibleSeries.cml,
  ]);

  // Zoom functions
  const zoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev * 1.5, 10));
  }, []);

  const zoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev / 1.5, 0.5));
  }, []);

  const resetZoom = useCallback(() => {
    setZoomLevel(1);
    setCurrentDomain(null);
    setZoomHistory([]);
  }, []);

  // Get effective domain based on zoom
  const effectiveDomain = useMemo(() => {
    if (currentDomain) {
      return currentDomain;
    }

    if (zoomLevel === 1) {
      return calculatedDomain;
    }

    const centerX = (calculatedDomain.x[0] + calculatedDomain.x[1]) / 2;
    const centerY = (calculatedDomain.y[0] + calculatedDomain.y[1]) / 2;
    const rangeX = (calculatedDomain.x[1] - calculatedDomain.x[0]) / zoomLevel;
    const rangeY = (calculatedDomain.y[1] - calculatedDomain.y[0]) / zoomLevel;

    return {
      x: [centerX - rangeX / 2, centerX + rangeX / 2] as [number, number],
      y: [centerY - rangeY / 2, centerY + rangeY / 2] as [number, number],
    };
  }, [currentDomain, zoomLevel, calculatedDomain]);

  // Clamp portfolio comparison points to the effective Y domain.
  // Points above/below the domain are snapped to the boundary so they remain
  // visible; the original return is preserved in `displayReturn` for tooltips.
  const clampedPortfolioPoints: ClampedPortfolioPoint[] = useMemo(() => {
    const [yMin, yMax] = effectiveDomain.y;
    return portfolioPoints.map((point) => {
      const isOffScaleHigh = point.return > yMax;
      const isOffScaleLow = point.return < yMin;
      const clampedReturn = isOffScaleHigh
        ? yMax
        : isOffScaleLow
          ? yMin
          : point.return;
      return {
        ...point,
        displayReturn: point.return,
        return: clampedReturn,
        isOffScaleHigh,
        isOffScaleLow,
      };
    });
  }, [portfolioPoints, effectiveDomain]);

  // Mouse handlers for box zoom
  const handleMouseDown = useCallback((e: any) => {
    if (e?.activeCoordinate) {
      setIsSelecting(true);
      setSelectionStart({ x: e.activeCoordinate.x, y: e.activeCoordinate.y });
      setSelectionEnd(null);
    }
  }, []);

  const handleMouseMove = useCallback(
    (e: any) => {
      if (isSelecting && e?.activeCoordinate) {
        setSelectionEnd({ x: e.activeCoordinate.x, y: e.activeCoordinate.y });
      }
    },
    [isSelecting],
  );

  const handleMouseUp = useCallback(() => {
    if (isSelecting && selectionStart && selectionEnd) {
      const x1 = Math.min(selectionStart.x, selectionEnd.x);
      const x2 = Math.max(selectionStart.x, selectionEnd.x);
      const y1 = Math.min(selectionStart.y, selectionEnd.y);
      const y2 = Math.max(selectionStart.y, selectionEnd.y);

      // Only zoom if selection is meaningful (not just a click)
      if (Math.abs(x2 - x1) > 0.001 && Math.abs(y2 - y1) > 0.001) {
        // Save current domain to history for undo
        if (currentDomain) {
          setZoomHistory((prev) => [...prev, currentDomain]);
        } else {
          setZoomHistory((prev) => [...prev, effectiveDomain]);
        }

        setCurrentDomain({
          x: [x1, x2],
          y: [y1, y2],
        });
      }
    }

    setIsSelecting(false);
    setSelectionStart(null);
    setSelectionEnd(null);
  }, [
    isSelecting,
    selectionStart,
    selectionEnd,
    currentDomain,
    effectiveDomain,
  ]);

  const hasData = sortedFrontier.length > 0 || portfolioPoints.length > 0;
  const hasCurrentPortfolio = clampedPortfolioPoints.find(
    (p) => p.type === "current",
  );
  const hasWeightsOptimized = clampedPortfolioPoints.find(
    (p) => p.type === "weights-optimized",
  );
  const hasMarketOptimized = clampedPortfolioPoints.find(
    (p) => p.type === "market-optimized",
  );

  // Dynamic metrics for educational copy (market-optimized preferred, else weights-optimized)
  const optimalPortfolio =
    marketOptimizedPortfolio ?? weightsOptimizedPortfolio;
  const explanationMetrics = useMemo(() => {
    const cur = currentPortfolio;
    const opt = optimalPortfolio;
    if (!cur) return null;
    const curRet = (cur.return ?? 0) * 100;
    const curRisk = (cur.risk ?? 0) * 100;
    const curSharpe =
      cur.sharpe_ratio != null && isFinite(cur.sharpe_ratio)
        ? cur.sharpe_ratio.toFixed(2)
        : "—";
    if (!opt) {
      return {
        currentReturn: curRet.toFixed(2),
        currentRisk: curRisk.toFixed(2),
        currentSharpe: curSharpe,
        hasOptimal: false,
        optimalReturn: "",
        optimalRisk: "",
        optimalSharpe: "",
        riskReductionPct: "",
        returnDelta: "",
        riskDelta: "",
      };
    }
    const optRet = (opt.return ?? 0) * 100;
    const optRisk = (opt.risk ?? 0) * 100;
    const optSharpe =
      opt.sharpe_ratio != null && isFinite(opt.sharpe_ratio)
        ? opt.sharpe_ratio.toFixed(2)
        : "—";
    const riskReductionPct =
      curRisk > 0 ? (((curRisk - optRisk) / curRisk) * 100).toFixed(1) : "—";
    const returnDelta = (optRet - curRet).toFixed(2);
    const riskDelta = (optRisk - curRisk).toFixed(2);
    return {
      currentReturn: curRet.toFixed(2),
      currentRisk: curRisk.toFixed(2),
      currentSharpe: curSharpe,
      hasOptimal: true,
      optimalReturn: optRet.toFixed(2),
      optimalRisk: optRisk.toFixed(2),
      optimalSharpe: optSharpe,
      riskReductionPct,
      returnDelta: Number(returnDelta) >= 0 ? `+${returnDelta}` : returnDelta,
      riskDelta: Number(riskDelta) <= 0 ? riskDelta : `+${riskDelta}`,
    };
  }, [currentPortfolio, optimalPortfolio]);

  return (
    <Card
      className={className}
      style={{
        background: chartTheme.cardBackground,
        borderColor: chartTheme.border,
      }}
    >
      <CardHeader className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex-1 text-center">
            <CardTitle
              className="text-lg"
              style={{
                color: chartTheme.text.primary,
                fontWeight: 600,
                letterSpacing: "-0.01em",
              }}
            >
              Efficient Frontier
            </CardTitle>
            <p
              className="text-xs mt-1"
              style={{ color: chartTheme.text.subtle }}
            >
              {showControls
                ? "Drag to zoom • Click legend to toggle series"
                : "Risk vs. Return analysis"}
            </p>
          </div>
          {showControls && (
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={zoomIn}
                className="h-7 w-7 p-0"
                title="Zoom in"
                disabled={zoomLevel >= 10}
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={currentDomain ? resetZoom : zoomOut}
                className="h-7 w-7 p-0"
                title="Zoom out"
                disabled={zoomLevel <= 0.5 && !currentDomain}
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={resetZoom}
                className="h-7 px-2 text-xs"
                title="Reset zoom"
                disabled={zoomLevel === 1 && !currentDomain}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1" />
                Reset
              </Button>
            </div>
          )}
        </div>

        {/* Interactive Legend with Visibility Toggles */}
        {showInteractiveLegend && (
          <div
            className="flex flex-wrap gap-2 justify-center border-t pt-3"
            style={{ borderColor: chartTheme.border }}
          >
            {/* Random Portfolios Toggle */}
            {randomPortfolios && randomPortfolios.length > 0 && (
              <button
                onClick={() => toggleSeriesVisibility("randomPortfolios")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.randomPortfolios
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.randomPortfolios
                    ? "Hide Random Portfolios"
                    : "Show Random Portfolios"
                }
              >
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: "#cbd5e1" }}
                />
                <span className="font-medium">Random</span>
              </button>
            )}

            {/* Efficient Frontier Toggle */}
            {efficientFrontier && efficientFrontier.length > 0 && (
              <button
                onClick={() => toggleSeriesVisibility("efficientFrontier")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.efficientFrontier
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.efficientFrontier
                    ? "Hide Efficient Frontier"
                    : "Show Efficient Frontier"
                }
              >
                <div
                  className="w-4 h-0.5"
                  style={{ backgroundColor: "#64748b" }}
                />
                <span className="font-medium text-foreground">Efficient</span>
              </button>
            )}

            {/* Inefficient Frontier Toggle */}
            {inefficientFrontier && inefficientFrontier.length > 0 && (
              <button
                onClick={() => toggleSeriesVisibility("inefficientFrontier")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.inefficientFrontier
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.inefficientFrontier
                    ? "Hide Inefficient Frontier"
                    : "Show Inefficient Frontier"
                }
              >
                <div className="flex gap-0.5">
                  <div
                    className="w-1.5 h-0.5"
                    style={{ backgroundColor: "#64748b" }}
                  />
                  <div
                    className="w-1.5 h-0.5"
                    style={{ backgroundColor: "#64748b" }}
                  />
                </div>
                <span className="font-medium text-foreground">Inefficient</span>
              </button>
            )}

            {/* CML Toggle */}
            {capitalMarketLine && capitalMarketLine.length > 0 && (
              <button
                onClick={() => toggleSeriesVisibility("cml")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.cml
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.cml
                    ? "Hide Capital Market Line"
                    : "Show Capital Market Line"
                }
              >
                <div className="flex gap-0.5">
                  <div
                    className="w-1 h-0.5"
                    style={{ backgroundColor: "#9333ea" }}
                  />
                  <div
                    className="w-1 h-0.5"
                    style={{ backgroundColor: "#9333ea" }}
                  />
                </div>
                <span className="font-medium text-foreground">CML</span>
              </button>
            )}

            {/* Current Portfolio Toggle */}
            {currentPortfolio && (
              <button
                onClick={() => toggleSeriesVisibility("currentPortfolio")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.currentPortfolio
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.currentPortfolio
                    ? "Hide Current Portfolio"
                    : "Show Current Portfolio"
                }
              >
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: "#ef4444" }}
                />
                <span className="font-medium text-foreground">Current</span>
              </button>
            )}

            {/* Weights-Optimized Toggle */}
            {weightsOptimizedPortfolio && (
              <button
                onClick={() => toggleSeriesVisibility("weightsOptimized")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.weightsOptimized
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.weightsOptimized
                    ? "Hide Weights-Optimized"
                    : "Show Weights-Optimized"
                }
              >
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: "#3b82f6" }}
                />
                <span className="font-medium text-foreground">Weights</span>
              </button>
            )}

            {/* Market-Optimized Toggle */}
            {marketOptimizedPortfolio && (
              <button
                onClick={() => toggleSeriesVisibility("marketOptimized")}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                  visibleSeries.marketOptimized
                    ? "border-border bg-card hover:bg-accent text-foreground"
                    : "border-border bg-muted/50 text-muted-foreground opacity-70"
                }`}
                title={
                  visibleSeries.marketOptimized
                    ? "Hide Market-Optimized"
                    : "Show Market-Optimized"
                }
              >
                <svg width="12" height="12" viewBox="0 0 16 16">
                  <polygon
                    points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6"
                    fill="#22c55e"
                    stroke="#fff"
                    strokeWidth="0.5"
                  />
                </svg>
                <span className="font-medium text-foreground">Market</span>
              </button>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent
        className="min-h-[500px] h-[500px]"
        style={{
          background: chartTheme.canvas,
          borderRadius: layoutConstants.radius,
          padding: "12px",
        }}
      >
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              margin={{ top: 24, right: 32, bottom: 64, left: 56 }}
              onMouseDown={showControls ? handleMouseDown : undefined}
              onMouseMove={showControls ? handleMouseMove : undefined}
              onMouseUp={showControls ? handleMouseUp : undefined}
              onMouseLeave={() => {
                if (isSelecting) {
                  setIsSelecting(false);
                  setSelectionStart(null);
                  setSelectionEnd(null);
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 4" stroke={chartTheme.grid} />
              <XAxis
                type="number"
                dataKey="risk"
                name="Risk"
                tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                axisLine={{ stroke: chartTheme.axes.line }}
                tickLine={{ stroke: "transparent" }}
                tick={{
                  fill: chartTheme.axes.tick,
                  fontSize: 12,
                  fontWeight: 500,
                }}
                domain={effectiveDomain.x}
                allowDataOverflow={true}
                label={{
                  value: "Risk",
                  position: "insideBottom",
                  offset: -6,
                  style: { fill: chartTheme.axes.label, fontWeight: 500 },
                }}
              />
              <YAxis
                type="number"
                dataKey="return"
                name="Return"
                tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                axisLine={{ stroke: chartTheme.axes.line }}
                tickLine={{ stroke: "transparent" }}
                tick={{
                  fill: chartTheme.axes.tick,
                  fontSize: 12,
                  fontWeight: 500,
                }}
                allowDataOverflow={true}
                domain={effectiveDomain.y}
                label={{
                  value: "Return",
                  angle: -90,
                  position: "left",
                  offset: 16,
                  style: { fill: chartTheme.axes.label, fontWeight: 500 },
                }}
              />
              <RechartsTooltip
                cursor={!isSelecting ? { strokeDasharray: "3 3" } : false}
                content={({
                  active,
                  payload,
                }: TooltipProps<ValueType, NameType>) => {
                  if (isSelecting) return null;
                  if (!active || !payload || payload.length === 0) return null;

                  // Portfolio points take priority — when hovering near a frontier
                  // line and a portfolio point simultaneously, show the portfolio.
                  const portfolioPayloadItem = payload.find((p: any) => {
                    const t = p?.payload?.type;
                    return (
                      t === "current" ||
                      t === "weights-optimized" ||
                      t === "market-optimized"
                    );
                  });
                  const firstPayload = portfolioPayloadItem || payload[0];
                  if (!firstPayload || !firstPayload.payload) return null;
                  const data = firstPayload.payload as ClampedPortfolioPoint;
                  // Use original (unclamped) return for display; clamped value is
                  // only used for SVG positioning when the point is off-scale.
                  const displayReturn = data.displayReturn ?? data.return;

                  // Check tooltip type
                  const isEfficientFrontierLine =
                    firstPayload.name === "Efficient Frontier" ||
                    data.type === "frontier";
                  const isInefficientFrontierLine =
                    firstPayload.name === "Inefficient Frontier" ||
                    data.type === "inefficient_frontier";
                  const isCML =
                    firstPayload.name === "Capital Market Line" ||
                    data.type === "cml";
                  const isPortfolioPoint =
                    data.type === "current" ||
                    data.type === "weights-optimized" ||
                    data.type === "market-optimized";

                  if (
                    !isEfficientFrontierLine &&
                    !isInefficientFrontierLine &&
                    !isCML &&
                    !isPortfolioPoint
                  )
                    return null;

                  // Safety check for required properties
                  if (
                    data.return == null ||
                    data.risk == null ||
                    typeof data.return !== "number" ||
                    typeof data.risk !== "number" ||
                    !isFinite(data.return) ||
                    !isFinite(data.risk)
                  )
                    return null;

                  if (isEfficientFrontierLine) {
                    return (
                      <div
                        className="rounded-lg border p-2 shadow-md max-w-xs"
                        style={{
                          background: chartTheme.cardBackground,
                          borderColor: "#64748b",
                        }}
                      >
                        <p
                          className="font-semibold text-sm"
                          style={{ color: "#64748b" }}
                        >
                          Efficient Frontier
                        </p>
                        <p
                          className="text-xs mt-1"
                          style={{ color: chartTheme.text.secondary }}
                        >
                          Optimal portfolios offering maximum return for given
                          risk levels.
                        </p>
                        <div
                          className="mt-2 space-y-1 text-xs"
                          style={{ color: chartTheme.text.primary }}
                        >
                          <p>
                            Return:{" "}
                            <span className="font-medium">
                              {formatPercent(data.return)}
                            </span>
                          </p>
                          <p>
                            Risk:{" "}
                            <span className="font-medium">
                              {formatPercent(data.risk)}
                            </span>
                          </p>
                          {data.sharpe_ratio != null &&
                            typeof data.sharpe_ratio === "number" &&
                            isFinite(data.sharpe_ratio) && (
                              <p>
                                Sharpe:{" "}
                                <span className="font-medium">
                                  {data.sharpe_ratio.toFixed(2)}
                                </span>
                              </p>
                            )}
                        </div>
                      </div>
                    );
                  }

                  if (isInefficientFrontierLine) {
                    return (
                      <div
                        className="rounded-lg border p-2 shadow-md max-w-xs"
                        style={{
                          background: chartTheme.cardBackground,
                          borderColor: "#94a3b8",
                        }}
                      >
                        <p
                          className="font-semibold text-sm"
                          style={{ color: "#94a3b8" }}
                        >
                          Inefficient Frontier
                        </p>
                        <p
                          className="text-xs mt-1"
                          style={{ color: chartTheme.text.secondary }}
                        >
                          Portfolios with minimum return for given risk levels
                          (lower branch).
                        </p>
                        <div
                          className="mt-2 space-y-1 text-xs"
                          style={{ color: chartTheme.text.primary }}
                        >
                          <p>
                            Return:{" "}
                            <span className="font-medium">
                              {formatPercent(data.return)}
                            </span>
                          </p>
                          <p>
                            Risk:{" "}
                            <span className="font-medium">
                              {formatPercent(data.risk)}
                            </span>
                          </p>
                        </div>
                      </div>
                    );
                  }

                  if (isCML) {
                    return (
                      <div
                        className="rounded-lg border p-2 shadow-md max-w-xs"
                        style={{
                          background: chartTheme.cardBackground,
                          borderColor: "#9333ea",
                        }}
                      >
                        <p
                          className="font-semibold text-sm"
                          style={{ color: "#9333ea" }}
                        >
                          Capital Market Line (CML)
                        </p>
                        <p
                          className="text-xs mt-1"
                          style={{ color: chartTheme.text.secondary }}
                        >
                          Optimal risk-return combinations combining risk-free
                          assets with the market portfolio.
                        </p>
                      </div>
                    );
                  }

                  // Portfolio point tooltip
                  const currentPortfolioMetrics = currentPortfolio;
                  const showComparison =
                    data.type !== "current" && currentPortfolioMetrics != null;

                  return (
                    <div
                      className="rounded-xl border p-3 shadow-lg max-w-xs"
                      style={{
                        background: chartTheme.cardBackground,
                        borderColor: chartTheme.border,
                      }}
                    >
                      <p
                        className="font-bold text-sm pb-2 mb-2 border-b"
                        style={{
                          color: chartTheme.text.primary,
                          borderColor: chartTheme.border,
                        }}
                      >
                        {data.type === "current"
                          ? "Current Portfolio"
                          : data.type === "weights-optimized"
                            ? "Weights-Optimized Portfolio"
                            : data.type === "market-optimized"
                              ? "Market-Optimized Portfolio"
                              : "Portfolio"}
                      </p>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                          <span style={{ color: chartTheme.text.secondary }}>
                            Return (μ):
                          </span>
                          <span
                            className="font-semibold"
                            style={{ color: chartTheme.text.primary }}
                          >
                            {formatPercent(displayReturn)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span style={{ color: chartTheme.text.secondary }}>
                            Risk (σ):
                          </span>
                          <span
                            className="font-semibold"
                            style={{ color: chartTheme.text.primary }}
                          >
                            {formatPercent(data.risk)}
                          </span>
                        </div>
                        {data.sharpe_ratio != null &&
                          typeof data.sharpe_ratio === "number" &&
                          isFinite(data.sharpe_ratio) && (
                            <div className="flex justify-between">
                              <span
                                style={{ color: chartTheme.text.secondary }}
                              >
                                Sharpe Ratio:
                              </span>
                              <span
                                className="font-semibold"
                                style={{ color: chartTheme.text.primary }}
                              >
                                {data.sharpe_ratio.toFixed(3)}
                              </span>
                            </div>
                          )}
                      </div>

                      {/* Comparison to current portfolio */}
                      {showComparison && currentPortfolioMetrics && (
                        <div
                          className="mt-3 pt-2 border-t"
                          style={{ borderColor: chartTheme.border }}
                        >
                          <div
                            className="text-xs font-semibold mb-1.5"
                            style={{ color: chartTheme.text.secondary }}
                          >
                            vs Current Portfolio:
                          </div>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between">
                              <span
                                style={{ color: chartTheme.text.secondary }}
                              >
                                Δ Return:
                              </span>
                              <span
                                className={`font-semibold ${displayReturn > currentPortfolioMetrics.return ? "text-green-500" : "text-red-500"}`}
                              >
                                {displayReturn > currentPortfolioMetrics.return
                                  ? "+"
                                  : ""}
                                {formatPercent(
                                  displayReturn -
                                    currentPortfolioMetrics.return,
                                )}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span
                                style={{ color: chartTheme.text.secondary }}
                              >
                                Δ Risk:
                              </span>
                              <span
                                className={`font-semibold ${data.risk < currentPortfolioMetrics.risk ? "text-green-500" : "text-red-500"}`}
                              >
                                {data.risk < currentPortfolioMetrics.risk
                                  ? ""
                                  : "+"}
                                {formatPercent(
                                  data.risk - currentPortfolioMetrics.risk,
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }}
              />

              {/* Selection Rectangle for Box Zoom */}
              {isSelecting && selectionStart && selectionEnd && (
                <ReferenceArea
                  x1={Math.min(selectionStart.x, selectionEnd.x)}
                  x2={Math.max(selectionStart.x, selectionEnd.x)}
                  y1={Math.min(selectionStart.y, selectionEnd.y)}
                  y2={Math.max(selectionStart.y, selectionEnd.y)}
                  strokeOpacity={0.3}
                  fill="#3b82f6"
                  fillOpacity={0.1}
                  stroke="#3b82f6"
                  strokeWidth={1}
                />
              )}

              {/* Random Portfolios (background scatter) */}
              {filteredRandomPortfolios.length > 0 && (
                <Scatter
                  name="Random Portfolios"
                  data={filteredRandomPortfolios}
                  fill="#cbd5e1"
                  fillOpacity={0.3}
                  shape={(props: any) => (
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={3}
                      fill="#cbd5e1"
                      fillOpacity={0.3}
                      stroke="#94a3b8"
                      strokeOpacity={0.2}
                      strokeWidth={0.5}
                    />
                  )}
                />
              )}

              {/* Inefficient Frontier (dashed line) */}
              {sortedInefficientFrontier.length > 0 && (
                <Line
                  name="Inefficient Frontier"
                  type="monotone"
                  dataKey="return"
                  data={sortedInefficientFrontier}
                  stroke="#64748b"
                  strokeWidth={2.5}
                  strokeDasharray="6 4"
                  strokeOpacity={0.7}
                  dot={false}
                  activeDot={{
                    r: 6,
                    fill: "#64748b",
                    stroke: "#fff",
                    strokeWidth: 2,
                  }}
                  isAnimationActive={true}
                  animationDuration={1500}
                  animationEasing="ease-out"
                  connectNulls={true}
                />
              )}

              {/* Efficient Frontier (solid line) */}
              {sortedFrontier.length > 0 && (
                <Line
                  name="Efficient Frontier"
                  type="monotone"
                  dataKey="return"
                  data={sortedFrontier}
                  stroke="#64748b"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: "#64748b",
                    stroke: "#fff",
                    strokeWidth: 2,
                  }}
                  isAnimationActive={true}
                  animationDuration={1500}
                  animationEasing="ease-out"
                  connectNulls={true}
                />
              )}

              {/* Capital Market Line */}
              {capitalMarketLine &&
                visibleSeries.cml &&
                capitalMarketLine.length > 0 && (
                  <Line
                    name="Capital Market Line"
                    type="linear"
                    dataKey="return"
                    data={capitalMarketLine.map((p) => ({ ...p, type: "cml" }))}
                    stroke="#9333ea"
                    strokeWidth={2}
                    strokeDasharray="4 3"
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "#9333ea",
                      stroke: "#fff",
                      strokeWidth: 2,
                    }}
                    isAnimationActive={true}
                    animationDuration={1500}
                    animationEasing="ease-out"
                    connectNulls={true}
                  />
                )}

              {/* Current Portfolio - RED circle with white dot */}
              {hasCurrentPortfolio && (
                <Scatter
                  name="Current Portfolio"
                  data={[
                    clampedPortfolioPoints.find((p) => p.type === "current")!,
                  ]}
                  fill="#ef4444"
                  fillOpacity={1}
                  shape={(props: any) => {
                    if (props.isOffScaleHigh) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#ef4444"
                            fillOpacity={0.2}
                            stroke="#ef4444"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy - 13} ${props.cx - 7},${props.cy - 3} ${props.cx + 7},${props.cy - 3}`}
                            fill="#ef4444"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    if (props.isOffScaleLow) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#ef4444"
                            fillOpacity={0.2}
                            stroke="#ef4444"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy + 13} ${props.cx - 7},${props.cy + 3} ${props.cx + 7},${props.cy + 3}`}
                            fill="#ef4444"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    return (
                      <g>
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={14}
                          fill="#ef4444"
                          fillOpacity={0.2}
                        />
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={10}
                          fill="#ef4444"
                          stroke="#fff"
                          strokeWidth={3}
                        />
                        <circle cx={props.cx} cy={props.cy} r={4} fill="#fff" />
                      </g>
                    );
                  }}
                />
              )}

              {/* Weights-Optimized Portfolio - BLUE diamond */}
              {hasWeightsOptimized && (
                <Scatter
                  name="Weights-Optimized Portfolio"
                  data={[
                    clampedPortfolioPoints.find(
                      (p) => p.type === "weights-optimized",
                    )!,
                  ]}
                  fill="#3b82f6"
                  fillOpacity={1}
                  shape={(props: any) => {
                    if (props.isOffScaleHigh) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#3b82f6"
                            fillOpacity={0.2}
                            stroke="#3b82f6"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy - 13} ${props.cx - 7},${props.cy - 3} ${props.cx + 7},${props.cy - 3}`}
                            fill="#3b82f6"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    if (props.isOffScaleLow) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#3b82f6"
                            fillOpacity={0.2}
                            stroke="#3b82f6"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy + 13} ${props.cx - 7},${props.cy + 3} ${props.cx + 7},${props.cy + 3}`}
                            fill="#3b82f6"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    const size = 10;
                    return (
                      <g>
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={14}
                          fill="#3b82f6"
                          fillOpacity={0.2}
                        />
                        <polygon
                          points={[
                            `${props.cx},${props.cy - size}`,
                            `${props.cx + size},${props.cy}`,
                            `${props.cx},${props.cy + size}`,
                            `${props.cx - size},${props.cy}`,
                          ].join(" ")}
                          fill="#3b82f6"
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      </g>
                    );
                  }}
                />
              )}

              {/* Market-Optimized Portfolio - GREEN star */}
              {hasMarketOptimized && (
                <Scatter
                  name="Market-Optimized Portfolio"
                  data={[
                    clampedPortfolioPoints.find(
                      (p) => p.type === "market-optimized",
                    )!,
                  ]}
                  fill="#22c55e"
                  fillOpacity={1}
                  shape={(props: any) => {
                    if (props.isOffScaleHigh) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#22c55e"
                            fillOpacity={0.2}
                            stroke="#22c55e"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy - 13} ${props.cx - 7},${props.cy - 3} ${props.cx + 7},${props.cy - 3}`}
                            fill="#22c55e"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    if (props.isOffScaleLow) {
                      return (
                        <g>
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#22c55e"
                            fillOpacity={0.2}
                            stroke="#22c55e"
                            strokeWidth={1}
                          />
                          <polygon
                            points={`${props.cx},${props.cy + 13} ${props.cx - 7},${props.cy + 3} ${props.cx + 7},${props.cy + 3}`}
                            fill="#22c55e"
                            stroke="#fff"
                            strokeWidth={1.5}
                          />
                        </g>
                      );
                    }
                    const outerR = 12;
                    const innerR = 5;
                    const starPoints = [];
                    for (let i = 0; i < 10; i++) {
                      const r = i % 2 === 0 ? outerR : innerR;
                      const angle = ((i * 36 - 90) * Math.PI) / 180;
                      starPoints.push(
                        `${props.cx + r * Math.cos(angle)},${props.cy + r * Math.sin(angle)}`,
                      );
                    }
                    return (
                      <g>
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={16}
                          fill="#22c55e"
                          fillOpacity={0.2}
                        />
                        <polygon
                          points={starPoints.join(" ")}
                          fill="#22c55e"
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      </g>
                    );
                  }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm" style={{ color: chartTheme.text.secondary }}>
              Run portfolio optimization to generate efficient frontier
              analysis.
            </p>
          </div>
        )}
      </CardContent>

      {/* Collapsible educational section: below graph, theme-aware, hidden by default */}
      <div className="px-6 pb-4">
        <Collapsible
          className="group rounded-md border"
          style={{ borderColor: chartTheme.border }}
        >
          <CollapsibleTrigger
            className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium transition-colors hover:opacity-90"
            style={{
              color: chartTheme.text.primary,
              background: chartTheme.canvas,
            }}
          >
            <div className="flex items-center gap-1.5">
              <BookOpen
                className="h-3.5 w-3.5 shrink-0"
                style={{ color: chartTheme.text.secondary }}
              />
              <span>Understanding this chart</span>
            </div>
            <ChevronDown
              className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180"
              style={{ color: chartTheme.text.secondary }}
            />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div
              className="border-t px-3 py-3 text-xs space-y-3 max-h-[280px] overflow-y-auto"
              style={{
                borderColor: chartTheme.border,
                color: chartTheme.text.secondary,
                background: chartTheme.cardBackground,
              }}
            >
              <section>
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Risk and return tradeoff
                </p>
                <p>
                  Expected return and volatility are positively related. In
                  equilibrium, higher expected return is associated with higher
                  risk. The relationship is analogous to yield and credit risk
                  in fixed income: greater reward typically requires bearing
                  more uncertainty.{" "}
                  {explanationMetrics?.hasOptimal && (
                    <>
                      Your current portfolio implies{" "}
                      <strong style={{ color: chartTheme.text.primary }}>
                        {explanationMetrics.currentReturn}%
                      </strong>{" "}
                      expected return at{" "}
                      <strong style={{ color: chartTheme.text.primary }}>
                        {explanationMetrics.currentRisk}%
                      </strong>{" "}
                      volatility. The market-optimized portfolio targets{" "}
                      <strong style={{ color: chartTheme.text.primary }}>
                        {explanationMetrics.optimalReturn}%
                      </strong>{" "}
                      return at{" "}
                      <strong style={{ color: chartTheme.text.primary }}>
                        {explanationMetrics.optimalRisk}%
                      </strong>{" "}
                      volatility.
                    </>
                  )}
                </p>
              </section>
              <section
                className="pt-2 border-t"
                style={{ borderColor: chartTheme.border }}
              >
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Markowitz optimization
                </p>
                <p>
                  The curve is the mean-variance efficient set: portfolios that
                  maximize expected return for a given level of risk, as
                  formalized by Harry Markowitz (1952). It is the investment
                  analogue of a production-possibility frontier, the boundary of
                  achievable risk and return outcomes.{" "}
                  {explanationMetrics?.hasOptimal &&
                    explanationMetrics.currentSharpe !== "—" &&
                    explanationMetrics.optimalSharpe !== "—" && (
                      <>
                        Moving toward the frontier can raise the Sharpe ratio
                        from{" "}
                        <strong style={{ color: chartTheme.text.primary }}>
                          {explanationMetrics.currentSharpe}
                        </strong>{" "}
                        to{" "}
                        <strong style={{ color: chartTheme.text.primary }}>
                          {explanationMetrics.optimalSharpe}
                        </strong>
                        .
                      </>
                    )}
                </p>
              </section>
              <section
                className="pt-2 border-t"
                style={{ borderColor: chartTheme.border }}
              >
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Diversification benefit
                </p>
                <p>
                  Efficient portfolios exploit diversification. Holding assets
                  whose returns are not perfectly correlated reduces portfolio
                  variance without sacrificing return proportionally. The idea
                  is analogous to a structural truss, where load is distributed
                  across members so that no single element bears the full
                  stress.{" "}
                  {explanationMetrics?.hasOptimal &&
                    explanationMetrics.riskReductionPct !== "—" &&
                    Number(explanationMetrics.riskReductionPct) > 0 && (
                      <>
                        The optimized portfolio can lower volatility by
                        approximately{" "}
                        <strong style={{ color: chartTheme.text.primary }}>
                          {explanationMetrics.riskReductionPct}%
                        </strong>{" "}
                        while targeting similar or higher return.
                      </>
                    )}
                </p>
              </section>
              <section
                className="pt-2 border-t"
                style={{ borderColor: chartTheme.border }}
              >
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Interpretation of positions
                </p>
                <p>
                  Points above the curve are not attainable. Points on the curve
                  are mean-variance efficient. Points below are dominated:
                  another portfolio offers the same return with lower risk, or
                  higher return for the same risk. The current portfolio (red)
                  and the optimized portfolio (green star or blue diamond) can
                  be compared accordingly. Moving toward the frontier improves
                  the risk-adjusted outcome.
                </p>
              </section>
              <section
                className="pt-2 border-t"
                style={{ borderColor: chartTheme.border }}
              >
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Capital Market Line (CML)
                </p>
                <p>
                  The purple dashed line represents combinations of the
                  risk-free asset and the tangency (market) portfolio. It is the
                  efficient way to choose exposure to market risk, analogous to
                  a single control that moves allocation along the optimal
                  trade-off from the risk-free rate to the market portfolio.
                </p>
              </section>
              <section
                className="pt-2 border-t"
                style={{ borderColor: chartTheme.border }}
              >
                <p
                  className="font-semibold mb-1"
                  style={{ color: chartTheme.text.primary }}
                >
                  Weights-optimized vs market-optimized
                </p>
                <p>
                  The weights-optimized portfolio (blue diamond) optimizes only
                  the allocation across your chosen assets. The market-optimized
                  portfolio (green star) also considers a risk-free asset and
                  targets maximum Sharpe ratio. In some cases the
                  weights-optimized portfolio can outperform the
                  market-optimized one. That can happen when your universe
                  contains names with strong expected returns that the optimizer
                  tilts into.{" "}
                  {weightsOptimizedTickerExample ? (
                    <>
                      For example, a holding such as{" "}
                      <strong style={{ color: chartTheme.text.primary }}>
                        {weightsOptimizedTickerExample}
                      </strong>{" "}
                      may have a higher expected return in the model than the
                      average market exposure, so the weights-optimized solution
                      can lean into it and achieve a better risk-adjusted result
                      than the market portfolio alone.
                    </>
                  ) : (
                    <>
                      For example, certain names in the weights-optimized
                      portfolio may have higher expected returns in the model
                      than the average market exposure. The optimizer can then
                      tilt into those names and deliver a better risk-adjusted
                      result than the market portfolio alone.
                    </>
                  )}
                </p>
              </section>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>

      {/* Static Legend (shown when interactive legend is disabled) */}
      {!showInteractiveLegend && (
        <div className="px-6 pb-6">
          <div className="flex flex-wrap gap-4 text-xs justify-center pt-2">
            {sortedFrontier.length > 0 && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-slate-500"></div>
                <span style={{ color: chartTheme.text.secondary }}>
                  Efficient Frontier
                </span>
              </div>
            )}
            {hasCurrentPortfolio && (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-background shadow"></div>
                <span style={{ color: chartTheme.text.secondary }}>
                  Current Portfolio
                </span>
              </div>
            )}
            {hasWeightsOptimized && (
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rotate-45"
                  style={{
                    width: "12px",
                    height: "12px",
                    backgroundColor: "#3b82f6",
                    border: "2px solid var(--background)",
                  }}
                ></div>
                <span style={{ color: chartTheme.text.secondary }}>
                  Weights-Optimized
                </span>
              </div>
            )}
            {hasMarketOptimized && (
              <div className="flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 16 16">
                  <polygon
                    points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6"
                    fill="#22c55e"
                    stroke="#fff"
                    strokeWidth="0.5"
                  />
                </svg>
                <span style={{ color: chartTheme.text.secondary }}>
                  Market-Optimized
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};
