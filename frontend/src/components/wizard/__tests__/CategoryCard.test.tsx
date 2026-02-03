import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CategoryCard } from '../CategoryCard';

describe('CategoryCard', () => {
  it('renders very-conservative category correctly', () => {
    render(<CategoryCard category="very-conservative" score={15} />);

    expect(screen.getByText('Very Conservative')).toBeInTheDocument();
    expect(screen.getByText('Risk Score: 15')).toBeInTheDocument();
    expect(screen.getByText('You prioritize protecting your money over growing it.')).toBeInTheDocument();
    expect(screen.getByText('Prefer guaranteed returns')).toBeInTheDocument();
    expect(screen.getByText('Uncomfortable with market swings')).toBeInTheDocument();
    expect(screen.getByText('Focus on capital preservation')).toBeInTheDocument();
    expect(screen.getByText('80-100% bonds, 0-20% stocks')).toBeInTheDocument();
  });

  it('renders conservative category correctly', () => {
    render(<CategoryCard category="conservative" score={35} />);

    expect(screen.getByText('Conservative')).toBeInTheDocument();
    expect(screen.getByText('Risk Score: 35')).toBeInTheDocument();
    expect(screen.getByText('You accept modest risk for steady growth.')).toBeInTheDocument();
    expect(screen.getByText('Some tolerance for fluctuation')).toBeInTheDocument();
    expect(screen.getByText('Value consistent income')).toBeInTheDocument();
    expect(screen.getByText('Prefer slower, steadier growth')).toBeInTheDocument();
    expect(screen.getByText('60-80% bonds, 20-40% stocks')).toBeInTheDocument();
  });

  it('renders moderate category correctly', () => {
    render(<CategoryCard category="moderate" score={55} />);

    expect(screen.getByText('Moderate')).toBeInTheDocument();
    expect(screen.getByText('Risk Score: 55')).toBeInTheDocument();
    expect(screen.getByText('You balance growth and stability.')).toBeInTheDocument();
    expect(screen.getByText('Accept ups and downs')).toBeInTheDocument();
    expect(screen.getByText('Long-term focused')).toBeInTheDocument();
    expect(screen.getByText('Diversification-minded')).toBeInTheDocument();
    expect(screen.getByText('40-60% bonds, 40-60% stocks')).toBeInTheDocument();
  });

  it('renders aggressive category correctly', () => {
    render(<CategoryCard category="aggressive" score={75} />);

    expect(screen.getByText('Aggressive')).toBeInTheDocument();
    expect(screen.getByText('Risk Score: 75')).toBeInTheDocument();
    expect(screen.getByText('You pursue growth and tolerate volatility.')).toBeInTheDocument();
    expect(screen.getByText('Comfortable with large swings')).toBeInTheDocument();
    expect(screen.getByText('Very long time horizon')).toBeInTheDocument();
    expect(screen.getByText('Growth over income')).toBeInTheDocument();
    expect(screen.getByText('20-40% bonds, 60-80% stocks')).toBeInTheDocument();
  });

  it('renders very-aggressive category correctly', () => {
    render(<CategoryCard category="very-aggressive" score={95} />);

    expect(screen.getByText('Very Aggressive')).toBeInTheDocument();
    expect(screen.getByText('Risk Score: 95')).toBeInTheDocument();
    expect(screen.getByText('You seek maximum growth with high risk tolerance.')).toBeInTheDocument();
    expect(screen.getByText('Embrace volatility')).toBeInTheDocument();
    expect(screen.getByText('Longest time horizon')).toBeInTheDocument();
    expect(screen.getByText('Concentrated positions acceptable')).toBeInTheDocument();
    expect(screen.getByText('0-20% bonds, 80-100% stocks')).toBeInTheDocument();
  });

  it('shows secondary category message when provided', () => {
    render(
      <CategoryCard
        category="moderate"
        secondaryCategory="conservative"
        score={55}
      />
    );

    // Check for the presence of the secondary category message elements
    expect(screen.getByText(/You also share some characteristics with/)).toBeInTheDocument();
    expect(screen.getByText('Conservative')).toBeInTheDocument();
    expect(screen.getByText(/investors\./)).toBeInTheDocument();
  });

  it('does not show secondary category message when null', () => {
    render(
      <CategoryCard
        category="moderate"
        secondaryCategory={null}
        score={55}
      />
    );

    expect(screen.queryByText(/You also share some characteristics/)).not.toBeInTheDocument();
  });

  it('does not show secondary category message when undefined', () => {
    render(<CategoryCard category="moderate" score={55} />);

    expect(screen.queryByText(/You also share some characteristics/)).not.toBeInTheDocument();
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

  it('displays all characteristics as bullet points', () => {
    render(<CategoryCard category="moderate" score={55} />);

    const characteristics = [
      'Accept ups and downs',
      'Long-term focused',
      'Diversification-minded'
    ];

    characteristics.forEach(char => {
      expect(screen.getByText(char)).toBeInTheDocument();
    });

    // Check that they are in a list
    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(3);
  });

  it('shows typical allocation in footer', () => {
    render(<CategoryCard category="moderate" score={55} />);

    const allocationText = screen.getByText('40-60% bonds, 40-60% stocks');
    expect(allocationText).toBeInTheDocument();

    // Check it's in a footer-like section (border-top)
    const parent = allocationText.parentElement;
    expect(parent).toHaveClass('border-t');
  });

  it('applies correct border color based on category', () => {
    const { container } = render(<CategoryCard category="moderate" score={55} />);

    const card = container.querySelector('[style*="border-color"]');
    expect(card).toHaveAttribute('style', expect.stringContaining('rgb(0, 128, 0)'));
  });
});