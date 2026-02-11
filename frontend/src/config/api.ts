// Use environment variable for production, empty string for development (uses Vite proxy)
// In production (Railway), VITE_API_BASE_URL will be set to the backend URL
// In development, empty string uses Vite proxy configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// API v1 prefix (backend serves all portfolio endpoints under /api/v1/portfolio)
const API_V1_PORTFOLIO = `${API_BASE_URL}/api/v1/portfolio`;

export const API_ENDPOINTS = {
  // Portfolio endpoints
  TICKER_SEARCH: (query: string, limit: number = 10) => `${API_V1_PORTFOLIO}/search-tickers?q=${encodeURIComponent(query)}&limit=${limit}`,
  TWO_ASSET_ANALYSIS: (ticker1: string, ticker2: string) => `${API_V1_PORTFOLIO}/two-asset-analysis?ticker1=${ticker1}&ticker2=${ticker2}`,
  RECOMMENDATIONS: (riskProfile: string) => `${API_V1_PORTFOLIO}/recommendations/${riskProfile}`,

  // Portfolio metrics and calculation
  CALCULATE_METRICS: `${API_V1_PORTFOLIO}/calculate-metrics`,

  // Portfolio optimization endpoints
  OPTIMIZE_RISK_PARITY: `${API_V1_PORTFOLIO}/optimize/risk-parity`,
  OPTIMIZE_MEAN_VARIANCE: `${API_V1_PORTFOLIO}/optimize/mean-variance`,
  OPTIMIZE_MVO: `${API_V1_PORTFOLIO}/optimization/mvo`,
  ELIGIBLE_TICKERS: (params?: string) => `${API_V1_PORTFOLIO}/optimization/eligible-tickers${params ? `?${params}` : ''}`,
  TICKER_METRICS: `${API_V1_PORTFOLIO}/optimization/ticker-metrics`,

  // Portfolio monitoring and rebalancing
  CHECK_REBALANCING: `${API_V1_PORTFOLIO}/rebalance/check`,
  PERFORMANCE_TRACKING: `${API_V1_PORTFOLIO}/monitor/performance-tracking`,

  // Advanced analytics
  PERFORMANCE_ATTRIBUTION: `${API_V1_PORTFOLIO}/analytics/performance-attribution`,
  RISK_DECOMPOSITION: `${API_V1_PORTFOLIO}/analytics/risk-decomposition`,

  // Mini-lesson endpoints
  MINI_LESSON_ASSETS: `${API_V1_PORTFOLIO}/mini-lesson/assets`,
  MINI_LESSON_RANDOM_PAIR: `${API_V1_PORTFOLIO}/mini-lesson/random-pair`,
  MINI_LESSON_CUSTOM_PORTFOLIO: `${API_V1_PORTFOLIO}/mini-lesson/custom-portfolio`,

  // Cache management
  CACHE_WARM: `${API_V1_PORTFOLIO}/warm-cache`,
  CACHE_STATUS: `${API_V1_PORTFOLIO}/cache-status`,
  CACHE_CLEAR: `${API_V1_PORTFOLIO}/clear-cache`,

  // Ticker management
  MASTER_TICKERS: `${API_V1_PORTFOLIO}/tickers/master`,
  REFRESH_TICKERS: `${API_V1_PORTFOLIO}/tickers/refresh`,
  TICKER_TABLE_DATA: `${API_V1_PORTFOLIO}/ticker-table/data`,
  REFRESH_TICKER_TABLE: `${API_V1_PORTFOLIO}/ticker-table/refresh`,

  // Health check (portfolio service health under v1)
  HEALTH_CHECK: `${API_V1_PORTFOLIO}/health`,

  // Legacy endpoints (keep for backward compatibility)
  TICKERS: `${API_V1_PORTFOLIO}/tickers/available`,
  MINI_LESSON_ANALYSIS: (testCaseId: number) => `${API_V1_PORTFOLIO}/mini-lesson/analysis/${testCaseId}`,
  RISK_RETURN_ANALYSIS: `${API_V1_PORTFOLIO}/analytics/risk-return-analysis`,
  SECTOR_DISTRIBUTION: `${API_V1_PORTFOLIO}/sector-distribution/enhanced`,
  ENHANCED_SECTOR_DISTRIBUTION: `${API_V1_PORTFOLIO}/sector-distribution/enhanced`,
} as const; 