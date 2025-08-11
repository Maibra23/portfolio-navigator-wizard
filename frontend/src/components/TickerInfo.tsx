import React, { useState, useEffect } from 'react';
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

  const fetchTickerInfo = async () => {
    if (!ticker.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(API_ENDPOINTS.TICKER_INFO(ticker.trim().toUpperCase()));
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch ticker information');
      }
      
      const data = await response.json();
      setTickerData(data);
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
            <Input
              type="text"
              placeholder="Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="flex-1"
              disabled={loading}
            />
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
