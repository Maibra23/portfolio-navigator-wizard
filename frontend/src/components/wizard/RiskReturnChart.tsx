import React, { useState } from 'react';
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Plus, Minus, RotateCcw } from 'lucide-react';

interface Asset {
  ticker: string;
  allocation: number;
}

interface PortfolioMetrics {
  expected_return: number;
  risk: number;
  sharpe_ratio: number;
  diversification_score: number;
}

interface EfficientFrontierPoint {
  return: number;
  risk: number;
  sharpe_ratio: number;
  weights: number[];
}

interface RiskReturnAnalysis {
  portfolio_metrics: PortfolioMetrics;
  asset_metrics: Record<string, { return: number; risk: number; sharpe_ratio: number }>;
  efficient_frontier: EfficientFrontierPoint[];
  selected_stocks: Asset[];
  capital: number;
}

interface RiskReturnChartProps {
  portfolioAssets: Asset[];
  efficientFrontier: EfficientFrontierPoint[];
  portfolioMetrics: PortfolioMetrics;
}

export const RiskReturnChart: React.FC<RiskReturnChartProps> = ({
  portfolioAssets,
  efficientFrontier,
  portfolioMetrics,
}) => {
  const [showFrontier, setShowFrontier] = useState(true);
  const [zoom, setZoom] = useState(1);

  // Prepare data for individual assets
  const assetData = portfolioAssets.map((asset) => ({
    name: asset.ticker,
    risk: portfolioMetrics.risk * (asset.allocation / 100),
    return: portfolioMetrics.expected_return * (asset.allocation / 100),
    type: 'asset',
  }));

  // Prepare efficient frontier data
  const frontierData = showFrontier
    ? efficientFrontier.map((point, index) => ({
        name: `Frontier ${index + 1}`,
        risk: point.risk,
        return: point.return,
        type: 'frontier',
      }))
    : [];

  // Find optimal portfolio (highest Sharpe ratio)
  const optimalPortfolio = efficientFrontier.reduce(
    (optimal, current) => (current.sharpe_ratio > optimal.sharpe_ratio ? current : optimal),
    efficientFrontier[0] || { return: 0, risk: 0, sharpe_ratio: 0 }
  );

  const optimalData = showFrontier
    ? [
        {
          name: 'Optimal Portfolio',
          risk: optimalPortfolio.risk,
          return: optimalPortfolio.return,
          type: 'optimal',
        },
      ]
    : [];

  // Current portfolio data
  const currentPortfolioData = [
    {
      name: 'Current Portfolio',
      risk: portfolioMetrics.risk,
      return: portfolioMetrics.expected_return,
      type: 'current',
    },
  ];

  const allData = [...assetData, ...frontierData, ...optimalData, ...currentPortfolioData];

  const formatPercentage = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatCurrency = (value: number) => `$${value.toLocaleString()}`;

  const getPerformanceColor = (sharpeRatio: number) => {
    if (sharpeRatio >= 1.0) return 'bg-green-500';
    if (sharpeRatio >= 0.5) return 'bg-blue-500';
    if (sharpeRatio >= 0.0) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getRiskColor = (risk: number) => {
    if (risk <= 0.15) return 'bg-green-500';
    if (risk <= 0.25) return 'bg-yellow-500';
    if (risk <= 0.35) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getDiversificationColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-500';
    if (score >= 0.4) return 'bg-blue-500';
    if (score >= 0.2) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Risk-Return Analysis</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFrontier(!showFrontier)}
            >
              {showFrontier ? 'Hide' : 'Show'} Frontier
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
            >
              <Minus className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoom(Math.min(2, zoom + 0.1))}
            >
              <Plus className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoom(1)}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart */}
          <div className="lg:col-span-2">
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={allData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="risk"
                  name="Risk"
                  tickFormatter={formatPercentage}
                  label={{ value: 'Risk (Volatility)', position: 'insideBottom', offset: -10 }}
                />
                <YAxis
                  dataKey="return"
                  name="Return"
                  tickFormatter={formatPercentage}
                  label={{ value: 'Expected Return', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    formatPercentage(value),
                    name === 'return' ? 'Expected Return' : 'Risk',
                  ]}
                  labelFormatter={(label) => `Portfolio: ${label}`}
                />
                <Legend />
                
                {/* Efficient Frontier Line */}
                {showFrontier && (
                  <Line
                    type="monotone"
                    dataKey="return"
                    data={frontierData}
                    stroke="#8884d8"
                    strokeWidth={2}
                    dot={false}
                    name="Efficient Frontier"
                  />
                )}
                
                {/* Individual Assets */}
                <Scatter
                  dataKey="return"
                  data={assetData}
                  fill="#82ca9d"
                  name="Individual Assets"
                />
                
                {/* Optimal Portfolio */}
                {showFrontier && (
                  <Scatter
                    dataKey="return"
                    data={optimalData}
                    fill="#ff7300"
                    name="Optimal Portfolio"
                  />
                )}
                
                {/* Current Portfolio */}
                <Scatter
                  dataKey="return"
                  data={currentPortfolioData}
                  fill="#ff0000"
                  name="Current Portfolio"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Metrics */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold mb-3">Portfolio Metrics</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-muted-foreground">Expected Return</span>
                    <Badge variant="secondary">
                      {formatPercentage(portfolioMetrics.expected_return)}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-muted-foreground">Risk (Volatility)</span>
                    <Badge variant="secondary" className={getRiskColor(portfolioMetrics.risk)}>
                      {formatPercentage(portfolioMetrics.risk)}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-muted-foreground">Sharpe Ratio</span>
                    <Badge variant="secondary" className={getPerformanceColor(portfolioMetrics.sharpe_ratio)}>
                      {portfolioMetrics.sharpe_ratio.toFixed(3)}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-muted-foreground">Diversification</span>
                    <Badge variant="secondary" className={getDiversificationColor(portfolioMetrics.diversification_score)}>
                      {(portfolioMetrics.diversification_score * 100).toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-3">Insights</h3>
              <div className="text-sm space-y-2">
                <p>
                  <strong>Performance:</strong>{' '}
                  {portfolioMetrics.sharpe_ratio >= 1.0
                    ? 'Excellent risk-adjusted returns'
                    : portfolioMetrics.sharpe_ratio >= 0.5
                    ? 'Good risk-adjusted returns'
                    : portfolioMetrics.sharpe_ratio >= 0.0
                    ? 'Fair risk-adjusted returns'
                    : 'Poor risk-adjusted returns'}
                </p>
                
                <p>
                  <strong>Diversification:</strong>{' '}
                  {portfolioMetrics.diversification_score >= 0.7
                    ? 'Well diversified portfolio'
                    : portfolioMetrics.diversification_score >= 0.4
                    ? 'Moderately diversified'
                    : portfolioMetrics.diversification_score >= 0.2
                    ? 'Limited diversification'
                    : 'Poor diversification - consider adding more assets'}
                </p>
                
                {showFrontier && optimalPortfolio && (
                  <p>
                    <strong>Optimization:</strong>{' '}
                    {portfolioMetrics.sharpe_ratio >= optimalPortfolio.sharpe_ratio * 0.9
                      ? 'Portfolio is close to optimal'
                      : 'Consider rebalancing for better risk-adjusted returns'}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default RiskReturnChart;