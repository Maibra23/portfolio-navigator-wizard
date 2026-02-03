import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { FlagAlerts } from './FlagAlerts';
import { CategoryCard } from './CategoryCard';
import { RiskSpectrum } from './RiskSpectrum';
import { TwoDimensionalMap } from './TwoDimensionalMap';
import { ConfirmationModal } from './ConfirmationModal';
import { ArrowRight, RotateCcw } from 'lucide-react';

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
  const [showConfirmation, setShowConfirmation] = useState(
    scoringResult.safeguards.flags.extreme_profile_confirmation
  );

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

  return (
    <div className={`space-y-8 pb-20 ${className || ''}`}>
      {/* Extreme Profile Confirmation Modal */}
      <ConfirmationModal
        category={risk_category}
        isOpen={showConfirmation}
        onConfirm={() => setShowConfirmation(false)}
        onReview={() => {
          setShowConfirmation(false);
          onReviewAnswers();
        }}
        onShowDescription={() => setShowConfirmation(false)}
      />

      {/* Flag Alerts */}
      {hasFlags && (
        <FlagAlerts
          flags={safeguards.flags}
          flagMessages={safeguards.flag_messages}
          onReviewAnswers={onReviewAnswers}
        />
      )}

      {/* Primary Category Result */}
      <CategoryCard
        category={risk_category}
        score={Math.round(normalized_score)}
        secondaryCategory={
          safeguards.flags.high_uncertainty && confidence_band.secondary_category
            ? confidence_band.secondary_category
            : undefined
        }
      />

      {/* Risk Spectrum with Confidence Band */}
      <RiskSpectrum
        score={Math.round(normalized_score)}
        confidenceBand={confidence_band}
        visualizationData={visualization_data}
      />

      {/* Two-Dimensional Map (hidden if gamified) */}
      <TwoDimensionalMap
        mptScore={Math.round(normalized_mpt)}
        prospectScore={Math.round(normalized_prospect)}
        isGamifiedPath={isGamifiedPath}
      />

      {/* Sticky Action Buttons for Mobile */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/95 backdrop-blur border-t z-10 flex gap-3 flex-col sm:flex-row sm:static sm:p-0 sm:bg-transparent sm:border-0 sm:justify-end">
        <Button
          variant="outline"
          onClick={onReviewAnswers}
          className="w-full sm:w-auto"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Review My Answers
        </Button>
        <Button
          onClick={onContinue}
          className="w-full sm:w-auto bg-primary hover:bg-primary/90"
        >
          Continue to Portfolio
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
