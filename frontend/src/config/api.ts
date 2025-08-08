const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Existing endpoints
  TICKERS: `${API_BASE_URL}/api/portfolio/tickers`,
  TICKER_INFO: (ticker: string) => `${API_BASE_URL}/api/portfolio/ticker/${ticker}/info`,
  MINI_LESSON_ANALYSIS: (testCaseId: number) => `${API_BASE_URL}/api/portfolio/mini-lesson/analysis/${testCaseId}`,
  
  // New endpoints for Risk-Return Analysis and Sector Distribution
  RISK_RETURN_ANALYSIS: `${API_BASE_URL}/api/portfolio/analytics/risk-return-analysis`,
  SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution`,
  ENHANCED_SECTOR_DISTRIBUTION: `${API_BASE_URL}/api/portfolio/sector-distribution/enhanced`,
} as const; 