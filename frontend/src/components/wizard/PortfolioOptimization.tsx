/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip as RechartsTooltip, Legend, ReferenceArea } from 'recharts';
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
  ZoomIn
} from 'lucide-react';

// Visualization theme matching Portfolio3PartVisualization
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
  spacing: {
    cardPadding: '28px',
    sectionGap: '28px',
  },
  radius: '18px',
  legend: {
    fontSize: 12,
    color: 'rgba(59, 59, 51, 0.8)',
  },
};

const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

interface PortfolioOptimizationProps {
  onNext: () => void;
  onPrev: () => void;
  selectedStocks: PortfolioAllocation[];
  riskProfile: string;
  capital: number;
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
  random_portfolios: EfficientFrontierPoint[];
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
  capital 
}: PortfolioOptimizationProps) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'optimization' | 'analysis' | 'recommendations'>('optimization');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingEligibleTickers, setIsLoadingEligibleTickers] = useState(false);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResult | null>(null);
  const [efficientFrontier, setEfficientFrontier] = useState<EfficientFrontierPoint[]>([]);
  const [randomPortfolios, setRandomPortfolios] = useState<EfficientFrontierPoint[]>([]);
  const [mvoResults, setMvoResults] = useState<MVOOptimizationResponse | null>(null);
  const [eligibleTickers, setEligibleTickers] = useState<EligibleTicker[]>([]);
  const [currentPortfolio, setCurrentPortfolio] = useState<PortfolioAllocation[]>(Array.isArray(selectedStocks) ? selectedStocks : []);
  const [optimizedPortfolio, setOptimizedPortfolio] = useState<PortfolioAllocation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  // Zoom state for eligible tickers chart
  const [eligibleTickersZoom, setEligibleTickersZoom] = useState<{ 
    x: [number, number]; 
    y: [number, number]; 
    zoomLevel: number;
  } | null>(null);
  
  // Zoom state for efficient frontier chart
  const [efficientFrontierZoom, setEfficientFrontierZoom] = useState<{ 
    x: [number, number]; 
    y: [number, number]; 
    zoomLevel: number;
  } | null>(null);

  // Calculate default domain ranges for zoom
  const eligibleTickersDomain = useMemo(() => {
    try {
      if (!eligibleTickers || eligibleTickers.length === 0) return null;
      
      const volatilities = eligibleTickers
        .map(t => t?.volatility)
        .filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v)) as number[];
      const returns = eligibleTickers
        .map(t => t?.expected_return)
        .filter(r => typeof r === 'number' && !isNaN(r) && isFinite(r)) as number[];
      
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
      
      return {
        x: [Math.max(0, minVol * 0.9), maxVol * 1.1] as [number, number],
        y: [Math.max(0, minRet * 0.9), maxRet * 1.1] as [number, number],
      };
    } catch (error) {
      console.error('Error calculating eligibleTickersDomain:', error);
      return null;
    }
  }, [eligibleTickers]);

  const efficientFrontierDomain = useMemo(() => {
    try {
      const allPoints: Array<{ risk: number; return: number }> = [];
      
      if (randomPortfolios && Array.isArray(randomPortfolios)) {
        randomPortfolios.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return)) {
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      if (efficientFrontier && Array.isArray(efficientFrontier)) {
        efficientFrontier.forEach(p => {
          if (p && typeof p.risk === 'number' && typeof p.return === 'number' && 
              !isNaN(p.risk) && !isNaN(p.return) && isFinite(p.risk) && isFinite(p.return)) {
            allPoints.push({ risk: p.risk, return: p.return });
          }
        });
      }
      
      if (mvoResults?.current_portfolio?.metrics) {
        const risk = mvoResults.current_portfolio.metrics.risk;
        const ret = mvoResults.current_portfolio.metrics.expected_return;
        if (typeof risk === 'number' && typeof ret === 'number' && 
            !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret)) {
          allPoints.push({ risk, return: ret });
        }
      }
      
      if (mvoResults?.optimized_portfolio?.metrics) {
        const risk = mvoResults.optimized_portfolio.metrics.risk;
        const ret = mvoResults.optimized_portfolio.metrics.expected_return;
        if (typeof risk === 'number' && typeof ret === 'number' && 
            !isNaN(risk) && !isNaN(ret) && isFinite(risk) && isFinite(ret)) {
          allPoints.push({ risk, return: ret });
        }
      }
      
      if (allPoints.length === 0) return null;
      
      const risks = allPoints.map(p => p.risk).filter(r => isFinite(r));
      const returns = allPoints.map(p => p.return).filter(r => isFinite(r));
      
      if (risks.length === 0 || returns.length === 0) return null;
      
      const minRisk = Math.min(...risks);
      const maxRisk = Math.max(...risks);
      const minRet = Math.min(...returns);
      const maxRet = Math.max(...returns);
      
      if (!isFinite(minRisk) || !isFinite(maxRisk) || !isFinite(minRet) || !isFinite(maxRet)) {
        return null;
      }
      
      // Ensure there's a valid range
      const riskRange = maxRisk - minRisk;
      const retRange = maxRet - minRet;
      
      if (riskRange <= 0 || retRange <= 0) return null;
      
      return {
        x: [Math.max(0, minRisk * 0.9), maxRisk * 1.1] as [number, number],
        y: [Math.max(0, minRet * 0.9), maxRet * 1.1] as [number, number],
      };
    } catch (error) {
      console.error('Error calculating efficientFrontierDomain:', error);
      return null;
    }
  }, [randomPortfolios, efficientFrontier, mvoResults]);

  // Zoom handlers for eligible tickers
  const handleEligibleTickersZoom = useCallback((delta: number, centerX?: number, centerY?: number) => {
    try {
      if (!eligibleTickersDomain || !eligibleTickersDomain.x || !eligibleTickersDomain.y) {
        return;
      }
      
      const currentZoom = eligibleTickersZoom || { 
        x: eligibleTickersDomain.x, 
        y: eligibleTickersDomain.y, 
        zoomLevel: 1 
      };
      
      // Validate current zoom values
      if (!currentZoom.x || !currentZoom.y || 
          !Array.isArray(currentZoom.x) || !Array.isArray(currentZoom.y) ||
          currentZoom.x.length !== 2 || currentZoom.y.length !== 2 ||
          !isFinite(currentZoom.x[0]) || !isFinite(currentZoom.x[1]) ||
          !isFinite(currentZoom.y[0]) || !isFinite(currentZoom.y[1])) {
        return;
      }
      
      const zoomFactor = delta > 0 ? 1.2 : 0.8;
      const newZoomLevel = Math.max(0.5, Math.min(5, (currentZoom.zoomLevel || 1) * zoomFactor));
      
      const xRange = currentZoom.x[1] - currentZoom.x[0];
      const yRange = currentZoom.y[1] - currentZoom.y[0];
      
      if (!isFinite(xRange) || !isFinite(yRange) || xRange <= 0 || yRange <= 0) {
        return;
      }
      
      const newXRange = xRange / zoomFactor;
      const newYRange = yRange / zoomFactor;
      
      let newX: [number, number];
      let newY: [number, number];
      
      if (centerX !== undefined && centerY !== undefined && 
          isFinite(centerX) && isFinite(centerY)) {
        // Zoom towards mouse position
        const xCenter = currentZoom.x[0] + (centerX * xRange);
        const yCenter = currentZoom.y[0] + (centerY * yRange);
        newX = [Math.max(0, xCenter - newXRange / 2), xCenter + newXRange / 2] as [number, number];
        newY = [Math.max(0, yCenter - newYRange / 2), yCenter + newYRange / 2] as [number, number];
      } else {
        // Zoom towards center
        const xCenter = (currentZoom.x[0] + currentZoom.x[1]) / 2;
        const yCenter = (currentZoom.y[0] + currentZoom.y[1]) / 2;
        newX = [Math.max(0, xCenter - newXRange / 2), xCenter + newXRange / 2] as [number, number];
        newY = [Math.max(0, yCenter - newYRange / 2), yCenter + newYRange / 2] as [number, number];
      }
      
      // Validate new zoom values before setting
      if (isFinite(newX[0]) && isFinite(newX[1]) && isFinite(newY[0]) && isFinite(newY[1]) &&
          newX[0] < newX[1] && newY[0] < newY[1]) {
        setEligibleTickersZoom({ x: newX, y: newY, zoomLevel: newZoomLevel });
      }
    } catch (error) {
      console.error('Error in handleEligibleTickersZoom:', error);
    }
  }, [eligibleTickersDomain, eligibleTickersZoom]);

  const handleEligibleTickersReset = useCallback(() => {
    setEligibleTickersZoom(null);
  }, []);

  // Zoom handlers for efficient frontier
  const handleEfficientFrontierZoom = useCallback((delta: number, centerX?: number, centerY?: number) => {
    try {
      if (!efficientFrontierDomain || !efficientFrontierDomain.x || !efficientFrontierDomain.y) {
        return;
      }
      
      const currentZoom = efficientFrontierZoom || { 
        x: efficientFrontierDomain.x, 
        y: efficientFrontierDomain.y, 
        zoomLevel: 1 
      };
      
      // Validate current zoom values
      if (!currentZoom.x || !currentZoom.y || 
          !Array.isArray(currentZoom.x) || !Array.isArray(currentZoom.y) ||
          currentZoom.x.length !== 2 || currentZoom.y.length !== 2 ||
          !isFinite(currentZoom.x[0]) || !isFinite(currentZoom.x[1]) ||
          !isFinite(currentZoom.y[0]) || !isFinite(currentZoom.y[1])) {
        return;
      }
      
      const zoomFactor = delta > 0 ? 1.2 : 0.8;
      const newZoomLevel = Math.max(0.5, Math.min(5, (currentZoom.zoomLevel || 1) * zoomFactor));
      
      const xRange = currentZoom.x[1] - currentZoom.x[0];
      const yRange = currentZoom.y[1] - currentZoom.y[0];
      
      if (!isFinite(xRange) || !isFinite(yRange) || xRange <= 0 || yRange <= 0) {
        return;
      }
      
      const newXRange = xRange / zoomFactor;
      const newYRange = yRange / zoomFactor;
      
      let newX: [number, number];
      let newY: [number, number];
      
      if (centerX !== undefined && centerY !== undefined && 
          isFinite(centerX) && isFinite(centerY)) {
        const xCenter = currentZoom.x[0] + (centerX * xRange);
        const yCenter = currentZoom.y[0] + (centerY * yRange);
        newX = [Math.max(0, xCenter - newXRange / 2), xCenter + newXRange / 2] as [number, number];
        newY = [Math.max(0, yCenter - newYRange / 2), yCenter + newYRange / 2] as [number, number];
      } else {
        const xCenter = (currentZoom.x[0] + currentZoom.x[1]) / 2;
        const yCenter = (currentZoom.y[0] + currentZoom.y[1]) / 2;
        newX = [Math.max(0, xCenter - newXRange / 2), xCenter + newXRange / 2] as [number, number];
        newY = [Math.max(0, yCenter - newYRange / 2), yCenter + newYRange / 2] as [number, number];
      }
      
      // Validate new zoom values before setting
      if (isFinite(newX[0]) && isFinite(newX[1]) && isFinite(newY[0]) && isFinite(newY[1]) &&
          newX[0] < newX[1] && newY[0] < newY[1]) {
        setEfficientFrontierZoom({ x: newX, y: newY, zoomLevel: newZoomLevel });
      }
    } catch (error) {
      console.error('Error in handleEfficientFrontierZoom:', error);
    }
  }, [efficientFrontierDomain, efficientFrontierZoom]);

  const handleEfficientFrontierReset = useCallback(() => {
    setEfficientFrontierZoom(null);
  }, []);

  const [currentMetrics, setCurrentMetrics] = useState<any>(null);

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

  // Fetch current portfolio metrics when portfolio changes
  useEffect(() => {
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
  }, [currentPortfolio, calculateCurrentMetrics]);

  // Fetch all eligible tickers (no risk profile filter) for initial state
  useEffect(() => {
    const fetchEligibleTickers = async () => {
      setIsLoadingEligibleTickers(true);
      setError(null);
      
      try {
        // Fetch all eligible tickers without risk profile filtering
        const params = new URLSearchParams({
          min_data_points: '12',
          filter_negative_returns: 'true',
          per_page: '500', // Get more tickers for visualization
          page: '1'
        });
        
        const response = await fetch(API_ENDPOINTS.ELIGIBLE_TICKERS(params.toString()));
        
        if (!response.ok) {
          throw new Error(`Failed to fetch eligible tickers: ${response.statusText}`);
        }
        
        const data = await response.json();
        const tickers = data.eligible_tickers || [];
        
        // Transform to our format
        const formattedTickers: EligibleTicker[] = tickers.map((t: any) => ({
          ticker: t.ticker || t.symbol,
          expected_return: t.expected_return || 0,
          volatility: t.volatility || 0,
          sector: t.sector,
          company_name: t.company_name
        }));
        
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

  // Run portfolio optimization using MVO endpoint
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
      
      // Prepare current portfolio weights for comparison
      const currentWeights: Record<string, number> = {};
      currentPortfolio.forEach(stock => {
        currentWeights[stock.symbol] = stock.allocation / 100;
      });
      
      // Call MVO optimization API with risk profile constraint
      const response = await fetch(API_ENDPOINTS.OPTIMIZE_MVO, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tickers: tickers,
          optimization_type: 'max_sharpe',
          risk_profile: riskProfile, // Apply risk profile constraint
          current_portfolio: {
            weights: currentWeights
          },
          include_efficient_frontier: true,
          include_random_portfolios: true,
          num_frontier_points: 20,
          num_random_portfolios: 200
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Optimization failed: ${response.statusText}`);
      }
      
      const data: MVOOptimizationResponse = await response.json();
      
      // Store MVO results
      setMvoResults(data);
      
      // Convert optimized portfolio to allocations format
      const optimizedAllocations: PortfolioAllocation[] = [];
      const optPortfolio = data.optimized_portfolio;
      
      optPortfolio.tickers.forEach((ticker, index) => {
        const weight = optPortfolio.weights[ticker] || 0;
        if (weight > 0.001) { // Only include significant weights
          const originalStock = currentPortfolio.find(s => s.symbol === ticker);
          optimizedAllocations.push({
            symbol: ticker,
            allocation: Math.round(weight * 100 * 10) / 10, // Round to 1 decimal
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
        diversificationScore: 0 // Will be calculated separately if needed
      });
      
      // Set efficient frontier
      if (data.efficient_frontier && data.efficient_frontier.length > 0) {
        setEfficientFrontier(data.efficient_frontier.map((point) => ({
          risk: point.risk,
          return: point.return,
          weights: point.weights_list || [],
          sharpe_ratio: point.sharpe_ratio,
          type: 'frontier' as const
        })));
      }
      
      // Set random portfolios
      if (data.random_portfolios && data.random_portfolios.length > 0) {
        setRandomPortfolios(data.random_portfolios.map((point) => ({
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
      console.error('Optimization error:', err);
      setError(err.message || 'Failed to run portfolio optimization. Please try again.');
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
    <div className="max-w-6xl mx-auto p-6">
      <Card>
        <CardHeader className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-primary flex items-center justify-center">
            <BarChart3 className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Portfolio Optimization</CardTitle>
          <p className="text-muted-foreground">
            Optimize your {capital ? capital.toLocaleString() : '0'} SEK portfolio for better risk-return balance
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Risk Profile: {getRiskProfileDisplay()}
            </span>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <Info className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="optimization" className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                Optimization
              </TabsTrigger>
              <TabsTrigger value="analysis" className="flex items-center gap-2">
                <LineChart className="h-4 w-4" />
                Analysis
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4" />
                Recommendations
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="h-5 w-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-blue-900">Portfolio Optimization</h3>
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
                      <div className="text-center p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg border border-emerald-200">
                        <div className="text-xl font-bold text-emerald-700">
                          {((currentMetrics.expectedReturn || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-emerald-600 mt-0.5">Expected Return</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
                        <div className="text-xl font-bold text-amber-700">
                          {((currentMetrics.risk || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-amber-600 mt-0.5">Risk Level</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
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
                  background: visualizationTheme.canvas,
                  padding: visualizationTheme.spacing.cardPadding,
                  borderRadius: visualizationTheme.radius,
                }}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3
                      className="text-lg font-semibold mb-1"
                      style={{ color: visualizationTheme.text.primary }}
                    >
                      Portfolio Optimization
                    </h3>
                    <p
                      className="text-sm"
                      style={{ color: visualizationTheme.text.secondary }}
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
                            per_page: '500',
                            page: '1'
                          });
                          const response = await fetch(API_ENDPOINTS.ELIGIBLE_TICKERS(params.toString()));
                          if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`);
                          const data = await response.json();
                          const tickers = data.eligible_tickers || [];
                          const formattedTickers: EligibleTicker[] = tickers.map((t: any) => ({
                            ticker: t.ticker || t.symbol,
                            expected_return: t.expected_return || 0,
                            volatility: t.volatility || 0,
                            sector: t.sector,
                            company_name: t.company_name
                          }));
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
                    style={{ borderColor: visualizationTheme.border, color: visualizationTheme.text.primary }}
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
                  style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
                >
                  <CardHeader className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <CardTitle
                        className="text-lg flex-1"
                        style={{ color: visualizationTheme.text.primary, textAlign: 'center', fontWeight: 600, letterSpacing: '-0.01em' }}
                      >
                        Return vs. Risk Tradeoff
                      </CardTitle>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEligibleTickersZoom(1)}
                          className="h-7 px-2 text-xs"
                          title="Zoom in"
                          disabled={!eligibleTickersDomain}
                        >
                          <ZoomIn className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEligibleTickersZoom(-1)}
                          className="h-7 px-2 text-xs"
                          title="Zoom out"
                          disabled={!eligibleTickersDomain}
                        >
                          <ZoomOut className="h-3.5 w-3.5" />
                        </Button>
                        {eligibleTickersZoom && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleEligibleTickersReset}
                            className="h-7 px-2 text-xs"
                            title="Reset zoom"
                          >
                            <RotateCcw className="h-3.5 w-3.5 mr-1" />
                            Reset
                          </Button>
                        )}
                      </div>
                    </div>
                    <p
                      className="text-xs text-center"
                      style={{ color: visualizationTheme.text.secondary }}
                    >
                      X-axis: Risk (Volatility) | Y-axis: Expected Return
                      <span className="block mt-1 text-xs" style={{ color: visualizationTheme.text.secondary, opacity: 0.7 }}>
                        💡 Use mouse wheel to zoom, or click zoom buttons
                      </span>
                    </p>
                  </CardHeader>
                  <CardContent
                    className="h-[420px]"
                    style={{
                      background: visualizationTheme.canvas,
                      borderRadius: visualizationTheme.radius,
                      padding: '12px',
                    }}
                  >
                    {isLoadingEligibleTickers ? (
                      <div className="flex h-full items-center justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      </div>
                    ) : eligibleTickers && Array.isArray(eligibleTickers) && eligibleTickers.length > 0 ? (
                      <div 
                        className="w-full h-full"
                        onWheel={(e) => {
                          if (eligibleTickersDomain && eligibleTickers && eligibleTickers.length > 0) {
                            e.preventDefault();
                            const delta = e.deltaY > 0 ? -1 : 1;
                            handleEligibleTickersZoom(delta);
                          }
                        }}
                        style={{ cursor: eligibleTickersDomain ? 'grab' : 'default' }}
                      >
                        <ResponsiveContainer width="100%" height="100%">
                          <ScatterChart
                            margin={{ top: 24, right: 32, bottom: 24, left: 48 }}
                          >
                          <CartesianGrid strokeDasharray="3 4" stroke={visualizationTheme.grid} />
                          <XAxis
                            type="number"
                            dataKey="volatility"
                            name="Risk"
                            tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                            axisLine={{ stroke: visualizationTheme.axes.line }}
                            tickLine={{ stroke: 'transparent' }}
                            tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                            domain={eligibleTickersZoom?.x || eligibleTickersDomain?.x || [0, 'auto']}
                            label={{
                              value: 'Risk',
                              position: 'insideBottom',
                              offset: -6,
                              style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                            }}
                          />
                          <YAxis
                            type="number"
                            dataKey="expected_return"
                            name="Return"
                            tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                            axisLine={{ stroke: visualizationTheme.axes.line }}
                            tickLine={{ stroke: 'transparent' }}
                            tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                            domain={eligibleTickersZoom?.y || eligibleTickersDomain?.y || [0, 'auto']}
                            label={{
                              value: 'Return',
                              angle: -90,
                              position: 'insideLeft',
                              style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                            }}
                          />
                          <RechartsTooltip
                            cursor={{ strokeDasharray: '3 3' }}
                            content={({ active, payload }: TooltipProps<ValueType, NameType>) => {
                              if (active && payload && payload.length) {
                                const data = payload[0].payload as EligibleTicker & { isSelected?: boolean };
                                return (
                                  <div
                                    className="rounded-xl border p-3 shadow-sm max-w-xs"
                                    style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
                                  >
                                    <p className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                                      {data.ticker}
                                    </p>
                                    {data.company_name && (
                                      <p className="text-sm mt-1" style={{ color: visualizationTheme.text.secondary }}>
                                        {data.company_name}
                                      </p>
                                    )}
                                    <div className="mt-2 space-y-1 text-sm" style={{ color: visualizationTheme.text.primary }}>
                                      <p>
                                        Return:{' '}
                                        <span className="font-medium">{formatPercent(data.expected_return)}</span>
                                      </p>
                                      <p>
                                        Risk:{' '}
                                        <span className="font-medium">{formatPercent(data.volatility)}</span>
                                      </p>
                                      {data.sector && (
                                        <p className="text-xs mt-1" style={{ color: visualizationTheme.text.secondary }}>
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
                              fontSize: visualizationTheme.legend.fontSize,
                              color: visualizationTheme.legend.color,
                            }}
                          />
                          
                          {/* All eligible tickers (gray dots) */}
                          <Scatter
                            name="Eligible Tickers"
                            data={(eligibleTickers || []).filter(t => {
                              if (!t || !t.ticker) return false;
                              if (!currentPortfolio || !Array.isArray(currentPortfolio)) return true;
                              return !currentPortfolio.some(s => s && s.symbol === t.ticker);
                            }).map(t => ({
                              volatility: t.volatility || 0,
                              expected_return: t.expected_return || 0,
                              ticker: t.ticker,
                              company_name: t.company_name,
                              sector: t.sector,
                              isSelected: false
                            }))}
                            fill="#94a3b8"
                            fillOpacity={0.6}
                            shape={(props) => {
                              const radius = 5.5;
                              return (
                                <circle
                                  cx={props.cx}
                                  cy={props.cy}
                                  r={radius}
                                  fill="#94a3b8"
                                  fillOpacity={0.6}
                                  stroke="#64748b"
                                  strokeOpacity={0.7}
                                  strokeWidth={1.6}
                                />
                              );
                            }}
                          />
                          
                          {/* Selected portfolio tickers (highlighted) */}
                          {currentPortfolio && Array.isArray(currentPortfolio) && currentPortfolio.length > 0 && (
                            <Scatter
                              name="Your Portfolio"
                              data={(eligibleTickers || [])
                                .filter(t => {
                                  if (!t || !t.ticker) return false;
                                  if (!currentPortfolio || !Array.isArray(currentPortfolio)) return false;
                                  return currentPortfolio.some(s => s && s.symbol === t.ticker);
                                })
                                .map(t => ({
                                  volatility: t.volatility || 0,
                                  expected_return: t.expected_return || 0,
                                  ticker: t.ticker,
                                  company_name: t.company_name,
                                  sector: t.sector,
                                  isSelected: true
                                }))}
                              fill="#2563eb"
                              fillOpacity={0.85}
                              shape={(props) => {
                                const radius = 6.5;
                                return (
                                  <circle
                                    cx={props.cx}
                                    cy={props.cy}
                                    r={radius}
                                    fill="#2563eb"
                                    fillOpacity={0.85}
                                    stroke="#1d4ed8"
                                    strokeOpacity={0.9}
                                    strokeWidth={2}
                                  />
                                );
                              }}
                            />
                          )}
                        </ScatterChart>
                      </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                        <div className="text-center">
                          <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>No eligible tickers available</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                  
                  {/* Legend and Optimize Button */}
                  <div className="px-6 pb-6 space-y-4">
                    <div className="flex flex-wrap gap-4 text-xs justify-center">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-slate-400"></div>
                        <span style={{ color: visualizationTheme.text.secondary }}>
                          Eligible Tickers ({(eligibleTickers || []).length})
                        </span>
                      </div>
                      {currentPortfolio && Array.isArray(currentPortfolio) && currentPortfolio.length > 0 && (
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <span style={{ color: visualizationTheme.text.secondary }}>
                            Your Portfolio ({currentPortfolio.length} tickers)
                          </span>
                        </div>
                      )}
                    </div>
                    
                    {/* Optimize Button */}
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
                      <p className="text-sm text-center" style={{ color: visualizationTheme.text.secondary }}>
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
                  background: visualizationTheme.canvas,
                  padding: visualizationTheme.spacing.cardPadding,
                  borderRadius: visualizationTheme.radius,
                }}
              >
                <div>
                  <h3
                    className="text-lg font-semibold mb-1"
                    style={{ color: visualizationTheme.text.primary }}
                  >
                    Portfolio Analysis
                  </h3>
                  <p
                    className="text-sm"
                    style={{ color: visualizationTheme.text.secondary }}
                  >
                    Efficient frontier visualization with risk-return optimization results
                  </p>
                </div>

                <Card
                  className="w-full"
                  style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
                >
                  <CardHeader className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <CardTitle
                        className="text-lg flex-1"
                        style={{ color: visualizationTheme.text.primary, textAlign: 'center', fontWeight: 600, letterSpacing: '-0.01em' }}
                      >
                        Efficient Frontier Analysis
                      </CardTitle>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEfficientFrontierZoom(1)}
                          className="h-7 px-2 text-xs"
                          title="Zoom in"
                          disabled={!efficientFrontierDomain}
                        >
                          <ZoomIn className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEfficientFrontierZoom(-1)}
                          className="h-7 px-2 text-xs"
                          title="Zoom out"
                          disabled={!efficientFrontierDomain}
                        >
                          <ZoomOut className="h-3.5 w-3.5" />
                        </Button>
                        {efficientFrontierZoom && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleEfficientFrontierReset}
                            className="h-7 px-2 text-xs"
                            title="Reset zoom"
                          >
                            <RotateCcw className="h-3.5 w-3.5 mr-1" />
                            Reset
                          </Button>
                        )}
                      </div>
                    </div>
                    <p
                      className="text-xs text-center"
                      style={{ color: visualizationTheme.text.secondary }}
                    >
                      X-axis: Risk (Volatility) | Y-axis: Expected Return
                      <span className="block mt-1 text-xs" style={{ color: visualizationTheme.text.secondary, opacity: 0.7 }}>
                        💡 Use mouse wheel to zoom, or click zoom buttons
                      </span>
                    </p>
                  </CardHeader>
                  <CardContent
                    className="h-[420px]"
                    style={{
                      background: visualizationTheme.canvas,
                      borderRadius: visualizationTheme.radius,
                      padding: '12px',
                    }}
                  >
                    {mvoResults && (efficientFrontier.length > 0 || randomPortfolios.length > 0) ? (
                      <>
                        {/* Risk Profile Zone Helper */}
                        {(() => {
                          const riskProfileMaxRisk: Record<string, number> = {
                            'very-conservative': 0.08,
                            'conservative': 0.12,
                            'moderate': 0.16,
                            'aggressive': 0.22,
                            'very-aggressive': 0.28
                          };
                          const maxRisk = riskProfileMaxRisk[riskProfile] || 0.16;
                          
                          return (
                            <div
                              className="mb-4 rounded-lg p-3 border"
                              style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}
                            >
                              <div className="flex items-center gap-2 mb-2">
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
                        
                        <div 
                          className="w-full h-full"
                          onWheel={(e) => {
                            if (efficientFrontierDomain && (efficientFrontier.length > 0 || randomPortfolios.length > 0)) {
                              e.preventDefault();
                              const delta = e.deltaY > 0 ? -1 : 1;
                              handleEfficientFrontierZoom(delta);
                            }
                          }}
                          style={{ cursor: efficientFrontierDomain ? 'grab' : 'default' }}
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart
                              margin={{ top: 24, right: 32, bottom: 24, left: 48 }}
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
                              domain={efficientFrontierZoom?.x || efficientFrontierDomain?.x || [0, 'auto']}
                              label={{
                                value: 'Risk',
                                position: 'insideBottom',
                                offset: -6,
                                style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                              }}
                            />
                            <YAxis
                              type="number"
                              dataKey="return"
                              name="Return"
                              tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                              axisLine={{ stroke: visualizationTheme.axes.line }}
                              tickLine={{ stroke: 'transparent' }}
                              tick={{ fill: visualizationTheme.axes.tick, fontSize: 12, fontWeight: 500 }}
                              domain={efficientFrontierZoom?.y || efficientFrontierDomain?.y || [0, 'auto']}
                              label={{
                                value: 'Return',
                                angle: -90,
                                position: 'insideLeft',
                                style: { fill: visualizationTheme.axes.label, fontWeight: 500 },
                              }}
                            />
                            <RechartsTooltip
                              cursor={{ strokeDasharray: '3 3' }}
                              content={({ active, payload }: TooltipProps<ValueType, NameType>) => {
                                if (active && payload && payload.length) {
                                  const data = payload[0].payload as EfficientFrontierPoint;
                                  return (
                                    <div
                                      className="rounded-xl border p-3 shadow-sm max-w-xs"
                                      style={{ background: visualizationTheme.cardBackground, borderColor: visualizationTheme.border }}
                                    >
                                      <p className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                                        {data.type === 'current' ? 'Current Portfolio' :
                                         data.type === 'optimized' ? 'Optimized Portfolio' :
                                         data.type === 'frontier' ? 'Efficient Frontier' :
                                         'Random Portfolio'}
                                      </p>
                                      <div className="mt-2 space-y-1 text-sm" style={{ color: visualizationTheme.text.primary }}>
                                        <p>
                                          Return:{' '}
                                          <span className="font-medium">{formatPercent(data.return)}</span>
                                        </p>
                                        <p>
                                          Risk:{' '}
                                          <span className="font-medium">{formatPercent(data.risk)}</span>
                                        </p>
                                        {data.sharpe_ratio !== undefined && (
                                          <p>
                                            Sharpe:{' '}
                                            <span className="font-medium">{data.sharpe_ratio.toFixed(2)}</span>
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
                                fontSize: visualizationTheme.legend.fontSize,
                                color: visualizationTheme.legend.color,
                              }}
                            />
                            
                            {/* Random Portfolios (background scatter) */}
                            {randomPortfolios.length > 0 && (
                              <Scatter
                                name="Random Portfolios"
                                data={randomPortfolios}
                                fill="#e2e8f0"
                                fillOpacity={0.4}
                                shape={(props) => {
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={4}
                                      fill="#e2e8f0"
                                      fillOpacity={0.4}
                                    />
                                  );
                                }}
                              />
                            )}
                            
                            {/* Efficient Frontier (line/curve) */}
                            {efficientFrontier.length > 0 && (
                              <Scatter
                                name="Efficient Frontier"
                                data={efficientFrontier}
                                fill="#64748b"
                                fillOpacity={0.8}
                                shape={(props) => {
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={5}
                                      fill="#64748b"
                                      fillOpacity={0.8}
                                      stroke="#475569"
                                      strokeWidth={1.5}
                                    />
                                  );
                                }}
                              />
                            )}
                            
                            {/* Current Portfolio */}
                            {mvoResults.current_portfolio && (
                              <Scatter
                                name="Current Portfolio"
                                data={[{
                                  risk: mvoResults.current_portfolio.metrics.risk,
                                  return: mvoResults.current_portfolio.metrics.expected_return,
                                  sharpe_ratio: mvoResults.current_portfolio.metrics.sharpe_ratio,
                                  type: 'current' as const
                                }]}
                                fill="#ef4444"
                                fillOpacity={1}
                                shape={(props) => {
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={7}
                                      fill="#ef4444"
                                      fillOpacity={1}
                                      stroke="#dc2626"
                                      strokeWidth={2.5}
                                    />
                                  );
                                }}
                              />
                            )}
                            
                            {/* Optimized Portfolio */}
                            {mvoResults.optimized_portfolio && (
                              <Scatter
                                name="Optimized Portfolio"
                                data={[{
                                  risk: mvoResults.optimized_portfolio.metrics.risk,
                                  return: mvoResults.optimized_portfolio.metrics.expected_return,
                                  sharpe_ratio: mvoResults.optimized_portfolio.metrics.sharpe_ratio,
                                  type: 'optimized' as const
                                }]}
                                fill="#22c55e"
                                fillOpacity={1}
                                shape={(props) => {
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={7}
                                      fill="#22c55e"
                                      fillOpacity={1}
                                      stroke="#16a34a"
                                      strokeWidth={2.5}
                                    />
                                  );
                                }}
                              />
                            )}
                          </ScatterChart>
                        </ResponsiveContainer>
                        </div>
                      </>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm" style={{ color: visualizationTheme.text.secondary }}>
                        <div className="text-center">
                          <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>Run portfolio optimization to generate efficient frontier analysis.</p>
                          <p className="text-xs mt-2">Click the "Optimize" button in the Optimization tab to get started.</p>
                        </div>
                      </div>
                    )}
                    
                    {/* Legend and Results Summary */}
                    {mvoResults && (efficientFrontier.length > 0 || randomPortfolios.length > 0) ? (
                      <div className="px-6 pb-6 space-y-4">
                      <div className="flex flex-wrap gap-4 text-xs justify-center">
                        {randomPortfolios.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-slate-300"></div>
                            <span style={{ color: visualizationTheme.text.secondary }}>
                              Random Portfolios ({randomPortfolios.length})
                            </span>
                          </div>
                        )}
                        {efficientFrontier.length > 0 && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-slate-500"></div>
                            <span style={{ color: visualizationTheme.text.secondary }}>
                              Efficient Frontier ({efficientFrontier.length} points)
                            </span>
                          </div>
                        )}
                        {mvoResults.current_portfolio && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-red-500"></div>
                            <span style={{ color: visualizationTheme.text.secondary }}>Current Portfolio</span>
                          </div>
                        )}
                        {mvoResults.optimized_portfolio && (
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-green-500"></div>
                            <span style={{ color: visualizationTheme.text.secondary }}>Optimized Portfolio</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Optimization Results Summary */}
                      {mvoResults.optimized_portfolio && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6 pt-6" style={{ borderTop: `1px solid ${visualizationTheme.border}` }}>
                          <div className="text-center p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg border border-emerald-200">
                            <div className="text-xl font-bold text-emerald-700">
                              {(mvoResults.optimized_portfolio.metrics.expected_return * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-emerald-600 mt-0.5">Optimized Return</div>
                          </div>
                          <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
                            <div className="text-xl font-bold text-amber-700">
                              {(mvoResults.optimized_portfolio.metrics.risk * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-amber-600 mt-0.5">Optimized Risk</div>
                          </div>
                          <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
                            <div className="text-xl font-bold text-purple-700">
                              {mvoResults.optimized_portfolio.metrics.sharpe_ratio.toFixed(2)}
                            </div>
                            <div className="text-xs text-purple-600 mt-0.5">Sharpe Ratio</div>
                          </div>
                        </div>
                      )}
                      
                      {/* Improvements */}
                      {mvoResults.improvements && (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <h5 className="font-medium text-green-900 mb-2">Optimization Improvements</h5>
                          <div className="grid grid-cols-3 gap-3 text-sm">
                            {mvoResults.improvements.return_improvement > 0 && (
                              <div>
                                <span className="text-green-700 font-medium">
                                  +{(mvoResults.improvements.return_improvement * 100).toFixed(1)}%
                                </span>
                                <span className="text-green-600 ml-1">Return</span>
                              </div>
                            )}
                            {mvoResults.improvements.risk_improvement > 0 && (
                              <div>
                                <span className="text-green-700 font-medium">
                                  -{(mvoResults.improvements.risk_improvement * 100).toFixed(1)}%
                                </span>
                                <span className="text-green-600 ml-1">Risk</span>
                              </div>
                            )}
                            {mvoResults.improvements.sharpe_improvement > 0 && (
                              <div>
                                <span className="text-green-700 font-medium">
                                  +{mvoResults.improvements.sharpe_improvement.toFixed(2)}
                                </span>
                                <span className="text-green-600 ml-1">Sharpe</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* Optimized Portfolio Allocations */}
                      {optimizedPortfolio.length > 0 && (
                        <div className="space-y-4 mt-6">
                          <h5 className="font-medium">Optimized Portfolio Allocations</h5>
                          {optimizedPortfolio.map((stock, index) => (
                            <div key={stock.symbol} className="flex items-center justify-between p-3 border rounded-lg">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                  <span className="text-sm font-medium text-green-600">{index + 1}</span>
                                </div>
                                <div>
                                  <div className="font-medium">{stock.symbol}</div>
                                  <div className="text-sm text-muted-foreground">{stock.name || 'Stock'}</div>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-semibold">{stock.allocation}%</div>
                                <div className="text-sm text-muted-foreground">
                                  {(stock.allocation / 100 * capital).toLocaleString()} SEK
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      </div>
                    ) : null}
                  </CardContent>
              </Card>
              </div>
            </TabsContent>

            {/* Recommendations Tab */}
            <TabsContent value="recommendations" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Optimization Recommendations</h3>
                <p className="text-muted-foreground">
                  Actionable insights to improve your portfolio's performance
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Key Recommendations</CardTitle>
                  <p className="text-muted-foreground">
                    Based on your risk profile and current portfolio
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h4 className="font-medium text-green-700">Immediate Actions</h4>
                      <div className="space-y-3">
                        <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                          <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                          <div>
                            <div className="font-medium text-green-800">Run Optimization</div>
                            <div className="text-sm text-green-700">
                              Use our algorithm to find better allocations
                            </div>
                          </div>
                        </div>
                        <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                          <div>
                            <div className="font-medium text-blue-800">Review Diversification</div>
                            <div className="text-sm text-blue-700">
                              Ensure proper sector and asset class balance
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <h4 className="font-medium text-orange-700">Long-term Strategy</h4>
                      <div className="space-y-3">
                        <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
                          <Target className="h-5 w-5 text-orange-600 mt-0.5" />
                          <div>
                            <div className="font-medium text-orange-800">Rebalancing Schedule</div>
                            <div className="text-sm text-orange-700">
                              Plan quarterly portfolio reviews
                            </div>
                          </div>
                        </div>
                        <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                          <TrendingUp className="h-5 w-5 text-purple-600 mt-0.5" />
                          <div>
                            <div className="font-medium text-purple-800">Performance Tracking</div>
                            <div className="text-sm text-purple-700">
                              Monitor against benchmarks regularly
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Risk Profile Specific Recommendations */}
                  <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-6 border border-indigo-200">
                    <h4 className="font-medium text-indigo-900 mb-3">
                      Recommendations for {getRiskProfileDisplay()} Investors
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
            </TabsContent>
          </Tabs>

          {/* Navigation */}
          <div className="flex justify-between pt-6">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={onNext}
              disabled={!currentPortfolio || currentPortfolio.length < 3}
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
