import json
import requests
from typing import List, Set
import logging

logger = logging.getLogger(__name__)

class TickerStore:
    """
    Manages the master ticker list combining S&P 500 and Nasdaq 100
    Provides validation and search functionality
    """
    
    def __init__(self):
        self.master_tickers: Set[str] = set()
        self.sp500_tickers: List[str] = []
        self.nasdaq100_tickers: List[str] = []
        self._load_tickers()
    
    def _fetch_sp500_tickers(self) -> List[str]:
        """Fetch S&P 500 tickers from Wikipedia"""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Simple parsing - in production you might want to use BeautifulSoup
            lines = response.text.split('\n')
            tickers = []
            
            for line in lines:
                if 'class="text"' in line and 'href="/wiki/' in line:
                    # Extract ticker from table row
                    parts = line.split('>')
                    for part in parts:
                        if part.startswith('<a href="/wiki/') and not part.startswith('<a href="/wiki/List'):
                            ticker = part.split('"')[1].split('/')[-1]
                            if len(ticker) <= 5 and ticker.isalpha():
                                tickers.append(ticker.upper())
                                break
            
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers")
            return tickers[:500]  # Ensure we don't exceed 500
            
        except Exception as e:
            logger.error(f"Error fetching S&P 500 tickers: {e}")
            # Fallback to a subset of major S&P 500 tickers
            fallback_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ',
                'JPM', 'V', 'PG', 'HD', 'MA', 'DIS', 'PYPL', 'BAC', 'ADBE', 'CRM',
                'NFLX', 'KO', 'PEP', 'ABT', 'TMO', 'AVGO', 'COST', 'DHR', 'ACN', 'WMT',
                'MRK', 'VZ', 'TXN', 'QCOM', 'HON', 'LLY', 'UNP', 'LOW', 'IBM', 'CAT',
                'GS', 'AXP', 'SPGI', 'GILD', 'PLD', 'T', 'DE', 'RTX', 'ISRG', 'ADI'
            ]
            logger.info(f"Using fallback S&P 500 tickers: {len(fallback_tickers)} tickers")
            return fallback_tickers
    
    def _fetch_nasdaq100_tickers(self) -> List[str]:
        """Fetch Nasdaq 100 tickers"""
        try:
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Simple parsing - in production you might want to use BeautifulSoup
            lines = response.text.split('\n')
            tickers = []
            
            for line in lines:
                if 'class="text"' in line and 'href="/wiki/' in line:
                    # Extract ticker from table row
                    parts = line.split('>')
                    for part in parts:
                        if part.startswith('<a href="/wiki/') and not part.startswith('<a href="/wiki/Nasdaq'):
                            ticker = part.split('"')[1].split('/')[-1]
                            if len(ticker) <= 5 and ticker.isalpha():
                                tickers.append(ticker.upper())
                                break
            
            logger.info(f"Fetched {len(tickers)} Nasdaq 100 tickers")
            return tickers[:100]  # Ensure we don't exceed 100
            
        except Exception as e:
            logger.error(f"Error fetching Nasdaq 100 tickers: {e}")
            # Fallback to major Nasdaq 100 tickers
            fallback_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
                'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
                'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
                'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
                'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE'
            ]
            logger.info(f"Using fallback Nasdaq 100 tickers: {len(fallback_tickers)} tickers")
            return fallback_tickers
    
    def _load_tickers(self):
        """Load and combine ticker lists"""
        logger.info("Loading ticker lists...")
        
        # Fetch tickers from sources
        self.sp500_tickers = self._fetch_sp500_tickers()
        self.nasdaq100_tickers = self._fetch_nasdaq100_tickers()
        
        # Combine and deduplicate
        all_tickers = set(self.sp500_tickers + self.nasdaq100_tickers)
        self.master_tickers = all_tickers
        
        logger.info(f"Master ticker list created: {len(self.master_tickers)} unique tickers")
        logger.info(f"S&P 500: {len(self.sp500_tickers)} tickers")
        logger.info(f"Nasdaq 100: {len(self.nasdaq100_tickers)} tickers")
        
        # If we have no tickers, use a basic set
        if len(self.master_tickers) == 0:
            logger.warning("No tickers loaded, using basic fallback set")
            basic_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
                'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
                'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
                'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
                'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE',
                'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC', 'KO', 'PEP', 'ABT', 'TMO',
                'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ', 'TXN', 'HON', 'LLY', 'UNP', 'LOW',
                'IBM', 'CAT', 'GS', 'AXP', 'SPGI', 'PLD', 'T', 'DE', 'RTX', 'ISRG'
            ]
            self.master_tickers = set(basic_tickers)
            self.sp500_tickers = basic_tickers[:50]
            self.nasdaq100_tickers = basic_tickers[50:]
            logger.info(f"Using basic fallback: {len(self.master_tickers)} tickers")
    
    def validate_ticker(self, ticker: str) -> bool:
        """Check if a ticker exists in the master list"""
        return ticker.upper() in self.master_tickers
    
    def search_tickers(self, query: str, limit: int = 10) -> List[str]:
        """Search tickers by query string"""
        query = query.upper()
        matches = []
        
        for ticker in self.master_tickers:
            if query in ticker:
                matches.append(ticker)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_all_tickers(self) -> List[str]:
        """Get the complete master ticker list"""
        return list(self.master_tickers)
    
    def get_ticker_count(self) -> int:
        """Get the total number of tickers"""
        return len(self.master_tickers)
    
    def refresh_tickers(self):
        """Refresh ticker lists from sources"""
        logger.info("Refreshing ticker lists...")
        self._load_tickers()

# Global instance
ticker_store = TickerStore() 