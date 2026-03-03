/**
 * Onboarding Tooltip Component
 * Provides first-visit guided tooltips for key UI elements
 */

import { useState, useEffect, useCallback } from "react";
import { X, ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TooltipStep {
  id: string;
  target: string; // CSS selector
  title: string;
  description: string;
  position?: "top" | "bottom" | "left" | "right";
}

interface OnboardingTooltipProps {
  steps: TooltipStep[];
  storageKey?: string;
  onComplete?: () => void;
  onSkip?: () => void;
}

const STORAGE_PREFIX = "portfolio-wizard-onboarding-";

export function OnboardingTooltip({
  steps,
  storageKey = "default",
  onComplete,
  onSkip,
}: OnboardingTooltipProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  const fullStorageKey = `${STORAGE_PREFIX}${storageKey}`;

  // Check if onboarding was already completed
  useEffect(() => {
    const completed = localStorage.getItem(fullStorageKey);
    if (!completed) {
      setIsVisible(true);
    }
  }, [fullStorageKey]);

  // Position tooltip relative to target element
  useEffect(() => {
    if (!isVisible || !steps[currentStep]) return;

    const step = steps[currentStep];
    const targetElement = document.querySelector(step.target);

    if (!targetElement) return;

    const rect = targetElement.getBoundingClientRect();
    const tooltipOffset = 12;

    let top = 0;
    let left = 0;

    switch (step.position || "bottom") {
      case "top":
        top = rect.top - tooltipOffset;
        left = rect.left + rect.width / 2;
        break;
      case "bottom":
        top = rect.bottom + tooltipOffset;
        left = rect.left + rect.width / 2;
        break;
      case "left":
        top = rect.top + rect.height / 2;
        left = rect.left - tooltipOffset;
        break;
      case "right":
        top = rect.top + rect.height / 2;
        left = rect.right + tooltipOffset;
        break;
    }

    setPosition({ top, left });

    // Highlight target element
    targetElement.classList.add("ring-2", "ring-primary", "ring-offset-2");

    return () => {
      targetElement.classList.remove("ring-2", "ring-primary", "ring-offset-2");
    };
  }, [isVisible, currentStep, steps]);

  const handleNext = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // Complete onboarding
      localStorage.setItem(fullStorageKey, "true");
      setIsVisible(false);
      onComplete?.();
    }
  }, [currentStep, steps.length, fullStorageKey, onComplete]);

  const handlePrev = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const handleSkip = useCallback(() => {
    localStorage.setItem(fullStorageKey, "true");
    setIsVisible(false);
    onSkip?.();
  }, [fullStorageKey, onSkip]);

  if (!isVisible || !steps[currentStep]) return null;

  const step = steps[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40"
        onClick={handleSkip}
        aria-hidden
      />

      {/* Tooltip */}
      <div
        className={cn(
          "fixed z-50 w-72 bg-card border border-border rounded-lg shadow-lg p-4",
          "animate-in fade-in-0 zoom-in-95 duration-200"
        )}
        style={{
          top: position.top,
          left: position.left,
          transform: "translateX(-50%)",
        }}
        role="dialog"
        aria-labelledby="onboarding-title"
        aria-describedby="onboarding-description"
      >
        {/* Close button */}
        <button
          onClick={handleSkip}
          className="absolute top-2 right-2 p-1 rounded hover:bg-muted text-muted-foreground"
          aria-label="Skip onboarding"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Content */}
        <div className="mb-4">
          <h3
            id="onboarding-title"
            className="font-semibold text-foreground mb-1"
          >
            {step.title}
          </h3>
          <p
            id="onboarding-description"
            className="text-sm text-muted-foreground"
          >
            {step.description}
          </p>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 mb-3">
          {steps.map((_, index) => (
            <div
              key={index}
              className={cn(
                "w-1.5 h-1.5 rounded-full transition-colors",
                index === currentStep
                  ? "bg-primary"
                  : "bg-muted-foreground/30"
              )}
              aria-hidden
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={handlePrev}
            disabled={isFirst}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>

          <span className="text-xs text-muted-foreground">
            {currentStep + 1} of {steps.length}
          </span>

          <Button size="sm" onClick={handleNext} className="gap-1">
            {isLast ? "Done" : "Next"}
            {!isLast && <ChevronRight className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </>
  );
}

/**
 * Reset onboarding state (for testing or user preference)
 */
export function resetOnboarding(storageKey: string = "default") {
  localStorage.removeItem(`${STORAGE_PREFIX}${storageKey}`);
}
