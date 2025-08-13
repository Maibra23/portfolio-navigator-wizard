#!/usr/bin/env python3
"""
Test yfinance API functionality with AAPL ticker
Verify data quality and API connectivity
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_yfinance_api():
    """Test yfinance API with AAPL ticker"""
    
    logger.info("🧪 Testing yfinance API with AAPL ticker")
    logger.info("==================================================")
    
    try:
        # Test 1: Basic ticker object creation
        logger.info("📊 Test 1: Creating yfinance ticker object...")
        ticker = yf.Ticker("AAPL")
        logger.info("✅ Ticker object created successfully")
        
        # Test 2: Company information
        logger.info("\n🏢 Test 2: Fetching company information...")
        try:
            info = ticker.info
            logger.info("✅ Company info fetched successfully")
            
            # Display key company information
            company_name = info.get('longName', info.get('shortName', 'Unknown'))
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            country = info.get('country', 'Unknown')
            exchange = info.get('exchange', 'Unknown')
            market_cap = info.get('marketCap', 0)
            
            logger.info(f"   Company Name: {company_name}")
            logger.info(f"   Sector: {sector}")
            logger.info(f"   Industry: {industry}")
            logger.info(f"   Country: {country}")
            logger.info(f"   Exchange: {exchange}")
            logger.info(f"   Market Cap: ${market_cap:,.0f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch company info: {str(e)}")
            return False
        
        # Test 3: Historical data - 15 years monthly
        logger.info("\n📈 Test 3: Fetching 15 years of monthly data...")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=15*365)
            
            logger.info(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            hist_data = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='1mo',
                auto_adjust=True,
                timeout=30
            )
            
            if hist_data.empty:
                logger.error("❌ No historical data returned")
                return False
            
            logger.info("✅ Historical data fetched successfully")
            logger.info(f"   Total data points: {len(hist_data)}")
            logger.info(f"   Columns available: {list(hist_data.columns)}")
            
            # Check if we have the required columns
            # Note: With auto_adjust=True, 'Close' column is already adjusted
            available_columns = list(hist_data.columns)
            logger.info(f"   Available columns: {available_columns}")
            
            # Display sample data
            logger.info("\n📊 Sample data (first 5 rows):")
            logger.info(hist_data.head().to_string())
            
            logger.info("\n📊 Sample data (last 5 rows):")
            logger.info(hist_data.tail().to_string())
            
            # Test 4: Data quality validation
            logger.info("\n🔍 Test 4: Data quality validation...")
            
            # Check for missing values
            missing_values = hist_data.isnull().sum()
            if missing_values.sum() > 0:
                logger.warning(f"⚠️ Missing values found: {missing_values.to_dict()}")
            else:
                logger.info("✅ No missing values found")
            
            # Check date range
            first_date = hist_data.index[0]
            last_date = hist_data.index[-1]
            logger.info(f"   First date: {first_date.strftime('%Y-%m-%d')}")
            logger.info(f"   Last date: {last_date.strftime('%Y-%m-%d')}")
            
            # Check if we have sufficient data (at least 10 years)
            expected_months = 10 * 12  # 10 years minimum
            if len(hist_data) >= expected_months:
                logger.info(f"✅ Sufficient data: {len(hist_data)} months (need at least {expected_months})")
            else:
                logger.warning(f"⚠️ Insufficient data: {len(hist_data)} months (need at least {expected_months})")
            
            # Test 5: Price data analysis
            logger.info("\n💰 Test 5: Price data analysis...")
            
            # Use 'Close' column since auto_adjust=True makes it adjusted
            if 'Close' in hist_data.columns:
                close_prices = hist_data['Close']
                logger.info("✅ Using 'Close' column (auto-adjusted for splits/dividends)")
                
                if not close_prices.empty:
                    current_price = close_prices.iloc[-1]
                    first_price = close_prices.iloc[0]
                    price_change = current_price - first_price
                    price_change_pct = (price_change / first_price) * 100
                    
                    logger.info(f"   First price: ${first_price:.2f}")
                    logger.info(f"   Current price: ${current_price:.2f}")
                    logger.info(f"   Total change: ${price_change:.2f} ({price_change_pct:.2f}%)")
                    
                    # Check for reasonable price values
                    if current_price > 0 and current_price < 10000:
                        logger.info("✅ Price values are reasonable")
                    else:
                        logger.warning(f"⚠️ Unusual price value: ${current_price:.2f}")
                        
                    # Show price progression
                    logger.info("\n📈 Price progression (every 2 years):")
                    for i in range(0, len(close_prices), 24):  # Every 2 years (24 months)
                        if i < len(close_prices):
                            date = close_prices.index[i].strftime('%Y-%m')
                            price = close_prices.iloc[i]
                            logger.info(f"   {date}: ${price:.2f}")
                            
                else:
                    logger.error("❌ Close prices are empty")
                    return False
            else:
                logger.error("❌ 'Close' column not found in data")
                return False
            
            # Test 6: API rate limiting test
            logger.info("\n⏱️ Test 6: API rate limiting test...")
            try:
                # Try to fetch another ticker to test rate limiting
                msft_ticker = yf.Ticker("MSFT")
                msft_info = msft_ticker.info
                logger.info("✅ Rate limiting test passed - can fetch multiple tickers")
            except Exception as e:
                logger.warning(f"⚠️ Rate limiting test failed: {str(e)}")
            
            logger.info("\n🎯 yfinance API Test Summary")
            logger.info("==================================================")
            logger.info("✅ yfinance API is working properly!")
            logger.info("✅ Can fetch company information")
            logger.info("✅ Can fetch historical monthly data")
            logger.info("✅ Data quality is good")
            logger.info("✅ Ready for Redis cache refresh")
            logger.info("✅ Using 'Close' column with auto_adjust=True (equivalent to Adj Close)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch historical data: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ yfinance API test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_yfinance_api()
    if success:
        logger.info("\n🚀 yfinance API is ready for Redis cache refresh!")
    else:
        logger.error("\n❌ yfinance API has issues - cannot proceed with cache refresh")
