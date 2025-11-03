import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class APIConfig:
    """Class-based configuration for API settings"""
    
    def __init__(self):
        # Environment
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.is_production = self.environment == 'production'
        
        # Alpha Vantage Configuration
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.alpha_vantage_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"
        
        # Yahoo Finance Configuration
        self.yahoo_finance_base_url = "https://query1.finance.yahoo.com"
        
        # Data Requirements
        self.minimum_data_years = 15
        self.daily_data_points = self.minimum_data_years * 252  # 252 trading days per year
        
        # Timeline Configuration
        self.use_live_data = os.getenv('USE_LIVE_DATA', 'false').lower() == 'true'
        self.end_date = datetime.now() if self.use_live_data else datetime(2025, 6, 1)
        self.start_date = self.end_date - relativedelta(years=self.minimum_data_years)
        
        # API Rate Limits (environment-specific)
        if self.is_production:
            self.alpha_vantage_rate_limit = 1200  # Higher limit for paid plans
            self.yahoo_finance_retry_attempts = 3
            self.cache_duration_hours = 48
        else:
            self.alpha_vantage_rate_limit = 500  # Free tier limit
            self.yahoo_finance_retry_attempts = 2
            self.cache_duration_hours = 24
        
        # Cache Configuration
        self.cache_max_size = int(os.getenv('CACHE_MAX_SIZE', '100'))
        self.cache_cleanup_interval = int(os.getenv('CACHE_CLEANUP_INTERVAL', '3600'))
        self.cache_persistence = os.getenv('CACHE_PERSISTENCE', 'memory').lower()
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.enable_debug_logs = os.getenv('ENABLE_DEBUG_LOGS', 'false').lower() == 'true'
    
        # Validated Master List Configuration
        # When True: Use pre-validated master list (only tickers confirmed to work with Yahoo)
        # When False: Use current inference path with full master list + normalization
        self.use_validated_master_list = os.getenv('USE_VALIDATED_MASTER_LIST', 'false').lower() == 'true'
    
    def get_cache_config(self) -> dict:
        """Get cache configuration as dictionary"""
        return {
            'max_size': self.cache_max_size,
            'duration_hours': self.cache_duration_hours,
            'cleanup_interval': self.cache_cleanup_interval,
            'persistence': self.cache_persistence
        }
    
    def get_api_limits(self) -> dict:
        """Get API rate limits as dictionary"""
        return {
            'alpha_vantage_daily': self.alpha_vantage_rate_limit,
            'yahoo_finance_retries': self.yahoo_finance_retry_attempts
        }
    
    def get_timeline_config(self) -> dict:
        """Get timeline configuration as dictionary"""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'minimum_years': self.minimum_data_years,
            'use_live_data': self.use_live_data
        }
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        try:
            assert self.alpha_vantage_key, "Alpha Vantage API key is required"
            assert self.minimum_data_years > 0, "Minimum data years must be positive"
            assert self.cache_max_size > 0, "Cache max size must be positive"
            assert self.alpha_vantage_rate_limit > 0, "Alpha Vantage rate limit must be positive"
            return True
        except AssertionError as e:
            raise ValueError(f"Configuration validation failed: {e}")

# Global configuration instance
config = APIConfig()

# Validate configuration on import
config.validate_config() 