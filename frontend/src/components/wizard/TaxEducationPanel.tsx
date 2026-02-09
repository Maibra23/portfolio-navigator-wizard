import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { BookOpen, Calculator, TrendingUp } from 'lucide-react';

export const TaxEducationPanel: React.FC = () => {
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
        </Accordion>
      </CardContent>
    </Card>
  );
};
