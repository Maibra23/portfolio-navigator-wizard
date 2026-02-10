import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

export interface StockSearchResult {
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

interface StockSearchBarProps {
  searchTerm: string;
  onSearchTermChange: (value: string) => void;
  searchResults: StockSearchResult[];
  isLoading: boolean;
  onSearch: () => void;
  onAddStock: (stock: StockSearchResult) => void;
  selectedSymbols: string[];
  maxStocks?: number;
  placeholder?: string;
}

export function StockSearchBar({
  searchTerm,
  onSearchTermChange,
  searchResults,
  isLoading,
  onSearch,
  onAddStock,
  selectedSymbols,
  maxStocks = 4,
  placeholder = 'Search for stocks (e.g., AAPL, MSFT)',
}: StockSearchBarProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-foreground mb-1.5">
        Add More Stocks
      </label>
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => onSearchTermChange(e.target.value)}
          className="flex-1"
        />
        <Button
          onClick={onSearch}
          disabled={!searchTerm.trim() || isLoading}
          size="sm"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
        </Button>
      </div>

      {searchTerm.trim() && searchResults.length > 0 && (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-2 mt-2">
          <h4 className="text-sm font-medium">Search Results:</h4>
          {searchResults.map((stock) => {
            const isAdded = selectedSymbols.includes(stock.symbol);
            const atMax = selectedSymbols.length >= maxStocks;
            return (
              <div
                key={stock.symbol}
                className="flex items-center justify-between p-3 border border-border rounded-lg bg-card hover:bg-accent/50"
              >
                <div>
                  <div className="font-medium text-foreground">{stock.symbol}</div>
                  <div className="text-sm text-muted-foreground">{stock.shortname}</div>
                </div>
                <Button
                  onClick={() => onAddStock(stock)}
                  size="sm"
                  variant="outline"
                  disabled={isAdded || atMax}
                >
                  {isAdded ? 'Added' : 'Add'}
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
