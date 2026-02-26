/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
  Info,
  BookOpen,
  ChevronDown,
  PieChart,
  ClipboardList,
  Receipt,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  PortfolioBuilder,
  PortfolioAllocation,
  PortfolioMetrics,
} from "./PortfolioBuilder";
import { PortfolioAnalyticsPanel } from "./PortfolioAnalyticsPanel";
import { usePortfolioState } from "@/hooks/usePortfolioState";
import { validateTab, canNavigateToTab } from "@/utils/tabValidation";
import { formatPercent, formatNumber } from "@/utils/numberFormat";
import { StressTest } from "./StressTest";
import { EfficientFrontierChart } from "./EfficientFrontierChart";
import { PortfolioComparisonTable } from "./PortfolioComparisonTable";
import {
  PerformanceSummaryCard,
  QualityScoreCard,
  MonteCarloCard,
} from "./FinalAnalysisComponents";
import { FiveYearProjectionChart } from "./FiveYearProjectionChart";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { TaxEducationPanel } from "./TaxEducationPanel";
import { TaxComparisonChart } from "./TaxComparisonChart";
import { TaxFreeVisualization } from "./TaxFreeVisualization";
import { WhatIfCalculator } from "./WhatIfCalculator";
import { TaxSummaryCard } from "./TaxSummaryCard";
import { TotalCostsCard } from "./TotalCostsCard";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
  riskProfile,
}) => {
  const {
    state,
    isLoaded,
    updateConstructedPortfolio,
    updateOptimizedPortfolio,
    updateStressTestResults,
    updateTaxSettings,
    markTabComplete,
    clearState,
  } = usePortfolioState();

  const [activeTab, setActiveTab] = useState<
    "builder" | "optimize" | "analysis" | "tax-cost"
  >("builder");
  const [hiddenTab, setHiddenTab] = useState<"stress-test" | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizeButtonClicked, setOptimizeButtonClicked] = useState(false); // hide button immediately on click
  const [optimizationError, setOptimizationError] = useState<string | null>(
    null,
  );
  const [portfolioMetrics, setPortfolioMetrics] =
    useState<PortfolioMetrics | null>(null);
  const [taxCalculation, setTaxCalculation] = useState<any>(null);
  const [transactionCosts, setTransactionCosts] = useState<any>(null);
  const [isLoadingTax, setIsLoadingTax] = useState(false);
  const [isLoadingCosts, setIsLoadingCosts] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<"pdf" | "csv" | null>(
    null,
  );
  const [portfolioName, setPortfolioName] = useState("My Investment Portfolio");
  const [selectedPortfolioType, setSelectedPortfolioType] = useState<
    "current" | "weights" | "market"
  >("current");
  const [taxComparisonData, setTaxComparisonData] = useState<any>(null);

  // Builder "Done" pressed: user must press Done in Portfolio Builder before Continue to Optimize
  const [builderDone, setBuilderDone] = useState(false);

  // Validation state
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string[]>
  >({});

  // Single source of truth for metrics shown on page and exported (PDF/CSV):
  // use the portfolio the user selected (Current / Weights / Market). Fall back to builder metrics when optimization isn't available.
  const displayMetrics = useMemo((): PortfolioMetrics | null => {
    const opt = state.optimizedPortfolio;
    const selected =
      selectedPortfolioType === "market" &&
      opt?.market_optimized_portfolio?.optimized_portfolio
        ? opt.market_optimized_portfolio.optimized_portfolio
        : selectedPortfolioType === "weights" &&
            opt?.weights_optimized_portfolio?.optimized_portfolio
          ? opt.weights_optimized_portfolio.optimized_portfolio
          : opt?.current_portfolio;

    const selectedMetrics: any = (selected as any)?.metrics;
    if (selectedMetrics) {
      return {
        expectedReturn:
          selectedMetrics.expected_return ??
          portfolioMetrics?.expectedReturn ??
          0,
        risk: selectedMetrics.risk ?? portfolioMetrics?.risk ?? 0,
        diversificationScore: portfolioMetrics?.diversificationScore ?? 0,
        sharpeRatio:
          selectedMetrics.sharpe_ratio ?? portfolioMetrics?.sharpeRatio ?? 0,
      };
    }
    return portfolioMetrics;
  }, [state.optimizedPortfolio, portfolioMetrics, selectedPortfolioType]);

  // Actionable insight line for tax tab (derived from comparison data)
  const taxInsightLine = useMemo(() => {
    const data = taxComparisonData;
    if (!data?.length || !state.taxSettings.accountType) return null;
    const low = Math.min(
      ...data.map((d: { annualTax: number }) => d.annualTax),
    );
    const cur = data.find(
      (d: { accountType: string }) =>
        d.accountType === state.taxSettings.accountType,
    );
    const best = data.find((d: { annualTax: number }) => d.annualTax === low);
    if (cur && best && cur.annualTax > low) {
      const savings = cur.annualTax - low;
      return `${best.accountType} saves you ${savings.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK/year vs ${cur.accountType}.`;
    }
    if (low === 0) return "You're in the tax-free zone for ISK/KF.";
    return null;
  }, [taxComparisonData, state.taxSettings.accountType]);

  // Validate current tab
  useEffect(() => {
    if (isLoaded) {
      const validation = validateTab(activeTab, state);
      setValidationErrors((prev) => ({
        ...prev,
        [activeTab]: validation.errors,
      }));
    }
  }, [activeTab, state, isLoaded]);

  // Handle tab change with validation (Optimize only reachable from Builder after Done)
  const handleTabChange = (newTab: string) => {
    if (newTab === "optimize" && activeTab === "builder" && !builderDone)
      return;
    if (canNavigateToTab(newTab, state, activeTab)) {
      setActiveTab(newTab as any);
      setValidationErrors({});
    } else {
      const validation = validateTab(newTab, state);
      setValidationErrors((prev) => ({
        ...prev,
        [newTab]: validation.errors,
      }));
    }
  };

  // Handle portfolio update from Tab 1 (search bar switch or allocation edit)
  const handlePortfolioUpdate = (stocks: PortfolioAllocation[]) => {
    updateConstructedPortfolio(stocks);
    // If user had already pressed Done, any change invalidates confirmation → Continue disabled until Done again
    setBuilderDone((prev) => (prev ? false : prev));
    // Reset selection type if manual changes are made
    setSelectedPortfolioType("current");

    // Validate allocation
    const totalAllocation = stocks.reduce(
      (sum, s) => sum + (s.allocation || 0),
      0,
    );
    if (
      stocks.length >= 3 &&
      stocks.length <= 4 &&
      Math.abs(totalAllocation - 100) < 0.1
    ) {
      markTabComplete("builder");
    }
  };

  // Handle metrics update
  const handleMetricsUpdate = (metrics: PortfolioMetrics | null) => {
    setPortfolioMetrics(metrics);
  };

  // Handle optimization (same request payload as PortfolioOptimization for identical results)
  const handleOptimize = async () => {
    if (state.constructedPortfolio.length === 0) {
      setOptimizationError("Please build a portfolio first");
      return;
    }

    setIsOptimizing(true);
    setOptimizationError(null);

    try {
      const userTickers = state.constructedPortfolio.map((s) => s.symbol);
      const userWeights = state.constructedPortfolio.reduce(
        (acc, s) => {
          acc[s.symbol] = s.allocation / 100;
          return acc;
        },
        {} as Record<string, number>,
      );

      const requestPayload = {
        user_tickers: userTickers,
        user_weights: userWeights,
        risk_profile: riskProfile,
        capital: capital,
        optimization_type: "max_sharpe",
        max_eligible_tickers: 20,
        include_efficient_frontier: true,
        include_random_portfolios: true,
        num_frontier_points: 20,
        num_random_portfolios: 300,
        use_combined_strategy: true,
        attempt_market_exploration: true,
      };

      const response = await fetch("/api/v1/portfolio/optimization/triple", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`Optimization failed: ${response.statusText}`);
      }

      const data = await response.json();
      updateOptimizedPortfolio(data);
      markTabComplete("optimize");
    } catch (error: any) {
      console.error("Optimization error:", error);
      setOptimizationError(error.message || "Failed to optimize portfolio");
    } finally {
      setIsOptimizing(false);
      setOptimizeButtonClicked(false);
    }
  };

  // Handle stress test navigation
  const handleRunStressTest = () => {
    const portfolio = state.optimizedPortfolio || {
      source: "current",
      tickers: state.constructedPortfolio.map((s) => s.symbol),
      weights: state.constructedPortfolio.reduce(
        (acc, s) => {
          acc[s.symbol] = s.allocation / 100;
          return acc;
        },
        {} as Record<string, number>,
      ),
      metrics: portfolioMetrics
        ? {
            expected_return: portfolioMetrics.expectedReturn,
            risk: portfolioMetrics.risk,
            sharpe_ratio: portfolioMetrics.sharpeRatio,
          }
        : {
            expected_return: 0.1,
            risk: 0.15,
            sharpe_ratio: 0.5,
          },
    };

    setHiddenTab("stress-test");
    setActiveTab("stress-test" as any);
  };

  // Handle stress test results
  const handleStressTestResults = (results: any) => {
    updateStressTestResults(results);
    setHiddenTab(null);
    setActiveTab("analysis");
  };

  // Handle portfolio selection from optimization results
  const handlePortfolioSelect = (type: "current" | "weights" | "market") => {
    if (!state.optimizedPortfolio) return;

    setSelectedPortfolioType(type);

    let selectedPortfolioData: any;
    if (type === "current" && state.optimizedPortfolio.current_portfolio) {
      selectedPortfolioData = state.optimizedPortfolio.current_portfolio;
    } else if (
      type === "weights" &&
      state.optimizedPortfolio.weights_optimized_portfolio
    ) {
      selectedPortfolioData =
        state.optimizedPortfolio.weights_optimized_portfolio
          .optimized_portfolio;
    } else if (
      type === "market" &&
      state.optimizedPortfolio.market_optimized_portfolio
    ) {
      selectedPortfolioData =
        state.optimizedPortfolio.market_optimized_portfolio.optimized_portfolio;
    }

    if (selectedPortfolioData) {
      // Map optimized weights back to PortfolioAllocation format
      const tickers: string[] =
        selectedPortfolioData.tickers ||
        (Array.isArray(selectedPortfolioData.tickers)
          ? selectedPortfolioData.tickers
          : []) ||
        selectedPortfolioData.tickers;
      const weights: Record<string, number> =
        selectedPortfolioData.weights || {};

      const sectorMap = new Map(
        state.constructedPortfolio
          .filter((s) => s.sector != null && s.sector !== "")
          .map((s) => [s.symbol, s.sector as string]),
      );
      const newStocks: PortfolioAllocation[] = (tickers || []).map((symbol) => {
        const existing = state.constructedPortfolio.find(
          (s) => s.symbol === symbol,
        );
        return {
          symbol,
          allocation: (weights[symbol] || 0) * 100,
          name: existing?.name ?? "",
          sector: existing?.sector ?? sectorMap.get(symbol),
          assetType: existing?.assetType,
        };
      });

      updateConstructedPortfolio(newStocks);
      // Mark builder as done since we just selected a valid optimized portfolio
      setBuilderDone(true);
      markTabComplete("builder");
    }
  };

  // Calculate tax when account type changes
  useEffect(() => {
    if (
      state.taxSettings.accountType &&
      state.taxSettings.taxYear &&
      capital > 0
    ) {
      setIsLoadingTax(true);
      const calculateTax = async () => {
        try {
          const expectedReturn =
            displayMetrics?.expectedReturn ??
            portfolioMetrics?.expectedReturn ??
            0.08;
          const requestBody: any = {
            accountType: state.taxSettings.accountType,
            taxYear: state.taxSettings.taxYear,
            expectedReturn,
          };

          if (
            state.taxSettings.accountType === "ISK" ||
            state.taxSettings.accountType === "KF"
          ) {
            requestBody.portfolioValue = capital;
          } else {
            // AF account - estimate based on expected return
            const estimatedGains = capital * expectedReturn;
            requestBody.realizedGains = estimatedGains;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }

          const response = await fetch("/api/v1/portfolio/tax/calculate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
          });

          if (!response.ok) {
            throw new Error(`Tax calculation failed: ${response.statusText}`);
          }

          const data = await response.json();
          setTaxCalculation(data);
        } catch (error: any) {
          console.error("Tax calculation error:", error);
          setTaxCalculation(null);
        } finally {
          setIsLoadingTax(false);
        }
      };

      calculateTax();
    } else {
      setTaxCalculation(null);
    }
  }, [
    state.taxSettings.accountType,
    state.taxSettings.taxYear,
    capital,
    portfolioMetrics,
    displayMetrics?.expectedReturn,
  ]);

  // Fetch 3-account tax comparison once (for chart and export); avoids duplicate calls from TaxComparisonChart
  useEffect(() => {
    if (capital <= 0 || !state.taxSettings.taxYear) {
      setTaxComparisonData(null);
      return;
    }
    const expectedRet =
      displayMetrics?.expectedReturn ??
      portfolioMetrics?.expectedReturn ??
      0.08;
    const accountTypes = ["ISK", "KF", "AF"];
    const promises = accountTypes.map(async (accountType) => {
      const requestBody: any = {
        accountType,
        taxYear: state.taxSettings.taxYear,
        expectedReturn: expectedRet,
      };
      if (accountType === "ISK" || accountType === "KF") {
        requestBody.portfolioValue = capital;
      } else {
        requestBody.realizedGains = capital * expectedRet;
        requestBody.dividends = 0;
        requestBody.fundHoldings = 0;
      }
      const response = await fetch("/api/v1/portfolio/tax/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!response.ok) return null;
      const result = await response.json();
      const annualTax = result.annualTax || 0;
      const effectiveRate =
        accountType === "AF" && capital > 0
          ? (annualTax / capital) * 100
          : (result.effectiveTaxRate ?? 0);
      return {
        accountType,
        annualTax,
        effectiveRate,
        displayName: accountType,
        afterTaxReturn: result.afterTaxReturn,
        taxFreeLevel: result.taxFreeLevel,
        capitalUnderlag: result.capitalUnderlag,
      };
    });
    Promise.all(promises)
      .then((results) => {
        setTaxComparisonData(
          results.filter((r): r is NonNullable<typeof r> => r !== null),
        );
      })
      .catch(() => setTaxComparisonData(null));
  }, [
    capital,
    state.taxSettings.taxYear,
    displayMetrics?.expectedReturn,
    portfolioMetrics?.expectedReturn,
  ]);

  // Calculate transaction costs when courtage class changes
  useEffect(() => {
    if (
      state.taxSettings.courtagClass &&
      state.constructedPortfolio.length > 0 &&
      capital > 0
    ) {
      setIsLoadingCosts(true);
      const calculateCosts = async () => {
        try {
          // Convert portfolio to transaction format
          const portfolio = state.constructedPortfolio.map((stock) => {
            const value = capital * (stock.allocation / 100);
            // Estimate shares (simplified - would need actual stock prices)
            const estimatedShares = Math.floor(value / 100); // Rough estimate
            return {
              ticker: stock.symbol,
              shares: estimatedShares,
              value: value,
            };
          });

          const response = await fetch(
            "/api/v1/portfolio/transaction-costs/estimate",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                courtageClass: state.taxSettings.courtagClass,
                portfolio: portfolio,
                rebalancingFrequency: "quarterly",
              }),
            },
          );

          if (!response.ok) {
            throw new Error(
              `Transaction cost calculation failed: ${response.statusText}`,
            );
          }

          const data = await response.json();
          setTransactionCosts(data);
        } catch (error: any) {
          console.error("Transaction cost calculation error:", error);
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
      const accountTypes = ["ISK", "KF", "AF"];
      const promises = accountTypes.map(async (accountType) => {
        const requestBody: any = {
          accountType,
          taxYear: state.taxSettings.taxYear,
        };

        if (accountType === "ISK" || accountType === "KF") {
          requestBody.portfolioValue = capital;
        } else {
          const estimatedGains =
            capital *
            (displayMetrics?.expectedReturn || portfolioMetrics.expectedReturn);
          requestBody.realizedGains = estimatedGains;
          requestBody.dividends = 0;
          requestBody.fundHoldings = 0;
        }

        const response = await fetch("/api/v1/portfolio/tax/calculate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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
          capitalUnderlag: result.capitalUnderlag || 0,
        };
      });

      const results = await Promise.all(promises);
      return results.filter((r) => r !== null);
    } catch (error) {
      console.error("Error fetching tax comparison for export:", error);
      return null;
    }
  };

  // Build shared export payload for PDF and CSV
  const buildExportRequest = async () => {
    const portfolioData = {
      tickers: state.constructedPortfolio.map((s) => s.symbol),
      weights: state.constructedPortfolio.reduce(
        (acc, s) => {
          acc[s.symbol] = s.allocation / 100;
          return acc;
        },
        {} as Record<string, number>,
      ),
      allocations: state.constructedPortfolio,
    };
    const opt = state.optimizedPortfolio;
    const selectedForExport =
      selectedPortfolioType === "market" &&
      opt?.market_optimized_portfolio?.optimized_portfolio
        ? opt.market_optimized_portfolio.optimized_portfolio
        : selectedPortfolioType === "weights" &&
            opt?.weights_optimized_portfolio?.optimized_portfolio
          ? opt.weights_optimized_portfolio.optimized_portfolio
          : opt?.current_portfolio;
    const projectionMetricsForExport = selectedForExport
      ? {
          weights:
            (selectedForExport as any).weights ?? portfolioData.weights ?? {},
          expectedReturn:
            (selectedForExport as any).metrics?.expected_return ??
            displayMetrics?.expectedReturn ??
            portfolioMetrics?.expectedReturn ??
            0.08,
          risk:
            (selectedForExport as any).metrics?.risk ??
            displayMetrics?.risk ??
            portfolioMetrics?.risk ??
            0.15,
        }
      : undefined;
    const metricsForExport = displayMetrics
      ? {
          expectedReturn: displayMetrics.expectedReturn,
          risk: displayMetrics.risk,
          diversificationScore: displayMetrics.diversificationScore,
          sharpeRatio: displayMetrics.sharpeRatio,
        }
      : null;

    // Use already-fetched comparison when available to avoid duplicate API calls
    const taxComparison =
      taxComparisonData && taxComparisonData.length >= 3
        ? taxComparisonData
        : await fetchTaxComparisonForExport();

    // Calculate tax-free visualization data
    const taxFreeLevel = state.taxSettings.taxYear === 2025 ? 150000 : 300000;
    const taxableAmount = Math.max(0, capital - taxFreeLevel);
    const taxFreeAmount = Math.min(capital, taxFreeLevel);
    const taxFreeData =
      state.taxSettings.accountType === "ISK" ||
      state.taxSettings.accountType === "KF"
        ? {
            taxFreeLevel,
            taxFreeAmount,
            taxableAmount,
            taxFreePercentage: (taxFreeAmount / capital) * 100,
            taxablePercentage: (taxableAmount / capital) * 100,
            isTaxFree: taxableAmount === 0,
          }
        : null;

    // Build recommendations summary for export
    const recommendations: string[] = [];

    if (
      state.taxSettings.taxYear === 2025 &&
      capital < 300000 &&
      taxCalculation
    ) {
      const currentTax = taxCalculation.annualTax || 0;
      if (currentTax > 0) {
        recommendations.push(
          `Tax Year Optimization: Consider switching to 2026 tax year. With your capital (${capital.toLocaleString("sv-SE")} SEK) below the 2026 tax-free level (300,000 SEK), you could significantly reduce or eliminate taxes.`,
        );
      }
    }

    if (taxComparison && taxComparison.length > 0) {
      const lowestTax = Math.min(...taxComparison.map((t: any) => t.annualTax));
      const currentAccountTax = taxComparison.find(
        (t: any) => t.accountType === state.taxSettings.accountType,
      );
      const lowestTaxAccount = taxComparison.find(
        (t: any) => t.annualTax === lowestTax,
      );

      if (
        currentAccountTax &&
        lowestTaxAccount &&
        currentAccountTax.annualTax > lowestTax + 100
      ) {
        const savings = currentAccountTax.annualTax - lowestTax;
        recommendations.push(
          `Account Type Optimization: Switching from ${state.taxSettings.accountType} to ${lowestTaxAccount.accountType} could save approximately ${savings.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK per year (${(savings * 5).toLocaleString("sv-SE", { maximumFractionDigits: 0 })} SEK over 5 years).`,
        );
      }
    }

    if (
      metricsForExport &&
      (state.taxSettings.accountType === "ISK" ||
        state.taxSettings.accountType === "KF") &&
      metricsForExport.expectedReturn > 0.08 &&
      capital > 300000
    ) {
      recommendations.push(
        `Optimal Configuration: With your expected return of ${(metricsForExport.expectedReturn * 100).toFixed(1)}%, using ${state.taxSettings.accountType} is optimal. You benefit from schablonbeskattning compared to traditional capital gains taxation.`,
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
        recommendations: recommendations.length > 0,
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
          schablonranta: state.taxSettings.taxYear === 2025 ? 2.96 : 3.55,
        },
        courtageInfo: {
          class: state.taxSettings.courtagClass,
          setupCost: transactionCosts?.setupCost || 0,
          annualRebalancing: transactionCosts?.annualRebalancingCost || 0,
          totalFirstYear: transactionCosts?.totalFirstYearCost || 0,
        },
      },
    };
  };

  const handleExportPdf = async () => {
    if (!state.taxSettings.accountType) return;
    setIsExporting(true);
    setExportingFormat("pdf");
    try {
      const exportRequest = await buildExportRequest();
      const pdfResponse = await fetch("/api/v1/portfolio/export/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(exportRequest),
      });
      if (!pdfResponse.ok)
        throw new Error(`PDF export failed: ${pdfResponse.statusText}`);
      const blob = await pdfResponse.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `portfolio_report_${portfolioName.replace(/[^a-zA-Z0-9]/g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      console.error("Export error:", error);
      alert(`PDF export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
      setExportingFormat(null);
    }
  };

  const handleExportCsv = async () => {
    if (!state.taxSettings.accountType) return;
    setIsExporting(true);
    setExportingFormat("csv");
    try {
      const exportRequest = await buildExportRequest();
      const csvResponse = await fetch("/api/v1/portfolio/export/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
          includeFiles: [
            "holdings",
            "tax",
            "costs",
            "metrics",
            "stressTest",
            "optimization",
            "projection",
            "taxComparison",
            "recommendations",
          ],
        }),
      });
      if (!csvResponse.ok)
        throw new Error(`CSV export failed: ${csvResponse.statusText}`);
      const csvData = await csvResponse.json();
      if (csvData.zipFile) {
        const zipBlob = Uint8Array.from(atob(csvData.zipFile), (c) =>
          c.charCodeAt(0),
        );
        const zipUrl = window.URL.createObjectURL(
          new Blob([zipBlob], { type: "application/zip" }),
        );
        const zipA = document.createElement("a");
        zipA.href = zipUrl;
        zipA.download = `portfolio_data_${portfolioName.replace(/[^a-zA-Z0-9]/g, "_")}_${new Date().toISOString().split("T")[0]}.zip`;
        document.body.appendChild(zipA);
        zipA.click();
        window.URL.revokeObjectURL(zipUrl);
        document.body.removeChild(zipA);
      } else if (csvData.files?.length === 1) {
        const file = csvData.files[0];
        const content = atob(file.content || "");
        const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download =
          file.filename ||
          `portfolio_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error: any) {
      console.error("Export error:", error);
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
      <Tabs
        value={hiddenTab || activeTab}
        onValueChange={handleTabChange}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger
            value="builder"
            disabled={!canNavigateToTab("builder", state, activeTab)}
          >
            Portfolio Builder
          </TabsTrigger>
          <TabsTrigger
            value="optimize"
            disabled={
              !canNavigateToTab("optimize", state, activeTab) ||
              (activeTab === "builder" && !builderDone)
            }
          >
            Optimize
          </TabsTrigger>
          <TabsTrigger
            value="analysis"
            disabled={!canNavigateToTab("analysis", state, activeTab)}
          >
            Final Analysis
          </TabsTrigger>
          <TabsTrigger
            value="tax-cost"
            disabled={!canNavigateToTab("tax-cost", state, activeTab)}
          >
            Tax & Summary
          </TabsTrigger>
          {hiddenTab === "stress-test" && (
            <TabsTrigger value="stress-test" className="hidden">
              Stress Test
            </TabsTrigger>
          )}
        </TabsList>

        {/* Tab 1: Portfolio Builder */}
        <TabsContent value="builder" className="space-y-4 mt-3">
          {/* Hero Header with Version B text */}
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <Card className="bg-gradient-to-br from-primary/5 via-background to-background border-primary/20 overflow-hidden">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <PieChart className="h-5 w-5 text-primary" />
                      </div>
                      Create Your Investment Portfolio
                    </CardTitle>
                    <p className="text-sm text-muted-foreground pl-11">
                      Choose your stocks from US, European, and Swedish markets,
                      then set your allocation
                    </p>
                  </div>
                </div>
                {/* Investment Details Banner */}
                <div className="mt-4 flex flex-wrap items-center gap-3 pl-11">
                  <Badge
                    variant="outline"
                    className="text-xs px-3 py-1 bg-emerald-50 border-emerald-200 text-emerald-700"
                  >
                    Investment:{" "}
                    {capital.toLocaleString("sv-SE", {
                      minimumFractionDigits: 0,
                    })}{" "}
                    SEK
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-xs px-3 py-1 bg-blue-50 border-blue-200 text-blue-700"
                  >
                    Risk:{" "}
                    {riskProfile.charAt(0).toUpperCase() + riskProfile.slice(1)}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-xs px-3 py-1 bg-purple-50 border-purple-200 text-purple-700"
                  >
                    Available Tickers: ~1,432
                  </Badge>
                </div>
              </CardHeader>
            </Card>
          </div>

          {/* Portfolio Builder Component */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-100">
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
          </div>

          {/* Portfolio Analytics Panel - appears after Done */}
          {state.constructedPortfolio.length >= 3 && builderDone && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 delay-200">
              <PortfolioAnalyticsPanel
                selectedStocks={state.constructedPortfolio}
                riskProfile={riskProfile}
                portfolioMetrics={portfolioMetrics}
              />
            </div>
          )}

          {/* Validation Errors */}
          {validationErrors.builder && validationErrors.builder.length > 0 && (
            <Alert
              variant="destructive"
              className="animate-in fade-in shake duration-300"
            >
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

          {/* Continue to Optimize Button */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 delay-300">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-block w-full">
                  <Button
                    onClick={() => handleTabChange("optimize")}
                    disabled={
                      !builderDone ||
                      !canNavigateToTab("optimize", state, activeTab)
                    }
                    className="w-full bg-primary hover:bg-primary/90 transition-all duration-200 shadow-sm hover:shadow-md"
                    size="lg"
                  >
                    Continue to Optimization
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-sm">
                {!builderDone
                  ? "Confirm your portfolio first by clicking the Confirm Portfolio button above."
                  : "Continue to optimize your portfolio allocation."}
              </TooltipContent>
            </Tooltip>
          </div>
        </TabsContent>

        {/* Tab 2: Optimize */}
        <TabsContent value="optimize" className="space-y-4 mt-3">
          {/* Header Card with animation */}
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <Card className="bg-gradient-to-br from-blue-500/5 via-background to-background border-blue-500/20">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <BarChart3 className="h-5 w-5 text-blue-600" />
                  </div>
                  Portfolio Optimization
                </CardTitle>
                <p className="text-sm text-muted-foreground pl-11">
                  Optimize your portfolio allocation to maximize risk-adjusted
                  returns
                </p>
              </CardHeader>
            </Card>
          </div>

          {/* Current Portfolio Summary Card with animation */}
          <div className="animate-in fade-in slide-in-from-left-2 duration-500 delay-100">
            <Card className="border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-emerald-500/10">
                    <ClipboardList className="h-4 w-4 text-emerald-600" />
                  </div>
                  <CardTitle className="text-base">
                    Current Portfolio Summary
                  </CardTitle>
                </div>
                <p className="text-xs text-muted-foreground mt-1 pl-8">
                  {state.constructedPortfolio.length} assets selected
                </p>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                {state.constructedPortfolio &&
                state.constructedPortfolio.length > 0 ? (
                  <div className="grid grid-cols-1 gap-2">
                    {state.constructedPortfolio.map((stock, index) => (
                      <div
                        key={stock.symbol}
                        className="flex items-center justify-between p-2.5 border rounded-lg bg-muted/30"
                      >
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-medium text-blue-600">
                              {index + 1}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium text-sm">
                              {stock.symbol}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {stock.name || "Stock"}
                            </div>
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="font-semibold text-sm">
                            {Number((stock.allocation || 0).toFixed(2))}%
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {capital
                              ? (
                                  (stock.allocation / 100) *
                                  capital
                                ).toLocaleString("sv-SE", {
                                  minimumFractionDigits: 0,
                                  maximumFractionDigits: 2,
                                })
                              : "0"}{" "}
                            SEK
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
                      <div className="text-xs text-emerald-600 mt-0.5">
                        Expected Return
                      </div>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg border border-border">
                      <div className="text-xl font-bold text-amber-700">
                        {formatPercent(displayMetrics.risk)}
                      </div>
                      <div className="text-xs text-amber-600 mt-0.5">
                        Risk Level
                      </div>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg border border-border">
                      <div className="text-xl font-bold text-purple-700">
                        {formatPercent(displayMetrics.diversificationScore)}
                      </div>
                      <div className="text-xs text-purple-600 mt-0.5">
                        Diversification
                      </div>
                    </div>
                  </div>
                )}

                {/* Continue to Final Analysis (enabled when user can navigate to analysis) */}
                <Button
                  onClick={() => handleTabChange("analysis")}
                  disabled={!canNavigateToTab("analysis", state, activeTab)}
                  className="w-full mt-4 bg-primary hover:bg-primary/90"
                  size="lg"
                >
                  Continue to Final Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Optimize Button with animation */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 delay-200">
            {!isOptimizing && !optimizeButtonClicked && (
              <Button
                onClick={() => {
                  setOptimizeButtonClicked(true);
                  handleOptimize();
                }}
                disabled={state.constructedPortfolio.length === 0}
                className="w-full bg-blue-600 hover:bg-blue-700 transition-all duration-200 shadow-sm hover:shadow-md"
                size="lg"
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                Run Optimization
              </Button>
            )}
            {(isOptimizing || optimizeButtonClicked) &&
              !state.optimizedPortfolio && (
                <div className="flex items-center justify-center gap-3 py-6 text-sm text-muted-foreground bg-muted/30 rounded-lg border border-border/50">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  <span>Optimizing your portfolio...</span>
                </div>
              )}
          </div>

          {/* Optimization Error */}
          {optimizationError && (
            <Alert
              variant="destructive"
              className="animate-in fade-in shake duration-300"
            >
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{optimizationError}</AlertDescription>
            </Alert>
          )}

          {/* Optimization Results with staggered animations */}
          {state.optimizedPortfolio && (
            <div className="space-y-4">
              {/* Success Message */}
              <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                <Alert className="bg-emerald-50 border-emerald-200">
                  <CheckCircle className="h-4 w-4 text-emerald-600" />
                  <AlertDescription className="text-emerald-800">
                    <strong>Optimization completed successfully!</strong>
                    <p className="text-sm mt-1">
                      Your portfolio has been optimized to maximize returns
                      while managing risk according to your {riskProfile}{" "}
                      profile.
                    </p>
                  </AlertDescription>
                </Alert>
              </div>

              {/* Efficient Frontier with animation */}
              <div className="animate-in fade-in slide-in-from-right-2 duration-500 delay-100">
                {(() => {
                  const frontierData =
                    state.optimizedPortfolio.market_optimized_portfolio ||
                    state.optimizedPortfolio.weights_optimized_portfolio;
                  const hasFrontier =
                    frontierData?.efficient_frontier &&
                    frontierData.efficient_frontier.length > 0;
                  if (!hasFrontier) return null;
                  return (
                    <EfficientFrontierChart
                      currentPortfolio={{
                        risk:
                          state.optimizedPortfolio.current_portfolio?.metrics
                            ?.risk ||
                          portfolioMetrics?.risk ||
                          0.15,
                        return:
                          state.optimizedPortfolio.current_portfolio?.metrics
                            ?.expected_return ||
                          portfolioMetrics?.expectedReturn ||
                          0.1,
                        name: "Current Portfolio",
                        type: "current",
                        sharpe_ratio:
                          state.optimizedPortfolio.current_portfolio?.metrics
                            ?.sharpe_ratio || portfolioMetrics?.sharpeRatio,
                      }}
                      efficientFrontier={frontierData.efficient_frontier}
                      inefficientFrontier={frontierData.inefficient_frontier}
                      randomPortfolios={frontierData.random_portfolios}
                      capitalMarketLine={frontierData.capital_market_line}
                      marketOptimizedPortfolio={
                        state.optimizedPortfolio.market_optimized_portfolio
                          ?.optimized_portfolio
                          ? {
                              risk: state.optimizedPortfolio
                                .market_optimized_portfolio.optimized_portfolio
                                .metrics.risk,
                              return:
                                state.optimizedPortfolio
                                  .market_optimized_portfolio
                                  .optimized_portfolio.metrics.expected_return,
                              name: "Market Optimized",
                              type: "market-optimized" as const,
                              sharpe_ratio:
                                state.optimizedPortfolio
                                  .market_optimized_portfolio
                                  .optimized_portfolio.metrics.sharpe_ratio,
                            }
                          : undefined
                      }
                      weightsOptimizedPortfolio={
                        state.optimizedPortfolio.weights_optimized_portfolio
                          ?.optimized_portfolio
                          ? {
                              risk: state.optimizedPortfolio
                                .weights_optimized_portfolio.optimized_portfolio
                                .metrics.risk,
                              return:
                                state.optimizedPortfolio
                                  .weights_optimized_portfolio
                                  .optimized_portfolio.metrics.expected_return,
                              name: "Weights Optimized",
                              type: "weights-optimized" as const,
                              sharpe_ratio:
                                state.optimizedPortfolio
                                  .weights_optimized_portfolio
                                  .optimized_portfolio.metrics.sharpe_ratio,
                            }
                          : undefined
                      }
                      showControls={true}
                      showInteractiveLegend={true}
                      weightsOptimizedTickerExample={
                        state.optimizedPortfolio.weights_optimized_portfolio
                          ?.optimized_portfolio?.tickers?.[0]
                      }
                    />
                  );
                })()}
              </div>

              {/* Portfolio Comparison with animation */}
              {state.optimizedPortfolio.current_portfolio &&
                state.optimizedPortfolio.weights_optimized_portfolio && (
                  <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-200">
                    <Card className="border-border/60 shadow-sm">
                      <CardContent className="pt-4">
                        <PortfolioComparisonTable
                          tripleOptimizationResults={{
                            current_portfolio: {
                              tickers:
                                state.optimizedPortfolio.current_portfolio
                                  .tickers ||
                                state.constructedPortfolio.map((s) => s.symbol),
                              weights:
                                state.optimizedPortfolio.current_portfolio
                                  .weights ||
                                state.constructedPortfolio.reduce(
                                  (acc, s) => {
                                    acc[s.symbol] = s.allocation / 100;
                                    return acc;
                                  },
                                  {} as Record<string, number>,
                                ),
                              metrics: {
                                expected_return:
                                  state.optimizedPortfolio.current_portfolio
                                    .metrics?.expected_return ||
                                  portfolioMetrics?.expectedReturn ||
                                  0,
                                risk:
                                  state.optimizedPortfolio.current_portfolio
                                    .metrics?.risk ||
                                  portfolioMetrics?.risk ||
                                  0,
                                sharpe_ratio:
                                  state.optimizedPortfolio.current_portfolio
                                    .metrics?.sharpe_ratio ||
                                  portfolioMetrics?.sharpeRatio ||
                                  0,
                              },
                            },
                            weights_optimized_portfolio: {
                              optimized_portfolio: {
                                tickers:
                                  state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.tickers,
                                weights:
                                  state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.weights,
                                metrics: {
                                  expected_return:
                                    state.optimizedPortfolio
                                      .weights_optimized_portfolio
                                      .optimized_portfolio.metrics
                                      .expected_return,
                                  risk: state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.metrics.risk,
                                  sharpe_ratio:
                                    state.optimizedPortfolio
                                      .weights_optimized_portfolio
                                      .optimized_portfolio.metrics.sharpe_ratio,
                                },
                              },
                            },
                            market_optimized_portfolio: state.optimizedPortfolio
                              .market_optimized_portfolio
                              ? {
                                  optimized_portfolio: {
                                    tickers:
                                      state.optimizedPortfolio
                                        .market_optimized_portfolio
                                        .optimized_portfolio.tickers,
                                    weights:
                                      state.optimizedPortfolio
                                        .market_optimized_portfolio
                                        .optimized_portfolio.weights,
                                    metrics: {
                                      expected_return:
                                        state.optimizedPortfolio
                                          .market_optimized_portfolio
                                          .optimized_portfolio.metrics
                                          .expected_return,
                                      risk: state.optimizedPortfolio
                                        .market_optimized_portfolio
                                        .optimized_portfolio.metrics.risk,
                                      sharpe_ratio:
                                        state.optimizedPortfolio
                                          .market_optimized_portfolio
                                          .optimized_portfolio.metrics
                                          .sharpe_ratio,
                                    },
                                  },
                                }
                              : null,
                            comparison: {
                              weights_vs_current: state.optimizedPortfolio
                                .comparison?.weights_vs_current || {
                                return_difference:
                                  (state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.metrics
                                    .expected_return || 0) -
                                  (state.optimizedPortfolio.current_portfolio
                                    .metrics?.expected_return || 0),
                                risk_difference:
                                  (state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.metrics.risk || 0) -
                                  (state.optimizedPortfolio.current_portfolio
                                    .metrics?.risk || 0),
                                sharpe_difference:
                                  (state.optimizedPortfolio
                                    .weights_optimized_portfolio
                                    .optimized_portfolio.metrics.sharpe_ratio ||
                                    0) -
                                  (state.optimizedPortfolio.current_portfolio
                                    .metrics?.sharpe_ratio || 0),
                              },
                              market_vs_current:
                                state.optimizedPortfolio.comparison
                                  ?.market_vs_current,
                              best_sharpe:
                                state.optimizedPortfolio.comparison
                                  ?.best_sharpe,
                            },
                            optimization_metadata:
                              state.optimizedPortfolio.optimization_metadata,
                          }}
                          selectedPortfolio={selectedPortfolioType}
                          onPortfolioSelect={handlePortfolioSelect}
                          showSelectionButtons={true}
                        />
                      </CardContent>
                    </Card>
                  </div>
                )}

              {/* Continue to Final Analysis Button with animation */}
              <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 delay-300">
                <Button
                  onClick={() => handleTabChange("analysis")}
                  disabled={!canNavigateToTab("analysis", state, activeTab)}
                  className="w-full bg-primary hover:bg-primary/90 transition-all duration-200 shadow-sm hover:shadow-md"
                  size="lg"
                >
                  Continue to Final Analysis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Validation Errors */}
          {validationErrors.optimize &&
            validationErrors.optimize.length > 0 && (
              <Alert
                variant="destructive"
                className="animate-in fade-in duration-200"
              >
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {validationErrors.optimize[0]}
                </AlertDescription>
              </Alert>
            )}
        </TabsContent>

        {/* Tab 3: Final Analysis */}
        <TabsContent value="analysis" className="space-y-4 mt-3">
          {/* Header Card with animation */}
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <Card className="bg-gradient-to-br from-purple-500/5 via-background to-background border-purple-500/20">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-purple-500/10">
                    <Shield className="h-5 w-5 text-purple-600" />
                  </div>
                  Final Analysis
                </CardTitle>
                <p className="text-sm text-muted-foreground pl-11">
                  Comprehensive analysis of your portfolio performance and risk
                  metrics
                </p>
              </CardHeader>
            </Card>
          </div>

          {/* Performance Summary, Quality Score, Monte Carlo from optimization (when available) */}
          {state.optimizedPortfolio?.comparison &&
            (() => {
              const triple = state.optimizedPortfolio;
              const selectedPortfolio = selectedPortfolioType;
              const isTriple = Boolean(triple.market_optimized_portfolio);
              return (
                <div className="space-y-4">
                  {/* Performance Summary with animation */}
                  <div className="animate-in fade-in slide-in-from-left-2 duration-500 delay-100">
                    <PerformanceSummaryCard
                      tripleOptimizationResults={triple}
                      selectedPortfolio={selectedPortfolio}
                      riskProfile={riskProfile}
                    />
                  </div>

                  {/* Quality Score with animation */}
                  {triple.comparison?.quality_scores && (
                    <div className="animate-in fade-in slide-in-from-right-2 duration-500 delay-200">
                      <QualityScoreCard
                        qualityData={triple.comparison.quality_scores}
                        selectedPortfolio={selectedPortfolio}
                        isTriple={isTriple}
                      />
                    </div>
                  )}

                  {/* Monte Carlo with animation */}
                  {triple.comparison?.monte_carlo && (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-300">
                      <MonteCarloCard
                        monteCarloData={triple.comparison.monte_carlo}
                        selectedPortfolio={selectedPortfolio}
                        isTriple={isTriple}
                      />
                    </div>
                  )}
                </div>
              );
            })()}

          {/* Fallback: simple metrics when no optimization run yet */}
          {!state.optimizedPortfolio?.comparison && displayMetrics && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <Card className="border-border/60 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base">
                    Performance Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-100">
                      <div className="text-sm text-emerald-600/80">
                        Expected Return
                      </div>
                      <div className="text-2xl font-bold text-emerald-700">
                        {formatPercent(displayMetrics.expectedReturn)}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-amber-50 border border-amber-100">
                      <div className="text-sm text-amber-600/80">Risk</div>
                      <div className="text-2xl font-bold text-amber-700">
                        {formatPercent(displayMetrics.risk)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {!state.optimizedPortfolio?.comparison && !displayMetrics && (
            <div className="animate-in fade-in duration-200">
              <Card className="border-dashed border-border/60 bg-muted/20">
                <CardContent className="py-8 text-center">
                  <Info className="h-10 w-10 mx-auto mb-3 text-muted-foreground/40" />
                  <p className="text-sm text-muted-foreground">
                    Run optimization in the Optimize tab to see full analysis
                    (Performance Summary, Quality Score, Monte Carlo) here.
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Stress Test Section with animation */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-400">
            <Card className="border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-orange-500/10">
                    <Shield className="h-4 w-4 text-orange-600" />
                  </div>
                  <CardTitle className="text-sm font-semibold">
                    Stress Testing
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Test how your portfolio would perform under extreme market
                  conditions
                </p>
                <Button
                  onClick={handleRunStressTest}
                  className="w-full"
                  size="default"
                  variant="outline"
                >
                  <Shield className="mr-2 h-4 w-4" />
                  Run Stress Test
                </Button>

                {state.stressTestResults && (
                  <Alert className="bg-emerald-50 border-emerald-200 animate-in fade-in slide-in-from-top-1 duration-200">
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                    <AlertDescription className="text-emerald-800">
                      Stress test completed. Resilience Score:{" "}
                      <strong>
                        {formatNumber(
                          state.stressTestResults.resilience_score,
                          {
                            maxDecimals: 0,
                          },
                        ) || "N/A"}
                      </strong>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Continue Button with animation */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 delay-500">
            <Button
              onClick={() => handleTabChange("tax-cost")}
              disabled={!canNavigateToTab("tax-cost", state, activeTab)}
              className="w-full bg-primary hover:bg-primary/90 transition-all duration-200 shadow-sm hover:shadow-md"
              size="lg"
            >
              Continue to Tax & Summary
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </TabsContent>

        {/* Hidden Tab: Stress Test */}
        {hiddenTab === "stress-test" && (
          <TabsContent value="stress-test" className="mt-6">
            <StressTest
              onNext={() => {
                setHiddenTab(null);
                setActiveTab("tax-cost");
              }}
              onPrev={() => {
                setHiddenTab(null);
                setActiveTab("analysis");
              }}
              onStressTestResults={updateStressTestResults}
              selectedPortfolio={{
                source: selectedPortfolioType,
                tickers: state.constructedPortfolio.map((s) => s.symbol),
                weights: state.constructedPortfolio.reduce(
                  (acc, s) => {
                    acc[s.symbol] = s.allocation / 100;
                    return acc;
                  },
                  {} as Record<string, number>,
                ),
                metrics: displayMetrics
                  ? {
                      expected_return: displayMetrics.expectedReturn,
                      risk: displayMetrics.risk,
                      sharpe_ratio: displayMetrics.sharpeRatio,
                    }
                  : {
                      expected_return: 0.1,
                      risk: 0.15,
                      sharpe_ratio: 0.5,
                    },
              }}
              capital={capital}
              riskProfile={riskProfile}
            />
          </TabsContent>
        )}

        {/* Tab 4: Tax, Cost & Summary */}
        <TabsContent value="tax-cost" className="space-y-4 mt-3">
          {/* Header Card with animation */}
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <Card className="bg-gradient-to-br from-amber-500/5 via-background to-background border-amber-500/20">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-amber-500/10">
                    <Calculator className="h-5 w-5 text-amber-600" />
                  </div>
                  Tax & Cost Summary
                </CardTitle>
                <p className="text-sm text-muted-foreground pl-11">
                  Configure tax settings and review your portfolio costs
                </p>
              </CardHeader>
            </Card>
          </div>

          {/* Swedish Investment Taxation — hidden until user opens it */}
          <div className="animate-in fade-in slide-in-from-left-2 duration-500 delay-100">
            <Collapsible className="rounded-lg border border-border bg-muted/30 shadow-sm">
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium hover:bg-muted/50 rounded-lg transition-colors group"
                >
                  <span className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-blue-600" />
                    Learn: Swedish Investment Taxation (ISK/KF vs AF)
                  </span>
                  <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <TaxEducationPanel
                  initialCapital={capital}
                  initialTaxYear={state.taxSettings.taxYear}
                />
              </CollapsibleContent>
            </Collapsible>
          </div>

          {/* Tax settings: account type, comparison, and optional what-if */}
          <div className="animate-in fade-in slide-in-from-right-2 duration-500 delay-200">
            <Card className="border-border/60 shadow-sm">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-amber-500/10">
                    <Calculator className="h-4 w-4 text-amber-600" />
                  </div>
                  <CardTitle className="text-base">Tax Settings</CardTitle>
                </div>
                <p className="text-sm text-muted-foreground mt-0.5 pl-8">
                  Set account type, tax year, and courtage for your report and
                  projections
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Settings: Account Type, Tax Year, Courtage (grid) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Account Type</label>
                    <Select
                      value={state.taxSettings.accountType || ""}
                      onValueChange={(value) =>
                        updateTaxSettings({ accountType: value as any })
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select account type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ISK">
                          ISK (Investeringssparkonto)
                        </SelectItem>
                        <SelectItem value="KF">
                          KF (Kapitalförsäkring)
                        </SelectItem>
                        <SelectItem value="AF">
                          AF (Aktie- och Fondkonto)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-1.5">
                      Tax Year
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span
                            className="inline-flex cursor-help text-muted-foreground hover:text-foreground"
                            aria-label="Tax year info"
                          >
                            <Info className="h-3.5 w-3.5" />
                          </span>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-sm">
                          <p className="font-medium mb-1">
                            Tax rates by year (ISK/KF)
                          </p>
                          <p className="text-xs mb-1">
                            <strong>2025:</strong> Tax-free level 150,000 SEK;
                            schablonränta 2.96%; effective rate about 0.89% on
                            capital above the free amount.
                          </p>
                          <p className="text-xs">
                            {" "}
                            <strong>2026:</strong> Tax-free level 300,000 SEK;
                            schablonränta 3.55%; effective rate about 1.07%.
                            Choosing 2026 lowers tax if your capital is under
                            300k and changes the 5-year projection.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </label>
                    <Select
                      value={String(state.taxSettings.taxYear)}
                      onValueChange={(value) =>
                        updateTaxSettings({
                          taxYear: parseInt(value, 10) as 2025 | 2026,
                        })
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Tax year" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="2025">2025</SelectItem>
                        <SelectItem value="2026">2026</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-1.5">
                      Courtage Class
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span
                            className="inline-flex cursor-help text-muted-foreground hover:text-foreground"
                            aria-label="Courtage class info"
                          >
                            <Info className="h-3.5 w-3.5" />
                          </span>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-sm">
                          <p className="font-medium mb-1">
                            Avanza courtage (transaction fees) – how it is
                            calculated
                          </p>
                          <p className="text-xs mb-1">
                            <strong>Start:</strong> Up to 50,000 SEK or 500 free
                            trades; after that 0 SEK per trade.
                          </p>
                          <p className="text-xs mb-1">
                            <strong>Mini:</strong> 1 SEK or 0.25% per order
                            (whichever is higher; orders up to 400 SEK = 1 SEK).
                          </p>
                          <p className="text-xs mb-1">
                            <strong>Small:</strong> 39 SEK or 0.15% (orders up
                            to 26,000 SEK = 39 SEK).
                          </p>
                          <p className="text-xs mb-1">
                            <strong>Medium:</strong> 69 SEK or 0.069% (orders up
                            to 100,000 SEK = 69 SEK).
                          </p>
                          <p className="text-xs mb-1">
                            <strong>Fast Pris:</strong> Fixed 99 SEK per order.
                          </p>
                          <p className="text-xs">
                            Used for the one-time setup (one order per holding).
                            Setup cost is subtracted in the 5-year projection.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </label>
                    <Select
                      value={state.taxSettings.courtagClass || ""}
                      onValueChange={(value) =>
                        updateTaxSettings({ courtagClass: value })
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select courtage class" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="start">Start</SelectItem>
                        <SelectItem value="mini">Mini</SelectItem>
                        <SelectItem value="small">Small</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="fastPris">Fast Pris</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Comparison chart (hero) */}
                {state.taxSettings.accountType && portfolioMetrics && (
                  <TaxComparisonChart
                    capital={capital}
                    taxYear={state.taxSettings.taxYear}
                    expectedReturn={
                      displayMetrics?.expectedReturn ||
                      portfolioMetrics.expectedReturn
                    }
                    selectedAccountType={state.taxSettings.accountType}
                    comparisonData={taxComparisonData}
                    noCard
                  />
                )}

                {/* Your annual tax (one line) */}
                {state.taxSettings.accountType && (
                  <TaxSummaryCard
                    taxCalculation={taxCalculation}
                    isLoading={isLoadingTax}
                    portfolioMetrics={portfolioMetrics}
                    capital={capital}
                    noCard
                    compact
                  />
                )}

                {/* Actionable insight */}
                {taxInsightLine && (
                  <p className="text-sm text-muted-foreground">
                    {taxInsightLine}
                  </p>
                )}

                {/* Optional: compare tax by capital and year (same card) */}
                {state.taxSettings.accountType && portfolioMetrics && (
                  <div className="border-t pt-4 space-y-2">
                    <Collapsible className="rounded-lg border border-border bg-muted/30">
                      <CollapsibleTrigger asChild>
                        <button
                          type="button"
                          className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm font-medium hover:bg-muted/50 rounded-lg transition-colors group"
                        >
                          <span className="flex items-center gap-2">
                            <Calculator className="h-3.5 w-3.5" />
                            Compare tax by capital and year
                          </span>
                          <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                        </button>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <WhatIfCalculator
                          initialCapital={capital}
                          initialTaxYear={state.taxSettings.taxYear}
                          expectedReturn={
                            displayMetrics?.expectedReturn ||
                            portfolioMetrics.expectedReturn
                          }
                        />
                      </CollapsibleContent>
                    </Collapsible>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Secondary: Transaction costs and Tax-Free with animation */}
          <div className="animate-in fade-in slide-in-from-left-2 duration-500 delay-300">
            <Card className="border-border/60 shadow-sm">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-emerald-500/10">
                    <Receipt className="h-4 w-4 text-emerald-600" />
                  </div>
                  <CardTitle className="text-base">
                    Costs & Tax-Free Level
                  </CardTitle>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 pl-8">
                  Setup costs and tax-free breakdown
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {state.taxSettings.courtagClass && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      Transaction costs (setup)
                    </p>
                    <TotalCostsCard
                      transactionCosts={transactionCosts}
                      isLoading={isLoadingCosts}
                      noCard
                    />
                  </div>
                )}
                {state.taxSettings.accountType &&
                  taxCalculation &&
                  (state.taxSettings.accountType === "ISK" ||
                    state.taxSettings.accountType === "KF") && (
                    <TaxFreeVisualization
                      capital={capital}
                      taxFreeLevel={
                        taxCalculation.taxFreeLevel ||
                        (state.taxSettings.taxYear === 2025 ? 150000 : 300000)
                      }
                      accountType={state.taxSettings.accountType}
                      taxYear={state.taxSettings.taxYear}
                    />
                  )}
              </CardContent>
            </Card>
          </div>

          {/* 5-Year Projection with animation */}
          <div className="animate-in fade-in slide-in-from-right-2 duration-500 delay-400">
            {(() => {
              const opt = state.optimizedPortfolio;
              const currentWeights =
                state.constructedPortfolio.length > 0
                  ? state.constructedPortfolio.reduce(
                      (acc, s) => {
                        acc[s.symbol] = s.allocation / 100;
                        return acc;
                      },
                      {} as Record<string, number>,
                    )
                  : {};
              const currentReturn = portfolioMetrics?.expectedReturn ?? 0.08;
              const currentRisk = portfolioMetrics?.risk ?? 0.15;

              let projectionWeights = currentWeights;
              let projectionExpectedReturn = currentReturn;
              let projectionRisk = currentRisk;

              if (
                selectedPortfolioType === "weights" &&
                opt?.weights_optimized_portfolio?.optimized_portfolio
              ) {
                const wo = opt.weights_optimized_portfolio.optimized_portfolio;
                projectionWeights = wo.weights ?? currentWeights;
                projectionExpectedReturn =
                  wo.metrics?.expected_return ?? currentReturn;
                projectionRisk = wo.metrics?.risk ?? currentRisk;
              } else if (
                selectedPortfolioType === "market" &&
                opt?.market_optimized_portfolio?.optimized_portfolio
              ) {
                const mo = opt.market_optimized_portfolio.optimized_portfolio;
                projectionWeights = mo.weights ?? currentWeights;
                projectionExpectedReturn =
                  mo.metrics?.expected_return ?? currentReturn;
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
          </div>

          {/* Portfolio name and export with animation */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-500">
            <Card className="border-border/60 shadow-sm">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-blue-500/10">
                    <FileText className="h-4 w-4 text-blue-600" />
                  </div>
                  <CardTitle className="text-base">Export Report</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">
                    Portfolio Name
                  </label>
                  <Input
                    value={portfolioName}
                    onChange={(e) => setPortfolioName(e.target.value)}
                    placeholder="Enter portfolio name..."
                    className="max-w-md"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Button
                    onClick={handleExportPdf}
                    variant="outline"
                    className="w-full hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
                    size="lg"
                    disabled={!state.taxSettings.accountType || isExporting}
                  >
                    {isExporting && exportingFormat === "pdf" ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Exporting PDF...
                      </>
                    ) : (
                      <>
                        <FileText className="mr-2 h-4 w-4" />
                        Download PDF Report
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={handleExportCsv}
                    variant="outline"
                    className="w-full hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-700 transition-colors"
                    size="lg"
                    disabled={!state.taxSettings.accountType || isExporting}
                  >
                    {isExporting && exportingFormat === "csv" ? (
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

                {validationErrors["tax-cost"] &&
                  validationErrors["tax-cost"].length > 0 && (
                    <Alert
                      variant="destructive"
                      className="animate-in fade-in duration-200"
                    >
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        {validationErrors["tax-cost"][0]}
                      </AlertDescription>
                    </Alert>
                  )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Navigation */}
      <div className="flex justify-between pt-6">
        <Button variant="outline" onClick={onPrev}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Previous
        </Button>
        {activeTab === "tax-cost" && state.taxSettings.accountType && (
          <Button onClick={handleComplete}>
            Complete
            <CheckCircle className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
};
