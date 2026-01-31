import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { ConfidenceBand } from '../confidence-calculator';
import {
  createAssessmentCompletedEvent,
  createOverrideTriggeredEvent,
  createFlagRaisedEvent,
  logAssessmentEvent
} from '../monitoring';

const band: ConfidenceBand = {
  lower: 40,
  upper: 60,
  primary_category: 'moderate',
  secondary_category: null,
  band_width: 20,
  adjustment_reasons: []
};

const baseDetails = {
  normalized_score: 55,
  confidence_band: band,
  category: 'moderate',
  overrides_applied: [],
  flags_raised: [],
  completion_time_seconds: 48,
  mpt_score: 60,
  prospect_score: 50
};

describe('monitoring', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('createAssessmentCompletedEvent builds expected structure', () => {
    const event = createAssessmentCompletedEvent('session-1', baseDetails, {
      completion_time_seconds: 48
    });
    expect(event.event_type).toBe('assessment_completed');
    expect(event.session_id).toBe('session-1');
    expect(event.timestamp).toBeInstanceOf(Date);
    expect(event.data.normalized_score).toBe(55);
    expect(event.data.confidence_band).toEqual(band);
    expect(event.data.category).toBe('moderate');
    expect(event.data.overrides_applied).toEqual([]);
    expect(event.data.flags_raised).toEqual([]);
    expect(event.data.completion_time_seconds).toBe(48);
    expect(event.data.mpt_score).toBe(60);
    expect(event.data.prospect_score).toBe(50);
  });

  it('createOverrideTriggeredEvent adds overrideType to overrides_applied', () => {
    const event = createOverrideTriggeredEvent('session-2', 'time_horizon_override', baseDetails);
    expect(event.event_type).toBe('override_triggered');
    expect(event.data.overrides_applied).toContain('time_horizon_override');
  });

  it('createFlagRaisedEvent adds flagType to flags_raised', () => {
    const event = createFlagRaisedEvent('session-3', 'high_uncertainty', baseDetails);
    expect(event.event_type).toBe('flag_raised');
    expect(event.data.flags_raised).toContain('high_uncertainty');
  });

  it('logAssessmentEvent logs structured JSON', () => {
    const event = createAssessmentCompletedEvent('session-4', baseDetails, {
      completion_time_seconds: 48
    });
    logAssessmentEvent(event);
    expect(consoleSpy).toHaveBeenCalledTimes(1);
    const logged = consoleSpy.mock.calls[0][0];
    expect(typeof logged).toBe('string');
    const parsed = JSON.parse(logged);
    expect(parsed.event_type).toBe('assessment_completed');
    expect(parsed.session_id).toBe('session-4');
  });
});
