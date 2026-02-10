/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip as RechartsTooltip, Legend, ReferenceArea, ReferenceDot, ReferenceLine, Line, ComposedChart, Customized, Label, AreaChart, Area } from 'recharts';
import type { TooltipProps, ValueType, NameType } from 'recharts';
import { API_ENDPOINTS } from '@/config/api';
import { 
  ArrowLeft, 
  ArrowRight, 
  TrendingUp, 
  Shield, 
  BarChart3,
  Target,
  Zap,
  Info,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  PieChart,
  LineChart,
  Settings,
  Database,
  XCircle,
  RotateCcw,
  Maximize2,
  Minimize2,
  Loader2,
  RefreshCw,
  ZoomOut,
  ZoomIn,
  Award,
  AlertCircle,
  TrendingDown,
  Activity,
  Eye,
  EyeOff
} from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { getChartTheme, getPortfolioColors, getVisualizationPalette } from '@/utils/chartThemes';
import { Skeleton } from '@/components/ui/skeleton';

// Layout constants (theme-independent)
const layoutConstants = {
  spacing: {
    cardPadding: '16px',
    sectionGap: '16px',
  },
  radius: '18px',
  legend: {
    fontSize: 12,
  },
};

const formatPercent = (value: number | null | undefined) => {
  if (value == null || typeof value !== 'number' || !isFinite(value)) return 'N/A';
  return `${(value * 100).toFixed(2)}%`;
};

interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

// Selected portfolio data to pass to next step
interface SelectedPortfolioData {
  source: 'current' | 'optimized';
  tickers: string[];
  weights: Record<string, number>;
  metrics: {
    expected_return: number;
    risk: number;
    sharpe_ratio: number;
  };
}

interface PortfolioOptimizationProps {
  onNext: () => void;
  onPrev: () => void;
  selectedStocks: PortfolioAllocation[];
  riskProfile: string;
  capital: number;
  portfolioMetrics?: PortfolioMetrics | null;
  onPortfolioSelection?: (portfolio: SelectedPortfolioData) => void;
  initialSelectedPortfolio?: SelectedPortfolioData | null;
}

interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
}

interface OptimizationResult {
  weights: number[];
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
}

interface EfficientFrontierPoint {
  risk: number;
  return: number;
  weights: number[];
  type: 'current' | 'optimized' | 'frontier' | 'random';
  sharpe_ratio?: number;
}

interface EligibleTicker {
  ticker: string;
  expected_return: number;
  volatility: number;
  sector?: string;
  company_name?: string;
}

interface NormalizedPoint {
  x: number;
  y: number;
}

interface SelectionBox {
  start?: NormalizedPoint & { isPixel?: boolean; isPlotAreaRelative?: boolean };
  end?: NormalizedPoint & { isPixel?: boolean; isPlotAreaRelative?: boolean };
}

// Helper interface for data coordinates
interface DataCoordinates {
  x: number;
  y: number;
}

const clampValue = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
const clampRiskValue = (value: number) => clampValue(value, 0, 1.4);
const clampNormalized = (value: number) => clampValue(value, 0, 1);
const normalizedToDomain = (normalized: number, domain: [number, number]) => domain[0] + normalized * (domain[1] - domain[0]);
const normalizedToDomainY = (normalized: number, domain: [number, number]) => domain[1] - normalized * (domain[1] - domain[0]);

interface MVOOptimizationResponse {
  optimization_type: string;
  strategy_name: string;
  optimized_portfolio: {
    tickers: string[];
    weights: Record<string, number>;
    weights_list: number[];
    metrics: {
      expected_return: number;
      risk: number;
      sharpe_ratio: number;
    };
  };
  current_portfolio?: {
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      risk: number;
      sharpe_ratio: number;
    };
  };
  efficient_frontier: EfficientFrontierPoint[];
  inefficient_frontier?: EfficientFrontierPoint[];  // Lower part of hyperbola
  random_portfolios: EfficientFrontierPoint[];
  capital_market_line?: EfficientFrontierPoint[];  // CML points
  improvements?: {
    return_improvement: number;
    risk_improvement: number;
    sharpe_improvement: number;
  };
  metadata: {
    num_tickers: number;
    processing_time_seconds: number;
    risk_free_rate: number;
  };
}

// Monte Carlo simulation results
interface MonteCarloResult {
  simulated_returns: number[];
  percentiles: {
    p5: number;
    p25: number;
    p50: number;
    p75: number;
    p95: number;
  };
  probability_positive: number;
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

// Quality Score breakdown
interface QualityScoreResult {
  composite_score: number;
  rating: string;
  rating_color: string;
  factor_breakdown: {
    risk_profile_compliance: {
      score: number;
      weight: number;
      label: string;
      description: string;
    };
    sortino_ratio: {
      score: number;
      raw_value: number;
      weight: number;
      label: string;
      description: string;
    };
    diversification: {
      score: number;
      weight: number;
      label: string;
      description: string;
    };
    consistency: {
      score: number;
      weight: number;
      label: string;
      description: string;
    };
  };
  weights_used: Record<string, number>;
}

interface DualOptimizationResponse {
  current_portfolio: {
    tickers: string[];
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      risk: number;
      sharpe_ratio: number;
    };
  };
  optimized_portfolio: MVOOptimizationResponse;  // Optimized portfolio from market tickers
  comparison: {
    return_difference: number;
    risk_difference: number;
    sharpe_difference: number;
    optimized_tickers: string[];
    current_tickers: string[];
    current_metrics_unreliable?: boolean;
    reliability_reasons?: string[];
    comparison_notes?: string[];
    monte_carlo?: {
      current: MonteCarloResult;
      optimized: MonteCarloResult;
    };
    quality_scores?: {
      current: QualityScoreResult;
      optimized: QualityScoreResult;
    };
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
  weights_optimized_portfolio: MVOOptimizationResponse;  // Weights-only optimization
  market_optimized_portfolio: MVOOptimizationResponse | null;  // Market exploration (optional)
  comparison: {
    weights_vs_current: {
      return_difference: number;
      risk_difference: number;
      sharpe_difference: number;
    };
    market_vs_current: {
      return_difference: number;
      risk_difference: number;
      sharpe_difference: number;
    } | null;
    market_vs_weights: {
      return_difference: number;
      risk_difference: number;
      sharpe_difference: number;
    } | null;
    best_return: 'current' | 'weights' | 'market';
    best_risk: 'current' | 'weights' | 'market';
    best_sharpe: 'current' | 'weights' | 'market';
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
    strategy_used: string;
    attempts_made: number;
    market_exploration_attempted: boolean;
    market_exploration_successful: boolean;
    recommendation: 'current' | 'weights' | 'market';
    processing_time_seconds: number;
  };
}

// Helper function to get risk profile display name
const getRiskProfileDisplay = (profile?: string): string => {
  const profileMap: Record<string, string> = {
    'very-conservative': 'Very Conservative',
    'conservative': 'Conservative',
    'moderate': 'Moderate',
    'aggressive': 'Aggressive',
    'very-aggressive': 'Very Aggressive'
  };
  return profileMap[profile || ''] || 'Moderate';
};

export const PortfolioOptimization = ({ 
  onNext, 
  onPrev, 
  selectedStocks, 
  riskProfile, 
  capital,
  portfolioMetrics: initialMetrics,
  onPortfolioSelection,
  initialSelectedPortfolio
}: PortfolioOptimizationProps) => {
  // Get current theme for dynamic colors
  const { theme } = useTheme();
  const chartTheme = getChartTheme(theme);
  const portfolioColors = getPortfolioColors(theme);
  const vividPalette = getVisualizationPalette(theme);

  const [activeTab, setActiveTab] = useState<'overview' | 'optimization' | 'analysis' | 'recommendations'>(initialSelectedPortfolio ? 'analysis' : 'optimization');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingEligibleTickers, setIsLoadingEligibleTickers] = useState(false);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResult | null>(null);
  const [efficientFrontier, setEfficientFrontier] = useState<EfficientFrontierPoint[]>([]);
  const [inefficientFrontier, setInefficientFrontier] = useState<EfficientFrontierPoint[]>([]);
  const [randomPortfolios, setRandomPortfolios] = useState<EfficientFrontierPoint[]>([]);
  const [mvoResults, setMvoResults] = useState<MVOOptimizationResponse | null>(null);
  const [dualOptimizationResults, setDualOptimizationResults] = useState<DualOptimizationResponse | null>(null);
  const [tripleOptimizationResults, setTripleOptimizationResults] = useState<TripleOptimizationResponse | null>(null);
  const [selectedPortfolio, setSelectedPortfolio] = useState<'current' | 'weights' | 'market'>('current');
  const isTriple = Boolean(tripleOptimizationResults);
  const [returnScenarioVisibility, setReturnScenarioVisibility] = useState({
    current: true,
    weights: true,
    market: true
  });
  const [selectedReturnScenario, setSelectedReturnScenario] = useState<string | null>(null);
  const [eligibleTickers, setEligibleTickers] = useState<EligibleTicker[]>([]);
  const [currentPortfolio, setCurrentPortfolio] = useState<PortfolioAllocation[]>(Array.isArray(selectedStocks) ? selectedStocks : []);
  const [optimizedPortfolio, setOptimizedPortfolio] = useState<PortfolioAllocation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [portfolioTickersMetrics, setPortfolioTickersMetrics] = useState<Map<string, { volatility: number; expected_return: number; company_name?: string; sector?: string }>>(new Map());
  
  // Box zoom state for eligible tickers chart
  const [eligibleTickersSelectionBox, setEligibleTickersSelectionBox] = useState<SelectionBox | null>(null);
  const [eligibleTickersSelectionBoxData, setEligibleTickersSelectionBoxData] = useState<{start: DataCoordinates, end: DataCoordinates} | null>(null);
  const [eligibleTickersZoomHistory, setEligibleTickersZoomHistory] = useState<Array<{x: [number, number], y: [number, number]}>>([]);
  const [eligibleTickersCurrentDomain, setEligibleTickersCurrentDomain] = useState<{x: [number, number], y: [number, number]} | null>(null);
  const [isEligibleTickersSelecting, setIsEligibleTickersSelecting] = useState(false);
  
  // Box zoom state for efficient frontier chart
  const [efficientFrontierSelectionBox, setEfficientFrontierSelectionBox] = useState<SelectionBox | null>(null);
  const [efficientFrontierSelectionBoxData, setEfficientFrontierSelectionBoxData] = useState<{start: DataCoordinates, end: DataCoordinates} | null>(null);
  const [efficientFrontierZoomHistory, setEfficientFrontierZoomHistory] = useState<Array<{x: [number, number], y: [number, number]}>>([]);
  const [efficientFrontierCurrentDomain, setEfficientFrontierCurrentDomain] = useState<{x: [number, number], y: [number, number]} | null>(null);
  const [isEfficientFrontierSelecting, setIsEfficientFrontierSelecting] = useState(false);
  
  // Legacy zoom level (kept for backward compatibility with buttons) - default 0.5 for 50% zoom out
  const [eligibleTickersZoomLevel, setEligibleTickersZoomLevel] = useState<number>(0.5);
  const [eligibleTickersOriginalDomain, setEligibleTickersOriginalDomain] = useState<{y: [number, number]} | null>(null);
  const [efficientFrontierZoomLevel, setEfficientFrontierZoomLevel] = useState<number>(1);
  const [efficientFrontierOriginalDomain, setEfficientFrontierOriginalDomain] = useState<{y: [number, number]} | null>(null);

  // Visibility toggles for efficient frontier chart series
  const [visibleSeries, setVisibleSeries] = useState({
    randomPortfolios: true,
    efficientFrontier: true,
    inefficientFrontier: true,
    cml: true,
    currentPortfolio: true,
    weightsOptimized: true,
    marketOptimized: true,
  });

  // Toggle visibility of a series
  const toggleSeriesVisibility = useCallback((series: keyof typeof visibleSeries) => {
    setVisibleSeries(prev => ({ ...prev, [series]: !prev[series] }));
  }, []);

  // Initialize currentMetrics - check if we can use initialMetrics on mount
  // MUST be declared before eligibleTickersDomain useMemo which uses it
  const [currentMetrics, setCurrentMetrics] = useState<any>(() => {
    // On mount, check if selectedStocks matches and we have initialMetrics
    if (initialMetrics && selectedStocks && selectedStocks.length > 0) {
      // Since currentPortfolio is initialized from selectedStocks, they should match on mount
      console.log('✅ Initializing metrics from props on mount:', initialMetrics);
      return {
        expectedReturn: initialMetrics.expectedReturn,
        risk: initialMetrics.risk,
        diversificationScore: initialMetrics.diversificationScore
      };
    }
    return null;
  });

  // Memoized list of portfolio tickers with their data from eligibleTickers or fetched metrics
  // MUST be declared before eligibleTickersDomain useMemo which uses it
  const portfolioTickersData = useMemo(() => {
    if (!currentPortfolio || !Array.isArray(currentPortfolio) || currentPortfolio.length === 0) {
      return [];
    }
    
    // Find all portfolio tickers in eligibleTickers - use case-insensitive matching
    const portfolioSymbols = new Set(
      currentPortfolio
        .map(s => s?.symbol?.toUpperCase().trim())
        .filter(Boolean)
    );
    
    const result: Array<{
      volatility: number;
      expected_return: number;
      ticker: string;
      company_name: string;
      sector?: string;
      isSelected: boolean;
    }> = [];
    
    // First, try to find in eligibleTickers
    if (eligibleTickers && Array.isArray(eligibleTickers) && eligibleTickers.length > 0) {
      const eligibleTickersMap = new Map<string, EligibleTicker>();
      eligibleTickers.forEach(t => {
        if (t && t.ticker) {
          eligibleTickersMap.set(t.ticker.toUpperCase().trim(), t);
        }
      });
      
      portfolioSymbols.forEach(symbol => {
        const tickerData = eligibleTickersMap.get(symbol);
        if (tickerData) {
          // Only add if we have valid metrics (not null/undefined)
          // If metrics are missing, we'll fetch them separately
          const volatility = tickerData.volatility;
          const expected_return = tickerData.expected_return;
          if (volatility != null && expected_return != null && 
              typeof volatility === 'number' && typeof expected_return === 'number' &&
              !isNaN(volatility) && !isNaN(expected_return) && isFinite(volatility) && isFinite(expected_return)) {
            // Only add if return is positive (exclude zero or negative)
            if (expected_return > 0) {
              result.push({
                // Always include portfolio tickers; clamp into chart range instead of filtering them out
                volatility: clampRiskValue(Math.max(0, volatility)), // 0–1.4, domain later caps to 1.1
                expected_return: clampValue(expected_return, 0, 1.0), // 0–1.0 (0–100% return)
                ticker: tickerData.ticker,
                company_name: tickerData.company_name || tickerData.ticker,
                sector: tickerData.sector,
                isSelected: true
              });
            }
          }
        }
      });
    }
    
    // Then, add any missing tickers from fetched metrics
    portfolioSymbols.forEach(symbol => {
      // Skip if already added from eligibleTickers
      if (result.some(r => r.ticker.toUpperCase().trim() === symbol)) {
        return;
      }
      
      const metrics = portfolioTickersMetrics.get(symbol);
      if (metrics) {
        // Find the original ticker format from currentPortfolio to preserve casing
        const originalTicker = currentPortfolio.find(s => s?.symbol?.toUpperCase().trim() === symbol)?.symbol || symbol;
        // Only add if return is positive (exclude zero or negative)
        const ret = metrics.expected_return ?? 0;
        if (ret > 0) {
          result.push({
            // Always include portfolio tickers; clamp into chart range instead of filtering them out
            volatility: clampRiskValue(Math.max(0, metrics.volatility || 0)), // 0–1.4, domain later caps to 1.1
            expected_return: clampValue(ret, 0, 1.0), // 0–1.0 (0–100% return)
            ticker: originalTicker, // Use original format
            company_name: metrics.company_name || originalTicker,
            sector: metrics.sector,
            isSelected: true
          });
        }
      }
    });
    
    // Log for debugging
    if (result.length !== portfolioSymbols.size) {
      const missingSymbols = Array.from(portfolioSymbols).filter(s => 
        !result.some(r => r.ticker.toUpperCase().trim() === s)
      );
      console.warn(`[PortfolioOptimization] ⚠️ Some portfolio tickers are missing from visualization:`, missingSymbols);
      console.log(`[PortfolioOptimization] Portfolio symbols:`, Array.from(portfolioSymbols));
      console.log(`[PortfolioOptimization] Result tickers:`, result.map(r => r.ticker));
    }
    
    return result;
  }, [currentPortfolio, eligibleTickers, portfolioTickersMetrics]);

  // Helper function to apply jitter to overlapping points
  const applyJitterToPoints = useCallback((points: any[], overlapThreshold: number = 0.01, offsetMagnitude: number = 0.005) => {
    if (!points || points.length === 0) return points;
    
    const processedIndices = new Set<number>();
    const result = [...points];
    
    points.forEach((point, index) => {
      if (processedIndices.has(index)) return;
      
      // Find all points that overlap with this one
      const overlappingIndices = [index];
      points.forEach((other, otherIndex) => {
        if (index === otherIndex || processedIndices.has(otherIndex)) return;
        const volDiff = Math.abs((point.volatility || 0) - (other.volatility || 0));
        const retDiff = Math.abs((point.expected_return || 0) - (other.expected_return || 0));
        if (volDiff < overlapThreshold && retDiff < overlapThreshold) {
          overlappingIndices.push(otherIndex);
        }
      });
      
      // Mark all overlapping indices as processed
      overlappingIndices.forEach(idx => processedIndices.add(idx));
      
      // If there are overlaps, distribute points in a circle pattern
      if (overlappingIndices.length > 1) {
        overlappingIndices.forEach((idx, i) => {
          const angle = (i * (2 * Math.PI)) / overlappingIndices.length;
          const offsetDistance = offsetMagnitude * Math.max(1, overlappingIndices.length - 1);
          result[idx] = {
            ...result[idx],
            volatility: (result[idx].volatility || 0) + Math.cos(angle) * offsetDistance,
            expected_return: (result[idx].expected_return || 0) + Math.sin(angle) * offsetDistance,
          };
        });
      }
    });
    
    return result;
  }, []);

  // Helper function to apply jitter to efficient frontier portfolio points (Current, Weights, Market)
  const applyJitterToPortfolioPoints = useCallback((points: Array<{risk: number, return: number, [key: string]: any}>, overlapThreshold: number = 0.005, offsetMagnitude: number = 0.003) => {
    if (!points || points.length === 0) return points;
    
    const processedIndices = new Set<number>();
    const result = points.map(p => ({ ...p }));
    
    points.forEach((point, index) => {
      if (processedIndices.has(index)) return;
      
      // Find all points that overlap with this one
      const overlappingIndices = [index];
      points.forEach((other, otherIndex) => {
        if (index === otherIndex || processedIndices.has(otherIndex)) return;
        const riskDiff = Math.abs((point.risk || 0) - (other.risk || 0));
        const returnDiff = Math.abs((point.return || 0) - (other.return || 0));
        if (riskDiff < overlapThreshold && returnDiff < overlapThreshold) {
          overlappingIndices.push(otherIndex);
        }
      });
      
      // Mark all overlapping indices as processed
      overlappingIndices.forEach(idx => processedIndices.add(idx));
      
      // If there are overlaps, distribute points in a circle pattern
      if (overlappingIndices.length > 1) {
        overlappingIndices.forEach((idx, i) => {
          const angle = (i * (2 * Math.PI)) / overlappingIndices.length;
          const offsetDistance = offsetMagnitude * Math.max(1, overlappingIndices.length - 1);
          result[idx] = {
            ...result[idx],
            risk: (result[idx].risk || 0) + Math.cos(angle) * offsetDistance,
            return: (result[idx].return || 0) + Math.sin(angle) * offsetDistance,
          };
        });
      }
    });
    
    return result;
  }, []);

  // Process portfolio tickers to handle overlapping points by applying small offsets
  const portfolioTickersDataWithOffsets = useMemo(() => {
    if (!portfolioTickersData || portfolioTickersData.length === 0) {
      return [];
    }
    return applyJitterToPoints(portfolioTickersData, 0.01, 0.005);
  }, [portfolioTickersData, applyJitterToPoints]);

  // Process eligible tickers to handle overlapping points
  const eligibleTickersWithOffsets = useMemo(() => {
    if (!eligibleTickers || eligibleTickers.length === 0) return [];
    
    const filtered = eligibleTickers.filter(t => {
      if (!t || !t.ticker) return false;
      if (!currentPortfolio || !Array.isArray(currentPortfolio)) return true;
      return !currentPortfolio.some(s => s && s.symbol && s.symbol.toUpperCase().trim() === t.ticker.toUpperCase().trim());
    }).filter(t => {
      const vol = t?.volatility ?? 0;
      const ret = t?.expected_return ?? 0;
      return vol >= 0 && vol <= 1.1 && ret > 0 && ret <= 1.0;
    }).map(t => ({
      volatility: t.volatility || 0,
      expected_return: t.expected_return ?? 0,
      ticker: t.ticker,
      company_name: t.company_name,
      sector: t.sector,
      isSelected: false
    }));
    
    return applyJitterToPoints(filtered, 0.008, 0.003); // Smaller threshold and offset for eligible tickers
  }, [eligibleTickers, currentPortfolio, applyJitterToPoints]);

  // Collect and apply jitter to portfolio points (Current, Weights-Optimized, Market-Optimized) for efficient frontier chart
  const portfolioPointsWithJitter = useMemo(() => {
    const points: Array<{risk: number, return: number, type: string, sharpe_ratio?: number}> = [];
    
    // Add Current Portfolio
    if (tripleOptimizationResults?.current_portfolio?.metrics) {
      points.push({
        risk: tripleOptimizationResults.current_portfolio.metrics.risk,
        return: tripleOptimizationResults.current_portfolio.metrics.expected_return,
        sharpe_ratio: tripleOptimizationResults.current_portfolio.metrics.sharpe_ratio,
        type: 'current'
      });
    }
    
    // Add Weights-Optimized Portfolio
    if (tripleOptimizationResults?.weights_optimized_portfolio?.optimized_portfolio?.metrics) {
      points.push({
        risk: tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.risk,
        return: tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return,
        sharpe_ratio: tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio,
        type: 'weights_optimized'
      });
    }
    
    // Add Market-Optimized Portfolio
    if (tripleOptimizationResults?.market_optimized_portfolio?.optimized_portfolio?.metrics) {
      points.push({
        risk: tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.risk,
        return: tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.expected_return,
        sharpe_ratio: tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio,
        type: 'market_optimized'
      });
    }
    
    // Add Legacy Optimized Portfolio (for backward compatibility)
    if (!tripleOptimizationResults && mvoResults?.optimized_portfolio?.metrics) {
      points.push({
        risk: mvoResults.optimized_portfolio.metrics.risk,
        return: mvoResults.optimized_portfolio.metrics.expected_return,
        sharpe_ratio: mvoResults.optimized_portfolio.metrics.sharpe_ratio,
        type: 'optimized'
      });
    }
    
    // Apply jitter to overlapping points
    return applyJitterToPortfolioPoints(points, 0.005, 0.003);
  }, [tripleOptimizationResults, mvoResults, applyJitterToPortfolioPoints]);


  // Calculate default domain ranges for zoom
  const eligibleTickersDomain = useMemo(() => {
    try {
      const volatilities: number[] = [];
      const returns: number[] = [];
      
      // Include eligible tickers (filtered to limits: X-axis max 1.1, Y-axis max 1.0)
      if (eligibleTickers && eligibleTickers.length > 0) {
        eligibleTickers.forEach(t => {
          const vol = typeof t?.volatility === 'number' ? t.volatility : null;
          const ret = typeof t?.expected_return === 'number' ? t.expected_return : null;
          // Only include values within limits
          if (vol !== null && !isNaN(vol) && isFinite(vol) && vol >= 0 && vol <= 1.1) {
            volatilities.push(vol);
          }
          // Exclude zero or negative returns
          if (ret !== null && !isNaN(ret) && isFinite(ret) && ret > 0 && ret <= 1.0) {
            returns.push(ret);
          }
        });
      }
      
      // CRITICAL FIX: Include actual current portfolio metrics in domain calculation
      // This ensures the chart ranges include the user's actual selected portfolio
      if (currentMetrics && typeof currentMetrics.risk === 'number' && typeof currentMetrics.expectedReturn === 'number' &&
          !isNaN(currentMetrics.risk) && !isNaN(currentMetrics.expectedReturn) && 
          isFinite(currentMetrics.risk) && isFinite(currentMetrics.expectedReturn)) {
        // Only include if within limits
        if (currentMetrics.risk >= 0 && currentMetrics.risk <= 1.1) {
          volatilities.push(currentMetrics.risk);
        }
        // Exclude zero or negative returns
        if (currentMetrics.expectedReturn > 0 && currentMetrics.expectedReturn <= 1.0) {
          returns.push(currentMetrics.expectedReturn);
        }
      }
      
      // Also include portfolio tickers data if available (filtered to limits)
      if (portfolioTickersData && portfolioTickersData.length > 0) {
        portfolioTickersData.forEach(t => {
          const vol = typeof t?.volatility === 'number' ? t.volatility : null;
          const ret = typeof t?.expected_return === 'number' ? t.expected_return : null;
          // Only include values within limits
          if (vol !== null && !isNaN(vol) && isFinite(vol) && vol >= 0 && vol <= 1.1) {
            volatilities.push(vol);
          }
          // Exclude zero or negative returns
          if (ret !== null && !isNaN(ret) && isFinite(ret) && ret > 0 && ret <= 1.0) {
            returns.push(ret);
          }
        });
      }
      
      if (volatilities.length === 0 || returns.length === 0) return null;
      
      const minVol = Math.min(...volatilities);
      const maxVol = Math.max(...volatilities);
      const minRet = Math.min(...returns);
      const maxRet = Math.max(...returns);
      
      if (!isFinite(minVol) || !isFinite(maxVol) || !isFinite(minRet) || !isFinite(maxRet)) {
        return null;
      }
      
      // Ensure there's a valid range
      const volRange = maxVol - minVol;
      const retRange = maxRet - minRet;
      
      if (volRange <= 0 || retRange <= 0) return null;
      
      // Dynamic range, capped at filter limits.
      // X-axis (Risk): linear 0 → maxX, capped at 110% (1.1)
      // Y-axis (Return): log-scale-safe minY → maxY, capped at 100% (1.0)
      const maxX = Math.min(maxVol, 1.1); // Cap at 110%
      const maxY = Math.min(Math.max(maxRet, 0.01), 1.0); // Cap at 100%, minimum 0.01
      const minY = Math.max(minRet, 0.01); // Avoid 0 for log scale on Y
      
      const domain = {
        x: [0, maxX] as [number, number],
        y: [minY, maxY] as [number, number],
      };
      
      return domain;
    } catch (error) {
      console.error('Error calculating eligibleTickersDomain:', error);
      return null;
    }
  }, [eligibleTickers, currentMetrics, portfolioTickersData]);

  // Check for missing portfolio tickers and show warning (fallback fetch disabled)
  useEffect(() => {
    const checkMissingPortfolioTickers = () => {
      if (!currentPortfolio || !Array.isArray(currentPortfolio) || currentPortfolio.length === 0) {
        return;
      }
      
      // Build a map of eligible tickers with their metrics
      const eligibleTickersMap = new Map<string, EligibleTicker>();
      if (eligibleTickers && Array.isArray(eligibleTickers) && eligibleTickers.length > 0) {
        eligibleTickers.forEach(t => {
          if (t && t.ticker) {
            eligibleTickersMap.set(t.ticker.toUpperCase().trim(), t);
          }
        });
      }
      
      // Find portfolio tickers that are missing valid metrics:
      // 1. Not in eligibleTickers, OR
      // 2. In eligibleTickers but have null/undefined/invalid metrics
      const portfolioSymbols = currentPortfolio
        .map(s => s?.symbol?.toUpperCase().trim())
        .filter(Boolean);
      
      const missingTickers = portfolioSymbols.filter(symbol => {
        // Check if already in portfolioTickersMetrics
        if (portfolioTickersMetrics.has(symbol)) {
          return false;
        }
        
        // Check if in eligibleTickers with valid metrics
        const eligibleTicker = eligibleTickersMap.get(symbol);
        if (eligibleTicker) {
          const volatility = eligibleTicker.volatility;
          const expected_return = eligibleTicker.expected_return;
          // If metrics are valid, we don't need to warn
          if (volatility != null && expected_return != null && 
              typeof volatility === 'number' && typeof expected_return === 'number' &&
              !isNaN(volatility) && !isNaN(expected_return) && isFinite(volatility) && isFinite(expected_return)) {
            return false;
          }
        }
        
        // Missing valid metrics for this ticker
        return true;
      });
      
      if (missingTickers.length > 1) {
        console.warn(`[PortfolioOptimization] ⚠️ Some portfolio tickers are missing metrics; fetching via ticker-metrics batch:`, missingTickers);
        
        // Fetch missing metrics via backend batch endpoint and populate portfolioTickersMetrics
        const fetchMissingMetrics = async () => {
          try {
            const response = await fetch(API_ENDPOINTS.TICKER_METRICS, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tickers: missingTickers }),
            });
            
            if (!response.ok) {
              console.warn('[PortfolioOptimization] Ticker metrics batch request failed:', response.status, response.statusText);
              return;
            }
            
            const data = await response.json();
            const mu = data?.mu;
            const sigma = data?.sigma;
            
            if (!mu || !sigma || typeof mu !== 'object' || typeof sigma !== 'object') {
              console.warn('[PortfolioOptimization] Ticker metrics response missing mu/sigma:', data);
              return;
            }
            
            setPortfolioTickersMetrics(prev => {
              const updated = new Map(prev);
              missingTickers.forEach(symbol => {
                const key = symbol.toUpperCase().trim();
                const expected_return = typeof mu[key] === 'number' ? mu[key] : null;
                const volatility = typeof sigma[key]?.[key] === 'number' ? Math.sqrt(Math.max(0, sigma[key][key])) : null;
                if (expected_return != null && volatility != null && isFinite(expected_return) && isFinite(volatility)) {
                  updated.set(key, {
                    volatility,
                    expected_return,
                    company_name: key,
                    sector: undefined,
                  });
                }
              });
              return updated;
            });
          } catch (err) {
            console.warn('[PortfolioOptimization] Error fetching missing ticker metrics:', err);
          }
        };
        
        fetchMissingMetrics();
      } else if (missingTickers.length === 1) {
        // With the current backend design, ticker-metrics requires at least 2 tickers
        // For a single missing ticker we keep the warning but avoid sending an invalid request
        console.warn('[PortfolioOptimization] Single missing ticker cannot be fetched via batch endpoint:', missingTickers[0]);
      }
    };
    
    checkMissingPortfolioTickers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPortfolio, eligibleTickers, portfolioTickersMetrics]);

  const efficientFrontierDomain = useMemo(() => {
    try {
      const allPoints: Array<{ risk: number; return: number }> = [];
      
      // Get risk-free rate for CML origin
      const riskFreeRate = mvoResults?.metadata?.risk_free_rate ?? 0.038; // Default 3.8%
      
      // Only include risk-free rate point if CML is visible
      if (visibleSeries.cml) {
        allPoints.push({ risk: 0, return: riskFreeRate });
      }
      
      // Only include random portfolios if visible
      if (visibleSeries.randomPortfolios && randomPortfolios && Array.isArray(randomPortfolios)) {
        randomPortfolios.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return) &&
              p.return >= 0) { // Only include non-negative returns
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      // Only include efficient frontier if visible
      if (visibleSeries.efficientFrontier && efficientFrontier && Array.isArray(efficientFrontier)) {
        efficientFrontier.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return) &&
              p.return >= 0) { // Only include non-negative returns
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      // Only include CML points if visible
      if (visibleSeries.cml && mvoResults?.capital_market_line && Array.isArray(mvoResults.capital_market_line)) {
        mvoResults.capital_market_line.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return) &&
              p.return >= 0) { // Only include non-negative returns
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      // Include current portfolio if visible
      if (visibleSeries.currentPortfolio) {
        if (tripleOptimizationResults?.current_portfolio?.metrics) {
          const risk = tripleOptimizationResults.current_portfolio.metrics.risk;
          const ret = tripleOptimizationResults.current_portfolio.metrics.expected_return;
          if (typeof risk === 'number' && typeof ret === 'number' && 
              !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret) &&
              ret >= 0) {
            allPoints.push({ risk, return: ret });
          }
        } else if (mvoResults?.current_portfolio?.metrics) {
          const risk = mvoResults.current_portfolio.metrics.risk;
          const ret = mvoResults.current_portfolio.metrics.expected_return;
          if (typeof risk === 'number' && typeof ret === 'number' && 
              !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret) &&
              ret >= 0) {
            allPoints.push({ risk, return: ret });
          }
        } else if (currentMetrics && typeof currentMetrics.risk === 'number' && typeof currentMetrics.expectedReturn === 'number' &&
            !isNaN(currentMetrics.risk) && !isNaN(currentMetrics.expectedReturn) && 
            isFinite(currentMetrics.risk) && isFinite(currentMetrics.expectedReturn) &&
            currentMetrics.expectedReturn >= 0) {
          allPoints.push({ 
            risk: currentMetrics.risk, 
            return: currentMetrics.expectedReturn 
          });
        }
      }
      
      // Include weights-optimized portfolio if visible
      if (visibleSeries.weightsOptimized && tripleOptimizationResults?.weights_optimized_portfolio?.optimized_portfolio?.metrics) {
        const risk = tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.risk;
        const ret = tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return;
        if (typeof risk === 'number' && typeof ret === 'number' && 
            !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret) &&
            ret >= 0) {
          allPoints.push({ risk, return: ret });
        }
      }
      
      // Include market-optimized portfolio if visible
      if (visibleSeries.marketOptimized && tripleOptimizationResults?.market_optimized_portfolio?.optimized_portfolio?.metrics) {
        const risk = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.risk;
        const ret = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.expected_return;
        if (typeof risk === 'number' && typeof ret === 'number' && 
            !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret) &&
            ret >= 0) {
          allPoints.push({ risk, return: ret });
        }
      }
      
      // Only include inefficient frontier if visible - but exclude negative returns
      if (visibleSeries.inefficientFrontier && inefficientFrontier && Array.isArray(inefficientFrontier)) {
        inefficientFrontier.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return) &&
              p.return >= 0) { // Only include non-negative returns
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      if (allPoints.length === 0) return null;
      
      const risks = allPoints.map(p => p.risk).filter(r => isFinite(r));
      const returns = allPoints.map(p => p.return).filter(r => isFinite(r) && r >= 0); // Filter out negative returns
      
      if (risks.length === 0 || returns.length === 0) return null;
      
      const minRisk = Math.min(...risks);
      const maxRisk = Math.max(...risks);
      const minRet = Math.max(0, Math.min(...returns)); // Ensure minimum is at least 0
      const maxRet = Math.max(...returns);
      
      if (!isFinite(minRisk) || !isFinite(maxRisk) || !isFinite(minRet) || !isFinite(maxRet)) {
        return null;
      }
      
      // Ensure there's a valid range
      const riskRange = maxRisk - minRisk;
      const retRange = maxRet - minRet;
      
      if (riskRange <= 0 || retRange <= 0) return null;
      
      // Use 35% padding for better visibility
      const padding = 0.35;
      
      // For Y-axis: Start from 0 or minimum positive return, no negative values
      const yMin = Math.max(0, minRet - retRange * padding);
      const yMax = maxRet + retRange * padding;
      
      // For X-axis: Start from 0 to show CML origin
      const xMin = Math.max(0, minRisk - riskRange * padding);
      const xMax = maxRisk + riskRange * padding;
      
      const domain = {
        x: [xMin, xMax] as [number, number],
        y: [yMin, yMax] as [number, number],
      };
      
      return domain;
    } catch (error) {
      console.error('Error calculating efficientFrontierDomain:', error);
      return null;
    }
  }, [randomPortfolios, efficientFrontier, inefficientFrontier, mvoResults, tripleOptimizationResults, currentMetrics, visibleSeries]);

  // Zoom functions for eligible tickers
  const zoomInEligibleTickers = useCallback(() => {
    setEligibleTickersZoomLevel(prev => {
      const newLevel = Math.min(prev * 1.5, 10);
      console.log('[PortfolioOptimization] Zoom in:', { prev, newLevel, originalDomain: eligibleTickersOriginalDomain });
      return newLevel;
    });
  }, [eligibleTickersOriginalDomain]);
  
  const zoomOutEligibleTickers = useCallback(() => {
    setEligibleTickersZoomLevel(prev => {
      // Default is 0.5, allow only one zoom out to 0.333 (0.5 / 1.5)
      const newLevel = Math.max(prev / 1.5, 0.333);
      console.log('[PortfolioOptimization] Zoom out:', { prev, newLevel });
      return newLevel;
    });
  }, []);
  
  const resetEligibleTickersZoom = useCallback(() => {
    console.log('[PortfolioOptimization] Reset zoom to default (0.5)');
    setEligibleTickersZoomLevel(0.5);
  }, []);
  
  // Zoom functions for efficient frontier
  const zoomInEfficientFrontier = useCallback(() => {
    setEfficientFrontierZoomLevel(prev => Math.min(prev * 1.5, 10));
  }, []);
  
  const zoomOutEfficientFrontier = useCallback(() => {
    setEfficientFrontierZoomLevel(prev => Math.max(prev / 1.5, 1));
  }, []);

  const resetEfficientFrontierZoom = useCallback(() => {
    setEfficientFrontierZoomLevel(1);
  }, []);

  // Box zoom handlers for eligible tickers chart - Standard Recharts ReferenceArea approach
  const handleEligibleTickersMouseDown = useCallback((e: any) => {
    if (!e || !e.activeCoordinate) return;
    // Recharts provides pixel coordinates in activeCoordinate
    const xValue = e.activeCoordinate?.x;
    const yValue = e.activeCoordinate?.y;
    if (xValue === undefined || yValue === undefined) return;
    
    // Convert pixel coordinates to data coordinates using chart dimensions
    // We need to get the actual data values from the chart
    const chartX = e.chartX;
    const chartY = e.chartY;
    if (chartX === undefined || chartY === undefined) return;
    
    setIsEligibleTickersSelecting(true);
    setEligibleTickersSelectionBox({
      start: { x: chartX, y: chartY },
      end: undefined
    });
  }, []);

  const handleEligibleTickersMouseMove = useCallback((e: any) => {
    if (!isEligibleTickersSelecting || !e) return;
    const chartX = e.chartX;
    const chartY = e.chartY;
    if (chartX === undefined || chartY === undefined) return;
    
    // Update pixel coordinates for visual feedback
    setEligibleTickersSelectionBox(prev => prev ? {
      ...prev,
      end: { x: chartX, y: chartY }
    } : null);
    
    // Convert to data coordinates for ReferenceArea display (real-time feedback)
    const domain = eligibleTickersCurrentDomain || eligibleTickersDomain;
    if (domain && domain.x && domain.y && eligibleTickersSelectionBox?.start) {
      try {
        // Get actual chart container dimensions
        const container = e.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
        const chartWidth = container?.clientWidth || 800;
        const chartHeight = container?.clientHeight || 400;
        
        // Margins matching ScatterChart margin prop
        const marginLeft = 48;
        const marginRight = 32;
        const marginTop = 24;
        const marginBottom = 64;
        const plotWidth = chartWidth - marginLeft - marginRight;
        const plotHeight = chartHeight - marginTop - marginBottom;
        
        if (plotWidth <= 0 || plotHeight <= 0) return; // Invalid dimensions
        
        // Get numeric domain values
        const domainX: [number, number] = Array.isArray(domain.x) ? [
          typeof domain.x[0] === 'number' ? domain.x[0] : 0,
          typeof domain.x[1] === 'number' ? domain.x[1] : (typeof domain.x[1] === 'string' && domain.x[1] === 'dataMax' ? 1.4 : 1)
        ] : [0, 1];
        
        const domainY: [number, number] = Array.isArray(domain.y) ? [
          typeof domain.y[0] === 'number' ? domain.y[0] : 0,
          typeof domain.y[1] === 'number' ? domain.y[1] : (typeof domain.y[1] === 'string' && domain.y[1] === 'dataMax' ? 1 : 1)
        ] : [0, 1];
        
        // Convert pixel to data coordinates
        const startXData = domainX[0] + (eligibleTickersSelectionBox.start.x - marginLeft) / plotWidth * (domainX[1] - domainX[0]);
        const startYData = domainY[1] - (eligibleTickersSelectionBox.start.y - marginTop) / plotHeight * (domainY[1] - domainY[0]);
        const endXData = domainX[0] + (chartX - marginLeft) / plotWidth * (domainX[1] - domainX[0]);
        const endYData = domainY[1] - (chartY - marginTop) / plotHeight * (domainY[1] - domainY[0]);
        
        setEligibleTickersSelectionBoxData({
          start: { x: startXData, y: startYData },
          end: { x: endXData, y: endYData }
        });
      } catch (error) {
        // Silently fail - will convert in mouseUp
        console.debug('Error converting coordinates in mouseMove:', error);
      }
    }
  }, [isEligibleTickersSelecting, eligibleTickersSelectionBox, eligibleTickersDomain, eligibleTickersCurrentDomain]);

  const handleEligibleTickersMouseUp = useCallback((e: any) => {
    if (!isEligibleTickersSelecting || !eligibleTickersSelectionBox?.start || !eligibleTickersSelectionBox?.end) {
      setIsEligibleTickersSelecting(false);
      setEligibleTickersSelectionBox(null);
      setEligibleTickersSelectionBoxData(null);
      return;
    }
    
    const domain = eligibleTickersCurrentDomain || eligibleTickersDomain;
    if (!domain || !domain.x || !domain.y) {
      setIsEligibleTickersSelecting(false);
      setEligibleTickersSelectionBox(null);
      setEligibleTickersSelectionBoxData(null);
      return;
    }
    const start = eligibleTickersSelectionBox.start;
    const end = eligibleTickersSelectionBox.end;
    
    // Get actual chart container dimensions
    let chartWidth = 800; // Fallback
    let chartHeight = 400; // Fallback
    try {
      const container = e?.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
      if (container) {
        chartWidth = container.clientWidth;
        chartHeight = container.clientHeight;
      }
    } catch (error) {
      console.debug('Could not get container dimensions, using fallback');
    }
    
    // Margins matching ScatterChart margin prop (line 1644)
    const marginLeft = 48;
    const marginRight = 32;
    const marginTop = 24;
    const marginBottom = 64;
    const plotWidth = chartWidth - marginLeft - marginRight;
    const plotHeight = chartHeight - marginTop - marginBottom;
    
    // Get numeric domain values
    const domainX: [number, number] = Array.isArray(domain.x) ? [
      typeof domain.x[0] === 'number' ? domain.x[0] : 0,
      typeof domain.x[1] === 'number' ? domain.x[1] : (typeof domain.x[1] === 'string' && domain.x[1] === 'dataMax' ? 1.4 : 1)
    ] : [0, 1];
    
    const domainY: [number, number] = Array.isArray(domain.y) ? [
      typeof domain.y[0] === 'number' ? domain.y[0] : 0,
      typeof domain.y[1] === 'number' ? domain.y[1] : (typeof domain.y[1] === 'string' && domain.y[1] === 'dataMax' ? 1 : 1)
    ] : [0, 1];
    
    // Convert pixel coordinates to data coordinates
    // X-axis: left to right, data increases with pixel
    const startXData = domainX[0] + (start.x - marginLeft) / plotWidth * (domainX[1] - domainX[0]);
    const endXData = domainX[0] + (end.x - marginLeft) / plotWidth * (domainX[1] - domainX[0]);
    
    // Y-axis: top to bottom, data decreases with pixel (inverted)
    const startYData = domainY[1] - (start.y - marginTop) / plotHeight * (domainY[1] - domainY[0]);
    const endYData = domainY[1] - (end.y - marginTop) / plotHeight * (domainY[1] - domainY[0]);
    
    // Calculate new domain from data coordinates
    const minX = Math.min(startXData, endXData);
    const maxX = Math.max(startXData, endXData);
    const minY = Math.max(0, Math.min(startYData, endYData)); // Ensure Y doesn't go below 0
    const maxY = Math.max(startYData, endYData);
    
    // Ensure minimum zoom size (at least 5% of current domain range)
    const domainRangeX = domainX[1] - domainX[0];
    const domainRangeY = domainY[1] - domainY[0];
    const minSizeX = domainRangeX * 0.05;
    const minSizeY = domainRangeY * 0.05;
    
    if (maxX - minX < minSizeX || maxY - minY < minSizeY) {
      setIsEligibleTickersSelecting(false);
      setEligibleTickersSelectionBox(null);
      setEligibleTickersSelectionBoxData(null);
      return;
    }
    
    // New domain is the selected data coordinates
    const newDomainX: [number, number] = [minX, maxX];
    const newDomainY: [number, number] = [minY, maxY];
    
    // Save to history (save the domain we're zooming FROM)
    setEligibleTickersZoomHistory(prev => [...prev, { x: domainX, y: domainY }]);
    setEligibleTickersCurrentDomain({ x: newDomainX, y: newDomainY });
    
    setIsEligibleTickersSelecting(false);
    setEligibleTickersSelectionBox(null);
    setEligibleTickersSelectionBoxData(null);
  }, [isEligibleTickersSelecting, eligibleTickersSelectionBox, eligibleTickersDomain, eligibleTickersCurrentDomain]);

  const resetEligibleTickersBoxZoom = useCallback(() => {
    setEligibleTickersCurrentDomain(null);
    setEligibleTickersZoomHistory([]);
    setEligibleTickersSelectionBox(null);
    setEligibleTickersSelectionBoxData(null);
    setIsEligibleTickersSelecting(false);
  }, []);

  const zoomBackEligibleTickers = useCallback(() => {
    if (eligibleTickersZoomHistory.length > 0) {
      const previousDomain = eligibleTickersZoomHistory[eligibleTickersZoomHistory.length - 1];
      setEligibleTickersZoomHistory(prev => prev.slice(0, -1));
      setEligibleTickersCurrentDomain(previousDomain);
    } else {
      resetEligibleTickersBoxZoom();
    }
  }, [eligibleTickersZoomHistory, resetEligibleTickersBoxZoom]);

  // Store chart ref for coordinate conversion
  const efficientFrontierChartRef = useRef<{ xScale?: any; yScale?: any; width?: number; height?: number; offset?: any } | null>(null);
  
  // Helper function to convert plot-area pixel coordinates to data coordinates
  const convertPlotPixelToData = useCallback((
    pixelX: number,
    pixelY: number,
    domain: { x: [number, number] | string[]; y: [number, number] | string[] },
    plotWidth: number,
    plotHeight: number
  ): { x: number; y: number } | null => {
    try {
      // Get numeric domain values
      const domainX: [number, number] = Array.isArray(domain.x) ? [
        typeof domain.x[0] === 'number' ? domain.x[0] : 0,
        typeof domain.x[1] === 'number' ? domain.x[1] : (typeof domain.x[1] === 'string' && domain.x[1] === 'dataMax' ? 1 : 1)
      ] : [0, 1];
      
      const domainY: [number, number] = Array.isArray(domain.y) ? [
        typeof domain.y[0] === 'number' ? domain.y[0] : 0,
        typeof domain.y[1] === 'number' ? domain.y[1] : (typeof domain.y[1] === 'string' && domain.y[1] === 'dataMax' ? 1 : 1)
      ] : [0, 1];
      
      if (plotWidth <= 0 || plotHeight <= 0) return null;
      
      // Convert plot-area pixel coordinates to data coordinates
      // X-axis: left to right, data increases with pixel
      const xData = domainX[0] + (pixelX / plotWidth) * (domainX[1] - domainX[0]);
      // Y-axis: top to bottom, data decreases with pixel (inverted)
      const yData = domainY[1] - (pixelY / plotHeight) * (domainY[1] - domainY[0]);
      
      return { x: xData, y: yData };
    } catch (error) {
      console.debug('Error converting plot pixel to data:', error);
      return null;
    }
  }, []);
  
  // Box zoom handlers for efficient frontier chart - Standard Recharts ReferenceArea approach
  const handleEfficientFrontierMouseDown = useCallback((e: any) => {
    if (!e) return;
    
    // Prefer activeCoordinate - it's already relative to plot area (excluding margins)
    // This is the most reliable coordinate source
    let plotX: number | undefined;
    let plotY: number | undefined;
    let isPlotAreaRelative = false;
    
    if (e.activeCoordinate) {
      // activeCoordinate is relative to plot area (excluding margins) - this is what we want
      plotX = e.activeCoordinate.x;
      plotY = e.activeCoordinate.y;
      isPlotAreaRelative = true;
    } else if (e.chartX !== undefined && e.chartY !== undefined) {
      // chartX/chartY are relative to chart container (including margins)
      // We need to get container dimensions and subtract margins
      try {
        const container = e.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
        if (container) {
          const chartWidth = container.clientWidth;
          const chartHeight = container.clientHeight;
          
          // Margins matching ComposedChart margin prop (line 2275)
          const marginLeft = 56;
          const marginTop = 24;
          
          // Convert container coordinates to plot-area coordinates
          plotX = e.chartX - marginLeft;
          plotY = e.chartY - marginTop;
          isPlotAreaRelative = true;
        }
      } catch (error) {
        console.debug('Could not convert chartX/chartY to plot coordinates:', error);
        return;
      }
    }
    
    if (plotX === undefined || plotY === undefined) return;
    
    // Get domain and plot dimensions for conversion
    const domain = efficientFrontierCurrentDomain || efficientFrontierDomain;
    if (!domain || !domain.x || !domain.y) return;
    
    try {
      const container = e.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
      const chartWidth = container?.clientWidth || 800;
      const chartHeight = container?.clientHeight || 400;
      
      const marginLeft = 56;
      const marginRight = 32;
      const marginTop = 24;
      const marginBottom = 64;
      const plotWidth = chartWidth - marginLeft - marginRight;
      const plotHeight = chartHeight - marginTop - marginBottom;
      
      // Convert to data coordinates immediately
      const dataCoords = convertPlotPixelToData(plotX, plotY, domain, plotWidth, plotHeight);
      if (!dataCoords) return;
      
      setIsEfficientFrontierSelecting(true);
      setEfficientFrontierSelectionBox({
        start: { x: plotX, y: plotY, isPixel: true, isPlotAreaRelative: true },
        end: undefined
      });
      // Store data coordinates for ReferenceArea
      setEfficientFrontierSelectionBoxData({
        start: dataCoords,
        end: dataCoords // Initially same as start
      });
    } catch (error) {
      console.debug('Error in handleEfficientFrontierMouseDown:', error);
    }
  }, [efficientFrontierCurrentDomain, efficientFrontierDomain, convertPlotPixelToData]);

  const handleEfficientFrontierMouseMove = useCallback((e: any) => {
    if (!isEfficientFrontierSelecting || !e || !efficientFrontierSelectionBox?.start) return;
    
    // Prefer activeCoordinate - it's already relative to plot area (excluding margins)
    let plotX: number | undefined;
    let plotY: number | undefined;
    
    if (e.activeCoordinate) {
      // activeCoordinate is relative to plot area - this is what we want
      plotX = e.activeCoordinate.x;
      plotY = e.activeCoordinate.y;
    } else if (e.chartX !== undefined && e.chartY !== undefined) {
      // chartX/chartY are relative to chart container (including margins)
      // Convert to plot-area coordinates
      try {
        const container = e.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
        if (container) {
          const marginLeft = 56;
          const marginTop = 24;
          
          plotX = e.chartX - marginLeft;
          plotY = e.chartY - marginTop;
        }
      } catch (error) {
        console.debug('Could not convert chartX/chartY to plot coordinates in mouseMove:', error);
        return;
      }
    }
    
    if (plotX === undefined || plotY === undefined) return;
      
    // Update pixel coordinates for tracking
      setEfficientFrontierSelectionBox(prev => prev ? {
        ...prev,
      end: { x: plotX!, y: plotY!, isPixel: true, isPlotAreaRelative: true }
      } : null);
      
      // Convert to data coordinates for ReferenceArea display (real-time feedback)
      const domain = efficientFrontierCurrentDomain || efficientFrontierDomain;
    if (domain && domain.x && domain.y && efficientFrontierSelectionBox.start) {
        try {
          const container = e.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
          const chartWidth = container?.clientWidth || 800;
          const chartHeight = container?.clientHeight || 400;
          
          const marginLeft = 56;
          const marginRight = 32;
          const marginTop = 24;
          const marginBottom = 64;
          const plotWidth = chartWidth - marginLeft - marginRight;
          const plotHeight = chartHeight - marginTop - marginBottom;
          
        if (plotWidth <= 0 || plotHeight <= 0) return;
        
        // Convert start coordinates (should already be plot-area relative)
        const startPlotX = efficientFrontierSelectionBox.start.isPlotAreaRelative 
          ? efficientFrontierSelectionBox.start.x 
          : efficientFrontierSelectionBox.start.x - marginLeft;
        const startPlotY = efficientFrontierSelectionBox.start.isPlotAreaRelative 
          ? efficientFrontierSelectionBox.start.y 
          : efficientFrontierSelectionBox.start.y - marginTop;
        
        // Convert both start and end to data coordinates
        const startDataCoords = convertPlotPixelToData(startPlotX, startPlotY, domain, plotWidth, plotHeight);
        const endDataCoords = convertPlotPixelToData(plotX, plotY, domain, plotWidth, plotHeight);
        
        if (startDataCoords && endDataCoords) {
          setEfficientFrontierSelectionBoxData({
            start: startDataCoords,
            end: endDataCoords
          });
        }
        } catch (error) {
          console.debug('Error converting coordinates in mouseMove:', error);
        }
      }
  }, [isEfficientFrontierSelecting, efficientFrontierSelectionBox, efficientFrontierDomain, efficientFrontierCurrentDomain, convertPlotPixelToData]);

  const handleEfficientFrontierMouseUp = useCallback((e: any) => {
    if (!isEfficientFrontierSelecting || !efficientFrontierSelectionBox?.start || !efficientFrontierSelectionBox?.end) {
      setIsEfficientFrontierSelecting(false);
      setEfficientFrontierSelectionBox(null);
      setEfficientFrontierSelectionBoxData(null);
      return;
    }
    
    const domain = efficientFrontierCurrentDomain || efficientFrontierDomain;
    if (!domain || !domain.x || !domain.y) {
      setIsEfficientFrontierSelecting(false);
      setEfficientFrontierSelectionBox(null);
      setEfficientFrontierSelectionBoxData(null);
      return;
    }
    
    // Get current domain values
    const currentDomainX: [number, number] = Array.isArray(domain.x) ? [
      typeof domain.x[0] === 'number' ? domain.x[0] : 0,
      typeof domain.x[1] === 'number' ? domain.x[1] : (typeof domain.x[1] === 'string' && domain.x[1] === 'dataMax' ? 1 : 1)
    ] : [0, 1];
    
    const currentDomainY: [number, number] = Array.isArray(domain.y) ? [
      typeof domain.y[0] === 'number' ? domain.y[0] : 0,
      typeof domain.y[1] === 'number' ? domain.y[1] : (typeof domain.y[1] === 'string' && domain.y[1] === 'dataMax' ? 1 : 1)
    ] : [0, 1];
    
    // Use the data coordinates from selectionBoxData if available (most accurate)
    // Otherwise convert from pixel coordinates
    let startXData: number;
    let endXData: number;
    let startYData: number;
    let endYData: number;
    
    if (efficientFrontierSelectionBoxData) {
      // Use pre-converted data coordinates (most reliable)
      startXData = efficientFrontierSelectionBoxData.start.x;
      startYData = efficientFrontierSelectionBoxData.start.y;
      endXData = efficientFrontierSelectionBoxData.end.x;
      endYData = efficientFrontierSelectionBoxData.end.y;
    } else {
      // Fallback: convert from pixel coordinates
      const start = efficientFrontierSelectionBox.start;
      const end = efficientFrontierSelectionBox.end;
      
      // Get actual chart container dimensions
      let chartWidth = 800; // Fallback
      let chartHeight = 400; // Fallback
      try {
        const container = e?.currentTarget?.closest('.recharts-wrapper') as HTMLElement;
        if (container) {
          chartWidth = container.clientWidth;
          chartHeight = container.clientHeight;
        }
      } catch (error) {
        console.debug('Could not get container dimensions, using fallback');
      }
      
      const marginLeft = 56;
      const marginRight = 32;
      const marginTop = 24;
      const marginBottom = 64;
      const plotWidth = chartWidth - marginLeft - marginRight;
      const plotHeight = chartHeight - marginTop - marginBottom;
      
      if (plotWidth <= 0 || plotHeight <= 0) {
        setIsEfficientFrontierSelecting(false);
        setEfficientFrontierSelectionBox(null);
        setEfficientFrontierSelectionBoxData(null);
        return;
      }
      
      // Convert plot-area pixel coordinates to data coordinates
      const startPlotX = start.isPlotAreaRelative ? start.x : start.x - marginLeft;
      const startPlotY = start.isPlotAreaRelative ? start.y : start.y - marginTop;
      const endPlotX = end.isPlotAreaRelative ? end.x : end.x - marginLeft;
      const endPlotY = end.isPlotAreaRelative ? end.y : end.y - marginTop;
      
      const startCoords = convertPlotPixelToData(startPlotX, startPlotY, domain, plotWidth, plotHeight);
      const endCoords = convertPlotPixelToData(endPlotX, endPlotY, domain, plotWidth, plotHeight);
      
      if (!startCoords || !endCoords) {
        setIsEfficientFrontierSelecting(false);
        setEfficientFrontierSelectionBox(null);
        setEfficientFrontierSelectionBoxData(null);
        return;
      }
      
      startXData = startCoords.x;
      startYData = startCoords.y;
      endXData = endCoords.x;
      endYData = endCoords.y;
    }
    
    const minX = Math.min(startXData, endXData);
    const maxX = Math.max(startXData, endXData);
    const minY = Math.min(startYData, endYData);
    const maxY = Math.max(startYData, endYData);
    
    // Ensure minimum zoom size (at least 5% of current domain range)
    const domainRangeX = currentDomainX[1] - currentDomainX[0];
    const domainRangeY = currentDomainY[1] - currentDomainY[0];
    const minSizeX = domainRangeX * 0.05;
    const minSizeY = domainRangeY * 0.05;
    
    if (maxX - minX < minSizeX || maxY - minY < minSizeY) {
      setIsEfficientFrontierSelecting(false);
      setEfficientFrontierSelectionBox(null);
      setEfficientFrontierSelectionBoxData(null);
      return;
    }
    
    // New domain is the selected data coordinates
    const newDomainX: [number, number] = [minX, maxX];
    const newDomainY: [number, number] = [minY, maxY];
    
    // Save to history (save the domain we're zooming FROM)
    setEfficientFrontierZoomHistory(prev => [...prev, { x: currentDomainX, y: currentDomainY }]);
    setEfficientFrontierCurrentDomain({ x: newDomainX, y: newDomainY });
    
    setIsEfficientFrontierSelecting(false);
    setEfficientFrontierSelectionBox(null);
    setEfficientFrontierSelectionBoxData(null);
  }, [isEfficientFrontierSelecting, efficientFrontierSelectionBox, efficientFrontierSelectionBoxData, efficientFrontierDomain, efficientFrontierCurrentDomain, convertPlotPixelToData]);

  const resetEfficientFrontierBoxZoom = useCallback(() => {
    setEfficientFrontierCurrentDomain(null);
    setEfficientFrontierZoomHistory([]);
    setEfficientFrontierSelectionBox(null);
    setEfficientFrontierSelectionBoxData(null);
    setIsEfficientFrontierSelecting(false);
  }, []);

  const zoomBackEfficientFrontier = useCallback(() => {
    if (efficientFrontierZoomHistory.length > 0) {
      const previousDomain = efficientFrontierZoomHistory[efficientFrontierZoomHistory.length - 1];
      setEfficientFrontierZoomHistory(prev => prev.slice(0, -1));
      setEfficientFrontierCurrentDomain(previousDomain);
    } else {
      resetEfficientFrontierBoxZoom();
    }
  }, [efficientFrontierZoomHistory, resetEfficientFrontierBoxZoom]);

  // Helper function to check if we should use initial metrics
  const shouldUseInitialMetrics = useCallback((portfolio: PortfolioAllocation[]): boolean => {
    if (!initialMetrics || !portfolio || portfolio.length === 0 || !selectedStocks || selectedStocks.length === 0) {
      return false;
    }
    
    // Check if the portfolio matches selectedStocks (same symbols and allocations)
    const sortedPortfolio = [...portfolio].sort((a, b) => a.symbol.localeCompare(b.symbol));
    const sortedSelected = [...selectedStocks].sort((a, b) => a.symbol.localeCompare(b.symbol));
    
    if (sortedPortfolio.length !== sortedSelected.length) {
      return false;
    }
    
    return sortedPortfolio.every((stock, idx) => 
      stock.symbol === sortedSelected[idx].symbol && 
      Math.abs(stock.allocation - sortedSelected[idx].allocation) < 0.1
    );
  }, [initialMetrics, selectedStocks]);

  // Calculate current portfolio metrics
  const calculateCurrentMetrics = useCallback(async () => {
    if (!currentPortfolio || currentPortfolio.length === 0) {
      setCurrentMetrics(null);
      return null;
    }
    
    try {
      const response = await fetch('/api/portfolio/calculate-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          allocations: currentPortfolio,
          riskProfile: riskProfile
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to calculate metrics: ${response.statusText}`);
      }
      
      const data = await response.json();
      return {
        expectedReturn: data.expectedReturn,
        risk: data.risk,
        diversificationScore: data.diversificationScore
      };
    } catch (err) {
      console.error('Error calculating metrics:', err);
      return null;
    }
  }, [currentPortfolio, riskProfile]);

  // Helper function to check if two portfolios match (same symbols and allocations)
  const portfoliosMatch = useCallback((portfolio1: PortfolioAllocation[], portfolio2: PortfolioAllocation[]): boolean => {
    if (!portfolio1 || !portfolio2 || portfolio1.length !== portfolio2.length) return false;
    const sorted1 = [...portfolio1].sort((a, b) => a.symbol.localeCompare(b.symbol));
    const sorted2 = [...portfolio2].sort((a, b) => a.symbol.localeCompare(b.symbol));
    return sorted1.every((stock, idx) => 
      stock.symbol === sorted2[idx].symbol && 
      Math.abs(stock.allocation - sorted2[idx].allocation) < 0.1
    );
  }, []);

  // Sync currentPortfolio when selectedStocks changes
  useEffect(() => {
    if (selectedStocks && selectedStocks.length > 0) {
      setCurrentPortfolio(selectedStocks);
    }
  }, [selectedStocks]);

  // Initialize or update metrics when portfolio or initialMetrics change
  useEffect(() => {
    // First, check if we can use initial metrics (portfolio matches selectedStocks)
    if (shouldUseInitialMetrics(currentPortfolio)) {
      console.log('✅ Using existing portfolio metrics from StockSelection:', initialMetrics);
      setCurrentMetrics({
        expectedReturn: initialMetrics!.expectedReturn,
        risk: initialMetrics!.risk,
        diversificationScore: initialMetrics!.diversificationScore
      });
      return;
    }

    // If initial metrics don't match or don't exist, calculate metrics
    const fetchMetrics = async () => {
      try {
        if (currentPortfolio && currentPortfolio.length > 0) {
          const metrics = await calculateCurrentMetrics();
          if (metrics) {
            setCurrentMetrics(metrics);
          }
        } else {
          setCurrentMetrics(null);
        }
      } catch (error) {
        console.error('Error in fetchMetrics useEffect:', error);
        setCurrentMetrics(null);
      }
    };
    
    fetchMetrics();
  }, [currentPortfolio, calculateCurrentMetrics, initialMetrics, selectedStocks, shouldUseInitialMetrics]);

  // Store original domain when eligibleTickersDomain changes (for zoom)
  // Lock the original domain once set, only reset if data fundamentally changes
  useEffect(() => {
    if (eligibleTickersDomain?.y && eligibleTickersDomain.y[0] !== undefined && eligibleTickersDomain.y[1] !== undefined) {
      setEligibleTickersOriginalDomain(prev => {
        // Only set if not already set, or if the domain changed significantly (more than 10% difference)
        // This prevents resetting zoom on minor data fluctuations
        if (!prev) {
          // First time - store the domain
          return { y: eligibleTickersDomain.y };
        } else {
          // Domain already set - only update if changed significantly (more than 10%)
          const percentChange = Math.abs(prev.y[1] - eligibleTickersDomain.y[1]) / prev.y[1];
          if (percentChange > 0.1) {
            // Significant change - reset zoom and update domain
            setEligibleTickersZoomLevel(1);
            return { y: eligibleTickersDomain.y };
          }
          // Minor change - keep original domain for consistent zoom
          return prev;
        }
      });
    }
  }, [eligibleTickersDomain]);

  // Store original domain when efficientFrontierDomain changes (for zoom)
  useEffect(() => {
    if (efficientFrontierDomain?.y && efficientFrontierDomain.y[0] !== undefined && efficientFrontierDomain.y[1] !== undefined) {
      setEfficientFrontierOriginalDomain(prev => {
        // Only update if not set yet, or if the domain changed significantly (reset zoom)
        if (!prev || Math.abs(prev.y[1] - efficientFrontierDomain.y[1]) > 0.01) {
          // Reset zoom when domain changes significantly
          if (prev && Math.abs(prev.y[1] - efficientFrontierDomain.y[1]) > 0.01) {
            setEfficientFrontierZoomLevel(1);
          }
          return { y: efficientFrontierDomain.y };
        }
        return prev;
      });
    }
  }, [efficientFrontierDomain]);

  // Fetch eligible tickers (no risk profile filter) for Stock Universe visualization
  useEffect(() => {
    const fetchEligibleTickers = async () => {
      setIsLoadingEligibleTickers(true);
      setError(null);
      
      try {
        // Fetch eligible tickers without risk profile filtering
        // Include tickers with negative returns
        const params = new URLSearchParams({
          min_data_points: '12',
          filter_negative_returns: 'false', // Include tickers with negative returns
          per_page: '700', // Increased to show more of the universe while keeping performance reasonable
          page: '1'
        });
        
        const response = await fetch(API_ENDPOINTS.ELIGIBLE_TICKERS(params.toString()));
        
        if (!response.ok) {
          throw new Error(`Failed to fetch eligible tickers: ${response.statusText}`);
        }
        
        const data = await response.json();
        const tickers = data.eligible_tickers || [];
        
        // Transform to our format
        const formattedTickers: EligibleTicker[] = tickers
          .map((t: any) => {
            const expectedReturn = typeof t.expected_return === 'number'
              ? t.expected_return
              : typeof t.expectedReturn === 'number'
              ? t.expectedReturn
              : 0;
            const volatility = typeof t.volatility === 'number'
              ? t.volatility
              : typeof t.risk === 'number'
              ? t.risk
              : 0;
            
            return {
              ticker: t.ticker || t.symbol,
              expected_return: expectedReturn,
              volatility,
              sector: t.sector || 'Unknown',
              company_name: t.company_name || t.ticker || t.symbol
            } as EligibleTicker;
          })
          .filter((t: EligibleTicker) => {
            // Include tickers with negative returns (filter_negative_returns=false)
            // Frontend filters: volatility > 0 and <= 140%, filter out ETFs and Unknown sectors
            const isETF = t.sector?.toLowerCase().includes('etf') || 
                         t.company_name?.toLowerCase().includes('etf') ||
                         t.company_name?.toLowerCase().includes('exchange traded fund') ||
                         t.sector === 'Diversified ETF' ||
                         t.sector === 'Technology ETF' ||
                         t.sector === 'Fixed Income ETF';
            const hasUnknownSector = !t.sector || t.sector.toLowerCase() === 'unknown';
            
            // Allow negative returns, just check that expected_return is a number
            return typeof t.expected_return === 'number'
              && typeof t.volatility === 'number' && t.volatility > 0 && t.volatility <= 1.4
              && !isETF && !hasUnknownSector;
          });
        
        setEligibleTickers(formattedTickers);
      } catch (err) {
        console.error('Error fetching eligible tickers:', err);
        setError('Failed to load eligible tickers. Please try again.');
      } finally {
        setIsLoadingEligibleTickers(false);
      }
    };
    
    fetchEligibleTickers();
  }, []);

  // Generate efficient frontier points
  const generateEfficientFrontier = () => {
    if (!currentPortfolio || currentPortfolio.length < 3) return [];
    
    const points: EfficientFrontierPoint[] = [];
    
    // Current portfolio point
    if (currentMetrics) {
      points.push({
        risk: currentMetrics.risk,
        return: currentMetrics.expectedReturn,
        weights: currentPortfolio.map(s => s.allocation / 100),
        type: 'current'
      });
    }
    
    // Generate frontier points
    for (let i = 0; i < 20; i++) {
      const riskRatio = i / 19; // 0 to 1
      const baseRisk = 0.08; // Minimum risk
      const maxRisk = 0.35; // Maximum risk
      const risk = baseRisk + (maxRisk - baseRisk) * riskRatio;
      
      // Generate return based on risk (efficient frontier curve)
      const return_ = 0.02 + 0.8 * risk + 0.1 * Math.random(); // Mock efficient frontier
      
      points.push({
        risk,
        return: return_,
        weights: currentPortfolio.map(() => Math.random()), // Mock weights
        type: 'frontier'
      });
    }
    
    // Optimized portfolio point (better than current)
    if (currentMetrics) {
      points.push({
        risk: currentMetrics.risk * 0.9, // 10% less risk
        return: currentMetrics.expectedReturn * 1.1, // 10% more return
        weights: currentPortfolio.map(s => s.allocation / 100),
        type: 'optimized'
      });
    }
    
    return points;
  };

  // Run portfolio optimization using MVO endpoint (supports dual optimization)
  const runOptimization = async () => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    
    try {
      // Extract ticker symbols from current portfolio
      const tickers = currentPortfolio.map(stock => stock.symbol);
      
      if (tickers.length < 2) {
        throw new Error('At least 2 tickers required for optimization');
      }

      // Quick backend health check before making the request
      try {
        const healthCheck = await fetch('/health', { signal: AbortSignal.timeout(5000) });
        if (!healthCheck.ok) {
          console.warn('[PortfolioOptimization] Backend health check returned non-OK status:', healthCheck.status);
        }
      } catch (healthError) {
        // Health check failed, but continue anyway - the actual request might work
        console.warn('[PortfolioOptimization] Backend health check failed (continuing anyway):', healthError);
      }

      // Validate risk profile
      if (!riskProfile || typeof riskProfile !== 'string') {
        throw new Error('Risk profile is required for optimization. Please select a risk profile.');
      }
      
      // Prepare current portfolio weights for comparison
      const currentWeights: Record<string, number> = {};
      currentPortfolio.forEach(stock => {
        currentWeights[stock.symbol] = stock.allocation / 100;
      });
      
      // Prepare request payload for triple optimization
      const requestPayload = {
        user_tickers: tickers,
        user_weights: currentWeights,  // NEW: Actual weights
        risk_profile: riskProfile,
        optimization_type: 'max_sharpe',
        max_eligible_tickers: 20,
        include_efficient_frontier: true,
        include_random_portfolios: true,
        num_frontier_points: 20,
        num_random_portfolios: 300,
        use_combined_strategy: true,  // NEW: Enable combined strategy
        attempt_market_exploration: true  // NEW: Always attempt market exploration
      };
      
      console.log('[PortfolioOptimization] Starting optimization with:', {
        tickers,
        riskProfile,
        requestPayload
      });
      
      // Always use market optimization: Optimize from eligible market tickers
      // Create an AbortController for timeout handling (60 seconds for optimization)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
      
      let response: Response;
      try {
        response = await fetch('/api/portfolio/optimization/triple', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestPayload),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        
        // Distinguish network errors from other fetch errors
        if (fetchError.name === 'AbortError') {
          throw new Error('Optimization request timed out after 60 seconds. This can happen with large portfolios. Please try again or select fewer tickers.');
        }
        
        // Network errors (connection refused, CORS, etc.)
        if (fetchError.message === 'Failed to fetch' || 
            fetchError.message.includes('NetworkError') ||
            fetchError.message.includes('network') ||
            fetchError.name === 'TypeError') {
          throw new Error('Cannot connect to the backend server. Please ensure:\n\n1. The backend server is running on port 8000\n2. Vite dev server is running and proxying requests\n3. Check your browser console for detailed error messages');
        }
        
        // Re-throw other errors
        throw new Error(`Network request failed: ${fetchError.message || 'Unknown error'}`);
      }
        
        if (!response.ok) {
          // Try to parse error response
          let errorMessage = `Server error: ${response.status} ${response.statusText}`;
          
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch (parseError) {
            // If JSON parsing fails, use status text
            const text = await response.text().catch(() => '');
            if (text) {
              errorMessage = `Server error (${response.status}): ${text.substring(0, 200)}`;
            }
          }
          
          // Provide helpful suggestions for specific error types
          const errorLower = errorMessage.toLowerCase();
          
          // Volatility constraint errors
          if (errorLower.includes("minimum volatility") || errorLower.includes("target_volatility")) {
            const minVolMatch = errorMessage.match(/(\d+\.?\d*)/);
            const minVol = minVolMatch ? parseFloat(minVolMatch[1]) : null;
            
            const suggestions: string[] = [];
            if (minVol !== null) {
              suggestions.push(`Your portfolio's minimum volatility (${(minVol * 100).toFixed(1)}%) exceeds the ${riskProfile} risk profile limit.`);
            }
            
            suggestions.push("Suggestions:");
            suggestions.push("1. Select a more aggressive risk profile that allows higher volatility");
            suggestions.push("2. Replace some high-volatility assets with lower-volatility alternatives");
            suggestions.push("3. Add more diversified assets to reduce overall portfolio risk");
            suggestions.push("4. Consider using 'min_variance' optimization instead of 'max_sharpe'");
            
            throw new Error(`${errorMessage}\n\n${suggestions.join('\n')}`);
          }
          
          // Insufficient tickers
          if (errorLower.includes("at least") && errorLower.includes("ticker")) {
            throw new Error(`${errorMessage}\n\nPlease ensure you have selected at least 2 tickers for optimization.`);
          }
          
          // Bad request errors
          if (response.status === 400) {
            throw new Error(`Invalid request: ${errorMessage}\n\nPlease check that all required fields are provided correctly.`);
          }
          
          // Server errors
          if (response.status >= 500) {
            throw new Error(`Server error: ${errorMessage}\n\nThe backend encountered an error. Please try again or check server logs.`);
          }
          
          // Other API errors
          throw new Error(`API error (${response.status}): ${errorMessage}`);
        }
        
        // Parse response JSON with error handling
        let tripleData: TripleOptimizationResponse;
        try {
          tripleData = await response.json();
        } catch (parseError: any) {
          throw new Error(`Failed to parse server response. The server may have returned invalid data. Error: ${parseError.message || 'Unknown parsing error'}`);
        }
        
        // Validate response structure
        if (!tripleData || !tripleData.current_portfolio || !tripleData.weights_optimized_portfolio) {
          throw new Error('Server returned incomplete data. Expected triple optimization response with current_portfolio and weights_optimized_portfolio.');
        }
        
        // Debug logging
        const currentTickers = tripleData.current_portfolio?.tickers || [];
        const weightsTickers = tripleData.weights_optimized_portfolio?.optimized_portfolio?.tickers || [];
        const marketTickers = tripleData.market_optimized_portfolio?.optimized_portfolio?.tickers || [];
        
        console.log('[PortfolioOptimization] Triple optimization results:', {
          current_tickers: currentTickers,
          weights_tickers: weightsTickers,
          market_tickers: marketTickers,
          current_metrics: tripleData.current_portfolio?.metrics,
          weights_metrics: tripleData.weights_optimized_portfolio?.optimized_portfolio?.metrics,
          market_metrics: tripleData.market_optimized_portfolio?.optimized_portfolio?.metrics,
          comparison: tripleData.comparison,
          recommendation: tripleData.optimization_metadata?.recommendation
        });
        
        // Store optimization results
        setTripleOptimizationResults(tripleData);
        setSelectedPortfolio(null);  // Reset selection
        
        // Set market-optimized as primary MVO result (for backward compatibility with existing chart code)
        // If market optimization failed, use weights-optimized
        const primaryMvoResult = tripleData.market_optimized_portfolio || tripleData.weights_optimized_portfolio;
        setMvoResults(primaryMvoResult);
        
        // Use recommended portfolio for allocations display (or market if available)
        const data = tripleData.market_optimized_portfolio || tripleData.weights_optimized_portfolio;
        
        // Convert optimized portfolio to allocations format
        const optimizedAllocations: PortfolioAllocation[] = [];
        const optPortfolio = data.optimized_portfolio;
        
        optPortfolio.tickers.forEach((ticker, index) => {
          const weight = optPortfolio.weights[ticker] || 0;
          if (weight > 0.001) {
            const originalStock = currentPortfolio.find(s => s.symbol === ticker);
            optimizedAllocations.push({
              symbol: ticker,
              allocation: Math.round(weight * 100 * 10) / 10,
              name: originalStock?.name,
              assetType: originalStock?.assetType || 'stock'
            });
          }
        });
        
        setOptimizedPortfolio(optimizedAllocations);
        
        // Set optimization results for display
        setOptimizationResults({
          weights: optPortfolio.weights_list,
          expectedReturn: optPortfolio.metrics.expected_return,
          risk: optPortfolio.metrics.risk,
          diversificationScore: 0
        });
        
        // Set efficient frontier - Use market-optimized portfolio's frontier if available, otherwise weights-optimized
        const frontierData = tripleData.market_optimized_portfolio || tripleData.weights_optimized_portfolio;
        if (frontierData?.efficient_frontier && frontierData.efficient_frontier.length > 0) {
          setEfficientFrontier(frontierData.efficient_frontier.map((point: any) => ({
            risk: point.risk,
            return: point.return,
            weights: point.weights_list || [],
            sharpe_ratio: point.sharpe_ratio,
            type: 'frontier' as const
          })));
          
          // Verify CML intersection - Market-Optimized Portfolio should intersect CML
          const marketOptMetrics = tripleData.market_optimized_portfolio?.optimized_portfolio?.metrics;
          const optimizedSharpe = marketOptMetrics?.sharpe_ratio ?? 0;
          const optimizedRisk = marketOptMetrics?.risk ?? 0;
          const optimizedReturn = marketOptMetrics?.expected_return ?? 0;
          
          // Find tangent portfolio from efficient frontier (for CML calculation)
          const tangentPortfolio = frontierData.efficient_frontier.length > 0 
            ? frontierData.efficient_frontier.reduce((max: any, p: any) => 
                (p.sharpe_ratio || 0) > (max.sharpe_ratio || 0) ? p : max, frontierData.efficient_frontier[0])
            : null;
          
          const tangentSharpe = tangentPortfolio?.sharpe_ratio || 0;
          const riskFreeRate = frontierData.metadata?.risk_free_rate || 0.038;
          
          // Calculate CML return at Optimized Portfolio's risk level
          const cmlReturnAtOptimizedRisk = riskFreeRate + tangentSharpe * optimizedRisk;
          const cmlIntersection = Math.abs(optimizedReturn - cmlReturnAtOptimizedRisk) < 0.01; // Within 1% tolerance
          
          console.log('[PortfolioOptimization] CML Intersection Verification:', {
            optimizedPortfolio: {
              sharpe: optimizedSharpe.toFixed(3),
              risk: (optimizedRisk * 100).toFixed(2) + '%',
              return: (optimizedReturn * 100).toFixed(2) + '%'
            },
            tangentPortfolio: {
              sharpe: tangentSharpe.toFixed(3),
              risk: tangentPortfolio ? (tangentPortfolio.risk * 100).toFixed(2) + '%' : 'N/A',
              return: tangentPortfolio ? (tangentPortfolio.return * 100).toFixed(2) + '%' : 'N/A'
            },
            cmlAtOptimizedRisk: {
              calculatedReturn: (cmlReturnAtOptimizedRisk * 100).toFixed(2) + '%',
              actualReturn: (optimizedReturn * 100).toFixed(2) + '%',
              difference: ((optimizedReturn - cmlReturnAtOptimizedRisk) * 100).toFixed(2) + '%'
            },
            intersectsCML: cmlIntersection,
            explanation: cmlIntersection 
              ? 'Optimized Portfolio intersects its CML (optimized from same ticker set as frontier)'
              : 'Optimized Portfolio may not exactly intersect CML due to risk profile constraints or optimization method'
          });
        }
        
        // Set inefficient frontier (from market-optimized if available)
        if (frontierData?.inefficient_frontier && frontierData.inefficient_frontier.length > 0) {
          setInefficientFrontier(frontierData.inefficient_frontier.map((point: any) => ({
            risk: point.risk,
            return: point.return,
            weights: point.weights_list || [],
            sharpe_ratio: point.sharpe_ratio,
            type: 'inefficient_frontier' as const
          })));
        } else {
          setInefficientFrontier([]);
        }
        
        // Set random portfolios (from market-optimized if available)
        if (frontierData?.random_portfolios && frontierData.random_portfolios.length > 0) {
          setRandomPortfolios(frontierData.random_portfolios.map((point: any) => ({
            risk: point.risk,
            return: point.return,
            weights: point.weights_list || [],
            sharpe_ratio: point.sharpe_ratio,
            type: 'random' as const
          })));
        }
        
        setSuccessMessage('Portfolio optimization completed successfully!');
      
      // Auto-switch to Analysis tab after optimization
      setTimeout(() => {
        setActiveTab('analysis');
      }, 500);
      
    } catch (err: any) {
      console.error('[PortfolioOptimization] Optimization error:', err);
      
      // Handle different error types with appropriate messages
      let errorMessage = 'Failed to run portfolio optimization. Please try again.';
      
      if (err instanceof Error) {
        // Use the error message we created with detailed information
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err?.message) {
        errorMessage = err.message;
      } else {
        // Fallback for unknown error types
        errorMessage = `Unexpected error: ${JSON.stringify(err).substring(0, 200)}`;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply optimization
  const applyOptimization = () => {
    if (optimizedPortfolio.length > 0) {
      setCurrentPortfolio(optimizedPortfolio);
      setSuccessMessage('Optimized portfolio applied successfully!');
    }
  };

  // Reset to original
  const resetToOriginal = () => {
    setCurrentPortfolio(selectedStocks);
    setOptimizedPortfolio([]);
    setOptimizationResults(null);
    setEfficientFrontier([]);
    setSuccessMessage('Portfolio reset to original selection');
  };

  // Get risk profile display name
  const getRiskProfileDisplay = () => {
    const profileMap: Record<string, string> = {
      'very-conservative': 'Very Conservative',
      'conservative': 'Conservative',
      'moderate': 'Moderate',
      'aggressive': 'Aggressive',
      'very-aggressive': 'Very Aggressive'
    };
    return profileMap[riskProfile] || 'Moderate';
  };

  return (
    <div className="max-w-6xl mx-auto p-4">
      <Card>
        <CardHeader className="text-center pb-2">
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-muted flex items-center justify-center border border-border">
            <BarChart3 className="h-5 w-5 text-white" />
          </div>
          <CardTitle className="text-xl">Portfolio Optimization</CardTitle>
          <p className="text-muted-foreground text-sm">
            Optimize your {capital ? capital.toLocaleString() : '0'} SEK portfolio for better risk-return balance
          </p>
          <div className="flex items-center justify-center gap-2 mt-1">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Risk Profile: {getRiskProfileDisplay()}
            </span>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <Tabs value={activeTab} onValueChange={(value) => {
            // Prevent manual switching if conditions aren't met
            if (value === 'analysis' && !mvoResults && !tripleOptimizationResults) return;
            if (value === 'recommendations' && (!mvoResults && !tripleOptimizationResults || !selectedPortfolio)) return;
            setActiveTab(value as any);
          }}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <Info className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="optimization" className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                Optimization
              </TabsTrigger>
              <TabsTrigger 
                value="analysis" 
                className="flex items-center gap-2"
                disabled={!mvoResults && !tripleOptimizationResults}
              >
                <LineChart className="h-4 w-4" />
                Analysis
              </TabsTrigger>
              <TabsTrigger 
                value="recommendations" 
                className="flex items-center gap-2"
                disabled={(!mvoResults && !tripleOptimizationResults) || !selectedPortfolio}
              >
                <Lightbulb className="h-4 w-4" />
                Recommendations
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <div className="bg-muted rounded-lg p-3 border border-border">
                <div className="flex items-center gap-2 mb-1">
                  <Lightbulb className="h-4 w-4 text-blue-600" />
                  <h3 className="text-base font-semibold text-blue-900">Portfolio Optimization</h3>
                </div>
                <p className="text-xs text-blue-800">
                  Advanced algorithms analyze your portfolio to find the optimal balance between risk and return using modern portfolio theory.
                </p>
              </div>

              {/* Current Portfolio Summary */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Current Portfolio Summary</CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    {currentPortfolio?.length || 0} assets selected
                  </p>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  {currentPortfolio && currentPortfolio.length > 0 ? (
                    <div className="grid grid-cols-1 gap-2">
                      {currentPortfolio.map((stock, index) => (
                        <div key={stock.symbol} className="flex items-center justify-between p-2.5 border rounded-lg bg-muted/30">
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                              <span className="text-xs font-medium text-blue-600">{index + 1}</span>
                            </div>
                            <div className="min-w-0">
                              <div className="font-medium text-sm">{stock.symbol}</div>
                              <div className="text-xs text-muted-foreground truncate">{stock.name || 'Stock'}</div>
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="font-semibold text-sm">{stock.allocation}%</div>
                            <div className="text-xs text-muted-foreground">
                              {capital ? (stock.allocation / 100 * capital).toLocaleString() : '0'} SEK
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground">
                      <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No portfolio selected</p>
                    </div>
                  )}
                  
                  {currentMetrics && (
                    <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-border/50">
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-emerald-700">
                          {((currentMetrics.expectedReturn || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-emerald-600 mt-0.5">Expected Return</div>
                      </div>
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-amber-700">
                          {((currentMetrics.risk || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-amber-600 mt-0.5">Risk Level</div>
                      </div>
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-purple-700">
                          {(currentMetrics.diversificationScore || 0).toFixed(0)}%
                        </div>
                        <div className="text-xs text-purple-600 mt-0.5">Diversification</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Optimization Tab */}
            <TabsContent value="optimization" className="space-y-6">
              <div
                className="space-y-6"
                style={{
                  background: chartTheme.canvas,
                  padding: layoutConstants.spacing.cardPadding,
                  borderRadius: layoutConstants.radius,
                }}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3
                      className="text-lg font-semibold mb-1"
                      style={{ color: chartTheme.text.primary }}
                    >
                      Portfolio Optimization
                    </h3>
                    <p
                      className="text-sm"
                      style={{ color: chartTheme.text.secondary }}
                    >
                      View all eligible tickers and your current portfolio on the risk-return graph
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsLoadingEligibleTickers(true);
                      setError(null);
                      // Re-fetch eligible tickers
                      const fetchEligibleTickers = async () => {
                        try {
                          const params = new URLSearchParams({
                            min_data_points: '12',
                            filter_negative_returns: 'true',
                            per_page: '700',
                            page: '1'
                          });
                          const response = await fetch(API_ENDPOINTS.ELIGIBLE_TICKERS(params.toString()));
                          if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`);
                          const data = await response.json();
                          const tickers = data.eligible_tickers || [];
                          const formattedTickers: EligibleTicker[] = tickers
                            .map((t: any) => {
                              const expectedReturn = typeof t.expected_return === 'number'
                                ? t.expected_return
                                : typeof t.expectedReturn === 'number'
                                ? t.expectedReturn
                                : 0;
                              const volatility = typeof t.volatility === 'number'
                                ? t.volatility
                                : typeof t.risk === 'number'
                                ? t.risk
                                : 0;
                              
                              return {
                            ticker: t.ticker || t.symbol,
                                expected_return: expectedReturn,
                                volatility,
                            sector: t.sector,
                            company_name: t.company_name
                              } as EligibleTicker;
                            })
                            .filter((t: EligibleTicker) => {
                              // Filter: positive returns, volatility > 0 and <= 140%
                              return typeof t.expected_return === 'number' && t.expected_return >= 0 
                                && typeof t.volatility === 'number' && t.volatility > 0 && t.volatility <= 1.4;
                            });
                          setEligibleTickers(formattedTickers);
                        } catch (err) {
                          console.error('Error fetching eligible tickers:', err);
                          setError('Failed to load eligible tickers. Please try again.');
                        } finally {
                          setIsLoadingEligibleTickers(false);
                        }
                      };
                      fetchEligibleTickers();
                    }}
                    disabled={isLoadingEligibleTickers}
                    style={{ borderColor: chartTheme.border, color: chartTheme.text.primary }}
                  >
                    {isLoadingEligibleTickers ? (
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

                {/* 2D Risk-Return Graph */}
                <Card
                  className="w-full"
                  style={{ background: chartTheme.cardBackground, borderColor: chartTheme.border }}
                >
                  <CardHeader className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 text-center">
                      <CardTitle
                          className="text-lg"
                          style={{ color: chartTheme.text.primary, fontWeight: 600, letterSpacing: '-0.01em' }}
                      >
                        Stock Universe
                      </CardTitle>
                        <p className="text-xs mt-1" style={{ color: chartTheme.text.subtle }}>
                          Drag to zoom • Use buttons to navigate
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={zoomInEligibleTickers}
                          className="h-7 w-7 p-0"
                          title="Zoom in (button)"
                          disabled={eligibleTickersZoomLevel >= 10}
                        >
                          <ZoomIn className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={zoomOutEligibleTickers}
                          className="h-7 w-7 p-0"
                          title="Zoom out (button)"
                          disabled={eligibleTickersZoomLevel <= 0.333}
                        >
                          <ZoomOut className="h-3.5 w-3.5" />
                        </Button>
                        {(eligibleTickersZoomLevel !== 0.5 || eligibleTickersCurrentDomain) && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={eligibleTickersCurrentDomain ? resetEligibleTickersBoxZoom : resetEligibleTickersZoom}
                            className="h-7 px-2 text-xs"
                            title="Reset zoom"
                          >
                            <RotateCcw className="h-3.5 w-3.5 mr-1" />
                            Reset
                          </Button>
                        )}
                        {eligibleTickersZoomHistory.length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={zoomBackEligibleTickers}
                            className="h-7 px-2 text-xs"
                            title="Zoom back"
                          >
                            <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                            Back
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent
                    className="min-h-[500px] h-[500px]"
                    style={{
                      background: chartTheme.canvas,
                      borderRadius: layoutConstants.radius,
                      padding: '12px',
                    }}
                  >
                    {isLoadingEligibleTickers ? (
                      <div className="flex h-full w-full flex-col gap-4 p-4">
                        <Skeleton className="h-full min-h-[400px] w-full rounded-lg" />
                        <div className="flex gap-2 justify-end">
                          <Skeleton className="h-9 w-24" />
                          <Skeleton className="h-9 w-24" />
                        </div>
                      </div>
                    ) : eligibleTickers && Array.isArray(eligibleTickers) && eligibleTickers.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <ScatterChart
                          margin={{ top: 24, right: 32, bottom: 64, left: 48 }}
                          onMouseDown={handleEligibleTickersMouseDown}
                          onMouseMove={handleEligibleTickersMouseMove}
                          onMouseUp={handleEligibleTickersMouseUp}
                          onMouseLeave={() => {
                            if (isEligibleTickersSelecting) {
                              setIsEligibleTickersSelecting(false);
                              setEligibleTickersSelectionBox(null);
                              setEligibleTickersSelectionBoxData(null);
                            }
                          }}
                          >
                          <CartesianGrid strokeDasharray="3 4" stroke={chartTheme.grid} />
                          <XAxis
                            type="number"
                            dataKey="volatility"
                            name="Risk"
                            tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                            axisLine={{ stroke: chartTheme.axes.line }}
                            tickLine={{ stroke: 'transparent' }}
                            tick={{ fill: chartTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                            domain={eligibleTickersCurrentDomain?.x || eligibleTickersDomain?.x || [0, 'dataMax']}
                            allowDataOverflow={true}
                            label={{
                              value: 'Risk',
                              position: 'insideBottom',
                              offset: -6,
                              style: { fill: chartTheme.axes.label, fontWeight: 500 },
                            }}
                          />
                          <YAxis
                            type="number"
                            scale="log"
                            dataKey="expected_return"
                            name="Return"
                            tickFormatter={(value) => {
                              // Only show positive or zero values - hide negative labels
                              if (value < 0) return '';
                              return `${(value * 100).toFixed(1)}%`;
                            }}
                            axisLine={{ stroke: chartTheme.axes.line }}
                            tickLine={{ stroke: 'transparent' }}
                            tick={{ fill: chartTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                            allowDecimals={true}
                            allowDataOverflow={true}
                            domain={
                              eligibleTickersCurrentDomain?.y
                                ? [Math.max(0.01, eligibleTickersCurrentDomain.y[0]), eligibleTickersCurrentDomain.y[1]]
                                : eligibleTickersZoomLevel > 1 && eligibleTickersOriginalDomain?.y
                                  ? [
                                      Math.max(0.01, eligibleTickersOriginalDomain.y[0] / eligibleTickersZoomLevel),
                                      Math.max(0.01, eligibleTickersOriginalDomain.y[1] / eligibleTickersZoomLevel)
                                    ]
                                  : eligibleTickersDomain?.y 
                                    ? eligibleTickersDomain.y
                                    : [0.01, 'dataMax'] // Default to dynamic range (log-safe)
                            }
                            label={{
                              value: 'Return',
                              angle: -90,
                              position: 'insideLeft',
                              style: { fill: chartTheme.axes.label, fontWeight: 500 },
                            }}
                          />
                          <RechartsTooltip
                            cursor={!isEligibleTickersSelecting ? { strokeDasharray: '3 3' } : false}
                            content={({ active, payload }: TooltipProps<ValueType, NameType>) => {
                              // Don't show tooltip during selection
                              if (isEligibleTickersSelecting) return null;
                              if (active && payload && payload.length && payload[0]?.payload) {
                                const data = payload[0].payload as EligibleTicker & { isSelected?: boolean };
                                // Safety check for required properties
                                if (!data.ticker) return null;
                                return (
                                  <div
                                    className="rounded-xl border p-3 shadow-sm max-w-xs"
                                    style={{ background: chartTheme.cardBackground, borderColor: chartTheme.border }}
                                  >
                                    <p className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                      {data.ticker}
                                    </p>
                                    {data.company_name && (
                                      <p className="text-sm mt-1" style={{ color: chartTheme.text.secondary }}>
                                        {data.company_name}
                                      </p>
                                    )}
                                    <div className="mt-2 space-y-1 text-sm" style={{ color: chartTheme.text.primary }}>
                                      <p>
                                        Return:{' '}
                                        <span className="font-medium">{formatPercent(data.expected_return)}</span>
                                      </p>
                                      <p>
                                        Risk:{' '}
                                        <span className="font-medium">{formatPercent(data.volatility)}</span>
                                      </p>
                                      {data.sector && (
                                        <p className="text-xs mt-1" style={{ color: chartTheme.text.secondary }}>
                                          Sector: {data.sector}
                                        </p>
                                      )}
                                      {data.isSelected && (
                                        <p className="text-xs mt-1 font-medium" style={{ color: '#2563eb' }}>
                                          ✓ In Your Portfolio
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Legend
                            wrapperStyle={{
                              paddingTop: 12,
                              fontSize: layoutConstants.legend.fontSize,
                              color: chartTheme.text.secondary,
                            }}
                          />
                          {/* All eligible tickers (gray dots) with jitter for overlapping points */}
                          <Scatter
                            name="Eligible Tickers"
                            data={eligibleTickersWithOffsets}
                            fill="#94a3b8"
                            fillOpacity={0.6}
                            shape={(props) => {
                              const radius = 3;
                              return (
                                <circle
                                  cx={props.cx}
                                  cy={props.cy}
                                  r={radius}
                                  fill="#94a3b8"
                                  fillOpacity={0.5}
                                  stroke="#64748b"
                                  strokeOpacity={0.6}
                                  strokeWidth={1}
                                />
                              );
                            }}
                          />
                          
                          {/* Selected portfolio tickers (highlighted with different colors per ticker) */}
                          {portfolioTickersDataWithOffsets.length > 0 && (
                            <Scatter
                              name="Your Portfolio"
                              data={portfolioTickersDataWithOffsets.filter(t => {
                                // Filter out zero/negative returns and values exceeding limits
                                // X-axis (Risk): max 110% (1.1), Y-axis (Return): max 100% (1.0), must be > 0
                                return t.volatility >= 0 && t.volatility <= 1.1 && 
                                       t.expected_return > 0 && t.expected_return <= 1.0;
                              })}
                              fill="#2563eb"
                              fillOpacity={0.85}
                              shape={(props) => {
                                // Color palette for portfolio tickers - distinct vibrant colors
                                const colorPalette = [
                                  { fill: '#2563eb', stroke: '#1e40af' }, // Blue
                                  { fill: '#dc2626', stroke: '#991b1b' }, // Red
                                  { fill: '#16a34a', stroke: '#15803d' }, // Green
                                  { fill: '#9333ea', stroke: '#7e22ce' }, // Purple
                                  { fill: '#ea580c', stroke: '#c2410c' }, // Orange
                                  { fill: '#0891b2', stroke: '#0e7490' }, // Cyan
                                ];
                                const dataIndex = props.index ?? 0;
                                const colors = colorPalette[dataIndex % colorPalette.length];
                                // Match eligible ticker size (radius 3) for consistent visual scaling
                                const radius = 3;
                                return (
                                  <circle
                                    cx={props.cx}
                                    cy={props.cy}
                                    r={radius}
                                    fill={colors.fill}
                                    fillOpacity={1.0}
                                    stroke={colors.stroke}
                                    strokeOpacity={1}
                                    strokeWidth={1.5}
                                  />
                                );
                              }}
                            />
                          )}
                          
                          {/* Box Zoom Selection Area - Standard Recharts ReferenceArea */}
                          {eligibleTickersSelectionBoxData && (
                              <ReferenceArea
                              x1={Math.min(eligibleTickersSelectionBoxData.start.x, eligibleTickersSelectionBoxData.end.x)}
                              x2={Math.max(eligibleTickersSelectionBoxData.start.x, eligibleTickersSelectionBoxData.end.x)}
                              y1={Math.max(0, Math.min(eligibleTickersSelectionBoxData.start.y, eligibleTickersSelectionBoxData.end.y))}
                              y2={Math.max(eligibleTickersSelectionBoxData.start.y, eligibleTickersSelectionBoxData.end.y)}
                                stroke="#2563eb"
                              strokeOpacity={0.6}
                                fill="#2563eb"
                              fillOpacity={0.15}
                                strokeWidth={2}
                              strokeDasharray="5 5"
                              />
                          )}
                          
                        </ScatterChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm" style={{ color: chartTheme.text.secondary }}>
                        <div className="text-center">
                          <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>No eligible tickers available</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                  
                  {/* Legend and Optimize Button */}
                  <div className="px-6 pb-6 space-y-4">
                    {/* Info: Always optimizes from market tickers */}
                    <div className="flex items-center justify-center gap-2 p-3 bg-blue-50/50 rounded-lg border border-blue-200">
                      <Info className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-blue-800">
                        Optimizes portfolio from eligible market tickers matching your risk profile
                      </span>
                    </div>
                    
                    <div className="flex justify-center pt-2">
                      <Button
                        onClick={runOptimization}
                        disabled={isLoading || !currentPortfolio || !Array.isArray(currentPortfolio) || currentPortfolio.length < 2}
                        size="lg"
                        className="flex items-center gap-2"
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Optimizing...
                          </>
                        ) : (
                          <>
                            <Zap className="h-4 w-4" />
                            Optimize
                          </>
                        )}
                      </Button>
                    </div>
                    
                    {(!currentPortfolio || currentPortfolio.length < 2) && (
                      <p className="text-sm text-center" style={{ color: chartTheme.text.secondary }}>
                        Select at least 2 stocks to enable optimization
                      </p>
                    )}
                    
                    {error && (
                      <Alert variant="destructive" className="mt-4">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    {successMessage && (
                      <Alert className="bg-green-50 border-green-200 text-green-800 mt-4">
                        <CheckCircle className="h-4 w-4" />
                        <AlertDescription>{successMessage}</AlertDescription>
                      </Alert>
                    )}
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Analysis Tab */}
            <TabsContent value="analysis" className="space-y-6">
              <div
                className="space-y-6"
                style={{
                  background: chartTheme.canvas,
                  padding: layoutConstants.spacing.cardPadding,
                  borderRadius: layoutConstants.radius,
                }}
              >
                <div>
                  <h3
                    className="text-lg font-semibold mb-1"
                    style={{ color: chartTheme.text.primary }}
                  >
                    Portfolio Analysis
                  </h3>
                  <p
                    className="text-sm"
                    style={{ color: chartTheme.text.secondary }}
                  >
                    Efficient frontier visualization with risk-return optimization results
                  </p>
                </div>

                <Card
                  className="w-full"
                  style={{ background: chartTheme.cardBackground, borderColor: chartTheme.border }}
                >
                  <CardHeader className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 text-center">
                      <CardTitle
                          className="text-lg"
                          style={{ color: chartTheme.text.primary, fontWeight: 600, letterSpacing: '-0.01em' }}
                      >
                        Efficient Frontier
                      </CardTitle>
                        <p className="text-xs mt-1" style={{ color: chartTheme.text.subtle }}>
                          Drag to zoom • Click legend to toggle series
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={zoomInEfficientFrontier}
                          className="h-7 w-7 p-0"
                          title="Zoom in (button)"
                          disabled={efficientFrontierZoomLevel >= 10}
                        >
                          <ZoomIn className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            if (efficientFrontierCurrentDomain) {
                              resetEfficientFrontierBoxZoom();
                            } else {
                              zoomOutEfficientFrontier();
                            }
                          }}
                          className="h-7 w-7 p-0"
                          title="Zoom out (button)"
                          disabled={efficientFrontierZoomLevel <= 1 && !efficientFrontierCurrentDomain}
                        >
                          <ZoomOut className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={efficientFrontierCurrentDomain ? resetEfficientFrontierBoxZoom : resetEfficientFrontierZoom}
                          className="h-7 px-2 text-xs"
                          title="Reset zoom"
                          disabled={efficientFrontierZoomLevel <= 1 && !efficientFrontierCurrentDomain}
                        >
                          <RotateCcw className="h-3.5 w-3.5 mr-1" />
                          Reset
                        </Button>
                      </div>
                    </div>
                    
                    {/* Interactive Legend with Visibility Toggles */}
                    <div className="flex flex-wrap gap-2 justify-center border-t pt-3" style={{ borderColor: chartTheme.border }}>
                      {/* Random Portfolios Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('randomPortfolios')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.randomPortfolios
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.randomPortfolios ? 'Hide Random Portfolios' : 'Show Random Portfolios'}
                      >
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#cbd5e1' }} />
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Random</span>
                      </button>
                      
                      {/* Efficient Frontier Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('efficientFrontier')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.efficientFrontier
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.efficientFrontier ? 'Hide Efficient Frontier' : 'Show Efficient Frontier'}
                      >
                        <div className="w-4 h-0.5" style={{ backgroundColor: '#64748b' }} />
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Efficient</span>
                      </button>
                      
                      {/* Inefficient Frontier Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('inefficientFrontier')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.inefficientFrontier
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.inefficientFrontier ? 'Hide Inefficient Frontier' : 'Show Inefficient Frontier'}
                      >
                        <div className="flex gap-0.5">
                          <div className="w-1.5 h-0.5" style={{ backgroundColor: '#64748b' }} />
                          <div className="w-1.5 h-0.5" style={{ backgroundColor: '#64748b' }} />
                        </div>
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Inefficient</span>
                      </button>
                      
                      {/* CML Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('cml')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.cml
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.cml ? 'Hide Capital Market Line' : 'Show Capital Market Line'}
                      >
                        <div className="flex gap-0.5">
                          <div className="w-1 h-0.5" style={{ backgroundColor: '#9333ea' }} />
                          <div className="w-1 h-0.5" style={{ backgroundColor: '#9333ea' }} />
                        </div>
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>CML</span>
                      </button>
                      
                      {/* Current Portfolio Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('currentPortfolio')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.currentPortfolio
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.currentPortfolio ? 'Hide Current Portfolio' : 'Show Current Portfolio'}
                      >
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#ef4444' }} />
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Current</span>
                      </button>
                      
                      {/* Weights-Optimized Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('weightsOptimized')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.weightsOptimized
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.weightsOptimized ? 'Hide Weights-Optimized' : 'Show Weights-Optimized'}
                      >
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#3b82f6' }} />
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Weights</span>
                      </button>
                      
                      {/* Market-Optimized Toggle */}
                      <button
                        onClick={() => toggleSeriesVisibility('marketOptimized')}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all ${
                          visibleSeries.marketOptimized
                            ? 'border-border bg-card hover:bg-accent text-foreground'
                            : 'border-border bg-muted/50 text-muted-foreground opacity-70'
                        }`}
                        title={visibleSeries.marketOptimized ? 'Hide Market-Optimized' : 'Show Market-Optimized'}
                      >
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#22c55e' }} />
                        <span className="font-medium" style={{ color: chartTheme.text.secondary }}>Market</span>
                      </button>
                    </div>
                  </CardHeader>
                  
                  {/* Risk Profile Zone Helper - Outside chart container */}
                  {mvoResults && (efficientFrontier.length > 0 || randomPortfolios.length > 0) && (() => {
                          // Risk limits based on volatility range upper bounds (standardized config)
                          const riskProfileMaxRisk: Record<string, number> = {
                      'very-conservative': 0.18,
                      'conservative': 0.25,
                      'moderate': 0.32,
                      'aggressive': 0.35,
                      'very-aggressive': 0.47
                          };
                    const maxRisk = riskProfileMaxRisk[riskProfile] || 0.32;
                          
                          return (
                            <div
                        className="mx-6 mb-2 rounded-lg p-3 border"
                              style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}
                            >
                        <div className="flex items-center gap-2 mb-1">
                                <Shield className="h-4 w-4" style={{ color: '#2563eb' }} />
                                <span className="text-sm font-medium" style={{ color: '#1e40af' }}>
                                  Optimized for {getRiskProfileDisplay(riskProfile)} investors
                                </span>
                              </div>
                              <p className="text-xs" style={{ color: '#1e3a8a' }}>
                                Risk profile constraint: Maximum risk {(maxRisk * 100).toFixed(0)}% | 
                                Optimized portfolio respects your risk tolerance
                              </p>
                            </div>
                          );
                        })()}
                        
                  <CardContent
                    className="min-h-[500px] h-[500px]"
                    style={{
                      background: chartTheme.canvas,
                      borderRadius: layoutConstants.radius,
                      padding: '12px',
                    }}
                  >
                    {mvoResults && (efficientFrontier.length > 0 || randomPortfolios.length > 0) ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart
                            margin={{ top: 24, right: 32, bottom: 64, left: 56 }}
                            onMouseDown={(e: any) => {
                              // Use activeCoordinate if available (when hovering over data), otherwise use chartX/chartY
                              if (e?.activeCoordinate) {
                                handleEfficientFrontierMouseDown(e);
                              } else if (e?.chartX !== undefined && e?.chartY !== undefined) {
                                handleEfficientFrontierMouseDown(e);
                              }
                            }}
                            onMouseMove={(e: any) => {
                              if (isEfficientFrontierSelecting) {
                                handleEfficientFrontierMouseMove(e);
                              }
                            }}
                            onMouseUp={(e: any) => {
                              handleEfficientFrontierMouseUp(e);
                            }}
                            onMouseLeave={() => {
                              if (isEfficientFrontierSelecting) {
                                setIsEfficientFrontierSelecting(false);
                                setEfficientFrontierSelectionBox(null);
                                setEfficientFrontierSelectionBoxData(null);
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
                              tickLine={{ stroke: 'transparent' }}
                              tick={{ fill: chartTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                              domain={
                                efficientFrontierCurrentDomain?.x 
                                  ? efficientFrontierCurrentDomain.x
                                  : efficientFrontierDomain?.x && efficientFrontierOriginalDomain?.y && efficientFrontierZoomLevel > 1
                                    ? [
                                        efficientFrontierDomain.x[0] + (efficientFrontierDomain.x[1] - efficientFrontierDomain.x[0]) * (1 - 1/efficientFrontierZoomLevel) / 2,
                                        efficientFrontierDomain.x[1] - (efficientFrontierDomain.x[1] - efficientFrontierDomain.x[0]) * (1 - 1/efficientFrontierZoomLevel) / 2
                                      ]
                                    : efficientFrontierDomain?.x || ['dataMin', 'dataMax']
                              }
                              allowDataOverflow={true}
                              label={{
                                value: 'Risk',
                                position: 'insideBottom',
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
                              tickLine={{ stroke: 'transparent' }}
                              tick={{ fill: chartTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                              allowDataOverflow={true}
                              domain={
                                efficientFrontierCurrentDomain?.y 
                                  ? efficientFrontierCurrentDomain.y
                                  : efficientFrontierDomain?.y && efficientFrontierOriginalDomain?.y && efficientFrontierZoomLevel > 1
                                    ? [
                                        efficientFrontierDomain.y[0] + (efficientFrontierDomain.y[1] - efficientFrontierDomain.y[0]) * (1 - 1/efficientFrontierZoomLevel) / 2,
                                        efficientFrontierDomain.y[1] - (efficientFrontierDomain.y[1] - efficientFrontierDomain.y[0]) * (1 - 1/efficientFrontierZoomLevel) / 2
                                      ]
                                    : efficientFrontierDomain?.y || ['auto', 'auto']  // Use 'auto' to show full data range
                              }
                              label={{
                                value: 'Return',
                                angle: -90,
                                position: 'left',
                                offset: 16,
                                style: { fill: chartTheme.axes.label, fontWeight: 500 },
                              }}
                            />
                            <RechartsTooltip
                              cursor={!isEfficientFrontierSelecting ? { strokeDasharray: '3 3' } : false}
                              content={({ active, payload }: TooltipProps<ValueType, NameType>) => {
                                // Don't show tooltip during selection
                                if (isEfficientFrontierSelecting) return null;
                                // Only show tooltip on hover (active must be true) - this is critical
                                if (!active) return null;
                                // Only show tooltip if we have valid payload with actual data
                                if (!payload || payload.length === 0) return null;
                                
                                // Only show tooltip for portfolio points (current, optimized), CML, or frontiers
                                const firstPayload = payload[0];
                                if (!firstPayload || !firstPayload.payload) return null;
                                const data = firstPayload.payload as EfficientFrontierPoint;
                                
                                // Check if this is CML by name (most reliable)
                                const isCML = firstPayload.name === 'Capital Market Line' || 
                                             (data as any)?.type === 'cml';
                                
                                // Check if this is Efficient Frontier
                                const isEfficientFrontier = firstPayload.name === 'Efficient Frontier' || 
                                                           data.type === 'frontier';
                                
                                // Check if this is Inefficient Frontier
                                const isInefficientFrontier = firstPayload.name === 'Inefficient Frontier' || 
                                                             data.type === 'inefficient_frontier';
                                
                                // Check if this is a portfolio point
                                const isPortfolioPoint = data.type === 'current' || data.type === 'optimized';
                                
                                // Only show tooltip for portfolio points, CML line, Efficient Frontier, or Inefficient Frontier
                                if (!isCML && !isPortfolioPoint && !isEfficientFrontier && !isInefficientFrontier) return null;
                                
                                // Prevent CML tooltip from showing when hovering over Efficient Frontier or Inefficient Frontier points
                                // Prioritize frontier tooltips over CML when they overlap
                                if (isCML && payload.length > 1) {
                                  const hasEfficientFrontier = payload.some(p => 
                                    p.name === 'Efficient Frontier' || (p.payload as any)?.type === 'frontier'
                                  );
                                  const hasInefficientFrontier = payload.some(p => 
                                    p.name === 'Inefficient Frontier' || (p.payload as any)?.type === 'inefficient_frontier'
                                  );
                                  if (hasEfficientFrontier || hasInefficientFrontier) {
                                    // Don't show CML tooltip when hovering over frontier lines
                                    return null;
                                  }
                                }
                                
                                // Prevent Efficient Frontier tooltip from showing when hovering over Inefficient Frontier
                                if (isEfficientFrontier && payload.length > 1) {
                                  const hasInefficientFrontier = payload.some(p => 
                                    p.name === 'Inefficient Frontier' || (p.payload as any)?.type === 'inefficient_frontier'
                                  );
                                  if (hasInefficientFrontier) {
                                    // Prioritize Inefficient Frontier when both are present
                                    return null;
                                  }
                                }
                                
                                if (isEfficientFrontier) {
                                  // Safety check for required properties
                                  if (data.return == null || data.risk == null || 
                                      typeof data.return !== 'number' || typeof data.risk !== 'number' ||
                                      !isFinite(data.return) || !isFinite(data.risk)) return null;
                                  
                                  return (
                                    <div
                                      className="rounded-lg border p-2 shadow-md max-w-xs"
                                      style={{ background: chartTheme.cardBackground, borderColor: '#64748b' }}
                                    >
                                      <p className="font-semibold text-sm" style={{ color: '#64748b' }}>
                                        Efficient Frontier
                                      </p>
                                      <p className="text-xs mt-1" style={{ color: chartTheme.text.secondary }}>
                                        Optimal portfolios offering maximum return for given risk levels.
                                      </p>
                                      <div className="mt-2 space-y-1 text-xs" style={{ color: chartTheme.text.primary }}>
                                        <p>
                                          Return:{' '}
                                          <span className="font-medium">{formatPercent(data.return)}</span>
                                        </p>
                                        <p>
                                          Risk:{' '}
                                          <span className="font-medium">{formatPercent(data.risk)}</span>
                                        </p>
                                        {data.sharpe_ratio != null && typeof data.sharpe_ratio === 'number' && isFinite(data.sharpe_ratio) && (
                                          <p>
                                            Sharpe:{' '}
                                            <span className="font-medium">{data.sharpe_ratio.toFixed(2)}</span>
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  );
                                }
                                
                                if (isCML) {
                                  return (
                                    <div
                                      className="rounded-lg border p-2 shadow-md max-w-xs"
                                      style={{ background: chartTheme.cardBackground, borderColor: '#9333ea' }}
                                    >
                                      <p className="font-semibold text-sm" style={{ color: '#9333ea' }}>
                                        Capital Market Line (CML)
                                      </p>
                                      <p className="text-xs mt-1" style={{ color: chartTheme.text.secondary }}>
                                        Optimal risk-return combinations combining risk-free assets with the market portfolio.
                                      </p>
                                    </div>
                                  );
                                }
                                
                                if (isInefficientFrontier) {
                                  // Safety check for required properties
                                  if (data.return == null || data.risk == null || 
                                      typeof data.return !== 'number' || typeof data.risk !== 'number' ||
                                      !isFinite(data.return) || !isFinite(data.risk)) return null;
                                  
                                  return (
                                    <div
                                      className="rounded-lg border p-2 shadow-md max-w-xs"
                                      style={{ background: chartTheme.cardBackground, borderColor: '#94a3b8' }}
                                    >
                                      <p className="font-semibold text-sm" style={{ color: '#94a3b8' }}>
                                        Inefficient Frontier
                                      </p>
                                      <p className="text-xs mt-1" style={{ color: chartTheme.text.secondary }}>
                                        Portfolios with minimum return for given risk levels (lower branch of the hyperbola).
                                      </p>
                                      <div className="mt-2 space-y-1 text-xs" style={{ color: chartTheme.text.primary }}>
                                        <p>
                                          Return:{' '}
                                          <span className="font-medium">{formatPercent(data.return)}</span>
                                        </p>
                                        <p>
                                          Risk:{' '}
                                          <span className="font-medium">{formatPercent(data.risk)}</span>
                                        </p>
                                      </div>
                                    </div>
                                  );
                                }
                                
                                // Safety check for required properties - must have valid numeric values
                                if (data.return == null || data.risk == null || 
                                    typeof data.return !== 'number' || typeof data.risk !== 'number' ||
                                    !isFinite(data.return) || !isFinite(data.risk)) return null;
                                
                                // Get current portfolio metrics for comparison
                                const currentPortfolioMetrics = tripleOptimizationResults?.current_portfolio?.metrics;
                                const showComparison = data.type !== 'current' && data.type !== 'random' && currentPortfolioMetrics;
                                
                                return (
                                  <div
                                    className="rounded-xl border p-3 shadow-lg max-w-xs"
                                    style={{ background: chartTheme.cardBackground, borderColor: chartTheme.border }}
                                  >
                                    <p className="font-bold text-sm pb-2 mb-2 border-b" style={{ color: chartTheme.text.primary, borderColor: chartTheme.border }}>
                                      {data.type === 'current' ? 'Current Portfolio' :
                                       data.type === 'weights_optimized' ? 'Weights-Optimized Portfolio' :
                                       data.type === 'market_optimized' ? 'Market-Optimized Portfolio' :
                                       data.type === 'optimized' ? 'Optimized Portfolio' :
                                       data.type === 'frontier' ? 'Efficient Frontier' :
                                       'Random Portfolio'}
                                    </p>
                                    <div className="space-y-1.5 text-xs">
                                      <div className="flex justify-between">
                                        <span style={{ color: chartTheme.text.secondary }}>Return (μ):</span>
                                        <span className="font-semibold" style={{ color: chartTheme.text.primary }}>{formatPercent(data.return)}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span style={{ color: chartTheme.text.secondary }}>Risk (σ):</span>
                                        <span className="font-semibold" style={{ color: chartTheme.text.primary }}>{formatPercent(data.risk)}</span>
                                      </div>
                                      {data.sharpe_ratio != null && typeof data.sharpe_ratio === 'number' && isFinite(data.sharpe_ratio) && (
                                        <div className="flex justify-between">
                                          <span style={{ color: chartTheme.text.secondary }}>Sharpe Ratio:</span>
                                          <span className="font-semibold" style={{ color: chartTheme.text.primary }}>{data.sharpe_ratio.toFixed(3)}</span>
                                        </div>
                                      )}
                                    </div>
                                    
                                    {/* Comparison to current portfolio */}
                                    {showComparison && currentPortfolioMetrics && (
                                      <div className="mt-3 pt-2 border-t" style={{ borderColor: chartTheme.border }}>
                                        <div className="text-xs font-semibold mb-1.5" style={{ color: chartTheme.text.secondary }}>vs Current Portfolio:</div>
                                        <div className="space-y-1 text-xs">
                                          <div className="flex justify-between">
                                            <span style={{ color: chartTheme.text.secondary }}>Δ Return:</span>
                                            <span className={`font-semibold ${data.return > currentPortfolioMetrics.expected_return ? 'text-green-600' : 'text-red-600'}`}>
                                              {data.return > currentPortfolioMetrics.expected_return ? '+' : ''}{formatPercent(data.return - currentPortfolioMetrics.expected_return)}
                                            </span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span style={{ color: chartTheme.text.secondary }}>Δ Risk:</span>
                                            <span className={`font-semibold ${data.risk < currentPortfolioMetrics.risk ? 'text-green-600' : 'text-red-600'}`}>
                                              {data.risk < currentPortfolioMetrics.risk ? '' : '+'}{formatPercent(data.risk - currentPortfolioMetrics.risk)}
                                            </span>
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              }}
                            />
                            {/* Random Portfolios (background scatter) - Same size as Stock Universe */}
                            {visibleSeries.randomPortfolios && randomPortfolios.length > 0 && (
                              <Scatter
                                name="Random Portfolios"
                                data={randomPortfolios}
                                fill="#cbd5e1"
                                fillOpacity={0.3}
                                shape={(props) => {
                                  const radius = 3; // Same size as Stock Universe
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={radius}
                                      fill="#cbd5e1"
                                      fillOpacity={0.3}
                                      stroke="#94a3b8"
                                      strokeOpacity={0.2}
                                      strokeWidth={0.5}
                                    />
                                  );
                                }}
                              />
                            )}
                            
                            {/* Efficient Frontier (line/curve) - Displayed as smooth line showing full curve from min variance to max return */}
                            {visibleSeries.efficientFrontier && efficientFrontier.length > 0 && (() => {
                              // Sort efficient frontier by risk to ensure proper curve display
                              const sortedFrontier = [...efficientFrontier].sort((a, b) => {
                                const riskA = a.risk ?? 0;
                                const riskB = b.risk ?? 0;
                                return riskA - riskB;
                              }).filter(p => 
                                p.risk != null && 
                                typeof p.risk === 'number' && 
                                isFinite(p.risk) &&
                                p.return != null &&
                                typeof p.return === 'number' &&
                                isFinite(p.return)
                              );
                              
                              // Show full efficient frontier - domain already calculated to include all points
                              // No filtering needed as domain calculation includes inefficient frontier and all points
                              return sortedFrontier.length > 0 ? (
                                <Line
                                  name="Efficient Frontier"
                                  type="monotone"
                                  dataKey="return"
                                  data={sortedFrontier}
                                  stroke="#64748b"
                                  strokeWidth={2.5}
                                  dot={false}
                                  activeDot={{ r: 4, fill: '#64748b', stroke: '#fff', strokeWidth: 2 }}
                                  isAnimationActive={true}
                                  animationDuration={1500}
                                  animationEasing="ease-out"
                                  connectNulls={true}
                                  xAxisId={0}
                                  yAxisId={0}
                                />
                              ) : null;
                            })()}
                            
                            {/* 
                              Inefficient Frontier (lower part of hyperbola) - Displayed as dashed line
                              
                              Why it exists: The inefficient frontier represents portfolios with MINIMUM return 
                              for given risk levels (the lower part of the hyperbola). It extends beyond the 
                              global minimum variance point to show the complete mathematical structure of the 
                              optimization space. This dashed line provides visual contrast to highlight the 
                              efficient frontier (optimal portfolios) and helps users understand that portfolios 
                              below the efficient frontier are suboptimal.
                              
                              Mathematical background: In Mean-Variance Optimization, the solution forms a 
                              hyperbola. The efficient frontier is the upper branch (max return for given risk), 
                              while the inefficient frontier is the lower branch (min return for given risk). 
                              Both branches meet at the global minimum variance portfolio.
                            */}
                            {/* Inefficient Frontier - Render before Efficient Frontier so it appears behind */}
                            {visibleSeries.inefficientFrontier && inefficientFrontier.length > 0 && (() => {
                              // Sort inefficient frontier by risk
                              const sortedInefficient = [...inefficientFrontier].sort((a, b) => {
                                const riskA = a.risk ?? 0;
                                const riskB = b.risk ?? 0;
                                return riskA - riskB;
                              }).filter(p => 
                                p.risk != null && 
                                typeof p.risk === 'number' && 
                                isFinite(p.risk) &&
                                p.return != null &&
                                typeof p.return === 'number' &&
                                isFinite(p.return)
                              );
                              
                              // Show full inefficient frontier - domain already calculated to include all points
                              return sortedInefficient.length > 0 ? (
                                <Line
                                  name="Inefficient Frontier"
                                  type="monotone"
                                  dataKey="return"
                                  data={sortedInefficient.map((point) => ({
                                    ...point,
                                    type: 'inefficient_frontier' as const
                                  }))}
                                  stroke="#64748b"
                                  strokeWidth={2.5}
                                  strokeDasharray="6 4"
                                  strokeOpacity={0.7}
                                  dot={false}
                                  activeDot={{ r: 6, fill: '#64748b', stroke: '#fff', strokeWidth: 2 }}
                                  isAnimationActive={true}
                                  animationDuration={1500}
                                  animationEasing="ease-out"
                                  connectNulls={true}
                                  xAxisId={0}
                                  yAxisId={0}
                                />
                              ) : null;
                            })()}
                            
                            {/* Capital Market Line (CML) - From optimized portfolio's efficient frontier */}
                            {visibleSeries.cml && mvoResults.capital_market_line && mvoResults.capital_market_line.length > 0 && (
                              <>
                                <Line
                                  name="Capital Market Line"
                                  type="monotone"
                                  dataKey="return"
                                  data={mvoResults.capital_market_line.map((point: any) => ({
                                    ...point,
                                    type: 'cml' as const
                                  }))}
                                  stroke="#9333ea"
                                  strokeWidth={2.5}
                                  strokeDasharray="5 5"
                                  dot={false}
                                  activeDot={false}
                                  isAnimationActive={true}
                                  animationDuration={1500}
                                  animationEasing="ease-out"
                                  connectNulls={true}
                                  xAxisId={0}
                                  yAxisId={0}
                                />
                                {/* Risk-Free Rate Point (Rf) - Starting point of CML */}
                                <ReferenceDot
                                  x={0}
                                  y={mvoResults?.metadata?.risk_free_rate ?? 0.038}
                                  r={5}
                                  fill="#9333ea"
                                  stroke="#fff"
                                  strokeWidth={2}
                                  xAxisId={0}
                                  yAxisId={0}
                                >
                                  <Label
                                    value="Rf"
                                    position="right"
                                    offset={8}
                                    style={{ fontSize: 11, fontWeight: 600, fill: '#9333ea' }}
                                  />
                                </ReferenceDot>
                              </>
                            )}
                            
                            {/* Current Portfolio - RED circle */}
                            {visibleSeries.currentPortfolio && tripleOptimizationResults?.current_portfolio?.metrics && (
                              <Scatter
                                name="Current Portfolio"
                                data={[{
                                  risk: tripleOptimizationResults.current_portfolio.metrics.risk,
                                  return: tripleOptimizationResults.current_portfolio.metrics.expected_return,
                                  sharpe_ratio: tripleOptimizationResults.current_portfolio.metrics.sharpe_ratio,
                                  type: 'current' as const
                                }]}
                                fill="#ef4444"
                                fillOpacity={1}
                                shape={(props) => {
                                  // Large red circle with white ring for maximum visibility
                                  return (
                                    <g>
                                      {/* Outer glow effect */}
                                      <circle cx={props.cx} cy={props.cy} r={14} fill="#ef4444" fillOpacity={0.2} />
                                      {/* Main circle */}
                                      <circle cx={props.cx} cy={props.cy} r={10} fill="#ef4444" stroke="#fff" strokeWidth={3} />
                                      {/* Inner dot */}
                                      <circle cx={props.cx} cy={props.cy} r={4} fill="#fff" />
                                    </g>
                                  );
                                }}
                              />
                            )}
                            
                            {/* Weights-Optimized Portfolio - BLUE diamond shape */}
                            {visibleSeries.weightsOptimized && portfolioPointsWithJitter.find(p => p.type === 'weights_optimized') && (
                              <Scatter
                                name="Weights-Optimized Portfolio"
                                data={[portfolioPointsWithJitter.find(p => p.type === 'weights_optimized')!]}
                                fill="#3b82f6"
                                fillOpacity={1}
                                shape={(props) => {
                                  // Blue diamond (rotated square)
                                  const size = 10;
                                  return (
                                    <g>
                                      {/* Outer glow */}
                                      <circle cx={props.cx} cy={props.cy} r={14} fill="#3b82f6" fillOpacity={0.2} />
                                      {/* Diamond shape */}
                                      <polygon
                                        points={[
                                          `${props.cx},${props.cy - size}`,
                                          `${props.cx + size},${props.cy}`,
                                          `${props.cx},${props.cy + size}`,
                                          `${props.cx - size},${props.cy}`
                                        ].join(' ')}
                                        fill="#3b82f6"
                                        stroke="#fff"
                                        strokeWidth={2}
                                      />
                                    </g>
                                  );
                                }}
                              />
                            )}
                            
                            {/* Market-Optimized Portfolio - GREEN star shape */}
                            {visibleSeries.marketOptimized && portfolioPointsWithJitter.find(p => p.type === 'market_optimized') && (
                              <Scatter
                                name="Market-Optimized Portfolio"
                                data={[portfolioPointsWithJitter.find(p => p.type === 'market_optimized')!]}
                                fill="#22c55e"
                                fillOpacity={1}
                                shape={(props) => {
                                  // 5-point star in green for market-optimized portfolio
                                  const outerR = 12;
                                  const innerR = 5;
                                  const points = [];
                                  for (let i = 0; i < 10; i++) {
                                    const r = i % 2 === 0 ? outerR : innerR;
                                    const angle = (i * 36 - 90) * Math.PI / 180;
                                    points.push(`${props.cx + r * Math.cos(angle)},${props.cy + r * Math.sin(angle)}`);
                                  }
                                  return (
                                    <g>
                                      {/* Outer glow */}
                                      <circle cx={props.cx} cy={props.cy} r={16} fill="#22c55e" fillOpacity={0.2} />
                                      {/* Star shape */}
                                      <polygon
                                        points={points.join(' ')}
                                        fill="#22c55e"
                                        stroke="#fff"
                                        strokeWidth={2}
                                      />
                                    </g>
                                  );
                                }}
                              />
                            )}
                            
                            {/* Legacy: Optimized Portfolio (for backward compatibility) */}
                            {!tripleOptimizationResults && portfolioPointsWithJitter.find(p => p.type === 'optimized') && (
                              <Scatter
                                name="Optimized Portfolio"
                                data={[portfolioPointsWithJitter.find(p => p.type === 'optimized')!]}
                                fill="#22c55e"
                                fillOpacity={1}
                                shape={(props) => {
                                  const outerR = 12;
                                  const innerR = 5;
                                  const points = [];
                                  for (let i = 0; i < 10; i++) {
                                    const r = i % 2 === 0 ? outerR : innerR;
                                    const angle = (i * 36 - 90) * Math.PI / 180;
                                    points.push(`${props.cx + r * Math.cos(angle)},${props.cy + r * Math.sin(angle)}`);
                                  }
                                  return (
                                    <g>
                                      <circle cx={props.cx} cy={props.cy} r={16} fill="#22c55e" fillOpacity={0.2} />
                                      <polygon
                                        points={points.join(' ')}
                                        fill="#22c55e"
                                        stroke="#fff"
                                        strokeWidth={2}
                                      />
                                    </g>
                                  );
                                }}
                              />
                            )}
                            
                            {/* Box Zoom Selection Area - Standard Recharts ReferenceArea */}
                            {efficientFrontierSelectionBoxData && (
                                <ReferenceArea
                                x1={Math.min(efficientFrontierSelectionBoxData.start.x, efficientFrontierSelectionBoxData.end.x)}
                                x2={Math.max(efficientFrontierSelectionBoxData.start.x, efficientFrontierSelectionBoxData.end.x)}
                                y1={Math.min(efficientFrontierSelectionBoxData.start.y, efficientFrontierSelectionBoxData.end.y)}
                                y2={Math.max(efficientFrontierSelectionBoxData.start.y, efficientFrontierSelectionBoxData.end.y)}
                                  stroke="#2563eb"
                                strokeOpacity={0.6}
                                  fill="#2563eb"
                                fillOpacity={0.15}
                                  strokeWidth={2}
                                strokeDasharray="5 5"
                                />
                            )}
                            
                          </ComposedChart>
                        </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm" style={{ color: chartTheme.text.secondary }}>
                        <div className="text-center">
                          <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>Run portfolio optimization to generate efficient frontier analysis.</p>
                          <p className="text-xs mt-2">Click the "Optimize" button in the Optimization tab to get started.</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                    
                  {/* Legend and Results Summary - Outside CardContent */}
                    {mvoResults && (efficientFrontier.length > 0 || randomPortfolios.length > 0) ? (
                      <div className="px-6 pb-6 space-y-4">
                      {/* Chart Legend */}
                      <div className="flex flex-wrap gap-4 text-xs justify-center pt-2">
                        {randomPortfolios.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#cbd5e1' }}></div>
                            <span style={{ color: chartTheme.text.secondary }}>
                              Random Portfolios ({randomPortfolios.length})
                            </span>
                          </div>
                        )}
                        {mvoResults.capital_market_line && mvoResults.capital_market_line.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-0.5" style={{ background: '#9333ea', borderTop: '2px dashed #9333ea' }}></div>
                            <span style={{ color: chartTheme.text.secondary }}>Capital Market Line (CML)</span>
                          </div>
                        )}
                        {efficientFrontier.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-slate-500"></div>
                            <span style={{ color: chartTheme.text.secondary }}>
                              Efficient Frontier
                            </span>
                          </div>
                        )}
                        {tripleOptimizationResults ? (
                          <>
                            <div className="flex items-center gap-2">
                              <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow"></div>
                              <span style={{ color: chartTheme.text.secondary }}>Current Portfolio</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rotate-45" style={{ width: '12px', height: '12px', backgroundColor: '#3b82f6', border: '2px solid white' }}></div>
                              <span style={{ color: chartTheme.text.secondary }}>Weights-Optimized</span>
                            </div>
                            {tripleOptimizationResults.market_optimized_portfolio && (
                              <div className="flex items-center gap-2">
                                <svg width="14" height="14" viewBox="0 0 16 16">
                                  <polygon points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6" fill="#22c55e" stroke="#fff" strokeWidth="0.5"/>
                                </svg>
                                <span style={{ color: chartTheme.text.secondary }}>Market-Optimized</span>
                              </div>
                            )}
                          </>
                        ) : (
                          <>
                            {mvoResults.current_portfolio && (
                              <div className="flex items-center gap-2">
                                <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow"></div>
                                <span style={{ color: chartTheme.text.secondary }}>Current Portfolio</span>
                              </div>
                            )}
                            {mvoResults.optimized_portfolio && (
                              <div className="flex items-center gap-2">
                                <div className="w-4 h-4 rotate-45 bg-amber-500 border-2 border-white shadow"></div>
                                <span style={{ color: chartTheme.text.secondary }}>Optimized Portfolio</span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                      
                      {/* Portfolio Comparison Table - Three Columns */}
                      {tripleOptimizationResults ? (
                        <div className="mt-6 pt-6" style={{ borderTop: `1px solid ${chartTheme.border}` }}>
                          <h5 className="font-semibold text-center mb-4" style={{ color: chartTheme.text.primary }}>
                            Portfolio Comparison
                          </h5>
                          
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm border-collapse">
                              <thead>
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <th className="text-left py-3 px-2 font-medium" style={{ color: chartTheme.text.secondary }}>Metric</th>
                                  <th className="text-center py-3 px-2" style={{ 
                                    borderLeft: tripleOptimizationResults.optimization_metadata?.recommendation === 'current' ? '3px solid #ef4444' : '1px solid ' + chartTheme.border
                                  }}>
                                    <div className="flex flex-col items-center gap-1">
                                      <div className="w-3 h-3 rounded-full bg-red-500 border border-white shadow-sm"></div>
                                      <span className="font-medium text-sm" style={{ color: chartTheme.text.primary }}>Current</span>
                                      {tripleOptimizationResults.optimization_metadata?.recommendation === 'current' && (
                                        <span className="text-xs font-medium" style={{ color: '#ef4444' }}>Recommended</span>
                                      )}
                                    </div>
                                  </th>
                                  <th className="text-center py-3 px-2" style={{ 
                                    borderLeft: tripleOptimizationResults.optimization_metadata?.recommendation === 'weights' ? '3px solid #3b82f6' : '1px solid ' + chartTheme.border
                                  }}>
                                    <div className="flex flex-col items-center gap-1">
                                      <div className="w-3 h-3 rotate-45" style={{ width: '12px', height: '12px', backgroundColor: '#3b82f6', border: '2px solid white' }}></div>
                                      <span className="font-medium text-sm" style={{ color: chartTheme.text.primary }}>Weights-Opt</span>
                                      {tripleOptimizationResults.optimization_metadata?.recommendation === 'weights' && (
                                        <span className="text-xs font-medium" style={{ color: '#3b82f6' }}>Recommended</span>
                                      )}
                                    </div>
                                  </th>
                                  {/* Market-Opt column - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <th className="text-center py-3 px-2" style={{ 
                                      borderLeft: tripleOptimizationResults.optimization_metadata?.recommendation === 'market' ? '3px solid #22c55e' : '1px solid ' + chartTheme.border
                                    }}>
                                      <div className="flex flex-col items-center gap-1">
                                        <svg width="14" height="14" viewBox="0 0 16 16">
                                          <polygon points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6" fill="#22c55e" stroke="#fff" strokeWidth="0.5"/>
                                        </svg>
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <span className="font-medium text-sm cursor-help" style={{ color: chartTheme.text.primary }}>Market-Opt</span>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p className="max-w-xs">Explores the entire market to find the best stocks and allocations, potentially replacing some of your current holdings for better risk-adjusted returns.</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                        {tripleOptimizationResults.optimization_metadata?.recommendation === 'market' && (
                                          <span className="text-xs font-medium" style={{ color: '#22c55e' }}>Recommended</span>
                                        )}
                                      </div>
                                    </th>
                                  )}
                                </tr>
                              </thead>
                              <tbody>
                                {/* Expected Return Row */}
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Expected Return
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                      {(tripleOptimizationResults.current_portfolio.metrics.expected_return * 100).toFixed(1)}%
                                    </span>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <div>
                                      <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                        {(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return * 100).toFixed(1)}%
                                      </span>
                                      {tripleOptimizationResults.comparison?.weights_vs_current && (
                                        <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.return_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                          ({tripleOptimizationResults.comparison.weights_vs_current.return_difference >= 0 ? '+' : ''}{(tripleOptimizationResults.comparison.weights_vs_current.return_difference * 100).toFixed(1)}%)
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                          {(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.expected_return * 100).toFixed(1)}%
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.return_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.return_difference >= 0 ? '+' : ''}{(tripleOptimizationResults.comparison.market_vs_current.return_difference * 100).toFixed(1)}%)
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  )}
                                </tr>
                                {/* Risk Row */}
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Risk (Volatility)
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                      {(tripleOptimizationResults.current_portfolio.metrics.risk * 100).toFixed(1)}%
                                    </span>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <div>
                                      <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                        {(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.risk * 100).toFixed(1)}%
                                      </span>
                                      {tripleOptimizationResults.comparison?.weights_vs_current && (
                                        <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.risk_difference <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                          ({tripleOptimizationResults.comparison.weights_vs_current.risk_difference <= 0 ? '' : '+'}{(tripleOptimizationResults.comparison.weights_vs_current.risk_difference * 100).toFixed(1)}%)
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                          {(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.risk * 100).toFixed(1)}%
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.risk_difference <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.risk_difference <= 0 ? '' : '+'}{(tripleOptimizationResults.comparison.market_vs_current.risk_difference * 100).toFixed(1)}%)
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  )}
                                </tr>
                                {/* Sharpe Ratio Row */}
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Sharpe Ratio
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                      {tripleOptimizationResults.current_portfolio.metrics.sharpe_ratio.toFixed(2)}
                                    </span>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <div>
                                      <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                        {tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio.toFixed(2)}
                                      </span>
                                      {tripleOptimizationResults.comparison?.weights_vs_current && (
                                        <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                          ({tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference >= 0 ? '+' : ''}{tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference.toFixed(2)})
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: chartTheme.text.primary }}>
                                          {tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio.toFixed(2)}
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.sharpe_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.sharpe_difference >= 0 ? '+' : ''}{tripleOptimizationResults.comparison.market_vs_current.sharpe_difference.toFixed(2)})
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  )}
                                </tr>
                                {/* Tickers Row */}
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Tickers
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                      {tripleOptimizationResults.current_portfolio.tickers.join(', ') || 'N/A'}
                                    </span>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                      {tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.tickers.join(', ') || 'N/A'}
                                    </span>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                        {tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.tickers.slice(0, 5).join(', ')}
                                        {(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.tickers.length > 5) && '...'}
                                      </span>
                                    </td>
                                  )}
                                </tr>
                                {/* Top 3 Weights Row */}
                                <tr className="border-b" style={{ borderColor: chartTheme.border }}>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Top 3 Weights
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                      {Object.entries(tripleOptimizationResults.current_portfolio.weights || {})
                                        .sort(([,a], [,b]) => (b as number) - (a as number))
                                        .slice(0, 3)
                                        .map(([ticker, weight]) => `${ticker}: ${((weight as number) * 100).toFixed(0)}%`)
                                        .join(', ') || 'Equal'}
                                    </span>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                      {Object.entries(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.weights || {})
                                        .sort(([,a], [,b]) => (b as number) - (a as number))
                                        .slice(0, 3)
                                        .map(([ticker, weight]) => `${ticker}: ${((weight as number) * 100).toFixed(0)}%`)
                                        .join(', ') || 'N/A'}
                                    </span>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <span className="text-xs" style={{ color: chartTheme.text.secondary }}>
                                        {Object.entries(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.weights || {})
                                          .sort(([,a], [,b]) => (b as number) - (a as number))
                                          .slice(0, 3)
                                          .map(([ticker, weight]) => `${ticker}: ${((weight as number) * 100).toFixed(0)}%`)
                                          .join(', ') || 'N/A'}
                                      </span>
                                    </td>
                                  )}
                                </tr>
                                {/* Key Strengths Row */}
                                <tr>
                                  <td className="py-3 px-2 font-medium" style={{ color: chartTheme.text.primary }}>
                                    Key Strengths
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <div className="text-xs space-y-1" style={{ color: chartTheme.text.secondary }}>
                                      <div>• Your actual holdings</div>
                                      <div>• Familiar stocks</div>
                                    </div>
                                  </td>
                                  <td className="text-center py-3 px-2">
                                    <div className="text-xs space-y-1" style={{ color: chartTheme.text.secondary }}>
                                      {tripleOptimizationResults.comparison.weights_vs_current.risk_difference < 0 && (
                                        <div>• Lower risk</div>
                                      )}
                                      {tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference > 0 && (
                                        <div>• Better Sharpe</div>
                                      )}
                                      <div>• Same tickers</div>
                                      <div>• Easy transition</div>
                                    </div>
                                  </td>
                                  {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
                                  {tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div className="text-xs space-y-1" style={{ color: chartTheme.text.secondary }}>
                                        {tripleOptimizationResults.comparison.market_vs_current && tripleOptimizationResults.comparison.market_vs_current.return_difference > 0 && (
                                          <div>• Higher return</div>
                                        )}
                                        {tripleOptimizationResults.comparison.best_sharpe === 'market' && (
                                          <div>• Best Sharpe</div>
                                        )}
                                        <div>• Market diversity</div>
                                        <div>• New opportunities</div>
                                      </div>
                                    </td>
                                  )}
                                </tr>
                                {/* Selection Buttons Row - Dynamic based on market_optimized_portfolio */}
                                <tr>
                                  <td colSpan={tripleOptimizationResults.market_optimized_portfolio ? 4 : 3} className="py-4 px-2">
                                    <div className={`grid gap-3 ${tripleOptimizationResults.market_optimized_portfolio ? 'grid-cols-3' : 'grid-cols-2'}`}>
                                      <Button
                                        variant={selectedPortfolio === 'current' ? 'default' : 'outline'}
                                        onClick={() => setSelectedPortfolio('current')}
                                        className={`w-full text-sm ${selectedPortfolio === 'current' ? 'bg-red-600 hover:bg-red-700 text-white border-red-600' : 'border-border bg-card'}`}
                                      >
                                        {selectedPortfolio === 'current' ? 'Selected' : 'Select Current'}
                                      </Button>
                                      <Button
                                        variant={selectedPortfolio === 'weights' ? 'default' : 'outline'}
                                        onClick={() => setSelectedPortfolio('weights')}
                                        className={`w-full text-sm ${selectedPortfolio === 'weights' ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-600' : 'border-border bg-card'}`}
                                      >
                                        {selectedPortfolio === 'weights' ? 'Selected' : 'Select Weights-Opt'}
                                      </Button>
                                      {/* Market-Opt button - only show if market_optimized_portfolio exists */}
                                      {tripleOptimizationResults.market_optimized_portfolio && (
                                        <Button
                                          variant={selectedPortfolio === 'market' ? 'default' : 'outline'}
                                          onClick={() => setSelectedPortfolio('market')}
                                          className={`w-full text-sm ${selectedPortfolio === 'market' ? 'bg-green-600 hover:bg-green-700 text-white border-green-600' : 'border-border bg-card'}`}
                                        >
                                          {selectedPortfolio === 'market' ? 'Selected' : 'Select Market-Opt'}
                                        </Button>
                                      )}
                                    </div>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ) : mvoResults?.optimized_portfolio ? (
                        // Fallback to old two-column table for backward compatibility
                        <div className="mt-6 pt-6" style={{ borderTop: `1px solid ${chartTheme.border}` }}>
                          <h5 className="font-semibold text-center mb-4" style={{ color: chartTheme.text.primary }}>
                            Portfolio Comparison
                          </h5>
                          
                          {/* Data Quality Warning */}
                          {dualOptimizationResults?.comparison?.current_metrics_unreliable && (
                            <div className="mb-4 p-3 rounded-lg bg-muted border border-border">
                              <div className="flex items-start gap-2">
                                <svg className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <div className="flex-1">
                                  <div className="font-semibold text-amber-800 mb-1">Data Quality Notice</div>
                                  <div className="text-sm text-amber-700 space-y-1">
                                    {dualOptimizationResults.comparison.reliability_reasons?.map((reason: string, idx: number) => (
                                      <div key={idx}>• {reason}</div>
                                    ))}
                                    {dualOptimizationResults.comparison.comparison_notes?.map((note: string, idx: number) => (
                                      <div key={idx} className="mt-2 text-xs italic">{note}</div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {/* Interpretation Guide */}
                          {dualOptimizationResults?.comparison && (
                            <div className="mt-4 p-3 rounded-lg bg-muted border border-border">
                              <div className="text-xs space-y-2" style={{ color: chartTheme.text.secondary }}>
                                <div className="font-semibold mb-2" style={{ color: chartTheme.text.primary }}>Understanding This Comparison:</div>
                                <div>• <strong>Expected Return:</strong> Annualized return based on historical data. Higher is generally better, but unrealistic values (&gt;50%) may indicate data quality issues.</div>
                                <div>• <strong>Risk (Volatility):</strong> Standard deviation of returns. Lower is generally better for the same return level.</div>
                                <div>• <strong>Sharpe Ratio:</strong> Risk-adjusted return. Values &gt;1 are good, &gt;2 are excellent, &gt;3 are rare. If current portfolio shows &gt;3, metrics may be unreliable.</div>
                                {dualOptimizationResults.comparison.current_metrics_unreliable && (
                                  <div className="mt-2 pt-2 border-t border-slate-300">
                                    <div className="font-semibold text-amber-700">⚠️ Current portfolio metrics appear unreliable.</div>
                                    <div className="mt-1">The optimized portfolio uses validated tickers with sufficient historical data and provides a more realistic risk-return profile.</div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          
                          {/* Sharpe Ratio Insight Box */}
                          {dualOptimizationResults?.comparison && (
                            <div className="mt-4 p-3 rounded-lg bg-muted border border-border">
                              {(() => {
                                const currentSharpe = dualOptimizationResults.current_portfolio?.metrics?.sharpe_ratio ?? 0;
                                const optimizedSharpe = mvoResults.optimized_portfolio.metrics?.sharpe_ratio ?? 0;
                                const sharpeDiff = optimizedSharpe - currentSharpe;
                                
                                const getSharpeLevel = (s: number) => {
                                  if (s < 0) return { label: 'Poor', color: 'text-red-600', bg: 'bg-red-100' };
                                  if (s < 0.5) return { label: 'Below Avg', color: 'text-orange-600', bg: 'bg-orange-100' };
                                  if (s < 1.0) return { label: 'Good', color: 'text-blue-600', bg: 'bg-blue-100' };
                                  if (s < 2.0) return { label: 'Very Good', color: 'text-green-600', bg: 'bg-green-100' };
                                  return { label: 'Excellent', color: 'text-purple-600', bg: 'bg-purple-100' };
                                };
                                
                                const currentLevel = getSharpeLevel(currentSharpe);
                                const optimizedLevel = getSharpeLevel(optimizedSharpe);
                                
                                return (
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                      <span className="text-xs font-medium text-gray-600">Sharpe Ratio (Risk-Adjusted Return)</span>
                                      <span className="text-xs text-gray-500">Higher = Better</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <div className="flex-1 flex items-center justify-between px-2 py-1.5 rounded border border-red-200 bg-red-50">
                                        <span className="text-xs text-red-700">Current</span>
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-bold text-red-800">{currentSharpe.toFixed(2)}</span>
                                          <span className={`text-xs px-1.5 py-0.5 rounded ${currentLevel.bg} ${currentLevel.color}`}>{currentLevel.label}</span>
                                        </div>
                                      </div>
                                      <div className="flex-1 flex items-center justify-between px-2 py-1.5 rounded border border-green-200 bg-green-50">
                                        <span className="text-xs text-green-700">Optimized</span>
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-bold text-green-800">{optimizedSharpe.toFixed(2)}</span>
                                          <span className={`text-xs px-1.5 py-0.5 rounded ${optimizedLevel.bg} ${optimizedLevel.color}`}>{optimizedLevel.label}</span>
                                        </div>
                                      </div>
                                    </div>
                                    <p className="text-xs text-gray-600">
                                      {sharpeDiff > 0.2 
                                        ? `Optimized portfolio offers +${sharpeDiff.toFixed(2)} better risk-adjusted returns.`
                                        : sharpeDiff > 0.05
                                        ? `Close performance (gap: ${sharpeDiff.toFixed(2)}). Good stock selection!`
                                        : sharpeDiff > 0
                                        ? `Optimized portfolio shows +${sharpeDiff.toFixed(2)} improvement.`
                                        : `Your current portfolio performs well.`}
                                    </p>
                                    <div className="grid grid-cols-5 gap-1 text-xs text-gray-500">
                                      <div className="text-center px-1 py-0.5 rounded bg-red-50 border border-red-100">
                                        <div className="font-medium text-red-700">&lt; 0</div>
                                        <div className="text-red-600">Poor</div>
                                      </div>
                                      <div className="text-center px-1 py-0.5 rounded bg-orange-50 border border-orange-100">
                                        <div className="font-medium text-orange-700">0-0.5</div>
                                        <div className="text-orange-600">Below Avg</div>
                                      </div>
                                      <div className="text-center px-1 py-0.5 rounded bg-blue-50 border border-blue-100">
                                        <div className="font-medium text-blue-700">0.5-1.0</div>
                                        <div className="text-blue-600">Good</div>
                                      </div>
                                      <div className="text-center px-1 py-0.5 rounded bg-green-50 border border-green-100">
                                        <div className="font-medium text-green-700">1.0-2.0</div>
                                        <div className="text-green-600">Very Good</div>
                                      </div>
                                      <div className="text-center px-1 py-0.5 rounded bg-purple-50 border border-purple-100">
                                        <div className="font-medium text-purple-700">&gt; 2.0</div>
                                        <div className="text-purple-600">Exceptional</div>
                                      </div>
                                    </div>
                                  </div>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      ) : null}
                      
                      {/* Optimized Portfolio Allocations - GREEN */}
                      {mvoResults?.optimized_portfolio?.weights && Object.keys(mvoResults.optimized_portfolio.weights).length > 0 && (
                        <div className="space-y-4 mt-6 pt-6" style={{ borderTop: `1px solid ${chartTheme.border}` }}>
                          <h5 className="font-semibold flex items-center gap-2" style={{ color: chartTheme.text.primary }}>
                            <svg width="16" height="16" viewBox="0 0 16 16">
                              <polygon points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6" fill="#22c55e" stroke="#fff" strokeWidth="1"/>
                            </svg>
                            Optimized Portfolio Allocations
                          </h5>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {Object.entries(mvoResults.optimized_portfolio.weights)
                              .sort(([,a], [,b]) => (b as number) - (a as number))
                              .slice(0, 6)
                              .map(([ticker, weight], index) => (
                                <div key={ticker} className="flex items-center justify-between p-3 border rounded-lg bg-muted border-border">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                  <span className="text-sm font-medium text-green-600">{index + 1}</span>
                                </div>
                                <div>
                                      <div className="font-medium text-green-900">{ticker}</div>
                                      <div className="text-xs text-green-700">Market Selection</div>
                                </div>
                              </div>
                              <div className="text-right">
                                    <div className="font-semibold text-green-700">{((weight as number) * 100).toFixed(1)}%</div>
                                    <div className="text-xs text-green-600">
                                      {((weight as number) * capital).toLocaleString()} SEK
                                </div>
                              </div>
                            </div>
                          ))}
                          </div>
                        </div>
                      )}
                      </div>
                    ) : null}
              </Card>
              </div>
            </TabsContent>

            {/* Recommendations Tab */}
            <TabsContent value="recommendations" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Optimization Recommendations</h3>
                <p className="text-muted-foreground">
                  {mvoResults ? 'Personalized insights based on your optimization results' : 'Run optimization to get personalized recommendations'}
                </p>
              </div>

              {/* Dynamic Recommendations based on Optimization Results */}
              {(mvoResults && dualOptimizationResults) || tripleOptimizationResults ? (
                <div className="space-y-6">

                  {/* Detailed Comparison Summary */}
                  <Card>
                <CardHeader>
                      <CardTitle className="text-lg">Performance Summary</CardTitle>
                </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Current vs Optimized - Uses Triple or Dual Results */}
                        <div className="p-6 rounded-lg bg-muted border border-border">
                          <div className="text-base font-semibold text-gray-700 mb-4">
                            {tripleOptimizationResults ? 'Current → Recommended' : 'Current → Optimized'}
                          </div>
                          <div className="space-y-3">
                      {(() => {
                              // Use triple optimization if available, otherwise fall back to dual
                              let returnDiff = 0;
                              let riskDiff = 0;
                              let sharpeDiff = 0;
                              
                              if (tripleOptimizationResults) {
                                const recommendation = tripleOptimizationResults.optimization_metadata?.recommendation || 'weights';
                                const currentMetrics = tripleOptimizationResults.current_portfolio.metrics;
                                
                                let recommendedMetrics;
                                if (recommendation === 'market' && tripleOptimizationResults.market_optimized_portfolio) {
                                  recommendedMetrics = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics;
                                } else if (recommendation === 'weights') {
                                  recommendedMetrics = tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics;
                                } else {
                                  recommendedMetrics = currentMetrics;
                                }
                                
                                returnDiff = recommendedMetrics.expected_return - currentMetrics.expected_return;
                                riskDiff = recommendedMetrics.risk - currentMetrics.risk;
                                sharpeDiff = recommendedMetrics.sharpe_ratio - currentMetrics.sharpe_ratio;
                              } else if (dualOptimizationResults) {
                                returnDiff = dualOptimizationResults.comparison.return_difference || 0;
                                riskDiff = dualOptimizationResults.comparison.risk_difference || 0;
                                sharpeDiff = dualOptimizationResults.comparison.sharpe_difference || 0;
                              }
                              
                              return (
                                <>
                                  <div className="flex justify-between items-center py-1 group relative">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-medium text-gray-700">Expected Return</span>
                                      <div className="absolute left-0 top-6 z-10 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg">
                                        <div className="font-semibold mb-1">Expected Return</div>
                                        <div>The annualized return you can expect from this portfolio based on historical data. Positive values indicate potential gains, negative values indicate potential losses.</div>
                                      </div>
                                      <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                    <span className={`text-lg font-bold ${returnDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {returnDiff >= 0 ? '+' : ''}{(returnDiff * 100).toFixed(1)}%
                                    </span>
                                          </div>
                                  <div className="flex justify-between items-center py-1 group relative">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-medium text-gray-700">Risk (Volatility)</span>
                                      <div className="absolute left-0 top-6 z-10 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg">
                                        <div className="font-semibold mb-1">Risk (Volatility)</div>
                                        <div>Measures the annual volatility (standard deviation) of returns. Higher risk means more price fluctuations. Lower risk is generally better, as it indicates more stable returns.</div>
                                      </div>
                                      <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                    <span className={`text-lg font-bold ${riskDiff <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {riskDiff <= 0 ? '' : '+'}{(riskDiff * 100).toFixed(1)}%
                                    </span>
                                        </div>
                                  <div className="flex justify-between items-center py-1 group relative border-t border-gray-200 pt-2 mt-2">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-medium text-gray-700">Sharpe Ratio</span>
                                      <div className="absolute left-0 top-6 z-10 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg">
                                        <div className="font-semibold mb-1">Sharpe Ratio</div>
                                        <div>Measures risk-adjusted returns. Higher values indicate better returns per unit of risk. Values above 1 are considered good, above 2 are excellent. Negative values indicate the portfolio underperforms the risk-free rate.</div>
                                      </div>
                                      <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                    <span className={`text-lg font-bold ${sharpeDiff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {sharpeDiff >= 0 ? '+' : ''}{sharpeDiff.toFixed(2)}
                                    </span>
                                    </div>
                                </>
                              );
                            })()}
                                  </div>
                                  </div>
                                  
                        {/* Risk Profile Compliance */}
                        <div className="p-6 rounded-lg bg-muted border border-border">
                          <div className="text-base font-semibold text-gray-700 mb-4 flex items-center gap-1 group relative">
                            Risk Profile Compliance
                            <div className="absolute left-0 top-6 z-10 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg">
                              <div className="font-semibold mb-1">Risk Profile Compliance</div>
                              <div>Checks if the portfolio's volatility (risk) stays within the maximum allowed for your selected risk profile. Each profile has a risk limit: Very-Conservative (18%), Conservative (25%), Moderate (32%), Aggressive (35%), Very-Aggressive (47%).</div>
                            </div>
                            <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </div>
                          <div className="space-y-3">
                            {(() => {
                              // Risk limits based on volatility range upper bounds (standardized config)
                              const riskProfileMaxRisk: Record<string, number> = {
                                'very-conservative': 0.18,
                                'conservative': 0.25,
                                'moderate': 0.32,
                                'aggressive': 0.35,
                                'very-aggressive': 0.47
                              };
                              const maxRisk = riskProfileMaxRisk[riskProfile] || 0.32;
                              
                              // Get the recommended portfolio risk (from triple or dual optimization)
                              let optimizedRisk = 0;
                              if (tripleOptimizationResults) {
                                const recommendation = tripleOptimizationResults.optimization_metadata?.recommendation || 'weights';
                                if (recommendation === 'market' && tripleOptimizationResults.market_optimized_portfolio) {
                                  optimizedRisk = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.risk;
                                } else if (recommendation === 'weights') {
                                  optimizedRisk = tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.risk;
                                } else {
                                  optimizedRisk = tripleOptimizationResults.current_portfolio.metrics.risk;
                                }
                              } else if (mvoResults) {
                                optimizedRisk = mvoResults.optimized_portfolio?.metrics?.risk ?? 0;
                              }
                              
                              const isCompliant = optimizedRisk <= maxRisk;
                              
                              return (
                                <>
                                  <div className="flex justify-between items-center py-1">
                                    <span className="text-sm font-medium text-gray-700">Max Allowed</span>
                                    <span className="text-lg font-bold text-indigo-600">{(maxRisk * 100).toFixed(0)}%</span>
                                          </div>
                                  <div className="flex justify-between items-center py-1">
                                    <span className="text-sm font-medium text-gray-700">Portfolio Risk</span>
                                    <span className={`text-lg font-bold ${isCompliant ? 'text-green-600' : 'text-red-600'}`}>
                                      {(optimizedRisk * 100).toFixed(1)}%
                                    </span>
                                </div>
                                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200">
                                    {isCompliant ? (
                                      <CheckCircle className="h-5 w-5 text-green-600" />
                                    ) : (
                                      <AlertTriangle className="h-5 w-5 text-red-600" />
                                    )}
                                    <span className={`text-sm font-semibold ${isCompliant ? 'text-green-600' : 'text-red-600'}`}>
                                      {isCompliant ? '✓ Compliant' : '⚠ Over Limit'}
                                    </span>
                                        </div>
                                </>
                              );
                            })()}
                                    </div>
                                  </div>
                        
                      </div>
                    </CardContent>
                  </Card>

                  {/* Multi-Factor Quality Score Card - Enhanced */}
                  {(tripleOptimizationResults?.comparison?.quality_scores || dualOptimizationResults?.comparison?.quality_scores) && (() => {
                    const selected = selectedPortfolio || 'current';
                    const qualityData = tripleOptimizationResults?.comparison?.quality_scores || dualOptimizationResults?.comparison?.quality_scores;
                    if (!qualityData) return null;

                    // Handle triple vs dual optimization
                    let selectedData: QualityScoreResult;
                    if (tripleOptimizationResults?.comparison?.quality_scores) {
                      const tripleQuality = qualityData as { current: QualityScoreResult; weights: QualityScoreResult; market?: QualityScoreResult | null };
                      selectedData = selected === 'market' && tripleQuality.market
                        ? tripleQuality.market
                        : selected === 'weights'
                        ? tripleQuality.weights
                        : tripleQuality.current;
                    } else {
                      // Dual optimization
                      const dualQuality = qualityData as { current: QualityScoreResult; optimized: QualityScoreResult };
                      const selectedDual = (selected === 'current' ? 'current' : 'optimized') as 'current' | 'optimized';
                      selectedData = selectedDual === 'current' ? dualQuality.current : dualQuality.optimized;
                    }

                    const score = selectedData.composite_score;
                    const rating = selectedData.rating;
                    
                    // Get factor scores with icons
                    const factors = [
                      { 
                        name: selectedData.factor_breakdown?.risk_profile_compliance?.label || 'Risk Profile Compliance', 
                        score: selectedData.factor_breakdown?.risk_profile_compliance?.score || 0,
                        description: selectedData.factor_breakdown?.risk_profile_compliance?.description || 'How well the portfolio matches your risk profile',
                        icon: Shield,
                      },
                      { 
                        name: selectedData.factor_breakdown?.sortino_ratio?.label || 'Downside Protection', 
                        score: selectedData.factor_breakdown?.sortino_ratio?.score || 0,
                        description: selectedData.factor_breakdown?.sortino_ratio?.description || 'Resilience during market downturns',
                        icon: TrendingDown,
                      },
                      { 
                        name: selectedData.factor_breakdown?.diversification?.label || 'Diversification', 
                        score: selectedData.factor_breakdown?.diversification?.score || 0,
                        description: selectedData.factor_breakdown?.diversification?.description || 'Spread of risk across different assets',
                        icon: Activity,
                      },
                      { 
                        name: selectedData.factor_breakdown?.consistency?.label || 'Consistency', 
                        score: selectedData.factor_breakdown?.consistency?.score || 0,
                        description: selectedData.factor_breakdown?.consistency?.description || 'Stability and predictability of returns',
                        icon: LineChart,
                      },
                    ];

                    const getScoreColor = (score: number) => {
                      if (score >= 80) return 'text-green-600';
                      if (score >= 60) return 'text-blue-600';
                      if (score >= 40) return 'text-amber-600';
                      return 'text-red-600';
                    };

                    const getScoreBarColor = (score: number) => {
                      if (score >= 80) return '#22c55e';
                      if (score >= 60) return '#3b82f6';
                      if (score >= 40) return '#f59e0b';
                      return '#ef4444';
                    };

                    const selectedColor = selected === 'current' ? 'red' : selected === 'weights' ? 'blue' : 'green';

                          return (
                      <Card className="border-2 border-purple-200">
                    <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <Award className="h-5 w-5 text-purple-600" />
                            Multi-Factor Quality Analysis
                          </CardTitle>
                          <p className="text-sm text-gray-500">Comprehensive portfolio quality assessment</p>
                    </CardHeader>
                        <CardContent className="space-y-6">
                          {/* Composite Score Gauge */}
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
                                <Badge className="text-sm px-3 py-1" style={{ backgroundColor: getScoreBarColor(score) }}>
                                  {rating}
                                </Badge>
                            </div>
                              <h3 className="text-xl font-bold mb-1">Composite Quality Score</h3>
                              <p className="text-sm text-gray-600">
                                Your portfolio scores {score.toFixed(0)}/100 across all quality factors
                              </p>
                          </div>
                                  </div>
                                  
                          {/* Factor Breakdown */}
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
                                      <span className="text-sm font-medium text-gray-700">{factor.name}</span>
                                      <div className="absolute left-0 top-6 z-10 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg">
                                        <div className="font-semibold mb-1">{factor.name}</div>
                                        <div>{factor.tooltip || factor.description}</div>
                                      </div>
                                      <Info className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                  </div>
                                    <span className={`text-sm font-bold ${getScoreColor(factor.score)}`}>
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
                                  <p className="text-xs text-gray-500 italic">{factor.description}</p>
                            </div>
                          );
                            })}
                          </div>

                          {/* Comparison with other portfolios */}
                          {tripleOptimizationResults?.comparison?.quality_scores && (() => {
                            const tripleQuality = qualityData as { current: QualityScoreResult; weights: QualityScoreResult; market?: QualityScoreResult | null };
                          return (
                              <div className="pt-4 border-t border-gray-200">
                                <h4 className="font-semibold text-sm text-gray-700 mb-3">Quality Score Comparison</h4>
                                <div className="grid grid-cols-3 gap-3">
                                  <div className={`p-3 rounded-lg border-2 ${selected === 'current' ? 'border-red-500 bg-red-50' : 'border-gray-200'}`}>
                                    <div className="text-xs text-gray-600 mb-1">Current</div>
                                    <div className="text-lg font-bold text-red-600">{tripleQuality.current.composite_score.toFixed(0)}</div>
                                </div>
                                  <div className={`p-3 rounded-lg border-2 ${selected === 'weights' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                                    <div className="text-xs text-gray-600 mb-1">Weights-Opt</div>
                                    <div className="text-lg font-bold text-blue-600">{tripleQuality.weights.composite_score.toFixed(0)}</div>
                          </div>
                                  {tripleQuality.market && (
                                    <div className={`p-3 rounded-lg border-2 ${selected === 'market' ? 'border-green-500 bg-green-50' : 'border-gray-200'}`}>
                                      <div className="text-xs text-gray-600 mb-1">Market-Opt</div>
                                      <div className="text-lg font-bold text-green-600">{tripleQuality.market.composite_score.toFixed(0)}</div>
                        </div>
                                  )}
                              </div>
                            </div>
                          );
                      })()}
                    </CardContent>
                  </Card>
                    );
                  })()}

                  {/* Monte Carlo Simulation Card - Enhanced */}
                  {tripleOptimizationResults?.comparison?.monte_carlo && (() => {
                    const monteCarloData = tripleOptimizationResults?.comparison?.monte_carlo;
                    if (!monteCarloData) return null;

                    const selected = selectedPortfolio || 'current';
                    const selectedMonteCarlo = selected === 'current' 
                      ? monteCarloData.current
                      : selected === 'weights'
                      ? monteCarloData.weights
                      : monteCarloData.market || monteCarloData.weights;
                    
                    const selectedLabel = isTriple
                      ? (selected === 'current' ? 'Current Portfolio' : selected === 'weights' ? 'Weights-Optimized' : 'Market-Optimized')
                      : (selected === 'current' || !selectedPortfolio ? 'Current Portfolio' : 'Optimized Portfolio');
                    const selectedColor = isTriple
                      ? (selected === 'current' ? 'red' : selected === 'weights' ? 'blue' : 'green')
                      : (selected === 'current' || !selectedPortfolio ? 'red' : 'green');
                    const selectedFill = selectedColor === 'red' ? '#fef2f2' : selectedColor === 'blue' ? '#eff6ff' : '#f0fdf4';
                    const selectedStroke = selectedColor === 'red' ? '#ef4444' : selectedColor === 'blue' ? '#3b82f6' : '#22c55e';

                    // Calculate VaR (Value at Risk) at 95% confidence
                    const var95 = selectedMonteCarlo.percentiles?.p5 || 0;
                    const expectedReturn = selectedMonteCarlo.percentiles?.p50 || 0;
                    const bestCase = selectedMonteCarlo.percentiles?.p95 || 0;

                    return (
                      <Card className="border-2 border-blue-200">
                    <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <BarChart3 className="h-5 w-5 text-blue-600" />
                            Monte Carlo Risk Analysis
                          </CardTitle>
                          <p className="text-sm text-gray-500">
                            {selectedMonteCarlo.parameters?.num_simulations?.toLocaleString() || '10,000'} simulations projecting 1-year return distribution
                          </p>
                    </CardHeader>
                        <CardContent className="space-y-6">
                          {/* Key Statistics Grid */}
                          <div className="grid grid-cols-3 gap-4">
                            <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                              <div className="flex items-center gap-2 mb-2">
                                <AlertCircle className="h-4 w-4 text-red-600" />
                                <span className="text-xs font-medium text-red-700">Value at Risk (95%)</span>
                            </div>
                              <div className="text-2xl font-bold text-red-800">
                                {(var95 * 100).toFixed(1)}%
                          </div>
                              <div className="text-xs text-red-600 mt-1">Worst case scenario</div>
                        </div>
                            
                            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                              <div className="flex items-center gap-2 mb-2">
                                <TrendingUp className="h-4 w-4 text-blue-600" />
                                <span className="text-xs font-medium text-blue-700">Expected Return</span>
                            </div>
                              <div className="text-2xl font-bold text-blue-800">
                                {(expectedReturn * 100).toFixed(1)}%
                          </div>
                              <div className="text-xs text-blue-600 mt-1">Median (50th percentile)</div>
                        </div>
                        
                            <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                              <div className="flex items-center gap-2 mb-2">
                                <Activity className="h-4 w-4 text-green-600" />
                                <span className="text-xs font-medium text-green-700">Best Case (95%)</span>
                      </div>
                              <div className="text-2xl font-bold text-green-800">
                                {(bestCase * 100).toFixed(1)}%
                    </div>
                              <div className="text-xs text-green-600 mt-1">Optimistic scenario</div>
                          </div>
                          </div>

                          {/* Return Distribution Area Chart with Multiple Portfolios */}
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-gray-700">Return Distribution</div>
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                        {(() => {
                                  // Calculate domain from all visible portfolios
                                  let allData: Array<{ return_pct: number }> = [];
                                  
                                  if (tripleOptimizationResults) {
                                    const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                    if (returnScenarioVisibility.current && tripleMonteCarlo.current.histogram_data) {
                                      allData = allData.concat(tripleMonteCarlo.current.histogram_data);
                                    }
                                    if (returnScenarioVisibility.weights && tripleMonteCarlo.weights.histogram_data) {
                                      allData = allData.concat(tripleMonteCarlo.weights.histogram_data);
                                    }
                                    if (returnScenarioVisibility.market && tripleMonteCarlo.market?.histogram_data) {
                                      allData = allData.concat(tripleMonteCarlo.market.histogram_data);
                                    }
                                  } else {
                                    allData = selectedMonteCarlo.histogram_data || [];
                                  }
                                  
                                  const minReturn = allData.length > 0 ? Math.min(...allData.map(d => d.return_pct)) : 0;
                                  const maxReturn = allData.length > 0 ? Math.max(...allData.map(d => d.return_pct)) : 100;
                                  
                                  return (
                                    <AreaChart
                                      margin={{ top: 10, right: 20, bottom: 30, left: 10 }}
                                    >
                                      <defs>
                                        <linearGradient id="colorGradient-red" x1="0" y1="0" x2="0" y2="1">
                                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                                        </linearGradient>
                                        <linearGradient id="colorGradient-blue" x1="0" y1="0" x2="0" y2="1">
                                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                                        </linearGradient>
                                        <linearGradient id="colorGradient-green" x1="0" y1="0" x2="0" y2="1">
                                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
                                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1}/>
                                        </linearGradient>
                                      </defs>
                                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                      <XAxis
                                        dataKey="return_pct"
                                        type="number"
                                        domain={[minReturn, maxReturn]}
                                        tickFormatter={(value) => `${value.toFixed(0)}%`}
                                        tick={{ fontSize: 10 }}
                                        label={{ value: 'Return (%)', position: 'bottom', offset: 15, fontSize: 11 }}
                                      />
                                      <YAxis
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(value) => `${value.toFixed(0)}%`}
                                        label={{ value: 'Probability Density', angle: -90, position: 'insideLeft', offset: 5, fontSize: 11 }}
                                      />
                                      <RechartsTooltip
                                        formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
                                        labelFormatter={(label) => `Return: ${Number(label).toFixed(1)}%`}
                                      />
                                      <Legend 
                                        verticalAlign="top"
                                        height={36}
                                      />
                                      
                                      {/* Current Portfolio Distribution */}
                                      {tripleOptimizationResults && returnScenarioVisibility.current && (() => {
                                        const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                        return (
                                          <Area
                                            type="monotone"
                                            data={tripleMonteCarlo.current.histogram_data}
                                            dataKey="frequency"
                                            name="Current Portfolio"
                                            stroke="#ef4444"
                                            strokeWidth={2}
                                            fill="url(#colorGradient-red)"
                                          />
                                        );
                                      })()}
                                      
                                      {/* Weights-Optimized Portfolio Distribution */}
                                      {tripleOptimizationResults && returnScenarioVisibility.weights && (() => {
                                        const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                        return (
                                          <Area
                                            type="monotone"
                                            data={tripleMonteCarlo.weights.histogram_data}
                                            dataKey="frequency"
                                            name="Weights-Optimized"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            fill="url(#colorGradient-blue)"
                                          />
                                        );
                                      })()}
                                      
                                      {/* Market-Optimized Portfolio Distribution */}
                                      {tripleOptimizationResults && returnScenarioVisibility.market && (() => {
                                        const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                        if (!tripleMonteCarlo.market) return null;
                                        return (
                                          <Area
                                            type="monotone"
                                            data={tripleMonteCarlo.market.histogram_data}
                                            dataKey="frequency"
                                            name="Market-Optimized"
                                            stroke="#22c55e"
                                            strokeWidth={2}
                                            fill="url(#colorGradient-green)"
                                          />
                                        );
                                      })()}
                                      
                                      {/* Fallback: Show selected portfolio if not triple optimization */}
                                      {!tripleOptimizationResults && (
                                        <Area
                                          type="monotone"
                                          data={selectedMonteCarlo.histogram_data}
                                          dataKey="frequency"
                                          name={selectedLabel}
                                          stroke={selectedStroke}
                                          strokeWidth={2}
                                          fill={`url(#colorGradient-${selectedColor})`}
                                        />
                                      )}
                                      
                                      {/* Highlight selected return scenario for all visible portfolios */}
                                      {selectedReturnScenario && (() => {
                                        const scenarioKey = selectedReturnScenario as 'p5' | 'p25' | 'p50' | 'p75' | 'p95';
                                        const highlights: JSX.Element[] = [];
                                        
                                        if (tripleOptimizationResults) {
                                          const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                          
                                          // Highlight Current Portfolio percentile
                                          if (returnScenarioVisibility.current && tripleMonteCarlo.current.percentiles?.[scenarioKey] !== undefined) {
                                            const percentileValue = (tripleMonteCarlo.current.percentiles[scenarioKey] || 0) * 100;
                                            highlights.push(
                                              <ReferenceLine
                                                key="current-highlight"
                                                x={percentileValue}
                                                stroke="#ef4444"
                                                strokeWidth={3}
                                                strokeDasharray="5 5"
                                              />
                                            );
                                          }
                                          
                                          // Highlight Weights-Optimized Portfolio percentile
                                          if (returnScenarioVisibility.weights && tripleMonteCarlo.weights.percentiles?.[scenarioKey] !== undefined) {
                                            const percentileValue = (tripleMonteCarlo.weights.percentiles[scenarioKey] || 0) * 100;
                                            highlights.push(
                                              <ReferenceLine
                                                key="weights-highlight"
                                                x={percentileValue}
                                                stroke="#3b82f6"
                                                strokeWidth={3}
                                                strokeDasharray="5 5"
                                              />
                                            );
                                          }
                                          
                                          // Highlight Market-Optimized Portfolio percentile
                                          if (returnScenarioVisibility.market && tripleMonteCarlo.market?.percentiles?.[scenarioKey] !== undefined) {
                                            const percentileValue = (tripleMonteCarlo.market.percentiles[scenarioKey] || 0) * 100;
                                            highlights.push(
                                              <ReferenceLine
                                                key="market-highlight"
                                                x={percentileValue}
                                                stroke="#22c55e"
                                                strokeWidth={3}
                                                strokeDasharray="5 5"
                                              />
                                            );
                                          }
                                        } else {
                                          // Single portfolio highlight
                                          if (selectedMonteCarlo.percentiles?.[scenarioKey] !== undefined) {
                                            const percentileValue = (selectedMonteCarlo.percentiles[scenarioKey] || 0) * 100;
                                            highlights.push(
                                              <ReferenceLine
                                                key="single-highlight"
                                                x={percentileValue}
                                                stroke={selectedStroke}
                                                strokeWidth={3}
                                                strokeDasharray="5 5"
                                              />
                                            );
                                          }
                                        }
                                        
                                        return <>{highlights}</>;
                                      })()}
                                    </AreaChart>
                                  );
                                })()}
                              </ResponsiveContainer>
                            </div>
                          </div>

                          {/* Interactive Legend and Return Scenarios */}
                          <div className="space-y-3">
                            {/* Interactive Legend */}
                            {tripleOptimizationResults && (() => {
                              const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                              
                              const toggleVisibility = (portfolio: 'current' | 'weights' | 'market') => {
                                setReturnScenarioVisibility(prev => ({
                                  ...prev,
                                  [portfolio]: !prev[portfolio]
                                }));
                              };
                              
                              return (
                                <div className="flex flex-wrap gap-2 justify-start border-b pb-3">
                                  {/* Current Portfolio Legend */}
                                  <button
                                    onClick={() => toggleVisibility('current')}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                                      returnScenarioVisibility.current
                                        ? 'border-red-300 bg-red-50 hover:bg-red-100'
                                        : 'border-gray-200 bg-gray-100 opacity-50'
                                    }`}
                                    title={returnScenarioVisibility.current ? 'Hide Current Portfolio' : 'Show Current Portfolio'}
                                  >
                                    {returnScenarioVisibility.current ? (
                                      <Eye className="h-4 w-4 text-red-600" />
                                    ) : (
                                      <EyeOff className="h-4 w-4 text-gray-500" />
                                    )}
                                    <div className="w-3 h-3 rounded-full bg-red-600" />
                                    <span className="font-medium text-red-700">Current</span>
                                  </button>
                                  
                                  {/* Weights-Optimized Legend */}
                                  <button
                                    onClick={() => toggleVisibility('weights')}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                                      returnScenarioVisibility.weights
                                        ? 'border-blue-300 bg-blue-50 hover:bg-blue-100'
                                        : 'border-gray-200 bg-gray-100 opacity-50'
                                    }`}
                                    title={returnScenarioVisibility.weights ? 'Hide Weights-Optimized' : 'Show Weights-Optimized'}
                                  >
                                    {returnScenarioVisibility.weights ? (
                                      <Eye className="h-4 w-4 text-blue-600" />
                                    ) : (
                                      <EyeOff className="h-4 w-4 text-gray-500" />
                                    )}
                                    <div className="w-3 h-3 rounded-full bg-blue-600" />
                                    <span className="font-medium text-blue-700">Weights-Opt</span>
                                  </button>
                                  
                                  {/* Market-Optimized Legend */}
                                  {tripleMonteCarlo.market && (
                                    <button
                                      onClick={() => toggleVisibility('market')}
                                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs transition-all ${
                                        returnScenarioVisibility.market
                                          ? 'border-green-300 bg-green-50 hover:bg-green-100'
                                          : 'border-gray-200 bg-gray-100 opacity-50'
                                      }`}
                                      title={returnScenarioVisibility.market ? 'Hide Market-Optimized' : 'Show Market-Optimized'}
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
                              );
                        })()}
                            
                            {/* Return Scenarios - Show for each visible portfolio */}
                            <div className="text-sm font-medium text-gray-700">Return Scenarios</div>
                            <div className="text-xs text-gray-500 mb-2">Click a scenario to highlight it in the distribution chart</div>
                            <div className="space-y-3">
                              {tripleOptimizationResults ? (() => {
                                const tripleMonteCarlo = monteCarloData as { current: MonteCarloResult; weights: MonteCarloResult; market?: MonteCarloResult | null };
                                const scenarios = [
                                  { label: 'Worst Case (5th percentile)', key: 'p5', color: '#ef4444' },
                                  { label: 'Pessimistic (25th percentile)', key: 'p25', color: '#f59e0b' },
                                  { label: 'Expected (50th percentile)', key: 'p50', color: '#3b82f6' },
                                  { label: 'Optimistic (75th percentile)', key: 'p75', color: '#22c55e' },
                                  { label: 'Best Case (95th percentile)', key: 'p95', color: '#10b981' },
                                ];
                                
                                return scenarios.map((scenario) => {
                                  const isSelected = selectedReturnScenario === scenario.key;
                                  const portfolioData: Array<{ label: string; value: number; color: string; visible: boolean }> = [];
                                  
                                  if (returnScenarioVisibility.current) {
                                    portfolioData.push({
                                      label: 'Current',
                                      value: tripleMonteCarlo.current.percentiles?.[scenario.key as keyof typeof tripleMonteCarlo.current.percentiles] || 0,
                                      color: '#ef4444',
                                      visible: true
                                    });
                                  }
                                  
                                  if (returnScenarioVisibility.weights) {
                                    portfolioData.push({
                                      label: 'Weights',
                                      value: tripleMonteCarlo.weights.percentiles?.[scenario.key as keyof typeof tripleMonteCarlo.weights.percentiles] || 0,
                                      color: '#3b82f6',
                                      visible: true
                                    });
                                  }
                                  
                                  if (returnScenarioVisibility.market && tripleMonteCarlo.market) {
                                    portfolioData.push({
                                      label: 'Market',
                                      value: tripleMonteCarlo.market.percentiles?.[scenario.key as keyof typeof tripleMonteCarlo.market.percentiles] || 0,
                                      color: '#22c55e',
                                      visible: true
                                    });
                                  }
                                  
                                  if (portfolioData.length === 0) return null;
                                  
                                  return (
                                    <button
                                      key={scenario.label}
                                      onClick={() => setSelectedReturnScenario(isSelected ? null : scenario.key)}
                                      className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                                        isSelected
                                          ? 'bg-blue-50 border-blue-400 shadow-md'
                                          : 'bg-gray-50 border-gray-200 hover:border-gray-300 hover:bg-gray-100'
                                      }`}
                                    >
                                      <div className="flex items-center justify-between mb-2">
                                        <div className="text-xs font-medium" style={{ color: isSelected ? '#1e40af' : '#4b5563' }}>
                                          {scenario.label}
                          </div>
                                        {isSelected && (
                                          <div className="text-xs text-blue-600 font-semibold">Selected</div>
                                        )}
                        </div>
                                      <div className="flex flex-wrap gap-3">
                                        {portfolioData.map((portfolio) => (
                                          <div key={portfolio.label} className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: portfolio.color }} />
                                            <span className="text-xs text-gray-600">{portfolio.label}:</span>
                                            <span className="text-sm font-bold" style={{ color: portfolio.color }}>
                                              {(portfolio.value * 100).toFixed(1)}%
                              </span>
                      </div>
                                        ))}
                                      </div>
                                    </button>
                                  );
                                });
                              })() : (
                                // Fallback for dual optimization or single portfolio
                                [
                                  { label: 'Worst Case (5th percentile)', value: selectedMonteCarlo.percentiles?.p5 || 0, color: 'red' },
                                  { label: 'Pessimistic (25th percentile)', value: selectedMonteCarlo.percentiles?.p25 || 0, color: 'orange' },
                                  { label: 'Expected (50th percentile)', value: selectedMonteCarlo.percentiles?.p50 || 0, color: 'blue' },
                                  { label: 'Optimistic (75th percentile)', value: selectedMonteCarlo.percentiles?.p75 || 0, color: 'green' },
                                  { label: 'Best Case (95th percentile)', value: selectedMonteCarlo.percentiles?.p95 || 0, color: 'emerald' },
                                ].map((scenario) => {
                                  const dotColor = scenario.color === 'red' ? '#ef4444' :
                                                   scenario.color === 'orange' ? '#f59e0b' :
                                                   scenario.color === 'blue' ? '#3b82f6' :
                                                   scenario.color === 'green' ? '#22c55e' : '#10b981';
                                  const scenarioKey = scenario.label.includes('5th') ? 'p5' :
                                                      scenario.label.includes('25th') ? 'p25' :
                                                      scenario.label.includes('50th') ? 'p50' :
                                                      scenario.label.includes('75th') ? 'p75' : 'p95';
                                  const isSelected = selectedReturnScenario === scenarioKey;
                                  return (
                                    <button
                                      key={scenario.label}
                                      onClick={() => setSelectedReturnScenario(isSelected ? null : scenarioKey)}
                                      className={`w-full flex items-center gap-3 p-2 rounded-lg border-2 transition-all ${
                                        isSelected
                                          ? 'bg-blue-50 border-blue-400 shadow-md'
                                          : 'bg-gray-50 border-gray-200 hover:border-gray-300 hover:bg-gray-100'
                                      }`}
                                    >
                                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: dotColor }} />
                                      <div className="flex-1 text-sm text-gray-700">{scenario.label}</div>
                                      <div className={`text-sm font-bold ${selectedColor === 'red' ? 'text-red-600' : selectedColor === 'blue' ? 'text-blue-600' : 'text-green-600'}`}>
                                        {(scenario.value * 100).toFixed(1)}%
                                      </div>
                                      {isSelected && (
                                        <div className="text-xs text-blue-600 font-semibold">Selected</div>
                                      )}
                                    </button>
                                  );
                                })
                              )}
                    </div>
                  </div>
                        
                          {/* Loss Probability Scenarios */}
                          <div className="space-y-3">
                            <div className="text-sm font-medium text-gray-700 flex items-center gap-1">
                              Loss Probability Scenarios
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-3 w-3 text-gray-400 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent side="bottom" className="max-w-xs">
                                    <div className="font-semibold mb-1">Loss Probability Scenarios</div>
                                    <div>Based on Monte Carlo simulations, these show the probability that your portfolio will experience losses exceeding the specified thresholds over a 1-year period. Lower percentages indicate better downside protection. For example, a 5% probability of 10%+ loss means there's a 5% chance your portfolio could lose 10% or more in a year.</div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                                <div className="text-xs font-medium text-red-700 mb-2 flex items-center gap-1">
                                  10% Loss Threshold
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Info className="h-3 w-3 text-red-500 cursor-help" />
                                      </TooltipTrigger>
                                      <TooltipContent side="right" className="max-w-xs">
                                        <div className="font-semibold mb-1">10% Loss Threshold</div>
                                        <div>The probability that your portfolio will lose 10% or more in value over a 1-year period, based on Monte Carlo simulations. This helps assess downside risk.</div>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                </div>
                                <div className="text-2xl font-bold text-red-800">
                                  {selectedMonteCarlo.probability_loss_thresholds?.loss_10pct?.toFixed(1) || 0}%
                                  </div>
                                <div className="text-xs text-red-600 mt-1">Probability of 10%+ loss</div>
                              </div>
                              <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                                <div className="text-xs font-medium text-red-700 mb-2 flex items-center gap-1">
                                  20% Loss Threshold
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Info className="h-3 w-3 text-red-500 cursor-help" />
                                      </TooltipTrigger>
                                      <TooltipContent side="right" className="max-w-xs">
                                        <div className="font-semibold mb-1">20% Loss Threshold</div>
                                        <div>The probability that your portfolio will lose 20% or more in value over a 1-year period, based on Monte Carlo simulations. This represents significant downside risk.</div>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                </div>
                                <div className="text-2xl font-bold text-red-800">
                                  {selectedMonteCarlo.probability_loss_thresholds?.loss_20pct?.toFixed(1) || 0}%
                                  </div>
                                <div className="text-xs text-red-600 mt-1">Probability of 20%+ loss</div>
                              </div>
                            </div>
                          </div>

                          {/* Risk Assessment Summary */}
                          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="flex items-start gap-3">
                              <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                              <div className="flex-1">
                                <div className="font-medium text-blue-900 mb-2">Risk Assessment</div>
                                <div className="text-sm text-blue-800 space-y-1">
                                  <p>• Probability of positive returns: <span className="font-semibold">{selectedMonteCarlo.probability_positive?.toFixed(1)}%</span></p>
                                  <p>• Expected return range: <span className="font-semibold">{(selectedMonteCarlo.percentiles?.p25 * 100)?.toFixed(1)}%</span> to <span className="font-semibold">{(selectedMonteCarlo.percentiles?.p75 * 100)?.toFixed(1)}%</span></p>
                                  <p>• Value at Risk (95% confidence): <span className="font-semibold">{(var95 * 100).toFixed(1)}%</span> maximum expected loss</p>
                                </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                    );
                  })()}
                </div>
              ) : (
                /* Pre-optimization recommendations */
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Getting Started</CardTitle>
                    <p className="text-muted-foreground">
                      Run the optimization to get personalized recommendations
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                      <div>
                        <div className="font-medium text-blue-800">Step 1: Run Optimization</div>
                        <div className="text-sm text-blue-700">
                          Go to the "Optimization" tab and click "Optimize & Compare" to analyze your portfolio against the best available options.
                        </div>
                      </div>
                    </div>
                    
                    {/* Risk Profile Specific Pre-recommendations */}
                  <div className="bg-muted rounded-lg p-6 border border-border">
                    <h4 className="font-medium text-indigo-900 mb-3">
                        General Tips for {getRiskProfileDisplay(riskProfile)} Investors
                    </h4>
                    <div className="text-sm text-indigo-800 space-y-2">
                      {riskProfile === 'very-conservative' && (
                        <>
                          <p>• Focus on capital preservation with stable dividend stocks</p>
                          <p>• Consider adding bond ETFs for stability</p>
                          <p>• Maintain high diversification across defensive sectors</p>
                        </>
                      )}
                      {riskProfile === 'conservative' && (
                        <>
                          <p>• Balance income generation with moderate growth</p>
                          <p>• Include blue-chip stocks with strong fundamentals</p>
                          <p>• Consider defensive sector ETFs for stability</p>
                        </>
                      )}
                      {riskProfile === 'moderate' && (
                        <>
                          <p>• Seek balanced growth across multiple sectors</p>
                          <p>• Include both value and growth stocks</p>
                          <p>• Consider international diversification</p>
                        </>
                      )}
                      {riskProfile === 'aggressive' && (
                        <>
                          <p>• Focus on high-growth technology and innovation</p>
                          <p>• Consider emerging market exposure</p>
                          <p>• Include momentum-driven stocks</p>
                        </>
                      )}
                      {riskProfile === 'very-aggressive' && (
                        <>
                          <p>• Maximize growth potential with high-conviction picks</p>
                          <p>• Consider sector-specific ETFs for trends</p>
                          <p>• Include disruptive technology companies</p>
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
              )}
            </TabsContent>
          </Tabs>

          {/* Navigation */}
          <div className="flex justify-between pt-6">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={() => {
                // Build selected portfolio data based on user selection
                let portfolioData: SelectedPortfolioData;
                
                if (selectedPortfolio === 'market' && tripleOptimizationResults?.market_optimized_portfolio?.optimized_portfolio) {
                  // User selected the market-optimized portfolio
                  const marketOpt = tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio;
                  portfolioData = {
                    source: 'market',
                    tickers: marketOpt.tickers || [],
                    weights: marketOpt.weights || {},
                    metrics: {
                      expected_return: marketOpt.metrics?.expected_return || 0,
                      risk: marketOpt.metrics?.risk || 0,
                      sharpe_ratio: marketOpt.metrics?.sharpe_ratio || 0,
                    }
                  };
                } else if (selectedPortfolio === 'market' && mvoResults?.optimized_portfolio) {
                  // Fallback: legacy MVO optimized portfolio
                  portfolioData = {
                    source: 'market',
                    tickers: mvoResults.optimized_portfolio.tickers || [],
                    weights: mvoResults.optimized_portfolio.weights || {},
                    metrics: {
                      expected_return: mvoResults.optimized_portfolio.metrics?.expected_return || 0,
                      risk: mvoResults.optimized_portfolio.metrics?.risk || 0,
                      sharpe_ratio: mvoResults.optimized_portfolio.metrics?.sharpe_ratio || 0,
                    }
                  };
                } else if (selectedPortfolio === 'weights' && tripleOptimizationResults?.weights_optimized_portfolio?.optimized_portfolio) {
                  // User selected the weights-optimized portfolio
                  const weightsOpt = tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio;
                  portfolioData = {
                    source: 'weights',
                    tickers: weightsOpt.tickers || [],
                    weights: weightsOpt.weights || {},
                    metrics: {
                      expected_return: weightsOpt.metrics?.expected_return || 0,
                      risk: weightsOpt.metrics?.risk || 0,
                      sharpe_ratio: weightsOpt.metrics?.sharpe_ratio || 0,
                    }
                  };
                } else {
                  // Default: use current portfolio
                  const currentTickers = currentPortfolio?.map(s => s.symbol) || [];
                  const currentWeights: Record<string, number> = {};
                  currentPortfolio?.forEach(s => {
                    currentWeights[s.symbol] = s.allocation / 100;
                  });
                  
                  // Get metrics from triple optimization if available, otherwise from dual or current
                  let expectedReturn = currentMetrics?.expectedReturn || 0;
                  let risk = currentMetrics?.risk || 0;
                  let sharpeRatio = 0;
                  
                  if (tripleOptimizationResults?.current_portfolio?.metrics) {
                    expectedReturn = tripleOptimizationResults.current_portfolio.metrics.expected_return || expectedReturn;
                    risk = tripleOptimizationResults.current_portfolio.metrics.risk || risk;
                    sharpeRatio = tripleOptimizationResults.current_portfolio.metrics.sharpe_ratio || sharpeRatio;
                  } else if (dualOptimizationResults?.current_portfolio?.metrics) {
                    expectedReturn = dualOptimizationResults.current_portfolio.metrics.expected_return || expectedReturn;
                    risk = dualOptimizationResults.current_portfolio.metrics.risk || risk;
                    sharpeRatio = dualOptimizationResults.current_portfolio.metrics.sharpe_ratio || sharpeRatio;
                  }
                  
                  portfolioData = {
                    source: 'current',
                    tickers: currentTickers,
                    weights: currentWeights,
                    metrics: {
                      expected_return: expectedReturn,
                      risk: risk,
                      sharpe_ratio: sharpeRatio,
                    }
                  };
                }
                
                // Call the portfolio selection callback if provided
                if (onPortfolioSelection) {
                  onPortfolioSelection(portfolioData);
                  console.log('📊 Selected portfolio forwarded:', portfolioData.source, portfolioData.tickers);
                }
                
                // Navigate between tabs within component, then proceed to next wizard step from recommendations
                if (activeTab === 'overview') {
                  setActiveTab('optimization');
                } else if (activeTab === 'optimization') {
                  // Should not reach here if optimization hasn't been run (button is disabled)
                  setActiveTab('analysis');
                } else if (activeTab === 'analysis') {
                  setActiveTab('recommendations');
                } else if (activeTab === 'recommendations') {
                  // From recommendations tab, proceed to next wizard step
                  onNext();
                }
              }}
              disabled={
                // Base validation: portfolio must exist and have at least 3 stocks
                !currentPortfolio || currentPortfolio.length < 3 ||
                // In optimization tab: must have run optimization before continuing
                (activeTab === 'optimization' && !mvoResults && !dualOptimizationResults && !tripleOptimizationResults) ||
                // In analysis tab: must have selected a portfolio before continuing
                (activeTab === 'analysis' && !selectedPortfolio)
              }
            >
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};



