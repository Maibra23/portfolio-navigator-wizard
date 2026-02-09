/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { PieChart as PieChartIcon, BarChart3 } from 'lucide-react';

interface Sector {
  sector: string;
  ticker_count: number;
  tickers: string[];
  industries: string[];
  exchanges: string[];
  countries: string[];
  average_return: number;
  average_risk: number;
  average_sharpe_ratio: number;
  performance_rating: string;
  risk_rating: string;
}

interface MarketOverview {
  best_performing_sector: string | null;
  highest_risk_sector: string | null;
  most_diversified_sector: string | null;
  total_sectors: number;
  total_tickers: number;
  market_average_return: number;
  market_average_risk: number;
  market_average_sharpe: number;
}

interface EnhancedSectorDistribution {
  sectors: Sector[];
  market_overview: MarketOverview;
}

interface SectorDistributionChartProps {
  sectorDistribution: EnhancedSectorDistribution;
  totalAssets: number;
}

const COLORS = [
  '#4ade80', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa',
  '#fb923c', '#22d3ee', '#f472b6', '#84cc16', '#06b6d4',
  '#94a3b8', '#facc15', '#c084fc', '#2dd4bf', '#38bdf8'
];

const SectorDistributionChart: React.FC<SectorDistributionChartProps> = ({
  sectorDistribution,
  totalAssets,
}) => {
  const [viewMode, setViewMode] = useState<'pie' | 'bar'>('pie');
  const [sortBy, setSortBy] = useState<'allocation' | 'return' | 'risk' | 'sharpe'>('allocation');

  const { sectors, market_overview } = sectorDistribution;

  // Calculate allocation percentages
  const sectorsWithAllocation = sectors.map(sector => ({
    ...sector,
    allocation_percentage: (sector.ticker_count / totalAssets) * 100,
  }));

  // Sort sectors based on selected criteria
  const sortedSectors = [...sectorsWithAllocation].sort((a, b) => {
    switch (sortBy) {
      case 'allocation':
        return b.allocation_percentage - a.allocation_percentage;
      case 'return':
        return b.average_return - a.average_return;
      case 'risk':
        return b.average_risk - a.average_risk;
      case 'sharpe':
        return b.average_sharpe_ratio - a.average_sharpe_ratio;
      default:
        return 0;
    }
  });

  // Prepare data for charts
  const chartData = sortedSectors.map((sector, index) => ({
    name: sector.sector,
    allocation: sector.allocation_percentage,
    return: sector.average_return * 100,
    risk: sector.average_risk * 100,
    sharpe: sector.average_sharpe_ratio,
    tickerCount: sector.ticker_count,
    color: COLORS[index % COLORS.length],
  }));

  const formatPercentage = (value: number) => `${value.toFixed(2)}%`;
  const formatNumber = (value: number) => value.toFixed(3);

  const getPerformanceColor = (rating: string) => {
    switch (rating) {
      case 'Excellent': return 'bg-green-500';
      case 'Good': return 'bg-blue-500';
      case 'Fair': return 'bg-yellow-500';
      case 'Poor': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getRiskColor = (rating: string) => {
    switch (rating) {
      case 'Low': return 'bg-green-500';
      case 'Medium': return 'bg-yellow-500';
      case 'High': return 'bg-orange-500';
      case 'Very High': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-popover text-popover-foreground p-3 border border-border rounded-lg shadow-lg">
          <p className="font-semibold">{label}</p>
          <p>Allocation: {formatPercentage(data.allocation)}</p>
          <p>Return: {formatPercentage(data.return)}</p>
          <p>Risk: {formatPercentage(data.risk)}</p>
          <p>Sharpe: {formatNumber(data.sharpe)}</p>
          <p>Tickers: {data.tickerCount}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Portfolio Sector Distribution</CardTitle>
          <div className="flex items-center gap-2">
            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="allocation">Allocation %</SelectItem>
                <SelectItem value="return">Average Return</SelectItem>
                <SelectItem value="risk">Average Risk</SelectItem>
                <SelectItem value="sharpe">Sharpe Ratio</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewMode(viewMode === 'pie' ? 'bar' : 'pie')}
            >
              {viewMode === 'pie' ? <BarChart3 className="h-4 w-4" /> : <PieChartIcon className="h-4 w-4" />}
              {viewMode === 'pie' ? 'Bar Chart' : 'Pie Chart'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart */}
          <div>
            <ResponsiveContainer width="100%" height={500}>
              {viewMode === 'pie' ? (
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, allocation }) => `${name}: ${formatPercentage(allocation)}`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="allocation"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              ) : (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                  <YAxis tickFormatter={formatPercentage} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="allocation" fill="#8884d8" />
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>

          {/* Market Overview */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold mb-3">Market Overview</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Total Sectors</span>
                  <Badge variant="secondary">{market_overview.total_sectors}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Total Tickers</span>
                  <Badge variant="secondary">{market_overview.total_tickers}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Market Avg Return</span>
                  <Badge variant="secondary">
                    {formatPercentage(market_overview.market_average_return * 100)}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Market Avg Risk</span>
                  <Badge variant="secondary">
                    {formatPercentage(market_overview.market_average_risk * 100)}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Market Avg Sharpe</span>
                  <Badge variant="secondary">
                    {formatNumber(market_overview.market_average_sharpe)}
                  </Badge>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-3">Top Performers</h3>
              <div className="space-y-2">
                {market_overview.best_performing_sector && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Best Performing</span>
                    <Badge variant="secondary" className="bg-green-500">
                      {market_overview.best_performing_sector}
                    </Badge>
                  </div>
                )}
                {market_overview.highest_risk_sector && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Highest Risk</span>
                    <Badge variant="secondary" className="bg-red-500">
                      {market_overview.highest_risk_sector}
                    </Badge>
                  </div>
                )}
                {market_overview.most_diversified_sector && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Most Diversified</span>
                    <Badge variant="secondary" className="bg-blue-500">
                      {market_overview.most_diversified_sector}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Table */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Sector Details</h3>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sector</TableHead>
                  <TableHead>Assets</TableHead>
                  <TableHead>Allocation</TableHead>
                  <TableHead>Avg Return</TableHead>
                  <TableHead>Avg Risk</TableHead>
                  <TableHead>Sharpe Ratio</TableHead>
                  <TableHead>Performance</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Tickers</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedSectors.map((sector) => (
                  <TableRow key={sector.sector}>
                    <TableCell className="font-medium">{sector.sector}</TableCell>
                    <TableCell>{sector.ticker_count}</TableCell>
                    <TableCell>{formatPercentage(sector.allocation_percentage)}</TableCell>
                    <TableCell>{formatPercentage(sector.average_return * 100)}</TableCell>
                    <TableCell>{formatPercentage(sector.average_risk * 100)}</TableCell>
                    <TableCell>{formatNumber(sector.average_sharpe_ratio)}</TableCell>
                    <TableCell>
                      <Badge className={getPerformanceColor(sector.performance_rating)}>
                        {sector.performance_rating}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getRiskColor(sector.risk_rating)}>
                        {sector.risk_rating}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate">
                      {sector.tickers.slice(0, 3).join(', ')}
                      {sector.tickers.length > 3 && ` +${sector.tickers.length - 3} more`}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Insights */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Portfolio Insights</h3>
          <div className="text-sm space-y-2">
            <p>
              <strong>Sector Concentration:</strong>{' '}
              {sortedSectors.length > 0 && sortedSectors[0].allocation_percentage > 50
                ? 'High concentration in a single sector - consider diversifying'
                : sortedSectors.length > 0 && sortedSectors[0].allocation_percentage > 30
                ? 'Moderate concentration - monitor sector performance'
                : 'Well distributed across sectors'}
            </p>
            
            <p>
              <strong>Overall Diversification:</strong>{' '}
              {sortedSectors.length >= 5
                ? 'Good sector diversification'
                : sortedSectors.length >= 3
                ? 'Moderate sector diversification'
                : 'Limited sector diversification - consider adding more sectors'}
            </p>
            
            {market_overview.best_performing_sector && (
              <p>
                <strong>Opportunity:</strong>{' '}
                {sortedSectors.find(s => s.sector === market_overview.best_performing_sector)?.allocation_percentage || 0 < 10
                  ? `Consider increasing exposure to ${market_overview.best_performing_sector}`
                  : `Good exposure to top-performing ${market_overview.best_performing_sector} sector`}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default SectorDistributionChart; 