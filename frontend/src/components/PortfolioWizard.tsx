import { useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
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
import { useWizardState } from "@/hooks/useWizardState";
import { useReducedMotion, getMotionTransition } from "@/hooks/useReducedMotion";
import { useKeyboardNavigation } from "@/hooks/useKeyboardNavigation";
import { useSwipeNavigation } from "@/hooks/useSwipeNavigation";
import type {
  RiskProfile,
  WizardData,
  PortfolioAllocation,
  PortfolioMetrics,
  SelectedPortfolioData,
} from "@/hooks/useWizardState";
import { validateStepRequirements } from "@/utils/wizardValidation";
import { updateWithInvalidation } from "@/utils/wizardInvalidation";
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

export type { RiskProfile, WizardData, PortfolioAllocation, PortfolioMetrics, SelectedPortfolioData };

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

// Motion-aware step transition factory
const createStepTransition = (prefersReducedMotion: boolean) => ({
  initial: (direction: number) => ({
    opacity: 0,
    x: prefersReducedMotion ? 0 : direction > 0 ? 80 : -80,
  }),
  animate: {
    opacity: 1,
    x: 0,
    transition: getMotionTransition(prefersReducedMotion, 0.3),
  },
  exit: (direction: number) => ({
    opacity: 0,
    x: prefersReducedMotion ? 0 : direction > 0 ? -80 : 80,
    transition: getMotionTransition(prefersReducedMotion, 0.25),
  }),
});

export const PortfolioWizard = () => {
  const {
    state: { currentStep, wizardData, finalizeOpenToTab },
    updateStep,
    updateWizardData: setWizardDataRaw,
    setFinalizeOpenToTab,
    resetWizardState,
  } = useWizardState();
  const directionRef = useRef(1);
  const prefersReducedMotion = useReducedMotion();
  const stepTransition = createStepTransition(prefersReducedMotion);

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  // Memoized navigation handlers for keyboard/swipe
  const canGoNext = currentStep < STEPS.length - 1;
  const canGoPrev = currentStep > 0;

  useEffect(() => {
    const validation = validateStepRequirements(currentStep, wizardData);
    if (!validation.valid && validation.redirectTo !== undefined) {
      updateStep(validation.redirectTo);
      toast.error(`Please complete: ${validation.missing.join(", ")}`);
    }
  }, [currentStep, wizardData, updateStep]);

  const nextStep = () => {
    if (currentStep >= STEPS.length - 1) return;
    const next = currentStep + 1;
    const validation = validateStepRequirements(next, wizardData);
    if (!validation.valid) {
      toast.error(`Missing: ${validation.missing.join(", ")}`);
      return;
    }
    directionRef.current = 1;
    updateStep(next);
  };

  const prevStep = () => {
    if (currentStep > 0) {
      directionRef.current = -1;
      updateStep(currentStep - 1);
    }
  };

  const updateWizardData = useCallback((data: Partial<WizardData>) => {
    setWizardDataRaw((prev) => {
      let next = prev;
      for (const key of Object.keys(data) as (keyof WizardData)[]) {
        if ((data as Record<string, unknown>)[key] !== undefined) {
          next = updateWithInvalidation(next, key, (data as Record<string, unknown>)[key] as WizardData[keyof WizardData]);
        }
      }
      return next;
    });
  }, [setWizardDataRaw]);

  // Keyboard navigation (arrow keys for step navigation)
  // Only enable on steps that don't have complex interactions
  const isSimpleStep = currentStep === 0 || currentStep === STEPS.length - 1;
  useKeyboardNavigation({
    onNext: canGoNext && isSimpleStep ? nextStep : undefined,
    onPrev: canGoPrev && isSimpleStep ? prevStep : undefined,
    enabled: isSimpleStep,
  });

  // Swipe navigation for mobile
  const swipeContainerRef = useSwipeNavigation({
    onSwipeLeft: canGoNext && isSimpleStep ? nextStep : undefined,
    onSwipeRight: canGoPrev && isSimpleStep ? prevStep : undefined,
    enabled: isSimpleStep,
    threshold: 75,
  });

  // Detect if user has saved progress (for Welcome Back prompt)
  // Check wizardData for actual progress since currentStep is always reset to 0
  const hasProgress = Boolean(
    wizardData.riskProfile || 
    wizardData.capital > 0 || 
    wizardData.selectedStocks.length > 0
  );
  
  // Determine which step the user would resume to based on their data
  const getSavedStepIndex = (): number => {
    if (wizardData.selectedPortfolio) return 5; // stress-test
    if (wizardData.selectedStocks.length > 0) return 4; // optimization
    if (wizardData.capital > 0) return 3; // stocks
    if (wizardData.riskProfile) return 2; // capital
    return 1; // risk
  };
  
  const savedStepIndex = hasProgress ? getSavedStepIndex() : 0;
  const savedStepName = hasProgress 
    ? STEPS[Math.min(savedStepIndex, STEPS.length - 1)]?.title 
    : undefined;

  const handleContinueProgress = useCallback(() => {
    if (hasProgress && savedStepIndex > 0) {
      directionRef.current = 1;
      updateStep(savedStepIndex);
    }
  }, [hasProgress, savedStepIndex, updateStep]);

  const handleStartFresh = useCallback(() => {
    resetWizardState();
  }, [resetWizardState]);

  const renderStep = () => {
    const stepId = STEPS[currentStep].id;
    const stepTitle = STEPS[currentStep].title;

    switch (stepId) {
      case "welcome":
        return (
          <WizardStepErrorBoundary stepName={stepTitle}>
            <WelcomeStep
              onNext={nextStep}
              hasProgress={hasProgress}
              savedStepName={savedStepName}
              onContinue={handleContinueProgress}
              onStartFresh={handleStartFresh}
            />
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
              resetWizardState();
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
    <div className="min-h-screen bg-background" ref={swipeContainerRef}>
      <ThemeSelector />

      <div className="max-w-5xl mx-auto px-4 md:px-6 py-4">
        {/* Progress header with auto-save indicator */}
        <div className="mb-4">
          <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
            <div className="flex items-center gap-2">
              <h2 className="text-lg md:text-xl font-semibold text-foreground">
                {STEPS[currentStep].title}
              </h2>
              <span className="text-xs md:text-sm text-muted-foreground">
                Step {currentStep + 1} of {STEPS.length}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs md:text-sm text-muted-foreground tabular-nums">
                {Math.round(progress)}%
              </span>
            </div>
          </div>
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
            <motion.div
              className="h-full bg-primary rounded-full"
              initial={false}
              animate={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 100, damping: 18 }}
            />
          </div>
          {/* Step indicator dots with completion animation */}
          <div className="flex justify-between mt-1.5 gap-0.5" aria-hidden="true">
            {STEPS.map((step, i) => (
              <div
                key={i}
                className={`h-1.5 w-1.5 rounded-full shrink-0 transition-all duration-300 ${
                  i < currentStep
                    ? "bg-primary animate-check scale-110"
                    : i === currentStep
                    ? "bg-primary ring-2 ring-primary/30"
                    : "bg-muted"
                }`}
                title={step.title}
              />
            ))}
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
