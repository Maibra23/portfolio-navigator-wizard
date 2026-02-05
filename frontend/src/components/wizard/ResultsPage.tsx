import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FlagAlerts } from './FlagAlerts';
import { CategoryCard } from './CategoryCard';
import { RiskSpectrum } from './RiskSpectrum';
import { TwoDimensionalMap, getQuadrant, QUADRANT_EXPLANATIONS, GAMIFIED_DISCLAIMER } from './TwoDimensionalMap';
import { ArrowRight, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

import type { ConfidenceBand } from './confidence-calculator';
import type { SafeguardResult } from './safeguards';

// Inline interface for VisualizationData as it might not be exported
interface VisualizationData {
  gradient_intensity: 'narrow' | 'medium' | 'wide';
  boundary_proximity: 'far' | 'near' | 'crossing';
}

export interface ResultsPageProps {
  scoringResult: {
    normalized_score: number;
    normalized_mpt: number;
    normalized_prospect: number;
    risk_category: string;
    confidence_band: ConfidenceBand;
    visualization_data: VisualizationData;
    safeguards: SafeguardResult;
  };
  isGamifiedPath: boolean;
  onReviewAnswers: () => void;
  onContinue: () => void;
  className?: string;
}

export const ResultsPage: React.FC<ResultsPageProps> = ({
  scoringResult,
  isGamifiedPath,
  onReviewAnswers,
  onContinue,
  className
}) => {
  const {
    normalized_score,
    normalized_mpt,
    normalized_prospect,
    risk_category,
    confidence_band,
    visualization_data,
    safeguards
  } = scoringResult;

  const hasFlags = Object.values(safeguards.flags).some(Boolean);
  const quadrant = getQuadrant(Math.round(normalized_mpt), Math.round(normalized_prospect));
  const quadrantExplanation = QUADRANT_EXPLANATIONS[quadrant];
  const quadrantStyle = quadrant === 'high-high' ? { backgroundColor: 'rgba(34, 197, 94, 0.15)', borderColor: '#10b981' } :
    quadrant === 'low-high' ? { backgroundColor: 'rgba(234, 179, 8, 0.15)', borderColor: '#eab308' } :
    quadrant === 'high-low' ? { backgroundColor: 'rgba(59, 130, 246, 0.15)', borderColor: '#3b82f6' } :
    { backgroundColor: 'rgba(107, 114, 128, 0.15)', borderColor: '#9ca3af' };

  return (
    <div className={cn("max-w-3xl mx-auto space-y-4 pb-16 animate-in fade-in duration-500", className)}>
      {/* Flag Alerts - Show at top if any */}
      {hasFlags && (
        <FlagAlerts
          flags={safeguards.flags}
          flagMessages={safeguards.flag_messages}
          onReviewAnswers={onReviewAnswers}
        />
      )}

      {/* Profile type - at top, centered */}
      <div className="flex justify-center">
        <CategoryCard
          category={risk_category}
          score={Math.round(normalized_score)}
          secondaryCategory={
            safeguards.flags.high_uncertainty && confidence_band.secondary_category
              ? confidence_band.secondary_category
              : undefined
          }
          className="w-full max-w-2xl"
        />
      </div>

      {/* Risk Spectrum - Visual Score Display */}
      <RiskSpectrum
        score={Math.round(normalized_score)}
        confidenceBand={confidence_band}
        visualizationData={visualization_data}
      />

      {/* Risk Breakdown - Graph full width, then stats + quadrant side by side */}
      <Card className="w-full shadow-sm border-muted">
        <CardContent className="p-4 space-y-4">
          <div>
            <h3 className="text-base font-semibold">Risk Breakdown</h3>
            <p className="text-xs text-muted-foreground">Analytical vs Emotional Risk Tolerance</p>
            {isGamifiedPath && (
              <p className="text-xs text-muted-foreground mt-1">{GAMIFIED_DISCLAIMER}</p>
            )}
          </div>
          {/* Graph full width */}
          <TwoDimensionalMap
            mptScore={Math.round(normalized_mpt)}
            prospectScore={Math.round(normalized_prospect)}
            isGamifiedPath={isGamifiedPath}
            chartOnly
            className="w-full"
          />
          {/* Stats and quadrant explanation side by side */}
          <div className="grid gap-4 md:grid-cols-[200px_1fr]">
            <Card className="shadow-sm border-muted h-fit">
              <CardContent className="p-4 space-y-3">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {Math.round(normalized_mpt)}
                  </div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Analytical</div>
                </div>
                <div className="h-px bg-border" />
                <div className="text-center">
                  <div className="text-2xl font-bold text-indigo-600">
                    {Math.round(normalized_prospect)}
                  </div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Emotional</div>
                </div>
              </CardContent>
            </Card>
            <div
              className="rounded-lg p-2.5 text-xs border-2 h-fit"
              style={quadrantStyle}
            >
              <div className="font-bold text-gray-900">{quadrantExplanation.title}</div>
              <p className="mt-1 text-gray-700 leading-snug">{quadrantExplanation.explanation}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3 justify-center pt-2">
        <Button
          variant="outline"
          onClick={onReviewAnswers}
          className="flex-1 max-w-[200px]"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Review
        </Button>
        <Button
          onClick={onContinue}
          className="flex-1 max-w-[200px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
        >
          Continue
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
