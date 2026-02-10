import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface RiskSpectrumProps {
  score: number;
  confidenceBand: {
    lower: number;
    upper: number;
    primary_category: string;
    secondary_category: string | null;
    band_width: number;
    adjustment_reasons: string[];
  };
  visualizationData: {
    gradient_intensity: 'narrow' | 'medium' | 'wide';
    boundary_proximity: 'far' | 'near' | 'crossing';
  };
  onCategoryClick?: (category: string) => void;
  className?: string;
}

// Risk spectrum zones with more vibrant colors
const RISK_ZONES = [
  { min: 0, max: 20, category: 'very-conservative', label: 'Very Conservative', color: '#1e40af' }, // Deep blue
  { min: 21, max: 40, category: 'conservative', label: 'Conservative', color: '#60a5fa' }, // Lighter blue
  { min: 41, max: 60, category: 'moderate', label: 'Moderate', color: '#10b981' }, // Emerald green
  { min: 61, max: 80, category: 'aggressive', label: 'Aggressive', color: '#f59e0b' }, // Amber
  { min: 81, max: 100, category: 'very-aggressive', label: 'Very Aggressive', color: '#ef4444' }, // Red
] as const;

// Tooltip content
const SPECTRUM_TOOLTIPS = {
  score_marker: "Your risk score based on your responses.",
  confidence_band: "The shaded area shows your natural range—most people's preferences vary slightly.",
  category_boundary: "You're near the boundary between {cat1} and {cat2}.",
  crossing_band: "Your responses suggest flexibility between {cat1} and {cat2}."
} as const;

export const RiskSpectrum: React.FC<RiskSpectrumProps> = ({
  score,
  confidenceBand,
  visualizationData,
  onCategoryClick,
  className
}) => {
  // Calculate marker position (0-100 scale)
  const markerPosition = Math.max(0, Math.min(100, score));

  // Calculate confidence band positions
  const bandLeft = Math.max(0, confidenceBand.lower);
  const bandRight = Math.min(100, confidenceBand.upper);
  const bandWidth = bandRight - bandLeft;

  // Get marker border intensity (no shadows per design)
  const getMarkerGlow = (intensity: typeof visualizationData.gradient_intensity) => {
    switch (intensity) {
      case 'narrow':
        return 'ring-2 ring-primary/50';
      case 'medium':
        return 'ring-2 ring-primary';
      case 'wide':
        return 'ring-2 ring-primary ring-offset-2 ring-offset-background animate-pulse';
      default:
        return '';
    }
  };

  // Find boundary positions
  const getBoundaryPositions = () => {
    const boundaries = [20, 40, 60, 80];
    const nearbyBoundaries = boundaries.filter(boundary => {
      const distance = Math.abs(score - boundary);
      return distance <= 10; // Within 10 points
    });
    return nearbyBoundaries;
  };

  const boundaryPositions = getBoundaryPositions();

  // Get crossing message
  const getCrossingMessage = () => {
    if (visualizationData.boundary_proximity !== 'crossing' || !confidenceBand.secondary_category) {
      return null;
    }

    const primaryLabel = RISK_ZONES.find(z => z.category === confidenceBand.primary_category)?.label || confidenceBand.primary_category;
    const secondaryLabel = RISK_ZONES.find(z => z.category === confidenceBand.secondary_category)?.label || confidenceBand.secondary_category;

    return `Your range spans ${primaryLabel} to ${secondaryLabel}`;
  };

  const crossingMessage = getCrossingMessage();

  return (
    <TooltipProvider>
      <Card className={cn("w-full", className)}>
        <CardHeader className="pb-3 text-center">
          <div className="flex flex-col items-center gap-1">
            <CardTitle className="text-base font-semibold">
              Risk Score: {score}
            </CardTitle>
            {confidenceBand.band_width > 5 && (
              <span className="text-xs text-muted-foreground">
                Range: {confidenceBand.lower.toFixed(0)}-{confidenceBand.upper.toFixed(0)}
              </span>
            )}
          </div>
          {crossingMessage && (
            <p className="text-xs text-muted-foreground mt-1">
              {crossingMessage}
            </p>
          )}
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Risk Spectrum Bar */}
          <div className="relative">
            {/* Main spectrum bar */}
            <div className="relative h-10 rounded-lg overflow-hidden border-2 border-gray-200 shadow-sm">
              {RISK_ZONES.map((zone) => (
                <div
                  key={zone.category}
                  className="absolute top-0 h-full cursor-pointer hover:brightness-110 transition-all"
                  style={{
                    left: `${zone.min}%`,
                    width: `${zone.max - zone.min}%`,
                    backgroundColor: zone.color,
                  }}
                  onClick={() => onCategoryClick?.(zone.category)}
                />
              ))}

              {/* Confidence band overlay */}
              <div
                className="absolute top-0 h-full bg-white/40 border-x-2 border-white/80"
                style={{
                  left: `${bandLeft}%`,
                  width: `${bandWidth}%`,
                }}
              />

              {/* Boundary lines for 'near' proximity */}
              {visualizationData.boundary_proximity === 'near' && boundaryPositions.map(boundary => (
                <div
                  key={boundary}
                  className="absolute top-0 h-full w-0.5 border-l-2 border-dashed border-white/90"
                  style={{ left: `${boundary}%` }}
                />
              ))}
            </div>

            {/* Score marker - animated on mount */}
            <Tooltip>
              <TooltipTrigger asChild>
                <motion.div
                  className={cn(
                    "absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10",
                    "w-5 h-5 bg-white rounded-full border-3 border-blue-600 shadow-lg",
                    getMarkerGlow(visualizationData.gradient_intensity)
                  )}
                  initial={{ left: '0%' }}
                  animate={{ left: `${markerPosition}%` }}
                  transition={{ type: 'spring', stiffness: 80, damping: 18 }}
                >
                  <motion.div
                    className="absolute inset-1 bg-blue-600 rounded-full"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: 'spring', stiffness: 200, damping: 15 }}
                  />
                </motion.div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{SPECTRUM_TOOLTIPS.score_marker}</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Category Labels - compact */}
          <div className="flex justify-between text-[10px] font-medium text-muted-foreground px-1">
            {RISK_ZONES.map((zone) => (
              <span key={zone.category} className="text-center" style={{ color: zone.color }}>
                {zone.label.split(' ')[0]}
              </span>
            ))}
          </div>

          {/* Adjustment Reasons - compact */}
          {confidenceBand.adjustment_reasons.length > 0 && (
            <div className="text-xs text-muted-foreground text-center">
              <span className="font-medium">Range factors: </span>
              {confidenceBand.adjustment_reasons.join(', ')}
            </div>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};