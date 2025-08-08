"""
Simple ticker table endpoint with return and risk metrics
"""
import gzip
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
import pandas as pd

from utils.enhanced_data_fetcher import enhanced_data_fetcher

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/ticker-table/data")
async def get_simple_ticker_table_data():
    """
    Get simple ticker table data with return and risk metrics
    Returns: Basic ticker information with essential metrics
    """
    try:
        # Get all tickers from the enhanced data fetcher
        all_tickers = enhanced_data_fetcher.all_tickers
        
        ticker_data = []
        
        for ticker in all_tickers:
            try:
                # Get price data using enhanced_data_fetcher's Redis connection
                price_key = f"ticker_data:prices:{ticker}"
                price_raw = enhanced_data_fetcher.r.get(price_key)
                
                # Get sector/company data
                sector_key = f"ticker_data:sector:{ticker}"
                sector_raw = enhanced_data_fetcher.r.get(sector_key)
                
                if price_raw and sector_raw:
                    # Parse price data
                    price_dict = json.loads(gzip.decompress(price_raw).decode())
                    prices = list(price_dict.values())
                    dates = list(price_dict.keys())
                    
                    # Parse sector data
                    sector_info = json.loads(sector_raw.decode())
                    
                    # Calculate data points and date range
                    data_points = len(prices)
                    first_date = dates[0] if dates else "N/A"
                    last_date = dates[-1] if dates else "N/A"
                    last_price = prices[-1] if prices else 0
                    
                    # Calculate return and risk metrics
                    annualized_return = 0
                    annualized_risk = 0
                    
                    if len(prices) > 1:
                        try:
                            # Calculate returns
                            returns = []
                            for i in range(1, len(prices)):
                                if prices[i-1] > 0:
                                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                                    returns.append(ret)
                            
                            if returns:
                                # Annualized return (assuming monthly data)
                                avg_monthly_return = sum(returns) / len(returns)
                                annualized_return = avg_monthly_return * 12 * 100  # Convert to percentage
                                
                                # Annualized volatility (risk)
                                if len(returns) > 1:
                                    monthly_volatility = pd.Series(returns).std()
                                    annualized_risk = monthly_volatility * (12 ** 0.5) * 100  # Convert to percentage
                        except Exception as e:
                            logger.warning(f"Error calculating metrics for {ticker}: {e}")
                    
                    ticker_info = {
                        "ticker": ticker,
                        "companyName": sector_info.get("companyName", ticker),
                        "sector": sector_info.get("sector", "Unknown"),
                        "industry": sector_info.get("industry", "Unknown"),
                        "exchange": sector_info.get("exchange", "Unknown"),
                        "country": sector_info.get("country", "Unknown"),
                        "dataPoints": data_points,
                        "firstDate": first_date,
                        "lastDate": last_date,
                        "lastPrice": round(last_price, 2) if last_price else 0,
                        "annualizedReturn": round(annualized_return, 2),
                        "annualizedRisk": round(annualized_risk, 2),
                        "status": "active",
                        "lastUpdated": datetime.now().isoformat()
                    }
                    
                    ticker_data.append(ticker_info)
                else:
                    # Missing data
                    ticker_info = {
                        "ticker": ticker,
                        "companyName": ticker,
                        "sector": "Unknown",
                        "industry": "Unknown",
                        "exchange": "Unknown",
                        "country": "Unknown",
                        "dataPoints": 0,
                        "firstDate": "N/A",
                        "lastDate": "N/A",
                        "lastPrice": 0,
                        "annualizedReturn": 0,
                        "annualizedRisk": 0,
                        "status": "missing_data",
                        "lastUpdated": datetime.now().isoformat()
                    }
                    ticker_data.append(ticker_info)
                    
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                # Add error entry
                ticker_info = {
                    "ticker": ticker,
                    "companyName": ticker,
                    "sector": "Error",
                    "industry": "Error",
                    "exchange": "Error",
                    "country": "Error",
                    "dataPoints": 0,
                    "firstDate": "N/A",
                    "lastDate": "N/A",
                    "lastPrice": 0,
                    "annualizedReturn": 0,
                    "annualizedRisk": 0,
                    "status": "error",
                    "lastUpdated": datetime.now().isoformat()
                }
                ticker_data.append(ticker_info)
        
        # Sort by ticker
        ticker_data.sort(key=lambda x: x["ticker"])
        
        return {
            "tickers": ticker_data,
            "total": len(ticker_data),
            "lastUpdated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ticker table data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting ticker table data: {str(e)}")
