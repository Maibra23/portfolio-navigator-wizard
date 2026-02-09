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
  Calendar,
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
  const [hypotheticalParams, setHypotheticalParams] = useState({
    scenario_type: 'tech_crash',
    market_decline: -30,
    sector_impact: 'technology',
    duration_months: 6,
    recovery_rate: 'moderate'
  });
  const [hypotheticalResults, setHypotheticalResults] = useState<any>(null);
  const [hypotheticalLoading, setHypotheticalLoading] = useState(false);
  const [activeView, setActiveView] = useState<'overview' | 'timeline' | 'monte-carlo' | 'hypothetical'>('overview');
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
  // Keep Stress Test focused on 4 tabs: Overview, Timeline, Monte Carlo, Scenarios.

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
        <CardContent className="p-6 pt-0 space-y-6 w-full min-w-0">
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
                          Most severe crisis since Great Depression (Sep 2008 - Mar 2010). Tests prolonged drawdown and recovery behavior.
                        </p>
                        <div className="space-y-1 text-xs text-gray-500">
                          <div>• Crisis Duration: 18 months</div>
                          <div>• Recovery Pattern: Prolonged</div>
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
                    className="bg-primary hover:bg-primary/90 min-w-[200px]"
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
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="overview" className="flex items-center gap-1 text-xs">
                    <FileText className="h-3 w-3" />
                    Overview
                  </TabsTrigger>
                  <TabsTrigger value="timeline" className="flex items-center gap-1 text-xs">
                    <Calendar className="h-3 w-3" />
                    Timeline
                  </TabsTrigger>
                  <TabsTrigger value="monte-carlo" className="flex items-center gap-1 text-xs">
                    <BarChart3 className="h-3 w-3" />
                    Monte Carlo
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
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                    <div className="text-center p-3 bg-blue-50 rounded-lg border border-blue-200 min-w-0">
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
                                    : stressTestResults.scenarios.covid19.metrics.trajectory_projections?.moderate_months
                                      ? `${stressTestResults.scenarios.covid19.metrics.trajectory_projections.moderate_months.toFixed(1)} mo (proj)`
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
                                <TooltipContent className="w-80 p-4 bg-gray-900 text-white text-xs border-0">
                                  <div className="font-semibold mb-2">Trajectory Projections</div>
                                  <div className="mb-3">Forward-looking scenarios showing potential portfolio recovery paths based on current trends.</div>

                                  <div className="mb-2"><strong>📈 Projection Types:</strong></div>
                                  <div className="mb-1 text-green-400"><strong>Positive Values:</strong> Portfolio trending upward - expected growth</div>
                                  <div className="mb-1 text-red-400"><strong>Negative Values:</strong> Portfolio trending downward - potential continued decline</div>
                                  <div className="mb-3 text-gray-300">⚠️ Negative projections indicate the portfolio may lose value at this annualized rate if current trends continue</div>

                                  <div className="mb-2"><strong>🎯 Scenarios:</strong></div>
                                  <div className="mb-1"><strong className="text-green-400">Aggressive (A):</strong> Best-case recovery (fastest)</div>
                                  <div className="mb-1"><strong className="text-blue-400">Moderate (M):</strong> Realistic scenario (typical)</div>
                                  <div className="mb-1"><strong className="text-orange-400">Conservative (C):</strong> Worst-case recovery (slowest)</div>

                                  <div className="text-yellow-300 mt-3 border-t border-gray-600 pt-2">
                                    <strong>💡 Insight:</strong> Use these projections to understand risk and plan rebalancing. Negative trends may signal need for portfolio adjustments.
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-xs text-green-600 font-medium">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.aggressive_months
                                  ? `A:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.aggressive_months.toFixed(1)}`
                                  : 'A:N/A'}
                              </span>
                              <span className="text-xs text-blue-700 font-bold">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.moderate_months
                                  ? `M:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.moderate_months.toFixed(1)}`
                                  : 'M:N/A'}
                              </span>
                              <span className="text-xs text-orange-600 font-medium">
                                {stressTestResults.scenarios.covid19.metrics.trajectory_projections.conservative_months
                                  ? `C:${stressTestResults.scenarios.covid19.metrics.trajectory_projections.conservative_months.toFixed(1)}`
                                  : 'C:N/A'}
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
                                {(() => {
                                  // Normalize data so January 2020 starts at 100%
                                  const jan2020Value = stressTestResults.scenarios.covid19.monthly_performance.find((m: any) => m.month === '2020-01')?.value || 1.0;
                                  const normalizationFactor = 1.0 / jan2020Value;
                                  
                                  // Store recovery peak info for rendering (if it exists)
                                  let recoveryPeakInfo: { date: string; value: number } | null = null;

                                    let baseData = stressTestResults.scenarios.covid19.monthly_performance.map((m: any) => ({
                                      date: m.month,
                                      value: ((m.value || 0) * normalizationFactor) * 100,
                                      return: (m.return || 0) * 100,
                                      aggressive: null,
                                      moderate: null,
                                      conservative: null
                                    }));

                                    // Find recovery point and truncate chart to show only relevant period
                                    // This prevents showing long periods of stable post-recovery data
                                    const peakValue = 100; // Normalized peak (January 2020 = 100%)
                                    const recoveryIndex = baseData.findIndex((d: any) => d.value >= peakValue);

                                    // Check if recovery peak exists and find its index
                                    let recoveryPeakIndex = -1;
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.recovery_peak) {
                                      const recoveryDateFull = stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      recoveryPeakIndex = baseData.findIndex((d: any) => d.date === recoveryDate);
                                    }

                                    if (recoveryIndex !== -1) {
                                      // Portfolio recovered - show 3-6 months after recovery, or up to recovery peak, or up to 24 months total
                                      const endIndex = Math.min(
                                        recoveryIndex + 3, // 3 months after recovery
                                        recoveryPeakIndex !== -1 ? recoveryPeakIndex + 1 : baseData.length - 1, // Include recovery peak if it exists
                                        baseData.length - 1, // Don't exceed available data
                                        24 // Maximum 24 months total for chart readability
                                      );
                                      baseData = baseData.slice(0, endIndex + 1);
                                    } else {
                                      // No recovery found - limit to reasonable length anyway, but include recovery peak if it exists
                                      const maxIndex = recoveryPeakIndex !== -1 
                                        ? Math.max(recoveryPeakIndex + 1, Math.min(baseData.length, 24))
                                        : Math.min(baseData.length, 24);
                                      baseData = baseData.slice(0, maxIndex);
                                    }
                                    
                                    // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                    // This handles cases where dates might be slightly off or missing
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.peak) {
                                      const peakDate = stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(0, 7) || '';
                                      if (peakDate && !baseData.find((d: any) => d.date === peakDate)) {
                                        // Peak date not in data - find closest month or insert
                                        const peakValue = ((stressTestResults.scenarios.covid19.peaks_troughs.peak.value || 0) * normalizationFactor) * 100;
                                        baseData.push({ date: peakDate, value: peakValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.trough) {
                                      const troughDate = stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(0, 7) || '';
                                      if (troughDate && !baseData.find((d: any) => d.date === troughDate)) {
                                        const troughValue = ((stressTestResults.scenarios.covid19.peaks_troughs.trough.value || 0) * normalizationFactor) * 100;
                                        baseData.push({ date: troughDate, value: troughValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    // Ensure recovery peak date exists in chart data for ReferenceDot rendering
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.recovery_peak) {
                                      const recoveryDateFull = stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      const recoveryValue = ((stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.value || 0) * normalizationFactor) * 100;
                                      
                                      if (recoveryDate && !baseData.find((d: any) => d.date === recoveryDate)) {
                                        // Recovery peak date not in data - insert it
                                        baseData.push({ date: recoveryDate, value: recoveryValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                      
                                      // Store recovery peak info for rendering (check if it's in visible range after truncation)
                                      const recoveryDataPoint = baseData.find((d: any) => d.date === recoveryDate);
                                      if (recoveryDataPoint) {
                                        recoveryPeakInfo = { date: recoveryDate, value: recoveryValue };
                                      }
                                    }
                                    
                                    // Add trajectory data if available
                                    // Projection lines should start from the end of the portfolio value line
                                    // Convert backend's cumulative values to frontend's normalized percentage format
                                    if (stressTestResults.scenarios.covid19.metrics.max_drawdown_data?.is_significant && 
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections?.trajectory_data &&
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.length > 0) {
                                      const lastDataPoint = baseData[baseData.length - 1];
                                      const lastDate = lastDataPoint?.date;
                                      const lastValue = lastDataPoint?.value; // This is the last actual portfolio value (already normalized to %)
                                      
                                      if (lastDate && lastValue !== null && lastValue !== undefined) {
                                        const [year, month] = lastDate.split('-').map(Number);
                                        
                                        // Get the backend's last value (current_value used for trajectory calculations)
                                        // Backend values are in decimal form (0.95 = 95%), need to normalize to match frontend
                                        const lastBackendValue = stressTestResults.scenarios.covid19.monthly_performance[stressTestResults.scenarios.covid19.monthly_performance.length - 1]?.value || 1.0;
                                        const backendNormalizedLastValue = (lastBackendValue * normalizationFactor) * 100; // Convert to frontend's normalized %
                                        
                                        // Calculate offset to align backend's trajectory starting point with frontend's lastValue
                                        // Backend's trajectory values are cumulative from backend's current_value
                                        // We need to adjust them to start from frontend's lastValue
                                        const valueOffset = lastValue - backendNormalizedLastValue;
                                        
                                        // First point: connect to the last actual portfolio value
                                        // Set all projection values to lastValue to ensure smooth connection
                                        baseData.push({
                                          date: lastDate, // Same date as last actual point
                                          value: lastValue, // Keep actual value for smooth connection
                                          return: null,
                                          aggressive: lastValue, // Start from lastValue
                                          moderate: lastValue, // Start from lastValue
                                          conservative: lastValue // Start from lastValue
                                        });
                                        
                                        // Add remaining projection points
                                        // Backend provides cumulative values from its current_value
                                        // Convert them to frontend normalized percentage and adjust by offset
                                        stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.forEach((point: any, idx: number) => {
                                          if (idx === 0) return; // Skip first point, already added
                                          
                                          const futureMonth = month + idx;
                                          const futureYear = year + Math.floor((futureMonth - 1) / 12);
                                          const futureMonthNormalized = ((futureMonth - 1) % 12) + 1;
                                          const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, '0')}`;
                                          
                                          // Convert backend values to frontend normalized percentage
                                          // Backend values are cumulative from its current_value in decimal form
                                          // Normalize them the same way as the actual data, then adjust by offset
                                          const backendAggressive = (point.aggressive || 0) * normalizationFactor * 100;
                                          const backendModerate = (point.moderate || 0) * normalizationFactor * 100;
                                          const backendConservative = (point.conservative || 0) * normalizationFactor * 100;
                                          
                                          // Apply offset to align with frontend's lastValue
                                          const aggressiveValue = backendAggressive + valueOffset;
                                          const moderateValue = backendModerate + valueOffset;
                                          const conservativeValue = backendConservative + valueOffset;
                                          
                                          baseData.push({
                                            date: futureDate,
                                            value: null, // No actual value, only projections
                                            return: null,
                                            aggressive: aggressiveValue,
                                            moderate: moderateValue,
                                            conservative: conservativeValue
                                          });
                                        });
                                      }
                                    }
                                    
                                    // Update recovery peak info after all data processing to ensure it's in visible range
                                    if (stressTestResults.scenarios.covid19.peaks_troughs?.recovery_peak && !recoveryPeakInfo) {
                                      const recoveryDateFull = stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      const recoveryValue = ((stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.value || 0) * normalizationFactor) * 100;
                                      
                                      // Check if recovery date exists in the final chart data (after truncation and projection additions)
                                      const recoveryDataPoint = baseData.find((d: any) => d.date === recoveryDate);
                                      if (recoveryDataPoint) {
                                        recoveryPeakInfo = { date: recoveryDate, value: recoveryValue };
                                      }
                                    }
                                    
                                    // Calculate dynamic domain based on all data (including projection lines)
                                    // Find min and max from all values: value, aggressive, moderate, conservative
                                    let minValue = Infinity;
                                    let maxValue = -Infinity;
                                    
                                    baseData.forEach((d: any) => {
                                      // Check all possible value fields
                                      const values = [
                                        d.value,
                                        d.aggressive,
                                        d.moderate,
                                        d.conservative
                                      ].filter(v => v !== null && v !== undefined && !isNaN(v));
                                      
                                      values.forEach(v => {
                                        if (v < minValue) minValue = v;
                                        if (v > maxValue) maxValue = v;
                                      });
                                    });
                                    
                                    // Add padding (10% on each side) and ensure minimum range
                                    const padding = Math.max((maxValue - minValue) * 0.1, 5);
                                    const calculatedMin = Math.max(0, Math.floor(minValue - padding));
                                    const calculatedMax = Math.ceil(maxValue + padding);
                                    
                                    const calculatedDomain: [number, number] = [calculatedMin, calculatedMax];
                                    
                                    return (
                                      <ComposedChart 
                                        data={baseData}
                                        margin={{ left: 10, right: 10, top: 10, bottom: 10 }}
                                      >
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                                        <XAxis
                                          dataKey="date"
                                          tick={{ fontSize: 10 }}
                                          label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
                                        />
                                        <YAxis
                                          type="number"
                                          tick={{ fontSize: 10 }}
                                          tickFormatter={(value) => `${value.toFixed(0)}%`}
                                          label={{ value: 'Portfolio Value (%)', angle: -90, position: 'left', offset: 0, style: { textAnchor: 'middle' } }}
                                          domain={calculatedDomain}
                                          allowDataOverflow={false}
                                          allowDecimals={false}
                                          width={70}
                                        />
                                        <Tooltip
                                          formatter={(value: number, name: string) => {
                                            if (name === 'Aggressive' || name === 'Moderate' || name === 'Conservative') {
                                              // This is a trajectory projection line
                                              const isNegative = value < 0;
                                              const insight = isNegative
                                                ? `⚠️ Projected ${Math.abs(value).toFixed(1)}% annual decline - consider rebalancing`
                                                : `📈 Projected ${value.toFixed(1)}% annual growth`;
                                              return [`${value.toFixed(1)}%`, `${name} Trajectory`];
                                            }
                                            return [`${value.toFixed(1)}%`, 'Portfolio Value'];
                                          }}
                                          labelFormatter={(label) => `Month: ${label}`}
                                          content={({ active, payload, label }) => {
                                            if (!active || !payload || !payload.length) return null;

                                            return (
                                              <div className="bg-background border rounded-lg p-3 shadow-lg max-w-xs">
                                                <p className="font-medium text-sm mb-2">{`Month: ${label}`}</p>
                                                {payload.map((entry, index) => {
                                                  const isTrajectory = entry.dataKey === 'aggressive' || entry.dataKey === 'moderate' || entry.dataKey === 'conservative';
                                                  const value = entry.value as number;
                                                  const name = entry.name as string;

                                                  if (isTrajectory) {
                                                    const isNegative = value < 0;
                                                    return (
                                                      <div key={index} className="mb-2 last:mb-0">
                                                        <div className="flex items-center gap-2">
                                                          <div
                                                            className="w-3 h-3 rounded-full"
                                                            style={{ backgroundColor: entry.color }}
                                                          />
                                                          <span className="font-medium text-sm capitalize">{name} Trajectory:</span>
                                                          <span className={`font-bold ${isNegative ? 'text-red-600' : 'text-green-600'}`}>
                                                            {value.toFixed(1)}%
                                                          </span>
                                                        </div>
                                                        <div className={`text-xs mt-1 ${isNegative ? 'text-red-500' : 'text-green-500'}`}>
                                                          {isNegative
                                                            ? `⚠️ Projected ${Math.abs(value).toFixed(1)}% annual decline - consider rebalancing`
                                                            : `📈 Projected ${value.toFixed(1)}% annual growth`
                                                          }
                                                        </div>
                                                      </div>
                                                    );
                                                  } else {
                                                    return (
                                                      <div key={index} className="flex items-center gap-2">
                                                        <div
                                                          className="w-3 h-3 rounded-full"
                                                          style={{ backgroundColor: entry.color }}
                                                        />
                                                        <span className="font-medium text-sm">{name}:</span>
                                                        <span className="font-bold">{value.toFixed(1)}%</span>
                                                      </div>
                                                    );
                                                  }
                                                })}
                                              </div>
                                            );
                                          }}
                                        />
                                        <Area
                                          type="monotone"
                                          dataKey="value"
                                          stroke="#3b82f6"
                                          strokeWidth={3}
                                          fill="#3b82f6"
                                          fillOpacity={0.35}
                                        />
                                        {/* Recovery Threshold Lines removed from Portfolio Value Over Time - only show in Interactive Timeline */}
                                        {/* Trajectory Projection Lines - Smooth lines starting from end of portfolio value */}
                                        {stressTestResults.scenarios.covid19.metrics.trajectory_projections?.trajectory_data &&
                                         stressTestResults.scenarios.covid19.metrics.trajectory_projections.trajectory_data.length > 0 && (
                                          <>
                                            {/* Aggressive Trajectory - Green (fastest recovery) */}
                                            <Line
                                              dataKey="aggressive"
                                              stroke="#22c55e"
                                              strokeDasharray="4 4"
                                              strokeWidth={1.5}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Aggressive"
                                            />
                                            {/* Moderate Trajectory - Blue (realistic recovery) */}
                                            <Line
                                              dataKey="moderate"
                                              stroke="#3b82f6"
                                              strokeDasharray="4 4"
                                              strokeWidth={2}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Moderate"
                                            />
                                            {/* Conservative Trajectory - Orange (slowest recovery) */}
                                            <Line
                                              dataKey="conservative"
                                              stroke="#f59e0b"
                                              strokeDasharray="4 4"
                                              strokeWidth={1.5}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Conservative"
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
                                      // Peak is always at 100% since we normalize to Jan 2020 = 100%
                                      peakValue = 100.0;
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
                                            r={12}
                                            fill="#22c55e"
                                            stroke="#fff"
                                            strokeWidth={3}
                                            label={{ value: 'Peak (100%)', position: peakLabelPos, fill: '#22c55e', fontSize: 11, fontWeight: 'bold' }}
                                          />
                                        )}
                                        {trough && (
                                          <ReferenceDot 
                                            x={troughDate} 
                                            y={troughValue}
                                            r={12}
                                            fill="#ef4444"
                                            stroke="#fff"
                                            strokeWidth={3}
                                            label={{ value: `Trough (${troughValue.toFixed(1)}%)`, position: troughLabelPos, fill: '#ef4444', fontSize: 11, fontWeight: 'bold' }}
                                          />
                                        )}
                                      </>
                                    );
                                  })()}
                                  {recoveryPeakInfo && (
                                    <ReferenceDot 
                                      x={recoveryPeakInfo.date} 
                                      y={recoveryPeakInfo.value}
                                      r={16}
                                      fill="#9333ea"
                                      stroke="#fff"
                                      strokeWidth={4}
                                      label={{ 
                                        value: `Recovery (${recoveryPeakInfo.value.toFixed(1)}%)`, 
                                        position: 'top', 
                                        fill: '#9333ea', 
                                        fontSize: 12, 
                                        fontWeight: 'bold',
                                        offset: 10
                                      }}
                                    />
                                  )}
                                      </ComposedChart>
                                    );
                                  })()}
                              </ResponsiveContainer>
                            </div>
                            {stressTestResults.scenarios.covid19.peaks_troughs && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-center gap-4 text-xs">
                                  {stressTestResults.scenarios.covid19.peaks_troughs.peak && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow-sm"></div>
                                          <span className="font-medium">Peak ({stressTestResults.scenarios.covid19.peaks_troughs.peak.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Pre-Crisis Peak</div>
                                        <div className="mb-2">The highest portfolio value before the crisis started. This represents your portfolio's value at its best point before market conditions deteriorated.</div>
                                        <div className="text-yellow-300 mt-2">Used as baseline for calculating drawdown and recovery metrics.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                  {stressTestResults.scenarios.covid19.peaks_troughs.trough && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow-sm"></div>
                                          <span className="font-medium">Trough ({stressTestResults.scenarios.covid19.peaks_troughs.trough.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Crisis Trough</div>
                                        <div className="mb-2">The lowest portfolio value during the crisis period. This is the worst point your portfolio reached when market conditions were at their most adverse.</div>
                                        <div className="text-yellow-300 mt-2">The difference between Peak and Trough determines your Maximum Drawdown.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                  {stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: '#9333ea' }}></div>
                                          <span className="font-medium">Recovery Peak ({stressTestResults.scenarios.covid19.peaks_troughs.recovery_peak.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Recovery Peak</div>
                                        <div className="mb-2">The highest portfolio value after the crisis trough, indicating full recovery. This shows when your portfolio returned to or exceeded its pre-crisis peak value.</div>
                                        <div className="text-yellow-300 mt-2">Recovery Time is measured from Trough to Recovery Peak.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500 text-center italic">
                                  Hover over markers above for detailed definitions
                                </div>
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
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
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
                        {/* Key Metrics - Compact Horizontal Layout (matching COVID-19) */}
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
                              {(stressTestResults.scenarios['2008_crisis'].metrics.total_return * 100).toFixed(1)}%
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
                              {(stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown * 100).toFixed(1)}%
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
                              {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant 
                                ? (stressTestResults.scenarios['2008_crisis'].metrics.recovered
                                    ? `${stressTestResults.scenarios['2008_crisis'].metrics.recovery_months} mo`
                                    : stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.moderate_months
                                      ? `${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.moderate_months.toFixed(1)} mo (proj)`
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
                              {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant
                                ? stressTestResults.scenarios['2008_crisis'].metrics.recovery_pattern.replace(' (projected)', '')
                                : 'N/A'}
                            </span>
                          </div>
                          
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct !== undefined && (
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
                                {stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct.toFixed(1)}%
                              </span>
                            </div>
                          )}
                          
                          {/* Projections - Only show if recovery is needed (recovery_needed_pct > 0) */}
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct > 0 &&
                           stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-indigo-50 border border-indigo-200">
                              <span className="text-xs text-indigo-700 font-medium">Projections</span>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-3 w-3 text-indigo-500 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="w-80 p-4 bg-gray-900 text-white text-xs border-0">
                                  <div className="font-semibold mb-2">Trajectory Projections</div>
                                  <div className="mb-3">Forward-looking scenarios showing potential portfolio recovery paths based on current trends.</div>

                                  <div className="mb-2"><strong>📈 Projection Types:</strong></div>
                                  <div className="mb-1 text-green-400"><strong>Positive Values:</strong> Portfolio trending upward - expected growth</div>
                                  <div className="mb-1 text-red-400"><strong>Negative Values:</strong> Portfolio trending downward - potential continued decline</div>
                                  <div className="mb-3 text-gray-300">⚠️ Negative projections indicate the portfolio may lose value at this annualized rate if current trends continue</div>

                                  <div className="mb-2"><strong>🎯 Scenarios:</strong></div>
                                  <div className="mb-1"><strong className="text-green-400">Aggressive (A):</strong> Best-case recovery (fastest)</div>
                                  <div className="mb-1"><strong className="text-blue-400">Moderate (M):</strong> Realistic scenario (typical)</div>
                                  <div className="mb-1"><strong className="text-orange-400">Conservative (C):</strong> Worst-case recovery (slowest)</div>

                                  <div className="text-yellow-300 mt-3 border-t border-gray-600 pt-2">
                                    <strong>💡 Insight:</strong> Use these projections to understand risk and plan rebalancing. Negative trends may signal need for portfolio adjustments.
                                  </div>
                                </TooltipContent>
                              </UITooltip>
                              <span className="text-xs text-green-600 font-medium">
                                {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.aggressive_months
                                  ? `A:${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.aggressive_months.toFixed(1)}`
                                  : 'A:N/A'}
                              </span>
                              <span className="text-xs text-blue-700 font-bold">
                                {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.moderate_months
                                  ? `M:${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.moderate_months.toFixed(1)}`
                                  : 'M:N/A'}
                              </span>
                              <span className="text-xs text-orange-600 font-medium">
                                {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.conservative_months
                                  ? `C:${stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.conservative_months.toFixed(1)}`
                                  : 'C:N/A'}
                              </span>
                            </div>
                          )}
                          {/* Show message when portfolio already recovered above peak */}
                          {stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                           stressTestResults.scenarios['2008_crisis'].metrics.recovery_needed_pct <= 0 && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-green-50 border border-green-200">
                              <CheckCircle className="h-4 w-4 text-green-600" />
                              <span className="text-xs text-green-700 font-medium">Already above peak - projections N/A</span>
                            </div>
                          )}
                        </div>

                        {/* Portfolio Value Timeline Chart */}
                        {stressTestResults.scenarios['2008_crisis'].monthly_performance && 
                         stressTestResults.scenarios['2008_crisis'].monthly_performance.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-center">Portfolio Value Over Time</div>
                            <div className="h-64 w-full -ml-4">
                              <ResponsiveContainer width="100%" height="100%">
                                {(() => {
                                  // Normalize data so August 2008 starts at 100% (pre-crisis baseline)
                                  const aug2008Value = stressTestResults.scenarios['2008_crisis'].monthly_performance.find((m: any) => m.month === '2008-08')?.value || 1.0;
                                  const normalizationFactor = 1.0 / aug2008Value;
                                  
                                  // Store recovery peak info for rendering (if it exists)
                                  let recoveryPeakInfo: { date: string; value: number } | null = null;

                                  let baseData = stressTestResults.scenarios['2008_crisis'].monthly_performance.map((m: any) => ({
                                      date: m.month,
                                      value: ((m.value || 0) * normalizationFactor) * 100,
                                      return: (m.return || 0) * 100,
                                      aggressive: null,
                                      moderate: null,
                                      conservative: null
                                    }));

                                    // Find recovery point and truncate chart to show only relevant period
                                    // CRITICAL: Always show the full crisis period (Sep 2008 - Mar 2010 = 18 months from Aug 2008 baseline)
                                    const peakValue = 100; // Normalized peak (August 2008 = 100%)
                                    
                                    // Find crisis end date (2010-03) to ensure we always show full crisis period
                                    const crisisEndDate = '2010-03';
                                    const crisisEndIndex = baseData.findIndex((d: any) => d.date === crisisEndDate);
                                    
                                    // Check if recovery peak exists and find its index
                                    let recoveryPeakIndex = -1;
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.recovery_peak) {
                                      const recoveryDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      recoveryPeakIndex = baseData.findIndex((d: any) => d.date === recoveryDate);
                                    }
                                    
                                    const recoveryIndex = baseData.findIndex((d: any) => d.value >= peakValue);

                                    // Calculate end index ensuring we show at least the full crisis period
                                    let endIndex: number;
                                    if (recoveryIndex !== -1) {
                                      // Portfolio recovered - show recovery + 3 months, but ensure we show full crisis period
                                      const recoveryEndIndex = Math.min(
                                        recoveryIndex + 3, // 3 months after recovery
                                        recoveryPeakIndex !== -1 ? recoveryPeakIndex + 1 : baseData.length - 1, // Include recovery peak if it exists
                                        baseData.length - 1 // Don't exceed available data
                                      );
                                      // Ensure we show at least until crisis end (2010-03) + 3 months for recovery context
                                      const minEndIndex = crisisEndIndex !== -1 ? crisisEndIndex + 3 : 20; // At least 20 months (crisis + recovery)
                                      endIndex = Math.max(recoveryEndIndex, minEndIndex, 20); // Always show at least 20 months
                                      endIndex = Math.min(endIndex, baseData.length - 1, 32); // Cap at 32 months (crisis + full recovery period)
                                    } else {
                                      // No recovery found - ensure we show full crisis period + recovery tracking period
                                      const minEndIndex = crisisEndIndex !== -1 ? crisisEndIndex + 6 : 24; // Crisis end + 6 months recovery tracking
                                      const maxIndex = recoveryPeakIndex !== -1 
                                        ? Math.max(recoveryPeakIndex + 1, minEndIndex)
                                        : minEndIndex;
                                      endIndex = Math.min(maxIndex, baseData.length - 1, 32); // Cap at 32 months
                                    }
                                    
                                    baseData = baseData.slice(0, endIndex + 1);
                                    
                                    // Ensure peak/trough dates exist in chart data for ReferenceDot rendering
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.peak) {
                                      const peakDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.date || '';
                                      const peakDate = peakDateFull.length >= 7 ? peakDateFull.substring(0, 7) : peakDateFull;
                                      if (peakDate && !baseData.find((d: any) => d.date === peakDate)) {
                                        // Peak is always at 100% since we normalize to Aug 2008 = 100%
                                        const peakValue = 100.0;
                                        baseData.push({ date: peakDate, value: peakValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.trough) {
                                      const troughDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.date || '';
                                      const troughDate = troughDateFull.length >= 7 ? troughDateFull.substring(0, 7) : troughDateFull;
                                      if (troughDate && !baseData.find((d: any) => d.date === troughDate)) {
                                        const troughValue = ((stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.value || 0) * normalizationFactor) * 100;
                                        baseData.push({ date: troughDate, value: troughValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                    }
                                    
                                    // Ensure recovery peak date exists in chart data for ReferenceDot rendering
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.recovery_peak) {
                                      const recoveryDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      const recoveryValue = ((stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.value || 0) * normalizationFactor) * 100;
                                      
                                      if (recoveryDate && !baseData.find((d: any) => d.date === recoveryDate)) {
                                        // Recovery peak date not in data - insert it
                                        baseData.push({ date: recoveryDate, value: recoveryValue, return: null, aggressive: null, moderate: null, conservative: null });
                                        baseData.sort((a: any, b: any) => a.date.localeCompare(b.date));
                                      }
                                      
                                      // Store recovery peak info for rendering (check if it's in visible range after truncation)
                                      const recoveryDataPoint = baseData.find((d: any) => d.date === recoveryDate);
                                      if (recoveryDataPoint) {
                                        recoveryPeakInfo = { date: recoveryDate, value: recoveryValue };
                                      }
                                    }
                                    
                                    // Add trajectory data if available
                                    if (stressTestResults.scenarios['2008_crisis'].metrics.max_drawdown_data?.is_significant && 
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.trajectory_data &&
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.length > 0) {
                                      const lastDataPoint = baseData[baseData.length - 1];
                                      const lastDate = lastDataPoint?.date;
                                      const lastValue = lastDataPoint?.value;
                                      
                                      if (lastDate && lastValue !== null && lastValue !== undefined) {
                                        const [year, month] = lastDate.split('-').map(Number);
                                        
                                        // Get the backend's last value to calculate the offset
                                        // Backend values are in decimal form (0.95 = 95%), need to normalize to match frontend
                                        const lastBackendValue = stressTestResults.scenarios['2008_crisis'].monthly_performance[stressTestResults.scenarios['2008_crisis'].monthly_performance.length - 1]?.value || 1.0;
                                        const backendNormalizedLastValue = (lastBackendValue * normalizationFactor) * 100; // Convert to frontend's normalized %
                                        
                                        // Calculate offset to align backend's trajectory starting point with frontend's lastValue
                                        // Backend's trajectory values are cumulative from backend's current_value
                                        // We need to adjust them to start from frontend's lastValue
                                        const valueOffset = lastValue - backendNormalizedLastValue;
                                        
                                        // First point: connect to the last actual portfolio value
                                        // Set all projection values to lastValue to ensure smooth connection
                                        baseData.push({
                                          date: lastDate, // Same date as last actual point
                                          value: lastValue, // Keep actual value for smooth connection
                                          return: null,
                                          aggressive: lastValue, // Start from lastValue
                                          moderate: lastValue, // Start from lastValue
                                          conservative: lastValue // Start from lastValue
                                        });
                                        
                                        // Add remaining projection points
                                        // Backend provides cumulative values from its current_value
                                        // Convert them to frontend normalized percentage and adjust by offset
                                        stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.forEach((point: any, idx: number) => {
                                          if (idx === 0) return; // Skip first point, already added
                                          
                                          const futureMonth = month + idx;
                                          const futureYear = year + Math.floor((futureMonth - 1) / 12);
                                          const futureMonthNormalized = ((futureMonth - 1) % 12) + 1;
                                          const futureDate = `${futureYear}-${String(futureMonthNormalized).padStart(2, '0')}`;
                                          
                                          // Convert backend values to frontend normalized percentage
                                          // Backend values are cumulative from its current_value in decimal form
                                          // Normalize them the same way as the actual data, then adjust by offset
                                          const backendAggressive = (point.aggressive || 0) * normalizationFactor * 100;
                                          const backendModerate = (point.moderate || 0) * normalizationFactor * 100;
                                          const backendConservative = (point.conservative || 0) * normalizationFactor * 100;
                                          
                                          // Apply offset to align with frontend's lastValue
                                          const aggressiveValue = backendAggressive + valueOffset;
                                          const moderateValue = backendModerate + valueOffset;
                                          const conservativeValue = backendConservative + valueOffset;
                                          
                                          baseData.push({
                                            date: futureDate,
                                            value: null, // No actual value, only projections
                                            return: null,
                                            aggressive: aggressiveValue,
                                            moderate: moderateValue,
                                            conservative: conservativeValue
                                          });
                                        });
                                      }
                                    }
                                    
                                    // Update recovery peak info after all data processing to ensure it's in visible range
                                    if (stressTestResults.scenarios['2008_crisis'].peaks_troughs?.recovery_peak && !recoveryPeakInfo) {
                                      const recoveryDateFull = stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date || '';
                                      const recoveryDate = recoveryDateFull.length >= 7 ? recoveryDateFull.substring(0, 7) : recoveryDateFull;
                                      const recoveryValue = ((stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.value || 0) * normalizationFactor) * 100;
                                      
                                      // Check if recovery date exists in the final chart data (after truncation and projection additions)
                                      const recoveryDataPoint = baseData.find((d: any) => d.date === recoveryDate);
                                      if (recoveryDataPoint) {
                                        recoveryPeakInfo = { date: recoveryDate, value: recoveryValue };
                                      }
                                    }
                                    
                                    // Calculate dynamic domain based on all data (including projection lines)
                                    // Find min and max from all values: value, aggressive, moderate, conservative
                                    let minValue = Infinity;
                                    let maxValue = -Infinity;
                                    
                                    baseData.forEach((d: any) => {
                                      // Check all possible value fields
                                      const values = [
                                        d.value,
                                        d.aggressive,
                                        d.moderate,
                                        d.conservative
                                      ].filter(v => v !== null && v !== undefined && !isNaN(v));
                                      
                                      values.forEach(v => {
                                        if (v < minValue) minValue = v;
                                        if (v > maxValue) maxValue = v;
                                      });
                                    });
                                    
                                    // Add padding (10% on each side) and ensure minimum range
                                    const padding = Math.max((maxValue - minValue) * 0.1, 5);
                                    const calculatedMin = Math.max(0, Math.floor(minValue - padding));
                                    const calculatedMax = Math.ceil(maxValue + padding);
                                    
                                    const calculatedDomain: [number, number] = [calculatedMin, calculatedMax];
                                    
                                    return (
                                      <ComposedChart 
                                        data={baseData}
                                        margin={{ left: 10, right: 10, top: 10, bottom: 10 }}
                                      >
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                                        <XAxis
                                          dataKey="date"
                                          tick={{ fontSize: 10 }}
                                          label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
                                        />
                                        <YAxis
                                          type="number"
                                          tick={{ fontSize: 10 }}
                                          tickFormatter={(value) => `${value.toFixed(0)}%`}
                                          label={{ value: 'Portfolio Value (%)', angle: -90, position: 'left', offset: 0, style: { textAnchor: 'middle' } }}
                                          domain={calculatedDomain}
                                          allowDataOverflow={false}
                                          allowDecimals={false}
                                          width={70}
                                        />
                                        <Tooltip
                                          formatter={(value: number, name: string) => {
                                            if (name === 'Aggressive' || name === 'Moderate' || name === 'Conservative') {
                                              // This is a trajectory projection line
                                              const isNegative = value < 0;
                                              return [`${value.toFixed(1)}%`, `${name} Trajectory`];
                                            }
                                            return [`${value.toFixed(1)}%`, 'Portfolio Value'];
                                          }}
                                          labelFormatter={(label) => `Month: ${label}`}
                                          content={({ active, payload, label }) => {
                                            if (!active || !payload || !payload.length) return null;

                                            return (
                                              <div className="bg-background border rounded-lg p-3 shadow-lg max-w-xs">
                                                <p className="font-medium text-sm mb-2">{`Month: ${label}`}</p>
                                                {payload.map((entry, index) => {
                                                  const isTrajectory = entry.dataKey === 'aggressive' || entry.dataKey === 'moderate' || entry.dataKey === 'conservative';
                                                  const value = entry.value as number;
                                                  const name = entry.name as string;

                                                  if (isTrajectory) {
                                                    const isNegative = value < 0;
                                                    return (
                                                      <div key={index} className="mb-2 last:mb-0">
                                                        <div className="flex items-center gap-2">
                                                          <div
                                                            className="w-3 h-3 rounded-full"
                                                            style={{ backgroundColor: entry.color }}
                                                          />
                                                          <span className="font-medium text-sm capitalize">{name} Trajectory:</span>
                                                          <span className={`font-bold ${isNegative ? 'text-red-600' : 'text-green-600'}`}>
                                                            {value.toFixed(1)}%
                                                          </span>
                                                        </div>
                                                        <div className={`text-xs mt-1 ${isNegative ? 'text-red-500' : 'text-green-500'}`}>
                                                          {isNegative
                                                            ? `⚠️ Projected ${Math.abs(value).toFixed(1)}% annual decline - consider rebalancing`
                                                            : `📈 Projected ${value.toFixed(1)}% annual growth`
                                                          }
                                                        </div>
                                                      </div>
                                                    );
                                                  } else {
                                                    return (
                                                      <div key={index} className="flex items-center gap-2">
                                                        <div
                                                          className="w-3 h-3 rounded-full"
                                                          style={{ backgroundColor: entry.color }}
                                                        />
                                                        <span className="font-medium text-sm">{name}:</span>
                                                        <span className="font-bold">{value.toFixed(1)}%</span>
                                                      </div>
                                                    );
                                                  }
                                                })}
                                              </div>
                                            );
                                          }}
                                        />
                                        <Area
                                          type="monotone"
                                          dataKey="value"
                                          stroke="#3b82f6"
                                          strokeWidth={3}
                                          fill="#3b82f6"
                                          fillOpacity={0.35}
                                        />
                                        {/* Recovery Threshold Lines removed from Portfolio Value Over Time - only show in Interactive Timeline */}
                                        {/* Trajectory Projection Lines - Smooth lines starting from end of portfolio value */}
                                        {stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections?.trajectory_data &&
                                         stressTestResults.scenarios['2008_crisis'].metrics.trajectory_projections.trajectory_data.length > 0 && (
                                          <>
                                            {/* Aggressive Trajectory - Green (fastest recovery) */}
                                            <Line
                                              dataKey="aggressive"
                                              stroke="#22c55e"
                                              strokeDasharray="4 4"
                                              strokeWidth={1.5}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Aggressive"
                                            />
                                            {/* Moderate Trajectory - Blue (realistic recovery) */}
                                            <Line
                                              dataKey="moderate"
                                              stroke="#3b82f6"
                                              strokeDasharray="4 4"
                                              strokeWidth={2}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Moderate"
                                            />
                                            {/* Conservative Trajectory - Orange (slowest recovery) */}
                                            <Line
                                              dataKey="conservative"
                                              stroke="#f59e0b"
                                              strokeDasharray="4 4"
                                              strokeWidth={1.5}
                                              dot={false}
                                              connectNulls={true}
                                              type="monotone"
                                              isAnimationActive={false}
                                              name="Conservative"
                                            />
                                          </>
                                        )}
                                  {(() => {
                                    // Calculate both peak and trough values first to detect overlap
                                    const aug2008Value = stressTestResults.scenarios['2008_crisis'].monthly_performance.find((m: any) => m.month === '2008-08')?.value || 1.0;
                                    const normalizationFactor = 1.0 / aug2008Value;
                                    
                                    const peak = stressTestResults.scenarios['2008_crisis'].peaks_troughs?.peak;
                                    const trough = stressTestResults.scenarios['2008_crisis'].peaks_troughs?.trough;
                                    
                                    if (!peak && !trough) return null;
                                    
                                    let peakValue = 0;
                                    let troughValue = 0;
                                    let peakDate = '';
                                    let troughDate = '';
                                    
                                    if (peak) {
                                      const peakDateFull = peak.date || '';
                                      peakDate = peakDateFull.length >= 7 ? peakDateFull.substring(0, 7) : peakDateFull;
                                      // Peak is always at 100% since we normalize to Aug 2008 = 100%
                                      peakValue = 100.0;
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
                                            r={12}
                                            fill="#22c55e"
                                            stroke="#fff"
                                            strokeWidth={3}
                                            label={{ value: 'Peak (100%)', position: peakLabelPos, fill: '#22c55e', fontSize: 11, fontWeight: 'bold' }}
                                          />
                                        )}
                                        {trough && (
                                          <ReferenceDot 
                                            x={troughDate} 
                                            y={troughValue}
                                            r={12}
                                            fill="#ef4444"
                                            stroke="#fff"
                                            strokeWidth={3}
                                            label={{ value: `Trough (${troughValue.toFixed(1)}%)`, position: troughLabelPos, fill: '#ef4444', fontSize: 11, fontWeight: 'bold' }}
                                          />
                                        )}
                                      </>
                                    );
                                  })()}
                                  {recoveryPeakInfo && (
                                    <ReferenceDot 
                                      x={recoveryPeakInfo.date} 
                                      y={recoveryPeakInfo.value}
                                      r={16}
                                      fill="#9333ea"
                                      stroke="#fff"
                                      strokeWidth={4}
                                      label={{ 
                                        value: `Recovery (${recoveryPeakInfo.value.toFixed(1)}%)`, 
                                        position: 'top', 
                                        fill: '#9333ea', 
                                        fontSize: 12, 
                                        fontWeight: 'bold',
                                        offset: 10
                                      }}
                                    />
                                  )}
                                      </ComposedChart>
                                    );
                                  })()}
                              </ResponsiveContainer>
                            </div>
                            {stressTestResults.scenarios['2008_crisis'].peaks_troughs && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-center gap-4 text-xs">
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow-sm"></div>
                                          <span className="font-medium">Peak ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.peak.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Pre-Crisis Peak</div>
                                        <div className="mb-2">The highest portfolio value before the crisis started. This represents your portfolio's value at its best point before market conditions deteriorated.</div>
                                        <div className="text-yellow-300 mt-2">Used as baseline for calculating drawdown and recovery metrics.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow-sm"></div>
                                          <span className="font-medium">Trough ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.trough.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Crisis Trough</div>
                                        <div className="mb-2">The lowest portfolio value during the crisis period. This is the worst point your portfolio reached when market conditions were at their most adverse.</div>
                                        <div className="text-yellow-300 mt-2">The difference between Peak and Trough determines your Maximum Drawdown.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                  {stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak && (
                                    <UITooltip>
                                      <TooltipTrigger asChild>
                                        <div className="flex items-center gap-2 cursor-help">
                                          <div className="w-4 h-4 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: '#9333ea' }}></div>
                                          <span className="font-medium">Recovery Peak ({stressTestResults.scenarios['2008_crisis'].peaks_troughs.recovery_peak.date?.substring(0, 7) || 'N/A'})</span>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent className="w-64 p-3 bg-gray-900 text-white text-xs border-0">
                                        <div className="font-semibold mb-1">Recovery Peak</div>
                                        <div className="mb-2">The highest portfolio value after the crisis trough, indicating full recovery. This shows when your portfolio returned to or exceeded its pre-crisis peak value.</div>
                                        <div className="text-yellow-300 mt-2">Recovery Time is measured from Trough to Recovery Peak.</div>
                                      </TooltipContent>
                                    </UITooltip>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500 text-center italic">
                                  Hover over markers above for detailed definitions
                                </div>
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
                          Probabilistic analysis showing range of possible outcomes (5,000 simulations)
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
                                <AreaChart
                                  margin={{ top: 10, right: 20, bottom: 30, left: 10 }}
                                  data={stressTestResults.scenarios[selectedScenario || 'covid19'].monte_carlo.histogram_data.map((h: any) => ({
                                    return_pct: h.return_pct,
                                    frequency: h.frequency
                                  }))}
                                >
                                  <defs>
                                    <linearGradient id="colorGradient-blue-stress" x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                                    </linearGradient>
                                  </defs>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                  <XAxis
                                    dataKey="return_pct"
                                    type="number"
                                    tickFormatter={(value) => {
                                      const n = typeof value === 'number' ? value : Number(value);
                                      return Number.isFinite(n) ? `${n.toFixed(0)}%` : String(value);
                                    }}
                                    tick={{ fontSize: 10 }}
                                    label={{ value: 'Return (%)', position: 'bottom', offset: 15, fontSize: 11 }}
                                  />
                                  <YAxis
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                                    label={{ value: 'Probability Density', angle: -90, position: 'insideLeft', offset: 5, fontSize: 11 }}
                                  />
                                  <Tooltip
                                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Frequency']}
                                    labelFormatter={(label) => {
                                      const n = typeof label === 'number' ? label : Number(label);
                                      return Number.isFinite(n) ? `Return: ${n.toFixed(1)}%` : `Return: ${label}%`;
                                    }}
                                  />
                                  <Area
                                    type="monotone"
                                    dataKey="frequency"
                                    name="Return Distribution"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    fill="url(#colorGradient-blue-stress)"
                                  />
                                </AreaChart>
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
                                  content={({ active, payload, label }) => {
                                    if (!active || !payload || !payload.length) return null;
                                    
                                    // Check if hovering near an event date
                                    const hoverDate = label as string;
                                    const nearbyEvent = crisisEvents[selectedScenario as keyof typeof crisisEvents]?.find((event) => {
                                      const eventDate = event.date.substring(0, 7); // YYYY-MM
                                      return eventDate === hoverDate;
                                    });
                                    
                                    if (nearbyEvent) {
                                      const eventColor = nearbyEvent.type === 'crisis' ? '#ef4444' : 
                                                        nearbyEvent.type === 'policy' ? '#3b82f6' : 
                                                        nearbyEvent.type === 'recovery' ? '#22c55e' : '#f59e0b';
                                      return (
                                        <div className="bg-gray-900 text-white p-3 rounded-lg shadow-lg border border-gray-700 text-xs">
                                          <div className="font-semibold mb-1" style={{ color: eventColor }}>
                                            {nearbyEvent.event}
                                          </div>
                                          <div className="text-gray-300">
                                            Date: {nearbyEvent.date}
                                          </div>
                                          <div className="mt-2 pt-2 border-t border-gray-700">
                                            <div className="text-gray-300">
                                              Portfolio Value: {payload[0]?.value ? `${Number(payload[0].value).toFixed(1)}%` : 'N/A'}
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    }
                                    
                                    // Default tooltip for portfolio value
                                    return (
                                      <div className="bg-gray-900 text-white p-2 rounded-lg shadow-lg text-xs">
                                        <div className="font-semibold mb-1">Month: {label}</div>
                                        <div className="text-gray-300">
                                          Portfolio Value: {payload[0]?.value ? `${Number(payload[0].value).toFixed(1)}%` : 'N/A'}
                                        </div>
                                      </div>
                                    );
                                  }}
                                />
                                <Area 
                                  type="monotone" 
                                  dataKey="value" 
                                  stroke="#6366f1" 
                                  fill="#6366f1" 
                                  fillOpacity={0.2}
                                />
                                {/* Recovery Threshold Lines removed - user requested no horizontal lines */}
                                {/* Event markers - Only show if event type is visible, no labels (use tooltips instead) */}
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
                                    />
                                  );
                                })}
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                          
                          {/* Interactive Legends */}
                          <div className="space-y-4">
                            {/* Recovery Thresholds Legend removed - user requested no horizontal lines */}
                            
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
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t w-full">
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
                                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-center min-w-0">
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
                                <div className="p-3 rounded-lg border text-center min-w-0" style={{ backgroundColor: '#faf5ff', borderColor: '#e9d5ff' }}>
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
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
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
                      <div className="space-y-4 pt-4 border-t w-full">
                        <div className="text-sm font-medium">Adjust Scenario Parameters</div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
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
                        className="w-full bg-primary hover:bg-primary/90"
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
                        <div className="space-y-6 mt-6 pt-6 border-t w-full">
                          {hypotheticalResults.scenario_type && (
                            <div className="text-sm text-muted-foreground">
                              <span className="font-medium">Scenario: </span>
                              {hypotheticalResults.scenario_type === 'tech_crash' ? 'Tech Bubble Burst' :
                               hypotheticalResults.scenario_type === 'inflation' ? 'Inflation Shock' :
                               hypotheticalResults.scenario_type === 'geopolitical' ? 'Geopolitical Crisis' :
                               hypotheticalResults.scenario_type === 'recession' ? 'Deep Recession' :
                               hypotheticalResults.scenario_type}
                              {hypotheticalResults.parameters && (() => {
                                const p = hypotheticalResults.parameters;
                                const parts = [];
                                if (p.market_decline != null) parts.push(`${(p.market_decline * 100).toFixed(0)}% decline`);
                                if (p.duration_months != null) parts.push(`${p.duration_months} mo`);
                                if (p.recovery_rate) parts.push(`${p.recovery_rate} recovery`);
                                return parts.length ? <span className="ml-2">({parts.join(', ')})</span> : null;
                              })()}
                            </div>
                          )}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                            <div className="p-4 rounded-lg bg-red-50 border border-red-200 min-w-0">
                              <div className="text-sm text-red-700 mb-1">Estimated Loss</div>
                              <div className="text-2xl font-bold text-red-800">
                                {(hypotheticalResults.estimated_loss * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 min-w-0">
                              <div className="text-sm text-blue-700 mb-1">Portfolio Impact</div>
                              <div className="text-2xl font-bold text-blue-800">
                                {hypotheticalResults.capital_at_risk ? hypotheticalResults.capital_at_risk.toLocaleString() : 'N/A'} SEK
                              </div>
                            </div>
                            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 min-w-0">
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
                                  <AreaChart
                                    margin={{ top: 10, right: 20, bottom: 30, left: 10 }}
                                    data={hypotheticalResults.monte_carlo.histogram_data.map((h: any) => ({
                                      return_pct: h.return_pct,
                                      frequency: h.frequency
                                    }))}
                                  >
                                    <defs>
                                      <linearGradient id="colorGradient-amber-stress" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1}/>
                                      </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis
                                      dataKey="return_pct"
                                      type="number"
                                      tickFormatter={(value) => {
                                        const n = typeof value === 'number' ? value : Number(value);
                                        return Number.isFinite(n) ? `${n.toFixed(0)}%` : String(value);
                                      }}
                                      tick={{ fontSize: 10 }}
                                      label={{ value: 'Return (%)', position: 'bottom', offset: 15, fontSize: 11 }}
                                    />
                                    <YAxis
                                      tick={{ fontSize: 10 }}
                                      tickFormatter={(value) => `${value.toFixed(0)}%`}
                                      label={{ value: 'Probability Density', angle: -90, position: 'insideLeft', offset: 5, fontSize: 11 }}
                                    />
                                    <Tooltip
                                      formatter={(value: number) => [`${value.toFixed(1)}%`, 'Frequency']}
                                      labelFormatter={(label) => {
                                        const n = typeof label === 'number' ? label : Number(label);
                                        return Number.isFinite(n) ? `Return: ${n.toFixed(1)}%` : `Return: ${label}%`;
                                      }}
                                    />
                                    <Area
                                      type="monotone"
                                      dataKey="frequency"
                                      name="Outcome Distribution"
                                      stroke="#f59e0b"
                                      strokeWidth={2}
                                      fill="url(#colorGradient-amber-stress)"
                                    />
                                  </AreaChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}
                          
                          {/* Sector Impact Analysis */}
                          {hypotheticalResults.sector_impact && Object.keys(hypotheticalResults.sector_impact).length > 0 && (
                            <div className="space-y-2 w-full">
                              <div className="text-sm font-medium">Sector Impact Analysis</div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
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
                className="bg-primary hover:bg-primary/90"
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
