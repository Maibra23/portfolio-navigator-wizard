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
  const [activeTab, setActiveTab] = useState<'mini-lesson' | 'recommendations' | 'custom' | 'full-customization'>('mini-lesson');
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
  
  // Full customization state
  const [fullCustomTickers, setFullCustomTickers] = useState<string[]>([]);
  const [fullCustomWeights, setFullCustomWeights] = useState<number[]>([]);
  const [fullCustomAnalysis, setFullCustomAnalysis] = useState<{
    efficientFrontier: Array<{return: number, risk: number, weights: number[]}>;
    optimalPortfolio: {return: number, risk: number, weights: number[]};
  } | null>(null);
  const [isLoadingFullCustom, setIsLoadingFullCustom] = useState(false);

  // Generate recommendations based on risk profile
  const generateRecommendations = (): PortfolioRecommendation[] => {
    // Define portfolio templates for each risk category
    const portfolioTemplates = {
      'very-conservative': {
        name: 'Very Conservative Portfolio',
        description: 'Maximum capital preservation with minimal risk exposure',
        allocations: [
          { symbol: 'JNJ', allocation: 35, name: 'Johnson & Johnson', assetType: 'stock' as const },
          { symbol: 'PG', allocation: 30, name: 'Procter & Gamble', assetType: 'stock' as const },
          { symbol: 'KO', allocation: 25, name: 'Coca-Cola', assetType: 'stock' as const },
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
          { symbol: 'JNJ', allocation: 30, name: 'Johnson & Johnson', assetType: 'stock' as const },
          { symbol: 'PG', allocation: 25, name: 'Procter & Gamble', assetType: 'stock' as const },
          { symbol: 'KO', allocation: 20, name: 'Coca-Cola', assetType: 'stock' as const },
          { symbol: 'VZ', allocation: 15, name: 'Verizon', assetType: 'stock' as const },
          { symbol: 'T', allocation: 10, name: 'AT&T', assetType: 'stock' as const }
        ],
        expectedReturn: 0.08,
        risk: 0.12,
        diversificationScore: 85
      },
      'moderate': {
        name: 'Balanced Portfolio',
        description: 'Moderate risk with a mix of growth and value stocks',
        allocations: [
          { symbol: 'AAPL', allocation: 25, name: 'Apple Inc.', assetType: 'stock' as const },
          { symbol: 'MSFT', allocation: 20, name: 'Microsoft', assetType: 'stock' as const },
          { symbol: 'GOOGL', allocation: 15, name: 'Alphabet Inc.', assetType: 'stock' as const },
          { symbol: 'AMZN', allocation: 15, name: 'Amazon.com', assetType: 'stock' as const },
          { symbol: 'TSLA', allocation: 10, name: 'Tesla Inc.', assetType: 'stock' as const },
          { symbol: 'NVDA', allocation: 15, name: 'NVIDIA', assetType: 'stock' as const }
        ],
        expectedReturn: 0.12,
        risk: 0.18,
        diversificationScore: 78
      },
      'aggressive': {
        name: 'Growth Portfolio',
        description: 'Higher risk portfolio targeting aggressive growth',
        allocations: [
          { symbol: 'NVDA', allocation: 30, name: 'NVIDIA', assetType: 'stock' as const },
          { symbol: 'TSLA', allocation: 25, name: 'Tesla Inc.', assetType: 'stock' as const },
          { symbol: 'AMD', allocation: 20, name: 'Advanced Micro Devices', assetType: 'stock' as const },
          { symbol: 'META', allocation: 15, name: 'Meta Platforms', assetType: 'stock' as const },
          { symbol: 'NFLX', allocation: 10, name: 'Netflix', assetType: 'stock' as const }
        ],
        expectedReturn: 0.18,
        risk: 0.28,
        diversificationScore: 65
      },
      'very-aggressive': {
        name: 'Very Aggressive Portfolio',
        description: 'Maximum growth potential with highest risk tolerance',
        allocations: [
          { symbol: 'NVDA', allocation: 35, name: 'NVIDIA', assetType: 'stock' as const },
          { symbol: 'TSLA', allocation: 30, name: 'Tesla Inc.', assetType: 'stock' as const },
          { symbol: 'AMD', allocation: 20, name: 'Advanced Micro Devices', assetType: 'stock' as const },
          { symbol: 'META', allocation: 15, name: 'Meta Platforms', assetType: 'stock' as const }
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

  // Load mini-lesson data from backend
  useEffect(() => {
    const loadMiniLesson = async () => {
      setIsLoadingMiniLesson(true);
      try {
        // Try to fetch real data from backend
        const response = await fetch('http://localhost:8000/api/portfolio/two-asset-analysis?ticker1=NVDA&ticker2=AMZN');
        
        if (response.ok) {
          const realData: TwoAssetAnalysis = await response.json();
          setTwoAssetAnalysis(realData);
          setCustomPortfolio(realData.portfolios[2]); // 50/50 portfolio
        } else {
          // Fallback to mock data if backend fails
          const mockData: TwoAssetAnalysis = {
            ticker1: 'NVDA',
            ticker2: 'AMZN',
            asset1_stats: {
              ticker: 'NVDA',
              annualized_return: 0.25,
              annualized_volatility: 0.35,
              price_history: [],
              last_price: 500,
              start_date: '2020-01-01',
              end_date: '2024-01-01',
              data_source: 'yahoo_finance'
            },
            asset2_stats: {
              ticker: 'AMZN',
              annualized_return: 0.15,
              annualized_volatility: 0.25,
              price_history: [],
              last_price: 150,
              start_date: '2020-01-01',
              end_date: '2024-01-01',
              data_source: 'yahoo_finance'
            },
            correlation: 0.3,
            portfolios: [
              { weights: [1, 0], return: 0.25, risk: 0.35, sharpe_ratio: 0.6 },
              { weights: [0.75, 0.25], return: 0.225, risk: 0.31, sharpe_ratio: 0.6 },
              { weights: [0.5, 0.5], return: 0.2, risk: 0.28, sharpe_ratio: 0.57 },
              { weights: [0.25, 0.75], return: 0.175, risk: 0.26, sharpe_ratio: 0.52 },
              { weights: [0, 1], return: 0.15, risk: 0.25, sharpe_ratio: 0.44 }
            ]
          };

          setTwoAssetAnalysis(mockData);
          setCustomPortfolio(mockData.portfolios[2]); // 50/50 portfolio
        }
      } catch (err) {
        setError('Failed to load mini-lesson data');
      } finally {
        setIsLoadingMiniLesson(false);
      }
    };

    loadMiniLesson();
  }, []);

  // Update custom portfolio when NVDA weight changes
  useEffect(() => {
    if (twoAssetAnalysis && nvdaWeight >= 0 && nvdaWeight <= 100) {
      const amznWeight = 100 - nvdaWeight;
      const nvdaWeightDecimal = nvdaWeight / 100;
      const amznWeightDecimal = amznWeight / 100;
      
      // Calculate custom portfolio metrics
      const asset1 = twoAssetAnalysis.asset1_stats;
      const asset2 = twoAssetAnalysis.asset2_stats;
      const correlation = twoAssetAnalysis.correlation;
      
      // Portfolio return: Σwi·ri
      const portfolioReturn = (nvdaWeightDecimal * asset1.annualized_return + 
                              amznWeightDecimal * asset2.annualized_return);
      
      // Portfolio risk: √(Σwi²·σi² + 2·w1·w2·σ1·σ2·ρ12)
      const sigma1 = asset1.annualized_volatility;
      const sigma2 = asset2.annualized_volatility;
      
      const portfolioRisk = Math.sqrt(
        nvdaWeightDecimal**2 * sigma1**2 + 
        amznWeightDecimal**2 * sigma2**2 + 
        2 * nvdaWeightDecimal * amznWeightDecimal * sigma1 * sigma2 * correlation
      );
      
      // Sharpe ratio: (return - risk_free_rate) / risk
      const riskFreeRate = 0.04;
      const sharpeRatio = (portfolioReturn - riskFreeRate) / portfolioRisk;
      
      setCustomPortfolio({
        weights: [nvdaWeightDecimal, amznWeightDecimal],
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
      // Use our enhanced backend API
      const response = await fetch(`http://localhost:8000/api/portfolio/asset-search?q=${encodeURIComponent(query)}`);

      if (!response.ok) {
        throw new Error('Failed to fetch stock data');
      }

      const data = await response.json();
      const stocks = data.results || [];
      
      setSearchResults(stocks.map((stock: {
        symbol: string;
        name: string;
        exchange: string;
        data_quality: {
          is_sufficient: boolean;
          years_covered: number;
          data_points: number;
          data_source: string;
          issues?: string[];
        };
      }) => ({
        symbol: stock.symbol,
        shortname: stock.name || stock.symbol,
        longname: stock.name || stock.symbol,
        typeDisp: stock.exchange || '',
        exchange: stock.exchange || '',
        quoteType: stock.data_quality?.data_source === 'yahoo_finance' ? 'EQUITY' : 'ETF',
        assetType: stock.data_quality?.data_source === 'yahoo_finance' ? 'stock' : 'etf',
        dataQuality: stock.data_quality
      })));
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
    if (selectedStocks.length >= 10) {
      setError('Maximum 10 stocks allowed');
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
      const rebalancedStocks = updatedStocks.map(s => ({
        ...s,
        allocation: 100 / updatedStocks.length
      }));
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
    setActiveTab('custom');
  };

  const handleNext = () => {
    if (selectedStocks.length >= 3) {
      onNext();
    }
  };

  const getRiskProfileDisplay = () => {
    const profiles = {
      'very-conservative': 'Very Conservative',
      'conservative': 'Conservative', 
      'moderate': 'Moderate',
      'aggressive': 'Aggressive',
      'very-aggressive': 'Very Aggressive'
    };
    return profiles[riskProfile as keyof typeof profiles] || 'Moderate';
  };

  const setPresetWeight = (nvdaPercent: number) => {
    setNvdaWeight(nvdaPercent);
  };

  return (
    <div className="max-w-6xl mx-auto">
      <Card className="shadow-card">
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
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "mini-lesson" | "recommendations" | "custom" | "full-customization")}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="mini-lesson" className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Mini-Lesson
              </TabsTrigger>
              <TabsTrigger value="recommendations" className="flex items-center gap-2">
                <Star className="h-4 w-4" />
                Recommendations
              </TabsTrigger>
              <TabsTrigger value="custom" className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                Custom Portfolio
              </TabsTrigger>
              <TabsTrigger value="full-customization" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Full Customization
              </TabsTrigger>
            </TabsList>

            {/* Mini-Lesson Tab */}
            <TabsContent value="mini-lesson" className="space-y-6">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
                <div className="flex items-center gap-3 mb-4">
                  <Lightbulb className="h-6 w-6 text-blue-600" />
                  <h3 className="text-xl font-semibold text-blue-900">How Risk and Return Trade Off: The Efficient Frontier</h3>
                </div>
                <p className="text-blue-800 mb-4">
                  Learn how combining different assets can reduce risk while maintaining returns. 
                  We'll use NVIDIA (NVDA) and Amazon (AMZN) to demonstrate portfolio theory.
                </p>
                
                {isLoadingMiniLesson ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-blue-700">Loading financial data...</p>
                  </div>
                ) : twoAssetAnalysis && customPortfolio ? (
                  <div className="space-y-6">
                    {/* Asset Information */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            {twoAssetAnalysis.ticker1} (NVIDIA)
                          </CardTitle>
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
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            {twoAssetAnalysis.ticker2} (Amazon)
                          </CardTitle>
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
                        </CardContent>
                      </Card>
                    </div>

                    {/* Interactive Slider */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Interactive Portfolio Builder</CardTitle>
                        <p className="text-muted-foreground">
                          Adjust the allocation between NVDA and AMZN to see how it affects your portfolio's risk and return.
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>NVDA Weight: {nvdaWeight}%</span>
                            <span>AMZN Weight: {100 - nvdaWeight}%</span>
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
                            25% NVDA
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPresetWeight(50)}
                          >
                            50% NVDA
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPresetWeight(75)}
                          >
                            75% NVDA
                          </Button>
                        </div>
                      </CardContent>
                    </Card>

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
                          <strong>Annualized Return:</strong> The average yearly growth rate of your investment 
                          over the past 5 years.
                        </AlertDescription>
                      </Alert>
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Standard Deviation:</strong> Measures how much returns vary from the average. 
                          Higher values mean more uncertainty.
                        </AlertDescription>
                      </Alert>
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Sharpe Ratio:</strong> Risk-adjusted return measure. Higher values indicate 
                          better risk-adjusted performance.
                        </AlertDescription>
                      </Alert>
                    </div>

                    {/* Data Source Indicator */}
                    <Alert className="mt-4">
                      <Database className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Data Source:</strong> {twoAssetAnalysis?.asset1_stats?.data_source === 'yahoo_finance' ? 
                          'Real market data from Yahoo Finance' : 'Simulated data for educational purposes'}
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
                <h3 className="text-xl font-semibold mb-2">Portfolio Recommendations Dashboard</h3>
                <p className="text-muted-foreground">
                  AI-powered recommendations based on your {getRiskProfileDisplay().toLowerCase()} risk profile
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {recommendations.map((recommendation, index) => (
                  <Card key={index} className="relative overflow-hidden">
                    <CardHeader className="pb-4">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">{recommendation.name}</CardTitle>
                        <Badge variant={index === 0 ? "default" : "secondary"}>
                          {index === 0 ? "Top Pick" : "Option " + (index + 1)}
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
            </TabsContent>

            {/* Custom Portfolio Tab */}
            <TabsContent value="custom" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Custom Portfolio Builder</h3>
                <p className="text-muted-foreground">
                  Search and select individual stocks to build your own portfolio
                </p>
              </div>

              {/* Stock Search */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Search Stocks</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        placeholder="Search for stocks (e.g., AAPL, MSFT, GOOGL)"
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
                </CardContent>
              </Card>

              {/* Selected Stocks */}
              {selectedStocks.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Selected Stocks ({selectedStocks.length}/5)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
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
                  </CardContent>
                </Card>
              )}

              {/* Portfolio Analytics */}
              {portfolioMetrics && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Portfolio Analytics</CardTitle>
                  </CardHeader>
                  <CardContent>
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
                  </CardContent>
                </Card>
              )}

              {/* Error message only for custom tab */}
              {selectedStocks.length < 3 && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Please select at least 3 stocks to continue. You currently have {selectedStocks.length} stocks selected.
                  </AlertDescription>
                </Alert>
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

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  This feature allows you to select 3-5 US stock tickers and analyze the efficient frontier 
                  to find optimal portfolio weights. Coming soon!
                </AlertDescription>
              </Alert>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Efficient Frontier Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Advanced portfolio optimization features will be available here.</p>
                    <p className="text-sm mt-2">This will include efficient frontier calculations, covariance analysis, and optimal weight recommendations.</p>
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
              disabled={activeTab === 'custom' && selectedStocks.length < 3}
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