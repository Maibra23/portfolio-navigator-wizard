/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import { Portfolio3PartVisualization } from './Portfolio3PartVisualization';
import { VisualizationErrorBoundary } from './VisualizationErrorBoundary';

interface StockSelectionProps {
  onNext: () => void;
  onPrev: () => void;
  onStocksUpdate: (stocks: PortfolioAllocation[]) => void;
  onMetricsUpdate?: (metrics: PortfolioMetrics | null) => void;
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
  strategy?: string;
  rank?: number;
  score?: number;
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
  onMetricsUpdate,
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
  
  // NEW: Pure Strategy Portfolio Generation State
  const [strategyPortfolios, setStrategyPortfolios] = useState<PortfolioRecommendation[]>([]);
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('diversification');
  
  // Generation limit tracking per strategy (max 2 generations per strategy)
  const [generationCounts, setGenerationCounts] = useState<Record<string, number>>({
    diversification: 0,
    risk: 0,
    return: 0
  });
  
  // Store all generated portfolios per strategy (to show them even after limit reached)
  const [allGeneratedPortfolios, setAllGeneratedPortfolios] = useState<Record<string, PortfolioRecommendation[]>>({
    diversification: [],
    risk: [],
    return: []
  });
  
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
  const [hasUserModified, setHasUserModified] = useState<boolean>(false);
  // Added: track original symbols, allocation history snapshots, and last removed original
  const [originalSymbols, setOriginalSymbols] = useState<Set<string>>(new Set());
  const [allocationHistory, setAllocationHistory] = useState<PortfolioAllocation[][]>([]);
  const [historyMarkers, setHistoryMarkers] = useState<("add" | "normalize")[]>([]);
  const [lastRemovedOriginal, setLastRemovedOriginal] = useState<{ symbol: string; allocation: number } | null>(null);
  // Configurable default weight for new additions
  const DEFAULT_ADD_WEIGHT = 5;
  
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
  
  // FIX #1: AbortController for cancelling pending metrics requests
  const [metricsAbortController, setMetricsAbortController] = useState<AbortController | null>(null);

  // Ticker warming function
  const warmTickers = useCallback(async (tickers: string[]) => {
    if (!tickers || tickers.length === 0) return;
    
    try {
      const uniqueTickers = Array.from(new Set(tickers.map(t => t.toUpperCase().trim()).filter(Boolean)));
      if (uniqueTickers.length === 0) return;

      const response = await fetch('/api/portfolio/warm-tickers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: uniqueTickers }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`🔥 Warmed ${result.warmed}/${result.total} tickers`);
      }
    } catch (error) {
      console.debug('Ticker warming failed (non-critical):', error);
    }
  }, []);

  // Debounced ticker warming ref
  const warmTickersTimeoutRef = useRef<number | null>(null);

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

  // Track last loaded risk profile and recommendations to prevent unnecessary refetches
  const lastLoadedRiskProfileRef = useRef<string | null>(null);
  const loadedRecommendationsRef = useRef<PortfolioRecommendation[]>([]);
  // Track customized portfolio state to preserve user modifications
  const customizedPortfolioRef = useRef<{
    selectedIndex: number | null;
    customizedStocks: PortfolioAllocation[];
    hasUserModified: boolean;
  } | null>(null);

  // Load dynamic recommendations from backend
  useEffect(() => {
    // Clear customized portfolio if risk profile changed
    if (lastLoadedRiskProfileRef.current !== null && lastLoadedRiskProfileRef.current !== riskProfile) {
      customizedPortfolioRef.current = null;
    }
    
    // Only fetch if risk profile changed or we don't have recommendations yet
    if (lastLoadedRiskProfileRef.current === riskProfile && loadedRecommendationsRef.current.length > 0) {
      console.log('Skipping refetch - recommendations already loaded for', riskProfile);
      // Restore the previously loaded recommendations
      setDynamicRecommendations(loadedRecommendationsRef.current);
      // Restore customized portfolio state if it exists
      if (customizedPortfolioRef.current && customizedPortfolioRef.current.selectedIndex !== null) {
        setSelectedPortfolioIndex(customizedPortfolioRef.current.selectedIndex);
        setHasUserModified(customizedPortfolioRef.current.hasUserModified);
        // If portfolio was customized, restore the customized stocks and update the recommendation
        if (customizedPortfolioRef.current.hasUserModified && customizedPortfolioRef.current.customizedStocks.length > 0) {
          // Restore customized stocks to parent component
          onStocksUpdate(customizedPortfolioRef.current.customizedStocks);
          
          const updatedRecommendations = [...loadedRecommendationsRef.current];
          const selectedIdx = customizedPortfolioRef.current.selectedIndex;
          if (selectedIdx !== null && selectedIdx < updatedRecommendations.length) {
            // Update the selected recommendation with customized stocks
            updatedRecommendations[selectedIdx] = {
              ...updatedRecommendations[selectedIdx],
              allocations: customizedPortfolioRef.current.customizedStocks,
            };
            setDynamicRecommendations(updatedRecommendations);
          }
        } else if (customizedPortfolioRef.current.selectedIndex !== null) {
          // Portfolio was selected but not customized - restore original recommendation stocks
          const selectedIdx = customizedPortfolioRef.current.selectedIndex;
          if (selectedIdx < loadedRecommendationsRef.current.length) {
            const originalRec = loadedRecommendationsRef.current[selectedIdx];
            onStocksUpdate(originalRec.allocations);
          }
        }
      }
      return;
    }

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
            allocations: (rec.portfolio || []).map(a => ({ ...a, allocation: Math.round((a.allocation || 0) * 100) / 100 })),
            expectedReturn: rec.expectedReturn || 0.1,
            risk: rec.risk || 0.15,
            diversificationScore: rec.diversificationScore || 75
          }));
          
          setDynamicRecommendations(transformedRecommendations);
          loadedRecommendationsRef.current = transformedRecommendations;
          lastLoadedRiskProfileRef.current = riskProfile;

          // Warm all tickers from all 3 recommendations
          const allTickers = new Set<string>();
          transformedRecommendations.forEach((rec: PortfolioRecommendation) => {
            rec.allocations?.forEach((alloc: PortfolioAllocation) => {
              if (alloc.symbol) allTickers.add(alloc.symbol);
            });
          });
          warmTickers(Array.from(allTickers));
        } else {
          console.warn('Failed to load dynamic recommendations, preserving existing ones if available');
          // Don't clear existing recommendations on error - preserve what we have
          if (loadedRecommendationsRef.current.length === 0) {
            // Only clear if we never had any recommendations
            setDynamicRecommendations([]);
            loadedRecommendationsRef.current = [];
          } else {
            // Restore previously loaded recommendations
            setDynamicRecommendations(loadedRecommendationsRef.current);
          }
        }
      } catch (error) {
        console.error('Error loading dynamic recommendations:', error);
        // Don't clear existing recommendations on error - preserve what we have
        if (loadedRecommendationsRef.current.length === 0) {
          // Only clear if we never had any recommendations
          setDynamicRecommendations([]);
          loadedRecommendationsRef.current = [];
        } else {
          // Restore previously loaded recommendations
          setDynamicRecommendations(loadedRecommendationsRef.current);
        }
      } finally {
        setIsLoadingRecommendations(false);
      }
    };

    loadDynamicRecommendations();
  }, [riskProfile]);

  // Track customizations to preserve them when navigating back
  useEffect(() => {
    // Only track if a portfolio is selected and has been customized
    if (selectedPortfolioIndex !== null && hasUserModified && selectedStocks.length > 0) {
      customizedPortfolioRef.current = {
        selectedIndex: selectedPortfolioIndex,
        customizedStocks: [...selectedStocks],
        hasUserModified: true,
      };
      console.log('Tracking customized portfolio:', {
        index: selectedPortfolioIndex,
        stocks: selectedStocks.map(s => s.symbol),
      });
    } else if (selectedPortfolioIndex !== null && !hasUserModified) {
      // Portfolio selected but not customized - still track the selection
      customizedPortfolioRef.current = {
        selectedIndex: selectedPortfolioIndex,
        customizedStocks: [],
        hasUserModified: false,
      };
    }
  }, [selectedStocks, selectedPortfolioIndex, hasUserModified]);

  // Client cache key for mini-lesson asset lists (v5 includes all 11 sectors)
  const MINI_LESSON_CACHE_KEY = 'mini_lesson_assets_v5';

  // FIX #5 & #6: Load available asset pairs with strict validation
  const loadAssetPairs = async (attempt = 1) => {
    try {
      // Try localStorage first
      const cached = typeof window !== 'undefined' ? window.localStorage.getItem(MINI_LESSON_CACHE_KEY) : null;
      if (cached) {
        try {
          const data = JSON.parse(cached);
          if (data && Array.isArray(data.sector_lists)) {
            // Build pairs from cached data with STRICT VALIDATION
            const pairsFromCache: any[] = [];
            const availableSectors = data.sector_lists.filter((list: any) => list.assets && list.assets.length > 0);
            if (availableSectors.length >= 2) {
              for (let i = 0; i < 3; i++) {
                const shuffledSectors = [...availableSectors].sort(() => Math.random() - 0.5);
                const sector1 = shuffledSectors[0];
                const sector2 = shuffledSectors[1];
                if (sector1 && sector2 && sector1.assets.length > 0 && sector2.assets.length > 0) {
                  const asset1 = sector1.assets[Math.floor(Math.random() * sector1.assets.length)];
                  const asset2 = sector2.assets[Math.floor(Math.random() * sector2.assets.length)];
                  
                  // STRICT VALIDATION: Ensure tickers are valid and different
                  if (asset1 && asset2 && 
                      asset1.ticker && asset2.ticker && 
                      asset1.ticker !== asset2.ticker &&
                      asset1.ticker.trim() !== '' && asset2.ticker.trim() !== '') {
                    pairsFromCache.push({
                      pair_id: `pair_cached_${i}_${Date.now()}`,
                      ticker1: asset1.ticker,
                      ticker2: asset2.ticker,
                      name1: asset1.name,
                      name2: asset2.name,
                      description: `${sector1.sector || sector1.sectors?.join(' / ')} vs ${sector2.sector || sector2.sectors?.join(' / ')}`,
                      educational_focus: `${sector1.sector || 'Sector 1'} vs ${sector2.sector || 'Sector 2'}`
                    });
                  }
                }
              }
            }
            if (pairsFromCache.length > 0) {
              setAvailableAssetPairs(pairsFromCache);
              setCurrentPair({ ticker1: pairsFromCache[0].ticker1, ticker2: pairsFromCache[0].ticker2 });
              setSelectedPairId(pairsFromCache[0].pair_id);
              // Continue to refresh cache in background
            }
          }
        } catch (storageError) {
          console.warn('Failed to parse cached mini-lesson assets', storageError);
        }
      }

      // FIX #7: Add retry logic for API connection failures
      let response: Response | null = null;
      for (let retryAttempt = 1; retryAttempt <= 3; retryAttempt++) {
        try {
          response = await fetch('/api/portfolio/mini-lesson/assets');
          if (response.ok) break;
          if (retryAttempt < 3) await new Promise(res => setTimeout(res, retryAttempt * 500));
        } catch (e) {
          console.warn(`Fetch attempt ${retryAttempt} failed:`, e);
          if (retryAttempt < 3) await new Promise(res => setTimeout(res, retryAttempt * 500));
        }
      }
      
      if (response && response.ok) {
        const data = await response.json();
        // Save to localStorage for instant reloads
        if (typeof window !== 'undefined') {
          try {
            window.localStorage.setItem(MINI_LESSON_CACHE_KEY, JSON.stringify(data));
          } catch (storageError) {
            console.warn('Failed to persist mini-lesson cache', storageError);
          }
        }
        
        // FIX #6 + ENHANCEMENT: Create unique sector pairs (no repeating sectors in same cycle)
        const pairs = [];
        
        // Get random assets from different sector lists
        if (data.sector_lists && data.sector_lists.length >= 3) {
          // Create more diverse combinations with UNIQUE sector pairings
          const availableSectors = data.sector_lists.filter(list => list.assets && list.assets.length > 0);
          
          if (availableSectors.length >= 2) {
            // Track used sectors to ensure uniqueness in this cycle
            const usedSectorIndices = new Set<number>();
            
            // Generate 3 random pairs with UNIQUE sectors (no sector repeats in same cycle)
            for (let i = 0; i < 3; i++) {
              // Find two sectors that haven't been used yet
              let sector1 = null;
              let sector2 = null;
              let sector1Index = -1;
              let sector2Index = -1;
              
              // Try to find two unused sectors (max 20 attempts)
              for (let attempt = 0; attempt < 20; attempt++) {
                const randomIndex1 = Math.floor(Math.random() * availableSectors.length);
                const randomIndex2 = Math.floor(Math.random() * availableSectors.length);
                
                // Ensure both sectors are different and not used yet
                if (randomIndex1 !== randomIndex2 && 
                    !usedSectorIndices.has(randomIndex1) && 
                    !usedSectorIndices.has(randomIndex2)) {
                  sector1 = availableSectors[randomIndex1];
                  sector2 = availableSectors[randomIndex2];
                  sector1Index = randomIndex1;
                  sector2Index = randomIndex2;
                  break;
                }
              }
              
              // If we couldn't find unique sectors, allow repeats for this pair
              if (!sector1 || !sector2) {
                const shuffled = [...availableSectors].sort(() => Math.random() - 0.5);
                sector1 = shuffled[0];
                sector2 = shuffled[1];
              }
              
              if (sector1 && sector2 && sector1.assets.length > 0 && sector2.assets.length > 0) {
                // Mark these sectors as used for this cycle
                if (sector1Index !== -1) usedSectorIndices.add(sector1Index);
                if (sector2Index !== -1) usedSectorIndices.add(sector2Index);
                
                // Randomly select assets from each sector
                const asset1 = sector1.assets[Math.floor(Math.random() * sector1.assets.length)];
                const asset2 = sector2.assets[Math.floor(Math.random() * sector2.assets.length)];
                
                // STRICT VALIDATION: Only create pair if both assets are valid
                if (!asset1 || !asset2 || !asset1.ticker || !asset2.ticker || 
                    asset1.ticker === asset2.ticker || 
                    asset1.ticker.trim() === '' || asset2.ticker.trim() === '') {
                  console.warn(`Invalid pair at index ${i}, skipping`);
                  continue;
                }
                
                // Use individual asset sectors for more accurate descriptions
                const asset1Sector = asset1.sector || 'Unknown';
                const asset2Sector = asset2.sector || 'Unknown';
                
                // Create educational themes based on sectors
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
                  'Utilities': 'Utility Services'
                };
                
                const theme1 = themes[asset1Sector] || asset1Sector;
                const theme2 = themes[asset2Sector] || asset2Sector;
                
                // Create shorter, more concise descriptions using individual asset sectors
                const shortSector1 = asset1Sector.length > 12 ? asset1Sector.substring(0, 12) + '...' : asset1Sector;
                const shortSector2 = asset2Sector.length > 12 ? asset2Sector.substring(0, 12) + '...' : asset2Sector;
                
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
              
              // Use individual asset sectors for descriptions
              const techSector = techAsset.sector || 'Technology';
              const healthSector = healthAsset.sector || 'Healthcare';
              
              pairs.push({
                pair_id: 'tech_health',
                ticker1: techAsset.ticker,
                ticker2: healthAsset.ticker,
                name1: techAsset.name,
                name2: healthAsset.name,
                description: `${techSector} vs ${healthSector}`,
                educational_focus: 'Innovation & Growth vs Health & Stability'
              });
            }
            
            // Pair 2: Consumer vs Energy
            const consumerList = data.sector_lists.find(list => list.list_id === 'consumer_discretionary');
            const energyList = data.sector_lists.find(list => list.list_id === 'energy_utilities');
            
            if (consumerList && energyList && consumerList.assets.length > 0 && energyList.assets.length > 0) {
              const consumerAsset = consumerList.assets[Math.floor(Math.random() * consumerList.assets.length)];
              const energyAsset = energyList.assets[Math.floor(Math.random() * energyList.assets.length)];
              
              // Use individual asset sectors for descriptions
              const consumerSector = consumerAsset.sector || 'Consumer Discretionary';
              const energySector = energyAsset.sector || 'Energy';
              
              pairs.push({
                pair_id: 'consumer_energy',
                ticker1: consumerAsset.ticker,
                ticker2: energyAsset.ticker,
                name1: consumerAsset.name,
                name2: energyAsset.name,
                description: `${consumerSector} vs ${energySector}`,
                educational_focus: 'Consumer Demand vs Energy Infrastructure'
              });
            }
            
            // Pair 3: Financial vs Stable Blue Chips
            const financialList = data.sector_lists.find(list => list.list_id === 'financial_services');
            const stableList = data.sector_lists.find(list => list.list_id === 'stable_blue_chips');
            
            if (financialList && stableList && financialList.assets.length > 0 && stableList.assets.length > 0) {
              const financialAsset = financialList.assets[Math.floor(Math.random() * financialList.assets.length)];
              const stableAsset = stableList.assets[Math.floor(Math.random() * stableList.assets.length)];
              
              // Use individual asset sectors for descriptions
              const financialSector = financialAsset.sector || 'Financial Services';
              const stableSector = stableAsset.sector || 'Consumer Staples';
              
              pairs.push({
                pair_id: 'financial_stable',
                ticker1: financialAsset.ticker,
                ticker2: stableAsset.ticker,
                name1: financialAsset.name,
                name2: stableAsset.name,
                description: `${financialSector} vs ${stableSector}`,
                educational_focus: 'Financial & Consumer Services vs Stability & Health'
              });
            }
          }
        }
        
        // FIX #6: Validate pairs before setting - ensure we have at least 1 valid pair
        if (pairs.length === 0) {
          console.error('No valid pairs generated from backend data');
          if (attempt < 3) {
            console.log(`Retrying pair generation (attempt ${attempt + 1}/3)...`);
            await new Promise(res => setTimeout(res, attempt * 1000));
            return loadAssetPairs(attempt + 1);
          } else {
            setError('Unable to generate asset pairs. Please refresh the page.');
            return;
          }
        }
        
        setAvailableAssetPairs(pairs);
        // Set current pair only if valid pairs exist
        if (pairs.length > 0) {
          // Double-check first pair is valid before setting
          if (pairs[0].ticker1 && pairs[0].ticker2 && pairs[0].ticker1 !== pairs[0].ticker2) {
            setCurrentPair({ ticker1: pairs[0].ticker1, ticker2: pairs[0].ticker2 });
            setSelectedPairId(pairs[0].pair_id);
          } else {
            console.error('First pair is invalid, using fallback');
            if (pairs.length > 1) {
              setCurrentPair({ ticker1: pairs[1].ticker1, ticker2: pairs[1].ticker2 });
              setSelectedPairId(pairs[1].pair_id);
            }
          }
        }
      } else {
        // FIX #7: Handle failed API response
        console.error('Failed to fetch mini-lesson assets:', response?.status);
        if (attempt < 3) {
          console.log(`Retrying fetch (attempt ${attempt + 1}/3)...`);
          await new Promise(res => setTimeout(res, attempt * 1000));
          return loadAssetPairs(attempt + 1);
        } else {
          setError('Unable to load asset data from server. Please try again later.');
        }
      }
    } catch (error) {
      console.error('Error loading asset pairs:', error);
      if (attempt < 3) {
        console.log(`Retrying after error (attempt ${attempt + 1}/3)...`);
        await new Promise(res => setTimeout(res, attempt * 1000));
        return loadAssetPairs(attempt + 1);
      } else {
        setError('Unable to connect to server. Please check your connection and try again.');
      }
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
        
        const ticker1 = (currentPair.ticker1 || '').trim();
        const ticker2 = (currentPair.ticker2 || '').trim();
        
        // Validate tickers before making API call
        if (!ticker1 || !ticker2 || ticker1 === '' || ticker2 === '' || ticker1 === ticker2) {
          console.log('Skipping mini-lesson load due to invalid/same tickers', { ticker1, ticker2 });
          setTwoAssetAnalysis(null);
          setIsLoadingMiniLesson(false);
          return;
        }
        
        const apiUrl = `/api/portfolio/two-asset-analysis?ticker1=${encodeURIComponent(ticker1)}&ticker2=${encodeURIComponent(ticker2)}`;
        
        // Simple retry with backoff: try up to 2 times
        let response: Response | null = null;
        for (let attempt = 1; attempt <= 2; attempt++) {
          try {
            response = await fetch(apiUrl);
            if (response.ok) break;
          } catch (e) {
            if (attempt === 2) throw e;
          }
          await new Promise(res => setTimeout(res, attempt * 500));
        }
        if (!response) throw new Error('No response from server');
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
          // Auto-rotate to next available pair to self-heal
          if (availableAssetPairs && availableAssetPairs.length > 1) {
            const nextIndex = Math.floor(Math.random() * availableAssetPairs.length);
            const nextPair = availableAssetPairs[nextIndex];
            if (nextPair && nextPair.ticker1 && nextPair.ticker2 && nextPair.ticker1 !== nextPair.ticker2) {
              setCurrentPair({ ticker1: nextPair.ticker1, ticker2: nextPair.ticker2 });
              setSelectedPairId(nextPair.pair_id);
              setIsLoadingMiniLesson(false);
              return;
            }
          }
          setError(`Unable to load financial data (HTTP ${response.status}). Please try again.`);
        }
      } catch (error) {
        console.error('Error loading mini-lesson data:', error);
        // Clear stale client cache and retry pair loading once
        try {
          if (typeof window !== 'undefined') {
            window.localStorage.removeItem(MINI_LESSON_CACHE_KEY);
          }
        } catch (storageError) {
          console.warn('Failed to clear mini-lesson cache', storageError);
        }
        setError('Unable to load financial data. Retrying with a fresh list...');
        // Trigger a refresh of pairs
        loadAssetPairs(2);
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
      
      // FIXED: Use correct endpoint path to match backend
      const response = await fetch(`/api/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=10`);

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
    // FIX: Clear results IMMEDIATELY when search term is empty (no debounce)
    if (!searchTerm.trim()) {
      setSearchResults([]);  // Clear results instantly
      setIsLoading(false);   // Clear loading state
      setError(null);        // Clear any errors
      return;
    }
    
    // Only debounce when there's actual search text
    const timeoutId = setTimeout(() => {
      searchStocks(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, searchStocks]);

  // Sync portfolio metrics to wizard when they change
  useEffect(() => {
    if (onMetricsUpdate) {
      onMetricsUpdate(portfolioMetrics);
    }
  }, [portfolioMetrics, onMetricsUpdate]);

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
      // FIX #1: Increased debounce delay for smoother UX
      const timeoutId = setTimeout(() => {
        calculateRealTimeMetrics();
        validatePortfolio();
      }, 800); // Increased from 200ms to 800ms for better debouncing
      
      return () => clearTimeout(timeoutId);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStocks, totalAllocation]); // calculateRealTimeMetrics and validatePortfolio are useCallback functions that depend on selectedStocks, so they're stable

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
    
    // Snapshot before change for possible restoration on delete of added ticker
    setAllocationHistory(prev => [...prev, selectedStocks.map(s => ({ ...s }))]);
    setHistoryMarkers(prev => [...prev, "add"]);

    let updatedStocks: PortfolioAllocation[] = [];
    if (lastRemovedOriginal && lastRemovedOriginal.allocation > 0) {
      // Replacement: assign removed original's weight to new ticker
      const newStock: PortfolioAllocation = {
        symbol: stock.symbol,
        allocation: lastRemovedOriginal.allocation,
        name: stock.longname || stock.shortname,
        assetType: stock.assetType || 'stock'
      };
      updatedStocks = [...selectedStocks, newStock];
      setLastRemovedOriginal(null);
    } else {
      // Default add: small weight, deduct proportionally
      const defaultWeight = DEFAULT_ADD_WEIGHT; // % configurable
      const sumOthers = selectedStocks.reduce((sum, s) => sum + s.allocation, 0);
      const factor = sumOthers > 0 ? (sumOthers - defaultWeight) / sumOthers : 0;
      const resizedOthers = selectedStocks.map(s => ({ ...s, allocation: Math.max(0, s.allocation * factor) }));
      const newStock: PortfolioAllocation = {
        symbol: stock.symbol,
        allocation: defaultWeight,
        name: stock.longname || stock.shortname,
        assetType: stock.assetType || 'stock'
      };
      updatedStocks = [...resizedOthers, newStock];
    }

    // Normalize to 100%
    const total = updatedStocks.reduce((sum, s) => sum + s.allocation, 0);
    const normalized = total > 0 ? updatedStocks.map(s => ({ ...s, allocation: (s.allocation / total) * 100 })) : updatedStocks;
    onStocksUpdate(normalized);
    
    // FIX #3: Clear search state in correct order
    setSearchResults([]);  // 1. Clear results FIRST (immediate)
    setSearchTerm('');     // 2. Then clear search term (prevents useEffect trigger)
    setError(null);        // 3. Clear any error messages
    
    setHasUserModified(true);
    
    // FIX #3: Remove focus from input field
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }

    // Warm the newly added ticker (debounced)
    if (warmTickersTimeoutRef.current) {
      window.clearTimeout(warmTickersTimeoutRef.current);
    }
    warmTickersTimeoutRef.current = window.setTimeout(() => {
      warmTickers([stock.symbol]);
    }, 500);
    
    // REMOVED: Explicit setTimeout call - useEffect (lines 902-922) will handle this automatically
    // This prevents double-triggering and glitches
  };

  const removeStock = (symbol: string) => {
    const isOriginal = originalSymbols.has(symbol);
    if (!isOriginal) {
      // Deleting an added ticker: restore previous snapshot if available
      if (allocationHistory.length > 0) {
        setAllocationHistory(prev => {
          const copy = [...prev];
          const markers = [...historyMarkers];
          // Pop until we find the last 'add' snapshot (skip 'normalize' snapshots)
          while (copy.length > 0 && markers.length > 0) {
            const snap = copy.pop() || [];
            const m = markers.pop();
            if (m === "add") {
              onStocksUpdate(snap);
              break;
            }
          }
          setHistoryMarkers(markers);
          return copy;
        });
        return;
      }
      // Fallback: remove and equal-rebalance
      const updatedStocks = selectedStocks.filter(s => s.symbol !== symbol);
      if (updatedStocks.length > 0) {
        const equalAllocation = 100 / updatedStocks.length;
        const rebalancedStocks = updatedStocks.map(s => ({ ...s, allocation: equalAllocation }));
        onStocksUpdate(rebalancedStocks);
      } else {
        onStocksUpdate([]);
        setHasUserModified(true);
      }
      return;
    }
    // Removing an original ticker: record its weight for replacement and keep others unchanged
    const removed = selectedStocks.find(s => s.symbol === symbol);
    setLastRemovedOriginal(removed ? { symbol, allocation: removed.allocation } : { symbol, allocation: 0 });
    const remaining = selectedStocks.filter(s => s.symbol !== symbol);
    onStocksUpdate(remaining);
  };

  const acceptRecommendation = (recommendation: PortfolioRecommendation, index: number) => {
    setSelectedPortfolioIndex(index);
    setOriginalRecommendation(recommendation);
    onStocksUpdate(recommendation.allocations);
    setHasSelectedPortfolio(true);
    setHasUserModified(false);
    // Initialize tracking for restoration logic
    setOriginalSymbols(new Set((recommendation.allocations || []).map(a => a.symbol)));
    setAllocationHistory([]);
    setLastRemovedOriginal(null);
    
    // Initialize allocation tracking
    const total = recommendation.allocations.reduce((sum, stock) => sum + stock.allocation, 0);
    setTotalAllocation(total);
    setIsValidAllocation(Math.abs(total - 100) < 0.1);

    // FIX #2: Show loading state briefly for smooth transition
    setIsLoadingMetrics(true);
    
    // REMOVED: Auto-navigation - navigation now only happens when user presses Continue button
    // Navigation will be handled by handleNext() when Continue is pressed
    
    // Mirror recommendation metrics immediately
    setPortfolioMetrics({
      expectedReturn: recommendation.expectedReturn,
      risk: recommendation.risk,
      diversificationScore: recommendation.diversificationScore,
      sharpeRatio: 0
    });

    // FIX #2: Clear loading state to display metrics
    setTimeout(() => {
      setIsLoadingMetrics(false);
    }, 100);

    // REMOVED: Explicit setTimeout call - useEffect will handle this automatically
    // The useEffect on lines 902-922 will trigger when selectedStocks changes
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
    
    // REMOVED: Explicit setTimeout call - useEffect will handle this automatically
  };

  // Equal allocation feature - equally distribute among all stocks
  const equalAllocation = () => {
    // Snapshot before equal allocation (marked as 'normalize' so delete-added skips it)
    setAllocationHistory(prev => [...prev, selectedStocks.map(s => ({ ...s }))]);
    setHistoryMarkers(prev => [...prev, "normalize"]);
    // Clear reserved replacement weight to avoid stale inheritance
    setLastRemovedOriginal(null);
    
    if (selectedStocks.length === 0) return;
    
    const equalWeight = 100 / selectedStocks.length;
    const equallyAllocatedStocks = selectedStocks.map(stock => ({
      ...stock,
      allocation: equalWeight
    }));
    
    onStocksUpdate(equallyAllocatedStocks);
    setTotalAllocation(100);
    setIsValidAllocation(true);
    setHasUserModified(true);
    
    // REMOVED: Explicit setTimeout call - useEffect will handle this automatically
  };

  // NEW: Reset to original function
  const resetToOriginal = () => {
    if (originalRecommendation) {
      onStocksUpdate(originalRecommendation.allocations);
      setTotalAllocation(100);
      setIsValidAllocation(true);
      setOriginalSymbols(new Set((originalRecommendation.allocations || []).map(a => a.symbol)));
      setAllocationHistory([]);
      setLastRemovedOriginal(null);
    }
  };

  // REMOVED: getPrimarySectors function - no longer needed since we removed primary sectors display

  // Continue enabled: mini-lesson always; recommendations when portfolio selected OR 3+ tickers; others by portfolioValidation
  const canContinue = activeTab === 'mini-lesson'
    ? true
    : activeTab === 'recommendations'
      ? (selectedPortfolioIndex !== null || selectedStocks.length >= 3)
      : portfolioValidation.canProceed;

  const handleNext = () => {
    // Prevent navigation if allocation is invalid (full-customization / dynamic-generation)
    if (activeTab !== 'mini-lesson' && activeTab !== 'recommendations' && (totalAllocation > 100 || totalAllocation < 85)) {
      return; // Do nothing - button should already be disabled
    }
    
    if (activeTab === 'mini-lesson') {
      // From mini-lesson, go to recommendations
      setActiveTab('recommendations');
    } else if (activeTab === 'recommendations') {
      // From recommendations, go to visual charts: need portfolio selected OR 3+ tickers
      if (selectedPortfolioIndex === null && selectedStocks.length < 3) {
        setError('Please select a recommended portfolio or add at least 3 tickers to create a portfolio before proceeding.');
        return;
      }
      setActiveTab('full-customization');
    } else if (activeTab === 'full-customization') {
      // From visual charts tab, ensure we have selected stocks and navigate to next wizard step
      if (selectedStocks.length >= 3) {
        onNext();
      }
    } else {
      // From other tabs, navigate to visual charts if we have selected stocks
      if (selectedStocks.length >= 3) {
        setActiveTab('full-customization');
      } else {
        // Otherwise call parent onNext
        onNext();
      }
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
    if (selectedStocks.length === 0) {
      console.log('No stocks selected, skipping metrics calculation');
      return;
    }

    // FIX #1: Cancel any pending metrics request
    if (metricsAbortController) {
      metricsAbortController.abort();
      console.log('Cancelled previous metrics calculation');
    }

    // Mirror selected recommendation metrics until user modifies allocations
    if (originalRecommendation && !hasUserModified) {
      setPortfolioMetrics({
        expectedReturn: originalRecommendation.expectedReturn,
        risk: originalRecommendation.risk,
        diversificationScore: originalRecommendation.diversificationScore,
        sharpeRatio: 0
      });
      return;
    }

    console.log('Calculating real-time metrics for portfolio:', selectedStocks.map(s => `${s.symbol}:${s.allocation}%`));
    
    setIsLoadingMetrics(true);
    setError(null);
    
    try {
      // FIX #1: Create new abort controller for this request
      const controller = new AbortController();
      setMetricsAbortController(controller);
      
      const requestBody = {
        allocations: selectedStocks,
        riskProfile: riskProfile
      };
      
      console.log('Sending metrics calculation request:', requestBody);
      
      const response = await fetch('/api/portfolio/calculate-metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: controller.signal  // FIX #1: Add abort signal
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Metrics calculation response:', data);
        
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
        
        console.log('Metrics updated successfully:', {
          expectedReturn: data.expectedReturn,
          risk: data.risk,
          diversificationScore: data.diversificationScore
        });
      } else {
        const errorText = await response.text();
        console.error('Metrics calculation failed:', response.status, errorText);
        throw new Error(`Failed to calculate metrics: ${response.status} ${errorText}`);
      }
    } catch (error: any) {
      // FIX #1: Handle abort errors gracefully
      if (error.name === 'AbortError') {
        console.log('Metrics calculation cancelled (new request initiated)');
        return; // Don't show error or update state for cancelled requests
      }
      
      console.error('Real-time calculation failed:', error);
      setError('Failed to calculate portfolio metrics. Using fallback calculations.');
      
      // Fallback to calculated metrics
      calculateFallbackMetrics();
    } finally {
      setIsLoadingMetrics(false);
      setMetricsAbortController(null); // FIX #1: Clear abort controller
    }
  }, [selectedStocks, riskProfile, originalRecommendation, hasUserModified, metricsAbortController]);

  // REMOVED: Duplicate useEffect that was causing glitches
  // The useEffect on lines 902-922 already handles selectedStocks changes with proper debouncing

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

  // Explicit Done handler for Customize Your Portfolio workflow
  const handleDone = async () => {
    // Enforce 3–4 tickers before proceeding
    if (selectedStocks.length < 3 || selectedStocks.length > 4) {
      setError('Please select between 3 and 4 tickers before clicking Done.');
      return;
    }

    // If no weights are set yet, auto-distribute equally
    const currentTotal = selectedStocks.reduce((sum, stock) => sum + (stock.allocation || 0), 0);
    if (Math.abs(currentTotal) < 0.01) {
      const equalAllocation = 100 / selectedStocks.length;
      const updatedStocks = selectedStocks.map(stock => ({
        ...stock,
        allocation: equalAllocation
      }));

      onStocksUpdate(updatedStocks);
      setTotalAllocation(100);
      setIsValidAllocation(true);
      setHasUserModified(true);
    }

    // Clear any stale errors and trigger immediate metrics + validation
    setError(null);
    await calculateRealTimeMetrics();
    validatePortfolio();
  };

  // NEW: Apply changes function
  const applyChanges = () => {
    if (portfolioValidation.isValid) {
      setSuccessMessage('Portfolio changes applied successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    }
  };

  // NEW: Generate pure strategy portfolios
  const generateStrategyPortfolios = async () => {
    // Check generation limit (max 2 per strategy)
    const currentCount = generationCounts[selectedStrategy] || 0;
    if (currentCount >= 2) {
      const strategyName = selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1);
      setError(
        `Generation limit reached: You have already generated portfolios twice for the ${strategyName} strategy. ` +
        `To ensure you have enough options to choose from, we limit each strategy to 2 generations. ` +
        `Please review and select one of the ${allGeneratedPortfolios[selectedStrategy].length} portfolios you've already generated, or try a different investment strategy.`
      );
      // Show existing portfolios if any
      if (allGeneratedPortfolios[selectedStrategy].length > 0) {
        setStrategyPortfolios(allGeneratedPortfolios[selectedStrategy]);
      }
      return;
    }
    
    setIsLoadingStrategy(true);
    setError(null);
    
    try {
      // Prepare strategy parameters
      const params = new URLSearchParams({
        risk_profile: riskProfile,
        strategy: selectedStrategy
      });
      
      const response = await fetch(`/api/portfolio/recommendations/strategy-pure?${params}`, {
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
          name?: string;
          description?: string;
        }, index: number) => ({
          name: portfolio.name || `${selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1)} Strategy Portfolio ${index + 1}`,
          description: portfolio.description || `Pure ${selectedStrategy} strategy portfolio optimized for your risk profile`,
          allocations: portfolio.portfolio || [],
          expectedReturn: portfolio.expectedReturn || 0.15,
          risk: portfolio.risk || 0.20,
          diversificationScore: portfolio.diversificationScore || 75,
          strategy: portfolio.strategy || selectedStrategy,
          rank: index + 1,
          score: 0
        }));
        
        // Update generation count
        const newCount = currentCount + 1;
        setGenerationCounts(prev => ({
          ...prev,
          [selectedStrategy]: newCount
        }));
        
        // Store all generated portfolios for this strategy
        setAllGeneratedPortfolios(prev => ({
          ...prev,
          [selectedStrategy]: [...(prev[selectedStrategy] || []), ...transformedPortfolios]
        }));
        
        setStrategyPortfolios(transformedPortfolios);
        setSuccessMessage(`Generated ${transformedPortfolios.length} ${selectedStrategy} strategy portfolios! (${newCount}/2 generations used)`);
        setTimeout(() => setSuccessMessage(null), 3000);

        // Warm all tickers from strategy portfolios
        const allTickers = new Set<string>();
        transformedPortfolios.forEach((portfolio: PortfolioRecommendation) => {
          portfolio.allocations?.forEach((alloc: PortfolioAllocation) => {
            if (alloc.symbol) allTickers.add(alloc.symbol);
          });
        });
        warmTickers(Array.from(allTickers));
      } else {
        throw new Error('Failed to generate strategy portfolios');
      }
    } catch (error) {
      console.error('Error generating strategy portfolios:', error);
      setError('Failed to generate strategy portfolios. Using fallback recommendations.');
      
      // Fallback to static recommendations
      const fallbackPortfolios = generateRecommendations();
      setStrategyPortfolios(fallbackPortfolios);
    } finally {
      setIsLoadingStrategy(false);
    }
  };
  
  // Update displayed portfolios when strategy changes
  useEffect(() => {
    const portfoliosForStrategy = allGeneratedPortfolios[selectedStrategy];
    if (portfoliosForStrategy && portfoliosForStrategy.length > 0) {
      setStrategyPortfolios(portfoliosForStrategy);
    } else {
      setStrategyPortfolios([]);
    }
    // Clear error when switching strategies
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStrategy]);

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
          risk_profile: riskProfile
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
        
        <CardContent>
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
            <TabsContent value="mini-lesson" className="space-y-4">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200">
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="h-5 w-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-blue-900">How Risk and Return Trade Off</h3>
                </div>
                <div className="bg-muted/30 rounded-lg p-3 border border-border/50 mb-3">
                  <p className="text-xs text-muted-foreground">
                    Learn how combining different assets can reduce risk while maintaining returns. Choose from educational asset pairs to explore portfolio theory and diversification benefits.
                  </p>
                </div>
                
                {/* Asset Pair Selection */}
                {availableAssetPairs.length > 0 && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-medium text-foreground">Select Asset Pair for Analysis</h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => loadAssetPairs()}
                        className="text-xs px-2 py-1 h-7"
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
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            {twoAssetAnalysis.ticker1}
                          </CardTitle>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {twoAssetAnalysis.asset1_stats.company_name || twoAssetAnalysis.ticker1}
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-1.5 pt-0">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Annual Return:</span>
                            <span className="font-medium text-green-600">
                              {(twoAssetAnalysis.asset1_stats.annualized_return * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Volatility:</span>
                            <span className="font-medium text-orange-600">
                              {(twoAssetAnalysis.asset1_stats.annualized_volatility * 100).toFixed(1)}%
                            </span>
                          </div>
                          {twoAssetAnalysis.asset1_stats.sector && (
                            <div className="flex justify-between text-xs">
                              <span className="text-muted-foreground">Sector:</span>
                              <span className="font-medium text-blue-600">
                                {twoAssetAnalysis.asset1_stats.sector}
                              </span>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            {twoAssetAnalysis.ticker2}
                          </CardTitle>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {twoAssetAnalysis.asset2_stats.company_name || twoAssetAnalysis.ticker2}
                          </p>
                        </CardHeader>
                        <CardContent className="space-y-1.5 pt-0">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Annual Return:</span>
                            <span className="font-medium text-green-600">
                              {(twoAssetAnalysis.asset2_stats.annualized_return * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Volatility:</span>
                            <span className="font-medium text-orange-600">
                              {(twoAssetAnalysis.asset2_stats.annualized_volatility * 100).toFixed(1)}%
                            </span>
                          </div>
                          {twoAssetAnalysis.asset2_stats.sector && (
                            <div className="flex justify-between text-xs">
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
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Interactive Portfolio Builder</CardTitle>
                        <p className="text-xs text-muted-foreground mt-1">
                          Adjust the allocation between {twoAssetAnalysis.ticker1} and {twoAssetAnalysis.ticker2} to see how it affects your portfolio's risk and return.
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-3 pt-0">
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{twoAssetAnalysis.ticker1} Weight: <strong className="text-foreground">{nvdaWeight}%</strong></span>
                            <span>{twoAssetAnalysis.ticker2} Weight: <strong className="text-foreground">{100 - nvdaWeight}%</strong></span>
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
                        <div className="flex gap-2 flex-wrap justify-center">
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
                    <Card className="bg-gradient-to-br from-slate-50 to-blue-50 border-0 shadow-lg">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                          <BarChart3 className="h-5 w-5 text-blue-600" />
                          Your Portfolio Metrics
                        </CardTitle>
                        <p className="text-xs text-slate-600 mt-1">
                          Real-time metrics based on your current allocation and market data
                        </p>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Expected Return */}
                          <div className="relative overflow-hidden rounded-lg bg-gradient-to-br from-emerald-50 to-emerald-100 p-4 border border-emerald-200">
                            <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-200 rounded-full -translate-y-8 translate-x-8 opacity-20"></div>
                            <div className="relative z-10">
                              <div className="flex items-center gap-1.5 mb-1.5">
                                <TrendingUp className="h-4 w-4 text-emerald-600" />
                                <span className="text-xs font-medium text-emerald-700">Expected Return</span>
                              </div>
                              <div className="text-2xl font-bold text-emerald-800 mb-0.5">
                                {(customPortfolio.return * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-emerald-600">
                                Annualized projection
                              </div>
                            </div>
                          </div>

                          {/* Risk Level */}
                          <div className="relative overflow-hidden rounded-lg bg-gradient-to-br from-amber-50 to-amber-100 p-4 border border-amber-200">
                            <div className="absolute top-0 right-0 w-16 h-16 bg-amber-200 rounded-full -translate-y-8 translate-x-8 opacity-20"></div>
                            <div className="relative z-10">
                              <div className="flex items-center gap-1.5 mb-1.5">
                                <Shield className="h-4 w-4 text-amber-600" />
                                <span className="text-xs font-medium text-amber-700">Risk (Volatility)</span>
                              </div>
                              <div className="text-2xl font-bold text-amber-800 mb-0.5">
                                {(customPortfolio.risk * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-amber-600">
                                Volatility measure
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Educational Info - Compact */}
                    <div className="bg-muted/30 rounded-lg p-3 border border-border/50">
                      <div className="text-xs text-muted-foreground space-y-2">
                        <div className="flex items-start gap-2">
                          <TrendingUp className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <strong className="text-foreground">Expected Return:</strong> Average yearly growth rate based on historical performance.
                          </div>
                        </div>
                        <div className="flex items-start gap-2">
                          <Shield className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <strong className="text-foreground">Risk (Volatility):</strong> Measures return variation. Higher values indicate more uncertainty.
                          </div>
                        </div>
                        <div className="pt-1.5 border-t border-border/30 mt-1.5 flex items-start gap-2">
                          <Database className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <strong className="text-foreground">Data Source:</strong> Yahoo Finance (monthly returns, annualized). Historical data for educational purposes only.
                          </div>
                        </div>
                      </div>
                    </div>
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
            <TabsContent value="recommendations" className="space-y-4">
              <div className="text-center mb-4">
                <h3 className="text-lg font-semibold mb-1">Portfolio Recommendations</h3>
                <p className="text-xs text-muted-foreground">
                  Personalized recommendations optimized for your {getRiskProfileDisplay().toLowerCase()} risk profile using live market data
                </p>
              </div>

              {isLoadingRecommendations ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  <p className="mt-2 text-muted-foreground">Generating personalized recommendations...</p>
                </div>
              ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                        <Badge variant="default" className="bg-green-600 text-xs">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Selected
                        </Badge>
                      </div>
                    )}
                    
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base">{recommendation.name}</CardTitle>
                        <Badge variant={index === 0 ? "default" : "secondary"} className="text-xs">
                          {index === 0 ? "Top Pick" : "Alt " + (index + 1)}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{recommendation.description}</p>
                    </CardHeader>
                    <CardContent className="space-y-3 pt-0">
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <div className="text-muted-foreground mb-0.5">Expected Return</div>
                          <div className="font-semibold text-green-600">
                            {(recommendation.expectedReturn * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground mb-0.5">Risk Level</div>
                          <div className="font-semibold text-orange-600">
                            {(recommendation.risk * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span>Diversification Score</span>
                          <span>{recommendation.diversificationScore}%</span>
                        </div>
                        <Progress value={recommendation.diversificationScore} className="h-1.5" />
                      </div>

                      {/* Enhanced portfolio information */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Total Allocation:</span>
                          <span className="font-medium">100%</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Number of Assets:</span>
                          <span className="font-medium">{recommendation.allocations.length}</span>
                        </div>
                      </div>

                      <div className="space-y-1.5 pt-1 border-t border-border/30">
                        <div className="text-xs font-medium mb-1">Allocations:</div>
                        {recommendation.allocations.slice(0, 3).map((allocation, idx) => (
                          <div key={idx} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{allocation.symbol}</span>
                            <span className="font-medium">{allocation.allocation}%</span>
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
                        className="w-full text-xs h-8"
                        variant={selectedPortfolioIndex === index ? "default" : "outline"}
                        size="sm"
                      >
                        {selectedPortfolioIndex === index ? (
                          <>
                            <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                            Selected
                          </>
                        ) : (
                          <>
                            <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
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
              {!hasSelectedPortfolio && activeTab === 'recommendations' && (
                <div className="text-center mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setActiveTab('dynamic-generation')}
                    className="flex items-center gap-1.5 mx-auto text-xs h-8"
                  >
                    <Zap className="h-3.5 w-3.5" />
                    Advanced Options
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1.5">
                    Generate custom portfolios using AI optimization algorithms
                  </p>
                </div>
              )}

              {/* Portfolio Customization Section - Only show after selection AND on recommendations tab */}
              {hasSelectedPortfolio && selectedStocks.length > 0 && activeTab === 'recommendations' && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Customize Your Portfolio</CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">
                      Modify the selected portfolio by adding or removing stocks and adjusting allocations
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
                                disabled={selectedStocks.some(s => s.symbol === stock.symbol) || selectedStocks.length >= 4}
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
                        <h4 className="text-lg font-medium">Selected Assets ({selectedStocks.length}/4)</h4>
                        <div className="text-sm text-muted-foreground">
                          Minimum 3, maximum 4 tickers
                        </div>
                      </div>

                      {/* Portfolio Overview - Moved here, below Selected Assets */}
                      <div className={`border rounded-lg p-3 ${totalAllocation > 100 ? 'bg-red-50 border-red-200' : 'bg-muted/30'}`}>
                        <div className="grid grid-cols-3 gap-3 text-center">
                          <div>
                            <div className="text-xl font-bold text-primary">{selectedStocks.length}</div>
                            <div className="text-xs text-muted-foreground">Stocks</div>
                          </div>
                          <div>
                            <div className={`text-xl font-bold ${totalAllocation > 100 ? 'text-red-600' : 'text-green-600'}`}>
                              {totalAllocation.toFixed(1)}%
                            </div>
                            <div className="text-xs text-muted-foreground">Total Allocation</div>
                          </div>
                          <div>
                            <div className={`text-xl font-bold ${totalAllocation > 100 ? 'text-red-600' : 'text-green-600'}`}>
                              {totalAllocation > 100 ? '✗' : '✓'}
                            </div>
                            <div className="text-xs text-muted-foreground">Status</div>
                          </div>
                        </div>
                        <div className={`mt-2 text-center text-xs ${totalAllocation > 100 ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
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
                        <h5 className="text-sm font-medium">Weight Editor</h5>
                        <p className="text-xs text-muted-foreground mt-0.5">
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
                            onClick={equalAllocation}
                            variant="outline"
                            size="sm"
                          >
                            Equal Allocation
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Done button and Portfolio Validation */}
                    <div className="mt-4 flex justify-end">
                      <Button
                        onClick={handleDone}
                        size="sm"
                        disabled={selectedStocks.length < 3 || selectedStocks.length > 4}
                      >
                        Done
                      </Button>
                    </div>

                    {/* Portfolio Validation */}
                    <div className="bg-muted/30 rounded-lg p-3 border border-border/50">
                      <h5 className="text-xs font-medium mb-2">Portfolio Validation</h5>
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Minimum 3 stocks</span>
                          <span className={selectedStocks.length >= 3 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                            {selectedStocks.length >= 3 ? '✓' : '✗'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Total allocation = 100%</span>
                          <span className={Math.abs(totalAllocation - 100) < 0.1 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                            {Math.abs(totalAllocation - 100) < 0.1 ? '✓' : '✗'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Portfolio Metrics Section - Enhanced UX Design */}
              {hasSelectedPortfolio && selectedStocks.length > 0 && activeTab === 'recommendations' && (
                <Card className="bg-gradient-to-br from-slate-50 to-blue-50 border-0 shadow-lg">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-xl flex items-center gap-3 text-slate-800">
                      <BarChart3 className="h-6 w-6 text-blue-600" />
                      Your Portfolio Performance
                      {isLoadingMetrics && (
                        <div className="ml-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        </div>
                      )}
                    </CardTitle>
                    <p className="text-slate-600">
                      {isLoadingMetrics ? 'Calculating metrics...' : 'Real-time metrics based on your current allocation and market data'}
                    </p>
                  </CardHeader>
                  <CardContent>
                    {isLoadingMetrics ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span className="ml-3 text-slate-600">Calculating portfolio metrics...</span>
                      </div>
                    ) : portfolioMetrics ? (
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
                    ) : (
                      <div className="flex items-center justify-center py-8">
                        <div className="text-center">
                          <div className="text-slate-500 mb-2">No metrics available</div>
                          <div className="text-sm text-slate-400">Please wait for calculation to complete</div>
                      </div>
                    </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Visual Charts Tab */}
            <TabsContent value="full-customization" className="space-y-4">
              <div className="text-center mb-4">
                <h3 className="text-lg font-semibold mb-1">Visual Charts & Analysis</h3>
                <p className="text-xs text-muted-foreground">
                  Interactive visual analytics synchronized with your selected portfolio and benchmarks
                </p>
              </div>

              {selectedStocks.length >= 3 ? (
                <VisualizationErrorBoundary>
                  <Portfolio3PartVisualization
                    selectedStocks={selectedStocks}
                    riskProfile={riskProfile}
                    selectedPortfolioIndex={selectedPortfolioIndex}
                    allRecommendations={dynamicRecommendations.length > 0 ? dynamicRecommendations : recommendations}
                    strategyPortfolios={strategyPortfolios}
                    compactMode={true}
                  />
                </VisualizationErrorBoundary>
              ) : (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Select a Portfolio to Continue</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1.5 text-center text-xs text-muted-foreground pt-0">
                    <p>Select a recommended portfolio or build a custom allocation with at least three assets.</p>
                    <p>Your selections will power the live visualization experience in this tab.</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Pure Strategy Generation Tab - Hidden by default, accessible via Advanced Options */}
            {activeTab === 'dynamic-generation' && (
              <TabsContent value="dynamic-generation" className="space-y-4">
                <div className="text-center mb-4">
                  <h3 className="text-lg font-semibold mb-1">Pure Strategy Portfolio Generation</h3>
                  <p className="text-xs text-muted-foreground">
                    Explore different investment strategies in their purest form. Each strategy is optimized using real market data and proven algorithms.
                  </p>
                </div>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Investment Strategy Selection</CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">
                      Choose an investment strategy to see how it performs with your risk profile.
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-0">
                    {/* Error message display */}
                    {error && (
                      <Alert className="bg-red-50 border-red-200 text-xs">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <AlertDescription className="text-red-800">
                          {error}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {/* Success message display */}
                    {successMessage && (
                      <Alert className="bg-green-50 border-green-200 text-xs">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-800">
                          {successMessage}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-foreground mb-1.5">Select Investment Strategy</label>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div 
                            className={`p-3 border rounded-lg cursor-pointer transition-all ${
                              selectedStrategy === 'diversification' 
                                ? 'border-primary bg-primary/5 ring-2 ring-primary' 
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => setSelectedStrategy('diversification')}
                          >
                            <h4 className="font-medium text-xs mb-0.5">Diversification Strategy</h4>
                            <p className="text-xs text-muted-foreground">Low correlation, balanced sector exposure</p>
                      </div>
                          <div 
                            className={`p-3 border rounded-lg cursor-pointer transition-all ${
                              selectedStrategy === 'risk' 
                                ? 'border-primary bg-primary/5 ring-2 ring-primary' 
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => setSelectedStrategy('risk')}
                          >
                            <h4 className="font-medium text-xs mb-0.5">Risk Minimization</h4>
                            <p className="text-xs text-muted-foreground">Low volatility, defensive positioning</p>
                      </div>
                          <div 
                            className={`p-3 border rounded-lg cursor-pointer transition-all ${
                              selectedStrategy === 'return' 
                                ? 'border-primary bg-primary/5 ring-2 ring-primary' 
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => setSelectedStrategy('return')}
                          >
                            <h4 className="font-medium text-xs mb-0.5">Return Maximization</h4>
                            <p className="text-xs text-muted-foreground">High expected return, growth focus</p>
                          </div>
                        </div>
                    </div>

                      <div className="space-y-2">
                        {/* Generation limit reached warning */}
                        {(generationCounts[selectedStrategy] || 0) >= 2 && (
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs">
                            <div className="flex items-start gap-2">
                              <svg className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              <div className="flex-1">
                                <p className="font-medium text-amber-800 mb-1.5">Generation Limit Reached</p>
                                <p className="text-amber-700 mb-2">
                                  You have used all 2 generations for the <span className="font-medium">{selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1)}</span> strategy. 
                                  This limit helps ensure you have a focused set of high-quality portfolio options to choose from.
                                </p>
                                <div className="bg-amber-100/50 rounded p-2 mt-2">
                                  <p className="text-amber-800 font-medium mb-1">What to do next:</p>
                                  <ul className="list-disc list-inside space-y-0.5 text-amber-700">
                                    <li>Review the {allGeneratedPortfolios[selectedStrategy]?.length || 0} portfolios displayed above</li>
                                    <li>Compare their expected returns, risk levels, and diversification scores</li>
                                    <li>Select the portfolio that best matches your investment goals</li>
                                    <li>Or try a different investment strategy to explore more options</li>
                                  </ul>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Approaching limit warning (1/2) */}
                        {(generationCounts[selectedStrategy] || 0) === 1 && (
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs">
                            <div className="flex items-start gap-2">
                              <svg className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                              </svg>
                              <div>
                                <p className="font-medium text-blue-800 mb-1">One Generation Remaining</p>
                                <p className="text-blue-700">
                                  You have used 1 of 2 generations for this strategy. You can generate portfolios one more time before reaching the limit.
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Generation count indicator (when not at limit) */}
                        {(generationCounts[selectedStrategy] || 0) === 0 && (
                          <div className="text-xs text-muted-foreground text-center">
                            You can generate portfolios up to 2 times for each strategy
                          </div>
                        )}
                        
                        <div className="flex gap-3">
                          <Button
                              onClick={() => generateStrategyPortfolios()}
                              disabled={isLoadingStrategy || (generationCounts[selectedStrategy] || 0) >= 2}
                              className="flex-1 text-xs h-8"
                              size="sm"
                            >
                              {isLoadingStrategy ? (
                              <>
                                <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Generating Portfolios...
                              </>
                            ) : (generationCounts[selectedStrategy] || 0) >= 2 ? (
                              <>
                                Limit Reached - Select a Portfolio
                              </>
                            ) : (
                              <>
                                  Generate {selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1)} Portfolios
                                <ArrowRight className="ml-2 h-4 w-4" />
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Strategy Portfolios Display */}
                    {isLoadingStrategy ? (
                        <div className="text-center py-8">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                        <p className="mt-2 text-xs text-muted-foreground">Generating {selectedStrategy} strategy portfolios...</p>
                        </div>
                      ) : strategyPortfolios.length > 0 ? (
                        <div className="mt-4">
                        <h4 className="text-base font-medium mb-3 text-center">
                          Generated {selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1)} Strategy Portfolios
                          {(generationCounts[selectedStrategy] || 0) >= 2 && (
                            <span className="ml-2 text-xs text-amber-600 font-normal">
                              ({strategyPortfolios.length} total - Select one to proceed)
                            </span>
                          )}
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {strategyPortfolios.map((portfolio, index) => (
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
                                <div className="bg-green-600 text-white text-xs px-2 py-1 rounded flex items-center gap-1">
                                  <CheckCircle className="h-3 w-3" />
                                  Selected
                                </div>
                              </div>
                            )}
                            
                            <CardHeader className="pb-3">
                              <div className="flex items-center justify-center">
                                  <CardTitle className="text-base">{portfolio.name}</CardTitle>
                              </div>
                                <p className="text-xs text-muted-foreground mt-1 text-center">{portfolio.description}</p>
                            </CardHeader>
                            <CardContent className="space-y-3 pt-0">
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <div className="text-muted-foreground mb-0.5">Expected Return</div>
                                  <div className="font-semibold text-green-600">
                                      {(portfolio.expectedReturn * 100).toFixed(1)}%
                                  </div>
                                </div>
                                <div>
                                  <div className="text-muted-foreground mb-0.5">Risk Level</div>
                                  <div className="font-semibold text-orange-600">
                                      {(portfolio.risk * 100).toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                              
                              <div>
                                <div className="flex justify-between text-xs mb-1">
                                  <span>Diversification Score</span>
                                    <span>{portfolio.diversificationScore}%</span>
                                </div>
                                  <Progress value={portfolio.diversificationScore} className="h-1.5" />
                              </div>

                                {/* Enhanced portfolio information */}
                                <div className="space-y-1.5">
                                  <div className="flex justify-between text-xs">
                                    <span className="text-muted-foreground">Total Allocation:</span>
                                    <span className="font-medium">100%</span>
                                  </div>
                                  <div className="flex justify-between text-xs">
                                    <span className="text-muted-foreground">Number of Assets:</span>
                                    <span className="font-medium">{portfolio.allocations.length}</span>
                              </div>
                              </div>

                              <div className="space-y-1.5 pt-1 border-t border-border/30">
                                <div className="text-xs font-medium mb-1">Allocations:</div>
                                  {portfolio.allocations.slice(0, 3).map((allocation, idx) => (
                                  <div key={idx} className="flex justify-between text-xs">
                                    <span className="text-muted-foreground">{allocation.symbol}</span>
                                    <span className="font-medium">{allocation.allocation}%</span>
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
                                className="w-full text-xs h-8"
                                variant={selectedPortfolioIndex === index ? "default" : "outline"}
                                size="sm"
                              >
                                {selectedPortfolioIndex === index ? (
                                  <>
                                    <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                                    Selected
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
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
              disabled={!canContinue}
              className={canContinue ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-300 cursor-not-allowed'}
            >
              {canContinue ? (
                <>
                  Continue
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              ) : activeTab === 'recommendations' ? (
                <>
                  Select a portfolio or add 3+ tickers
                  <AlertTriangle className="ml-2 h-4 w-4" />
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