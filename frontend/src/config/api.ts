// Use environment variable for production, empty string for development (uses Vite proxy)
// In production (Railway), VITE_API_BASE_URL will be set to the backend URL
// In development, empty string uses Vite proxy configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const API_ENDPOINTS = {
  // Portfolio endpoints
  TICKER_SEARCH: (query: string, limit: number = 10) => `${API_BASE_URL}/api/portfolio/search-tickers?q=${encodeURIComponent(query)}&limit=${limit}`,
  TWO_ASSET_ANALYSIS: (ticker1: string, ticker2: string) => `${API_BASE_URL}/api/portfolio/two-asset-analysis?ticker1=${ticker1}&ticker2=${ticker2}`,
  RECOMMENDATIONS: (riskProfile: string) => `${API_BASE_URL}/api/portfolio/recommendations/${riskProfile}`,
  
  // Portfolio metrics and calculation
  CALCULATE_METRICS: `${API_BASE_URL}/api/portfolio/calculate-metrics`,
  
  // Portfolio optimization endpoints
  OPTIMIZE_RISK_PARITY: `${API_BASE_URL}/api/portfolio/optimize/risk-parity`,
  OPTIMIZE_MEAN_VARIANCE: `${API_BASE_URL}/api/portfolio/optimize/mean-variance`,
  OPTIMIZE_MVO: `${API_BASE_URL}/api/portfolio/optimization/mvo`,
  ELIGIBLE_TICKERS: (params?: string) => `${API_BASE_URL}/api/portfolio/optimization/eligible-tickers${params ? `?${params}` : ''}`,
  TICKER_METRICS: `${API_BASE_URL}/api/portfolio/optimization/ticker-metrics`,
  
  // Portfolio monitoring and rebalancing
  CHECK_REBALANCING: `${API_BASE_URL}/api/portfolio/rebalance/check`,
  PERFORMANCE_TRACKING: `${API_BASE_URL}/api/portfolio/monitor/performance-tracking`,
  
  // Advanced analytics
  PERFORMANCE_ATTRIBUTION: `${API_BASE_URL}/api/portfolio/analytics/performance-attribution`,
  RISK_DECOMPOSITION: `${API_BASE_URL}/api/portfolio/analytics/risk-decomposition`,
  
  // Mini-lesson endpoints
  MINI_LESSON_ASSETS: `${API_BASE_URL}/api/portfolio/mini-lesson/assets`,
  MINI_LESSON_RANDOM_PAIR: `${API_BASE_URL}/api/portfolio/mini-lesson/random-pair`,
  MINI_LESSON_CUSTOM_PORTFOLIO: `${API_BASE_URL}/api/portfolio/mini-lesson/custom-portfolio`,
  
  // Cache management
  CACHE_WARM: `${API_BASE_URL}/api/portfolio/cache/warm`,
  CACHE_STATUS: `${API_BASE_URL}/api/portfolio/cache/status`,
  CACHE_CLEAR: `${API_BASE_URL}/api/portfolio/cache/clear`,
  
  // Ticker management
  MASTER_TICKERS: `${API_BASE_URL}/api/portfolio/tickers/master`,
  REFRESH_TICKERS: `${API_BASE_URL}/api/portfolio/tickers/refresh`,
  TICKER_TABLE_DATA: `${API_BASE_URL}/api/portfolio/ticker-table/data`,
  REFRESH_TICKER_TABLE: `${API_BASE_URL}/api/portfolio/ticker-table/refresh`,
  
  // Health check
  HEALTH_CHECK: `${API_BASE_URL}/api/portfolio/health`,
  
  // Legacy endpoints (keep for backward compatibility)
  TICKERS: `${API_BASE_URL}/api/portfolio/tickers`,
  MINI_LESSON_ANALYSIS: (testCaseId: number) => `${API_BASE_URL}/api/portfolio/mini-lesson/analysis/${testCaseId}`,
  RISK_RETURN_ANALYSIS: `${API_BASE_URL}/api/portfolio/analytics/risk-return-analysis`,
  SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution`,
  ENHANCED_SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution/enhanced`,
} as const; 