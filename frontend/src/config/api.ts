const API_BASE_URL = 'http://127.0.0.1:8000';

export const API_ENDPOINTS = {
  // Portfolio endpoints
  TICKER_SEARCH: (query: string, limit: number = 10) => `${API_BASE_URL}/api/portfolio/ticker/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  TWO_ASSET_ANALYSIS: (ticker1: string, ticker2: string) => `${API_BASE_URL}/api/portfolio/two-asset-analysis?ticker1=${ticker1}&ticker2=${ticker2}`,
  RECOMMENDATIONS: (riskProfile: string) => `${API_BASE_URL}/api/portfolio/recommendations/${riskProfile}`,
  
  // Mini-lesson endpoints
  MINI_LESSON_ASSETS: `${API_BASE_URL}/api/portfolio/mini-lesson/assets`,
  MINI_LESSON_RANDOM_PAIR: `${API_BASE_URL}/api/portfolio/mini-lesson/random-pair`,
  MINI_LESSON_CUSTOM_PORTFOLIO: `${API_BASE_URL}/api/portfolio/mini-lesson/custom-portfolio`,
  
  // Legacy endpoints (keep for backward compatibility)
  TICKERS: `${API_BASE_URL}/api/portfolio/tickers`,
  TICKER_INFO: (ticker: string) => `${API_BASE_URL}/api/portfolio/ticker/${ticker}/info`,
  MINI_LESSON_ANALYSIS: (testCaseId: number) => `${API_BASE_URL}/api/portfolio/mini-lesson/analysis/${testCaseId}`,
  RISK_RETURN_ANALYSIS: `${API_BASE_URL}/api/portfolio/analytics/risk-return-analysis`,
  SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution`,
  ENHANCED_SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution/enhanced`,
} as const; 