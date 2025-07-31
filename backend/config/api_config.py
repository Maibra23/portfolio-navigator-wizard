import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

load_dotenv()

# Alpha Vantage API Configuration
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required. Please set it in your .env file")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Yahoo Finance Configuration (no API key needed)
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com"

# Data Requirements
MINIMUM_DATA_YEARS = 15
DAILY_DATA_POINTS = MINIMUM_DATA_YEARS * 252  # 252 trading days per year

# Timeline Configuration
USE_LIVE_DATA = os.getenv('USE_LIVE_DATA', 'false').lower() == 'true'
END_DATE = datetime.now() if USE_LIVE_DATA else datetime(2025, 6, 1)  # Configurable end date
START_DATE = END_DATE - relativedelta(years=MINIMUM_DATA_YEARS)  # Calendar-aware 15 years back

# Environment Configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# API Rate Limits (environment-specific)
if ENVIRONMENT == 'production':
    ALPHA_VANTAGE_RATE_LIMIT = 1200  # Higher limit for paid plans
    YAHOO_FINANCE_RETRY_ATTEMPTS = 3
    CACHE_DURATION_HOURS = 48  # Longer cache in production
else:
    ALPHA_VANTAGE_RATE_LIMIT = 500  # Free tier limit
    YAHOO_FINANCE_RETRY_ATTEMPTS = 2
    CACHE_DURATION_HOURS = 24  # Standard cache duration

# Cache Configuration
CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '100'))  # Maximum number of cached tickers
CACHE_CLEANUP_INTERVAL = int(os.getenv('CACHE_CLEANUP_INTERVAL', '3600'))  # Cleanup every hour (seconds)
CACHE_PERSISTENCE = os.getenv('CACHE_PERSISTENCE', 'memory').lower()  # 'memory' or 'file' 