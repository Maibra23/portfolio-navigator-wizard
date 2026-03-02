import type { WizardData } from "@/hooks/useWizardState";

export interface StepValidationResult {
  valid: boolean;
  missing: string[];
  redirectTo?: number;
}

const STEP_REQUIREMENTS: Record<
  number,
  { name: string; requires: ("riskProfile" | "selectedStocks" | "selectedPortfolio")[] }
> = {
  0: { name: "Welcome", requires: [] },
  1: { name: "Risk Profile", requires: [] },
  2: { name: "Capital", requires: [] },
  3: { name: "Stock Selection", requires: ["riskProfile"] },
  4: { name: "Optimization", requires: ["selectedStocks"] },
  5: { name: "Stress Test", requires: ["selectedPortfolio"] },
  6: { name: "Finalize", requires: ["selectedPortfolio"] },
  7: { name: "Thank You", requires: [] },
};

export function validateStepRequirements(
  step: number,
  wizardData: WizardData
): StepValidationResult {
  const config = STEP_REQUIREMENTS[step];
  if (!config) {
    return { valid: true, missing: [] };
  }

  const missing: string[] = [];

  for (const req of config.requires) {
    switch (req) {
      case "riskProfile":
        if (!wizardData.riskProfile) {
          missing.push("Risk Profile");
        }
        break;
      case "selectedStocks":
        if (
          !wizardData.selectedStocks ||
          wizardData.selectedStocks.length < 3
        ) {
          missing.push("At least 3 stocks");
        }
        break;
      case "selectedPortfolio":
        if (!wizardData.selectedPortfolio) {
          missing.push("Portfolio selection");
        }
        break;
    }
  }

  const valid = missing.length === 0;

  let redirectTo: number | undefined;
  if (!valid) {
    if (missing.includes("Portfolio selection")) redirectTo = 4;
    else if (missing.includes("At least 3 stocks")) redirectTo = 3;
    else if (missing.includes("Risk Profile")) redirectTo = 1;
  }

  return { valid, missing, redirectTo };
}
