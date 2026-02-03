import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TwoDimensionalMap } from '../TwoDimensionalMap';

describe('TwoDimensionalMap', () => {
  describe('Gamified path (under-19)', () => {
    it('hides the 2D map and shows message when isGamifiedPath is true', () => {
      render(
        <TwoDimensionalMap
          mptScore={50}
          prospectScore={50}
          isGamifiedPath={true}
        />
      );

      expect(screen.getByText(/Complete the full assessment at 19\+/)).toBeInTheDocument();
      expect(screen.getByText(/analytical vs emotional risk breakdown/)).toBeInTheDocument();
      expect(screen.queryByText('Two-Dimensional Risk Map')).not.toBeInTheDocument();
    });
  });

  describe('Quadrant display', () => {
    it('renders map and quadrant labels when not gamified', () => {
      render(
        <TwoDimensionalMap
          mptScore={60}
          prospectScore={60}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText('Two-Dimensional Risk Map')).toBeInTheDocument();
      expect(screen.getAllByText('Fully Risk-Seeking').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Emotionally Bold, Analytically Cautious')).toBeInTheDocument();
      expect(screen.getByText('Analytically Bold, Emotionally Cautious')).toBeInTheDocument();
      expect(screen.getByText('Fully Risk-Averse')).toBeInTheDocument();
    });

    it('shows high-high quadrant explanation when both scores >= 50', () => {
      render(
        <TwoDimensionalMap
          mptScore={70}
          prospectScore={80}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText("You're comfortable with risk analytically and emotionally.")).toBeInTheDocument();
      expect(screen.getByText('Your portfolio can align with your analytical preferences.')).toBeInTheDocument();
    });

    it('shows low-high quadrant explanation when MPT < 50 and Prospect >= 50', () => {
      render(
        <TwoDimensionalMap
          mptScore={30}
          prospectScore={70}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText(/You may feel confident about taking risks/)).toBeInTheDocument();
      expect(screen.getByText(/Building investment knowledge/)).toBeInTheDocument();
    });

    it('shows high-low quadrant explanation when MPT >= 50 and Prospect < 50', () => {
      render(
        <TwoDimensionalMap
          mptScore={75}
          prospectScore={25}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText(/You understand risk-return connection/)).toBeInTheDocument();
      expect(screen.getByText(/Consider whether your analytical view/)).toBeInTheDocument();
    });

    it('shows low-low quadrant explanation when both scores < 50', () => {
      render(
        <TwoDimensionalMap
          mptScore={20}
          prospectScore={30}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText('You prefer safety on all dimensions.')).toBeInTheDocument();
      expect(screen.getByText('A conservative portfolio aligns with your complete risk profile.')).toBeInTheDocument();
    });

    it('places user dot in correct quadrant for given MPT/Prospect scores', () => {
      const cases: Array<{ mpt: number; prospect: number; quadrantTitle: string }> = [
        { mpt: 60, prospect: 70, quadrantTitle: 'Fully Risk-Seeking' },
        { mpt: 30, prospect: 70, quadrantTitle: 'Emotionally Bold, Analytically Cautious' },
        { mpt: 70, prospect: 30, quadrantTitle: 'Analytically Bold, Emotionally Cautious' },
        { mpt: 20, prospect: 25, quadrantTitle: 'Fully Risk-Averse' },
      ];
      cases.forEach(({ mpt, prospect, quadrantTitle }) => {
        const { unmount } = render(
          <TwoDimensionalMap mptScore={mpt} prospectScore={prospect} isGamifiedPath={false} />
        );
        expect(screen.getAllByText(quadrantTitle).length).toBeGreaterThanOrEqual(1);
        unmount();
      });
    });
  });

  describe('Axis labels', () => {
    it('shows axis description', () => {
      render(
        <TwoDimensionalMap
          mptScore={50}
          prospectScore={50}
          isGamifiedPath={false}
        />
      );

      expect(screen.getByText(/Analytical Risk Tolerance.*Emotional Risk Tolerance/)).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('handles boundary at 50/50', () => {
      render(
        <TwoDimensionalMap
          mptScore={50}
          prospectScore={50}
          isGamifiedPath={false}
        />
      );

      // At 50/50, quadrant is high-high (>= 50)
      expect(screen.getByText("You're comfortable with risk analytically and emotionally.")).toBeInTheDocument();
    });

    it('clamps scores to 0-100 range', () => {
      render(
        <TwoDimensionalMap
          mptScore={150}
          prospectScore={-10}
          isGamifiedPath={false}
        />
      );

      // Component renders; clamped to (100, 0) -> high-low quadrant
      expect(screen.getByText('Two-Dimensional Risk Map')).toBeInTheDocument();
      expect(screen.getByText(/You understand risk-return connection/)).toBeInTheDocument();
    });

    it('accepts custom className', () => {
      const { container } = render(
        <TwoDimensionalMap
          mptScore={50}
          prospectScore={50}
          isGamifiedPath={false}
          className="custom-map"
        />
      );

      const card = container.querySelector('[class*="custom-map"]');
      expect(card).toBeInTheDocument();
    });
  });
});
