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
from utils.port_analytics import PortfolioAnalytics
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Initialize portfolio analytics
portfolio_analytics = PortfolioAnalytics()

# New model for portfolio metrics calculation
class PortfolioMetricsRequest(BaseModel):
    allocations: List[PortfolioAllocation]
    riskProfile: str

# New model for portfolio metrics response
class PortfolioMetricsResponse(BaseModel):
    expectedReturn: float
    risk: float
    diversificationScore: float
    sharpeRatio: float
    totalAllocation: float
    stockCount: int
    validation: Dict

# New model for portfolio optimization request
class PortfolioOptimizationRequest(BaseModel):
    allocations: List[PortfolioAllocation]
    riskProfile: str
    optimizationType: str = "mean-variance"  # "mean-variance", "risk-parity", "custom"
    targetReturn: Optional[float] = None
    maxRisk: Optional[float] = None

# New model for portfolio optimization response
class PortfolioOptimizationResponse(BaseModel):
    originalMetrics: PortfolioMetricsResponse
    optimizedMetrics: PortfolioMetricsResponse
    optimizedAllocations: List[PortfolioAllocation]
    efficientFrontier: List[Dict]
    improvement: Dict
    recommendations: List[str]

@router.post("/calculate-metrics", response_model=PortfolioMetricsResponse)
def calculate_portfolio_metrics(request: PortfolioMetricsRequest):
    """
    Calculate real-time portfolio metrics based on current allocations
    """
    try:
        allocations = request.allocations
        risk_profile = request.riskProfile
        
        if not allocations:
            raise HTTPException(status_code=400, detail="Portfolio allocations required")
        
        # Calculate metrics using cached data
        portfolio_data = {
            'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in allocations]
        }
        
        # Calculate portfolio metrics
        metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
        
        # Calculate validation data
        total_allocation = sum(a.allocation for a in allocations)
        stock_count = len(allocations)
        
        # Generate validation warnings
        warnings = []
        if abs(total_allocation - 100) > 0.01:
            warnings.append(f"Total allocation is {total_allocation:.1f}%. Must equal 100%.")
        
        if stock_count < 3:
            warnings.append(f"Portfolio must have at least 3 stocks. Currently: {stock_count}")
        
        for allocation in allocations:
            if allocation.allocation < 5:
                warnings.append(f"{allocation.symbol} allocation ({allocation.allocation:.1f}%) is very low")
            if allocation.allocation > 50:
                warnings.append(f"{allocation.symbol} allocation ({allocation.allocation:.1f}%) is very high")
        
        is_valid = total_allocation == 100 and stock_count >= 3 and len(warnings) == 0
        can_proceed = stock_count >= 3
        
        return PortfolioMetricsResponse(
            expectedReturn=metrics.get('expected_return', 0.0),
            risk=metrics.get('risk', 0.0),
            diversificationScore=metrics.get('diversification_score', 0.0),
            sharpeRatio=0.0,  # Always 0 as requested
            totalAllocation=total_allocation,
            stockCount=stock_count,
            validation={
                "isValid": is_valid,
                "canProceed": can_proceed,
                "warnings": warnings
            }
        )
        
    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize", response_model=PortfolioOptimizationResponse)
def optimize_portfolio(request: PortfolioOptimizationRequest):
    """
    Optimize portfolio allocations using advanced algorithms
    """
    try:
        allocations = request.allocations
        risk_profile = request.riskProfile
        optimization_type = request.optimizationType
        
        if not allocations:
            raise HTTPException(status_code=400, detail="Portfolio allocations required")
        
        if len(allocations) < 3:
            raise HTTPException(status_code=400, detail="Portfolio must have at least 3 stocks")
        
        # Calculate original portfolio metrics
        original_metrics = portfolio_analytics.calculate_real_portfolio_metrics({
            'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in allocations]
        })
        
        # Get ticker symbols for optimization
        tickers = [a.symbol for a in allocations]
        
        # Get historical data from Redis cache
        try:
            price_data = get_price_data_from_redis(tickers)
            if not price_data or len(price_data) < 3:
                raise HTTPException(status_code=400, detail="Insufficient historical data for optimization")
        except Exception as e:
            logger.error(f"Error getting price data: {e}")
            raise HTTPException(status_code=400, detail="Unable to retrieve historical data for optimization")
        
        # Calculate returns for optimization
        returns_data = {}
        for ticker, prices in price_data.items():
            if len(prices) > 1:
                returns = prices.pct_change().dropna()
                returns_data[ticker] = returns
        
        if len(returns_data) < 3:
            raise HTTPException(status_code=400, detail="Insufficient return data for optimization")
        
        # Run optimization based on type
        if optimization_type == "mean-variance":
            optimized_weights = optimize_mean_variance_weights(returns_data, risk_profile)
        elif optimization_type == "risk-parity":
            optimized_weights = optimize_risk_parity_weights(returns_data, risk_profile)
        else:
            optimized_weights = optimize_custom_weights(returns_data, risk_profile, request.targetReturn, request.maxRisk)
        
        # Create optimized allocations
        optimized_allocations = []
        for i, ticker in enumerate(tickers):
            if i < len(optimized_weights):
                optimized_allocations.append(PortfolioAllocation(
                    symbol=ticker,
                    allocation=round(optimized_weights[i] * 100, 1),
                    name=allocations[i].name if allocations[i].name else None,
                    assetType=allocations[i].assetType if allocations[i].assetType else 'stock'
                ))
        
        # Calculate optimized metrics
        optimized_metrics = portfolio_analytics.calculate_real_portfolio_metrics({
            'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in optimized_allocations]
        })
        
        # Generate efficient frontier points
        efficient_frontier = generate_efficient_frontier_points(returns_data, allocations, 20)
        
        # Calculate improvements
        return_improvement = ((optimized_metrics.get('expected_return', 0) - original_metrics.get('expected_return', 0)) / 
                            max(original_metrics.get('expected_return', 0.01), 0.01)) * 100
        risk_improvement = ((original_metrics.get('risk', 0) - optimized_metrics.get('risk', 0)) / 
                          max(original_metrics.get('risk', 0.01), 0.01)) * 100
        
        # Generate recommendations
        recommendations = []
        if return_improvement > 5:
            recommendations.append(f"Expected return improved by {return_improvement:.1f}%")
        if risk_improvement > 5:
            recommendations.append(f"Risk reduced by {risk_improvement:.1f}%")
        if optimized_metrics.get('diversification_score', 0) > original_metrics.get('diversification_score', 0):
            recommendations.append("Diversification improved")
        
        if not recommendations:
            recommendations.append("Portfolio is already well-optimized for your risk profile")
        
        return PortfolioOptimizationResponse(
            originalMetrics=PortfolioMetricsResponse(
                expectedReturn=original_metrics.get('expected_return', 0.0),
                risk=original_metrics.get('risk', 0.0),
                diversificationScore=original_metrics.get('diversification_score', 0.0),
                sharpeRatio=0.0,
                totalAllocation=100.0,
                stockCount=len(allocations),
                validation={"isValid": True, "canProceed": True, "warnings": []}
            ),
            optimizedMetrics=PortfolioMetricsResponse(
                expectedReturn=optimized_metrics.get('expected_return', 0.0),
                risk=optimized_metrics.get('risk', 0.0),
                diversificationScore=optimized_metrics.get('diversification_score', 0.0),
                sharpeRatio=0.0,
                totalAllocation=100.0,
                stockCount=len(optimized_allocations),
                validation={"isValid": True, "canProceed": True, "warnings": []}
            ),
            optimizedAllocations=optimized_allocations,
            efficientFrontier=efficient_frontier,
            improvement={
                "returnImprovement": return_improvement,
                "riskImprovement": risk_improvement,
                "diversificationImprovement": optimized_metrics.get('diversification_score', 0) - original_metrics.get('diversification_score', 0)
            },
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def optimize_mean_variance_weights(returns_data: Dict[str, pd.Series], risk_profile: str) -> List[float]:
    """
    Optimize portfolio weights using mean-variance optimization
    """
    try:
        # Convert returns to DataFrame
        returns_df = pd.DataFrame(returns_data)
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 30:  # Need sufficient data
            return [1.0/len(returns_data)] * len(returns_data)
        
        # Calculate expected returns and covariance matrix
        expected_returns = returns_df.mean() * 252  # Annualized
        cov_matrix = returns_df.cov() * 252  # Annualized
        
        # Risk profile constraints
        risk_constraints = {
            'very-conservative': 0.08,
            'conservative': 0.12,
            'moderate': 0.16,
            'aggressive': 0.22,
            'very-aggressive': 0.28
        }
        max_risk = risk_constraints.get(risk_profile, 0.16)
        
        # Simple optimization: minimize variance subject to return constraint
        n_assets = len(expected_returns)
        
        # Use equal weight as starting point
        weights = np.array([1.0/n_assets] * n_assets)
        
        # Simple iterative optimization
        for _ in range(100):
            portfolio_return = np.sum(weights * expected_returns)
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if portfolio_risk <= max_risk:
                break
            
            # Reduce weights of highest risk assets
            risk_contributions = np.dot(cov_matrix, weights)
            high_risk_indices = np.argsort(risk_contributions)[-3:]  # Top 3 risk contributors
            weights[high_risk_indices] *= 0.95
            weights = weights / np.sum(weights)  # Renormalize
        
        return weights.tolist()
        
    except Exception as e:
        logger.error(f"Error in mean-variance optimization: {e}")
        # Return equal weights as fallback
        return [1.0/len(returns_data)] * len(returns_data)

def optimize_risk_parity_weights(returns_data: Dict[str, pd.Series], risk_profile: str) -> List[float]:
    """
    Optimize portfolio weights using risk parity approach
    """
    try:
        # Convert returns to DataFrame
        returns_df = pd.DataFrame(returns_data)
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 30:
            return [1.0/len(returns_data)] * len(returns_data)
        
        # Calculate covariance matrix
        cov_matrix = returns_df.cov() * 252
        
        # Risk parity: equal risk contribution from each asset
        n_assets = len(returns_data)
        weights = np.array([1.0/n_assets] * n_assets)
        
        # Iterative optimization to achieve risk parity
        for _ in range(50):
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            risk_contributions = np.dot(cov_matrix, weights) / portfolio_risk
            
            # Adjust weights to equalize risk contributions
            target_risk_contribution = portfolio_risk / n_assets
            adjustments = (target_risk_contribution - risk_contributions) / risk_contributions
            adjustments = np.clip(adjustments, -0.1, 0.1)  # Limit adjustment size
            
            weights *= (1 + adjustments)
            weights = weights / np.sum(weights)  # Renormalize
        
        return weights.tolist()
        
    except Exception as e:
        logger.error(f"Error in risk parity optimization: {e}")
        return [1.0/len(returns_data)] * len(returns_data)

def optimize_custom_weights(returns_data: Dict[str, pd.Series], risk_profile: str, 
                           target_return: Optional[float] = None, max_risk: Optional[float] = None) -> List[float]:
    """
    Custom optimization with specific return/risk targets
    """
    try:
        # Use mean-variance as base, then apply custom constraints
        weights = optimize_mean_variance_weights(returns_data, risk_profile)
        
        if target_return is not None or max_risk is not None:
            # Apply additional constraints
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            expected_returns = returns_df.mean() * 252
            cov_matrix = returns_df.cov() * 252
            
            # Adjust weights to meet constraints
            current_return = np.sum(weights * expected_returns)
            current_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if target_return is not None and current_return < target_return:
                # Increase weights of higher return assets
                high_return_indices = np.argsort(expected_returns)[-3:]
                weights[high_return_indices] *= 1.1
                weights = weights / np.sum(weights)
            
            if max_risk is not None and current_risk > max_risk:
                # Reduce weights of higher risk assets
                high_risk_indices = np.argsort(np.diag(cov_matrix))[-3:]
                weights[high_risk_indices] *= 0.9
                weights = weights / np.sum(weights)
        
        return weights
        
    except Exception as e:
        logger.error(f"Error in custom optimization: {e}")
        return [1.0/len(returns_data)] * len(returns_data)

@router.get("/ticker/search")
def search_tickers(q: str, limit: int = 10):
    """
    Search tickers by query string
    """
    try:
        results = enhanced_data_fetcher.search_tickers(q, limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ticker/{ticker}/info")
def get_ticker_info(ticker: str):
    """
    Get comprehensive ticker information including prices, metrics, and company details
    """
    try:
        ticker_info = enhanced_data_fetcher.get_ticker_info(ticker)
        if not ticker_info:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found or no data available")
        return ticker_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        # Cache should be warmed at startup, not on every request
        # cache_status = enhanced_data_fetcher.warm_required_cache()
        # logger.info(f"Cache status: {cache_status}")
        
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
                    # Reduced logging verbosity
                    # logger.info(f"Using {ticker} with {cached_assets[ticker]['data_points']} months of data")
        
        if not cached_assets:
            # Use fallback instead of warming cache
            logger.warning("No cached data available, using fallback recommendations")
            return _get_static_portfolio_recommendations(risk_profile)
        
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

# NEW: Dynamic Portfolio Generation Endpoint
@router.post("/recommendations/dynamic", response_model=List[PortfolioResponse])
def generate_dynamic_portfolio_recommendations(
    risk_profile: str,
    target_return: Optional[float] = None,
    max_risk: Optional[float] = None,
    num_portfolios: int = 5
):
    """
    Generate dynamic, optimized portfolio recommendations using advanced algorithms
    
    This endpoint uses multiple optimization strategies to create personalized portfolios:
    1. Sharpe Ratio Optimization - Maximizes risk-adjusted returns
    2. Risk Parity - Equal risk contribution from each asset
    3. Maximum Diversification - Minimizes correlation between assets
    4. Target Return - Optimizes for specific return with minimum risk
    5. Minimum Risk - For conservative investors
    
    Args:
        risk_profile: User's risk tolerance level
        target_return: Optional target annual return (e.g., 0.15 for 15%)
        max_risk: Optional maximum annual risk tolerance (e.g., 0.25 for 25%)
        num_portfolios: Number of portfolios to generate (default: 5)
    """
    try:
        logger.info(f"Generating dynamic portfolios for {risk_profile} profile")
        
        # Get all available assets from cache
        available_tickers = []
        cached_assets = {}
        
        # Get master ticker list
        master_tickers = enhanced_data_fetcher.get_all_tickers()
        
        # Use all available tickers (no sector filtering)
        available_tickers = master_tickers[:100]  # Limit to top 100 for performance
        
        if not available_tickers:
            logger.warning("No tickers available for dynamic portfolio generation")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Generate dynamic portfolios using advanced optimization
        dynamic_portfolios = portfolio_analytics.generate_dynamic_portfolios(
            risk_profile=risk_profile,
            available_assets=available_tickers,
            target_return=target_return,
            max_risk=max_risk,
            num_portfolios=num_portfolios
        )
        
        # Convert to PortfolioResponse format
        responses = []
        for portfolio in dynamic_portfolios:
            # Convert weights to allocations
            allocations = []
            for ticker, weight in portfolio['weights'].items():
                # Get asset info
                asset_data = cached_assets.get(ticker, {})
                allocations.append(PortfolioAllocation(
                    symbol=ticker,
                    allocation=weight * 100,  # Convert to percentage
                    name=asset_data.get('company_name', ticker),
                    assetType='stock'
                ))
            
            responses.append(PortfolioResponse(
                portfolio=allocations,
                expectedReturn=portfolio['expected_return'],
                risk=portfolio['risk'],
                diversificationScore=portfolio['diversification_score']
            ))
        
        logger.info(f"Generated {len(responses)} dynamic portfolios for {risk_profile} profile")
        return responses
        
    except Exception as e:
        logger.error(f"Error generating dynamic portfolio recommendations: {e}")
        # Fallback to static recommendations
        return _get_static_portfolio_recommendations(risk_profile)

# NEW: Portfolio Optimization Analysis Endpoint
@router.post("/optimize/analysis", response_model=Dict)
def analyze_portfolio_optimization(
    current_portfolio: List[PortfolioAllocation],
    risk_profile: str,
    target_return: Optional[float] = None,
    max_risk: Optional[float] = None
):
    """
    Analyze current portfolio and provide optimization recommendations
    
    This endpoint:
    1. Analyzes current portfolio performance
    2. Suggests optimization strategies
    3. Provides alternative portfolio configurations
    4. Shows risk-return trade-offs
    """
    try:
        # Calculate current portfolio metrics
        current_data = {
            'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in current_portfolio]
        }
        current_metrics = portfolio_analytics.calculate_real_portfolio_metrics(current_data)
        
        # Get available assets for optimization
        master_tickers = enhanced_data_fetcher.get_all_tickers()[:100]
        
        # Generate optimized alternatives
        optimized_portfolios = portfolio_analytics.generate_dynamic_portfolios(
            risk_profile=risk_profile,
            available_assets=master_tickers,
            target_return=target_return,
            max_risk=max_risk,
            num_portfolios=3
        )
        
        # Calculate improvement metrics
        improvements = []
        for opt_portfolio in optimized_portfolios:
            improvement = {
                'strategy': opt_portfolio['strategy'],
                'return_improvement': opt_portfolio['expected_return'] - current_metrics['expected_return'],
                'risk_change': opt_portfolio['risk'] - current_metrics['risk'],
                'sharpe_improvement': opt_portfolio['sharpe_ratio'] - (current_metrics.get('sharpe_ratio', 0)),
                'diversification_improvement': opt_portfolio['diversification_score'] - current_metrics['diversification_score']
            }
            improvements.append(improvement)
        
        return {
            'current_portfolio': {
                'metrics': current_metrics,
                'allocations': current_portfolio
            },
            'optimization_alternatives': optimized_portfolios,
            'improvements': improvements,
            'recommendations': _generate_optimization_recommendations(current_metrics, improvements, risk_profile)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing portfolio optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _generate_optimization_recommendations(current_metrics: Dict, improvements: List[Dict], risk_profile: str) -> List[str]:
    """Generate actionable optimization recommendations"""
    recommendations = []
    
    # Analyze current portfolio
    if current_metrics['diversification_score'] < 70:
        recommendations.append("Consider increasing diversification by adding assets from different sectors")
    
    if current_metrics['risk'] > 0.3 and risk_profile in ['very-conservative', 'conservative']:
        recommendations.append("Current portfolio risk is high for your risk profile. Consider adding more stable assets")
    
    # Analyze improvements
    best_improvement = max(improvements, key=lambda x: x['sharpe_improvement'])
    if best_improvement['sharpe_improvement'] > 0.1:
        recommendations.append(f"Strategy '{best_improvement['strategy']}' could significantly improve your risk-adjusted returns")
    
    if best_improvement['diversification_improvement'] > 10:
        recommendations.append("Optimization could improve diversification by 10+ points")
    
    return recommendations

def _get_static_portfolio_recommendations(risk_profile: str) -> List[PortfolioResponse]:
    """Fallback static portfolio recommendations with consistent metrics calculation"""
    from utils.port_analytics import PortfolioAnalytics
    
    # Initialize portfolio analytics for consistent calculations
    portfolio_analytics = PortfolioAnalytics()
    
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
        
        # Calculate metrics using the same method as real-time calculations
        try:
            portfolio_data = {
                'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in allocations]
            }
            metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
            
            responses.append(PortfolioResponse(
                portfolio=allocations,
                expectedReturn=metrics.get('expected_return', 0.10),
                risk=metrics.get('risk', 0.15),
                diversificationScore=metrics.get('diversification_score', 75.0),
                sharpeRatio=0.0  # Always 0 as requested
            ))
        except Exception as e:
            logger.warning(f"Failed to calculate metrics for {template['name']}, using fallback: {e}")
            # Use fallback metrics if calculation fails
            responses.append(PortfolioResponse(
                portfolio=allocations,
                expectedReturn=0.10,  # 10% fallback
                risk=0.15,  # 15% fallback
                diversificationScore=75.0,  # 75% fallback
                sharpeRatio=0.0  # Always 0 as requested
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
    Get available assets for mini-lesson with predefined sector-based asset lists
    Returns: Sector-based asset lists for educational analysis with pre-calculated metrics
    """
    try:
        # Predefined sector-based asset lists (5 assets each from different sectors)
        sector_asset_lists = [
            {
                'list_id': 'tech_growth',
                'name': 'Technology Growth',
                'description': 'High-growth technology companies',
                'sector': 'Technology',
                'assets': [
                    {
                        'ticker': 'NVDA',
                        'name': 'NVIDIA Corporation',
                        'sector': 'Technology',
                        'industry': 'Semiconductors',
                        'focus': 'AI & Gaming Chips'
                    },
                    {
                        'ticker': 'TSLA',
                        'name': 'Tesla Inc.',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Automobiles',
                        'focus': 'Electric Vehicles'
                    },
                    {
                        'ticker': 'META',
                        'name': 'Meta Platforms Inc.',
                        'sector': 'Technology',
                        'industry': 'Internet Content',
                        'focus': 'Social Media'
                    },
                    {
                        'ticker': 'AMD',
                        'name': 'Advanced Micro Devices',
                        'sector': 'Technology',
                        'industry': 'Semiconductors',
                        'focus': 'Computer Processors'
                    },
                    {
                        'ticker': 'ADBE',
                        'name': 'Adobe Inc.',
                        'sector': 'Technology',
                        'industry': 'Software',
                        'focus': 'Creative Software'
                    }
                ]
            },
            {
                'list_id': 'stable_blue_chips',
                'name': 'Stable Blue Chips',
                'description': 'Established companies with stable returns',
                'sector': 'Mixed',
                'assets': [
                    {
                        'ticker': 'JNJ',
                        'name': 'Johnson & Johnson',
                        'sector': 'Healthcare',
                        'industry': 'Pharmaceuticals',
                        'focus': 'Healthcare Products'
                    },
                    {
                        'ticker': 'PG',
                        'name': 'Procter & Gamble Co.',
                        'sector': 'Consumer Staples',
                        'industry': 'Household Products',
                        'focus': 'Consumer Goods'
                    },
                    {
                        'ticker': 'KO',
                        'name': 'Coca-Cola Company',
                        'sector': 'Consumer Staples',
                        'industry': 'Beverages',
                        'focus': 'Beverages'
                    },
                    {
                        'ticker': 'WMT',
                        'name': 'Walmart Inc.',
                        'sector': 'Consumer Staples',
                        'industry': 'Discount Stores',
                        'focus': 'Retail'
                    },
                    {
                        'ticker': 'UNH',
                        'name': 'UnitedHealth Group',
                        'sector': 'Healthcare',
                        'industry': 'Health Insurance',
                        'focus': 'Health Insurance'
                    }
                ]
            },
            {
                'list_id': 'financial_services',
                'name': 'Financial Services',
                'description': 'Banking and financial services companies',
                'sector': 'Financial Services',
                'assets': [
                    {
                        'ticker': 'JPM',
                        'name': 'JPMorgan Chase & Co.',
                        'sector': 'Financial Services',
                        'industry': 'Banks',
                        'focus': 'Investment Banking'
                    },
                    {
                        'ticker': 'V',
                        'name': 'Visa Inc.',
                        'sector': 'Financial Services',
                        'industry': 'Credit Services',
                        'focus': 'Payment Processing'
                    },
                    {
                        'ticker': 'MA',
                        'name': 'Mastercard Inc.',
                        'sector': 'Financial Services',
                        'industry': 'Credit Services',
                        'focus': 'Payment Processing'
                    },
                    {
                        'ticker': 'HD',
                        'name': 'Home Depot Inc.',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Home Improvement Retail',
                        'focus': 'Home Improvement'
                    },
                    {
                        'ticker': 'DIS',
                        'name': 'Walt Disney Company',
                        'sector': 'Communication Services',
                        'industry': 'Entertainment',
                        'focus': 'Media & Entertainment'
                    }
                ]
            },
            {
                'list_id': 'healthcare_pharma',
                'name': 'Healthcare & Pharma',
                'description': 'Healthcare and pharmaceutical companies',
                'sector': 'Healthcare',
                'assets': [
                    {
                        'ticker': 'PFE',
                        'name': 'Pfizer Inc.',
                        'sector': 'Healthcare',
                        'industry': 'Pharmaceuticals',
                        'focus': 'Vaccines & Medicines'
                    },
                    {
                        'ticker': 'ABBV',
                        'name': 'AbbVie Inc.',
                        'sector': 'Healthcare',
                        'industry': 'Pharmaceuticals',
                        'focus': 'Biopharmaceuticals'
                    },
                    {
                        'ticker': 'TMO',
                        'name': 'Thermo Fisher Scientific',
                        'sector': 'Healthcare',
                        'industry': 'Medical Devices',
                        'focus': 'Scientific Instruments'
                    },
                    {
                        'ticker': 'DHR',
                        'name': 'Danaher Corporation',
                        'sector': 'Healthcare',
                        'industry': 'Medical Devices',
                        'focus': 'Life Sciences'
                    },
                    {
                        'ticker': 'BMY',
                        'name': 'Bristol-Myers Squibb',
                        'sector': 'Healthcare',
                        'industry': 'Pharmaceuticals',
                        'focus': 'Biopharmaceuticals'
                    }
                ]
            },
            {
                'list_id': 'consumer_discretionary',
                'name': 'Consumer Discretionary',
                'description': 'Consumer discretionary and retail companies',
                'sector': 'Consumer Discretionary',
                'assets': [
                    {
                        'ticker': 'AMZN',
                        'name': 'Amazon.com Inc.',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Internet Retail',
                        'focus': 'E-commerce & Cloud'
                    },
                    {
                        'ticker': 'NKE',
                        'name': 'Nike Inc.',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Textiles & Apparel',
                        'focus': 'Athletic Footwear'
                    },
                    {
                        'ticker': 'SBUX',
                        'name': 'Starbucks Corporation',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Restaurants',
                        'focus': 'Coffee & Beverages'
                    },
                    {
                        'ticker': 'MCD',
                        'name': 'McDonald\'s Corporation',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Restaurants',
                        'focus': 'Fast Food'
                    },
                    {
                        'ticker': 'TJX',
                        'name': 'TJX Companies Inc.',
                        'sector': 'Consumer Discretionary',
                        'industry': 'Apparel Retail',
                        'focus': 'Off-Price Retail'
                    }
                ]
            },
            {
                'list_id': 'energy_utilities',
                'name': 'Energy & Utilities',
                'description': 'Energy and utility companies',
                'sector': 'Energy',
                'assets': [
                    {
                        'ticker': 'XOM',
                        'name': 'Exxon Mobil Corporation',
                        'sector': 'Energy',
                        'industry': 'Oil & Gas',
                        'focus': 'Integrated Oil'
                    },
                    {
                        'ticker': 'CVX',
                        'name': 'Chevron Corporation',
                        'sector': 'Energy',
                        'industry': 'Oil & Gas',
                        'focus': 'Integrated Oil'
                    },
                    {
                        'ticker': 'DUK',
                        'name': 'Duke Energy Corporation',
                        'sector': 'Utilities',
                        'industry': 'Electric Utilities',
                        'focus': 'Electric Power'
                    },
                    {
                        'ticker': 'NEE',
                        'name': 'NextEra Energy Inc.',
                        'sector': 'Utilities',
                        'industry': 'Electric Utilities',
                        'focus': 'Renewable Energy'
                    },
                    {
                        'ticker': 'SO',
                        'name': 'Southern Company',
                        'sector': 'Utilities',
                        'industry': 'Electric Utilities',
                        'focus': 'Electric Power'
                    }
                ]
            }
        ]
        
        # Check which assets are available in cache and add pre-calculated metrics
        available_lists = []
        for asset_list in sector_asset_lists:
            available_assets = []
            for asset in asset_list['assets']:
                ticker = asset['ticker']
                if enhanced_data_fetcher._is_cached(ticker, 'prices'):
                    # Get pre-calculated metrics from cache
                    cached_metrics = enhanced_data_fetcher.get_cached_metrics(ticker)
                    if cached_metrics:
                        available_assets.append({
                            **asset,
                            'annualized_return': cached_metrics['annualized_return'],
                            'risk': cached_metrics['risk'],  # Consistent naming: 'risk' not 'volatility'
                            'data_points': cached_metrics['data_points'],
                            'last_price': cached_metrics['last_price']
                        })
                    else:
                        # Fallback: calculate metrics on-the-fly
                        asset_data = enhanced_data_fetcher.get_monthly_data(ticker)
                        if asset_data and len(asset_data['prices']) >= 12:
                            prices = asset_data['prices']
                            returns = pd.Series(prices).pct_change().dropna()
                            annual_return = (1 + returns.mean()) ** 12 - 1
                            annual_risk = returns.std() * np.sqrt(12)
                            
                            available_assets.append({
                                **asset,
                                'annualized_return': annual_return,
                                'risk': annual_risk,  # Consistent naming: 'risk' not 'volatility'
                                'data_points': len(prices),
                                'last_price': prices[-1] if prices else 0
                            })
            
            if len(available_assets) >= 3:  # Only include lists with at least 3 available assets
                available_lists.append({
                    **asset_list,
                    'assets': available_assets,
                    'available_count': len(available_assets)
                })
        
        return {
            'sector_lists': available_lists,
            'total_lists': len(available_lists),
            'message': 'Sector-based asset lists with pre-calculated metrics'
        }
        
    except Exception as e:
        logger.error(f"Error getting mini-lesson assets: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting mini-lesson assets: {str(e)}")

@router.get("/mini-lesson/random-pair")
def get_random_asset_pair():
    """
    Generate a truly random educational asset pair from all available assets
    Returns: Random pair with different sectors for educational value
    """
    try:
        # Get sector lists
        sector_lists_response = get_mini_lesson_assets()
        sector_lists = sector_lists_response.get('sector_lists', [])
        
        if len(sector_lists) < 2:
            raise HTTPException(status_code=404, detail="Insufficient sector lists available")
        
        # Collect ALL available assets from ALL lists
        all_assets = []
        for sector_list in sector_lists:
            for asset in sector_list['assets']:
                all_assets.append({
                    **asset,
                    'source_list': sector_list['name']  # Track which list it came from
                })
        
        if len(all_assets) < 2:
            raise HTTPException(status_code=404, detail="Insufficient assets available")
        
        # Select two random assets from ALL available assets
        import random
        selected_assets = random.sample(all_assets, 2)
        asset1, asset2 = selected_assets
        
        # Ensure we have different assets (in case of duplicates)
        attempts = 0
        while asset1['ticker'] == asset2['ticker'] and attempts < 10:
            asset2 = random.choice(all_assets)
            attempts += 1
        
        # Create educational theme based on sectors
        themes = {
            ('Technology', 'Healthcare'): 'Innovation vs Stability',
            ('Technology', 'Consumer Discretionary'): 'Growth vs Consumer Demand',
            ('Technology', 'Energy'): 'Innovation vs Traditional Energy',
            ('Healthcare', 'Consumer Discretionary'): 'Health vs Lifestyle',
            ('Healthcare', 'Energy'): 'Health vs Energy Infrastructure',
            ('Consumer Discretionary', 'Energy'): 'Consumer Spending vs Energy Demand',
            ('Financial Services', 'Technology'): 'Financial Infrastructure vs Innovation',
            ('Financial Services', 'Healthcare'): 'Financial Services vs Healthcare',
            ('Financial Services', 'Consumer Discretionary'): 'Financial Services vs Consumer Spending',
            ('Financial Services', 'Energy'): 'Financial Services vs Energy'
        }
        
        theme_key = (asset1['sector'], asset2['sector'])
        educational_theme = themes.get(theme_key, f"{asset1['sector']} vs {asset2['sector']}")
        
        return {
            'ticker1': asset1['ticker'],
            'ticker2': asset2['ticker'],
            'name1': asset1['name'],
            'name2': asset2['name'],
            'sector1': asset1['sector'],
            'sector2': asset2['sector'],
            'industry1': asset1['industry'],
            'industry2': asset2['industry'],
            'focus1': asset1['focus'],
            'focus2': asset2['focus'],
            'description': f"{asset1['sector']} vs {asset2['sector']}",
            'educational_focus': educational_theme,
            'asset1_metrics': {
                'annualized_return': asset1['annualized_return'],
                'risk': asset1['risk']
            },
            'asset2_metrics': {
                'annualized_return': asset2['annualized_return'],
                'risk': asset2['risk']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating random asset pair: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating random asset pair: {str(e)}")


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
                'risk': asset1_metrics['risk']  # Using consistent naming: 'risk' not 'volatility'
            },
            'asset2_metrics': {
                'ticker': ticker2.upper(),
                'return': asset2_metrics['annualized_return'],
                'risk': asset2_metrics['risk']  # Using consistent naming: 'risk' not 'volatility'
            },
            'correlation': correlation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating custom portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating custom portfolio: {str(e)}")

@router.post("/optimize/risk-parity")
async def optimize_risk_parity(request: dict):
    """
    Optimize portfolio using risk parity approach
    Returns: Risk-parity optimized weights and metrics
    """
    try:
        tickers = request.get('tickers', [])
        target_risk = request.get('target_risk', 0.15)  # Default 15% target risk
        
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required for optimization")
        
        # Get price data for all tickers
        price_data = {}
        for ticker in tickers:
            data = enhanced_data_fetcher.get_monthly_data(ticker)
            if data and data['prices']:
                price_data[ticker] = data['prices']
        
        if len(price_data) < 2:
            raise HTTPException(status_code=404, detail="Insufficient price data for optimization")
        
        # Calculate returns and covariance matrix
        returns_data = {}
        for ticker, prices in price_data.items():
            returns = pd.Series(prices).pct_change().dropna()
            returns_data[ticker] = returns
        
        # Align all returns to same length
        min_length = min(len(returns) for returns in returns_data.values())
        aligned_returns = {}
        for ticker, returns in returns_data.items():
            aligned_returns[ticker] = returns.iloc[-min_length:]
        
        returns_df = pd.DataFrame(aligned_returns)
        covariance_matrix = returns_df.cov() * 12  # Annualized
        
        # Risk parity optimization
        from scipy.optimize import minimize
        
        def risk_contribution_objective(weights):
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            risk_contributions = []
            for i in range(len(weights)):
                risk_contribution = weights[i] * np.dot(covariance_matrix.iloc[i], weights) / portfolio_risk
                risk_contributions.append(risk_contribution)
            
            # Penalty for unequal risk contributions
            target_contribution = portfolio_risk / len(weights)
            penalty = sum((rc - target_contribution) ** 2 for rc in risk_contributions)
            return penalty
        
        # Constraints: weights sum to 1, all weights >= 0
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = [(0, 1) for _ in range(len(tickers))]
        
        # Initial guess: equal weights
        initial_weights = np.array([1/len(tickers)] * len(tickers))
        
        # Optimize
        result = minimize(risk_contribution_objective, initial_weights, 
                        method='SLSQP', bounds=bounds, constraints=constraints)
        
        if not result.success:
            raise HTTPException(status_code=500, detail="Optimization failed")
        
        optimal_weights = result.x
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, [np.mean(returns) * 12 for returns in aligned_returns.values()])
        portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(covariance_matrix, optimal_weights)))
        
        # Calculate risk contributions
        risk_contributions = []
        for i, ticker in enumerate(tickers):
            risk_contribution = optimal_weights[i] * np.dot(covariance_matrix.iloc[i], optimal_weights) / portfolio_risk
            risk_contributions.append({
                'ticker': ticker,
                'weight': optimal_weights[i],
                'risk_contribution': risk_contribution,
                'risk_contribution_pct': (risk_contribution / portfolio_risk) * 100
            })
        
        return {
            'optimization_type': 'risk_parity',
            'target_risk': target_risk,
            'portfolio_metrics': {
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - 0.02) / portfolio_risk if portfolio_risk > 0 else 0
            },
            'allocations': [
                {
                    'ticker': ticker,
                    'weight': weight,
                    'allocation_pct': weight * 100
                }
                for ticker, weight in zip(tickers, optimal_weights)
            ],
            'risk_contributions': risk_contributions,
            'optimization_success': result.success
        }
        
    except Exception as e:
        logger.error(f"Error in risk parity optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Error in risk parity optimization: {str(e)}")

@router.post("/optimize/mean-variance")
async def optimize_mean_variance(request: dict):
    """
    Optimize portfolio using mean-variance optimization (Markowitz)
    Returns: Mean-variance optimized weights and efficient frontier
    """
    try:
        tickers = request.get('tickers', [])
        target_return = request.get('target_return', None)
        risk_aversion = request.get('risk_aversion', 1.0)  # Default risk aversion
        
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required for optimization")
        
        # Get price data for all tickers
        price_data = {}
        for ticker in tickers:
            data = enhanced_data_fetcher.get_monthly_data(ticker)
            if data and data['prices']:
                price_data[ticker] = data['prices']
        
        if len(price_data) < 2:
            raise HTTPException(status_code=404, detail="Insufficient price data for optimization")
        
        # Calculate returns and covariance matrix
        returns_data = {}
        for ticker, prices in price_data.items():
            returns = pd.Series(prices).pct_change().dropna()
            returns_data[ticker] = returns
        
        # Align all returns to same length
        min_length = min(len(returns) for returns in returns_data.values())
        aligned_returns = {}
        for ticker, returns in returns_data.items():
            aligned_returns[ticker] = returns.iloc[-min_length:]
        
        returns_df = pd.DataFrame(aligned_returns)
        expected_returns = returns_df.mean() * 12  # Annualized
        covariance_matrix = returns_df.cov() * 12  # Annualized
        
        # Mean-variance optimization
        from scipy.optimize import minimize
        
        if target_return is not None:
            # Constrained optimization: minimize risk for target return
            def objective(weights):
                portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
                return portfolio_risk
            
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
                {'type': 'eq', 'fun': lambda x: np.dot(x, expected_returns) - target_return}  # Target return
            ]
        else:
            # Unconstrained optimization: maximize utility function
            def objective(weights):
                portfolio_return = np.dot(weights, expected_returns)
                portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
                utility = portfolio_return - 0.5 * risk_aversion * portfolio_risk ** 2
                return -utility  # Minimize negative utility
            
            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        
        bounds = [(0, 1) for _ in range(len(tickers))]
        initial_weights = np.array([1/len(tickers)] * len(tickers))
        
        # Optimize
        result = minimize(objective, initial_weights, 
                        method='SLSQP', bounds=bounds, constraints=constraints)
        
        if not result.success:
            raise HTTPException(status_code=500, detail="Optimization failed")
        
        optimal_weights = result.x
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, expected_returns)
        portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(covariance_matrix, optimal_weights)))
        
        # Generate efficient frontier points
        frontier_points = []
        return_range = np.linspace(expected_returns.min(), expected_returns.max(), 20)
        
        for target_ret in return_range:
            try:
                constraints = [
                    {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                    {'type': 'eq', 'fun': lambda x: np.dot(x, expected_returns) - target_ret}
                ]
                
                frontier_result = minimize(
                    lambda x: np.sqrt(np.dot(x.T, np.dot(covariance_matrix, x))),
                    initial_weights, method='SLSQP', bounds=bounds, constraints=constraints
                )
                
                if frontier_result.success:
                    frontier_weights = frontier_result.x
                    frontier_risk = np.sqrt(np.dot(frontier_weights.T, np.dot(covariance_matrix, frontier_weights)))
                    frontier_points.append({
                        'return': target_ret,
                        'risk': frontier_risk,
                        'weights': frontier_weights.tolist()
                    })
            except:
                continue
        
        return {
            'optimization_type': 'mean_variance',
            'target_return': target_return,
            'risk_aversion': risk_aversion,
            'portfolio_metrics': {
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - 0.02) / portfolio_risk if portfolio_risk > 0 else 0
            },
            'allocations': [
                {
                    'ticker': ticker,
                    'weight': weight,
                    'allocation_pct': weight * 100
                }
                for ticker, weight in zip(tickers, optimal_weights)
            ],
            'efficient_frontier': frontier_points,
            'optimization_success': result.success
        }
        
    except Exception as e:
        logger.error(f"Error in mean-variance optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Error in mean-variance optimization: {str(e)}")

@router.get("/analytics/performance-attribution")
async def performance_attribution(portfolio_id: str = None, allocations: str = None):
    """
    Analyze performance attribution for a portfolio
    Returns: Performance breakdown by asset, sector, and factor
    """
    try:
        # Parse allocations if provided as string
        if allocations:
            import json
            try:
                allocation_data = json.loads(allocations)
            except:
                raise HTTPException(status_code=400, detail="Invalid allocations format")
        else:
            raise HTTPException(status_code=400, detail="Portfolio allocations required")
        
        # Extract tickers and weights
        tickers = [item['symbol'] for item in allocation_data]
        weights = [item['allocation'] / 100 for item in allocation_data]  # Convert to decimal
        
        if len(tickers) < 1:
            raise HTTPException(status_code=400, detail="At least one asset required")
        
        # Get price data for all assets
        price_data = {}
        for ticker in tickers:
            data = enhanced_data_fetcher.get_monthly_data(ticker)
            if data and data['prices']:
                price_data[ticker] = data['prices']
        
        if not price_data:
            raise HTTPException(status_code=404, detail="No price data available")
        
        # Calculate returns for each asset
        returns_data = {}
        asset_performance = {}
        
        for ticker, prices in price_data.items():
            returns = pd.Series(prices).pct_change().dropna()
            returns_data[ticker] = returns
            
            # Calculate individual asset metrics
            annual_return = (1 + returns.mean()) ** 12 - 1
            annual_risk = returns.std() * np.sqrt(12)
            
            asset_performance[ticker] = {
                'annual_return': annual_return,
                'annual_risk': annual_risk,
                'sharpe_ratio': (annual_return - 0.02) / annual_risk if annual_risk > 0 else 0,
                'data_points': len(returns)
            }
        
        # Calculate portfolio-level metrics
        portfolio_return = sum(weights[i] * asset_performance[tickers[i]]['annual_return'] 
                             for i in range(len(tickers)) if tickers[i] in asset_performance)
        portfolio_risk = 0
        
        if len(tickers) > 1:
            # Calculate portfolio risk using correlation
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr().fillna(0)
            
            for i, ticker1 in enumerate(tickers):
                for j, ticker2 in enumerate(tickers):
                    if ticker1 in asset_performance and ticker2 in asset_performance:
                        corr = correlation_matrix.loc[ticker1, ticker2] if not pd.isna(correlation_matrix.loc[ticker1, ticker2]) else 0
                        portfolio_risk += weights[i] * weights[j] * asset_performance[ticker1]['annual_risk'] * asset_performance[ticker2]['annual_risk'] * corr
            
            portfolio_risk = np.sqrt(portfolio_risk)
        else:
            portfolio_risk = asset_performance[tickers[0]]['annual_risk']
        
        # Calculate attribution metrics
        attribution_analysis = []
        for i, ticker in enumerate(tickers):
            if ticker in asset_performance:
                asset_return = asset_performance[ticker]['annual_return']
                weight = weights[i]
                
                # Return contribution
                return_contribution = weight * asset_return
                return_contribution_pct = (return_contribution / portfolio_return) * 100 if portfolio_return != 0 else 0
                
                # Risk contribution
                risk_contribution = weight * asset_performance[ticker]['annual_risk']
                risk_contribution_pct = (risk_contribution / portfolio_risk) * 100 if portfolio_risk != 0 else 0
                
                # Information ratio (excess return per unit of risk)
                excess_return = asset_return - 0.02  # Assuming 2% risk-free rate
                information_ratio = excess_return / asset_performance[ticker]['annual_risk'] if asset_performance[ticker]['annual_risk'] > 0 else 0
                
                attribution_analysis.append({
                    'ticker': ticker,
                    'weight': weight,
                    'weight_pct': weight * 100,
                    'asset_return': asset_return,
                    'asset_risk': asset_performance[ticker]['annual_risk'],
                    'return_contribution': return_contribution,
                    'return_contribution_pct': return_contribution_pct,
                    'risk_contribution': risk_contribution,
                    'risk_contribution_pct': risk_contribution_pct,
                    'information_ratio': information_ratio,
                    'sharpe_ratio': asset_performance[ticker]['sharpe_ratio']
                })
        
        # Sort by return contribution
        attribution_analysis.sort(key=lambda x: x['return_contribution'], reverse=True)
        
        return {
            'portfolio_id': portfolio_id,
            'portfolio_metrics': {
                'total_return': portfolio_return,
                'total_risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - 0.02) / portfolio_risk if portfolio_risk > 0 else 0
            },
            'attribution_analysis': attribution_analysis,
            'summary': {
                'top_contributor': attribution_analysis[0] if attribution_analysis else None,
                'bottom_contributor': attribution_analysis[-1] if attribution_analysis else None,
                'total_assets': len(tickers),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in performance attribution: {e}")
        raise HTTPException(status_code=500, detail=f"Error in performance attribution: {str(e)}")

@router.get("/analytics/risk-decomposition")
async def risk_decomposition(allocations: str):
    """
    Decompose portfolio risk into systematic and idiosyncratic components
    Returns: Risk breakdown and factor analysis
    """
    try:
        # Parse allocations
        import json
        try:
            allocation_data = json.loads(allocations)
        except:
            raise HTTPException(status_code=400, detail="Invalid allocations format")
        
        tickers = [item['symbol'] for item in allocation_data]
        weights = [item['allocation'] / 100 for item in allocation_data]
        
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 assets required for risk decomposition")
        
        # Get price data
        price_data = {}
        for ticker in tickers:
            data = enhanced_data_fetcher.get_monthly_data(ticker)
            if data and data['prices']:
                price_data[ticker] = data['prices']
        
        if len(price_data) < 2:
            raise HTTPException(status_code=404, detail="Insufficient price data")
        
        # Calculate returns and covariance
        returns_data = {}
        for ticker, prices in price_data.items():
            returns = pd.Series(prices).pct_change().dropna()
            returns_data[ticker] = returns
        
        # Align returns
        min_length = min(len(returns) for returns in returns_data.values())
        aligned_returns = {}
        for ticker, returns in returns_data.items():
            aligned_returns[ticker] = returns.iloc[-min_length:]
        
        returns_df = pd.DataFrame(aligned_returns)
        covariance_matrix = returns_df.cov() * 12  # Annualized
        
        # Calculate portfolio risk
        weights_array = np.array(weights)
        portfolio_risk = np.sqrt(np.dot(weights_array.T, np.dot(covariance_matrix, weights_array)))
        
        # Risk decomposition by asset
        risk_decomposition = []
        for i, ticker in enumerate(tickers):
            # Marginal risk contribution
            marginal_risk = np.dot(covariance_matrix.iloc[i], weights_array) / portfolio_risk if portfolio_risk > 0 else 0
            
            # Risk contribution
            risk_contribution = weights_array[i] * marginal_risk
            
            # Percentage contribution
            risk_contribution_pct = (risk_contribution / portfolio_risk) * 100 if portfolio_risk > 0 else 0
            
            risk_decomposition.append({
                'ticker': ticker,
                'weight': weights[i],
                'weight_pct': weights[i] * 100,
                'marginal_risk': marginal_risk,
                'risk_contribution': risk_contribution,
                'risk_contribution_pct': risk_contribution_pct
            })
        
        # Sort by risk contribution
        risk_decomposition.sort(key=lambda x: x['risk_contribution'], reverse=True)
        
        # Calculate concentration metrics
        herfindahl_index = sum(w**2 for w in weights)
        concentration_ratio = max(weights)
        
        # Factor analysis (simplified)
        # Calculate correlation with market proxy (equal-weighted portfolio)
        market_returns = returns_df.mean(axis=1)
        factor_loadings = {}
        
        for ticker in tickers:
            if ticker in aligned_returns:
                correlation = aligned_returns[ticker].corr(market_returns)
                factor_loadings[ticker] = correlation if not pd.isna(correlation) else 0
        
        return {
            'portfolio_risk': portfolio_risk,
            'risk_decomposition': risk_decomposition,
            'concentration_metrics': {
                'herfindahl_index': herfindahl_index,
                'concentration_ratio': concentration_ratio,
                'effective_number_of_assets': 1 / herfindahl_index if herfindahl_index > 0 else 0
            },
            'factor_analysis': {
                'market_correlation': factor_loadings,
                'average_market_correlation': np.mean(list(factor_loadings.values())) if factor_loadings else 0
            },
            'summary': {
                'highest_risk_contributor': risk_decomposition[0] if risk_decomposition else None,
                'lowest_risk_contributor': risk_decomposition[-1] if risk_decomposition else None,
                'total_assets': len(tickers),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in risk decomposition: {e}")
        raise HTTPException(status_code=500, detail=f"Error in risk decomposition: {str(e)}") 

@router.post("/rebalance/check")
async def check_rebalancing_needs(request: dict):
    """
    Check if portfolio needs rebalancing based on drift thresholds
    Returns: Rebalancing recommendations and drift analysis
    """
    try:
        current_allocations = request.get('current_allocations', [])
        target_allocations = request.get('target_allocations', [])
        drift_threshold = request.get('drift_threshold', 5.0)  # Default 5% threshold
        
        if not current_allocations or not target_allocations:
            raise HTTPException(status_code=400, detail="Both current and target allocations required")
        
        if len(current_allocations) != len(target_allocations):
            raise HTTPException(status_code=400, detail="Current and target allocations must have same length")
        
        # Calculate drift for each asset
        drift_analysis = []
        total_drift = 0
        needs_rebalancing = False
        
        for current, target in zip(current_allocations, target_allocations):
            if current['symbol'] != target['symbol']:
                continue
                
            current_weight = current['allocation']
            target_weight = target['allocation']
            drift = current_weight - target_weight
            drift_pct = abs(drift)
            
            if drift_pct > drift_threshold:
                needs_rebalancing = True
            
            drift_analysis.append({
                'symbol': current['symbol'],
                'current_allocation': current_weight,
                'target_allocation': target_weight,
                'drift': drift,
                'drift_pct': drift_pct,
                'exceeds_threshold': drift_pct > drift_threshold,
                'action_needed': 'buy' if drift < 0 else 'sell' if drift > 0 else 'hold'
            })
            
            total_drift += drift_pct
        
        # Calculate portfolio-level metrics
        portfolio_drift = total_drift / len(drift_analysis) if drift_analysis else 0
        assets_exceeding_threshold = sum(1 for item in drift_analysis if item['exceeds_threshold'])
        
        # Generate rebalancing recommendations
        rebalancing_recommendations = []
        for item in drift_analysis:
            if item['exceeds_threshold']:
                action = item['action_needed']
                adjustment = abs(item['drift'])
                
                if action == 'buy':
                    rebalancing_recommendations.append({
                        'symbol': item['symbol'],
                        'action': 'buy',
                        'current_allocation': item['current_allocation'],
                        'target_allocation': item['target_allocation'],
                        'adjustment_needed': adjustment,
                        'priority': 'high' if adjustment > drift_threshold * 2 else 'medium'
                    })
                elif action == 'sell':
                    rebalancing_recommendations.append({
                        'symbol': item['symbol'],
                        'action': 'sell',
                        'current_allocation': item['current_allocation'],
                        'target_allocation': item['target_allocation'],
                        'adjustment_needed': adjustment,
                        'priority': 'high' if adjustment > drift_threshold * 2 else 'medium'
                    })
        
        return {
            'needs_rebalancing': needs_rebalancing,
            'portfolio_drift': portfolio_drift,
            'assets_exceeding_threshold': assets_exceeding_threshold,
            'drift_threshold': drift_threshold,
            'drift_analysis': drift_analysis,
            'rebalancing_recommendations': rebalancing_recommendations,
            'summary': {
                'total_assets': len(drift_analysis),
                'assets_needing_rebalancing': len(rebalancing_recommendations),
                'high_priority_actions': len([r for r in rebalancing_recommendations if r['priority'] == 'high']),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking rebalancing needs: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking rebalancing needs: {str(e)}")

@router.post("/monitor/performance-tracking")
async def track_portfolio_performance(request: dict):
    """
    Track portfolio performance over time with historical analysis
    Returns: Performance tracking data and analytics
    """
    try:
        portfolio_snapshot = request.get('portfolio_snapshot', {})
        allocations = portfolio_snapshot.get('allocations', [])
        start_date = request.get('start_date')
        end_date = request.get('end_date')
        
        if not allocations:
            raise HTTPException(status_code=400, detail="Portfolio allocations required")
        
        # Get tickers and weights
        tickers = [item['symbol'] for item in allocations]
        weights = [item['allocation'] / 100 for item in allocations]
        
        # Get historical data for all assets
        price_data = {}
        for ticker in tickers:
            data = enhanced_data_fetcher.get_monthly_data(ticker)
            if data and data['prices']:
                price_data[ticker] = data['prices']
        
        if not price_data:
            raise HTTPException(status_code=404, detail="No price data available")
        
        # Calculate portfolio performance over time
        portfolio_values = []
        benchmark_values = []  # Equal-weighted benchmark
        
        # Find common date range
        all_dates = set()
        for ticker, prices in price_data.items():
            if isinstance(prices, dict):  # If prices is a date-price dict
                all_dates.update(prices.keys())
            else:  # If prices is a list
                all_dates.update(range(len(prices)))
        
        if isinstance(list(all_dates)[0], str):  # Date strings
            sorted_dates = sorted(all_dates)
        else:  # Numeric indices
            sorted_dates = sorted(all_dates)
        
        # Calculate portfolio value at each point
        for date_idx in sorted_dates:
            portfolio_value = 0
            benchmark_value = 0
            
            for i, ticker in enumerate(tickers):
                if ticker in price_data:
                    if isinstance(price_data[ticker], dict):
                        price = price_data[ticker].get(str(date_idx), 0)
                    else:
                        price = price_data[ticker][date_idx] if date_idx < len(price_data[ticker]) else 0
                    
                    if price > 0:
                        portfolio_value += weights[i] * price
                        benchmark_value += (1 / len(tickers)) * price
            
            if portfolio_value > 0:
                portfolio_values.append(portfolio_value)
                benchmark_values.append(benchmark_value)
        
        # Calculate performance metrics
        if len(portfolio_values) > 1:
            portfolio_returns = []
            benchmark_returns = []
            
            for i in range(1, len(portfolio_values)):
                if portfolio_values[i-1] > 0:
                    portfolio_ret = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
                    portfolio_returns.append(portfolio_ret)
                
                if benchmark_values[i-1] > 0:
                    benchmark_ret = (benchmark_values[i] - benchmark_values[i-1]) / benchmark_values[i-1]
                    benchmark_returns.append(benchmark_ret)
            
            # Portfolio metrics
            total_return = (portfolio_values[-1] / portfolio_values[0] - 1) * 100 if portfolio_values[0] > 0 else 0
            annualized_return = ((portfolio_values[-1] / portfolio_values[0]) ** (12 / len(portfolio_values)) - 1) * 100 if portfolio_values[0] > 0 else 0
            volatility = np.std(portfolio_returns) * np.sqrt(12) * 100 if portfolio_returns else 0
            sharpe_ratio = (np.mean(portfolio_returns) * 12 - 0.02) / (np.std(portfolio_returns) * np.sqrt(12)) if portfolio_returns and np.std(portfolio_returns) > 0 else 0
            
            # Benchmark metrics
            benchmark_total_return = (benchmark_values[-1] / benchmark_values[0] - 1) * 100 if benchmark_values[0] > 0 else 0
            benchmark_annualized_return = ((benchmark_values[-1] / benchmark_values[0]) ** (12 / len(benchmark_values)) - 1) * 100 if benchmark_values[0] > 0 else 0
            
            # Tracking error and information ratio
            excess_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
            tracking_error = np.std(excess_returns) * np.sqrt(12) * 100 if excess_returns else 0
            information_ratio = (np.mean(excess_returns) * 12) / (np.std(excess_returns) * np.sqrt(12)) if excess_returns and np.std(excess_returns) > 0 else 0
            
            # Maximum drawdown
            peak = portfolio_values[0]
            max_drawdown = 0
            for value in portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            performance_metrics = {
                'total_return_pct': round(total_return, 2),
                'annualized_return_pct': round(annualized_return, 2),
                'volatility_pct': round(volatility, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown_pct': round(max_drawdown, 2),
                'tracking_error_pct': round(tracking_error, 2),
                'information_ratio': round(information_ratio, 2),
                'benchmark_total_return_pct': round(benchmark_total_return, 2),
                'benchmark_annualized_return_pct': round(benchmark_annualized_return, 2),
                'excess_return_pct': round(total_return - benchmark_total_return, 2)
            }
        else:
            performance_metrics = {
                'total_return_pct': 0,
                'annualized_return_pct': 0,
                'volatility_pct': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'tracking_error_pct': 0,
                'information_ratio': 0,
                'benchmark_total_return_pct': 0,
                'benchmark_annualized_return_pct': 0,
                'excess_return_pct': 0
            }
        
        return {
            'portfolio_snapshot': portfolio_snapshot,
            'performance_metrics': performance_metrics,
            'time_series': {
                'dates': sorted_dates,
                'portfolio_values': portfolio_values,
                'benchmark_values': benchmark_values
            },
            'analysis_period': {
                'start_date': sorted_dates[0] if sorted_dates else None,
                'end_date': sorted_dates[-1] if sorted_dates else None,
                'data_points': len(portfolio_values)
            },
            'summary': {
                'total_assets': len(tickers),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error tracking portfolio performance: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking portfolio performance: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for portfolio service
    Returns: Service status and dependencies
    """
    try:
        # Check Redis connection
        redis_status = "healthy"
        try:
            redis_client.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        # Check data fetcher status
        data_fetcher_status = "healthy"
        try:
            cache_status = enhanced_data_fetcher.get_cache_status()
            data_fetcher_status = "healthy" if cache_status else "unhealthy"
        except Exception as e:
            data_fetcher_status = f"unhealthy: {str(e)}"
        
        # Check portfolio analytics
        analytics_status = "healthy"
        try:
            # Simple test calculation
            test_data = {'allocations': [{'symbol': 'AAPL', 'allocation': 100}]}
            test_result = portfolio_analytics.calculate_real_portfolio_metrics(test_data)
            analytics_status = "healthy" if test_result else "unhealthy"
        except Exception as e:
            analytics_status = f"unhealthy: {str(e)}"
        
        return {
            'service': 'portfolio-service',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'dependencies': {
                'redis': redis_status,
                'data_fetcher': data_fetcher_status,
                'portfolio_analytics': analytics_status
            },
            'version': '1.0.0'
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'service': 'portfolio-service',
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }

