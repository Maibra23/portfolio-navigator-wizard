import { useState, useEffect, useCallback, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  Loader2,
  TrendingUp,
  Building2,
  Plus,
  Check,
  X,
} from "lucide-react";

export interface SearchResult {
  ticker: string;
  company_name: string;
  sector: string;
  industry?: string;
  relevance_score?: number;
}

interface Sector {
  id: string;
  name: string;
  icon: string;
}

interface EnhancedStockSearchProps {
  onSelectStock: (stock: SearchResult) => void;
  selectedTickers: string[];
  maxStocks?: number;
  riskProfile?: string;
}

export function EnhancedStockSearch({
  onSelectStock,
  selectedTickers,
  maxStocks = 10,
  riskProfile,
}: EnhancedStockSearchProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [popularTickers, setPopularTickers] = useState<SearchResult[]>([]);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [sectorTickers, setSectorTickers] = useState<SearchResult[]>([]);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [isLoadingPopular, setIsLoadingPopular] = useState(false);
  const [isLoadingSectors, setIsLoadingSectors] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch popular tickers on mount
  useEffect(() => {
    const fetchPopular = async () => {
      setIsLoadingPopular(true);
      try {
        const response = await fetch("/api/v1/portfolio/popular-tickers?limit=12");
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            setPopularTickers(data.tickers);
          }
        }
      } catch (e) {
        console.error("Failed to fetch popular tickers:", e);
      } finally {
        setIsLoadingPopular(false);
      }
    };
    fetchPopular();
  }, []);

  // Fetch sectors on mount
  useEffect(() => {
    const fetchSectors = async () => {
      setIsLoadingSectors(true);
      try {
        const response = await fetch("/api/v1/portfolio/sectors");
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            setSectors(data.sectors);
          }
        }
      } catch (e) {
        console.error("Failed to fetch sectors:", e);
      } finally {
        setIsLoadingSectors(false);
      }
    };
    fetchSectors();
  }, []);

  // Fetch suggestions as user types (debounced)
  useEffect(() => {
    if (!searchTerm.trim() || searchTerm.length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setIsLoadingSuggestions(true);
      try {
        const response = await fetch(
          `/api/v1/portfolio/search-suggestions?q=${encodeURIComponent(searchTerm)}&limit=6`
        );
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.suggestions) {
            setSuggestions(
              data.suggestions.map((s: any) => ({
                ticker: s.ticker,
                company_name: s.name,
                sector: s.sector,
              }))
            );
            setShowSuggestions(true);
          }
        }
      } catch (e) {
        console.error("Failed to fetch suggestions:", e);
      } finally {
        setIsLoadingSuggestions(false);
      }
    }, 150); // Fast debounce for suggestions

    return () => clearTimeout(timeoutId);
  }, [searchTerm]);

  // Full search
  const performSearch = useCallback(async () => {
    if (!searchTerm.trim()) return;

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);
    setShowSuggestions(false);

    try {
      const url = riskProfile
        ? `/api/v1/portfolio/search-tickers?q=${encodeURIComponent(searchTerm)}&limit=15&risk_profile=${riskProfile}`
        : `/api/v1/portfolio/search-tickers?q=${encodeURIComponent(searchTerm)}&limit=15`;

      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error("Search failed");

      const data = await response.json();
      if (data.success && data.results) {
        setSearchResults(
          data.results.map((r: any) => ({
            ticker: r.ticker,
            company_name: r.company_name,
            sector: r.sector,
            industry: r.industry,
            relevance_score: r.relevance_score,
          }))
        );
      } else {
        setSearchResults([]);
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError("Search failed. Please try again.");
        setSearchResults([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, riskProfile]);

  // Search on Enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      performSearch();
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  // Fetch tickers for selected sector
  const handleSectorClick = async (sector: Sector) => {
    if (selectedSector === sector.id) {
      setSelectedSector(null);
      setSectorTickers([]);
      return;
    }

    setSelectedSector(sector.id);
    setIsLoading(true);

    try {
      const response = await fetch(
        `/api/v1/portfolio/sectors/${encodeURIComponent(sector.id)}/tickers?limit=20`
      );
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSectorTickers(data.tickers);
        }
      }
    } catch (e) {
      console.error("Failed to fetch sector tickers:", e);
    } finally {
      setIsLoading(false);
    }
  };

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isSelected = (ticker: string) => selectedTickers.includes(ticker);
  const atMax = selectedTickers.length >= maxStocks;

  const StockCard = ({ stock }: { stock: SearchResult }) => {
    const selected = isSelected(stock.ticker);
    return (
      <div
        className={`flex items-center justify-between p-2.5 rounded-lg border transition-all ${
          selected
            ? "bg-primary/10 border-primary/30"
            : "bg-card border-border hover:border-primary/50 hover:bg-accent/30"
        }`}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{stock.ticker}</span>
            {stock.sector && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                {stock.sector}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {stock.company_name}
          </p>
        </div>
        <Button
          size="sm"
          variant={selected ? "secondary" : "outline"}
          className="ml-2 h-7 px-2"
          disabled={selected || atMax}
          onClick={() => onSelectStock(stock)}
        >
          {selected ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div ref={searchRef} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by ticker or company name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              className="pl-9"
            />
            {isLoadingSuggestions && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
          <Button onClick={performSearch} disabled={!searchTerm.trim() || isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </Button>
        </div>

        {/* Autocomplete Suggestions Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
            {suggestions.map((s) => (
              <button
                key={s.ticker}
                className="w-full px-3 py-2 text-left hover:bg-accent flex items-center justify-between"
                onClick={() => {
                  setSearchTerm(s.ticker);
                  setShowSuggestions(false);
                  performSearch();
                }}
              >
                <div>
                  <span className="font-medium">{s.ticker}</span>
                  <span className="text-muted-foreground ml-2 text-sm">
                    {s.company_name}
                  </span>
                </div>
                {s.sector && (
                  <Badge variant="outline" className="text-[10px]">
                    {s.sector}
                  </Badge>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="text-sm text-destructive flex items-center gap-2">
          <X className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-2">
            <Search className="h-4 w-4" />
            Search Results ({searchResults.length})
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
            {searchResults.map((stock) => (
              <StockCard key={stock.ticker} stock={stock} />
            ))}
          </div>
        </div>
      )}

      {/* Popular Tickers */}
      {!searchResults.length && !selectedSector && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Popular Stocks
          </h4>
          {isLoadingPopular ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {popularTickers.slice(0, 9).map((stock) => (
                <StockCard key={stock.ticker} stock={stock} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Browse by Sector */}
      {!searchResults.length && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Browse by Sector
          </h4>
          {isLoadingSectors ? (
            <div className="flex flex-wrap gap-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-8 w-24 rounded-full" />
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {sectors.map((sector) => (
                <Button
                  key={sector.id}
                  variant={selectedSector === sector.id ? "default" : "outline"}
                  size="sm"
                  className="text-xs"
                  onClick={() => handleSectorClick(sector)}
                >
                  <span className="mr-1">{sector.icon}</span>
                  {sector.name}
                </Button>
              ))}
            </div>
          )}

          {/* Sector Tickers */}
          {selectedSector && sectorTickers.length > 0 && (
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-60 overflow-y-auto">
              {sectorTickers.map((stock) => (
                <StockCard key={stock.ticker} stock={stock} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
