import { useState, useEffect, useCallback } from "react";

export type RiskProfile =
  | "very-conservative"
  | "conservative"
  | "moderate"
  | "aggressive"
  | "very-aggressive"
  | null;

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: "stock" | "bond" | "etf";
}

export interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

export interface SelectedPortfolioData {
  source: "current" | "weights" | "market";
  tickers: string[];
  weights: Record<string, number>;
  metrics: {
    expected_return: number;
    risk: number;
    sharpe_ratio: number;
  };
}

export interface WizardData {
  riskProfile: RiskProfile;
  riskAnalysis: unknown;
  capital: number;
  selectedStocks: PortfolioAllocation[];
  portfolioMetrics: PortfolioMetrics | null;
  selectedPortfolio: SelectedPortfolioData | null;
}

export interface WizardFlowState {
  currentStep: number;
  wizardData: WizardData;
  finalizeOpenToTab: "tax-cost" | null;
}

const STORAGE_KEY = "wizard_flow_state";

const initialWizardData: WizardData = {
  riskProfile: null,
  riskAnalysis: null,
  capital: 0,
  selectedStocks: [],
  portfolioMetrics: null,
  selectedPortfolio: null,
};

const initialState: WizardFlowState = {
  currentStep: 0,
  wizardData: initialWizardData,
  finalizeOpenToTab: null,
};

function loadInitialState(): WizardFlowState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved) as Partial<WizardFlowState>;
      // Always start at step 0 (Welcome) so user can choose to continue or start fresh
      // The wizardData is preserved so "Continue" can restore progress
      return {
        currentStep: 0, // Always show Welcome step first
        wizardData: {
          ...initialWizardData,
          ...(parsed.wizardData && typeof parsed.wizardData === "object"
            ? parsed.wizardData
            : {}),
        },
        finalizeOpenToTab:
          parsed.finalizeOpenToTab === "tax-cost" ? "tax-cost" : null,
      };
    }
  } catch (error) {
    console.error("Error loading wizard state:", error);
  }
  return initialState;
}

export function useWizardState() {
  const [state, setState] = useState<WizardFlowState>(loadInitialState);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      console.error("Error saving wizard state:", error);
    }
  }, [state]);

  const updateStep = useCallback((step: number) => {
    setState((prev) => ({ ...prev, currentStep: step }));
  }, []);

  const updateWizardData = useCallback(
    (dataOrUpdater: Partial<WizardData> | ((prev: WizardData) => WizardData)) => {
      setState((prev) => ({
        ...prev,
        wizardData:
          typeof dataOrUpdater === "function"
            ? dataOrUpdater(prev.wizardData)
            : { ...prev.wizardData, ...dataOrUpdater },
      }));
    },
    []
  );

  const setFinalizeOpenToTab = useCallback((tab: "tax-cost" | null) => {
    setState((prev) => ({ ...prev, finalizeOpenToTab: tab }));
  }, []);

  const resetWizardState = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState(initialState);
  }, []);

  return {
    state,
    setState,
    updateStep,
    updateWizardData,
    setFinalizeOpenToTab,
    resetWizardState,
  };
}
