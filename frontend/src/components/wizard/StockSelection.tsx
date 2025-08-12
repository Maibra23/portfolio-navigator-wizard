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
  Database,
  XCircle,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Switch } from '@/components/ui/switch';
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
  sharpeRatio: number; // Keep for compatibility but will be set to 0
}

// NEW: Portfolio Validation Interface
interface PortfolioValidation {
  isValid: boolean;
  totalAllocation: number;
  stockCount: number;
  warnings: string[];
  canProceed: boolean;
  optimalityScore?: number;
  ranking?: number;
}

// NEW: Dynamic Portfolio State Interface
interface DynamicPortfolioState {
  selectedStocks: PortfolioAllocation[];
  portfolioMetrics: PortfolioMetrics | null;
  portfolioValidation: PortfolioValidation;
  showWeightEditor: boolean;
  hasSelectedPortfolio: boolean;
  selectedPortfolioIndex: number | null;
  originalRecommendation: PortfolioRecommendation | null;
  isLoadingMetrics: boolean;
  error: string | null;
  successMessage: string | null;
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
  sharpe_ratio: number; // Keep for compatibility but will be set to 0
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
  const [activeTab, setActiveTab] = useState<'mini-lesson' | 'recommendations' | 'full-customization' | 'dynamic-generation'>('mini-lesson');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<StockResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);
  const [sectorRecommendations, setSectorRecommendations] = useState<SectorRecommendation[]>([]);
  const [showDiversification, setShowDiversification] = useState(false);
  
  // NEW: Dynamic Portfolio Generation State
  const [dynamicPortfolios, setDynamicPortfolios] = useState<PortfolioRecommendation[]>([]);
  const [isLoadingDynamic, setIsLoadingDynamic] = useState(false);
  const [optimizationParams, setOptimizationParams] = useState({
    targetReturn: 0.15,
    maxRisk: 0.25
  });
  const [selectedOptimizationStrategy, setSelectedOptimizationStrategy] = useState<string>('all');
  
  // NEW: Dynamic Portfolio State Management
  const [portfolioValidation, setPortfolioValidation] = useState<PortfolioValidation>({
    isValid: false,
    totalAllocation: 0,
    stockCount: 0,
    warnings: [],
    canProceed: false
  });
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [hasSelectedPortfolio, setHasSelectedPortfolio] = useState(false);
  const [selectedPortfolioIndex, setSelectedPortfolioIndex] = useState<number | null>(null);
  const [originalRecommendation, setOriginalRecommendation] = useState<PortfolioRecommendation | null>(null);
  
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
  const [selectedPairId, setSelectedPairId] = useState('random');
  const [currentPair, setCurrentPair] = useState({ ticker1: '', ticker2: '' });
  
  // Full customization state
  const [fullCustomTickers, setFullCustomTickers] = useState<string[]>([]);
  const [fullCustomWeights, setFullCustomWeights] = useState<number[]>([]);
  const [fullCustomAnalysis, setFullCustomAnalysis] = useState<{
    efficientFrontier: Array<{return: number, risk: number, weights: number[]}>;
    optimalPortfolio: {return: number, risk: number, weights: number[]};
  } | null>(null);
  const [isLoadingFullCustom, setIsLoadingFullCustom] = useState(false);

  // Track if user has selected a portfolio recommendation
  const [dynamicRecommendations, setDynamicRecommendations] = useState<PortfolioRecommendation[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  
  // NEW: Weight editor state
  const [showWeightEditor, setShowWeightEditor] = useState(false);
  const [totalAllocation, setTotalAllocation] = useState(100);
  const [isValidAllocation, setIsValidAllocation] = useState(true);

  // Generate recommendations based on risk profile with updated names and descriptions
  const generateRecommendations = (): PortfolioRecommendation[] => {
    // Define portfolio templates for each risk category with improved names and descriptions
    const portfolioTemplates = {
      'very-conservative': {
        name: 'Capital Preservation Portfolio',
        description: 'Defensive strategy focused on stable dividend stocks and capital preservation. Ideal for investors who prioritize safety over growth.',
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
        name: 'Income & Stability Portfolio',
        description: 'Balanced approach combining steady income generation with moderate growth potential. Suitable for conservative investors seeking reliable returns.',
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
        name: 'Balanced Growth Portfolio',
        description: 'Diversified mix of growth and value stocks offering balanced risk-return profile. Perfect for investors comfortable with moderate market volatility.',
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
        name: 'Growth Momentum Portfolio',
        description: 'High-growth strategy targeting companies with strong momentum and innovation potential. Designed for investors seeking above-market returns.',
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
        name: 'Maximum Growth Portfolio',
        description: 'High-conviction growth strategy focusing on disruptive technologies and emerging trends. For investors with high risk tolerance seeking maximum growth potential.',
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
        const response = await fetch(`/api/portfolio/recommendations/${riskProfile}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Dynamic recommendations received:', data);
          
          // Transform backend data to frontend format
          const transformedRecommendations = data.map((rec: {
            name?: string;
            description?: string;
            portfolio?: PortfolioAllocation[];
            expectedReturn?: number;
            risk?: number;
            diversificationScore?: number;
          }, index: number) => ({
            name: rec.name || `Portfolio ${index + 1}`,
            description: rec.description || 'Diversified portfolio based on your risk profile',
            allocations: rec.portfolio || [],
            expectedReturn: rec.expectedReturn || 0.1,
            risk: rec.risk || 0.15,
            diversificationScore: rec.diversificationScore || 75
          }));
          
          setDynamicRecommendations(transformedRecommendations);
        } else {
          console.warn('Failed to load dynamic recommendations, using static ones');
          setDynamicRecommendations([]);
        }
      } catch (error) {
        console.error('Error loading dynamic recommendations:', error);
        setDynamicRecommendations([]);
      } finally {
        setIsLoadingRecommendations(false);
      }
    };

    loadDynamicRecommendations();
  }, [riskProfile]);

  // Load available asset pairs for mini-lesson
  const loadAssetPairs = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/portfolio/mini-lesson/assets');
      if (response.ok) {
        const data = await response.json();
        
        // Create 3 fixed educational pairs from sector lists with improved rotation
        const pairs = [];
        
        // Get random assets from different sector lists
        if (data.sector_lists && data.sector_lists.length >= 3) {
          // Create more diverse combinations by randomly selecting from available sectors
          const availableSectors = data.sector_lists.filter(list => list.assets && list.assets.length > 0);
          
          if (availableSectors.length >= 2) {
            // Generate 3 random pairs from different sector combinations
            for (let i = 0; i < 3; i++) {
              // Randomly select two different sectors
              const shuffledSectors = [...availableSectors].sort(() => Math.random() - 0.5);
              const sector1 = shuffledSectors[0];
              const sector2 = shuffledSectors[1];
              
              if (sector1 && sector2 && sector1.assets.length > 0 && sector2.assets.length > 0) {
                // Randomly select assets from each sector
                const asset1 = sector1.assets[Math.floor(Math.random() * sector1.assets.length)];
                const asset2 = sector2.assets[Math.floor(Math.random() * sector2.assets.length)];
                
                // Create educational theme based on sectors
                const themes = {
                  'Technology': 'Innovation & Growth',
                  'Healthcare': 'Health & Stability',
                  'Financial Services': 'Financial Infrastructure',
                  'Consumer Discretionary': 'Consumer Demand',
                  'Consumer Staples': 'Essential Goods',
                  'Energy': 'Energy Infrastructure',
                  'Communication Services': 'Communication & Media',
                  'Industrials': 'Industrial Strength',
                  'Materials': 'Raw Materials',
                  'Real Estate': 'Property & Real Estate',
                  'Utilities': 'Utility Services',
                  'Consumer Staples & Healthcare': 'Stability & Health',
                  'Financial Services & Consumer': 'Financial & Consumer Services'
                };
                
                const theme1 = themes[sector1.sector] || sector1.sector;
                const theme2 = themes[sector2.sector] || sector2.sector;
                
                // Create shorter, more concise descriptions
                const shortSector1 = sector1.sector.length > 12 ? sector1.sector.substring(0, 12) + '...' : sector1.sector;
                const shortSector2 = sector2.sector.length > 12 ? sector2.sector.substring(0, 12) + '...' : sector2.sector;
                
                pairs.push({
                  pair_id: `pair_${i}_${Date.now()}`,
                  ticker1: asset1.ticker,
                  ticker2: asset2.ticker,
                  name1: asset1.name,
                  name2: asset2.name,
                  description: `${shortSector1} vs ${shortSector2}`,
                  educational_focus: `${theme1} vs ${theme2}`
                });
              }
            }
          }
          
          // If we don't have enough diverse sectors, fall back to original logic
          if (pairs.length < 3) {
            // Pair 1: Tech vs Healthcare
            const techList = data.sector_lists.find(list => list.list_id === 'tech_growth');
            const healthList = data.sector_lists.find(list => list.list_id === 'healthcare_pharma');
            
            if (techList && healthList && techList.assets.length > 0 && healthList.assets.length > 0) {
              const techAsset = techList.assets[Math.floor(Math.random() * techList.assets.length)];
              const healthAsset = healthList.assets[Math.floor(Math.random() * healthList.assets.length)];
              
              pairs.push({
                pair_id: 'tech_health',
                ticker1: techAsset.ticker,
                ticker2: healthAsset.ticker,
                name1: techAsset.name,
                name2: healthAsset.name,
                description: 'Technology Growth vs Healthcare & Pharma',
                educational_focus: 'Innovation & Growth vs Health & Stability'
              });
            }
            
            // Pair 2: Consumer vs Energy
            const consumerList = data.sector_lists.find(list => list.list_id === 'consumer_discretionary');
            const energyList = data.sector_lists.find(list => list.list_id === 'energy_utilities');
            
            if (consumerList && energyList && consumerList.assets.length > 0 && energyList.assets.length > 0) {
              const consumerAsset = consumerList.assets[Math.floor(Math.random() * consumerList.assets.length)];
              const energyAsset = energyList.assets[Math.floor(Math.random() * energyList.assets.length)];
              
              pairs.push({
                pair_id: 'consumer_energy',
                ticker1: consumerAsset.ticker,
                ticker2: energyAsset.ticker,
                name1: consumerAsset.name,
                name2: consumerAsset.name,
                description: 'Consumer Discretionary vs Energy & Utilities',
                educational_focus: 'Consumer Demand vs Energy Infrastructure'
              });
            }
            
            // Pair 3: Financial vs Stable Blue Chips
            const financialList = data.sector_lists.find(list => list.list_id === 'financial_services');
            const stableList = data.sector_lists.find(list => list.list_id === 'stable_blue_chips');
            
            if (financialList && stableList && financialList.assets.length > 0 && stableList.assets.length > 0) {
              const financialAsset = financialList.assets[Math.floor(Math.random() * financialList.assets.length)];
              const stableAsset = stableList.assets[Math.floor(Math.random() * stableList.assets.length)];
              
              pairs.push({
                pair_id: 'financial_stable',
                ticker1: financialAsset.ticker,
                ticker2: stableAsset.ticker,
                name1: financialAsset.name,
                name2: stableAsset.name,
                description: 'Financial Services & Consumer vs Stable Blue Chips',
                educational_focus: 'Financial & Consumer Services vs Stability & Health'
              });
            }
          }
        }
        
        setAvailableAssetPairs(pairs);
        
        // Set current pair to the first available pair
        if (pairs.length > 0) {
          setCurrentPair({ ticker1: pairs[0].ticker1, ticker2: pairs[0].ticker2 });
          setSelectedPairId(pairs[0].pair_id);
        }
      }
    } catch (error) {
      console.error('Error loading asset pairs:', error);
    }
  };

  useEffect(() => {
    loadAssetPairs();
  }, []);

  // Load mini-lesson data when pair changes
  useEffect(() => {
    const loadMiniLesson = async () => {
      setIsLoadingMiniLesson(true);
      try {
        console.log('Loading mini-lesson data for:', currentPair);
        
        const ticker1 = currentPair.ticker1;
        const ticker2 = currentPair.ticker2;
        
        const apiUrl = `http://127.0.0.1:8000/api/portfolio/two-asset-analysis?ticker1=${ticker1}&ticker2=${ticker2}`;
        
        const response = await fetch(apiUrl);
        console.log('Mini-lesson response status:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Mini-lesson data received:', data);
          
          setTwoAssetAnalysis(data);
          
          // Calculate initial custom portfolio (50/50 split)
          const asset1Allocation = 50 / 100;
          const asset2Allocation = 50 / 100;
          
          const portfolioReturn = asset1Allocation * data.asset1_stats.annualized_return + 
                                 asset2Allocation * data.asset2_stats.annualized_return;
          
          const portfolioRisk = Math.sqrt(
            Math.pow(asset1Allocation * data.asset1_stats.annualized_volatility, 2) +
            Math.pow(asset2Allocation * data.asset2_stats.annualized_volatility, 2) +
            2 * asset1Allocation * asset2Allocation * data.asset1_stats.annualized_volatility * 
            data.asset2_stats.annualized_volatility * data.correlation
          );
          
          setCustomPortfolio({
            weights: [asset1Allocation, asset2Allocation],
            return: portfolioReturn,
            risk: portfolioRisk,
            sharpe_ratio: 0 // Removed Sharpe ratio calculation
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
  }, [currentPair.ticker1, currentPair.ticker2, selectedPairId]);

  // Update portfolio when weights change - instant calculation
  useEffect(() => {
    if (twoAssetAnalysis) {
      const asset1Allocation = nvdaWeight / 100;
      const asset2Allocation = (100 - nvdaWeight) / 100;
      
      const portfolioReturn = asset1Allocation * twoAssetAnalysis.asset1_stats.annualized_return + 
                             asset2Allocation * twoAssetAnalysis.asset2_stats.annualized_return;
      
      const portfolioRisk = Math.sqrt(
        Math.pow(asset1Allocation * twoAssetAnalysis.asset1_stats.annualized_volatility, 2) +
        Math.pow(asset2Allocation * twoAssetAnalysis.asset2_stats.annualized_volatility, 2) +
        2 * asset1Allocation * asset2Allocation * twoAssetAnalysis.asset1_stats.annualized_volatility * 
        twoAssetAnalysis.asset2_stats.annualized_volatility * twoAssetAnalysis.correlation
      );
      
      setCustomPortfolio({
        weights: [asset1Allocation, asset2Allocation],
        return: portfolioReturn,
        risk: portfolioRisk,
        sharpe_ratio: 0 // Removed Sharpe ratio calculation
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
      
      // FIXED: Use relative URL to work with Vite proxy
      const response = await fetch(`/api/portfolio/ticker/search?q=${encodeURIComponent(query)}&limit=10`);

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
      
      // NEW: Add warning if no results found
      if (tickers.length === 0) {
        setError(`No stocks found for "${query}". The stock may not be in our database. Try a different search term.`);
        setSearchResults([]);
        return;
      }
      
      setSearchResults(tickers.map((ticker: {
        ticker: string;
        name?: string;
        longname?: string;
        typeDisp?: string;
        exchange?: string;
        quoteType?: string;
        assetType?: string;
      }) => ({
        symbol: ticker.ticker,
        shortname: ticker.name || ticker.ticker,
        longname: ticker.longname,
        typeDisp: ticker.typeDisp,
        exchange: ticker.exchange,
        quoteType: ticker.quoteType,
        assetType: ticker.assetType || 'stock',
        dataQuality: {
          is_sufficient: true,
          years_covered: 5,
          data_points: 60,
          data_source: 'Yahoo Finance',
        }
      })));
    } catch (error) {
      console.error('Search error:', error);
      setError(error instanceof Error ? error.message : 'Failed to search stocks');
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

  // Calculate portfolio metrics based on SELECTED portfolio, not individual stocks
  useEffect(() => {
    if (selectedPortfolioIndex !== null && originalRecommendation) {
      // Use the selected portfolio's actual metrics, not calculated from individual stocks
      setPortfolioMetrics({
        expectedReturn: originalRecommendation.expectedReturn,
        risk: originalRecommendation.risk,
        diversificationScore: originalRecommendation.diversificationScore,
        sharpeRatio: 0 // Always 0 as requested
      });
    } else if (selectedStocks.length > 0) {
      // Fallback for custom portfolios (not from recommendations)
      const totalAllocation = selectedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
      const avgReturn = selectedStocks.reduce((sum, stock) => sum + (stock.allocation / 100) * 0.12, 0);
      const avgRisk = selectedStocks.reduce((sum, stock) => sum + (stock.allocation / 100) * 0.2, 0);
      
      setPortfolioMetrics({
        expectedReturn: avgReturn,
        risk: avgRisk,
        diversificationScore: Math.min(100, selectedStocks.length * 20),
        sharpeRatio: 0 // Always 0 as requested
      });
    }
  }, [selectedStocks, selectedPortfolioIndex, originalRecommendation]);

  // NEW: Real-time portfolio metrics calculation and validation
  useEffect(() => {
    if (selectedStocks.length > 0) {
      // Trigger real-time metrics calculation
      setTimeout(() => {
        calculateRealTimeMetrics();
        validatePortfolio();
      }, 100);
    } else {
      // Reset metrics and validation when no stocks selected
      setPortfolioMetrics(null);
      setPortfolioValidation({
        isValid: false,
        totalAllocation: 0,
        stockCount: 0,
        warnings: [],
        canProceed: false
      });
    }
  }, [selectedStocks]);

  const addStock = (stock: StockResult) => {
    // Validation checks
    if (selectedStocks.some(s => s.symbol === stock.symbol)) {
      setError(`${stock.symbol} is already in your portfolio`);
      return;
    }
    
    if (selectedStocks.length >= 10) {
      setError('Maximum 10 stocks allowed in portfolio');
      return;
    }
    
    // Add stock with smart weight distribution
    const newStock: PortfolioAllocation = {
      symbol: stock.symbol,
      allocation: 100 / (selectedStocks.length + 1),
      name: stock.longname || stock.shortname,
      assetType: stock.assetType || 'stock'
    };
    
    // Update portfolio and normalize weights
    const updatedStocks = [...selectedStocks, newStock];
    const normalizedStocks = updatedStocks.map(s => ({
      ...s,
      allocation: 100 / updatedStocks.length
    }));
    
    onStocksUpdate(normalizedStocks);
    setSearchTerm('');
    setSearchResults([]);
    
    // Portfolio metrics update automatically via useEffect
  };

  const removeStock = (symbol: string) => {
    const updatedStocks = selectedStocks.filter(s => s.symbol !== symbol);
    if (updatedStocks.length > 0) {
      // Rebalance weights after removal
      const equalAllocation = 100 / updatedStocks.length;
      const rebalancedStocks = updatedStocks.map(s => ({ ...s, allocation: equalAllocation }));
      onStocksUpdate(rebalancedStocks);
      
      // Portfolio metrics update automatically via useEffect
    } else {
      onStocksUpdate([]);
    }
  };

  const acceptRecommendation = (recommendation: PortfolioRecommendation, index: number) => {
    setSelectedPortfolioIndex(index);
    setOriginalRecommendation(recommendation);
    onStocksUpdate(recommendation.allocations);
    setHasSelectedPortfolio(true);
    
    // Initialize allocation tracking
    const total = recommendation.allocations.reduce((sum, stock) => sum + stock.allocation, 0);
    setTotalAllocation(total);
    setIsValidAllocation(Math.abs(total - 100) < 0.1);
  };

  // Enhanced allocation update with validation and real-time updates
  const updateAllocation = (symbol: string, newAllocation: number) => {
    const updatedStocks = selectedStocks.map(stock => 
      stock.symbol === symbol ? { ...stock, allocation: newAllocation } : stock
    );
    
    const total = updatedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
    setTotalAllocation(total);
    setIsValidAllocation(Math.abs(total - 100) < 0.1);
    
    onStocksUpdate(updatedStocks);
    
    // Portfolio metrics update automatically via useEffect
  };

  // NEW: Auto-normalization feature with real-time updates
  const normalizeWeights = () => {
    const total = selectedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
    const normalizedStocks = selectedStocks.map(stock => ({
      ...stock,
      allocation: (stock.allocation / total) * 100
    }));
    
    onStocksUpdate(normalizedStocks);
    setTotalAllocation(100);
    setIsValidAllocation(true);
    
    // Trigger real-time metrics update
    setTimeout(() => {
      calculateRealTimeMetrics();
      validatePortfolio();
    }, 100);
  };

  // NEW: Reset to original function
  const resetToOriginal = () => {
    if (originalRecommendation) {
      onStocksUpdate(originalRecommendation.allocations);
      setTotalAllocation(100);
      setIsValidAllocation(true);
    }
  };

  // REMOVED: getPrimarySectors function - no longer needed since we removed primary sectors display

  const handleNext = () => {
    // Prevent navigation if allocation is invalid
    if (totalAllocation > 100 || totalAllocation < 85) {
      return; // Do nothing - button should already be disabled
    }
    
    if (activeTab === 'mini-lesson') {
      // From mini-lesson, go to recommendations
      setActiveTab('recommendations');
    } else if (activeTab === 'recommendations') {
      // From recommendations, go to visual charts
      setActiveTab('full-customization');
    } else {
      // From other tabs, call the parent onNext
      onNext();
    }
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

  // NEW: Real-time portfolio metrics calculation
  const calculateRealTimeMetrics = useCallback(async () => {
    if (selectedStocks.length === 0) return;
    
    setIsLoadingMetrics(true);
    setError(null);
    
    try {
      const response = await fetch('/api/portfolio/calculate-metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allocations: selectedStocks,
          riskProfile: riskProfile
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setPortfolioMetrics({
          expectedReturn: data.expectedReturn,
          risk: data.risk,
          diversificationScore: data.diversificationScore,
          sharpeRatio: 0
        });
        
        // Update validation state
        setPortfolioValidation({
          isValid: data.validation.isValid,
          totalAllocation: data.totalAllocation,
          stockCount: data.stockCount,
          warnings: data.validation.warnings,
          canProceed: data.validation.canProceed
        });
      } else {
        throw new Error('Failed to calculate metrics');
      }
    } catch (error) {
      console.error('Real-time calculation failed:', error);
      setError('Failed to calculate portfolio metrics. Using fallback calculations.');
      
      // Fallback to calculated metrics
      calculateFallbackMetrics();
    } finally {
      setIsLoadingMetrics(false);
    }
  }, [selectedStocks, riskProfile]);

  // NEW: Fallback calculation when API fails
  const calculateFallbackMetrics = useCallback(() => {
    if (selectedStocks.length === 0) return;
    
    const totalAllocation = selectedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
    
    // Use historical averages for individual stocks
    const avgReturn = selectedStocks.reduce((sum, stock) => {
      const stockReturn = getStockHistoricalReturn(stock.symbol) || 0.12;
      return sum + (stock.allocation / 100) * stockReturn;
    }, 0);
    
    const avgRisk = selectedStocks.reduce((sum, stock) => {
      const stockRisk = getStockHistoricalRisk(stock.symbol) || 0.20;
      return sum + (stock.allocation / 100) * stockRisk;
    }, 0);
    
    const diversificationScore = Math.min(100, selectedStocks.length * 20);
    
    setPortfolioMetrics({
      expectedReturn: avgReturn,
      risk: avgRisk,
      diversificationScore: diversificationScore,
      sharpeRatio: 0
    });
  }, [selectedStocks]);

  // NEW: Helper functions for fallback calculations
  const getStockHistoricalReturn = (symbol: string): number => {
    // Simplified historical returns for fallback
    const returns: Record<string, number> = {
      'AAPL': 0.15, 'MSFT': 0.18, 'GOOGL': 0.16, 'AMZN': 0.20,
      'NVDA': 0.35, 'TSLA': 0.25, 'JNJ': 0.08, 'PG': 0.09,
      'KO': 0.07, 'VZ': 0.06, 'AMD': 0.30, 'META': 0.22
    };
    return returns[symbol] || 0.12;
  };

  const getStockHistoricalRisk = (symbol: string): number => {
    // Simplified historical risk for fallback
    const risks: Record<string, number> = {
      'AAPL': 0.25, 'MSFT': 0.22, 'GOOGL': 0.24, 'AMZN': 0.30,
      'NVDA': 0.35, 'TSLA': 0.40, 'JNJ': 0.15, 'PG': 0.18,
      'KO': 0.16, 'VZ': 0.20, 'AMD': 0.42, 'META': 0.28
    };
    return risks[symbol] || 0.20;
  };

  // NEW: Real-time portfolio validation
  const validatePortfolio = useCallback(() => {
    const totalAllocation = selectedStocks.reduce((sum, stock) => sum + stock.allocation, 0);
    const stockCount = selectedStocks.length;
    
    const warnings: string[] = [];
    
    // Check allocation
    if (Math.abs(totalAllocation - 100) > 0.01) {
      warnings.push(`Total allocation is ${totalAllocation.toFixed(1)}%. Must equal 100%.`);
    }
    
    // Check minimum stock count
    if (stockCount < 3) {
      warnings.push(`Portfolio must have at least 3 stocks. Currently: ${stockCount}`);
    }
    
    // Check individual allocations
    selectedStocks.forEach(stock => {
      if (stock.allocation < 5) {
        warnings.push(`${stock.symbol} allocation (${stock.allocation.toFixed(1)}%) is very low`);
      }
      if (stock.allocation > 50) {
        warnings.push(`${stock.symbol} allocation (${stock.allocation.toFixed(1)}%) is very high`);
      }
    });
    
    const isValid = totalAllocation === 100 && stockCount >= 3 && warnings.length === 0;
    const canProceed = stockCount >= 3; // Can proceed with 3+ stocks even if allocation isn't perfect
    
    setPortfolioValidation({
      isValid,
      totalAllocation,
      stockCount,
      warnings,
      canProceed
    });
  }, [selectedStocks]);

  // NEW: Apply changes function
  const applyChanges = () => {
    if (portfolioValidation.isValid) {
      setSuccessMessage('Portfolio changes applied successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  // NEW: Generate dynamic portfolios using advanced optimization
  const generateDynamicPortfolios = async () => {
    setIsLoadingDynamic(true);
    setError(null);
    
    try {
      // Prepare optimization parameters
      const params = new URLSearchParams({
        risk_profile: riskProfile,
        target_return: optimizationParams.targetReturn.toString(),
        max_risk: optimizationParams.maxRisk.toString(),
        num_portfolios: '5'
      });
      
      const response = await fetch(`/api/portfolio/recommendations/dynamic?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Transform backend data to frontend format
        const transformedPortfolios = data.map((portfolio: {
          portfolio?: PortfolioAllocation[];
          expectedReturn?: number;
          risk?: number;
          diversificationScore?: number;
          strategy?: string;
          rank?: number;
          score?: number;
        }, index: number) => ({
          name: `Dynamic Portfolio ${index + 1}`,
          description: `AI-optimized portfolio using ${portfolio.strategy || 'advanced algorithms'}`,
          allocations: portfolio.portfolio || [],
          expectedReturn: portfolio.expectedReturn || 0.15,
          risk: portfolio.risk || 0.20,
          diversificationScore: portfolio.diversificationScore || 75,
          strategy: portfolio.strategy || 'Optimization',
          rank: portfolio.rank || index + 1,
          score: portfolio.score || 0
        }));
        
        setDynamicPortfolios(transformedPortfolios);
        setSuccessMessage(`Generated ${transformedPortfolios.length} dynamic portfolios!`);
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        throw new Error('Failed to generate dynamic portfolios');
      }
    } catch (error) {
      console.error('Error generating dynamic portfolios:', error);
      setError('Failed to generate dynamic portfolios. Using fallback recommendations.');
      
      // Fallback to static recommendations
      const fallbackPortfolios = generateRecommendations();
      setDynamicPortfolios(fallbackPortfolios);
    } finally {
      setIsLoadingDynamic(false);
    }
  };

  // NEW: Portfolio optimization analysis
  const analyzePortfolioOptimization = async () => {
    if (selectedStocks.length === 0) {
      setError('Please select a portfolio first to analyze optimization');
      return;
    }
    
    try {
      const response = await fetch('/api/portfolio/optimize/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_portfolio: selectedStocks,
          risk_profile: riskProfile,
          target_return: optimizationParams.targetReturn,
          max_risk: optimizationParams.maxRisk
        })
      });
      
      if (response.ok) {
        const analysis = await response.json();
        console.log('Portfolio optimization analysis:', analysis);
        
        // You can display this analysis in the UI
        setSuccessMessage('Portfolio optimization analysis completed!');
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        throw new Error('Failed to analyze portfolio optimization');
      }
    } catch (error) {
      console.error('Error analyzing portfolio optimization:', error);
      setError('Failed to analyze portfolio optimization');
    }
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
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "mini-lesson" | "recommendations" | "full-customization" | "dynamic-generation")}>
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
                <BarChart3 className="h-4 w-4" />
                Visual Charts
              </TabsTrigger>
            </TabsList>

            {/* Mini-Lesson Tab - Enhanced with Asset Selection */}
            <TabsContent value="mini-lesson" className="space-y-6">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
                <div className="flex items-center gap-3 mb-4">
                  <Lightbulb className="h-6 w-6 text-blue-600" />
                  <h3 className="text-xl font-semibold text-blue-900">How Risk and Return Trade Off</h3>
                </div>
                <p className="text-blue-800 mb-4">
                  Learn how combining different assets can reduce risk while maintaining returns. 
                  Choose from educational asset pairs to explore portfolio theory and diversification benefits.
                  Each pair represents different sectors and investment themes for comprehensive learning.
                </p>
                
                {/* Asset Pair Selection */}
                {availableAssetPairs.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-lg font-medium text-blue-900">Select Asset Pair for Analysis</h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => loadAssetPairs()}
                        className="text-xs px-3 py-1 h-8"
                      >
                        <RefreshCw className="h-3 w-3 mr-1" />
                        New Pairs
                      </Button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {availableAssetPairs.map((pair) => (
                        <Tooltip key={pair.pair_id}>
                          <TooltipTrigger asChild>
                            <Button
                              variant={selectedPairId === pair.pair_id ? "default" : "outline"}
                              className={`p-3 h-auto min-h-[90px] max-h-[120px] text-left w-full flex-shrink-0 group relative ${selectedPairId === pair.pair_id ? 'bg-blue-600 text-white' : 'bg-white text-blue-900 border-blue-200 hover:border-blue-300'}`}
                              onClick={() => {
                                setSelectedPairId(pair.pair_id);
                                if (pair.pair_id !== 'random') {
                                  setCurrentPair({ ticker1: pair.ticker1, ticker2: pair.ticker2 });
                                }
                              }}
                            >
                              <div className="flex flex-col w-full h-full justify-center overflow-hidden">
                                <div className="font-medium text-xs leading-tight mb-2 text-ellipsis overflow-hidden whitespace-nowrap">
                                  {pair.description}
                                </div>
                                <div className="text-xs opacity-80 leading-tight text-ellipsis overflow-hidden whitespace-nowrap">
                                  {pair.educational_focus}
                                </div>
                              </div>
                              
                              {/* Hover indicator */}
                              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <div className="w-2 h-2 bg-current rounded-full opacity-60"></div>
                              </div>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-sm p-4 bg-slate-900 text-white border-0 shadow-xl rounded-lg">
                            <div className="space-y-3">
                              <div className="font-semibold text-base border-b border-slate-700 pb-2 text-center">
                                Asset Pair Analysis
                              </div>
                              
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-sm font-medium text-blue-300">{pair.ticker1}</span>
                                  <span className="text-xs opacity-75">vs</span>
                                  <span className="text-sm font-medium text-amber-300">{pair.ticker2}</span>
                                </div>
                                
                                <div className="text-xs opacity-90 text-center">
                                  {pair.description}
                                </div>
                              </div>
                              
                              <div className="bg-slate-800 rounded p-2">
                                <div className="text-xs font-medium text-slate-300 mb-1">Educational Focus:</div>
                                <div className="text-sm opacity-90">
                                  {pair.educational_focus}
                                </div>
                              </div>
                              
                              <div className="text-xs opacity-75 pt-2 border-t border-slate-700 space-y-1">
                                <div className="flex justify-between">
                                  <span className="font-medium">{pair.ticker1}:</span>
                                  <span className="text-right max-w-[120px] truncate">{pair.name1}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="font-medium">{pair.ticker2}:</span>
                                  <span className="text-right max-w-[120px] truncate">{pair.name2}</span>
                                </div>
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
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
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                        </div>
                      </CardContent>
                    </Card>

                    {/* Educational Callouts */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Expected Return:</strong> The average yearly growth rate of your investment 
                          based on historical performance data.
                        </AlertDescription>
                      </Alert>
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Risk (Volatility):</strong> Measures how much returns vary from the average. 
                          Higher values mean more uncertainty and potential for larger price swings.
                        </AlertDescription>
                      </Alert>
                    </div>

                    {/* Data Source Indicator */}
                    <Alert className="mt-4">
                      <Database className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Data Source:</strong> Real market data from Yahoo Finance (monthly returns, annualized). All calculations are based on historical performance and are for educational demonstration purposes only.
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
                <h3 className="text-xl font-semibold mb-2">Portfolio Recommendations</h3>
                <p className="text-muted-foreground">
                  Personalized recommendations optimized for your {getRiskProfileDisplay().toLowerCase()} risk profile using live market data
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
                  <Card 
                    key={index} 
                    className={`relative overflow-hidden transition-all duration-200 cursor-pointer ${
                      selectedPortfolioIndex === index 
                        ? 'ring-2 ring-primary shadow-lg scale-105' 
                        : 'hover:shadow-md'
                    }`}
                    onClick={() => acceptRecommendation(recommendation, index)}
                  >
                    {/* Selection indicator */}
                    {selectedPortfolioIndex === index && (
                      <div className="absolute top-2 right-2 z-10">
                        <Badge variant="default" className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Selected
                        </Badge>
                      </div>
                    )}
                    
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

                      {/* Enhanced portfolio information */}
                      <div className="mt-4 space-y-3">
                        <div className="flex justify-between text-sm">
                          <span>Total Allocation:</span>
                          <span className="font-medium">100%</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span>Number of Assets:</span>
                          <span className="font-medium">{recommendation.allocations.length}</span>
                        </div>
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
                        onClick={(e) => {
                          e.stopPropagation();
                          acceptRecommendation(recommendation, index);
                        }}
                        className="w-full"
                        variant={selectedPortfolioIndex === index ? "default" : "outline"}
                      >
                        {selectedPortfolioIndex === index ? (
                          <>
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Portfolio Selected
                          </>
                        ) : (
                          <>
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Use This Portfolio
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
              )}

              {/* Advanced Options Button - Small and at the bottom */}
              {!hasSelectedPortfolio && (
                <div className="text-center mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setActiveTab('dynamic-generation')}
                    className="flex items-center gap-2 mx-auto"
                  >
                    <Zap className="h-4 w-4" />
                    Advanced Options
                  </Button>
                  <p className="text-xs text-muted-foreground mt-2">
                    Generate custom portfolios using AI optimization algorithms
                  </p>
                </div>
              )}

              {/* Portfolio Customization Section - Only show after selection */}
              {hasSelectedPortfolio && selectedStocks.length > 0 && (
              <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Customize Your Portfolio</CardTitle>
                    <p className="text-muted-foreground">
                      Modify the selected portfolio by adding or removing stocks and adjusting allocations
                    </p>
                </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Stock Search */}
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
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

                      {/* Search Results */}
                      {searchResults.length > 0 && (
                        <div className="space-y-2">
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
                                disabled={selectedStocks.some(s => s.symbol === stock.symbol)}
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
                        <h4 className="text-lg font-medium">Selected Assets ({selectedStocks.length}/5)</h4>
                        <div className="text-sm text-muted-foreground">
                          Minimum 3 recommended
                        </div>
                      </div>

                      {/* Portfolio Overview - Moved here, below Selected Assets */}
                      <div className={`border rounded-lg p-4 ${totalAllocation > 100 ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-2xl font-bold text-primary">{selectedStocks.length}</div>
                            <div className="text-sm text-muted-foreground">Stocks</div>
                          </div>
                          <div>
                            <div className={`text-2xl font-bold ${totalAllocation > 100 ? 'text-red-600' : 'text-green-600'}`}>
                              {totalAllocation.toFixed(1)}%
                            </div>
                            <div className="text-sm text-muted-foreground">Total Allocation</div>
                          </div>
                          <div>
                            <div className={`text-2xl font-bold ${totalAllocation > 100 ? 'text-red-600' : 'text-green-600'}`}>
                              {totalAllocation > 100 ? '✗' : '✓'}
                            </div>
                            <div className="text-sm text-muted-foreground">Status</div>
                          </div>
                        </div>
                        <div className={`mt-3 text-center text-sm ${totalAllocation > 100 ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
                          Total Allocation: {totalAllocation.toFixed(1)}%
                        </div>
                      </div>

                      {/* Allocation Outcome Warnings - Only in Selected Assets section */}
                      {(() => {
                        if (totalAllocation > 100) {
                          return (
                            <div className="mt-3 bg-red-100 border border-red-300 rounded-lg p-3">
                              <div className="flex items-center gap-2 text-red-800">
                                <AlertTriangle className="h-4 w-4" />
                                <span className="text-sm font-medium">Over-Allocation Warning</span>
                              </div>
                              <p className="text-sm text-red-700 mt-1">
                                Oops—your allocation exceeds 100%. Adjust the weights so your portfolio stays balanced.
                              </p>
                            </div>
                          );
                        } else if (totalAllocation === 0) {
                          return (
                            <div className="mt-3 bg-blue-100 border border-blue-300 rounded-lg p-3">
                              <div className="flex items-center gap-2 text-blue-800">
                                <Info className="h-4 w-4" />
                                <span className="text-sm font-medium">No Allocations Yet</span>
                              </div>
                              <p className="text-sm text-blue-700 mt-1">
                                No allocations yet. Assign your weights so they sum to 100% before moving on.
                              </p>
                            </div>
                          );
                        } else if (totalAllocation < 85) {
                          return (
                            <div className="mt-3 bg-red-100 border border-red-300 rounded-lg p-3">
                              <div className="flex items-center gap-2 text-red-800">
                                <AlertTriangle className="h-4 w-4" />
                                <span className="text-sm font-medium">Insufficient Allocation</span>
                              </div>
                              <p className="text-sm text-red-700 mt-1">
                                You need at least 85% allocation to proceed. Currently at {totalAllocation.toFixed(1)}%. 
                                Increase your allocations or add more assets to continue.
                              </p>
                            </div>
                          );
                        } else if (totalAllocation >= 85 && totalAllocation < 90) {
                          // Check if this is a strategic cash allocation
                          const cashPercentage = 100 - totalAllocation;
                          if (cashPercentage >= 10 && cashPercentage <= 15) {
                            // Strategic cash allocation - show encouraging message with random text
                            const randomTexts = [
                              `Great job—you're confidently deployed ${totalAllocation.toFixed(1)}% of your portfolio. Keeping ${cashPercentage.toFixed(1)}% in cash gives you flexibility for opportunities or unexpected needs.`,
                              `Solid allocation! With ${totalAllocation.toFixed(1)}% invested and ${cashPercentage.toFixed(1)}% in cash, you're well-positioned to act fast on opportunities while staying balanced.`,
                              `You're nearly fully allocated. Reserving ${cashPercentage.toFixed(1)}% in cash means you're ready to seize chances when they arise, without overextending your investments.`
                            ];
                            const randomIndex = Math.floor(Math.random() * randomTexts.length);
                            
                            return (
                              <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                                <div className="flex items-center gap-2 text-emerald-800">
                                  <CheckCircle className="h-4 w-4" />
                                  <span className="text-sm font-medium">Smart Allocation Strategy!</span>
                                </div>
                                <p className="text-sm text-emerald-700 mt-1">
                                  {randomTexts[randomIndex]}
                                </p>
                              </div>
                            );
                          } else {
                            // Regular under-allocation notice
                            return (
                              <div className="mt-3 bg-amber-100 border border-amber-300 rounded-lg p-3">
                                <div className="flex items-center gap-2 text-amber-800">
                                  <AlertTriangle className="h-4 w-4" />
                                  <span className="text-sm font-medium">Under-Allocation Notice</span>
                                </div>
                                <p className="text-sm text-amber-700 mt-1">
                                  Heads-up: your allocations don't sum to 100%. You may want to allocate remaining funds or keep cash deliberately.
                                </p>
                              </div>
                            );
                          }
                        } else if (totalAllocation >= 90 && totalAllocation < 100) {
                          // For allocations 90-99%, always show encouraging message since user can proceed
                          const cashPercentage = 100 - totalAllocation;
                          const randomTexts = [
                            `Great job—you're confidently deployed ${totalAllocation.toFixed(1)}% of your portfolio. Keeping ${cashPercentage.toFixed(1)}% in cash gives you flexibility for opportunities or unexpected needs.`,
                            `Solid allocation! With ${totalAllocation.toFixed(1)}% invested and ${cashPercentage.toFixed(1)}% in cash, you're well-positioned to act fast on opportunities while staying balanced.`,
                            `You're nearly fully allocated. Reserving ${cashPercentage.toFixed(1)}% in cash means you're ready to seize chances when they arise, without overextending your investments.`
                          ];
                          const randomIndex = Math.floor(Math.random() * randomTexts.length);
                          
                          return (
                            <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                              <div className="flex items-center gap-2 text-emerald-800">
                                <CheckCircle className="h-4 w-4" />
                                <span className="text-sm font-medium">Smart Allocation Strategy!</span>
                              </div>
                              <p className="text-sm text-emerald-700 mt-1">
                                {randomTexts[randomIndex]}
                              </p>
                            </div>
                          );
                        } else if (Math.abs(totalAllocation - 100) < 0.1) {
                          return (
                            <div className="mt-3 bg-green-100 border border-green-300 rounded-lg p-3">
                              <div className="flex items-center gap-2 text-green-800">
                                <CheckCircle className="h-4 w-4" />
                                <span className="text-sm font-medium">Perfect Allocation!</span>
                              </div>
                              <p className="text-sm text-green-700 mt-1">
                                Great job! Your portfolio is perfectly balanced at 100%. You're ready to proceed.
                              </p>
                            </div>
                          );
                        }
                        return null;
                      })()}
                      

                    </div>

                    {/* Weight Editor Toggle */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="font-medium">Weight Editor</h5>
                        <p className="text-sm text-muted-foreground">
                          Manually adjust stock weights or use auto-normalization
                        </p>
                      </div>
                      <Switch
                        checked={showWeightEditor}
                        onCheckedChange={setShowWeightEditor}
                      />
                    </div>

                    {/* Weight Editor */}
                    {showWeightEditor && (
                      <div className="space-y-3">
                        {selectedStocks.map((stock, index) => (
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
                                    // Allow empty input
                                    updateAllocation(stock.symbol, 0);
                                  } else {
                                    const numValue = parseFloat(value);
                                    if (!isNaN(numValue)) {
                                      updateAllocation(stock.symbol, numValue);
                                    }
                                  }
                                }}
                                onBlur={(e) => {
                                  // When input loses focus, ensure we have a valid number
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
                        
                        {/* Allocation Warning */}
                        {selectedStocks.some(stock => stock.allocation > 100) && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                            <div className="flex items-center gap-2 text-red-800">
                              <AlertTriangle className="h-4 w-4" />
                              <span className="text-sm font-medium">Allocation Warning</span>
                            </div>
                            <p className="text-sm text-red-700 mt-1">
                              Some stocks have allocations exceeding 100%. Please adjust weights to ensure total allocation equals 100%.
                            </p>
                          </div>
                        )}
                        
                        <div className="flex justify-end">
                          <Button
                            onClick={normalizeWeights}
                            variant="outline"
                            size="sm"
                          >
                            Auto-Normalize Weights
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Portfolio Validation */}
                    <div className="space-y-3">
                      <h5 className="font-medium">Portfolio Validation</h5>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>Minimum 3 stocks</span>
                          <span className={selectedStocks.length >= 3 ? 'text-green-600' : 'text-red-600'}>
                            {selectedStocks.length >= 3 ? '✓' : '✗'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span>Total allocation = 100%</span>
                          <span className={Math.abs(totalAllocation - 100) < 0.1 ? 'text-green-600' : 'text-red-600'}>
                            {Math.abs(totalAllocation - 100) < 0.1 ? '✓' : '✗'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Portfolio Metrics Section - Enhanced UX Design */}
              {hasSelectedPortfolio && selectedStocks.length > 0 && portfolioMetrics && (
                <Card className="bg-gradient-to-br from-slate-50 to-blue-50 border-0 shadow-lg">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-xl flex items-center gap-3 text-slate-800">
                      <BarChart3 className="h-6 w-6 text-blue-600" />
                      Your Portfolio Performance
                    </CardTitle>
                    <p className="text-slate-600">
                      Real-time metrics based on your current allocation and market data
                    </p>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {/* Expected Return */}
                      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 p-6 border border-emerald-200">
                        <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-200 rounded-full -translate-y-10 translate-x-10 opacity-20"></div>
                        <div className="relative z-10">
                          <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="h-5 w-5 text-emerald-600" />
                            <span className="text-sm font-medium text-emerald-700">Expected Return</span>
                          </div>
                          <div className="text-3xl font-bold text-emerald-800 mb-1">
                            {(portfolioMetrics.expectedReturn * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-emerald-600">
                            Annualized projection
                          </div>
                        </div>
                      </div>

                      {/* Risk Level */}
                      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-50 to-amber-100 p-6 border border-amber-200">
                        <div className="absolute top-0 right-0 w-20 h-20 bg-amber-200 rounded-full -translate-y-10 translate-x-10 opacity-20"></div>
                        <div className="relative z-10">
                          <div className="flex items-center gap-2 mb-2">
                            <Shield className="h-5 w-5 text-amber-600" />
                            <span className="text-sm font-medium text-amber-700">Risk Level</span>
                          </div>
                          <div className="text-3xl font-bold text-amber-800 mb-1">
                            {(portfolioMetrics.risk * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-amber-600">
                            Volatility measure
                          </div>
                        </div>
                      </div>

                      {/* Diversification Score */}
                      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-violet-50 to-violet-100 p-6 border border-violet-200">
                        <div className="absolute top-0 right-0 w-20 h-20 bg-violet-200 rounded-full -translate-y-10 translate-x-10 opacity-20"></div>
                        <div className="relative z-10">
                          <div className="flex items-center gap-2 mb-2">
                            <PieChart className="h-5 w-5 text-violet-600" />
                            <span className="text-sm font-medium text-violet-700">Diversification</span>
                          </div>
                          <div className="text-3xl font-bold text-violet-800 mb-1">
                            {portfolioMetrics.diversificationScore}%
                          </div>
                          <div className="text-xs text-violet-600">
                            Portfolio balance
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Continue Button */}
                    <div className="mt-6 text-center">
                      <Button 
                        onClick={handleNext}
                        size="lg"
                        disabled={totalAllocation < 85}
                        className={`px-8 py-3 rounded-xl shadow-lg transition-all duration-200 ${
                          totalAllocation < 85 
                            ? 'bg-gray-400 text-gray-600 cursor-not-allowed shadow-none' 
                            : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white hover:shadow-xl'
                        }`}
                      >
                        {totalAllocation > 100 ? (
                          <>
                            <AlertTriangle className="mr-2 h-5 w-5" />
                            Fix Allocation Before Continuing
                          </>
                        ) : totalAllocation === 0 ? (
                          <>
                            <Info className="mr-2 h-5 w-5" />
                            Set Allocations to Continue
                          </>
                        ) : totalAllocation < 85 ? (
                          <>
                            <AlertTriangle className="mr-2 h-5 w-5" />
                            Need 85%+ Allocation to Continue
                          </>
                        ) : totalAllocation >= 85 && totalAllocation < 90 ? (
                          <>
                            <Lightbulb className="mr-2 h-5 w-5" />
                            Proceed with {totalAllocation.toFixed(1)}% Allocation
                          </>
                        ) : totalAllocation >= 90 && totalAllocation < 100 ? (
                          <>
                            <Lightbulb className="mr-2 h-5 w-5" />
                            Proceed with {totalAllocation.toFixed(1)}% Allocation
                          </>
                        ) : (
                          <>
                            Continue to Visual Charts
                            <ArrowRight className="ml-2 h-5 w-5" />
                          </>
                        )}
                      </Button>
                      

                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Visual Charts Tab */}
            <TabsContent value="full-customization" className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">Visual Charts & Analysis</h3>
                <p className="text-muted-foreground">
                  Advanced portfolio visualization with efficient frontier analysis and interactive charts
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

            {/* Dynamic Generation Tab - Hidden by default, accessible via Advanced Options */}
            {activeTab === 'dynamic-generation' && (
              <TabsContent value="dynamic-generation" className="space-y-6">
                <div className="text-center mb-6">
                  <h3 className="text-xl font-semibold mb-2">Dynamic Portfolio Generation</h3>
                  <p className="text-muted-foreground">
                    Generate custom portfolios based on your risk profile and desired return/risk trade-offs using advanced optimization algorithms.
                  </p>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Optimization Parameters</CardTitle>
                    <p className="text-muted-foreground">
                      Adjust these parameters to generate portfolios that meet your investment goals.
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="targetReturn" className="block text-sm font-medium text-gray-700 mb-1">Target Expected Return (%)</label>
                        <Slider
                          id="targetReturn"
                          value={[optimizationParams.targetReturn * 100]}
                          onValueChange={(value) => setOptimizationParams(prev => ({ ...prev, targetReturn: value[0] / 100 }))}
                          min={0}
                          max={30}
                          step={0.1}
                          className="w-full"
                        />
                        <span className="text-sm text-gray-600 mt-1">
                          {optimizationParams.targetReturn * 100}%
                        </span>
                      </div>
                      <div>
                        <label htmlFor="maxRisk" className="block text-sm font-medium text-gray-700 mb-1">Maximum Risk (%)</label>
                        <Slider
                          id="maxRisk"
                          value={[optimizationParams.maxRisk * 100]}
                          onValueChange={(value) => setOptimizationParams(prev => ({ ...prev, maxRisk: value[0] / 100 }))}
                          min={0}
                          max={40}
                          step={0.1}
                          className="w-full"
                        />
                        <span className="text-sm text-gray-600 mt-1">
                          {optimizationParams.maxRisk * 100}%
                        </span>
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Optimization Strategy</label>
                      <select
                        value={selectedOptimizationStrategy}
                        onChange={(e) => setSelectedOptimizationStrategy(e.target.value)}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                      >
                        <option value="all">Maximize Diversification (All Assets)</option>
                        <option value="risk">Minimize Risk (All Assets)</option>
                        <option value="return">Maximize Return (All Assets)</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Button
                        onClick={() => generateDynamicPortfolios()}
                        disabled={isLoadingDynamic}
                        className="w-full"
                      >
                        {isLoadingDynamic ? (
                          <>
                            <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Generating Portfolios...
                          </>
                        ) : (
                          <>
                            Generate Dynamic Portfolios
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </>
                        )}
                      </Button>
                      
                      <Button
                        onClick={() => analyzePortfolioOptimization()}
                        disabled={selectedStocks.length === 0}
                        variant="outline"
                        className="w-full"
                      >
                        <BarChart3 className="mr-2 h-4 w-4" />
                        Analyze Optimization
                      </Button>
                    </div>

                    {/* Dynamic Portfolios Display */}
                    {isLoadingDynamic ? (
                      <div className="text-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                        <p className="mt-2 text-muted-foreground">Generating dynamic portfolios...</p>
                      </div>
                    ) : dynamicPortfolios.length > 0 ? (
                      <div className="mt-6">
                        <h4 className="text-lg font-medium mb-4">Generated Dynamic Portfolios</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          {dynamicPortfolios.map((portfolio, index) => (
                            <Card
                              key={index}
                              className={`relative overflow-hidden transition-all duration-200 cursor-pointer ${
                                selectedPortfolioIndex === index
                                  ? 'ring-2 ring-primary shadow-lg scale-105'
                                  : 'hover:shadow-md'
                              }`}
                              onClick={() => acceptRecommendation(portfolio, index)}
                            >
                              {/* Selection indicator */}
                              {selectedPortfolioIndex === index && (
                                <div className="absolute top-2 right-2 z-10">
                                  <Badge variant="default" className="bg-green-600">
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    Selected
                                  </Badge>
                                </div>
                              )}
                              
                              <CardHeader className="pb-4">
                                <div className="flex items-center justify-between">
                                  <CardTitle className="text-lg">{portfolio.name}</CardTitle>
                                  <Badge variant={index === 0 ? "default" : "secondary"}>
                                    {index === 0 ? "Top Pick" : "Alternative " + (index + 1)}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">{portfolio.description}</p>
                              </CardHeader>
                              <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <div className="text-muted-foreground">Expected Return</div>
                                    <div className="font-semibold text-green-600">
                                      {(portfolio.expectedReturn * 100).toFixed(1)}%
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-muted-foreground">Risk Level</div>
                                    <div className="font-semibold text-orange-600">
                                      {(portfolio.risk * 100).toFixed(1)}%
                                    </div>
                                  </div>
                                </div>
                                
                                <div>
                                  <div className="flex justify-between text-sm mb-1">
                                    <span>Diversification Score</span>
                                    <span>{portfolio.diversificationScore}%</span>
                                  </div>
                                  <Progress value={portfolio.diversificationScore} className="h-2" />
                                </div>

                                {/* Enhanced portfolio information */}
                                <div className="mt-4 space-y-3">
                                  <div className="flex justify-between text-sm">
                                    <span>Total Allocation:</span>
                                    <span className="font-medium">100%</span>
                                  </div>
                                  <div className="flex justify-between text-sm">
                                    <span>Number of Assets:</span>
                                    <span className="font-medium">{portfolio.allocations.length}</span>
                                  </div>
                                </div>

                                <div className="space-y-2">
                                  <div className="text-sm font-medium">Allocations:</div>
                                  {portfolio.allocations.slice(0, 3).map((allocation, idx) => (
                                    <div key={idx} className="flex justify-between text-xs">
                                      <span>{allocation.symbol}</span>
                                      <span>{allocation.allocation}%</span>
                                    </div>
                                  ))}
                                  {portfolio.allocations.length > 3 && (
                                    <div className="text-xs text-muted-foreground">
                                      +{portfolio.allocations.length - 3} more stocks
                                    </div>
                                  )}
                                </div>

                                <Button 
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    acceptRecommendation(portfolio, index);
                                  }}
                                  className="w-full"
                                  variant={selectedPortfolioIndex === index ? "default" : "outline"}
                                >
                                  {selectedPortfolioIndex === index ? (
                                    <>
                                      <CheckCircle className="mr-2 h-4 w-4" />
                                      Portfolio Selected
                                    </>
                                  ) : (
                                    <>
                                      <CheckCircle className="mr-2 h-4 w-4" />
                                      Use This Portfolio
                                    </>
                                  )}
                                </Button>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>

          {/* Success Message Display */}
          {successMessage && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 text-green-800">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">{successMessage}</span>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between pt-6">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={handleNext}
              disabled={!portfolioValidation.canProceed}
              className={portfolioValidation.canProceed ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-300 cursor-not-allowed'}
            >
              {portfolioValidation.canProceed ? (
                <>
                  Continue
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              ) : (
                <>
                  Need 3+ Stocks
                  <AlertTriangle className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>

        </CardContent>
      </Card>
    </div>
  );
};