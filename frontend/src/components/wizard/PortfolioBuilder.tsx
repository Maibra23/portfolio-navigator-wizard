/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Search,
  Loader2,
  AlertTriangle,
  Info,
  CheckCircle,
  Plus,
  X,
  Percent,
  TrendingUp,
  Building2,
  Sparkles,
  Wallet,
  Shuffle,
} from "lucide-react";

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  sector?: string;
  assetType?: "stock" | "bond" | "etf";
}

export interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

interface StockResult {
  symbol: string;
  shortname: string;
  longname?: string;
  sector?: string;
  typeDisp?: string;
  exchange?: string;
  quoteType?: string;
  assetType?: "stock" | "bond" | "etf";
  dataQuality?: {
    is_sufficient: boolean;
    years_covered: number;
    data_points: number;
    data_source: string;
    issues?: string[];
  };
}

interface PortfolioBuilderProps {
  selectedStocks: PortfolioAllocation[];
  onStocksUpdate: (stocks: PortfolioAllocation[]) => void;
  onMetricsUpdate?: (metrics: PortfolioMetrics | null) => void;
  onDone?: () => void; // Called when user clicks Done (finalize workflow)
  riskProfile: string;
  capital: number;
  minStocks?: number; // Default: 3
  maxStocks?: number; // Default: 4
  fullUniverse?: boolean; // Default: true (no risk profile filtering)
  showValidation?: boolean; // Default: true
}

export const PortfolioBuilder: React.FC<PortfolioBuilderProps> = ({
  selectedStocks,
  onStocksUpdate,
  onMetricsUpdate,
  onDone,
  riskProfile,
  capital,
  minStocks = 3,
  maxStocks = 4,
  fullUniverse = true,
  showValidation = true,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showWeightEditor, setShowWeightEditor] = useState(false);
  const [portfolioMetrics, setPortfolioMetrics] =
    useState<PortfolioMetrics | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [tickerUniverse, setTickerUniverse] = useState<{
    count: number;
    regionLabels: string[];
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/v1/portfolio/ticker-universe")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const count = data.selectable_count;
        const labels = Array.isArray(data.regions)
          ? data.regions.map((r: { label: string }) => r.label)
          : [];
        if (typeof count === "number") {
          setTickerUniverse({ count, regionLabels: labels });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Calculate total allocation
  const totalAllocation = selectedStocks.reduce(
    (sum, stock) => sum + (stock.allocation || 0),
    0,
  );

  // Search stocks function
  const searchStocks = useCallback(
    async (query: string) => {
      if (!query.trim() || query.length < 1) {
        setSearchResults([]);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        console.log(`Searching for: "${query}"`);

        // Build search URL with optional risk profile filter
        const searchUrl = fullUniverse
          ? `/api/v1/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=20`
          : `/api/v1/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=20&risk_profile=${riskProfile}`;

        const response = await fetch(searchUrl);

        if (!response.ok) {
          throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success && data.results) {
          const formattedResults: StockResult[] = data.results.map(
            (result: any) => ({
              symbol: result.ticker,
              shortname: result.company_name || result.ticker,
              longname: result.company_name,
              sector: result.sector,
              assetType: "stock" as const,
              dataQuality: result.data_quality,
            }),
          );

          setSearchResults(formattedResults);
        } else {
          setSearchResults([]);
        }
      } catch (err: any) {
        console.error("Search error:", err);
        setError(err.message || "Failed to search stocks");
        setSearchResults([]);
      } finally {
        setIsLoading(false);
      }
    },
    [riskProfile, fullUniverse],
  );

  // Debounced search
  useEffect(() => {
    if (!searchTerm.trim()) {
      setSearchResults([]);
      return;
    }

    const timeoutId = setTimeout(() => {
      searchStocks(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, searchStocks]);

  // Add stock function - automatically allocate equally among all stocks
  const addStock = (stock: StockResult) => {
    // Validation checks
    if (selectedStocks.some((s) => s.symbol === stock.symbol)) {
      setError(`${stock.symbol} is already in your portfolio`);
      return;
    }

    if (selectedStocks.length >= maxStocks) {
      setError(`Maximum ${maxStocks} stocks allowed in portfolio`);
      return;
    }

    // Always equally allocate among all stocks (including the new one)
    const equalAllocation = 100 / (selectedStocks.length + 1);
    const newStock: PortfolioAllocation = {
      symbol: stock.symbol,
      allocation: equalAllocation,
      name: stock.shortname || stock.symbol,
      sector: stock.sector,
      assetType: stock.assetType || "stock",
    };

    // Update all stocks to have equal allocation
    const updatedStocks = [
      ...selectedStocks.map((s) => ({
        ...s,
        allocation: equalAllocation,
      })),
      newStock,
    ];

    onStocksUpdate(updatedStocks);
    setError(null);
  };

  // Remove stock function
  const removeStock = (symbol: string) => {
    const updatedStocks = selectedStocks.filter((s) => s.symbol !== symbol);

    if (updatedStocks.length > 0) {
      // Normalize remaining allocations to sum to 100%
      const remainingTotal = updatedStocks.reduce(
        (sum, s) => sum + s.allocation,
        0,
      );
      const normalizedStocks = updatedStocks.map((s) => ({
        ...s,
        allocation:
          remainingTotal > 0
            ? (s.allocation / remainingTotal) * 100
            : 100 / updatedStocks.length,
      }));

      onStocksUpdate(normalizedStocks);
    } else {
      onStocksUpdate([]);
    }
  };

  // Update allocation function
  const updateAllocation = (symbol: string, newAllocation: number) => {
    const updatedStocks = selectedStocks.map((stock) =>
      stock.symbol === symbol
        ? { ...stock, allocation: Math.max(0, Math.min(100, newAllocation)) }
        : stock,
    );

    onStocksUpdate(updatedStocks);
  };

  // Equal allocation function - equally distribute among all stocks
  const applyEqualAllocation = () => {
    if (selectedStocks.length === 0) return;

    const equalWeight = 100 / selectedStocks.length;
    const equallyAllocatedStocks = selectedStocks.map((stock) => ({
      ...stock,
      allocation: equalWeight,
    }));

    onStocksUpdate(equallyAllocatedStocks);
  };

  // Random allocation - random weights that sum to 100%
  const applyRandomAllocation = () => {
    if (selectedStocks.length === 0) return;

    const n = selectedStocks.length;
    const raw = selectedStocks.map(() => Math.random() + 0.1);
    const sum = raw.reduce((a, b) => a + b, 0);
    const scaled = raw.map((r) => (r / sum) * 100);
    // Round to 1 decimal and fix last so total is exactly 100
    const rounded = scaled.map((v, i) =>
      i < n - 1 ? Math.round(v * 10) / 10 : 0,
    );
    const roundedSum = rounded.slice(0, -1).reduce((a, b) => a + b, 0);
    rounded[n - 1] = Math.round((100 - roundedSum) * 10) / 10;

    const randomlyAllocatedStocks = selectedStocks.map((stock, i) => ({
      ...stock,
      allocation: rounded[i],
    }));

    onStocksUpdate(randomlyAllocatedStocks);
  };

  // Calculate portfolio metrics once the user confirms the portfolio with Done
  const calculateMetrics = useCallback(
    async (allocations: PortfolioAllocation[]) => {
      if (allocations.length === 0) {
        setPortfolioMetrics(null);
        if (onMetricsUpdate) {
          onMetricsUpdate(null);
        }
        return;
      }

      setIsLoadingMetrics(true);
      try {
        const response = await fetch("/api/v1/portfolio/calculate-metrics", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            allocations,
            riskProfile,
          }),
        });

        if (!response.ok) {
          throw new Error(
            `Failed to calculate metrics: ${response.statusText}`,
          );
        }

        const data = await response.json();
        const metrics: PortfolioMetrics = {
          expectedReturn: data.expectedReturn || 0,
          risk: data.risk || 0,
          diversificationScore: data.diversificationScore || 0,
          sharpeRatio: data.sharpeRatio || 0,
        };

        setPortfolioMetrics(metrics);
        if (onMetricsUpdate) {
          onMetricsUpdate(metrics);
        }
      } catch (err) {
        console.error("Error calculating metrics:", err);
        setPortfolioMetrics(null);
        if (onMetricsUpdate) {
          onMetricsUpdate(null);
        }
      } finally {
        setIsLoadingMetrics(false);
      }
    },
    [riskProfile, onMetricsUpdate],
  );

  // Validation
  const isValidStockCount =
    selectedStocks.length >= minStocks && selectedStocks.length <= maxStocks;
  const isValidAllocation = Math.abs(totalAllocation - 100) < 0.1;
  const isValid = isValidStockCount && isValidAllocation;

  // Done handler for finalize workflow
  const handleDone = () => {
    // Require valid stock count (3–4) before proceeding
    if (!isValidStockCount) {
      setError(
        `Please select between ${minStocks} and ${maxStocks} stocks before continuing.`,
      );
      return;
    }

    // If no weights are set at all, auto-distribute equally across selected tickers
    let nextStocks = selectedStocks;
    const currentTotal = selectedStocks.reduce(
      (sum, s) => sum + (s.allocation || 0),
      0,
    );

    if (selectedStocks.length > 0 && Math.abs(currentTotal) < 0.0001) {
      const equalWeight = 100 / selectedStocks.length;
      nextStocks = selectedStocks.map((s) => ({
        ...s,
        allocation: parseFloat(equalWeight.toFixed(2)),
      }));
      onStocksUpdate(nextStocks);
    } else if (
      selectedStocks.length > 0 &&
      Math.abs(currentTotal - 100) > 0.1
    ) {
      // If there are some weights but they don't sum to ~100%, normalize them
      const normalized = selectedStocks.map((s) => ({
        ...s,
        allocation: currentTotal > 0 ? (s.allocation / currentTotal) * 100 : 0,
      }));
      nextStocks = normalized;
      onStocksUpdate(nextStocks);
    } else {
      // Allocation already ~100%: sync parent state so Continue can use latest portfolio
      onStocksUpdate(selectedStocks);
    }

    // Calculate metrics immediately for the confirmed portfolio
    calculateMetrics(nextStocks);
    onDone?.();
  };

  // Progress calculation for visual feedback
  const stockProgress = (selectedStocks.length / maxStocks) * 100;
  const allocationProgress = Math.min(totalAllocation, 100);

  return (
    <div className="space-y-4">
      {/* Search Section - Clean and prominent */}
      <Card className="border-border/60 shadow-sm overflow-hidden">
        <CardHeader className="pb-3 bg-gradient-to-r from-muted/30 to-transparent">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-primary/10">
                <Search className="h-4 w-4 text-primary" />
              </div>
              <CardTitle className="text-sm font-semibold">
                Find Stocks
              </CardTitle>
            </div>
            {tickerUniverse && (
              <Badge variant="secondary" className="text-xs font-normal">
                {tickerUniverse.count.toLocaleString()} tickers available
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by ticker or company name (e.g., AAPL, Apple)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 h-10 bg-background"
            />
            {isLoading && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-3 flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Search Results */}
          {searchTerm.trim() && searchResults.length > 0 && (
            <div className="mt-3 space-y-1.5 max-h-64 overflow-y-auto animate-in fade-in slide-in-from-top-2 duration-300">
              {searchResults.map((stock, index) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/40 hover:border-border transition-all duration-150 group"
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-primary">
                        {stock.symbol.slice(0, 2)}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-sm">
                        {stock.symbol}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {stock.shortname}
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => addStock(stock)}
                    size="sm"
                    variant={
                      selectedStocks.some((s) => s.symbol === stock.symbol)
                        ? "secondary"
                        : "default"
                    }
                    disabled={
                      selectedStocks.some((s) => s.symbol === stock.symbol) ||
                      selectedStocks.length >= maxStocks
                    }
                    className="h-8 px-3 text-xs"
                  >
                    {selectedStocks.some((s) => s.symbol === stock.symbol) ? (
                      <>
                        <CheckCircle className="h-3 w-3 mr-1" /> Added
                      </>
                    ) : (
                      <>
                        <Plus className="h-3 w-3 mr-1" /> Add
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* No results message */}
          {searchTerm.trim() && !isLoading && searchResults.length === 0 && (
            <div className="mt-3 text-center py-6 text-muted-foreground animate-in fade-in duration-200">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No stocks found for "{searchTerm}"</p>
              <p className="text-xs mt-1">
                Try a different ticker or company name
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Portfolio Summary - Visual progress indicators */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-emerald-500/10">
                <Wallet className="h-4 w-4 text-emerald-600" />
              </div>
              <CardTitle className="text-sm font-semibold">
                Your Portfolio
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant={isValidStockCount ? "default" : "secondary"}
                className={`text-xs ${isValidStockCount ? "bg-emerald-500/90" : ""}`}
              >
                {selectedStocks.length} of {minStocks}-{maxStocks} stocks
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-2">
          {/* Progress Indicators */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Stock Selection</span>
                <span
                  className={`font-medium ${isValidStockCount ? "text-emerald-600" : "text-amber-600"}`}
                >
                  {selectedStocks.length}/{maxStocks}
                </span>
              </div>
              <Progress value={stockProgress} className="h-1.5" />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Allocation</span>
                <span
                  className={`font-medium ${isValidAllocation ? "text-emerald-600" : totalAllocation > 100 ? "text-red-600" : "text-amber-600"}`}
                >
                  {totalAllocation.toFixed(1)}%
                </span>
              </div>
              <Progress
                value={allocationProgress}
                className={`h-1.5 ${totalAllocation > 100 ? "[&>div]:bg-red-500" : ""}`}
              />
            </div>
          </div>

          {/* Selected Stocks List */}
          {selectedStocks.length > 0 ? (
            <div className="space-y-2">
              {selectedStocks.map((stock, index) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/30 transition-colors group animate-in fade-in slide-in-from-left-2 duration-200"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                      <span className="text-xs font-bold text-primary">
                        {index + 1}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-sm">
                        {stock.symbol}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {stock.name || stock.symbol}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {showWeightEditor ? (
                      <div className="flex items-center gap-1.5">
                        <Input
                          type="number"
                          value={stock.allocation || ""}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value === "") {
                              updateAllocation(stock.symbol, 0);
                            } else {
                              const numValue = parseFloat(value);
                              if (!isNaN(numValue)) {
                                updateAllocation(stock.symbol, numValue);
                              }
                            }
                          }}
                          onBlur={(e) => {
                            const value = e.target.value;
                            if (value === "" || isNaN(parseFloat(value))) {
                              updateAllocation(stock.symbol, 0);
                            }
                          }}
                          className={`w-16 h-8 text-center text-sm ${stock.allocation > 100 ? "border-red-500 bg-red-50" : ""}`}
                          min="0"
                          max="100"
                          step="0.1"
                          placeholder="0"
                        />
                        <Percent className="h-3 w-3 text-muted-foreground" />
                      </div>
                    ) : (
                      <Badge variant="outline" className="text-xs font-medium">
                        {stock.allocation?.toFixed(1)}%
                      </Badge>
                    )}
                    <Button
                      onClick={() => removeStock(stock.symbol)}
                      size="sm"
                      variant="ghost"
                      className="h-8 w-8 p-0 opacity-50 group-hover:opacity-100 hover:bg-red-100 hover:text-red-600 transition-all"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 border border-dashed border-border/60 rounded-lg bg-muted/10 animate-in fade-in duration-300">
              <Building2 className="h-10 w-10 mx-auto mb-3 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                No stocks selected yet
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Search above to add stocks to your portfolio
              </p>
            </div>
          )}

          {/* Allocation Controls */}
          {selectedStocks.length > 0 && (
            <div className="flex items-center justify-between pt-2 border-t border-border/30">
              <div className="flex items-center gap-2">
                <Switch
                  id="weight-editor"
                  checked={showWeightEditor}
                  onCheckedChange={setShowWeightEditor}
                />
                <label
                  htmlFor="weight-editor"
                  className="text-xs text-muted-foreground cursor-pointer"
                >
                  Edit allocations manually
                </label>
              </div>
              {showWeightEditor && (
                <div className="flex flex-col gap-1.5">
                  <Button
                    onClick={applyEqualAllocation}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                  >
                    <Sparkles className="h-3 w-3 mr-1" />
                    Equal Split
                  </Button>
                  <Button
                    onClick={applyRandomAllocation}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                  >
                    <Shuffle className="h-3 w-3 mr-1" />
                    Random allocation
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Validation Status - Compact inline messages */}
          {showValidation && selectedStocks.length > 0 && (
            <div className="space-y-2 pt-2">
              {!isValidStockCount && (
                <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-md px-3 py-2 animate-in fade-in slide-in-from-top-1 duration-200">
                  <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>
                    {selectedStocks.length < minStocks
                      ? `Add ${minStocks - selectedStocks.length} more stock${minStocks - selectedStocks.length > 1 ? "s" : ""} (minimum ${minStocks} required)`
                      : `Remove ${selectedStocks.length - maxStocks} stock${selectedStocks.length - maxStocks > 1 ? "s" : ""} (maximum ${maxStocks} allowed)`}
                  </span>
                </div>
              )}

              {isValidStockCount && !isValidAllocation && (
                <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-md px-3 py-2 animate-in fade-in slide-in-from-top-1 duration-200">
                  <Info className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>
                    {totalAllocation > 100
                      ? `Reduce allocation by ${(totalAllocation - 100).toFixed(1)}% to reach 100%`
                      : `Add ${(100 - totalAllocation).toFixed(1)}% to complete allocation`}
                  </span>
                </div>
              )}

              {isValid && (
                <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 rounded-md px-3 py-2 animate-in fade-in slide-in-from-top-1 duration-200">
                  <CheckCircle className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>
                    Portfolio ready - {selectedStocks.length} stocks, 100%
                    allocated
                  </span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Performance Metrics Card - Shows after Done */}
      {portfolioMetrics && (
        <Card className="border-border/60 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-purple-500/10">
                <TrendingUp className="h-4 w-4 text-purple-600" />
              </div>
              <CardTitle className="text-sm font-semibold">
                Portfolio Metrics
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingMetrics ? (
              <div className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Calculating metrics...
              </div>
            ) : (
              <div className="grid grid-cols-4 gap-3">
                <div className="text-center p-3 rounded-lg bg-emerald-50 border border-emerald-100">
                  <div className="text-lg font-bold text-emerald-700">
                    {(portfolioMetrics.expectedReturn * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-emerald-600/80">
                    Expected Return
                  </div>
                </div>
                <div className="text-center p-3 rounded-lg bg-amber-50 border border-amber-100">
                  <div className="text-lg font-bold text-amber-700">
                    {(portfolioMetrics.risk * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-amber-600/80">Risk</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-blue-50 border border-blue-100">
                  <div className="text-lg font-bold text-blue-700">
                    {portfolioMetrics.diversificationScore.toFixed(0)}%
                  </div>
                  <div className="text-xs text-blue-600/80">
                    Diversification
                  </div>
                </div>
                <div className="text-center p-3 rounded-lg bg-purple-50 border border-purple-100">
                  <div className="text-lg font-bold text-purple-700">
                    {portfolioMetrics.sharpeRatio.toFixed(2)}
                  </div>
                  <div className="text-xs text-purple-600/80">Sharpe Ratio</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Done Button - Prominent call to action */}
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={handleDone}
          disabled={
            !isValidStockCount ||
            isLoadingMetrics ||
            selectedStocks.length === 0
          }
          size="lg"
          className="px-8 bg-primary hover:bg-primary/90 transition-all duration-200 shadow-sm hover:shadow-md"
        >
          {isLoadingMetrics ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4 mr-2" />
              Confirm Portfolio
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
