import type { ConfidenceBand } from './confidence-calculator';

export interface AssessmentEvent {
  event_type: 'assessment_completed' | 'override_triggered' | 'flag_raised' | 'branching_path_selected';
  timestamp: Date;
  session_id: string;
  data: {
    normalized_score?: number;
    confidence_band?: ConfidenceBand;
    category?: string;
    overrides_applied?: string[];
    flags_raised?: string[];
    completion_time_seconds?: number;
    mpt_score?: number;
    prospect_score?: number;
    // Branching-specific fields
    phase1_score?: number;
    selected_path?: string;
    questions_in_path?: string[];
  };
}

export interface ScoringResultInput {
  normalized_score: number;
  confidence_band: ConfidenceBand;
  category: string;
  overrides_applied?: string[];
  flags_raised?: string[];
  mpt_score: number;
  prospect_score: number;
}

export interface TimingDataInput {
  completion_time_seconds: number;
}

export interface EventDetailsInput extends ScoringResultInput, TimingDataInput {}

export const logAssessmentEvent = (event: AssessmentEvent): void => {
  // TODO: integrate with production logging service
  console.log(JSON.stringify(event));
};

const normalizeEventData = (details: EventDetailsInput) => ({
  normalized_score: details.normalized_score,
  confidence_band: details.confidence_band,
  category: details.category,
  overrides_applied: details.overrides_applied ?? [],
  flags_raised: details.flags_raised ?? [],
  completion_time_seconds: details.completion_time_seconds,
  mpt_score: details.mpt_score,
  prospect_score: details.prospect_score
});

export const createAssessmentCompletedEvent = (
  sessionId: string,
  scoringResult: ScoringResultInput,
  timingData: TimingDataInput
): AssessmentEvent => ({
  event_type: 'assessment_completed',
  timestamp: new Date(),
  session_id: sessionId,
  data: normalizeEventData({ ...scoringResult, ...timingData })
});

export const createOverrideTriggeredEvent = (
  sessionId: string,
  overrideType: string,
  details: EventDetailsInput
): AssessmentEvent => {
  const data = normalizeEventData(details);
  return {
    event_type: 'override_triggered',
    timestamp: new Date(),
    session_id: sessionId,
    data: {
      ...data,
      overrides_applied: Array.from(new Set([...data.overrides_applied, overrideType]))
    }
  };
};

export const createFlagRaisedEvent = (
  sessionId: string,
  flagType: string,
  details: EventDetailsInput
): AssessmentEvent => {
  const data = normalizeEventData(details);
  return {
    event_type: 'flag_raised',
    timestamp: new Date(),
    session_id: sessionId,
    data: {
      ...data,
      flags_raised: Array.from(new Set([...data.flags_raised, flagType]))
    }
  };
};

export const createBranchingPathSelectedEvent = (
  sessionId: string,
  phase1Score: number,
  selectedPath: string,
  questionsInPath: string[]
): AssessmentEvent => ({
  event_type: 'branching_path_selected',
  timestamp: new Date(),
  session_id: sessionId,
  data: {
    phase1_score: phase1Score,
    selected_path: selectedPath,
    questions_in_path: questionsInPath
  }
});
