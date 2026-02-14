import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, Loader2 } from "lucide-react";
import { formatPercent } from "@/utils/numberFormat";

interface TaxSummaryCardProps {
  taxCalculation: any;
  isLoading: boolean;
  portfolioMetrics: any;
  capital?: number;
  /** When true, render only inner content (no Card wrapper). */
  noCard?: boolean;
}

const MARGINAL_CAPITAL = 50000;
const SCHABLON_2025 = 0.0296;
const SCHABLON_2026 = 0.0355;
const TAX_RATE = 0.3;

function marginalTaxSek(
  capital: number,
  taxFreeLevel: number,
  taxYear: number,
): number {
  const taxableNow = Math.max(0, capital - taxFreeLevel);
  const taxableAfter = Math.max(0, capital + MARGINAL_CAPITAL - taxFreeLevel);
  const increase = taxableAfter - taxableNow;
  const schablon = taxYear === 2026 ? SCHABLON_2026 : SCHABLON_2025;
  return Math.round(increase * schablon * TAX_RATE);
}

export const TaxSummaryCard: React.FC<TaxSummaryCardProps> = ({
  taxCalculation,
  isLoading,
  portfolioMetrics,
  capital,
  noCard = false,
}) => {
  const content = (
    <>
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Calculating tax...
        </div>
      ) : taxCalculation ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                Account Type
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="Account type info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    ISK/KF: tax on imputed income. AF: tax on gains, dividends,
                    and fund holdings. This choice drives the 5-year projection.
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium">{taxCalculation.accountType}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                Tax Year
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="Tax year info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    Different tax-free levels and schablonränta per year;
                    affects annual tax and projection.
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium">{taxCalculation.taxYear}</div>
            </div>
            {taxCalculation.capitalUnderlag !== undefined &&
              taxCalculation.capitalUnderlag !== null && (
                <div>
                  <div className="text-sm text-muted-foreground flex items-center gap-1">
                    Tax Base (Capital)
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span
                          className="inline-flex cursor-help"
                          aria-label="Tax base info"
                        >
                          <Info className="h-3 w-3" />
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        Average capital used as the tax base for ISK/KF. The
                        tax-free amount is deducted first; the remainder ×
                        imputed rate × 30% gives annual tax. This base is used
                        each year in the 5-year projection.
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-medium">
                    {taxCalculation.capitalUnderlag.toLocaleString("sv-SE")} SEK
                  </div>
                </div>
              )}
            {taxCalculation.taxFreeLevel !== undefined &&
              taxCalculation.taxFreeLevel !== null && (
                <div>
                  <div className="text-sm text-muted-foreground flex items-center gap-1">
                    Tax-Free Level
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span
                          className="inline-flex cursor-help"
                          aria-label="Tax-free level info"
                        >
                          <Info className="h-3 w-3" />
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        Amount of capital not subject to tax (ISK/KF). 2025:
                        150,000 SEK; 2026: 300,000 SEK. Only the part above this
                        is taxed.
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-medium">
                    {taxCalculation.taxFreeLevel.toLocaleString("sv-SE")} SEK
                  </div>
                </div>
              )}
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                Annual Tax
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="Annual tax info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    Estimated tax for this year. This amount is subtracted from
                    portfolio growth each year in the 5-year projection.
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium text-lg">
                {(taxCalculation.annualTax || 0).toLocaleString("sv-SE", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                SEK
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                Effective Tax Rate
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="Effective tax rate info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    Annual tax as a percentage of your capital. Shows how much
                    of your portfolio is effectively taxed each year (ISK/KF).
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium">
                {formatPercent((taxCalculation.effectiveTaxRate ?? 0) / 100)}
              </div>
            </div>
          </div>
          {taxCalculation.afterTaxReturn !== undefined && portfolioMetrics && (
            <div className="pt-3 border-t">
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                After-Tax Return
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="After-tax return info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-sm">
                    <p className="font-semibold mb-1">What it means</p>
                    <p className="mb-2">
                      Your portfolio’s expected return after subtracting the
                      estimated tax you pay each year. It’s the growth rate you
                      effectively keep.
                    </p>
                    <p className="font-semibold mb-1">Example</p>
                    <p>
                      If your portfolio’s expected return is 8% and tax costs
                      you about 0.5% of your capital per year, your after-tax
                      return is roughly 7.5%. The higher the tax, the lower the
                      after-tax return.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium text-lg">
                {formatPercent(taxCalculation.afterTaxReturn)}
              </div>
            </div>
          )}
          {(taxCalculation.accountType === "ISK" ||
            taxCalculation.accountType === "KF") &&
            capital != null &&
            capital > 0 &&
            taxCalculation.taxFreeLevel != null &&
            (() => {
              const marginal = marginalTaxSek(
                capital,
                taxCalculation.taxFreeLevel,
                taxCalculation.taxYear,
              );
              if (marginal <= 0) return null;
              return (
                <div className="pt-3 border-t text-xs text-muted-foreground">
                  Adding {MARGINAL_CAPITAL.toLocaleString("sv-SE")} SEK would
                  add approximately {marginal.toLocaleString("sv-SE")} SEK in
                  annual tax ({taxCalculation.accountType} schablon).
                </div>
              );
            })()}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">
          No tax calculation available
        </div>
      )}
    </>
  );

  if (noCard) return content;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-1.5">
          Tax Summary
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className="inline-flex cursor-help text-muted-foreground hover:text-foreground"
                aria-label="Tax summary info"
              >
                <Info className="h-3.5 w-3.5" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm">
              <p className="font-semibold mb-1">What this section shows</p>
              <p className="text-xs mb-2">
                How your chosen account type and tax year determine your
                estimated annual tax. The same logic is applied each year in the
                5-year projection, so lower tax here means higher projected
                growth.
              </p>
              <p className="font-semibold mb-1">Example</p>
              <p className="text-xs">
                You have 500,000 SEK in an ISK and tax year 2026 (tax-free level
                300,000 SEK). Your tax base is 500,000 SEK; the part above
                300,000 is taxed at the imputed rate. Your annual tax and
                after-tax return below reflect that. In an AF account, tax would
                be on realized gains and dividends instead.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
};
