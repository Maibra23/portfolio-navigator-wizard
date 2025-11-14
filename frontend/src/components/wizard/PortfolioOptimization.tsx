/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  Minimize2
} from 'lucide-react';

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
  type: 'current' | 'optimized' | 'frontier';
}

export const PortfolioOptimization = ({ 
  onNext, 
  onPrev, 
  selectedStocks, 
  riskProfile, 
  capital 
}: PortfolioOptimizationProps) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'optimization' | 'analysis' | 'recommendations'>('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResult | null>(null);
  const [efficientFrontier, setEfficientFrontier] = useState<EfficientFrontierPoint[]>([]);
  const [currentPortfolio, setCurrentPortfolio] = useState<PortfolioAllocation[]>(selectedStocks);
  const [optimizedPortfolio, setOptimizedPortfolio] = useState<PortfolioAllocation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Calculate current portfolio metrics
  const calculateCurrentMetrics = async () => {
    if (currentPortfolio.length === 0) return null;
    
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
  };

  const [currentMetrics, setCurrentMetrics] = useState<any>(null);

  // Fetch current portfolio metrics when portfolio changes
  useEffect(() => {
    const fetchMetrics = async () => {
      if (currentPortfolio.length > 0) {
        const metrics = await calculateCurrentMetrics();
        setCurrentMetrics(metrics);
      }
    };
    
    fetchMetrics();
  }, [currentPortfolio]);

  // Generate efficient frontier points
  const generateEfficientFrontier = () => {
    if (currentPortfolio.length < 3) return [];
    
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

  // Run portfolio optimization
  const runOptimization = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Call backend optimization API
      const response = await fetch('/api/portfolio/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          allocations: currentPortfolio,
          riskProfile: riskProfile,
          optimizationType: 'mean-variance'
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Optimization failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Set optimized portfolio
      setOptimizedPortfolio(data.optimizedAllocations);
      
      // Set optimization results
      setOptimizationResults({
        weights: data.optimizedMetrics.expectedReturn,
        expectedReturn: data.optimizedMetrics.expectedReturn,
        risk: data.optimizedMetrics.risk,
        diversificationScore: data.optimizedMetrics.diversificationScore
      });
      
      // Set efficient frontier
      if (data.efficientFrontier && data.efficientFrontier.length > 0) {
        setEfficientFrontier(data.efficientFrontier.map((point: any) => ({
          risk: point.risk,
          return: point.return,
          weights: point.weights,
          type: point.type || 'frontier'
        })));
      }
      
      setSuccessMessage('Portfolio optimization completed successfully!');
      
    } catch (err) {
      console.error('Optimization error:', err);
      setError('Failed to run portfolio optimization. Please try again.');
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
            Optimize your {capital.toLocaleString()} SEK portfolio for better risk-return balance
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
                    {currentPortfolio.length} assets selected
                  </p>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
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
                            {(stock.allocation / 100 * capital).toLocaleString()} SEK
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {currentMetrics && (
                    <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-border/50">
                      <div className="text-center p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg border border-emerald-200">
                        <div className="text-xl font-bold text-emerald-700">
                          {(currentMetrics.expectedReturn * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-emerald-600 mt-0.5">Expected Return</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
                        <div className="text-xl font-bold text-amber-700">
                          {(currentMetrics.risk * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-amber-600 mt-0.5">Risk Level</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
                        <div className="text-xl font-bold text-purple-700">
                          {currentMetrics.diversificationScore.toFixed(0)}%
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
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Portfolio Optimization Engine</h3>
                <p className="text-muted-foreground">
                  Run advanced optimization algorithms to improve your portfolio's efficiency
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Optimization Controls</CardTitle>
                  <p className="text-muted-foreground">
                    Choose your optimization strategy and run the analysis
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex gap-4 flex-wrap">
                    <Button
                      onClick={runOptimization}
                      disabled={isLoading || currentPortfolio.length < 3}
                      className="flex items-center gap-2"
                    >
                      {isLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Optimizing...
                        </>
                      ) : (
                        <>
                          <Zap className="h-4 w-4" />
                          Run Optimization
                        </>
                      )}
                    </Button>
                    
                    {optimizedPortfolio.length > 0 && (
                      <>
                        <Button
                          onClick={applyOptimization}
                          variant="default"
                          className="flex items-center gap-2"
                        >
                          <CheckCircle className="h-4 w-4" />
                          Apply Optimization
                        </Button>
                        <Button
                          onClick={resetToOriginal}
                          variant="outline"
                          className="flex items-center gap-2"
                        >
                          <RotateCcw className="h-4 w-4" />
                          Reset to Original
                        </Button>
                      </>
                    )}
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  {successMessage && (
                    <Alert className="bg-green-50 border-green-200 text-green-800">
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>{successMessage}</AlertDescription>
                    </Alert>
                  )}

                  {/* Optimization Results */}
                  {optimizationResults && (
                    <div className="space-y-4">
                      <h4 className="text-lg font-medium">Optimization Results</h4>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="text-center p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg border border-emerald-200">
                          <div className="text-xl font-bold text-emerald-700">
                            {(optimizationResults.expectedReturn * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-emerald-600 mt-0.5">Optimized Return</div>
                        </div>
                        <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
                          <div className="text-xl font-bold text-amber-700">
                            {(optimizationResults.risk * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-amber-600 mt-0.5">Optimized Risk</div>
                        </div>
                        <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
                          <div className="text-xl font-bold text-purple-700">
                            {optimizationResults.diversificationScore.toFixed(0)}%
                          </div>
                          <div className="text-xs text-purple-600 mt-0.5">Diversification</div>
                        </div>
                      </div>

                      {/* Optimized Portfolio */}
                      {optimizedPortfolio.length > 0 && (
                        <div className="space-y-4">
                          <h5 className="font-medium">Optimized Allocations</h5>
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
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Analysis Tab */}
            <TabsContent value="analysis" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Portfolio Analysis</h3>
                <p className="text-muted-foreground">
                  Deep dive into your portfolio's risk-return characteristics
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Efficient Frontier Analysis</CardTitle>
                  <p className="text-muted-foreground">
                    Visual representation of risk-return trade-offs and optimization opportunities
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  {efficientFrontier.length > 0 ? (
                    <div className="space-y-4">
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <h5 className="font-medium mb-2">Efficient Frontier Chart</h5>
                        <p className="text-sm text-muted-foreground">
                          This chart shows the relationship between risk and return. Points on the frontier represent 
                          optimal portfolios for different risk tolerances.
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center p-3 bg-blue-50 rounded-lg border">
                          <div className="w-4 h-4 bg-blue-500 rounded-full mx-auto mb-2"></div>
                          <div className="text-sm font-medium">Current Portfolio</div>
                          <div className="text-xs text-muted-foreground">Your selection</div>
                        </div>
                        <div className="text-center p-3 bg-green-50 rounded-lg border">
                          <div className="w-4 h-4 bg-green-500 rounded-full mx-auto mb-2"></div>
                          <div className="text-sm font-medium">Optimized Portfolio</div>
                          <div className="text-xs text-muted-foreground">Best risk-return</div>
                        </div>
                        <div className="text-center p-3 bg-gray-50 rounded-lg border">
                          <div className="w-4 h-4 bg-gray-400 rounded-full mx-auto mb-2"></div>
                          <div className="text-sm font-medium">Efficient Frontier</div>
                          <div className="text-xs text-muted-foreground">Optimal combinations</div>
                        </div>
                      </div>

                      <div className="bg-gray-100 p-8 rounded-lg text-center">
                        <LineChart className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                        <p className="text-gray-600">
                          Interactive chart visualization will be implemented here showing the efficient frontier, 
                          current portfolio position, and optimization opportunities.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Run portfolio optimization to generate efficient frontier analysis.</p>
                    </div>
                  )}
                </CardContent>
              </Card>
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
              disabled={currentPortfolio.length < 3}
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
