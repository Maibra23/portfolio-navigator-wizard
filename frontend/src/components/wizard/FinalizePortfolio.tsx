/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  ArrowLeft, 
  ArrowRight, 
  CheckCircle, 
  AlertTriangle,
  Loader2,
  BarChart3,
  TrendingUp,
  Shield,
  FileText,
  Calculator,
  Info
} from 'lucide-react';
import { PortfolioBuilder, PortfolioAllocation, PortfolioMetrics } from './PortfolioBuilder';
import { PortfolioAnalyticsPanel } from './PortfolioAnalyticsPanel';
import { usePortfolioState } from '@/hooks/usePortfolioState';
import { validateTab, canNavigateToTab } from '@/utils/tabValidation';
import { formatPercent, formatNumber } from '@/utils/numberFormat';
import { StressTest } from './StressTest';
import { EfficientFrontierChart } from './EfficientFrontierChart';
import { PortfolioComparisonTable } from './PortfolioComparisonTable';
import { PerformanceSummaryCard, QualityScoreCard, MonteCarloCard } from './FinalAnalysisComponents';
import { FiveYearProjectionChart } from './FiveYearProjectionChart';

interface FinalizePortfolioProps {
  onComplete: () => void;
  onPrev: () => void;
  capital: number;
  riskProfile: string;
}

export const FinalizePortfolio: React.FC<FinalizePortfolioProps> = ({
  onComplete,
  onPrev,
  capital,
  riskProfile
}) => {
  const {
    state,
    isLoaded,
    updateConstructedPortfolio,
    updateOptimizedPortfolio,
    updateStressTestResults,
    updateTaxSettings,
    markTabComplete,
    clearState
  } = usePortfolioState();

  const [activeTab, setActiveTab] = useState<'builder' | 'optimize' | 'analysis' | 'tax-cost'>('builder');
  const [hiddenTab, setHiddenTab] = useState<'stress-test' | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationError, setOptimizationError] = useState<string | null>(null);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [taxCalculation, setTaxCalculation] = useState<any>(null);
  const [transactionCosts, setTransactionCosts] = useState<any>(null);
  const [isLoadingTax, setIsLoadingTax] = useState(false);
  const [isLoadingCosts, setIsLoadingCosts] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Validation state
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});

  // Validate current tab
  useEffect(() => {
    if (isLoaded) {
      const validation = validateTab(activeTab, state);
      setValidationErrors(prev => ({
        ...prev,
        [activeTab]: validation.errors
      }));
    }
  }, [activeTab, state, isLoaded]);

  // Handle tab change with validation
  const handleTabChange = (newTab: string) => {
    if (canNavigateToTab(newTab, state, activeTab)) {
      setActiveTab(newTab as any);
      setValidationErrors({});
    } else {
      const validation = validateTab(newTab, state);
      setValidationErrors(prev => ({
        ...prev,
        [newTab]: validation.errors
      }));
    }
  };

  // Handle portfolio update from Tab 1
  const handlePortfolioUpdate = (stocks: PortfolioAllocation[]) => {
    updateConstructedPortfolio(stocks);
    
    // Validate allocation
    const totalAllocation = stocks.reduce((sum, s) => sum + (s.allocation || 0), 0);
    if (stocks.length >= 3 && stocks.length <= 4 && Math.abs(totalAllocation - 100) < 0.1) {
      markTabComplete('builder');
    }
  };

  // Handle metrics update
  const handleMetricsUpdate = (metrics: PortfolioMetrics | null) => {
    setPortfolioMetrics(metrics);
  };

  // Handle optimization (same request payload as PortfolioOptimization for identical results)
  const handleOptimize = async () => {
    if (state.constructedPortfolio.length === 0) {
      setOptimizationError('Please build a portfolio first');
      return;
    }

    setIsOptimizing(true);
    setOptimizationError(null);

    try {
      const userTickers = state.constructedPortfolio.map(s => s.symbol);
      const userWeights = state.constructedPortfolio.reduce((acc, s) => {
        acc[s.symbol] = s.allocation / 100;
        return acc;
      }, {} as Record<string, number>);

      const requestPayload = {
        user_tickers: userTickers,
        user_weights: userWeights,
        risk_profile: riskProfile,
        capital: capital,
        optimization_type: 'max_sharpe',
        max_eligible_tickers: 20,
        include_efficient_frontier: true,
        include_random_portfolios: true,
        num_frontier_points: 20,
        num_random_portfolios: 300,
        use_combined_strategy: true,
        attempt_market_exploration: true,
      };

      const response = await fetch('/api/portfolio/optimization/triple', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`Optimization failed: ${response.statusText}`);
      }

      const data = await response.json();
      updateOptimizedPortfolio(data);
      markTabComplete('optimize');
    } catch (error: any) {
      console.error('Optimization error:', error);
      setOptimizationError(error.message || 'Failed to optimize portfolio');
    } finally {
      setIsOptimizing(false);
    }
  };

  // Handle stress test navigation
  const handleRunStressTest = () => {
    const portfolio = state.optimizedPortfolio || {
      source: 'current',
      tickers: state.constructedPortfolio.map(s => s.symbol),
      weights: state.constructedPortfolio.reduce((acc, s) => {
        acc[s.symbol] = s.allocation / 100;
        return acc;
      }, {} as Record<string, number>),
      metrics: portfolioMetrics ? {
        expected_return: portfolioMetrics.expectedReturn,
        risk: portfolioMetrics.risk,
        sharpe_ratio: portfolioMetrics.sharpeRatio
      } : {
        expected_return: 0.1,
        risk: 0.15,
        sharpe_ratio: 0.5
      }
    };

    setHiddenTab('stress-test');
    setActiveTab('stress-test' as any);
  };

  // Handle stress test results
  const handleStressTestResults = (results: any) => {
    updateStressTestResults(results);
    setHiddenTab(null);
    setActiveTab('analysis');
  };

  // Calculate tax when account type changes
  useEffect(() => {
    if (state.taxSettings.accountType && state.taxSettings.taxYear && capital > 0) {
      setIsLoadingTax(true);
      const calculateTax = async () => {
        try {
          const requestBody: any = {
            accountType: state.taxSettings.accountType,
            taxYear: state.taxSettings.taxYear
          };

          if (state.taxSettings.accountType === 'ISK' || state.taxSettings.accountType === 'KF') {
            requestBody.portfolioValue = capital;
          } else {
            // AF account - estimate based on expected return
            const estimatedGains = capital * (portfolioMetrics?.expectedReturn || 0.1);
            requestBody.realizedGains = estimatedGains;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }

          const response = await fetch('/api/portfolio/tax/calculate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
          });

          if (!response.ok) {
            throw new Error(`Tax calculation failed: ${response.statusText}`);
          }

          const data = await response.json();
          setTaxCalculation(data);
        } catch (error: any) {
          console.error('Tax calculation error:', error);
          setTaxCalculation(null);
        } finally {
          setIsLoadingTax(false);
        }
      };

      calculateTax();
    } else {
      setTaxCalculation(null);
    }
  }, [state.taxSettings.accountType, state.taxSettings.taxYear, capital, portfolioMetrics]);

  // Calculate transaction costs when courtage class changes
  useEffect(() => {
    if (state.taxSettings.courtagClass && state.constructedPortfolio.length > 0 && capital > 0) {
      setIsLoadingCosts(true);
      const calculateCosts = async () => {
        try {
          // Convert portfolio to transaction format
          const portfolio = state.constructedPortfolio.map(stock => {
            const value = capital * (stock.allocation / 100);
            // Estimate shares (simplified - would need actual stock prices)
            const estimatedShares = Math.floor(value / 100); // Rough estimate
            return {
              ticker: stock.symbol,
              shares: estimatedShares,
              value: value
            };
          });

          const response = await fetch('/api/portfolio/transaction-costs/estimate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              courtageClass: state.taxSettings.courtagClass,
              portfolio: portfolio,
              rebalancingFrequency: 'quarterly'
            }),
          });

          if (!response.ok) {
            throw new Error(`Transaction cost calculation failed: ${response.statusText}`);
          }

          const data = await response.json();
          setTransactionCosts(data);
        } catch (error: any) {
          console.error('Transaction cost calculation error:', error);
          setTransactionCosts(null);
        } finally {
          setIsLoadingCosts(false);
        }
      };

      calculateCosts();
    } else {
      setTransactionCosts(null);
    }
  }, [state.taxSettings.courtagClass, state.constructedPortfolio, capital]);

  // Handle export
  const handleExport = async () => {
    if (!state.taxSettings.accountType) {
      return;
    }

    setIsExporting(true);
    try {
      // Prepare portfolio data
      const portfolioData = {
        tickers: state.constructedPortfolio.map(s => s.symbol),
        weights: state.constructedPortfolio.reduce((acc, s) => {
          acc[s.symbol] = s.allocation / 100;
          return acc;
        }, {} as Record<string, number>),
        allocations: state.constructedPortfolio
      };

      // Prepare export request (include optimization for PDF sections 4 and 5-year projection)
      const exportRequest = {
        portfolio: portfolioData,
        includeSections: {
          optimization: state.optimizedPortfolio != null,
          stressTest: state.stressTestResults != null,
          goals: false,
          rebalancing: false
        },
        optimizationResults: state.optimizedPortfolio ?? undefined,
        taxData: taxCalculation,
        costData: transactionCosts,
        stressTestResults: state.stressTestResults,
        portfolioValue: capital,
        accountType: state.taxSettings.accountType,
        taxYear: state.taxSettings.taxYear,
        metrics: portfolioMetrics ? {
          expectedReturn: portfolioMetrics.expectedReturn,
          risk: portfolioMetrics.risk,
          diversificationScore: portfolioMetrics.diversificationScore,
          sharpeRatio: portfolioMetrics.sharpeRatio
        } : null
      };

      // Generate PDF
      const pdfResponse = await fetch('/api/portfolio/export/pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(exportRequest),
      });

      if (!pdfResponse.ok) {
        throw new Error(`PDF export failed: ${pdfResponse.statusText}`);
      }

      // Download PDF
      const blob = await pdfResponse.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `portfolio_report_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Also generate CSV
      const csvResponse = await fetch('/api/portfolio/export/csv', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          portfolio: portfolioData,
          taxData: taxCalculation,
          costData: transactionCosts,
          stressTestResults: state.stressTestResults,
          metrics: exportRequest.metrics,
          includeFiles: ['holdings', 'tax', 'costs', 'metrics', 'stressTest']
        }),
      });

      if (csvResponse.ok) {
        const csvData = await csvResponse.json();
        if (csvData.zipFile) {
          // Download ZIP file
          const zipBlob = Uint8Array.from(atob(csvData.zipFile), c => c.charCodeAt(0));
          const zipUrl = window.URL.createObjectURL(new Blob([zipBlob], { type: 'application/zip' }));
          const zipA = document.createElement('a');
          zipA.href = zipUrl;
          zipA.download = `portfolio_data_${new Date().toISOString().split('T')[0]}.zip`;
          document.body.appendChild(zipA);
          zipA.click();
          window.URL.revokeObjectURL(zipUrl);
          document.body.removeChild(zipA);
        }
      }

      clearState();
      onComplete();
    } catch (error: any) {
      console.error('Export error:', error);
      alert(`Export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Handle completion
  const handleComplete = () => {
    handleExport();
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Tabs value={hiddenTab || activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="builder" disabled={!canNavigateToTab('builder', state, activeTab)}>
            Portfolio Builder
          </TabsTrigger>
          <TabsTrigger
            value="optimize"
            disabled={!canNavigateToTab('optimize', state, activeTab)}
          >
            Optimize
          </TabsTrigger>
          <TabsTrigger
            value="analysis"
            disabled={!canNavigateToTab('analysis', state, activeTab)}
          >
            Final Analysis
          </TabsTrigger>
          <TabsTrigger
            value="tax-cost"
            disabled={!canNavigateToTab('tax-cost', state, activeTab)}
          >
            Tax & Summary
          </TabsTrigger>
          {hiddenTab === 'stress-test' && (
            <TabsTrigger value="stress-test" className="hidden">
              Stress Test
            </TabsTrigger>
          )}
        </TabsList>

        {/* Tab 1: Portfolio Builder */}
        <TabsContent value="builder" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Build Your Portfolio
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Select 3 to 4 stocks from the full universe and allocate 100% of your capital
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <PortfolioBuilder
                selectedStocks={state.constructedPortfolio}
                onStocksUpdate={handlePortfolioUpdate}
                onMetricsUpdate={handleMetricsUpdate}
                riskProfile={riskProfile}
                capital={capital}
                minStocks={3}
                maxStocks={4}
                fullUniverse={true}
                showValidation={true}
              />

              {state.constructedPortfolio.length >= 3 && (
                <PortfolioAnalyticsPanel
                  selectedStocks={state.constructedPortfolio}
                  riskProfile={riskProfile}
                  portfolioMetrics={portfolioMetrics}
                />
              )}

              {validationErrors.builder && validationErrors.builder.length > 0 && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1">
                      {validationErrors.builder.map((error, idx) => (
                        <li key={idx}>{error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Optimize */}
        <TabsContent value="optimize" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Portfolio Optimization
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Optimize your portfolio based on your risk profile
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Portfolio Overview - Matching PortfolioOptimization structure */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Current Portfolio Summary</CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    {state.constructedPortfolio.length} assets selected
                  </p>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  {state.constructedPortfolio && state.constructedPortfolio.length > 0 ? (
                    <div className="grid grid-cols-1 gap-2">
                      {state.constructedPortfolio.map((stock, index) => (
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
                  
                  {portfolioMetrics && (
                    <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-border/50">
                      <div className="text-center p-3 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg border border-emerald-200">
                        <div className="text-xl font-bold text-emerald-700">
                          {((portfolioMetrics.expectedReturn || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-emerald-600 mt-0.5">Expected Return</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg border border-amber-200">
                        <div className="text-xl font-bold text-amber-700">
                          {((portfolioMetrics.risk || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-amber-600 mt-0.5">Risk Level</div>
                      </div>
                      <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
                        <div className="text-xl font-bold text-purple-700">
                          {(portfolioMetrics.diversificationScore || 0).toFixed(0)}%
                        </div>
                        <div className="text-xs text-purple-600 mt-0.5">Diversification</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Optimize Button */}
              <Button
                onClick={handleOptimize}
                disabled={isOptimizing || state.constructedPortfolio.length === 0}
                className="w-full"
                size="lg"
              >
                {isOptimizing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Optimizing...
                  </>
                ) : (
                  <>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Optimize
                  </>
                )}
              </Button>

              {optimizationError && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{optimizationError}</AlertDescription>
                </Alert>
              )}

              {/* Optimization Results */}
              {state.optimizedPortfolio && (
                <div className="space-y-4">
                  <Alert className="bg-green-50 border-green-200">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-800">
                      <strong>Optimization completed successfully!</strong>
                      <p className="text-sm mt-1">
                        Your portfolio has been optimized to maximize returns while managing risk according to your {riskProfile} profile.
                      </p>
                    </AlertDescription>
                  </Alert>

                  {/* Efficient Frontier - Use frontierData (market || weights) so CML intersects market-opt when present */}
                  {(() => {
                    const frontierData = state.optimizedPortfolio.market_optimized_portfolio || state.optimizedPortfolio.weights_optimized_portfolio;
                    const hasFrontier = frontierData?.efficient_frontier && frontierData.efficient_frontier.length > 0;
                    if (!hasFrontier) return null;
                    return (
                      <EfficientFrontierChart
                        currentPortfolio={{
                          risk: state.optimizedPortfolio.current_portfolio?.metrics?.risk || portfolioMetrics?.risk || 0.15,
                          return: state.optimizedPortfolio.current_portfolio?.metrics?.expected_return || portfolioMetrics?.expectedReturn || 0.1,
                          name: 'Current Portfolio',
                          type: 'current',
                          sharpe_ratio: state.optimizedPortfolio.current_portfolio?.metrics?.sharpe_ratio || portfolioMetrics?.sharpeRatio
                        }}
                        efficientFrontier={frontierData.efficient_frontier}
                        inefficientFrontier={frontierData.inefficient_frontier}
                        randomPortfolios={frontierData.random_portfolios}
                        capitalMarketLine={frontierData.capital_market_line}
                        marketOptimizedPortfolio={state.optimizedPortfolio.market_optimized_portfolio?.optimized_portfolio ? {
                          risk: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.risk,
                          return: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.expected_return,
                          name: 'Market Optimized',
                          type: 'market-optimized' as const,
                          sharpe_ratio: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio
                        } : undefined}
                        weightsOptimizedPortfolio={state.optimizedPortfolio.weights_optimized_portfolio?.optimized_portfolio ? {
                          risk: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.risk,
                          return: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return,
                          name: 'Weights Optimized',
                          type: 'weights-optimized' as const,
                          sharpe_ratio: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio
                        } : undefined}
                        showControls={true}
                        showInteractiveLegend={true}
                      />
                    );
                  })()}

                  {/* Portfolio Comparison - Using shared component from PortfolioOptimization */}
                  {state.optimizedPortfolio.current_portfolio && state.optimizedPortfolio.weights_optimized_portfolio && (
                    <Card>
                      <CardContent className="pt-0">
                        <PortfolioComparisonTable
                          tripleOptimizationResults={{
                            current_portfolio: {
                              tickers: state.optimizedPortfolio.current_portfolio.tickers || state.constructedPortfolio.map(s => s.symbol),
                              weights: state.optimizedPortfolio.current_portfolio.weights || state.constructedPortfolio.reduce((acc, s) => {
                                acc[s.symbol] = s.allocation / 100;
                                return acc;
                              }, {} as Record<string, number>),
                              metrics: {
                                expected_return: state.optimizedPortfolio.current_portfolio.metrics?.expected_return || portfolioMetrics?.expectedReturn || 0,
                                risk: state.optimizedPortfolio.current_portfolio.metrics?.risk || portfolioMetrics?.risk || 0,
                                sharpe_ratio: state.optimizedPortfolio.current_portfolio.metrics?.sharpe_ratio || portfolioMetrics?.sharpeRatio || 0
                              }
                            },
                            weights_optimized_portfolio: {
                              optimized_portfolio: {
                                tickers: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.tickers,
                                weights: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.weights,
                                metrics: {
                                  expected_return: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return,
                                  risk: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.risk,
                                  sharpe_ratio: state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio
                                }
                              }
                            },
                            market_optimized_portfolio: state.optimizedPortfolio.market_optimized_portfolio ? {
                              optimized_portfolio: {
                                tickers: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.tickers,
                                weights: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.weights,
                                metrics: {
                                  expected_return: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.expected_return,
                                  risk: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.risk,
                                  sharpe_ratio: state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio
                                }
                              }
                            } : null,
                            comparison: {
                              weights_vs_current: state.optimizedPortfolio.comparison?.weights_vs_current || {
                                return_difference: (state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return || 0) -
                                                   (state.optimizedPortfolio.current_portfolio.metrics?.expected_return || 0),
                                risk_difference: (state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.risk || 0) -
                                                 (state.optimizedPortfolio.current_portfolio.metrics?.risk || 0),
                                sharpe_difference: (state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio || 0) -
                                                   (state.optimizedPortfolio.current_portfolio.metrics?.sharpe_ratio || 0)
                              },
                              market_vs_current: state.optimizedPortfolio.comparison?.market_vs_current,
                              best_sharpe: state.optimizedPortfolio.comparison?.best_sharpe
                            },
                            optimization_metadata: state.optimizedPortfolio.optimization_metadata
                          }}
                          showSelectionButtons={false}
                        />
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {validationErrors.optimize && validationErrors.optimize.length > 0 && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {validationErrors.optimize[0]}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Final Analysis */}
        <TabsContent value="analysis" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Final Analysis
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Comprehensive analysis of your portfolio performance and risk
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Performance Summary, Quality Score, Monte Carlo from optimization (when available) */}
              {state.optimizedPortfolio?.comparison && (() => {
                const triple = state.optimizedPortfolio;
                const selectedPortfolio = (triple.optimization_metadata?.recommendation || 'weights') as 'current' | 'weights' | 'market';
                const isTriple = Boolean(triple.market_optimized_portfolio);
                return (
                  <div className="space-y-6">
                    <PerformanceSummaryCard
                      tripleOptimizationResults={triple}
                      selectedPortfolio={selectedPortfolio}
                      riskProfile={riskProfile}
                    />
                    {triple.comparison?.quality_scores && (
                      <QualityScoreCard
                        qualityData={triple.comparison.quality_scores}
                        selectedPortfolio={selectedPortfolio}
                        isTriple={isTriple}
                      />
                    )}
                    {triple.comparison?.monte_carlo && (
                      <MonteCarloCard
                        monteCarloData={triple.comparison.monte_carlo}
                        selectedPortfolio={selectedPortfolio}
                        isTriple={isTriple}
                      />
                    )}
                  </div>
                );
              })()}

              {/* Fallback: simple metrics when no optimization run yet */}
              {!state.optimizedPortfolio?.comparison && portfolioMetrics && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Performance Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Expected Return</div>
                        <div className="text-2xl font-bold">{formatPercent(portfolioMetrics.expectedReturn)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Risk</div>
                        <div className="text-2xl font-bold">{formatPercent(portfolioMetrics.risk)}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
              {!state.optimizedPortfolio?.comparison && !portfolioMetrics && (
                <p className="text-sm text-muted-foreground">Run optimization in the Optimize tab to see full analysis (Performance Summary, Quality Score, Monte Carlo) here.</p>
              )}

              {/* Stress Test Button */}
              <Button
                onClick={handleRunStressTest}
                className="w-full"
                size="lg"
                variant="outline"
              >
                <Shield className="mr-2 h-4 w-4" />
                Run Stress Test
              </Button>

              {state.stressTestResults && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    Stress test completed. Resilience Score: {formatNumber(state.stressTestResults.resilience_score, { maxDecimals: 0 }) || 'N/A'}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                onClick={() => handleTabChange('tax-cost')}
                disabled={!canNavigateToTab('tax-cost', state, activeTab)}
                className="w-full mt-4"
                size="lg"
              >
                Continue
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Hidden Tab: Stress Test */}
        {hiddenTab === 'stress-test' && (
          <TabsContent value="stress-test" className="mt-6">
            <StressTest
              onNext={() => {
                setHiddenTab(null);
                setActiveTab('analysis');
              }}
              onPrev={() => {
                setHiddenTab(null);
                setActiveTab('analysis');
              }}
              selectedPortfolio={{
                source: 'current',
                tickers: state.constructedPortfolio.map(s => s.symbol),
                weights: state.constructedPortfolio.reduce((acc, s) => {
                  acc[s.symbol] = s.allocation / 100;
                  return acc;
                }, {} as Record<string, number>),
                metrics: portfolioMetrics ? {
                  expected_return: portfolioMetrics.expectedReturn,
                  risk: portfolioMetrics.risk,
                  sharpe_ratio: portfolioMetrics.sharpeRatio
                } : {
                  expected_return: 0.1,
                  risk: 0.15,
                  sharpe_ratio: 0.5
                }
              }}
              capital={capital}
              riskProfile={riskProfile}
            />
          </TabsContent>
        )}

        {/* Tab 4: Tax, Cost & Summary */}
        <TabsContent value="tax-cost" className="space-y-6 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Tax, Cost & Summary
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Swedish taxes and transaction costs, 5-year projection, then export
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Settings: Account Type, Tax Year, Courtage (grid) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Account Type</label>
                  <select
                    className="w-full p-2 border rounded-md"
                    value={state.taxSettings.accountType || ''}
                    onChange={(e) => updateTaxSettings({ accountType: e.target.value as any })}
                  >
                    <option value="">Select account type</option>
                    <option value="ISK">ISK (Investeringssparkonto)</option>
                    <option value="KF">KF (Kapitalförsäkring)</option>
                    <option value="AF">AF (Aktie- och Fondkonto)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tax Year</label>
                  <select
                    className="w-full p-2 border rounded-md"
                    value={state.taxSettings.taxYear}
                    onChange={(e) => updateTaxSettings({ taxYear: parseInt(e.target.value) as 2025 | 2026 })}
                  >
                    <option value="2025">2025</option>
                    <option value="2026">2026</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Courtage Class</label>
                  <select
                    className="w-full p-2 border rounded-md"
                    value={state.taxSettings.courtagClass || ''}
                    onChange={(e) => updateTaxSettings({ courtagClass: e.target.value })}
                  >
                    <option value="">Select courtage class</option>
                    <option value="start">Start</option>
                    <option value="mini">Mini</option>
                    <option value="small">Small</option>
                    <option value="medium">Medium</option>
                    <option value="fastPris">Fast Pris</option>
                  </select>
                </div>
              </div>

              {/* Section: Tax Summary */}
              {state.taxSettings.accountType && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Tax Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingTax ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Calculating tax...
                      </div>
                    ) : taxCalculation ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground">Account Type</div>
                            <div className="font-medium">{taxCalculation.accountType}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Tax Year</div>
                            <div className="font-medium">{taxCalculation.taxYear}</div>
                          </div>
                          {taxCalculation.capitalUnderlag !== undefined && (
                            <div>
                              <div className="text-sm text-muted-foreground">Capital Underlag</div>
                              <div className="font-medium">{taxCalculation.capitalUnderlag.toLocaleString('sv-SE')} SEK</div>
                            </div>
                          )}
                          {taxCalculation.taxFreeLevel !== undefined && (
                            <div>
                              <div className="text-sm text-muted-foreground">Tax-Free Level</div>
                              <div className="font-medium">{taxCalculation.taxFreeLevel.toLocaleString('sv-SE')} SEK</div>
                            </div>
                          )}
                          <div>
                            <div className="text-sm text-muted-foreground">Annual Tax</div>
                            <div className="font-medium text-lg">{taxCalculation.annualTax.toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Effective Tax Rate</div>
                            <div className="font-medium">{formatPercent((taxCalculation.effectiveTaxRate ?? 0) / 100)}</div>
                          </div>
                        </div>
                        {taxCalculation.afterTaxReturn !== undefined && portfolioMetrics && (
                          <div className="pt-3 border-t">
                            <div className="text-sm text-muted-foreground">After-Tax Return</div>
                            <div className="font-medium text-lg">{formatPercent(taxCalculation.afterTaxReturn)}</div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">No tax calculation available</div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Section: Total & Ongoing Costs (no cost-optimization suggestion panel) */}
              {state.taxSettings.courtagClass && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Total & Ongoing Costs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isLoadingCosts ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Calculating costs...
                      </div>
                    ) : transactionCosts ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground">Courtage Class</div>
                            <div className="font-medium">{transactionCosts.courtageClass}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Setup Cost</div>
                            <div className="font-medium">{transactionCosts.setupCost.toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Annual Rebalancing</div>
                            <div className="font-medium">{transactionCosts.annualRebalancingCost.toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">Total First Year</div>
                            <div className="font-medium text-lg">{transactionCosts.totalFirstYearCost.toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">No cost calculation available</div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* 5-Year Projection with Tax Drag (three regression-based lines) */}
              <FiveYearProjectionChart
                weights={state.constructedPortfolio.length > 0
                  ? state.constructedPortfolio.reduce((acc, s) => {
                      acc[s.symbol] = s.allocation / 100;
                      return acc;
                    }, {} as Record<string, number>)
                  : {}}
                capital={capital}
                accountType={state.taxSettings.accountType}
                taxYear={state.taxSettings.taxYear}
                courtageClass={state.taxSettings.courtagClass}
                expectedReturn={portfolioMetrics?.expectedReturn ?? 0.08}
                risk={portfolioMetrics?.risk ?? 0.15}
                rebalancingFrequency="quarterly"
              />

              {/* Export Button */}
              <Button
                onClick={handleComplete}
                className="w-full"
                size="lg"
                disabled={!state.taxSettings.accountType || isExporting}
              >
                {isExporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Export Portfolio Report
                  </>
                )}
              </Button>

              {validationErrors['tax-cost'] && validationErrors['tax-cost'].length > 0 && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {validationErrors['tax-cost'][0]}
                  </AlertDescription>
                </Alert>
              )}
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
        {activeTab === 'tax-cost' && state.taxSettings.accountType && (
          <Button onClick={handleComplete}>
            Complete
            <CheckCircle className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
};
