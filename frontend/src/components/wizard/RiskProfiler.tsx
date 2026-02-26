import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepCardHeader } from "@/components/wizard/StepCardHeader";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Progress } from "@/components/ui/progress";
import {
  ArrowRight,
  ArrowLeft,
  Shield,
  TrendingUp,
  AlertTriangle,
  Zap,
  Target,
  Brain,
} from "lucide-react";
import type { RiskProfile } from "../PortfolioWizard";

interface RiskProfilerProps {
  onNext: () => void;
  onPrev: () => void;
  onProfileUpdate: (profile: RiskProfile, analysis: any) => void;
  currentProfile: RiskProfile;
  currentAnalysis?: any;
}

// Screening Questions Interface
interface ScreeningData {
  ageGroup: "under-19" | "above-19" | null;
  experience: "0-2" | "3-5" | "6-10" | "10+" | null;
  knowledge: "beginner" | "intermediate" | "advanced" | null;
}

/**
 * SCREENING QUESTIONS: Implemented in UI (lines 724-823)
 * - S1: Age group (under-19 vs above-19) - maxScore: 0, construct: 'age_screening'
 * - S2: Investment experience (0-2, 3-5, 6-10, 10+) - maxScore: 0, construct: 'experience_screening'
 * - S3: Investment knowledge (beginner, intermediate, advanced) - maxScore: 0, construct: 'knowledge_screening'
 * These are NOT scored but determine question routing logic.
 */

// Question Interface with Metadata for Scoring
interface Question {
  // Core identifiers
  id: string;

  // NEW: Grouping for scoring pipeline
  group: "MPT" | "PROSPECT" | "SCREENING";

  // Type classification (legacy compatibility)
  type: "mpt" | "prospect" | "storyline";

  // Question text
  question: string;
  text?: string; // Alias for question (optional)

  // NEW: Scoring metadata (required for proper normalization)
  maxScore: number; // Maximum points for this question
  construct: string; // Psychological construct being measured (e.g., 'loss_aversion', 'time_horizon')
  difficulty?: "low" | "medium" | "high"; // Optional difficulty indicator
  /** If true, question is shown in UI but excluded from risk score (preference only). */
  excludeFromScoring?: boolean;

  // Answer options (enhanced structure with backward compatibility)
  options?: Array<{
    label?: string; // Display text (preferred for new questions)
    value: number; // Numeric value for scoring (1-5 or 1-4) - MUST be number for proper normalization
    text: string; // Legacy text field (backward compatibility)
    score: number; // Legacy score field (backward compatibility)
  }>;

  // Optional UI configurations
  sliderConfig?: {
    min: number;
    max: number;
    step: number;
    labels: { min: string; max: string };
  };
  gamifiedText?: string;
  storylineData?: StorylineNode;
  /** Optional note for scoring interpretation (e.g. counterfactual / recency). */
  scoring_note?: string;
  /** Optional note for UI (e.g. special framing). */
  ui_note?: string;
}

// Risk Profile Result Interface
interface RiskResult {
  raw_score: number;
  normalized_score: number;
  normalized_mpt?: number;
  normalized_prospect?: number;
  risk_category: RiskProfile;
  color_code: string;
}

// Progressive Storyline for Gamified Experience
interface StorylineNode {
  id: string;
  scenario: string;
  visual: string;
  avatarMood: "excited" | "worried" | "confident" | "surprised" | "happy";
  options: Array<{
    text: string;
    icon: string;
    consequence: string;
    score: number;
    nextScenario?: string;
  }>;
  feedback?: string;
}

const GAMIFIED_STORYLINE: StorylineNode[] = [
  {
    id: "story-1",
    scenario:
      "You received $1,000—maybe a gift or from work. You won't need it for 3 years. What do you do?",
    visual: "🏆",
    avatarMood: "excited",
    options: [
      {
        text: "Savings account",
        icon: "🛡️",
        consequence: "Safe, grows slowly",
        score: 1,
        nextScenario: "Your money is safe, but it grows slowly over the years.",
      },
      {
        text: "Save most, invest a little",
        icon: "📈",
        consequence: "Mostly safe with learning",
        score: 2,
        nextScenario: "You keep most safe and learn a bit about investing.",
      },
      {
        text: "Invest most in diversified fund",
        icon: "📊",
        consequence: "Could grow, will fluctuate",
        score: 3,
        nextScenario:
          "Your money could grow, but you'll see some ups and downs.",
      },
      {
        text: "High growth potential investment",
        icon: "🎲",
        consequence: "Could grow a lot or lose",
        score: 4,
        nextScenario: "You're aiming for higher growth—with higher risk.",
      },
    ],
    feedback: "Your gaming coach says: 'Every choice shapes your future!'",
  },
  {
    id: "story-2",
    scenario:
      "📈 Your investment choice is working! But now the market is getting wild. Your $1,000 has grown to $1,500, but there is news of a big market drop coming.",
    visual: "📉",
    avatarMood: "worried",
    options: [
      {
        text: "🏃‍♂️ Sell everything now",
        icon: "💨",
        consequence: "Lock in your $500 profit",
        score: 1,
        nextScenario:
          "You're safe with your profit, but what if the market recovers?",
      },
      {
        text: "🔄 Sell half, keep half",
        icon: "⚖️",
        consequence: "Balance safety and opportunity",
        score: 2,
        nextScenario: "Smart move! You're protected but still in the game.",
      },
      {
        text: "🤔 Wait and see",
        icon: "👀",
        consequence: "Ride out the storm",
        score: 3,
        nextScenario: "You decide to stay calm and not panic sell.",
      },
      {
        text: "💎 Buy more on the dip",
        icon: "📈",
        consequence: "Double down on opportunity",
        score: 4,
        nextScenario: "You see this as a chance to buy more at lower prices!",
      },
    ],
    feedback:
      "Your mentor says: 'Markets go up and down, but your strategy matters most!'",
  },
  {
    id: "story-3",
    scenario:
      "🎯 Time for a big decision! You have $2,000 saved up. Your dream is to start your own business, but you also want to travel the world.",
    visual: "🌍",
    avatarMood: "confident",
    options: [
      {
        text: "🏦 Put it all in savings",
        icon: "🔒",
        consequence: "Safe and secure, but slow growth",
        score: 1,
        nextScenario: "Your money is protected, but it is not growing much.",
      },
      {
        text: "✈️ Use it for travel now",
        icon: "🎒",
        consequence: "Amazing experiences, but no investment",
        score: 2,
        nextScenario: "You have incredible memories, but your money is gone.",
      },
      {
        text: "💼 Start a small business",
        icon: "🚀",
        consequence: "High risk, but you're your own boss",
        score: 3,
        nextScenario: "You're taking control of your future!",
      },
      {
        text: "🎲 Invest in crypto/startups",
        icon: "⚡",
        consequence: "Maximum risk, maximum potential",
        score: 4,
        nextScenario: "You're going all-in on the future!",
      },
    ],
    feedback:
      "Your life coach says: 'Balance today's dreams with tomorrow's security!'",
  },
  {
    id: "story-4",
    scenario:
      "🎉 Surprise! Your choices paid off! You now have $5,000. But here is the twist - you discover a once-in-a-lifetime opportunity that requires all your money.",
    visual: "💎",
    avatarMood: "surprised",
    options: [
      {
        text: "❌ Too risky, keep my money",
        icon: "🛡️",
        consequence: "Stay safe with what you have",
        score: 1,
        nextScenario:
          "You play it safe, but wonder about the opportunity you missed.",
      },
      {
        text: "🤝 Invest 25% of my money",
        icon: "⚖️",
        consequence: "Moderate risk, moderate potential",
        score: 2,
        nextScenario: "You're testing the waters without going all-in.",
      },
      {
        text: "💪 Invest 50% of my money",
        icon: "🎯",
        consequence: "Balanced approach",
        score: 3,
        nextScenario: "You're taking a calculated risk.",
      },
      {
        text: "🚀 Go all-in! Invest everything",
        icon: "🔥",
        consequence: "Maximum risk, maximum reward",
        score: 4,
        nextScenario: "You're betting everything on this opportunity!",
      },
    ],
    feedback:
      "Your financial advisor says: 'Big opportunities come with big decisions!'",
  },
  {
    id: "story-5",
    scenario:
      "A friend asks what YOU would do with $500 based on your experience.",
    visual: "🤝",
    avatarMood: "happy",
    options: [
      {
        text: "Keep it safe—protecting money is most important",
        icon: "🛡️",
        consequence: "Conservative approach",
        score: 1,
        nextScenario: "You'd keep it safe.",
      },
      {
        text: "Save most, maybe invest tiny bit to learn",
        icon: "📚",
        consequence: "Mostly safe with a little learning",
        score: 2,
        nextScenario: "You'd save most and dabble a little.",
      },
      {
        text: "Invest good portion, accept some ups and downs",
        icon: "🌱",
        consequence: "Balanced growth approach",
        score: 3,
        nextScenario: "You'd put a good portion to work.",
      },
      {
        text: "Look for growth—have to take some risk",
        icon: "🎲",
        consequence: "Growth-oriented approach",
        score: 4,
        nextScenario: "You'd look for growth and accept risk.",
      },
    ],
    feedback:
      "Your friend says: 'Thanks for the advice! I'll think about it carefully.'",
  },
];

// MPT Question Pool (Modern Portfolio Theory - 15 questions, all 1-5 scale)
// Total maxScore in pool: 75. Effective for scoring: 12 × 5 = 60 (M13, M14, M15 excluded from scoring; see riskUtils.SCORING_EXCLUSIONS).
const MPT_QUESTIONS: Question[] = [
  {
    id: "M1",
    group: "MPT",
    type: "mpt",
    question:
      "How would you prefer to allocate your investments over a long time horizon?",
    text: "How would you prefer to allocate your investments over a long time horizon?",
    maxScore: 5,
    construct: "time_horizon",
    difficulty: "low",
    options: [
      {
        label: "All in stable, low-risk assets",
        value: 1,
        text: "All in stable, low-risk assets",
        score: 1,
      },
      {
        label: "Mostly stable with some growth investments",
        value: 2,
        text: "Mostly stable with some growth investments",
        score: 2,
      },
      {
        label: "Balanced mix of stable and growth",
        value: 3,
        text: "Balanced mix of stable and growth",
        score: 3,
      },
      {
        label: "Mostly growth with some stable assets",
        value: 4,
        text: "Mostly growth with some stable assets",
        score: 4,
      },
      {
        label: "All in high-growth investments",
        value: 5,
        text: "All in high-growth investments",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "All Stable", max: "All Growth" },
    },
    gamifiedText:
      "If you were building a team for a long adventure, would you pick all defenders, or mostly attackers?",
  },
  {
    id: "M2",
    group: "MPT",
    type: "mpt",
    question: "What is your preferred investment time horizon?",
    text: "What is your preferred investment time horizon?",
    maxScore: 5,
    construct: "time_horizon",
    difficulty: "low",
    options: [
      {
        label: "Less than 2 years",
        value: 1,
        text: "Less than 2 years",
        score: 1,
      },
      { label: "2-5 years", value: 2, text: "2-5 years", score: 2 },
      { label: "5-10 years", value: 3, text: "5-10 years", score: 3 },
      { label: "10-20 years", value: 4, text: "10-20 years", score: 4 },
      {
        label: "More than 20 years",
        value: 5,
        text: "More than 20 years",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "2 years", max: "20+ years" },
    },
    gamifiedText:
      "How long do you want to keep your money invested? Think of it like planting a tree - how long until you want to see it grow big?",
  },
  {
    id: "M3",
    group: "MPT",
    type: "mpt",
    question: "How much volatility can you tolerate in your portfolio?",
    text: "How much volatility can you tolerate in your portfolio?",
    maxScore: 5,
    construct: "volatility_tolerance",
    difficulty: "low",
    options: [
      {
        label: "Very low - I prefer stable returns",
        value: 1,
        text: "Very low - I prefer stable returns",
        score: 1,
      },
      {
        label: "Low - some ups and downs are okay",
        value: 2,
        text: "Low - some ups and downs are okay",
        score: 2,
      },
      {
        label: "Moderate - I can handle regular fluctuations",
        value: 3,
        text: "Moderate - I can handle regular fluctuations",
        score: 3,
      },
      {
        label: "High - I am comfortable with significant swings",
        value: 4,
        text: "High - I am comfortable with significant swings",
        score: 4,
      },
      {
        label: "Very high - I thrive on market excitement",
        value: 5,
        text: "Very high - I thrive on market excitement",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Very Stable", max: "Very Exciting" },
    },
    gamifiedText:
      "Think of your money like a roller coaster! How bumpy of a ride are you okay with?",
  },
  {
    id: "M4",
    group: "MPT",
    type: "mpt",
    question:
      "What percentage of your total savings are you planning to invest?",
    text: "What percentage of your total savings are you planning to invest?",
    maxScore: 5,
    construct: "capital_allocation",
    difficulty: "medium",
    options: [
      { label: "Less than 10%", value: 1, text: "Less than 10%", score: 1 },
      { label: "10-25%", value: 2, text: "10-25%", score: 2 },
      { label: "25-50%", value: 3, text: "25-50%", score: 3 },
      { label: "50-75%", value: 4, text: "50-75%", score: 4 },
      { label: "More than 75%", value: 5, text: "More than 75%", score: 5 },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "10%", max: "75%+" },
    },
    gamifiedText:
      "Out of all your savings, how much do you want to put into investments? Like deciding how much of your allowance to save vs. spend!",
  },
  {
    id: "M5",
    group: "MPT",
    type: "mpt",
    question:
      "How important is it that your investments provide steady income?",
    text: "How important is it that your investments provide steady income?",
    maxScore: 5,
    construct: "income_requirement",
    difficulty: "low",
    options: [
      {
        label: "Extremely important - I need regular income",
        value: 1,
        text: "Extremely important - I need regular income",
        score: 1,
      },
      { label: "Very important", value: 2, text: "Very important", score: 2 },
      {
        label: "Somewhat important",
        value: 3,
        text: "Somewhat important",
        score: 3,
      },
      {
        label: "Not very important",
        value: 4,
        text: "Not very important",
        score: 4,
      },
      {
        label: "Not important - I focus on growth",
        value: 5,
        text: "Not important - I focus on growth",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Need Income", max: "Want Growth" },
    },
    gamifiedText:
      "Do you want your investments to give you regular money (like an allowance) or just grow bigger over time?",
  },
  {
    id: "M6",
    group: "MPT",
    type: "mpt",
    question: "What is your primary investment goal?",
    text: "What is your primary investment goal?",
    maxScore: 5,
    construct: "capital_preservation",
    difficulty: "low",
    options: [
      {
        label: "Capital preservation",
        value: 1,
        text: "Capital preservation",
        score: 1,
      },
      { label: "Steady income", value: 2, text: "Steady income", score: 2 },
      { label: "Balanced growth", value: 3, text: "Balanced growth", score: 3 },
      {
        label: "Growth with some risk",
        value: 4,
        text: "Growth with some risk",
        score: 4,
      },
      {
        label: "Maximum growth potential",
        value: 5,
        text: "Maximum growth potential",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Keep Safe", max: "Grow Fast" },
    },
    gamifiedText:
      "What is your main goal? Keep your money safe, get regular payments, or make it grow as much as possible?",
  },
  {
    id: "M7",
    group: "MPT",
    type: "mpt",
    question: "How do you plan to use your investment returns?",
    text: "How do you plan to use your investment returns?",
    maxScore: 5,
    construct: "return_utilization",
    difficulty: "medium",
    options: [
      {
        label: "Immediate spending needs",
        value: 1,
        text: "Immediate spending needs",
        score: 1,
      },
      {
        label: "Regular living expenses",
        value: 2,
        text: "Regular living expenses",
        score: 2,
      },
      {
        label: "Supplemental income",
        value: 3,
        text: "Supplemental income",
        score: 3,
      },
      {
        label: "Future large purchases",
        value: 4,
        text: "Future large purchases",
        score: 4,
      },
      {
        label: "Long-term wealth building",
        value: 5,
        text: "Long-term wealth building",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Spend Now", max: "Build Wealth" },
    },
    gamifiedText:
      "What will you do with the money you make? Spend it right away or let it grow for your future?",
  },
  {
    id: "M8",
    group: "MPT",
    type: "mpt",
    question: "What is your reaction to market downturns?",
    text: "What is your reaction to market downturns?",
    maxScore: 5,
    construct: "market_reaction",
    difficulty: "medium",
    options: [
      {
        label: "I would sell immediately",
        value: 1,
        text: "I would sell immediately",
        score: 1,
      },
      {
        label: "I would be very concerned",
        value: 2,
        text: "I would be very concerned",
        score: 2,
      },
      {
        label: "I would be worried but hold",
        value: 3,
        text: "I would be worried but hold",
        score: 3,
      },
      {
        label: "I would view it as temporary",
        value: 4,
        text: "I would view it as temporary",
        score: 4,
      },
      {
        label: "I would see it as opportunity",
        value: 5,
        text: "I would see it as opportunity",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Sell Fast", max: "Buy More" },
    },
    gamifiedText:
      "When the market goes down (like when your favorite game price drops), what would you do?",
  },
  {
    id: "M9",
    group: "MPT",
    type: "mpt",
    question: "How would you prefer to spread your investments?",
    text: "How would you prefer to spread your investments?",
    maxScore: 5,
    construct: "diversification_preference",
    difficulty: "medium",
    options: [
      {
        label: "Concentrated in 1-2",
        value: 1,
        text: "Concentrated in 1-2",
        score: 1,
      },
      { label: "3-5 holdings", value: 2, text: "3-5 holdings", score: 2 },
      { label: "6-10 holdings", value: 3, text: "6-10 holdings", score: 3 },
      {
        label: "Spread across 6-10",
        value: 4,
        text: "Spread across 6-10",
        score: 4,
      },
      {
        label: "Spread across 10+",
        value: 5,
        text: "Spread across 10+",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Concentrated", max: "Spread 10+" },
    },
    gamifiedText:
      "Would you rather have a few favorite games or a huge collection of different games?",
  },
  {
    id: "M10",
    group: "MPT",
    type: "mpt",
    question: "How quickly might you need access to your invested money?",
    text: "How quickly might you need access to your invested money?",
    maxScore: 5,
    construct: "liquidity_constraint",
    difficulty: "low",
    options: [
      {
        label: "Within days (need immediate access)",
        value: 1,
        text: "Within days (need immediate access)",
        score: 1,
      },
      {
        label: "Within months (short-term access)",
        value: 2,
        text: "Within months (short-term access)",
        score: 2,
      },
      {
        label: "Within 1-2 years",
        value: 3,
        text: "Within 1-2 years",
        score: 3,
      },
      {
        label: "Within 3-5 years",
        value: 4,
        text: "Within 3-5 years",
        score: 4,
      },
      {
        label: "Not for 5+ years (can lock it up)",
        value: 5,
        text: "Not for 5+ years (can lock it up)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Need Soon", max: "Long Term" },
    },
    gamifiedText:
      "If you saved your allowance, would you want to spend it soon or save it for something big later?",
  },
  {
    id: "M11",
    group: "MPT",
    type: "mpt",
    question:
      "What percentage of your portfolio would you put in your single best investment idea?",
    text: "What percentage of your portfolio would you put in your single best investment idea?",
    maxScore: 5,
    construct: "concentration_risk",
    difficulty: "medium",
    options: [
      {
        label: "Less than 5% (very diversified)",
        value: 1,
        text: "Less than 5% (very diversified)",
        score: 1,
      },
      { label: "5-10%", value: 2, text: "5-10%", score: 2 },
      { label: "10-20%", value: 3, text: "10-20%", score: 3 },
      { label: "20-40%", value: 4, text: "20-40%", score: 4 },
      {
        label: "More than 40% (concentrated bet)",
        value: 5,
        text: "More than 40% (concentrated bet)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Very Spread Out", max: "Concentrated" },
    },
    gamifiedText:
      "If you had 100 coins, how many would you bet on your favorite team winning?",
  },
  {
    id: "M12",
    group: "MPT",
    type: "mpt",
    question:
      "If your investments dropped 20%, how long would you be willing to wait for recovery?",
    text: "If your investments dropped 20%, how long would you be willing to wait for recovery?",
    maxScore: 5,
    construct: "recovery_tolerance",
    difficulty: "medium",
    options: [
      {
        label: "Less than 6 months",
        value: 1,
        text: "Less than 6 months",
        score: 1,
      },
      { label: "6-12 months", value: 2, text: "6-12 months", score: 2 },
      { label: "1-2 years", value: 3, text: "1-2 years", score: 3 },
      { label: "2-5 years", value: 4, text: "2-5 years", score: 4 },
      {
        label: "5+ years (as long as needed)",
        value: 5,
        text: "5+ years (as long as needed)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Quick Recovery", max: "Patient" },
    },
    gamifiedText:
      "If you lost a game level, how long would you keep trying to beat it?",
  },
  {
    id: "M13",
    group: "MPT",
    type: "mpt",
    question: "How often would you want to review and adjust your investments?",
    text: "How often would you want to review and adjust your investments?",
    maxScore: 5,
    construct: "rebalancing_frequency",
    difficulty: "low",
    excludeFromScoring: true,
    options: [
      {
        label: "Daily or weekly (active management)",
        value: 1,
        text: "Daily or weekly (active management)",
        score: 1,
      },
      { label: "Monthly", value: 2, text: "Monthly", score: 2 },
      { label: "Quarterly", value: 3, text: "Quarterly", score: 3 },
      { label: "Annually", value: 4, text: "Annually", score: 4 },
      {
        label: "Rarely or never (set and forget)",
        value: 5,
        text: "Rarely or never (set and forget)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Check Often", max: "Set & Forget" },
    },
    gamifiedText:
      "Would you check your game progress every day, or just play and forget about stats?",
  },
  {
    id: "M14",
    group: "MPT",
    type: "mpt",
    question: "How important is minimizing taxes on your investment gains?",
    text: "How important is minimizing taxes on your investment gains?",
    maxScore: 5,
    construct: "tax_sensitivity",
    difficulty: "high",
    excludeFromScoring: true,
    options: [
      {
        label: "Extremely important (tax-optimized strategy)",
        value: 1,
        text: "Extremely important (tax-optimized strategy)",
        score: 1,
      },
      { label: "Very important", value: 2, text: "Very important", score: 2 },
      {
        label: "Somewhat important",
        value: 3,
        text: "Somewhat important",
        score: 3,
      },
      {
        label: "Not very important",
        value: 4,
        text: "Not very important",
        score: 4,
      },
      {
        label: "Not important (focus on returns)",
        value: 5,
        text: "Not important (focus on returns)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Tax Matters", max: "Returns Matter" },
    },
    gamifiedText:
      "Would you rather keep more of your winnings now, or potentially win bigger later?",
  },
  {
    id: "M15",
    group: "MPT",
    type: "mpt",
    question:
      "How much would you sacrifice returns to invest according to your values (environmental, social, ethical)?",
    text: "How much would you sacrifice returns to invest according to your values (environmental, social, ethical)?",
    maxScore: 5,
    construct: "values_alignment",
    difficulty: "medium",
    excludeFromScoring: true,
    options: [
      {
        label: "Significant sacrifice (values first)",
        value: 1,
        text: "Significant sacrifice (values first)",
        score: 1,
      },
      {
        label: "Moderate sacrifice",
        value: 2,
        text: "Moderate sacrifice",
        score: 2,
      },
      { label: "Small sacrifice", value: 3, text: "Small sacrifice", score: 3 },
      {
        label: "Minimal sacrifice",
        value: 4,
        text: "Minimal sacrifice",
        score: 4,
      },
      {
        label: "No sacrifice (returns only)",
        value: 5,
        text: "No sacrifice (returns only)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Values First", max: "Returns First" },
    },
    gamifiedText:
      "Would you rather support your favorite charity or win more prizes in a game?",
  },
];

// Prospect Theory Question Pool (Behavioral finance - 13 questions, mixed scales)
// Total maxScore: 53 (12 questions × 4 + 1 question × 5; includes PT-13 counterfactual)
const PROSPECT_QUESTIONS: Question[] = [
  {
    id: "PT-1",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You can take a guaranteed 5,000 SEK or a 75% chance at 7,000 SEK; which do you choose?",
    text: "You can take a guaranteed 5,000 SEK or a 75% chance at 7,000 SEK; which do you choose?",
    maxScore: 4,
    construct: "certainty_effect",
    difficulty: "low",
    options: [
      {
        label: "Guaranteed 5,000 SEK",
        value: 1,
        text: "Guaranteed 5,000 SEK",
        score: 1,
      },
      {
        label: "Probably take guaranteed 5,000 SEK",
        value: 2,
        text: "Probably take guaranteed 5,000 SEK",
        score: 2,
      },
      {
        label: "Probably take 75% chance at 7,000 SEK",
        value: 3,
        text: "Probably take 75% chance at 7,000 SEK",
        score: 3,
      },
      {
        label: "75% chance at 7,000 SEK",
        value: 4,
        text: "75% chance at 7,000 SEK",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Guaranteed 5,000 SEK", max: "Risk 7,000 SEK" },
    },
    gamifiedText:
      "You can either get 5,000 SEK for sure, or take a chance to get 7,000 SEK (but you might get nothing). What do you pick?",
  },
  {
    id: "PT-2",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You have 10,000 SEK invested. Would you prefer a guaranteed loss of 2,000 SEK or a 50% chance to lose 4,000 SEK?",
    text: "You have 10,000 SEK invested. Would you prefer a guaranteed loss of 2,000 SEK or a 50% chance to lose 4,000 SEK?",
    maxScore: 4,
    construct: "loss_aversion",
    difficulty: "medium",
    options: [
      {
        label: "Definitely take guaranteed loss of 2,000 SEK",
        value: 1,
        text: "Definitely take guaranteed loss of 2,000 SEK",
        score: 1,
      },
      {
        label: "Probably take guaranteed loss of 2,000 SEK",
        value: 2,
        text: "Probably take guaranteed loss of 2,000 SEK",
        score: 2,
      },
      {
        label: "Probably take 50% chance to lose 4,000 SEK",
        value: 3,
        text: "Probably take 50% chance to lose 4,000 SEK",
        score: 3,
      },
      {
        label: "Definitely take 50% chance to lose 4,000 SEK",
        value: 4,
        text: "Definitely take 50% chance to lose 4,000 SEK",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Lose 2,000 SEK", max: "Risk 4,000 SEK" },
    },
    gamifiedText:
      "You have 10,000 SEK. Would you rather lose 2,000 SEK for sure, or take a chance to lose 4,000 SEK (but you might lose nothing)?",
  },
  {
    id: "PT-3",
    group: "PROSPECT",
    type: "prospect",
    question: "Your portfolio gained 30% this year. Would you:",
    text: "Your portfolio gained 30% this year. Would you:",
    maxScore: 4,
    construct: "regret_aversion",
    difficulty: "low",
    options: [
      {
        label: "Sell everything to lock in gains",
        value: 1,
        text: "Sell everything to lock in gains",
        score: 1,
      },
      {
        label: "Sell some to take partial profits",
        value: 2,
        text: "Sell some to take partial profits",
        score: 2,
      },
      { label: "Hold and wait", value: 3, text: "Hold and wait", score: 3 },
      {
        label: "Invest even more",
        value: 4,
        text: "Invest even more",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Sell All", max: "Invest More" },
    },
    gamifiedText:
      "Your investments just made 30% more money! What would you do? Sell everything, sell some, keep it, or invest even more?",
  },
  {
    id: "PT-4",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You are offered two investment options: Option A has a 90% chance to return 10% and 10% chance to lose 5%. Option B has a 50% chance to return 20% and 50% chance to lose 10%. Which do you choose?",
    text: "You are offered two investment options: Option A has a 90% chance to return 10% and 10% chance to lose 5%. Option B has a 50% chance to return 20% and 50% chance to lose 10%. Which do you choose?",
    maxScore: 4,
    construct: "probability_weighting",
    difficulty: "medium",
    options: [
      {
        label: "Definitely Option A (safer)",
        value: 1,
        text: "Definitely Option A (safer)",
        score: 1,
      },
      {
        label: "Probably Option A",
        value: 2,
        text: "Probably Option A",
        score: 2,
      },
      {
        label: "Probably Option B (riskier)",
        value: 3,
        text: "Probably Option B (riskier)",
        score: 3,
      },
      {
        label: "Definitely Option B (riskier)",
        value: 4,
        text: "Definitely Option B (riskier)",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Safe Option A", max: "Risky Option B" },
    },
    gamifiedText:
      "You have two choices: A safe option that almost always wins a little, or a risky option that might win big or lose big. Which do you pick?",
  },
  {
    id: "PT-5",
    group: "PROSPECT",
    type: "prospect",
    question:
      "If you could invest in one sector, which would you choose? (Note: these have different risk levels.)",
    text: "If you could invest in one sector, which would you choose? (Note: these have different risk levels.)",
    maxScore: 4,
    construct: "sector_preference",
    difficulty: "low",
    options: [
      {
        label: "Utilities — stable, low volatility, lower growth",
        value: 1,
        text: "Utilities — stable, low volatility, lower growth",
        score: 1,
      },
      {
        label: "Consumer staples — steady growth, moderate risk",
        value: 2,
        text: "Consumer staples — steady growth, moderate risk",
        score: 2,
      },
      {
        label: "Technology — high growth potential, higher volatility",
        value: 3,
        text: "Technology — high growth potential, higher volatility",
        score: 3,
      },
      {
        label: "Cryptocurrency — highest risk and potential reward",
        value: 4,
        text: "Cryptocurrency — highest risk and potential reward",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Utilities", max: "Crypto" },
    },
    gamifiedText:
      "Which type of investment sounds most exciting to you? Safe utilities, steady consumer goods, exciting tech, or wild crypto?",
  },
  {
    id: "PT-6",
    group: "PROSPECT",
    type: "prospect",
    question: "How would you react if your investment lost 20% in one month?",
    text: "How would you react if your investment lost 20% in one month?",
    maxScore: 4,
    construct: "drawdown_behavior",
    difficulty: "medium",
    options: [
      {
        label: "Sell immediately to stop losses",
        value: 1,
        text: "Sell immediately to stop losses",
        score: 1,
      },
      {
        label: "Sell some to reduce exposure",
        value: 2,
        text: "Sell some to reduce exposure",
        score: 2,
      },
      {
        label: "Hold and wait for recovery",
        value: 3,
        text: "Hold and wait for recovery",
        score: 3,
      },
      {
        label: "Buy more while it's cheap",
        value: 4,
        text: "Buy more while it's cheap",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Sell All", max: "Buy More" },
    },
    gamifiedText:
      "Your investment just lost 20%! Do you panic and sell, sell some, wait it out, or buy more while it's cheap?",
  },
  {
    id: "PT-7",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You bought a stock at 1,000 SEK. It's now at 800 SEK, but analysts say it's worth 600 SEK. What do you do?",
    text: "You bought a stock at 1,000 SEK. It's now at 800 SEK, but analysts say it's worth 600 SEK. What do you do?",
    maxScore: 4,
    construct: "anchoring_bias",
    difficulty: "medium",
    options: [
      {
        label: "Sell immediately (avoid further loss)",
        value: 1,
        text: "Sell immediately (avoid further loss)",
        score: 1,
      },
      {
        label: "Sell when it gets back to 1,000 SEK",
        value: 2,
        text: "Sell when it gets back to 1,000 SEK",
        score: 2,
      },
      {
        label: "Hold and re-evaluate quarterly",
        value: 3,
        text: "Hold and re-evaluate quarterly",
        score: 3,
      },
      {
        label: "Buy more at the lower price",
        value: 4,
        text: "Buy more at the lower price",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Sell Now", max: "Buy More" },
    },
    gamifiedText:
      "You bought a game item for 1,000 coins. It's now worth 800, but people say it will drop to 600. What do you do?",
  },
  {
    id: "PT-8",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You have two investments: One is up 30%, another is down 30%. You need cash. Which do you sell?",
    text: "You have two investments: One is up 30%, another is down 30%. You need cash. Which do you sell?",
    maxScore: 5,
    construct: "disposition_effect",
    difficulty: "high",
    options: [
      {
        label: "Sell the winner (lock in gains)",
        value: 1,
        text: "Sell the winner (lock in gains)",
        score: 1,
      },
      {
        label: "Sell whichever is more overvalued",
        value: 2,
        text: "Sell whichever is more overvalued",
        score: 2,
      },
      {
        label: "Sell half of each",
        value: 3,
        text: "Sell half of each",
        score: 3,
      },
      {
        label: "Analyze which has better prospects",
        value: 4,
        text: "Analyze which has better prospects",
        score: 4,
      },
      {
        label: "Sell the loser (cut losses)",
        value: 5,
        text: "Sell the loser (cut losses)",
        score: 5,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: "Sell Winner", max: "Sell Loser" },
    },
    gamifiedText:
      "You have two trading cards: one doubled in value, one lost half. You need to sell one. Which?",
  },
  {
    id: "PT-9",
    group: "PROSPECT",
    type: "prospect",
    question:
      "After researching an investment for a few hours, how would you act?",
    text: "After researching an investment for a few hours, how would you act?",
    maxScore: 4,
    construct: "overconfidence_bias",
    difficulty: "medium",
    options: [
      {
        label: "I would not invest without professional advice",
        value: 1,
        text: "I would not invest without professional advice",
        score: 1,
      },
      {
        label: "I would invest a small amount to test",
        value: 2,
        text: "I would invest a small amount to test",
        score: 2,
      },
      {
        label: "I would invest a meaningful amount",
        value: 3,
        text: "I would invest a meaningful amount",
        score: 3,
      },
      {
        label: "I would invest with conviction",
        value: 4,
        text: "I would invest with conviction",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Need Advice", max: "Act with Conviction" },
    },
    gamifiedText:
      "After practicing a game for 2 hours, how sure are you that you'll win the next match?",
  },
  {
    id: "PT-10",
    group: "PROSPECT",
    type: "prospect",
    question: "Everyone is buying a trending investment. What's your reaction?",
    text: "Everyone is buying a trending investment. What's your reaction?",
    maxScore: 4,
    construct: "herd_behavior",
    difficulty: "low",
    options: [
      {
        label: "Avoid it (contrarian approach)",
        value: 1,
        text: "Avoid it (contrarian approach)",
        score: 1,
      },
      {
        label: "Be skeptical, wait and see",
        value: 2,
        text: "Be skeptical, wait and see",
        score: 2,
      },
      {
        label: "Research first, then maybe join",
        value: 3,
        text: "Research first, then maybe join",
        score: 3,
      },
      {
        label: "Join immediately (don't miss out)",
        value: 4,
        text: "Join immediately (don't miss out)",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Avoid", max: "Join Now" },
    },
    gamifiedText:
      "Everyone at school is playing a new game. Do you download it immediately or wait to see if it's actually good?",
  },
  {
    id: "PT-11",
    group: "PROSPECT",
    type: "prospect",
    question: "A company had 5 great years. How likely is year 6 to be great?",
    text: "A company had 5 great years. How likely is year 6 to be great?",
    maxScore: 4,
    construct: "representativeness_bias",
    difficulty: "high",
    options: [
      {
        label: "No more likely than average",
        value: 1,
        text: "No more likely than average",
        score: 1,
      },
      {
        label: "Less likely (regression to mean)",
        value: 2,
        text: "Less likely (regression to mean)",
        score: 2,
      },
      { label: "Somewhat likely", value: 3, text: "Somewhat likely", score: 3 },
      {
        label: "Very likely (hot streak continues)",
        value: 4,
        text: "Very likely (hot streak continues)",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Average Odds", max: "Hot Streak" },
    },
    gamifiedText:
      "Your friend won 5 games in a row. Do you think they'll win the 6th?",
  },
  {
    id: "PT-12",
    group: "PROSPECT",
    type: "prospect",
    question:
      "You inherited a stock worth 50,000 SEK. You wouldn't buy it at this price. Do you keep it?",
    text: "You inherited a stock worth 50,000 SEK. You wouldn't buy it at this price. Do you keep it?",
    maxScore: 4,
    construct: "endowment_effect",
    difficulty: "medium",
    options: [
      {
        label: "Definitely keep it (it's mine now)",
        value: 1,
        text: "Definitely keep it (it's mine now)",
        score: 1,
      },
      {
        label: "Probably keep it",
        value: 2,
        text: "Probably keep it",
        score: 2,
      },
      {
        label: "Probably sell it",
        value: 3,
        text: "Probably sell it",
        score: 3,
      },
      {
        label: "Definitely sell it (treat it like cash)",
        value: 4,
        text: "Definitely sell it (treat it like cash)",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: "Keep It", max: "Sell It" },
    },
    gamifiedText:
      "You got a game skin as a gift. You wouldn't buy it yourself. Do you keep or trade it?",
  },
  {
    id: "PT-13",
    group: "PROSPECT",
    type: "prospect",
    question:
      "Imagine two scenarios: In Scenario A, the market dropped 30% last month. In Scenario B, the market gained 30% last month. How would your answers to this questionnaire differ between these scenarios?",
    text: "Imagine two scenarios: In Scenario A, the market dropped 30% last month. In Scenario B, the market gained 30% last month. How would your answers to this questionnaire differ between these scenarios?",
    maxScore: 4,
    construct: "recency_awareness",
    difficulty: "medium",
    options: [
      {
        label: "I would be much more conservative after a drop (Scenario A)",
        value: 1,
        text: "I would be much more conservative after a drop (Scenario A)",
        score: 1,
      },
      {
        label: "I would be somewhat more conservative after a drop",
        value: 2,
        text: "I would be somewhat more conservative after a drop",
        score: 2,
      },
      {
        label: "My answers wouldn't change much either way",
        value: 3,
        text: "My answers wouldn't change much either way",
        score: 3,
      },
      {
        label:
          "I might actually be more aggressive after a drop (buying opportunity)",
        value: 4,
        text: "I might actually be more aggressive after a drop (buying opportunity)",
        score: 4,
      },
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: {
        min: "More conservative after drop",
        max: "More aggressive after drop",
      },
    },
    scoring_note:
      "Higher scores indicate lower recency bias and more stable risk preferences",
    ui_note: "Display with special framing - this is a self-awareness question",
  },
];

/** Resolve full question (text, options, storylineData) by id. Selector returns minimal Question; this enriches for display. */
function getFullQuestionById(id: string): Question | undefined {
  const fromMpt = MPT_QUESTIONS.find((q) => q.id === id);
  if (fromMpt) return fromMpt;
  const fromProspect = PROSPECT_QUESTIONS.find((q) => q.id === id);
  if (fromProspect) return fromProspect;
  const fromReverse = REVERSE_CODED_QUESTIONS.find((q) => q.id === id);
  if (fromReverse) return fromReverse as unknown as Question;
  const fromStory = GAMIFIED_STORYLINE.find((s) => s.id === id);
  if (fromStory) {
    return {
      id: fromStory.id,
      group: "PROSPECT",
      type: "storyline",
      question: fromStory.scenario,
      text: fromStory.scenario,
      maxScore: 4,
      construct: "gamified_scenario",
      options: fromStory.options.map((o, i) => ({
        label: o.text,
        value: i + 1,
        text: o.text,
        score: o.score,
      })),
      storylineData: fromStory,
    };
  }
  return undefined;
}

/**
 * VALIDATION FUNCTION - Run this in console to verify question data
 * Usage: Copy to browser console and run validateQuestions()
 */
const validateQuestions = () => {
  const allQuestions = [...MPT_QUESTIONS, ...PROSPECT_QUESTIONS];
  const results = {
    totalCount: allQuestions.length,
    mptCount: MPT_QUESTIONS.length,
    prospectCount: PROSPECT_QUESTIONS.length,
    mptMaxSum: MPT_QUESTIONS.reduce((sum, q) => sum + q.maxScore, 0),
    prospectMaxSum: PROSPECT_QUESTIONS.reduce((sum, q) => sum + q.maxScore, 0),
    duplicateIds: [] as string[],
    missingMetadata: [] as string[],
    invalidScales: [] as string[],
    groupErrors: [] as string[],
  };

  // Check for duplicate IDs
  const ids = allQuestions.map((q) => q.id);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
  results.duplicateIds = [...new Set(duplicates)];

  // Check metadata and scales
  allQuestions.forEach((q) => {
    // Check required metadata fields
    if (!q.group || !q.maxScore || !q.construct) {
      results.missingMetadata.push(q.id);
    }

    // Check group matches expected values
    if (q.id.startsWith("M") && q.group !== "MPT") {
      results.groupErrors.push(
        `${q.id}: Expected group='MPT', got '${q.group}'`,
      );
    }
    if (q.id.startsWith("PT") && q.group !== "PROSPECT") {
      results.groupErrors.push(
        `${q.id}: Expected group='PROSPECT', got '${q.group}'`,
      );
    }

    // Check option values are sequential
    if (q.options) {
      const values = q.options.map((o) => o.value).sort((a, b) => a - b);
      const expected = Array.from({ length: values.length }, (_, i) => i + 1);
      if (JSON.stringify(values) !== JSON.stringify(expected)) {
        results.invalidScales.push(
          `${q.id}: Values are ${values.join(",")}, expected ${expected.join(",")}`,
        );
      }

      // Check maxScore matches option count
      const maxValue = Math.max(...values);
      if (q.maxScore !== maxValue) {
        results.invalidScales.push(
          `${q.id}: maxScore=${q.maxScore} but max option value=${maxValue}`,
        );
      }
    }
  });

  console.log("=== QUESTION VALIDATION RESULTS ===");
  console.log(
    `Total Questions: ${results.totalCount} ${results.totalCount === 28 ? "✅" : "❌ (expected: 28)"}`,
  );
  console.log(
    `MPT Questions: ${results.mptCount} ${results.mptCount === 15 ? "✅" : "❌ (expected: 15)"}`,
  );
  console.log(
    `Prospect Questions: ${results.prospectCount} ${results.prospectCount === 13 ? "✅" : "❌ (expected: 13)"}`,
  );
  console.log(
    `MPT maxScore sum: ${results.mptMaxSum} ${results.mptMaxSum === 75 ? "✅" : "❌ (expected: 75)"}`,
  );
  console.log(
    `Prospect maxScore sum: ${results.prospectMaxSum} ${results.prospectMaxSum === 53 ? "✅" : "❌ (expected: 53)"}`,
  );
  console.log(
    `Duplicate IDs: ${results.duplicateIds.length === 0 ? "✅ None" : "❌ " + results.duplicateIds.join(", ")}`,
  );
  console.log(
    `Missing Metadata: ${results.missingMetadata.length === 0 ? "✅ None" : "❌ " + results.missingMetadata.join(", ")}`,
  );
  console.log(
    `Group Errors: ${results.groupErrors.length === 0 ? "✅ None" : "❌ " + results.groupErrors.join("; ")}`,
  );
  console.log(
    `Invalid Scales: ${results.invalidScales.length === 0 ? "✅ None" : "❌ " + results.invalidScales.join("; ")}`,
  );

  const allPassed =
    results.totalCount === 28 &&
    results.mptCount === 15 &&
    results.prospectCount === 13 &&
    results.mptMaxSum === 75 &&
    results.prospectMaxSum === 53 &&
    results.duplicateIds.length === 0 &&
    results.missingMetadata.length === 0 &&
    results.groupErrors.length === 0 &&
    results.invalidScales.length === 0;

  console.log(
    `\n${allPassed ? "✅ ALL CHECKS PASSED - Ready for Agent 2" : "❌ VALIDATION FAILED - Fix errors before proceeding"}`,
  );
  return results;
};

// Export validation function for testing
if (typeof window !== "undefined") {
  (window as any).validateQuestions = validateQuestions;
}
import { computeRiskResult } from "./riskUtils";
import { createQuestionSelector, QuestionSelector } from "./question-selector";
import { computeScoring } from "./scoring-engine";
import { checkConstructCoverage } from "./adaptive-branching";
import { CONSTRUCT_MAPPINGS } from "./metadata";
import {
  createBranchingPathSelectedEvent,
  logAssessmentEvent,
} from "./monitoring";
import {
  ScreeningContradiction,
  checkScreeningContradiction,
} from "./ScreeningContradiction";
import { REVERSE_CODED_QUESTIONS } from "./reverse-coded";
import { CONSISTENCY_PAIRS } from "./question-pools";
import { ResultsPage } from "./ResultsPage";

export const RiskProfiler = ({
  onNext,
  onPrev,
  onProfileUpdate,
  currentProfile,
  currentAnalysis,
}: RiskProfilerProps) => {
  const [step, setStep] = useState<"screening" | "questions" | "result">(
    currentAnalysis ? "result" : "screening",
  );
  const [screeningData, setScreeningData] = useState<ScreeningData>({
    ageGroup: null,
    experience: null,
    knowledge: null,
  });
  const [questionSelector, setQuestionSelector] =
    useState<QuestionSelector | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [answerTimings, setAnswerTimings] = useState<Record<string, number>>(
    {},
  );
  const [selectedOptionValues, setSelectedOptionValues] = useState<
    Record<string, string>
  >({});
  const [result, setResult] = useState<any>(currentAnalysis || null);
  const [storylineProgress, setStorylineProgress] = useState(0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [currentFeedback, setCurrentFeedback] = useState("");
  const [showContradictionPrompt, setShowContradictionPrompt] = useState(false);

  // Shuffle options per question so answer order is not predictable (adaptive path)
  const shuffledOptionsForQuestion = useMemo(() => {
    if (!currentQuestion?.id) return [];
    const q = getFullQuestionById(currentQuestion.id);
    const opts = q?.options ?? [];
    return [...opts].sort(() => Math.random() - 0.5);
  }, [currentQuestion?.id]);

  // Calculate experience points from screening data
  const getExperiencePoints = (data: ScreeningData): number => {
    const experienceMap = { "0-2": 0, "3-5": 1, "6-10": 2, "10+": 3 };
    const knowledgeMap = { beginner: 0, intermediate: 1, advanced: 2 };

    return (
      (experienceMap[data.experience!] || 0) +
      (knowledgeMap[data.knowledge!] || 0)
    );
  };

  // Determine question mix based on screening data
  const determineQuestionMix = (data: ScreeningData) => {
    const isUnder19 = data.ageGroup === "under-19";
    const experiencePoints = getExperiencePoints(data);

    let mptRatio: number;
    let prospectRatio: number;

    if (isUnder19) {
      mptRatio = 0.2; // 20% MPT
      prospectRatio = 0.8; // 80% Prospect Theory
    } else if (experiencePoints >= 3) {
      mptRatio = 0.8; // 80% MPT
      prospectRatio = 0.2; // 20% Prospect Theory
    } else {
      mptRatio = 0.3; // 30% MPT
      prospectRatio = 0.7; // 70% Prospect Theory
    }

    return { mptRatio, prospectRatio, isUnder19 };
  };

  // Select questions based on mix and age
  const selectQuestions = (
    mptRatio: number,
    prospectRatio: number,
    isUnder19: boolean,
  ): Question[] => {
    if (isUnder19) {
      // For under-19 users, use the gamified storyline
      // Map storyline to question objects with proper metadata (group, maxScore)
      // Gamified path construct balance: 3 MPT (60%) + 2 Prospect (40%)
      // MPT: story-1 (time_horizon), story-2 (market_reaction), story-5 (volatility_tolerance)
      // Prospect: story-3 (risk_seeking), story-4 (overconfidence)
      const STORY_MAPPINGS: Record<
        string,
        { group: "MPT" | "PROSPECT"; construct: string }
      > = {
        "story-1": { group: "MPT", construct: "time_horizon" }, // Savings vs Growth (Time/Risk)
        "story-2": { group: "MPT", construct: "market_reaction" }, // Market drop behavior
        "story-3": { group: "PROSPECT", construct: "risk_seeking" }, // Business/Crypto (Opportunity/Risk)
        "story-4": { group: "PROSPECT", construct: "overconfidence" }, // All-in bet (Concentration/Bias)
        "story-5": { group: "MPT", construct: "volatility_tolerance" }, // General advice (Risk Tolerance)
      };

      return GAMIFIED_STORYLINE.map((storyNode) => {
        const mapping = STORY_MAPPINGS[storyNode.id] || {
          group: "PROSPECT",
          construct: "gamified_scenario",
        };
        return {
          id: storyNode.id,
          group: mapping.group,
          type: "storyline" as const,
          question: storyNode.scenario,
          text: storyNode.scenario,
          maxScore: 4,
          construct: mapping.construct,
          options: storyNode.options.map((option, optIndex) => ({
            label: option.text,
            value: optIndex + 1,
            text: option.text,
            score: option.score,
          })),
          storylineData: storyNode,
        };
      });
    } else {
      // For older users, use traditional questions
      const totalQuestions = 12;
      const mptCount = Math.round(totalQuestions * mptRatio);
      const prospectCount = totalQuestions - mptCount;

      // Filter by group to ensure metadata-driven selection
      const mptPool = MPT_QUESTIONS.filter((q) => q.group === "MPT");
      const prospectPool = PROSPECT_QUESTIONS.filter(
        (q) => q.group === "PROSPECT",
      );

      // Shuffle and select MPT questions
      const shuffledMPT = [...mptPool].sort(() => Math.random() - 0.5);
      const selectedMPT = shuffledMPT.slice(0, mptCount);

      // Shuffle and select Prospect Theory questions
      const shuffledProspect = [...prospectPool].sort(
        () => Math.random() - 0.5,
      );
      const selectedProspect = shuffledProspect.slice(0, prospectCount);

      // Combine and shuffle all questions
      const allQuestions = [...selectedMPT, ...selectedProspect].sort(
        () => Math.random() - 0.5,
      );

      // Shuffle options within each question, preserve metadata
      return allQuestions.map((question) => ({
        ...question,
        options: question.options
          ? [...question.options].sort(() => Math.random() - 0.5)
          : question.options,
      }));
    }
  };

  // Handle screening completion
  const handleScreeningComplete = () => {
    // Calculate experience points from screening data
    let experiencePoints = 0;
    if (screeningData.experience === "3-5") experiencePoints = 1;
    else if (screeningData.experience === "6-10") experiencePoints = 2;
    else if (screeningData.experience === "10+") experiencePoints = 3;

    // Initialize QuestionSelector
    const selector = createQuestionSelector();
    selector.initialize({
      ageGroup: screeningData.ageGroup || "above-19",
      experiencePoints,
    });

    setQuestionSelector(selector);

    // Get first question
    const firstQuestion = selector.getNextQuestion();
    setCurrentQuestion(firstQuestion);

    setStep("questions");
  };

  // Handle answer submission
  const handleAnswerSubmit = (value: number) => {
    if (!questionSelector || !currentQuestion) return;

    const startTime = Date.now();
    // Record the answer
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: value }));

    const fullQ = getFullQuestionById(currentQuestion.id);
    if (screeningData.ageGroup === "under-19" && fullQ?.storylineData) {
      const selectedOption = fullQ.storylineData!.options[value - 1];
      setCurrentFeedback(selectedOption.consequence);
      setShowFeedback(true);

      // Submit answer and get next question after feedback
      setTimeout(() => {
        const answerTime = (Date.now() - startTime) / 1000; // Convert to seconds
        questionSelector.submitAnswer(currentQuestion.id, value, answerTime);
        setAnswerTimings((prev) => ({
          ...prev,
          [currentQuestion.id]: answerTime,
        }));

        setShowFeedback(false);
        const nextQuestion = questionSelector.getNextQuestion();
        if (nextQuestion) {
          setCurrentQuestion(nextQuestion);
          const selectedQuestions = questionSelector.getSelectedQuestions();
          setStorylineProgress(
            (selectedQuestions.length /
              (screeningData.ageGroup === "under-19" ? 5 : 12)) *
              100,
          );
        } else {
          calculateRiskProfile();
        }
      }, 3000);
    } else {
      // Submit answer immediately for non-storyline questions
      const answerTime = (Date.now() - startTime) / 1000;
      questionSelector.submitAnswer(currentQuestion.id, value, answerTime);
      setAnswerTimings((prev) => ({
        ...prev,
        [currentQuestion.id]: answerTime,
      }));

      const nextQuestion = questionSelector.getNextQuestion();
      if (nextQuestion) {
        setCurrentQuestion(nextQuestion);
      } else {
        calculateRiskProfile();
      }
    }
  };

  // Calculate risk profile (uses new scoring engine with branching metadata)
  const calculateRiskProfile = () => {
    if (!questionSelector) return;

    const selectedQuestions = questionSelector.getSelectedQuestions();
    const branchingPath = questionSelector.getBranchingPath();
    const branchingState = questionSelector.getState();

    // Calculate construct coverage
    const constructCoverage = checkConstructCoverage(
      selectedQuestions.map((q) => q.id),
      CONSTRUCT_MAPPINGS,
    );

    // Prepare branching metadata
    const branchingMetadata = branchingState
      ? {
          path: branchingPath as
            | "conservative"
            | "aggressive"
            | "moderate"
            | "gamified",
          phase1Score: branchingState.phase1_score,
          constructCoverage: {
            covered: Array.from(constructCoverage.covered),
            missing: constructCoverage.missing,
            percent: constructCoverage.coveragePercent,
          },
        }
      : undefined;

    // Calculate total completion time
    const totalTimeSeconds = Object.values(answerTimings).reduce(
      (sum, time) => sum + time,
      0,
    );

    // Log branching decision if applicable
    if (branchingState && branchingState.phase1_score !== null) {
      const branchingEvent = createBranchingPathSelectedEvent(
        "session-current", // Would be generated in real implementation
        branchingState.phase1_score,
        branchingPath,
        selectedQuestions.map((q) => q.id),
      );
      logAssessmentEvent(branchingEvent);
    }

    const reverseCodedPairs = Object.entries(CONSISTENCY_PAIRS).flatMap(
      ([originalId, reverseId]) => {
        const originalAnswer = answers[originalId];
        const reverseAnswer = answers[reverseId];
        const originalQuestion = getFullQuestionById(originalId);
        const reverseQuestion = getFullQuestionById(reverseId);
        if (
          originalAnswer == null ||
          reverseAnswer == null ||
          !originalQuestion ||
          !reverseQuestion
        ) {
          return [];
        }
        return [
          {
            originalAnswer,
            originalMax: originalQuestion.maxScore,
            reverseAnswer,
            reverseMax: reverseQuestion.maxScore,
          },
        ];
      },
    );

    // Use new scoring engine (pass anchor answers so safeguards can cap/warn)
    const scoringResult = computeScoring({
      selectedQuestions: selectedQuestions.map((q) => ({
        id: q.id,
        group: q.group as "MPT" | "PROSPECT" | "SCREENING",
        maxScore: q.maxScore,
        excludeFromScoring: false,
      })),
      answersMap: answers,
      completionTimeSeconds: totalTimeSeconds,
      timeHorizonAnswer: answers["M2"],
      lossAversionAnswer: answers["PT-2"],
      reverseCodedPairs,
      branchingMetadata,
    });

    setResult(scoringResult);
    onProfileUpdate(scoringResult.risk_category, scoringResult);
    setStep("result");
  };

  // Get profile information
  const getProfileInfo = (profile: RiskProfile) => {
    switch (profile) {
      case "very-conservative":
        return {
          icon: Shield,
          title: "Very Conservative Investor",
          description:
            "You prioritize capital preservation above all else. You prefer the safest investments with minimal risk.",
          characteristics: [
            "Maximum capital preservation",
            "Very low risk tolerance",
            "Income-focused",
            "Short-term thinking",
          ],
        };
      case "conservative":
        return {
          icon: Shield,
          title: "Conservative Investor",
          description:
            "You prefer stability and lower risk. Focus on stable, dividend-oriented stocks and capital preservation.",
          characteristics: [
            "Capital preservation focused",
            "Prefers steady returns",
            "Lower volatility tolerance",
            "Income-oriented investments",
          ],
        };
      case "moderate":
        return {
          icon: TrendingUp,
          title: "Moderate Investor",
          description:
            "You seek balanced growth with moderate risk. A diversified mix of value and growth stocks suits your profile.",
          characteristics: [
            "Balanced risk-return approach",
            "Diversified portfolio",
            "Medium-term growth focus",
            "Some volatility tolerance",
          ],
        };
      case "aggressive":
        return {
          icon: AlertTriangle,
          title: "Aggressive Investor",
          description:
            "You pursue high growth potential and can handle significant volatility. Growth stocks and emerging markets fit your style.",
          characteristics: [
            "High growth potential",
            "High risk tolerance",
            "Long-term focused",
            "Comfortable with volatility",
          ],
        };
      case "very-aggressive":
        return {
          icon: Zap,
          title: "Very Aggressive Investor",
          description:
            "You seek maximum growth potential and can handle extreme volatility. You're comfortable with high-risk, high-reward investments.",
          characteristics: [
            "Maximum growth potential",
            "Very high risk tolerance",
            "Long-term focused",
            "Thrives on volatility",
          ],
        };
      default:
        return null;
    }
  };

  // Render screening questions
  if (step === "screening") {
    if (showContradictionPrompt) {
      return (
        <div className="max-w-2xl mx-auto py-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <ScreeningContradiction
            onKeepBeginner={() => {
              setShowContradictionPrompt(false);
              handleScreeningComplete();
            }}
            onReviseKnowledge={() => setShowContradictionPrompt(false)}
          />
        </div>
      );
    }

    const isComplete =
      screeningData.ageGroup &&
      screeningData.experience &&
      screeningData.knowledge;

    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <StepCardHeader
            title="Investment Profile Screening"
            subtitle="Let's start with a few quick questions to personalize your experience"
          />

          <CardContent className="space-y-4">
            {/* Age Group */}
            <div className="space-y-2">
              <h3 className="font-semibold text-base">
                1. What is your age group?
              </h3>
              <RadioGroup
                value={screeningData.ageGroup || ""}
                onValueChange={(value) =>
                  setScreeningData((prev) => ({
                    ...prev,
                    ageGroup: value as "under-19" | "above-19",
                  }))
                }
              >
                <div className="flex items-center space-x-2 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                  <RadioGroupItem value="under-19" id="age-under-19" />
                  <Label
                    htmlFor="age-under-19"
                    className="flex-1 cursor-pointer text-sm"
                  >
                    Under 19 years old
                  </Label>
                </div>
                <div className="flex items-center space-x-2 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                  <RadioGroupItem value="above-19" id="age-above-19" />
                  <Label
                    htmlFor="age-above-19"
                    className="flex-1 cursor-pointer text-sm"
                  >
                    19 years old or above
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Investment Experience */}
            <div className="space-y-2">
              <h3 className="font-semibold text-base">
                2. How many years of investing experience do you have?
              </h3>
              <RadioGroup
                value={screeningData.experience || ""}
                onValueChange={(value) =>
                  setScreeningData((prev) => ({
                    ...prev,
                    experience: value as "0-2" | "3-5" | "6-10" | "10+",
                  }))
                }
              >
                {[
                  { value: "0-2", text: "0-2 years" },
                  { value: "3-5", text: "3-5 years" },
                  { value: "6-10", text: "6-10 years" },
                  { value: "10+", text: "10+ years" },
                ].map((option) => (
                  <div
                    key={option.value}
                    className="flex items-center space-x-2 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <RadioGroupItem
                      value={option.value}
                      id={`exp-${option.value}`}
                    />
                    <Label
                      htmlFor={`exp-${option.value}`}
                      className="flex-1 cursor-pointer text-sm"
                    >
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Investment Knowledge */}
            <div className="space-y-2">
              <h3 className="font-semibold text-base">
                3. How would you rate your investment knowledge?
              </h3>
              <RadioGroup
                value={screeningData.knowledge || ""}
                onValueChange={(value) =>
                  setScreeningData((prev) => ({
                    ...prev,
                    knowledge: value as
                      | "beginner"
                      | "intermediate"
                      | "advanced",
                  }))
                }
              >
                {[
                  {
                    value: "beginner",
                    text: "Beginner - I'm new to investing",
                  },
                  {
                    value: "intermediate",
                    text: "Intermediate - I have some experience",
                  },
                  {
                    value: "advanced",
                    text: "Advanced - I'm experienced with various investments",
                  },
                ].map((option) => (
                  <div
                    key={option.value}
                    className="flex items-center space-x-2 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <RadioGroupItem
                      value={option.value}
                      id={`knowledge-${option.value}`}
                    />
                    <Label
                      htmlFor={`knowledge-${option.value}`}
                      className="flex-1 cursor-pointer text-sm"
                    >
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            <div className="flex gap-2 justify-center pt-3 border-t">
              <Button variant="outline" onClick={onPrev}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Previous
              </Button>
              <Button
                onClick={() => {
                  if (!isComplete) return;
                  if (
                    checkScreeningContradiction(
                      screeningData.experience,
                      screeningData.knowledge,
                    )
                  ) {
                    setShowContradictionPrompt(true);
                  } else {
                    handleScreeningComplete();
                  }
                }}
                disabled={!isComplete}
                className="bg-primary hover:bg-primary/90 disabled:opacity-50"
              >
                Start Risk Assessment
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render questions
  if (step === "questions") {
    if (!currentQuestion) return null;

    const fullQuestion =
      getFullQuestionById(currentQuestion.id) ?? currentQuestion;
    const selectedQuestions = questionSelector?.getSelectedQuestions() || [];
    const totalQuestions = screeningData.ageGroup === "under-19" ? 5 : 12;
    // Cap index so we never show "14 of 12" (adaptive path can ask more than 12)
    const rawIndex = selectedQuestions.length + 1;
    const currentIndex = Math.min(rawIndex, totalQuestions);
    const progress =
      totalQuestions > 0
        ? (Math.min(selectedQuestions.length + 1, totalQuestions) /
            totalQuestions) *
          100
        : 0;
    const isUnder19 = screeningData.ageGroup === "under-19";

    // Show feedback overlay for storyline
    if (showFeedback && isUnder19) {
      return (
        <div className="max-w-2xl mx-auto">
          <Card className="bg-muted border border-border">
            <CardContent className="text-center py-6">
              <div className="text-4xl mb-2">✨</div>
              <h3 className="text-lg font-bold mb-2 text-foreground">
                Your Choice!
              </h3>
              <p className="text-base text-foreground mb-3">
                {currentFeedback}
              </p>
              <div className="animate-pulse">
                <p className="text-sm text-muted-foreground">
                  Continuing your adventure...
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl mb-1">
              {isUnder19 ? "Your Adventure Continues!" : "Risk Assessment"}
            </CardTitle>
            <p className="text-muted-foreground text-sm mb-2">
              {isUnder19
                ? `Chapter ${currentIndex} of 5`
                : `Question ${currentIndex} of 12`}
            </p>
            <Progress value={progress} className="w-full h-1" />
          </CardHeader>

          <CardContent className="space-y-4">
            {isUnder19 && fullQuestion.storylineData ? (
              // Gamified storyline interface
              <div className="space-y-4">
                <div className="text-center mb-3">
                  <div className="text-3xl mb-2">
                    {fullQuestion.storylineData.visual}
                  </div>
                  <h3 className="text-base font-semibold text-foreground leading-relaxed">
                    {fullQuestion.storylineData.scenario}
                  </h3>
                </div>

                <div className="space-y-2">
                  {fullQuestion.storylineData.options.map((option, index) => (
                    <div
                      key={index}
                      onClick={() => handleAnswerSubmit(option.score)}
                      className="p-3 rounded-lg border-2 border-border hover:border-primary hover:bg-muted transition-all cursor-pointer group"
                    >
                      <div className="flex items-center space-x-2">
                        <div className="text-xl">{option.icon}</div>
                        <div className="flex-1">
                          <div className="font-medium text-sm text-foreground group-hover:text-primary">
                            {option.text}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {option.consequence}
                          </div>
                        </div>
                        <div className="text-muted-foreground group-hover:text-primary">
                          <ArrowRight className="h-4 w-4" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {fullQuestion.storylineData.feedback && (
                  <div className="mt-3 p-3 bg-muted rounded-lg border border-border">
                    <p className="text-sm text-foreground text-center">
                      💡 {fullQuestion.storylineData.feedback}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              // Traditional multiple choice interface (full question text and options from lookup)
              <div className="space-y-2">
                <h3 className="font-semibold text-base">
                  {fullQuestion.question ?? currentQuestion.id}
                </h3>

                <RadioGroup
                  value={selectedOptionValues[currentQuestion.id] || ""}
                  onValueChange={(value) => {
                    const option = fullQuestion.options?.find(
                      (o) => String(o.value) === String(value),
                    );
                    if (option) {
                      setSelectedOptionValues((prev) => ({
                        ...prev,
                        [currentQuestion.id]: String(option.value),
                      }));
                      setAnswers((prev) => ({
                        ...prev,
                        [currentQuestion.id]: option.score,
                      }));
                    }
                  }}
                >
                  {shuffledOptionsForQuestion.map((option) => (
                    <div
                      key={option.value}
                      className="flex items-center space-x-2 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <RadioGroupItem
                        value={String(option.value)}
                        id={`q${currentQuestion.id}-${option.value}`}
                      />
                      <Label
                        htmlFor={`q${currentQuestion.id}-${option.value}`}
                        className="flex-1 cursor-pointer text-sm"
                      >
                        {option.text}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>
            )}

            {!isUnder19 && (
              <div className="flex gap-2 justify-center pt-3 border-t">
                <Button
                  onClick={() =>
                    handleAnswerSubmit(answers[currentQuestion.id] || 1)
                  }
                  disabled={!answers[currentQuestion.id]}
                  className="bg-primary hover:bg-primary/90 disabled:opacity-50"
                >
                  {questionSelector?.isComplete()
                    ? "Calculate Profile"
                    : "Next Question"}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render result: use ResultsPage (confidence band, safeguards, 2D map, flags)
  if (step === "result" && result) {
    const isGamifiedPath = result.branching_metadata?.path === "gamified";
    return (
      <div className="max-w-2xl mx-auto">
        <ResultsPage
          scoringResult={{
            normalized_score: result.normalized_score,
            normalized_mpt: result.normalized_mpt,
            normalized_prospect: result.normalized_prospect,
            risk_category: result.risk_category,
            confidence_band: result.confidence_band,
            visualization_data: result.visualization_data,
            safeguards: result.safeguards,
          }}
          isGamifiedPath={isGamifiedPath}
          onReviewAnswers={() => setStep("questions")}
          onContinue={onNext}
        />
      </div>
    );
  }

  return null;
};
