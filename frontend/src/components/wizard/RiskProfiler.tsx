import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, ArrowLeft, Shield, TrendingUp, AlertTriangle, Zap, Target, Brain } from 'lucide-react';
import type { RiskProfile } from '../PortfolioWizard';

interface RiskProfilerProps {
  onNext: () => void;
  onPrev: () => void;
  onProfileUpdate: (profile: RiskProfile) => void;
  currentProfile: RiskProfile;
}

// Screening Questions Interface
interface ScreeningData {
  ageGroup: 'under-19' | 'above-19' | null;
  experience: '0-2' | '3-5' | '6-10' | '10+' | null;
  knowledge: 'beginner' | 'intermediate' | 'advanced' | null;
}

// Question Interface
interface Question {
  id: string;
  type: 'mpt' | 'prospect' | 'storyline';
  question: string;
  options?: Array<{ value: string; text: string; score: number }>;
  sliderConfig?: {
    min: number;
    max: number;
    step: number;
    labels: { min: string; max: string };
  };
  gamifiedText?: string;
  storylineData?: StorylineNode;
}

// Risk Profile Result Interface
interface RiskResult {
  raw_score: number;
  normalized_score: number;
  risk_category: RiskProfile;
  color_code: string;
}

// Progressive Storyline for Gamified Experience
interface StorylineNode {
  id: string;
  scenario: string;
  visual: string;
  avatarMood: 'excited' | 'worried' | 'confident' | 'surprised' | 'happy';
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
    id: 'story-1',
    scenario: "🎮 You just won $1,000 in a gaming tournament! Your friends are celebrating, but now you need to decide what to do with your prize money.",
    visual: "🏆",
    avatarMood: 'excited',
    options: [
      {
        text: "💰 Cash out safely",
        icon: "🛡️",
        consequence: "Guaranteed $1,000 in your pocket",
        score: 1,
        nextScenario: "Your money is safe, but you wonder if you missed out on bigger opportunities..."
      },
      {
        text: "🎧 Buy streaming gear",
        icon: "📈",
        consequence: "Grow your audience → potential future income",
        score: 2,
        nextScenario: "Your new gear helps you gain more followers and sponsorships!"
      },
      {
        text: "📱 Invest in gaming stocks",
        icon: "📊",
        consequence: "Market-dependent returns",
        score: 3,
        nextScenario: "The gaming industry is booming, but stock prices can be unpredictable..."
      },
      {
        text: "🚀 Fund indie game studio",
        icon: "🎲",
        consequence: "High risk, huge potential",
        score: 4,
        nextScenario: "You're taking a big chance, but if it works, you could be part of the next big game!"
      }
    ],
    feedback: "Your gaming coach says: 'Every choice shapes your future!'"
  },
  {
    id: 'story-2',
    scenario: "📈 Your investment choice is working! But now the market is getting wild. Your $1,000 has grown to $1,500, but there is news of a big market drop coming.",
    visual: "📉",
    avatarMood: 'worried',
    options: [
      {
        text: "🏃‍♂️ Sell everything now",
        icon: "💨",
        consequence: "Lock in your $500 profit",
        score: 1,
        nextScenario: "You're safe with your profit, but what if the market recovers?"
      },
      {
        text: "🔄 Sell half, keep half",
        icon: "⚖️",
        consequence: "Balance safety and opportunity",
        score: 2,
        nextScenario: "Smart move! You're protected but still in the game."
      },
      {
        text: "🤔 Wait and see",
        icon: "👀",
        consequence: "Ride out the storm",
        score: 3,
        nextScenario: "You decide to stay calm and not panic sell."
      },
      {
        text: "💎 Buy more on the dip",
        icon: "📈",
        consequence: "Double down on opportunity",
        score: 4,
        nextScenario: "You see this as a chance to buy more at lower prices!"
      }
    ],
    feedback: "Your mentor says: 'Markets go up and down, but your strategy matters most!'"
  },
  {
    id: 'story-3',
    scenario: "🎯 Time for a big decision! You have $2,000 saved up. Your dream is to start your own business, but you also want to travel the world.",
    visual: "🌍",
    avatarMood: 'confident',
    options: [
      {
        text: "🏦 Put it all in savings",
        icon: "🔒",
        consequence: "Safe and secure, but slow growth",
        score: 1,
        nextScenario: "Your money is protected, but it is not growing much."
      },
      {
        text: "✈️ Use it for travel now",
        icon: "🎒",
        consequence: "Amazing experiences, but no investment",
        score: 2,
        nextScenario: "You have incredible memories, but your money is gone."
      },
      {
        text: "💼 Start a small business",
        icon: "🚀",
        consequence: "High risk, but you're your own boss",
        score: 3,
        nextScenario: "You're taking control of your future!"
      },
      {
        text: "🎲 Invest in crypto/startups",
        icon: "⚡",
        consequence: "Maximum risk, maximum potential",
        score: 4,
        nextScenario: "You're going all-in on the future!"
      }
    ],
    feedback: "Your life coach says: 'Balance today's dreams with tomorrow's security!'"
  },
  {
    id: 'story-4',
    scenario: "🎉 Surprise! Your choices paid off! You now have $5,000. But here is the twist - you discover a once-in-a-lifetime opportunity that requires all your money.",
    visual: "💎",
    avatarMood: 'surprised',
    options: [
      {
        text: "❌ Too risky, keep my money",
        icon: "🛡️",
        consequence: "Stay safe with what you have",
        score: 1,
        nextScenario: "You play it safe, but wonder about the opportunity you missed."
      },
      {
        text: "🤝 Invest 25% of my money",
        icon: "⚖️",
        consequence: "Moderate risk, moderate potential",
        score: 2,
        nextScenario: "You're testing the waters without going all-in."
      },
      {
        text: "💪 Invest 50% of my money",
        icon: "🎯",
        consequence: "Balanced approach",
        score: 3,
        nextScenario: "You're taking a calculated risk."
      },
      {
        text: "🚀 Go all-in! Invest everything",
        icon: "🔥",
        consequence: "Maximum risk, maximum reward",
        score: 4,
        nextScenario: "You're betting everything on this opportunity!"
      }
    ],
    feedback: "Your financial advisor says: 'Big opportunities come with big decisions!'"
  },
  {
    id: 'story-5',
    scenario: "🌟 Your journey has taught you a lot! Now you are helping a friend who just got $500. What advice would you give them based on your experience?",
    visual: "🤝",
    avatarMood: 'happy',
    options: [
      {
        text: "🛡️ Save it all safely",
        icon: "🏦",
        consequence: "Conservative approach",
        score: 1,
        nextScenario: "You recommend playing it safe."
      },
      {
        text: "📚 Learn first, then invest",
        icon: "📖",
        consequence: "Education-focused approach",
        score: 2,
        nextScenario: "You suggest they learn before risking money."
      },
      {
        text: "🎯 Start small, grow gradually",
        icon: "🌱",
        consequence: "Balanced growth approach",
        score: 3,
        nextScenario: "You recommend starting small and building up."
      },
      {
        text: "⚡ Take calculated risks",
        icon: "🎲",
        consequence: "Aggressive approach",
        score: 4,
        nextScenario: "You encourage them to be bold but smart."
      }
    ],
    feedback: "Your friend says: 'Thanks for the advice! I'll think about it carefully.'"
  }
];

// MPT Question Pool (Modern Portfolio Theory - Factual, quantitative items)
const MPT_QUESTIONS: Question[] = [
  {
    id: 'mpt-1',
    type: 'mpt',
    question: "You expect a long time horizon; how would you allocate between stocks and bonds?",
    options: [
      { value: '1', text: '100% bonds', score: 1 },
      { value: '2', text: '75% bonds, 25% stocks', score: 2 },
      { value: '3', text: '50% bonds, 50% stocks', score: 3 },
      { value: '4', text: '25% bonds, 75% stocks', score: 4 },
      { value: '5', text: '100% stocks', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: '100% Bonds', max: '100% Stocks' }
    },
    gamifiedText: "Imagine you are saving for your future! How would you split your money between safe bonds and exciting stocks?"
  },
  {
    id: 'mpt-2',
    type: 'mpt',
    question: "What is your preferred investment time horizon?",
    options: [
      { value: '1', text: 'Less than 2 years', score: 1 },
      { value: '2', text: '2-5 years', score: 2 },
      { value: '3', text: '5-10 years', score: 3 },
      { value: '4', text: '10-20 years', score: 4 },
      { value: '5', text: 'More than 20 years', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: '2 years', max: '20+ years' }
    },
    gamifiedText: "How long do you want to keep your money invested? Think of it like planting a tree - how long until you want to see it grow big?"
  },
  {
    id: 'mpt-3',
    type: 'mpt',
    question: "How much volatility can you tolerate in your portfolio?",
    options: [
      { value: '1', text: 'Very low - I prefer stable returns', score: 1 },
      { value: '2', text: 'Low - some ups and downs are okay', score: 2 },
      { value: '3', text: 'Moderate - I can handle regular fluctuations', score: 3 },
      { value: '4', text: "High - I am comfortable with significant swings", score: 4 },
      { value: '5', text: 'Very high - I thrive on market excitement', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: 'Very Stable', max: 'Very Exciting' }
    },
    gamifiedText: "Think of your money like a roller coaster! How bumpy of a ride are you okay with?"
  },
  {
    id: 'mpt-4',
    type: 'mpt',
    question: "What percentage of your total savings are you planning to invest?",
    options: [
      { value: '1', text: 'Less than 10%', score: 1 },
      { value: '2', text: '10-25%', score: 2 },
      { value: '3', text: '25-50%', score: 3 },
      { value: '4', text: '50-75%', score: 4 },
      { value: '5', text: 'More than 75%', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: '10%', max: '75%+' }
    },
    gamifiedText: "Out of all your savings, how much do you want to put into investments? Like deciding how much of your allowance to save vs. spend!"
  },
  {
    id: 'mpt-5',
    type: 'mpt',
    question: "How important is it that your investments provide steady income?",
    options: [
      { value: '1', text: 'Extremely important - I need regular income', score: 1 },
      { value: '2', text: 'Very important', score: 2 },
      { value: '3', text: 'Somewhat important', score: 3 },
      { value: '4', text: 'Not very important', score: 4 },
      { value: '5', text: 'Not important - I focus on growth', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: 'Need Income', max: 'Want Growth' }
    },
    gamifiedText: "Do you want your investments to give you regular money (like an allowance) or just grow bigger over time?"
  },
  {
    id: 'mpt-6',
    type: 'mpt',
    question: "What is your primary investment goal?",
    options: [
      { value: '1', text: 'Capital preservation', score: 1 },
      { value: '2', text: 'Steady income', score: 2 },
      { value: '3', text: 'Balanced growth', score: 3 },
      { value: '4', text: 'Growth with some risk', score: 4 },
      { value: '5', text: 'Maximum growth potential', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: 'Keep Safe', max: 'Grow Fast' }
    },
    gamifiedText: "What is your main goal? Keep your money safe, get regular payments, or make it grow as much as possible?"
  },
  {
    id: 'mpt-7',
    type: 'mpt',
    question: "How do you plan to use your investment returns?",
    options: [
      { value: '1', text: 'Immediate spending needs', score: 1 },
      { value: '2', text: 'Regular living expenses', score: 2 },
      { value: '3', text: 'Supplemental income', score: 3 },
      { value: '4', text: 'Future large purchases', score: 4 },
      { value: '5', text: 'Long-term wealth building', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: 'Spend Now', max: 'Build Wealth' }
    },
    gamifiedText: "What will you do with the money you make? Spend it right away or let it grow for your future?"
  },
  {
    id: 'mpt-8',
    type: 'mpt',
    question: "What is your reaction to market downturns?",
    options: [
      { value: '1', text: 'I would sell immediately', score: 1 },
      { value: '2', text: 'I would be very concerned', score: 2 },
      { value: '3', text: 'I would be worried but hold', score: 3 },
      { value: '4', text: 'I would view it as temporary', score: 4 },
      { value: '5', text: 'I would see it as opportunity', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 5,
      step: 1,
      labels: { min: 'Sell Fast', max: 'Buy More' }
    },
    gamifiedText: "When the market goes down (like when your favorite game price drops), what would you do?"
  }
];

// Prospect Theory Question Pool (Behavioral, loss-aversion scenarios)
const PROSPECT_QUESTIONS: Question[] = [
  {
    id: 'prospect-1',
    type: 'prospect',
    question: "You can take a guaranteed 5,000 SEK or a 75% chance at 7,000 SEK; which do you choose?",
    options: [
      { value: '1', text: 'Guaranteed 5,000 SEK', score: 1 },
      { value: '2', text: '75% chance at 7,000 SEK', score: 4 }
    ],
    sliderConfig: {
      min: 1,
      max: 2,
      step: 1,
      labels: { min: 'Guaranteed 5,000 SEK', max: 'Risk 7,000 SEK' }
    },
    gamifiedText: "You can either get 5,000 SEK for sure, or take a chance to get 7,000 SEK (but you might get nothing). What do you pick?"
  },
  {
    id: 'prospect-2',
    type: 'prospect',
    question: "You have 10,000 SEK invested. Would you prefer a guaranteed loss of 2,000 SEK or a 50% chance to lose 4,000 SEK?",
    options: [
      { value: '1', text: 'Guaranteed loss of 2,000 SEK', score: 2 },
      { value: '2', text: '50% chance to lose 4,000 SEK', score: 1 }
    ],
    sliderConfig: {
      min: 1,
      max: 2,
      step: 1,
      labels: { min: 'Lose 2,000 SEK', max: 'Risk 4,000 SEK' }
    },
    gamifiedText: "You have 10,000 SEK. Would you rather lose 2,000 SEK for sure, or take a chance to lose 4,000 SEK (but you might lose nothing)?"
  },
  {
    id: 'prospect-3',
    type: 'prospect',
    question: "Your portfolio gained 30% this year. Would you:",
    options: [
      { value: '1', text: 'Sell everything to lock in gains', score: 1 },
      { value: '2', text: 'Sell some to take partial profits', score: 2 },
      { value: '3', text: 'Hold and wait', score: 3 },
      { value: '4', text: 'Invest even more', score: 4 }
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: 'Sell All', max: 'Invest More' }
    },
    gamifiedText: "Your investments just made 30% more money! What would you do? Sell everything, sell some, keep it, or invest even more?"
  },
  {
    id: 'prospect-4',
    type: 'prospect',
    question: "You are offered two investment options: Option A has a 90% chance to return 10% and 10% chance to lose 5%. Option B has a 50% chance to return 20% and 50% chance to lose 10%. Which do you choose?",
    options: [
      { value: '1', text: 'Option A (safer)', score: 1 },
      { value: '2', text: 'Option B (riskier)', score: 4 }
    ],
    sliderConfig: {
      min: 1,
      max: 2,
      step: 1,
      labels: { min: 'Safe Option A', max: 'Risky Option B' }
    },
    gamifiedText: "You have two choices: A safe option that almost always wins a little, or a risky option that might win big or lose big. Which do you pick?"
  },
  {
    id: 'prospect-5',
    type: 'prospect',
    question: "If you could invest in one sector, which would you choose?",
    options: [
      { value: '1', text: 'Utilities (stable, low growth)', score: 1 },
      { value: '2', text: 'Consumer staples (steady growth)', score: 2 },
      { value: '3', text: 'Technology (high growth, high risk)', score: 4 },
      { value: '4', text: 'Cryptocurrency (highest risk/reward)', score: 5 }
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: 'Utilities', max: 'Crypto' }
    },
    gamifiedText: "Which type of investment sounds most exciting to you? Safe utilities, steady consumer goods, exciting tech, or wild crypto?"
  },
  {
    id: 'prospect-6',
    type: 'prospect',
    question: "How would you react if your investment lost 20% in one month?",
    options: [
      { value: '1', text: 'Sell immediately to stop losses', score: 1 },
      { value: '2', text: 'Sell some to reduce exposure', score: 2 },
      { value: '3', text: 'Hold and wait for recovery', score: 3 },
      { value: '4', text: 'Buy more while it\'s cheap', score: 4 }
    ],
    sliderConfig: {
      min: 1,
      max: 4,
      step: 1,
      labels: { min: 'Sell All', max: 'Buy More' }
    },
    gamifiedText: "Your investment just lost 20%! Do you panic and sell, sell some, wait it out, or buy more while it's cheap?"
  }
];

export const RiskProfiler = ({ onNext, onPrev, onProfileUpdate, currentProfile }: RiskProfilerProps) => {
  const [step, setStep] = useState<'screening' | 'questions' | 'result'>('screening');
  const [screeningData, setScreeningData] = useState<ScreeningData>({
    ageGroup: null,
    experience: null,
    knowledge: null
  });
  const [selectedQuestions, setSelectedQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<RiskResult | null>(null);
  const [storylineProgress, setStorylineProgress] = useState(0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [currentFeedback, setCurrentFeedback] = useState('');

  // Calculate experience points from screening data
  const getExperiencePoints = (data: ScreeningData): number => {
    const experienceMap = { '0-2': 0, '3-5': 1, '6-10': 2, '10+': 3 };
    const knowledgeMap = { 'beginner': 0, 'intermediate': 1, 'advanced': 2 };
    
    return (experienceMap[data.experience!] || 0) + (knowledgeMap[data.knowledge!] || 0);
  };

  // Determine question mix based on screening data
  const determineQuestionMix = (data: ScreeningData) => {
    const isUnder19 = data.ageGroup === 'under-19';
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
  const selectQuestions = (mptRatio: number, prospectRatio: number, isUnder19: boolean): Question[] => {
    if (isUnder19) {
      // For under-19 users, use the gamified storyline
      return GAMIFIED_STORYLINE.map((storyNode, index) => ({
        id: storyNode.id,
        type: 'storyline' as const,
        question: storyNode.scenario,
        options: storyNode.options.map((option, optIndex) => ({
          value: (optIndex + 1).toString(),
          text: option.text,
          score: option.score
        })),
        storylineData: storyNode
      }));
    } else {
      // For older users, use traditional questions
      const totalQuestions = 12;
      const mptCount = Math.round(totalQuestions * mptRatio);
      const prospectCount = totalQuestions - mptCount;
      
      // Shuffle and select MPT questions
      const shuffledMPT = [...MPT_QUESTIONS].sort(() => Math.random() - 0.5);
      const selectedMPT = shuffledMPT.slice(0, mptCount);
      
      // Shuffle and select Prospect Theory questions
      const shuffledProspect = [...PROSPECT_QUESTIONS].sort(() => Math.random() - 0.5);
      const selectedProspect = shuffledProspect.slice(0, prospectCount);
      
      // Combine and shuffle all questions
      const allQuestions = [...selectedMPT, ...selectedProspect].sort(() => Math.random() - 0.5);
      
      // Shuffle options within each question
      return allQuestions.map(question => ({
        ...question,
        options: question.options ? [...question.options].sort(() => Math.random() - 0.5) : question.options
      }));
    }
  };

  // Handle screening completion
  const handleScreeningComplete = () => {
    const { mptRatio, prospectRatio, isUnder19 } = determineQuestionMix(screeningData);
    const questions = selectQuestions(mptRatio, prospectRatio, isUnder19);
    setSelectedQuestions(questions);
    setStep('questions');
  };

  // Handle answer submission
  const handleAnswerSubmit = (value: number) => {
    const currentQuestion = selectedQuestions[currentQuestionIndex];
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: value }));
    
    // Show feedback for storyline questions
    if (screeningData.ageGroup === 'under-19' && currentQuestion.storylineData) {
      const selectedOption = currentQuestion.storylineData.options[value - 1];
      setCurrentFeedback(selectedOption.consequence);
      setShowFeedback(true);
      
      // Auto-advance after showing feedback
      setTimeout(() => {
        setShowFeedback(false);
        if (currentQuestionIndex < selectedQuestions.length - 1) {
          setCurrentQuestionIndex(prev => prev + 1);
          setStorylineProgress(((currentQuestionIndex + 2) / selectedQuestions.length) * 100);
        } else {
          calculateRiskProfile();
        }
      }, 3000);
    } else {
      // For traditional questions, advance immediately
      if (currentQuestionIndex < selectedQuestions.length - 1) {
        setCurrentQuestionIndex(prev => prev + 1);
      } else {
        calculateRiskProfile();
      }
    }
  };

  // Calculate risk profile
  const calculateRiskProfile = () => {
    const rawScore = Object.values(answers).reduce((sum, score) => sum + score, 0);
    const maxPossibleScore = selectedQuestions.length * 5;
    const normalizedScore = (rawScore / maxPossibleScore) * 100;
    
    let riskCategory: RiskProfile;
    let colorCode: string;
    
    // Adjusted thresholds to make extreme categories more achievable
    if (normalizedScore <= 25) {
      riskCategory = 'very-conservative';
      colorCode = '#00008B';
    } else if (normalizedScore <= 40) {
      riskCategory = 'conservative';
      colorCode = '#ADD8E6';
    } else if (normalizedScore <= 60) {
      riskCategory = 'moderate';
      colorCode = '#008000';
    } else if (normalizedScore <= 75) {
      riskCategory = 'aggressive';
      colorCode = '#FFA500';
    } else {
      riskCategory = 'very-aggressive';
      colorCode = '#FF0000';
    }
    
    const riskResult: RiskResult = {
      raw_score: rawScore,
      normalized_score: normalizedScore,
      risk_category: riskCategory,
      color_code: colorCode
    };
    
    setResult(riskResult);
    onProfileUpdate(riskCategory);
    setStep('result');
  };

  // Get profile information
  const getProfileInfo = (profile: RiskProfile) => {
    switch (profile) {
      case 'very-conservative':
        return {
          icon: Shield,
          title: 'Very Conservative Investor',
          description: 'You prioritize capital preservation above all else. You prefer the safest investments with minimal risk.',
          characteristics: ['Maximum capital preservation', 'Very low risk tolerance', 'Income-focused', 'Short-term thinking']
        };
      case 'conservative':
        return {
          icon: Shield,
          title: 'Conservative Investor',
          description: 'You prefer stability and lower risk investments. Focus on bonds, dividend stocks, and capital preservation.',
          characteristics: ['Capital preservation focused', 'Prefers steady returns', 'Lower volatility tolerance', 'Income-oriented investments']
        };
      case 'moderate':
        return {
          icon: TrendingUp,
          title: 'Moderate Investor',
          description: 'You seek balanced growth with moderate risk. A mix of stocks and bonds suits your profile.',
          characteristics: ['Balanced risk-return approach', 'Diversified portfolio', 'Medium-term growth focus', 'Some volatility tolerance']
        };
      case 'aggressive':
        return {
          icon: AlertTriangle,
          title: 'Aggressive Investor',
          description: 'You pursue high growth potential and can handle significant volatility. Growth stocks and emerging markets fit your style.',
          characteristics: ['High growth potential', 'High risk tolerance', 'Long-term focused', 'Comfortable with volatility']
        };
      case 'very-aggressive':
        return {
          icon: Zap,
          title: 'Very Aggressive Investor',
          description: 'You seek maximum growth potential and can handle extreme volatility. You\'re comfortable with high-risk, high-reward investments.',
          characteristics: ['Maximum growth potential', 'Very high risk tolerance', 'Long-term focused', 'Thrives on volatility']
        };
      default:
        return null;
    }
  };

  // Render screening questions
  if (step === 'screening') {
    const isComplete = screeningData.ageGroup && screeningData.experience && screeningData.knowledge;
    
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-elegant">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl mb-2">Investment Profile Screening</CardTitle>
            <p className="text-muted-foreground">
              Let's start with a few quick questions to personalize your experience
            </p>
          </CardHeader>
          
          <CardContent className="space-y-8">
            {/* Age Group */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">1. What is your age group?</h3>
              <RadioGroup
                value={screeningData.ageGroup || ""}
                onValueChange={(value) => setScreeningData(prev => ({ ...prev, ageGroup: value as 'under-19' | 'above-19' }))}
              >
                <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                  <RadioGroupItem value="under-19" id="age-under-19" />
                  <Label htmlFor="age-under-19" className="flex-1 cursor-pointer">
                    Under 19 years old
                  </Label>
                </div>
                <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                  <RadioGroupItem value="above-19" id="age-above-19" />
                  <Label htmlFor="age-above-19" className="flex-1 cursor-pointer">
                    19 years old or above
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Investment Experience */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">2. How many years of investing experience do you have?</h3>
              <RadioGroup
                value={screeningData.experience || ""}
                onValueChange={(value) => setScreeningData(prev => ({ ...prev, experience: value as '0-2' | '3-5' | '6-10' | '10+' }))}
              >
                {[
                  { value: '0-2', text: '0-2 years' },
                  { value: '3-5', text: '3-5 years' },
                  { value: '6-10', text: '6-10 years' },
                  { value: '10+', text: '10+ years' }
                ].map((option) => (
                  <div key={option.value} className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                    <RadioGroupItem value={option.value} id={`exp-${option.value}`} />
                    <Label htmlFor={`exp-${option.value}`} className="flex-1 cursor-pointer">
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Investment Knowledge */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">3. How would you rate your investment knowledge?</h3>
              <RadioGroup
                value={screeningData.knowledge || ""}
                onValueChange={(value) => setScreeningData(prev => ({ ...prev, knowledge: value as 'beginner' | 'intermediate' | 'advanced' }))}
              >
                {[
                  { value: 'beginner', text: 'Beginner - I\'m new to investing' },
                  { value: 'intermediate', text: 'Intermediate - I have some experience' },
                  { value: 'advanced', text: 'Advanced - I\'m experienced with various investments' }
                ].map((option) => (
                  <div key={option.value} className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                    <RadioGroupItem value={option.value} id={`knowledge-${option.value}`} />
                    <Label htmlFor={`knowledge-${option.value}`} className="flex-1 cursor-pointer">
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            <div className="flex gap-4 justify-center pt-6 border-t">
              <Button variant="outline" onClick={onPrev}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Previous
              </Button>
              <Button 
                onClick={handleScreeningComplete} 
                disabled={!isComplete}
                className="bg-gradient-primary hover:opacity-90 disabled:opacity-50"
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
  if (step === 'questions') {
    const currentQuestion = selectedQuestions[currentQuestionIndex];
    const progress = ((currentQuestionIndex + 1) / selectedQuestions.length) * 100;
    const isUnder19 = screeningData.ageGroup === 'under-19';
    
    // Show feedback overlay for storyline
    if (showFeedback && isUnder19) {
      return (
        <div className="max-w-2xl mx-auto">
          <Card className="shadow-elegant bg-gradient-to-r from-green-50 to-blue-50 border-2 border-green-200">
            <CardContent className="text-center py-12">
              <div className="text-6xl mb-4">✨</div>
              <h3 className="text-xl font-bold mb-4 text-green-700">Your Choice!</h3>
              <p className="text-lg text-gray-700 mb-6">{currentFeedback}</p>
              <div className="animate-pulse">
                <p className="text-sm text-gray-500">Continuing your adventure...</p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }
    
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-elegant">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl mb-2">
              {isUnder19 ? 'Your Adventure Continues!' : 'Risk Assessment'}
            </CardTitle>
            <p className="text-muted-foreground mb-4">
              {isUnder19 ? `Chapter ${currentQuestionIndex + 1} of ${selectedQuestions.length}` : `Question ${currentQuestionIndex + 1} of ${selectedQuestions.length}`}
            </p>
            <Progress value={progress} className="w-full" />
          </CardHeader>
          
          <CardContent className="space-y-6">
            {isUnder19 && currentQuestion.storylineData ? (
              // Gamified storyline interface
              <div className="space-y-6">
                <div className="text-center mb-6">
                  <div className="text-4xl mb-4">{currentQuestion.storylineData.visual}</div>
                  <h3 className="text-lg font-semibold text-gray-800 leading-relaxed">
                    {currentQuestion.storylineData.scenario}
                  </h3>
                </div>
                
                <div className="space-y-3">
                  {currentQuestion.storylineData.options.map((option, index) => (
                    <div
                      key={index}
                      onClick={() => handleAnswerSubmit(option.score)}
                      className="p-4 rounded-lg border-2 border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all cursor-pointer group"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="text-2xl">{option.icon}</div>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900 group-hover:text-blue-700">
                            {option.text}
                          </div>
                          <div className="text-sm text-gray-600 mt-1">
                            {option.consequence}
                          </div>
                        </div>
                        <div className="text-gray-400 group-hover:text-blue-500">
                          <ArrowRight className="h-5 w-5" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {currentQuestion.storylineData.feedback && (
                  <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                    <p className="text-sm text-yellow-800 text-center">
                      💡 {currentQuestion.storylineData.feedback}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              // Traditional multiple choice interface
              <div className="space-y-4">
                <h3 className="font-semibold text-lg">
                  {currentQuestion.question}
                </h3>
                
                <RadioGroup
                  value={answers[currentQuestion.id]?.toString() || ""}
                  onValueChange={(value) => {
                    const option = currentQuestion.options?.find(o => o.value === value);
                    if (option) {
                      setAnswers(prev => ({ ...prev, [currentQuestion.id]: option.score }));
                    }
                  }}
                >
                  {currentQuestion.options?.map((option) => (
                    <div key={option.value} className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                      <RadioGroupItem value={option.value} id={`q${currentQuestion.id}-${option.value}`} />
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
              <div className="flex gap-4 justify-center pt-6 border-t">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentQuestionIndex(prev => Math.max(0, prev - 1))}
                  disabled={currentQuestionIndex === 0}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Previous
                </Button>
                <Button 
                  onClick={() => handleAnswerSubmit(answers[currentQuestion.id] || 1)}
                  disabled={!answers[currentQuestion.id]}
                  className="bg-gradient-primary hover:opacity-90 disabled:opacity-50"
                >
                  {currentQuestionIndex === selectedQuestions.length - 1 ? 'Calculate Profile' : 'Next Question'}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render result
  if (step === 'result' && result && currentProfile) {
    const profileInfo = getProfileInfo(currentProfile);
    if (!profileInfo) return null;

    const ProfileIcon = profileInfo.icon;

    return (
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-elegant">
          <CardHeader className="text-center">
            <div 
              className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4"
              style={{ backgroundColor: `${result.color_code}20` }}
            >
              <ProfileIcon className="h-10 w-10" style={{ color: result.color_code }} />
            </div>
            <CardTitle className="text-2xl mb-2">Your Risk Profile</CardTitle>
            <Badge 
              variant="secondary" 
              className="text-lg px-4 py-2"
              style={{ 
                backgroundColor: `${result.color_code}20`, 
                color: result.color_code,
                borderColor: `${result.color_code}40`
              }}
            >
              {profileInfo.title}
            </Badge>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <div className="text-center">
              <p className="text-muted-foreground mb-4">{profileInfo.description}</p>
              <div className="flex justify-center items-center gap-2 text-sm text-muted-foreground">
                <span>Raw Score: {result.raw_score}/{selectedQuestions.length * 5}</span>
                <span>•</span>
                <span>Normalized Score: {result.normalized_score.toFixed(1)}%</span>
              </div>
            </div>

            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="font-semibold mb-3">Key Characteristics</h4>
              <ul className="space-y-2">
                {profileInfo.characteristics.map((char, index) => (
                  <li key={index} className="flex items-center gap-2 text-sm">
                    <div 
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: result.color_code }}
                    />
                    {char}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex gap-4 justify-center">
              <Button variant="outline" onClick={() => setStep('questions')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Retake Assessment
              </Button>
              <Button onClick={onNext} className="bg-gradient-primary hover:opacity-90">
                Continue to Capital Input
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};