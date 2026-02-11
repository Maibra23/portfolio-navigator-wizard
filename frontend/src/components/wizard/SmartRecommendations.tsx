import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, TrendingUp, Sparkles, AlertTriangle, DollarSign } from 'lucide-react';

interface SmartRecommendationsProps {
  capital: number;
  accountType: string;
  taxYear: 2025 | 2026;
  courtagClass: string;
  expectedReturn: number;
  taxCalculation: any;
  transactionCosts: any;
}

interface Recommendation {
  type: 'success' | 'info' | 'warning';
  icon: React.ReactNode;
  title: string;
  description: string;
  savings?: number;
  why?: string;
  priority?: number;
}

export const SmartRecommendations: React.FC<SmartRecommendationsProps> = ({
  capital,
  accountType,
  taxYear,
  courtagClass,
  expectedReturn,
  taxCalculation,
  transactionCosts
}) => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const generateRecommendations = async () => {
      setLoading(true);
      const recs: Recommendation[] = [];

      try {
        // Recommendation 1: Tax Year Optimization
        if (taxYear === 2025 && capital < 300000) {
          const currentTax = taxCalculation?.annualTax || 0;

          // Calculate what tax would be in 2026
          const req2026Body: any = {
            accountType,
            taxYear: 2026
          };

          if (accountType === 'ISK' || accountType === 'KF') {
            req2026Body.portfolioValue = capital;
          } else {
            req2026Body.realizedGains = capital * expectedReturn;
            req2026Body.dividends = 0;
            req2026Body.fundHoldings = 0;
          }

          const response2026 = await fetch('/api/v1/portfolio/tax/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req2026Body),
          });

          if (response2026.ok) {
            const data2026 = await response2026.json();
            const tax2026 = data2026.annualTax || 0;
            const savings = currentTax - tax2026;

            if (savings > 0) {
              recs.push({
                type: 'success',
                icon: <CheckCircle className="h-4 w-4 text-green-600" />,
                title: 'Switch to 2026 Tax Year for Significant Savings',
                description: `Your capital (${capital.toLocaleString('sv-SE')} SEK) is below the 2026 tax-free level (300,000 SEK). By switching to tax year 2026, you could save approximately ${savings.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK per year. Over 5 years, that's ${(savings * 5).toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK more for your investments!`,
                savings: savings * 5,
                why: 'Capital below 300k and 2026 tax-free level → lower or zero tax.'
              });
            }
          }
        }

        // Recommendation 2: Courtage Class Optimization
        if (courtagClass && transactionCosts) {
          const courtageClasses = ['start', 'mini', 'small', 'medium', 'fastPris'];
          const currentIndex = courtageClasses.indexOf(courtagClass);

          // Try to calculate for other courtage classes
          const courtagePromises = courtageClasses.map(async (cls) => {
            if (cls === courtagClass) return null;

            const portfolio = []; // Simplified for recommendation
            const response = await fetch('/api/v1/portfolio/transaction-costs/estimate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                courtageClass: cls,
                portfolio: [{
                  ticker: 'DUMMY',
                  shares: Math.floor(capital / 100),
                  value: capital
                }],
                rebalancingFrequency: 'quarterly'
              }),
            });

            if (response.ok) {
              const data = await response.json();
              return {
                class: cls,
                totalFirstYear: data.totalFirstYearCost || 0,
                annualRebalancing: data.annualRebalancingCost || 0
              };
            }
            return null;
          });

          const courtageResults = await Promise.all(courtagePromises);
          const validResults = courtageResults.filter(r => r !== null) as any[];

          if (validResults.length > 0) {
            const currentTotal = transactionCosts.totalFirstYearCost + (transactionCosts.annualRebalancingCost * 4);
            const bestOption = validResults.reduce((best, curr) => {
              const currTotal = curr.totalFirstYear + (curr.annualRebalancing * 4);
              const bestTotal = best ? best.totalFirstYear + (best.annualRebalancing * 4) : Infinity;
              return currTotal < bestTotal ? curr : best;
            }, null as any);

            if (bestOption) {
              const bestTotal = bestOption.totalFirstYear + (bestOption.annualRebalancing * 4);
              const savings = currentTotal - bestTotal;

              if (savings > 100) {
                recs.push({
                  type: 'info',
                  icon: <TrendingUp className="h-4 w-4 text-blue-600" />,
                  title: `Consider ${bestOption.class.charAt(0).toUpperCase() + bestOption.class.slice(1)} Courtage Class`,
                  description: `With your capital and trading pattern, switching from ${courtagClass} to ${bestOption.class} courtage could save you approximately ${savings.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK over 5 years in transaction costs.`,
                  savings,
                  why: `Estimated 5-year cost with ${bestOption.class} is lower than with ${courtagClass}.`
                });
              }
            }
          }
        }

        // Recommendation 3: Account Type Based on Expected Returns
        if ((accountType === 'ISK' || accountType === 'KF') && expectedReturn < 0.035) {
          recs.push({
            type: 'warning',
            icon: <AlertTriangle className="h-4 w-4 text-amber-600" />,
            title: 'Consider AF Account for Lower Expected Returns',
            description: `Your expected return (${(expectedReturn * 100).toFixed(1)}%) is below the current schablonränta (~3.5%). With AF (Aktie- och Fondkonto), you'd only pay tax on actual gains, which could be more favorable for conservative portfolios or if you plan to hold long-term without rebalancing.`,
            savings: undefined,
            why: 'Expected return below schablonränta → AF tax on actual gains may be lower than ISK schablon.'
          });
        }

        // Recommendation 4: High Returns in ISK/KF
        if ((accountType === 'ISK' || accountType === 'KF') && expectedReturn > 0.08 && capital > 300000) {
          const potentialGains = capital * expectedReturn;
          const actualTax = taxCalculation?.annualTax || 0;
          const afTax = potentialGains * 0.30;
          const savings = afTax - actualTax;

          if (savings > 1000) {
            recs.push({
              type: 'success',
              icon: <DollarSign className="h-4 w-4 text-green-600" />,
              title: 'Great Choice for High-Return Portfolio',
              description: `With your expected return of ${(expectedReturn * 100).toFixed(1)}%, using ${accountType} is optimal. If you were using AF instead, you'd pay approximately ${savings.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK more per year in taxes on realized gains. You're saving money with schablonbeskattning!`,
              savings,
              why: 'Expected return above schablonränta → ISK/KF schablon tax is lower than 30% on gains.'
            });
          }
        }

        // Recommendation 5: Capital Near Tax-Free Threshold
        if ((accountType === 'ISK' || accountType === 'KF')) {
          const taxFreeLevel = taxYear === 2025 ? 150000 : 300000;
          const distanceToThreshold = Math.abs(capital - taxFreeLevel);
          const percentDiff = (distanceToThreshold / taxFreeLevel) * 100;

          if (capital > taxFreeLevel && percentDiff < 20) {
            recs.push({
              type: 'info',
              icon: <Sparkles className="h-4 w-4 text-purple-600" />,
              title: 'Near Tax-Free Threshold',
              description: `Your capital (${capital.toLocaleString('sv-SE')} SEK) is just above the tax-free level (${taxFreeLevel.toLocaleString('sv-SE')} SEK). Consider this when adding more capital - staying below the threshold means zero tax!`,
              savings: undefined,
              why: `Capital within 20% of tax-free level (${taxFreeLevel.toLocaleString('sv-SE')} SEK) for ${taxYear}.`
            });
          }
        }

        // Recommendation 6: Start Courtage with High Capital
        if (courtagClass === 'start' && capital > 50000) {
          recs.push({
            type: 'warning',
            icon: <AlertTriangle className="h-4 w-4 text-amber-600" />,
            title: 'Start Courtage Free Trade Limit',
            description: `You're using Start courtage with ${capital.toLocaleString('sv-SE')} SEK. Remember that Start class provides free trades up to 50,000 SEK or 500 trades. After that, each trade costs money. Plan your trades carefully or consider upgrading to a class with better rates for your capital level.`,
            savings: undefined,
            why: 'Start class: free up to 50k SEK or 500 trades; your capital may exceed that.'
          });
        }

      } catch (error) {
        console.error('Error generating recommendations:', error);
      } finally {
        setLoading(false);
      }

      // Sort by savings (highest first) and assign priority for "by savings" badge
      const withSavings = recs.filter((r) => r.savings != null && r.savings > 0);
      const sorted = [...withSavings].sort((a, b) => (b.savings ?? 0) - (a.savings ?? 0));
      sorted.forEach((r, i) => {
        r.priority = i + 1;
      });
      setRecommendations(recs);
    };

    if (accountType && taxYear && capital > 0) {
      generateRecommendations();
    }
  }, [capital, accountType, taxYear, courtagClass, expectedReturn, taxCalculation, transactionCosts]);

  if (loading) {
    return (
      <Card className="border border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 animate-pulse text-muted-foreground" />
            Smart Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Analyzing your settings...</p>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card className="border border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
            Smart Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Your settings look well-optimized. No suggestions right now.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border bg-card w-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          Smart Recommendations
        </CardTitle>
        <p className="text-xs text-muted-foreground font-normal">
          Personalized suggestions based on your portfolio settings
        </p>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {recommendations.map((rec, index) => (
          <div
            key={index}
            className={`rounded-lg border p-3 ${
              rec.type === 'success'
                ? 'bg-green-500/10 border-green-500/30 dark:bg-green-500/5 dark:border-green-500/20'
                : rec.type === 'info'
                ? 'bg-primary/5 border-primary/20 dark:bg-primary/10 dark:border-primary/30'
                : 'bg-amber-500/10 border-amber-500/30 dark:bg-amber-500/5 dark:border-amber-500/20'
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="mt-0.5 shrink-0 [&_svg]:text-foreground">{rec.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-medium text-foreground">{rec.title}</p>
                  {rec.priority === 1 && rec.savings != null && rec.savings > 0 && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-green-500/20 text-green-700 dark:text-green-400">
                      #1 by savings
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-1">{rec.description}</p>
                {rec.why && (
                  <p className="text-[11px] text-muted-foreground/90 mt-1.5 italic">Why: {rec.why}</p>
                )}
                {rec.savings != null && rec.savings > 0 && (
                  <p className="text-xs font-semibold text-green-600 dark:text-green-400 mt-2">
                    Potential 5-year savings: {rec.savings.toLocaleString('sv-SE', { maximumFractionDigits: 0 })} SEK
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
