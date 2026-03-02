import type { WizardData } from "@/hooks/useWizardState";

export const INVALIDATION_RULES: Partial<
  Record<keyof WizardData, (keyof WizardData)[]>
> = {
  riskProfile: ["portfolioMetrics", "selectedPortfolio"],
  selectedStocks: ["portfolioMetrics", "selectedPortfolio"],
};

export function updateWithInvalidation(
  prev: WizardData,
  field: keyof WizardData,
  value: WizardData[keyof WizardData]
): WizardData {
  const updated = { ...prev, [field]: value };
  const toInvalidate = INVALIDATION_RULES[field];
  if (toInvalidate) {
    for (const key of toInvalidate) {
      (updated as Record<string, unknown>)[key] = null;
    }
  }
  return updated;
}
