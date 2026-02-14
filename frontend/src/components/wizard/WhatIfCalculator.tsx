import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Calculator, Info, RefreshCw } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";

interface WhatIfCalculatorProps {
  initialCapital: number;
  initialTaxYear: 2025 | 2026;
  expectedReturn: number;
}

interface TaxResult {
  accountType: string;
  annualTax: number;
  effectiveRate: number;
  afterTaxReturn: number;
}

export const WhatIfCalculator: React.FC<WhatIfCalculatorProps> = ({
  initialCapital,
  initialTaxYear,
  expectedReturn,
}) => {
  const [simulatedCapital, setSimulatedCapital] = useState(initialCapital);
  const [simulatedTaxYear, setSimulatedTaxYear] = useState<2025 | 2026>(
    initialTaxYear,
  );
  const [taxResults, setTaxResults] = useState<TaxResult[]>([]);
  const [loading, setLoading] = useState(false);

  // Calculate taxes for all three account types
  useEffect(() => {
    const calculateTaxes = async () => {
      if (simulatedCapital <= 0) {
        setTaxResults([]);
        return;
      }

      setLoading(true);

      try {
        const accountTypes = ["ISK", "KF", "AF"];
        const promises = accountTypes.map(async (accountType) => {
          const requestBody: any = {
            accountType,
            taxYear: simulatedTaxYear,
          };

          if (accountType === "ISK" || accountType === "KF") {
            requestBody.portfolioValue = simulatedCapital;
          } else {
            const estimatedGains = simulatedCapital * expectedReturn;
            requestBody.realizedGains = estimatedGains;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }

          const response = await fetch("/api/v1/portfolio/tax/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
          });

          if (!response.ok) {
            throw new Error(`Failed to calculate tax for ${accountType}`);
          }

          const result = await response.json();
          const annualTax = result.annualTax || 0;
          const effectiveRate =
            accountType === "AF" && simulatedCapital > 0
              ? (annualTax / simulatedCapital) * 100
              : (result.effectiveTaxRate ?? 0);
          return {
            accountType,
            annualTax,
            effectiveRate,
            afterTaxReturn: result.afterTaxReturn || expectedReturn,
          };
        });

        const results = await Promise.all(promises);
        setTaxResults(results);
      } catch (err) {
        console.error("Tax calculation error:", err);
        setTaxResults([]);
      } finally {
        setLoading(false);
      }
    };

    calculateTaxes();
  }, [simulatedCapital, simulatedTaxYear, expectedReturn]);

  const handleReset = () => {
    setSimulatedCapital(initialCapital);
    setSimulatedTaxYear(initialTaxYear);
  };

  const lowestTax =
    taxResults.length > 0 ? Math.min(...taxResults.map((r) => r.annualTax)) : 0;
  const lowestTaxAccount = taxResults.find((r) => r.annualTax === lowestTax);

  return (
    <Card className="border border-border bg-muted/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Calculator className="h-4 w-4 text-primary" />
          Tax Impact Calculator
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-3.5 w-3.5" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm">
              <p className="text-xs">
                Adjust capital and tax year to see how annual tax differs by
                account type (ISK, KF, AF).
              </p>
            </TooltipContent>
          </Tooltip>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="ml-auto h-6 px-2 text-xs"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reset
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium">Capital</label>
              <span className="text-xs font-semibold text-primary">
                {simulatedCapital.toLocaleString("sv-SE")} SEK
              </span>
            </div>
            <Slider
              value={[simulatedCapital]}
              onValueChange={([val]) => setSimulatedCapital(val)}
              min={50000}
              max={2000000}
              step={10000}
              className="w-full"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>50,000</span>
              <span>2,000,000 SEK</span>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium">Tax Year</label>
            <div className="grid grid-cols-2 gap-1.5">
              <Button
                variant={simulatedTaxYear === 2025 ? "default" : "outline"}
                size="sm"
                onClick={() => setSimulatedTaxYear(2025)}
                className="h-8 text-xs"
              >
                2025 (150k free)
              </Button>
              <Button
                variant={simulatedTaxYear === 2026 ? "default" : "outline"}
                size="sm"
                onClick={() => setSimulatedTaxYear(2026)}
                className="h-8 text-xs"
              >
                2026 (300k free)
              </Button>
            </div>
          </div>
        </div>

        {/* Real-time Results */}
        {loading ? (
          <div className="text-center py-4 text-sm text-muted-foreground">
            Calculating...
          </div>
        ) : taxResults.length > 0 ? (
          <div className="space-y-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
              Annual tax by account type
            </p>
            <div className="grid grid-cols-3 gap-2">
              {taxResults.map((result) => {
                const isLowest = result.annualTax === lowestTax;
                return (
                  <div
                    key={result.accountType}
                    className={`rounded-md border px-2 py-2 text-center ${
                      isLowest
                        ? "border-accent bg-accent/10"
                        : "border-border bg-card"
                    }`}
                  >
                    <p className="text-[10px] font-bold">
                      {result.accountType}
                    </p>
                    <p className="text-sm font-bold text-destructive">
                      {result.annualTax.toLocaleString("sv-SE", {
                        maximumFractionDigits: 0,
                      })}{" "}
                      SEK
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {result.effectiveRate.toFixed(2)}% eff.
                    </p>
                  </div>
                );
              })}
            </div>
            {lowestTaxAccount && (
              <p className="text-[10px] text-muted-foreground">
                Lowest: <strong>{lowestTaxAccount.accountType}</strong> at{" "}
                <strong>
                  {lowestTaxAccount.annualTax.toLocaleString("sv-SE", {
                    maximumFractionDigits: 0,
                  })}{" "}
                  SEK/year
                </strong>
                {lowestTaxAccount.annualTax === 0 && " (below tax-free level)."}
              </p>
            )}
            <p className="text-[10px] text-muted-foreground">
              5-year total: ISK {(taxResults[0]?.annualTax ?? 0) * 5} · KF{" "}
              {(taxResults[1]?.annualTax ?? 0) * 5} · AF{" "}
              {(taxResults[2]?.annualTax ?? 0) * 5} SEK
            </p>
            {(simulatedCapital !== initialCapital ||
              simulatedTaxYear !== initialTaxYear) && (
              <p className="text-[10px] text-muted-foreground">
                Simulated. Your settings:{" "}
                {initialCapital.toLocaleString("sv-SE")} SEK, {initialTaxYear}.
              </p>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
};
