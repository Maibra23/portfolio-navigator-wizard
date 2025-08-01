import pandas as pd
from functools import lru_cache
import logging
from typing import List
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fast startup mode - set to False to fetch all tickers from Wikipedia
FAST_STARTUP = os.getenv('FAST_STARTUP', 'false').lower() == 'true'

@lru_cache()
def get_sp500():
    """Fetch S&P 500 tickers from Wikipedia or use fallback for fast startup"""
    if FAST_STARTUP:
        # Use comprehensive fallback for fast startup
        fallback_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
            'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
            'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
            'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
            'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE',
            'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC', 'KO', 'PEP', 'ABT', 'TMO',
            'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ', 'TXN', 'HON', 'LLY', 'UNP', 'LOW',
            'IBM', 'CAT', 'GS', 'AXP', 'SPGI', 'PLD', 'T', 'DE', 'RTX', 'ISRG', 'CVX',
            'XOM', 'COP', 'EOG', 'SLB', 'HAL', 'BKR', 'MPC', 'PSX', 'VLO', 'DVN', 'PXD',
            'OXY', 'FANG', 'EOG', 'MRO', 'APA', 'HES', 'NOV', 'FTI', 'NBR', 'HP', 'RIG',
            'DO', 'NE', 'SDRL', 'PTEN', 'WFT', 'SPN', 'OIS', 'CLR', 'CHK', 'SWN', 'RRC',
            'NFX', 'QEP', 'WLL', 'CRZO', 'GST', 'LPI', 'PE', 'PDCE', 'WPX', 'AR', 'CXO',
            'PXD', 'EOG', 'FANG', 'MRO', 'APA', 'HES', 'NOV', 'FTI', 'NBR', 'HP', 'RIG',
            'DO', 'NE', 'SDRL', 'PTEN', 'WFT', 'SPN', 'OIS', 'CLR', 'CHK', 'SWN', 'RRC',
            'NFX', 'QEP', 'WLL', 'CRZO', 'GST', 'LPI', 'PE', 'PDCE', 'WPX', 'AR', 'CXO'
        ]
        logger.info(f"Fast startup: Using fallback S&P 500 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers
    
    try:
        df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        tickers = df.Symbol.str.upper().tolist()
        logger.info(f"Successfully fetched {len(tickers)} S&P 500 tickers from Wikipedia")
        return tickers
    except Exception as e:
        logger.error(f"Error fetching S&P 500 tickers: {e}")
        # Fallback to major S&P 500 tickers
        fallback_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
            'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
            'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
            'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
            'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE',
            'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC', 'KO', 'PEP', 'ABT', 'TMO',
            'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ', 'TXN', 'HON', 'LLY', 'UNP', 'LOW',
            'IBM', 'CAT', 'GS', 'AXP', 'SPGI', 'PLD', 'T', 'DE', 'RTX', 'ISRG'
        ]
        logger.info(f"Using fallback S&P 500 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers

@lru_cache()
def get_nasdaq100():
    """Fetch Nasdaq 100 tickers from Wikipedia or use fallback for fast startup"""
    if FAST_STARTUP:
        # Use comprehensive fallback for fast startup
        fallback_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
            'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
            'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
            'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
            'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE',
            'OKTA', 'CRWD', 'ZS', 'PLTR', 'COIN', 'RBLX', 'HOOD', 'SNAP', 'PINS', 'TWTR',
            'UBER', 'LYFT', 'DASH', 'ABNB', 'RDFN', 'ZM', 'DOCU', 'SQ', 'SHOP', 'ETSY',
            'MELI', 'SE', 'JD', 'BIDU', 'NTES', 'TCEHY', 'PDD', 'BABA', 'NIO', 'XPEV',
            'LI', 'XPENG', 'BILI', 'HUYA', 'DOYU', 'TME', 'VIPS', 'JD', 'BIDU', 'NTES'
        ]
        logger.info(f"Fast startup: Using fallback Nasdaq 100 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers
    
    try:
        # Try multiple approaches to get Nasdaq 100
        approaches = [
            # Approach 1: Try different table indices
            lambda: _try_nasdaq_table_indices(),
            # Approach 2: Try different Wikipedia pages
            lambda: _try_nasdaq_alternative_pages(),
            # Approach 3: Manual parsing with better error handling
            lambda: _try_nasdaq_manual_parsing()
        ]
        
        for approach in approaches:
            try:
                tickers = approach()
                if tickers and len(tickers) >= 90:  # Should have close to 100 tickers
                    logger.info(f"Successfully fetched {len(tickers)} Nasdaq 100 tickers")
                    return tickers
            except Exception as e:
                logger.warning(f"Nasdaq 100 approach failed: {e}")
                continue
        
        # If all approaches fail, use comprehensive fallback
        raise Exception("All Nasdaq 100 fetching approaches failed")
        
    except Exception as e:
        logger.error(f"Error fetching Nasdaq 100 tickers: {e}")
        # Comprehensive fallback with all major Nasdaq 100 tickers
        fallback_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM',
            'PYPL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'ADI', 'KLAC', 'MU', 'LRCX', 'ASML',
            'ORLY', 'PAYX', 'ROST', 'BIIB', 'GILD', 'REGN', 'VRTX', 'MELI', 'JD', 'PDD',
            'BIDU', 'NTES', 'ATVI', 'EA', 'TTWO', 'ZM', 'TEAM', 'SNPS', 'CDNS', 'ANSS',
            'ADSK', 'CTAS', 'FAST', 'ODFL', 'CHTR', 'CMCSA', 'COST', 'MAR', 'BKNG', 'EXPE',
            'OKTA', 'CRWD', 'ZS', 'PLTR', 'COIN', 'RBLX', 'HOOD', 'SNAP', 'PINS', 'TWTR',
            'UBER', 'LYFT', 'DASH', 'ABNB', 'RDFN', 'ZM', 'DOCU', 'SQ', 'SHOP', 'ETSY',
            'MELI', 'SE', 'JD', 'BIDU', 'NTES', 'TCEHY', 'PDD', 'BABA', 'NIO', 'XPEV',
            'LI', 'XPENG', 'BILI', 'HUYA', 'DOYU', 'TME', 'VIPS', 'JD', 'BIDU', 'NTES'
        ]
        logger.info(f"Using comprehensive fallback Nasdaq 100 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers

def _try_nasdaq_table_indices():
    """Try different table indices for Nasdaq 100"""
    for table_index in [3, 2, 1, 0]:
        try:
            df = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[table_index]
            # Look for Symbol column (case insensitive)
            symbol_col = None
            for col in df.columns:
                if isinstance(col, str) and 'symbol' in col.lower():
                    symbol_col = col
                    break
            
            if symbol_col:
                tickers = df[symbol_col].str.upper().tolist()
                # Filter out non-ticker entries
                tickers = [t for t in tickers if isinstance(t, str) and len(t) <= 5 and t.isalpha()]
                if len(tickers) >= 90:
                    logger.info(f"Found {len(tickers)} Nasdaq 100 tickers in table {table_index}")
                    return tickers
        except Exception as e:
            logger.warning(f"Failed to fetch from table {table_index}: {e}")
            continue
    return []

def _try_nasdaq_alternative_pages():
    """Try alternative Wikipedia pages for Nasdaq 100"""
    alternative_urls = [
        "https://en.wikipedia.org/wiki/Nasdaq-100",
        "https://en.wikipedia.org/wiki/List_of_Nasdaq-100_companies"
    ]
    
    for url in alternative_urls:
        try:
            tables = pd.read_html(url)
            for i, df in enumerate(tables):
                # Look for Symbol column
                for col in df.columns:
                    if isinstance(col, str) and 'symbol' in col.lower():
                        tickers = df[col].str.upper().tolist()
                        tickers = [t for t in tickers if isinstance(t, str) and len(t) <= 5 and t.isalpha()]
                        if len(tickers) >= 90:
                            logger.info(f"Found {len(tickers)} Nasdaq 100 tickers from {url} table {i}")
                            return tickers
        except Exception as e:
            logger.warning(f"Failed to fetch from {url}: {e}")
            continue
    return []

def _try_nasdaq_manual_parsing():
    """Manual parsing approach for Nasdaq 100"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for tables with ticker symbols
        tables = soup.find_all('table', {'class': 'wikitable'})
        for table in tables:
            rows = table.find_all('tr')
            tickers = []
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if len(text) <= 5 and text.isalpha() and text.isupper():
                        tickers.append(text)
            
            if len(tickers) >= 90:
                logger.info(f"Found {len(tickers)} Nasdaq 100 tickers via manual parsing")
                return tickers
    except Exception as e:
        logger.warning(f"Manual parsing failed: {e}")
    
    return []

@lru_cache()
def get_dow30():
    """Fetch Dow Jones Industrial Average tickers from Wikipedia or use fallback for fast startup"""
    if FAST_STARTUP:
        # Use fallback for fast startup
        fallback_tickers = [
            'AAPL', 'MSFT', 'JPM', 'JNJ', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC',
            'KO', 'PEP', 'ABT', 'TMO', 'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ',
            'TXN', 'HON', 'LLY', 'UNP', 'LOW', 'IBM', 'CAT', 'GS', 'AXP', 'SPGI'
        ]
        logger.info(f"Fast startup: Using fallback Dow 30 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers
    
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
        # Try different table indices for Dow 30
        for table_index in [1, 0, 2]:
            try:
                df = tables[table_index]
                # Look for Symbol column
                symbol_col = None
                for col in df.columns:
                    if isinstance(col, str) and 'symbol' in col.lower():
                        symbol_col = col
                        break
                
                if symbol_col:
                    tickers = df[symbol_col].str.upper().tolist()
                    tickers = [t for t in tickers if isinstance(t, str) and len(t) <= 5 and t.isalpha()]
                    if len(tickers) >= 25:  # Should have around 30 tickers
                        logger.info(f"Successfully fetched {len(tickers)} Dow 30 tickers from Wikipedia (table {table_index})")
                        return tickers
            except Exception as e:
                logger.warning(f"Failed to fetch Dow 30 from table {table_index}: {e}")
                continue
        
        raise Exception("All Dow 30 table indices failed")
        
    except Exception as e:
        logger.error(f"Error fetching Dow 30 tickers: {e}")
        # Fallback to major Dow 30 tickers
        fallback_tickers = [
            'AAPL', 'MSFT', 'JPM', 'JNJ', 'V', 'PG', 'HD', 'MA', 'DIS', 'BAC',
            'KO', 'PEP', 'ABT', 'TMO', 'COST', 'DHR', 'ACN', 'WMT', 'MRK', 'VZ',
            'TXN', 'HON', 'LLY', 'UNP', 'LOW', 'IBM', 'CAT', 'GS', 'AXP', 'SPGI'
        ]
        logger.info(f"Using fallback Dow 30 tickers: {len(fallback_tickers)} tickers")
        return fallback_tickers

@lru_cache()
def get_all_tickers():
    """Get combined and deduplicated list of all tickers (S&P 500 + Nasdaq 100 + Dow 30)"""
    sp500_tickers = get_sp500()
    nasdaq100_tickers = get_nasdaq100()
    dow30_tickers = get_dow30()
    
    # Combine and deduplicate
    all_tickers = sorted(set(sp500_tickers + nasdaq100_tickers + dow30_tickers))
    
    logger.info(f"Combined ticker list: {len(all_tickers)} unique tickers")
    logger.info(f"  S&P 500: {len(sp500_tickers)} tickers")
    logger.info(f"  Nasdaq 100: {len(nasdaq100_tickers)} tickers")
    logger.info(f"  Dow 30: {len(dow30_tickers)} tickers")
    
    return all_tickers

def validate_ticker(tkr):
    """Validate if a ticker exists in the master list"""
    return tkr.upper() in get_all_tickers()

def search_tickers(query, limit=10):
    """Search tickers by prefix"""
    q = query.strip().upper()
    all_tickers = get_all_tickers()
    matches = [t for t in all_tickers if t.startswith(q)][:limit]
    return matches

class TickerStore:
    """
    Legacy class for backward compatibility
    All methods now delegate to the new functions above
    """
    
    def __init__(self):
        # Initialize by calling get_all_tickers to load data
        self._tickers = get_all_tickers()
        self._sp500_tickers = get_sp500()
        self._nasdaq100_tickers = get_nasdaq100()
        self._dow30_tickers = get_dow30()
    
    def validate_ticker(self, ticker: str) -> bool:
        """Check if a ticker exists in the master list"""
        return validate_ticker(ticker)
    
    def search_tickers(self, query: str, limit: int = 10) -> List[str]:
        """Search tickers by query string"""
        return search_tickers(query, limit)
    
    def get_all_tickers(self) -> List[str]:
        """Get the complete master ticker list"""
        return get_all_tickers()
    
    def get_ticker_count(self) -> int:
        """Get the total number of tickers"""
        return len(get_all_tickers())
    
    def refresh_tickers(self):
        """Refresh ticker lists from sources (clears cache)"""
        logger.info("Refreshing ticker lists...")
        # Clear the LRU cache to force fresh fetch
        get_sp500.cache_clear()
        get_nasdaq100.cache_clear()
        get_dow30.cache_clear()
        get_all_tickers.cache_clear()
        
        # Re-initialize
        self._tickers = get_all_tickers()
        self._sp500_tickers = get_sp500()
        self._nasdaq100_tickers = get_nasdaq100()
        self._dow30_tickers = get_dow30()
        
        logger.info(f"Ticker lists refreshed: {len(self._tickers)} total tickers")
    
    @property
    def sp500_tickers(self):
        """Get S&P 500 tickers"""
        return self._sp500_tickers
    
    @property
    def nasdaq100_tickers(self):
        """Get Nasdaq 100 tickers"""
        return self._nasdaq100_tickers
    
    @property
    def dow30_tickers(self):
        """Get Dow 30 tickers"""
        return self._dow30_tickers
    
    @property
    def master_tickers(self):
        """Get master ticker list"""
        return self._tickers

# Global instance for backward compatibility
ticker_store = TickerStore() 