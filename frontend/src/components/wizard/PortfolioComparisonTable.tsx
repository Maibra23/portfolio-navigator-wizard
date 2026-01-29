/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { formatPercent, formatNumber } from '@/utils/numberFormat';

// Visualization theme matching PortfolioOptimization
const visualizationTheme = {
  canvas: '#FAFAF4',
  cardBackground: '#FFFFFF',
  border: 'rgba(90, 90, 82, 0.12)',
  grid: 'rgba(200, 200, 195, 0.8)',
  axes: {
    line: 'rgba(94, 94, 86, 0.28)',
    tick: 'rgba(75, 75, 68, 0.82)',
    label: '#3B3B33',
  },
  text: {
    primary: '#2F2F29',
    secondary: '#6D6D62',
    subtle: 'rgba(90, 90, 82, 0.65)',
  },
  spacing: {
    cardPadding: '28px',
    sectionGap: '28px',
  },
  radius: '18px',
  legend: {
    fontSize: 12,
    color: 'rgba(59, 59, 51, 0.8)',
  },
};

interface TripleOptimizationResults {
  current_portfolio: {
    tickers: string[];
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      risk: number;
      sharpe_ratio: number;
    };
  };
  weights_optimized_portfolio: {
    optimized_portfolio: {
      tickers: string[];
      weights: Record<string, number>;
      metrics: {
        expected_return: number;
        risk: number;
        sharpe_ratio: number;
      };
    };
  };
  market_optimized_portfolio?: {
    optimized_portfolio: {
      tickers: string[];
      weights: Record<string, number>;
      metrics: {
        expected_return: number;
        risk: number;
        sharpe_ratio: number;
      };
    };
  } | null;
  comparison: {
    weights_vs_current: {
      return_difference: number;
      risk_difference: number;
      sharpe_difference: number;
    };
    market_vs_current?: {
      return_difference: number;
      risk_difference: number;
      sharpe_difference: number;
    } | null;
    best_sharpe?: 'current' | 'weights' | 'market';
  };
  optimization_metadata?: {
    recommendation?: 'current' | 'weights' | 'market';
  };
}

interface PortfolioComparisonTableProps {
  tripleOptimizationResults: TripleOptimizationResults;
  selectedPortfolio?: 'current' | 'weights' | 'market';
  onPortfolioSelect?: (portfolio: 'current' | 'weights' | 'market') => void;
  showSelectionButtons?: boolean;
  className?: string;
}

export const PortfolioComparisonTable: React.FC<PortfolioComparisonTableProps> = ({
  tripleOptimizationResults,
  selectedPortfolio = 'current',
  onPortfolioSelect,
  showSelectionButtons = true,
  className = ''
}) => {
  const hasMarketOptimized = !!tripleOptimizationResults.market_optimized_portfolio;
  const recommendation = tripleOptimizationResults.optimization_metadata?.recommendation;

  return (
    <div className={`mt-6 pt-6 ${className}`} style={{ borderTop: `1px solid ${visualizationTheme.border}` }}>
      <h5 className="font-semibold text-center mb-4" style={{ color: visualizationTheme.text.primary }}>
        Portfolio Comparison
      </h5>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <th className="text-left py-3 px-2 font-medium" style={{ color: visualizationTheme.text.secondary }}>Metric</th>
              <th className="text-center py-3 px-2" style={{ 
                borderLeft: recommendation === 'current' ? '3px solid #ef4444' : '1px solid ' + visualizationTheme.border
              }}>
                <div className="flex flex-col items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-red-500 border border-white shadow-sm"></div>
                  <span className="font-medium text-sm" style={{ color: visualizationTheme.text.primary }}>Current</span>
                  {recommendation === 'current' && (
                    <span className="text-xs font-medium" style={{ color: '#ef4444' }}>Recommended</span>
                  )}
                </div>
              </th>
              <th className="text-center py-3 px-2" style={{ 
                borderLeft: recommendation === 'weights' ? '3px solid #3b82f6' : '1px solid ' + visualizationTheme.border
              }}>
                <div className="flex flex-col items-center gap-1">
                  <div className="w-3 h-3 rotate-45" style={{ width: '12px', height: '12px', backgroundColor: '#3b82f6', border: '2px solid white' }}></div>
                  <span className="font-medium text-sm" style={{ color: visualizationTheme.text.primary }}>Weights-Opt</span>
                  {recommendation === 'weights' && (
                    <span className="text-xs font-medium" style={{ color: '#3b82f6' }}>Recommended</span>
                  )}
                </div>
              </th>
              {/* Market-Opt column - only show if market_optimized_portfolio exists */}
              {hasMarketOptimized && (
                <th className="text-center py-3 px-2" style={{ 
                  borderLeft: recommendation === 'market' ? '3px solid #22c55e' : '1px solid ' + visualizationTheme.border
                }}>
                  <div className="flex flex-col items-center gap-1">
                    <svg width="14" height="14" viewBox="0 0 16 16">
                      <polygon points="8,1 10,6 15,6 11,9 13,15 8,11 3,15 5,9 1,6 6,6" fill="#22c55e" stroke="#fff" strokeWidth="0.5"/>
                    </svg>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="font-medium text-sm cursor-help" style={{ color: visualizationTheme.text.primary }}>Market-Opt</span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">Explores the entire market to find the best stocks and allocations, potentially replacing some of your current holdings for better risk-adjusted returns.</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    {recommendation === 'market' && (
                      <span className="text-xs font-medium" style={{ color: '#22c55e' }}>Recommended</span>
                    )}
                  </div>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {/* Expected Return Row */}
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Expected Return
              </td>
              <td className="text-center py-3 px-2">
                <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                  {formatPercent(tripleOptimizationResults.current_portfolio.metrics.expected_return)}
                </span>
              </td>
              <td className="text-center py-3 px-2">
                <div>
                  <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                    {formatPercent(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.expected_return)}
                  </span>
                  {tripleOptimizationResults.comparison?.weights_vs_current && (
                    <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.return_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ({tripleOptimizationResults.comparison.weights_vs_current.return_difference >= 0 ? '+' : ''}{formatPercent(tripleOptimizationResults.comparison.weights_vs_current.return_difference)})
                    </span>
                  )}
                </div>
              </td>
              {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                                          {formatPercent(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.expected_return)}
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.return_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.return_difference >= 0 ? '+' : ''}{formatPercent(tripleOptimizationResults.comparison.market_vs_current.return_difference)})
                                          </span>
                                        )}
                                      </div>
                                    </td>
              )}
            </tr>
            {/* Risk Row */}
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Risk (Volatility)
              </td>
              <td className="text-center py-3 px-2">
                <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                  {formatPercent(tripleOptimizationResults.current_portfolio.metrics.risk)}
                </span>
              </td>
              <td className="text-center py-3 px-2">
                <div>
                  <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                    {formatPercent(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.risk)}
                  </span>
                  {tripleOptimizationResults.comparison?.weights_vs_current && (
                    <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.risk_difference <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ({tripleOptimizationResults.comparison.weights_vs_current.risk_difference <= 0 ? '' : '+'}{formatPercent(tripleOptimizationResults.comparison.weights_vs_current.risk_difference)})
                    </span>
                  )}
                </div>
              </td>
              {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                                          {formatPercent(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.risk)}
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.risk_difference <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.risk_difference <= 0 ? '' : '+'}{formatPercent(tripleOptimizationResults.comparison.market_vs_current.risk_difference)})
                                          </span>
                                        )}
                                      </div>
                                    </td>
              )}
            </tr>
            {/* Sharpe Ratio Row */}
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Sharpe Ratio
              </td>
              <td className="text-center py-3 px-2">
                <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                  {formatNumber(tripleOptimizationResults.current_portfolio.metrics.sharpe_ratio, { maxDecimals: 2 })}
                </span>
              </td>
              <td className="text-center py-3 px-2">
                <div>
                  <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                    {formatNumber(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio, { maxDecimals: 2 })}
                  </span>
                  {tripleOptimizationResults.comparison?.weights_vs_current && (
                    <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ({tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference >= 0 ? '+' : ''}{formatNumber(tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference, { maxDecimals: 2 })})
                    </span>
                  )}
                </div>
              </td>
              {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                                    <td className="text-center py-3 px-2">
                                      <div>
                                        <span className="font-semibold" style={{ color: visualizationTheme.text.primary }}>
                                          {formatNumber(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.metrics.sharpe_ratio, { maxDecimals: 2 })}
                                        </span>
                                        {tripleOptimizationResults.comparison?.market_vs_current && (
                                          <span className={`ml-1 text-xs ${tripleOptimizationResults.comparison.market_vs_current.sharpe_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ({tripleOptimizationResults.comparison.market_vs_current.sharpe_difference >= 0 ? '+' : ''}{formatNumber(tripleOptimizationResults.comparison.market_vs_current.sharpe_difference, { maxDecimals: 2 })})
                                          </span>
                                        )}
                                      </div>
                                    </td>
              )}
            </tr>
            {/* Tickers Row */}
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Tickers
              </td>
              <td className="text-center py-3 px-2">
                <span className="text-xs" style={{ color: visualizationTheme.text.secondary }}>
                  {tripleOptimizationResults.current_portfolio.tickers.join(', ') || 'N/A'}
                </span>
              </td>
              <td className="text-center py-3 px-2">
                <span className="text-xs" style={{ color: visualizationTheme.text.secondary }}>
                  {tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.tickers.join(', ') || 'N/A'}
                </span>
              </td>
              {/* Market-Opt cell - with tooltip showing all tickers */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                <td className="text-center py-3 px-2">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="text-xs cursor-help underline decoration-dotted" style={{ color: visualizationTheme.text.secondary }}>
                          {tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.tickers.slice(0, 5).join(', ')}
                          {(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.tickers.length > 5) && '...'}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-sm">
                        <p className="font-semibold text-xs mb-1">Market-Opt tickers</p>
                        <p className="text-xs whitespace-normal">
                          {tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.tickers.join(', ')}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </td>
              )}
            </tr>
            {/* Top 3 Weights Row */}
            <tr className="border-b" style={{ borderColor: visualizationTheme.border }}>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Top 3 Weights
              </td>
              <td className="text-center py-3 px-2">
                <span className="text-xs" style={{ color: visualizationTheme.text.secondary }}>
                  {Object.entries(tripleOptimizationResults.current_portfolio.weights || {})
                    .sort(([,a], [,b]) => (b as number) - (a as number))
                    .slice(0, 3)
                    .map(([ticker, weight]) => `${ticker}: ${formatPercent(weight as number)}`)
                    .join(', ') || 'Equal'}
                </span>
              </td>
              <td className="text-center py-3 px-2">
                <span className="text-xs" style={{ color: visualizationTheme.text.secondary }}>
                  {Object.entries(tripleOptimizationResults.weights_optimized_portfolio.optimized_portfolio.weights || {})
                    .sort(([,a], [,b]) => (b as number) - (a as number))
                    .slice(0, 3)
                    .map(([ticker, weight]) => `${ticker}: ${formatPercent(weight as number)}`)
                    .join(', ') || 'N/A'}
                </span>
              </td>
              {/* Market-Opt cell - with tooltip showing all weight allocations */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                <td className="text-center py-3 px-2">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="text-xs cursor-help underline decoration-dotted" style={{ color: visualizationTheme.text.secondary }}>
                          {Object.entries(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.weights || {})
                            .sort(([,a], [,b]) => (b as number) - (a as number))
                            .slice(0, 3)
                            .map(([ticker, weight]) => `${ticker}: ${formatPercent(weight as number)}`)
                            .join(', ') || 'N/A'}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-sm">
                        <p className="font-semibold text-xs mb-1">Market-Opt weight allocations</p>
                        <ul className="text-xs list-none space-y-0.5">
                          {Object.entries(tripleOptimizationResults.market_optimized_portfolio.optimized_portfolio.weights || {})
                            .sort(([,a], [,b]) => (b as number) - (a as number))
                            .map(([ticker, weight]) => (
                              <li key={ticker}>{ticker}: {formatPercent(weight as number)}</li>
                            ))}
                        </ul>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </td>
              )}
            </tr>
            {/* Key Strengths Row */}
            <tr>
              <td className="py-3 px-2 font-medium" style={{ color: visualizationTheme.text.primary }}>
                Key Strengths
              </td>
              <td className="text-center py-3 px-2">
                <div className="text-xs space-y-1" style={{ color: visualizationTheme.text.secondary }}>
                  <div>• Your actual holdings</div>
                  <div>• Familiar stocks</div>
                </div>
              </td>
              <td className="text-center py-3 px-2">
                <div className="text-xs space-y-1" style={{ color: visualizationTheme.text.secondary }}>
                  {tripleOptimizationResults.comparison.weights_vs_current.risk_difference < 0 && (
                    <div>• Lower risk</div>
                  )}
                  {tripleOptimizationResults.comparison.weights_vs_current.sharpe_difference > 0 && (
                    <div>• Better Sharpe</div>
                  )}
                  <div>• Same tickers</div>
                  <div>• Easy transition</div>
                </div>
              </td>
              {/* Market-Opt cell - only show if market_optimized_portfolio exists */}
              {hasMarketOptimized && tripleOptimizationResults.market_optimized_portfolio && (
                <td className="text-center py-3 px-2">
                  <div className="text-xs space-y-1" style={{ color: visualizationTheme.text.secondary }}>
                    {tripleOptimizationResults.comparison.market_vs_current && tripleOptimizationResults.comparison.market_vs_current.return_difference > 0 && (
                      <div>• Higher return</div>
                    )}
                    {tripleOptimizationResults.comparison.best_sharpe === 'market' && (
                      <div>• Best Sharpe</div>
                    )}
                    <div>• Market diversity</div>
                    <div>• New opportunities</div>
                  </div>
                </td>
              )}
            </tr>
            {/* Selection Buttons Row - Dynamic based on market_optimized_portfolio */}
            {showSelectionButtons && onPortfolioSelect && (
              <tr>
                <td colSpan={hasMarketOptimized ? 4 : 3} className="py-4 px-2">
                  <div className={`grid gap-3 ${hasMarketOptimized ? 'grid-cols-3' : 'grid-cols-2'}`}>
                    <Button
                      variant={selectedPortfolio === 'current' ? 'default' : 'outline'}
                      onClick={() => onPortfolioSelect('current')}
                      className={`w-full text-sm ${selectedPortfolio === 'current' ? 'bg-red-600 hover:bg-red-700 text-white border-red-600' : 'border-gray-300'}`}
                    >
                      {selectedPortfolio === 'current' ? 'Selected' : 'Select Current'}
                    </Button>
                    <Button
                      variant={selectedPortfolio === 'weights' ? 'default' : 'outline'}
                      onClick={() => onPortfolioSelect('weights')}
                      className={`w-full text-sm ${selectedPortfolio === 'weights' ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-600' : 'border-gray-300'}`}
                    >
                      {selectedPortfolio === 'weights' ? 'Selected' : 'Select Weights-Opt'}
                    </Button>
                    {/* Market-Opt button - only show if market_optimized_portfolio exists */}
                    {hasMarketOptimized && (
                      <Button
                        variant={selectedPortfolio === 'market' ? 'default' : 'outline'}
                        onClick={() => onPortfolioSelect('market')}
                        className={`w-full text-sm ${selectedPortfolio === 'market' ? 'bg-green-600 hover:bg-green-700 text-white border-green-600' : 'border-gray-300'}`}
                      >
                        {selectedPortfolio === 'market' ? 'Selected' : 'Select Market-Opt'}
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
