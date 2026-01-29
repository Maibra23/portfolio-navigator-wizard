/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Portfolio3PartVisualization } from './Portfolio3PartVisualization';
import { PortfolioAllocation, PortfolioMetrics } from './PortfolioBuilder';

interface PortfolioAnalyticsPanelProps {
  selectedStocks: PortfolioAllocation[];
  riskProfile: string;
  portfolioMetrics?: PortfolioMetrics | null;
}

export const PortfolioAnalyticsPanel: React.FC<PortfolioAnalyticsPanelProps> = ({
  selectedStocks,
  riskProfile,
  portfolioMetrics
}) => {
  const mockRecommendations = [{
    name: 'Current Portfolio',
    description: 'Your selected portfolio',
    allocations: selectedStocks,
    expectedReturn: portfolioMetrics?.expectedReturn || 0.10,
    risk: portfolioMetrics?.risk || 0.15,
    diversificationScore: portfolioMetrics?.diversificationScore || 75
  }];

  if (selectedStocks.length < 3) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Portfolio Analytics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            Select at least 3 stocks to view analytics
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Portfolio Analytics</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Visual analysis of your portfolio's correlation structure and sector allocation
        </p>
      </CardHeader>
      <CardContent>
        <div className="min-h-96 mt-4">
          <Portfolio3PartVisualization
            selectedStocks={selectedStocks}
            allRecommendations={mockRecommendations}
            selectedPortfolioIndex={0}
            riskProfile={riskProfile}
            compactMode={true}
          />
        </div>
      </CardContent>
    </Card>
  );
};
