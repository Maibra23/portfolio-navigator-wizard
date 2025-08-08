from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation
from typing import List, Dict, Optional
import logging
import numpy as np
import pandas as pd
import redis
import json
import gzip
from utils.enhanced_data_fetcher import enhanced_data_fetcher
from utils.ticker_store import ticker_store
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("/ticker/search")
def search_tickers(q: str, limit: int = 10):
    """
    Search tickers by query string
    Returns: List of matching tickers with cache status
    """
    try:
        if not q or len(q) < 1:
            raise HTTPException(status_code=400, detail="Search query required")
        
        results = enhanced_data_fetcher.search_tickers(q, limit)
        
        return {
            "query": q,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching tickers: {str(e)}")

@router.get("/returns/monthly")
def get_monthly_returns(ticker: str):
    """
    Get monthly returns data for a ticker
    Returns: Monthly prices and dates (cached if available)
    """
    try:
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker required")
        
        # Validate ticker
        if not ticker_store.validate_ticker(ticker):
            raise HTTPException(status_code=404, detail=f"Invalid ticker: {ticker}")
        
        data = enhanced_data_fetcher.get_monthly_data(ticker)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        return {
            "ticker": ticker.upper(),
            "dates": data['dates'],
            "prices": data['prices'],
            "data_points": data['data_points'],
            "source": data['source']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching monthly data: {str(e)}")

@router.post("/cache/warm")
def warm_cache():
    """
    Warm the cache with monthly data for all master tickers
    Returns: Cache warming results
    """
    try:
        logger.info("Starting cache warming process...")
        results = enhanced_data_fetcher.warm_cache()
        
        return {
            "status": "success",
            "results": results,
            "message": "Cache warming completed"
        }
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error warming cache: {str(e)}")

@router.get("/cache/status")
def get_cache_status():
    """
    Get cache status
    Returns: Cache statistics and system information
    """
    try:
        status = enhanced_data_fetcher.get_cache_status()
        
        return {
            "system_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@router.delete("/cache/clear")
def clear_cache():
    """
    Clear all cached monthly data
    """
    try:
        results = enhanced_data_fetcher.clear_cache()
        
        return {
            "status": "success",
            "results": results,
            "message": "Cache cleared for all tickers"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@router.get("/tickers/master")
def get_master_tickers():
    """
    Get the complete master ticker list
    Returns: All available tickers
    """
    try:
        tickers = ticker_store.get_all_tickers()
        
        return {
            "total_tickers": len(tickers),
            "tickers": tickers,
            "sp500_count": len(ticker_store.sp500_tickers),
            "nasdaq100_count": len(ticker_store.nasdaq100_tickers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting master tickers: {str(e)}")

@router.post("/tickers/refresh")
def refresh_tickers():
    """
    Refresh ticker lists from sources
    """
    try:
        ticker_store.refresh_tickers()
        
        return {
            "status": "success",
            "message": "Ticker lists refreshed",
            "total_tickers": ticker_store.get_ticker_count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing tickers: {str(e)}")

@router.get("/recommendations/{risk_profile}", response_model=List[PortfolioResponse])
def get_portfolio_recommendations(risk_profile: str):
    """Generate portfolio recommendations based on risk profile"""
    
    # Define portfolio templates for each risk profile
    templates = {
        'very-conservative': [
            {
                'name': 'Conservative Growth Seeker',
                'allocations': [
                    {'symbol': 'VTI', 'allocation': 15, 'name': 'Vanguard Total Stock Market ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 70, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 5, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'},
                    {'symbol': 'BNDX', 'allocation': 10, 'name': 'Vanguard Total International Bond ETF', 'assetType': 'etf'}
                ]
            },
            {
                'name': 'Income Focus',
                'allocations': [
                    {'symbol': 'VYM', 'allocation': 20, 'name': 'Vanguard High Dividend Yield ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 60, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'SCHD', 'allocation': 15, 'name': 'Schwab U.S. Dividend Equity ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 5, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            }
        ],
        'conservative': [
            {
                'name': 'Balanced Conservative',
                'allocations': [
                    {'symbol': 'VTI', 'allocation': 40, 'name': 'Vanguard Total Stock Market ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 50, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            },
            {
                'name': 'Dividend Growth',
                'allocations': [
                    {'symbol': 'VYM', 'allocation': 30, 'name': 'Vanguard High Dividend Yield ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 45, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'SCHD', 'allocation': 20, 'name': 'Schwab U.S. Dividend Equity ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 5, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            }
        ],
        'moderate': [
            {
                'name': 'Moderate Growth',
                'allocations': [
                    {'symbol': 'VTI', 'allocation': 60, 'name': 'Vanguard Total Stock Market ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 30, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            },
            {
                'name': 'Growth & Value',
                'allocations': [
                    {'symbol': 'VUG', 'allocation': 25, 'name': 'Vanguard Growth ETF', 'assetType': 'etf'},
                    {'symbol': 'VTV', 'allocation': 25, 'name': 'Vanguard Value ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 30, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'},
                    {'symbol': 'VXUS', 'allocation': 10, 'name': 'Vanguard Total International Stock ETF', 'assetType': 'etf'}
                ]
            }
        ],
        'aggressive': [
            {
                'name': 'Growth Focused',
                'allocations': [
                    {'symbol': 'VTI', 'allocation': 75, 'name': 'Vanguard Total Stock Market ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 15, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            },
            {
                'name': 'Sector Rotation',
                'allocations': [
                    {'symbol': 'XLK', 'allocation': 25, 'name': 'Technology Select Sector SPDR Fund', 'assetType': 'etf'},
                    {'symbol': 'XLF', 'allocation': 20, 'name': 'Financial Select Sector SPDR Fund', 'assetType': 'etf'},
                    {'symbol': 'XLV', 'allocation': 20, 'name': 'Health Care Select Sector SPDR Fund', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 15, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'},
                    {'symbol': 'VXUS', 'allocation': 10, 'name': 'Vanguard Total International Stock ETF', 'assetType': 'etf'}
                ]
            }
        ],
        'very-aggressive': [
            {
                'name': 'Maximum Growth',
                'allocations': [
                    {'symbol': 'VTI', 'allocation': 85, 'name': 'Vanguard Total Stock Market ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 5, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            },
            {
                'name': 'Tech & Growth',
                'allocations': [
                    {'symbol': 'XLK', 'allocation': 35, 'name': 'Technology Select Sector SPDR Fund', 'assetType': 'etf'},
                    {'symbol': 'VUG', 'allocation': 30, 'name': 'Vanguard Growth ETF', 'assetType': 'etf'},
                    {'symbol': 'VXUS', 'allocation': 20, 'name': 'Vanguard Total International Stock ETF', 'assetType': 'etf'},
                    {'symbol': 'AGG', 'allocation': 5, 'name': 'iShares Core U.S. Aggregate Bond ETF', 'assetType': 'etf'},
                    {'symbol': 'VNQ', 'allocation': 10, 'name': 'Vanguard Real Estate ETF', 'assetType': 'etf'}
                ]
            }
        ]
    }
    
    # Get templates for the risk profile, default to moderate if not found
    profile_templates = templates.get(risk_profile, templates['moderate'])
    
    recommendations = []
    for template in profile_templates:
        # Convert template to PortfolioAllocation objects
        allocations = [
            PortfolioAllocation(
                symbol=alloc['symbol'],
                allocation=alloc['allocation'],
                name=alloc['name'],
                assetType=alloc['assetType']
            ) for alloc in template['allocations']
        ]
        
        # Calculate metrics for this portfolio
        weighted_return = 0.0
        weighted_risk = 0.0
        
        for stock in allocations:
            # Assign expected returns based on asset type and risk profile
            if stock.assetType == 'bond':
                base_return = 0.03
            elif stock.assetType == 'etf':
                base_return = 0.08
            else:
                base_return = 0.10
            
            # Adjust based on risk profile
            risk_multiplier = {
                'very-conservative': 0.6,
                'conservative': 0.8,
                'moderate': 1.0,
                'aggressive': 1.2,
                'very-aggressive': 1.4
            }.get(risk_profile, 1.0)
            
            stock_return = base_return * risk_multiplier
            stock_risk = base_return * 1.5 * risk_multiplier
            
            weighted_return += (stock.allocation / 100) * stock_return
            weighted_risk += (stock.allocation / 100) * stock_risk
        
        # Calculate diversification score
        num_assets = len(allocations)
        max_allocation = max(stock.allocation for stock in allocations)
        asset_diversity = min(100, num_assets * 20)
        allocation_diversity = max(0, 100 - (max_allocation - 100/num_assets) * 2)
        diversification_score = (asset_diversity + allocation_diversity) / 2
        
        # Calculate Sharpe ratio
        risk_free_rate = 0.02
        sharpe_ratio = (weighted_return - risk_free_rate) / weighted_risk if weighted_risk > 0 else 0
        
        recommendations.append(PortfolioResponse(
            portfolio=allocations,
            expectedReturn=weighted_return * 100,
            risk=weighted_risk * 100,
            diversificationScore=diversification_score,
            sharpeRatio=sharpe_ratio
        ))
    
    return recommendations

@router.post("", response_model=PortfolioResponse)
def create_portfolio(data: PortfolioRequest):
    # Validate portfolio has allocations
    if not data.selectedStocks:
        return PortfolioResponse(
            portfolio=[],
            expectedReturn=0.0,
            risk=0.0,
            diversificationScore=0.0,
            sharpeRatio=0.0
        )
    
    # Define risk profile characteristics
    risk_profiles = {
        'very-conservative': {'expected_return': 0.03, 'risk': 0.05, 'bond_ratio': 0.8},
        'conservative': {'expected_return': 0.05, 'risk': 0.08, 'bond_ratio': 0.6},
        'moderate': {'expected_return': 0.08, 'risk': 0.12, 'bond_ratio': 0.4},
        'aggressive': {'expected_return': 0.12, 'risk': 0.18, 'bond_ratio': 0.2},
        'very-aggressive': {'expected_return': 0.16, 'risk': 0.25, 'bond_ratio': 0.0}
    }
    
    profile = risk_profiles.get(data.riskProfile, risk_profiles['moderate'])
    
    # Calculate portfolio metrics based on allocations
    total_allocation = sum(stock.allocation for stock in data.selectedStocks)
    
    if total_allocation == 0:
        return PortfolioResponse(
            portfolio=data.selectedStocks,
            expectedReturn=0.0,
            risk=0.0,
            diversificationScore=0.0,
            sharpeRatio=0.0
        )
    
    # Normalize allocations to 100%
    normalized_portfolio = []
    for stock in data.selectedStocks:
        normalized_allocation = (stock.allocation / total_allocation) * 100
        normalized_portfolio.append(PortfolioAllocation(
            symbol=stock.symbol,
            allocation=normalized_allocation,
            name=stock.name,
            assetType=stock.assetType
        ))
    
    # Calculate weighted expected return and risk
    weighted_return = 0.0
    weighted_risk = 0.0
    
    for stock in normalized_portfolio:
        # Assign expected returns based on asset type and risk profile
        if stock.assetType == 'bond':
            base_return = 0.03  # Conservative bond return
        elif stock.assetType == 'etf':
            base_return = 0.08  # Market ETF return
        else:  # stock
            base_return = 0.10  # Individual stock return
        
        # Adjust based on risk profile
        risk_multiplier = {
            'very-conservative': 0.6,
            'conservative': 0.8,
            'moderate': 1.0,
            'aggressive': 1.2,
            'very-aggressive': 1.4
        }.get(data.riskProfile, 1.0)
        
        stock_return = base_return * risk_multiplier
        stock_risk = base_return * 1.5 * risk_multiplier  # Risk is typically 1.5x return
        
        weighted_return += (stock.allocation / 100) * stock_return
        weighted_risk += (stock.allocation / 100) * stock_risk
    
    # Calculate diversification score based on number of assets and allocation distribution
    num_assets = len(normalized_portfolio)
    max_allocation = max(stock.allocation for stock in normalized_portfolio)
    
    # Diversification score: higher for more assets and more even distribution
    asset_diversity = min(100, num_assets * 20)  # 20 points per asset, max 100
    allocation_diversity = max(0, 100 - (max_allocation - 100/num_assets) * 2)  # Penalty for concentration
    diversification_score = (asset_diversity + allocation_diversity) / 2
    
    # Calculate Sharpe ratio (assuming risk-free rate of 2%)
    risk_free_rate = 0.02
    sharpe_ratio = (weighted_return - risk_free_rate) / weighted_risk if weighted_risk > 0 else 0
    
    return PortfolioResponse(
        portfolio=normalized_portfolio,
        expectedReturn=weighted_return * 100,  # Convert to percentage
        risk=weighted_risk * 100,  # Convert to percentage
        diversificationScore=diversification_score,
        sharpeRatio=sharpe_ratio
    ) 

@router.get("/two-asset-analysis")
def two_asset_analysis(ticker1: str, ticker2: str):
    """
    Get two-asset analysis for educational mini-lesson
    Returns: Portfolio analysis with real data from enhanced data fetcher
    """
    try:
        if not ticker1 or not ticker2:
            raise HTTPException(status_code=400, detail="Both tickers required")
        
        # Validate tickers
        if not ticker_store.validate_ticker(ticker1):
            raise HTTPException(status_code=404, detail=f"Invalid ticker: {ticker1}")
        if not ticker_store.validate_ticker(ticker2):
            raise HTTPException(status_code=404, detail=f"Invalid ticker: {ticker2}")
        
        # Get monthly data for both tickers
        data1 = enhanced_data_fetcher.get_monthly_data(ticker1)
        data2 = enhanced_data_fetcher.get_monthly_data(ticker2)
        
        if not data1 or not data2:
            raise HTTPException(status_code=404, detail="Data not available for one or both tickers")
        
        # Calculate basic statistics (simplified for demo)
        prices1 = data1['prices']
        prices2 = data2['prices']
        
        # Calculate returns
        returns1 = []
        returns2 = []
        for i in range(1, len(prices1)):
            if prices1[i-1] > 0:
                returns1.append((prices1[i] - prices1[i-1]) / prices1[i-1])
        for i in range(1, len(prices2)):
            if prices2[i-1] > 0:
                returns2.append((prices2[i] - prices2[i-1]) / prices2[i-1])
        
        # Calculate annualized statistics
        if len(returns1) > 0 and len(returns2) > 0:
            
            # Annualized return (assuming monthly data)
            annualized_return1 = (np.mean(returns1) * 12) if len(returns1) > 0 else 0.15
            annualized_return2 = (np.mean(returns2) * 12) if len(returns2) > 0 else 0.12
            
            # Annualized volatility
            annualized_volatility1 = (np.std(returns1) * np.sqrt(12)) if len(returns1) > 0 else 0.25
            annualized_volatility2 = (np.std(returns2) * np.sqrt(12)) if len(returns2) > 0 else 0.20
            
            # Correlation
            min_len = min(len(returns1), len(returns2))
            if min_len > 1:
                correlation = np.corrcoef(returns1[:min_len], returns2[:min_len])[0, 1]
                if np.isnan(correlation):
                    correlation = 0.3
            else:
                correlation = 0.3
        else:
            # Fallback values
            annualized_return1, annualized_return2 = 0.25, 0.15
            annualized_volatility1, annualized_volatility2 = 0.35, 0.25
            correlation = 0.3
        
        # Create portfolio combinations
        portfolios = []
        weights_combinations = [
            [1.0, 0.0],    # 100% ticker1
            [0.75, 0.25],  # 75% ticker1, 25% ticker2
            [0.5, 0.5],    # 50% each
            [0.25, 0.75],  # 25% ticker1, 75% ticker2
            [0.0, 1.0]     # 100% ticker2
        ]
        
        for w1, w2 in weights_combinations:
            # Portfolio return
            portfolio_return = w1 * annualized_return1 + w2 * annualized_return2
            
            # Portfolio risk
            portfolio_risk = np.sqrt(
                w1**2 * annualized_volatility1**2 + 
                w2**2 * annualized_volatility2**2 + 
                2 * w1 * w2 * annualized_volatility1 * annualized_volatility2 * correlation
            )
            
            # Sharpe ratio (assuming 4% risk-free rate)
            risk_free_rate = 0.04
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            portfolios.append({
                "weights": [w1, w2],
                "return": portfolio_return,
                "risk": portfolio_risk,
                "sharpe_ratio": sharpe_ratio
            })
        
        return {
            "ticker1": ticker1.upper(),
            "ticker2": ticker2.upper(),
            "asset1_stats": {
                "ticker": ticker1.upper(),
                "annualized_return": annualized_return1,
                "annualized_volatility": annualized_volatility1,
                "price_history": prices1,
                "last_price": prices1[-1] if prices1 else 0,
                "start_date": data1['dates'][0] if data1['dates'] else "2020-01-01",
                "end_date": data1['dates'][-1] if data1['dates'] else "2024-01-01",
                "data_source": "yahoo_finance"
            },
            "asset2_stats": {
                "ticker": ticker2.upper(),
                "annualized_return": annualized_return2,
                "annualized_volatility": annualized_volatility2,
                "price_history": prices2,
                "last_price": prices2[-1] if prices2 else 0,
                "start_date": data2['dates'][0] if data2['dates'] else "2020-01-01",
                "end_date": data2['dates'][-1] if data2['dates'] else "2024-01-01",
                "data_source": "yahoo_finance"
            },
            "correlation": correlation,
            "portfolios": portfolios
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in two-asset analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error in two-asset analysis: {str(e)}")

# Redis connection for enhanced analytics
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Pydantic models for new endpoints
class RiskProfile(BaseModel):
    risk_tolerance: str
    investment_horizon: str
    capital: float

class PortfolioAnalyticsRequest(BaseModel):
    selected_stocks: List[PortfolioAllocation]
    risk_profile: RiskProfile
    capital: float

# Helper function to get price data from Redis
def get_price_data_from_redis(tickers: List[str]) -> Dict[str, pd.Series]:
    price_data = {}
    for ticker in tickers:
        try:
            # Try to get compressed data first
            compressed_data = redis_client.get(f"price_data:{ticker}")
            if compressed_data:
                decompressed_data = gzip.decompress(compressed_data.encode('latin1'))
                data = json.loads(decompressed_data.decode('utf-8'))
                price_data[ticker] = pd.Series(data)
            else:
                # Fallback to uncompressed data
                data = redis_client.get(f"price_data:{ticker}")
                if data:
                    price_data[ticker] = pd.Series(json.loads(data))
        except Exception as e:
            print(f"Error getting data for {ticker}: {e}")
            continue
    return price_data

# Helper function to calculate annualized metrics
def calculate_annualized_metrics(returns: pd.Series) -> Dict[str, float]:
    if len(returns) < 2:
        return {"return": 0.0, "risk": 0.0, "sharpe_ratio": 0.0}
    
    # Calculate annualized return (assuming monthly data)
    annualized_return = (1 + returns.mean()) ** 12 - 1
    
    # Calculate annualized volatility
    annualized_volatility = returns.std() * np.sqrt(12)
    
    # Calculate Sharpe ratio (assuming risk-free rate of 2%)
    risk_free_rate = 0.02
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0
    
    return {
        "return": annualized_return,
        "risk": annualized_volatility,
        "sharpe_ratio": sharpe_ratio
    }

# Helper function to generate efficient frontier points
def generate_efficient_frontier_points(returns_data: Dict[str, pd.Series], selected_stocks: List[PortfolioAllocation], num_points: int = 50):
    if len(selected_stocks) < 2:
        return []
    
    tickers = [stock.symbol for stock in selected_stocks]
    returns_df = pd.DataFrame({ticker: returns_data[ticker] for ticker in tickers if ticker in returns_data})
    
    if returns_df.empty or len(returns_df.columns) < 2:
        return []
    
    # Calculate correlation matrix
    correlation_matrix = returns_df.corr()
    
    # Monte Carlo simulation for efficient frontier
    frontier_points = []
    np.random.seed(42)  # For reproducibility
    
    for _ in range(num_points):
        # Generate random weights
        weights = np.random.random(len(returns_df.columns))
        weights = weights / weights.sum()
        
        # Calculate portfolio return and risk
        portfolio_return = (returns_df.mean() * weights).sum() * 12  # Annualized
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(returns_df.cov() * 12, weights)))
        
        # Calculate Sharpe ratio
        risk_free_rate = 0.02
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
        
        frontier_points.append({
            "return": portfolio_return,
            "risk": portfolio_risk,
            "sharpe_ratio": sharpe_ratio,
            "weights": weights.tolist()
        })
    
    # Sort by risk
    frontier_points.sort(key=lambda x: x["risk"])
    return frontier_points

# Helper function to calculate diversification score
def calculate_diversification_score(correlation_matrix: pd.DataFrame, selected_stocks: List[PortfolioAllocation]) -> float:
    if len(selected_stocks) < 2:
        return 0.0
    
    # Calculate average correlation (excluding diagonal)
    correlations = []
    for i in range(len(correlation_matrix)):
        for j in range(i+1, len(correlation_matrix)):
            correlations.append(abs(correlation_matrix.iloc[i, j]))
    
    avg_correlation = np.mean(correlations) if correlations else 0
    
    # Calculate concentration (Herfindahl index)
    total_allocation = sum(stock.allocation for stock in selected_stocks)
    if total_allocation == 0:
        return 0.0
    
    concentration = sum((stock.allocation / total_allocation) ** 2 for stock in selected_stocks)
    
    # Diversification score: lower correlation and lower concentration = higher score
    diversification_score = (1 - avg_correlation) * (1 - concentration) * len(selected_stocks) / 10
    
    return min(diversification_score, 1.0)  # Cap at 1.0

@router.post("/analytics/risk-return-analysis")
async def risk_return_analysis(request: PortfolioAnalyticsRequest):
    try:
        selected_stocks = request.selected_stocks
        capital = request.capital
        
        if len(selected_stocks) < 1:
            raise HTTPException(status_code=400, detail="At least one stock must be selected")
        
        # Get price data from Redis
        tickers = [stock.symbol for stock in selected_stocks]
        price_data = get_price_data_from_redis(tickers)
        
        if not price_data:
            raise HTTPException(status_code=404, detail="No price data found for selected stocks")
        
        # Calculate returns for each asset
        returns_data = {}
        asset_metrics = {}
        
        for ticker in tickers:
            if ticker in price_data:
                prices = price_data[ticker]
                returns = prices.pct_change().dropna()
                returns_data[ticker] = returns
                
                # Calculate individual asset metrics
                metrics = calculate_annualized_metrics(returns)
                asset_metrics[ticker] = metrics
        
        # Calculate portfolio metrics
        if len(selected_stocks) > 1:
            # Calculate correlation matrix
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr().fillna(0)
            
            # Calculate portfolio weights
            total_allocation = sum(stock.allocation for stock in selected_stocks)
            weights = np.array([stock.allocation / total_allocation for stock in selected_stocks])
            
            # Calculate portfolio return and risk
            asset_returns = np.array([asset_metrics[ticker]["return"] for ticker in tickers])
            portfolio_return = np.dot(weights, asset_returns)
            
            # Calculate portfolio risk using correlation matrix
            asset_risks = np.array([asset_metrics[ticker]["risk"] for ticker in tickers])
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(correlation_matrix * np.outer(asset_risks, asset_risks), weights)))
            
            # Calculate portfolio Sharpe ratio
            risk_free_rate = 0.02
            portfolio_sharpe = (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            # Calculate diversification score
            diversification_score = calculate_diversification_score(correlation_matrix, selected_stocks)
            
            # Generate efficient frontier
            efficient_frontier = generate_efficient_frontier_points(returns_data, selected_stocks)
            
        else:
            # Single asset portfolio
            ticker = tickers[0]
            portfolio_return = asset_metrics[ticker]["return"]
            portfolio_risk = asset_metrics[ticker]["risk"]
            portfolio_sharpe = asset_metrics[ticker]["sharpe_ratio"]
            diversification_score = 0.0
            correlation_matrix = pd.DataFrame()
            efficient_frontier = []
        
        # Prepare response
        response = {
            "portfolio_metrics": {
                "expected_return": portfolio_return,
                "risk": portfolio_risk,
                "sharpe_ratio": portfolio_sharpe,
                "diversification_score": diversification_score
            },
            "asset_metrics": asset_metrics,
            "correlation_matrix": correlation_matrix.to_dict() if not correlation_matrix.empty else {},
            "efficient_frontier": efficient_frontier,
            "selected_stocks": [{"ticker": stock.symbol, "allocation": stock.allocation} for stock in selected_stocks],
            "capital": capital
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk-return analysis: {str(e)}")

@router.get("/sector-distribution/enhanced")
async def enhanced_sector_distribution():
    try:
        # Get all tickers from Redis
        all_keys = redis_client.keys("sector_data:*")
        tickers = [key.split(":")[1] for key in all_keys]
        
        if not tickers:
            raise HTTPException(status_code=404, detail="No sector data found")
        
        # Get sector data for all tickers
        sector_data = {}
        for ticker in tickers:
            try:
                sector_info = redis_client.get(f"sector_data:{ticker}")
                if sector_info:
                    sector_data[ticker] = json.loads(sector_info)
            except Exception as e:
                print(f"Error getting sector data for {ticker}: {e}")
                continue
        
        # Group by sector
        sectors = {}
        for ticker, data in sector_data.items():
            sector = data.get("sector", "Unknown")
            if sector not in sectors:
                sectors[sector] = {
                    "tickers": [],
                    "industries": set(),
                    "exchanges": set(),
                    "countries": set(),
                    "returns": [],
                    "risks": [],
                    "sharpe_ratios": []
                }
            
            sectors[sector]["tickers"].append(ticker)
            sectors[sector]["industries"].add(data.get("industry", "Unknown"))
            sectors[sector]["exchanges"].add(data.get("exchange", "Unknown"))
            sectors[sector]["countries"].add(data.get("country", "Unknown"))
            
            # Get performance metrics
            try:
                price_data = get_price_data_from_redis([ticker])
                if ticker in price_data:
                    prices = price_data[ticker]
                    returns = prices.pct_change().dropna()
                    metrics = calculate_annualized_metrics(returns)
                    sectors[sector]["returns"].append(metrics["return"])
                    sectors[sector]["risks"].append(metrics["risk"])
                    sectors[sector]["sharpe_ratios"].append(metrics["sharpe_ratio"])
            except Exception as e:
                print(f"Error calculating metrics for {ticker}: {e}")
        
        # Calculate sector-level metrics
        sector_analysis = []
        for sector, data in sectors.items():
            avg_return = np.mean(data["returns"]) if data["returns"] else 0
            avg_risk = np.mean(data["risks"]) if data["risks"] else 0
            avg_sharpe = np.mean(data["sharpe_ratios"]) if data["sharpe_ratios"] else 0
            
            sector_analysis.append({
                "sector": sector,
                "ticker_count": len(data["tickers"]),
                "tickers": data["tickers"],
                "industries": list(data["industries"]),
                "exchanges": list(data["exchanges"]),
                "countries": list(data["countries"]),
                "average_return": avg_return,
                "average_risk": avg_risk,
                "average_sharpe_ratio": avg_sharpe,
                "performance_rating": get_performance_rating(avg_sharpe),
                "risk_rating": get_risk_rating(avg_risk)
            })
        
        # Sort by average Sharpe ratio
        sector_analysis.sort(key=lambda x: x["average_sharpe_ratio"], reverse=True)
        
        # Calculate market overview
        all_returns = [s["average_return"] for s in sector_analysis if s["average_return"] > 0]
        all_risks = [s["average_risk"] for s in sector_analysis if s["average_risk"] > 0]
        all_sharpes = [s["average_sharpe_ratio"] for s in sector_analysis if s["average_sharpe_ratio"] > 0]
        
        market_overview = {
            "best_performing_sector": sector_analysis[0]["sector"] if sector_analysis else None,
            "highest_risk_sector": max(sector_analysis, key=lambda x: x["average_risk"])["sector"] if sector_analysis else None,
            "most_diversified_sector": max(sector_analysis, key=lambda x: len(x["industries"]))["sector"] if sector_analysis else None,
            "total_sectors": len(sector_analysis),
            "total_tickers": sum(s["ticker_count"] for s in sector_analysis),
            "market_average_return": np.mean(all_returns) if all_returns else 0,
            "market_average_risk": np.mean(all_risks) if all_risks else 0,
            "market_average_sharpe": np.mean(all_sharpes) if all_sharpes else 0
        }
        
        return {
            "sectors": sector_analysis,
            "market_overview": market_overview
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating sector distribution: {str(e)}")

def get_performance_rating(sharpe_ratio: float) -> str:
    if sharpe_ratio >= 1.0:
        return "Excellent"
    elif sharpe_ratio >= 0.5:
        return "Good"
    elif sharpe_ratio >= 0.0:
        return "Fair"
    else:
        return "Poor"

def get_risk_rating(risk: float) -> str:
    if risk <= 0.15:
        return "Low"
    elif risk <= 0.25:
        return "Medium"
    elif risk <= 0.35:
        return "High"
    else:
        return "Very High" 