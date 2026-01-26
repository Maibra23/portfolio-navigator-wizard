import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import { Button } from '@/components/ui/button';
import { ZoomOut } from 'lucide-react';

interface PortfolioPoint {
  risk: number;
  return: number;
  name: string;
  type: 'current' | 'recommended' | 'frontier';
}

interface EfficientFrontierChartProps {
  currentPortfolio: PortfolioPoint | null;
  recommendedPortfolios: PortfolioPoint[];
  className?: string;
}

export const EfficientFrontierChart = ({
  currentPortfolio,
  recommendedPortfolios,
  className
}: EfficientFrontierChartProps) => {
  const [isZoomedOut, setIsZoomedOut] = useState(false);
  const [hasZoomedOut, setHasZoomedOut] = useState(false);

  // Generate efficient frontier curve points
  const frontierPoints: PortfolioPoint[] = [
    { risk: 5, return: 4, name: 'Conservative', type: 'frontier' },
    { risk: 8, return: 6, name: 'Moderate Conservative', type: 'frontier' },
    { risk: 12, return: 8, name: 'Moderate', type: 'frontier' },
    { risk: 16, return: 10, name: 'Moderate Aggressive', type: 'frontier' },
    { risk: 20, return: 12, name: 'Aggressive', type: 'frontier' },
    { risk: 25, return: 14, name: 'Very Aggressive', type: 'frontier' },
  ];

  // Extended frontier points for zoomed-out view
  const extendedFrontierPoints: PortfolioPoint[] = [
    { risk: 2, return: 2, name: 'Ultra Conservative', type: 'frontier' },
    { risk: 5, return: 4, name: 'Conservative', type: 'frontier' },
    { risk: 8, return: 6, name: 'Moderate Conservative', type: 'frontier' },
    { risk: 12, return: 8, name: 'Moderate', type: 'frontier' },
    { risk: 16, return: 10, name: 'Moderate Aggressive', type: 'frontier' },
    { risk: 20, return: 12, name: 'Aggressive', type: 'frontier' },
    { risk: 25, return: 14, name: 'Very Aggressive', type: 'frontier' },
    { risk: 30, return: 15, name: 'High Risk High Reward', type: 'frontier' },
    { risk: 35, return: 16, name: 'Speculative', type: 'frontier' },
  ];

  const handleZoomOut = () => {
    if (!hasZoomedOut) {
      setIsZoomedOut(true);
      setHasZoomedOut(true);
    }
  };

  const displayFrontierPoints = isZoomedOut ? extendedFrontierPoints : frontierPoints;

  // Combine all data points
  const allData = [
    ...displayFrontierPoints,
    ...recommendedPortfolios,
    ...(currentPortfolio ? [currentPortfolio] : [])
  ];

  const chartConfig = {
    frontier: {
      label: "Efficient Frontier",
      color: "#94a3b8",
    },
    recommended: {
      label: "Recommended Portfolios",
      color: "#3b82f6",
    },
    current: {
      label: "Your Portfolio",
      color: "#ef4444",
    },
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Efficient Frontier</CardTitle>
            <p className="text-sm text-muted-foreground">
              Risk vs. Return analysis of your portfolio
            </p>
          </div>
          {!hasZoomedOut && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              className="flex items-center gap-2"
            >
              <ZoomOut className="h-4 w-4" />
              Zoom Out
            </Button>
          )}
          {hasZoomedOut && (
            <div className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
              Zoomed Out View
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart
              data={allData}
              margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="risk" 
                name="Risk" 
                unit="%" 
                label={{ value: 'Risk (Standard Deviation)', position: 'bottom' }}
              />
              <YAxis
                dataKey="return"
                name="Return"
                unit="%"
                label={{ value: 'Expected Return', angle: -90, position: 'left' }}
                domain={isZoomedOut ? [0, 18] : [0, 16]}
              />
              <ChartTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as PortfolioPoint;
                    return (
                      <div className="bg-background border rounded-lg p-2 shadow-lg">
                        <p className="font-medium">{data.name}</p>
                        <p className="text-sm text-muted-foreground">
                          Risk: {data.risk}% | Return: {data.return}%
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              {/* Efficient Frontier */}
              <Scatter
                data={displayFrontierPoints}
                fill="#94a3b8"
                stroke="#64748b"
                strokeWidth={2}
                dataKey="return"
                name="Efficient Frontier"
              />
              
              {/* Recommended Portfolios */}
              {recommendedPortfolios.length > 0 && (
                <Scatter
                  data={recommendedPortfolios}
                  fill="#3b82f6"
                  stroke="#1d4ed8"
                  strokeWidth={2}
                  dataKey="return"
                  name="Recommended"
                />
              )}
              
              {/* Current Portfolio */}
              {currentPortfolio && (
                <Scatter
                  data={[currentPortfolio]}
                  fill="#ef4444"
                  stroke="#dc2626"
                  strokeWidth={3}
                  dataKey="return"
                  name="Current"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartContainer>
        
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-slate-400"></div>
            <span>Efficient Frontier</span>
          </div>
          {recommendedPortfolios.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span>Recommended</span>
            </div>
          )}
          {currentPortfolio && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span>Your Portfolio</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}; 