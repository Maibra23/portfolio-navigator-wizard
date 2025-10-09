import { render, screen } from '@testing-library/react';
import App from './App';
import { describe, it, expect } from 'vitest';

describe('App', () => {
  it('renders without crashing and shows app container', () => {
    render(<App />);
    expect(screen.getByTestId('app-container')).toBeInTheDocument();
  });
}); 