import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Shield, PieChart } from "lucide-react";

interface AssetStats {
  ticker: string;
  annualized_return: number;
  annualized_volatility: number;
  price_history: number[];
  last_price: number;
  start_date: string;
  end_date: string;
  data_source?: string;
}

interface TwoAssetPortfolio {
  weights: [number, number];
  return: number;
  risk: number;
  sharpe_ratio: number; // Keep for compatibility but will be set to 0
}

interface TwoAssetAnalysis {
  ticker1: string;
  ticker2: string;
  asset1_stats: AssetStats;
  asset2_stats: AssetStats;
  correlation: number;
  portfolios: TwoAssetPortfolio[];
}

interface TwoAssetChartProps {
  analysis: TwoAssetAnalysis;
  customPortfolio: TwoAssetPortfolio;
  nvdaWeight: number;
}

export const TwoAssetChart: React.FC<TwoAssetChartProps> = ({
  analysis,
  customPortfolio,
  nvdaWeight,
}) => {
  // Create portfolio comparison data
  const portfolioData = [
    {
      name: "A",
      weights: [100, 0],
      return: analysis.portfolios[0]?.return || 0,
      risk: analysis.portfolios[0]?.risk || 0,
      type: "static",
    },
    {
      name: "B",
      weights: [75, 25],
      return: analysis.portfolios[1]?.return || 0,
      risk: analysis.portfolios[1]?.risk || 0,
      type: "static",
    },
    {
      name: "C",
      weights: [50, 50],
      return: analysis.portfolios[2]?.return || 0,
      risk: analysis.portfolios[2]?.risk || 0,
      type: "static",
    },
    {
      name: "D",
      weights: [25, 75],
      return: analysis.portfolios[3]?.return || 0,
      risk: analysis.portfolios[3]?.risk || 0,
      type: "static",
    },
    {
      name: "E",
      weights: [0, 100],
      return: analysis.portfolios[4]?.return || 0,
      risk: analysis.portfolios[4]?.risk || 0,
      type: "static",
    },
    {
      name: "Custom Portfolio",
      weights: [nvdaWeight, 100 - nvdaWeight],
      return: customPortfolio.return,
      risk: customPortfolio.risk,
      type: "custom",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Portfolio Comparison</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Compare different portfolio allocations and their risk-return
          characteristics
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Portfolio</TableHead>
              <TableHead>{analysis.ticker1} Weight</TableHead>
              <TableHead>{analysis.ticker2} Weight</TableHead>
              <TableHead>Expected Return</TableHead>
              <TableHead>Risk (Volatility)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {portfolioData.map((portfolio, index) => (
              <TableRow
                key={index}
                className={
                  portfolio.type === "custom"
                    ? "bg-blue-500/10 font-medium"
                    : ""
                }
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{portfolio.name}</span>
                    {portfolio.type === "custom" && (
                      <Badge variant="default" className="text-xs">
                        Current
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>{portfolio.weights[0]}%</TableCell>
                <TableCell>{portfolio.weights[1]}%</TableCell>
                <TableCell className="text-green-500 font-medium">
                  {(portfolio.return * 100).toFixed(1)}%
                </TableCell>
                <TableCell className="text-orange-500 font-medium">
                  {(portfolio.risk * 100).toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <div className="mt-4 bg-muted/30 rounded-lg p-3 border border-border/50">
          <div className="text-xs text-muted-foreground space-y-2">
            <div>
              <strong className="text-foreground">
                Diversification Benefit:
              </strong>{" "}
              Combining {analysis.ticker1} and {analysis.ticker2} reduces
              overall portfolio risk.
            </div>
            <div>
              <strong className="text-foreground">
                Risk-Return Trade-off:
              </strong>{" "}
              Higher {analysis.ticker1} allocation increases both potential
              return and risk.
            </div>
            <div>
              <strong className="text-foreground">Correlation:</strong> These
              stocks have a correlation of{" "}
              {(analysis.correlation * 100).toFixed(0)}%, providing
              diversification benefits.
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
