import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  ArrowRight, 
  TrendingUp, 
  Shield, 
  Search, 
  Plus, 
  X, 
  Info,
  BarChart3,
  Target,
  Zap,
  BookOpen,
  Star,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  Calculator,
  PieChart,
  LineChart,
  Settings,
  Database
} from 'lucide-react';
import { TwoAssetChart } from './TwoAssetChart';

interface StockSelectionProps {
  onNext: () => void;
  onPrev: () => void;
  onStocksUpdate: (stocks: PortfolioAllocation[]) => void;
  selectedStocks: PortfolioAllocation[];
  riskProfile: string;
  capital: number;
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

interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
}

interface PortfolioRecommendation {
  name: string;
  description: string;
  allocations: PortfolioAllocation[];
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
}

interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

interface SectorRecommendation {
  sector: string;
  reason: string;
  suggestions: Array<{
    symbol: string;
    name: string;
    type: string;
    description: string;
  }>;
}

interface AssetStats {
  ticker: string;
  annualized_return: number;
  annualized_volatility: number;
  price_history: number[];
  last_price: number;
  start_date: string;
  end_date: string;
  data_source?: string;
  company_name?: string;
  sector?: string;
  industry?: string;
}

interface TwoAssetPortfolio {
  weights: [number, number];
  return: number;
  risk: number;
  sharpe_ratio: number;
}

interface TwoAssetAnalysis {
  ticker1: string;
  ticker2: string;
  asset1_stats: AssetStats;
  asset2_stats: AssetStats;
  correlation: number;
  portfolios: TwoAssetPortfolio[];
}

export const StockSelection = ({ 
  onNext, 
  onPrev, 
  onStocksUpdate, 
  selectedStocks, 
  riskProfile, 
  capital 
}: StockSelectionProps) => {
  const [activeTab, setActiveTab] = useState<'mini-lesson' | 'recommendations' | 'full-customization'>('mini-lesson');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [sectorRecommendations, setSectorRecommendations] = useState<SectorRecommendation[]>([]);
  const [showDiversification, setShowDiversification] = useState(false);
  
  // Mini-lesson state
  const [twoAssetAnalysis, setTwoAssetAnalysis] = useState<TwoAssetAnalysis | null>(null);
  const [nvdaWeight, setNvdaWeight] = useState(50);
  const [customPortfolio, setCustomPortfolio] = useState<TwoAssetPortfolio | null>(null);
  const [isLoadingMiniLesson, setIsLoadingMiniLesson] = useState(false);
  const [availableAssetPairs, setAvailableAssetPairs] = useState<Array<{
    pair_id: string;
    ticker1: string;
    ticker2: string;
    name1: string;
    name2: string;
    description: string;
    educational_focus: string;
  }>>([]);
  const [selectedPairId, setSelectedPairId] = useState('nvda_amzn');
  const [currentPair, setCurrentPair] = useState({ ticker1: 'NVDA', ticker2: 'AMZN' });
  
  // Full customization state
  const [fullCustomTickers, setFullCustomTickers] = useState<string[]>([]);
  const [fullCustomWeights, setFullCustomWeights] = useState<number[]>([]);
  const [fullCustomAnalysis, setFullCustomAnalysis] = useState<{
    efficientFrontier: Array<{return: number, risk: number, weights: number[]}>;
    optimalPortfolio: {return: number, risk: number, weights: number[]};
  } | null>(null);
  const [isLoadingFullCustom, setIsLoadingFullCustom] = useState(false);

  // Track if user has selected a portfolio recommendation
  const [hasSelectedPortfolio, setHasSelectedPortfolio] = useState(false);
  const [dynamicRecommendations, setDynamicRecommendations] = useState<PortfolioRecommendation[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);

  // Generate recommendations based on risk profile
  const generateRecommendations = (): PortfolioRecommendation[] => {
    // Define portfolio templates for each risk category (max 4 stocks each)
    const portfolioTemplates = {
      'very-conservative': {
        name: 'Very Conservative Portfolio',
        description: 'Maximum capital preservation with minimal risk exposure',
        allocations: [
          { symbol: 'JNJ', allocation: 40, name: 'Johnson & Johnson', assetType: 'stock' as const },
          { symbol: 'PG', allocation: 30, name: 'Procter & Gamble', assetType: 'stock' as const },
          { symbol: 'KO', allocation: 20, name: 'Coca-Cola', assetType: 'stock' as const },
          { symbol: 'VZ', allocation: 10, name: 'Verizon', assetType: 'stock' as const }
        ],
        expectedReturn: 0.06,
        risk: 0.08,
        diversificationScore: 90
      },
      'conservative': {
        name: 'Conservative Portfolio',
        description: 'Low-risk portfolio focused on stable, dividend-paying stocks',
        allocations: [
          { symbol: 'JNJ', allocation: 35, name: 'Johnson & Johnson', assetType: 'stock' as const },
          { symbol: 'PG', allocation: 30, name: 'Procter & Gamble', assetType: 'stock' as const },
          { symbol: 'KO', allocation: 25, name: 'Coca-Cola', assetType: 'stock' as const },
          { symbol: 'VZ', allocation: 10, name: 'Verizon', assetType: 'stock' as const }
        ],
        expectedReturn: 0.08,
        risk: 0.12,
        diversificationScore: 85
      },
      'moderate': {
        name: 'Balanced Portfolio',
        description: 'Moderate risk with a mix of growth and value stocks',
        allocations: [
          { symbol: 'AAPL', allocation: 30, name: 'Apple Inc.', assetType: 'stock' as const },
          { symbol: 'MSFT', allocation: 25, name: 'Microsoft', assetType: 'stock' as const },
          { symbol: 'GOOGL', allocation: 25, name: 'Alphabet Inc.', assetType: 'stock' as const },
          { symbol: 'AMZN', allocation: 20, name: 'Amazon.com', assetType: 'stock' as const }
        ],
        expectedReturn: 0.12,
        risk: 0.18,
        diversificationScore: 78
      },
      'aggressive': {
        name: 'Growth Portfolio',
        description: 'Higher risk portfolio targeting aggressive growth',
        allocations: [
          { symbol: 'NVDA', allocation: 35, name: 'NVIDIA', assetType: 'stock' as const },
          { symbol: 'TSLA', allocation: 30, name: 'Tesla Inc.', assetType: 'stock' as const },
          { symbol: 'AMD', allocation: 20, name: 'Advanced Micro Devices', assetType: 'stock' as const },
          { symbol: 'META', allocation: 15, name: 'Meta Platforms', assetType: 'stock' as const }
        ],
        expectedReturn: 0.18,
        risk: 0.28,
        diversificationScore: 65
      },
      'very-aggressive': {
        name: 'Very Aggressive Portfolio',
        description: 'Maximum growth potential with highest risk tolerance',
        allocations: [
          { symbol: 'NVDA', allocation: 40, name: 'NVIDIA', assetType: 'stock' as const },
          { symbol: 'TSLA', allocation: 35, name: 'Tesla Inc.', assetType: 'stock' as const },
          { symbol: 'AMD', allocation: 15, name: 'Advanced Micro Devices', assetType: 'stock' as const },
          { symbol: 'META', allocation: 10, name: 'Meta Platforms', assetType: 'stock' as const }
        ],
        expectedReturn: 0.25,
        risk: 0.35,
        diversificationScore: 55
      }
    };

    // Define the order of recommendations based on risk profile
    const recommendationOrder = {
      'very-conservative': ['very-conservative', 'conservative', 'moderate'],
      'conservative': ['conservative', 'moderate', 'very-conservative'],
      'moderate': ['moderate', 'aggressive', 'conservative'],
      'aggressive': ['aggressive', 'moderate', 'very-aggressive'],
      'very-aggressive': ['very-aggressive', 'aggressive', 'moderate']
    };

    const order = recommendationOrder[riskProfile as keyof typeof recommendationOrder] || ['moderate', 'conservative', 'aggressive'];

    // Generate recommendations in the correct order
    return order.map((profileType, index) => {
      const template = portfolioTemplates[profileType as keyof typeof portfolioTemplates];
      return {
        ...template,
        name: template.name + (index === 0 ? ' (Top Pick)' : ` (Option ${index + 1})`),
        expectedReturn: template.expectedReturn,
        risk: template.risk,
        diversificationScore: template.diversificationScore
      };
    });
  };

  const recommendations = generateRecommendations();

  // Load dynamic recommendations from backend
  useEffect(() => {
    const loadDynamicRecommendations = async () => {
      setIsLoadingRecommendations(true);
      try {
        console.log('Loading dynamic recommendations for risk profile:', riskProfile);
        const response = await fetch(`http://127.0.0.1:8000/api/portfolio/recommendations/${riskProfile}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Dynamic recommendations received:', data);
          
          // Transform backend data to match frontend interface
          const transformedRecommendations = data.map((item: {
            portfolio: Array<{symbol: string; allocation: number; name?: string; assetType?: string}>;
            expectedReturn: number;
            risk: number;
            diversificationScore: number;
            sharpeRatio: number;
          }, index: number) => ({
            name: `AI Portfolio Option ${index + 1}${index === 0 ? ' (Recommended)' : ''}`,
            description: `Optimized ${riskProfile} portfolio with real market data`,
            allocations: item.portfolio.map((allocation) => ({
              symbol: allocation.symbol,
              allocation: allocation.allocation,
              name: allocation.name || allocation.symbol,
              assetType: allocation.assetType || 'stock'
            })),
            expectedReturn: item.expectedReturn,
            risk: item.risk,
            diversificationScore: item.diversificationScore,
            sharpeRatio: item.sharpeRatio
          }));
          
          setDynamicRecommendations(transformedRecommendations);
        } else {
          console.error('Failed to load dynamic recommendations, using fallback');
          setDynamicRecommendations(recommendations); // Fallback to static
        }
      } catch (error) {
        console.error('Error loading dynamic recommendations:', error);
        setDynamicRecommendations(recommendations); // Fallback to static
      } finally {
        setIsLoadingRecommendations(false);
      }
    };

    loadDynamicRecommendations();
  }, [riskProfile, recommendations]);

  // Load available asset pairs for mini-lesson
  useEffect(() => {
    const loadAssetPairs = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/portfolio/mini-lesson/assets');
        if (response.ok) {
          const data = await response.json();
          setAvailableAssetPairs([...data.educational_pairs, { 
            pair_id: 'random', 
            ticker1: 'Random', 
            ticker2: 'Random',
            name1: 'Random Asset 1',
            name2: 'Random Asset 2',
            description: 'Random Asset Pair',
            educational_focus: 'Dynamic Selection'
          }]);
        }
      } catch (error) {
        console.error('Error loading asset pairs:', error);
      }
    };

    loadAssetPairs();
  }, []);

  // Load mini-lesson data when pair changes
  useEffect(() => {
    const loadMiniLesson = async () => {
      setIsLoadingMiniLesson(true);
      try {
        console.log('Loading mini-lesson data for:', currentPair);
        
        let apiUrl;
        if (selectedPairId === 'random') {
          // Get random pair first
          const randomResponse = await fetch('http://127.0.0.1:8000/api/portfolio/mini-lesson/random-pair');
          if (randomResponse.ok) {
            const randomPair = await randomResponse.json();
            setCurrentPair({ ticker1: randomPair.ticker1, ticker2: randomPair.ticker2 });
            apiUrl = `http://127.0.0.1:8000/api/portfolio/two-asset-analysis?ticker1=${randomPair.ticker1}&ticker2=${randomPair.ticker2}`;
          } else {
            apiUrl = 'http://127.0.0.1:8000/api/portfolio/two-asset-analysis?ticker1=NVDA&ticker2=AMZN';
          }
        } else {
          apiUrl = `http://127.0.0.1:8000/api/portfolio/two-asset-analysis?ticker1=${currentPair.ticker1}&ticker2=${currentPair.ticker2}`;
        }
        
        const response = await fetch(apiUrl);
        console.log('Mini-lesson response status:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Mini-lesson data received:', data);
          setTwoAssetAnalysis(data);
          
          // Calculate initial portfolio
          const asset1Allocation = nvdaWeight / 100;
          const asset2Allocation = (100 - nvdaWeight) / 100;
          
          const portfolioReturn = asset1Allocation * data.asset1_stats.annualized_return + 
                                 asset2Allocation * data.asset2_stats.annualized_return;
          
          const portfolioRisk = Math.sqrt(
            Math.pow(asset1Allocation * data.asset1_stats.annualized_volatility, 2) +
            Math.pow(asset2Allocation * data.asset2_stats.annualized_volatility, 2) +
            2 * asset1Allocation * asset2Allocation * data.asset1_stats.annualized_volatility * 
            data.asset2_stats.annualized_volatility * data.correlation
          );
          
          const riskFreeRate = 0.04; // 4% risk-free rate
          const sharpeRatio = (portfolioReturn - riskFreeRate) / portfolioRisk;
          
          setCustomPortfolio({
            weights: [asset1Allocation, asset2Allocation],
            return: portfolioReturn,
            risk: portfolioRisk,
            sharpe_ratio: sharpeRatio
          });
        } else {
          const errorText = await response.text();
          console.error('Mini-lesson API error:', response.status, errorText);
        }
      } catch (error) {
        console.error('Error loading mini-lesson data:', error);
      } finally {
        setIsLoadingMiniLesson(false);
      }
    };

    loadMiniLesson();
  }, [selectedPairId, currentPair.ticker1, currentPair.ticker2, nvdaWeight]);

  // Update portfolio when weights change
  useEffect(() => {
    if (twoAssetAnalysis) {
      const nvdaAllocation = nvdaWeight / 100;
      const amznAllocation = (100 - nvdaWeight) / 100;
      
      const portfolioReturn = nvdaAllocation * twoAssetAnalysis.asset1_stats.annualized_return + 
                             amznAllocation * twoAssetAnalysis.asset2_stats.annualized_return;
      
      const portfolioRisk = Math.sqrt(
        Math.pow(nvdaAllocation * twoAssetAnalysis.asset1_stats.annualized_volatility, 2) +
        Math.pow(amznAllocation * twoAssetAnalysis.asset2_stats.annualized_volatility, 2) +
        2 * nvdaAllocation * amznAllocation * twoAssetAnalysis.asset1_stats.annualized_volatility * 
        twoAssetAnalysis.asset2_stats.annualized_volatility * twoAssetAnalysis.correlation
      );
      
      const riskFreeRate = 0.04; // 4% risk-free rate
      const sharpeRatio = (portfolioReturn - riskFreeRate) / portfolioRisk;
      
      setCustomPortfolio({
        weights: [nvdaAllocation, amznAllocation],
        return: portfolioReturn,
        risk: portfolioRisk,
        sharpe_ratio: sharpeRatio
      });
    }
  }, [nvdaWeight, twoAssetAnalysis]);

  const searchStocks = useCallback(async (query: string) => {
    if (!query.trim() || query.length < 1) {
      setSearchResults([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      console.log(`Searching for: "${query}"`);
      
      // Use our enhanced backend API with the correct endpoint
      const response = await fetch(`http://127.0.0.1:8000/api/portfolio/ticker/search?q=${encodeURIComponent(query)}&limit=10`);

      console.log(`Response status: ${response.status}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API Error: ${response.status} - ${errorText}`);
        throw new Error(`Failed to fetch stock data: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('API Response:', data);
      
      const tickers = data.results || [];
      console.log(`Found ${tickers.length} tickers`);
      
      setSearchResults(tickers.map((ticker: {
        ticker: string;
        cached: number;
      }) => ({
        symbol: ticker.ticker,
        shortname: ticker.ticker,
        longname: ticker.ticker,
        typeDisp: 'Stock',
        exchange: 'NASDAQ/NYSE',
        quoteType: 'EQUITY',
        assetType: 'stock' as const,
        dataQuality: {
          is_sufficient: true,
          years_covered: 15,
          data_points: 180,
          data_source: 'yahoo_finance',
          issues: ticker.cached ? [] : ['Data may need to be fetched']
        }
      })));
    } catch (err) {
      console.error('Search error:', err);
              setError(`Unable to fetch stock data: ${err instanceof Error ? err.message : 'Unknown error'}. Please check if the backend server is running.`);
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

  // Calculate portfolio metrics
  useEffect(() => {
    if (selectedStocks.length > 0) {
      // Simulate portfolio metrics calculation
      const totalAllocation = selectedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
      const avgReturn = selectedStocks.reduce((sum, stock) => sum + (stock.allocation / 100) * 0.12, 0);
      const avgRisk = selectedStocks.reduce((sum, stock) => sum + (stock.allocation / 100) * 0.2, 0);
      
      setPortfolioMetrics({
        expectedReturn: avgReturn,
        risk: avgRisk,
        diversificationScore: Math.min(100, selectedStocks.length * 20),
        sharpeRatio: (avgReturn - 0.04) / avgRisk
      });
    }
  }, [selectedStocks]);

  const addStock = (stock: StockResult) => {
    if (selectedStocks.length >= 5) {
      setError('Maximum 5 assets allowed for optimal portfolio analysis');
      return;
    }
    
    const newStock: PortfolioAllocation = {
      symbol: stock.symbol,
      allocation: 100 / (selectedStocks.length + 1),
      name: stock.shortname,
      assetType: stock.assetType
    };
    
    const updatedStocks = [...selectedStocks, newStock].map(s => ({
      ...s,
      allocation: 100 / (selectedStocks.length + 1)
    }));
    
    onStocksUpdate(updatedStocks);
    setSearchTerm('');
    setSearchResults([]);
  };

  const removeStock = (symbol: string) => {
    const updatedStocks = selectedStocks.filter(s => s.symbol !== symbol);
    if (updatedStocks.length > 0) {
      const equalAllocation = 100 / updatedStocks.length;
      const rebalancedStocks = updatedStocks.map(s => ({ ...s, allocation: equalAllocation }));
      onStocksUpdate(rebalancedStocks);
    } else {
      onStocksUpdate([]);
    }
  };

  const updateAllocation = (symbol: string, newAllocation: number) => {
    const updatedStocks = selectedStocks.map(s => 
      s.symbol === symbol ? { ...s, allocation: newAllocation } : s
    );
    onStocksUpdate(updatedStocks);
  };

  const acceptRecommendation = (recommendation: PortfolioRecommendation) => {
    onStocksUpdate(recommendation.allocations);
    setHasSelectedPortfolio(true);
  };

  const handleNext = () => {
      onNext();
  };

  const getRiskProfileDisplay = () => {
    const profileMap: { [key: string]: string } = {
      'very-conservative': 'Very Conservative',
      'conservative': 'Conservative', 
      'moderate': 'Moderate',
      'aggressive': 'Aggressive',
      'very-aggressive': 'Very Aggressive'
    };
    return profileMap[riskProfile] || 'Moderate';
  };

  const setPresetWeight = (nvdaPercent: number) => {
    setNvdaWeight(nvdaPercent);
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <Card>
        <CardHeader className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-primary flex items-center justify-center">
            <TrendingUp className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Enhanced Portfolio Construction</CardTitle>
          <p className="text-muted-foreground">
            Build your custom investment portfolio with {capital.toLocaleString()} SEK
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Risk Profile: {getRiskProfileDisplay()}
            </span>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "mini-lesson" | "recommendations" | "full-customization")}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="mini-lesson" className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Mini-Lesson
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="flex items-center gap-2">
                <Star className="h-4 w-4" />
                Recommendations
              </TabsTrigger>
              <TabsTrigger value="full-customization" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Full Customization
              </TabsTrigger>
            </TabsList>

            {/* Mini-Lesson Tab - Enhanced with Asset Selection */}
            <TabsContent value="mini-lesson" className="space-y-6">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
                <div className="flex items-center gap-3 mb-4">
                  <Lightbulb className="h-6 w-6 text-blue-600" />
                  <h3 className="text-xl font-semibold text-blue-900">How Risk and Return Trade Off: The Efficient Frontier</h3>
                </div>
                <p className="text-blue-800 mb-4">
                  Learn how combining different assets can reduce risk while maintaining returns. 
                  Choose from educational asset pairs or get a random comparison to explore portfolio theory.
                  <strong>Note:</strong> All calculations shown are based on real market data and are for educational demonstration purposes only.
                </p>
                
                {/* Asset Pair Selection */}
                {availableAssetPairs.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-lg font-medium text-blue-900 mb-3">Select Asset Pair for Analysis</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {availableAssetPairs.map((pair) => (
                        <Button
                          key={pair.pair_id}
                          variant={selectedPairId === pair.pair_id ? "default" : "outline"}
                          className={`p-4 h-auto text-left ${selectedPairId === pair.pair_id ? 'bg-blue-600 text-white' : 'bg-white text-blue-900 border-blue-200'}`}
                          onClick={() => {
                            setSelectedPairId(pair.pair_id);
                            if (pair.pair_id !== 'random') {
                              setCurrentPair({ ticker1: pair.ticker1, ticker2: pair.ticker2 });
                            }
                          }}
                        >
                          <div className="flex flex-col">
                            <div className="font-medium">{pair.description}</div>
                            <div className="text-sm opacity-80">{pair.educational_focus}</div>
                          </div>
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                
                {isLoadingMiniLesson ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-blue-700">Loading financial data...</p>
                  </div>
                ) : twoAssetAnalysis && customPortfolio ? (
                  <div className="space-y-6">
                    {/* Asset Information Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            {twoAssetAnalysis.ticker1}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            {twoAssetAnalysis.asset1_stats.company_name || twoAssetAnalysis.ticker1}
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Annual Return:</span>
                            <span className="font-medium text-green-600">
                              {(twoAssetAnalysis.asset1_stats.annualized_return * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Volatility:</span>
                            <span className="font-medium text-orange-600">
                              {(twoAssetAnalysis.asset1_stats.annualized_volatility * 100).toFixed(1)}%
                            </span>
                          </div>
                          {twoAssetAnalysis.asset1_stats.sector && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Sector:</span>
                              <span className="font-medium text-blue-600">
                                {twoAssetAnalysis.asset1_stats.sector}
                              </span>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            {twoAssetAnalysis.ticker2}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            {twoAssetAnalysis.asset2_stats.company_name || twoAssetAnalysis.ticker2}
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Annual Return:</span>
                            <span className="font-medium text-green-600">
                              {(twoAssetAnalysis.asset2_stats.annualized_return * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Volatility:</span>
                            <span className="font-medium text-orange-600">
                              {(twoAssetAnalysis.asset2_stats.annualized_volatility * 100).toFixed(1)}%
                            </span>
                          </div>
                          {twoAssetAnalysis.asset2_stats.sector && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Sector:</span>
                              <span className="font-medium text-blue-600">
                                {twoAssetAnalysis.asset2_stats.sector}
                              </span>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    </div>

                    {/* Interactive Two-Asset Chart */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Interactive Portfolio Builder</CardTitle>
                        <p className="text-muted-foreground">
                          Adjust the allocation between {twoAssetAnalysis.ticker1} and {twoAssetAnalysis.ticker2} to see how it affects your portfolio's risk and return.
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>{twoAssetAnalysis.ticker1} Weight: {nvdaWeight}%</span>
                            <span>{twoAssetAnalysis.ticker2} Weight: {100 - nvdaWeight}%</span>
                          </div>
                          <Slider
                            value={[nvdaWeight]}
                            onValueChange={(value) => setNvdaWeight(value[0])}
                            max={100}
                            min={0}
                            step={1}
                            className="w-full"
                          />
                        </div>
                        
                        {/* Preset Buttons */}
                        <div className="flex gap-2 flex-wrap">
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPresetWeight(25)}
                          >
                            25% {twoAssetAnalysis.ticker1}
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPresetWeight(50)}
                          >
                            50% {twoAssetAnalysis.ticker1}
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPresetWeight(75)}
                          >
                            75% {twoAssetAnalysis.ticker1}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Two-Asset Chart Component */}
                    {twoAssetAnalysis && customPortfolio && (
                      <TwoAssetChart
                        analysis={twoAssetAnalysis}
                        customPortfolio={customPortfolio}
                        nvdaWeight={nvdaWeight}
                      />
                    )}

                    {/* Portfolio Metrics */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Your Portfolio Metrics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="text-center p-4 bg-green-50 rounded-lg">
                            <div className="text-2xl font-bold text-green-600">
                              {(customPortfolio.return * 100).toFixed(1)}%
                            </div>
                            <div className="text-sm text-green-700">Expected Return</div>
                          </div>
                          <div className="text-center p-4 bg-orange-50 rounded-lg">
                            <div className="text-2xl font-bold text-orange-600">
                              {(customPortfolio.risk * 100).toFixed(1)}%
                            </div>
                            <div className="text-sm text-orange-700">Risk (Volatility)</div>
                          </div>
                          <div className="text-center p-4 bg-blue-50 rounded-lg">
                            <div className="text-2xl font-bold text-blue-600">
                              {customPortfolio.sharpe_ratio.toFixed(2)}
                            </div>
                            <div className="text-sm text-blue-700">Sharpe Ratio</div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Educational Callouts */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Expected Return:</strong> The average yearly growth rate of your investment 
                          based on historical data from Yahoo Finance (monthly returns, annualized).
                        </AlertDescription>
                      </Alert>
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Risk (Volatility):</strong> Measures how much returns vary from the average. 
                          Higher values mean more uncertainty and potential for larger price swings.
                        </AlertDescription>
                      </Alert>
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Sharpe Ratio:</strong> Risk-adjusted return measure. Higher values indicate 
                          better risk-adjusted performance relative to risk taken.
                        </AlertDescription>
                      </Alert>
                    </div>

                    {/* Data Source Indicator */}
                    <Alert className="mt-4">
                      <Database className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Data Source:</strong> Real market data from Yahoo Finance (monthly returns, annualized). 
                        <strong>Note:</strong> All calculations in this mini-lesson are hypothetical and for demonstration purposes only.
                      </AlertDescription>
                    </Alert>
                  </div>
                ) : (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      Unable to load financial data. Please try refreshing the page.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </TabsContent>

            {/* Recommendations Tab */}
            <TabsContent value="recommendations" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">AI-Powered Portfolio Recommendations</h3>
                <p className="text-muted-foreground">
                  Real-time recommendations optimized for your {getRiskProfileDisplay().toLowerCase()} risk profile using live market data
                </p>
              </div>

              {isLoadingRecommendations ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  <p className="mt-2 text-muted-foreground">Generating personalized recommendations...</p>
                </div>
              ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {(dynamicRecommendations.length > 0 ? dynamicRecommendations : recommendations).map((recommendation, index) => (
                  <Card key={index} className="relative overflow-hidden">
                    <CardHeader className="pb-4">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">{recommendation.name}</CardTitle>
                        <Badge variant={index === 0 ? "default" : "secondary"}>
                          {index === 0 ? "Top Pick" : "Alternative " + (index + 1)}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{recommendation.description}</p>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Expected Return</div>
                          <div className="font-semibold text-green-600">
                            {(recommendation.expectedReturn * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Risk Level</div>
                          <div className="font-semibold text-orange-600">
                            {(recommendation.risk * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Diversification Score</span>
                          <span>{recommendation.diversificationScore}%</span>
                        </div>
                        <Progress value={recommendation.diversificationScore} className="h-2" />
                      </div>

                      <div className="space-y-2">
                        <div className="text-sm font-medium">Allocations:</div>
                        {recommendation.allocations.slice(0, 3).map((allocation, idx) => (
                          <div key={idx} className="flex justify-between text-xs">
                            <span>{allocation.symbol}</span>
                            <span>{allocation.allocation}%</span>
                          </div>
                        ))}
                        {recommendation.allocations.length > 3 && (
                          <div className="text-xs text-muted-foreground">
                            +{recommendation.allocations.length - 3} more stocks
                          </div>
                        )}
                      </div>

                      <Button 
                        onClick={() => acceptRecommendation(recommendation)}
                        className="w-full"
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Use This Portfolio
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
              )}

              {/* Portfolio Customization Section - Only show after selection */}
              {hasSelectedPortfolio && selectedStocks.length > 0 && (
              <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Customize Your Portfolio</CardTitle>
                    <p className="text-muted-foreground">
                      Modify the selected portfolio by adding or removing stocks
                    </p>
                </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Stock Search */}
                    <div className="space-y-4">
                      <div className="flex gap-2">
                    <Input
                      placeholder="Search for stocks and ETFs (e.g., AAPL, MSFT, VOO, QQQ)"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                          className="flex-1"
                    />
                        {isLoading && <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>}
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  {searchResults.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-medium">Search Results</h4>
                      {searchResults.map((stock) => (
                        <div
                          key={stock.symbol}
                          className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                          onClick={() => addStock(stock)}
                        >
                          <div>
                            <div className="font-medium">{stock.symbol}</div>
                            <div className="text-sm text-muted-foreground">{stock.shortname}</div>
                          </div>
                              <Button size="sm" variant="outline">
                                Add
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                    </div>

                                  {/* Selected Stocks */}
                    <div className="space-y-4">
                      <h4 className="font-medium">Selected Assets ({selectedStocks.length}/5) - Minimum 3 recommended</h4>
                      {selectedStocks.map((stock) => (
                        <div key={stock.symbol} className="flex items-center gap-4 p-4 border rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-2">
                              <div>
                                <span className="font-medium">{stock.symbol}</span>
                                {stock.name && (
                                  <span className="text-sm text-muted-foreground ml-2">
                                    {stock.name}
                                  </span>
                                )}
                              </div>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => removeStock(stock.symbol)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                            <div className="flex items-center gap-2">
                              <Slider
                                value={[stock.allocation]}
                                onValueChange={(value) => updateAllocation(stock.symbol, value[0])}
                                max={100}
                                min={0}
                                step={1}
                                className="flex-1"
                              />
                              <span className="text-sm font-medium w-12 text-right">
                                {stock.allocation.toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

              {/* Portfolio Analytics */}
              {portfolioMetrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 bg-green-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">
                          {(portfolioMetrics.expectedReturn * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-green-700">Expected Return</div>
                      </div>
                      <div className="text-center p-4 bg-orange-50 rounded-lg">
                        <div className="text-2xl font-bold text-orange-600">
                          {(portfolioMetrics.risk * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-orange-700">Risk Level</div>
                      </div>
                      <div className="text-center p-4 bg-blue-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">
                          {portfolioMetrics.sharpeRatio.toFixed(2)}
                        </div>
                        <div className="text-sm text-blue-700">Sharpe Ratio</div>
                      </div>
                      <div className="text-center p-4 bg-purple-50 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600">
                          {portfolioMetrics.diversificationScore}%
                        </div>
                        <div className="text-sm text-purple-700">Diversification</div>
                      </div>
                    </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Full Customization Tab */}
            <TabsContent value="full-customization" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Full Customization</h3>
                <p className="text-muted-foreground">
                  Advanced portfolio construction with efficient frontier analysis
                </p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Search and Select Assets</CardTitle>
                  <p className="text-muted-foreground">
                    Search for stocks and ETFs to build your custom portfolio for efficient frontier analysis (3-5 assets recommended)
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Stock Search */}
                  <div className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        placeholder="Search for stocks and ETFs (e.g., AAPL, MSFT, VOO, QQQ)"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="flex-1"
                      />
                      {isLoading && <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>}
                    </div>

                    {error && (
                      <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    {searchResults.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="font-medium">Search Results</h4>
                        {searchResults.map((stock) => (
                          <div
                            key={stock.symbol}
                            className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                            onClick={() => addStock(stock)}
                          >
                            <div>
                              <div className="font-medium">{stock.symbol}</div>
                              <div className="text-sm text-muted-foreground">{stock.shortname}</div>
                            </div>
                            <Button size="sm" variant="outline">
                              Add
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Selected Assets for Full Customization */}
                  {selectedStocks.length > 0 && (
                    <div className="space-y-4">
                      <h4 className="font-medium">Selected Assets ({selectedStocks.length}/5) - Minimum 3 recommended</h4>
                      {selectedStocks.map((stock) => (
                        <div key={stock.symbol} className="flex items-center gap-4 p-4 border rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-2">
                              <div>
                                <span className="font-medium">{stock.symbol}</span>
                                {stock.name && (
                                  <span className="text-sm text-muted-foreground ml-2">
                                    {stock.name}
                                  </span>
                                )}
                              </div>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => removeStock(stock.symbol)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                            <div className="flex items-center gap-2">
                              <Slider
                                value={[stock.allocation]}
                                onValueChange={(value) => updateAllocation(stock.symbol, value[0])}
                                max={100}
                                min={0}
                                step={1}
                                className="flex-1"
                              />
                              <span className="text-sm font-medium w-12 text-right">
                                {stock.allocation.toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Efficient Frontier Placeholder */}
                  <div className="text-center py-8 text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Efficient Frontier analysis will be computed once you select 3-5 assets.</p>
                    <p className="text-sm mt-2">This will include covariance analysis, optimal weight recommendations, and interactive frontier visualization.</p>
                  </div>
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
            <Button 
              onClick={handleNext}
              disabled={selectedStocks.length < 3}
            >
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>

        </CardContent>
      </Card>
    </div>
  );
};