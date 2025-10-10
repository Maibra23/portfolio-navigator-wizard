import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, ArrowLeft, TrendingUp, Search, Plus, X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface StockSelectionProps {
  onNext: () => void;
  onPrev: () => void;
  onStocksUpdate: (stocks: string[]) => void;
  selectedStocks: string[];
}

interface StockResult {
  symbol: string;
  shortname: string;
  longname?: string;
  typeDisp?: string;
  exchange?: string;
}

export const StockSelection = ({ onNext, onPrev, onStocksUpdate, selectedStocks }: StockSelectionProps) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [customStock, setCustomStock] = useState('');
  const [searchResults, setSearchResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleStock = (symbol: string) => {
    const newStocks = selectedStocks.includes(symbol)
      ? selectedStocks.filter(s => s !== symbol)
      : [...selectedStocks, symbol];
    onStocksUpdate(newStocks);
  };

  const addCustomStock = () => {
    if (customStock.trim() && !selectedStocks.includes(customStock.toUpperCase())) {
      onStocksUpdate([...selectedStocks, customStock.toUpperCase()]);
      setCustomStock('');
    }
  };

  const removeStock = (symbol: string) => {
    onStocksUpdate(selectedStocks.filter(s => s !== symbol));
  };

  const searchStocks = useCallback(async (query: string) => {
    if (!query.trim() || query.length < 1) {
      setSearchResults([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Using Yahoo Finance autocomplete API via RapidAPI proxy
      const response = await fetch(`https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(query)}&lang=en-US&region=US&quotesCount=20&newsCount=0&listsCount=0&enableFuzzyQuery=false`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stock data');
      }

      const data = await response.json();
      const stocks: unknown[] = data.quotes || [];

      type YahooQuote = {
        quoteType?: string;
        symbol?: string;
        shortname?: string;
        longname?: string;
        typeDisp?: string;
        exchange?: string;
      };

      const typedResults: StockResult[] = (stocks as YahooQuote[])
        .filter((stock) => stock.quoteType === 'EQUITY' && !!stock.symbol && !!stock.shortname)
        .map((stock) => ({
          symbol: stock.symbol as string,
          shortname: stock.shortname as string,
          longname: stock.longname,
          typeDisp: stock.typeDisp,
          exchange: stock.exchange,
        }));

      setSearchResults(typedResults);
    } catch (err) {
      setError('Unable to fetch stock data. Please try entering symbols manually.');
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchStocks(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, searchStocks]);

  const handleNext = () => {
    if (selectedStocks.length >= 3) {
      onNext();
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <Card className="shadow-card">
        <CardHeader className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-primary flex items-center justify-center">
            <TrendingUp className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Stock Selection</CardTitle>
          <p className="text-muted-foreground">
            Choose stocks for your portfolio. Select at least 3 for proper diversification.
          </p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Selected Stocks */}
          {selectedStocks.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium">Selected Stocks ({selectedStocks.length})</h3>
              <div className="flex flex-wrap gap-2">
                {selectedStocks.map(symbol => (
                  <Badge 
                    key={symbol} 
                    variant="default" 
                    className="px-3 py-1 text-sm cursor-pointer hover:bg-destructive"
                    onClick={() => removeStock(symbol)}
                  >
                    {symbol}
                    <X className="ml-1 h-3 w-3" />
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search stocks by name or symbol..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg">
                {error}
              </div>
            )}

            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Searching stocks...</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
              {!isLoading && searchResults.map(stock => {
                const isSelected = selectedStocks.includes(stock.symbol);
                return (
                  <Card 
                    key={stock.symbol}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                      isSelected ? 'ring-2 ring-primary bg-primary/5' : ''
                    }`}
                    onClick={() => toggleStock(stock.symbol)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium">{stock.symbol}</h4>
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {stock.shortname}
                          </p>
                          {stock.typeDisp && (
                            <Badge variant="outline" className="mt-1 text-xs">
                              {stock.typeDisp}
                            </Badge>
                          )}
                        </div>
                        {isSelected && (
                          <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                            <span className="text-xs text-white">✓</span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}

              {!isLoading && searchTerm && searchResults.length === 0 && (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  No stocks found. Try a different search term or add manually below.
                </div>
              )}

              {!searchTerm && !isLoading && (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  Start typing to search for stocks...
                </div>
              )}
            </div>
          </div>

          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="font-medium mb-2">Add Custom Stock</h4>
            <p className="text-sm text-muted-foreground mb-3">
              Enter a stock symbol (e.g., AAPL, MSFT) to add it to your portfolio.
            </p>
            <div className="flex gap-2">
              <Input
                placeholder="Enter stock symbol..."
                value={customStock}
                onChange={(e) => setCustomStock(e.target.value.toUpperCase())}
                onKeyPress={(e) => e.key === 'Enter' && addCustomStock()}
              />
              <Button onClick={addCustomStock} disabled={!customStock.trim()}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <Button variant="outline" onClick={onPrev} className="flex-1">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={handleNext} 
              className="flex-1"
              disabled={selectedStocks.length < 3}
            >
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          
          {selectedStocks.length < 3 && (
            <p className="text-sm text-muted-foreground text-center">
              Select at least 3 stocks to continue
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};