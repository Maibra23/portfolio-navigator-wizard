/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * 5-Year Projection with Tax Drag
 * - X-axis: Year (0, 1, 2, 3, 4, 5). Year 0 = initial capital.
 * - Y-axis: Portfolio value in SEK. Values are shown as k (thousands) or M (millions) when large.
 * - Three lines: Optimistic (expectedReturn + 0.5*risk), Base (expectedReturn), Pessimistic (expectedReturn - 0.5*risk).
 * - Backend applies Swedish tax (ISK/KF/AF) and Avanza courtage each year; net value is projected.
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, TrendingUp, Info, TrendingDown, Minus } from 'lucide-react';
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface FiveYearProjectionChartProps {
  weights: Record<string, number>;
  capital: number;
  accountType: string | null;
  taxYear: 2025 | 2026;
  courtageClass: string | null;
  expectedReturn: number;
  risk: number;
  rebalancingFrequency?: string;
}

interface ProjectionDataPoint {
  year: number;
  optimistic: number;
  base: number;
  pessimistic: number;
}

export const FiveYearProjectionChart: React.FC<FiveYearProjectionChartProps> = ({
  weights,
  capital,
  accountType,
  taxYear,
  courtageClass,
  expectedReturn,
  risk,
  rebalancingFrequency = 'quarterly',
}) => {
  const [data, setData] = useState<ProjectionDataPoint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canFetch = Boolean(
    accountType &&
    courtageClass &&
    capital > 0 &&
    Object.keys(weights).length > 0 &&
    typeof expectedReturn === 'number' &&
    typeof risk === 'number'
  );

  useEffect(() => {
    if (!canFetch) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch('/api/v1/portfolio/projection/five-year', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        weights,
        capital,
        accountType,
        taxYear,
        courtageClass,
        expectedReturn,
        risk,
        rebalancingFrequency,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((json: { years: number[]; optimistic: number[]; base: number[]; pessimistic: number[] }) => {
        const points: ProjectionDataPoint[] = json.years.map((year, i) => ({
          year,
          optimistic: json.optimistic[i] ?? 0,
          base: json.base[i] ?? 0,
          pessimistic: json.pessimistic[i] ?? 0,
        }));
        setData(points);
      })
      .catch((e) => {
        setError(e.message || 'Failed to load projection');
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [canFetch, weights, capital, accountType, taxYear, courtageClass, expectedReturn, risk, rebalancingFrequency]);

  if (!canFetch) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Select account type and courtage class above to see 5-year projections (optimistic, base, pessimistic) with Swedish tax and costs.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
            Calculating projection...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            5-Year Projection with Tax Drag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error || 'No projection data'}</p>
        </CardContent>
      </Card>
    );
  }

  // Y-axis: portfolio value in SEK. "M" = millions SEK, "k" = thousands SEK (e.g. 1.2M = 1,200,000 SEK)
  const formatSEK = (value: number) =>
    value >= 1e6 ? `${(value / 1e6).toFixed(2)}M` : value >= 1e3 ? `${(value / 1e3).toFixed(2)}k` : value.toFixed(2);

  // Calculate summary metrics
  const initialValue = data[0]?.base || capital;
  const finalBaseValue = data[data.length - 1]?.base || capital;
  const finalOptimisticValue = data[data.length - 1]?.optimistic || capital;
  const finalPessimisticValue = data[data.length - 1]?.pessimistic || capital;

  const totalGrowthBase = finalBaseValue - initialValue;
  const totalGrowthPercentBase = ((finalBaseValue / initialValue - 1) * 100);
  const annualizedReturnBase = (Math.pow(finalBaseValue / initialValue, 1/5) - 1) * 100;

  const totalGrowthOptimistic = finalOptimisticValue - initialValue;
  const totalGrowthPercentOptimistic = ((finalOptimisticValue / initialValue - 1) * 100);

  const totalGrowthPessimistic = finalPessimisticValue - initialValue;
  const totalGrowthPercentPessimistic = ((finalPessimisticValue / initialValue - 1) * 100);

  // Custom tooltip with detailed breakdown
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div className="bg-popover text-popover-foreground border border-border rounded-lg shadow-lg p-4 space-y-2">
        <p className="font-semibold text-sm border-b pb-2">Year {label}</p>
        {payload.map((entry: any, index: number) => {
          const value = entry.value;
          const growth = value - initialValue;
          const growthPercent = ((value / initialValue - 1) * 100).toFixed(1);
          return (
            <div key={index} className="space-y-1">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm font-medium">{entry.name}</span>
              </div>
              <div className="ml-5 text-xs space-y-0.5">
                <p className="font-semibold">{value.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK</p>
                <p className={growth >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {growth >= 0 ? '+' : ''}{growth.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                  ({growthPercent}%)
                </p>
                <p className="text-muted-foreground">
                  After taxes & costs
                </p>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          5-Year Projection (Tax & Cost Adjusted)
          <UITooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm">
              <p className="font-semibold mb-2">How This Projection Works</p>
              <div className="space-y-2">
                <p><strong>Three Scenarios:</strong></p>
                <ul className="list-disc ml-4 space-y-1">
                  <li><span className="text-green-600 font-semibold">Optimistic:</span> Expected return + 50% of risk (upside scenario)</li>
                  <li><span className="text-blue-600 font-semibold">Base:</span> Expected return (most likely scenario)</li>
                  <li><span className="text-red-600 font-semibold">Pessimistic:</span> Expected return - 50% of risk (downside scenario)</li>
                </ul>
                <p className="mt-2"><strong>What's Included:</strong></p>
                <ul className="list-disc ml-4 space-y-1">
                  <li>Swedish tax ({accountType}) calculated annually</li>
                  <li>Transaction costs ({courtageClass} class)</li>
                  <li>Quarterly rebalancing costs</li>
                  <li>Compound growth effects</li>
                </ul>
                <p className="mt-2 text-muted-foreground italic">
                  All values shown are NET after deducting taxes and costs each year.
                </p>
              </div>
            </TooltipContent>
          </UITooltip>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Three scenarios showing your portfolio growth after Swedish taxes and transaction costs
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {accountType === 'AF' && (
          <p className="text-xs text-muted-foreground rounded-lg border border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800 px-3 py-2">
            We assume gains are realized each year (e.g. rebalancing); actual AF tax depends on when you sell.
          </p>
        )}
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Card className="border-green-200 bg-green-50/50">
            <CardContent className="pt-4 pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <TrendingUp className="h-3.5 w-3.5 text-green-600" />
                    <p className="text-xs font-medium text-green-700">Optimistic</p>
                  </div>
                  <p className="text-xl font-bold text-green-700">
                    {finalOptimisticValue.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                  </p>
                  <p className="text-xs text-green-600 mt-0.5">
                    +{totalGrowthOptimistic.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                    ({totalGrowthPercentOptimistic.toFixed(1)}%)
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-blue-200 bg-blue-50/50">
            <CardContent className="pt-4 pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Minus className="h-3.5 w-3.5 text-blue-600" />
                    <p className="text-xs font-medium text-blue-700">Base Scenario</p>
                  </div>
                  <p className="text-xl font-bold text-blue-700">
                    {finalBaseValue.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                  </p>
                  <p className="text-xs text-blue-600 mt-0.5">
                    +{totalGrowthBase.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                    ({totalGrowthPercentBase.toFixed(1)}%)
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    {annualizedReturnBase.toFixed(2)}% annualized
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-red-200 bg-red-50/50">
            <CardContent className="pt-4 pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <TrendingDown className="h-3.5 w-3.5 text-red-600" />
                    <p className="text-xs font-medium text-red-700">Pessimistic</p>
                  </div>
                  <p className="text-xl font-bold text-red-700">
                    {finalPessimisticValue.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                  </p>
                  <p className="text-xs text-red-600 mt-0.5">
                    {totalGrowthPessimistic >= 0 ? '+' : ''}{totalGrowthPessimistic.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                    ({totalGrowthPercentPessimistic.toFixed(1)}%)
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Alert explaining what scenarios mean */}
        <Alert className="bg-blue-50 border-blue-200">
          <Info className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-xs text-blue-900">
            <strong>Understanding the scenarios:</strong> These projections use your portfolio's expected return
            ({(expectedReturn * 100).toFixed(1)}%) and risk ({(risk * 100).toFixed(1)}%) to model three possible outcomes.
            The <strong>Base scenario</strong> is most likely. Hover over the chart lines for year-by-year details.
          </AlertDescription>
        </Alert>

        {/* Chart */}
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11 }}
                label={{ value: 'Year', position: 'insideBottom', offset: -4, style: { fontSize: 11 } }}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => `${formatSEK(v)}`}
                label={{ value: 'Portfolio Value (SEK)', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Line
                type="monotone"
                dataKey="optimistic"
                name="Optimistic"
                stroke="#22c55e"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#22c55e' }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="base"
                name="Base"
                stroke="#3b82f6"
                strokeWidth={3}
                dot={{ r: 5, fill: '#3b82f6' }}
                activeDot={{ r: 7 }}
              />
              <Line
                type="monotone"
                dataKey="pessimistic"
                name="Pessimistic"
                stroke="#ef4444"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#ef4444' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Additional context */}
        <div className="text-xs text-muted-foreground space-y-1 border-t pt-3">
          <p><strong>Note:</strong> All projections include:</p>
          <ul className="list-disc ml-5 space-y-0.5">
            <li>Annual {accountType} tax based on {taxYear} rates</li>
            <li>Initial setup costs and quarterly rebalancing costs ({courtageClass} courtage class)</li>
            <li>These are estimates based on historical patterns and current tax law</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
