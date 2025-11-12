import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
} from 'recharts';
import {
  Pie,
  PieChart,
  Cell,
  Tooltip as PieTooltip,
} from 'recharts';
import type { TooltipProps, ValueType, NameType } from 'recharts';
import { Loader2, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

const visualizationTheme = {
  canvas: '#FAFAF4',
  cardBackground: '#FFFFFF',
  border: 'rgba(90, 90, 82, 0.12)',
  grid: 'rgba(226, 226, 221, 0.7)',
  axes: {
    line: 'rgba(94, 94, 86, 0.28)',
    tick: 'rgba(75, 75, 68, 0.82)',
    label: '#3B3B33',
  },
  text: {
    primary: '#2F2F29',
    secondary: '#6D6D62',
    subtle: 'rgba(90, 90, 82, 0.65)',
  },
  clusterPalette: {
    selected: '#82BCB0',
    benchmark1: '#D9A49A',
    benchmark2: '#B7C089',
    benchmarks: ['#D9A49A', '#B7C089', '#A3B9D9', '#C9AFD9', '#E0C0A0'],
    fallback: '#8EA9BA',
  },
  portfolioPalette: ['#82BCB0', '#D9A49A', '#B7C089', '#A3B9D9', '#C9AFD9', '#E7C79B', '#99C2C9', '#C2D7A0', '#8EA9BA', '#B2C5E5'],
  hull: {
    strokeOpacity: 0.55,
    strokeDasharray: '5 6',
  },
  pie: {
    palette: ['#82BCB0', '#D9A49A', '#B7C089', '#A3B9D9', '#C9AFD9', '#E7C79B', '#99C2C9', '#C2D7A0'],
  },
  spacing: {
    cardPadding: '28px',
    sectionGap: '28px',
  },
  radius: '18px',
  hoverFadeOpacity: 0.4,
  legend: {
    fontSize: 12,
    color: 'rgba(59, 59, 51, 0.8)',
  },
};

interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
}

interface PortfolioRecommendation {
  name: string;
  allocations: PortfolioAllocation[];
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
}

interface ScatterPoint {
  symbol: string;
  portfolioLabel: string;
  annualReturn: number;
  risk: number;
  diversificationScore: number;
  sector: string;
  clusterId: number;
  allocation: number;
  color: string;
}

type ClusterHull = {
  label: string;
  color: string;
  points: ScatterPoint[];
};

const clusterColorForLabel = (label: string, index: number): string => {
  const normalized = label.toLowerCase();
  if (normalized.includes('selected')) {
    return visualizationTheme.clusterPalette.selected;
  }
  if (normalized.includes('benchmark 1')) {
    return visualizationTheme.clusterPalette.benchmark1;
  }
  if (normalized.includes('benchmark 2')) {
    return visualizationTheme.clusterPalette.benchmark2;
  }

  const palette = visualizationTheme.clusterPalette.benchmarks;
  return palette[index % palette.length] ?? visualizationTheme.clusterPalette.fallback;
};

const getPortfolioColorGenerator = (palette: string[]) => {
  const assignments = new Map<string, string>();
  let nextIndex = 0;

  return (label: string) => {
    if (!assignments.has(label)) {
      const color = palette[nextIndex % palette.length] ?? visualizationTheme.clusterPalette.fallback;
      assignments.set(label, color);
      nextIndex += 1;
    }
    return assignments.get(label) ?? visualizationTheme.clusterPalette.fallback;
  };
};

const computeConvexHull = (points: ScatterPoint[]): ScatterPoint[] => {
  if (points.length < 3) return [];

  const sorted = [...points].sort((a, b) => (a.risk === b.risk ? a.annualReturn - b.annualReturn : a.risk - b.risk));

  const cross = (o: ScatterPoint, a: ScatterPoint, b: ScatterPoint) =>
    (a.risk - o.risk) * (b.annualReturn - o.annualReturn) - (a.annualReturn - o.annualReturn) * (b.risk - o.risk);

  const lower: ScatterPoint[] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  const upper: ScatterPoint[] = [];
  for (let i = sorted.length - 1; i >= 0; i -= 1) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  upper.pop();
  lower.pop();
  return [...lower, ...upper];
};

interface RawClusteringPoint {
  label: string;
  risk: number;
  returnValue: number;
  symbol?: string | null;
  sector?: string | null;
  allocation?: number | null;
  diversificationScore?: number | null;
}

interface RawClusterInfo {
  center: {
    risk: number;
    returnValue: number;
  };
  points: number[];
  label: string;
  hullPoints?: number[];
}

interface RawClusteringData {
  points: RawClusteringPoint[];
  clusters: RawClusterInfo[];
  palette: string[];
  warnings: string[];
  metadata: Record<string, unknown>;
}

interface CorrelationData {
  tickers: string[];
  matrix: number[][];
  sectors: string[];
  portfolioLabels: string[];
  sectorMap?: Record<string, string>;
}

interface SectorAllocationEntry {
  sector: string;
  weight?: number;
  percent?: number;
  color: string;
  holdings: string[];
}

interface SectorAllocationData {
  sectors: SectorAllocationEntry[];
  totalPercent: number;
  warnings: string[];
  metadata: Record<string, unknown>;
}

type SectorData = {
  sector: string;
  percent: number;
  holdings: string[];
  stockAllocations?: Array<{ symbol: string; allocation: number }>;
};

interface VisualizationResponse {
  clustering: RawClusteringData;
  correlation: CorrelationData;
  sectorAllocation: SectorAllocationData;
  warnings?: string[];
  metadata?: Record<string, unknown>;
}

interface Portfolio3PartVisualizationProps {
  selectedStocks: PortfolioAllocation[];
  allRecommendations: PortfolioRecommendation[];
  selectedPortfolioIndex: number | null;
  riskProfile: string;
}

type FetchState = 'idle' | 'loading' | 'success' | 'error';

const CORRELATION_MIN = -1;
const CORRELATION_MAX = 1;

const getCorrelationColor = (value: number) => {
  if (Number.isNaN(value)) return 'rgba(148, 163, 184, 0.18)';
  const clamped = Math.max(CORRELATION_MIN, Math.min(CORRELATION_MAX, value));
  const ratio = (clamped - CORRELATION_MIN) / (CORRELATION_MAX - CORRELATION_MIN);
  const red = Math.round(222 + (84 - 222) * ratio);
  const green = Math.round(170 + (128 - 170) * ratio);
  const blue = Math.round(158 + (98 - 158) * ratio);
  const alpha = 0.12 + 0.45 * Math.abs(clamped);
  return `rgba(${red}, ${green}, ${blue}, ${alpha.toFixed(2)})`;
};

const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

const fetchVisualizationData = async (
  payload: Record<string, unknown>,
  signal?: AbortSignal
): Promise<VisualizationResponse> => {
  const response = await fetch('/api/portfolio/visualization/data', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Visualization data request failed (${response.status})`);
  }

  return response.json();
};

export const Portfolio3PartVisualization: React.FC<Portfolio3PartVisualizationProps> = ({
  selectedStocks,
  allRecommendations,
  selectedPortfolioIndex,
  riskProfile,
}) => {
  const [data, setData] = useState<VisualizationResponse | null>(null);
  const [fetchState, setFetchState] = useState<FetchState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);
  const [hoveredTickers, setHoveredTickers] = useState<[number, number] | null>(null);
  const debounceRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const resetHighlights = useCallback(() => {
    setHoveredSymbol(null);
    setHoveredSector(null);
    setHoveredTickers(null);
  }, []);

  const payload = useMemo(() => ({
    selectedPortfolio: selectedStocks.map((allocation) => ({
      symbol: allocation.symbol,
      allocation: allocation.allocation,
      name: allocation.name,
    })),
    allRecommendations: allRecommendations.map((recommendation) => ({
      name: recommendation.name,
      expectedReturn: recommendation.expectedReturn,
      risk: recommendation.risk,
      diversificationScore: recommendation.diversificationScore,
      portfolio: recommendation.allocations.map((allocation) => ({
        symbol: allocation.symbol,
        allocation: allocation.allocation,
        name: allocation.name,
      })),
    })),
    selectedPortfolioIndex: selectedPortfolioIndex ?? -1,
    riskProfile,
  }), [allRecommendations, selectedPortfolioIndex, riskProfile, selectedStocks]);

  const loadData = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    setFetchState('loading');
    setError(null);
    resetHighlights();

    fetchVisualizationData(payload, controller.signal)
      .then((response) => {
        setData(response);
        const mergedWarnings = [
          ...(response.warnings ?? []),
          ...(response.clustering?.warnings ?? []),
          ...(response.correlation?.warnings ?? []),
          ...(response.sectorAllocation?.warnings ?? []),
        ];
        setWarnings(mergedWarnings);
        setFetchState('success');
      })
      .catch((err: unknown) => {
        if ((err as Error)?.name === 'AbortError') {
          return;
        }
        setFetchState('error');
        setError(err instanceof Error ? err.message : 'Failed to load visualization data');
      });
  }, [payload, resetHighlights]);

  useEffect(() => {
    if (selectedStocks.length < 3) {
      setData(null);
      setWarnings([]);
      setFetchState('idle');
      setError(null);
      return () => undefined;
    }

    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current);
    }

    debounceRef.current = window.setTimeout(() => {
      loadData();
    }, 350);

    return () => {
      if (debounceRef.current) {
        window.clearTimeout(debounceRef.current);
      }
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [loadData, selectedStocks.length]);

  const portfolioNameMap = useMemo(() => {
    const map = new Map<string, string>();
    const safeRecommendations = Array.isArray(allRecommendations) ? allRecommendations : [];

    if (safeRecommendations.length > 0) {
      if (
        typeof selectedPortfolioIndex === 'number' &&
        selectedPortfolioIndex >= 0 &&
        selectedPortfolioIndex < safeRecommendations.length
      ) {
        map.set('Selected Portfolio', safeRecommendations[selectedPortfolioIndex]?.name ?? 'Selected Portfolio');
      }

      let benchmarkCounter = 0;
      safeRecommendations.forEach((recommendation, index) => {
        if (typeof selectedPortfolioIndex === 'number' && index === selectedPortfolioIndex) return;
        benchmarkCounter += 1;
        map.set(`Benchmark ${benchmarkCounter}`, recommendation?.name ?? `Portfolio ${benchmarkCounter}`);
      });
    }
    return map;
  }, [allRecommendations, selectedPortfolioIndex]);

  const normalizedScatterPoints = useMemo<ScatterPoint[]>(() => {
    if (!data?.clustering?.points) return [];

    const assignments = new Map<number, number>();
    data.clustering.clusters?.forEach((cluster, clusterIndex) => {
      cluster.points?.forEach((pointIdx) => assignments.set(pointIdx, clusterIndex));
    });

    const colorForPortfolio = getPortfolioColorGenerator(visualizationTheme.portfolioPalette);

    return data.clustering.points.map((point, idx) => {
      const clusterIndex = assignments.get(idx);
      const fallbackLabel = clusterIndex !== undefined ? `Cluster ${clusterIndex + 1}` : 'Portfolio';
      const baseLabel = point.label ?? fallbackLabel;
      const portfolioLabel = portfolioNameMap.get(baseLabel) ?? baseLabel;
      const color = colorForPortfolio(portfolioLabel);

      return {
        symbol: point.symbol ?? point.label ?? '—',
        portfolioLabel,
        annualReturn: point.returnValue ?? 0,
        risk: point.risk ?? 0,
        diversificationScore: point.diversificationScore ?? 0,
        sector: point.sector ?? 'Unknown',
        clusterId: clusterIndex ?? -1,
        allocation: point.allocation ?? 0,
        color,
      };
    });
  }, [data?.clustering, portfolioNameMap]);

  const groupedScatter = useMemo(() => {
    const groups = new Map<string, ScatterPoint[]>();
    normalizedScatterPoints.forEach((point) => {
      const key = point.portfolioLabel || 'Portfolio';
      const existing = groups.get(key) ?? [];
      existing.push(point);
      groups.set(key, existing);
    });
    return groups;
  }, [normalizedScatterPoints]);

  const portfolioHulls = useMemo<ClusterHull[]>(() => {
    return Array.from(groupedScatter.entries())
      .map(([label, points]) => {
        if (!points || points.length < 3) return null;
        const hullPoints = computeConvexHull(points);
        if (!hullPoints.length) return null;
        const color = points[0]?.color ?? visualizationTheme.clusterPalette.fallback;
        return {
          label,
          color,
          points: [...hullPoints, hullPoints[0]],
        };
      })
      .filter((item): item is ClusterHull => Boolean(item));
  }, [groupedScatter]);

  const sectorHighlights = useMemo(() => {
    if (!hoveredSector) return new Set<string>();
    return new Set(
      data?.sectorAllocation?.sectors
        ?.filter((item) => item.sector === hoveredSector)
        .flatMap((item) => item.holdings) ?? []
    );
  }, [data?.sectorAllocation?.sectors, hoveredSector]);

  const hoveredTickerSet = useMemo(() => {
    if (!hoveredTickers || !data?.correlation) return new Set<string>();
    const [row, col] = hoveredTickers;
    const tickers = data.correlation.tickers;
    return new Set([tickers[row], tickers[col]].filter(Boolean));
  }, [data?.correlation, hoveredTickers]);

  const highlightedSymbols = useMemo(() => {
    const highlights = new Set<string>();
    if (hoveredSymbol) {
      highlights.add(hoveredSymbol);
    }
    sectorHighlights.forEach((symbol) => highlights.add(symbol));
    hoveredTickerSet.forEach((symbol) => highlights.add(symbol));
    return highlights;
  }, [hoveredSymbol, hoveredTickerSet, sectorHighlights]);

  const sectorSlices = useMemo(() => {
    if (selectedStocks.length === 0) return [];
    
    // Calculate sector allocation for selected portfolio only
    const selectedPortfolioSymbols = new Set(selectedStocks.map(s => s.symbol.toUpperCase()));
    const sectorWeights: Map<string, { weight: number; holdings: string[]; stockAllocations: Array<{ symbol: string; allocation: number }> }> = new Map();
    
    // Priority 1: Use correlation matrix sectorMap (most accurate, from Redis)
    const symbolToSector = new Map<string, string>();
    if (data?.correlation?.sectorMap) {
      Object.entries(data.correlation.sectorMap).forEach(([ticker, sector]) => {
        const tickerUpper = ticker.toUpperCase();
        if (selectedPortfolioSymbols.has(tickerUpper) && sector && sector !== 'Unknown') {
          symbolToSector.set(tickerUpper, sector);
        }
      });
    }
    
    // Priority 2: Use backend sector allocation data (calculated from Redis)
    // The backend calculates sectors correctly, but we need to match tickers to sectors
    // We'll use the backend's sector weights and match our tickers to those sectors
    if (data?.sectorAllocation?.sectors && symbolToSector.size === 0) {
      // Backend has calculated sectors, but we need ticker-to-sector mapping
      // Use scatter points as they have sector info from backend
      normalizedScatterPoints.forEach((point) => {
        const symbolUpper = point.symbol.toUpperCase();
        if (selectedPortfolioSymbols.has(symbolUpper) && point.sector && point.sector !== 'Unknown') {
          symbolToSector.set(symbolUpper, point.sector);
        }
      });
    }
    
    // Priority 3: Fallback to scatter points sector data
    if (symbolToSector.size === 0) {
      normalizedScatterPoints.forEach((point) => {
        const symbolUpper = point.symbol.toUpperCase();
        if (selectedPortfolioSymbols.has(symbolUpper) && point.sector && point.sector !== 'Unknown') {
          symbolToSector.set(symbolUpper, point.sector);
        }
      });
    }
    
    // Aggregate weights by sector for selected portfolio stocks only
    selectedStocks.forEach((stock) => {
      const symbol = stock.symbol.toUpperCase();
      const sector = symbolToSector.get(symbol);
      
      // Skip if sector is Unknown or not found - this should not happen if Redis has sector data
      if (!sector || sector === 'Unknown') {
        console.warn(`Sector not found for ${symbol} - this ticker may not have sector data in Redis`);
        return;
      }
      
      if (!sectorWeights.has(sector)) {
        sectorWeights.set(sector, { weight: 0, holdings: [], stockAllocations: [] });
      }
      const entry = sectorWeights.get(sector)!;
      entry.weight += stock.allocation;
      if (!entry.holdings.includes(symbol)) {
        entry.holdings.push(symbol);
        entry.stockAllocations.push({ symbol, allocation: stock.allocation });
      }
    });
    
    // Convert to array and sort by weight
    const sectors = Array.from(sectorWeights.entries())
      .map(([sector, data], index) => {
        const color = visualizationTheme.pie.palette[index % visualizationTheme.pie.palette.length];
        // Sort stock allocations by allocation percentage (descending)
        const sortedAllocations = [...data.stockAllocations].sort((a, b) => b.allocation - a.allocation);
        return {
          sector,
          percent: data.weight,
          color,
          holdings: data.holdings,
          stockAllocations: sortedAllocations,
        };
      })
      .sort((a, b) => b.percent - a.percent);
    
    return sectors;
  }, [selectedStocks, normalizedScatterPoints, data?.correlation?.sectorMap, data?.sectorAllocation?.sectors]);

  const selectedPortfolioDiversificationScore = useMemo(() => {
    if (typeof selectedPortfolioIndex === 'number' && selectedPortfolioIndex >= 0 && Array.isArray(allRecommendations) && selectedPortfolioIndex < allRecommendations.length) {
      return allRecommendations[selectedPortfolioIndex]?.diversificationScore ?? null;
    }
    return null;
  }, [allRecommendations, selectedPortfolioIndex]);

  const renderScatterTooltip = useCallback((tooltipProps: TooltipProps<ValueType, NameType>) => {
    if (!tooltipProps.active || !tooltipProps.payload?.length) return null;
    const [firstEntry] = tooltipProps.payload;
    const point = firstEntry?.payload as ScatterPoint | undefined;
    if (!point) return null;

    return (
      <div
        className="rounded-xl border p-3 shadow-sm"
        style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
      >
        <p className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
          {point.symbol}
        </p>
        <p className="text-sm" style={{ color: visualizationTheme.text.secondary }}>
          {point.portfolioLabel}
        </p>
        <div className="mt-2 space-y-1 text-sm" style={{ color: visualizationTheme.text.primary }}>
          <p>
            Return:{' '}
            <span className="font-medium">{formatPercent(point.annualReturn)}</span>
          </p>
          <p>
            Risk:{' '}
            <span className="font-medium">{formatPercent(point.risk)}</span>
          </p>
        </div>
      </div>
    );
  }, []);

  const renderPieTooltip = useCallback((tooltipProps: TooltipProps<ValueType, NameType>) => {
    if (!tooltipProps.active || !tooltipProps.payload?.length) return null;
    const [firstEntry] = tooltipProps.payload;
    const sectorItem = firstEntry?.payload as SectorData | undefined;
    if (!sectorItem) return null;

    return (
      <div
        className="rounded-xl border p-3 shadow-sm max-w-xs"
        style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
      >
        <p className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
          {sectorItem.sector}
        </p>
        <div className="mt-2 space-y-1 text-sm" style={{ color: visualizationTheme.text.primary }}>
          <p>
            Total Allocation:{' '}
            <span className="font-medium">{sectorItem.percent.toFixed(2)}%</span>
          </p>
          {sectorItem.stockAllocations && sectorItem.stockAllocations.length > 0 && (
            <div className="mt-2 pt-2 border-t" style={{ borderColor: visualizationTheme.border }}>
              <p className="text-xs font-semibold mb-1" style={{ color: visualizationTheme.text.secondary }}>
                Stock Allocations:
              </p>
              <div className="space-y-0.5">
                {sectorItem.stockAllocations.map((stock, idx) => (
                  <p key={idx} className="text-xs flex justify-between">
                    <span>{stock.symbol}:</span>
                    <span className="font-medium ml-2">{stock.allocation.toFixed(2)}%</span>
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }, []);

  const handleRetry = useCallback(() => {
    if (selectedStocks.length < 3) return;
    // Reset all highlights
    resetHighlights();
    // Reload all visualization data (clustering, correlation, sector allocation)
    loadData();
  }, [loadData, selectedStocks.length, resetHighlights]);

  const isLoading = fetchState === 'loading';
  const hasData = fetchState === 'success' && normalizedScatterPoints.length > 0;
  const isDataReady = Array.isArray(allRecommendations) && allRecommendations.length > 0 && selectedStocks.length >= 3;

  return (
    <div
      className="space-y-6"
      style={{
        background: visualizationTheme.canvas,
        padding: visualizationTheme.spacing.cardPadding,
        borderRadius: visualizationTheme.radius,
      }}
    >
      {warnings.length > 0 && (
        <Alert>
          <AlertDescription>
            <div className="space-y-1">
              {warnings.map((warning, index) => (
                <p key={index} className="text-sm" style={{ color: visualizationTheme.text.secondary }}>
                  {warning}
                </p>
              ))}
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRetry}
          disabled={isLoading || !isDataReady}
          style={{ borderColor: visualizationTheme.border, color: visualizationTheme.text.primary }}
          title="Refresh all visualization data including scatter plot, correlation matrix, and sector allocation"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Refreshing
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" /> Refresh
            </>
          )}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>{error}</span>
            <Button size="sm" onClick={handleRetry}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-6">
        <Card
          className="w-full"
          style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
        >
          <CardHeader className="flex flex-col gap-3">
            <CardTitle
              className="text-lg"
              style={{ color: visualizationTheme.text.primary, textAlign: 'center', fontWeight: 600, letterSpacing: '-0.01em' }}
            >
              Return vs. Risk Tradeoff
            </CardTitle>
          </CardHeader>
          <CardContent
            className="h-[420px]"
            style={{
              background: visualizationTheme.canvas,
              borderRadius: visualizationTheme.radius,
              padding: '12px',
            }}
          >
            {!isDataReady && (
              <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                Please select a portfolio with at least 3 stocks to view visualizations.
              </div>
            )}

            {isDataReady && isLoading && (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            )}

            {isDataReady && !isLoading && hasData && groupedScatter.size === 0 && (
              <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                No data available for the current selection.
              </div>
            )}

            {isDataReady && !isLoading && hasData && groupedScatter.size > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 24, right: 32, bottom: 36, left: 48 }}>
                  <CartesianGrid strokeDasharray="3 4" stroke={visualizationTheme.grid} />
                  <XAxis
                    type="number"
                    dataKey="risk"
                    name="Risk"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={['auto', 'auto']}
                    label={{
                      value: 'Risk',
                      position: 'insideBottom',
                      offset: -6,
                      style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                    }}
                  />
                  <YAxis
                    type="number"
                    dataKey="annualReturn"
                    name="Return"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={['auto', 'auto']}
                    label={{
                      value: 'Return',
                      angle: -90,
                      position: 'insideLeft',
                      style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                    }}
                  />
                  <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} content={renderScatterTooltip} />
                  <Legend
                    wrapperStyle={{
                      paddingTop: 12,
                      fontSize: visualizationTheme.legend.fontSize,
                      color: visualizationTheme.legend.color,
                    }}
                  />
                  {portfolioHulls.map((hull) => (
                    <Scatter
                      key={`hull-${hull.label}`}
                      data={hull.points}
                      line
                      lineType="linear"
                      lineJointType="linear"
                      stroke={hull.color}
                      strokeDasharray="3 3"
                      strokeWidth={1.25}
                      strokeOpacity={0.6}
                      shape={() => null}
                      legendType="none"
                    />
                  ))}
                  {Array.from(groupedScatter.entries()).map(([label, points]) => (
                    <Scatter
                      key={label}
                      name={label}
                      data={points}
                      fill={points[0]?.color ?? visualizationTheme.clusterPalette.fallback}
                      shape={(props) => {
                        const point = props.payload as ScatterPoint;
                        const highlightActive = highlightedSymbols.size > 0;
                        const isHighlighted = highlightedSymbols.has(point.symbol);
                        const radius = hoveredSymbol === point.symbol ? 7 : 5.5;
                        const strokeOpacity = hoveredSymbol === point.symbol || isHighlighted ? 0.9 : 0.7;
                        return (
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={radius}
                            fill={point.color}
                            fillOpacity={highlightActive ? (isHighlighted ? 0.9 : visualizationTheme.hoverFadeOpacity) : 0.85}
                            stroke={point.color}
                            strokeOpacity={strokeOpacity}
                            strokeWidth={1.6}
                            onMouseEnter={() => setHoveredSymbol(point.symbol)}
                            onMouseLeave={() => setHoveredSymbol(null)}
                          />
                        );
                      }}
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card
          className="w-full"
          style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
        >
            <CardHeader>
            <CardTitle
              className="text-lg"
              style={{ color: visualizationTheme.text.primary, textAlign: 'center', fontWeight: 600, letterSpacing: '-0.01em' }}
            >
              Correlation Matrix
            </CardTitle>
            </CardHeader>
            <CardContent
              className="max-h-[420px] overflow-auto"
              style={{ background: visualizationTheme.canvas, borderRadius: visualizationTheme.radius, padding: '16px' }}
            >
              {isLoading && (
                <div className="flex h-64 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}

              {isDataReady && !isLoading && hasData && data?.correlation?.tickers?.length ? (
                <div className="min-w-full space-y-1">
                  <div
                    className="sticky top-0 z-10 flex"
                    style={{ background: visualizationTheme.canvas, color: visualizationTheme.text.secondary, fontWeight: 600 }}
                  >
                    <div
                      className="w-24 flex-shrink-0 border-r p-2 text-xs uppercase"
                      style={{ borderColor: visualizationTheme.border, color: visualizationTheme.text.secondary, letterSpacing: '0.08em' }}
                    >
                      Ticker
                    </div>
                    {data.correlation.tickers.map((ticker) => (
                      <div
                        key={`col-${ticker}`}
                        className="flex-1 border-r p-2 text-center text-xs font-semibold"
                        style={{ borderColor: visualizationTheme.border, color: visualizationTheme.text.secondary }}
                      >
                        {ticker}
                      </div>
                    ))}
                  </div>
                  {data.correlation.matrix.map((row, rowIndex) => (
                    <div key={`row-${rowIndex}`} className="flex">
                      <div
                        className="w-24 flex-shrink-0 border-r p-2 text-xs font-medium"
                        style={{
                          borderColor: visualizationTheme.border,
                          background: visualizationTheme.canvas,
                          color: visualizationTheme.text.primary,
                        }}
                      >
                        <div style={{ fontWeight: 600 }}>{data.correlation.tickers[rowIndex]}</div>
                        <div style={{ color: visualizationTheme.text.secondary, fontSize: 10, fontWeight: 400 }}>
                          {data.correlation.portfolioLabels?.[rowIndex]}
                        </div>
                      </div>
                      {row.map((value, colIndex) => {
                        const tickerKey = `${rowIndex}-${colIndex}`;
                        const isSelf = rowIndex === colIndex;
                        return (
                          <div
                            key={tickerKey}
                            className="flex-1 border-r border-b p-2 text-center text-xs font-medium"
                            style={{
                              background: isSelf ? 'rgba(130, 188, 176, 0.25)' : getCorrelationColor(value),
                              borderColor: visualizationTheme.border,
                              color: visualizationTheme.text.primary,
                            }}
                          >
                            {value.toFixed(2)}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              ) : isDataReady && !isLoading ? (
                <div className="flex h-64 items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                  No correlation data available.
                </div>
              ) : !isDataReady ? (
                <div className="flex h-64 items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                  Please select a portfolio to view correlation data.
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card
            className="w-full"
            style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
          >
            <CardHeader>
            <CardTitle
              className="text-lg"
              style={{ color: visualizationTheme.text.primary, textAlign: 'center', fontWeight: 600, letterSpacing: '-0.01em' }}
            >
              Sector Allocation
            </CardTitle>
            <p className="text-xs text-center mt-2" style={{ color: visualizationTheme.text.secondary }}>
              Showing sector breakdown for your selected portfolio only
            </p>
            {selectedPortfolioDiversificationScore !== null && (
              <div className="flex justify-center mt-2">
                <Badge
                  variant="outline"
                  style={{
                    borderColor: visualizationTheme.border,
                    background: visualizationTheme.cardBackground,
                    color: visualizationTheme.text.primary,
                  }}
                >
                  Diversification Score: {selectedPortfolioDiversificationScore.toFixed(1)}
                </Badge>
              </div>
            )}
            </CardHeader>
            <CardContent
              className="h-[240px]"
              style={{ background: visualizationTheme.canvas, borderRadius: visualizationTheme.radius, padding: '16px' }}
            >
              {isLoading && (
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}

              {isDataReady && !isLoading && hasData && sectorSlices.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sectorSlices}
                      dataKey="percent"
                      nameKey="sector"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
                      onMouseEnter={(_, index) => setHoveredSector(sectorSlices[index]?.sector ?? null)}
                      onMouseLeave={() => setHoveredSector(null)}
                    >
                      {sectorSlices.map((sector, index) => {
                        const isHovered = hoveredSector === sector.sector;
                        const highlightsActive = highlightedSymbols.size > 0;
                        const hasHighlightedHolding = sector.holdings.some((symbol) => highlightedSymbols.has(symbol));
                        const paletteColor = visualizationTheme.pie.palette[index % visualizationTheme.pie.palette.length];
                        return (
                          <Cell
                            key={`${sector.sector}-${index}`}
                            fill={paletteColor}
                            fillOpacity={
                              highlightsActive
                                ? hasHighlightedHolding || isHovered
                                  ? 0.95
                                  : visualizationTheme.hoverFadeOpacity
                                : isHovered
                                ? 0.95
                                : 0.85
                            }
                          />
                        );
                      })}
                    </Pie>
                    <PieTooltip content={renderPieTooltip} />
                  </PieChart>
                </ResponsiveContainer>
              ) : isDataReady && !isLoading ? (
                <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                  No sector allocation data available.
                </div>
              ) : !isDataReady ? (
                <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                  Please select a portfolio to view sector allocation.
                </div>
              ) : null}
            </CardContent>
          </Card>
      </div>
    </div>
  );
};


