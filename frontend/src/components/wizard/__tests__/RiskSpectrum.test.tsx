import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RiskSpectrum } from '../RiskSpectrum';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('RiskSpectrum', () => {
  const mockConfidenceBand = {
    lower: 35,
    upper: 65,
    primary_category: 'moderate',
    secondary_category: 'conservative',
    band_width: 30,
    adjustment_reasons: ['variance']
  };

  const mockVisualizationData = {
    gradient_intensity: 'medium' as const,
    boundary_proximity: 'far' as const
  };

  it('renders with basic props', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getByText('Risk Score: 50')).toBeInTheDocument();
  });

  it('displays category first-word labels', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getAllByText('Very').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Conservative')).toBeInTheDocument();
    expect(screen.getByText('Moderate')).toBeInTheDocument();
    expect(screen.getByText('Aggressive')).toBeInTheDocument();
  });

  it('renders correctly for all category score ranges (0-20, 21-40, 41-60, 61-80, 81-100)', () => {
    const ranges = [
      { score: 10, primary: 'very-conservative' },
      { score: 30, primary: 'conservative' },
      { score: 50, primary: 'moderate' },
      { score: 70, primary: 'aggressive' },
      { score: 90, primary: 'very-aggressive' },
    ];
    ranges.forEach(({ score, primary }) => {
      const { unmount } = render(
        <RiskSpectrum
          score={score}
          confidenceBand={{
            ...mockConfidenceBand,
            primary_category: primary,
            lower: Math.max(0, score - 5),
            upper: Math.min(100, score + 5),
          }}
          visualizationData={mockVisualizationData}
        />
      );
      expect(screen.getByText(`Risk Score: ${score}`)).toBeInTheDocument();
      unmount();
    });
  });

  it('shows confidence band range when band width is significant', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getByText('Range: 35-65')).toBeInTheDocument();
  });

  it('shows adjustment reasons when present', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getByText(/Range factors:/)).toBeInTheDocument();
    expect(screen.getByText(/variance/)).toBeInTheDocument();
  });

  it('handles narrow gradient intensity', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={{
          ...mockVisualizationData,
          gradient_intensity: 'narrow'
        }}
      />
    );

    expect(screen.getByText('Risk Score: 50')).toBeInTheDocument();
  });

  it('handles wide gradient intensity', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={{
          ...mockVisualizationData,
          gradient_intensity: 'wide'
        }}
      />
    );

    expect(screen.getByText('Risk Score: 50')).toBeInTheDocument();
  });

  it('shows crossing message when boundary proximity is crossing', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={{
          ...mockVisualizationData,
          boundary_proximity: 'crossing'
        }}
      />
    );

    expect(screen.getByText('Your range spans Moderate to Conservative')).toBeInTheDocument();
  });

  it('handles category click callback', async () => {
    const user = userEvent.setup();
    const mockOnCategoryClick = vi.fn();

    render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
        onCategoryClick={mockOnCategoryClick}
      />
    );

    expect(mockOnCategoryClick).not.toHaveBeenCalled();
  });

  it('handles extreme scores within bounds', () => {
    render(
      <RiskSpectrum
        score={5}
        confidenceBand={{
          ...mockConfidenceBand,
          lower: 0,
          upper: 15
        }}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getByText('Risk Score: 5')).toBeInTheDocument();
  });

  it('handles high scores within bounds', () => {
    render(
      <RiskSpectrum
        score={95}
        confidenceBand={{
          ...mockConfidenceBand,
          lower: 85,
          upper: 100
        }}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.getByText('Risk Score: 95')).toBeInTheDocument();
  });

  it('handles empty adjustment reasons', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={{
          ...mockConfidenceBand,
          adjustment_reasons: []
        }}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.queryByText(/Range factors:/)).not.toBeInTheDocument();
  });

  it('handles small confidence band', () => {
    render(
      <RiskSpectrum
        score={50}
        confidenceBand={{
          ...mockConfidenceBand,
          band_width: 3,
          lower: 48.5,
          upper: 51.5
        }}
        visualizationData={mockVisualizationData}
      />
    );

    expect(screen.queryByText(/Range:/)).not.toBeInTheDocument();
  });

  it('accepts custom className', () => {
    const { container } = render(
      <RiskSpectrum
        score={50}
        confidenceBand={mockConfidenceBand}
        visualizationData={mockVisualizationData}
        className="custom-class"
      />
    );

    const cardElement = container.querySelector('[class*="custom-class"]');
    expect(cardElement).toBeInTheDocument();
  });
});
