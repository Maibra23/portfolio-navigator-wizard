import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Info, Loader2 } from 'lucide-react';

interface TotalCostsCardProps {
  transactionCosts: any;
  isLoading: boolean;
}

export const TotalCostsCard: React.FC<TotalCostsCardProps> = ({
  transactionCosts,
  isLoading,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-1.5">
          Total & Ongoing Costs
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground" aria-label="Costs info"><Info className="h-3.5 w-3.5" /></span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-sm p-3">
              <p className="text-xs">Setup cost = courtage for initial purchases. Annual rebalancing = courtage for 4 rebalances per year. These costs are included in the 5-year projection and reduce net growth.</p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>
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
                      <span className="inline-flex cursor-help" aria-label="Courtage class info"><Info className="h-3 w-3" /></span>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-sm p-2 text-xs">
                      Start: 50k SEK or 500 trades free. Mini: 1 SEK or 0.25%. Small: 39 SEK or 0.15%. Medium: 69 SEK or 0.069%. Fast Pris: 99 SEK fixed. Per-order fees × number of orders = setup and rebalancing costs used in the 5-year projection.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="font-medium">{transactionCosts.courtageClass}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Setup Cost</div>
                <div className="font-medium">{(transactionCosts.setupCost || 0).toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Annual Rebalancing</div>
                <div className="font-medium">{(transactionCosts.annualRebalancingCost || 0).toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Total First Year</div>
                <div className="font-medium text-lg">{(transactionCosts.totalFirstYearCost || 0).toLocaleString('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} SEK</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No cost calculation available</div>
        )}
      </CardContent>
    </Card>
  );
};
