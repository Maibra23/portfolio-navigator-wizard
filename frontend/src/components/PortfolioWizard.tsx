import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  TrendingUp,
  Shield,
  DollarSign,
  BarChart3,
  CheckCircle,
  FileText,
} from "lucide-react";
import { WelcomeStep } from "./wizard/WelcomeStep";
import { RiskProfiler } from "./wizard/RiskProfiler";
import { CapitalInput } from "./wizard/CapitalInput";
import { StockSelection } from "./wizard/StockSelection";
import { PortfolioOptimization } from "./wizard/PortfolioOptimization";
import { StressTest } from "./wizard/StressTest";
import { FinalizePortfolio } from "./wizard/FinalizePortfolio";
import { ThankYouStep } from "./wizard/ThankYouStep";
import { WizardStepErrorBoundary } from "./wizard/WizardStepErrorBoundary";
import { ThemeSelector } from "@/components/ThemeSelector";

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
  riskAnalysis: any;
  capital: number;
  selectedStocks: PortfolioAllocation[];
  portfolioMetrics: PortfolioMetrics | null;
  selectedPortfolio: SelectedPortfolioData | null;
}

const STEPS = [
  { id: "welcome", title: "Welcome", icon: TrendingUp },
  { id: "risk", title: "Risk Profile", icon: Shield },
  { id: "capital", title: "Capital Input", icon: DollarSign },
  { id: "stocks", title: "Stock Selection", icon: TrendingUp },
  { id: "optimization", title: "Optimization", icon: BarChart3 },
  { id: "stress-test", title: "Stress Test", icon: Shield },
  { id: "finalize", title: "Finalize Portfolio", icon: FileText },
  { id: "thank-you", title: "Complete", icon: CheckCircle },
];

const stepTransition = {
  initial: (direction: number) => ({
    opacity: 0,
    x: direction > 0 ? 80 : -80,
  }),
  animate: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: "easeOut" },
  },
  exit: (direction: number) => ({
    opacity: 0,
    x: direction > 0 ? -80 : 80,
    transition: { duration: 0.25, ease: "easeIn" },
  }),
};

export const PortfolioWizard = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [finalizeOpenToTab, setFinalizeOpenToTab] = useState<"tax-cost" | null>(
    null,
  );
  const [wizardData, setWizardData] = useState<WizardData>({
    riskProfile: null,
    riskAnalysis: null,
    capital: 0,
    selectedStocks: [],
    portfolioMetrics: null,
    selectedPortfolio: null,
  });
  const directionRef = useRef(1);

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      directionRef.current = 1;
      setCurrentStep((prev) => prev + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      directionRef.current = -1;
      setCurrentStep((prev) => prev - 1);
    }
  };

  const updateWizardData = (data: Partial<WizardData>) => {
    setWizardData((prev) => ({ ...prev, ...data }));
  };

  const renderStep = () => {
    const stepId = STEPS[currentStep].id;
    const stepTitle = STEPS[currentStep].title;

    switch (stepId) {
      case "welcome":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <WelcomeStep onNext={nextStep} />
          </WizardStepErrorBoundary>
        );
      case "risk":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <RiskProfiler
              onNext={nextStep}
              onPrev={prevStep}
              onProfileUpdate={(profile, analysis) =>
                updateWizardData({
                  riskProfile: profile,
                  riskAnalysis: analysis,
                })
              }
              currentProfile={wizardData.riskProfile}
              currentAnalysis={wizardData.riskAnalysis}
            />
          </WizardStepErrorBoundary>
        );
      case "capital":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <CapitalInput
              onNext={nextStep}
              onPrev={prevStep}
              onCapitalUpdate={(capital) => updateWizardData({ capital })}
              currentCapital={wizardData.capital}
            />
          </WizardStepErrorBoundary>
        );
      case "stocks":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <StockSelection
              onNext={nextStep}
              onPrev={prevStep}
              onStocksUpdate={(selectedStocks) =>
                updateWizardData({ selectedStocks })
              }
              onMetricsUpdate={(metrics) =>
                updateWizardData({ portfolioMetrics: metrics })
              }
              selectedStocks={wizardData.selectedStocks}
              riskProfile={wizardData.riskProfile || "moderate"}
              capital={wizardData.capital}
            />
          </WizardStepErrorBoundary>
        );
      case "optimization":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <PortfolioOptimization
              onNext={nextStep}
              onPrev={prevStep}
              selectedStocks={wizardData.selectedStocks}
              riskProfile={wizardData.riskProfile || "moderate"}
              capital={wizardData.capital}
              portfolioMetrics={wizardData.portfolioMetrics}
              initialSelectedPortfolio={wizardData.selectedPortfolio}
              onPortfolioSelection={(portfolio) =>
                updateWizardData({ selectedPortfolio: portfolio })
              }
            />
          </WizardStepErrorBoundary>
        );
      case "stress-test":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <StressTest
              onNext={nextStep}
              onPrev={prevStep}
              selectedPortfolio={wizardData.selectedPortfolio}
              capital={wizardData.capital}
              riskProfile={wizardData.riskProfile || "moderate"}
            />
          </WizardStepErrorBoundary>
        );
      case "finalize":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <FinalizePortfolio
              onComplete={nextStep}
              onPrev={prevStep}
              capital={wizardData.capital}
              riskProfile={wizardData.riskProfile || "moderate"}
              initialTab={finalizeOpenToTab}
              onInitialTabApplied={() => setFinalizeOpenToTab(null)}
            />
          </WizardStepErrorBoundary>
        );
      case "thank-you":
        return (
          <ThankYouStep
            onBackToSummary={() => {
              setFinalizeOpenToTab("tax-cost");
              prevStep();
            }}
            onStartOver={() => {
              directionRef.current = -1;
              setCurrentStep(0);
            }}
          />
        );
      default:
        return (
          <div className="text-center py-12">
            <h3 className="text-xl font-semibold mb-4">
              Step {currentStep + 1} - Coming Soon
            </h3>
            <p className="text-muted-foreground mb-6">
              This step is under development.
            </p>
            <div className="flex gap-4 justify-center">
              {currentStep > 0 && (
                <Button variant="outline" onClick={prevStep}>
                  Previous
                </Button>
              )}
              <Button
                onClick={nextStep}
                disabled={currentStep >= STEPS.length - 1}
              >
                Next Step
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <ThemeSelector />

      <div className="max-w-4xl mx-auto px-4 py-4">
        <div className="mb-3">
          <div className="flex items-center justify-center gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-foreground">
                {STEPS[currentStep].title}
              </h2>
              <span className="text-xs text-muted-foreground">
                Step {currentStep + 1} of {STEPS.length}
              </span>
            </div>
            <span className="text-xs text-muted-foreground tabular-nums">
              {Math.round(progress)}%
            </span>
          </div>
          <div className="relative h-1 w-full overflow-hidden rounded-full bg-secondary">
            <motion.div
              className="h-full bg-primary rounded-full"
              initial={false}
              animate={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 100, damping: 18 }}
            />
          </div>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={currentStep}
            custom={directionRef.current}
            initial={stepTransition.initial(directionRef.current)}
            animate={stepTransition.animate}
            exit={stepTransition.exit(directionRef.current)}
            className="relative"
          >
            {renderStep()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};
