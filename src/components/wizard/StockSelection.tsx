import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, ArrowLeft, TrendingUp, Search, Plus, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface StockSelectionProps {
  onNext: () => void;
  onPrev: () => void;
  onStocksUpdate: (stocks: string[]) => void;
  selectedStocks: string[];
}

const CURATED_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', sector: 'Technology' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', sector: 'Technology' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', sector: 'Consumer' },
  { symbol: 'TSLA', name: 'Tesla Inc.', sector: 'Automotive' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', sector: 'Technology' },
  { symbol: 'JPM', name: 'JPMorgan Chase & Co.', sector: 'Financial' },
  { symbol: 'V', name: 'Visa Inc.', sector: 'Financial' },
  { symbol: 'JNJ', name: 'Johnson & Johnson', sector: 'Healthcare' },
  { symbol: 'WMT', name: 'Walmart Inc.', sector: 'Consumer' },
  { symbol: 'PG', name: 'Procter & Gamble Co.', sector: 'Consumer' },
  { symbol: 'UNH', name: 'UnitedHealth Group Inc.', sector: 'Healthcare' },
  { symbol: 'HD', name: 'The Home Depot Inc.', sector: 'Consumer' },
  { symbol: 'MA', name: 'Mastercard Incorporated', sector: 'Financial' },
  { symbol: 'DIS', name: 'The Walt Disney Company', sector: 'Entertainment' },
];

export const StockSelection = ({ onNext, onPrev, onStocksUpdate, selectedStocks }: StockSelectionProps) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [customStock, setCustomStock] = useState('');

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

  const filteredStocks = CURATED_STOCKS.filter(stock =>
    stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    stock.sector.toLowerCase().includes(searchTerm.toLowerCase())
  );

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

          <Tabs defaultValue="curated" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="curated">Curated Selection</TabsTrigger>
              <TabsTrigger value="search">Custom Search</TabsTrigger>
            </TabsList>
            
            <TabsContent value="curated" className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search stocks..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                {filteredStocks.map(stock => {
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
                              {stock.name}
                            </p>
                            <Badge variant="outline" className="mt-1 text-xs">
                              {stock.sector}
                            </Badge>
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
              </div>
            </TabsContent>
            
            <TabsContent value="search" className="space-y-4">
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
              
              <div className="bg-muted/50 rounded-lg p-4">
                <h4 className="font-medium mb-2">Portfolio Guidelines</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Select at least 3-5 stocks for diversification</li>
                  <li>• Consider different sectors and industries</li>
                  <li>• Mix of growth and value stocks can balance risk</li>
                  <li>• Research companies before investing</li>
                </ul>
              </div>
            </TabsContent>
          </Tabs>

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