import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, TrendingUp, Shield, DollarSign, BarChart3, CheckCircle, FileText } from 'lucide-react';
import { WelcomeStep } from './wizard/WelcomeStep';
import { RiskProfiler } from './wizard/RiskProfiler';
import { CapitalInput } from './wizard/CapitalInput';
import { StockSelection } from './wizard/StockSelection';
import { PortfolioOptimization } from './wizard/PortfolioOptimization';
import { StressTest } from './wizard/StressTest';
import { FinalizePortfolio } from './wizard/FinalizePortfolio';
import { ThankYouStep } from './wizard/ThankYouStep';

export type RiskProfile = 'very-conservative' | 'conservative' | 'moderate' | 'aggressive' | 'very-aggressive' | null;

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
}

export interface PortfolioMetrics {
  expectedReturn: number;
  risk: number;
  diversificationScore: number;
  sharpeRatio: number;
}

// Selected portfolio data from optimization step
export interface SelectedPortfolioData {
  source: 'current' | 'weights' | 'market';
  tickers: string[];
  weights: Record<string, number>;
  metrics: {
    expected_return: number;
    risk: number;
    sharpe_ratio: number;
  };
}

export interface WizardData {
  riskProfile: RiskProfile;
  riskAnalysis: any;
  capital: number;
  selectedStocks: PortfolioAllocation[];
  portfolioMetrics: PortfolioMetrics | null;
  selectedPortfolio: SelectedPortfolioData | null;
}

const STEPS = [
  { id: 'welcome', title: 'Welcome', icon: TrendingUp },
  { id: 'risk', title: 'Risk Profile', icon: Shield },
  { id: 'capital', title: 'Capital Input', icon: DollarSign },
  { id: 'stocks', title: 'Stock Selection', icon: TrendingUp },
  { id: 'optimization', title: 'Optimization', icon: BarChart3 },
  { id: 'stress-test', title: 'Stress Test', icon: Shield },
  { id: 'finalize', title: 'Finalize Portfolio', icon: FileText },
  { id: 'thank-you', title: 'Complete', icon: CheckCircle },
];

export const PortfolioWizard = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [wizardData, setWizardData] = useState<WizardData>({
    riskProfile: null,
    riskAnalysis: null,
    capital: 0,
    selectedStocks: [],
    portfolioMetrics: null,
    selectedPortfolio: null,
  });

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const nextStep = () => {
    console.log('🔄 nextStep called. Current step:', currentStep, 'Max step:', STEPS.length - 1);
    if (currentStep < STEPS.length - 1) {
      const newStep = currentStep + 1;
      console.log('✅ Moving to step:', newStep, 'Step ID:', STEPS[newStep].id);
      setCurrentStep(newStep);
    } else {
      console.log('⚠️ Already at last step');
    }
  };

  const prevStep = () => {
    console.log('🔄 prevStep called. Current step:', currentStep);
    if (currentStep > 0) {
      const newStep = currentStep - 1;
      console.log('✅ Moving to step:', newStep, 'Step ID:', STEPS[newStep].id);
      setCurrentStep(newStep);
    } else {
      console.log('⚠️ Already at first step');
    }
  };

  const updateWizardData = (data: Partial<WizardData>) => {
    setWizardData(prev => ({ ...prev, ...data }));
  };

  const renderStep = () => {
    console.log('🔄 renderStep called. Current step:', currentStep, 'Step ID:', STEPS[currentStep].id, 'Step title:', STEPS[currentStep].title);
    
    switch (STEPS[currentStep].id) {
      case 'welcome':
        console.log('📱 Rendering WelcomeStep');
        return <WelcomeStep onNext={nextStep} />;
      case 'risk':
        console.log('📱 Rendering RiskProfiler');
        return (
          <RiskProfiler
            onNext={nextStep}
            onPrev={prevStep}
            onProfileUpdate={(profile, analysis) => updateWizardData({ riskProfile: profile, riskAnalysis: analysis })}
            currentProfile={wizardData.riskProfile}
            currentAnalysis={wizardData.riskAnalysis}
          />
        );
      case 'capital':
        console.log('📱 Rendering CapitalInput');
        return (
          <CapitalInput
            onNext={nextStep}
            onPrev={prevStep}
            onCapitalUpdate={(capital) => updateWizardData({ capital })}
            currentCapital={wizardData.capital}
          />
        );
      case 'stocks':
        console.log('📱 Rendering StockSelection component with data:', {
          riskProfile: wizardData.riskProfile,
          capital: wizardData.capital,
          selectedStocks: wizardData.selectedStocks.length
        });
        return (
          <StockSelection
            onNext={nextStep}
            onPrev={prevStep}
            onStocksUpdate={(selectedStocks) => updateWizardData({ selectedStocks })}
            onMetricsUpdate={(metrics) => updateWizardData({ portfolioMetrics: metrics })}
            selectedStocks={wizardData.selectedStocks}
            riskProfile={wizardData.riskProfile || 'moderate'}
            capital={wizardData.capital}
          />
        );
      case 'optimization':
        console.log('📱 Rendering PortfolioOptimization component');
        return (
          <PortfolioOptimization
            onNext={nextStep}
            onPrev={prevStep}
            selectedStocks={wizardData.selectedStocks}
            riskProfile={wizardData.riskProfile || 'moderate'}
            capital={wizardData.capital}
            portfolioMetrics={wizardData.portfolioMetrics}
            initialSelectedPortfolio={wizardData.selectedPortfolio}
            onPortfolioSelection={(portfolio) => {
              console.log('📊 Portfolio selection received:', portfolio.source, portfolio.tickers);
              updateWizardData({ selectedPortfolio: portfolio });
            }}
          />
        );
      case 'stress-test':
        console.log('📱 Rendering StressTest component');
        return (
          <StressTest
            onNext={nextStep}
            onPrev={prevStep}
            selectedPortfolio={wizardData.selectedPortfolio}
            capital={wizardData.capital}
            riskProfile={wizardData.riskProfile || 'moderate'}
          />
        );
      case 'finalize':
        console.log('📱 Rendering FinalizePortfolio component');
        return (
          <FinalizePortfolio
            onComplete={() => {
              console.log('✅ Portfolio finalized – moving to thank-you step');
              nextStep();
            }}
            onPrev={prevStep}
            capital={wizardData.capital}
            riskProfile={wizardData.riskProfile || 'moderate'}
          />
        );
      case 'thank-you':
        return (
          <ThankYouStep
            onBackToSummary={prevStep}
            onStartOver={() => setCurrentStep(0)}
          />
        );
      default:
        console.log('📱 Rendering default step for:', STEPS[currentStep].id);
        return (
          <div className="text-center py-12">
            <h3 className="text-xl font-semibold mb-4">Step {currentStep + 1} - Coming Soon</h3>
            <p className="text-muted-foreground mb-6">This step is under development.</p>
            <div className="flex gap-4 justify-center">
              {currentStep > 0 && (
                <Button variant="outline" onClick={prevStep}>
                  Previous
                </Button>
              )}
              <Button onClick={nextStep} disabled={currentStep >= STEPS.length - 1}>
                Next Step
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation Header */}
      <div className="bg-card border-b border-border px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-center items-center">
          <h1 className="text-2xl font-bold text-foreground">Portfolio Navigator</h1>
        </div>
      </div>

      {/* Main Wizard Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-semibold text-sm">
                {currentStep + 1}
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">
                  {STEPS[currentStep].title}
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Step {currentStep + 1} of {STEPS.length}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-muted-foreground">{Math.round(progress)}%</div>
              <div className="text-xs text-muted-foreground">Complete</div>
            </div>
          </div>
          <Progress value={progress} className="h-1.5" />
        </div>

        {renderStep()}
      </div>
    </div>
  );
};