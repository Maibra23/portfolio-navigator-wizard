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
  it('getCategory maps scores to expected buckets', () => {
    expect(getCategory(0)).toBe('very-conservative');
    expect(getCategory(20)).toBe('very-conservative');
    expect(getCategory(21)).toBe('conservative');
    expect(getCategory(40)).toBe('conservative');
    expect(getCategory(41)).toBe('moderate');
    expect(getCategory(60)).toBe('moderate');
    expect(getCategory(61)).toBe('aggressive');
    expect(getCategory(80)).toBe('aggressive');
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
    // With 4 questions (short assessment), penalties are reduced:
    // base=5, variance=+1, speed=+2, divergence=+1.5 → total=9.5 → band_width=19
    const band = calculateConfidenceBand(
      50,
      { q1: 1, q2: 5 },
      20,
      60,
      4,
      4
    );
    expect(band.band_width).toBe(19);
    expect(band.adjustment_reasons).toEqual(['variance', 'speed', 'divergence']);
    expect(band.lower).toBe(40.5);
    expect(band.upper).toBe(59.5);
    expect(band.primary_category).toBe('moderate');
    expect(band.secondary_category).toBeNull(); // Band stays within moderate
  });

  it('calculateConfidenceBand defaults to base uncertainty when no triggers', () => {
    const band = calculateConfidenceBand(
      55,
      { q1: 0.5, q2: 0.5, q3: 0.5 },
      55,
      60,
      60,
      12
    );
    expect(band.band_width).toBe(10);
    expect(band.adjustment_reasons).toEqual([]);
  });

  it('ADJUSTMENT_TOOLTIPS contains expected keys', () => {
    expect(ADJUSTMENT_TOOLTIPS.variance).toBeDefined();
    expect(ADJUSTMENT_TOOLTIPS.speed).toBeDefined();
    expect(ADJUSTMENT_TOOLTIPS.divergence).toBeDefined();
  });

  it('calculateConfidenceBand uses full penalties for 12-question assessments', () => {
    // With 12 questions (full assessment), penalties are standard:
    // base=5, variance=+2, speed=+2, divergence=+3 → total=12 → band_width=24
    const band = calculateConfidenceBand(
      50,
      { q1: 1, q2: 5 },
      20,
      60,
      4,
      12
    );
    expect(band.band_width).toBe(24);
    expect(band.adjustment_reasons).toEqual(['variance', 'speed', 'divergence']);
    expect(band.lower).toBe(38);
    expect(band.upper).toBe(62);
    expect(band.primary_category).toBe('moderate');
    expect(band.secondary_category).toBe('aggressive');
  });
});
