import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, TrendingUp, Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';

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
  taxYear
}) => {
  // Only show for ISK/KF
  if (accountType !== 'ISK' && accountType !== 'KF') {
    return null;
  }

  const taxableAmount = Math.max(0, capital - taxFreeLevel);
  const taxFreeAmount = Math.min(capital, taxFreeLevel);
  const taxFreePercentage = (taxFreeAmount / capital) * 100;
  const taxablePercentage = (taxableAmount / capital) * 100;
  const isTaxFree = taxableAmount === 0;

  return (
    <Card className={isTaxFree ? 'border-green-300 bg-green-50' : 'border-amber-200 bg-amber-50'}>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Shield className={`h-4 w-4 ${isTaxFree ? 'text-green-600' : 'text-amber-600'}`} />
          Your Capital vs. Tax-Free Level
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-help text-muted-foreground hover:text-foreground">
                <Info className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-md p-3">
              <p className="text-xs mb-2">
                For ISK and KF accounts, Swedish tax law provides a <strong>tax-free level</strong> where
                the first portion of your capital is not subject to schablonbeskattning.
              </p>
              <p className="text-xs font-semibold mb-1">Tax-Free Levels:</p>
              <ul className="text-xs space-y-1 list-disc ml-4">
                <li><strong>2025:</strong> 150,000 SEK</li>
                <li><strong>2026:</strong> 300,000 SEK (doubled!)</li>
              </ul>
              <p className="text-xs mt-2">
                Only the amount <strong>above</strong> this level is subject to tax calculation.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          {accountType} account • Tax year {taxYear}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Visual bar representation */}
        <div className="space-y-2">
          <div className="relative h-16 bg-muted rounded-lg overflow-hidden border-2 border-border">
            {taxFreeAmount > 0 && (
              <div
                style={{ width: `${taxFreePercentage}%` }}
                className="absolute left-0 top-0 h-full bg-green-600 flex items-center justify-center transition-all duration-300"
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
                style={{ width: `${taxablePercentage}%`, left: `${taxFreePercentage}%` }}
                className="absolute top-0 h-full bg-amber-600 flex items-center justify-center transition-all duration-300"
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
          <div className="bg-card rounded-lg border-2 border-border p-3">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="h-4 w-4 text-green-600" />
              <p className="text-xs font-semibold text-green-700">Tax-Free Portion</p>
            </div>
            <p className="text-lg font-bold text-green-700">
              {taxFreeAmount.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
            </p>
            <p className="text-xs text-green-600 mt-0.5">
              {taxFreePercentage.toFixed(1)}% of your capital
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Up to {taxFreeLevel.toLocaleString('sv-SE')} SEK limit
            </p>
          </div>

          <div className={`rounded-lg border-2 p-3 ${taxableAmount > 0 ? 'bg-card border-destructive/50' : 'bg-muted/30 border-border'}`}>
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className={`h-4 w-4 ${taxableAmount > 0 ? 'text-red-600' : 'text-gray-400'}`} />
              <p className={`text-xs font-semibold ${taxableAmount > 0 ? 'text-red-700' : 'text-gray-500'}`}>
                Taxable Portion
              </p>
            </div>
            <p className={`text-lg font-bold ${taxableAmount > 0 ? 'text-red-700' : 'text-gray-500'}`}>
              {taxableAmount.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
            </p>
            <p className={`text-xs mt-0.5 ${taxableAmount > 0 ? 'text-red-600' : 'text-gray-500'}`}>
              {taxablePercentage.toFixed(1)}% of your capital
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              {taxableAmount > 0 ? 'Subject to schablonbeskattning' : 'No taxable amount'}
            </p>
          </div>
        </div>

        {/* Insights */}
        {isTaxFree && (
          <div className="bg-green-100 border border-green-300 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Shield className="h-4 w-4 text-green-700 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-green-900 mb-1">
                  Your entire portfolio is tax-free!
                </p>
                <p className="text-xs text-green-800">
                  Since your capital ({capital.toLocaleString('sv-SE')} SEK) is below the {taxYear} tax-free level
                  ({taxFreeLevel.toLocaleString('sv-SE')} SEK), you won't pay any tax on this {accountType} account.
                  This is a great opportunity for tax-free growth!
                </p>
              </div>
            </div>
          </div>
        )}

        {!isTaxFree && taxYear === 2025 && capital <= 300000 && (
          <div className="bg-blue-100 border border-blue-300 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-700 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-blue-900 mb-1">
                  2026 Tax-Free Level Increase
                </p>
                <p className="text-xs text-blue-800">
                  In 2026, the tax-free level increases to 300,000 SEK. With your current capital
                  of {capital.toLocaleString('sv-SE')} SEK, switching to tax year 2026 could
                  {capital <= 300000 ? ' eliminate' : ' significantly reduce'} your tax burden!
                </p>
              </div>
            </div>
          </div>
        )}

        {!isTaxFree && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <TrendingUp className="h-4 w-4 text-amber-700 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-amber-900 mb-1">
                  How Your Tax is Calculated
                </p>
                <p className="text-xs text-amber-800">
                  Only the <strong className="text-red-700">{taxableAmount.toLocaleString('sv-SE')} SEK</strong> above
                  the tax-free level is used to calculate your annual tax. The formula: Taxable amount × Schablonränta × 30%.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
