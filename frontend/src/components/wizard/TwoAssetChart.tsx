import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Line, LineChart } from 'recharts';

interface TwoAssetPortfolio {
  weights: [number, number];
  return: number;
  risk: number;
  sharpe_ratio: number;
}

interface TwoAssetChartProps {
  portfolios: TwoAssetPortfolio[];
  customPortfolio: TwoAssetPortfolio | null;
  nvdaWeight: number;
  className?: string;
}

export const TwoAssetChart = ({ 
  portfolios, 
  customPortfolio, 
  nvdaWeight, 
  className 
}: TwoAssetChartProps) => {
  // Prepare data for the chart
  const chartData = portfolios.map((portfolio, index) => ({
    risk: portfolio.risk * 100, // Convert to percentage
    return: portfolio.return * 100, // Convert to percentage
    name: `${(portfolio.weights[0] * 100).toFixed(0)}/${(portfolio.weights[1] * 100).toFixed(0)}`,
    type: 'static'
  }));

  // Add custom portfolio point
  if (customPortfolio) {
    chartData.push({
      risk: customPortfolio.risk * 100,
      return: customPortfolio.return * 100,
      name: `Custom (${nvdaWeight}/${100 - nvdaWeight})`,
      type: 'custom'
    });
  }

  const chartConfig = {
    static: {
      label: "Static Portfolios",
      color: "#3b82f6",
    },
    custom: {
      label: "Your Portfolio",
      color: "#ef4444",
    },
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">Risk vs Return Analysis</CardTitle>
        <p className="text-sm text-muted-foreground">
          X-axis: Risk (Standard Deviation %), Y-axis: Expected Return (%)
        </p>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart
              data={chartData}
              margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="risk" 
                name="Risk" 
                unit="%" 
                label={{ value: 'Risk (Standard Deviation %)', position: 'bottom' }}
              />
              <YAxis 
                dataKey="return" 
                name="Return" 
                unit="%" 
                label={{ value: 'Expected Return (%)', angle: -90, position: 'left' }}
              />
              <ChartTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-background border rounded-lg p-2 shadow-lg">
                        <p className="font-medium">{data.name}</p>
                        <p className="text-sm text-muted-foreground">
                          Risk: {data.risk.toFixed(1)}% | Return: {data.return.toFixed(1)}%
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              {/* Static portfolio points */}
              <Scatter
                data={chartData.filter(d => d.type === 'static')}
                fill="#3b82f6"
                stroke="#1d4ed8"
                strokeWidth={2}
                dataKey="return"
                name="Static Portfolios"
              />
              
              {/* Custom portfolio point */}
              {customPortfolio && (
                <Scatter
                  data={chartData.filter(d => d.type === 'custom')}
                  fill="#ef4444"
                  stroke="#dc2626"
                  strokeWidth={3}
                  dataKey="return"
                  name="Your Portfolio"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartContainer>
        
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Static Portfolios</span>
          </div>
          {customPortfolio && (
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