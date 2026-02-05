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
  Customized,
  Brush,
} from 'recharts';
import {
  Pie,
  PieChart,
  Cell,
  Tooltip as PieTooltip,
} from 'recharts';
import type { TooltipProps, ValueType, NameType } from 'recharts';
import { Loader2, RefreshCw, ZoomOut } from 'lucide-react';
import clsx from 'clsx';

const vividPalette = [
  '#16a34a', // Vibrant green
  '#dc2626', // Vibrant red
  '#2563eb', // Vibrant blue
  '#ca8a04', // Vibrant yellow/gold
  '#9333ea', // Vibrant purple
  '#ea580c', // Vibrant orange
  '#0891b2', // Vibrant cyan
  '#be185d', // Vibrant pink
  '#65a30d', // Vibrant lime
  '#0e7490', // Vibrant teal
];

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
    selected: vividPalette[0],
    benchmark1: vividPalette[1],
    benchmark2: vividPalette[2],
    benchmarks: vividPalette.slice(1),
    fallback: vividPalette[3],
  },
  portfolioPalette: vividPalette,
  hull: {
    strokeOpacity: 0.55,
    strokeDasharray: '5 6',
  },
  pie: {
    palette: vividPalette,
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
  strategy?: string;
}

interface ScatterPoint {
  symbol: string;
  portfolioLabel: string;
  annualReturn: number;
  risk: number;
  diversificationScore: number;
  sector: string;
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


// Custom component to render filled hull polygons using Recharts' coordinate system
const HullPolygons: React.FC<{
  hulls: ClusterHull[];
  xAxisId?: string | number;
  yAxisId?: string | number;
}> = ({ hulls, xAxisId, yAxisId }) => {
  const resolveAxis = useCallback(
    (axisMap: Record<string, any> | undefined, axisKey?: string | number) => {
      if (!axisMap) return null;
      if (axisKey !== undefined && axisKey !== null) {
        const direct = axisMap[axisKey as keyof typeof axisMap];
        if (direct) return direct;

        const numericKey = typeof axisKey === 'number' ? String(axisKey) : axisKey;
        if (numericKey && axisMap[numericKey]) return axisMap[numericKey];

        const prefixedKey = `axis-${numericKey}`;
        if (numericKey && axisMap[prefixedKey]) return axisMap[prefixedKey];
      }

      const entries = Object.values(axisMap);
      return entries.length > 0 ? entries[0] : null;
    },
    []
  );

  return (
    <Customized
      component={(props: any) => {
        const { xAxisMap, yAxisMap, offset } = props;

        // Get the scale functions from Recharts
        const xAxis = resolveAxis(xAxisMap, xAxisId ?? props.xAxisId ?? 0);
        const yAxis = resolveAxis(yAxisMap, yAxisId ?? props.yAxisId ?? 0);
        const xScale = xAxis?.scale;
        const yScale = yAxis?.scale;
        
        if (!xScale || !yScale) {
          console.error('❌ HullPolygons: Scale functions not available', {
            xScale: !!xScale,
            yScale: !!yScale,
            xAxisKeys: xAxisMap ? Object.keys(xAxisMap) : 'none',
            yAxisKeys: yAxisMap ? Object.keys(yAxisMap) : 'none',
            xAxisId,
            yAxisId,
          });
          return null;
        }
        
        const leftOffset = offset?.left ?? 0;
        const topOffset = offset?.top ?? 0;

        console.log('✅ HullPolygons: Rendering', hulls.length, 'hulls', {
          hullLabels: hulls.map((h) => h.label),
          offsets: { leftOffset, topOffset },
        });
        
        return (
          <g className="hull-polygons">
            {hulls.map((hull, hullIndex) => {
              if (!hull.points || hull.points.length < 3) {
                console.warn(`⚠️ HullPolygons: Hull ${hull.label} has insufficient points:`, hull.points?.length);
                return null;
              }
              
              console.log(`🎨 HullPolygons: Rendering hull for ${hull.label} with color ${hull.color}`);
              
              // Convert data coordinates to pixel coordinates
              const pathSegments = hull.points
                .map((point, index) => {
                  const xVal = point.risk;
                  const yVal = point.annualReturn;
                  if (xVal == null || yVal == null) return null;

                  const scaledX = typeof xScale === 'function' ? xScale(xVal) : xVal;
                  const scaledY = typeof yScale === 'function' ? yScale(yVal) : yVal;

                  const x = Number.isFinite(scaledX) ? scaledX + leftOffset : null;
                  const y = Number.isFinite(scaledY) ? scaledY + topOffset : null;

                  if (x == null || y == null) return null;

                  return `${index === 0 ? 'M' : 'L'} ${x},${y}`;
                })
                .filter((segment): segment is string => Boolean(segment));

              if (pathSegments.length < 3) {
                console.warn(`⚠️ HullPolygons: Not enough valid segments for ${hull.label}`, pathSegments);
                return null;
              }

              const pathData = `${pathSegments.join(' ')} Z`; // Close the path
              
              console.log(`HullPolygons: Rendering hull for ${hull.label} with ${hull.points.length} points`);
              
              return (
                <g key={`hull-polygon-${hull.label}-${hullIndex}`}>
                  {/* Filled polygon - HIGHLY VISIBLE */}
                  <path
                    d={pathData}
                    fill={hull.color}
                    fillOpacity={0.5}
                    stroke={hull.color}
                    strokeWidth={4}
                    strokeOpacity={0.95}
                    strokeDasharray="8 4"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    style={{ pointerEvents: 'none' }}
                  />
                </g>
              );
            })}
          </g>
        );
      }}
    />
  );
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

interface RawScatterPoint {
  label: string;
  risk: number;
  returnValue: number;
  symbol?: string | null;
  sector?: string | null;
  allocation?: number | null;
  diversificationScore?: number | null;
}

interface RawScatterData {
  points: RawScatterPoint[];
  tickerPoints?: RawScatterPoint[];
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
  scatter: RawScatterData;
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
  strategyPortfolios?: PortfolioRecommendation[];
  compactMode?: boolean; // When true, uses compact layout for Finalize Portfolio
}

type FetchState = 'idle' | 'loading' | 'success' | 'error';

const CORRELATION_MIN = -1;
const CORRELATION_MAX = 1;

const getCorrelationColor = (value: number) => {
  if (Number.isNaN(value)) return 'rgba(148, 163, 184, 0.25)';
  const clamped = Math.max(CORRELATION_MIN, Math.min(CORRELATION_MAX, value));
  
  // Enhanced color scheme with more vibrant, distinct colors
  // Strong negative correlation: Deep Red
  // Weak/No correlation: Light Gray/Yellow
  // Strong positive correlation: Deep Green/Blue
  
  if (clamped < -0.5) {
    // Strong negative: Deep red with high opacity
    const intensity = Math.abs(clamped);
    return `rgba(220, 38, 38, ${0.4 + intensity * 0.5})`;
  } else if (clamped < -0.2) {
    // Moderate negative: Orange-red
    const intensity = Math.abs(clamped) * 2;
    return `rgba(251, 146, 60, ${0.35 + intensity * 0.4})`;
  } else if (clamped < 0.2) {
    // Weak/No correlation: Light yellow-gray
    return `rgba(253, 224, 71, ${0.25 + Math.abs(clamped) * 0.3})`;
  } else if (clamped < 0.5) {
    // Moderate positive: Light green
    const intensity = clamped * 2;
    return `rgba(134, 239, 172, ${0.35 + intensity * 0.4})`;
  } else {
    // Strong positive: Deep green-blue
    const intensity = clamped;
    return `rgba(34, 197, 94, ${0.45 + intensity * 0.5})`;
  }
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
    let errorMessage = `Visualization data request failed (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = errorData.detail;
      } else if (typeof errorData === 'string') {
        errorMessage = errorData;
      }
    } catch {
      // If JSON parsing fails, try text
      const text = await response.text();
      if (text) {
        try {
          const parsed = JSON.parse(text);
          errorMessage = parsed.detail || parsed.message || text;
        } catch {
          errorMessage = text || errorMessage;
        }
      }
    }
    throw new Error(errorMessage);
  }

  return response.json();
};

export const Portfolio3PartVisualization: React.FC<Portfolio3PartVisualizationProps> = ({
  selectedStocks,
  allRecommendations,
  selectedPortfolioIndex,
  riskProfile,
  strategyPortfolios = [],
  compactMode = false,
}) => {
  const [data, setData] = useState<VisualizationResponse | null>(null);
  const [fetchState, setFetchState] = useState<FetchState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);
  const [hoveredTickers, setHoveredTickers] = useState<[number, number] | null>(null);
  // In compact mode (Finalize Portfolio), force ticker-only view. Otherwise, allow toggle.
  const [viewMode, setViewMode] = useState<'portfolio' | 'ticker'>(compactMode ? 'ticker' : 'portfolio');
  const [zoomDomain, setZoomDomain] = useState<{ x?: [number, number]; y?: [number, number] } | null>(null);
  const debounceRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const resetHighlights = useCallback(() => {
    setHoveredSymbol(null);
    setHoveredSector(null);
    setHoveredTickers(null);
  }, []);

  // Determine which portfolios to use for comparison
  // If selected portfolio is from strategyPortfolios, compare only with same-strategy portfolios
  const portfoliosForComparison = useMemo(() => {
    // Check if selectedStocks matches any strategy portfolio
    const selectedSymbols = new Set(selectedStocks.map(s => s.symbol.toUpperCase()));
    const selectedAllocations = new Map(selectedStocks.map(s => [s.symbol.toUpperCase(), s.allocation]));
    
    // Find matching strategy portfolio
    const matchingStrategyPortfolio = strategyPortfolios.find(portfolio => {
      if (!portfolio.allocations || portfolio.allocations.length !== selectedStocks.length) {
        return false;
      }
      const portfolioSymbols = new Set(portfolio.allocations.map(a => a.symbol.toUpperCase()));
      if (portfolioSymbols.size !== selectedSymbols.size) {
        return false;
      }
      // Check if all symbols match
      for (const symbol of portfolioSymbols) {
        if (!selectedSymbols.has(symbol)) {
          return false;
        }
      }
      return true;
    });

    // If we found a matching strategy portfolio, filter to same-strategy portfolios
    if (matchingStrategyPortfolio && matchingStrategyPortfolio.strategy) {
      const strategyName = matchingStrategyPortfolio.strategy;
      const sameStrategyPortfolios = strategyPortfolios.filter(
        p => p.strategy === strategyName
      );
      console.log(`Using ${sameStrategyPortfolios.length} portfolios from strategy: ${strategyName}`);
      return sameStrategyPortfolios;
    }

    // Otherwise, use regular recommendations
    console.log(`Using ${allRecommendations.length} regular recommendation portfolios`);
    return allRecommendations;
  }, [selectedStocks, strategyPortfolios, allRecommendations]);

  const warmVisualizationTickers = useCallback(async () => {
    const tickers = new Set<string>();

    selectedStocks.forEach((stock) => {
      if (stock.symbol) {
        tickers.add(stock.symbol.toUpperCase());
      }
    });

    // Use portfoliosForComparison to warm only relevant tickers
    portfoliosForComparison.forEach((recommendation) => {
      recommendation.allocations?.forEach((allocation) => {
        if (allocation.symbol) {
          tickers.add(allocation.symbol.toUpperCase());
        }
      });
    });

    const tickersToWarm = Array.from(tickers);
    if (tickersToWarm.length === 0) {
      return;
    }

    try {
      await fetch('/api/portfolio/warm-tickers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tickers: tickersToWarm }),
      });
    } catch (warmError) {
      console.warn('Failed to warm visualization tickers', warmError);
    }
  }, [portfoliosForComparison, selectedStocks]);

  const payload = useMemo(() => ({
    selectedPortfolio: selectedStocks.map((allocation) => ({
      symbol: allocation.symbol,
      allocation: allocation.allocation,
      name: allocation.name,
    })),
    allRecommendations: portfoliosForComparison.map((recommendation) => ({
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
  }), [portfoliosForComparison, selectedPortfolioIndex, riskProfile, selectedStocks]);

  const loadData = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    setFetchState('loading');
    setError(null);
    resetHighlights();

    try {
      await warmVisualizationTickers();
    } catch (error) {
      console.warn('Visualization warm-up failed', error);
    }

    try {
      const response = await fetchVisualizationData(payload, controller.signal);
        setData(response);
        
        // Log ticker data for debugging
        console.log('[Portfolio3PartVisualization] Visualization data received:', {
          selectedPortfolioTickers: selectedStocks.map(s => s.symbol),
          tickerPointsTotal: response.scatter?.tickerPoints?.length || 0,
          tickerPointsLabels: [...new Set((response.scatter?.tickerPoints || []).map(t => t.label))],
          selectedPortfolioTickerPoints: (response.scatter?.tickerPoints || []).filter(t => t.label === 'Selected Portfolio'),
          selectedPortfolioTickerSymbols: (response.scatter?.tickerPoints || [])
            .filter(t => t.label === 'Selected Portfolio')
            .map(t => t.symbol)
        });
        
        const mergedWarnings = [
          ...(response.warnings ?? []),
        ...(response.scatter?.warnings ?? []),
          ...(response.correlation?.warnings ?? []),
          ...(response.sectorAllocation?.warnings ?? []),
        ];
        setWarnings(mergedWarnings);
        setFetchState('success');
    } catch (err) {
        if ((err as Error)?.name === 'AbortError') {
          return;
        }
        setFetchState('error');
      const errorMessage = err instanceof Error ? err.message : 'Failed to load visualization data';
      
      // Parse error message to provide actionable guidance
      let userFriendlyError = errorMessage;
      if (errorMessage.includes('Correlation matrix calculation failed')) {
        if (errorMessage.includes('Missing tickers')) {
          userFriendlyError = `Some tickers are missing price data. ${errorMessage.split('Missing tickers:')[1] || 'Please refresh the data or try selecting a different portfolio.'}`;
        } else {
          userFriendlyError = 'Unable to calculate correlation matrix. Some tickers may be missing price data. Try refreshing the data.';
        }
      } else if (errorMessage.includes('Scatter data preparation failed')) {
        userFriendlyError = 'Unable to prepare risk/return scatter data. Please ensure all tickers have valid metrics and try refreshing.';
      } else if (errorMessage.includes('Sector allocation calculation failed')) {
        userFriendlyError = 'Unable to calculate sector allocation. Some tickers may be missing sector information. Try refreshing the data.';
      } else if (errorMessage.includes('HTTPException')) {
        userFriendlyError = 'A server error occurred. Please check that all tickers have price and sector data, then try refreshing.';
      }
      
      setError(userFriendlyError);
    }
  }, [payload, resetHighlights, warmVisualizationTickers]);

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
    // Use portfoliosForComparison instead of allRecommendations
    const safeRecommendations = Array.isArray(portfoliosForComparison) ? portfoliosForComparison : [];

    if (safeRecommendations.length > 0) {
      // Find the index of the selected portfolio in portfoliosForComparison
      const selectedPortfolioName = selectedStocks.length > 0 
        ? safeRecommendations.find(p => {
            const portfolioSymbols = new Set((p.allocations || []).map(a => a.symbol.toUpperCase()));
            const selectedSymbols = new Set(selectedStocks.map(s => s.symbol.toUpperCase()));
            return portfolioSymbols.size === selectedSymbols.size &&
                   Array.from(portfolioSymbols).every(s => selectedSymbols.has(s));
          })?.name
        : null;

      if (selectedPortfolioName) {
        map.set('Selected Portfolio', selectedPortfolioName);
      } else if (
        typeof selectedPortfolioIndex === 'number' &&
        selectedPortfolioIndex >= 0 &&
        selectedPortfolioIndex < safeRecommendations.length
      ) {
        map.set('Selected Portfolio', safeRecommendations[selectedPortfolioIndex]?.name ?? 'Selected Portfolio');
      }

      let benchmarkCounter = 0;
      safeRecommendations.forEach((recommendation, index) => {
        // Skip if this is the selected portfolio
        const isSelected = selectedPortfolioName === recommendation.name ||
          (typeof selectedPortfolioIndex === 'number' && index === selectedPortfolioIndex);
        if (isSelected) return;
        benchmarkCounter += 1;
        map.set(`Benchmark ${benchmarkCounter}`, recommendation?.name ?? `Portfolio ${benchmarkCounter}`);
      });
    }
    return map;
  }, [portfoliosForComparison, selectedPortfolioIndex, selectedStocks]);

  const normalizedScatterPoints = useMemo<ScatterPoint[]>(() => {
    if (!data?.scatter?.points) return [];

    const colorForPortfolio = getPortfolioColorGenerator(visualizationTheme.portfolioPalette);

    return data.scatter.points.map((point) => {
      const baseLabel = point.label ?? 'Portfolio';
      const portfolioLabel = portfolioNameMap.get(baseLabel) ?? baseLabel;
      const color = colorForPortfolio(portfolioLabel);

      return {
        symbol: point.symbol ?? point.label ?? '—',
        portfolioLabel,
        annualReturn: point.returnValue ?? 0,
        risk: point.risk ?? 0,
        diversificationScore: point.diversificationScore ?? 0,
        sector: point.sector ?? 'Unknown',
        allocation: point.allocation ?? 0,
        color,
      };
    });
  }, [data?.scatter, portfolioNameMap]);

  const normalizedTickerPoints = useMemo<ScatterPoint[]>(() => {
    if (!data?.scatter?.tickerPoints) return [];

    const colorForPortfolio = getPortfolioColorGenerator(visualizationTheme.portfolioPalette);

    const mapped = data.scatter.tickerPoints.map((point) => {
      const baseLabel = point.label ?? 'Portfolio';
      const portfolioLabel = portfolioNameMap.get(baseLabel) ?? baseLabel;
      const color = colorForPortfolio(portfolioLabel);

      return {
        symbol: point.symbol ?? '—',
        portfolioLabel,
        annualReturn: point.returnValue ?? 0,
        risk: point.risk ?? 0,
        diversificationScore: 0, // Not applicable for individual tickers
        sector: point.sector ?? 'Unknown',
        allocation: 0,
        color,
      };
    });

    // Log for debugging
    const selectedPortfolioTickers = mapped.filter(p => p.portfolioLabel === portfolioNameMap.get('Selected Portfolio') || p.portfolioLabel.includes('Selected'));
    console.log('[Portfolio3PartVisualization] Normalized ticker points:', {
      total: mapped.length,
      selectedPortfolioCount: selectedPortfolioTickers.length,
      selectedPortfolioTickers: selectedPortfolioTickers.map(t => ({ symbol: t.symbol, return: t.annualReturn, risk: t.risk })),
      allLabels: [...new Set(mapped.map(p => p.portfolioLabel))]
    });

    return mapped;
  }, [data?.scatter?.tickerPoints, portfolioNameMap]);

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

  // Prepare brush data for zoom functionality
  const brushData = useMemo(() => {
    const allPoints: Array<{ risk: number; annualReturn: number }> = [];
    Array.from(groupedScatter.values()).forEach(points => {
      allPoints.push(...points);
    });
    return allPoints.length > 0 ? [...allPoints].sort((a, b) => a.risk - b.risk) : [];
  }, [groupedScatter]);

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

  const tickerHulls = useMemo<ClusterHull[]>(() => {
    if (viewMode !== 'ticker') {
      return [];
    }
    
    if (normalizedTickerPoints.length === 0) {
      return [];
    }

    const groups = new Map<string, ScatterPoint[]>();
    normalizedTickerPoints.forEach((point) => {
      const key = point.portfolioLabel || 'Portfolio';
      const existing = groups.get(key) ?? [];
      existing.push(point);
      groups.set(key, existing);
    });

    console.log('tickerHulls: Grouped into', groups.size, 'portfolios:', Array.from(groups.keys()));

    const hulls = Array.from(groups.entries())
      .map(([label, points]) => {
        if (!points || points.length === 0) return null;
        const color = points[0]?.color ?? visualizationTheme.clusterPalette.fallback;
        
        console.log(`tickerHulls: Processing ${label} with ${points.length} points`);
        
        let hullPoints: ScatterPoint[];

        // Calculate data range for proportional scaling
        const allRisks = normalizedTickerPoints.map(p => p.risk);
        const allReturns = normalizedTickerPoints.map(p => p.annualReturn);
        const riskRange = Math.max(...allRisks) - Math.min(...allRisks);
        const returnRange = Math.max(...allReturns) - Math.min(...allReturns);

        // Scale radius to 2% of the larger dimension (minimum 0.01 for safety)
        const dataScale = Math.max(riskRange, returnRange);
        const dynamicRadius = Math.max(dataScale * 0.02, 0.01);

        if (points.length === 1) {
          // Single point: create a small circle around it with dynamic radius
          const point = points[0];
          hullPoints = [
            { ...point, risk: point.risk - dynamicRadius, annualReturn: point.annualReturn },
            { ...point, risk: point.risk, annualReturn: point.annualReturn + dynamicRadius },
            { ...point, risk: point.risk + dynamicRadius, annualReturn: point.annualReturn },
            { ...point, risk: point.risk, annualReturn: point.annualReturn - dynamicRadius },
          ];
          console.log(`tickerHulls: Created 4-point circle for single ticker in ${label} (radius: ${dynamicRadius.toFixed(4)})`);
        } else if (points.length === 2) {
          // Two points: create an ellipse/circle around them with dynamic padding
          const p1 = points[0];
          const p2 = points[1];
          const midRisk = (p1.risk + p2.risk) / 2;
          const midReturn = (p1.annualReturn + p2.annualReturn) / 2;
          const distRisk = Math.abs(p2.risk - p1.risk) / 2 + dynamicRadius;
          const distReturn = Math.abs(p2.annualReturn - p1.annualReturn) / 2 + dynamicRadius;
          hullPoints = [
            { ...p1, risk: midRisk - distRisk, annualReturn: midReturn },
            { ...p1, risk: midRisk, annualReturn: midReturn + distReturn },
            { ...p1, risk: midRisk + distRisk, annualReturn: midReturn },
            { ...p1, risk: midRisk, annualReturn: midReturn - distReturn },
          ];
          console.log(`tickerHulls: Created ellipse for 2 tickers in ${label} (padding: ${dynamicRadius.toFixed(4)})`);
        } else {
          // Three or more points: use convex hull
          hullPoints = computeConvexHull(points);
          if (!hullPoints.length) {
            console.warn(`tickerHulls: Convex hull calculation failed for ${label}`);
            return null;
          }
          console.log(`tickerHulls: Created convex hull with ${hullPoints.length} points for ${label}`);
        }
        
        return {
          label,
          color,
          points: [...hullPoints, hullPoints[0]], // Close the polygon
        };
      })
      .filter((item): item is ClusterHull => Boolean(item));
    
    console.log('tickerHulls: Generated', hulls.length, 'hulls');
    return hulls;
  }, [viewMode, normalizedTickerPoints]);

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
    
    // Build ticker-to-sector mapping from all available sources
    const symbolToSector = new Map<string, string>();
    
    // Priority 1: Use correlation matrix sectorMap (most accurate, from Redis)
    if (data?.correlation?.sectorMap) {
      Object.entries(data.correlation.sectorMap).forEach(([ticker, sector]) => {
        const tickerUpper = ticker.toUpperCase();
        if (selectedPortfolioSymbols.has(tickerUpper) && sector && sector !== 'Unknown') {
          symbolToSector.set(tickerUpper, sector);
        }
      });
    }
    
    // Priority 2: Use ticker points (individual ticker data with sector info from backend)
    // This includes all tickers from selected portfolio and benchmarks
    normalizedTickerPoints.forEach((point) => {
      const symbolUpper = point.symbol.toUpperCase();
      if (selectedPortfolioSymbols.has(symbolUpper) && point.sector && point.sector !== 'Unknown') {
        // Only add if not already found in correlation sectorMap
        if (!symbolToSector.has(symbolUpper)) {
          symbolToSector.set(symbolUpper, point.sector);
        }
      }
    });
    
    // Priority 3: Use scatter points (portfolio-level points may have sector info)
    normalizedScatterPoints.forEach((point) => {
      const symbolUpper = point.symbol.toUpperCase();
      if (selectedPortfolioSymbols.has(symbolUpper) && point.sector && point.sector !== 'Unknown') {
        // Only add if not already found
        if (!symbolToSector.has(symbolUpper)) {
          symbolToSector.set(symbolUpper, point.sector);
        }
      }
    });
    
    // Priority 4: Fallback - reconstruct from sector allocation response
    // The backend sector allocation has sectors but we need to match tickers
    // We can infer ticker-to-sector by checking which tickers belong to which sectors
    // This is a last resort since sector allocation doesn't provide direct ticker mapping
    
    // Aggregate weights by sector for selected portfolio stocks only
    selectedStocks.forEach((stock) => {
      const symbol = stock.symbol.toUpperCase();
      let sector = symbolToSector.get(symbol);
      
      // Attempt to find sector from any ticker in data if not found directly
      if (!sector || sector === 'Unknown') {
        const anyTickerData = [...normalizedTickerPoints, ...normalizedScatterPoints].find(
          p => p.symbol.toUpperCase() === symbol && p.sector && p.sector !== 'Unknown'
        );
        if (anyTickerData) {
          sector = anyTickerData.sector;
        }
      }

      // Skip if sector is still Unknown or not found - this should not happen if Redis has sector data
      if (!sector || sector === 'Unknown') {
        console.warn(`Sector not found for ${symbol} - this ticker may not have sector data in Redis or API response`);
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
  }, [selectedStocks, normalizedScatterPoints, normalizedTickerPoints, data?.correlation?.sectorMap, data?.sectorAllocation?.sectors]);

  const selectedPortfolioDiversificationScore = useMemo(() => {
    if (typeof selectedPortfolioIndex === 'number' && selectedPortfolioIndex >= 0 && Array.isArray(allRecommendations) && selectedPortfolioIndex < allRecommendations.length) {
      return allRecommendations[selectedPortfolioIndex]?.diversificationScore ?? null;
    }
    return null;
  }, [allRecommendations, selectedPortfolioIndex]);

  // Track filtered tickers for data quality warnings
  const filteredTickerInfo = useMemo(() => {
    const filtered = normalizedTickerPoints.filter(point => {
      return point.annualReturn > 0 && point.risk >= 0;
    });

    const selectedPortfolioTickers = filtered.filter(p =>
      p.portfolioLabel === portfolioNameMap.get('Selected Portfolio') ||
      p.portfolioLabel.includes('Selected')
    );
    const selectedPortfolioExpected = selectedStocks.map(s => s.symbol.toUpperCase());
    const selectedPortfolioFound = selectedPortfolioTickers.map(p => p.symbol.toUpperCase());
    const missing = selectedPortfolioExpected.filter(s => !selectedPortfolioFound.includes(s));

    return {
      filtered,
      missing,
      totalFiltered: normalizedTickerPoints.length - filtered.length
    };
  }, [normalizedTickerPoints, selectedStocks, portfolioNameMap]);

  // Update warnings when tickers are filtered
  useEffect(() => {
    if (filteredTickerInfo.missing.length > 0) {
      const missingWarning = `${filteredTickerInfo.missing.length} ticker(s) from your portfolio are not displayed due to insufficient data: ${filteredTickerInfo.missing.join(', ')}`;
      setWarnings(prev => {
        // Only add if not already present
        if (!prev.includes(missingWarning)) {
          return [...prev, missingWarning];
        }
        return prev;
      });
    }
  }, [filteredTickerInfo.missing]);

  const renderScatterTooltip = useCallback((tooltipProps: TooltipProps<ValueType, NameType>) => {
    // Only show tooltip if hoveredSymbol is set (prevents lingering tooltip)
    if (!hoveredSymbol || !tooltipProps.active || !tooltipProps.payload?.length) return null;
    const [firstEntry] = tooltipProps.payload;
    const point = firstEntry?.payload as ScatterPoint | undefined;
    if (!point || point.symbol !== hoveredSymbol) return null;

    return (
      <div
        className="rounded-xl border p-3 shadow-sm max-w-xs"
        style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
      >
        <p className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
          {point.symbol}
        </p>
        <p className="text-sm mt-1" style={{ color: visualizationTheme.text.secondary }}>
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
  }, [hoveredSymbol]);

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
    // Reload all visualization data (scatter, correlation, sector allocation)
    loadData();
  }, [loadData, selectedStocks.length, resetHighlights]);

  const isLoading = fetchState === 'loading';
  const hasData = fetchState === 'success' && (normalizedScatterPoints.length > 0 || normalizedTickerPoints.length > 0);
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

      {!compactMode && (
        <div className="flex items-center justify-between mb-4 px-2">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-muted-foreground">View:</span>
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'portfolio' ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setViewMode('portfolio');
                  resetHighlights();
                }}
              >
                Portfolio
              </Button>
              <Button
                variant={viewMode === 'ticker' ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setViewMode('ticker');
                  resetHighlights();
                }}
              >
                Ticker
              </Button>
            </div>
          </div>
          <div className="flex gap-2">
            {zoomDomain && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setZoomDomain(null)}
              >
                <ZoomOut className="h-4 w-4 mr-1" />
                Reset Zoom
              </Button>
            )}
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
        </div>
      )}

      {compactMode && (
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
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription className="space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="font-semibold mb-1">Visualization Error</p>
                <p className="text-sm">{error}</p>
                {(error.includes('Missing tickers') || error.includes('missing') || error.includes('price data')) ? (
                  <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                    <p className="font-medium text-yellow-800 mb-1">💡 How to fix:</p>
                    <ul className="list-disc list-inside text-yellow-700 space-y-1">
                      <li>Click "Refresh" to warm up all ticker data</li>
                      <li>If the issue persists, try selecting a different portfolio</li>
                      <li>Check backend logs for specific ticker names that failed</li>
                    </ul>
                  </div>
                ) : null}
              </div>
            <Button size="sm" onClick={handleRetry}>
              Retry
            </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className={compactMode ? "flex flex-col gap-3" : "flex flex-col gap-6"}>
        {/* Return vs Risk Tradeoff */}
        <Card
          className="w-full"
          style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
        >
          <CardHeader className="pb-2">
            <CardTitle
              className={compactMode ? "text-sm md:text-base text-center" : "text-lg text-center"}
              style={{ color: visualizationTheme.text.primary, fontWeight: 600, letterSpacing: '-0.01em' }}
            >
              Return vs. Risk Tradeoff
            </CardTitle>
          </CardHeader>
          <CardContent
            className={compactMode ? "h-[240px] md:h-[280px]" : "h-[420px]"}
            style={{
              background: visualizationTheme.canvas,
              borderRadius: visualizationTheme.radius,
              padding: compactMode ? '10px' : '12px',
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

            {isDataReady && !isLoading && hasData && viewMode === 'portfolio' && groupedScatter.size === 0 && (
              <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                No data available for the current selection.
              </div>
            )}

            {isDataReady && !isLoading && hasData && viewMode === 'ticker' && normalizedTickerPoints.length === 0 && (
              <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                No ticker data available. Please refresh the data.
              </div>
            )}

            {isDataReady && !isLoading && hasData && viewMode === 'portfolio' && groupedScatter.size > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart
                  margin={{ top: 24, right: 32, bottom: 70, left: 48 }}
                  onMouseLeave={(e) => {
                    setHoveredSymbol(null);
                    setHoveredSector(null);
                  }}
                  onMouseMove={(e) => {
                    if (!e || !e.activePayload || e.activePayload.length === 0) {
                      setHoveredSymbol(null);
                      setHoveredSector(null);
                    }
                  }}
                >
                  <CartesianGrid strokeDasharray="3 4" stroke={visualizationTheme.grid} />
                  <XAxis
                    type="number"
                    dataKey="risk"
                    name="Risk"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={zoomDomain?.x || [0, 'auto']}
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
                    scale="log"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={zoomDomain?.y || [0.01, 'auto']}
                    label={{
                      value: 'Return',
                      angle: -90,
                      position: 'insideLeft',
                      style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                    }}
                  />
                  <RechartsTooltip 
                    cursor={{ strokeDasharray: '3 3' }} 
                    content={renderScatterTooltip}
                    isAnimationActive={false}
                    animationDuration={0}
                    active={hoveredSymbol !== null ? true : undefined}
                  />
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
                  {Array.from(groupedScatter.entries()).map(([label, points]) => {
                    const isSelectedPortfolio = label === portfolioNameMap.get('Selected Portfolio') || 
                                               label.includes('Selected');
                    
                    return (
                      <Scatter
                        key={label}
                        name={label}
                        data={points}
                        fill={points[0]?.color ?? visualizationTheme.clusterPalette.fallback}
                        shape={(props) => {
                          const point = props.payload as ScatterPoint;
                          const highlightActive = highlightedSymbols.size > 0;
                          const isHighlighted = highlightedSymbols.has(point.symbol);
                          const isHovered = hoveredSymbol === point.symbol;
                          const radius = isHovered ? 7 : 5;
                          const strokeWidth = 1.6;
                          const strokeOpacity = isHovered || isHighlighted ? 1.0 : 0.7;
                          const fillOpacity = highlightActive 
                            ? (isHighlighted ? 1.0 : visualizationTheme.hoverFadeOpacity) 
                            : 0.85;
                          
                          return (
                            <circle
                              cx={props.cx}
                              cy={props.cy}
                              r={radius}
                              fill={point.color}
                              fillOpacity={fillOpacity}
                              stroke={point.color}
                              strokeOpacity={strokeOpacity}
                              strokeWidth={strokeWidth}
                              onMouseEnter={() => {
                                setHoveredSymbol(point.symbol);
                                const sectorValue = point.sector && point.sector !== 'Unknown' ? point.sector : null;
                                setHoveredSector(sectorValue);
                              }}
                              onMouseLeave={() => {
                                setHoveredSymbol(null);
                                setHoveredSector(null);
                              }}
                            />
                          );
                        }}
                      />
                    );
                  })}
                  {brushData.length > 0 && (
                    <Brush
                      dataKey="risk"
                      height={30}
                      stroke={visualizationTheme.axes.line}
                      strokeWidth={1.5}
                      fill={visualizationTheme.grid}
                      fillOpacity={0.4}
                      data={brushData}
                      onChange={(brushEvent) => {
                        if (brushEvent && typeof brushEvent === 'object' && 'startIndex' in brushEvent && 'endIndex' in brushEvent) {
                          const startIdx = brushEvent.startIndex as number;
                          const endIdx = brushEvent.endIndex as number;
                          
                          if (startIdx !== undefined && endIdx !== undefined && startIdx >= 0 && endIdx >= 0 && startIdx <= endIdx) {
                            const visiblePoints = brushData.slice(startIdx, endIdx + 1);
                            
                            if (visiblePoints.length > 0) {
                              const riskMin = Math.min(...visiblePoints.map(p => p.risk));
                              const riskMax = Math.max(...visiblePoints.map(p => p.risk));
                              const returnMin = Math.min(...visiblePoints.map(p => p.annualReturn));
                              const returnMax = Math.max(...visiblePoints.map(p => p.annualReturn));
                              
                              const riskPadding = (riskMax - riskMin) * 0.1;
                              const returnPadding = (returnMax - returnMin) * 0.1;
                              
                              setZoomDomain({
                                x: [Math.max(0, riskMin - riskPadding), riskMax + riskPadding],
                                y: [Math.max(0, returnMin - returnPadding), returnMax + returnPadding],
                              });
                            }
                          }
                        } else {
                          setZoomDomain(null);
                        }
                      }}
                    />
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            )}

            {isDataReady && !isLoading && hasData && viewMode === 'ticker' && normalizedTickerPoints.length > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart
                  margin={{ top: 24, right: 32, bottom: 70, left: 48 }}
                  onMouseLeave={(e) => {
                    // Immediately clear hover state when mouse leaves chart area
                    setHoveredSymbol(null);
                    setHoveredSector(null);
                  }}
                  onMouseMove={(e) => {
                    // Clear hover if mouse moves to empty area (no data point)
                    if (!e || !e.activePayload || e.activePayload.length === 0) {
                      setHoveredSymbol(null);
                      setHoveredSector(null);
                    }
                  }}
                >
                  <CartesianGrid strokeDasharray="3 4" stroke={visualizationTheme.grid} />
                  <XAxis
                    type="number"
                    dataKey="risk"
                    name="Risk"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={zoomDomain?.x || [0, 'auto']}
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
                    scale="log"
                    tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                    axisLine={{ stroke: visualizationTheme.axes.line }}
                    tickLine={{ stroke: 'transparent' }}
                    tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                    domain={zoomDomain?.y || [0.01, 'auto']}
                    label={{
                      value: 'Return',
                      angle: -90,
                      position: 'insideLeft',
                      style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                    }}
                  />
                  <RechartsTooltip 
                    cursor={{ strokeDasharray: '3 3' }} 
                    content={renderScatterTooltip}
                    isAnimationActive={false}
                    animationDuration={0}
                    active={hoveredSymbol !== null ? true : undefined}
                  />
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
                  {Array.from(groupedScatter.entries()).map(([label, points]) => {
                    // Enhanced visibility for selected portfolio
                    const isSelectedPortfolio = label === portfolioNameMap.get('Selected Portfolio') || 
                                               label.includes('Selected');
                    
                    return (
                      <Scatter
                        key={label}
                        name={label}
                        data={points}
                        fill={points[0]?.color ?? visualizationTheme.clusterPalette.fallback}
                        shape={(props) => {
                          const point = props.payload as ScatterPoint;
                          const highlightActive = highlightedSymbols.size > 0;
                          const isHighlighted = highlightedSymbols.has(point.symbol);
                          const isHovered = hoveredSymbol === point.symbol;
                          // Consistent radius for all points - only hover increases size
                          const radius = isHovered ? 7 : 5;
                          const strokeWidth = 1.6;
                          const strokeOpacity = isHovered || isHighlighted ? 1.0 : 0.7;
                          const fillOpacity = highlightActive 
                            ? (isHighlighted ? 1.0 : visualizationTheme.hoverFadeOpacity) 
                            : 0.85;
                          
                          return (
                            <circle
                              cx={props.cx}
                              cy={props.cy}
                              r={radius}
                              fill={point.color}
                              fillOpacity={fillOpacity}
                              stroke={point.color}
                              strokeOpacity={strokeOpacity}
                              strokeWidth={strokeWidth}
                              onMouseEnter={() => {
                                setHoveredSymbol(point.symbol);
                                const sectorValue = point.sector && point.sector !== 'Unknown' ? point.sector : null;
                                setHoveredSector(sectorValue);
                              }}
                              onMouseLeave={() => {
                                setHoveredSymbol(null);
                                setHoveredSector(null);
                              }}
                            />
                          );
                        }}
                      />
                    );
                  })}
                  {brushData.length > 0 && (
                    <Brush
                      dataKey="risk"
                      height={30}
                      stroke={visualizationTheme.axes.line}
                      strokeWidth={1.5}
                      fill={visualizationTheme.grid}
                      fillOpacity={0.4}
                      data={brushData}
                      onChange={(brushEvent) => {
                        if (brushEvent && typeof brushEvent === 'object' && 'startIndex' in brushEvent && 'endIndex' in brushEvent) {
                          const startIdx = brushEvent.startIndex as number;
                          const endIdx = brushEvent.endIndex as number;
                          
                          if (startIdx !== undefined && endIdx !== undefined && startIdx >= 0 && endIdx >= 0 && startIdx <= endIdx) {
                            const visiblePoints = brushData.slice(startIdx, endIdx + 1);
                            
                            if (visiblePoints.length > 0) {
                              const riskMin = Math.min(...visiblePoints.map(p => p.risk));
                              const riskMax = Math.max(...visiblePoints.map(p => p.risk));
                              const returnMin = Math.min(...visiblePoints.map(p => p.annualReturn));
                              const returnMax = Math.max(...visiblePoints.map(p => p.annualReturn));
                              
                              // Add padding
                              const riskPadding = (riskMax - riskMin) * 0.1;
                              const returnPadding = (returnMax - returnMin) * 0.1;
                              
                              setZoomDomain({
                                x: [Math.max(0, riskMin - riskPadding), riskMax + riskPadding],
                                y: [Math.max(0, returnMin - returnPadding), returnMax + returnPadding],
                              });
                            }
                          }
                        } else {
                          // Reset zoom when brush is cleared
                          setZoomDomain(null);
                        }
                      }}
                    />
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            )}

          </CardContent>
        </Card>

        {/* Correlation Matrix and Sector Allocation - conditional layout */}
        {compactMode ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card
              className="w-full"
              style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
            >
              <CardHeader className="pb-2">
                <CardTitle
                  className="text-sm md:text-base text-center"
                  style={{ color: visualizationTheme.text.primary, fontWeight: 600, letterSpacing: '-0.01em' }}
                >
                  Correlation Matrix
                </CardTitle>
              </CardHeader>
              <CardContent
                className="h-[200px] overflow-auto"
                style={{ background: visualizationTheme.canvas, borderRadius: visualizationTheme.radius, padding: '10px' }}
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
            <CardHeader className="pb-3">
            <CardTitle
              className="text-sm md:text-base text-center"
              style={{ color: visualizationTheme.text.primary, fontWeight: 600, letterSpacing: '-0.01em' }}
            >
              Sector Allocation
            </CardTitle>
            {selectedPortfolioDiversificationScore !== null && (
              <div className="flex justify-center mt-1">
                <Badge
                  variant="outline"
                  className="text-xs"
                  style={{
                    borderColor: visualizationTheme.border,
                    background: visualizationTheme.cardBackground,
                    color: visualizationTheme.text.primary,
                  }}
                >
                  Diversification: {selectedPortfolioDiversificationScore.toFixed(1)}%
                </Badge>
              </div>
            )}
            </CardHeader>
            <CardContent
              className="h-[200px]"
              style={{ background: visualizationTheme.canvas, borderRadius: visualizationTheme.radius, padding: '12px' }}
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
        ) : (
          // Non-compact mode: Stacked layout
          <>
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
                <p className="text-xs text-muted-foreground mt-1 text-center">
                  Showing sector breakdown for your selected portfolio only
                </p>
                {selectedPortfolioDiversificationScore !== null && (
                  <div className="flex justify-center mt-1">
                    <Badge
                      variant="outline"
                      className="text-xs"
                      style={{
                        borderColor: visualizationTheme.border,
                        background: visualizationTheme.cardBackground,
                        color: visualizationTheme.text.primary,
                      }}
                    >
                      Diversification: {selectedPortfolioDiversificationScore.toFixed(1)}%
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
          </>
        )}
      </div>
    </div>
  );
};


