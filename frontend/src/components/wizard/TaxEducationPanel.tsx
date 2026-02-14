import React, { useState, useMemo, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { BookOpen, Scale, Plus, X, ChevronDown, Info } from "lucide-react";

const DEFAULT_CAPITAL = 400000;
const DEFAULT_RETURNS_PCT = [1, 3, 5, 7, 10];
const MAX_RETURN_ROWS = 5;

function iskTaxForYear(capital: number, taxYear: 2025 | 2026): number {
  const taxFree = taxYear === 2025 ? 150000 : 300000;
  const schablon = taxYear === 2025 ? 0.0296 : 0.0355;
  const taxable = Math.max(0, capital - taxFree);
  return Math.round(taxable * schablon * 0.3);
}

type BestAccount = "ISK" | "KF" | "AF";

function buildIskAfTableRows(
  capital: number,
  taxYear: 2025 | 2026,
  returnPcts: number[],
) {
  const iskTax = iskTaxForYear(capital, taxYear);
  const kfTax = iskTax; // KF uses same calculation as ISK
  const sorted = [...returnPcts]
    .filter((p) => p > 0 && p <= 100)
    .sort((a, b) => a - b);
  return sorted.map((pct) => {
    const gain = (capital * pct) / 100;
    const afTax = Math.round(gain * 0.3);
    const bestTax = Math.min(iskTax, kfTax, afTax);
    const worstTax = Math.max(iskTax, kfTax, afTax);
    const savings = worstTax - bestTax;
    const bestAccount: BestAccount = afTax <= bestTax ? "AF" : "ISK"; // ISK/KF tie, so we use ISK when schablon wins
    return { pct, gain, iskTax, kfTax, afTax, savings, bestAccount };
  });
}

export interface TaxEducationPanelProps {
  /** Pre-fill capital in the ISK vs AF table (e.g. user's portfolio capital). */
  initialCapital?: number;
  /** Pre-fill tax year in the ISK vs AF table. */
  initialTaxYear?: 2025 | 2026;
  /** When true, render without outer Card (for embedding inside another card). */
  embedded?: boolean;
}

export const TaxEducationPanel: React.FC<TaxEducationPanelProps> = ({
  initialCapital,
  initialTaxYear = 2026,
  embedded = false,
}) => {
  const [tableCapital, setTableCapital] = useState<number>(
    initialCapital ?? DEFAULT_CAPITAL,
  );
  const [tableTaxYear, setTableTaxYear] = useState<2025 | 2026>(initialTaxYear);
  const [returnPcts, setReturnPcts] = useState<number[]>(DEFAULT_RETURNS_PCT);
  const [customReturnInput, setCustomReturnInput] = useState<string>("");

  useEffect(() => {
    if (initialCapital != null && initialCapital > 0)
      setTableCapital(initialCapital);
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
    const val = parseFloat(customReturnInput.replace(",", "."));
    if (
      !Number.isNaN(val) &&
      val > 0 &&
      val <= 100 &&
      !returnPcts.includes(val)
    ) {
      setReturnPcts((prev) => [...prev, val].sort((a, b) => a - b));
      setCustomReturnInput("");
    }
  };

  const atMaxReturnRows = returnPcts.length >= MAX_RETURN_ROWS;

  const removeReturn = (pct: number) => {
    setReturnPcts((prev) => prev.filter((p) => p !== pct));
  };

  const schablonPctDisplay = tableTaxYear === 2025 ? "2.96" : "3.55";
  const taxFreeDisplay = tableTaxYear === 2025 ? "150,000" : "300,000";

  const inner = (
    <Tabs defaultValue="isk-kf" className="w-full">
      <TabsList className="grid w-full grid-cols-3 h-9">
        <TabsTrigger value="isk-kf" className="text-xs">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center text-[9px] font-bold text-green-700">
              ISK
            </span>
            ISK / KF
          </span>
        </TabsTrigger>
        <TabsTrigger value="af" className="text-xs">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-5 h-5 bg-purple-100 rounded-full flex items-center justify-center text-[9px] font-bold text-purple-700">
              AF
            </span>
            AF
          </span>
        </TabsTrigger>
        <TabsTrigger value="compare" className="text-xs">
          <span className="inline-flex items-center gap-1.5">
            <Scale className="h-3.5 w-3.5" />
            Compare
          </span>
        </TabsTrigger>
      </TabsList>

      {/* ── ISK / KF Tab ── */}
      <TabsContent value="isk-kf" className="mt-3 space-y-3">
        {/* Glossary */}
        <div className="bg-blue-50/60 border border-blue-200/60 rounded-lg p-3 text-xs space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-blue-900">
            <Info className="h-3.5 w-3.5" />
            Key terms
          </div>
          <ul className="space-y-1 text-blue-800">
            <li>
              <strong>Schablonrantan</strong> (standard interest rate) -- Set
              annually by the government: statslanerantan + 1 pp. For{" "}
              {tableTaxYear}: <strong>{schablonPctDisplay}%</strong>. Determined
              by Riksgalden (Swedish National Debt Office).
            </li>
            <li>
              <strong>Schablonintakt</strong> (imputed income) -- A notional
              (deemed) income: taxable capital x schablonrantan. Not real
              income; it is the amount that gets taxed at 30%.
            </li>
            <li>
              <strong>Skattefritt grundavdrag</strong> (tax-free threshold) --
              Capital below this level is exempt from ISK/KF tax. {tableTaxYear}
              : {taxFreeDisplay} SEK.
            </li>
          </ul>
        </div>

        {/* ISK description */}
        <div className="bg-card rounded-lg border border-border p-3 space-y-2">
          <p className="text-xs font-semibold text-green-800">
            ISK (Investeringssparkonto) -- Investment Savings Account
          </p>
          <p className="text-xs text-muted-foreground">
            Uses <strong>schablonbeskattning</strong>: you pay a fixed tax based
            on capital value, regardless of actual gains. Tax = (Capital -
            tax-free threshold) x schablonrantan x 30%.
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="font-medium text-green-700 mb-0.5">Advantages</p>
              <ul className="list-disc ml-4 space-y-0.5 text-muted-foreground">
                <li>Simple, predictable taxation</li>
                <li>No transaction tracking needed</li>
                <li>Great when returns exceed the schablonrantan</li>
                <li>
                  Tax-free level: {taxFreeDisplay} SEK ({tableTaxYear})
                </li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-red-700 mb-0.5">Disadvantages</p>
              <ul className="list-disc ml-4 space-y-0.5 text-muted-foreground">
                <li>Pay tax even on losses</li>
                <li>Cannot deduct losses against other income</li>
              </ul>
            </div>
          </div>
        </div>

        {/* KF note */}
        <div className="bg-card rounded-lg border border-border p-3 space-y-1">
          <p className="text-xs font-semibold text-blue-800">
            KF (Kapitalforsakring) -- Capital Insurance
          </p>
          <p className="text-xs text-muted-foreground">
            Taxed <strong>identically to ISK</strong> (same schablonrantan, same
            tax-free levels). The key difference: KF includes{" "}
            <strong>life insurance protection</strong> -- beneficiaries receive
            the portfolio value directly, bypassing the estate. Choose KF for
            inheritance/estate-planning needs.
          </p>
        </div>

        {/* Guidance callout */}
        <p className="text-[11px] text-muted-foreground bg-muted/50 rounded px-2.5 py-1.5 border border-border">
          ISK/KF is generally better when your expected return exceeds the
          schablonrantan (~{schablonPctDisplay}%). Below the tax-free threshold
          ({taxFreeDisplay} SEK in {tableTaxYear}), ISK/KF tax is zero.
        </p>
      </TabsContent>

      {/* ── AF Tab ── */}
      <TabsContent value="af" className="mt-3 space-y-3">
        <div className="bg-card rounded-lg border border-border p-3 space-y-2">
          <p className="text-xs font-semibold text-purple-800">
            AF (Aktie- och Fondkonto) -- Stock & Fund Account
          </p>
          <p className="text-xs text-muted-foreground">
            Uses <strong>traditional capital gains taxation</strong>: 30% tax on
            realized gains (when you sell) and on dividends. No tax until you
            sell.
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="font-medium text-green-700 mb-0.5">Advantages</p>
              <ul className="list-disc ml-4 space-y-0.5 text-muted-foreground">
                <li>Tax only on realized gains</li>
                <li>No tax while holding long-term</li>
                <li>Losses deductible against gains</li>
                <li>Good for buy-and-hold strategies</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-red-700 mb-0.5">Disadvantages</p>
              <ul className="list-disc ml-4 space-y-0.5 text-muted-foreground">
                <li>Must track every transaction</li>
                <li>30% on dividends (withheld automatically)</li>
                <li>More admin for tax filing</li>
                <li>Rebalancing triggers taxable events</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-[11px]">
          <p className="font-semibold text-amber-900 mb-0.5">
            Note for this wizard
          </p>
          <p className="text-amber-800">
            Our projections assume quarterly rebalancing, which generates
            taxable events each quarter in AF accounts. Tax is estimated from
            expected annual returns.
          </p>
        </div>

        <p className="text-[11px] text-muted-foreground bg-muted/50 rounded px-2.5 py-1.5 border border-border">
          AF is generally better for long-term buy-and-hold with infrequent
          trading, or when you expect returns lower than the schablonrantan and
          want to defer tax.
        </p>
      </TabsContent>

      {/* ── Compare Tab ── */}
      <TabsContent value="compare" className="mt-3 space-y-2">
        <p className="text-[11px] text-muted-foreground">
          ISK/KF: fixed annual tax (schablonbeskattning); AF: 30% of gains.
          Adjust capital, tax year or returns below. Max {MAX_RETURN_ROWS}{" "}
          return rows.
        </p>

        {/* Inputs */}
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-foreground">
              Capital (SEK)
            </label>
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
            <label className="text-[11px] font-medium text-foreground">
              Tax year
            </label>
            <select
              className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
              value={tableTaxYear}
              onChange={(e) =>
                setTableTaxYear(parseInt(e.target.value, 10) as 2025 | 2026)
              }
            >
              <option value={2025}>2025 (150k tax-free)</option>
              <option value={2026}>2026 (300k tax-free)</option>
            </select>
          </div>
        </div>

        {/* Return rows */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-foreground">
            Return rows (%):
          </span>
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
              onKeyDown={(e) =>
                e.key === "Enter" && (e.preventDefault(), addReturn())
              }
              className="h-7 w-16 text-[11px]"
              disabled={atMaxReturnRows}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addReturn}
              className="h-7 px-1.5 gap-0.5 text-[11px]"
              disabled={atMaxReturnRows}
            >
              <Plus className="h-2.5 w-2.5" />
              Add
            </Button>
          </div>
          {atMaxReturnRows && (
            <span className="text-[10px] text-muted-foreground">
              Max {MAX_RETURN_ROWS} rows. Remove one to add another.
            </span>
          )}
        </div>

        {/* Comparison table */}
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-[11px] border-collapse">
            <caption className="sr-only">
              Tax cost ISK vs. KF vs. AF at different returns,{" "}
              {tableCapital.toLocaleString("sv-SE")} SEK
            </caption>
            <thead>
              <tr className="bg-muted border-b border-border">
                <th className="text-left p-1.5 font-semibold">Return (%)</th>
                <th className="text-right p-1.5 font-semibold">Gain (SEK)</th>
                <th className="text-right p-1.5 font-semibold">ISK (fixed)</th>
                <th className="text-right p-1.5 font-semibold">KF (fixed)</th>
                <th className="text-right p-1.5 font-semibold">AF (30%)</th>
                <th className="text-right p-1.5 font-semibold">Savings</th>
                <th className="text-center p-1.5 font-semibold">Best</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const savingsColor =
                  row.bestAccount === "AF"
                    ? "text-amber-700 bg-amber-100"
                    : "text-green-700 bg-green-100";
                const bestBadgeColor =
                  row.bestAccount === "AF"
                    ? "text-purple-700 bg-purple-100"
                    : "text-green-700 bg-green-100";
                return (
                  <tr
                    key={`${row.pct}-${i}`}
                    className={i % 2 === 0 ? "bg-card" : "bg-muted/30"}
                  >
                    <td className="p-1.5">
                      {row.pct === 7 ? "7% (Avg)" : `${row.pct}%`}
                    </td>
                    <td className="p-1.5 text-right">
                      {row.gain.toLocaleString("sv-SE")} SEK
                    </td>
                    <td className="p-1.5 text-right">
                      {row.iskTax.toLocaleString("sv-SE")} SEK
                    </td>
                    <td className="p-1.5 text-right">
                      {row.kfTax.toLocaleString("sv-SE")} SEK
                    </td>
                    <td className="p-1.5 text-right">
                      {row.afTax.toLocaleString("sv-SE")} SEK
                    </td>
                    <td className="p-1.5 text-right">
                      <span
                        className={`inline-block rounded px-1 font-medium ${row.savings === 0 ? "text-muted-foreground" : savingsColor}`}
                      >
                        {row.savings === 0
                          ? "0 SEK"
                          : `+ ${row.savings.toLocaleString("sv-SE")} SEK`}
                      </span>
                    </td>
                    <td className="p-1.5 text-center">
                      <span
                        className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${bestBadgeColor}`}
                      >
                        {row.bestAccount}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Collapsible math explanation with Swedish terms */}
        {rows.length > 0 &&
          (() => {
            const taxFreeLevel = tableTaxYear === 2025 ? 150000 : 300000;
            const schablonPct = tableTaxYear === 2025 ? 2.96 : 3.55;
            const taxableCapital = Math.max(0, tableCapital - taxFreeLevel);
            const imputedIncome = Math.round(
              taxableCapital * (schablonPct / 100),
            );
            const iskTax = iskTaxForYear(tableCapital, tableTaxYear);
            const maxReturnPct = Math.max(...returnPcts);
            const gainAtMax = (tableCapital * maxReturnPct) / 100;
            const afTaxAtMax = Math.round(gainAtMax * 0.3);
            return (
              <Collapsible className="group mt-1 rounded-md border border-border">
                <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-left text-[11px] font-medium hover:bg-muted/50">
                  <span>
                    How the math works (capital{" "}
                    {tableCapital.toLocaleString("sv-SE")} SEK, highest return{" "}
                    {maxReturnPct}%)
                  </span>
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="border-t border-border bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground space-y-2">
                    <p className="font-medium text-foreground">
                      Capital = {tableCapital.toLocaleString("sv-SE")} SEK, Tax
                      year {tableTaxYear} (skattefritt grundavdrag:{" "}
                      {taxFreeLevel.toLocaleString("sv-SE")} SEK),
                      schablonrantan: {schablonPct}%.
                    </p>
                    <p>
                      <strong>ISK / KF:</strong> Taxable ={" "}
                      {tableCapital.toLocaleString("sv-SE")} -{" "}
                      {taxFreeLevel.toLocaleString("sv-SE")} ={" "}
                      {taxableCapital.toLocaleString("sv-SE")} SEK.
                      Schablonintakt (imputed income) ={" "}
                      {taxableCapital.toLocaleString("sv-SE")} x {schablonPct}%
                      = {imputedIncome.toLocaleString("sv-SE")} SEK. Tax ={" "}
                      {imputedIncome.toLocaleString("sv-SE")} x 30% ={" "}
                      <strong>{iskTax.toLocaleString("sv-SE")} SEK</strong>{" "}
                      (same every row).
                    </p>
                    <p>
                      <strong>AF at {maxReturnPct}%:</strong> Gain ={" "}
                      {tableCapital.toLocaleString("sv-SE")} x {maxReturnPct}% ={" "}
                      {gainAtMax.toLocaleString("sv-SE")} SEK. Tax = 30% x{" "}
                      {gainAtMax.toLocaleString("sv-SE")} ={" "}
                      <strong>{afTaxAtMax.toLocaleString("sv-SE")} SEK</strong>.
                    </p>
                    <p>
                      <strong>Savings:</strong> For each row: highest tax -
                      lowest tax = the amount saved by choosing the best
                      account.
                    </p>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            );
          })()}
      </TabsContent>
    </Tabs>
  );

  if (embedded) {
    return (
      <div className="border-t border-border pt-4 mt-4">
        <p className="text-xs font-semibold text-muted-foreground mb-2">
          Swedish Investment Taxation — ISK/KF vs AF
        </p>
        {inner}
      </div>
    );
  }

  return (
    <Card className="bg-muted border border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-blue-600" />
          Swedish Investment Taxation
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-0.5">
          How ISK, KF and AF accounts are taxed differently
        </p>
      </CardHeader>
      <CardContent className="pt-0">{inner}</CardContent>
    </Card>
  );
};
