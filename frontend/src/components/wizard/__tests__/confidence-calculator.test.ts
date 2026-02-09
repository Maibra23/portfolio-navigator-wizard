import { describe, it, expect } from 'vitest';
import {
  ADJUSTMENT_TOOLTIPS,
  calculateConfidenceBand,
  determineBoundaryProximity,
  determineGradientIntensity,
  getCategory,
  getSecondaryCategory
} from '../confidence-calculator';

describe('confidence-calculator', () => {
  it('getCategory uses exclusive upper bounds', () => {
    expect(getCategory(0)).toBe('very-conservative');
    expect(getCategory(19)).toBe('very-conservative');
    expect(getCategory(20)).toBe('conservative');
    expect(getCategory(39)).toBe('conservative');
    expect(getCategory(40)).toBe('moderate');
    expect(getCategory(59)).toBe('moderate');
    expect(getCategory(60)).toBe('aggressive');
    expect(getCategory(79)).toBe('aggressive');
    expect(getCategory(80)).toBe('very-aggressive');
    expect(getCategory(81)).toBe('very-aggressive');
  });

  it('getSecondaryCategory returns adjacent category when band crosses a boundary', () => {
    expect(getSecondaryCategory(39, 4)).toBe('moderate');
    expect(getSecondaryCategory(61, 3)).toBe('moderate');
    expect(getSecondaryCategory(10, 2)).toBeNull();
  });

  it('determineGradientIntensity returns narrow/medium/wide correctly', () => {
    expect(determineGradientIntensity(8)).toBe('narrow');
    expect(determineGradientIntensity(10)).toBe('medium');
    expect(determineGradientIntensity(15)).toBe('medium');
    expect(determineGradientIntensity(16)).toBe('wide');
  });

  it('determineBoundaryProximity returns crossing when categories differ', () => {
    expect(determineBoundaryProximity(20, 18, 22)).toBe('crossing');
  });

  it('determineBoundaryProximity returns near when close to boundary', () => {
    expect(determineBoundaryProximity(38, 35, 39)).toBe('near');
  });

  it('determineBoundaryProximity returns far when not near boundary', () => {
    expect(determineBoundaryProximity(30, 27, 33)).toBe('far');
  });

  it('calculateConfidenceBand applies variance, speed, and divergence adjustments', () => {
    const band = calculateConfidenceBand(
      50,
      { q1: 1, q2: 5 },
      20,
      60,
      4,
      4,
      { q1: 5, q2: 5 }
    );
    expect(band.band_width).toBe(19);
    expect(band.adjustment_reasons).toEqual(['variance', 'speed', 'divergence']);
    expect(band.lower).toBe(40.5);
    expect(band.upper).toBe(59.5);
    expect(band.primary_category).toBe('moderate');
    expect(band.secondary_category).toBeNull();
  });

  it('calculateConfidenceBand defaults to base uncertainty when no triggers', () => {
    const answers: Record<string, number> = {};
    const maxScores: Record<string, number> = {};
    for (let i = 0; i < 12; i++) {
      answers[`q${i}`] = 2 + (i % 2);
      maxScores[`q${i}`] = 5;
    }
    const band = calculateConfidenceBand(55, answers, 55, 55, 60, 12, maxScores);
    expect(band.band_width).toBe(10);
    expect(band.adjustment_reasons).toEqual([]);
  });

  it('ADJUSTMENT_TOOLTIPS contains expected keys', () => {
    expect(ADJUSTMENT_TOOLTIPS.variance).toBeDefined();
    expect(ADJUSTMENT_TOOLTIPS.speed).toBeDefined();
    expect(ADJUSTMENT_TOOLTIPS.divergence).toBeDefined();
    expect(ADJUSTMENT_TOOLTIPS.zero_variance).toBeDefined();
  });

  it('calculateConfidenceBand uses full penalties for 12-question assessments', () => {
    const band = calculateConfidenceBand(
      50,
      { q1: 1, q2: 5 },
      20,
      60,
      4,
      12,
      { q1: 5, q2: 5 }
    );
    expect(band.band_width).toBe(24);
    expect(band.adjustment_reasons).toEqual(['variance', 'speed', 'divergence']);
    expect(band.lower).toBe(38);
    expect(band.upper).toBe(62);
    expect(band.primary_category).toBe('moderate');
    expect(band.secondary_category).toBe('aggressive');
  });

  it('calculateConfidenceBand flags zero variance when all answers identical', () => {
    const band = calculateConfidenceBand(
      50,
      { q1: 3, q2: 3, q3: 3 },
      50,
      50,
      30,
      3,
      { q1: 5, q2: 5, q3: 5 }
    );
    expect(band.adjustment_reasons).toContain('zero_variance');
  });
});
