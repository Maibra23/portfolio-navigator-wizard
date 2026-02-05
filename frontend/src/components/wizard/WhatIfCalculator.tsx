import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Calculator, Info, RefreshCw } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';

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
  expectedReturn
}) => {
  const [simulatedCapital, setSimulatedCapital] = useState(initialCapital);
  const [simulatedTaxYear, setSimulatedTaxYear] = useState<2025 | 2026>(initialTaxYear);
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
        const accountTypes = ['ISK', 'KF', 'AF'];
        const promises = accountTypes.map(async (accountType) => {
          const requestBody: any = {
            accountType,
            taxYear: simulatedTaxYear
          };

          if (accountType === 'ISK' || accountType === 'KF') {
            requestBody.portfolioValue = simulatedCapital;
          } else {
            const estimatedGains = simulatedCapital * expectedReturn;
            requestBody.realizedGains = estimatedGains;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }

          const response = await fetch('/api/portfolio/tax/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
          });

          if (!response.ok) {
            throw new Error(`Failed to calculate tax for ${accountType}`);
          }

          const result = await response.json();
          return {
            accountType,
            annualTax: result.annualTax || 0,
            effectiveRate: result.effectiveTaxRate || 0,
            afterTaxReturn: result.afterTaxReturn || expectedReturn
          };
        });

        const results = await Promise.all(promises);
        setTaxResults(results);
      } catch (err) {
        console.error('Tax calculation error:', err);
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

  const lowestTax = taxResults.length > 0 ? Math.min(...taxResults.map(r => r.annualTax)) : 0;
  const lowestTaxAccount = taxResults.find(r => r.annualTax === lowestTax);

  return (
    <Card className="border-2 border-dashed border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Calculator className="h-5 w-5 text-blue-600" />
          Tax Impact Calculator - Try Different Scenarios
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-md p-3">
              <p className="text-xs">
                Use the sliders to explore how different capital amounts and tax years affect your annual tax burden.
                This helps you understand the impact of your investment decisions and tax planning opportunities.
              </p>
            </TooltipContent>
          </Tooltip>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="ml-auto h-7 px-2"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reset
          </Button>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Experiment with different values to see how taxes change
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Capital Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Adjust Capital Amount</label>
            <span className="text-sm font-bold text-blue-700">
              {simulatedCapital.toLocaleString('sv-SE')} SEK
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
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>50,000 SEK</span>
            <span>2,000,000 SEK</span>
          </div>
        </div>

        {/* Tax Year Toggle */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Tax Year</label>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant={simulatedTaxYear === 2025 ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSimulatedTaxYear(2025)}
              className="w-full"
            >
              2025
              <span className="ml-2 text-xs opacity-70">(150k free)</span>
            </Button>
            <Button
              variant={simulatedTaxYear === 2026 ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSimulatedTaxYear(2026)}
              className="w-full"
            >
              2026
              <span className="ml-2 text-xs opacity-70">(300k free)</span>
            </Button>
          </div>
        </div>

        {/* Real-time Results */}
        {loading ? (
          <div className="text-center py-4 text-sm text-muted-foreground">
            Calculating...
          </div>
        ) : taxResults.length > 0 ? (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-blue-900">Annual Tax Breakdown:</p>
            <div className="grid grid-cols-3 gap-2">
              {taxResults.map((result) => {
                const isLowest = result.annualTax === lowestTax;
                return (
                  <Card
                    key={result.accountType}
                    className={`${
                      isLowest
                        ? 'border-2 border-green-500 bg-green-50'
                        : 'border border-gray-200 bg-white'
                    }`}
                  >
                    <CardContent className="pt-3 pb-3 text-center">
                      <div className="flex items-center justify-center gap-1 mb-1">
                        <p className="text-xs font-bold">{result.accountType}</p>
                      </div>
                      <p className="text-base font-bold text-red-700">
                        {result.annualTax.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        {result.effectiveRate.toFixed(2)}% rate
                      </p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Insight */}
            {lowestTaxAccount && (
              <div className="bg-white rounded-lg border border-green-300 p-3">
                <p className="text-xs font-semibold text-green-900 mb-1">
                  Result:
                </p>
                <p className="text-xs text-green-800">
                  With <strong>{simulatedCapital.toLocaleString('sv-SE')} SEK</strong> in tax year{' '}
                  <strong>{simulatedTaxYear}</strong>, the <strong>{lowestTaxAccount.accountType}</strong>{' '}
                  account type offers the lowest tax burden at{' '}
                  <strong>{lowestTaxAccount.annualTax.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK/year</strong>.
                </p>
                {lowestTaxAccount.annualTax === 0 && (
                  <p className="text-xs text-green-700 mt-1 font-semibold">
                    Zero tax! Your capital is below the tax-free level.
                  </p>
                )}
              </div>
            )}

            {/* 5-year projection */}
            <div className="bg-blue-100 border border-blue-300 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-900 mb-2">
                5-Year Tax Impact:
              </p>
              <div className="grid grid-cols-3 gap-2">
                {taxResults.map((result) => (
                  <div key={result.accountType} className="text-center">
                    <p className="text-[10px] text-blue-700 font-medium">{result.accountType}</p>
                    <p className="text-xs font-bold text-blue-900">
                      {(result.annualTax * 5).toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-blue-700 mt-2">
                Total tax over 5 years (assuming constant capital)
              </p>
            </div>

            {/* Comparison to current */}
            {simulatedCapital !== initialCapital || simulatedTaxYear !== initialTaxYear ? (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-2">
                <p className="text-[10px] text-amber-800">
                  <strong>Note:</strong> These are simulated values. Your actual settings are{' '}
                  {initialCapital.toLocaleString('sv-SE')} SEK and tax year {initialTaxYear}.
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
};
