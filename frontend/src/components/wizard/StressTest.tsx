/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  LineChart, 
  AreaChart, 
  BarChart, 
  ComposedChart,
  ResponsiveContainer, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  Line, 
  Area, 
  Bar,
  ReferenceDot,
  ReferenceLine
} from 'recharts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  Shield, 
  TrendingDown, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  ArrowRight, 
  ArrowLeft,
  Loader2,
  Info,
  BarChart3,
  Activity,
  AlertCircle,
  Building2,
  Check,
  Download,
  Share2,
  Settings,
  Zap,
  Calendar,
  GitCompare,
  FileText
} from 'lucide-react';

interface SelectedPortfolioData {
  source: 'current' | 'weights' | 'market';
  tickers: string[];
  weights: Record<string, number>;
  metrics: {
    expected_return: number;
    risk: number;
    sharpe_ratio: number;
  };
}

interface StressTestProps {
  onNext: () => void;
  onPrev: () => void;
  selectedPortfolio: SelectedPortfolioData | null;
  capital: number;
  riskProfile: string;
}

export const StressTest: React.FC<StressTestProps> = ({
  onNext,
  onPrev,
  selectedPortfolio,
  capital,
  riskProfile
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string | null>('covid19');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStep, setLoadingStep] = useState('');
  const [stressTestResults, setStressTestResults] = useState<{
    portfolio_summary: any;
    scenarios: {
      covid19?: any;
      '2008_crisis'?: any;
    };
    resilience_score: number;
    overall_assessment: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [whatIfResults, setWhatIfResults] = useState<any>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfParams, setWhatIfParams] = useState({
    volatility_multiplier: 2.0,
    return_adjustment: -0.15,
    time_horizon_months: 12
  });
  const [showComparison, setShowComparison] = useState(false);
  const [hypotheticalParams, setHypotheticalParams] = useState({
    scenario_type: 'tech_crash',
    market_decline: -30,
    sector_impact: 'technology',
    duration_months: 6,
    recovery_rate: 'moderate'
  });
  const [hypotheticalResults, setHypotheticalResults] = useState<any>(null);
  const [hypotheticalLoading, setHypotheticalLoading] = useState(false);
  const [activeView, setActiveView] = useState<'overview' | 'comparison' | 'monte-carlo' | 'what-if' | 'hypothetical' | 'timeline'>('overview');
  const [selectedTimelineEvent, setSelectedTimelineEvent] = useState<any>(null);
  // Toggle states for Interactive Timeline legend
  const [visibleEventTypes, setVisibleEventTypes] = useState<{
    crisis: boolean;
    policy: boolean;
    recovery: boolean;
    warning: boolean;
  }>({
    crisis: true,
    policy: true,
    recovery: true,
    warning: true
  });
  const [showRecoveryThresholds, setShowRecoveryThresholds] = useState(true);
  const [showRecoveryThresholdsOverview, setShowRecoveryThresholdsOverview] = useState(true);

  // Cache warm-up: Pre-warm Redis cache when portfolio is available
  React.useEffect(() => {
    if (selectedPortfolio && selectedPortfolio.tickers && selectedPortfolio.tickers.length > 0) {
      // Warm cache in background (non-blocking)
      fetch('/api/portfolio/warm-tickers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: selectedPortfolio.tickers })
      }).catch(() => {
        // Silently fail - cache warm-up is optional
      });
    }
  }, [selectedPortfolio]);

  // Key market events for interactive timeline annotations
  const crisisEvents = {
    covid19: [
      { date: '2020-02', event: 'WHO declares COVID-19 pandemic concerns', type: 'warning' },
      { date: '2020-03', event: 'Fed emergency rate cut to 0%', type: 'policy' },
      { date: '2020-03', event: 'Market circuit breakers triggered 4x', type: 'crisis' },
      { date: '2020-04', event: 'Fed launches $2.3T lending programs', type: 'policy' },
      { date: '2020-06', event: 'Markets recover to pre-crisis levels', type: 'recovery' }
    ],
    '2008_crisis': [
      { date: '2008-03', event: 'Bear Stearns collapse', type: 'crisis' },
      { date: '2008-09', event: 'Lehman Brothers bankruptcy', type: 'crisis' },
      { date: '2008-10', event: 'Fed slashes rates, TARP announced', type: 'policy' },
      { date: '2009-03', event: 'Market bottom reached', type: 'bottom' },
      { date: '2009-06', event: 'Recovery begins', type: 'recovery' }
    ]
  };

  const handleRunStressTest = async () => {
    if (!selectedPortfolio || !selectedScenario) return;
    
    // Validation
    if (!selectedPortfolio.tickers || selectedPortfolio.tickers.length < 2) {
      setError('Portfolio must contain at least 2 tickers for stress testing');
      return;
    }
    
    if (!selectedPortfolio.weights || Object.keys(selectedPortfolio.weights).length === 0) {
      setError('Portfolio weights are required for stress testing');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setLoadingProgress(0);
    setLoadingStep('Initializing analysis...');
    
    // Simulate progress updates
    let progressInterval: NodeJS.Timeout | null = setInterval(() => {
      setLoadingProgress(prev => {
        if (prev < 90) {
          const steps = [
            'Fetching historical data...',
            'Calculating portfolio values...',
            'Analyzing crisis period...',
            'Computing risk metrics...',
            'Running Monte Carlo simulation...',
            'Finalizing results...'
          ];
          const stepIndex = Math.floor((prev / 90) * steps.length);
          setLoadingStep(steps[stepIndex] || 'Processing...');
          return prev + 10;
        }
        return prev;
      });
    }, 500);
    
    try {
      const response = await fetch('/api/portfolio/stress-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tickers: selectedPortfolio.tickers,
          weights: selectedPortfolio.weights,
          scenarios: [selectedScenario],
          capital: capital,
          risk_profile: riskProfile,
        }),
      });
      
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setLoadingProgress(100);
      setLoadingStep('Complete!');
      
      if (!response.ok) {
        let errorMessage = 'Failed to run stress test';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      
      // Validate response structure
      if (!data || !data.scenarios || Object.keys(data.scenarios).length === 0) {
        throw new Error('No scenario results returned from server');
      }
      
      setStressTestResults(data);
      setActiveScenario(selectedScenario);
    } catch (err: any) {
      console.error('Stress test error:', err);
      setError(err.message || 'An error occurred while running stress tests. Please try again.');
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setLoadingProgress(0);
      setLoadingStep('');
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        setLoadingProgress(0);
        setLoadingStep('');
      }, 500);
    }
  };
  
  const handleExportResults = () => {
    if (!stressTestResults) return;
    
    // Create CSV content
    const csvRows = [];
    csvRows.push('Portfolio Stress Test Results');
    csvRows.push('');
    csvRows.push('Portfolio Summary');
    csvRows.push(`Tickers,${stressTestResults.portfolio_summary.tickers.join(';')}`);
    csvRows.push(`Capital,${stressTestResults.portfolio_summary.capital}`);
    csvRows.push(`Risk Profile,${stressTestResults.portfolio_summary.risk_profile}`);
    csvRows.push('');
    csvRows.push('Resilience Score');
    csvRows.push(`Score,${stressTestResults.resilience_score}`);
    csvRows.push(`Assessment,${stressTestResults.overall_assessment}`);
    csvRows.push('');
    
    // Add scenario data
    Object.entries(stressTestResults.scenarios).forEach(([scenario, data]: [string, any]) => {
      csvRows.push(`${data.scenario_name || scenario}`);
      csvRows.push(`Total Return,${(data.metrics.total_return * 100).toFixed(2)}%`);
      csvRows.push(`Max Drawdown,${(data.metrics.max_drawdown * 100).toFixed(2)}%`);
      csvRows.push(`Recovery Months,${data.metrics.recovery_months || 'N/A'}`);
      csvRows.push('');
    });
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `stress-test-results-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const getResilienceColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getResilienceBadgeColor = (score: number) => {
    if (score >= 70) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getResilienceLabel = (score: number) => {
    if (score >= 70) return 'Strong';
    if (score >= 50) return 'Moderate';
    return 'Weak';
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl flex items-center justify-center gap-2">
            <Shield className="h-6 w-6 text-blue-600" />
            Portfolio Stress Test
          </CardTitle>
          <p className="text-muted-foreground mt-2">
            Test your portfolio's resilience during historical market crises
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Step Indicator - Progressive Disclosure */}
          <div className="flex items-center justify-center gap-4 mb-6 pb-6 border-b">
            <div className="flex items-center gap-2">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                selectedScenario ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {selectedScenario ? <Check className="h-5 w-5" /> : '1'}
              </div>
              <span className="text-sm font-medium">Select Scenario</span>
            </div>
            <ArrowRight className="h-5 w-5 text-gray-400" />
            <div className="flex items-center gap-2">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                isLoading ? 'bg-blue-500 text-white animate-pulse' : 
                stressTestResults ? 'bg-green-500 text-white' : 
                'bg-gray-200 text-gray-600'
              }`}>
                {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : 
                 stressTestResults ? <Check className="h-5 w-5" /> : '2'}
              </div>
              <span className="text-sm font-medium">Run Test</span>
            </div>
            <ArrowRight className="h-5 w-5 text-gray-400" />
            <div className="flex items-center gap-2">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                stressTestResults ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {stressTestResults ? <Check className="h-5 w-5" /> : '3'}
              </div>
              <span className="text-sm font-medium">Review Results</span>
            </div>
          </div>

          {/* Scenario Selection */}
          {!stressTestResults && (
            <div className="space-y-4">
              <div className="text-center">
                <h3 className="text-lg font-semibold mb-2">Select Stress Test Scenario</h3>
                <p className="text-sm text-muted-foreground">
                  Choose one scenario to test your portfolio's resilience
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* COVID-19 Scenario Card */}
                <Card 
                  className={`cursor-pointer transition-all ${
                    selectedScenario === 'covid19' 
                      ? 'border-2 border-blue-500 bg-blue-50 shadow-md' 
                      : 'border border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                  onClick={() => setSelectedScenario('covid19')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {selectedScenario === 'covid19' && (
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                          )}
                          <AlertCircle className="h-5 w-5 text-blue-600" />
                          <h3 className="font-semibold text-lg">2020 COVID-19 Crash</h3>
                        </div>
                        <p className="text-xs text-gray-600 mb-3">
                          Fastest market crash in modern history (Feb-Apr 2020). Tests rapid volatility and recovery capability.
                        </p>
                        <div className="space-y-1 text-xs text-gray-500">
                          <div>• Crisis Duration: 3 months</div>
                          <div>• Recovery Pattern: V-shaped</div>
                          <div>• Volatility: High</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 2008 Crisis Scenario Card */}
                <Card 
                  className={`cursor-pointer transition-all ${
                    selectedScenario === '2008_crisis' 
                      ? 'border-2 border-blue-500 bg-blue-50 shadow-md' 
                      : 'border border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                  onClick={() => setSelectedScenario('2008_crisis')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {selectedScenario === '2008_crisis' && (
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                          )}
                          <Building2 className="h-5 w-5 text-amber-600" />
                          <h3 className="font-semibold text-lg">2008 Financial Crisis</h3>
                        </div>
                        <p className="text-xs text-gray-600 mb-3">
                          Most severe crisis since Great Depression (Sep 2008 - Mar 2010). Tests prolonged drawdown and correlation breakdown.
                        </p>
                        <div className="space-y-1 text-xs text-gray-500">
                          <div>• Crisis Duration: 18 months</div>
                          <div>• Recovery Pattern: Prolonged</div>
                          <div>• Correlation Breakdown: Yes</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Options */}
              <div className="flex flex-col gap-3 pt-4">
                {/* Progress Indicator */}
                {isLoading && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">{loadingStep}</span>
                      <span className="text-gray-600">{loadingProgress}%</span>
                    </div>
                    <Progress value={loadingProgress} className="h-2" />
                  </div>
                )}
                
                {/* Run Button */}
                <div className="flex justify-center pt-2">
                  <Button
                    onClick={handleRunStressTest}
                    disabled={!selectedScenario || isLoading || !selectedPortfolio}
                    className="bg-gradient-primary hover:opacity-90 min-w-[200px]"
                    size="lg"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Running Stress Test...
                      </>
                    ) : (
                      <>
                        <Shield className="mr-2 h-5 w-5" />
                        Run Selected Scenario
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {!selectedPortfolio && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Please select a portfolio in the Optimization step before running stress tests.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {/* Results Display */}
          {stressTestResults && (
            <div className="space-y-6">
              {/* Action Bar */}
              <div className="flex items-center justify-between pb-4 border-b">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowComparison(!showComparison)}
                    disabled={Object.keys(stressTestResults.scenarios).length < 2}
                  >
                    <GitCompare className="h-4 w-4 mr-2" />
                    {showComparison ? 'Hide Comparison' : 'Show Comparison'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExportResults}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export Results
                  </Button>
                </div>
                <Badge variant="outline" className="text-sm">
                  Processing Time: {stressTestResults.processing_time_seconds}s
                </Badge>
              </div>
              
              {/* View Tabs */}
              <Tabs value={activeView} onValueChange={(v) => setActiveView(v as any)}>
                <TabsList className="grid w-full grid-cols-7">
                  <TabsTrigger value="overview" className="flex items-center gap-1 text-xs">
                    <FileText className="h-3 w-3" />
                    Overview
                  </TabsTrigger>
                  <TabsTrigger value="timeline" className="flex items-center gap-1 text-xs">
                    <Calendar className="h-3 w-3" />
                    Timeline
                  </TabsTrigger>
                  <TabsTrigger value="comparison" className="flex items-center gap-1 text-xs" disabled={!showComparison || Object.keys(stressTestResults.scenarios).length < 2}>
                    <GitCompare className="h-3 w-3" />
                    Compare
                  </TabsTrigger>
                  <TabsTrigger value="monte-carlo" className="flex items-center gap-1 text-xs">
                    <BarChart3 className="h-3 w-3" />
                    Monte Carlo
                  </TabsTrigger>
                  <TabsTrigger value="what-if" className="flex items-center gap-1 text-xs">
                    <Zap className="h-3 w-3" />
                    What-If
                  </TabsTrigger>
                  <TabsTrigger value="hypothetical" className="flex items-center gap-1 text-xs">
                    <AlertTriangle className="h-3 w-3" />
                    Scenarios
                  </TabsTrigger>
                </TabsList>
                
                {/* Overview Tab */}
                <TabsContent value="overview" className="space-y-6 mt-6">
                  {/* Portfolio Summary Card */}
                  <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>Portfolio Summary</span>
                    <Badge variant="outline" className="text-xs">
                      {selectedPortfolio!.source === 'current' ? 'Current Portfolio' : 
                       selectedPortfolio!.source === 'weights' ? 'Weights-Optimized' : 
                       'Market-Optimized'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    <div className="text-sm text-gray-600 mb-2">
                      <strong>Tickers:</strong> {selectedPortfolio!.tickers.join(', ')}
                    </div>
                    <div className="text-xs text-gray-500">
                      Portfolio forwarded from Recommendations tab ({selectedPortfolio!.tickers.length} holdings)
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="text-xs text-gray-600 mb-1">Expected Return</div>
                      <div className="text-xl font-bold text-blue-700">
                        {(selectedPortfolio!.metrics.expected_return * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="text-center p-3 bg-amber-50 rounded-lg border border-amber-200">
                      <div className="text-xs text-gray-600 mb-1">Risk Level</div>
                      <div className="text-xl font-bold text-amber-700">
                        {(selectedPortfolio!.metrics.risk * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="text-center p-3 bg-purple-50 rounded-lg border border-purple-200">
                      <div className="text-xs text-gray-600 mb-1">Sharpe Ratio</div>
                      <div className="text-xl font-bold text-purple-700">
                        {selectedPortfolio!.metrics.sharpe_ratio.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

                  {/* Resilience Score Card */}
                  <Card className="border-2 border-green-200">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Shield className="h-5 w-5 text-green-600" />
                    Portfolio Resilience Score
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-6">
                    <div className="relative w-32 h-32">
                      <svg className="w-32 h-32 transform -rotate-90">
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="#e5e7eb"
                          strokeWidth="12"
                          fill="none"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke={Math.min(100, stressTestResults.resilience_score) >= 70 ? '#22c55e' : Math.min(100, stressTestResults.resilience_score) >= 50 ? '#f59e0b' : '#ef4444'}
                          strokeWidth="12"
                          fill="none"
                          strokeDasharray={`${(Math.min(100, Math.max(0, stressTestResults.resilience_score)) / 100) * 351.86} 351.86`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                          <div className={`text-2xl font-bold ${getResilienceColor(Math.min(100, stressTestResults.resilience_score))}`}>
                            {Math.min(100, Math.max(0, stressTestResults.resilience_score)).toFixed(0)}
                          </div>
                          <div className="text-xs text-gray-500">out of 100</div>
                        </div>
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-gray-700 mb-3">
                        {stressTestResults.overall_assessment}
                      </p>
                      <Badge className={`${getResilienceBadgeColor(stressTestResults.resilience_score)} text-white`}>
                        {getResilienceLabel(stressTestResults.resilience_score)} Resilience
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
                  
                  {/* Scenario Results - Show based on selected scenario */}
                  {selectedScenario === 'covid19' && stressTestResults.scenarios.covid19 && (
                    <Card className="border-2 border-blue-200">
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Activity className="h-5 w-5 text-blue-600" />
                          2020 COVID-19 Crash Analysis
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          Period: {stressTestResults.scenarios.covid19.period.start} to {stressTestResults.scenarios.covid19.period.end}
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        {/* Key Metrics - Compact Horizontal Layout */}
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-red-50 border border-red-200">
                            <span className="text-xs text-red-700 font-medium">Total Return</span>
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <Info className="h-3 w-3 text-red-500 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                Total return over the entire crisis period (from start to end date). Positive values indicate portfolio growth despite the crisis.
                              </TooltipContent>
                            </UITooltip>
                            <span className="text-sm font-bold text-red-800">
                              {(stressTestResults.scenarios.covid19.metrics.total_return * 100).toFixed(1)}%
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-orange-50 border border-orange-200">
                            <span className="text-xs text-orange-700 font-medium">Max Drawdown</span>
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <Info className="h-3 w-3 text-orange-500 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                <div className="font-semibold mb-1">Maximum Drawdown</div>
                                <div className="mb-2">Maximum decline from pre-crisis peak to crisis trough.</div>
                                <div className="mb-1"><strong>Calculation:</strong> (Trough Value - Peak Value) / Peak Value</div>
                                <div className="mb-1"><strong>Peak:</strong> Portfolio value at crisis start (or max before crisis)</div>
                                <div className="mb-1"><strong>Trough:</strong> Minimum value during crisis period</div>
                                <div className="text-yellow-300 mt-2">Only shown if drawdown exceeds 3% threshold</div>
                              </TooltipContent>
                            </UITooltip>
                            <span className="text-sm font-bold text-orange-800">
                              {(stressTestResults.scenarios.covid19.metrics.max_drawdown * 100).toFixed(1)}%
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-blue-50 border border-blue-200">
                            <span className="text-xs text-blue-700 font-medium">Recovery Time</span>
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <Info className="h-3 w-3 text-blue-500 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                <div className="font-semibold mb-1">Recovery Time to Peak</div>
                                <div className="mb-2">Time to recover to 100% of pre-crisis peak value (full recovery).</div>
                                <div className="mb-1"><strong>If Recovered:</strong> Actual months from trough to peak</div>
                                <div className="mb-1"><strong>If Not Recovered:</strong> Projected months based on current trajectory (realistic scenario)</div>
                                <div className="mb-1"><strong>Target:</strong> 100% of peak (full recovery)</div>
                                <div className="text-yellow-300 mt-2">Only calculated if drawdown exceeds 3% threshold</div>
                              </TooltipContent>
                            </UITooltip>
                            <span className="text-sm font-bold text-blue-800">
                              {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant 
                                ? (stressTestResults.scenarios.covid19.metrics.recovered
                                    ? `${stressTestResults.scenarios.covid19.metrics.recovery_months} mo`
                                    : stressTestResults.scenarios.covid19.metrics.trajectory_projections?.realistic_months
                                      ? `${stressTestResults.scenarios.covid19.metrics.trajectory_projections.realistic_months.toFixed(1)} mo (proj)`
                                      : 'N/A')
                                : 'N/A'}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-purple-50 border border-purple-200">
                            <span className="text-xs text-purple-700 font-medium">Pattern</span>
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <Info className="h-3 w-3 text-purple-500 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                V-shaped: Quick recovery (&lt;6 months). U-shaped: Moderate recovery (6-12 months). L-shaped: Slow or no recovery (&gt;12 months).
                              </TooltipContent>
                            </UITooltip>
                            <span className="text-sm font-bold text-purple-800">
                              {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant
                                ? stressTestResults.scenarios.covid19.metrics.recovery_pattern.replace(' (projected)', '')
                                : 'N/A'}
                            </span>
                          </div>
                          
                          {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios.covid19.metrics.recovery_needed_pct !== undefined && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-amber-50 border border-amber-200">
                              <span className="text-xs text-amber-700 font-medium">Recovery Needed</span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-amber-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                  <div className="font-semibold mb-1">Recovery Needed</div>
                                  <div className="mb-2">Percentage increase needed to restore portfolio to pre-crisis peak value.</div>
                                  <div className="mb-1"><strong>Calculation:</strong> ((Peak Value - Current Value) / Peak Value) × 100</div>
                                  <div className="mb-1"><strong>Peak:</strong> Portfolio value at crisis start</div>
                                  <div className="mb-1"><strong>Current:</strong> Latest portfolio value</div>
                                  <div className="text-yellow-300 mt-2">Only shown if drawdown exceeds 3% threshold</div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-sm font-bold text-amber-800">
                                {stressTestResults.scenarios.covid19.metrics.recovery_needed_pct.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          
                          {/* Projections - Only show if recovery is needed (recovery_needed_pct > 0) */}
                          {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios.covid19.metrics.recovery_needed_pct > 0 &&
                           stressTestResults.scenarios.covid19.metrics.trajectory_projections && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-indigo-50 border border-indigo-200">
                              <span className="text-xs text-indigo-700 font-medium">Projections</span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                  <div className="font-semibold mb-1">Trajectory Projections</div>
                                  <div className="mb-2">Estimated months to reach peak value based on current trend analysis.</div>
                                  <div className="mb-1"><strong>Realistic:</strong> Mean projection based on linear regression</div>
                                  <div className="mb-1"><strong>Optimistic:</strong> Upper bound (faster recovery)</div>
                                  <div className="mb-1"><strong>Pessimistic:</strong> Lower bound (slower recovery)</div>
                                  <div className="text-yellow-300 mt-2">Based on last 6 months trend</div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-xs text-indigo-600 font-medium">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.optimistic_months 
                                  ? `O:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.optimistic_months.toFixed(1)}`
                                  : 'O:N/A'}
                              </span>
                              <span className="text-xs text-indigo-700 font-bold">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.realistic_months 
                                  ? `R:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.realistic_months.toFixed(1)}`
                                  : 'R:N/A'}
                              </span>
                              <span className="text-xs text-indigo-600 font-medium">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.pessimistic_months 
                                  ? `P:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.pessimistic_months.toFixed(1)}`
                                  : 'P:N/A'}
                              </span>
                            </div>
                          )}
                          {/* Show message when portfolio already recovered above peak */}
                          {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios.covid19.metrics.recovery_needed_pct <= 0 && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-green-50 border border-green-200">
                              <CheckCircle className="h-4 w-4 text-green-600" />
                              <span className="text-xs text-green-700 font-medium">Already above peak - projections N/A</span>
                            </div>
                          )}
                        </div>

                        {/* Portfolio Value Timeline Chart */}
                        {stressTestResults.scenarios.covid19.monthly_performance && 
                         stressTestResults.scenarios.covid19.monthly_performance.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-center">Portfolio Value Over Time</div>
                            <div className="h-64 w-full -ml-4">
                              <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart 
                                  data={(() => {
                                    // Normalize data so January 2020 starts at 100%
                                    const jan2020Value = stressTestResults.scenarios.covid19.monthly_performance.find((m: any) => m.month === '2020-01')?.value || 1.0;
                                    const normalizationFactor = 1.0 / jan2020Value;
                                    
                                    const baseData = stressTestResults.scenarios.covid19.monthly_performance.map((m: any) => ({
                                      date: m.month,
                                      value: ((m.value || 0) * normalizationFactor) * 100,
                                      return: (m.return || 0) * 100,
                                      optimistic: null,
                                      realistic: null,
                                      pessimistic: null
                                    }));
                                    
                                    // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                    // This handles cases where dates might be slightly off or missing
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.peak) {
                                      const peakDate = stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(0, 7) || '';
                                      if (peakDate && !baseData.find((d: any) => d.date === peakDate)) {
                                        // Peak date not in data - find closest month or insert
                                        const peakValue = ((stressTestResults.scenarios.covid19.peaks_troughs.peak.value || 0) * normalizationFactor) * 100;
                                        baseData.push({ date: peakDate, value: peakValue, return: null, optimistic: null, realistic: null, pessimistic: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.trough) {
                                      const troughDate = stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(0, 7) || '';
                                      if (troughDate && !baseData.find((d: any) => d.date === troughDate)) {
                                        const troughValue = ((stressTestResults.scenarios.covid19.peaks_troughs.trough.value || 0) * normalizationFactor) * 100;
                                        baseData.push({ date: troughDate, value: troughValue, return: null, optimistic: null, realistic: null, pessimistic: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    // Add trajectory data if available
                                    // Projection lines should start from the end of the portfolio value line
                                    if (stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections?.trajectory_data &&
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.length > 0) {
                                      const lastDataPoint = baseData[baseData.length - 1];
                                      const lastDate = lastDataPoint?.date;
                                      const lastValue = lastDataPoint?.value; // This is the last actual portfolio value
                                      
                                      if (lastDate && lastValue !== null && lastValue !== undefined) {
                                        const [year, month] = lastDate.split('-').map(Number);
                                        
                                        // First point: connect to the last actual portfolio value
                                        // This ensures smooth connection from actual data to projections
                                        const firstProjectionPoint = stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data[0];
                                        baseData.push({
                                          date: lastDate, // Same date as last actual point
                                          value: lastValue, // Keep actual value for smooth connection
                                          return: null,
                                          optimistic: (firstProjectionPoint?.optimistic || 0) * 100,
                                          realistic: (firstProjectionPoint?.realistic || 0) * 100,
                                          pessimistic: (firstProjectionPoint?.pessimistic || 0) * 100
                                        });
                                        
                                        // Add remaining projection points
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.slice(1).forEach((point: any, idx: number) => {
                                          const futureMonth = month + idx + 2; // +2 because we already added first point
                                          const futureYear = year + Math.floor((futureMonth - 1) / 12);
                                          const futureMonthNormalized = ((futureMonth - 1) % 12) + 1;
                                          const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, '0')}`;
                                          
                                          baseData.push({
                                            date: futureDate,
                                            value: null, // No actual value, only projections
                                            return: null,
                                            optimistic: (point.optimistic || 0) * 100,
                                            realistic: (point.realistic || 0) * 100,
                                            pessimistic: (point.pessimistic || 0) * 100
                                          });
                                        });
                                      }
                                    }
                                    
                                    return baseData;
                                  })()}
                                  margin={{ left: 10, right: 10, top: 10, bottom: 10 }}
                                >
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                                  <XAxis 
                                    dataKey="date" 
                                    tick={{ fontSize: 10 }}
                                    label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
                                  />
                                  <YAxis 
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                                    label={{ value: 'Portfolio Value (%)', angle: -90, position: 'left', offset: 0, style: { textAnchor: 'middle' } }}
                                    domain={['dataMin', 'dataMax']}
                                    width={70}
                                  />
                                  <Tooltip 
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Portfolio Value']}
                                    labelFormatter={(label) => `Month: ${label}`}
                                  />
                                  <Area 
                                    type="monotone" 
                                    dataKey="value" 
                                    stroke="#3b82f6" 
                                    fill="#3b82f6" 
                                    fillOpacity={0.2}
                                  />
                                  {/* Recovery Threshold Lines removed from Portfolio Value Over Time - only show in Interactive Timeline */}
                                  {/* Trajectory Projection Lines - Smooth lines starting from end of portfolio value */}
                                  {stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                                   stressTestResults.scenarios.covid19.metrics.trajectory_projections?.trajectory_data &&
                                   stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.length > 0 && (
                                    <>
                                      {/* Optimistic Trajectory - Smooth line */}
                                      <Line 
                                        dataKey="optimistic" 
                                        stroke="#22c55e"
                                        strokeDasharray="4 4"
                                        strokeWidth={1.5}
                                        dot={false}
                                        connectNulls={true}
                                        type="monotone"
                                        isAnimationActive={false}
                                        name="Optimistic"
                                      />
                                      {/* Realistic Trajectory - Smooth line */}
                                      <Line 
                                        dataKey="realistic" 
                                        stroke="#3b82f6"
                                        strokeDasharray="4 4"
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls={true}
                                        type="monotone"
                                        isAnimationActive={false}
                                        name="Realistic"
                                      />
                                      {/* Pessimistic Trajectory - Smooth line */}
                                      <Line 
                                        dataKey="pessimistic" 
                                        stroke="#f59e0b"
                                        strokeDasharray="4 4"
                                        strokeWidth={1.5}
                                        dot={false}
                                        connectNulls={true}
                                        type="monotone"
                                        isAnimationActive={false}
                                        name="Pessimistic"
                                      />
                                    </>
                                  )}
                                  {(() => {
                                    // Calculate both peak and trough values first to detect overlap
                                    const jan2020Value = stressTestResults.scenarios.covid19.monthly_performance.find((m: any) => m.month === '2020-01')?.value || 1.0;
                                    const normalizationFactor = 1.0 / jan2020Value;
                                    
                                    const peak = stressTestResults.scenarios.covid19.peaks_troughs?.peak;
                                    const trough = stressTestResults.scenarios.covid19.peaks_troughs?.trough;
                                    
                                    if (!peak && !trough) return null;
                                    
                                    let peakValue = 0;
                                    let troughValue = 0;
                                    let peakDate = '';
                                    let troughDate = '';
                                    
                                    if (peak) {
                                      const peakDateFull = peak.date || '';
                                      peakDate = peakDateFull.length >= 7 ? peakDateFull.substring(0, 7) : peakDateFull;
                                      const peakValueRaw = peak.value || 1.0;
                                      peakValue = (peakValueRaw * normalizationFactor) * 100;
                                    }
                                    
                                    if (trough) {
                                      const troughDateFull = trough.date || '';
                                      troughDate = troughDateFull.length >= 7 ? troughDateFull.substring(0, 7) : troughDateFull;
                                      troughValue = ((trough.value || 0) * normalizationFactor) * 100;
                                    }
                                    
                                    // Detect if peak and trough are visually close (within 5% on the chart)
                                    const valueDiff = Math.abs(peakValue - troughValue);
                                    const isOverlapping = valueDiff < 5.0;
                                    
                                    // Adjust label positions to avoid overlap
                                    const peakLabelPos = isOverlapping ? 'topRight' : 'top';
                                    const troughLabelPos = isOverlapping ? 'bottomLeft' : 'bottom';
                                    
                                    return (
                                      <>
                                        {peak && (
                                          <ReferenceDot 
                                            x={peakDate} 
                                            y={peakValue}
                                            r={8}
                                            fill="#22c55e"
                                            stroke="#fff"
                                            strokeWidth={2}
                                            label={{ value: `Peak (${peakValue.toFixed(1)}%)`, position: peakLabelPos, fill: '#22c55e', fontSize: 10 }}
                                          />
                                        )}
                                        {trough && (
                                          <ReferenceDot 
                                            x={troughDate} 
                                            y={troughValue}
                                            r={8}
                                            fill="#ef4444"
                                            stroke="#fff"
                                            strokeWidth={2}
                                            label={{ value: `Trough (${troughValue.toFixed(1)}%)`, position: troughLabelPos, fill: '#ef4444', fontSize: 10 }}
                                          />
                                        )}
                                      </>
                                    );
                                  })()}
                                  {stressTestResults.scenarios.covid19.peaks_troughs?.recovery_peak && (() => {
                                    // Normalize recovery peak value to match chart normalization
                                    const jan2020Value = stressTestResults.scenarios.covid19.monthly_performance.find((m: any) => m.month === '2020-01')?.value || 1.0;
                                    const normalizationFactor = 1.0 / jan2020Value;
                                    // Handle different date formats: YYYY-MM-DD or YYYY-MM
                                    const recoveryDateFull = stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date || '';
                                    const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                    const recoveryValue = ((stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.value || 0) * normalizationFactor) * 100;
                                    
                                    // Always render recovery peak marker
                                    return (
                                      <ReferenceDot 
                                        x={recoveryDate} 
                                        y={recoveryValue}
                                        r={8}
                                        fill="#9333ea"
                                        stroke="#fff"
                                        strokeWidth={2}
                                        label={{ value: `Recovery (${recoveryValue.toFixed(1)}%)`, position: 'top', fill: '#9333ea', fontSize: 10 }}
                                      />
                                    );
                                  })()}
                                </ComposedChart>
                              </ResponsiveContainer>
                            </div>
                            {stressTestResults.scenarios.covid19.peaks_troughs && (
                              <div className="flex items-center justify-center gap-4 text-xs">
                                {stressTestResults.scenarios.covid19.peaks_troughs.peak && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                    <span>Peak ({stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                                {stressTestResults.scenarios.covid19.peaks_troughs.trough && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                    <span>Trough ({stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                                {stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#9333ea' }}></div>
                                    <span>Recovery Peak ({stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Sector Impact */}
                        {stressTestResults.scenarios.covid19.sector_impact && 
                         stressTestResults.scenarios.covid19.sector_impact.sector_returns &&
                         Object.keys(stressTestResults.scenarios.covid19.sector_impact.sector_returns).length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium">Sector Performance During Crisis</div>
                            <div className="h-48 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={Object.entries(stressTestResults.scenarios.covid19.sector_impact.sector_returns).map(([sector, return_pct]: [string, any]) => ({
                                  sector: sector.length > 15 ? sector.substring(0, 15) + '...' : sector,
                                  return: return_pct * 100
                                }))}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis 
                                    dataKey="sector" 
                                    tick={{ fontSize: 10 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={80}
                                  />
                                  <YAxis 
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                                  />
                                  <Tooltip 
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Return']}
                                  />
                                  <Bar 
                                    dataKey="return" 
                                    fill={(entry: any) => entry.return >= 0 ? '#22c55e' : '#ef4444'}
                                  />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* 2008 Crisis Scenario Results */}
                  {selectedScenario === '2008_crisis' && stressTestResults.scenarios['2008_crisis'] && (
                <Card className="border-2 border-amber-200">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Building2 className="h-5 w-5 text-amber-600" />
                      2008 Financial Crisis Analysis
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Period: {stressTestResults.scenarios['2008_crisis'].period.start} to {stressTestResults.scenarios['2008_crisis'].period.end}
                    </p>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        {/* Key Metrics Grid */}
                        <div className="grid grid-cols-4 gap-4">
                          <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                            <div className="text-xs text-red-700 mb-1 flex items-center gap-1">
                              Total Return
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-red-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                  Total return over the entire crisis period (from start to end date). Positive values indicate portfolio growth despite the crisis.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-xl font-bold text-red-800">
                              {(stressTestResults.scenarios['2008_crisis'].metrics.total_return * 100).toFixed(1)}%
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                            <div className="text-xs text-orange-700 mb-1 flex items-center gap-1">
                              Max Drawdown
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-orange-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                  Maximum decline from peak to trough during the crisis. Negative value indicates loss from the highest point.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-xl font-bold text-orange-800">
                              {(stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown * 100).toFixed(1)}%
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="text-xs text-blue-700 mb-1 flex items-center gap-1">
                              Recovery Time
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-blue-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                  Time to recover to 95% of peak value after the trough. N/A means portfolio did not recover within the analyzed period.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-xl font-bold text-blue-800">
                              {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant 
                                ? (stressTestResults.scenarios['2008_crisis'].metrics.recovered
                                    ? `${stressTestResults.scenarios['2008_crisis'].metrics.recovery_months} months`
                                    : stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.realistic_months
                                      ? `${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.realistic_months.toFixed(1)} months (projected)`
                                      : 'N/A')
                                : 'No Significant Drawdown'}
                              {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                               !stressTestResults.scenarios['2008_crisis'].metrics.recovered && 
                               !stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.realistic_months && (
                                <div className="text-xs text-blue-600 mt-1 font-normal">
                                  (Cannot project recovery)
                                </div>
                              )}
                              {!stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && (
                                <div className="text-xs text-blue-600 mt-1 font-normal">
                                  (Drawdown &lt; 3% threshold)
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                            <div className="text-xs text-purple-700 mb-1 flex items-center gap-1">
                              Recovery Pattern
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-purple-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-48 p-2 bg-gray-900 text-white text-xs border-0">
                                  V-shaped: Quick recovery (&lt;6 months). U-shaped: Moderate recovery (6-12 months). L-shaped: Slow or no recovery (&gt;12 months).
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-sm font-bold text-purple-800">
                              {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant
                                ? stressTestResults.scenarios['2008_crisis'].metrics.recovery_pattern
                                : 'No Significant Drawdown'}
                            </div>
                          </div>
                          {/* Recovery Needed Metric */}
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct !== undefined && (
                            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                              <div className="text-xs text-amber-700 mb-1 flex items-center gap-1">
                                Recovery Needed
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-3 w-3 text-amber-500 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                    <div className="font-semibold mb-1">Recovery Needed</div>
                                    <div className="mb-2">Percentage increase needed to restore portfolio to pre-crisis peak value.</div>
                                    <div className="mb-1"><strong>Calculation:</strong> ((Peak Value - Current Value) / Peak Value) × 100</div>
                                    <div className="mb-1"><strong>Peak:</strong> Portfolio value at crisis start</div>
                                    <div className="mb-1"><strong>Current:</strong> Latest portfolio value</div>
                                    <div className="text-yellow-300 mt-2">Only shown if drawdown exceeds 3% threshold</div>
                                  </TooltipContent>
                                </UITooltip>
                              </div>
                              <div className="text-xl font-bold text-amber-800">
                                {stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct.toFixed(1)}%
                              </div>
                            </div>
                          )}
                          {/* Trajectory Projections - Only show if recovery is needed and projections are available */}
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct > 0 &&
                           stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections && (
                            <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200">
                              <div className="text-xs text-indigo-700 mb-2 flex items-center gap-1">
                                Recovery Projections to Peak
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                    <div className="font-semibold mb-1">Trajectory Projections</div>
                                    <div className="mb-2">Estimated months to reach peak value based on current trend analysis.</div>
                                    <div className="mb-1"><strong>Realistic:</strong> Mean projection based on linear regression</div>
                                    <div className="mb-1"><strong>Optimistic:</strong> Upper bound (faster recovery)</div>
                                    <div className="mb-1"><strong>Pessimistic:</strong> Lower bound (slower recovery)</div>
                                    <div className="text-yellow-300 mt-2">Based on last 6 months trend</div>
                                  </TooltipContent>
                                </UITooltip>
                              </div>
                              <div className="grid grid-cols-3 gap-2 text-xs">
                                <div className="text-center">
                                  <div className="text-indigo-600 font-medium">Optimistic</div>
                                  <div className="text-lg font-bold text-indigo-800">
                                    {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.optimistic_months 
                                      ? `${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.optimistic_months.toFixed(1)} mo`
                                      : 'N/A'}
                                  </div>
                                </div>
                                <div className="text-center">
                                  <div className="text-indigo-600 font-medium">Realistic</div>
                                  <div className="text-lg font-bold text-indigo-800">
                                    {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.realistic_months 
                                      ? `${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.realistic_months.toFixed(1)} mo`
                                      : 'N/A'}
                                  </div>
                                </div>
                                <div className="text-center">
                                  <div className="text-indigo-600 font-medium">Pessimistic</div>
                                  <div className="text-lg font-bold text-indigo-800">
                                    {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.pessimistic_months 
                                      ? `${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.pessimistic_months.toFixed(1)} mo`
                                      : 'N/A'}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                          {/* Show message when portfolio already recovered above peak */}
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct <= 0 && (
                            <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                              <div className="text-xs text-green-700 flex items-center gap-2">
                                <CheckCircle className="h-4 w-4" />
                                <span>Portfolio has already recovered above pre-crisis peak. Recovery projections are not applicable.</span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Correlation Breakdown */}
                        {stressTestResults.scenarios['2008_crisis'].metrics.correlation_breakdown && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium">Correlation Breakdown</div>
                            <div className="grid grid-cols-3 gap-4">
                              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                                <div className="text-xs text-blue-700 mb-1">Crisis Correlation</div>
                                <div className="text-lg font-bold text-blue-800">
                                  {stressTestResults.scenarios['2008_crisis'].metrics.correlation_breakdown.crisis_correlation.toFixed(2)}
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-gray-50 border border-gray-200">
                                <div className="text-xs text-gray-700 mb-1">Normal Correlation</div>
                                <div className="text-lg font-bold text-gray-800">
                                  {stressTestResults.scenarios['2008_crisis'].metrics.correlation_breakdown.normal_correlation.toFixed(2)}
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                                <div className="text-xs text-red-700 mb-1">Diversification Effectiveness</div>
                                <div className="text-lg font-bold text-red-800">
                                  {stressTestResults.scenarios['2008_crisis'].metrics.correlation_breakdown.diversification_effectiveness.toFixed(0)}/100
                                </div>
                              </div>
                            </div>
                            <p className="text-xs text-gray-600">
                              Higher correlation during crisis ({stressTestResults.scenarios['2008_crisis'].metrics.correlation_breakdown.correlation_increase.toFixed(2)} increase) 
                              indicates diversification breakdown - assets moved together during crisis.
                            </p>
                          </div>
                        )}

                        {/* Portfolio Value Timeline Chart */}
                        {stressTestResults.scenarios['2008_crisis'].monthly_performance && 
                         stressTestResults.scenarios['2008_crisis'].monthly_performance.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-center">Portfolio Value Over Time</div>
                            <div className="h-64 w-full -ml-4">
                              <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart 
                                  data={(() => {
                                    const baseData = stressTestResults.scenarios['2008_crisis'].monthly_performance.map((m: any) => ({
                                      date: m.month,
                                      value: (m.value || 0) * 100,
                                      return: (m.return || 0) * 100,
                                      optimistic: null,
                                      realistic: null,
                                      pessimistic: null
                                    }));
                                    
                                    // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.peak) {
                                      const peakDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.date || '';
                                      const peakDate = peakDateFull.length >= 7 ? peakDateFull.substring(0, 7) : peakDateFull;
                                      if (peakDate && !baseData.find((d: any) => d.date === peakDate)) {
                                        const peakValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.value || 0) * 100;
                                        baseData.push({ date: peakDate, value: peakValue, return: null, optimistic: null, realistic: null, pessimistic: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.trough) {
                                      const troughDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.date || '';
                                      const troughDate = troughDateFull.length >= 7 ? troughDateFull.substring(0, 7) : troughDateFull;
                                      if (troughDate && !baseData.find((d: any) => d.date === troughDate)) {
                                        const troughValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.value || 0) * 100;
                                        baseData.push({ date: troughDate, value: troughValue, return: null, optimistic: null, realistic: null, pessimistic: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    // Add trajectory data if available
                                    if (stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.trajectory_data &&
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.length > 0) {
                                      const lastDate = baseData[baseData.length - 1]?.date;
                                      if (lastDate) {
                                        const [year, month] = lastDate.split('-').map(Number);
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.forEach((point: any, idx: number) => {
                                          const futureMonth = month + idx + 1;
                                          const futureYear = year + Math.floor((futureMonth - 1) / 12);
                                          const futureMonthNormalized = ((futureMonth - 1) % 12) + 1;
                                          const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, '0')}`;
                                          
                                          baseData.push({
                                            date: futureDate,
                                            value: null,
                                            return: null,
                                            optimistic: (point.optimistic || 0) * 100,
                                            realistic: (point.realistic || 0) * 100,
                                            pessimistic: (point.pessimistic || 0) * 100
                                          });
                                        });
                                      }
                                    }
                                    
                                    return baseData;
                                  })()}
                                  margin={{ left: 10, right: 10, top: 10, bottom: 10 }}
                                >
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis 
                                    dataKey="date" 
                                    tick={{ fontSize: 10 }}
                                    label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
                                  />
                                  <YAxis 
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                                    label={{ value: 'Portfolio Value (%)', angle: -90, position: 'left', offset: 0, style: { textAnchor: 'middle' } }}
                                    domain={['dataMin', 'dataMax']}
                                    width={70}
                                  />
                                  <Tooltip 
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Portfolio Value']}
                                    labelFormatter={(label) => `Month: ${label}`}
                                  />
                                  <Area 
                                    type="monotone" 
                                    dataKey="value" 
                                    stroke="#f59e0b" 
                                    fill="#f59e0b" 
                                    fillOpacity={0.2}
                                  />
                                  {/* Recovery Threshold Lines - Only show if significant drawdown */}
                                  {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                                   stressTestResults.scenarios['2008_crisis'].peaks_troughs?.peak && (() => {
                                    const peakValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.value || 0) * 100;
                                    const recoveryThresholds = stressTestResults.scenarios['2008_crisis'].metrics.recovery_thresholds || {};
                                    return (
                                      <>
                                        {/* 90% Recovery Threshold (10% below peak) */}
                                        {recoveryThresholds['90'] && (
                                          <ReferenceLine 
                                            y={peakValue * 0.90}
                                            stroke="#fbbf24"
                                            strokeDasharray="3 3"
                                            strokeWidth={1.5}
                                            label={{ value: '90% Recovery', position: 'right', fill: '#fbbf24', fontSize: 9 }}
                                          />
                                        )}
                                        {/* 95% Recovery Threshold (5% below peak - standard) */}
                                        {recoveryThresholds['95'] && (
                                          <ReferenceLine 
                                            y={peakValue * 0.95}
                                            stroke="#10b981"
                                            strokeDasharray="3 3"
                                            strokeWidth={2}
                                            label={{ value: '95% Recovery', position: 'right', fill: '#10b981', fontSize: 9, fontWeight: 'bold' }}
                                          />
                                        )}
                                        {/* 100% Recovery Threshold (Peak - Full Recovery Target) */}
                                        {recoveryThresholds['100'] && (
                                          <ReferenceLine 
                                            y={peakValue}
                                            stroke="#3b82f6"
                                            strokeDasharray="5 5"
                                            strokeWidth={2.5}
                                            label={{ value: 'Peak (100%)', position: 'right', fill: '#3b82f6', fontSize: 10, fontWeight: 'bold' }}
                                          />
                                        )}
                                      </>
                                    );
                                  })()}
                                  {/* Trajectory Projection Lines */}
                                  {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                                   stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.trajectory_data &&
                                   stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.length > 0 && (
                                    <>
                                      {/* Optimistic Trajectory */}
                                      <Line 
                                        dataKey="optimistic" 
                                        stroke="#22c55e"
                                        strokeDasharray="4 4"
                                        strokeWidth={1.5}
                                        dot={false}
                                        connectNulls={false}
                                        isAnimationActive={false}
                                        name="Optimistic"
                                      />
                                      {/* Realistic Trajectory */}
                                      <Line 
                                        dataKey="realistic" 
                                        stroke="#3b82f6"
                                        strokeDasharray="4 4"
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls={false}
                                        isAnimationActive={false}
                                        name="Realistic"
                                      />
                                      {/* Pessimistic Trajectory */}
                                      <Line 
                                        dataKey="pessimistic" 
                                        stroke="#f59e0b"
                                        strokeDasharray="4 4"
                                        strokeWidth={1.5}
                                        dot={false}
                                        connectNulls={false}
                                        isAnimationActive={false}
                                        name="Pessimistic"
                                      />
                                    </>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs?.peak && (() => {
                                    // Handle different date formats: YYYY-MM-DD or YYYY-MM
                                    const peakDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.date || '';
                                    const peakDate = peakDateFull.length >= 7 ? peakDateFull.substring(0, 7) : peakDateFull;
                                    const peakValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.value || 0) * 100;
                                    
                                    // Always render peak marker
                                    return (
                                      <ReferenceDot 
                                        x={peakDate} 
                                        y={peakValue}
                                        r={8}
                                        fill="#22c55e"
                                        stroke="#fff"
                                        strokeWidth={2}
                                        label={{ value: `Peak (${peakValue.toFixed(1)}%)`, position: 'top', fill: '#22c55e', fontSize: 10 }}
                                      />
                                    );
                                  })()}
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs?.trough && (() => {
                                    // Handle different date formats: YYYY-MM-DD or YYYY-MM
                                    const troughDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.date || '';
                                    const troughDate = troughDateFull.length >= 7 ? troughDateFull.substring(0, 7) : troughDateFull;
                                    const troughValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.value || 0) * 100;
                                    
                                    // Always render trough marker
                                    return (
                                      <ReferenceDot 
                                        x={troughDate} 
                                        y={troughValue}
                                        r={8}
                                        fill="#ef4444"
                                        stroke="#fff"
                                        strokeWidth={2}
                                        label={{ value: `Trough (${troughValue.toFixed(1)}%)`, position: 'bottom', fill: '#ef4444', fontSize: 10 }}
                                      />
                                    );
                                  })()}
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs?.recovery_peak && (() => {
                                    // Handle different date formats: YYYY-MM-DD or YYYY-MM
                                    const recoveryDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date || '';
                                    const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                    const recoveryValue = (stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.value || 0) * 100;
                                    
                                    // Always render recovery peak marker
                                    return (
                                      <ReferenceDot 
                                        x={recoveryDate} 
                                        y={recoveryValue}
                                        r={8}
                                        fill="#10b981"
                                        stroke="#fff"
                                        strokeWidth={2}
                                        label={{ value: `Recovery (${recoveryValue.toFixed(1)}%)`, position: 'top', fill: '#10b981', fontSize: 10 }}
                                      />
                                    );
                                  })()}
                                </ComposedChart>
                              </ResponsiveContainer>
                            </div>
                            {stressTestResults.scenarios['2008_crisis'].peaks_troughs && (
                              <div className="flex items-center gap-4 text-xs">
                                {stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                    <span>Peak ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                                {stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                    <span>Trough ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                                {stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak && (
                                  <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                                    <span>Recovery Peak ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date?.substring(0, 7) || 'N/A'})</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Sector Impact */}
                        {stressTestResults.scenarios['2008_crisis'].sector_impact && 
                         stressTestResults.scenarios['2008_crisis'].sector_impact.sector_returns &&
                         Object.keys(stressTestResults.scenarios['2008_crisis'].sector_impact.sector_returns).length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium">Sector Performance During Crisis</div>
                            <div className="h-48 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={Object.entries(stressTestResults.scenarios['2008_crisis'].sector_impact.sector_returns).map(([sector, return_pct]: [string, any]) => ({
                                  sector: sector.length > 15 ? sector.substring(0, 15) + '...' : sector,
                                  return: return_pct * 100
                                }))}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis 
                                    dataKey="sector" 
                                    tick={{ fontSize: 10 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={80}
                                  />
                                  <YAxis 
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                                  />
                                  <Tooltip 
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Return']}
                                  />
                                  <Bar 
                                    dataKey="return" 
                                    fill={(entry: any) => entry.return >= 0 ? '#22c55e' : '#ef4444'}
                                  />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}

                        {/* Detailed Metrics Table */}
                        <div className="space-y-2">
                          <div className="text-sm font-medium">Detailed Metrics</div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs border-collapse">
                              <thead>
                                <tr className="border-b">
                                  <th className="text-left py-2 px-2">Metric</th>
                                  <th className="text-right py-2 px-2">Value</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr className="border-b">
                                  <td className="py-2 px-2">Worst Month Return</td>
                                  <td className="text-right py-2 px-2 text-red-700 font-medium">
                                    {((stressTestResults.scenarios['2008_crisis'].metrics.worst_month_return || 0) * 100).toFixed(1)}%
                                  </td>
                                </tr>
                                <tr className="border-b">
                                  <td className="py-2 px-2">Volatility During Crisis</td>
                                  <td className="text-right py-2 px-2">
                                    {((stressTestResults.scenarios['2008_crisis'].metrics.volatility_during_crisis || 0) * 100).toFixed(1)}%
                                  </td>
                                </tr>
                                <tr className="border-b">
                                  <td className="py-2 px-2">Volatility Ratio (vs Normal)</td>
                                  <td className="text-right py-2 px-2">
                                    {(stressTestResults.scenarios['2008_crisis'].metrics.volatility_ratio || 1.0).toFixed(2)}x
                                  </td>
                                </tr>
                                <tr>
                                  <td className="py-2 px-2">Recovery Date</td>
                                  <td className="text-right py-2 px-2">
                                    {stressTestResults.scenarios['2008_crisis'].metrics.recovery_date || 'Not recovered'}
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  
                  {/* Advanced Risk Metrics */}
                  {stressTestResults.scenarios[selectedScenario || 'covid19']?.metrics?.advanced_risk && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Activity className="h-5 w-5 text-purple-600" />
                          Advanced Risk Metrics
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                          <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                            <div className="text-xs text-red-700 mb-1 flex items-center gap-1">
                              VaR (95%)
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-red-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-56 p-2 bg-gray-900 text-white text-xs border-0">
                                  Value at Risk: The maximum expected loss at 95% confidence level. Represents the 5% worst-case scenario return.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-red-800">
                              {(stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.advanced_risk.var_95 * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-red-600 mt-1">5% worst case</div>
                          </div>
                          <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                            <div className="text-xs text-orange-700 mb-1 flex items-center gap-1">
                              CVaR (95%)
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-orange-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-56 p-2 bg-gray-900 text-white text-xs border-0">
                                  Conditional Value at Risk: Expected loss beyond VaR threshold. Average of losses in the worst 5% of scenarios.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-orange-800">
                              {(stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.advanced_risk.cvar_95 * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-orange-600 mt-1">Expected tail loss</div>
                          </div>
                          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="text-xs text-blue-700 mb-1 flex items-center gap-1">
                              Beta
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-blue-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-56 p-2 bg-gray-900 text-white text-xs border-0">
                                  Beta measures portfolio sensitivity to market movements. 1.0 = moves with market, &gt;1.0 = more volatile, &lt;1.0 = less volatile.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-blue-800">
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.advanced_risk.beta.toFixed(2)}
                            </div>
                            <div className="text-xs text-blue-600 mt-1">Market correlation</div>
                          </div>
                          <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                            <div className="text-xs text-purple-700 mb-1 flex items-center gap-1">
                              Tail Risk
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-purple-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-56 p-2 bg-gray-900 text-white text-xs border-0">
                                  Probability of extreme losses beyond 2 standard deviations. Higher percentage indicates greater risk of severe losses.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-purple-800">
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.advanced_risk.tail_risk.toFixed(1)}%
                            </div>
                            <div className="text-xs text-purple-600 mt-1">Extreme loss prob</div>
                          </div>
                          <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200">
                            <div className="text-xs text-indigo-700 mb-1 flex items-center gap-1">
                              Downside Dev
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-56 p-2 bg-gray-900 text-white text-xs border-0">
                                  Downside Deviation: Standard deviation of negative returns only. Measures volatility of losses, ignoring gains.
                                </TooltipContent>
                              </UITooltip>
                            </div>
                            <div className="text-lg font-bold text-indigo-800">
                              {(stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.advanced_risk.downside_deviation * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-indigo-600 mt-1">Negative volatility</div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>
                
                {/* Comparison Tab */}
                <TabsContent value="comparison" className="space-y-6 mt-6">
                  {showComparison && Object.keys(stressTestResults.scenarios).length >= 2 && (
                    <div className="space-y-6">
                      {/* Side-by-Side Comparison Table */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg flex items-center gap-2">
                            <GitCompare className="h-5 w-5 text-blue-600" />
                            Scenario Comparison
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b">
                                  <th className="text-left py-3 px-4">Metric</th>
                                  {stressTestResults.scenarios.covid19 && (
                                    <th className="text-center py-3 px-4 bg-blue-50">COVID-19</th>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <th className="text-center py-3 px-4 bg-amber-50">2008 Crisis</th>
                                  )}
                                </tr>
                              </thead>
                              <tbody>
                                <tr className="border-b">
                                  <td className="py-3 px-4 font-medium">Total Return</td>
                                  {stressTestResults.scenarios.covid19 && (
                                    <td className="text-center py-3 px-4">
                                      <span className={`font-bold ${stressTestResults.scenarios.covid19.metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {(stressTestResults.scenarios.covid19.metrics.total_return * 100).toFixed(1)}%
                                      </span>
                                    </td>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <td className="text-center py-3 px-4">
                                      <span className={`font-bold ${stressTestResults.scenarios['2008_crisis'].metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {(stressTestResults.scenarios['2008_crisis'].metrics.total_return * 100).toFixed(1)}%
                                      </span>
                                    </td>
                                  )}
                                </tr>
                                <tr className="border-b">
                                  <td className="py-3 px-4 font-medium">Max Drawdown</td>
                                  {stressTestResults.scenarios.covid19 && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold text-red-600">
                                        {(stressTestResults.scenarios.covid19.metrics.max_drawdown * 100).toFixed(1)}%
                                      </span>
                                    </td>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold text-red-600">
                                        {(stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown * 100).toFixed(1)}%
                                      </span>
                                    </td>
                                  )}
                                </tr>
                                <tr className="border-b">
                                  <td className="py-3 px-4 font-medium">Recovery Time</td>
                                  {stressTestResults.scenarios.covid19 && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold">
                                        {stressTestResults.scenarios.covid19.metrics.recovery_months || 'N/A'} {stressTestResults.scenarios.covid19.metrics.recovery_months ? 'months' : ''}
                                      </span>
                                    </td>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold">
                                        {stressTestResults.scenarios['2008_crisis'].metrics.recovery_months || 'N/A'} {stressTestResults.scenarios['2008_crisis'].metrics.recovery_months ? 'months' : ''}
                                      </span>
                                    </td>
                                  )}
                                </tr>
                                <tr className="border-b">
                                  <td className="py-3 px-4 font-medium">Recovery Pattern</td>
                                  {stressTestResults.scenarios.covid19 && (
                                    <td className="text-center py-3 px-4">
                                      <Badge variant="outline">{stressTestResults.scenarios.covid19.metrics.recovery_pattern}</Badge>
                                    </td>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <td className="text-center py-3 px-4">
                                      <Badge variant="outline">{stressTestResults.scenarios['2008_crisis'].metrics.recovery_pattern}</Badge>
                                    </td>
                                  )}
                                </tr>
                                <tr>
                                  <td className="py-3 px-4 font-medium">Volatility Ratio</td>
                                  {stressTestResults.scenarios.covid19 && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold">
                                        {stressTestResults.scenarios.covid19.metrics.volatility_ratio.toFixed(2)}x
                                      </span>
                                    </td>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'] && (
                                    <td className="text-center py-3 px-4">
                                      <span className="font-bold">
                                        {stressTestResults.scenarios['2008_crisis'].metrics.volatility_ratio.toFixed(2)}x
                                      </span>
                                    </td>
                                  )}
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Side-by-Side Charts */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {stressTestResults.scenarios.covid19 && stressTestResults.scenarios.covid19.monthly_performance && stressTestResults.scenarios.covid19.monthly_performance.length > 0 && (
                          <Card>
                            <CardHeader>
                              <CardTitle className="text-sm">COVID-19 Portfolio Value</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="h-64 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <AreaChart data={stressTestResults.scenarios.covid19.monthly_performance.map((m: any) => ({
                                    date: m.month,
                                    value: (m.value || 0) * 100
                                  }))}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                                    <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`, 'Value']} />
                                    <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
                                  </AreaChart>
                                </ResponsiveContainer>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                        {stressTestResults.scenarios['2008_crisis'] && stressTestResults.scenarios['2008_crisis'].monthly_performance && stressTestResults.scenarios['2008_crisis'].monthly_performance.length > 0 && (
                          <Card>
                            <CardHeader>
                              <CardTitle className="text-sm">2008 Crisis Portfolio Value</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="h-64 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <AreaChart data={stressTestResults.scenarios['2008_crisis'].monthly_performance.map((m: any) => ({
                                    date: m.month,
                                    value: (m.value || 0) * 100
                                  }))}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                                    <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`, 'Value']} />
                                    <Area type="monotone" dataKey="value" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} />
                                  </AreaChart>
                                </ResponsiveContainer>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </div>
                  )}
                  {(!showComparison || Object.keys(stressTestResults.scenarios).length < 2) && (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        Enable comparison mode and run both scenarios to see side-by-side comparison.
                      </AlertDescription>
                    </Alert>
                  )}
                </TabsContent>
                
                {/* Monte Carlo Tab */}
                <TabsContent value="monte-carlo" className="space-y-6 mt-6">
                  {stressTestResults.scenarios[selectedScenario || 'covid19']?.monte_carlo ? (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <BarChart3 className="h-5 w-5 text-blue-600" />
                          Monte Carlo Simulation Results
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          Probabilistic analysis showing range of possible outcomes (10,000 simulations)
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        {/* Histogram */}
                        {stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.histogram_data && 
                         stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.histogram_data.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium">Return Distribution</div>
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.histogram_data.map((h: any) => ({
                                  return: h.return_pct,
                                  frequency: h.frequency
                                }))}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis 
                                    dataKey="return" 
                                    tick={{ fontSize: 10 }}
                                    label={{ value: 'Return (%)', position: 'insideBottom', offset: -5 }}
                                  />
                                  <YAxis 
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(1)}%`}
                                    label={{ value: 'Frequency (%)', angle: -90, position: 'insideLeft' }}
                                  />
                                  <Tooltip 
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Frequency']}
                                    labelFormatter={(label) => `Return: ${label}%`}
                                  />
                                  <Bar dataKey="frequency" fill="#3b82f6" fillOpacity={0.7} />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}
                        
                        {/* Percentiles */}
                        {stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles && (
                          <div className="grid grid-cols-5 gap-3">
                            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                              <div className="text-xs text-red-700 mb-1">5th Percentile</div>
                              <div className="text-lg font-bold text-red-800">
                                {(stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles.p5 * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-orange-50 border border-orange-200 text-center">
                              <div className="text-xs text-orange-700 mb-1">25th Percentile</div>
                              <div className="text-lg font-bold text-orange-800">
                                {(stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles.p25 * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-center">
                              <div className="text-xs text-blue-700 mb-1">Median (50th)</div>
                              <div className="text-lg font-bold text-blue-800">
                                {(stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles.p50 * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                              <div className="text-xs text-green-700 mb-1">75th Percentile</div>
                              <div className="text-lg font-bold text-green-800">
                                {(stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles.p75 * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-purple-50 border border-purple-200 text-center">
                              <div className="text-xs text-purple-700 mb-1">95th Percentile</div>
                              <div className="text-lg font-bold text-purple-800">
                                {(stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.percentiles.p95 * 100).toFixed(1)}%
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Probability Statements */}
                        {stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.probability_statements && (
                          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="text-sm font-semibold mb-2">Key Insights</div>
                            <ul className="space-y-1 text-sm">
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.probability_statements.map((stmt: string, idx: number) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <CheckCircle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                                  <span>{stmt}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        Monte Carlo simulation results are not available for the selected scenario. Run a stress test to generate probabilistic analysis.
                      </AlertDescription>
                    </Alert>
                  )}
                </TabsContent>
                
                {/* What-If Tab */}
                <TabsContent value="what-if" className="space-y-6 mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Zap className="h-5 w-5 text-yellow-600" />
                        What-If Scenario Simulator
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Test custom scenarios by adjusting market parameters
                      </p>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Parameter Controls */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Volatility Multiplier</label>
                          <input
                            type="number"
                            min="0.5"
                            max="5"
                            step="0.1"
                            value={whatIfParams.volatility_multiplier}
                            onChange={(e) => setWhatIfParams({...whatIfParams, volatility_multiplier: parseFloat(e.target.value) || 2.0})}
                            className="w-full px-3 py-2 border rounded-md"
                          />
                          <p className="text-xs text-muted-foreground">
                            {whatIfParams.volatility_multiplier}x normal volatility
                          </p>
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Return Adjustment (%)</label>
                          <input
                            type="number"
                            min="-50"
                            max="50"
                            step="1"
                            value={whatIfParams.return_adjustment * 100}
                            onChange={(e) => setWhatIfParams({...whatIfParams, return_adjustment: (parseFloat(e.target.value) || 0) / 100})}
                            className="w-full px-3 py-2 border rounded-md"
                          />
                          <p className="text-xs text-muted-foreground">
                            {whatIfParams.return_adjustment >= 0 ? '+' : ''}{(whatIfParams.return_adjustment * 100).toFixed(1)}% annual return
                          </p>
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Time Horizon (months)</label>
                          <input
                            type="number"
                            min="1"
                            max="60"
                            step="1"
                            value={whatIfParams.time_horizon_months}
                            onChange={(e) => setWhatIfParams({...whatIfParams, time_horizon_months: parseInt(e.target.value) || 12})}
                            className="w-full px-3 py-2 border rounded-md"
                          />
                          <p className="text-xs text-muted-foreground">
                            {whatIfParams.time_horizon_months} month{whatIfParams.time_horizon_months !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      
                      <Button
                        onClick={async () => {
                          if (!selectedPortfolio) {
                            setError('Please select a portfolio first');
                            return;
                          }
                          setWhatIfLoading(true);
                          setError(null);
                          try {
                            const response = await fetch('/api/portfolio/what-if-scenario', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                tickers: selectedPortfolio.tickers,
                                weights: selectedPortfolio.weights,
                                volatility_multiplier: whatIfParams.volatility_multiplier,
                                return_adjustment: whatIfParams.return_adjustment,
                                time_horizon_months: whatIfParams.time_horizon_months,
                                capital: capital
                              })
                            });
                            if (!response.ok) {
                              const errorData = await response.json();
                              throw new Error(errorData.detail || 'Failed to run What-If scenario');
                            }
                            const data = await response.json();
                            setWhatIfResults(data);
                          } catch (err: any) {
                            setError(err.message || 'Failed to run What-If scenario');
                          } finally {
                            setWhatIfLoading(false);
                          }
                        }}
                        disabled={whatIfLoading || !selectedPortfolio}
                        className="w-full bg-gradient-primary hover:opacity-90"
                      >
                        {whatIfLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Running Simulation...
                          </>
                        ) : (
                          <>
                            <Zap className="mr-2 h-4 w-4" />
                            Run What-If Simulation
                          </>
                        )}
                      </Button>
                      
                      {/* Results */}
                      {whatIfResults && (
                        <div className="space-y-6 mt-6 pt-6 border-t">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                              <div className="text-sm text-blue-700 mb-1">Adjusted Expected Return</div>
                              <div className="text-2xl font-bold text-blue-800">
                                {(whatIfResults.metrics.expected_return * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-blue-600 mt-1">
                                Baseline: {(whatIfResults.metrics.baseline_expected_return * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                              <div className="text-sm text-red-700 mb-1">Adjusted Volatility</div>
                              <div className="text-2xl font-bold text-red-800">
                                {(whatIfResults.metrics.volatility * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-red-600 mt-1">
                                Baseline: {(whatIfResults.metrics.baseline_volatility * 100).toFixed(1)}%
                              </div>
                            </div>
                          </div>
                          
                          {/* Monte Carlo Histogram */}
                          {whatIfResults.monte_carlo && whatIfResults.monte_carlo.histogram_data && (
                            <div className="space-y-2">
                              <div className="text-sm font-medium">Return Distribution</div>
                              <div className="h-64 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart data={whatIfResults.monte_carlo.histogram_data.map((h: any) => ({
                                    return: h.return_pct,
                                    frequency: h.frequency
                                  }))}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis 
                                      dataKey="return" 
                                      tick={{ fontSize: 10 }}
                                      label={{ value: 'Return (%)', position: 'insideBottom', offset: -5 }}
                                    />
                                    <YAxis 
                                      tick={{ fontSize: 10 }}
                                      tickFormatter={(value) => `${value.toFixed(1)}%`}
                                      label={{ value: 'Frequency (%)', angle: -90, position: 'insideLeft' }}
                                    />
                                    <Tooltip 
                                      formatter={(value: number) => [`${value.toFixed(1)}%`, 'Frequency']}
                                      labelFormatter={(label) => `Return: ${label}%`}
                                    />
                                    <Bar dataKey="frequency" fill="#f59e0b" fillOpacity={0.7} />
                                  </BarChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}
                          
                          {/* Percentiles */}
                          {whatIfResults.monte_carlo && whatIfResults.monte_carlo.percentiles && (
                            <div className="grid grid-cols-5 gap-3">
                              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                                <div className="text-xs text-red-700 mb-1">5th Percentile</div>
                                <div className="text-lg font-bold text-red-800">
                                  {(whatIfResults.monte_carlo.percentiles.p5 * 100).toFixed(1)}%
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-orange-50 border border-orange-200 text-center">
                                <div className="text-xs text-orange-700 mb-1">25th Percentile</div>
                                <div className="text-lg font-bold text-orange-800">
                                  {(whatIfResults.monte_carlo.percentiles.p25 * 100).toFixed(1)}%
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-center">
                                <div className="text-xs text-blue-700 mb-1">Median (50th)</div>
                                <div className="text-lg font-bold text-blue-800">
                                  {(whatIfResults.monte_carlo.percentiles.p50 * 100).toFixed(1)}%
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                                <div className="text-xs text-green-700 mb-1">75th Percentile</div>
                                <div className="text-lg font-bold text-green-800">
                                  {(whatIfResults.monte_carlo.percentiles.p75 * 100).toFixed(1)}%
                                </div>
                              </div>
                              <div className="p-3 rounded-lg bg-purple-50 border border-purple-200 text-center">
                                <div className="text-xs text-purple-700 mb-1">95th Percentile</div>
                                <div className="text-lg font-bold text-purple-800">
                                  {(whatIfResults.monte_carlo.percentiles.p95 * 100).toFixed(1)}%
                                </div>
                              </div>
                            </div>
                          )}
                          
                          {/* Probability Statements */}
                          {whatIfResults.monte_carlo && (
                            <div className="space-y-3">
                              <div className="text-sm font-medium">Probability Analysis</div>
                              <div className="grid grid-cols-3 gap-3">
                                <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                                  <div className="text-xs text-green-700 mb-1">Probability of Positive Return</div>
                                  <div className="text-xl font-bold text-green-800">
                                    {typeof whatIfResults.metrics.probability_positive === 'number' 
                                      ? (whatIfResults.metrics.probability_positive > 1 
                                          ? whatIfResults.metrics.probability_positive.toFixed(1) 
                                          : (whatIfResults.metrics.probability_positive * 100).toFixed(1)
                                        ) + '%'
                                      : 'N/A'}
                                  </div>
                                  {/* Note: probability_positive is already a percentage (0-100) from backend */}
                                </div>
                                <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                                  <div className="text-xs text-orange-700 mb-1">Probability of &gt;10% Loss</div>
                                  <div className="text-xl font-bold text-orange-800">
                                    {(whatIfResults.metrics.probability_loss_10pct * 100).toFixed(1)}%
                                  </div>
                                </div>
                                <div className="p-3 rounded-lg bg-red-50 border border-red-200">
                                  <div className="text-xs text-red-700 mb-1">Probability of &gt;20% Loss</div>
                                  <div className="text-xl font-bold text-red-800">
                                    {(whatIfResults.metrics.probability_loss_20pct * 100).toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
                
                {/* Interactive Timeline Tab */}
                <TabsContent value="timeline" className="space-y-6 mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-indigo-600" />
                        Interactive Crisis Timeline
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Key market events and their impact on your portfolio
                      </p>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Timeline Visualization */}
                      {stressTestResults.scenarios[selectedScenario || 'covid19']?.monthly_performance && (
                        <div className="space-y-4">
                          <div className="h-64 w-full -ml-4">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart 
                                data={(() => {
                                  // Normalize to match Portfolio Value Over Time graph (January 2020 = 100%)
                                  const jan2020Value = stressTestResults.scenarios[selectedScenario || 'covid19'].monthly_performance.find((m: any) => m.month === '2020-01')?.value || 
                                                       stressTestResults.scenarios[selectedScenario || 'covid19'].monthly_performance[0]?.value || 1.0;
                                  const normalizationFactor = 1.0 / jan2020Value;
                                  
                                  return stressTestResults.scenarios[selectedScenario || 'covid19'].monthly_performance.map((m: any) => ({
                                    date: m.month,
                                    value: ((m.value || 0) * normalizationFactor) * 100,
                                    return: (m.return || 0) * 100
                                  }));
                                })()}
                                margin={{ left: 10, right: 10, top: 40, bottom: 10 }}
                              >
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                                <YAxis 
                                  tick={{ fontSize: 10 }}
                                  tickFormatter={(value) => `${value.toFixed(0)}%`}
                                  label={{ value: 'Portfolio Value (%)', angle: -90, position: 'left', offset: 0, style: { textAnchor: 'middle' } }}
                                  domain={['dataMin', 'dataMax']}
                                  width={70}
                                />
                                <Tooltip 
                                  formatter={(value: number) => [`${value.toFixed(1)}%`, 'Value']}
                                  labelFormatter={(label) => `Month: ${label}`}
                                />
                                <Area 
                                  type="monotone" 
                                  dataKey="value" 
                                  stroke="#6366f1" 
                                  fill="#6366f1" 
                                  fillOpacity={0.2}
                                />
                                {/* Recovery Threshold Lines - Only show if significant drawdown and toggle is on */}
                                {showRecoveryThresholds &&
                                 stressTestResults.scenarios[selectedScenario || 'covid19']?.metrics?.max_drawdown_data?.is_significant && 
                                 stressTestResults.scenarios[selectedScenario || 'covid19']?.peaks_troughs?.peak && (() => {
                                  // Normalize peak value to match chart normalization (peak = 100%)
                                  const jan2020Value = stressTestResults.scenarios[selectedScenario || 'covid19'].monthly_performance.find((m: any) => m.month === '2020-01')?.value || 
                                                       stressTestResults.scenarios[selectedScenario || 'covid19'].monthly_performance[0]?.value || 1.0;
                                  const normalizationFactor = 1.0 / jan2020Value;
                                  const peakValue = 100.0; // Peak is always at 100% (normalized starting value)
                                  const recoveryThresholds = stressTestResults.scenarios[selectedScenario || 'covid19']?.metrics?.recovery_thresholds || {};
                                  return (
                                    <>
                                      {/* 90% Recovery Threshold (10% below peak) */}
                                      {recoveryThresholds['90'] && (
                                        <ReferenceLine 
                                          y={peakValue * 0.90}
                                          stroke="#fbbf24"
                                          strokeDasharray="3 3"
                                          strokeWidth={1.5}
                                          label={{ value: '90% Recovery', position: 'right', fill: '#fbbf24', fontSize: 9 }}
                                        />
                                      )}
                                      {/* 95% Recovery Threshold (5% below peak - standard) */}
                                      {recoveryThresholds['95'] && (
                                        <ReferenceLine 
                                          y={peakValue * 0.95}
                                          stroke="#10b981"
                                          strokeDasharray="3 3"
                                          strokeWidth={2}
                                          label={{ value: '95% Recovery', position: 'right', fill: '#10b981', fontSize: 9, fontWeight: 'bold' }}
                                        />
                                      )}
                                      {/* 98% Recovery Threshold (2% below peak - near full) */}
                                      {recoveryThresholds['98'] && (
                                        <ReferenceLine 
                                          y={peakValue * 0.98}
                                          stroke="#22c55e"
                                          strokeDasharray="3 3"
                                          strokeWidth={1.5}
                                          label={{ value: '98% Recovery', position: 'right', fill: '#22c55e', fontSize: 9 }}
                                        />
                                      )}
                                    </>
                                  );
                                })()}
                                {/* Event markers - Only show if event type is visible */}
                                {crisisEvents[selectedScenario as keyof typeof crisisEvents]?.map((event, idx) => {
                                  const isSelected = selectedTimelineEvent === event;
                                  const isVisible = 
                                    (event.type === 'crisis' && visibleEventTypes.crisis) ||
                                    (event.type === 'policy' && visibleEventTypes.policy) ||
                                    (event.type === 'recovery' && visibleEventTypes.recovery) ||
                                    ((event.type === 'warning' || event.type === 'bottom') && visibleEventTypes.warning);
                                  
                                  if (!isVisible) return null;
                                  
                                  return (
                                    <ReferenceLine 
                                      key={idx}
                                      x={event.date}
                                      stroke={event.type === 'crisis' ? '#ef4444' : event.type === 'policy' ? '#3b82f6' : event.type === 'recovery' ? '#22c55e' : '#f59e0b'}
                                      strokeDasharray={isSelected ? "3 3" : "5 5"}
                                      strokeWidth={isSelected ? 3 : 2}
                                      label={{ 
                                        value: event.event.substring(0, 20) + (event.event.length > 20 ? '...' : ''), 
                                        position: 'top', 
                                        offset: 5,
                                        fill: event.type === 'crisis' ? '#ef4444' : event.type === 'policy' ? '#3b82f6' : event.type === 'recovery' ? '#22c55e' : '#f59e0b', 
                                        fontSize: isSelected ? 9 : 8,
                                        fontWeight: isSelected ? 'bold' : 'normal',
                                        angle: 0
                                      }}
                                    />
                                  );
                                })}
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                          
                          {/* Interactive Legends */}
                          <div className="space-y-4">
                            {/* Recovery Thresholds Legend - Only show if significant drawdown */}
                            {stressTestResults.scenarios[selectedScenario || 'covid19']?.metrics?.max_drawdown_data?.is_significant && 
                             stressTestResults.scenarios[selectedScenario || 'covid19']?.metrics?.recovery_thresholds && (
                              <div className="p-3 rounded-lg bg-gray-50 border border-gray-200">
                                <div className="text-xs font-medium text-gray-700 mb-2 flex items-center justify-between">
                                  <div className="flex items-center gap-1">
                                    Recovery Thresholds
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <Info className="h-3 w-3 text-gray-500 cursor-help" />
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Recovery Thresholds</div>
                                        <div className="mb-2">Horizontal lines showing where portfolio needs to reach for different recovery levels.</div>
                                        <div className="mb-1"><strong>90%:</strong> 10% below peak (partial recovery)</div>
                                        <div className="mb-1"><strong>95%:</strong> 5% below peak (standard recovery)</div>
                                        <div className="mb-1"><strong>98%:</strong> 2% below peak (near full recovery)</div>
                                        <div className="text-yellow-300 mt-2">Only shown if drawdown exceeds 3% threshold</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  </div>
                                  <button
                                    onClick={() => setShowRecoveryThresholds(!showRecoveryThresholds)}
                                    className={`px-2 py-1 text-xs rounded border transition-colors ${
                                      showRecoveryThresholds 
                                        ? 'bg-green-100 border-green-300 text-green-700 hover:bg-green-200' 
                                        : 'bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200'
                                    }`}
                                  >
                                    {showRecoveryThresholds ? 'Hide' : 'Show'}
                                  </button>
                                </div>
                                <div className="grid grid-cols-3 gap-3 text-xs">
                                  {['90', '95', '98'].map((threshold) => {
                                    const thresholdData = stressTestResults.scenarios[selectedScenario || 'covid19'].metrics.recovery_thresholds[threshold];
                                    const colors = { '90': '#fbbf24', '95': '#10b981', '98': '#22c55e' };
                                    const color = colors[threshold as keyof typeof colors];
                                    
                                    return (
                                      <div 
                                        key={threshold}
                                        className={`flex items-center gap-2 p-2 rounded transition-opacity ${
                                          showRecoveryThresholds ? 'opacity-100' : 'opacity-50'
                                        }`}
                                        title={thresholdData?.recovered ? `Recovered in ${thresholdData.months} months` : `Not recovered (${thresholdData?.progress_pct?.toFixed(1) || 0}% progress)`}
                                      >
                                        <div className="w-4 h-0.5" style={{ backgroundColor: color }}></div>
                                        <div className="flex-1">
                                          <div className="font-medium" style={{ color }}>
                                            {threshold}% Recovery
                                          </div>
                                          <div className="text-gray-600 text-xs">
                                            {thresholdData?.recovered 
                                              ? `${thresholdData.months} months`
                                              : thresholdData?.progress_pct 
                                                ? `${thresholdData.progress_pct.toFixed(1)}% progress`
                                                : 'N/A'}
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                            
                            {/* Event Type Legend */}
                            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                              <div className="text-xs font-medium text-blue-700 mb-2">Key Events Timeline</div>
                              <div className="flex items-center justify-center gap-6 text-xs flex-wrap mb-3">
                                <button
                                  onClick={() => setVisibleEventTypes({...visibleEventTypes, crisis: !visibleEventTypes.crisis})}
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.crisis 
                                      ? 'bg-red-100 border border-red-300 text-red-700 hover:bg-red-200' 
                                      : 'bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50'
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-red-500"></div>
                                  <span>Crisis Event</span>
                                </button>
                                <button
                                  onClick={() => setVisibleEventTypes({...visibleEventTypes, policy: !visibleEventTypes.policy})}
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.policy 
                                      ? 'bg-blue-100 border border-blue-300 text-blue-700 hover:bg-blue-200' 
                                      : 'bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50'
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-blue-500"></div>
                                  <span>Policy Action</span>
                                </button>
                                <button
                                  onClick={() => setVisibleEventTypes({...visibleEventTypes, recovery: !visibleEventTypes.recovery})}
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.recovery 
                                      ? 'bg-green-100 border border-green-300 text-green-700 hover:bg-green-200' 
                                      : 'bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50'
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-green-500"></div>
                                  <span>Recovery</span>
                                </button>
                                <button
                                  onClick={() => setVisibleEventTypes({...visibleEventTypes, warning: !visibleEventTypes.warning})}
                                  className={`flex items-center gap-2 px-2 py-1 rounded transition-all ${
                                    visibleEventTypes.warning 
                                      ? 'bg-yellow-100 border border-yellow-300 text-yellow-700 hover:bg-yellow-200' 
                                      : 'bg-gray-100 border border-gray-300 text-gray-500 hover:bg-gray-200 opacity-50'
                                  }`}
                                >
                                  <div className="w-4 h-1 bg-yellow-500"></div>
                                  <span>Warning</span>
                                </button>
                              </div>
                              <div className="space-y-2">
                                {crisisEvents[selectedScenario as keyof typeof crisisEvents]?.map((event, idx) => (
                                  <div 
                                    key={idx}
                                    className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                                      event.type === 'crisis' ? 'bg-red-50 border-red-200 hover:bg-red-100' : 
                                      event.type === 'policy' ? 'bg-blue-50 border-blue-200 hover:bg-blue-100' : 
                                      event.type === 'recovery' ? 'bg-green-50 border-green-200 hover:bg-green-100' : 
                                      'bg-yellow-50 border-yellow-200 hover:bg-yellow-100'
                                    }`}
                                    onClick={() => setSelectedTimelineEvent(event)}
                                  >
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${
                                          event.type === 'crisis' ? 'bg-red-500' : 
                                          event.type === 'policy' ? 'bg-blue-500' : 
                                          event.type === 'recovery' ? 'bg-green-500' : 
                                          'bg-yellow-500'
                                        }`}></div>
                                        <span className="text-sm font-medium">{event.event}</span>
                                      </div>
                                      <span className="text-xs text-muted-foreground">{event.date}</span>
                                    </div>
                                    {selectedTimelineEvent === event && (
                                      <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-600">
                                        Click to view details on chart
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                          
                          {/* Peak/Trough Summary */}
                          {stressTestResults.scenarios[selectedScenario || 'covid19']?.peaks_troughs && (
                            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.peak && (
                                <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-center">
                                  <div className="text-xs text-green-700 mb-1">Peak</div>
                                  <div className="text-lg font-bold text-green-800">
                                    {(stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.peak.value * 100).toFixed(1)}%
                                  </div>
                                  <div className="text-xs text-green-600">
                                    {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.peak.date?.substring(0, 7)}
                                  </div>
                                </div>
                              )}
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.trough && (
                                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center">
                                  <div className="text-xs text-red-700 mb-1">Trough</div>
                                  <div className="text-lg font-bold text-red-800">
                                    {(stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.trough.value * 100).toFixed(1)}%
                                  </div>
                                  <div className="text-xs text-red-600">
                                    {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.trough.date?.substring(0, 7)}
                                  </div>
                                </div>
                              )}
                              {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.recovery_peak && (
                                <div className="p-3 rounded-lg border text-center" style={{ backgroundColor: '#faf5ff', borderColor: '#e9d5ff' }}>
                                  <div className="text-xs mb-1" style={{ color: '#9333ea' }}>Recovery Peak</div>
                                  <div className="text-lg font-bold" style={{ color: '#7e22ce' }}>
                                    {(stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.recovery_peak.value * 100).toFixed(1)}%
                                  </div>
                                  <div className="text-xs" style={{ color: '#a855f7' }}>
                                    {stressTestResults.scenarios[selectedScenario || 'covid19'].peaks_troughs.recovery_peak.date?.substring(0, 7)}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
                
                {/* Hypothetical Scenarios Tab */}
                <TabsContent value="hypothetical" className="space-y-6 mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                        Forward-Looking Stress Scenarios
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Test your portfolio against hypothetical market scenarios
                      </p>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Predefined Scenarios */}
                      <div className="space-y-4">
                        <div className="text-sm font-medium">Select Hypothetical Scenario</div>
                        <div className="grid grid-cols-2 gap-4">
                          <div 
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === 'tech_crash' 
                                ? 'border-purple-500 bg-purple-50' 
                                : 'border-gray-200 hover:border-purple-300'
                            }`}
                            onClick={() => setHypotheticalParams({...hypotheticalParams, scenario_type: 'tech_crash', market_decline: -40, sector_impact: 'technology'})}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <AlertCircle className="h-4 w-4 text-purple-600" />
                              <span className="font-medium">Tech Bubble Burst</span>
                            </div>
                            <p className="text-xs text-muted-foreground">40% tech sector crash with spillover to broader market</p>
                          </div>
                          
                          <div 
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === 'inflation' 
                                ? 'border-orange-500 bg-orange-50' 
                                : 'border-gray-200 hover:border-orange-300'
                            }`}
                            onClick={() => setHypotheticalParams({...hypotheticalParams, scenario_type: 'inflation', market_decline: -25, sector_impact: 'bonds'})}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingUp className="h-4 w-4 text-orange-600" />
                              <span className="font-medium">Inflation Shock</span>
                            </div>
                            <p className="text-xs text-muted-foreground">Sharp rate hikes causing bond crash and equity correction</p>
                          </div>
                          
                          <div 
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === 'geopolitical' 
                                ? 'border-red-500 bg-red-50' 
                                : 'border-gray-200 hover:border-red-300'
                            }`}
                            onClick={() => setHypotheticalParams({...hypotheticalParams, scenario_type: 'geopolitical', market_decline: -35, sector_impact: 'energy'})}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Shield className="h-4 w-4 text-red-600" />
                              <span className="font-medium">Geopolitical Crisis</span>
                            </div>
                            <p className="text-xs text-muted-foreground">Major conflict causing oil spike and global market selloff</p>
                          </div>
                          
                          <div 
                            className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                              hypotheticalParams.scenario_type === 'recession' 
                                ? 'border-gray-500 bg-gray-50' 
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => setHypotheticalParams({...hypotheticalParams, scenario_type: 'recession', market_decline: -30, sector_impact: 'cyclical'})}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingDown className="h-4 w-4 text-gray-600" />
                              <span className="font-medium">Deep Recession</span>
                            </div>
                            <p className="text-xs text-muted-foreground">Prolonged economic contraction with high unemployment</p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Custom Parameters */}
                      <div className="space-y-4 pt-4 border-t">
                        <div className="text-sm font-medium">Adjust Scenario Parameters</div>
                        <div className="grid grid-cols-3 gap-4">
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">Market Decline (%)</label>
                            <input
                              type="number"
                              min="-80"
                              max="0"
                              value={hypotheticalParams.market_decline}
                              onChange={(e) => setHypotheticalParams({...hypotheticalParams, market_decline: parseInt(e.target.value) || -30})}
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">Duration (months)</label>
                            <input
                              type="number"
                              min="1"
                              max="36"
                              value={hypotheticalParams.duration_months}
                              onChange={(e) => setHypotheticalParams({...hypotheticalParams, duration_months: parseInt(e.target.value) || 6})}
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">Recovery Rate</label>
                            <select
                              value={hypotheticalParams.recovery_rate}
                              onChange={(e) => setHypotheticalParams({...hypotheticalParams, recovery_rate: e.target.value})}
                              className="w-full px-3 py-2 border rounded-md text-sm"
                            >
                              <option value="slow">Slow (L-shaped)</option>
                              <option value="moderate">Moderate (U-shaped)</option>
                              <option value="fast">Fast (V-shaped)</option>
                            </select>
                          </div>
                        </div>
                      </div>
                      
                      {/* Run Simulation Button */}
                      <Button
                        onClick={async () => {
                          if (!selectedPortfolio) {
                            setError('Please select a portfolio first');
                            return;
                          }
                          setHypotheticalLoading(true);
                          setError(null);
                          try {
                            // Use what-if endpoint with scenario_type for backward compatibility
                            const response = await fetch('/api/portfolio/what-if-scenario', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                tickers: selectedPortfolio.tickers,
                                weights: selectedPortfolio.weights,
                                scenario_type: hypotheticalParams.scenario_type,
                                market_decline: hypotheticalParams.market_decline / 100,
                                duration_months: hypotheticalParams.duration_months,
                                recovery_rate: hypotheticalParams.recovery_rate,
                                capital: capital
                              })
                            });
                            if (!response.ok) {
                              const errorData = await response.json();
                              throw new Error(errorData.detail || 'Failed to run hypothetical scenario');
                            }
                            const data = await response.json();
                            setHypotheticalResults(data);
                          } catch (err: any) {
                            setError(err.message || 'Failed to run hypothetical scenario');
                          } finally {
                            setHypotheticalLoading(false);
                          }
                        }}
                        disabled={hypotheticalLoading || !selectedPortfolio}
                        className="w-full bg-gradient-primary hover:opacity-90"
                      >
                        {hypotheticalLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Running Scenario...
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="mr-2 h-4 w-4" />
                            Run Hypothetical Scenario
                          </>
                        )}
                      </Button>
                      
                      {/* Results */}
                      {hypotheticalResults && (
                        <div className="space-y-6 mt-6 pt-6 border-t">
                          <div className="grid grid-cols-3 gap-4">
                            <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                              <div className="text-sm text-red-700 mb-1">Estimated Loss</div>
                              <div className="text-2xl font-bold text-red-800">
                                {(hypotheticalResults.estimated_loss * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
                              <div className="text-sm text-blue-700 mb-1">Portfolio Impact</div>
                              <div className="text-2xl font-bold text-blue-800">
                                {hypotheticalResults.capital_at_risk ? hypotheticalResults.capital_at_risk.toLocaleString() : 'N/A'} SEK
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
                              <div className="text-sm text-amber-700 mb-1">Recovery Estimate</div>
                              <div className="text-2xl font-bold text-amber-800">
                                {hypotheticalResults.estimated_recovery_months || 'N/A'} months
                              </div>
                            </div>
                          </div>
                          
                          {/* Monte Carlo Distribution */}
                          {hypotheticalResults.monte_carlo && hypotheticalResults.monte_carlo.histogram_data && (
                            <div className="space-y-2">
                              <div className="text-sm font-medium">Outcome Distribution</div>
                              <div className="h-48 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart data={hypotheticalResults.monte_carlo.histogram_data.map((h: any) => ({
                                    return: h.return_pct,
                                    frequency: h.frequency
                                  }))}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis dataKey="return" tick={{ fontSize: 10 }} />
                                    <YAxis tick={{ fontSize: 10 }} />
                                    <Tooltip />
                                    <Bar dataKey="frequency" fill="#f59e0b" fillOpacity={0.7} />
                                  </BarChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}
                          
                          {/* Sector Impact Analysis */}
                          {hypotheticalResults.sector_impact && (
                            <div className="space-y-2">
                              <div className="text-sm font-medium">Sector Impact Analysis</div>
                              <div className="grid grid-cols-2 gap-4">
                                {Object.entries(hypotheticalResults.sector_impact).map(([sector, impact]: [string, any]) => (
                                  <div key={sector} className="p-3 rounded-lg bg-gray-50 border">
                                    <div className="flex items-center justify-between">
                                      <span className="text-sm font-medium">{sector}</span>
                                      <span className={`text-sm font-bold ${impact < 0 ? 'text-red-600' : 'text-green-600'}`}>
                                        {(impact * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-6 border-t">
            <Button variant="outline" onClick={onPrev}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <div className="flex gap-2">
              {stressTestResults && (
                <Button variant="outline" onClick={() => {
                  setStressTestResults(null);
                  setSelectedScenario('covid19');
                  setError(null);
                }}>
                  Run Again
                </Button>
              )}
              <Button 
                onClick={onNext}
                className="bg-gradient-primary hover:opacity-90"
              >
                {stressTestResults ? 'Complete & Proceed' : 'Skip Stress Test'}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
