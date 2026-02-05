import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Loader2, TrendingDown, Info } from 'lucide-react';
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface TaxComparisonChartProps {
  capital: number;
  taxYear: 2025 | 2026;
  expectedReturn: number;
  selectedAccountType?: string;
}

interface TaxComparisonData {
  accountType: string;
  annualTax: number;
  effectiveRate: number;
  displayName: string;
}

export const TaxComparisonChart: React.FC<TaxComparisonChartProps> = ({
  capital,
  taxYear,
  expectedReturn,
  selectedAccountType
}) => {
  const [data, setData] = useState<TaxComparisonData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchComparisons = async () => {
      if (capital <= 0) {
        setData([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Fetch tax calculations for all three account types
        const accountTypes = ['ISK', 'KF', 'AF'];
        const promises = accountTypes.map(async (accountType) => {
          const requestBody: any = {
            accountType,
            taxYear
          };

          if (accountType === 'ISK' || accountType === 'KF') {
            requestBody.portfolioValue = capital;
          } else {
            // AF - estimate based on expected return
            const estimatedGains = capital * expectedReturn;
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
            displayName: accountType
          };
        });

        const results = await Promise.all(promises);
        setData(results);
      } catch (err: any) {
        console.error('Tax comparison error:', err);
        setError(err.message || 'Failed to calculate tax comparisons');
      } finally {
        setLoading(false);
      }
    };

    fetchComparisons();
  }, [capital, taxYear, expectedReturn]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Account Type Tax Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
            Calculating tax comparisons...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Account Type Tax Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error || 'Unable to load tax comparisons'}
          </p>
        </CardContent>
      </Card>
    );
  }

  // Find the lowest tax option
  const lowestTax = Math.min(...data.map(d => d.annualTax));
  const potentialSavings = data.find(d => d.accountType === selectedAccountType)?.annualTax;
  const savingsAmount = potentialSavings && potentialSavings > lowestTax ? potentialSavings - lowestTax : 0;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload;
    return (
      <div className="bg-white border rounded-lg shadow-lg p-3 space-y-1">
        <p className="font-semibold text-sm">{data.displayName}</p>
        <p className="text-xs text-muted-foreground">Annual Tax</p>
        <p className="font-bold text-red-600">{data.annualTax.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK</p>
        <p className="text-xs text-muted-foreground mt-1">Effective Rate</p>
        <p className="font-semibold">{data.effectiveRate.toFixed(2)}%</p>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingDown className="h-4 w-4" />
          Account Type Tax Comparison
          <UITooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-md p-3">
              <p className="text-xs mb-2">
                This chart compares the estimated annual tax you would pay under each account type,
                based on your capital of {capital.toLocaleString('sv-SE')} SEK and tax year {taxYear}.
              </p>
              <p className="text-xs font-semibold mb-1">Calculation Methods:</p>
              <ul className="text-xs space-y-1 list-disc ml-4">
                <li><strong>ISK/KF:</strong> Schablonbeskattning on capital above tax-free level</li>
                <li><strong>AF:</strong> 30% tax on estimated realized gains (based on {(expectedReturn * 100).toFixed(1)}% expected return)</li>
              </ul>
            </TooltipContent>
          </UITooltip>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Based on your capital of {capital.toLocaleString('sv-SE')} SEK and tax year {taxYear}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-3">
          {data.map((item) => {
            const isSelected = item.accountType === selectedAccountType;
            const isLowest = item.annualTax === lowestTax;
            return (
              <Card
                key={item.accountType}
                className={`${
                  isSelected
                    ? 'border-blue-500 bg-blue-50'
                    : isLowest
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200'
                }`}
              >
                <CardContent className="pt-3 pb-3">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <p className="text-xs font-bold">{item.displayName}</p>
                    </div>
                    <p className="text-lg font-bold text-red-600">
                      {item.annualTax.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {item.effectiveRate.toFixed(2)}% effective rate
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Chart */}
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="displayName"
                tick={{ fontSize: 12 }}
                label={{ value: 'Account Type', position: 'insideBottom', offset: -10, style: { fontSize: 12 } }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                label={{ value: 'Annual Tax (SEK)', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              <Bar dataKey="annualTax" name="Annual Tax (SEK)" radius={[8, 8, 0, 0]}>
                {data.map((entry, index) => {
                  const isSelected = entry.accountType === selectedAccountType;
                  const isLowest = entry.annualTax === lowestTax;
                  return (
                    <Cell
                      key={`cell-${index}`}
                      fill={isLowest ? '#22c55e' : isSelected ? '#3b82f6' : '#ef4444'}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Insights */}
        {savingsAmount > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p className="text-xs font-semibold text-amber-900 mb-1">
              Potential Tax Savings
            </p>
            <p className="text-xs text-amber-800">
              By switching from <strong>{selectedAccountType}</strong> to the lowest-tax option, you could
              save approximately <strong>{savingsAmount.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK per year</strong> in taxes.
              Over 5 years, that's <strong>{(savingsAmount * 5).toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK</strong> more
              for your investments!
            </p>
          </div>
        )}

        {lowestTax === 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-xs font-semibold text-green-900 mb-1">
              Tax-Free Investing
            </p>
            <p className="text-xs text-green-800">
              With your capital of {capital.toLocaleString('sv-SE')} SEK and tax year {taxYear}, you're below
              the tax-free level for ISK/KF accounts. This means <strong>zero tax</strong> on your investments!
            </p>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          <strong>Note:</strong> AF estimate assumes realized gains equal to your expected return
          ({(expectedReturn * 100).toFixed(1)}%). Actual AF tax depends on when and what you sell.
        </p>
      </CardContent>
    </Card>
  );
};
