import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

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
  sharpe_ratio: number;
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
  nvdaWeight
}) => {
  // Create portfolio comparison data
  const portfolioData = [
    {
      name: '100% NVDA',
      weights: [100, 0],
      return: analysis.portfolios[0]?.return || 0,
      risk: analysis.portfolios[0]?.risk || 0,
      sharpe: analysis.portfolios[0]?.sharpe_ratio || 0,
      type: 'static'
    },
    {
      name: '75% NVDA, 25% AMZN',
      weights: [75, 25],
      return: analysis.portfolios[1]?.return || 0,
      risk: analysis.portfolios[1]?.risk || 0,
      sharpe: analysis.portfolios[1]?.sharpe_ratio || 0,
      type: 'static'
    },
    {
      name: '50% NVDA, 50% AMZN',
      weights: [50, 50],
      return: analysis.portfolios[2]?.return || 0,
      risk: analysis.portfolios[2]?.risk || 0,
      sharpe: analysis.portfolios[2]?.sharpe_ratio || 0,
      type: 'static'
    },
    {
      name: '25% NVDA, 75% AMZN',
      weights: [25, 75],
      return: analysis.portfolios[3]?.return || 0,
      risk: analysis.portfolios[3]?.risk || 0,
      sharpe: analysis.portfolios[3]?.sharpe_ratio || 0,
    type: 'static'
    },
    {
      name: '100% AMZN',
      weights: [0, 100],
      return: analysis.portfolios[4]?.return || 0,
      risk: analysis.portfolios[4]?.risk || 0,
      sharpe: analysis.portfolios[4]?.sharpe_ratio || 0,
      type: 'static'
    },
    {
      name: 'Custom Portfolio',
      weights: [nvdaWeight, 100 - nvdaWeight],
      return: customPortfolio.return,
      risk: customPortfolio.risk,
      sharpe: customPortfolio.sharpe_ratio,
      type: 'custom'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Portfolio Comparison</CardTitle>
        <p className="text-muted-foreground">
          Compare different portfolio allocations and their risk-return characteristics
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Portfolio</TableHead>
              <TableHead>NVDA Weight</TableHead>
              <TableHead>AMZN Weight</TableHead>
              <TableHead>Expected Return</TableHead>
              <TableHead>Risk (Volatility)</TableHead>
              <TableHead>Sharpe Ratio</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {portfolioData.map((portfolio, index) => (
              <TableRow 
                key={index}
                className={portfolio.type === 'custom' ? 'bg-blue-50 font-medium' : ''}
              >
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{portfolio.name}</span>
                    {portfolio.type === 'custom' && (
                      <Badge variant="default" className="text-xs">
                        Current
                      </Badge>
                    )}
                      </div>
                </TableCell>
                <TableCell>{portfolio.weights[0]}%</TableCell>
                <TableCell>{portfolio.weights[1]}%</TableCell>
                <TableCell className="text-green-600 font-medium">
                  {(portfolio.return * 100).toFixed(1)}%
                </TableCell>
                <TableCell className="text-orange-600 font-medium">
                  {(portfolio.risk * 100).toFixed(1)}%
                </TableCell>
                <TableCell className="text-blue-600 font-medium">
                  {portfolio.sharpe.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2">Key Insights:</h4>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>• <strong>Diversification Benefit:</strong> Notice how combining NVDA and AMZN reduces overall portfolio risk</li>
            <li>• <strong>Risk-Return Trade-off:</strong> Higher NVDA allocation increases both potential return and risk</li>
            <li>• <strong>Sharpe Ratio:</strong> Measures risk-adjusted returns - higher values indicate better performance per unit of risk</li>
            <li>• <strong>Correlation:</strong> These stocks have a correlation of {(analysis.correlation * 100).toFixed(0)}%, providing diversification benefits</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}; 