import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { BookOpen, Calculator, TrendingUp, Plus, X, ChevronDown, ChevronRight } from 'lucide-react';

const DEFAULT_CAPITAL = 400000;
const DEFAULT_RETURNS_PCT = [1, 3, 5, 7, 10];
const MAX_RETURN_ROWS = 5;

function iskTaxForYear(capital: number, taxYear: 2025 | 2026): number {
  const taxFree = taxYear === 2025 ? 150000 : 300000;
  const schablon = taxYear === 2025 ? 0.0296 : 0.0355;
  const taxable = Math.max(0, capital - taxFree);
  return Math.round(taxable * schablon * 0.30);
}

type BestAccount = 'ISK' | 'KF' | 'AF';

function buildIskAfTableRows(capital: number, taxYear: 2025 | 2026, returnPcts: number[]) {
  const iskTax = iskTaxForYear(capital, taxYear);
  const kfTax = iskTax; // KF uses same calculation as ISK
  const sorted = [...returnPcts].filter((p) => p > 0 && p <= 100).sort((a, b) => a - b);
  return sorted.map((pct) => {
    const gain = (capital * pct) / 100;
    const afTax = Math.round(gain * 0.30);
    const bestTax = Math.min(iskTax, kfTax, afTax);
    const worstTax = Math.max(iskTax, kfTax, afTax);
    const savings = worstTax - bestTax;
    const bestAccount: BestAccount = afTax <= bestTax ? 'AF' : 'ISK'; // ISK/KF tie, so we use ISK when schablon wins
    return { pct, gain, iskTax, kfTax, afTax, savings, bestAccount };
  });
}

export interface TaxEducationPanelProps {
  /** Pre-fill capital in the ISK vs AF table (e.g. user's portfolio capital). */
  initialCapital?: number;
  /** Pre-fill tax year in the ISK vs AF table. */
  initialTaxYear?: 2025 | 2026;
}

export const TaxEducationPanel: React.FC<TaxEducationPanelProps> = ({
  initialCapital,
  initialTaxYear = 2026,
}) => {
  const [tableCapital, setTableCapital] = useState<number>(initialCapital ?? DEFAULT_CAPITAL);
  const [tableTaxYear, setTableTaxYear] = useState<2025 | 2026>(initialTaxYear);
  const [returnPcts, setReturnPcts] = useState<number[]>(DEFAULT_RETURNS_PCT);
  const [customReturnInput, setCustomReturnInput] = useState<string>('');

  useEffect(() => {
    if (initialCapital != null && initialCapital > 0) setTableCapital(initialCapital);
  }, [initialCapital]);
  useEffect(() => {
    setTableTaxYear(initialTaxYear);
  }, [initialTaxYear]);

  const rows = useMemo(
    () => buildIskAfTableRows(tableCapital, tableTaxYear, returnPcts),
    [tableCapital, tableTaxYear, returnPcts],
  );

  const addReturn = () => {
    if (returnPcts.length >= MAX_RETURN_ROWS) return;
    const val = parseFloat(customReturnInput.replace(',', '.'));
    if (!Number.isNaN(val) && val > 0 && val <= 100 && !returnPcts.includes(val)) {
      setReturnPcts((prev) => [...prev, val].sort((a, b) => a - b));
      setCustomReturnInput('');
    }
  };

  const atMaxReturnRows = returnPcts.length >= MAX_RETURN_ROWS;

  const removeReturn = (pct: number) => {
    setReturnPcts((prev) => prev.filter((p) => p !== pct));
  };
  return (
    <Card className="bg-muted border border-border">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-blue-600" />
          Understanding Swedish Investment Taxation
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Learn how different account types affect your investment returns
        </p>
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible className="w-full space-y-2">
          {/* ISK */}
          <AccordionItem value="isk" className="bg-card rounded-lg border border-border px-4">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-green-700">ISK</span>
                </div>
                ISK (Investeringssparkonto) - Investment Savings Account
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm space-y-3 pt-2">
              <div className="space-y-2">
                <p className="text-muted-foreground">
                  ISK uses a <strong>standard tax rate (schablonbeskattning)</strong> based on the Swedish government's
                  interest rate, regardless of your actual investment performance.
                </p>

                <div className="bg-muted p-4 rounded-lg border border-border space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Calculator className="h-4 w-4 text-green-700" />
                    <h4 className="font-semibold text-green-900">Example Calculation (2026):</h4>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Your capital:</span>
                      <span className="font-semibold">500,000 SEK</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Tax-free level (2026):</span>
                      <span className="font-semibold">300,000 SEK</span>
                    </div>
                    <div className="flex justify-between border-t pt-1.5 mt-1.5">
                      <span className="text-muted-foreground">Taxable amount:</span>
                      <span className="font-semibold">200,000 SEK</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">× Schablonränta (2026):</span>
                      <span className="font-semibold">3.55%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">= Tax base:</span>
                      <span className="font-semibold">7,100 SEK</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">× Income tax rate:</span>
                      <span className="font-semibold">30%</span>
                    </div>
                    <div className="flex justify-between border-t pt-1.5 mt-1.5 bg-muted/30 rounded px-2 py-1">
                      <span className="font-bold text-green-700">Annual tax:</span>
                      <span className="font-bold text-green-700">2,130 SEK</span>
                    </div>
                    <div className="flex justify-between bg-muted/30 rounded px-2 py-1">
                      <span className="font-bold text-green-700">Effective rate:</span>
                      <span className="font-bold text-green-700">0.43%</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <p className="font-semibold text-green-700">Advantages:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-muted-foreground">
                    <li>Simple and predictable taxation</li>
                    <li>No need to track individual transactions</li>
                    <li>Great if your returns exceed the schablonränta</li>
                    <li>Tax-free level increased to 300,000 SEK in 2026</li>
                  </ul>

                  <p className="font-semibold text-red-700 mt-2">Disadvantages:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-muted-foreground">
                    <li>Pay tax even if you make losses</li>
                    <li>Cannot deduct losses against other income</li>
                  </ul>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* KF */}
          <AccordionItem value="kf" className="bg-card rounded-lg border border-border px-4">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-blue-700">KF</span>
                </div>
                KF (Kapitalförsäkring) - Capital Insurance
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm space-y-3 pt-2">
              <div className="space-y-2">
                <p className="text-muted-foreground">
                  KF works <strong>almost identically to ISK</strong> in terms of taxation, using the same
                  schablonbeskattning system and tax-free levels.
                </p>

                <div className="bg-muted p-4 rounded-lg border border-border space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="h-4 w-4 text-blue-700" />
                    <h4 className="font-semibold text-blue-900">Key Difference:</h4>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    The main difference is that KF includes <strong>life insurance protection</strong>.
                    Upon death, beneficiaries receive the portfolio value directly without it being part
                    of the estate (may avoid certain fees).
                  </p>
                </div>

                <div className="space-y-1.5 text-xs">
                  <p className="font-semibold text-blue-700">Tax Calculation:</p>
                  <p className="text-muted-foreground">
                    Identical to ISK - see ISK example above. Same tax-free levels (150k for 2025, 300k for 2026),
                    same schablonränta, same 30% rate on imputed income.
                  </p>

                  <p className="font-semibold text-blue-700 mt-2">When to Choose KF:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-muted-foreground">
                    <li>You want simplified inheritance for beneficiaries</li>
                    <li>You have estate planning considerations</li>
                    <li>The insurance provider offers other benefits</li>
                  </ul>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* AF */}
          <AccordionItem value="af" className="bg-card rounded-lg border border-border px-4">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-purple-700">AF</span>
                </div>
                AF (Aktie- och Fondkonto) - Stock and Fund Account
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm space-y-3 pt-2">
              <div className="space-y-2">
                <p className="text-muted-foreground">
                  AF uses <strong>traditional capital gains taxation</strong> - you only pay tax when you
                  realize gains (sell stocks) or receive dividends.
                </p>

                <div className="bg-muted p-4 rounded-lg border border-border space-y-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Calculator className="h-4 w-4 text-purple-700" />
                    <h4 className="font-semibold text-purple-900">Example Calculation:</h4>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Purchase price:</span>
                      <span className="font-semibold">100,000 SEK</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Sale price:</span>
                      <span className="font-semibold">150,000 SEK</span>
                    </div>
                    <div className="flex justify-between border-t pt-1.5 mt-1.5">
                      <span className="text-muted-foreground">Capital gain:</span>
                      <span className="font-semibold text-green-600">50,000 SEK</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">× Capital gains tax:</span>
                      <span className="font-semibold">30%</span>
                    </div>
                    <div className="flex justify-between border-t pt-1.5 mt-1.5 bg-muted/30 rounded px-2 py-1">
                      <span className="font-bold text-purple-700">Tax owed:</span>
                      <span className="font-bold text-purple-700">15,000 SEK</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <p className="font-semibold text-green-700">Advantages:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-muted-foreground">
                    <li>Only pay tax on <strong>realized</strong> gains (when you sell)</li>
                    <li>No tax if you hold stocks long-term without selling</li>
                    <li>Can deduct losses against gains and other capital income</li>
                    <li>Great for buy-and-hold strategies</li>
                  </ul>

                  <p className="font-semibold text-red-700 mt-2">Disadvantages:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-muted-foreground">
                    <li>More complex - must track every transaction</li>
                    <li>30% tax on dividends (withheld automatically)</li>
                    <li>More administrative work for tax filing</li>
                    <li>Rebalancing triggers taxable events</li>
                  </ul>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs">
                  <p className="font-semibold text-amber-900 mb-1">Important for this wizard:</p>
                  <p className="text-amber-800">
                    Since our projections assume quarterly rebalancing, AF will generate taxable events each quarter.
                    For AF accounts, we estimate tax based on expected annual returns.
                  </p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Comparison */}
          <AccordionItem value="comparison" className="bg-card rounded-lg border border-border px-4">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-amber-700">?</span>
                </div>
                Which Account Type Should I Choose?
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm space-y-3 pt-2">
              <div className="space-y-3">
                <div className="bg-muted p-3 rounded-lg border border-border">
                  <p className="font-semibold text-green-900 mb-1.5 text-xs">Choose ISK/KF if:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-xs text-muted-foreground">
                    <li>You expect returns <strong>higher than the schablonränta</strong> (~3-4%)</li>
                    <li>You want simple, predictable taxation</li>
                    <li>You plan to actively trade or rebalance frequently</li>
                    <li>Your capital is close to or below the tax-free level</li>
                  </ul>
                </div>

                <div className="bg-muted p-3 rounded-lg border border-border">
                  <p className="font-semibold text-purple-900 mb-1.5 text-xs">Choose AF if:</p>
                  <ul className="list-disc ml-5 space-y-0.5 text-xs text-muted-foreground">
                    <li>You plan to buy and hold for many years</li>
                    <li>You want to defer taxes until you sell</li>
                    <li>You're comfortable with transaction tracking</li>
                    <li>You expect lower returns or want loss deduction</li>
                  </ul>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="font-semibold text-blue-900 mb-1 text-xs">2026 Tax-Free Level Update:</p>
                  <p className="text-xs text-blue-800">
                    The 2026 increase to 300,000 SEK makes ISK/KF even more attractive for portfolios under this amount.
                    If your capital is below 300k and you select 2026, you'll see <strong>significantly lower or zero tax</strong> in the projection!
                  </p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Collapsible: Tax cost ISK vs. AF – interactive */}
          <AccordionItem value="isk-af-table" className="bg-card rounded-lg border border-border px-4">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-slate-700">ISK vs AF</span>
                </div>
                Tax cost: ISK vs. AF account ({tableCapital.toLocaleString('sv-SE')} SEK)
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm space-y-2 pt-2">
              <p className="text-[11px] text-muted-foreground">
                ISK/KF: fixed rate; AF: 30% of gains. Change capital, tax year or return to update. Max {MAX_RETURN_ROWS} return rows.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-foreground">Capital (SEK)</label>
                  <Input
                    type="number"
                    min={10000}
                    max={10000000}
                    step={10000}
                    value={tableCapital}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10);
                      if (!Number.isNaN(v) && v >= 0) setTableCapital(v);
                    }}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-foreground">Tax year</label>
                  <select
                    className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
                    value={tableTaxYear}
                    onChange={(e) => setTableTaxYear(parseInt(e.target.value, 10) as 2025 | 2026)}
                  >
                    <option value={2025}>2025 (150k tax-free)</option>
                    <option value={2026}>2026 (300k tax-free)</option>
                  </select>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-medium text-foreground">Return rows (%):</span>
                <div className="flex flex-wrap gap-1">
                  {returnPcts.map((pct) => (
                    <span
                      key={pct}
                      className="inline-flex items-center gap-0.5 rounded bg-muted px-1.5 py-0.5 text-[11px]"
                    >
                      {pct}%
                      <button
                        type="button"
                        onClick={() => removeReturn(pct)}
                        className="rounded p-0.5 hover:bg-muted-foreground/20"
                        aria-label={`Remove ${pct}%`}
                      >
                        <X className="h-2.5 w-2.5" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-1 items-center">
                  <Input
                    type="number"
                    min={0.1}
                    max={100}
                    step={0.5}
                    placeholder="e.g. 4"
                    value={customReturnInput}
                    onChange={(e) => setCustomReturnInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addReturn())}
                    className="h-7 w-16 text-[11px]"
                    disabled={atMaxReturnRows}
                  />
                  <Button type="button" variant="outline" size="sm" onClick={addReturn} className="h-7 px-1.5 gap-0.5 text-[11px]" disabled={atMaxReturnRows}>
                    <Plus className="h-2.5 w-2.5" />
                    Add
                  </Button>
                </div>
                {atMaxReturnRows && <span className="text-[10px] text-muted-foreground">Max {MAX_RETURN_ROWS} rows. Remove one to add another.</span>}
              </div>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-[11px] border-collapse">
                  <caption className="sr-only">
                    Tax cost ISK vs. KF vs. AF at different returns, {tableCapital.toLocaleString('sv-SE')} SEK
                  </caption>
                  <thead>
                    <tr className="bg-muted border-b border-border">
                      <th className="text-left p-1.5 font-semibold">Return (%)</th>
                      <th className="text-right p-1.5 font-semibold">Gain (SEK)</th>
                      <th className="text-right p-1.5 font-semibold">ISK (fixed)</th>
                      <th className="text-right p-1.5 font-semibold">KF (fixed)</th>
                      <th className="text-right p-1.5 font-semibold">AF (30%)</th>
                      <th className="text-right p-1.5 font-semibold">Savings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => {
                      const tooltipText = `ISK: ${row.iskTax.toLocaleString('sv-SE')} SEK · KF: ${row.kfTax.toLocaleString('sv-SE')} SEK · AF: ${row.afTax.toLocaleString('sv-SE')} SEK. Best: ${row.bestAccount}. Save ${row.savings.toLocaleString('sv-SE')} SEK vs highest.`;
                      const savingsColor = row.bestAccount === 'AF' ? 'text-amber-700 bg-amber-100' : 'text-green-700 bg-green-100';
                      return (
                        <tr key={`${row.pct}-${i}`} className={i % 2 === 0 ? 'bg-card' : 'bg-muted/30'}>
                          <td className="p-1.5">{row.pct === 7 ? '7% (Avg)' : `${row.pct}%`}</td>
                          <td className="p-1.5 text-right">{row.gain.toLocaleString('sv-SE')} SEK</td>
                          <td className="p-1.5 text-right">{row.iskTax.toLocaleString('sv-SE')} SEK</td>
                          <td className="p-1.5 text-right">{row.kfTax.toLocaleString('sv-SE')} SEK</td>
                          <td className="p-1.5 text-right">{row.afTax.toLocaleString('sv-SE')} SEK</td>
                          <td className="p-1.5 text-right">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`inline-block rounded px-1 font-medium ${row.savings === 0 ? 'text-muted-foreground' : savingsColor}`}>
                                  {row.savings === 0 ? '0 SEK' : `+ ${row.savings.toLocaleString('sv-SE')} SEK`}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs p-2">
                                {tooltipText}
                              </TooltipContent>
                            </Tooltip>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Collapsible: concise math using table capital and highest return */}
              {rows.length > 0 && (() => {
                const taxFreeLevel = tableTaxYear === 2025 ? 150000 : 300000;
                const schablonPct = tableTaxYear === 2025 ? 2.96 : 3.55;
                const taxableCapital = Math.max(0, tableCapital - taxFreeLevel);
                const imputedIncome = Math.round(taxableCapital * (schablonPct / 100));
                const iskTax = iskTaxForYear(tableCapital, tableTaxYear);
                const maxReturnPct = Math.max(...returnPcts);
                const gainAtMax = (tableCapital * maxReturnPct) / 100;
                const afTaxAtMax = Math.round(gainAtMax * 0.30);
                return (
                  <Collapsible className="group mt-2 rounded-md border border-border">
                    <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-[11px] font-medium hover:bg-muted/50">
                      <span>How the math works (capital {tableCapital.toLocaleString('sv-SE')} SEK, highest return {maxReturnPct}%)</span>
                      <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="border-t border-border bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground space-y-2">
                        <p className="font-medium text-foreground">Reference: Capital = {tableCapital.toLocaleString('sv-SE')} SEK, Tax year {tableTaxYear} (tax-free {taxFreeLevel.toLocaleString('sv-SE')} SEK), highest return in table = {maxReturnPct}%.</p>
                        <p><strong>ISK / KF (fixed):</strong> Taxable = {tableCapital.toLocaleString('sv-SE')} − {taxFreeLevel.toLocaleString('sv-SE')} = {taxableCapital.toLocaleString('sv-SE')} SEK. Imputed income = {taxableCapital.toLocaleString('sv-SE')} × {schablonPct}% = {imputedIncome.toLocaleString('sv-SE')} SEK. Tax = {imputedIncome.toLocaleString('sv-SE')} × 30% = <strong>{iskTax.toLocaleString('sv-SE')} SEK</strong> (same every row).</p>
                        <p><strong>AF at {maxReturnPct}%:</strong> Gain = {tableCapital.toLocaleString('sv-SE')} × {maxReturnPct}% = {gainAtMax.toLocaleString('sv-SE')} SEK. Tax = 30% × {gainAtMax.toLocaleString('sv-SE')} = <strong>{afTaxAtMax.toLocaleString('sv-SE')} SEK</strong>.</p>
                        <p><strong>Savings:</strong> For each row, savings = highest tax − lowest tax (the amount you save by choosing the best account).</p>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              })()}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  );
};
