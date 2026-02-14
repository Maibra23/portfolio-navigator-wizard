import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, Loader2 } from "lucide-react";

interface TotalCostsCardProps {
  transactionCosts: any;
  isLoading: boolean;
  /** When true, render only inner content (no Card wrapper). */
  noCard?: boolean;
}

export const TotalCostsCard: React.FC<TotalCostsCardProps> = ({
  transactionCosts,
  isLoading,
  noCard = false,
}) => {
  const content = (
    <>
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Calculating costs...
        </div>
      ) : transactionCosts ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-1">
                Courtage Class
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      className="inline-flex cursor-help"
                      aria-label="Courtage class info"
                    >
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-sm">
                    This is the option you selected in the dropdown above. Each
                    class has different per-order fees (e.g. Start: 50k SEK or
                    500 trades free; Medium: 69 SEK or 0.069% per order). Setup
                    cost = per-order fee × number of holdings for your initial
                    purchases.
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="font-medium">
                {transactionCosts.courtageClass}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Setup Cost</div>
              <div className="font-medium">
                {(transactionCosts.setupCost || 0).toLocaleString("sv-SE", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                SEK
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">
          No cost calculation available
        </div>
      )}
    </>
  );

  if (noCard) return content;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-1.5">
          Transaction Costs (Setup)
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className="inline-flex cursor-help text-muted-foreground hover:text-foreground"
                aria-label="Costs info"
              >
                <Info className="h-3.5 w-3.5" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm">
              <p className="font-semibold mb-1">What this section shows</p>
              <p className="text-xs mb-2">
                The one-time broker fee (courtage) for opening your portfolio:
                one order per holding. Courtage class is the option you selected
                above; the amount is calculated from your portfolio size and
                that selection.
              </p>
              <p className="font-semibold mb-1">Example</p>
              <p className="text-xs">
                You have 4 holdings and choose Medium class. Setup cost is the
                total fee for placing 4 buy orders when you first invest (e.g.
                500,000 SEK across 4 stocks might give a one-time setup of a few
                hundred SEK, depending on the broker&apos;s per-order rules).
                This one-time cost is included in the 5-year projection as a
                drag in year 1.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
};
