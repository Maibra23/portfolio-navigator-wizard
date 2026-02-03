import React from 'react';
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

// Risk spectrum zones with colors
const RISK_ZONES = [
  { min: 0, max: 20, category: 'very-conservative', label: 'Very Conservative', color: '#00008B' },
  { min: 21, max: 40, category: 'conservative', label: 'Conservative', color: '#ADD8E6' },
  { min: 41, max: 60, category: 'moderate', label: 'Moderate', color: '#008000' },
  { min: 61, max: 80, category: 'aggressive', label: 'Aggressive', color: '#FFA500' },
  { min: 81, max: 100, category: 'very-aggressive', label: 'Very Aggressive', color: '#FF0000' },
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

  // Get gradient intensity styles
  const getMarkerGlow = (intensity: typeof visualizationData.gradient_intensity) => {
    switch (intensity) {
      case 'narrow':
        return 'shadow-[0_0_4px_rgba(59,130,246,0.5)]';
      case 'medium':
        return 'shadow-[0_0_8px_rgba(59,130,246,0.6)]';
      case 'wide':
        return 'shadow-[0_0_16px_rgba(59,130,246,0.7),0_0_24px_rgba(59,130,246,0.4)] animate-pulse';
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
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold text-center">
            Your Risk Profile
          </CardTitle>
          {crossingMessage && (
            <p className="text-sm text-muted-foreground text-center mt-2">
              {crossingMessage}
            </p>
          )}
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Risk Spectrum Bar */}
          <div className="relative">
            {/* Main spectrum bar */}
            <div className="relative h-8 rounded-lg overflow-hidden border">
              {RISK_ZONES.map((zone, index) => (
                <div
                  key={zone.category}
                  className="absolute top-0 h-full cursor-pointer hover:opacity-80 transition-opacity"
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
                className="absolute top-0 h-full bg-white/30 border-x border-white/50"
                style={{
                  left: `${bandLeft}%`,
                  width: `${bandWidth}%`,
                }}
              />

              {/* Boundary lines for 'near' proximity */}
              {visualizationData.boundary_proximity === 'near' && boundaryPositions.map(boundary => (
                <div
                  key={boundary}
                  className="absolute top-0 h-full w-px border-l-2 border-dashed border-white/70"
                  style={{ left: `${boundary}%` }}
                />
              ))}
            </div>

            {/* Score marker */}
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    "absolute top-1/2 transform -translate-y-1/2 -translate-x-1/2 z-10",
                    "w-4 h-4 bg-blue-500 rounded-full border-2 border-white",
                    getMarkerGlow(visualizationData.gradient_intensity)
                  )}
                  style={{ left: `${markerPosition}%` }}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p>{SPECTRUM_TOOLTIPS.score_marker}</p>
              </TooltipContent>
            </Tooltip>

            {/* Confidence band tooltip area */}
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className="absolute top-0 h-full cursor-help"
                  style={{
                    left: `${bandLeft}%`,
                    width: `${bandWidth}%`,
                  }}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p>{SPECTRUM_TOOLTIPS.confidence_band}</p>
              </TooltipContent>
            </Tooltip>

            {/* Boundary tooltips for near/crossing */}
            {visualizationData.boundary_proximity !== 'far' && boundaryPositions.map(boundary => {
              const zoneIndex = RISK_ZONES.findIndex(z => boundary >= z.min && boundary < z.max);
              const nextZone = RISK_ZONES[zoneIndex + 1];
              if (!nextZone) return null;

              return (
                <Tooltip key={boundary}>
                  <TooltipTrigger asChild>
                    <div
                      className="absolute top-0 h-full w-2 cursor-help -translate-x-1"
                      style={{ left: `${boundary}%` }}
                    />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {SPECTRUM_TOOLTIPS.category_boundary
                        .replace('{cat1}', RISK_ZONES[zoneIndex]?.label || '')
                        .replace('{cat2}', nextZone.label)}
                    </p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>

          {/* Category Labels */}
          <div className="grid grid-cols-5 gap-1 text-xs font-medium text-center">
            {RISK_ZONES.map((zone) => (
              <button
                key={zone.category}
                className="hover:text-primary transition-colors truncate"
                onClick={() => onCategoryClick?.(zone.category)}
              >
                {zone.label}
              </button>
            ))}
          </div>

          {/* Score Display */}
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">
              {score}
            </div>
            <div className="text-sm text-muted-foreground">
              Risk Score
            </div>
            {confidenceBand.band_width > 5 && (
              <div className="text-xs text-muted-foreground mt-1">
                Range: {confidenceBand.lower.toFixed(1)} - {confidenceBand.upper.toFixed(1)}
              </div>
            )}
          </div>

          {/* Adjustment Reasons */}
          {confidenceBand.adjustment_reasons.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Why this range?</h4>
              <ul className="space-y-1">
                {confidenceBand.adjustment_reasons.map((reason, index) => (
                  <li key={index} className="text-xs text-muted-foreground flex items-start gap-2">
                    <span className="w-1 h-1 bg-muted-foreground rounded-full mt-1.5 flex-shrink-0" />
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};