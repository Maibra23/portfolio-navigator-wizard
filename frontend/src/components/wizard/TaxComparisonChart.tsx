import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Loader2, TrendingDown, Info } from "lucide-react";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTheme } from "@/hooks/useTheme";
import { getChartTheme, getVisualizationPalette } from "@/utils/chartThemes";

interface TaxComparisonChartProps {
  capital: number;
  taxYear: 2025 | 2026;
  expectedReturn: number;
  selectedAccountType?: string;
  /** When provided, chart uses this instead of fetching (avoids duplicate API calls). */
  comparisonData?:
    | {
        accountType: string;
        annualTax: number;
        effectiveRate: number;
        displayName?: string;
      }[]
    | null;
  /** When true, render only inner content (no Card wrapper). */
  noCard?: boolean;
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
  selectedAccountType,
  comparisonData: comparisonDataProp,
  noCard = false,
}) => {
  const { theme } = useTheme();
  const chartTheme = getChartTheme(theme);
  const palette = getVisualizationPalette(theme);
  const [data, setData] = useState<TaxComparisonData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (comparisonDataProp && comparisonDataProp.length > 0) {
      setData(
        comparisonDataProp.map((r) => ({
          accountType: r.accountType,
          annualTax: r.annualTax,
          effectiveRate: r.effectiveRate,
          displayName: r.displayName ?? r.accountType,
        })),
      );
      setError(null);
      setLoading(false);
      return;
    }

    const fetchComparisons = async () => {
      if (capital <= 0) {
        setData([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const accountTypes = ["ISK", "KF", "AF"];
        const promises = accountTypes.map(async (accountType) => {
          const requestBody: any = { accountType, taxYear };
          if (accountType === "ISK" || accountType === "KF") {
            requestBody.portfolioValue = capital;
          } else {
            requestBody.realizedGains = capital * expectedReturn;
            requestBody.dividends = 0;
            requestBody.fundHoldings = 0;
          }
          const response = await fetch("/api/v1/portfolio/tax/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
          });
          if (!response.ok)
            throw new Error(`Failed to calculate tax for ${accountType}`);
          const result = await response.json();
          const annualTax = result.annualTax || 0;
          const effectiveRate =
            accountType === "AF" && capital > 0
              ? (annualTax / capital) * 100
              : (result.effectiveTaxRate ?? 0);
          return {
            accountType,
            annualTax,
            effectiveRate,
            displayName: accountType,
          };
        });
        const results = await Promise.all(promises);
        setData(results);
      } catch (err: any) {
        console.error("Tax comparison error:", err);
        setError(err.message || "Failed to calculate tax comparisons");
      } finally {
        setLoading(false);
      }
    };

    fetchComparisons();
  }, [capital, taxYear, expectedReturn, comparisonDataProp]);

  if (loading) {
    const loadingContent = (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
        <Loader2 className="h-5 w-5 animate-spin" />
        Calculating tax comparisons...
      </div>
    );
    if (noCard) return loadingContent;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Account Type Tax Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>{loadingContent}</CardContent>
      </Card>
    );
  }

  if (error || data.length === 0) {
    const errorContent = (
      <p className="text-sm text-muted-foreground">
        {error || "Unable to load tax comparisons"}
      </p>
    );
    if (noCard) return errorContent;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Account Type Tax Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>{errorContent}</CardContent>
      </Card>
    );
  }

  // Find the lowest tax option
  const lowestTax = Math.min(...data.map((d) => d.annualTax));
  const potentialSavings = data.find(
    (d) => d.accountType === selectedAccountType,
  )?.annualTax;
  const savingsAmount =
    potentialSavings && potentialSavings > lowestTax
      ? potentialSavings - lowestTax
      : 0;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload;
    return (
      <div className="bg-popover text-popover-foreground border border-border rounded-lg shadow-lg p-3 space-y-1">
        <p className="font-semibold text-sm">{data.displayName}</p>
        <p className="text-xs text-muted-foreground">Annual Tax</p>
        <p className="font-bold text-destructive">
          {data.annualTax.toLocaleString("sv-SE", { maximumFractionDigits: 0 })}{" "}
          SEK
        </p>
        <p className="text-xs text-muted-foreground mt-1">Effective Rate</p>
        <p className="font-semibold">{data.effectiveRate.toFixed(2)}%</p>
      </div>
    );
  };

  const chartContent = (
    <div className="space-y-4">
      {/* Summary row — compact */}
      <div className="grid grid-cols-3 gap-2">
        {data.map((item) => {
          const isSelected = item.accountType === selectedAccountType;
          const isLowest = item.annualTax === lowestTax;
          return (
            <div
              key={item.accountType}
              className={`rounded-md border px-2 py-2 text-center ${
                isSelected
                  ? "border-primary bg-primary/10"
                  : isLowest
                    ? "border-accent bg-accent/10"
                    : "border-border bg-muted/30"
              }`}
            >
              <p className="text-[10px] font-bold">{item.displayName}</p>
              <p className="text-sm font-bold text-destructive">
                {item.annualTax.toLocaleString("sv-SE", {
                  maximumFractionDigits: 0,
                })}{" "}
                SEK
              </p>
              <p className="text-[10px] text-muted-foreground">
                {item.effectiveRate.toFixed(2)}% eff.
              </p>
            </div>
          );
        })}
      </div>

      {/* Chart */}
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis
              dataKey="displayName"
              tick={{ fontSize: 12 }}
              label={{
                value: "Account Type",
                position: "insideBottom",
                offset: -10,
                style: { fontSize: 12 },
              }}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              label={{
                value: "Annual Tax (SEK)",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11 },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
            <Bar
              dataKey="annualTax"
              name="Annual Tax (SEK)"
              radius={[8, 8, 0, 0]}
            >
              {data.map((entry, index) => {
                const isSelected = entry.accountType === selectedAccountType;
                const isLowest = entry.annualTax === lowestTax;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      isLowest
                        ? palette[0]
                        : isSelected
                          ? palette[2]
                          : palette[1]
                    }
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Insights */}
      {savingsAmount > 0 && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
          <p className="text-xs font-semibold text-foreground mb-1">
            Potential Tax Savings
          </p>
          <p className="text-xs text-muted-foreground">
            By switching from <strong>{selectedAccountType}</strong> to the
            lowest-tax option, you could save approximately{" "}
            <strong>
              {savingsAmount.toLocaleString("sv-SE", {
                maximumFractionDigits: 0,
              })}{" "}
              SEK per year
            </strong>{" "}
            in taxes. Over 5 years, that's{" "}
            <strong>
              {(savingsAmount * 5).toLocaleString("sv-SE", {
                maximumFractionDigits: 0,
              })}{" "}
              SEK
            </strong>{" "}
            more for your investments!
          </p>
        </div>
      )}

      {lowestTax === 0 && (
        <div className="bg-accent/10 border border-accent/30 rounded-lg p-3">
          <p className="text-xs font-semibold text-foreground mb-1">
            Tax-Free Investing
          </p>
          <p className="text-xs text-muted-foreground">
            With your capital of {capital.toLocaleString("sv-SE")} SEK and tax
            year {taxYear}, you're below the tax-free level for ISK/KF accounts.
            This means <strong>zero tax</strong> on your investments!
          </p>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        <strong>Note:</strong> AF estimate assumes realized gains equal to your
        expected return ({(expectedReturn * 100).toFixed(1)}%). Actual AF tax
        depends on when and what you sell.
      </p>
    </div>
  );

  if (noCard) return chartContent;
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
            <TooltipContent side="top" className="max-w-sm">
              <p className="mb-2">
                This chart compares the estimated annual tax you would pay under
                each account type, based on your capital of{" "}
                {capital.toLocaleString("sv-SE")} SEK and tax year {taxYear}.
              </p>
              <p className="font-semibold mb-1">Calculation Methods:</p>
              <ul className="space-y-1 list-disc ml-4">
                <li>
                  <strong>ISK/KF:</strong> Schablonbeskattning on capital above
                  tax-free level
                </li>
                <li>
                  <strong>AF:</strong> 30% tax on estimated realized gains
                  (based on {(expectedReturn * 100).toFixed(1)}% expected
                  return)
                </li>
              </ul>
            </TooltipContent>
          </UITooltip>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Based on your capital of {capital.toLocaleString("sv-SE")} SEK and tax
          year {taxYear}
        </p>
      </CardHeader>
      <CardContent>{chartContent}</CardContent>
    </Card>
  );
};
