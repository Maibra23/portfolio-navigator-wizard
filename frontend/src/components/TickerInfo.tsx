import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Search, TrendingUp, TrendingDown, Info, Building2, Globe, Database } from 'lucide-react';
import { API_ENDPOINTS } from '@/config/api';

interface TickerInfoData {
  ticker: string;
  company_name: string;
  sector: string;
  industry: string;
  country: string;
  exchange: string;
  current_price: number;
  price_change: number;
  price_change_pct: number;
  last_updated: string;
  data_points: number;
  cached: boolean;
  prices: number[];
  dates: string[];
  annualized_return?: number;
  risk?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  var_95?: number;
  skewness?: number;
  kurtosis?: number;
}

export const TickerInfo: React.FC = () => {
  const [ticker, setTicker] = useState<string>('');
  const [tickerData, setTickerData] = useState<TickerInfoData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<{ ticker: string; company_name: string; sector?: string }[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState<boolean>(false);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const searchCache = useRef<Record<string, { ticker: string; company_name: string; sector?: string }[]>>({});
  const MIN_QUERY_LEN = 2;
  const SEARCH_LIMIT = 8;
  const SEARCH_DEBOUNCE_MS = 150;

  // Common company-name → ticker aliases to handle rebrands or colloquial names
  const COMPANY_TO_TICKER_ALIASES: Record<string, string[]> = {
    'GOOGLE': ['GOOGL', 'GOOG'],
    'ALPHABET': ['GOOGL', 'GOOG'],
    'FACEBOOK': ['META'],
    'SQUARE': ['SQ'],
    'GOOGLE INC': ['GOOGL', 'GOOG'],
    'META PLATFORMS': ['META'],
    'APPLE': ['AAPL'],
    'MICROSOFT': ['MSFT'],
    'AMAZON': ['AMZN'],
    'TESLA': ['TSLA'],
    'NVIDIA': ['NVDA'],
  };

  const fetchTickerBySymbol = async (symbol: string): Promise<boolean> => {
    try {
      const response = await fetch(API_ENDPOINTS.TICKER_INFO(symbol));
      if (!response.ok) return false;
      const data = await response.json();
      setTickerData(data);
      setTicker(symbol);
      return true;
    } catch {
      return false;
    }
  };

  const fetchTickerInfo = async () => {
    const query = ticker.trim();
    if (!query) return;
    setLoading(true);
    setError(null);

    // Helper: resolve free-text/company name to a valid ticker via enhanced search
    const resolveTicker = async (q: string): Promise<string | null> => {
      try {
        const resp = await fetch(API_ENDPOINTS.TICKER_SEARCH(q, 1));
        if (!resp.ok) return null;
        const data = await resp.json();
        if (Array.isArray(data) && data.length > 0 && data[0].ticker) {
          return String(data[0].ticker);
        }
        return null;
      } catch {
        return null;
      }
    };

    try {
      // First try direct fetch assuming user typed a valid symbol
      const directSymbol = query.toUpperCase();
      // 1) Direct attempt
      let ok = await fetchTickerBySymbol(directSymbol);

      // 2) If failed, try alias map from company/common name
      if (!ok) {
        const aliasCandidates = COMPANY_TO_TICKER_ALIASES[directSymbol] || COMPANY_TO_TICKER_ALIASES[query.toUpperCase()] || [];
        for (const candidate of aliasCandidates) {
          ok = await fetchTickerBySymbol(candidate);
          if (ok) break;
        }
      }

      // 3) If still failed, resolve via enhanced search (same as Customize flow)
      if (!ok) {
        const resolved = await resolveTicker(query) || await resolveTicker(directSymbol);
        if (resolved) {
          ok = await fetchTickerBySymbol(resolved);
        }
      }

      if (!ok) {
        throw new Error('Ticker not found. Please select from suggestions.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setTickerData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTickerInfo();
  };

  // Lightweight enhanced search (reuse backend endpoint used in Customize Your Portfolio)
  useEffect(() => {
    const q = ticker.trim();
    if (!q) {
      setSearchResults([]);
      setIsSuggestionsOpen(false);
      setHighlightedIndex(-1);
      return;
    }
    if (q.length < MIN_QUERY_LEN) {
      setSearchResults([]);
      setIsSuggestionsOpen(false);
      setHighlightedIndex(-1);
      return;
    }
    const controller = new AbortController();
    const doSearch = async () => {
      try {
        setIsSearching(true);
        const key = q.toLowerCase();
        if (searchCache.current[key]) {
          const cached = searchCache.current[key];
          setSearchResults(cached);
          setIsSuggestionsOpen(cached.length > 0);
          setHighlightedIndex(cached.length > 0 ? 0 : -1);
          setIsSearching(false);
          return;
        }
        const resp = await fetch(API_ENDPOINTS.TICKER_SEARCH(q, SEARCH_LIMIT), { signal: controller.signal });
        if (!resp.ok) {
          setSearchResults([]);
          setIsSuggestionsOpen(false);
          return;
        }
        const data = await resp.json();
        // Expect list of { ticker, company_name, ... }
        const results = Array.isArray(data) ? data : [];
        setSearchResults(results);
        setIsSuggestionsOpen(results.length > 0);
        setHighlightedIndex(results.length > 0 ? 0 : -1);
        searchCache.current[key] = results;
      } catch (_e) {
        // ignore abort/errors for suggestions
      } finally {
        setIsSearching(false);
      }
    };
    const t = setTimeout(doSearch, SEARCH_DEBOUNCE_MS);
    return () => {
      controller.abort();
      clearTimeout(t);
    };
  }, [ticker]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatNumber = (value: number) => {
    return value.toFixed(4);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Ticker Information Lookup
          </CardTitle>
          <p className="text-muted-foreground">
            Get comprehensive information about any stock ticker including prices, metrics, and company details
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Enter ticker or company (e.g., AAPL or Apple)"
                value={ticker}
                onChange={(e) => {
                  setTicker(e.target.value);
                  setIsSuggestionsOpen(true);
                }}
                className="w-full"
                disabled={loading}
              />
              {/* Keyboard navigation for suggestions */}
              <div className="sr-only" aria-live="polite">
                {isSuggestionsOpen && searchResults.length > 0 ? `${searchResults.length} suggestions available` : ''}
              </div>
              {isSuggestionsOpen && ticker.trim() && searchResults.length > 0 && (
                <div className="mt-2 max-h-64 overflow-y-auto border rounded-md bg-white shadow-md" role="listbox">
                  {searchResults.map((r, idx) => (
                    <div
                      key={r.ticker}
                      role="option"
                      aria-selected={highlightedIndex === idx}
                      className={`flex items-center justify-between p-2 cursor-pointer ${highlightedIndex === idx ? 'bg-gray-100' : 'hover:bg-gray-50'}`}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                      onMouseLeave={() => setHighlightedIndex(-1)}
                      onClick={() => {
                        setTicker(r.ticker);
                        setTickerData(null);
                        setIsSuggestionsOpen(false);
                      }}
                    >
                      <div>
                        <div className="font-medium">{r.ticker}</div>
                        <div className="text-xs text-muted-foreground">{r.company_name}</div>
                      </div>
                      {r.sector && <Badge variant="outline">{r.sector}</Badge>}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <Button type="submit" disabled={loading || !ticker.trim()}>
              {loading ? 'Loading...' : 'Search'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Progress value={undefined} className="flex-1" />
              <span className="text-sm text-muted-foreground">Fetching ticker data...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {tickerData && (
        <div className="space-y-6">
          {/* Company Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Company Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h3 className="font-semibold text-lg">{tickerData.company_name}</h3>
                  <p className="text-2xl font-bold text-primary">{tickerData.ticker}</p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold">{formatCurrency(tickerData.current_price)}</p>
                  <div className="flex items-center justify-end gap-2">
                    {tickerData.price_change >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-green-600" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-600" />
                    )}
                    <span className={`font-semibold ${tickerData.price_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPercentage(tickerData.price_change_pct)}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Sector</p>
                  <p className="font-medium">{tickerData.sector}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Industry</p>
                  <p className="font-medium">{tickerData.industry}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Country</p>
                  <p className="font-medium">{tickerData.country}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Exchange</p>
                  <p className="font-medium">{tickerData.exchange}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Price Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Price Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Current Price</p>
                  <p className="font-semibold">{formatCurrency(tickerData.current_price)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Price Change</p>
                  <p className={`font-semibold ${tickerData.price_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(tickerData.price_change)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Data Points</p>
                  <p className="font-semibold">{tickerData.data_points}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Updated</p>
                  <p className="font-semibold">{tickerData.last_updated}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Badge variant={tickerData.cached ? "default" : "secondary"}>
                  <Database className="h-3 w-3 mr-1" />
                  {tickerData.cached ? 'Cached Data' : 'Live Data'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Risk Metrics */}
          {tickerData.risk && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Risk Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {tickerData.annualized_return !== undefined && (
                    <div>
                      <p className="text-sm text-muted-foreground">Annualized Return</p>
                      <p className="font-semibold">{formatPercentage(tickerData.annualized_return * 100)}</p>
                    </div>
                  )}
                  {tickerData.risk !== undefined && (
                    <div>
                      <p className="text-sm text-muted-foreground">Risk (Volatility)</p>
                      <p className="font-semibold">{formatPercentage(tickerData.risk * 100)}</p>
                    </div>
                  )}
                  {tickerData.sharpe_ratio !== undefined && (
                    <div>
                      <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                      <p className="font-semibold">{formatNumber(tickerData.sharpe_ratio)}</p>
                    </div>
                  )}
                  {tickerData.max_drawdown !== undefined && (
                    <div>
                      <p className="text-sm text-muted-foreground">Max Drawdown</p>
                      <p className="font-semibold">{formatPercentage(tickerData.max_drawdown * 100)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Price Chart Data */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Price Data (Last 30 points)</CardTitle>
              <p className="text-muted-foreground">
                Historical price data for analysis and visualization
              </p>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">
                <p>Available price points: {tickerData.prices.length}</p>
                <p>Date range: {tickerData.dates[0]} to {tickerData.dates[tickerData.dates.length - 1]}</p>
                <p className="mt-2">
                  <strong>Note:</strong> This data can be used to create charts, calculate additional metrics, 
                  or perform portfolio analysis.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
