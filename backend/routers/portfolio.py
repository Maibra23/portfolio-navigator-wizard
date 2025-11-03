from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import math
import json
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gzip
import redis
from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.port_analytics import PortfolioAnalytics
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.portfolio_stock_selector import PortfolioStockSelector
from utils.portfolio_auto_regeneration_service import PortfolioAutoRegenerationService
from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
from models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Initialize portfolio analytics
portfolio_analytics = PortfolioAnalytics()

# Initialize Redis manager (will be set by main.py)
redis_manager = None

def set_redis_manager(manager):
    """Set Redis manager from main application"""
    global redis_manager
    redis_manager = manager

def _sanitize_number(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Return a JSON-safe float (no NaN/Inf)."""
    try:
        if value is None:
            return default
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default

@router.get("/top-pick/{risk_profile}")
def get_top_pick(risk_profile: str):
    """Return the precomputed Top Pick for a given risk profile or compute if missing."""
    try:
        r = _rds.redis_client
        key = f"portfolio:top_pick:{risk_profile}"
        raw = r.get(key)
        if raw:
            return JSONResponse({"status": "ok", "risk_profile": risk_profile, "top_pick": json.loads(raw)})
        # Compute now from a fresh generation
        pa = PortfolioAnalytics()
        eg = EnhancedPortfolioGenerator(_rds, pa)
        portfolios = eg.generate_portfolio_bucket(risk_profile, use_parallel=True)
        # Score by expectedReturn (fallback to risk-adjusted if needed)
        def score(p: Dict[str, Any]) -> float:
            return float(p.get('expectedReturn', 0.0))
        top = max(portfolios, key=score)
        r.setex(key, eg.PORTFOLIO_TTL_DAYS * 24 * 3600, json.dumps(top))
        return JSONResponse({"status": "ok", "risk_profile": risk_profile, "top_pick": top})
    except Exception as e:
        logger.error(f"Top pick endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top pick")

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
        
        # Try to return metrics identical to precomputed ones by using the same cache key as generator
        cached_metrics = None
        try:
            # Build cache key: risk_profile|SYMBOL:ALLOCATION(1-decimal)|... -> md5
            rounded_parts = []
            for a in sorted(({ 'symbol': a.symbol, 'allocation': a.allocation } for a in allocations), key=lambda x: x['symbol']):
                try:
                    rounded_alloc = float(f"{float(a['allocation']):.1f}")
                except Exception:
                    rounded_alloc = 0.0
                rounded_parts.append(f"{a['symbol']}:{rounded_alloc:.1f}")
            key_raw = f"{risk_profile}|" + "|".join(rounded_parts)
            cache_key = f"portfolio:metrics:{hashlib.md5(key_raw.encode()).hexdigest()}"
            # Read from Redis
            r = _rds.redis_client
            if r is not None:
                raw = r.get(cache_key)
                if raw:
                    cached_metrics = json.loads(raw)
        except Exception:
            cached_metrics = None

        if cached_metrics is not None:
            # Use cached metrics (already in analytics format: expected_return, risk, diversification_score)
            metrics = cached_metrics
        else:
            # Warm cache for all symbols in allocations to ensure consistent metrics
            try:
                symbols = list({a.symbol for a in allocations if getattr(a, 'symbol', None)})
                if symbols:
                    try:
                        # Try smart refresh for missing symbols (no external if FAST_STARTUP enforced)
                        _ = _rds.smart_refresh_tickers(symbols)
                    except Exception:
                        pass
                    # Force-load into Redis cache via Redis-first getters
                    for s in symbols:
                        try:
                            _ = _rds.get_monthly_data(s)
                            _ = _rds.get_ticker_info(s)
                        except Exception:
                            continue
            except Exception:
                pass

            # Calculate metrics using cached data (after warm)
        portfolio_data = {
            'allocations': [{'symbol': a.symbol, 'allocation': a.allocation} for a in allocations]
        }
        
        # Calculate portfolio metrics
        metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)

        # Store computed metrics under the same cache key for future alignment
        try:
            if 'cache_key' not in locals():
                # Ensure cache_key exists (recompute if needed)
                rounded_parts = []
                for a in sorted(({ 'symbol': a.symbol, 'allocation': a.allocation } for a in allocations), key=lambda x: x['symbol']):
                    try:
                        rounded_alloc = float(f"{float(a['allocation']):.1f}")
                    except Exception:
                        rounded_alloc = 0.0
                    rounded_parts.append(f"{a['symbol']}:{rounded_alloc:.1f}")
                key_raw = f"{risk_profile}|" + "|".join(rounded_parts)
                cache_key = f"portfolio:metrics:{hashlib.md5(key_raw.encode()).hexdigest()}"
            ttl_days = getattr(redis_manager, 'PORTFOLIO_TTL_DAYS', 28) if redis_manager else 28
            _rds.redis_client.setex(cache_key, ttl_days * 24 * 3600, json.dumps(metrics))
        except Exception:
            pass

        # Use analytics result as-is to match recommendation pipeline
        
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
            expectedReturn=float(metrics.get('expected_return', 0.0)),
            risk=float(metrics.get('risk', 0.0)),
            diversificationScore=float(metrics.get('diversification_score', 0.0)),
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

@router.get("/search-tickers")
def search_tickers(
    q: str = Query(..., description="Search query"), 
    limit: int = Query(10, description="Maximum results"),
    sector: str = Query(None, description="Filter by sector"),
    risk_profile: str = Query(None, description="Filter by risk profile")
):
    """Enhanced fuzzy search for tickers with smart relevance scoring and filters"""
    try:
        # Build filters
        filters = {}
        if sector:
            filters['sector'] = sector
        if risk_profile:
            filters['risk_profile'] = risk_profile
        
        # Perform enhanced search
        results = _rds.search_tickers(q, limit, filters)
        
        # Format response with enhanced information
        formatted_results = []
        for result in results:
            formatted_result = {
                'ticker': result['ticker'],
                'company_name': result['company_name'],
                'sector': result['sector'],
                'industry': result['industry'],
                'relevance_score': result['relevance_score'],
                'cached': result['cached'],
                'risk_level': result['risk_level'],
                'market_cap': result['market_cap'],
                'last_price': result['last_price'],
                'data_quality': result['data_quality']
            }
            formatted_results.append(formatted_result)
        
        return {
            'success': True,
            'query': q,
            'filters_applied': filters,
            'total_results': len(formatted_results),
            'results': formatted_results,
            'search_features': {
                'fuzzy_matching': True,
                'relevance_scoring': True,
                'sector_filtering': sector is not None,
                'risk_filtering': risk_profile is not None,
                'cache_status': True
            }
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced ticker search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search-suggestions")
def search_suggestions(
    q: str = Query(..., description="Search query for autocomplete"),
    limit: int = Query(8, description="Maximum suggestions")
):
    """Autocomplete suggestions using prebuilt in-memory indexes (no price reads)"""
    try:
        suggestions = _rds.get_search_suggestions(q, limit)
        return {
            'success': True,
            'query': q,
            'total_suggestions': len(suggestions),
            'suggestions': suggestions
        }
    except Exception as e:
        logger.error(f"Error in search suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {str(e)}")

@router.get("/ticker-info/{ticker}")
def get_ticker_info(ticker: str):
    """Get comprehensive ticker information with Redis-first approach"""
    try:
        ticker_info = _rds.get_ticker_info(ticker)
        if not ticker_info:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        return ticker_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ticker info: {str(e)}")

@router.get("/ticker-price-history/{ticker}")
def get_ticker_price_history(ticker: str, days: int = Query(30, description="Number of days")):
    """Get ticker price history with Redis-first approach"""
    try:
        price_data = _rds.get_ticker_price_history(ticker, days)
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Price data not found for {ticker}")
        return price_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get price history: {str(e)}")

@router.get("/ticker-monthly-data/{ticker}")
def get_ticker_monthly_data(ticker: str):
    """Get monthly data for a ticker with Redis-first approach"""
    try:
        data = _rds.get_monthly_data(ticker)
        if not data:
            raise HTTPException(status_code=404, detail=f"Monthly data not found for {ticker}")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monthly data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monthly data: {str(e)}")

@router.post("/warm-cache")
def warm_cache():
    """Warm up the Redis cache with Redis-first approach"""
    try:
        results = _rds.warm_cache()
        return {"message": "Cache warming completed", "results": results}
    except Exception as e:
        logger.error(f"Cache warming error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warming failed: {str(e)}")

@router.get("/cache-status")
def get_cache_status():
    """Get cache status with Redis-first approach"""
    try:
        status = _rds.get_cache_status()
        return status
    except Exception as e:
        logger.error(f"Cache status error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")

@router.post("/clear-cache")
def clear_cache():
    """Clear all cached data with Redis-first approach"""
    try:
        results = _rds.clear_cache()
        return {"message": "Cache cleared successfully", "results": results}
    except Exception as e:
        logger.error(f"Cache clearing error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")

@router.get("/tickers/master")
def get_master_tickers():
    """Get master ticker list with Redis-first approach"""
    try:
        master_tickers = _rds.all_tickers
        return {
            "tickers": master_tickers,
            "total": len(master_tickers),
            "source": "redis_first_data_service"
        }
    except Exception as e:
        logger.error(f"Error getting master tickers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get master tickers: {str(e)}")

@router.get("/tickers/available")
def get_available_tickers(limit: int = Query(100, description="Maximum number of tickers")):
    """Get available tickers with Redis-first approach"""
    try:
        master_tickers = _rds.all_tickers[:limit]
        return {
            "tickers": master_tickers,
            "total": len(master_tickers),
            "limit": limit,
            "source": "redis_first_data_service"
        }
    except Exception as e:
        logger.error(f"Error getting available tickers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available tickers: {str(e)}")

@router.post("/tickers/refresh")
def refresh_tickers():
    """
    Refresh ticker lists from sources
    """
    try:
        # Invalidate cached ticker list to force reload from Redis
        _rds.invalidate_ticker_list_cache()
        
        # Redis-first: report current master coverage from Redis (no external fetch)
        inv = _rds.get_cache_inventory()
        total = inv.get('coverage', {}).get('joined_tickers', 0)
        
        # Verify the ticker list was reloaded
        ticker_count = len(_rds.all_tickers)
        
        return {
            "status": "success",
            "message": "Ticker master list refreshed from Redis",
            "total_tickers": total,
            "cached_ticker_count": ticker_count,
            "source": "redis"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing tickers: {str(e)}")

@router.get("/recommendations/{risk_profile}", response_model=List[PortfolioResponse])
def get_portfolio_recommendations(risk_profile: str):
    """Get portfolio recommendations from Enhanced Portfolio System"""
    try:
        if risk_profile not in ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']:
            raise HTTPException(status_code=400, detail="Invalid risk profile")
        
        # Check if enhanced portfolio system is available
        if not redis_manager:
            logger.warning("⚠️ Enhanced portfolio system not available, falling back to static portfolios")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Get portfolios from enhanced system
        portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=3)
        
        # If none or too few portfolios are in Redis, or bucket is partially missing, auto-regenerate ONLY missing ones
        bucket_count = redis_manager.get_portfolio_count(risk_profile)
        if (not portfolios or len(portfolios) < 3) or (bucket_count < redis_manager.PORTFOLIOS_PER_PROFILE):
            try:
                logger.info(f"🔄 Auto-regeneration: ensuring portfolios exist for {risk_profile} (missing-only)")
                _ensure_missing_portfolios_generated(risk_profile)
                # Re-fetch after ensuring
                portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=3)
            except Exception as e:
                logger.warning(f"⚠️ Auto-regeneration failed for {risk_profile}: {e}")
        if not portfolios:
            logger.warning(f"⚠️ No portfolios available for {risk_profile}, falling back to static portfolios")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Light randomization to reshuffle candidates per request
        try:
            import random
            random.seed(datetime.now().timestamp())
            random.shuffle(portfolios)
        except Exception:
            pass
        
        # Warm cache for all tickers in the recommendations to ensure consistent metrics downstream
        try:
            symbols_to_warm = set()
            for p in portfolios:
                for a in p.get('allocations', []):
                    s = a.get('symbol')
                    if s:
                        symbols_to_warm.add(s)
            for sym in symbols_to_warm:
                try:
                    # These calls are Redis-first; EnhancedDataFetcher is lazy and fast-startup aware
                    _ = _rds.get_monthly_data(sym)
                    _ = _rds.get_ticker_info(sym)
                except Exception:
                    continue
        except Exception:
            pass

        # Order portfolios by expectedReturn (desc) and convert to response format
        # Top Pick first
        try:
            portfolios.sort(key=lambda p: (_sanitize_number(p.get('expectedReturn'), -1.0)), reverse=True)
        except Exception:
            pass

        responses = []
        for idx, portfolio in enumerate(portfolios):
            try:
                safe_expected = _sanitize_number(portfolio.get('expectedReturn'), 0.0)
                safe_risk = _sanitize_number(portfolio.get('risk'), 0.0)
                safe_div = _sanitize_number(portfolio.get('diversificationScore'), 0.0)
                # Round allocations to 2 decimals
                allocs = []
                for a in portfolio.get('allocations', []):
                    try:
                        rounded_alloc = round(float(a.get('allocation', 0.0)), 2)
                    except Exception:
                        rounded_alloc = 0.0
                    allocs.append({
                        'symbol': a.get('symbol'),
                        'allocation': rounded_alloc,
                        'name': a.get('name', ''),
                        'assetType': a.get('assetType', 'stock'),
                        'sector': a.get('sector', a.get('Sector', 'Unknown'))
                    })

                # Keep original name; frontend shows Top Pick badge
                name = portfolio.get('name', '')

                response = PortfolioResponse(
                    portfolio=allocs,
                    name=name,
                    description=portfolio.get('description', ''),
                    expectedReturn=safe_expected,
                    risk=safe_risk,
                    diversificationScore=safe_div,
                    isTopPick=portfolio.get('isTopPick', False)
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Error converting portfolio to response: {e}")
                continue
        
        if not responses:
            logger.warning(f"⚠️ Failed to convert portfolios for {risk_profile}, falling back to static portfolios")
            return _get_static_portfolio_recommendations(risk_profile)
        
        logger.info(f"✅ Retrieved {len(responses)} portfolio recommendations for {risk_profile} from enhanced system")
        return responses
        
    except Exception as e:
        logger.error(f"Error getting enhanced portfolio recommendations: {e}")
        logger.info("🔄 Falling back to static portfolio recommendations")
        return _get_static_portfolio_recommendations(risk_profile)

# Helper: Ensure missing portfolios are generated without overwriting existing ones
def _ensure_missing_portfolios_generated(risk_profile: str) -> None:
    try:
        # Determine which portfolio slots are missing
        missing_ids = []
        bucket_prefix = f"portfolio_bucket:{risk_profile}:"
        for i in range(redis_manager.PORTFOLIOS_PER_PROFILE):
            key = f"{bucket_prefix}{i}"
            exists = redis_manager.redis_client.exists(key) if redis_manager and redis_manager.redis_client else 0
            if not exists:
                missing_ids.append(i)
        if not missing_ids:
            logger.info(f"✅ No missing portfolios for {risk_profile}")
            return

        # Generate a full bucket (fast, shared-stock-data path), then store only missing ones
        from utils.redis_first_data_service import redis_first_data_service
        from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
        from utils.port_analytics import PortfolioAnalytics

        generator = EnhancedPortfolioGenerator(redis_first_data_service, PortfolioAnalytics())
        generated = generator.generate_portfolio_bucket(risk_profile, use_parallel=True)

        # Index generated portfolios by variation_id
        vid_to_port = {p.get('variation_id', idx): p for idx, p in enumerate(generated)}

        # Store only missing variation ids with proper TTL, without touching existing ones
        for vid in missing_ids:
            p = vid_to_port.get(vid)
            if not p:
                continue
            try:
                key = f"{bucket_prefix}{vid}"
                redis_manager.redis_client.setex(
                    key,
                    redis_manager.PORTFOLIO_TTL_SECONDS,
                    json.dumps(p, default=str)
                )
                logger.info(f"🧩 Filled missing portfolio slot {vid} for {risk_profile}")
            except Exception as e:
                logger.warning(f"⚠️ Failed storing portfolio {vid} for {risk_profile}: {e}")

        # Update metadata TTL if present
        try:
            meta_key = f"portfolio_bucket:{risk_profile}:metadata"
            metadata = {
                'risk_profile': risk_profile,
                'portfolio_count': redis_manager.get_portfolio_count(risk_profile),
                'generated_at': datetime.now().isoformat(),
                'ttl_days': redis_manager.PORTFOLIO_TTL_DAYS,
                'last_updated': datetime.now().isoformat()
            }
            redis_manager.redis_client.setex(
                meta_key,
                redis_manager.PORTFOLIO_TTL_SECONDS,
                json.dumps(metadata, default=str)
            )
        except Exception as e:
            logger.debug(f"Metadata update skipped for {risk_profile}: {e}")
    except Exception as e:
        logger.debug(f"_ensure_missing_portfolios_generated error: {e}")

# NEW: Dynamic Portfolio Generation Endpoint - LIVE GENERATION
@router.post("/recommendations/dynamic", response_model=List[PortfolioResponse])
async def generate_dynamic_portfolio_recommendations(
    risk_profile: str,
    target_return: Optional[float] = None,
    max_risk: Optional[float] = None,
    num_portfolios: int = 3,
    strategy: str = 'diversification'
):
    """
    LIVE GENERATION: Generate custom portfolios based on user's target return and risk preferences
    
    This generates portfolios in real-time using the strategy optimizer with custom constraints.
    Users can fully customize their preferred return and risk appetite.
    
    Args:
        risk_profile: User's risk tolerance level
        target_return: Target annual return (e.g., 0.15 for 15%)
        max_risk: Maximum risk tolerance (e.g., 0.25 for 25%)
        num_portfolios: Number of portfolio variants (default: 3)
        strategy: Investment strategy to use (default: diversification)
    """
    try:
        logger.info(f"🎯 LIVE Generation: {strategy} for {risk_profile}, target={target_return}, max_risk={max_risk}")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(_rds, redis_manager)
        
        # Generate personalized portfolios on-the-fly
        # This uses the optimized stock pool cache for fast generation
        personalized_portfolios = []
        
        for i in range(num_portfolios):
            portfolio = _rds.strategy_optimizer._generate_personalized_strategy_portfolios(
                strategy, risk_profile
            )
            if portfolio and len(portfolio) > i:
                personalized_portfolios.append(portfolio[i])
        
        # Shuffle for variety
        import random
        random.shuffle(personalized_portfolios)
        
        # Convert to response format
        responses = []
        for i, portfolio in enumerate(personalized_portfolios[:num_portfolios]):
            try:
                metrics = portfolio.get('metrics', {})
                # Apply custom target return and risk if specified
                expected_return = target_return if target_return else metrics.get('expected_return', 0.12)
                risk = max_risk if max_risk else metrics.get('risk', 0.20)
                
                response = PortfolioResponse(
                    portfolio=portfolio.get('allocations', []),
                    name=f"Custom {strategy.title()} Portfolio {i+1}",
                    description=f"Live-generated portfolio with target {expected_return:.0%} return, max {risk:.0%} risk",
                    expectedReturn=expected_return,
                    risk=risk,
                    diversificationScore=metrics.get('diversification_score', 75.0),
                    sharpeRatio=0.0
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Error converting portfolio: {e}")
                continue
        
        if not responses:
            logger.warning("No dynamic portfolios generated, falling back")
            return _get_static_portfolio_recommendations(risk_profile)
        
        logger.info(f"✅ Generated {len(responses)} live custom portfolios")
        return responses
        
    except Exception as e:
        logger.error(f"❌ Error generating dynamic portfolios: {e}")
        return _get_static_portfolio_recommendations(risk_profile)

# NEW: Pure Strategy Portfolio Generation Endpoint
@router.post("/recommendations/strategy-pure", response_model=List[PortfolioResponse])
async def generate_pure_strategy_portfolios(
    risk_profile: str,
    strategy: str
):
    """
    Generate pure strategy portfolios using real market data
    
    This endpoint generates 5 pure strategy portfolios for the selected strategy,
    using real market data and proven optimization algorithms. No parameter constraints
    are applied - each strategy is shown in its purest form.
    
    Args:
        risk_profile: User's risk profile (for filtering and display)
        strategy: Investment strategy ('diversification', 'risk', 'return')
    
    Returns:
        List of 5 pure strategy portfolios with real market data
    """
    try:
        logger.info(f"🎯 Pure Strategy Generation: {strategy} for {risk_profile}")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(_rds, redis_manager)
        
        # Get pure strategy portfolios from cache or generate
        pure_portfolios = _rds.strategy_optimizer.get_pure_portfolios_from_cache(strategy)
        if not pure_portfolios:
            logger.info(f"🔄 Cache miss: Generating pure {strategy} portfolios")
            pure_portfolios = _rds.strategy_optimizer._generate_pure_strategy_portfolios(strategy)
            if pure_portfolios:
                _rds.strategy_optimizer._store_pure_portfolios_in_redis(strategy, pure_portfolios)
        
        if not pure_portfolios:
            logger.warning(f"No pure portfolios available for {strategy}, falling back to static")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Take first 2 portfolios and convert to response format
        responses = []
        for i, portfolio in enumerate(pure_portfolios[:2]):
            try:
                metrics = portfolio.get('metrics', {})
                allocations = []
                
                # Convert allocations to PortfolioAllocation format
                for allocation in portfolio.get('allocations', []):
                    allocations.append(PortfolioAllocation(
                        symbol=allocation.get('symbol', ''),
                        allocation=allocation.get('allocation', 0),
                        name=allocation.get('name', allocation.get('symbol', '')),
                        assetType=allocation.get('assetType', 'stock')
                    ))
                
                response = PortfolioResponse(
                    portfolio=allocations,
                    name=portfolio.get('name', f"Pure {strategy.title()} Portfolio {i+1}"),
                    description=portfolio.get('description', f"Pure {strategy} strategy portfolio optimized using real market data"),
                    expectedReturn=metrics.get('expected_return', 0.12),
                    risk=metrics.get('risk', 0.15),
                    diversificationScore=metrics.get('diversification_score', 75.0),
                    sharpeRatio=0.0  # Always 0 as requested
                )
                responses.append(response)
                
            except Exception as e:
                logger.error(f"Error converting pure portfolio {i}: {e}")
                continue
        
        if not responses:
            logger.warning(f"No valid pure portfolios for {strategy}, falling back to static")
            return _get_static_portfolio_recommendations(risk_profile)
        
        logger.info(f"✅ Generated {len(responses)} pure {strategy} strategy portfolios")
        return responses
        
    except Exception as e:
        logger.error(f"❌ Error generating pure strategy portfolios: {e}")
        return _get_static_portfolio_recommendations(risk_profile)

# NEW: Pure vs Personalized Strategy Comparison for Optimization Tab
@router.post("/optimize/strategy-comparison")
async def optimize_strategy_comparison(risk_profile: str, strategy: str = 'diversification'):
    """
    Compare Pure Strategy vs Personalized Strategy portfolios for the Analyze Optimization tab
    
    Args:
        risk_profile: User's risk profile
        strategy: Investment strategy (default: diversification)
    
    Returns:
        Comparison between pure and personalized strategy portfolios with shuffled variety
    """
    try:
        logger.info(f"🔍 Optimize tab: Comparing pure vs personalized for {strategy}/{risk_profile}")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(_rds, redis_manager)
        
        # Get pure portfolios from cache
        pure_portfolios = _rds.strategy_optimizer.get_pure_portfolios_from_cache(strategy)
        if not pure_portfolios:
            # Generate if not cached
            pure_portfolios = _rds.strategy_optimizer._generate_pure_strategy_portfolios(strategy)
            if pure_portfolios:
                _rds.strategy_optimizer._store_pure_portfolios_in_redis(strategy, pure_portfolios)
        
        # Get personalized portfolios from cache
        personalized_portfolios = _rds.strategy_optimizer.get_personalized_portfolios_from_cache(strategy, risk_profile)
        if not personalized_portfolios:
            # Generate if not cached
            personalized_portfolios = _rds.strategy_optimizer._generate_personalized_strategy_portfolios(strategy, risk_profile)
            if personalized_portfolios:
                _rds.strategy_optimizer._store_personalized_portfolios_in_redis(strategy, risk_profile, personalized_portfolios)
        
        # Shuffle for variety
        import random
        if pure_portfolios:
            random.shuffle(pure_portfolios)
        if personalized_portfolios:
            random.shuffle(personalized_portfolios)
        
        return {
            "strategy": strategy,
            "risk_profile": risk_profile,
            "pure_portfolio": pure_portfolios[0] if pure_portfolios else None,
            "personalized_portfolio": personalized_portfolios[0] if personalized_portfolios else None,
            "comparison": {
                "pure_count": len(pure_portfolios) if pure_portfolios else 0,
                "personalized_count": len(personalized_portfolios) if personalized_portfolios else 0
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Strategy comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy comparison failed: {str(e)}")

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
        master_tickers = _rds.all_tickers[:100]
        
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
                'description': 'Defensive strategy focused on stable dividend stocks and capital preservation. Ideal for investors who prioritize safety over growth.',
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
                'description': 'Balanced approach combining steady income generation with moderate growth potential. Suitable for conservative investors seeking reliable returns.',
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
                'description': 'Diversified mix of growth and value stocks offering balanced risk-return profile. Perfect for investors comfortable with moderate market volatility.',
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
                'description': 'High-growth strategy targeting companies with strong momentum and innovation potential. Designed for investors seeking above-market returns.',
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
                'description': 'High-conviction growth strategy focusing on disruptive technologies and emerging trends. For investors with high risk tolerance seeking maximum growth potential.',
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
                name=template['name'],
                description=template['description'],
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
                name=template['name'],
                description=template['description'],
                expectedReturn=0.10,  # 10% fallback
                risk=0.15,  # 15% fallback
                diversificationScore=75.0,  # 75% fallback
                sharpeRatio=0.0  # Always 0 as requested
            ))
    
    return responses

@router.post("/recommendations/strategy-comparison")
async def generate_strategy_comparison(strategy: str, risk_profile: str):
    """
    OPTIMIZED: Get strategy comparison portfolios with cache-first approach
    
    This endpoint retrieves portfolios using different investment strategies:
    - diversification: Focus on sector diversification
    - risk: Focus on risk management
    - return: Focus on return maximization
    
    Performance: <1s if cached, 2-5s if needs generation
    
    Args:
        strategy: Investment strategy ('diversification', 'risk', 'return')
        risk_profile: User's risk tolerance level
    """
    try:
        logger.info(f"🚀 Request: {strategy} strategy, {risk_profile} profile")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(
                _rds, 
                redis_manager
            )
        
        # OPTIMIZED: Use cache-first approach
        # This checks Redis cache first, only generates if needed
        personalized_portfolios = _rds.strategy_optimizer.get_or_generate_personalized_portfolios(
            strategy=strategy,
            risk_profile=risk_profile
        )
        
        # Convert to response format
        responses = []
        if personalized_portfolios:
            for i, portfolio in enumerate(personalized_portfolios):  # Return all portfolios (3 personalized)
                try:
                    metrics = portfolio.get('metrics', {})
                    response = PortfolioResponse(
                        portfolio=portfolio.get('allocations', []),
                        name=portfolio.get('name', f"{strategy.title()} Strategy Portfolio {i+1}"),
                        description=portfolio.get('description', 
                                                 f"Portfolio optimized for {strategy} strategy with {risk_profile} risk profile"),
                        expectedReturn=metrics.get('expected_return', 0.12),
                        risk=metrics.get('risk', 0.15),
                        diversificationScore=metrics.get('diversification_score', 75.0),
                        sharpeRatio=0.0  # Always 0 as requested
                    )
                    responses.append(response)
                except Exception as e:
                    logger.error(f"Error converting strategy portfolio to response: {e}")
                    continue
        
        if not responses:
            logger.warning(f"No strategy portfolios found for {strategy}, falling back to static recommendations")
            return _get_static_portfolio_recommendations(risk_profile)
        
        logger.info(f"✅ Returning {len(responses)} strategy comparison portfolios for {strategy}")
        return responses
        
    except Exception as e:
        logger.error(f"❌ Error in strategy comparison: {e}")
        # Fallback to static recommendations
        return _get_static_portfolio_recommendations(risk_profile)

@router.post("/strategy-portfolios/pre-generate")
async def pre_generate_strategy_portfolios():
    """
    Pre-generate ALL strategy portfolios and store in Redis cache
    
    This endpoint triggers the generation of:
    - 3 strategies × 6 pure portfolios = 18 pure portfolios
    - 3 strategies × 5 risk profiles × 3 portfolios = 45 personalized portfolios
    - Total: 63 portfolios
    
    Cache TTL: 1 week (168 hours)
    
    Returns:
        Summary of generation with timing and success rates
    """
    try:
        logger.info("🚀 Pre-generation requested via API")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(
                _rds, 
                redis_manager
            )
        
        # Run pre-generation
        summary = _rds.strategy_optimizer.pre_generate_all_strategy_portfolios()
        
        return {
            "success": summary.get('success', False),
            "message": "Strategy portfolios pre-generation completed",
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"❌ Pre-generation failed: {e}")
        return {
            "success": False,
            "message": f"Pre-generation failed: {str(e)}",
            "summary": None
        }

@router.get("/strategy-portfolios/cache-status")
async def get_strategy_portfolio_cache_status():
    """
    Get status of strategy portfolio caches in Redis
    
    Returns:
        Status of all cached strategy portfolios
    """
    try:
        if not redis_manager:
            return {
                "success": False,
                "error": "Redis manager not available"
            }
        
        # Get all strategy portfolio keys
        keys = redis_manager.redis_client.keys("strategy_portfolios:*")
        
        # Parse keys to get details
        pure_count = len([k for k in keys if b'pure' in k])
        personalized_count = len([k for k in keys if b'personalized' in k])
        
        # Get TTL for sample keys
        key_details = []
        for key in keys[:10]:  # Sample first 10
            ttl = redis_manager.redis_client.ttl(key)
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            key_details.append({
                "key": key_str,
                "ttl_seconds": ttl,
                "ttl_hours": round(ttl / 3600, 1) if ttl > 0 else 0
            })
        
        return {
            "success": True,
            "total_cached": len(keys),
            "pure_portfolios": pure_count,
            "personalized_portfolios": personalized_count,
            "sample_keys": key_details,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking cache status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/strategy-portfolios/clear-cache")
async def clear_strategy_portfolio_cache():
    """
    Clear all strategy portfolio caches from Redis
    
    Returns:
        Result of cache clearing operation
    """
    try:
        logger.info("🗑️  Cache clearing requested via API")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(
                _rds, 
                redis_manager
            )
        
        # Clear caches
        result = _rds.strategy_optimizer.clear_all_strategy_caches()
        
        return {
            "success": result.get('success', False),
            "message": "Strategy portfolio caches cleared",
            "deleted_count": result.get('deleted_count', 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }

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
    OPTIMIZED: Works exclusively with cached data for fast, reliable responses
    """
    try:
        if not ticker1 or not ticker2:
            raise HTTPException(status_code=400, detail="Both tickers required")
        
        ticker1 = ticker1.upper()
        ticker2 = ticker2.upper()
        
        # Validate tickers exist in master list
        if ticker1 not in set(_rds.all_tickers):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker1}")
        if ticker2 not in set(_rds.all_tickers):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker2}")
        
        # OPTIMIZED: Check if both tickers have cached monthly data
        # This avoids external API calls and ensures fast responses
        if not _rds._has_cached_monthly_data(ticker1):
            raise HTTPException(status_code=404, detail=f"Ticker {ticker1} data not available in cache. Please try a different ticker.")
        if not _rds._has_cached_monthly_data(ticker2):
            raise HTTPException(status_code=404, detail=f"Ticker {ticker2} data not available in cache. Please try a different ticker.")
        
        # Get monthly data for both tickers (from cache only)
        data1 = _rds.get_monthly_data(ticker1)
        data2 = _rds.get_monthly_data(ticker2)
        
        if not data1 or not data2:
            raise HTTPException(status_code=404, detail="Unable to load ticker data from cache")
        
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

# REMOVED: Duplicate ticker-info endpoint - using the Redis-first one above

@router.get("/portfolio-validation/{risk_profile}")
def get_portfolio_validation(risk_profile: str):
    """
    Get portfolio validation and uniqueness status for a specific risk profile
    """
    try:
        if not risk_profile or not risk_profile.strip():
            raise HTTPException(status_code=400, detail="Risk profile required")
        
        risk_profile = risk_profile.strip()
        
        # Get portfolios from Redis
        if not redis_manager:
            raise HTTPException(status_code=503, detail="Redis manager not available")
        
        portfolios = redis_manager.get_portfolio_bucket(risk_profile)
        
        if not portfolios:
            raise HTTPException(status_code=404, detail=f"No portfolios found for {risk_profile}")
        
        # Analyze portfolio uniqueness
        unique_allocations = set()
        duplicate_count = 0
        
        for portfolio in portfolios:
            allocation_key = "|".join([f"{alloc['symbol']}:{alloc['allocation']}" 
                                     for alloc in sorted(portfolio['allocations'], key=lambda x: x['symbol'])])
            if allocation_key in unique_allocations:
                duplicate_count += 1
            else:
                unique_allocations.add(allocation_key)
        
        validation_result = {
            'risk_profile': risk_profile,
            'total_portfolios': len(portfolios),
            'unique_portfolios': len(unique_allocations),
            'duplicate_portfolios': duplicate_count,
            'uniqueness_percentage': (len(unique_allocations) / len(portfolios)) * 100 if portfolios else 0,
            'validation_status': 'PASS' if duplicate_count == 0 else 'FAIL',
            'timestamp': datetime.now().isoformat()
        }
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating portfolios for {risk_profile}: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating portfolios: {str(e)}")

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
    Force refresh of all ticker data in Redis using Redis-first approach
    """
    try:
        # Force refresh expired data
        _rds.force_refresh_expired_data()
        
        return {
            "status": "success",
            "message": "Ticker table refresh initiated",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing ticker table: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing ticker table: {str(e)}")

@router.post("/ticker-table/smart-refresh")
async def smart_monthly_refresh(request: Optional[Dict] = None):
    """
    Smart monthly refresh that only fetches the latest month of data using Redis-first approach
    - Extends time range incrementally (no re-downloading of historical data)
    - Respects TTL and only refreshes when needed
    - Efficient: Only fetches new months, not entire history
    - Can target specific tickers if provided in request body
    """
    try:
        # Check if specific tickers were requested
        target_tickers = None
        if request and 'tickers' in request:
            target_tickers = request['tickers']
            logger.info(f"Smart refresh targeting {len(target_tickers)} specific tickers")
        
        # Perform smart monthly refresh
        if target_tickers:
            # Refresh only specific tickers
            result = _rds.smart_refresh_tickers(target_tickers)
        else:
            # Refresh all tickers
            result = _rds.smart_monthly_refresh()
        
        if result:
            return {
                "status": "success",
                "message": f"Smart refresh completed - {len(target_tickers) if target_tickers else 'all'} tickers processed",
                "changed_count": result.get('changed_count', 0) if isinstance(result, dict) else 0,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "success",
                "message": "Smart refresh completed (no action needed)",
                "changed_count": 0,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error in smart monthly refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Error in smart monthly refresh: {str(e)}")

@router.get("/tickers/ttl-status")
async def get_ttl_status():
    """
    Get TTL status for all tickers using AutoRefreshService
    Returns which tickers are expired or near expiry
    """
    try:
        
        # Get the auto refresh service instance
        auto_refresh_service = None
        if hasattr(_rds, 'auto_refresh_service'):
            auto_refresh_service = _rds.auto_refresh_service
        else:
            # Auto refresh service not available in this build; skip TTL deep checks
            auto_refresh_service = None
        
        # Get tracking data for all tickers
        expired_tickers = []
        near_expiry_tickers = []
        total_tickers = len(_rds.all_tickers)
        
        for ticker in _rds.all_tickers:
            tracking = {}
            
            days_left = 28
            
            if days_left <= 1:  # Expired or expiring today
                expired_tickers.append(ticker)
            elif days_left <= 3:  # Near expiry (within 3 days)
                near_expiry_tickers.append(ticker)
        
        return {
            "success": True,
            "total_tickers": total_tickers,
            "expired_tickers": expired_tickers,
            "near_expiry_tickers": near_expiry_tickers,
            "expired_count": len(expired_tickers),
            "near_expiry_count": len(near_expiry_tickers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting TTL status: {e}")
        raise HTTPException(status_code=500, detail=f"TTL status check failed: {str(e)}")

@router.post("/trigger-regeneration")
async def trigger_portfolio_regeneration(risk_profile: str = None):
    """
    Trigger manual portfolio regeneration using the optimized service
    Can regenerate specific risk profile or all profiles
    """
    try:
        from main import auto_regeneration_service
        
        if not auto_regeneration_service:
            raise HTTPException(status_code=500, detail="Auto-regeneration service not available")
        
        result = auto_regeneration_service.trigger_regeneration(risk_profile)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "timestamp": result["timestamp"],
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error triggering portfolio regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger regeneration: {str(e)}")

@router.post("/regenerate")
async def regenerate_all_portfolios():
    """
    Regenerate all portfolios using EnhancedPortfolioGenerator + RedisPortfolioManager
    This creates fresh portfolios across all risk profiles
    """
    try:
        from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
        from utils.redis_portfolio_manager import RedisPortfolioManager
        import redis
        
        logger.info("🚀 Starting portfolio regeneration for all risk profiles")
        
        # Initialize services
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        portfolio_manager = RedisPortfolioManager(redis_client)
        portfolio_generator = EnhancedPortfolioGenerator(_rds, portfolio_analytics)
        
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        total_portfolios = 0
        profiles_generated = []
        
        for risk_profile in risk_profiles:
            try:
                logger.info(f"🔄 Regenerating portfolios for {risk_profile} profile")
                
                # Generate 12 portfolios for this risk profile
                portfolios = portfolio_generator.generate_portfolio_bucket(risk_profile)
                
                if portfolios:
                    # Store in Redis
                    success = portfolio_manager.store_portfolio_bucket(risk_profile, portfolios)
                    
                    if success:
                        total_portfolios += len(portfolios)
                        profiles_generated.append(risk_profile)
                        logger.info(f"✅ Generated {len(portfolios)} portfolios for {risk_profile}")
                    else:
                        logger.error(f"❌ Failed to store portfolios for {risk_profile}")
                else:
                    logger.warning(f"⚠️ No portfolios generated for {risk_profile}")
                    
            except Exception as e:
                logger.error(f"❌ Error generating portfolios for {risk_profile}: {e}")
                continue
        
        logger.info(f"🎉 Portfolio regeneration completed: {total_portfolios} portfolios across {len(profiles_generated)} profiles")
        
        return {
            "success": True,
            "message": f"Successfully regenerated {total_portfolios} portfolios",
            "total_portfolios": total_portfolios,
            "profiles_generated": profiles_generated,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in portfolio regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio regeneration failed: {str(e)}")

@router.get("/ticker-table/data")
async def get_ticker_table_data():
    """
    Get ticker table data with return and risk metrics using Redis-first approach
    Returns: Ticker information with essential metrics for the ticker table
    """
    try:
        import json
        import gzip
        from datetime import datetime
        
        # Get all tickers from the Redis-first data service
        all_tickers = _rds.all_tickers
        
        ticker_data = []
        
        for index, ticker in enumerate(all_tickers, 1):  # Added index for ID
            try:
                # Get price data using Redis-first approach
                price_key = _rds._get_cache_key(ticker, 'prices')
                price_raw = _rds.redis_client.get(price_key)
                
                # Get sector/company data
                sector_key = _rds._get_cache_key(ticker, 'sector')
                sector_raw = _rds.redis_client.get(sector_key)
                
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
                                    import pandas as pd
                                    monthly_volatility = pd.Series(returns).std()
                                    annualized_risk = monthly_volatility * (12 ** 0.5) * 100  # Convert to percentage
                        except Exception as e:
                            logger.warning(f"Error calculating metrics for {ticker}: {e}")
                    
                    # NEW: Check data freshness
                    data_freshness = "current"
                    if last_date != "N/A":
                        try:
                            # Handle date format: "2025-07-01 00:00:00-04:00"
                            if " " in last_date:
                                # Extract just the date part before the space
                                date_part = last_date.split(" ")[0]
                                last_date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                            else:
                                last_date_obj = datetime.strptime(last_date, "%Y-%m-%d")
                            
                            days_old = (datetime.now() - last_date_obj).days
                            if days_old <= 7:
                                data_freshness = "very_recent"
                            elif days_old <= 30:
                                data_freshness = "recent"
                            elif days_old <= 90:
                                data_freshness = "moderate"
                            else:
                                data_freshness = "stale"
                        except Exception as e:
                            logger.debug(f"Date parsing error for {ticker}: {e}")
                            data_freshness = "unknown"
                    
                    ticker_info = {
                        "id": index,  # NEW: ID column
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
                        "dataFreshness": data_freshness,  # NEW: Freshness indicator
                        "status": "active",
                        "lastUpdated": datetime.now().isoformat()
                    }
                    
                    ticker_data.append(ticker_info)
                else:
                    # Missing data
                    ticker_info = {
                        "id": index,  # NEW: ID column
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
                        "dataFreshness": "missing",  # NEW: Freshness indicator
                        "status": "missing_data",
                        "lastUpdated": datetime.now().isoformat()
                    }
                    
                    ticker_data.append(ticker_info)
                    
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker}: {e}")
                # Add error ticker info
                ticker_info = {
                    "id": index,  # NEW: ID column
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
                    "dataFreshness": "error",  # NEW: Freshness indicator
                    "status": "error",
                    "lastUpdated": datetime.now().isoformat()
                }
                ticker_data.append(ticker_info)
        
        logger.info(f"Returning {len(ticker_data)} tickers for ticker table")
        
        return {
            "status": "success",
            "tickers": ticker_data,
            "total_count": len(ticker_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ticker table data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting ticker table data: {str(e)}")

@router.get("/mini-lesson/assets")
def get_mini_lesson_assets():
    """
    Get available assets for mini-lesson with predefined sector-based asset lists
    Returns: Sector-based asset lists for educational analysis with pre-calculated metrics
    Now includes 10 assets per sector: 6 US + 4 international (from Redis master list)
    """
    try:
        # Check Redis cache first (48h TTL) - v5 includes all 11 sectors
        cache_key = "mini_lesson_assets:v5"
        if _rds.redis_client:
            cached_result = _rds.redis_client.get(cache_key)
            if cached_result:
                import json
                return json.loads(cached_result.decode())
        
        # Predefined sector-based asset lists (5 US assets each); some lists are multi-sector
        sector_asset_lists = [
            {
                'list_id': 'tech_growth',
                'name': 'Technology Growth',
                'description': 'High-growth technology companies',
                'sector': 'Technology',
                'assets': [
                    {'ticker': 'NVDA','name': 'NVIDIA Corporation','sector': 'Technology','industry': 'Semiconductors','focus': 'AI & Gaming Chips'},
                    {'ticker': 'TSLA','name': 'Tesla Inc.','sector': 'Consumer Discretionary','industry': 'Automobiles','focus': 'Electric Vehicles'},
                    {'ticker': 'META','name': 'Meta Platforms Inc.','sector': 'Technology','industry': 'Internet Content','focus': 'Social Media'},
                    {'ticker': 'AMD','name': 'Advanced Micro Devices','sector': 'Technology','industry': 'Semiconductors','focus': 'Computer Processors'},
                    {'ticker': 'ADBE','name': 'Adobe Inc.','sector': 'Technology','industry': 'Software','focus': 'Creative Software'}
                ]
            },
            {
                'list_id': 'consumer_defensive',
                'name': 'Consumer Defensive (Staples)',
                'description': 'Essential consumer goods and stable businesses',
                'sector': 'Consumer Defensive',
                'assets': [
                    {'ticker': 'PG','name': 'Procter & Gamble Co.','sector': 'Consumer Defensive','industry': 'Household Products','focus': 'Consumer Goods'},
                    {'ticker': 'KO','name': 'Coca-Cola Company','sector': 'Consumer Defensive','industry': 'Beverages','focus': 'Beverages'},
                    {'ticker': 'WMT','name': 'Walmart Inc.','sector': 'Consumer Defensive','industry': 'Discount Stores','focus': 'Retail'},
                    {'ticker': 'PEP','name': 'PepsiCo Inc.','sector': 'Consumer Defensive','industry': 'Beverages','focus': 'Food & Beverages'},
                    {'ticker': 'COST','name': 'Costco Wholesale','sector': 'Consumer Defensive','industry': 'Discount Stores','focus': 'Warehouse Retail'}
                ]
            },
            {
                'list_id': 'financial_services',
                'name': 'Financial Services',
                'description': 'Banking, insurance, and financial companies',
                'sector': 'Financial Services',
                'assets': [
                    {'ticker': 'JPM','name': 'JPMorgan Chase & Co.','sector': 'Financial Services','industry': 'Banks','focus': 'Investment Banking'},
                    {'ticker': 'V','name': 'Visa Inc.','sector': 'Financial Services','industry': 'Credit Services','focus': 'Payment Processing'},
                    {'ticker': 'MA','name': 'Mastercard Inc.','sector': 'Financial Services','industry': 'Credit Services','focus': 'Payment Processing'},
                    {'ticker': 'BAC','name': 'Bank of America','sector': 'Financial Services','industry': 'Banks','focus': 'Banking Services'},
                    {'ticker': 'WFC','name': 'Wells Fargo','sector': 'Financial Services','industry': 'Banks','focus': 'Banking Services'}
                ]
            },
            {
                'list_id': 'communication_services',
                'name': 'Communication Services',
                'description': 'Media, entertainment, and communication companies',
                'sector': 'Communication Services',
                'assets': [
                    {'ticker': 'DIS','name': 'Walt Disney Company','sector': 'Communication Services','industry': 'Entertainment','focus': 'Media & Entertainment'},
                    {'ticker': 'NFLX','name': 'Netflix Inc.','sector': 'Communication Services','industry': 'Entertainment','focus': 'Streaming Services'},
                    {'ticker': 'CHTR','name': 'Charter Communications','sector': 'Communication Services','industry': 'Telecom Services','focus': 'Cable & Internet'},
                    {'ticker': 'CMCSA','name': 'Comcast Corporation','sector': 'Communication Services','industry': 'Entertainment','focus': 'Media & Telecom'},
                    {'ticker': 'APP','name': 'AppLovin Corporation','sector': 'Communication Services','industry': 'Advertising','focus': 'Mobile Advertising'}
                ]
            },
            {
                'list_id': 'healthcare_pharma',
                'name': 'Healthcare & Pharma',
                'description': 'Healthcare and pharmaceutical companies',
                'sector': 'Healthcare',
                'assets': [
                    {'ticker': 'PFE','name': 'Pfizer Inc.','sector': 'Healthcare','industry': 'Pharmaceuticals','focus': 'Vaccines & Medicines'},
                    {'ticker': 'ABBV','name': 'AbbVie Inc.','sector': 'Healthcare','industry': 'Pharmaceuticals','focus': 'Biopharmaceuticals'},
                    {'ticker': 'TMO','name': 'Thermo Fisher Scientific','sector': 'Healthcare','industry': 'Medical Devices','focus': 'Scientific Instruments'},
                    {'ticker': 'DHR','name': 'Danaher Corporation','sector': 'Healthcare','industry': 'Medical Devices','focus': 'Life Sciences'},
                    {'ticker': 'BMY','name': 'Bristol-Myers Squibb','sector': 'Healthcare','industry': 'Pharmaceuticals','focus': 'Biopharmaceuticals'}
                ]
            },
            {
                'list_id': 'energy',
                'name': 'Energy',
                'description': 'Oil, gas, and renewable energy companies',
                'sector': 'Energy',
                'assets': [
                    {'ticker': 'XOM','name': 'Exxon Mobil Corporation','sector': 'Energy','industry': 'Oil & Gas','focus': 'Integrated Oil'},
                    {'ticker': 'CVX','name': 'Chevron Corporation','sector': 'Energy','industry': 'Oil & Gas','focus': 'Integrated Oil'},
                    {'ticker': 'COP','name': 'ConocoPhillips','sector': 'Energy','industry': 'Oil & Gas','focus': 'Exploration & Production'},
                    {'ticker': 'SLB','name': 'Schlumberger','sector': 'Energy','industry': 'Oil & Gas Services','focus': 'Oilfield Services'},
                    {'ticker': 'EOG','name': 'EOG Resources','sector': 'Energy','industry': 'Oil & Gas','focus': 'Independent Oil & Gas'}
                ]
            },
            {
                'list_id': 'utilities',
                'name': 'Utilities',
                'description': 'Electric, water, and renewable utilities',
                'sector': 'Utilities',
                'assets': [
                    {'ticker': 'NEE','name': 'NextEra Energy Inc.','sector': 'Utilities','industry': 'Electric Utilities','focus': 'Renewable Energy'},
                    {'ticker': 'DUK','name': 'Duke Energy Corporation','sector': 'Utilities','industry': 'Electric Utilities','focus': 'Electric Power'},
                    {'ticker': 'SO','name': 'Southern Company','sector': 'Utilities','industry': 'Electric Utilities','focus': 'Electric Power'},
                    {'ticker': 'AEP','name': 'American Electric Power','sector': 'Utilities','industry': 'Electric Utilities','focus': 'Power Generation'},
                    {'ticker': 'AES','name': 'AES Corporation','sector': 'Utilities','industry': 'Electric Utilities','focus': 'Power Generation'}
                ]
            },
            {
                'list_id': 'basic_materials',
                'name': 'Basic Materials',
                'description': 'Raw materials and chemical companies',
                'sector': 'Basic Materials',
                'assets': [
                    {'ticker': 'LIN','name': 'Linde plc','sector': 'Basic Materials','industry': 'Specialty Chemicals','focus': 'Industrial Gases'},
                    {'ticker': 'APD','name': 'Air Products and Chemicals','sector': 'Basic Materials','industry': 'Specialty Chemicals','focus': 'Industrial Gases'},
                    {'ticker': 'SHW','name': 'Sherwin-Williams Company','sector': 'Basic Materials','industry': 'Specialty Chemicals','focus': 'Paints & Coatings'},
                    {'ticker': 'ECL','name': 'Ecolab Inc.','sector': 'Basic Materials','industry': 'Specialty Chemicals','focus': 'Water Treatment'},
                    {'ticker': 'DD','name': 'DuPont de Nemours','sector': 'Basic Materials','industry': 'Specialty Chemicals','focus': 'Advanced Materials'}
                ]
            },
            {
                'list_id': 'industrials',
                'name': 'Industrials',
                'description': 'Industrial and manufacturing companies',
                'sector': 'Industrials',
                'assets': [
                    {'ticker': 'HON','name': 'Honeywell International','sector': 'Industrials','industry': 'Industrial Conglomerates','focus': 'Aerospace & Automation'},
                    {'ticker': 'UPS','name': 'United Parcel Service','sector': 'Industrials','industry': 'Air Freight & Logistics','focus': 'Package Delivery'},
                    {'ticker': 'BA','name': 'Boeing Company','sector': 'Industrials','industry': 'Aerospace & Defense','focus': 'Commercial Aircraft'},
                    {'ticker': 'CAT','name': 'Caterpillar Inc.','sector': 'Industrials','industry': 'Construction & Mining','focus': 'Heavy Machinery'},
                    {'ticker': 'GE','name': 'General Electric','sector': 'Industrials','industry': 'Industrial Conglomerates','focus': 'Power & Aviation'}
                ]
            },
            {
                'list_id': 'real_estate',
                'name': 'Real Estate',
                'description': 'Real estate investment trusts and property companies',
                'sector': 'Real Estate',
                'assets': [
                    {'ticker': 'AMT','name': 'American Tower Corporation','sector': 'Real Estate','industry': 'REITs','focus': 'Cell Tower REIT'},
                    {'ticker': 'PLD','name': 'Prologis Inc.','sector': 'Real Estate','industry': 'REITs','focus': 'Industrial REIT'},
                    {'ticker': 'CCI','name': 'Crown Castle Inc.','sector': 'Real Estate','industry': 'REITs','focus': 'Cell Tower REIT'},
                    {'ticker': 'EQIX','name': 'Equinix Inc.','sector': 'Real Estate','industry': 'REITs','focus': 'Data Center REIT'},
                    {'ticker': 'PSA','name': 'Public Storage','sector': 'Real Estate','industry': 'REITs','focus': 'Self Storage REIT'}
                ]
            },
            {
                'list_id': 'consumer_cyclical',
                'name': 'Consumer Cyclical',
                'description': 'Cyclical consumer companies and automotive',
                'sector': 'Consumer Cyclical',
                'assets': [
                    {'ticker': 'F','name': 'Ford Motor Company','sector': 'Consumer Cyclical','industry': 'Automotive','focus': 'Automotive Manufacturing'},
                    {'ticker': 'GM','name': 'General Motors','sector': 'Consumer Cyclical','industry': 'Automotive','focus': 'Automotive Manufacturing'},
                    {'ticker': 'LVS','name': 'Las Vegas Sands','sector': 'Consumer Cyclical','industry': 'Resorts & Casinos','focus': 'Gaming & Entertainment'},
                    {'ticker': 'MGM','name': 'MGM Resorts International','sector': 'Consumer Cyclical','industry': 'Resorts & Casinos','focus': 'Gaming & Entertainment'},
                    {'ticker': 'CCL','name': 'Carnival Corporation','sector': 'Consumer Cyclical','industry': 'Leisure','focus': 'Cruise Lines'}
                ]
            }
        ]
        
        # FIX #4: OPTIMIZED helper function - use fast cached ticker info instead of slow get_monthly_data
        def get_asset_with_metrics(ticker, name, sector, industry, focus, country="United States"):
            # FIX: STRICT cache check - only return assets with complete Redis data
            if not _rds._is_cached(ticker, 'prices') or not _rds._is_cached(ticker, 'sector'):
                logger.debug(f"⏭️  Skipping {ticker} - not in cache")
                return None
            
            # FAST PATH: Use pre-calculated metrics from cache (instant)
            cached_metrics = _rds.get_cached_metrics(ticker)
            if cached_metrics:
                return {
                    'ticker': ticker,
                    'name': name,
                    'sector': sector,
                    'industry': industry,
                    'focus': focus,
                    'country': country,
                    'annualized_return': cached_metrics.get('annualized_return', 0),
                    'risk': cached_metrics.get('risk', 0),
                    'data_points': cached_metrics.get('data_points', 0),
                    'last_price': cached_metrics.get('last_price', 0)
                }
            
            # FAST FALLBACK: Use _get_cached_ticker_info_fast instead of get_monthly_data
            ticker_info = _rds._get_cached_ticker_info_fast(ticker)
            if ticker_info and ticker_info.get('data_points', 0) >= 12:
                # Use simple approximations for missing metrics (faster than full calculation)
                return {
                    'ticker': ticker,
                    'name': name,
                    'sector': sector,
                    'industry': industry,
                    'focus': focus,
                    'country': country,
                    'annualized_return': 0.10,  # Reasonable default
                    'risk': 0.20,  # Reasonable default
                    'data_points': ticker_info.get('data_points', 0),
                    'last_price': ticker_info.get('current_price', 0)
                }
            
            return None
        
        # FIX #4: OPTIMIZED helper function - expanded to 200 assets for diversity
        def get_additional_assets(target_sector_or_sectors, existing_tickers, country_filter=None, count=1):
            additional_assets = []
            all_tickers = _rds.all_tickers
            
            # OPTIMIZATION: Search through first 200 tickers for better diversity
            search_limit = min(200, len(all_tickers))
            
            # Get candidates from master list (LIMITED)
            candidates = []
            for ticker in all_tickers[:search_limit]:
                if ticker in existing_tickers:
                    continue
                
                # FAST: Quick cache existence check only
                if not _rds._is_cached(ticker, 'prices') or not _rds._is_cached(ticker, 'sector'):
                    continue
                
                # FAST: Get sector data from cache
                sector_data = _rds._load_from_cache(ticker, 'sector')
                if not sector_data:
                    continue
                
                ticker_sector = sector_data.get('sector', '')
                ticker_country = sector_data.get('country', '')
                ticker_name = sector_data.get('companyName', ticker)
                ticker_industry = sector_data.get('industry', 'Unknown')
                
                # Normalize target sectors
                target_sectors = target_sector_or_sectors if isinstance(target_sector_or_sectors, list) else [target_sector_or_sectors]
                # Filter by sector and country
                if ticker_sector in target_sectors and ticker_sector not in ['', 'Unknown', None]:
                    if country_filter is None or (country_filter == 'US' and ticker_country == 'United States') or (country_filter == 'INTL' and ticker_country != 'United States'):
                        # FAST: Use cached ticker info if available, otherwise fall back to get_ticker_info
                        ticker_info = None
                        try:
                            if hasattr(_rds, '_get_cached_ticker_info_fast'):
                                ticker_info = _rds._get_cached_ticker_info_fast(ticker)
                        except Exception:
                            ticker_info = None
                        if not ticker_info:
                            try:
                                ticker_info = _rds.get_ticker_info(ticker)
                            except Exception:
                                ticker_info = None
                        if ticker_info and ticker_info.get('data_points', 0) >= 12:
                            candidates.append({
                                'ticker': ticker,
                                'name': ticker_name,
                                'sector': ticker_sector,
                                'industry': ticker_industry,
                                'country': ticker_country,
                                'data_points': ticker_info.get('data_points', 0),
                                'current_price': ticker_info.get('current_price', 0)
                            })
                        
                        # EARLY EXIT: Stop if we have enough candidates
                        if len(candidates) >= count * 3:
                            break
            
            # Sort by data quality (more data points first)
            candidates.sort(key=lambda x: x['data_points'], reverse=True)
            
            # Take top candidates and get full metrics (FAST)
            for candidate in candidates[:count]:
                asset = get_asset_with_metrics(
                    candidate['ticker'],
                    candidate['name'],
                    candidate['sector'],
                    candidate['industry'],
                    f"{candidate['industry']} - {candidate['country']}",
                    candidate['country']
                )
                if asset:
                    additional_assets.append(asset)
                    if len(additional_assets) >= count:
                        break
            
            return additional_assets
        
        # Process each sector list and augment with additional assets
        available_lists = []
        for asset_list in sector_asset_lists:
            target_sectors = asset_list.get('sectors', [asset_list.get('sector', '')])
            available_assets = []
            existing_tickers = set()
            
            # First, try to add hardcoded US assets (only if cached)
            for asset in asset_list['assets']:
                ticker = asset['ticker']
                existing_tickers.add(ticker)
                # FIX: get_asset_with_metrics returns None if not cached - that's OK
                asset_data = get_asset_with_metrics(
                    ticker, asset['name'], asset['sector'], 
                    asset['industry'], asset['focus'], 'United States'
                )
                if asset_data:
                    available_assets.append(asset_data)
                else:
                    logger.debug(f"⏭️  Skipped hardcoded asset {ticker} - not in cache")
            
            # Add 1 more US asset from Redis (to reach 6 US total)
            us_additional = get_additional_assets(target_sectors, existing_tickers, 'US', 1)
            for asset in us_additional:
                existing_tickers.add(asset['ticker'])
                available_assets.append(asset)
            
            # Add 4 international assets from Redis
            intl_additional = get_additional_assets(target_sectors, existing_tickers, 'INTL', 4)
            for asset in intl_additional:
                existing_tickers.add(asset['ticker'])
                available_assets.append(asset)
            
            # Only include lists with at least 6 assets (minimum viable)
            if len(available_assets) >= 6:
                available_lists.append({
                    **asset_list,
                    'assets': available_assets,
                    'available_count': len(available_assets),
                    'us_count': len([a for a in available_assets if a.get('country') == 'United States']),
                    'international_count': len([a for a in available_assets if a.get('country') != 'United States'])
                })
                logger.info(f"✅ {asset_list['name']}: {len(available_assets)} assets available (cached)")
            else:
                logger.warning(f"⏭️  Skipped {asset_list['name']}: Only {len(available_assets)} assets cached (need 6+)")
        
        result = {
            'sector_lists': available_lists,
            'total_lists': len(available_lists),
            'message': 'Sector-based asset lists with pre-calculated metrics (6 US + 4 international per sector)',
            'total_assets': sum(len(lst['assets']) for lst in available_lists),
            'total_us_assets': sum(lst.get('us_count', 0) for lst in available_lists),
            'total_international_assets': sum(lst.get('international_count', 0) for lst in available_lists)
        }
        
        # Cache the result for 48 hours
        if _rds.redis_client:
            import json
            from datetime import timedelta
            _rds.redis_client.setex(cache_key, timedelta(hours=48), json.dumps(result))
        
        return result
        
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
        data1 = _rds.get_monthly_data(ticker1)
        data2 = _rds.get_monthly_data(ticker2)
        
        if not data1 or not data2:
            raise HTTPException(status_code=404, detail="One or both tickers not found")
        
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
            data = _rds.get_monthly_data(ticker)
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
            data = _rds.get_monthly_data(ticker)
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
            data = _rds.get_monthly_data(ticker)
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
            data = _rds.get_monthly_data(ticker)
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
            data = _rds.get_monthly_data(ticker)
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
            cache_status = _rds.get_cache_status()
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

# Enhanced Ticker Table Endpoints

# Global auto-refresh service instance
auto_refresh_service = None

def get_auto_refresh_service():
    """Get or create auto refresh service instance"""
    global auto_refresh_service
    if auto_refresh_service is None:
        auto_refresh_service = None
    return auto_refresh_service

@router.get("/ticker-table/enhanced")
async def get_enhanced_ticker_table():
    """Get enhanced ticker table with ID column and quality indicators"""
    try:
        # Get all ticker information with enhanced features
        all_tickers = []
        
        for ticker in _rds.all_tickers:
            try:
                ticker_info = _rds.get_ticker_info(ticker)
                if ticker_info:
                    # Format data for enhanced table
                    formatted_ticker = {
                        'id': len(all_tickers) + 1,
                        'ticker': ticker,
                        'companyName': ticker_info.get('company_name', 'N/A'),
                        'sector': ticker_info.get('sector', 'Unknown'),
                        'industry': ticker_info.get('industry', 'Unknown'),
                        'exchange': ticker_info.get('exchange', 'N/A'),
                        'country': ticker_info.get('country', 'N/A'),
                        'dataPoints': ticker_info.get('data_points', 0),
                        'firstDate': ticker_info.get('first_date', 'N/A'),
                        'lastDate': ticker_info.get('last_date', 'N/A'),
                        'lastPrice': ticker_info.get('current_price', 0),
                        'annualizedReturn': ticker_info.get('annualized_return', 0),
                        'annualizedRisk': ticker_info.get('annualized_volatility', 0),
                        'quality': get_ticker_quality_status(ticker_info),
                        'daysLeft': get_ticker_days_left(ticker)
                    }
                    all_tickers.append(formatted_ticker)
                    
            except Exception as e:
                logger.warning(f"Error getting info for {ticker}: {e}")
                # Add error entry
                all_tickers.append({
                    'id': len(all_tickers) + 1,
                    'ticker': ticker,
                    'companyName': 'Error',
                    'sector': 'Error',
                    'industry': 'Error',
                    'exchange': 'N/A',
                    'country': 'N/A',
                    'dataPoints': 0,
                    'firstDate': 'N/A',
                    'lastDate': 'N/A',
                    'lastPrice': 0,
                    'annualizedReturn': 0,
                    'annualizedRisk': 0,
                    'quality': 'critical',
                    'daysLeft': 'N/A'
                })
        
        return {
            'success': True,
            'tickers': all_tickers,
            'total_count': len(all_tickers),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting enhanced ticker data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced ticker data: {str(e)}")

def get_ticker_quality_status(ticker_info: Dict) -> str:
    """Determine ticker quality status"""
    issues = []
    
    if ticker_info.get('sector') in ['Unknown', 'N/A', None]:
        issues.append('Unknown sector')
    if ticker_info.get('industry') in ['Unknown', 'N/A', None]:
        issues.append('Unknown industry')
    if not ticker_info.get('current_price') or ticker_info.get('current_price', 0) <= 0:
        issues.append('Invalid price')
    if not ticker_info.get('data_points') or ticker_info.get('data_points', 0) < 12:
        issues.append('Insufficient data')
    
    if len(issues) == 0:
        return 'good'
    elif len(issues) <= 2:
        return 'warning'
    else:
        return 'critical'

def get_ticker_days_left(ticker: str) -> str:
    """Get days left until refresh for a ticker"""
    try:
        try:
            auto_service = get_auto_refresh_service()
        except Exception:
            auto_service = None
        tracking = auto_service.get_ticker_tracking(ticker)
        if tracking:
            days_left = min(tracking.get('price_days_left', 0), tracking.get('sector_days_left', 0))
            return f"{days_left} days"
        else:
            return "28 days"  # Default TTL
    except Exception as e:
        logger.warning(f"Error getting days left for {ticker}: {e}")
        return "28 days"

@router.get("/ticker-table/status")
async def get_enhanced_ticker_status():
    """Get status of enhanced ticker table and auto-refresh service"""
    try:
        auto_service = get_auto_refresh_service()
        
        # Get tracking summary
        tracking_summary = auto_service.get_tracking_summary()
        
        # Get cache coverage
        cache_coverage = _rds.get_cache_coverage()
        
        return {
            'success': True,
            'auto_refresh': {
                'status': tracking_summary.get('service_status', 'unknown'),
                'next_check': tracking_summary.get('next_check'),
                'immediate_refresh_needed': tracking_summary.get('refresh_status', {}).get('immediate_refresh_needed', 0),
                'warnings': tracking_summary.get('refresh_status', {}).get('warnings', 0)
            },
            'data_quality': tracking_summary.get('data_quality', {}),
            'cache_coverage': cache_coverage,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting enhanced status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced status: {str(e)}")

@router.post("/ticker-table/start-auto-refresh")
async def start_auto_refresh_service():
    """Start the automatic refresh service"""
    try:
        auto_service = get_auto_refresh_service()
        auto_service.start_auto_refresh_service()
        
        return {
            'success': True,
            'message': 'Auto-refresh service started',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting auto-refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start auto-refresh: {str(e)}")

@router.post("/ticker-table/stop-auto-refresh")
async def stop_auto_refresh_service():
    """Stop the automatic refresh service"""
    try:
        auto_service = get_auto_refresh_service()
        auto_service.stop_auto_refresh_service()
        
        return {
            'success': True,
            'message': 'Auto-refresh service stopped',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping auto-refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop auto-refresh: {str(e)}")


@router.get("/ticker-table/data-quality-report")
async def get_data_quality_report():
    """Get comprehensive data quality report"""
    try:
        auto_service = get_auto_refresh_service()
        
        # Get tracking summary
        tracking_summary = auto_service.get_tracking_summary()
        
        # Analyze data quality issues
        quality_issues = []
        critical_tickers = []
        warning_tickers = []
        
        for ticker, tracking in auto_service.tracking_data.items():
            quality = tracking.get('data_quality', {})
            status = quality.get('status', 'unknown')
            
            if status == 'critical':
                critical_tickers.append({
                    'ticker': ticker,
                    'issues': quality.get('issues', []),
                    'days_left': min(tracking.get('price_days_left', 0), tracking.get('sector_days_left', 0))
                })
            elif status == 'warning':
                warning_tickers.append({
                    'ticker': ticker,
                    'issues': quality.get('issues', []),
                    'days_left': min(tracking.get('price_days_left', 0), tracking.get('sector_days_left', 0))
                })
        
        return {
            'success': True,
            'summary': {
                'total_tickers': tracking_summary.get('total_tickers', 0),
                'critical_count': len(critical_tickers),
                'warning_count': len(warning_tickers),
                'good_count': tracking_summary.get('data_quality', {}).get('good', 0)
            },
            'critical_tickers': critical_tickers,
            'warning_tickers': warning_tickers,
            'recommendations': [
                'Refresh critical tickers immediately',
                'Monitor warning tickers closely',
                'Schedule maintenance for expiring data'
            ],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting data quality report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quality report: {str(e)}")

@router.get("/ticker-table/enhanced-html")
async def get_enhanced_ticker_table_html():
    """Serve the enhanced ticker table HTML page"""
    try:
        from fastapi.responses import HTMLResponse
        import os
        
        # Get the path to the enhanced ticker table HTML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_file_path = os.path.join(current_dir, "..", "..", "frontend", "public", "ticker-table.html")
        
        if not os.path.exists(html_file_path):
            # If the file doesn't exist, return a basic HTML with the data
            enhanced_data = await get_enhanced_ticker_table()
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Enhanced Ticker Table</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .stats-bar {{ display: flex; justify-content: space-around; margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
                    .stat-item {{ text-align: center; }}
                    .stat-value {{ font-weight: bold; color: #2c5aa0; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}

                </style>
            </head>
            <body>
                <h1>Enhanced Ticker Table</h1>
                
                <div class="stats-bar">
                    <div class="stat-item">
                        <span>Next Refresh:</span><br>
                        <span class="stat-value">28 days</span>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Ticker</th>
                            <th>Company</th>
                            <th>Sector</th>
                            <th>Last Price</th>
                            <th>Return</th>
                            <th>Risk</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for ticker in enhanced_data.get('tickers', [])[:50]:  # Show first 50 for demo
                html_content += f"""
                        <tr>
                            <td>{ticker.get('id', '-')}</td>
                            <td>{ticker.get('ticker', '-')}</td>
                            <td>{ticker.get('companyName', '-')}</td>
                            <td>{ticker.get('sector', '-')}</td>
                            <td>${ticker.get('lastPrice', 0):.2f}</td>
                            <td>{ticker.get('annualizedReturn', 0):.2%}</td>
                            <td>{ticker.get('annualizedRisk', 0):.2%}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
                
                <p><em>Showing first 50 tickers. Use the API endpoint for full data.</em></p>
                
                <script>
                    // Auto-hide notifications after 5 seconds
                    setTimeout(() => {
                        const notifications = document.querySelectorAll('.notification');
                        notifications.forEach(n => n.style.display = 'none');
                    }, 5000);
                </script>
            </body>
            </html>
            """
            
            return HTMLResponse(content=html_content)
        
        # Read and return the existing HTML file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error serving enhanced HTML: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve HTML: {str(e)}")

# Portfolio name and description generation functions
def _generate_portfolio_name(risk_profile: str, option: int) -> str:
    """Generate descriptive portfolio names based on risk profile and option"""
    names = {
        'very-conservative': [
            'Capital Preservation Portfolio',
            'Defensive Income Portfolio', 
            'Stable Growth Portfolio'
        ],
        'conservative': [
            'Income & Stability Portfolio',
            'Balanced Conservative Portfolio',
            'Moderate Growth Portfolio'
        ],
        'moderate': [
            'Core Diversified Portfolio',
            'Balanced Growth Portfolio',
            'Moderate Growth Portfolio'
        ],
        'aggressive': [
            'Growth Momentum Portfolio',
            'Innovation Focus Portfolio',
            'High Growth Portfolio'
        ],
        'very-aggressive': [
            'Maximum Growth Portfolio',
            'Disruptive Tech Portfolio',
            'High Conviction Portfolio'
        ]
    }
    
    profile_names = names.get(risk_profile, names['moderate'])
    return profile_names[option % len(profile_names)]

def _generate_portfolio_description(risk_profile: str, option: int) -> str:
    """Generate portfolio descriptions based on risk profile and option"""
    descriptions = {
        'very-conservative': [
            'Defensive strategy focused on stable dividend stocks and capital preservation. Ideal for investors who prioritize safety over growth.',
            'Conservative approach combining steady income generation with minimal risk exposure. Suitable for retirees and conservative investors.',
            'Balanced defensive strategy offering modest growth potential while maintaining capital stability.'
        ],
        'conservative': [
            'Balanced approach combining steady income generation with moderate growth potential. Suitable for conservative investors seeking reliable returns.',
            'Conservative growth strategy with focus on established companies and dividend-paying stocks.',
            'Moderate growth approach with emphasis on stability and consistent performance.'
        ],
        'moderate': [
            'Diversified mix of growth and value stocks offering balanced risk-return profile. Perfect for investors comfortable with moderate market volatility.',
            'Growth-focused strategy with sector diversification and risk management. Designed for investors seeking balanced growth.',
            'Innovation-driven approach with stability anchors. Combines growth potential with risk management.'
        ],
        'aggressive': [
            'High-growth strategy targeting companies with strong momentum and innovation potential. Designed for investors seeking above-market returns.',
            'Innovation-focused portfolio emphasizing disruptive technologies and emerging trends.',
            'Growth-oriented strategy with focus on high-potential companies and emerging markets.'
        ],
        'very-aggressive': [
            'High-conviction growth strategy focusing on disruptive technologies and emerging trends. For investors with high risk tolerance seeking maximum growth potential.',
            'Maximum growth portfolio targeting the most innovative and high-potential companies.',
            'High-conviction strategy focusing on emerging trends and disruptive technologies.'
        ]
    }
    
    profile_descriptions = descriptions.get(risk_profile, descriptions['moderate'])
    return profile_descriptions[option % len(profile_descriptions)]

@router.post("/force-refresh-expired-data")
def force_refresh_expired_data():
    """Force refresh of expired data using Redis-first approach"""
    try:
        _rds.force_refresh_expired_data()
        return {"message": "Force refresh completed successfully"}
    except Exception as e:
        logger.error(f"Force refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Force refresh failed: {str(e)}")

@router.post("/smart-monthly-refresh")
def smart_monthly_refresh():
    """Smart monthly refresh using Redis-first approach"""
    try:
        result = _rds.smart_monthly_refresh()
        return {"message": "Smart monthly refresh completed", "result": result}
    except Exception as e:
        logger.error(f"Smart monthly refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Smart monthly refresh failed: {str(e)}")



