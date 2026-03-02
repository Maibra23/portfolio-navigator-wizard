import { describe, it, expect } from "vitest";
import { updateWithInvalidation } from "../wizardInvalidation";
import type { WizardData } from "@/hooks/useWizardState";

const base: WizardData = {
  riskProfile: "moderate",
  riskAnalysis: null,
  capital: 50000,
  selectedStocks: [
    { symbol: "AAPL", allocation: 25 },
    { symbol: "MSFT", allocation: 25 },
    { symbol: "GOOGL", allocation: 50 },
  ],
  portfolioMetrics: {
    expectedReturn: 0.08,
    risk: 0.12,
    diversificationScore: 75,
    sharpeRatio: 0.6,
  },
  selectedPortfolio: {
    source: "current",
    tickers: ["AAPL", "MSFT", "GOOGL"],
    weights: { AAPL: 0.25, MSFT: 0.25, GOOGL: 0.5 },
    metrics: { expected_return: 0.08, risk: 0.12, sharpe_ratio: 0.6 },
  },
};

describe("wizardInvalidation", () => {
  describe("updateWithInvalidation", () => {
    it("clears portfolioMetrics and selectedPortfolio when riskProfile changes", () => {
      const next = updateWithInvalidation(base, "riskProfile", "conservative");
      expect(next.riskProfile).toBe("conservative");
      expect(next.portfolioMetrics).toBeNull();
      expect(next.selectedPortfolio).toBeNull();
      expect(next.selectedStocks).toEqual(base.selectedStocks);
    });

    it("clears portfolioMetrics and selectedPortfolio when selectedStocks changes", () => {
      const newStocks = [
        ...base.selectedStocks,
        { symbol: "NVDA", allocation: 25 },
      ].map((s, i, arr) => ({ ...s, allocation: 100 / arr.length }));
      const next = updateWithInvalidation(base, "selectedStocks", newStocks);
      expect(next.selectedStocks).toEqual(newStocks);
      expect(next.portfolioMetrics).toBeNull();
      expect(next.selectedPortfolio).toBeNull();
    });

    it("does not clear downstream when capital changes", () => {
      const next = updateWithInvalidation(base, "capital", 100000);
      expect(next.capital).toBe(100000);
      expect(next.portfolioMetrics).toEqual(base.portfolioMetrics);
      expect(next.selectedPortfolio).toEqual(base.selectedPortfolio);
    });

    it("does not clear downstream when selectedPortfolio changes", () => {
      const newPortfolio = { ...base.selectedPortfolio!, source: "market" as const };
      const next = updateWithInvalidation(base, "selectedPortfolio", newPortfolio);
      expect(next.selectedPortfolio).toEqual(newPortfolio);
    });
  });
});
