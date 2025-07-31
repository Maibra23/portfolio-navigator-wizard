import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, TrendingUp, Shield, DollarSign } from 'lucide-react';
import { WelcomeStep } from './wizard/WelcomeStep';
import { RiskProfiler } from './wizard/RiskProfiler';
import { CapitalInput } from './wizard/CapitalInput';
import { StockSelection } from './wizard/StockSelection';

export type RiskProfile = 'very-conservative' | 'conservative' | 'moderate' | 'aggressive' | 'very-aggressive' | null;

export interface PortfolioAllocation {
  symbol: string;
  allocation: number;
  name?: string;
  assetType?: 'stock' | 'bond' | 'etf';
}

export interface WizardData {
  riskProfile: RiskProfile;
  capital: number;
  selectedStocks: PortfolioAllocation[];
}

const STEPS = [
  { id: 'welcome', title: 'Welcome', icon: TrendingUp },
  { id: 'risk', title: 'Risk Profile', icon: Shield },
  { id: 'capital', title: 'Capital Input', icon: DollarSign },
  { id: 'stocks', title: 'Stock Selection', icon: TrendingUp },
  { id: 'optimization', title: 'Optimization', icon: TrendingUp },
  { id: 'stress-test', title: 'Stress Test', icon: Shield },
];

export const PortfolioWizard = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [wizardData, setWizardData] = useState<WizardData>({
    riskProfile: null,
    capital: 0,
    selectedStocks: [],
  });

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateWizardData = (data: Partial<WizardData>) => {
    setWizardData(prev => ({ ...prev, ...data }));
  };

  const renderStep = () => {
    console.log('Current step:', currentStep, 'Step ID:', STEPS[currentStep].id);
    
    switch (STEPS[currentStep].id) {
      case 'welcome':
        return <WelcomeStep onNext={nextStep} />;
      case 'risk':
        return (
          <RiskProfiler
            onNext={nextStep}
            onPrev={prevStep}
            onProfileUpdate={(profile) => updateWizardData({ riskProfile: profile })}
            currentProfile={wizardData.riskProfile}
          />
        );
      case 'capital':
        return (
          <CapitalInput
            onNext={nextStep}
            onPrev={prevStep}
            onCapitalUpdate={(capital) => updateWizardData({ capital })}
            currentCapital={wizardData.capital}
          />
        );
      case 'stocks':
        console.log('Rendering StockSelection component');
        return (
          <StockSelection
            onNext={nextStep}
            onPrev={prevStep}
            onStocksUpdate={(selectedStocks) => updateWizardData({ selectedStocks })}
            selectedStocks={wizardData.selectedStocks}
            riskProfile={wizardData.riskProfile || 'moderate'}
            capital={wizardData.capital}
          />
        );
      default:
        console.log('Rendering default step for:', STEPS[currentStep].id);
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
    <div className="min-h-screen bg-gradient-bg">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-4">
            Portfolio Wizard
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Build and test your custom investment portfolio step by step
          </p>
        </div>

        {/* Progress Bar */}
        <Card className="shadow-card mb-8">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">
                Step {currentStep + 1} of {STEPS.length}: {STEPS[currentStep].title}
              </h2>
              <span className="text-sm text-muted-foreground">{Math.round(progress)}% Complete</span>
            </div>
            <Progress value={progress} className="h-3" />
            
            {/* Step indicators */}
            <div className="flex justify-between mt-4">
              {STEPS.map((step, index) => {
                const StepIcon = step.icon;
                const isCompleted = index < currentStep;
                const isCurrent = index === currentStep;
                
                return (
                  <div key={step.id} className="flex flex-col items-center">
                    <div
                      className={`
                        w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-colors
                        ${isCompleted ? 'bg-accent text-accent-foreground' : 
                          isCurrent ? 'bg-primary text-primary-foreground' : 
                          'bg-muted text-muted-foreground'}
                      `}
                    >
                      <StepIcon className="h-4 w-4" />
                    </div>
                    <span className="text-xs text-center">{step.title}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Step Content */}
        <div className="animate-fade-in">
          {renderStep()}
        </div>
        
        {/* Debug Panel - Remove in production */}
        <div className="mt-8 p-4 bg-muted/30 rounded-lg">
          <h4 className="font-medium mb-2">Debug Information</h4>
          <div className="text-sm space-y-1">
            <p>Current Step Index: {currentStep}</p>
            <p>Current Step ID: {STEPS[currentStep].id}</p>
            <p>Current Step Title: {STEPS[currentStep].title}</p>
            <p>Total Steps: {STEPS.length}</p>
            <p>Risk Profile: {wizardData.riskProfile || 'null'}</p>
            <p>Capital: {wizardData.capital}</p>
            <p>Selected Stocks: {wizardData.selectedStocks.length}</p>
          </div>
        </div>
      </div>
    </div>
  );
};