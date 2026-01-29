import { useState, useEffect, useCallback } from 'react';

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
}

export interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

export interface TaxSettings {
  accountType: 'ISK' | 'KF' | 'AF' | null;
  taxYear: 2025 | 2026;
  courtagClass: string | null;
}

export interface TabCompletion {
  builder: boolean;
  optimize: boolean;
  analysis: boolean;
  taxCost: boolean;
}

export interface PortfolioState {
  constructedPortfolio: PortfolioAllocation[];
  optimizedPortfolio: any | null;
  stressTestResults: any | null;
  taxSettings: TaxSettings;
  tabCompletion: TabCompletion;
  lastSaved: string;
}

const STORAGE_KEY = 'finalize_portfolio_state';

const defaultState: PortfolioState = {
  constructedPortfolio: [],
  optimizedPortfolio: null,
  stressTestResults: null,
  taxSettings: {
    accountType: null,
    taxYear: 2026,
    courtagClass: null
  },
  tabCompletion: {
    builder: false,
    optimize: false,
    analysis: false,
    taxCost: false
  },
  lastSaved: new Date().toISOString()
};

export const usePortfolioState = () => {
  const [state, setState] = useState<PortfolioState>(defaultState);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Always start the builder with an empty constructed portfolio so
        // users select all stocks themselves, even if a previous session
        // was saved in localStorage.
        setState({
          ...defaultState,
          ...parsed,
          constructedPortfolio: [],
          optimizedPortfolio: null,
          stressTestResults: null,
          tabCompletion: {
            ...defaultState.tabCompletion,
            ...parsed.tabCompletion,
            builder: false,
            optimize: false,
            analysis: false
          }
        });
      }
    } catch (error) {
      console.error('Error loading portfolio state:', error);
    } finally {
      setIsLoaded(true);
    }
  }, []);

  // Auto-save to localStorage whenever state changes
  useEffect(() => {
    if (isLoaded) {
      try {
        const stateToSave = {
          ...state,
          lastSaved: new Date().toISOString()
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
      } catch (error) {
        console.error('Error saving portfolio state:', error);
      }
    }
  }, [state, isLoaded]);

  // Update state function
  const updateState = useCallback((updates: Partial<PortfolioState>) => {
    setState(prev => ({
      ...prev,
      ...updates
    }));
  }, []);

  // Update constructed portfolio
  const updateConstructedPortfolio = useCallback((portfolio: PortfolioAllocation[]) => {
    const totalAllocation = portfolio.reduce((sum, s) => sum + (s.allocation || 0), 0);
    const isValidCount = portfolio.length >= 3 && portfolio.length <= 4;
    const isValidAllocation = Math.abs(totalAllocation - 100) < 0.1;

    setState(prev => ({
      ...prev,
      constructedPortfolio: portfolio,
      tabCompletion: {
        ...prev.tabCompletion,
        builder: isValidCount && isValidAllocation
      }
    }));
  }, []);

  // Update optimized portfolio
  const updateOptimizedPortfolio = useCallback((portfolio: any) => {
    setState(prev => ({
      ...prev,
      optimizedPortfolio: portfolio,
      tabCompletion: {
        ...prev.tabCompletion,
        optimize: portfolio !== null
      }
    }));
  }, []);

  // Update stress test results
  const updateStressTestResults = useCallback((results: any) => {
    setState(prev => ({
      ...prev,
      stressTestResults: results
    }));
  }, []);

  // Update tax settings
  const updateTaxSettings = useCallback((settings: Partial<TaxSettings>) => {
    setState(prev => ({
      ...prev,
      taxSettings: {
        ...prev.taxSettings,
        ...settings
      },
      tabCompletion: {
        ...prev.tabCompletion,
        taxCost: settings.accountType !== null && settings.accountType !== undefined
      }
    }));
  }, []);

  // Mark tab as complete
  const markTabComplete = useCallback((tab: keyof TabCompletion) => {
    setState(prev => ({
      ...prev,
      tabCompletion: {
        ...prev.tabCompletion,
        [tab]: true
      }
    }));
  }, []);

  // Clear all state
  const clearState = useCallback(() => {
    setState(defaultState);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    state,
    isLoaded,
    updateState,
    updateConstructedPortfolio,
    updateOptimizedPortfolio,
    updateStressTestResults,
    updateTaxSettings,
    markTabComplete,
    clearState
  };
};
