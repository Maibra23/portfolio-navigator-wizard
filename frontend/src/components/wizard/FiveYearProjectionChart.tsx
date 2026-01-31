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
import { Loader2, TrendingUp } from 'lucide-react';

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
    fetch('/api/portfolio/projection/five-year', {
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          5-Year Projection with Tax Drag
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          X-axis: year (0–5). Y-axis: portfolio value in SEK (k = thousands, M = millions). Three regression-based scenarios with Swedish tax and transaction costs applied each year.
        </p>
      </CardHeader>
      <CardContent>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} label={{ value: 'Year', position: 'insideBottom', offset: -4 }} />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => `${formatSEK(v)}`}
                label={{ value: 'Portfolio value (SEK, k=1000, M=1e6)', angle: -90, position: 'insideLeft', fontSize: 10 }}
              />
              <Tooltip
                formatter={(value: number, name: string) => [value.toLocaleString('sv-SE', { maximumFractionDigits: 0 }) + ' SEK', name]}
                labelFormatter={(label) => `Year ${label}`}
              />
              <Legend />
              <Line type="monotone" dataKey="optimistic" name="Optimistic" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="base" name="Base" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="pessimistic" name="Pessimistic" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
