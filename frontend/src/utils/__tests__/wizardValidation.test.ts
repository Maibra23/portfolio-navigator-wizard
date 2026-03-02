import { describe, it, expect } from "vitest";
import { validateStepRequirements } from "../wizardValidation";
import type { WizardData } from "@/hooks/useWizardState";

const emptyWizardData: WizardData = {
  riskProfile: null,
  riskAnalysis: null,
  capital: 0,
  selectedStocks: [],
  portfolioMetrics: null,
  selectedPortfolio: null,
};

describe("wizardValidation", () => {
  describe("validateStepRequirements", () => {
    it("allows steps 0, 1, 2 with no data", () => {
      expect(validateStepRequirements(0, emptyWizardData)).toEqual({
        valid: true,
        missing: [],
      });
      expect(validateStepRequirements(1, emptyWizardData)).toEqual({
        valid: true,
        missing: [],
      });
      expect(validateStepRequirements(2, emptyWizardData)).toEqual({
        valid: true,
        missing: [],
      });
    });

    it("requires riskProfile for step 3 (stocks)", () => {
      const result = validateStepRequirements(3, emptyWizardData);
      expect(result.valid).toBe(false);
      expect(result.missing).toContain("Risk Profile");
      expect(result.redirectTo).toBe(1);
    });

    it("allows step 3 when riskProfile is set", () => {
      const withRisk = { ...emptyWizardData, riskProfile: "moderate" as const };
      expect(validateStepRequirements(3, withRisk)).toEqual({
        valid: true,
        missing: [],
      });
    });

    it("requires at least 3 stocks for step 4 (optimization)", () => {
      const withRisk = { ...emptyWizardData, riskProfile: "moderate" as const };
      const result = validateStepRequirements(4, withRisk);
      expect(result.valid).toBe(false);
      expect(result.missing).toContain("At least 3 stocks");
      expect(result.redirectTo).toBe(3);
    });

    it("allows step 4 when 3+ stocks selected", () => {
      const withStocks = {
        ...emptyWizardData,
        riskProfile: "moderate" as const,
        selectedStocks: [
          { symbol: "AAPL", allocation: 33 },
          { symbol: "MSFT", allocation: 33 },
          { symbol: "GOOGL", allocation: 34 },
        ],
      };
      expect(validateStepRequirements(4, withStocks)).toEqual({
        valid: true,
        missing: [],
      });
    });

    it("requires selectedPortfolio for steps 5 and 6", () => {
      const withStocks = {
        ...emptyWizardData,
        riskProfile: "moderate" as const,
        selectedStocks: [
          { symbol: "AAPL", allocation: 33 },
          { symbol: "MSFT", allocation: 33 },
          { symbol: "GOOGL", allocation: 34 },
        ],
      };
      const result5 = validateStepRequirements(5, withStocks);
      expect(result5.valid).toBe(false);
      expect(result5.missing).toContain("Portfolio selection");
      expect(result5.redirectTo).toBe(4);

      const result6 = validateStepRequirements(6, withStocks);
      expect(result6.valid).toBe(false);
      expect(result6.redirectTo).toBe(4);
    });

    it("allows step 7 (thank-you) with no requirements", () => {
      expect(validateStepRequirements(7, emptyWizardData)).toEqual({
        valid: true,
        missing: [],
      });
    });
  });
});
