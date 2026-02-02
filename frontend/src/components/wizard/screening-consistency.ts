/**
 * Screening contradiction detection.
 * Used when experience and knowledge answers suggest a mismatch (e.g. high experience + beginner knowledge).
 */

export const SCREENING_CONTRADICTION = {
  trigger: {
    experience: ['6-10', '10+'] as readonly string[],
    knowledge: 'beginner' as const
  },
  prompt: {
    message: "You indicated significant investment experience but beginner-level knowledge. Which better describes your situation?",
    options: [
      {
        label: "I have experience but still consider myself a beginner",
        action: 'keep_beginner' as const,
        result: { knowledge: 'beginner' as const }
      },
      {
        label: "I know more than a beginner—let me update my answer",
        action: 'revise_knowledge' as const,
        result: null
      }
    ]
  }
} as const;

export interface ContradictionResult {
  message: string;
  options: ReadonlyArray<{
    label: string;
    action: string;
    result: { knowledge: string } | null;
  }>;
}

/**
 * Returns the contradiction prompt if screening answers trigger the rule, otherwise null.
 * Trigger: experience is '6-10' or '10+' AND knowledge is 'beginner'.
 */
export function checkScreeningContradiction(
  experience: string,
  knowledge: string
): ContradictionResult | null {
  const experienceTriggers = SCREENING_CONTRADICTION.trigger.experience;
  const knowledgeTrigger = SCREENING_CONTRADICTION.trigger.knowledge;

  if (!experienceTriggers.includes(experience) || knowledge !== knowledgeTrigger) {
    return null;
  }

  return {
    message: SCREENING_CONTRADICTION.prompt.message,
    options: SCREENING_CONTRADICTION.prompt.options
  };
}
