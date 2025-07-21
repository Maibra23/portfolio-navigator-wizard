import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, ArrowLeft, Shield, TrendingUp, AlertTriangle } from 'lucide-react';
import type { RiskProfile } from '../PortfolioWizard';

interface RiskProfilerProps {
  onNext: () => void;
  onPrev: () => void;
  onProfileUpdate: (profile: RiskProfile) => void;
  currentProfile: RiskProfile;
}

const questions = [
  {
    id: 1,
    question: "How do you typically react when your investments lose 20% of their value in a short period?",
    options: [
      { value: "1", text: "I would sell immediately to prevent further losses", score: 1 },
      { value: "2", text: "I would be very concerned and consider selling", score: 2 },
      { value: "3", text: "I would be worried but likely hold on", score: 3 },
      { value: "4", text: "I would view it as a temporary setback", score: 4 },
      { value: "5", text: "I would see it as a buying opportunity", score: 5 }
    ]
  },
  {
    id: 2,
    question: "What is your primary investment timeline?",
    options: [
      { value: "1", text: "Less than 2 years", score: 1 },
      { value: "2", text: "2-5 years", score: 2 },
      { value: "3", text: "5-10 years", score: 3 },
      { value: "4", text: "10-20 years", score: 4 },
      { value: "5", text: "More than 20 years", score: 5 }
    ]
  },
  {
    id: 3,
    question: "Which statement best describes your investment experience?",
    options: [
      { value: "1", text: "I'm new to investing", score: 1 },
      { value: "2", text: "I have some basic knowledge", score: 2 },
      { value: "3", text: "I have moderate experience", score: 3 },
      { value: "4", text: "I'm experienced with various investments", score: 4 },
      { value: "5", text: "I'm an expert investor", score: 5 }
    ]
  },
  {
    id: 4,
    question: "How important is it that your investments provide steady income?",
    options: [
      { value: "5", text: "Extremely important - I need regular income", score: 1 },
      { value: "4", text: "Very important", score: 2 },
      { value: "3", text: "Somewhat important", score: 3 },
      { value: "2", text: "Not very important", score: 4 },
      { value: "1", text: "Not important - I focus on growth", score: 5 }
    ]
  },
  {
    id: 5,
    question: "If your portfolio gained 30% in the first year, what would you do?",
    options: [
      { value: "1", text: "Sell everything to lock in gains", score: 1 },
      { value: "2", text: "Sell some to reduce risk", score: 2 },
      { value: "3", text: "Do nothing and stay the course", score: 3 },
      { value: "4", text: "Feel confident about my strategy", score: 4 },
      { value: "5", text: "Consider investing more", score: 5 }
    ]
  },
  {
    id: 6,
    question: "What percentage of your total savings are you planning to invest?",
    options: [
      { value: "1", text: "Less than 10%", score: 1 },
      { value: "2", text: "10-25%", score: 2 },
      { value: "3", text: "25-50%", score: 3 },
      { value: "4", text: "50-75%", score: 4 },
      { value: "5", text: "More than 75%", score: 5 }
    ]
  }
];

export const RiskProfiler = ({ onNext, onPrev, onProfileUpdate, currentProfile }: RiskProfilerProps) => {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [showResult, setShowResult] = useState(false);

  const handleAnswerChange = (questionId: number, value: string) => {
    const question = questions.find(q => q.id === questionId);
    const option = question?.options.find(o => o.value === value);
    if (option) {
      setAnswers(prev => ({ ...prev, [questionId]: option.score }));
    }
  };

  const calculateProfile = (): RiskProfile => {
    const totalScore = Object.values(answers).reduce((sum, score) => sum + score, 0);
    
    if (totalScore <= 14) return 'conservative';
    if (totalScore <= 22) return 'moderate';
    return 'aggressive';
  };

  const handleSubmit = () => {
    if (Object.keys(answers).length === questions.length) {
      const profile = calculateProfile();
      onProfileUpdate(profile);
      setShowResult(true);
    }
  };

  const isComplete = Object.keys(answers).length === questions.length;
  const totalScore = Object.values(answers).reduce((sum, score) => sum + score, 0);

  const getProfileInfo = (profile: RiskProfile) => {
    switch (profile) {
      case 'conservative':
        return {
          icon: Shield,
          color: 'conservative',
          title: 'Conservative Investor',
          description: 'You prefer stability and lower risk investments. Focus on bonds, dividend stocks, and capital preservation.',
          characteristics: ['Capital preservation focused', 'Prefers steady returns', 'Lower volatility tolerance', 'Income-oriented investments']
        };
      case 'moderate':
        return {
          icon: TrendingUp,
          color: 'moderate',
          title: 'Moderate Investor',
          description: 'You seek balanced growth with moderate risk. A mix of stocks and bonds suits your profile.',
          characteristics: ['Balanced risk-return approach', 'Diversified portfolio', 'Medium-term growth focus', 'Some volatility tolerance']
        };
      case 'aggressive':
        return {
          icon: AlertTriangle,
          color: 'aggressive',
          title: 'Aggressive Investor',
          description: 'You pursue high growth potential and can handle significant volatility. Growth stocks and emerging markets fit your style.',
          characteristics: ['High growth potential', 'High risk tolerance', 'Long-term focused', 'Comfortable with volatility']
        };
      default:
        return null;
    }
  };

  if (showResult && currentProfile) {
    const profileInfo = getProfileInfo(currentProfile);
    if (!profileInfo) return null;

    const ProfileIcon = profileInfo.icon;

    return (
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-elegant">
          <CardHeader className="text-center">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 bg-${profileInfo.color}/10`}>
              <ProfileIcon className={`h-10 w-10 text-${profileInfo.color}`} />
            </div>
            <CardTitle className="text-2xl mb-2">Your Risk Profile</CardTitle>
            <Badge variant="secondary" className={`bg-${profileInfo.color}/10 text-${profileInfo.color} border-${profileInfo.color}/20 text-lg px-4 py-2`}>
              {profileInfo.title}
            </Badge>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <div className="text-center">
              <p className="text-muted-foreground mb-4">{profileInfo.description}</p>
              <div className="flex justify-center items-center gap-2 text-sm text-muted-foreground">
                <span>Your Score: {totalScore}/30</span>
                <span>•</span>
                <span>
                  {currentProfile === 'conservative' && '6-14 points'}
                  {currentProfile === 'moderate' && '15-22 points'}
                  {currentProfile === 'aggressive' && '23-30 points'}
                </span>
              </div>
            </div>

            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="font-semibold mb-3">Key Characteristics</h4>
              <ul className="space-y-2">
                {profileInfo.characteristics.map((char, index) => (
                  <li key={index} className="flex items-center gap-2 text-sm">
                    <div className={`w-2 h-2 bg-${profileInfo.color} rounded-full`} />
                    {char}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex gap-4 justify-center">
              <Button variant="outline" onClick={onPrev}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Previous
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

  return (
    <div className="max-w-3xl mx-auto">
      <Card className="shadow-elegant">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl mb-2">Risk Personality Assessment</CardTitle>
          <p className="text-muted-foreground">
            Answer these 6 questions to determine your investment risk tolerance
          </p>
          <div className="flex justify-center mt-4">
            <div className="text-sm text-muted-foreground">
              Progress: {Object.keys(answers).length}/{questions.length} questions completed
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-8">
          {questions.map((question) => (
            <div key={question.id} className="space-y-4">
              <h3 className="font-semibold text-lg">
                {question.id}. {question.question}
              </h3>
              <RadioGroup
                value={answers[question.id]?.toString() || ""}
                onValueChange={(value) => handleAnswerChange(question.id, value)}
              >
                {question.options.map((option) => (
                  <div key={option.value} className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                    <RadioGroupItem value={option.value} id={`q${question.id}-${option.value}`} />
                    <Label 
                      htmlFor={`q${question.id}-${option.value}`} 
                      className="flex-1 cursor-pointer text-sm"
                    >
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>
          ))}

          <div className="flex gap-4 justify-center pt-6 border-t">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={!isComplete}
              className="bg-gradient-primary hover:opacity-90 disabled:opacity-50"
            >
              Calculate My Risk Profile
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};