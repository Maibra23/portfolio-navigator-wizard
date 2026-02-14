import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield, TrendingUp, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Progress } from "@/components/ui/progress";

interface TaxFreeVisualizationProps {
  capital: number;
  taxFreeLevel: number;
  accountType: string;
  taxYear: 2025 | 2026;
}

export const TaxFreeVisualization: React.FC<TaxFreeVisualizationProps> = ({
  capital,
  taxFreeLevel,
  accountType,
  taxYear,
}) => {
  // Only show for ISK/KF
  if (accountType !== "ISK" && accountType !== "KF") {
    return null;
  }

  const taxableAmount = Math.max(0, capital - taxFreeLevel);
  const taxFreeAmount = Math.min(capital, taxFreeLevel);
  const taxFreePercentage = (taxFreeAmount / capital) * 100;
  const taxablePercentage = (taxableAmount / capital) * 100;
  const isTaxFree = taxableAmount === 0;

  return (
    <Card
      className={`rounded-lg ${isTaxFree ? "border-accent/30 bg-accent/10" : "border-border bg-muted/50"}`}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Shield
            className={`h-3.5 w-3.5 ${isTaxFree ? "text-accent-foreground" : "text-muted-foreground"}`}
          />
          Your Capital vs. Tax-Free Level
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-3.5 w-3.5" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm">
              <p className="font-semibold mb-1">Why this section</p>
              <p className="mb-2 text-xs">
                Shows how much of your capital is below the tax-free level (no
                tax) vs above (taxed). Lets you see at a glance if you are in
                the zero-tax zone.
              </p>
              <p className="text-xs mb-1">
                ISK/KF: first portion of capital is exempt; only the amount
                above the level is subject to schablonbeskattning. 2025: 150,000
                SEK; 2026: 300,000 SEK.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
        <p className="text-[10px] text-muted-foreground">
          {accountType} • Tax year {taxYear}
        </p>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Visual bar representation */}
        <div className="space-y-1.5">
          <div className="relative h-10 bg-muted rounded-md overflow-hidden border border-border">
            {taxFreeAmount > 0 && (
              <div
                style={{ width: `${taxFreePercentage}%` }}
                className="absolute left-0 top-0 h-full bg-accent flex items-center justify-center transition-all duration-300"
              >
                {taxFreePercentage > 20 && (
                  <div className="text-white text-xs font-bold px-2 text-center">
                    <Shield className="h-3 w-3 inline mr-1" />
                    Tax-Free
                  </div>
                )}
              </div>
            )}
            {taxableAmount > 0 && (
              <div
                style={{
                  width: `${taxablePercentage}%`,
                  left: `${taxFreePercentage}%`,
                }}
                className="absolute top-0 h-full bg-destructive/80 flex items-center justify-center transition-all duration-300"
              >
                {taxablePercentage > 20 && (
                  <div className="text-white text-xs font-bold px-2 text-center">
                    <TrendingUp className="h-3 w-3 inline mr-1" />
                    Taxable
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Progress bar alternative for mobile */}
          <div className="md:hidden">
            <Progress value={taxFreePercentage} className="h-3" />
          </div>
        </div>

        {/* Breakdown */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-card rounded-lg border-2 border-accent/50 p-3">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="h-4 w-4 text-accent-foreground" />
              <p className="text-xs font-semibold text-foreground">
                Tax-Free Portion
              </p>
            </div>
            <p className="text-lg font-bold text-foreground">
              {taxFreeAmount.toLocaleString("sv-SE", {
                maximumFractionDigits: 0,
              })}{" "}
              SEK
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {taxFreePercentage.toFixed(1)}% of your capital
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Up to {taxFreeLevel.toLocaleString("sv-SE")} SEK limit
            </p>
          </div>

          <div
            className={`rounded-lg border-2 p-3 ${taxableAmount > 0 ? "bg-card border-destructive/50" : "bg-muted/30 border-border"}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp
                className={`h-4 w-4 ${taxableAmount > 0 ? "text-destructive" : "text-muted-foreground"}`}
              />
              <p
                className={`text-xs font-semibold ${taxableAmount > 0 ? "text-destructive" : "text-muted-foreground"}`}
              >
                Taxable Portion
              </p>
            </div>
            <p
              className={`text-lg font-bold ${taxableAmount > 0 ? "text-destructive" : "text-muted-foreground"}`}
            >
              {taxableAmount.toLocaleString("sv-SE", {
                maximumFractionDigits: 0,
              })}{" "}
              SEK
            </p>
            <p
              className={`text-xs mt-0.5 ${taxableAmount > 0 ? "text-destructive" : "text-muted-foreground"}`}
            >
              {taxablePercentage.toFixed(1)}% of your capital
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              {taxableAmount > 0
                ? "Subject to schablonbeskattning"
                : "No taxable amount"}
            </p>
          </div>
        </div>

        {/* Insights */}
        {isTaxFree && (
          <div className="bg-accent/10 border border-accent/30 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Shield className="h-4 w-4 text-accent-foreground mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">
                  Your entire portfolio is tax-free!
                </p>
                <p className="text-xs text-muted-foreground">
                  Since your capital ({capital.toLocaleString("sv-SE")} SEK) is
                  below the {taxYear} tax-free level (
                  {taxFreeLevel.toLocaleString("sv-SE")} SEK), you won't pay any
                  tax on this {accountType} account. This is a great opportunity
                  for tax-free growth!
                </p>
              </div>
            </div>
          </div>
        )}

        {!isTaxFree && taxYear === 2025 && capital <= 300000 && (
          <div className="bg-primary/10 border border-primary/30 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-primary mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">
                  2026 Tax-Free Level Increase
                </p>
                <p className="text-xs text-muted-foreground">
                  In 2026, the tax-free level increases to 300,000 SEK. With
                  your current capital of {capital.toLocaleString("sv-SE")} SEK,
                  switching to tax year 2026 could
                  {capital <= 300000
                    ? " eliminate"
                    : " significantly reduce"}{" "}
                  your tax burden!
                </p>
              </div>
            </div>
          </div>
        )}

        {!isTaxFree && (
          <div className="bg-muted/50 border border-border rounded-lg p-3">
            <div className="flex items-start gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-foreground mb-1">
                  How Your Tax is Calculated
                </p>
                <p className="text-xs text-muted-foreground">
                  Only the{" "}
                  <strong className="text-destructive">
                    {taxableAmount.toLocaleString("sv-SE")} SEK
                  </strong>{" "}
                  above the tax-free level is used to calculate your annual tax.
                  The formula: Taxable amount × Schablonränta × 30%.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
