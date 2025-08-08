from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation
from typing import List, Dict, Optional
import logging
import numpy as np
import pandas as pd
import redis
import json
import gzip
from backend.utils.enhanced_data_fetcher import enhanced_data_fetcher
from backend.utils.ticker_store import ticker_store
from backend.utils.port_analytics import PortfolioAnalytics
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Initialize portfolio analytics
portfolio_analytics = PortfolioAnalytics()

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
    """Generate portfolio recommendations based on risk profile using cached data only"""
    
    try:
        # First, ensure cache is warmed
        cache_status = enhanced_data_fetcher.warm_required_cache()
        logger.info(f"Cache status: {cache_status}")
        
        # Define asset pools based on risk characteristics
        asset_pools = {
            'conservative': [
                ('JNJ', 'Healthcare - Stable'),
                ('PG', 'Consumer Staples'),
                ('KO', 'Consumer Staples'),
                ('WMT', 'Consumer Staples'),
                ('VZ', 'Telecom - Stable'),
                ('UNH', 'Healthcare - Stable')
            ],
            'moderate': [
                ('AAPL', 'Tech - Blue Chip'),
                ('MSFT', 'Tech - Blue Chip'),
                ('GOOGL', 'Tech - Blue Chip'),
                ('V', 'Fintech - Stable'),
                ('MA', 'Fintech - Stable'),
                ('HD', 'Retail - Stable')
            ],
            'aggressive': [
                ('NVDA', 'Tech - Growth'),
                ('TSLA', 'EV - Growth'),
                ('AMD', 'Tech - Growth'),
                ('ADBE', 'Tech - Growth'),
                ('CRM', 'Tech - Growth'),
                ('META', 'Tech - Growth')
            ]
        }
        
        # Get cached data for all assets
        cached_assets = {}
        for pool in asset_pools.values():
            for ticker, _ in pool:
                data = enhanced_data_fetcher.get_monthly_data(ticker)
                if data and data['prices'] and len(data['prices']) >= 12:  # Minimum 1 year of data
                    cached_assets[ticker] = {
                        'prices': data['prices'],
                        'name': data.get('company_name', ticker),
                        'sector': data.get('sector', 'Unknown'),
                        'data_points': len(data['prices'])
                    }
                    logger.info(f"Using {ticker} with {cached_assets[ticker]['data_points']} months of data")
        
        if not cached_assets:
            raise HTTPException(status_code=500, detail="No cached data available")
        
        # Risk-based weights
        risk_weights = {
            'very-conservative': {'conservative': 0.8, 'moderate': 0.2, 'aggressive': 0.0},
            'conservative': {'conservative': 0.6, 'moderate': 0.3, 'aggressive': 0.1},
            'moderate': {'conservative': 0.3, 'moderate': 0.5, 'aggressive': 0.2},
            'aggressive': {'conservative': 0.1, 'moderate': 0.4, 'aggressive': 0.5},
            'very-aggressive': {'conservative': 0.0, 'moderate': 0.3, 'aggressive': 0.7}
        }
        
        weights = risk_weights.get(risk_profile, risk_weights['moderate'])
        responses = []
        
        # Generate 3 different portfolio options
        for option in range(3):
            allocations = []
            total_weight = 0
            
            # Select assets from each pool based on risk weights
            for pool_type, pool_weight in weights.items():
                if pool_weight > 0:
                    pool = asset_pools[pool_type]
                    available_tickers = [(t, d) for t, d in pool if t in cached_assets]
                    
                    if available_tickers:
                        # Select 1-2 assets based on pool weight
                        import random
                        num_assets = min(2, max(1, int(pool_weight * 4)))
                        selected = random.sample(available_tickers, min(num_assets, len(available_tickers)))
                        
                        for ticker, description in selected:
                            weight = (pool_weight / len(selected)) * 100
                            allocations.append(PortfolioAllocation(
                                symbol=ticker,
                                allocation=weight,
                                name=cached_assets[ticker]['name'],
                                assetType='stock'
                            ))
                            total_weight += weight
            
            # Normalize weights to 100%
            for alloc in allocations:
                alloc.allocation = (alloc.allocation / total_weight) * 100
            
            # Calculate portfolio metrics using cached data only
            portfolio_data = {
                'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in allocations]
            }
            
            metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
            
            responses.append(PortfolioResponse(
                portfolio=allocations,
                expectedReturn=metrics['expected_return'],
                risk=metrics['risk'],  # Using risk instead of volatility
                diversificationScore=metrics['diversification_score']
            ))
        
        return responses
        
    except Exception as e:
        logger.error(f"Error generating portfolio recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_static_portfolio_recommendations(risk_profile: str) -> List[PortfolioResponse]:
    """Fallback static portfolio recommendations"""
    # Define portfolio templates for each risk profile
    templates = {
        'very-conservative': [
            {
                'name': 'Conservative Growth Seeker',
                'allocations': [
                    {'symbol': 'JNJ', 'allocation': 40, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                    {'symbol': 'PG', 'allocation': 30, 'name': 'Procter & Gamble', 'assetType': 'stock'},
                    {'symbol': 'KO', 'allocation': 20, 'name': 'Coca-Cola', 'assetType': 'stock'},
                    {'symbol': 'VZ', 'allocation': 10, 'name': 'Verizon', 'assetType': 'stock'}
                ]
            }
        ],
        'conservative': [
            {
                'name': 'Balanced Conservative',
                'allocations': [
                    {'symbol': 'JNJ', 'allocation': 35, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                    {'symbol': 'PG', 'allocation': 30, 'name': 'Procter & Gamble', 'assetType': 'stock'},
                    {'symbol': 'KO', 'allocation': 25, 'name': 'Coca-Cola', 'assetType': 'stock'},
                    {'symbol': 'VZ', 'allocation': 10, 'name': 'Verizon', 'assetType': 'stock'}
                ]
            }
        ],
        'moderate': [
            {
                'name': 'Moderate Growth',
                'allocations': [
                    {'symbol': 'AAPL', 'allocation': 30, 'name': 'Apple Inc.', 'assetType': 'stock'},
                    {'symbol': 'MSFT', 'allocation': 25, 'name': 'Microsoft', 'assetType': 'stock'},
                    {'symbol': 'GOOGL', 'allocation': 25, 'name': 'Alphabet Inc.', 'assetType': 'stock'},
                    {'symbol': 'AMZN', 'allocation': 20, 'name': 'Amazon.com', 'assetType': 'stock'}
                ]
            }
        ],
        'aggressive': [
            {
                'name': 'Growth Focused',
                'allocations': [
                    {'symbol': 'NVDA', 'allocation': 35, 'name': 'NVIDIA', 'assetType': 'stock'},
                    {'symbol': 'TSLA', 'allocation': 30, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                    {'symbol': 'AMD', 'allocation': 20, 'name': 'Advanced Micro Devices', 'assetType': 'stock'},
                    {'symbol': 'META', 'allocation': 15, 'name': 'Meta Platforms', 'assetType': 'stock'}
                ]
            }
        ],
        'very-aggressive': [
            {
                'name': 'Maximum Growth',
                'allocations': [
                    {'symbol': 'NVDA', 'allocation': 40, 'name': 'NVIDIA', 'assetType': 'stock'},
                    {'symbol': 'TSLA', 'allocation': 35, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                    {'symbol': 'AMD', 'allocation': 15, 'name': 'Advanced Micro Devices', 'assetType': 'stock'},
                    {'symbol': 'META', 'allocation': 10, 'name': 'Meta Platforms', 'assetType': 'stock'}
                ]
            }
        ]
    }
    
    # Get templates for the risk profile, default to moderate if not found
    profile_templates = templates.get(risk_profile, templates['moderate'])
    
    responses = []
    for template in profile_templates:
        allocations = []
        for allocation in template['allocations']:
            allocations.append(PortfolioAllocation(
                symbol=allocation['symbol'],
                allocation=allocation['allocation'],
                name=allocation['name'],
                assetType=allocation['assetType']
            ))
        
        # Use fallback metrics
        responses.append(PortfolioResponse(
            portfolio=allocations,
            expectedReturn=0.10,  # 10% fallback
            risk=0.15,  # 15% fallback
            diversificationScore=75.0,  # 75% fallback
            sharpeRatio=0.4  # 0.4 fallback
        ))
    
    return responses

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
        
        # Get monthly data for both tickers using enhanced method
        data1 = enhanced_data_fetcher.get_monthly_data(ticker1)
        data2 = enhanced_data_fetcher.get_monthly_data(ticker2)
        
        if not data1 or not data2:
            raise HTTPException(status_code=404, detail="Data not available for one or both tickers")
        
        # Use portfolio analytics for comprehensive analysis
        analysis = portfolio_analytics.two_asset_analysis(
            ticker1, data1['prices'], ticker2, data2['prices']
        )
        
        # Add additional metadata from enhanced data fetcher
        analysis['asset1_stats'].update({
            'sector': data1.get('sector', 'Unknown'),
            'industry': data1.get('industry', 'Unknown'),
            'company_name': data1.get('company_name', ticker1.upper()),
            'start_date': data1['dates'][0] if data1['dates'] else "2020-01-01",
            'end_date': data1['dates'][-1] if data1['dates'] else "2024-01-01",
            'data_source': "yahoo_finance"
        })
        
        analysis['asset2_stats'].update({
            'sector': data2.get('sector', 'Unknown'),
            'industry': data2.get('industry', 'Unknown'),
            'company_name': data2.get('company_name', ticker2.upper()),
            'start_date': data2['dates'][0] if data2['dates'] else "2020-01-01",
            'end_date': data2['dates'][-1] if data2['dates'] else "2024-01-01",
            'data_source': "yahoo_finance"
        })
        
        return analysis
        
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

@router.get("/ticker-table/data")
async def get_ticker_table_data():
    """
    Get comprehensive ticker table data from Redis with all required fields
    Returns: Complete ticker information for web table display
    """
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        import json
        from datetime import datetime
        
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
                    "status": "error",
                    "lastUpdated": datetime.now().isoformat()
                }
                ticker_data.append(ticker_info)
        
        # Sort by ticker
        ticker_data.sort(key=lambda x: x["ticker"])
        
        return {
            "tickers": ticker_data,
            "total": len(ticker_data),
            "lastUpdated": datetime.now().isoformat(),
            "cacheStatus": enhanced_data_fetcher.get_cache_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting ticker table data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting ticker table data: {str(e)}")

@router.post("/ticker-table/refresh")
async def refresh_ticker_table():
    """
    Force refresh of all ticker data in Redis
    """
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        # Force refresh expired data
        enhanced_data_fetcher.force_refresh_expired_data()
        
        return {
            "status": "success",
            "message": "Ticker table refresh initiated",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing ticker table: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing ticker table: {str(e)}") 

@router.get("/mini-lesson/assets")
def get_mini_lesson_assets():
    """
    Get available assets for mini-lesson with educational pairs and dynamic options
    Returns: Fixed educational pairs and dynamic asset options
    """
    try:
        # Fixed educational pairs for consistent learning
        educational_pairs = [
            {
                'pair_id': 'nvda_amzn',
                'ticker1': 'NVDA',
                'ticker2': 'AMZN',
                'name1': 'NVIDIA Corporation',
                'name2': 'Amazon.com Inc.',
                'description': 'Tech Growth vs E-commerce Giant',
                'educational_focus': 'Growth vs Diversified Business Model'
            },
            {
                'pair_id': 'jnj_tsla',
                'ticker1': 'JNJ',
                'ticker2': 'TSLA',
                'name1': 'Johnson & Johnson',
                'name2': 'Tesla Inc.',
                'description': 'Healthcare Value vs High Volatility',
                'educational_focus': 'Stability vs Innovation Risk'
            }
        ]
        
        # Get available assets for dynamic selection
        available_assets = enhanced_data_fetcher.search_tickers('', limit=50)
        
        # Filter for popular/well-known stocks
        popular_assets = [
            'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'TSLA', 'AMD', 'NFLX',
            'JPM', 'JNJ', 'PG', 'KO', 'WMT', 'UNH', 'HD', 'DIS', 'V', 'MA',
            'PYPL', 'ADBE', 'CRM', 'ORCL', 'INTC', 'CSCO', 'PFE', 'ABT'
        ]
        
        dynamic_assets = []
        for asset in popular_assets:
            # Check if asset is available in cache
            if enhanced_data_fetcher._is_cached(asset, 'prices'):
                asset_data = enhanced_data_fetcher.get_monthly_data(asset)
                if asset_data:
                    dynamic_assets.append({
                        'ticker': asset,
                        'name': asset_data.get('company_name', asset),
                        'sector': asset_data.get('sector', 'Unknown'),
                        'industry': asset_data.get('industry', 'Unknown')
                    })
        
        return {
            'educational_pairs': educational_pairs,
            'dynamic_assets': dynamic_assets[:20],  # Limit to top 20
            'total_available': len(dynamic_assets)
        }
        
    except Exception as e:
        logger.error(f"Error getting mini-lesson assets: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting mini-lesson assets: {str(e)}")

@router.get("/mini-lesson/random-pair")
def get_random_asset_pair():
    """
    Generate a random educational asset pair from available assets
    Returns: Random pair with different sectors for educational value
    """
    try:
        # Get available assets
        popular_assets = [
            'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'TSLA', 'AMD', 'NFLX',
            'JPM', 'JNJ', 'PG', 'KO', 'WMT', 'UNH', 'HD', 'DIS', 'V', 'MA'
        ]
        
        available_assets = []
        for asset in popular_assets:
            if enhanced_data_fetcher._is_cached(asset, 'prices'):
                asset_data = enhanced_data_fetcher.get_monthly_data(asset)
                if asset_data:
                    available_assets.append({
                        'ticker': asset,
                        'name': asset_data.get('company_name', asset),
                        'sector': asset_data.get('sector', 'Unknown'),
                        'industry': asset_data.get('industry', 'Unknown')
                    })
        
        if len(available_assets) < 2:
            raise HTTPException(status_code=404, detail="Insufficient assets available")
        
        # Try to select assets from different sectors for educational value
        import random
        random.shuffle(available_assets)
        
        asset1 = available_assets[0]
        asset2 = None
        
        # Try to find an asset from a different sector
        for asset in available_assets[1:]:
            if asset['sector'] != asset1['sector']:
                asset2 = asset
                break
        
        # If no different sector found, just use the second asset
        if not asset2:
            asset2 = available_assets[1]
        
        return {
            'pair_id': f"{asset1['ticker'].lower()}_{asset2['ticker'].lower()}",
            'ticker1': asset1['ticker'],
            'ticker2': asset2['ticker'],
            'name1': asset1['name'],
            'name2': asset2['name'],
            'sector1': asset1['sector'],
            'sector2': asset2['sector'],
            'description': f"{asset1['sector']} vs {asset2['sector']}",
            'educational_focus': 'Sector Diversification Analysis'
        }
        
    except Exception as e:
        logger.error(f"Error generating random pair: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating random pair: {str(e)}")

@router.post("/mini-lesson/custom-portfolio")
def calculate_custom_portfolio(request: dict):
    """
    Calculate custom portfolio metrics for interactive slider
    Returns: Real-time portfolio metrics for given weights
    """
    try:
        ticker1 = request.get('ticker1')
        ticker2 = request.get('ticker2')
        weight1 = request.get('weight1', 0.5)  # Default to 50/50
        
        if not ticker1 or not ticker2:
            raise HTTPException(status_code=400, detail="Both tickers required")
        
        # Validate weight
        if not 0 <= weight1 <= 1:
            raise HTTPException(status_code=400, detail="Weight must be between 0 and 1")
        
        # Get data for both assets
        data1 = enhanced_data_fetcher.get_monthly_data(ticker1)
        data2 = enhanced_data_fetcher.get_monthly_data(ticker2)
        
        if not data1 or not data2:
            raise HTTPException(status_code=404, detail="Data not available for one or both tickers")
        
        # Calculate individual asset metrics
        asset1_metrics = portfolio_analytics.calculate_asset_metrics(data1['prices'])
        asset2_metrics = portfolio_analytics.calculate_asset_metrics(data2['prices'])
        
        # Calculate correlation
        returns1 = pd.Series(data1['prices']).pct_change().dropna()
        returns2 = pd.Series(data2['prices']).pct_change().dropna()
        
        min_length = min(len(returns1), len(returns2))
        returns1_aligned = returns1.iloc[-min_length:]
        returns2_aligned = returns2.iloc[-min_length:]
        
        correlation = returns1_aligned.corr(returns2_aligned)
        if pd.isna(correlation):
            correlation = 0.0
        
        # Calculate custom portfolio metrics
        custom_portfolio = portfolio_analytics.calculate_custom_portfolio(
            weight1, asset1_metrics, asset2_metrics, correlation
        )
        
        return {
            'portfolio_metrics': custom_portfolio,
            'asset1_metrics': {
                'ticker': ticker1.upper(),
                'return': asset1_metrics['annualized_return'],
                'risk': asset1_metrics['annualized_volatility'],
                'sharpe': asset1_metrics['sharpe_ratio']
            },
            'asset2_metrics': {
                'ticker': ticker2.upper(),
                'return': asset2_metrics['annualized_return'],
                'risk': asset2_metrics['annualized_volatility'],
                'sharpe': asset2_metrics['sharpe_ratio']
            },
            'correlation': correlation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating custom portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating custom portfolio: {str(e)}") 