import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CategoryCard } from '../CategoryCard';

describe('CategoryCard', () => {
  it('renders very-conservative category correctly', () => {
    render(<CategoryCard category="very-conservative" score={15} />);

    expect(screen.getByText('Very Conservative')).toBeInTheDocument();
    expect(screen.getByText('You prioritize protecting your money over growing it.')).toBeInTheDocument();
    expect(screen.getByText('Prefer guaranteed returns')).toBeInTheDocument();
    expect(screen.getByText('Uncomfortable with market swings')).toBeInTheDocument();
    expect(screen.getByText('Focus on capital preservation')).toBeInTheDocument();
    expect(screen.getByText('Stable dividend stocks, broad diversification, low concentration')).toBeInTheDocument();
  });

  it('renders conservative category correctly', () => {
    render(<CategoryCard category="conservative" score={35} />);

    expect(screen.getByText('Conservative')).toBeInTheDocument();
    expect(screen.getByText('You accept modest risk for steady growth.')).toBeInTheDocument();
    expect(screen.getByText('Some tolerance for fluctuation')).toBeInTheDocument();
    expect(screen.getByText('Value consistent income')).toBeInTheDocument();
    expect(screen.getByText('Prefer slower, steadier growth')).toBeInTheDocument();
    expect(screen.getByText('Mix of stable and growth stocks, diversified, moderate concentration')).toBeInTheDocument();
  });

  it('renders moderate category correctly', () => {
    render(<CategoryCard category="moderate" score={55} />);

    expect(screen.getByText('Moderate')).toBeInTheDocument();
    expect(screen.getByText('You balance growth and stability.')).toBeInTheDocument();
    expect(screen.getByText('Accept ups and downs')).toBeInTheDocument();
    expect(screen.getByText('Long-term focused')).toBeInTheDocument();
    expect(screen.getByText('Diversification-minded')).toBeInTheDocument();
    expect(screen.getByText('Balanced mix of value and growth stocks, diversified')).toBeInTheDocument();
  });

  it('renders aggressive category correctly', () => {
    render(<CategoryCard category="aggressive" score={75} />);

    expect(screen.getByText('Aggressive')).toBeInTheDocument();
    expect(screen.getByText('You pursue growth and tolerate volatility.')).toBeInTheDocument();
    expect(screen.getByText('Comfortable with large swings')).toBeInTheDocument();
    expect(screen.getByText('Very long time horizon')).toBeInTheDocument();
    expect(screen.getByText('Growth over income')).toBeInTheDocument();
    expect(screen.getByText('Growth-oriented stocks, comfortable with volatility, fewer holdings')).toBeInTheDocument();
  });

  it('renders very-aggressive category correctly', () => {
    render(<CategoryCard category="very-aggressive" score={95} />);

    expect(screen.getByText('Very Aggressive')).toBeInTheDocument();
    expect(screen.getByText('You seek maximum growth with high risk tolerance.')).toBeInTheDocument();
    expect(screen.getByText('Embrace volatility')).toBeInTheDocument();
    expect(screen.getByText('Longest time horizon')).toBeInTheDocument();
    expect(screen.getByText('Concentrated positions acceptable')).toBeInTheDocument();
    expect(screen.getByText('High-conviction growth stocks, concentrated positions, long horizon')).toBeInTheDocument();
  });

  it('shows secondary category message when provided', () => {
    render(
      <CategoryCard
        category="moderate"
        secondaryCategory="conservative"
        score={55}
      />
    );

    expect(screen.getByText(/Also shares traits with/)).toBeInTheDocument();
    expect(screen.getByText('Conservative')).toBeInTheDocument();
  });

  it('does not show secondary category message when null', () => {
    render(
      <CategoryCard
        category="moderate"
        secondaryCategory={null}
        score={55}
      />
    );

    expect(screen.queryByText(/Also shares traits with/)).not.toBeInTheDocument();
  });

  it('does not show secondary category message when undefined', () => {
    render(<CategoryCard category="moderate" score={55} />);

    expect(screen.queryByText(/Also shares traits with/)).not.toBeInTheDocument();
  });

  it('handles unknown category gracefully', () => {
    render(<CategoryCard category="unknown-category" score={50} />);

    expect(screen.getByText('Category content not found')).toBeInTheDocument();
  });

  it('accepts custom className', () => {
    const { container } = render(
      <CategoryCard
        category="moderate"
        score={55}
        className="custom-class"
      />
    );

    const cardElement = container.querySelector('[class*="custom-class"]');
    expect(cardElement).toBeInTheDocument();
  });

  it('displays all characteristics', () => {
    render(<CategoryCard category="moderate" score={55} />);

    const characteristics = [
      'Accept ups and downs',
      'Long-term focused',
      'Diversification-minded'
    ];

    characteristics.forEach(char => {
      expect(screen.getByText(char)).toBeInTheDocument();
    });
  });

  it('shows style guidance (equity style, no bonds)', () => {
    render(<CategoryCard category="moderate" score={55} />);

    expect(screen.getByText('Style:')).toBeInTheDocument();
    const allocationText = screen.getByText('Balanced mix of value and growth stocks, diversified');
    expect(allocationText).toBeInTheDocument();
  });

  it('applies correct border color based on category', () => {
    const { container } = render(<CategoryCard category="moderate" score={55} />);

    const card = container.querySelector('[style*="border"]');
    expect(card).toBeTruthy();
    expect(card?.getAttribute('style')).toMatch(/10b981|185|129/);
  });
});