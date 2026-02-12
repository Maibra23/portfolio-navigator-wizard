/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  FileArchive,
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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { TaxEducationPanel } from './TaxEducationPanel';
import { TaxComparisonChart } from './TaxComparisonChart';
import { TaxFreeVisualization } from './TaxFreeVisualization';
import { WhatIfCalculator } from './WhatIfCalculator';
import { TaxSummaryCard } from './TaxSummaryCard';
import { TotalCostsCard } from './TotalCostsCard';

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
  const [optimizeButtonClicked, setOptimizeButtonClicked] = useState(false); // hide button immediately on click
  const [optimizationError, setOptimizationError] = useState<string | null>(null);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [taxCalculation, setTaxCalculation] = useState<any>(null);
  const [transactionCosts, setTransactionCosts] = useState<any>(null);
  const [isLoadingTax, setIsLoadingTax] = useState(false);
  const [isLoadingCosts, setIsLoadingCosts] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<'pdf' | 'csv' | null>(null);
  const [portfolioName, setPortfolioName] = useState('My Investment Portfolio');
  const [selectedPortfolioType, setSelectedPortfolioType] = useState<'current' | 'weights' | 'market'>('current');
  const [taxComparisonData, setTaxComparisonData] = useState<any>(null);

  // Builder "Done" pressed: user must press Done in Portfolio Builder before Continue to Optimize
  const [builderDone, setBuilderDone] = useState(false);

  // Validation state
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});

  // Single source of truth for metrics shown on page and exported (PDF/CSV):
  // use the portfolio the user selected (Current / Weights / Market). Fall back to builder metrics when optimization isn't available.
  const displayMetrics = useMemo((): PortfolioMetrics | null => {
    const opt = state.optimizedPortfolio;
    const selected =
      selectedPortfolioType === 'market' && opt?.market_optimized_portfolio?.optimized_portfolio
        ? opt.market_optimized_portfolio.optimized_portfolio
        : selectedPortfolioType === 'weights' && opt?.weights_optimized_portfolio?.optimized_portfolio
          ? opt.weights_optimized_portfolio.optimized_portfolio
          : opt?.current_portfolio;

    const selectedMetrics: any = (selected as any)?.metrics;
    if (selectedMetrics) {
      return {
        expectedReturn: selectedMetrics.expected_return ?? portfolioMetrics?.expectedReturn ?? 0,
        risk: selectedMetrics.risk ?? portfolioMetrics?.risk ?? 0,
        diversificationScore: portfolioMetrics?.diversificationScore ?? 0,
        sharpeRatio: selectedMetrics.sharpe_ratio ?? portfolioMetrics?.sharpeRatio ?? 0
      };
    }
    return portfolioMetrics;
  }, [state.optimizedPortfolio, portfolioMetrics, selectedPortfolioType]);

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

  // Handle tab change with validation (Optimize only reachable from Builder after Done)
  const handleTabChange = (newTab: string) => {
    if (newTab === 'optimize' && activeTab === 'builder' && !builderDone) return;
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

  // Handle portfolio update from Tab 1 (search bar switch or allocation edit)
  const handlePortfolioUpdate = (stocks: PortfolioAllocation[]) => {
    updateConstructedPortfolio(stocks);
    // If user had already pressed Done, any change invalidates confirmation → Continue disabled until Done again
    setBuilderDone((prev) => (prev ? false : prev));
    // Reset selection type if manual changes are made
    setSelectedPortfolioType('current');

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

      const response = await fetch('/api/v1/portfolio/optimization/triple', {
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
      setOptimizeButtonClicked(false);
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

  // Handle portfolio selection from optimization results
  const handlePortfolioSelect = (type: 'current' | 'weights' | 'market') => {
    if (!state.optimizedPortfolio) return;

    setSelectedPortfolioType(type);

    let selectedPortfolioData: any;
    if (type === 'current' && state.optimizedPortfolio.current_portfolio) {
      selectedPortfolioData = state.optimizedPortfolio.current_portfolio;
    } else if (type === 'weights' && state.optimizedPortfolio.weights_optimized_portfolio) {
      selectedPortfolioData = state.optimizedPortfolio.weights_optimized_portfolio.optimized_portfolio;
    } else if (type === 'market' && state.optimizedPortfolio.market_optimized_portfolio) {
      selectedPortfolioData = state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio;
    }

    if (selectedPortfolioData) {
      // Map optimized weights back to PortfolioAllocation format
      const tickers: string[] =
        selectedPortfolioData.tickers ||
        (Array.isArray(selectedPortfolioData.tickers) ? selectedPortfolioData.tickers : []) ||
        selectedPortfolioData.tickers;
      const weights: Record<string, number> = selectedPortfolioData.weights || {};

      const newStocks: PortfolioAllocation[] = (tickers || []).map(symbol => ({
        symbol,
        allocation: (weights[symbol] || 0) * 100,
        // Try to preserve existing names if they exist in current portfolio
        name: state.constructedPortfolio.find(s => s.symbol === symbol)?.name || ''
      }));
      
      updateConstructedPortfolio(newStocks);
      // Mark builder as done since we just selected a valid optimized portfolio
      setBuilderDone(true);
      markTabComplete('builder');
    }
  };

  // Calculate tax when account type changes
  useEffect(() => {
    if (state.taxSettings.accountType && state.taxSettings.taxYear && capital > 0) {
      setIsLoadingTax(true);
      const calculateTax = async () => {
        try {
          const expectedReturn = displayMetrics?.expectedReturn ?? portfolioMetrics?.expectedReturn ?? 0.08;
          const requestBody: any = {
            accountType: state.taxSettings.accountType,
            taxYear: state.taxSettings.taxYear,
            expectedReturn
          };

          if (state.taxSettings.accountType === 'ISK' || state.taxSettings.accountType === 'KF') {
            requestBody.portfolioValue = capital;
          } else {
            // AF account - estimate based on expected return
            const estimatedGains = capital * expectedReturn;
            requestBody.realizedGains = estimatedGains;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }

          const response = await fetch('/api/v1/portfolio/tax/calculate', {
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
  }, [state.taxSettings.accountType, state.taxSettings.taxYear, capital, portfolioMetrics, displayMetrics?.expectedReturn]);

  // Fetch 3-account tax comparison once (for chart and export); avoids duplicate calls from TaxComparisonChart
  useEffect(() => {
    if (capital <= 0 || !state.taxSettings.taxYear) {
      setTaxComparisonData(null);
      return;
    }
    const expectedRet = displayMetrics?.expectedReturn ?? portfolioMetrics?.expectedReturn ?? 0.08;
    const accountTypes = ['ISK', 'KF', 'AF'];
    const promises = accountTypes.map(async (accountType) => {
      const requestBody: any = { accountType, taxYear: state.taxSettings.taxYear, expectedReturn: expectedRet };
      if (accountType === 'ISK' || accountType === 'KF') {
        requestBody.portfolioValue = capital;
      } else {
        requestBody.realizedGains = capital * expectedRet;
        requestBody.dividends = 0;
        requestBody.fundHoldings = 0;
      }
      const response = await fetch('/api/v1/portfolio/tax/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      if (!response.ok) return null;
      const result = await response.json();
      return {
        accountType,
        annualTax: result.annualTax || 0,
        effectiveRate: result.effectiveTaxRate || 0,
        displayName: accountType,
        afterTaxReturn: result.afterTaxReturn,
        taxFreeLevel: result.taxFreeLevel,
        capitalUnderlag: result.capitalUnderlag,
      };
    });
    Promise.all(promises).then((results) => {
      setTaxComparisonData(results.filter((r): r is NonNullable<typeof r> => r !== null));
    }).catch(() => setTaxComparisonData(null));
  }, [capital, state.taxSettings.taxYear, displayMetrics?.expectedReturn, portfolioMetrics?.expectedReturn]);

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

          const response = await fetch('/api/v1/portfolio/transaction-costs/estimate', {
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

  // Fetch tax comparison data for all account types (for export)
  const fetchTaxComparisonForExport = async () => {
    if (!state.taxSettings.accountType || !portfolioMetrics) return null;

    try {
      const accountTypes = ['ISK', 'KF', 'AF'];
      const promises = accountTypes.map(async (accountType) => {
        const requestBody: any = {
          accountType,
          taxYear: state.taxSettings.taxYear
        };

        if (accountType === 'ISK' || accountType === 'KF') {
          requestBody.portfolioValue = capital;
        } else {
          const estimatedGains = capital * (displayMetrics?.expectedReturn || portfolioMetrics.expectedReturn);
          requestBody.realizedGains = estimatedGains;
          requestBody.dividends = 0;
          requestBody.fundHoldings = 0;
        }

        const response = await fetch('/api/v1/portfolio/tax/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) return null;

        const result = await response.json();
        return {
          accountType,
          annualTax: result.annualTax || 0,
          effectiveRate: result.effectiveTaxRate || 0,
          afterTaxReturn: result.afterTaxReturn || 0,
          taxFreeLevel: result.taxFreeLevel || 0,
          capitalUnderlag: result.capitalUnderlag || 0
        };
      });

      const results = await Promise.all(promises);
      return results.filter(r => r !== null);
    } catch (error) {
      console.error('Error fetching tax comparison for export:', error);
      return null;
    }
  };

  // Build shared export payload for PDF and CSV
  const buildExportRequest = async () => {
    const portfolioData = {
      tickers: state.constructedPortfolio.map(s => s.symbol),
      weights: state.constructedPortfolio.reduce((acc, s) => {
        acc[s.symbol] = s.allocation / 100;
        return acc;
      }, {} as Record<string, number>),
      allocations: state.constructedPortfolio
    };
    const opt = state.optimizedPortfolio;
    const selectedForExport =
      selectedPortfolioType === 'market' && opt?.market_optimized_portfolio?.optimized_portfolio
        ? opt.market_optimized_portfolio.optimized_portfolio
        : selectedPortfolioType === 'weights' && opt?.weights_optimized_portfolio?.optimized_portfolio
          ? opt.weights_optimized_portfolio.optimized_portfolio
          : opt?.current_portfolio;
    const projectionMetricsForExport = selectedForExport ? {
      weights: (selectedForExport as any).weights ?? portfolioData.weights ?? {},
      expectedReturn: (selectedForExport as any).metrics?.expected_return ?? displayMetrics?.expectedReturn ?? portfolioMetrics?.expectedReturn ?? 0.08,
      risk: (selectedForExport as any).metrics?.risk ?? displayMetrics?.risk ?? portfolioMetrics?.risk ?? 0.15
    } : undefined;
    const metricsForExport = displayMetrics ? {
      expectedReturn: displayMetrics.expectedReturn,
      risk: displayMetrics.risk,
      diversificationScore: displayMetrics.diversificationScore,
      sharpeRatio: displayMetrics.sharpeRatio
    } : null;

    // Use already-fetched comparison when available to avoid duplicate API calls
    const taxComparison = (taxComparisonData && taxComparisonData.length >= 3)
      ? taxComparisonData
      : await fetchTaxComparisonForExport();

    // Calculate tax-free visualization data
    const taxFreeLevel = state.taxSettings.taxYear === 2025 ? 150000 : 300000;
    const taxableAmount = Math.max(0, capital - taxFreeLevel);
    const taxFreeAmount = Math.min(capital, taxFreeLevel);
    const taxFreeData = (state.taxSettings.accountType === 'ISK' || state.taxSettings.accountType === 'KF') ? {
      taxFreeLevel,
      taxFreeAmount,
      taxableAmount,
      taxFreePercentage: (taxFreeAmount / capital) * 100,
      taxablePercentage: (taxableAmount / capital) * 100,
      isTaxFree: taxableAmount === 0
    } : null;

    // Build recommendations summary for export
    const recommendations: string[] = [];

    if (state.taxSettings.taxYear === 2025 && capital < 300000 && taxCalculation) {
      const currentTax = taxCalculation.annualTax || 0;
      if (currentTax > 0) {
        recommendations.push(
          `Tax Year Optimization: Consider switching to 2026 tax year. With your capital (${capital.toLocaleString('sv-SE')} SEK) below the 2026 tax-free level (300,000 SEK), you could significantly reduce or eliminate taxes.`
        );
      }
    }

    if (taxComparison && taxComparison.length > 0) {
      const lowestTax = Math.min(...taxComparison.map((t: any) => t.annualTax));
      const currentAccountTax = taxComparison.find((t: any) => t.accountType === state.taxSettings.accountType);
      const lowestTaxAccount = taxComparison.find((t: any) => t.annualTax === lowestTax);

      if (currentAccountTax && lowestTaxAccount && currentAccountTax.annualTax > lowestTax + 100) {
        const savings = currentAccountTax.annualTax - lowestTax;
        recommendations.push(
          `Account Type Optimization: Switching from ${state.taxSettings.accountType} to ${lowestTaxAccount.accountType} could save approximately ${savings.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK per year (${(savings * 5).toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK over 5 years).`
        );
      }
    }

    if (metricsForExport && (state.taxSettings.accountType === 'ISK' || state.taxSettings.accountType === 'KF') && metricsForExport.expectedReturn > 0.08 && capital > 300000) {
      recommendations.push(
        `Optimal Configuration: With your expected return of ${(metricsForExport.expectedReturn * 100).toFixed(1)}%, using ${state.taxSettings.accountType} is optimal. You benefit from schablonbeskattning compared to traditional capital gains taxation.`
      );
    }

    return {
      portfolio: portfolioData,
      portfolioName: portfolioName,
      includeSections: {
        optimization: state.optimizedPortfolio != null,
        stressTest: state.stressTestResults != null,
        goals: false,
        rebalancing: false,
        taxEducation: true,
        taxComparison: true,
        recommendations: recommendations.length > 0
      },
      optimizationResults: state.optimizedPortfolio ?? undefined,
      projectionMetrics: projectionMetricsForExport,
      taxData: taxCalculation,
      costData: transactionCosts,
      stressTestResults: state.stressTestResults,
      portfolioValue: capital,
      accountType: state.taxSettings.accountType,
      taxYear: state.taxSettings.taxYear,
      courtageClass: state.taxSettings.courtagClass,
      metrics: metricsForExport,
      // New enhanced data for visualizations
      taxComparison,
      taxFreeData,
      recommendations,
      // Educational content summary
      educationalSummary: {
        selectedAccountType: state.taxSettings.accountType,
        taxYearInfo: {
          year: state.taxSettings.taxYear,
          taxFreeLevel: taxFreeLevel,
          schablonranta: state.taxSettings.taxYear === 2025 ? 2.96 : 3.55
        },
        courtageInfo: {
          class: state.taxSettings.courtagClass,
          setupCost: transactionCosts?.setupCost || 0,
          annualRebalancing: transactionCosts?.annualRebalancingCost || 0,
          totalFirstYear: transactionCosts?.totalFirstYearCost || 0
        }
      }
    };
  };

  const handleExportPdf = async () => {
    if (!state.taxSettings.accountType) return;
    setIsExporting(true);
    setExportingFormat('pdf');
    try {
      const exportRequest = await buildExportRequest();
      const pdfResponse = await fetch('/api/v1/portfolio/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exportRequest),
      });
      if (!pdfResponse.ok) throw new Error(`PDF export failed: ${pdfResponse.statusText}`);
      const blob = await pdfResponse.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `portfolio_report_${portfolioName.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      console.error('Export error:', error);
      alert(`PDF export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
      setExportingFormat(null);
    }
  };

  const handleExportCsv = async () => {
    if (!state.taxSettings.accountType) return;
    setIsExporting(true);
    setExportingFormat('csv');
    try {
      const exportRequest = await buildExportRequest();
      const csvResponse = await fetch('/api/v1/portfolio/export/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolio: exportRequest.portfolio,
          portfolioName: exportRequest.portfolioName,
          taxData: exportRequest.taxData,
          costData: exportRequest.costData,
          stressTestResults: exportRequest.stressTestResults,
          metrics: exportRequest.metrics,
          optimizationResults: exportRequest.optimizationResults,
          projectionMetrics: exportRequest.projectionMetrics,
          portfolioValue: exportRequest.portfolioValue,
          accountType: exportRequest.accountType,
          taxYear: exportRequest.taxYear,
          courtageClass: exportRequest.courtageClass,
          // Enhanced data
          taxComparison: exportRequest.taxComparison,
          taxFreeData: exportRequest.taxFreeData,
          recommendations: exportRequest.recommendations,
          educationalSummary: exportRequest.educationalSummary,
          includeFiles: ['holdings', 'tax', 'costs', 'metrics', 'stressTest', 'optimization', 'projection', 'taxComparison', 'recommendations']
        }),
      });
      if (!csvResponse.ok) throw new Error(`CSV export failed: ${csvResponse.statusText}`);
      const csvData = await csvResponse.json();
      if (csvData.zipFile) {
        const zipBlob = Uint8Array.from(atob(csvData.zipFile), c => c.charCodeAt(0));
        const zipUrl = window.URL.createObjectURL(new Blob([zipBlob], { type: 'application/zip' }));
        const zipA = document.createElement('a');
        zipA.href = zipUrl;
        zipA.download = `portfolio_data_${portfolioName.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.zip`;
        document.body.appendChild(zipA);
        zipA.click();
        window.URL.revokeObjectURL(zipUrl);
        document.body.removeChild(zipA);
      } else if (csvData.files?.length === 1) {
        const file = csvData.files[0];
        const content = atob(file.content || '');
        const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.filename || `portfolio_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error: any) {
      console.error('Export error:', error);
      alert(`CSV export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
      setExportingFormat(null);
    }
  };

  const handleComplete = () => {
    onComplete();
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Tabs value={hiddenTab || activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="builder" disabled={!canNavigateToTab('builder', state, activeTab)}>
            Portfolio Builder
          </TabsTrigger>
          <TabsTrigger
            value="optimize"
            disabled={!canNavigateToTab('optimize', state, activeTab) || (activeTab === 'builder' && !builderDone)}
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
        <TabsContent value="builder" className="space-y-4 mt-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Build Your Portfolio
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Select 3 to 4 stocks from the full universe and allocate 100% of your capital
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <PortfolioBuilder
                selectedStocks={state.constructedPortfolio}
                onStocksUpdate={handlePortfolioUpdate}
                onMetricsUpdate={handleMetricsUpdate}
                onDone={() => setBuilderDone(true)}
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

              {/* Continue to Optimize: enabled only after user presses Done and validation passes */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-block w-full">
                    <Button
                      onClick={() => handleTabChange('optimize')}
                      disabled={!builderDone || !canNavigateToTab('optimize', state, activeTab)}
                      className="w-full mt-4"
                      size="lg"
                    >
                      Continue
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-sm">
                  {!builderDone ? 'Press the Done button above to confirm your portfolio, then you can continue to Optimize.' : 'Continue to the Optimize tab.'}
                </TooltipContent>
              </Tooltip>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Optimize */}
        <TabsContent value="optimize" className="space-y-4 mt-3">
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
              {/* Current Portfolio Summary: max 2 decimals, Continue to Final Analysis */}
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
                            <div className="font-semibold text-sm">{Number((stock.allocation || 0).toFixed(2))}%</div>
                            <div className="text-xs text-muted-foreground">
                              {capital ? (stock.allocation / 100 * capital).toLocaleString('sv-SE', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) : '0'} SEK
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
                  
                  {displayMetrics && (
                    <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-border/50">
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-emerald-700">
                          {formatPercent(displayMetrics.expectedReturn)}
                        </div>
                        <div className="text-xs text-emerald-600 mt-0.5">Expected Return</div>
                      </div>
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-amber-700">
                          {formatPercent(displayMetrics.risk)}
                        </div>
                        <div className="text-xs text-amber-600 mt-0.5">Risk Level</div>
                      </div>
                      <div className="text-center p-3 bg-muted rounded-lg border border-border">
                        <div className="text-xl font-bold text-purple-700">
                          {formatPercent(displayMetrics.diversificationScore)}
                        </div>
                        <div className="text-xs text-purple-600 mt-0.5">Diversification</div>
                      </div>
                    </div>
                  )}

                  {/* Continue to Final Analysis (enabled when user can navigate to analysis) */}
                  <Button
                    onClick={() => handleTabChange('analysis')}
                    disabled={!canNavigateToTab('analysis', state, activeTab)}
                    className="w-full mt-4 bg-primary hover:bg-primary/90"
                    size="lg"
                  >
                    Continue to Final Analysis
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>

              {/* Optimize Button: disappears as soon as clicked to avoid double-submit */}
              {!isOptimizing && !optimizeButtonClicked && (
                <Button
                  onClick={() => {
                    setOptimizeButtonClicked(true);
                    handleOptimize();
                  }}
                  disabled={state.constructedPortfolio.length === 0}
                  className="w-full"
                  size="lg"
                >
                  <BarChart3 className="mr-2 h-4 w-4" />
                  Optimize
                </Button>
              )}
              {(isOptimizing || optimizeButtonClicked) && (
                <div className="flex items-center justify-center gap-2 py-3 text-sm text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Optimizing...
                </div>
              )}

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
                          selectedPortfolio={selectedPortfolioType}
                          onPortfolioSelect={handlePortfolioSelect}
                          showSelectionButtons={true}
                        />
                      </CardContent>
                    </Card>
                  )}

                  {/* Continue to Final Analysis: enabled when optimization ran and portfolio has at least one stock (Optimize→Analysis uses relaxed validation) */}
                  <Button
                    onClick={() => handleTabChange('analysis')}
                    disabled={!canNavigateToTab('analysis', state, activeTab)}
                    className="w-full mt-4 bg-primary hover:bg-primary/90"
                    size="lg"
                  >
                    Continue to Final Analysis
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
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
        <TabsContent value="analysis" className="space-y-4 mt-3">
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
                const selectedPortfolio = selectedPortfolioType;
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
              {!state.optimizedPortfolio?.comparison && displayMetrics && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Performance Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Expected Return</div>
                        <div className="text-2xl font-bold">{formatPercent(displayMetrics.expectedReturn)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Risk</div>
                        <div className="text-2xl font-bold">{formatPercent(displayMetrics.risk)}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
              {!state.optimizedPortfolio?.comparison && !displayMetrics && (
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
                source: selectedPortfolioType,
                tickers: state.constructedPortfolio.map(s => s.symbol),
                weights: state.constructedPortfolio.reduce((acc, s) => {
                  acc[s.symbol] = s.allocation / 100;
                  return acc;
                }, {} as Record<string, number>),
                metrics: displayMetrics ? {
                  expected_return: displayMetrics.expectedReturn,
                  risk: displayMetrics.risk,
                  sharpe_ratio: displayMetrics.sharpeRatio
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
        <TabsContent value="tax-cost" className="space-y-4 mt-3">
          {/* Educational Panel */}
          <TaxEducationPanel
            initialCapital={capital}
            initialTaxYear={state.taxSettings.taxYear}
          />

          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Tax, Cost & Summary
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Configure your account settings and see how taxes affect your portfolio
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
                  <label className="text-sm font-medium flex items-center gap-1.5">
                    Tax Year
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground" aria-label="Tax year info"><Info className="h-3.5 w-3.5" /></span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-sm">
                        <p className="font-medium mb-1">Tax rates by year (ISK/KF)</p>
                        <p className="text-xs mb-1"><strong>2025:</strong> Tax-free level 150,000 SEK; schablonränta 2.96%; effective rate about 0.89% on capital above the free amount.</p>
                        <p className="text-xs"> <strong>2026:</strong> Tax-free level 300,000 SEK; schablonränta 3.55%; effective rate about 1.07%. Choosing 2026 lowers tax if your capital is under 300k and changes the 5-year projection.</p>
                      </TooltipContent>
                    </Tooltip>
                  </label>
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
                  <label className="text-sm font-medium flex items-center gap-1.5">
                    Courtage Class
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground" aria-label="Courtage class info"><Info className="h-3.5 w-3.5" /></span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-sm">
                        <p className="font-medium mb-1">Avanza courtage (transaction fees) – how it is calculated</p>
                        <p className="text-xs mb-1"><strong>Start:</strong> Up to 50,000 SEK or 500 free trades; after that 0 SEK per trade.</p>
                        <p className="text-xs mb-1"><strong>Mini:</strong> 1 SEK or 0.25% per order (whichever is higher; orders up to 400 SEK = 1 SEK).</p>
                        <p className="text-xs mb-1"><strong>Small:</strong> 39 SEK or 0.15% (orders up to 26,000 SEK = 39 SEK).</p>
                        <p className="text-xs mb-1"><strong>Medium:</strong> 69 SEK or 0.069% (orders up to 100,000 SEK = 69 SEK).</p>
                        <p className="text-xs mb-1"><strong>Fast Pris:</strong> Fixed 99 SEK per order.</p>
                        <p className="text-xs">Used for initial setup and for each rebalancing. Total first-year and annual rebalancing costs are subtracted in the 5-year projection.</p>
                      </TooltipContent>
                    </Tooltip>
                  </label>
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

              {/* Total cost of ownership: tax + annual rebalancing */}
              {state.taxSettings.accountType && (taxCalculation != null || transactionCosts != null) && (
                <div className="rounded-lg border border-border bg-muted/30 px-4 py-3">
                  <p className="text-sm font-medium text-foreground">
                    Estimated annual burden (tax + rebalancing):{' '}
                    <span className="font-semibold">
                      {((taxCalculation?.annualTax ?? 0) + (transactionCosts?.annualRebalancingCost ?? 0)).toLocaleString('sv-SE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}{' '}
                      SEK
                    </span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Tax and courtage for rebalancing are applied each year in the 5-year projection.
                  </p>
                </div>
              )}

              {/* Tax Comparison Chart */}
              {state.taxSettings.accountType && portfolioMetrics && (
                <TaxComparisonChart
                  capital={capital}
                  taxYear={state.taxSettings.taxYear}
                  expectedReturn={displayMetrics?.expectedReturn || portfolioMetrics.expectedReturn}
                  selectedAccountType={state.taxSettings.accountType}
                  comparisonData={taxComparisonData}
                />
              )}

              {/* Tax-Free Visualization (only for ISK/KF) */}
              {state.taxSettings.accountType && taxCalculation && (state.taxSettings.accountType === 'ISK' || state.taxSettings.accountType === 'KF') && (
                <TaxFreeVisualization
                  capital={capital}
                  taxFreeLevel={taxCalculation.taxFreeLevel || (state.taxSettings.taxYear === 2025 ? 150000 : 300000)}
                  accountType={state.taxSettings.accountType}
                  taxYear={state.taxSettings.taxYear}
                />
              )}

              {/* What-If Calculator */}
              {state.taxSettings.accountType && portfolioMetrics && (
                <WhatIfCalculator
                  initialCapital={capital}
                  initialTaxYear={state.taxSettings.taxYear}
                  expectedReturn={displayMetrics?.expectedReturn || portfolioMetrics.expectedReturn}
                />
              )}

              {/* Section: Tax Summary */}
              {state.taxSettings.accountType && (
                <TaxSummaryCard
                  taxCalculation={taxCalculation}
                  isLoading={isLoadingTax}
                  portfolioMetrics={portfolioMetrics}
                  capital={capital}
                />
              )}

              {/* Section: Total & Ongoing Costs */}
              {state.taxSettings.courtagClass && (
                <TotalCostsCard
                  transactionCosts={transactionCosts}
                  isLoading={isLoadingCosts}
                />
              )}

              {/* 5-Year Projection: use the portfolio selected in Optimize (Current / Weights-Optimized / Market-Optimized) */}
              {(() => {
                const opt = state.optimizedPortfolio;
                const currentWeights = state.constructedPortfolio.length > 0
                  ? state.constructedPortfolio.reduce((acc, s) => {
                      acc[s.symbol] = s.allocation / 100;
                      return acc;
                    }, {} as Record<string, number>)
                  : {};
                const currentReturn = portfolioMetrics?.expectedReturn ?? 0.08;
                const currentRisk = portfolioMetrics?.risk ?? 0.15;

                let projectionWeights = currentWeights;
                let projectionExpectedReturn = currentReturn;
                let projectionRisk = currentRisk;

                if (selectedPortfolioType === 'weights' && opt?.weights_optimized_portfolio?.optimized_portfolio) {
                  const wo = opt.weights_optimized_portfolio.optimized_portfolio;
                  projectionWeights = wo.weights ?? currentWeights;
                  projectionExpectedReturn = wo.metrics?.expected_return ?? currentReturn;
                  projectionRisk = wo.metrics?.risk ?? currentRisk;
                } else if (selectedPortfolioType === 'market' && opt?.market_optimized_portfolio?.optimized_portfolio) {
                  const mo = opt.market_optimized_portfolio.optimized_portfolio;
                  projectionWeights = mo.weights ?? currentWeights;
                  projectionExpectedReturn = mo.metrics?.expected_return ?? currentReturn;
                  projectionRisk = mo.metrics?.risk ?? currentRisk;
                }
                // selectedPortfolioType === 'current' or no optimized data: use currentWeights, currentReturn, currentRisk (already set)

                return (
                  <FiveYearProjectionChart
                    weights={projectionWeights}
                    capital={capital}
                    accountType={state.taxSettings.accountType}
                    taxYear={state.taxSettings.taxYear}
                    courtageClass={state.taxSettings.courtagClass}
                    expectedReturn={projectionExpectedReturn}
                    risk={projectionRisk}
                    rebalancingFrequency="quarterly"
                  />
                );
              })()}

              <div className="mt-6 mb-4">
                <label className="text-sm font-medium mb-1.5 block">Portfolio Name (for report)</label>
                <Input
                  value={portfolioName}
                  onChange={(e) => setPortfolioName(e.target.value)}
                  placeholder="Enter portfolio name..."
                  className="max-w-md"
                />
              </div>

              {/* Export options: PDF and CSV (ZIP) */}
              <p className="text-sm text-muted-foreground mb-2">Export your report:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <Button
                  onClick={handleExportPdf}
                  variant="outline"
                  className="w-full"
                  size="lg"
                  disabled={!state.taxSettings.accountType || isExporting}
                >
                  {isExporting && exportingFormat === 'pdf' ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exporting PDF...
                    </>
                  ) : (
                    <>
                      <FileText className="mr-2 h-4 w-4" />
                      Download PDF report
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleExportCsv}
                  variant="outline"
                  className="w-full"
                  size="lg"
                  disabled={!state.taxSettings.accountType || isExporting}
                >
                  {isExporting && exportingFormat === 'csv' ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exporting CSV...
                    </>
                  ) : (
                    <>
                      <FileArchive className="mr-2 h-4 w-4" />
                      Download CSV (ZIP)
                    </>
                  )}
                </Button>
              </div>

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
