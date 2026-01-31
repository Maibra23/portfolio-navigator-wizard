/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Search, 
  Loader2,
  AlertTriangle,
  Info,
  CheckCircle
} from 'lucide-react';

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
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
  typeDisp?: string;
  exchange?: string;
  quoteType?: string;
  assetType?: 'stock' | 'bond' | 'etf';
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
  riskProfile,
  capital,
  minStocks = 3,
  maxStocks = 4,
  fullUniverse = true,
  showValidation = true
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showWeightEditor, setShowWeightEditor] = useState(false);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);

  // Calculate total allocation
  const totalAllocation = selectedStocks.reduce((sum, stock) => sum + (stock.allocation || 0), 0);

  // Search stocks function
  const searchStocks = useCallback(async (query: string) => {
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
        ? `/api/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=20`
        : `/api/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=20&risk_profile=${riskProfile}`;

      const response = await fetch(searchUrl);
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success && data.results) {
        const formattedResults: StockResult[] = data.results.map((result: any) => ({
          symbol: result.ticker,
          shortname: result.company_name || result.ticker,
          longname: result.company_name,
          assetType: 'stock' as const,
          dataQuality: result.data_quality
        }));
        
        setSearchResults(formattedResults);
      } else {
        setSearchResults([]);
      }
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to search stocks');
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [riskProfile, fullUniverse]);

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
    if (selectedStocks.some(s => s.symbol === stock.symbol)) {
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
      assetType: stock.assetType || 'stock'
    };
    
    // Update all stocks to have equal allocation
    const updatedStocks = [...selectedStocks.map(s => ({
      ...s,
      allocation: equalAllocation
    })), newStock];
    
    onStocksUpdate(updatedStocks);
    setError(null);
  };

  // Remove stock function
  const removeStock = (symbol: string) => {
    const updatedStocks = selectedStocks.filter(s => s.symbol !== symbol);
    
    if (updatedStocks.length > 0) {
      // Normalize remaining allocations to sum to 100%
      const remainingTotal = updatedStocks.reduce((sum, s) => sum + s.allocation, 0);
      const normalizedStocks = updatedStocks.map(s => ({
        ...s,
        allocation: remainingTotal > 0 ? (s.allocation / remainingTotal) * 100 : 100 / updatedStocks.length
      }));
      
      onStocksUpdate(normalizedStocks);
    } else {
      onStocksUpdate([]);
    }
  };

  // Update allocation function
  const updateAllocation = (symbol: string, newAllocation: number) => {
    const updatedStocks = selectedStocks.map(stock => 
      stock.symbol === symbol ? { ...stock, allocation: Math.max(0, Math.min(100, newAllocation)) } : stock
    );
    
    onStocksUpdate(updatedStocks);
  };

  // Equal allocation function - equally distribute among all stocks
  const applyEqualAllocation = () => {
    if (selectedStocks.length === 0) return;
    
    const equalWeight = 100 / selectedStocks.length;
    const equallyAllocatedStocks = selectedStocks.map(stock => ({
      ...stock,
      allocation: equalWeight
    }));
    
    onStocksUpdate(equallyAllocatedStocks);
  };

  // Calculate portfolio metrics once the user confirms the portfolio with Done
  const calculateMetrics = useCallback(async (allocations: PortfolioAllocation[]) => {
    if (allocations.length === 0) {
      setPortfolioMetrics(null);
      if (onMetricsUpdate) {
        onMetricsUpdate(null);
      }
      return;
    }

    setIsLoadingMetrics(true);
    try {
      const response = await fetch('/api/portfolio/calculate-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          allocations,
          riskProfile
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to calculate metrics: ${response.statusText}`);
      }

      const data = await response.json();
      const metrics: PortfolioMetrics = {
        expectedReturn: data.expectedReturn || 0,
        risk: data.risk || 0,
        diversificationScore: data.diversificationScore || 0,
        sharpeRatio: data.sharpeRatio || 0
      };
      
      setPortfolioMetrics(metrics);
      if (onMetricsUpdate) {
        onMetricsUpdate(metrics);
      }
    } catch (err) {
      console.error('Error calculating metrics:', err);
      setPortfolioMetrics(null);
      if (onMetricsUpdate) {
        onMetricsUpdate(null);
      }
    } finally {
      setIsLoadingMetrics(false);
    }
  }, [riskProfile, onMetricsUpdate]);

  // Validation
  const isValidStockCount = selectedStocks.length >= minStocks && selectedStocks.length <= maxStocks;
  const isValidAllocation = Math.abs(totalAllocation - 100) < 0.1;
  const isValid = isValidStockCount && isValidAllocation;

  // Done handler for finalize workflow
  const handleDone = () => {
    // Require valid stock count (3–4) before proceeding
    if (!isValidStockCount) {
      setError(`Please select between ${minStocks} and ${maxStocks} stocks before continuing.`);
      return;
    }

    // If no weights are set at all, auto-distribute equally across selected tickers
    let nextStocks = selectedStocks;
    const currentTotal = selectedStocks.reduce((sum, s) => sum + (s.allocation || 0), 0);

    if (selectedStocks.length > 0 && Math.abs(currentTotal) < 0.0001) {
      const equalWeight = 100 / selectedStocks.length;
      nextStocks = selectedStocks.map((s) => ({
        ...s,
        allocation: parseFloat(equalWeight.toFixed(2)),
      }));
      onStocksUpdate(nextStocks);
    } else if (selectedStocks.length > 0 && Math.abs(currentTotal - 100) > 0.1) {
      // If there are some weights but they don't sum to ~100%, normalize them
      const normalized = selectedStocks.map((s) => ({
        ...s,
        allocation: currentTotal > 0 ? (s.allocation / currentTotal) * 100 : 0,
      }));
      nextStocks = normalized;
      onStocksUpdate(nextStocks);
    }

    // Calculate metrics immediately for the confirmed portfolio
    calculateMetrics(nextStocks);
    onDoneProp?.();
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Customize Your Portfolio</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          {fullUniverse 
            ? 'Search and select stocks from the full universe (~600 tickers)'
            : 'Modify the selected portfolio by adding or removing stocks and adjusting allocations'
          }
        </p>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {/* Stock Search */}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">
              Add More Stocks
            </label>
            <div className="flex gap-2">
              <Input
                type="text"
                placeholder="Search for stocks (e.g., AAPL, MSFT)"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1"
              />
              <Button
                onClick={() => searchStocks(searchTerm)}
                disabled={!searchTerm.trim() || isLoading}
                size="sm"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
              </Button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="py-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}

          {/* Search Results */}
          {searchTerm.trim() && searchResults.length > 0 && (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-2">
              <h4 className="text-sm font-medium">Search Results:</h4>
              {searchResults.map((stock) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                >
                  <div>
                    <div className="font-medium">{stock.symbol}</div>
                    <div className="text-sm text-gray-600">{stock.shortname}</div>
                  </div>
                  <Button
                    onClick={() => addStock(stock)}
                    size="sm"
                    variant="outline"
                    disabled={selectedStocks.some(s => s.symbol === stock.symbol) || selectedStocks.length >= maxStocks}
                  >
                    {selectedStocks.some(s => s.symbol === stock.symbol) ? 'Added' : 'Add'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected Assets Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-medium">
              Selected Assets ({selectedStocks.length}/{maxStocks})
            </h4>
            <div className="text-sm text-muted-foreground">
              Minimum {minStocks} required
            </div>
          </div>

          {/* Portfolio Overview */}
          <div className={`border rounded-lg p-3 ${totalAllocation > 100 ? 'bg-red-50 border-red-200' : isValid ? 'bg-green-50 border-green-200' : 'bg-muted/30'}`}>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-xl font-bold text-primary">{selectedStocks.length}</div>
                <div className="text-xs text-muted-foreground">Stocks</div>
              </div>
              <div>
                <div className={`text-xl font-bold ${totalAllocation > 100 ? 'text-red-600' : isValid ? 'text-green-600' : 'text-amber-600'}`}>
                  {totalAllocation.toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">Total Allocation</div>
              </div>
              <div>
                <div className={`text-xl font-bold ${isValid ? 'text-green-600' : 'text-red-600'}`}>
                  {isValid ? '✓' : '✗'}
                </div>
                <div className="text-xs text-muted-foreground">Status</div>
              </div>
            </div>
          </div>

          {/* Validation Messages - only show after user has interacted */}
          {showValidation && (searchTerm.length > 0 || selectedStocks.length > 0) && (
            <div className="space-y-2">
              {!isValidStockCount && selectedStocks.length > 0 && (
                <Alert variant="destructive" className="py-3 border-l-4">
                  <AlertTriangle className="h-5 w-5" />
                  <AlertDescription className="text-sm">
                    <p className="font-semibold mb-1">Stock Count Requirement</p>
                    {selectedStocks.length < minStocks
                      ? `You need at least ${minStocks} stocks. Currently have ${selectedStocks.length}. Please add ${minStocks - selectedStocks.length} more stock${minStocks - selectedStocks.length > 1 ? 's' : ''}.`
                      : `Maximum ${maxStocks} stocks allowed. Currently have ${selectedStocks.length}. Please remove ${selectedStocks.length - maxStocks} stock${selectedStocks.length - maxStocks > 1 ? 's' : ''}.`
                    }
                  </AlertDescription>
                </Alert>
              )}

              {isValidStockCount && !isValidAllocation && (
                <Alert className="py-3 border-l-4 bg-amber-50 border-amber-400">
                  <Info className="h-5 w-5 text-amber-600" />
                  <AlertDescription className="text-sm text-amber-800">
                    <p className="font-semibold mb-1">Allocation Adjustment Needed</p>
                    Total allocation is {totalAllocation.toFixed(1)}%.
                    {totalAllocation > 100
                      ? ` Please reduce by ${(totalAllocation - 100).toFixed(1)}% to reach 100%.`
                      : ` Please add ${(100 - totalAllocation).toFixed(1)}% to reach 100%.`
                    }
                  </AlertDescription>
                </Alert>
              )}

              {isValid && (
                <Alert className="py-3 border-l-4 bg-green-50 border-green-400">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <AlertDescription className="text-sm text-green-800">
                    <p className="font-semibold mb-1">Portfolio Ready</p>
                    Perfect! You have {selectedStocks.length} stocks with {totalAllocation.toFixed(1)}% allocation. Your portfolio meets all requirements.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>

        {/* Allocation Editor Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <h5 className="text-sm font-medium">Allocation Editor</h5>
            <p className="text-xs text-muted-foreground mt-0.5">
              Manually adjust stock allocations or use equal allocation
            </p>
          </div>
          <Switch
            checked={showWeightEditor}
            onCheckedChange={setShowWeightEditor}
          />
        </div>

        {/* Allocation Editor */}
        {showWeightEditor && (
          <div className="space-y-3">
            {selectedStocks.map((stock) => (
              <div key={stock.symbol} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="font-medium">{stock.symbol}</div>
                  <div className="text-sm text-muted-foreground">{stock.name || stock.symbol}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={stock.allocation || ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value === '') {
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
                      if (value === '' || isNaN(parseFloat(value))) {
                        updateAllocation(stock.symbol, 0);
                      }
                    }}
                    className={`w-20 text-center ${stock.allocation > 100 ? 'border-red-500 bg-red-50' : ''}`}
                    min="0"
                    max="100"
                    step="0.1"
                    placeholder="0"
                  />
                  <span className="text-sm text-muted-foreground">%</span>
                </div>
                <Button
                  onClick={() => removeStock(stock.symbol)}
                  size="sm"
                  variant="destructive"
                >
                  Remove
                </Button>
              </div>
            ))}
            
            {selectedStocks.length > 0 && (
              <div className="flex justify-end">
                <Button
                  onClick={applyEqualAllocation}
                  variant="outline"
                  size="sm"
                >
                  Equal Allocation
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Performance Metrics Display */}
        {portfolioMetrics && (
          <div className="bg-muted/30 rounded-lg p-3 border border-border/50">
            <h5 className="text-xs font-medium mb-2">Performance Metrics</h5>
            {isLoadingMetrics ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Calculating metrics...
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Expected Return:</span>
                  <span className="ml-2 font-medium">{(portfolioMetrics.expectedReturn * 100).toFixed(2)}%</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Risk:</span>
                  <span className="ml-2 font-medium">{(portfolioMetrics.risk * 100).toFixed(2)}%</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Diversification:</span>
                  <span className="ml-2 font-medium">{portfolioMetrics.diversificationScore.toFixed(0)}%</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Sharpe Ratio:</span>
                  <span className="ml-2 font-medium">{portfolioMetrics.sharpeRatio.toFixed(2)}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Done button for finalize workflow */}
        <div className="flex justify-end pt-2">
          <Button
            type="button"
            onClick={handleDone}
            disabled={!isValidStockCount || isLoadingMetrics || selectedStocks.length === 0}
          >
            Done
          </Button>
        </div>

        {/* Portfolio Validation Summary */}
        {showValidation && (
          <div className="bg-muted/30 rounded-lg p-3 border border-border/50">
            <h5 className="text-xs font-medium mb-2">Portfolio Validation</h5>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  {minStocks} to {maxStocks} stocks
                </span>
                <span className={isValidStockCount ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                  {isValidStockCount ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Total allocation = 100%</span>
                <span className={isValidAllocation ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                  {isValidAllocation ? '✓' : '✗'}
                </span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
