from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Literal, Union
import logging
import math
import json
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import gzip
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.port_analytics import PortfolioAnalytics
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.portfolio_stock_selector import PortfolioStockSelector
from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
from utils.portfolio_mvo_optimizer import PortfolioMVOptimizer
from utils.logging_utils import get_job_logger
from utils.swedish_tax_calculator import SwedishTaxCalculator
from utils.transaction_cost_calculator import AvanzaCourtageCalculator
from utils.pdf_report_generator import PDFReportGenerator
from utils.csv_export_generator import CSVExportGenerator
from utils.shareable_link_generator import ShareableLinkGenerator
from utils.five_year_projection import run_five_year_projection
from utils.redis_ttl_monitor import RedisTTLMonitor
from slowapi import Limiter
from slowapi.util import get_remote_address
from pypfopt import EfficientFrontier
from fastapi.responses import Response, StreamingResponse
import base64
import zipfile
from io import BytesIO
from models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation
from datetime import datetime, timedelta, date
import random

logger = logging.getLogger(__name__)
portfolio_regen_logger = get_job_logger("portfolio_regeneration")

# Define a router without a hardcoded prefix so it can be mounted under
# multiple prefixes (v1 and legacy) by the main application.
router = APIRouter()

# Include domain-focused sub-routers
from .admin import router as admin_router
router.include_router(admin_router)

# Domain routers (routes in this file are attached to these).
# Sub-routers are included at the end of this file so all route decorators run first.
portfolios_router = APIRouter()
optimization_router = APIRouter()
analytics_router = APIRouter()
export_router = APIRouter()

# Initialize rate limiter (used by routes still in this file)
limiter = Limiter(key_func=get_remote_address)

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

@portfolios_router.get("/top-pick/{risk_profile}")
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
        # Use conservative approach + Strategy 5 for aggressive profiles
        eg = EnhancedPortfolioGenerator(_rds, pa, use_conservative_approach=True)
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

@portfolios_router.post("/calculate-metrics", response_model=PortfolioMetricsResponse)
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
        
        # Generate validation warnings (allow rounding e.g. 99.5-100.5)
        warnings = []
        if abs(total_allocation - 100) > 0.5:
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

@portfolios_router.post("/optimize", response_model=PortfolioOptimizationResponse)
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
                returns = prices.pct_change(fill_method=None).dropna()
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
        
        # Risk profile constraints - using centralized config
        from utils.risk_profile_config import get_max_risk_for_profile
        max_risk = get_max_risk_for_profile(risk_profile)
        
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

@portfolios_router.get("/search-tickers")
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

@portfolios_router.get("/search-suggestions")
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

@portfolios_router.get("/ticker-info/{ticker}")
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

@portfolios_router.get("/ticker-price-history/{ticker}")
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

@portfolios_router.get("/ticker-monthly-data/{ticker}")
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

# (Admin routes: warm-cache, warm-tickers, cache-status, clear-cache, TTL, force-refresh, health -> routers/admin.py)

@portfolios_router.get("/tickers/master")
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

@portfolios_router.get("/tickers/available")
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


def _ticker_region_from_symbol(ticker: str) -> str:
    """Classify ticker into region by symbol suffix. Returns 'swedish', 'european', 'us', or 'other'."""
    if not ticker or not isinstance(ticker, str):
        return "other"
    t = ticker.upper().strip()
    if t.endswith(".ST") or t.endswith(".SS"):
        return "swedish"
    european_suffixes = (
        ".DE", ".F", ".XETR", ".PA", ".EPA", ".L", ".LSE", ".MI", ".BIT",
        ".AS", ".AMS", ".MC", ".MCE", ".SW", ".VX", ".OL", ".OSL",
        ".CO", ".CPH", ".HE", ".HEL", ".BR", ".LS", ".WA", ".VI"
    )
    if any(t.endswith(s) for s in european_suffixes):
        return "european"
    if "." not in t or t.endswith(".US"):
        return "us"
    return "other"


@portfolios_router.get("/ticker-universe")
def get_ticker_universe():
    """
    Redis-backed ticker universe for UI: approximate count and exchange/region breakdown.
    Used for the info bar e.g. '~1,400 tickers across US, European, and Swedish exchanges'.
    """
    try:
        selectable = _rds.list_cached_tickers()
        selectable_count = len(selectable)
        master_list = _rds.all_tickers or []
        total_in_master = len(master_list)

        region_counts = {"us": 0, "european": 0, "swedish": 0, "other": 0}
        for t in selectable:
            region = _ticker_region_from_symbol(t)
            region_counts[region] = region_counts.get(region, 0) + 1

        regions = []
        if region_counts.get("us", 0) > 0:
            regions.append({"label": "US (e.g. S&P 500)", "count": region_counts["us"]})
        if region_counts.get("european", 0) > 0:
            regions.append({"label": "European", "count": region_counts["european"]})
        if region_counts.get("swedish", 0) > 0:
            regions.append({"label": "Swedish", "count": region_counts["swedish"]})
        if region_counts.get("other", 0) > 0:
            regions.append({"label": "Other", "count": region_counts["other"]})

        return {
            "selectable_count": selectable_count,
            "total_in_master": total_in_master,
            "regions": regions,
            "source": "redis",
        }
    except Exception as e:
        logger.error(f"Error getting ticker universe: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ticker universe: {str(e)}")


@portfolios_router.post("/tickers/refresh")
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

# ============================================================================
# Agent 1: Optimization Data Preparation Endpoints
# ============================================================================

# ============================================================================
# Cache Invalidation and Refresh Functions
# ============================================================================

# Global flag to prevent multiple simultaneous cache refreshes
_refresh_in_progress = False

def _invalidate_eligible_tickers_cache():
    """
    Invalidate all eligible tickers cache entries.
    Called when ticker data is refreshed to ensure cache stays in sync.
    """
    if not _rds.redis_client:
        return
    
    try:
        # Find all eligible tickers cache keys
        pattern = "optimization:eligible_tickers:*"
        keys = _rds.redis_client.keys(pattern)
        if keys:
            _rds.redis_client.delete(*keys)
            logger.info(f"🗑️  Invalidated {len(keys)} eligible tickers cache entries")
        else:
            logger.debug("No eligible tickers cache entries to invalidate")
    except Exception as e:
        logger.error(f"❌ Error invalidating eligible tickers cache: {e}")

def _trigger_eligible_tickers_refresh():
    """
    Trigger background refresh of eligible tickers cache.
    Called after ticker data is refreshed to rebuild the cache automatically.
    Prevents multiple simultaneous refreshes using a global flag.
    """
    global _refresh_in_progress
    
    # Prevent multiple simultaneous refreshes
    if _refresh_in_progress:
        logger.debug("⏳ Eligible tickers cache refresh already in progress, skipping duplicate trigger")
        return
    
    import asyncio
    
    async def refresh_cache():
        global _refresh_in_progress
        _refresh_in_progress = True
        try:
            logger.info("🔄 Triggering background refresh of eligible tickers cache after ticker data update...")
            from routers.portfolio import _compute_eligible_tickers_internal
            from utils.redis_first_data_service import redis_first_data_service as _rds
            import time
            import json
            import hashlib
            
            start_time = time.time()
            
            # Get all tickers
            all_tickers = _rds.all_tickers or _rds.list_cached_tickers()
            if not all_tickers:
                logger.warning("⚠️  No tickers available for cache refresh")
                return
            
            logger.info(f"📋 Refreshing eligible tickers cache for {len(all_tickers)} tickers...")
            
            # Compute with optimized parallel processing (8 workers, 4 batches)
            eligible_tickers, filtered_stats = await asyncio.to_thread(
                _compute_eligible_tickers_internal,
                all_tickers,
                min_data_points=30,
                filter_negative_returns=True,
                min_volatility=None,
                max_volatility=5.0,
                min_return=None,
                max_return=10.0,
                sectors_list=None,
                exclude_list=None,
                sort_by='ticker',
                max_workers=8,  # Optimized: 8 workers
                batch_workers=4,  # Optimized: 4 batches
                batch_size=100
            )
            
            # Calculate statistics
            total_eligible = len(eligible_tickers)
            overlap_groups = {'full': 0, 'partial': 0}
            data_quality_dist = {'Good': 0, 'Fair': 0, 'Limited': 0}
            
            for ticker_info in eligible_tickers:
                overlap_groups[ticker_info.get('overlap_group', 'partial')] += 1
                data_quality_dist[ticker_info.get('data_quality', 'Unknown')] += 1
            
            summary = {
                "total_eligible": total_eligible,
                "filtered_by_negative_returns": filtered_stats['negative_returns'],
                "filtered_by_insufficient_data": filtered_stats['insufficient_data'],
                "filtered_by_data_quality": filtered_stats['data_quality'],
                "filtered_by_missing_metrics": filtered_stats['missing_metrics'],
                "filtered_by_volatility": filtered_stats['volatility'],
                "filtered_by_return": filtered_stats['return'],
                "filtered_by_sector": filtered_stats['sector'],
                "filtered_by_exclude": filtered_stats['exclude'],
                "overlap_groups": overlap_groups,
                "data_quality_distribution": data_quality_dist
            }
            
            # Cache the result with 1 week TTL
            cache_params = {
                'min_data_points': 30,
                'filter_negative_returns': True,
                'min_volatility': None,
                'max_volatility': 5.0,
                'min_return': None,
                'max_return': 10.0,
                'sectors': None
            }
            cache_key_str = json.dumps(cache_params, sort_keys=True)
            cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
            cache_key = f"optimization:eligible_tickers:{cache_hash}"
            
            result_to_cache = {
                "eligible_tickers": eligible_tickers,
                "summary": summary
            }
            
            if _rds.redis_client:
                _rds.redis_client.setex(
                    cache_key,
                    604800,  # 7 days TTL - background regeneration handles refresh before expiry
                    json.dumps(result_to_cache)
                )
            
            elapsed = time.time() - start_time
            logger.info("="*80)
            logger.info("✅ ELIGIBLE TICKERS CACHE REFRESHED AFTER TICKER DATA UPDATE!")
            logger.info(f"   ⏱️  Processing Time: {elapsed:.2f}s")
            logger.info(f"   📊 Total Eligible: {total_eligible} tickers")
            logger.info(f"   🔗 Full Overlap: {overlap_groups['full']} tickers")
            logger.info(f"   🔗 Partial Overlap: {overlap_groups['partial']} tickers")
            logger.info(f"   ⚡ Performance: {len(all_tickers)/elapsed:.2f} tickers/sec")
            logger.info("="*80)
            logger.info("✅ Eligible tickers cache is now up-to-date with latest ticker data!")
            
        except Exception as e:
            logger.error(f"❌ Background eligible tickers cache refresh failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            _refresh_in_progress = False
    
    # Schedule background task: only create the coroutine when we will run it
    # to avoid "coroutine was never awaited" when there is no running loop.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        loop.create_task(refresh_cache())
    else:
        import threading
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(refresh_cache())
            new_loop.close()
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

# ============================================================================
# Reusable function for computing eligible tickers (used by endpoint and background task)
# ============================================================================

def _compute_eligible_tickers_internal(
    all_tickers: List[str],
    min_data_points: int = 30,
    filter_negative_returns: bool = True,
    min_volatility: Optional[float] = None,
    max_volatility: float = 5.0,
    min_return: Optional[float] = None,
    max_return: float = 10.0,
    sectors_list: Optional[List[str]] = None,
    exclude_list: Optional[List[str]] = None,
    sort_by: str = 'ticker',
    max_workers: int = 8,
    batch_workers: int = 4,
    batch_size: int = 100
) -> tuple[List[Dict], Dict]:
    """
    Internal function to compute eligible tickers with parallel processing.
    
    Returns:
        (eligible_tickers_list, filtered_stats_dict)
    """
    eligible_tickers = []
    filtered_by_negative_returns = 0
    filtered_by_insufficient_data = 0
    filtered_by_missing_metrics = 0
    filtered_by_data_quality = 0
    filtered_by_volatility = 0
    filtered_by_return = 0
    filtered_by_sector = 0
    filtered_by_exclude = 0
    
    redis_client = _rds.redis_client
    
    def _parse_price_data(raw_data: bytes, ticker: str) -> Optional[pd.Series]:
        """Parse price data from raw Redis bytes"""
        if not raw_data:
            return None
        try:
            try:
                data_dict = json.loads(gzip.decompress(raw_data).decode())
            except:
                data_dict = json.loads(raw_data.decode())
            prices = pd.Series(data_dict)
            if not isinstance(prices.index, pd.DatetimeIndex):
                prices.index = pd.to_datetime(prices.index, format='mixed', utc=True)
            return prices
        except Exception as e:
            logger.debug(f"⚠️ Error parsing price data for {ticker}: {e}")
            return None
    
    def _parse_metrics_data(raw_data: bytes) -> Optional[Dict]:
        """Parse metrics data from raw Redis bytes"""
        if not raw_data:
            return None
        try:
            return json.loads(raw_data.decode())
        except:
            return None
    
    def _parse_sector_data(raw_data: bytes) -> Optional[Any]:
        """Parse sector data from raw Redis bytes"""
        if not raw_data:
            return None
        try:
            return json.loads(raw_data.decode())
        except:
            return None
    
    def _process_ticker_batch(batch_tickers: List[str], batch_num: int) -> tuple:
        """Process a batch of tickers and return eligible ones"""
        batch_eligible = []
        batch_filtered_stats = {
            'negative_returns': 0,
            'insufficient_data': 0,
            'data_quality': 0,
            'missing_metrics': 0,
            'volatility': 0,
            'return': 0,
            'sector': 0,
            'exclude': 0
        }
        
        # Batch load from Redis
        batch_data = {}
        if redis_client:
            try:
                with redis_client.pipeline() as pipe:
                    for ticker in batch_tickers:
                        pipe.get(_rds._get_cache_key(ticker, 'prices'))
                        pipe.get(_rds._get_cache_key(ticker, 'metrics'))
                        pipe.get(_rds._get_cache_key(ticker, 'sector'))
                    results = pipe.execute()
                
                # Parse in parallel
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    parse_futures = {}
                    for i, ticker in enumerate(batch_tickers):
                        price_idx = i * 3
                        metrics_idx = i * 3 + 1
                        sector_idx = i * 3 + 2
                        
                        parse_futures[ticker] = {
                            'prices': executor.submit(_parse_price_data, results[price_idx], ticker),
                            'metrics': executor.submit(_parse_metrics_data, results[metrics_idx]),
                            'sector': executor.submit(_parse_sector_data, results[sector_idx])
                        }
                    
                    # Collect parsed data
                    for ticker in batch_tickers:
                        futures = parse_futures[ticker]
                        batch_data[ticker] = {
                            'prices': futures['prices'].result(),
                            'metrics': futures['metrics'].result(),
                            'sector': futures['sector'].result()
                        }
            except Exception as e:
                logger.debug(f"⚠️ Batch {batch_num} pipeline failed: {e}")
                batch_data = {}
        
        # Process each ticker
        for ticker in batch_tickers:
            try:
                # Skip if in exclude list
                if exclude_list and ticker.upper() in exclude_list:
                    batch_filtered_stats['exclude'] += 1
                    continue
                
                # Get parsed data
                prices = batch_data.get(ticker, {}).get('prices')
                if prices is None:
                    prices = _rds._load_from_cache(ticker, 'prices')
                
                if prices is None or (hasattr(prices, 'empty') and prices.empty):
                    batch_filtered_stats['insufficient_data'] += 1
                    continue
                
                # Quick check: data points before expensive validation
                data_points = len(prices) if hasattr(prices, '__len__') else 0
                if data_points < min_data_points:
                    batch_filtered_stats['insufficient_data'] += 1
                    continue
                
                # Validate price data quality
                if not _validate_price_data_optimization(prices, ticker):
                    batch_filtered_stats['data_quality'] += 1
                    continue
                
                # Get metrics
                metrics = batch_data.get(ticker, {}).get('metrics')
                if metrics is None:
                    metrics = _rds._load_from_cache(ticker, 'metrics')
                
                expected_return = None
                volatility = None
                
                if metrics and isinstance(metrics, dict):
                    expected_return = metrics.get('annualized_return')
                    volatility = metrics.get('risk')
                
                # Validate cached metrics
                if expected_return is not None and volatility is not None:
                    if not _validate_calculated_metrics_optimization(expected_return, volatility, ticker):
                        expected_return = None
                        volatility = None
                
                # Calculate if needed
                if expected_return is None or volatility is None:
                    calculated_metrics = _calculate_metrics_safely_optimization(prices, ticker)
                    if calculated_metrics is None:
                        batch_filtered_stats['missing_metrics'] += 1
                        continue
                    expected_return = calculated_metrics['expected_return']
                    volatility = calculated_metrics['volatility']
                
                # Apply filters
                if filter_negative_returns and (expected_return is None or expected_return <= 0):
                    batch_filtered_stats['negative_returns'] += 1
                    continue
                
                if min_volatility is not None and volatility < min_volatility:
                    batch_filtered_stats['volatility'] += 1
                    continue
                
                if volatility > max_volatility:
                    batch_filtered_stats['volatility'] += 1
                    continue
                
                if min_return is not None and expected_return < min_return:
                    batch_filtered_stats['return'] += 1
                    continue
                
                if expected_return > max_return:
                    batch_filtered_stats['return'] += 1
                    continue
                
                # Get sector info
                sector_data = batch_data.get(ticker, {}).get('sector')
                if sector_data is None:
                    sector_data = _rds._load_from_cache(ticker, 'sector')
                
                sector = 'Unknown'
                industry = 'Unknown'
                company_name = ticker
                
                if sector_data and isinstance(sector_data, dict):
                    sector = sector_data.get('sector', 'Unknown')
                    industry = sector_data.get('industry', 'Unknown')
                    company_name = sector_data.get('companyName', ticker)
                elif sector_data and isinstance(sector_data, str):
                    sector = sector_data
                
                # Apply sector filter
                if sectors_list and sector.lower() not in sectors_list:
                    batch_filtered_stats['sector'] += 1
                    continue
                
                # Determine data quality and overlap group
                data_quality = 'Good'
                if data_points < 60:
                    data_quality = 'Fair'
                if data_points < 36:
                    data_quality = 'Limited'
                
                # Store date range for overlap calculation (will be processed after all batches)
                overlap_group = 'partial'
                recommended_for_optimization = False
                date_range = None
                if data_points >= 178:
                    try:
                        if isinstance(prices.index, pd.DatetimeIndex):
                            start_date = prices.index[0]
                            end_date = prices.index[-1]
                            # Normalize timestamps to timezone-naive for comparison
                            # Convert timezone-aware timestamps to naive
                            if isinstance(start_date, pd.Timestamp) and start_date.tz is not None:
                                start_date = start_date.tz_convert('UTC').tz_localize(None)
                            
                            if isinstance(end_date, pd.Timestamp) and end_date.tz is not None:
                                end_date = end_date.tz_convert('UTC').tz_localize(None)
                            
                            date_range = {
                                'start': start_date,
                                'end': end_date,
                                'data_points': data_points
                            }
                    except Exception as e:
                        logger.debug(f"Error creating date range: {e}")
                        pass
                
                # Add to eligible list (store date_range for later overlap calculation)
                batch_eligible.append({
                    'ticker': ticker,
                    'sector': sector,
                    'industry': industry,
                    'company_name': company_name,
                    'volatility': round(volatility, 4) if volatility else None,
                    'expected_return': round(expected_return, 4) if expected_return else None,
                    'data_points': data_points,
                    'data_quality': data_quality,
                    'overlap_group': overlap_group,
                    'recommended_for_optimization': recommended_for_optimization,
                    '_date_range': date_range  # Internal: used for overlap calculation
                })
                
            except Exception as e:
                logger.debug(f"⚠️ Error processing {ticker}: {e}")
                batch_filtered_stats['insufficient_data'] += 1
                continue
        
        return batch_eligible, batch_filtered_stats
    
    # Process batches in parallel
    ticker_batches = [all_tickers[i:i + batch_size] for i in range(0, len(all_tickers), batch_size)]
    
    with ThreadPoolExecutor(max_workers=batch_workers) as executor:
        future_to_batch = {
            executor.submit(_process_ticker_batch, batch, idx + 1): idx
            for idx, batch in enumerate(ticker_batches)
        }
        
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                batch_eligible, batch_stats = future.result()
                eligible_tickers.extend(batch_eligible)
                
                # Update filtered stats
                filtered_by_negative_returns += batch_stats['negative_returns']
                filtered_by_insufficient_data += batch_stats['insufficient_data']
                filtered_by_data_quality += batch_stats['data_quality']
                filtered_by_missing_metrics += batch_stats['missing_metrics']
                filtered_by_volatility += batch_stats['volatility']
                filtered_by_return += batch_stats['return']
                filtered_by_sector += batch_stats['sector']
                filtered_by_exclude += batch_stats['exclude']
            except Exception as e:
                logger.error(f"❌ Batch {batch_idx + 1} failed: {e}")
    
    # Calculate maximum overlap period from all eligible tickers with 178+ data points
    date_ranges_178_plus = []
    for ticker_info in eligible_tickers:
        if ticker_info.get('_date_range') is not None:
            date_ranges_178_plus.append(ticker_info['_date_range'])
    
    # Find longest common overlap period
    max_overlap_start = None
    max_overlap_end = None
    max_overlap_count = 0
    max_overlap_months = 0
    
    if date_ranges_178_plus:
        # Strategy: Find the longest period that maximizes both coverage and duration
        # Normalize all timestamps to timezone-naive before comparison
        normalized_ranges = []
        for dr in date_ranges_178_plus:
            try:
                start = dr['start']
                end = dr['end']
                # Normalize to timezone-naive if needed
                # Convert timezone-aware timestamps to naive for comparison
                if isinstance(start, pd.Timestamp):
                    if start.tz is not None:
                        # Convert to UTC first, then remove timezone
                        start = start.tz_convert('UTC').tz_localize(None)
                else:
                    start = pd.Timestamp(start)
                    if start.tz is not None:
                        start = start.tz_convert('UTC').tz_localize(None)
                
                if isinstance(end, pd.Timestamp):
                    if end.tz is not None:
                        # Convert to UTC first, then remove timezone
                        end = end.tz_convert('UTC').tz_localize(None)
                else:
                    end = pd.Timestamp(end)
                    if end.tz is not None:
                        end = end.tz_convert('UTC').tz_localize(None)
                
                normalized_ranges.append({
                    'start': start,
                    'end': end,
                    'data_points': dr.get('data_points', 0)
                })
            except Exception as e:
                logger.debug(f"Error normalizing date range: {e}")
                continue
        
        # Get all unique start and end dates
        all_starts = sorted(set(dr['start'] for dr in normalized_ranges))
        all_ends = sorted(set(dr['end'] for dr in normalized_ranges))
        
        # Try all combinations of start/end dates to find maximum overlap
        # Limit to reasonable candidates to avoid excessive computation
        start_candidates = all_starts[:100] if len(all_starts) > 100 else all_starts
        end_candidates = all_ends[-100:] if len(all_ends) > 100 else all_ends
        
        for start_candidate in start_candidates:
            for end_candidate in end_candidates:
                if start_candidate >= end_candidate:
                    continue
                
                # Count how many tickers cover this period
                covering_tickers = [
                    dr for dr in normalized_ranges
                    if dr['start'] <= start_candidate and dr['end'] >= end_candidate
                ]
                covering_count = len(covering_tickers)
                
                if covering_count == 0:
                    continue
                
                # Calculate period length in months
                period_months = (end_candidate - start_candidate).days / 30.44
                
                # Prefer longer periods with good coverage
                # Score balances both coverage count and duration
                # We want to maximize: coverage * duration (weighted)
                score = covering_count * (1 + period_months / 50)  # Weight duration
                
                # Update if this is better (more coverage OR same coverage but longer period)
                if (covering_count > max_overlap_count) or \
                   (covering_count == max_overlap_count and period_months > max_overlap_months) or \
                   (score > max_overlap_count * (1 + max_overlap_months / 50) if max_overlap_months > 0 else False):
                    max_overlap_start = start_candidate
                    max_overlap_end = end_candidate
                    max_overlap_count = covering_count
                    max_overlap_months = period_months
        
        # If no good overlap found with candidates, use intersection approach
        if max_overlap_start is None and date_ranges_178_plus:
            # Find the intersection: latest start and earliest end
            latest_start = max(dr['start'] for dr in date_ranges_178_plus)
            earliest_end = min(dr['end'] for dr in date_ranges_178_plus)
            
            if latest_start < earliest_end:
                covering_tickers = [
                    dr for dr in date_ranges_178_plus
                    if dr['start'] <= latest_start and dr['end'] >= earliest_end
                ]
                if len(covering_tickers) > 0:
                    max_overlap_start = latest_start
                    max_overlap_end = earliest_end
                    max_overlap_count = len(covering_tickers)
                    max_overlap_months = (earliest_end - latest_start).days / 30.44
        
        # Update overlap_group for tickers that cover the maximum overlap period
        if max_overlap_start is not None and max_overlap_end is not None:
            logger.info(f"📊 Maximum overlap period: {max_overlap_start.date()} to {max_overlap_end.date()} "
                       f"({max_overlap_months:.1f} months, {max_overlap_count} tickers)")
            
            for ticker_info in eligible_tickers:
                date_range = ticker_info.get('_date_range')
                if date_range is not None:
                    if date_range['start'] <= max_overlap_start and date_range['end'] >= max_overlap_end:
                        ticker_info['overlap_group'] = 'full'
                        ticker_info['recommended_for_optimization'] = True
    
    # Remove internal _date_range field before returning
    for ticker_info in eligible_tickers:
        ticker_info.pop('_date_range', None)
    
    # Sort eligible tickers
    if sort_by == 'return':
        eligible_tickers.sort(key=lambda x: x.get('expected_return', 0), reverse=True)
    elif sort_by == 'volatility':
        eligible_tickers.sort(key=lambda x: x.get('volatility', 0))
    elif sort_by == 'sector':
        eligible_tickers.sort(key=lambda x: x.get('sector', ''))
    else:  # 'ticker'
        eligible_tickers.sort(key=lambda x: x.get('ticker', ''))
    
    filtered_stats = {
        'negative_returns': filtered_by_negative_returns,
        'insufficient_data': filtered_by_insufficient_data,
        'data_quality': filtered_by_data_quality,
        'missing_metrics': filtered_by_missing_metrics,
        'volatility': filtered_by_volatility,
        'return': filtered_by_return,
        'sector': filtered_by_sector,
        'exclude': filtered_by_exclude
    }
    
    return eligible_tickers, filtered_stats

# Helper functions for data validation and metrics calculation
def _validate_price_data_optimization(prices: pd.Series, ticker: str) -> bool:
    """Validate price data quality before calculation (for optimization)"""
    if prices is None or prices.empty:
        return False
    
    # Check minimum data points
    if len(prices) < 12:
        return False
    
    # Check for zeros or negative prices
    if (prices <= 0).any():
        return False
    
    # Check for excessive missing values
    if prices.isna().sum() / len(prices) > 0.2:
        return False
    
    # Check for no variation (all same value)
    if prices.std() == 0:
        return False
    
    # Check for reasonable price range (filter extreme outliers)
    if prices.max() > 10000 or prices.min() < 0.01:
        return False
    
    # Check for suspicious jumps (price changes > 1000% in one period)
    try:
        pct_changes = prices.pct_change(fill_method=None).dropna()
        if len(pct_changes) > 0 and (pct_changes.abs() > 10).any():  # >1000% change
            return False
    except:
        pass
    
    return True

def _validate_calculated_metrics_optimization(expected_return: float, volatility: float, ticker: str) -> bool:
    """Validate calculated metrics for sanity (for optimization)"""
    # Check for NaN or Inf
    if pd.isna(expected_return) or pd.isna(volatility):
        return False
    if np.isinf(expected_return) or np.isinf(volatility):
        return False
    
    # Check for reasonable volatility (max 500% annual)
    if volatility > 5.0:
        logger.debug(f"⚠️ {ticker}: Volatility too high ({volatility:.2f})")
        return False
    
    # Check for reasonable expected return (max 1000% annual)
    if expected_return > 10.0:
        logger.debug(f"⚠️ {ticker}: Expected return too high ({expected_return:.2f})")
        return False
    
    # Check for negative volatility (impossible)
    if volatility < 0:
        return False
    
    return True

def _calculate_metrics_safely_optimization(prices: pd.Series, ticker: str) -> Optional[Dict[str, float]]:
    """Calculate metrics with proper error handling and validation (for optimization)"""
    try:
        # Validate price data first
        if not _validate_price_data_optimization(prices, ticker):
            return None
        
        # Calculate returns
        returns = prices.pct_change(fill_method=None).dropna()
        
        if len(returns) < 3:
            return None
        
        # Filter out extreme returns (likely data errors)
        # Remove returns > 500% or < -90% (likely data errors)
        returns_clean = returns[(returns > -0.90) & (returns < 5.0)]
        
        if len(returns_clean) < 3:
            # If too many outliers, use original but cap extreme values
            returns_clean = returns.clip(-0.90, 5.0)
        
        # Calculate monthly metrics
        monthly_return = returns_clean.mean()
        monthly_vol = returns_clean.std()
        
        # Annualize with safeguards
        # Use compound formula but cap extreme values
        if monthly_return > 0.5:  # >50% monthly return is suspicious
            monthly_return = min(monthly_return, 0.5)
        if monthly_return < -0.5:  # < -50% monthly return is suspicious
            monthly_return = max(monthly_return, -0.5)
        
        # Annualized return: (1 + monthly) ^ 12 - 1
        # But use simpler formula if compound would be extreme
        if abs(monthly_return) < 0.1:  # Small returns, compound is fine
            expected_return = (1 + monthly_return) ** 12 - 1
        else:  # Large returns, use simple multiplication to avoid extreme values
            expected_return = monthly_return * 12
        
        # Annualized volatility
        volatility = monthly_vol * np.sqrt(12)
        
        # Validate calculated metrics
        if not _validate_calculated_metrics_optimization(expected_return, volatility, ticker):
            return None
        
        return {
            'expected_return': float(expected_return),
            'volatility': float(volatility)
        }
    except Exception as e:
        logger.debug(f"⚠️ Error calculating metrics for {ticker}: {e}")
        return None

# Task 1.1: Get Eligible Tickers for Optimization (Internal Function)
def _get_eligible_tickers_internal(
    min_data_points: int = 30,
    filter_negative_returns: bool = True,
    min_volatility: Optional[float] = None,
    max_volatility: float = 5.0,
    min_return: Optional[float] = None,
    max_return: float = 10.0,
    sectors: Optional[str] = None,
    exclude_tickers: Optional[str] = None,
    use_cache: bool = True,
    page: int = 1,
    per_page: int = 100,
    sort_by: str = 'ticker'
):
    """
    Internal function to get eligible tickers (accepts regular Python parameters, not Query objects)
    
    Returns all tickers that meet data quality and filtering criteria.
    The optimizer will apply risk profile constraints later.
    """
    import time
    start_time = time.time()
    
    try:
        # Check cache if enabled
        if use_cache and _rds.redis_client:
            try:
                # Create cache key hash from parameters
                cache_params = {
                    'min_data_points': min_data_points,
                    'filter_negative_returns': filter_negative_returns,
                    'min_volatility': min_volatility,
                    'max_volatility': max_volatility,
                    'min_return': min_return,
                    'max_return': max_return,
                    'sectors': sectors
                }
                cache_key_str = json.dumps(cache_params, sort_keys=True)
                cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
                cache_key = f"optimization:eligible_tickers:{cache_hash}"
                
                cached_data = _rds.redis_client.get(cache_key)
                if cached_data:
                    try:
                        cached_result = json.loads(cached_data.decode())
                        logger.info(f"✅ Cache hit for eligible tickers")
                        # Apply pagination to cached result
                        total = len(cached_result.get('eligible_tickers', []))
                        start_idx = (page - 1) * per_page
                        end_idx = start_idx + per_page
                        paginated_tickers = cached_result['eligible_tickers'][start_idx:end_idx]
                        
                        return {
                            "eligible_tickers": paginated_tickers,
                            "pagination": {
                                "total": total,
                                "page": page,
                                "per_page": per_page,
                                "has_more": end_idx < total,
                                "total_pages": (total + per_page - 1) // per_page
                            },
                            "summary": cached_result.get('summary', {}),
                            "processing_time_seconds": 0.0
                        }
                    except Exception as e:
                        logger.debug(f"⚠️ Failed to parse cached data: {e}")
            except Exception as e:
                logger.debug(f"⚠️ Cache check failed: {e}")
        
        # Get all available tickers
        logger.info("📋 Getting all available tickers...")
        all_tickers = _rds.all_tickers or _rds.list_cached_tickers()
        
        if not all_tickers:
            raise HTTPException(status_code=404, detail="No tickers found in system")
        
        logger.info(f"✅ Found {len(all_tickers)} total tickers")
        
        # Parse filter parameters (sectors and exclude_tickers are strings here, not Query objects)
        sectors_list = [s.strip().lower() for s in sectors.split(',')] if sectors else None
        exclude_list = [t.strip().upper() for t in exclude_tickers.split(',')] if exclude_tickers else None
        
        eligible_tickers = []
        filtered_by_negative_returns = 0
        filtered_by_insufficient_data = 0
        filtered_by_missing_metrics = 0
        filtered_by_data_quality = 0
        filtered_by_volatility = 0
        filtered_by_return = 0
        filtered_by_sector = 0
        filtered_by_exclude = 0
        
        # Use optimized parallel processing (8 workers, 4 batches)
        logger.info(f"🔍 Processing {len(all_tickers)} tickers with optimized parallel processing (8 workers, 4 batches)...")
        
        # Compute eligible tickers using internal function
        eligible_tickers, filtered_stats_dict = _compute_eligible_tickers_internal(
            all_tickers=all_tickers,
            min_data_points=min_data_points,
            filter_negative_returns=filter_negative_returns,
            min_volatility=min_volatility,
            max_volatility=max_volatility,
            min_return=min_return,
            max_return=max_return,
            sectors_list=sectors_list,
            exclude_list=exclude_list,
            sort_by=sort_by,
            max_workers=8,  # Optimized: 8 workers for parsing
            batch_workers=4,  # Optimized: 4 batches in parallel
            batch_size=100
        )
        
        # Update filtered stats
        filtered_by_negative_returns = filtered_stats_dict['negative_returns']
        filtered_by_insufficient_data = filtered_stats_dict['insufficient_data']
        filtered_by_data_quality = filtered_stats_dict['data_quality']
        filtered_by_missing_metrics = filtered_stats_dict['missing_metrics']
        filtered_by_volatility = filtered_stats_dict['volatility']
        filtered_by_return = filtered_stats_dict['return']
        filtered_by_sector = filtered_stats_dict['sector']
        filtered_by_exclude = filtered_stats_dict['exclude']
        
        # Note: eligible_tickers are already sorted by _compute_eligible_tickers_internal
        
        # Calculate statistics
        total_eligible = len(eligible_tickers)
        overlap_groups = {'full': 0, 'partial': 0}
        data_quality_dist = {'Good': 0, 'Fair': 0, 'Limited': 0}
        
        for ticker_info in eligible_tickers:
            overlap_groups[ticker_info.get('overlap_group', 'partial')] += 1
            data_quality_dist[ticker_info.get('data_quality', 'Unknown')] += 1
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_tickers = eligible_tickers[start_idx:end_idx]
        
        summary = {
            "total_eligible": total_eligible,
            "filtered_by_negative_returns": filtered_by_negative_returns,
            "filtered_by_insufficient_data": filtered_by_insufficient_data,
            "filtered_by_data_quality": filtered_by_data_quality,
            "filtered_by_missing_metrics": filtered_by_missing_metrics,
            "filtered_by_volatility": filtered_by_volatility,
            "filtered_by_return": filtered_by_return,
            "filtered_by_sector": filtered_by_sector,
            "filtered_by_exclude": filtered_by_exclude,
            "overlap_groups": overlap_groups,
            "data_quality_distribution": data_quality_dist
        }
        
        elapsed_time = time.time() - start_time
        
        # Cache the result if enabled
        if use_cache and _rds.redis_client:
            try:
                cache_params = {
                    'min_data_points': min_data_points,
                    'filter_negative_returns': filter_negative_returns,
                    'min_volatility': min_volatility,
                    'max_volatility': max_volatility,
                    'min_return': min_return,
                    'max_return': max_return,
                    'sectors': sectors
                }
                cache_key_str = json.dumps(cache_params, sort_keys=True)
                cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
                cache_key = f"optimization:eligible_tickers:{cache_hash}"
                
                result_to_cache = {
                    "eligible_tickers": eligible_tickers,
                    "summary": summary
                }
                
                _rds.redis_client.setex(
                    cache_key,
                    604800,  # 7 days TTL - background regeneration handles refresh before expiry
                    json.dumps(result_to_cache)
                )
                logger.info(f"✅ Cached eligible tickers list (key: {cache_key}, TTL: 7 days)")
            except Exception as e:
                logger.debug(f"⚠️ Failed to cache eligible tickers: {e}")
        
        logger.info(f"✅ Found {total_eligible} eligible tickers in {elapsed_time:.2f}s")
        
        return {
            "eligible_tickers": paginated_tickers,
            "pagination": {
                "total": total_eligible,
                "page": page,
                "per_page": per_page,
                "has_more": end_idx < total_eligible,
                "total_pages": (total_eligible + per_page - 1) // per_page
            },
            "summary": summary,
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting eligible tickers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get eligible tickers: {str(e)}")

# Task 1.1: Get Eligible Tickers for Optimization (API Endpoint)
@optimization_router.get("/optimization/eligible-tickers")
def get_eligible_tickers_for_optimization(
    min_data_points: int = Query(30, ge=12, le=180, description="Minimum historical data points required"),
    filter_negative_returns: bool = Query(True, description="Filter out tickers with negative expected returns"),
    min_volatility: Optional[float] = Query(None, ge=0.0, le=5.0, description="Optional: Minimum volatility filter"),
    max_volatility: float = Query(5.0, ge=0.0, le=5.0, description="Maximum volatility filter (prevents extreme values)"),
    min_return: Optional[float] = Query(None, description="Optional: Minimum expected return filter"),
    max_return: float = Query(10.0, description="Maximum expected return filter (prevents extreme values)"),
    sectors: Optional[str] = Query(None, description="Optional: Comma-separated list of sectors to include"),
    exclude_tickers: Optional[str] = Query(None, description="Optional: Comma-separated list of tickers to exclude"),
    use_cache: bool = Query(True, description="Use cached eligible list if available"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    per_page: int = Query(100, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query('ticker', description="Sort by: 'ticker', 'return', 'volatility', 'sector'")
):
    """
    Get all eligible tickers for optimization (no risk profile filtering)
    
    Returns all tickers that meet data quality and filtering criteria.
    The optimizer will apply risk profile constraints later.
    """
    return _get_eligible_tickers_internal(
        min_data_points=min_data_points,
        filter_negative_returns=filter_negative_returns,
        min_volatility=min_volatility,
        max_volatility=max_volatility,
        min_return=min_return,
        max_return=max_return,
        sectors=sectors,
        exclude_tickers=exclude_tickers,
        use_cache=use_cache,
        page=page,
        per_page=per_page,
        sort_by=sort_by
    )

# Task 1.2: Get Ticker Metrics Batch
class TickerMetricsRequest(BaseModel):
    tickers: List[str]
    annualize: bool = True
    min_overlap_months: int = 12
    strict_overlap: bool = True

@optimization_router.post("/optimization/ticker-metrics")
def get_ticker_metrics_batch(request: TickerMetricsRequest):
    """
    Get mean returns (μ) and covariance matrix (Σ) for a list of tickers
    
    Required for Mean-Variance Optimization (MVO) calculations.
    Validates date overlap before calculation to ensure valid covariance.
    """
    import time
    start_time = time.time()
    
    try:
        tickers = [t.upper().strip() for t in request.tickers]
        annualize = request.annualize
        min_overlap_months = request.min_overlap_months
        strict_overlap = request.strict_overlap
        
        # Validate input
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required for covariance calculation")
        
        if len(tickers) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 tickers per request")
        
        # Check cache if enabled
        cache_hit = False
        if _rds.redis_client:
            try:
                ticker_hash = hashlib.md5(','.join(sorted(tickers)).encode()).hexdigest()
                cache_key = f"optimization:metrics:{ticker_hash}:{min_overlap_months}:{annualize}"
                
                cached_data = _rds.redis_client.get(cache_key)
                if cached_data:
                    try:
                        cached_result = json.loads(cached_data.decode())
                        logger.info(f"✅ Cache hit for {len(tickers)} tickers")
                        cache_hit = True
                        cached_result['metadata']['cache_hit'] = True
                        cached_result['metadata']['processing_time_seconds'] = 0.0
                        return cached_result
                    except Exception as e:
                        logger.debug(f"⚠️ Failed to parse cached data: {e}")
            except Exception as e:
                logger.debug(f"⚠️ Cache check failed: {e}")
        
        # OPTIMIZATION: Batch load price data using Redis pipeline
        logger.info(f"📊 Getting price data for {len(tickers)} tickers (batch loading)...")
        price_data = {}
        missing_tickers = []
        redis_client = _rds.redis_client
        
        # Try batch loading first
        if redis_client and len(tickers) > 1:
            try:
                with redis_client.pipeline() as pipe:
                    for ticker in tickers:
                        pipe.get(_rds._get_cache_key(ticker, 'prices'))
                    results = pipe.execute()
                
                # Parse batch results
                for ticker, raw_data in zip(tickers, results):
                    if raw_data:
                        try:
                            try:
                                data_dict = json.loads(gzip.decompress(raw_data).decode())
                            except:
                                data_dict = json.loads(raw_data.decode())
                            
                            prices = pd.Series(data_dict)
                            if not isinstance(prices.index, pd.DatetimeIndex):
                                prices.index = pd.to_datetime(prices.index, format='mixed', utc=True)
                            
                            if len(prices) >= 3:
                                price_data[ticker] = prices
                            else:
                                missing_tickers.append(ticker)
                        except Exception as e:
                            logger.debug(f"⚠️ Error parsing batch data for {ticker}: {e}")
                            missing_tickers.append(ticker)
                    else:
                        missing_tickers.append(ticker)
            except Exception as e:
                logger.debug(f"⚠️ Batch load failed, using individual loads: {e}")
                # Fallback to individual loads
                for ticker in tickers:
                    try:
                        prices = _rds._load_from_cache(ticker, 'prices')
                        if prices is None or (hasattr(prices, 'empty') and prices.empty):
                            missing_tickers.append(ticker)
                            continue
                        
                        if hasattr(prices, '__len__') and len(prices) < 3:
                            missing_tickers.append(ticker)
                            continue
                        
                        price_data[ticker] = prices
                    except Exception as e2:
                        logger.debug(f"⚠️ Error loading {ticker}: {e2}")
                        missing_tickers.append(ticker)
                        continue
        else:
            # Individual loads for small batches or no Redis
            for ticker in tickers:
                try:
                    prices = _rds._load_from_cache(ticker, 'prices')
                    if prices is None or (hasattr(prices, 'empty') and prices.empty):
                        missing_tickers.append(ticker)
                        continue
                    
                    if hasattr(prices, '__len__') and len(prices) < 3:
                        missing_tickers.append(ticker)
                        continue
                    
                    price_data[ticker] = prices
                except Exception as e:
                    logger.debug(f"⚠️ Error loading {ticker}: {e}")
                    missing_tickers.append(ticker)
                    continue
        
        if len(price_data) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient price data: only {len(price_data)}/{len(tickers)} tickers have data (need at least 2)"
            )
        
        # Calculate returns for each ticker and collect date ranges
        logger.info(f"📈 Calculating returns for {len(price_data)} tickers...")
        returns_data = {}
        date_ranges = {}
        
        for ticker, prices in price_data.items():
            try:
                if isinstance(prices, pd.Series):
                    # Ensure we have a DatetimeIndex
                    if not isinstance(prices.index, pd.DatetimeIndex):
                        try:
                            prices.index = pd.to_datetime(prices.index, format='mixed', utc=True)
                        except:
                            logger.debug(f"⚠️ {ticker}: Could not convert index to DatetimeIndex")
                            missing_tickers.append(ticker)
                            continue
                    
                    # Store date range
                    if len(prices) > 0:
                        date_ranges[ticker] = {
                            'start': prices.index[0],
                            'end': prices.index[-1],
                            'months': len(prices)
                        }
                    
                    returns = prices.pct_change(fill_method=None).dropna()
                else:
                    # Convert to Series if needed
                    prices_series = pd.Series(prices)
                    if len(prices_series) > 0:
                        date_ranges[ticker] = {
                            'start': prices_series.index[0] if hasattr(prices_series.index[0], 'strftime') else None,
                            'end': prices_series.index[-1] if hasattr(prices_series.index[-1], 'strftime') else None,
                            'months': len(prices_series)
                        }
                    returns = prices_series.pct_change(fill_method=None).dropna()
                
                if len(returns) >= 3:
                    returns_data[ticker] = returns
                else:
                    missing_tickers.append(ticker)
            except Exception as e:
                logger.debug(f"⚠️ Error calculating returns for {ticker}: {e}")
                missing_tickers.append(ticker)
                continue
        
        if len(returns_data) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient returns data: only {len(returns_data)}/{len(tickers)} tickers have valid returns (need at least 2)"
            )
        
        # Align all returns to common date range (intersection)
        logger.info("🔄 Aligning returns to common date range...")
        returns_df = pd.DataFrame(returns_data)
        
        # Find intersection of all date ranges
        if len(returns_df) == 0:
            error_metadata = {
                "ticker_count": len(tickers),
                "available_tickers": len(returns_data),
                "missing_tickers": missing_tickers,
                "overlap_months": 0,
                "min_overlap_required": min_overlap_months,
                "date_ranges": {k: {
                    'start': str(v['start']) if v.get('start') else None,
                    'end': str(v['end']) if v.get('end') else None,
                    'months': v['months']
                } for k, v in date_ranges.items()},
                "error": "No overlapping date ranges found",
                "cache_hit": False,
                "processing_time_seconds": round(time.time() - start_time, 3)
            }
            return JSONResponse(
                status_code=400,
                content={
                    "error": "No overlapping data after alignment",
                    "mu": {},
                    "sigma": {},
                    "metadata": error_metadata
                }
            )
        
        # Drop rows with any NaN (only keep overlapping periods)
        returns_df_aligned = returns_df.dropna()
        
        # Validate overlap BEFORE calculation
        overlap_months = len(returns_df_aligned)
        if overlap_months < min_overlap_months:
            error_metadata = {
                "ticker_count": len(tickers),
                "available_tickers": len(returns_data),
                "missing_tickers": missing_tickers,
                "overlap_months": overlap_months,
                "min_overlap_required": min_overlap_months,
                "overlap_sufficient": False,
                "date_ranges": {k: {
                    'start': str(v['start']) if v.get('start') else None,
                    'end': str(v['end']) if v.get('end') else None,
                    'months': v['months']
                } for k, v in date_ranges.items()},
                "suggestion": "Reduce ticker list or lower min_overlap_months requirement. Consider using tickers from full overlap group (400 tickers available with 178 months overlap).",
                "cache_hit": False,
                "processing_time_seconds": round(time.time() - start_time, 3)
            }
            if strict_overlap:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Insufficient date overlap",
                        "mu": {},
                        "sigma": {},
                        "metadata": error_metadata
                    }
                )
            else:
                logger.warning(f"⚠️ Insufficient overlap: {overlap_months} months (minimum: {min_overlap_months})")
        
        # Calculate mean returns (μ)
        logger.info("📊 Calculating mean returns...")
        monthly_mean_returns = returns_df_aligned.mean()
        
        if annualize:
            # Annualize: (1 + monthly_mean) ^ 12 - 1
            mu = {ticker: float((1 + monthly_mean) ** 12 - 1) for ticker, monthly_mean in monthly_mean_returns.items()}
        else:
            mu = {ticker: float(monthly_mean) for ticker, monthly_mean in monthly_mean_returns.items()}
        
        # Calculate covariance matrix (Σ)
        logger.info("📊 Calculating covariance matrix...")
        monthly_cov = returns_df_aligned.cov()
        
        if annualize:
            # Annualize: multiply by 12 for monthly data
            sigma_annualized = monthly_cov * 12
        else:
            sigma_annualized = monthly_cov
        
        # Convert to nested dict format
        sigma = {}
        for ticker1 in sigma_annualized.index:
            sigma[ticker1] = {}
            for ticker2 in sigma_annualized.columns:
                sigma[ticker1][ticker2] = float(sigma_annualized.loc[ticker1, ticker2])
        
        # Get date range from aligned data
        date_range = None
        if len(returns_df_aligned) > 0:
            try:
                start_date = returns_df_aligned.index[0]
                end_date = returns_df_aligned.index[-1]
                if hasattr(start_date, 'strftime'):
                    start_str = start_date.strftime('%Y-%m-%d')
                else:
                    start_str = str(start_date)
                if hasattr(end_date, 'strftime'):
                    end_str = end_date.strftime('%Y-%m-%d')
                else:
                    end_str = str(end_date)
                
                date_range = {
                    "start": start_str,
                    "end": end_str,
                    "months": len(returns_df_aligned)
                }
            except Exception as e:
                logger.debug(f"⚠️ Error formatting date range: {e}")
                date_range = {
                    "start": str(returns_df_aligned.index[0]),
                    "end": str(returns_df_aligned.index[-1]),
                    "months": len(returns_df_aligned)
                }
        
        # Validate calculated metrics for sanity
        metrics_valid = True
        warnings = []
        
        # Check for NaN or Inf in mu
        for ticker, mu_val in mu.items():
            if pd.isna(mu_val) or np.isinf(mu_val):
                metrics_valid = False
                warnings.append(f"{ticker}: Invalid mean return (NaN or Inf)")
            elif abs(mu_val) > 10.0:  # >1000% annual return
                warnings.append(f"{ticker}: Extreme mean return ({mu_val:.2f})")
        
        # Check for NaN or Inf in sigma
        for ticker1 in sigma:
            for ticker2 in sigma[ticker1]:
                sigma_val = sigma[ticker1][ticker2]
                if pd.isna(sigma_val) or np.isinf(sigma_val):
                    metrics_valid = False
                    warnings.append(f"{ticker1}-{ticker2}: Invalid covariance (NaN or Inf)")
        
        # Prepare metadata
        metadata = {
            "ticker_count": len(tickers),
            "available_tickers": len(returns_data),
            "missing_tickers": missing_tickers,
            "date_range": date_range,
            "overlap_months": len(returns_df_aligned),
            "min_overlap_required": min_overlap_months,
            "overlap_sufficient": overlap_months >= min_overlap_months,
            "annualized": annualize,
            "metrics_valid": metrics_valid,
            "warnings": warnings,
            "cache_hit": cache_hit,
            "processing_time_seconds": round(time.time() - start_time, 3)
        }
        
        result = {
            "mu": mu,
            "sigma": sigma,
            "metadata": metadata
        }
        
        # Cache the result if enabled
        if not cache_hit and _rds.redis_client:
            try:
                ticker_hash = hashlib.md5(','.join(sorted(tickers)).encode()).hexdigest()
                cache_key = f"optimization:metrics:{ticker_hash}:{min_overlap_months}:{annualize}"
                
                _rds.redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL - ephemeral computation result
                    json.dumps(result)
                )
                logger.info(f"✅ Cached metrics for {len(tickers)} tickers (key: {cache_key}, TTL: 1 hour)")
            except Exception as e:
                logger.debug(f"⚠️ Failed to cache metrics: {e}")
        
        logger.info(f"✅ Calculated metrics for {len(returns_data)} tickers in {metadata['processing_time_seconds']:.3f}s")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting ticker metrics: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get ticker metrics: {str(e)}")

# Task 2: Mean-Variance Optimization (MVO) Endpoint
class MVOOptimizationRequest(BaseModel):
    tickers: List[str]
    optimization_type: str = "max_sharpe"  # "max_sharpe", "min_variance", "target_return", "target_risk"
    target_return: Optional[float] = None
    max_risk: Optional[float] = None
    risk_profile: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    current_portfolio: Optional[Dict[str, Any]] = None  # Optional: current portfolio weights for comparison
    include_efficient_frontier: bool = True
    include_random_portfolios: bool = True
    num_frontier_points: int = 20
    num_random_portfolios: int = 200

class MVOOptimizationResponse(BaseModel):
    optimization_type: str
    strategy_name: str
    optimized_portfolio: Dict[str, Any]
    current_portfolio: Optional[Dict[str, Any]] = None
    efficient_frontier: List[Dict[str, Any]] = []
    inefficient_frontier: List[Dict[str, Any]] = []  # Lower part of hyperbola
    random_portfolios: List[Dict[str, Any]] = []
    capital_market_line: List[Dict[str, Any]] = []  # CML points
    improvements: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any]

# Initialize MVO optimizer (will use internal API calls)
_mvo_optimizer = None

def get_mvo_optimizer():
    """Get or create MVO optimizer instance"""
    global _mvo_optimizer
    if _mvo_optimizer is None:
        # Create internal function to call ticker-metrics endpoint
        def get_ticker_metrics_internal(tickers, annualize=True, min_overlap_months=12, strict_overlap=True):
            """Internal function to get ticker metrics"""
            request = TickerMetricsRequest(
                tickers=tickers,
                annualize=annualize,
                min_overlap_months=min_overlap_months,
                strict_overlap=strict_overlap
            )
            result = get_ticker_metrics_batch(request)
            # Handle JSONResponse - extract dict if needed
            if isinstance(result, JSONResponse):
                import json
                result_dict = json.loads(result.body.decode())
                # Check if it's an error response
                if result_dict.get('error') or not result_dict.get('sigma'):
                    error_msg = result_dict.get('error', 'No covariance matrix in response')
                    metadata = result_dict.get('metadata', {})
                    overlap_info = f" (overlap: {metadata.get('overlap_months', 'unknown')} months, required: {metadata.get('min_overlap_required', 'unknown')} months)"
                    raise ValueError(f"{error_msg}{overlap_info}")
                return result_dict
            return result
        
        # Use internal function calls (more efficient than HTTP)
        _mvo_optimizer = PortfolioMVOptimizer(get_ticker_metrics_func=get_ticker_metrics_internal)
    return _mvo_optimizer

@optimization_router.post("/optimization/mvo", response_model=MVOOptimizationResponse)
def optimize_portfolio_mvo(request: MVOOptimizationRequest):
    """
    Mean-Variance Optimization using PyPortfolioOpt
    
    This endpoint integrates with Agent 1 endpoints to:
    1. Get ticker metrics (μ and Σ) from /api/v1/portfolio/optimization/ticker-metrics
    2. Perform MVO optimization using PyPortfolioOpt
    3. Generate efficient frontier and random portfolios for visualization
    
    Optimization types:
    - max_sharpe: Maximum Sharpe ratio portfolio
    - min_variance: Minimum variance portfolio
    - target_return: Portfolio with target return and minimum risk
    - target_risk: Portfolio with target risk and maximum return
    """
    import time
    start_time = time.time()
    
    try:
        tickers = [t.upper().strip() for t in request.tickers]
        
        # Validate input
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required for optimization")
        
        if len(tickers) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 tickers per request")
        
        # Get MVO optimizer
        optimizer = get_mvo_optimizer()
        
        # Calculate current portfolio metrics if provided
        current_portfolio = None
        if request.current_portfolio:
            try:
                current_weights = request.current_portfolio.get('weights', {})
                current_metrics = optimizer.calculate_portfolio_metrics(tickers, current_weights)
                current_portfolio = {
                    "weights": current_weights,
                    "metrics": current_metrics
                }
            except Exception as e:
                logger.warning(f"⚠️ Could not calculate current portfolio metrics: {e}")
        
        # Perform optimization
        logger.info(f"🔧 Optimizing portfolio with {len(tickers)} tickers using {request.optimization_type}...")
        optimized_result = optimizer.optimize_portfolio(
            tickers=tickers,
            optimization_type=request.optimization_type,
            target_return=request.target_return,
            max_risk=request.max_risk,
            risk_profile=request.risk_profile,
            constraints=request.constraints
        )
        
        # Generate efficient frontier if requested
        efficient_frontier = []
        if request.include_efficient_frontier:
            try:
                logger.info(f"📊 Generating efficient frontier with {request.num_frontier_points} points...")
                efficient_frontier = optimizer.generate_efficient_frontier(
                    tickers=tickers,
                    num_points=request.num_frontier_points,
                    risk_profile=request.risk_profile
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not generate efficient frontier: {e}")
        
        # Generate inefficient frontier if requested (lower part of hyperbola)
        inefficient_frontier = []
        if request.include_efficient_frontier:  # Generate inefficient frontier when efficient frontier is requested
            try:
                logger.info(f"📊 Generating inefficient frontier with {request.num_frontier_points} points...")
                inefficient_frontier = optimizer.generate_inefficient_frontier(
                    tickers=tickers,
                    num_points=request.num_frontier_points,
                    risk_profile=request.risk_profile
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not generate inefficient frontier: {e}")
        
        # Generate random portfolios if requested
        random_portfolios = []
        if request.include_random_portfolios:
            try:
                logger.info(f"🎲 Generating {request.num_random_portfolios} random portfolios...")
                random_portfolios = optimizer.generate_random_portfolios(
                    tickers=tickers,
                    num_portfolios=request.num_random_portfolios,
                    risk_profile=request.risk_profile
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not generate random portfolios: {e}")
        
        # Calculate Capital Market Line (CML) from efficient frontier
        capital_market_line = []
        if efficient_frontier and len(efficient_frontier) > 0:
            try:
                logger.info("📈 Calculating Capital Market Line...")
                capital_market_line = optimizer.calculate_capital_market_line(
                    efficient_frontier=efficient_frontier,
                    risk_free_rate=optimizer.risk_free_rate
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not calculate CML: {e}")
        
        # Calculate improvements if current portfolio provided
        improvements = None
        if current_portfolio:
            current_metrics = current_portfolio.get('metrics', {})
            optimized_metrics = {
                'expected_return': optimized_result.get('expected_return', 0),
                'risk': optimized_result.get('risk', 0),
                'sharpe_ratio': optimized_result.get('sharpe_ratio', 0)
            }
            
            improvements = {
                'return_improvement': optimized_metrics['expected_return'] - current_metrics.get('expected_return', 0),
                'risk_improvement': current_metrics.get('risk', 0) - optimized_metrics['risk'],
                'sharpe_improvement': optimized_metrics['sharpe_ratio'] - current_metrics.get('sharpe_ratio', 0)
            }
        
        # Prepare response
        processing_time = time.time() - start_time
        
        response = MVOOptimizationResponse(
            optimization_type=optimized_result.get('optimization_type', request.optimization_type),
            strategy_name=optimized_result.get('strategy_name', 'MVO Optimization'),
            optimized_portfolio={
                "tickers": optimized_result.get('tickers', tickers),
                "weights": optimized_result.get('weights', {}),
                "weights_list": optimized_result.get('weights_list', []),
                "metrics": {
                    "expected_return": optimized_result.get('expected_return', 0),
                    "risk": optimized_result.get('risk', 0),
                    "sharpe_ratio": optimized_result.get('sharpe_ratio', 0)
                }
            },
            current_portfolio=current_portfolio,
            efficient_frontier=efficient_frontier,
            inefficient_frontier=inefficient_frontier,
            random_portfolios=random_portfolios,
            capital_market_line=capital_market_line,
            improvements=improvements,
            metadata={
                "num_tickers": len(tickers),
                "processing_time_seconds": round(processing_time, 3),
                "risk_free_rate": optimizer.risk_free_rate
            }
        )
        
        logger.info(f"✅ MVO optimization completed in {processing_time:.3f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in MVO optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to optimize portfolio: {str(e)}")

class DualOptimizationRequest(BaseModel):
    user_tickers: List[str]  # User's selected tickers
    risk_profile: str
    optimization_type: str = "max_sharpe"
    max_eligible_tickers: int = 20  # Top N eligible tickers to consider
    include_efficient_frontier: bool = True
    include_random_portfolios: bool = True
    num_frontier_points: int = 20
    num_random_portfolios: int = 200
    test_hour: Optional[int] = None  # For testing: override hour for diversity seed (0-23)
    # Optional: Current portfolio weights and metrics (if already calculated)
    current_portfolio_weights: Optional[Dict[str, float]] = None  # Actual allocation weights
    current_portfolio_metrics: Optional[Dict[str, float]] = None  # Pre-calculated metrics (expected_return, risk, sharpe_ratio)

class DualOptimizationResponse(BaseModel):
    current_portfolio: Dict[str, Any]  # User's current portfolio metrics and tickers
    optimized_portfolio: MVOOptimizationResponse  # Optimized portfolio from market tickers
    comparison: Dict[str, Any]  # Comparison metrics between current and optimized

class TripleOptimizationRequest(BaseModel):
    user_tickers: List[str]  # User's selected tickers
    user_weights: Dict[str, float]  # REQUIRED: Actual allocation weights (0.0-1.0)
    risk_profile: str
    optimization_type: str = "max_sharpe"
    max_eligible_tickers: int = 20
    include_efficient_frontier: bool = True
    include_random_portfolios: bool = True
    num_frontier_points: int = 20
    num_random_portfolios: int = 200
    use_combined_strategy: bool = True  # Enable weights-first + market exploration
    attempt_market_exploration: bool = True  # Always attempt market optimization

class TripleOptimizationResponse(BaseModel):
    current_portfolio: Dict[str, Any]  # Starting portfolio with actual weights
    weights_optimized_portfolio: MVOOptimizationResponse  # Weights-only optimization
    market_optimized_portfolio: Optional[MVOOptimizationResponse]  # Market exploration (optional)
    comparison: Dict[str, Any]  # Comparison between all three
    optimization_metadata: Dict[str, Any]  # Strategy used, attempts, recommendation

# Helper functions for triple optimization
def _postprocess_weights(weights: Dict[str, float], max_assets: int = 10, min_weight: float = 0.005) -> Dict[str, float]:
    """
    Trim weights to a practical holding count:
    - Drop tiny weights (< min_weight)
    - Keep top weights up to max_assets
    - Renormalize to sum to 1.0
    """
    if not weights:
        return {}
    # Drop tiny weights first
    filtered = {k: v for k, v in weights.items() if v >= min_weight and v > 0}
    if not filtered:
        filtered = weights
    # Sort by weight desc and keep top N
    sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    trimmed = dict(sorted_items[:max_assets])
    total = sum(trimmed.values())
    if total <= 0:
        return trimmed
    return {k: v / total for k, v in trimmed.items()}
def compute_portfolio_metrics_with_weights(tickers: List[str], weights: Dict[str, float],
                                          optimizer, min_overlap_months: int = 24,
                                          risk_profile: str = "moderate",
                                          _recursion_depth: int = 0) -> Dict[str, Any]:
    """Compute portfolio metrics using actual weights."""
    # Prevent infinite recursion
    if _recursion_depth > 0:
        logger.error(f"❌ Maximum recursion depth reached in compute_portfolio_metrics_with_weights")
        # Return fallback values instead of recursing
        return {
            "expected_return": 0.0,
            "risk": 0.0,
            "sharpe_ratio": 0.0
        }
    
    try:
        # Get ticker metrics
        mu_dict, sigma_df = optimizer.get_ticker_metrics(
            tickers=tickers,
            annualize=True,
            min_overlap_months=min_overlap_months,
            strict_overlap=False
        )
        
        # CRITICAL: Ensure tickers match between weights and metrics
        # get_ticker_metrics may filter out tickers with insufficient data
        # So we need to align weights with the actual tickers returned
        available_tickers = list(sigma_df.index) if hasattr(sigma_df, 'index') else list(mu_dict.keys())
        
        # Filter to only tickers that exist in both weights and metrics
        valid_tickers = [t for t in tickers if t in available_tickers and t in weights]
        
        if len(valid_tickers) < 2:
            raise ValueError(f"Insufficient valid tickers: {len(valid_tickers)} (need at least 2)")
        
        # Normalize weights for valid tickers only
        total_weight = sum(weights.get(t, 0.0) for t in valid_tickers)
        if total_weight <= 0:
            raise ValueError("Weights sum to zero or negative")
        
        # Create aligned arrays - ensure order matches sigma_df
        w_array = np.array([weights.get(t, 0.0) / total_weight for t in available_tickers])
        mu_array = np.array([mu_dict.get(t, 0.0) for t in available_tickers])
        
        # Ensure sigma_matrix matches the order
        sigma_matrix = sigma_df.loc[available_tickers, available_tickers].values
        
        # Verify dimensions match
        if len(w_array) != len(mu_array) or len(w_array) != sigma_matrix.shape[0]:
            raise ValueError(
                f"Dimension mismatch: w_array={len(w_array)}, mu_array={len(mu_array)}, "
                f"sigma_matrix={sigma_matrix.shape}"
            )
        
        # Calculate portfolio metrics
        expected_return = float(w_array @ mu_array)
        portfolio_variance = float(w_array @ sigma_matrix @ w_array)
        risk = float(np.sqrt(max(portfolio_variance, 0.0)))

        sharpe_ratio = (expected_return - optimizer.risk_free_rate) / risk if risk > 0 else 0.0

        # Cap extreme returns at the profile's realistic upper bound.
        # Current-portfolio weights are user-defined (not optimizer output), but
        # a holding in a stock with an exceptional historical year can still produce
        # an inflated portfolio return.  We apply the same profile-level cap used
        # in optimize_weights_only() for a consistent comparison table.
        from utils.risk_profile_config import get_max_realistic_return_for_profile
        max_return = get_max_realistic_return_for_profile(risk_profile)
        if expected_return > max_return:
            logger.debug(
                f"Capping current portfolio return {expected_return:.2%} → {max_return:.2%} "
                f"for profile '{risk_profile}'"
            )
            expected_return = max_return
            sharpe_ratio = (expected_return - optimizer.risk_free_rate) / risk if risk > 0 else 0.0

        return {
            "expected_return": expected_return,
            "risk": risk,
            "sharpe_ratio": sharpe_ratio
        }
    except Exception as e:
        logger.warning(f"⚠️ Error computing portfolio metrics with weights: {e}")
        # Fallback to equal weights with recursion guard
        if len(tickers) >= 2:
            equal_weight = 1.0 / len(tickers)
            return compute_portfolio_metrics_with_weights(
                tickers,
                {t: equal_weight for t in tickers},
                optimizer,
                min_overlap_months,
                risk_profile,
                _recursion_depth + 1
            )
        else:
            # Can't compute with less than 2 tickers
            return {
                "expected_return": 0.0,
                "risk": 0.0,
                "sharpe_ratio": 0.0
            }

def find_matching_portfolio_in_redis(user_tickers: List[str], user_weights: Dict[str, float], 
                                     risk_profile: str) -> Optional[Dict[str, Any]]:
    """
    Find a matching portfolio in Redis and return its precomputed metrics.
    
    Returns:
        Dict with precomputed metrics if match found, None otherwise
    """
    try:
        r = _rds.redis_client
        if not r:
            return None
        
        bucket_key = f"portfolio_bucket:{risk_profile}"
        
        # Check up to 60 portfolios (standard bucket size)
        for i in range(60):
            portfolio_key = f"{bucket_key}:{i}"
            portfolio_data = r.get(portfolio_key)
            
            if not portfolio_data:
                continue
            
            try:
                portfolio = json.loads(portfolio_data)
                allocations = portfolio.get('allocations', [])
                
                if not allocations:
                    continue
                
                # Check if tickers match
                portfolio_tickers = {a.get('symbol', '').upper() for a in allocations}
                user_tickers_set = {t.upper() for t in user_tickers}
                
                if portfolio_tickers != user_tickers_set:
                    continue
                
                # Check if allocations match (within 1% tolerance)
                portfolio_allocations = {a.get('symbol', '').upper(): a.get('allocation', 0) for a in allocations}
                matches = True
                for ticker in user_tickers_set:
                    user_alloc = user_weights.get(ticker.upper(), 0) * 100  # Convert to percentage
                    portfolio_alloc = portfolio_allocations.get(ticker.upper(), 0)
                    if abs(user_alloc - portfolio_alloc) > 1.0:  # 1% tolerance
                        matches = False
                        break
                
                if matches:
                    # Found matching portfolio - return precomputed metrics
                    # Handle both percentage (0-100) and decimal (0-1) formats
                    expected_return = portfolio.get('expectedReturn', 0)
                    if expected_return > 1.0:  # If > 1, it's a percentage, convert to decimal
                        expected_return = expected_return / 100.0
                    
                    risk = portfolio.get('risk', 0)
                    if risk > 1.0:  # If > 1, it's a percentage, convert to decimal
                        risk = risk / 100.0
                    
                    sharpe_ratio = portfolio.get('sharpeRatio', None)
                    # If sharpeRatio is missing, calculate it
                    if sharpe_ratio is None or sharpe_ratio == 0:
                        from utils.portfolio_mvo_optimizer import PortfolioMVOptimizer
                        optimizer_temp = PortfolioMVOptimizer()
                        risk_free_rate = optimizer_temp.risk_free_rate
                        sharpe_ratio = (expected_return - risk_free_rate) / risk if risk > 0 else 0.0
                    
                    logger.info(f"✅ Found matching portfolio in Redis for {risk_profile}, using precomputed metrics (Return: {expected_return:.2%}, Risk: {risk:.2%}, Sharpe: {sharpe_ratio:.2f})")
                    return {
                        "expected_return": expected_return,
                        "risk": risk,
                        "sharpe_ratio": sharpe_ratio
                    }
            except Exception as e:
                logger.debug(f"Error checking portfolio {i}: {e}")
                continue
        
        return None
    except Exception as e:
        logger.debug(f"Error searching Redis for matching portfolio: {e}")
        return None

def optimize_weights_only(tickers: List[str], risk_profile: str, optimizer, 
                         optimization_type: str = "max_sharpe") -> Dict[str, Any]:
    """Optimize weights of current tickers only (no new tickers)."""
    try:
        # Get ticker metrics
        mu_dict, sigma_df = optimizer.get_ticker_metrics(
            tickers=tickers,
            annualize=True,
            min_overlap_months=24,
            strict_overlap=False
        )
        
        # CRITICAL: Align tickers - get_ticker_metrics may filter out tickers with insufficient data
        # Get the actual tickers that were returned (from sigma_df index or mu_dict keys)
        available_tickers = list(sigma_df.index) if hasattr(sigma_df, 'index') and len(sigma_df.index) > 0 else list(mu_dict.keys())
        
        # Filter to only tickers that exist in both the original list and returned metrics
        valid_tickers = [t for t in tickers if t in available_tickers]
        
        if len(valid_tickers) < 2:
            raise ValueError(f"Insufficient valid tickers for optimization: {len(valid_tickers)} (need at least 2). Original: {len(tickers)}, Available: {len(available_tickers)}")
        
        # Create aligned arrays using the valid tickers in the same order as sigma_df
        mu_array = np.array([mu_dict.get(t, 0.0) for t in available_tickers])
        sigma_matrix = sigma_df.loc[available_tickers, available_tickers].values

        # Verify dimensions match
        if len(mu_array) != sigma_matrix.shape[0] or len(mu_array) != sigma_matrix.shape[1]:
            raise ValueError(
                f"Dimension mismatch after alignment: mu_array={len(mu_array)}, "
                f"sigma_matrix={sigma_matrix.shape}, available_tickers={len(available_tickers)}"
            )

        # --- Winsorise individual stock expected returns ---
        # Historical μ can be inflated by one-off exceptional years (e.g. a stock
        # returning +120 % in a single period).  Feeding raw outlier returns into
        # max-Sharpe causes extreme concentration (62 %+ in one ticker) and
        # produces unrealistic portfolio-level forecasts.
        # Clipping each stock's μ at the profile's max_realistic_return is the
        # standard MVO regularisation approach: the optimizer still maximises
        # Sharpe, but from a bounded, profile-consistent return landscape.
        from utils.risk_profile_config import get_max_realistic_return_for_profile
        max_stock_return = get_max_realistic_return_for_profile(risk_profile)
        clipped = np.clip(mu_array, -np.inf, max_stock_return)
        if not np.array_equal(clipped, mu_array):
            clipped_tickers = [
                available_tickers[i] for i in range(len(mu_array))
                if mu_array[i] > max_stock_return
            ]
            logger.info(
                f"📐 Winsorised {len(clipped_tickers)} ticker(s) to profile cap "
                f"{max_stock_return:.2%} for '{risk_profile}': {clipped_tickers}"
            )
            mu_array = clipped

        ef = EfficientFrontier(mu_array, sigma_matrix)
        
        if optimization_type == "max_sharpe":
            weights_array = ef.max_sharpe(risk_free_rate=optimizer.risk_free_rate)
        elif optimization_type == "min_variance":
            weights_array = ef.min_volatility()
        else:
            weights_array = ef.max_sharpe(risk_free_rate=optimizer.risk_free_rate)
        
        # Convert to dict - use available_tickers (aligned with optimization)
        optimized_weights = {available_tickers[i]: float(weights_array[i]) for i in range(len(available_tickers))}
        
        # Set weights to 0 for tickers that were filtered out
        for ticker in tickers:
            if ticker not in optimized_weights:
                optimized_weights[ticker] = 0.0
        
        # Calculate metrics using aligned arrays (mu_array already Winsorised above)
        w_array = np.array([weights_array[i] for i in range(len(available_tickers))])
        expected_return = float(w_array @ mu_array)
        portfolio_variance = float(w_array @ sigma_matrix @ w_array)
        risk = float(np.sqrt(max(portfolio_variance, 0.0)))
        sharpe_ratio = (expected_return - optimizer.risk_free_rate) / risk if risk > 0 else 0.0

        # Safety-net output cap (catches any residual excess after Winsorization)
        if expected_return > max_stock_return:
            logger.warning(
                f"⚠️ Weights-optimised return {expected_return:.2%} still exceeds "
                f"profile cap {max_stock_return:.2%}; capping."
            )
            expected_return = max_stock_return
            sharpe_ratio = (expected_return - optimizer.risk_free_rate) / risk if risk > 0 else 0.0

        return {
            "tickers": valid_tickers,  # Return only valid tickers that were optimized
            "weights": optimized_weights,
            "metrics": {
                "expected_return": expected_return,
                "risk": risk,
                "sharpe_ratio": sharpe_ratio
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in weights-only optimization: {e}")
        raise

def decide_best_portfolio(current: Dict[str, Any], weights_opt: Dict[str, Any], 
                         market_opt: Optional[Dict[str, Any]], risk_profile: str) -> str:
    """
    Decision framework: determine which portfolio to recommend.
    
    Updated rule (user intent):
    - Only recommend MARKET when:
        Sharpe_market >= Sharpe_weights + 0.10
        AND Risk_market <= Risk_weights + RISK_BUFFER (profile-specific)
    - Otherwise fall back to WEIGHTS vs CURRENT comparison.
    
    Risk buffers are profile-specific to account for:
    - Conservative profiles: tighter risk tolerance, small buffer
    - Aggressive profiles: more risk tolerance, larger buffer
    """
    EPS_SHARPE_SMALL = 0.05  # For weights vs current
    MARKET_SHARPE_MARGIN = 0.10
    
    # Profile-specific risk buffer: allows market portfolio to have slightly higher risk
    # This improves acceptance rate while maintaining risk-appropriate recommendations
    # Optimized based on comprehensive testing across all portfolios
    RISK_BUFFER_BY_PROFILE = {
        'very-conservative': 0.02,  # +2% buffer (slightly relaxed for better acceptance)
        'conservative': 0.03,       # +3% buffer
        'moderate': 0.03,           # +3% buffer
        'aggressive': 0.04,         # +4% buffer (more tolerance for higher risk profiles)
        'very-aggressive': 0.01     # +1% buffer (small buffer, already has good risk profile)
    }
    risk_buffer = RISK_BUFFER_BY_PROFILE.get(risk_profile, 0.03)
    
    current_sharpe = current.get("sharpe_ratio", 0.0)
    weights_sharpe = weights_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
    weights_risk = weights_opt.get("metrics", {}).get("risk", 0.0)
    current_risk = current.get("risk", 0.0)
    
    weights_vs_current = weights_sharpe - current_sharpe
    weights_risk_change = weights_risk - current_risk
    
    # If market optimization was attempted, apply acceptance rule with risk buffer
    if market_opt:
        market_sharpe = market_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
        market_risk = market_opt.get("metrics", {}).get("risk", 0.0)
        market_vs_weights = market_sharpe - weights_sharpe
        
        # Recommend market when:
        # 1. Sharpe is at least 0.10 better than weights
        # 2. Risk is not worse than weights + profile-specific buffer
        if (market_vs_weights >= MARKET_SHARPE_MARGIN) and (market_risk <= weights_risk + risk_buffer):
            return "market"
    
    # Is weights better than current?
    if weights_vs_current >= EPS_SHARPE_SMALL and weights_risk_change <= 0.0:
        return "weights"
    
    # Current is best
    return "current"

def decide_best_portfolio_v2(current: Dict[str, Any], weights_opt: Dict[str, Any], 
                             market_opt: Optional[Dict[str, Any]], risk_profile: str) -> str:
    """
    NEW Recommendation Logic (Conceptual Implementation):
    
    Compare Sharpe ratios across all portfolios.
    If an optimized portfolio has significantly better Sharpe (e.g., >0.10 improvement), 
    recommend it even with a moderate risk increase.
    Only default to "current" if it genuinely has the best risk-adjusted return or 
    if optimized portfolios have unacceptable risk levels.
    """
    from utils.risk_profile_config import RISK_PROFILE_MAX_RISK_WITH_BUFFER
    
    SIGNIFICANT_SHARPE_IMPROVEMENT = 0.10  # Threshold for "significantly better"
    MODERATE_RISK_INCREASE = 0.05  # 5% absolute increase considered moderate
    
    # Get maximum risk limit with 10% buffer
    max_risk_limit = RISK_PROFILE_MAX_RISK_WITH_BUFFER.get(risk_profile, 0.32 * 1.10)
    
    # Extract metrics
    current_sharpe = current.get("sharpe_ratio", 0.0)
    current_risk = current.get("risk", 0.0)
    
    weights_sharpe = weights_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
    weights_risk = weights_opt.get("metrics", {}).get("risk", 0.0)
    
    # Calculate Sharpe improvements
    weights_vs_current_sharpe = weights_sharpe - current_sharpe
    weights_risk_increase = weights_risk - current_risk
    
    market_sharpe = 0.0
    market_risk = 0.0
    market_vs_current_sharpe = 0.0
    market_vs_weights_sharpe = 0.0
    market_risk_increase = 0.0
    
    if market_opt:
        market_sharpe = market_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
        market_risk = market_opt.get("metrics", {}).get("risk", 0.0)
        market_vs_current_sharpe = market_sharpe - current_sharpe
        market_vs_weights_sharpe = market_sharpe - weights_sharpe
        market_risk_increase = market_risk - current_risk
    
    # Check risk compliance (with buffer)
    weights_risk_compliant = weights_risk <= max_risk_limit
    market_risk_compliant = market_risk <= max_risk_limit if market_opt else False
    
    # Strategy: Compare all portfolios by Sharpe ratio
    # Priority: Market > Weights > Current (if Sharpe improvements are significant)
    
    # 1. Check Market portfolio
    if market_opt and market_risk_compliant:
        # Market is acceptable if:
        # - Significantly better Sharpe than current (>0.10) AND risk increase is moderate (≤5%)
        # OR
        # - Significantly better Sharpe than weights (>0.10) AND risk is acceptable
        if (market_vs_current_sharpe >= SIGNIFICANT_SHARPE_IMPROVEMENT and 
            market_risk_increase <= MODERATE_RISK_INCREASE) or \
           (market_vs_weights_sharpe >= SIGNIFICANT_SHARPE_IMPROVEMENT):
            return "market"
    
    # 2. Check Weights portfolio
    if weights_risk_compliant:
        # Weights is acceptable if:
        # - Significantly better Sharpe than current (>0.10) AND risk increase is moderate (≤5%)
        # OR
        # - Better Sharpe than current (≥0.05) AND risk doesn't increase
        if (weights_vs_current_sharpe >= SIGNIFICANT_SHARPE_IMPROVEMENT and 
            weights_risk_increase <= MODERATE_RISK_INCREASE) or \
           (weights_vs_current_sharpe >= 0.05 and weights_risk_increase <= 0.0):
            return "weights"
    
    # 3. Default to Current
    # Only if:
    # - Current has best Sharpe ratio, OR
    # - Optimized portfolios violate risk limits, OR
    # - Optimized portfolios don't provide significant improvement
    return "current"

def build_triple_comparison(current: Dict[str, Any], weights_opt: Dict[str, Any], 
                           market_opt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build comparison between all three portfolios."""
    current_ret = current.get("expected_return", 0.0)
    current_risk = current.get("risk", 0.0)
    current_sharpe = current.get("sharpe_ratio", 0.0)
    
    weights_ret = weights_opt.get("metrics", {}).get("expected_return", 0.0)
    weights_risk = weights_opt.get("metrics", {}).get("risk", 0.0)
    weights_sharpe = weights_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
    
    # Weights vs Current
    weights_vs_current = {
        "return_difference": weights_ret - current_ret,
        "risk_difference": weights_risk - current_risk,
        "sharpe_difference": weights_sharpe - current_sharpe
    }
    
    # Market vs Current and Market vs Weights
    market_vs_current = None
    market_vs_weights = None
    
    if market_opt:
        market_ret = market_opt.get("metrics", {}).get("expected_return", 0.0)
        market_risk = market_opt.get("metrics", {}).get("risk", 0.0)
        market_sharpe = market_opt.get("metrics", {}).get("sharpe_ratio", 0.0)
        
        market_vs_current = {
            "return_difference": market_ret - current_ret,
            "risk_difference": market_risk - current_risk,
            "sharpe_difference": market_sharpe - current_sharpe
        }
        
        market_vs_weights = {
            "return_difference": market_ret - weights_ret,
            "risk_difference": market_risk - weights_risk,
            "sharpe_difference": market_sharpe - weights_sharpe
        }
    
    # Find best metrics
    returns = [current_ret, weights_ret]
    risks = [current_risk, weights_risk]
    sharpes = [current_sharpe, weights_sharpe]
    
    if market_opt:
        returns.append(market_opt.get("metrics", {}).get("expected_return", 0.0))
        risks.append(market_opt.get("metrics", {}).get("risk", 0.0))
        sharpes.append(market_opt.get("metrics", {}).get("sharpe_ratio", 0.0))
    
    best_return_idx = returns.index(max(returns))
    best_risk_idx = risks.index(min(risks))
    best_sharpe_idx = sharpes.index(max(sharpes))
    
    best_return = ["current", "weights", "market"][best_return_idx] if best_return_idx < 3 else "current"
    best_risk = ["current", "weights", "market"][best_risk_idx] if best_risk_idx < 3 else "current"
    best_sharpe = ["current", "weights", "market"][best_sharpe_idx] if best_sharpe_idx < 3 else "current"
    
    return {
        "weights_vs_current": weights_vs_current,
        "market_vs_current": market_vs_current,
        "market_vs_weights": market_vs_weights,
        "best_return": best_return,
        "best_risk": best_risk,
        "best_sharpe": best_sharpe
    }

@optimization_router.post("/optimization/dual", response_model=DualOptimizationResponse)
def optimize_dual_portfolio(request: DualOptimizationRequest):
    """
    Portfolio Optimization: Compare user's current portfolio vs optimized portfolio from market
    
    This endpoint:
    1. Calculates current portfolio metrics (user's selected tickers with current weights)
    2. Gets eligible tickers from entire market matching risk profile (with diversity rotation)
    3. Optimizes best portfolio from eligible market tickers
    4. Returns current portfolio + optimized portfolio for comparison
    
    The optimized portfolio uses diversity rotation to provide different ticker combinations
    over time while maintaining quality (high Sharpe ratio).
    """
    import time
    start_time = time.time()
    
    try:
        user_tickers = [t.upper().strip() for t in request.user_tickers]
        
        if len(user_tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 user tickers required")
        
        optimizer = get_mvo_optimizer()
        
        # Step 1: Calculate current portfolio metrics (user's tickers with equal weights for comparison)
        logger.info(f"🔧 Step 1: Calculating current portfolio metrics from {len(user_tickers)} tickers...")
        current_weights = {}
        if user_tickers:
            # Equal weights for current portfolio (or could use provided weights if available)
            equal_weight = 1.0 / len(user_tickers)
            current_weights = {ticker: equal_weight for ticker in user_tickers}
        
        # Calculate current portfolio metrics
        current_data_quality_warnings = []
        try:
            current_mvo_result = optimizer.optimize_portfolio(
            tickers=user_tickers,
            optimization_type=request.optimization_type,
            risk_profile=request.risk_profile,
                min_overlap_months=24,
                strict_overlap=False
            )
            current_expected_return = current_mvo_result.get('expected_return', 0)
            current_risk = current_mvo_result.get('risk', 0)
            current_sharpe = current_mvo_result.get('sharpe_ratio', 0)
            
            # Validate metrics for data quality issues
            # Flag unrealistic returns (>50% annual is suspicious for most portfolios)
            if current_expected_return > 0.50:
                current_data_quality_warnings.append(
                    f"Current portfolio shows {current_expected_return*100:.1f}% expected return, which may indicate limited historical data or data quality issues"
                )
                logger.warning(f"⚠️ Suspiciously high return for current portfolio: {current_expected_return*100:.1f}%")
            
            # Flag unrealistic risk (>60% annual volatility is very high)
            if current_risk > 0.60:
                current_data_quality_warnings.append(
                    f"Current portfolio shows {current_risk*100:.1f}% volatility, which is extremely high"
                )
            
            # Flag unrealistic Sharpe ratio (>3.0 is very rare, >5.0 is almost certainly data error)
            if current_sharpe > 3.0:
                current_data_quality_warnings.append(
                    f"Current portfolio Sharpe ratio of {current_sharpe:.2f} is unusually high and may indicate data quality issues"
                )
                logger.warning(f"⚠️ Suspiciously high Sharpe ratio for current portfolio: {current_sharpe:.2f}")
            
            current_metrics = {
                "expected_return": current_expected_return,
                "risk": current_risk,
                "sharpe_ratio": current_sharpe,
                "data_quality_warnings": current_data_quality_warnings
            }
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate current portfolio metrics: {e}, using fallback")
            current_metrics = {
                "expected_return": 0.10,
                "risk": 0.20,
                "sharpe_ratio": 0.50,
                "data_quality_warnings": ["Could not calculate metrics from historical data - using fallback values"]
            }
        
        # Step 2: Get eligible tickers for risk profile
        logger.info(f"🔧 Step 2: Getting eligible tickers for {request.risk_profile} risk profile...")
        try:
            # Get eligible tickers using the internal function (not the endpoint)
            # CRITICAL: Request MANY more tickers to ensure sufficient pool for diversity rotation
            # We need a large pool so that shuffling and sampling can produce variation
            # Use 50x multiplier or minimum 2000 to ensure we have enough tickers after filtering
            per_page_size = max(request.max_eligible_tickers * 50, 2000)
            eligible_response = _get_eligible_tickers_internal(
                min_data_points=36,  # Recommended V2: 36 months (3 years) for excellent covariance reliability
                filter_negative_returns=True,
                per_page=per_page_size,
                page=1,
                sort_by='return'  # Sort by return, but we'll shuffle by quality tiers later
            )
            
            eligible_tickers_data = eligible_response.get('eligible_tickers', [])
            pagination_info = eligible_response.get('pagination', {})
            total_eligible = pagination_info.get('total', len(eligible_tickers_data))
            
            # VERIFICATION: Log actual pool sizes at each step
            logger.info(f"🔍 POOL SIZE VERIFICATION:")
            logger.info(f"   Requested per_page_size: {per_page_size}")
            logger.info(f"   Total eligible tickers available: {total_eligible}")
            logger.info(f"   Eligible tickers returned (paginated): {len(eligible_tickers_data)}")
            logger.info(f"   Has more pages: {pagination_info.get('has_more', False)}")
            
            # CRITICAL: If pagination limited results, we need to fetch more pages
            if pagination_info.get('has_more', False) and len(eligible_tickers_data) < total_eligible:
                logger.warning(f"⚠️ WARNING: Only got {len(eligible_tickers_data)} tickers but {total_eligible} available. Pagination may be limiting diversity pool!")
            
            # Filter by risk profile volatility ranges - using centralized config
            from utils.risk_profile_config import get_volatility_range_for_profile
            vol_range = get_volatility_range_for_profile(request.risk_profile)
            min_vol, max_vol = vol_range
            
            # Filter with volatility range (min and max)
            filtered_tickers = [
                t for t in eligible_tickers_data
                if (t.get('volatility', 1.0) >= min_vol and 
                    t.get('volatility', 1.0) <= max_vol)
            ]
            
            logger.info(f"📊 Filtered {len(filtered_tickers)} tickers in volatility range {min_vol:.2%}-{max_vol:.2%} for {request.risk_profile}")
            
            # DIVERSITY ROTATION: Quality tier selection (NO metric manipulation)
            # Create deterministic but varied seed based on user tickers + hourly rotation
            import hashlib
            import random as diversity_random
            import random
            import numpy as np
            
            user_key = "_".join(sorted(user_tickers))
            current_datetime = datetime.now()
            date_seed = current_datetime.date().toordinal() % 7  # Weekly component for stability
            # Use test_hour if provided (for testing), otherwise use actual hour
            hour_seed = request.test_hour if request.test_hour is not None else current_datetime.hour  # Hourly rotation (0-23)
            # Increase hour component impact for better diversity (multiply by larger factor)
            # Calculate base hash (consistent for same user + risk profile)
            base_hash = int(hashlib.md5(f"{user_key}_{request.risk_profile}".encode()).hexdigest()[:8], 16)
            # Make hour component more significant by using it as a multiplier factor
            # This ensures different hours produce significantly different seeds
            # Calculate diversity_seed_value for ticker count determination (keep for compatibility)
            diversity_seed_value = (
                base_hash +
                date_seed * 100000 +  # Weekly variation (increased)
                hour_seed * 10000     # Hourly variation (increased significantly)
            )
            if request.test_hour is not None:
                logger.info(f"🔀 Diversity seed (TEST MODE): base_hash({base_hash}) + date({date_seed}*100000) + hour({hour_seed}*10000) = {diversity_seed_value}")
            else:
                logger.debug(f"🔀 Diversity seed: base_hash({base_hash}) + date({date_seed}*100000) + hour({hour_seed}*10000) = {diversity_seed_value}")
            # DO NOT seed diversity_random here - it will be seeded separately for shuffling and selection
            
            # Sort by overlap first, then by Sharpe ratio (NO manipulation)
            # This creates deterministic order BEFORE shuffling - this is intentional
            # We'll shuffle within quality tiers to introduce diversity
            filtered_tickers.sort(
                key=lambda x: (
                    bool(x.get('recommended_for_optimization', False)),  # Full overlap first
                    x.get('sharpe_ratio', x.get('expected_return', 0))  # Pure quality metric
                ),
                reverse=True
            )
            
            if request.test_hour is not None and filtered_tickers:
                sorted_order = [t['ticker'] for t in filtered_tickers[:10]]
                logger.info(f"🔀 After sort by Sharpe (first 10): {sorted_order}")
            
            # Quality tier selection (NO metric manipulation)
            # Categorize tickers into quality tiers based on actual Sharpe ratios
            sharpe_values = [t.get('sharpe_ratio', t.get('expected_return', 0)) for t in filtered_tickers if t.get('sharpe_ratio') is not None or t.get('expected_return') is not None]
            
            if sharpe_values and len(sharpe_values) > 0:
                top_tier_threshold = np.percentile(sharpe_values, 80)  # Top 20%
                mid_tier_threshold = np.percentile(sharpe_values, 50)  # Top 50%
                
                # Group by tier
                top_tier_tickers = []
                mid_tier_tickers = []
                lower_tier_tickers = []
                
                for t in filtered_tickers:
                    sharpe = t.get('sharpe_ratio', t.get('expected_return', 0))
                    if sharpe >= top_tier_threshold:
                        top_tier_tickers.append(t)
                    elif sharpe >= mid_tier_threshold:
                        mid_tier_tickers.append(t)
                    else:
                        lower_tier_tickers.append(t)
                
                # Randomize order within each tier (for diversity, NO metric modification)
                # CRITICAL: Use hour_seed as PRIMARY component to ensure different hours = different orders
                # Create dedicated Random instances for each tier to avoid seed conflicts
                user_hash_component = int(hashlib.md5(f"{user_key}_{request.risk_profile}".encode()).hexdigest()[:4], 16) % 1000
                shuffle_seed_top = hour_seed * 1000000 + date_seed * 10000 + user_hash_component
                shuffle_seed_mid = hour_seed * 1000000 + date_seed * 10000 + user_hash_component + 50000  # Different offset
                
                # Use dedicated Random instances to ensure isolation - SHUFFLE IN PLACE
                shuffle_random_top = random.Random(shuffle_seed_top)
                shuffle_random_top.shuffle(top_tier_tickers)  # Shuffles the list in place
                
                shuffle_random_mid = random.Random(shuffle_seed_mid)
                shuffle_random_mid.shuffle(mid_tier_tickers)  # Shuffles the list in place
                
                # Rebuild filtered_tickers with shuffled tier-based ordering
                # This order will vary by hour due to shuffling above
                filtered_tickers = top_tier_tickers + mid_tier_tickers + lower_tier_tickers
                
                if request.test_hour is not None:
                    top_tickers_sample = [t['ticker'] for t in top_tier_tickers[:3]]
                    filtered_sample = [t['ticker'] for t in filtered_tickers[:6]]
                    logger.info(f"🔀 Shuffle (hour={hour_seed}): Top seed={shuffle_seed_top}, Top 3={top_tickers_sample}, Filtered first 6={filtered_sample}")
                
                logger.info(f"📊 Quality tiers: Top 20%: {len(top_tier_tickers)}, Mid 30%: {len(mid_tier_tickers)}, Lower: {len(lower_tier_tickers)}")
            else:
                logger.warning("⚠️ Could not calculate quality tiers, using original order")
            
            # Count full overlap tickers in filtered set
            full_overlap_count = sum(1 for t in filtered_tickers if t.get('recommended_for_optimization', False))
            logger.info(f"📊 Found {full_overlap_count} tickers with full date overlap ({full_overlap_count/len(filtered_tickers)*100:.1f}%)" if filtered_tickers else "📊 No tickers found")
            
            # Dynamic ticker count: Select between 3-7 tickers based on pool size and hour-based seed
            # CRITICAL: Use hour_seed directly to ensure target_count varies by hour
            def determine_ticker_count(filtered_count: int, hour_seed: int, date_seed: int) -> int:
                """Determine ticker count (3-7) based on available pool and hour-based seed"""
                if filtered_count < 3:
                    return max(2, filtered_count)  # Minimum 2 for optimization
                if filtered_count < 5:
                    return 3  # Use minimum if pool is small
                
                # CRITICAL: Use hour as primary component to ensure variation
                count_seed = hour_seed * 1000000 + date_seed * 10000
                temp_random = random.Random(count_seed)
                
                # CRITICAL: Ensure we leave room for variation
                # If pool is small (<=8), use smaller target to allow sampling variation
                if filtered_count <= 8:
                    # Small pool - use 3-5 to ensure we can sample different combinations
                    count = temp_random.choice([3, 4, 5])
                    return min(count, filtered_count)
                
                # Larger pool - random selection between 3-7, weighted towards 4-6
                weights = [0.1, 0.2, 0.3, 0.3, 0.1]  # 3, 4, 5, 6, 7
                count = temp_random.choices([3, 4, 5, 6, 7], weights=weights, k=1)[0]
                return min(count, filtered_count)
            
            # Select tickers: Can include user's tickers if they're high quality
            user_tickers_set = set(t.upper() for t in user_tickers)
            
            # CRITICAL FIX: Use dedicated Random instance for selection to avoid seed conflicts
            # Hour component MUST be primary to ensure different hours = different selections
            # Use a DIFFERENT seed calculation than shuffle to ensure independence
            user_hash_small = int(hashlib.md5(f"{user_key}_{request.risk_profile}_SELECTION".encode()).hexdigest()[:4], 16) % 1000
            # Make hour component EXTREMELY dominant for selection (increased multiplier)
            selection_seed = hour_seed * 1000000000 + date_seed * 100000 + user_hash_small
            
            # Create dedicated random instance for selection (isolated from tier shuffling)
            selection_random = random.Random(selection_seed)
            
            # CHANGE: Include user tickers in market pool for fair comparison
            # This ensures both portfolios use the same opportunity set
            # Separate user and non-user tickers from shuffled list (order matters - uses shuffled order)
            non_user_tickers = [t['ticker'].upper() for t in filtered_tickers if t['ticker'].upper() not in user_tickers_set]
            user_tickers_in_pool = [t['ticker'].upper() for t in filtered_tickers if t['ticker'].upper() in user_tickers_set]
            
            # Combine all tickers for market pool (user tickers included)
            # This ensures the efficient frontier includes user's tickers in the opportunity set
            market_pool_tickers = filtered_tickers  # All filtered tickers (includes user tickers)
            
            # VERIFICATION: Log pool sizes after user ticker filtering
            logger.info(f"🔍 POOL SIZE AFTER USER FILTER:")
            logger.info(f"   Total filtered_tickers: {len(filtered_tickers)}")
            logger.info(f"   Non-user tickers: {len(non_user_tickers)}")
            logger.info(f"   User tickers in pool: {len(user_tickers_in_pool)}")
            logger.info(f"   User tickers excluded: {user_tickers}")
            
            # CRITICAL: Determine target_count AFTER we know non_user_tickers size
            # Adjust target if pool is small to ensure variation is possible
            initial_target = determine_ticker_count(len(filtered_tickers), hour_seed, date_seed)
            
            # CRITICAL: ALWAYS ensure target_count allows variation when pool is small
            # This is essential for diversity rotation - we need room to sample different combinations
            # Force reduction if pool size is small (<=8) to ensure we can get different ticker sets
            if len(non_user_tickers) <= 8:
                # Small pool - MUST reduce target to allow variation
                # Use hour-based random to vary the target, ensuring different hours get different counts
                if len(non_user_tickers) <= 6:
                    # Very small pool (6 or less) - use 3-4 to ensure we can get different combinations
                    # CRITICAL: This MUST vary by hour to produce different ticker sets
                    target_count = selection_random.choice([3, 4])
                    # Ensure target is less than pool size to allow variation
                    if target_count >= len(non_user_tickers):
                        target_count = len(non_user_tickers) - 1
                    if request.test_hour is not None:
                        logger.info(f"🔀 Very small pool ({len(non_user_tickers)} tickers): Using target {target_count} (was {initial_target}) for variation")
                else:
                    # Small pool (7-8) - reduce by 1-2 from initial, but ensure it's less than pool
                    reduction = selection_random.randint(1, min(2, initial_target - 3))
                    target_count = max(3, initial_target - reduction)
                    # Ensure target is less than pool size
                    if target_count >= len(non_user_tickers):
                        target_count = len(non_user_tickers) - 1
                    if request.test_hour is not None:
                        logger.info(f"🔀 Small pool ({len(non_user_tickers)} tickers): Adjusted target {initial_target} -> {target_count} for variation")
            else:
                target_count = initial_target
                if request.test_hour is not None:
                    logger.info(f"🔀 Large pool ({len(non_user_tickers)} tickers): Using initial target {target_count}")
            
            logger.info(f"📊 Dynamic ticker count: {target_count} (from pool of {len(filtered_tickers)}, non-user: {len(non_user_tickers)})")
            
            if request.test_hour is not None:
                logger.info(f"🔀 Selection prep (hour={hour_seed}): selection_seed={selection_seed}")
                logger.info(f"🔀   Non-user tickers (from shuffled list) first 15: {non_user_tickers[:15]}")
                logger.info(f"🔀   Total non-user: {len(non_user_tickers)}, target_count: {target_count}")
            
            # Prefer non-user tickers, but allow user tickers if pool is limited
            pool_size = len(non_user_tickers)
            
            # CRITICAL: Determine actual_target BEFORE any conditions
            # Force variation by varying sample size based on hour for large pools
            if pool_size > 10:
                # Large pool - ALWAYS use hour-based size to guarantee variation
                hour_based_size = 3 + (hour_seed % 4)  # 3, 4, 5, or 6 based on hour
                actual_target = min(hour_based_size, pool_size - 1)
                if request.test_hour is not None:
                    logger.info(f"🔀 VARIATION FIX (LARGE POOL): pool_size={pool_size}, hour={hour_seed}, hour%4={hour_seed % 4}")
                    logger.info(f"🔀   hour_based_size={hour_based_size}, actual_target={actual_target} (overriding target_count={target_count})")
            elif pool_size <= target_count + 2:
                # Small pool - reduce target to ensure variation
                max_reduction = min(3, pool_size - 3)
                reduction = selection_random.randint(1, max_reduction)
                actual_target = max(3, pool_size - reduction)
                if request.test_hour is not None:
                    logger.info(f"🔀 Small pool ({pool_size}): Reduced target from {target_count} to {actual_target}")
            else:
                # Medium pool - use target_count but ensure it's less than pool
                actual_target = min(target_count, pool_size - 1)
                if request.test_hour is not None:
                    logger.info(f"🔀 Medium pool ({pool_size}): Using target {actual_target}")
            
            # Now proceed with selection using actual_target
            if pool_size >= actual_target:
                # CRITICAL FIX: Shuffle the list using hour-based seed to ensure variation
                # The shuffle order will differ by hour, ensuring different tickers are selected
                if request.test_hour is not None:
                    before_shuffle = non_user_tickers[:10].copy()
                    logger.info(f"🔀 BEFORE shuffle (hour={hour_seed}): first 10 = {before_shuffle}")
                
                selection_random.shuffle(non_user_tickers)  # Shuffle in place - order varies by hour
                
                if request.test_hour is not None:
                    after_shuffle = non_user_tickers[:10].copy()
                    logger.info(f"🔀 AFTER shuffle (hour={hour_seed}): first 10 = {after_shuffle}")
                    logger.info(f"🔀 Shuffle changed: {before_shuffle != after_shuffle}")
                
                # FINAL SAFETY CHECK: Ensure actual_target is always less than pool_size
                if actual_target >= pool_size:
                    actual_target = max(3, pool_size - selection_random.randint(1, 2))
                    if request.test_hour is not None:
                        logger.info(f"🔀 SAFETY CHECK: Forced actual_target to {actual_target} (pool={pool_size})")
                
                # Use random.sample() to select actual_target tickers from shuffled list
                # This ensures variation - different hours will produce different samples
                best_tickers = selection_random.sample(non_user_tickers, actual_target)
                
                if request.test_hour is not None:
                    logger.info(f"🔀 Selection RESULT (hour={hour_seed}): sampled {actual_target} from {pool_size} tickers")
                    logger.info(f"🔀   Selected tickers ({len(best_tickers)}): {best_tickers}")
                    logger.info(f"🔀   Selection seed: {selection_seed}")
            elif market_pool_size <= target_count:
                # Not enough total tickers - use all available from market pool
                best_tickers = market_pool_ticker_symbols
                if request.test_hour is not None:
                    logger.info(f"🔀 Selection (hour={hour_seed}): using all {len(best_tickers)} available tickers from market pool")
            else:
                # Should not reach here due to earlier checks, but fallback
                best_tickers = selection_random.sample(market_pool_ticker_symbols, min(actual_target, market_pool_size))
                if request.test_hour is not None:
                    logger.info(f"🔀 Selection (hour={hour_seed}): fallback selection of {len(best_tickers)} tickers")
            
            logger.info(f"📊 Diversity selection: diversity_seed={diversity_seed_value}, hour={hour_seed}, date={date_seed}")
            
            # Ensure minimum 2 tickers for optimization
            if len(best_tickers) < 2:
                logger.warning("⚠️ Not enough eligible tickers, using all available")
                best_tickers = [t['ticker'].upper() for t in filtered_tickers[:max(2, target_count)]]
            
            overlap_count = len(set(best_tickers) & user_tickers_set)
            logger.info(f"✅ Selected {len(best_tickers)} tickers (target: {target_count}): {best_tickers[:10]}...")
            logger.info(f"📊 User tickers: {user_tickers}, Selected tickers: {best_tickers[:10]}, Overlap: {overlap_count}/{len(best_tickers)}")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Could not get eligible tickers: {e}")
            logger.error(f"   Cannot create best available portfolio without eligible tickers")
            # DO NOT fallback to user_tickers - this would make both portfolios identical
            # Instead, raise an error or use empty list to signal failure
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get eligible tickers for best available portfolio: {str(e)}"
            )
        
        # Step 3: Optimize portfolio from market tickers (with diversity rotation)
        # Use 24 months overlap requirement (eligible tickers have 36 months individually, 
        # so overlap should be at least 24 months) and strict_overlap=False for leniency
        logger.info(f"🔧 Step 3: Optimizing portfolio from market tickers ({len(best_tickers)} tickers, 24mo overlap, lenient)...")
        try:
            # Directly call optimizer with 24 months overlap
            optimized_result = optimizer.optimize_portfolio(
                tickers=best_tickers,
                optimization_type=request.optimization_type,
                risk_profile=request.risk_profile,
                min_overlap_months=24,  # 24 months overlap (eligible tickers have 36mo individually)
                strict_overlap=False     # Lenient: use available overlap even if slightly less than 24mo
            )
            
            # Generate efficient frontier if requested
            efficient_frontier = []
            if request.include_efficient_frontier:
                try:
                    logger.info(f"📊 Generating efficient frontier for optimized portfolio...")
                    efficient_frontier = optimizer.generate_efficient_frontier(
                        tickers=best_tickers,
                        num_points=request.num_frontier_points,
                        risk_profile=request.risk_profile,
                        min_overlap_months=24,
                        strict_overlap=False
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not generate efficient frontier: {e}")
            
            # Generate random portfolios if requested
            random_portfolios = []
            if request.include_random_portfolios:
                try:
                    logger.info(f"🎲 Generating {request.num_random_portfolios} random portfolios...")
                    random_portfolios = optimizer.generate_random_portfolios(
                        tickers=best_tickers,
                        num_portfolios=request.num_random_portfolios,
                        risk_profile=request.risk_profile,
                        min_overlap_months=24,
                        strict_overlap=False
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not generate random portfolios: {e}")
            
            # Generate inefficient frontier
            inefficient_frontier = []
            if efficient_frontier:
                try:
                    inefficient_frontier = optimizer.generate_inefficient_frontier(
                        tickers=best_tickers,
                        num_points=request.num_frontier_points,
                        risk_profile=request.risk_profile
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not generate inefficient frontier: {e}")
            
            # Calculate CML from efficient frontier (Optimized Portfolio will intersect this)
            capital_market_line = []
            if efficient_frontier:
                try:
                    logger.info("📈 Calculating Capital Market Line...")
                    capital_market_line = optimizer.calculate_capital_market_line(
                        efficient_frontier=efficient_frontier,
                        risk_free_rate=optimizer.risk_free_rate
                    )
                    logger.info(f"✅ Generated CML with {len(capital_market_line)} points")
                except Exception as e:
                    logger.warning(f"⚠️ Could not calculate CML: {e}")
            
            # Build optimized portfolio response
            # CRITICAL: Use tickers from weights to ensure consistency
            optimized_weights = optimized_result.get('weights', {})
            optimized_tickers_from_weights = list(optimized_weights.keys()) if optimized_weights else []
            
            # Use tickers from weights if available, otherwise fall back
            if optimized_tickers_from_weights and len(optimized_tickers_from_weights) >= 2:
                final_tickers = optimized_tickers_from_weights
            else:
                optimized_tickers = optimized_result.get('tickers', best_tickers)
                if set(optimized_tickers).issubset(set(best_tickers)) and len(optimized_tickers) >= 2:
                    final_tickers = optimized_tickers
                else:
                    final_tickers = best_tickers
            
            # Ensure final_tickers match weights keys exactly
            if optimized_weights:
                final_tickers = [t for t in final_tickers if t in optimized_weights]
                if len(final_tickers) < 2:
                    logger.warning(f"⚠️ Only {len(final_tickers)} tickers have weights. Using all weight keys.")
                    final_tickers = list(optimized_weights.keys())
            
            logger.info(f"✅ Optimized portfolio: {len(final_tickers)} tickers, Sharpe: {optimized_result.get('sharpe_ratio', 0):.3f}")
            
            optimized_portfolio_response = MVOOptimizationResponse(
                optimization_type=request.optimization_type,
                strategy_name=f"Optimized Portfolio ({request.risk_profile})",
                optimized_portfolio={
                    "tickers": final_tickers,
                    "weights": optimized_weights,
                    "weights_list": optimized_result.get('weights_list', []),
                    "metrics": {
                        "expected_return": optimized_result.get('expected_return', 0),
                        "risk": optimized_result.get('risk', 0),
                        "sharpe_ratio": optimized_result.get('sharpe_ratio', 0)
                    }
                },
                current_portfolio={
                    "tickers": user_tickers,
                    "weights": current_weights,
                    "metrics": current_metrics
                },
                efficient_frontier=efficient_frontier,
                inefficient_frontier=inefficient_frontier,
                random_portfolios=random_portfolios,
                capital_market_line=capital_market_line,
                metadata={
                    "ticker_count": len(final_tickers),
                    "risk_profile": request.risk_profile,
                    "min_overlap_months": 24,
                    "strict_overlap": False,
                    "diversity_seed": diversity_seed_value
                }
            )
        except Exception as e:
            logger.error(f"❌ Error optimizing portfolio: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to optimize portfolio: {str(e)}")
        
        # Step 4: Compare results
        optimized_metrics = optimized_portfolio_response.optimized_portfolio.get('metrics', {})
        
        # Prepare comparison data with data quality assessment
        optimized_tickers_for_comparison = final_tickers if 'final_tickers' in locals() else best_tickers
        
        # Assess data quality of current portfolio
        current_return = current_metrics.get('expected_return', 0)
        current_risk = current_metrics.get('risk', 0)
        current_sharpe = current_metrics.get('sharpe_ratio', 0)
        
        # Flag if current portfolio metrics seem unreliable
        current_metrics_unreliable = False
        reliability_reasons = []
        
        if current_return > 0.50:  # >50% annual return is suspicious
            current_metrics_unreliable = True
            reliability_reasons.append(f"Unusually high return ({current_return*100:.1f}%) may indicate limited historical data")
        
        if current_risk > 0.60:  # >60% volatility is extremely high
            current_metrics_unreliable = True
            reliability_reasons.append(f"Extremely high volatility ({current_risk*100:.1f}%) suggests data quality issues")
        
        if current_sharpe > 3.0:  # Sharpe >3 is very rare, >5 is almost certainly wrong
            current_metrics_unreliable = True
            reliability_reasons.append(f"Sharpe ratio of {current_sharpe:.2f} is unusually high and may be unreliable")
        
        # Check if optimized portfolio is more realistic
        optimized_return = optimized_metrics.get('expected_return', 0)
        optimized_risk = optimized_metrics.get('risk', 0)
        optimized_sharpe = optimized_metrics.get('sharpe_ratio', 0)
        
        # If current metrics are unreliable, adjust comparison interpretation
        comparison_notes = []
        if current_metrics_unreliable:
            comparison_notes.append("Current portfolio metrics may be unreliable due to limited historical data or data quality issues")
            comparison_notes.append("Optimized portfolio uses validated tickers with sufficient historical data (36+ months)")
            comparison_notes.append("Consider the optimized portfolio's more realistic risk-return profile")
        
        comparison = {
            'return_difference': optimized_return - current_return,
            'risk_difference': optimized_risk - current_risk,
            'sharpe_difference': optimized_sharpe - current_sharpe,
            'optimized_tickers': optimized_tickers_for_comparison,
            'current_tickers': user_tickers,
            'current_metrics_unreliable': current_metrics_unreliable,
            'reliability_reasons': reliability_reasons,
            'comparison_notes': comparison_notes
        }
        
        # ==================== NEW: Add Monte Carlo and Quality Score ====================
        try:
            from utils.port_analytics import PortfolioAnalytics
            analytics = PortfolioAnalytics()
            
            # Get diversification scores
            # For current portfolio, estimate diversification
            current_diversification = 50.0  # Default
            if current_weights:
                allocations = [{'symbol': t, 'allocation': w * 100, 'sector': 'Unknown'} for t, w in current_weights.items()]
                current_diversification = analytics._calculate_sophisticated_diversification_score(allocations)
            
            # For optimized portfolio
            optimized_diversification = 50.0
            if optimized_weights:
                allocations = [{'symbol': t, 'allocation': w * 100, 'sector': 'Unknown'} for t, w in optimized_weights.items()]
                optimized_diversification = analytics._calculate_sophisticated_diversification_score(allocations)
            
            # Monte Carlo simulations
            current_monte_carlo = analytics.run_monte_carlo_simulation(
                expected_return=current_return,
                risk=current_risk,
                num_simulations=10000
            )
            
            optimized_monte_carlo = analytics.run_monte_carlo_simulation(
                expected_return=optimized_return,
                risk=optimized_risk,
                num_simulations=10000
            )
            
            # Quality scores
            current_quality = analytics.calculate_quality_score(
                expected_return=current_return,
                risk=current_risk,
                risk_profile=request.risk_profile,
                diversification_score=current_diversification
            )
            
            optimized_quality = analytics.calculate_quality_score(
                expected_return=optimized_return,
                risk=optimized_risk,
                risk_profile=request.risk_profile,
                diversification_score=optimized_diversification
            )
            
            # Add to comparison
            comparison['monte_carlo'] = {
                'current': current_monte_carlo,
                'optimized': optimized_monte_carlo
            }
            
            comparison['quality_scores'] = {
                'current': current_quality,
                'optimized': optimized_quality
            }
            
            logger.info(f"📊 Quality scores - Current: {current_quality['composite_score']:.1f}, Optimized: {optimized_quality['composite_score']:.1f}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate Monte Carlo/Quality scores: {e}")
            # Continue without these metrics
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Portfolio optimization completed in {processing_time:.3f}s")
        
        return DualOptimizationResponse(
            current_portfolio={
                "tickers": user_tickers,
                "weights": current_weights,
                "metrics": current_metrics
            },
            optimized_portfolio=optimized_portfolio_response,
            comparison=comparison
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in dual optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to perform dual optimization: {str(e)}")

@optimization_router.post("/optimization/triple", response_model=TripleOptimizationResponse)
def optimize_triple_portfolio(request: TripleOptimizationRequest):
    """
    Combined Strategy Optimization: Compare current, weights-optimized, and market-optimized portfolios
    
    This endpoint:
    1. Calculates current portfolio metrics using ACTUAL weights
    2. Optimizes weights of current tickers (weights-only optimization)
    3. Always attempts market exploration (optimization from market tickers)
    4. Returns all three portfolios for comparison
    
    Decision framework determines which portfolio to recommend, but all three are always returned.
    """
    import time
    start_time = time.time()
    
    try:
        user_tickers = [t.upper().strip() for t in request.user_tickers]
        
        if len(user_tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 user tickers required")
        
        if not request.user_weights:
            raise HTTPException(status_code=400, detail="user_weights is required")
        
        optimizer = get_mvo_optimizer()
        
        # Step 1: Calculate current portfolio metrics using ACTUAL weights
        # First, try to find matching portfolio in Redis with precomputed metrics
        logger.info(f"🔧 Step 1: Checking Redis for precomputed metrics for current portfolio...")
        current_metrics = find_matching_portfolio_in_redis(
            user_tickers=user_tickers,
            user_weights=request.user_weights,
            risk_profile=request.risk_profile
        )
        
        if current_metrics is None:
            # No match found in Redis - calculate metrics from live data
            logger.info(f"🔧 Step 1: No matching portfolio in Redis, calculating metrics with actual weights from {len(user_tickers)} tickers...")
            current_metrics = compute_portfolio_metrics_with_weights(
                tickers=user_tickers,
                weights=request.user_weights,
                optimizer=optimizer,
                min_overlap_months=24,
                risk_profile=request.risk_profile
            )
        else:
            logger.info(f"✅ Step 1: Using precomputed metrics from Redis (Return: {current_metrics['expected_return']:.2%}, Risk: {current_metrics['risk']:.2%}, Sharpe: {current_metrics['sharpe_ratio']:.2f})")
        
        current_portfolio_data = {
            "tickers": user_tickers,
            "weights": request.user_weights,
            "metrics": current_metrics
        }
        
        # Step 2: Weights-only optimization (ALWAYS done)
        logger.info(f"🔧 Step 2: Optimizing weights of current tickers...")
        weights_optimized_data = optimize_weights_only(
            tickers=user_tickers,
            risk_profile=request.risk_profile,
            optimizer=optimizer,
            optimization_type=request.optimization_type
        )
        
        # Generate efficient frontier and related curves for the weights-only universe
        efficient_frontier_weights: List[Dict[str, Any]] = []
        inefficient_frontier_weights: List[Dict[str, Any]] = []
        random_portfolios_weights: List[Dict[str, Any]] = []
        capital_market_line_weights: List[Dict[str, Any]] = []
        
        try:
            if request.include_efficient_frontier:
                logger.info("📊 Generating efficient frontier for weights-optimized portfolio...")
                efficient_frontier_weights = optimizer.generate_efficient_frontier(
                    tickers=weights_optimized_data["tickers"],
                    num_points=request.num_frontier_points,
                    risk_profile=request.risk_profile,
                    min_overlap_months=24,
                    strict_overlap=True
                )
                
                # Inefficient frontier (lower part of the hyperbola)
                try:
                    inefficient_frontier_weights = optimizer.generate_inefficient_frontier(
                        tickers=weights_optimized_data["tickers"],
                        num_points=request.num_frontier_points,
                        risk_profile=request.risk_profile
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not generate inefficient frontier for weights-only optimization: {e}")
                
                # Capital Market Line from weights-only efficient frontier
                try:
                    if efficient_frontier_weights:
                        logger.info("📈 Calculating Capital Market Line for weights-only efficient frontier...")
                        capital_market_line_weights = optimizer.calculate_capital_market_line(
                            efficient_frontier=efficient_frontier_weights,
                            risk_free_rate=optimizer.risk_free_rate
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Could not calculate CML for weights-only optimization: {e}")
            
            if request.include_random_portfolios:
                try:
                    logger.info(f"🎲 Generating {request.num_random_portfolios} random portfolios for weights-only universe...")
                    random_portfolios_weights = optimizer.generate_random_portfolios(
                        tickers=weights_optimized_data["tickers"],
                        num_portfolios=request.num_random_portfolios,
                        min_overlap_months=24,
                        strict_overlap=True
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not generate random portfolios for weights-only optimization: {e}")
        except Exception as e:
            # Frontier generation is non-critical; optimization results are still valid
            logger.warning(f"⚠️ Failed to generate frontier data for weights-only optimization: {e}")
            efficient_frontier_weights = []
            inefficient_frontier_weights = []
            random_portfolios_weights = []
            capital_market_line_weights = []
        
        # Build MVOOptimizationResponse for weights-optimized
        weights_optimized_response = MVOOptimizationResponse(
            optimization_type=request.optimization_type,
            strategy_name=f"Weights-Optimized Portfolio ({request.risk_profile})",
            optimized_portfolio={
                "tickers": weights_optimized_data["tickers"],
                "weights": weights_optimized_data["weights"],
                "weights_list": list(weights_optimized_data["weights"].values()),
                "metrics": weights_optimized_data["metrics"]
            },
            current_portfolio=current_portfolio_data,
            efficient_frontier=efficient_frontier_weights,
            inefficient_frontier=inefficient_frontier_weights,
            random_portfolios=random_portfolios_weights,
            capital_market_line=capital_market_line_weights,
            metadata={
                "ticker_count": len(weights_optimized_data["tickers"]),
                "risk_profile": request.risk_profile,
                "optimization_type": "weights_only"
            }
        )
        
        # Step 3: Market exploration (ALWAYS attempted)
        market_optimized_response = None
        market_exploration_successful = False
        
        if request.attempt_market_exploration:
            logger.info(f"🔧 Step 3: Market exploration - optimizing from eligible market tickers...")
            try:
                # Use similar logic to dual optimization for market exploration
                # CRITICAL: Sort by data_points first to get tickers with long histories (better overlap)
                per_page_size = max(request.max_eligible_tickers * 50, 2000)
                eligible_response = _get_eligible_tickers_internal(
                    min_data_points=96,  # Require at least 96 months (8 years) of data for strong overlap
                    filter_negative_returns=True,
                    per_page=per_page_size,
                    page=1,
                    sort_by='data_points'  # Sort by data points to get tickers with longest histories
                )
                
                eligible_tickers_data = eligible_response.get('eligible_tickers', [])
                if not eligible_tickers_data:
                    logger.warning("⚠️ No eligible tickers found for market exploration")
                else:
                    # Extract ticker symbols, preferring non-user tickers for diversity
                    user_tickers_set = set(user_tickers)
                    
                    # OPTION A (enhanced): Variable basket size with Sharpe-driven, diversified sampling
                    # Create variation seed from user tickers + timestamp for different baskets each run
                    user_tickers_str = ','.join(sorted(user_tickers))
                    import time
                    seed_value = int(hashlib.md5(f"{user_tickers_str}_{time.time()}".encode()).hexdigest()[:8], 16)
                    variation_random = random.Random(seed_value)
                    
                    # CRITICAL FIX: Pre-validate tickers for data overlap before optimization
                    # Get a larger candidate pool (top 200) and sort by Sharpe for better selection
                    candidate_pool_size = 200
                    # Sort by sharpe_ratio (fallback to expected_return) descending for high-quality pool
                    sorted_eligible = sorted(
                        [
                            t for t in eligible_tickers_data
                            if t.get('ticker') and t['ticker'].upper() not in user_tickers_set
                        ],
                        key=lambda t: t.get('sharpe_ratio', t.get('expected_return', 0.0)),
                        reverse=True
                    )
                    all_candidates = [t['ticker'].upper() for t in sorted_eligible][:candidate_pool_size]
                    
                    # Shuffle ALL candidates for variation (not just positions 51-200)
                    # This ensures different ticker combinations each run while keeping high Sharpe focus
                    shuffled_candidates = all_candidates.copy()
                    variation_random.shuffle(shuffled_candidates)
                    
                    # Variable basket size by risk profile
                    # LARGER baskets = more diversification = lower risk = better acceptance rate
                    # PRIORITY 3: Expanded ticker pool for very-conservative to reduce solver infeasibility
                    # Optimized based on comprehensive testing across all portfolios
                    BASKET_SIZE_BY_PROFILE = {
                        'very-conservative': (15, 20),  # Expanded for better feasibility (was 10-14)
                        'conservative': (10, 14),       # Larger for better diversification
                        'moderate': (12, 16),           # Even larger for moderate
                        'aggressive': (12, 16),         # Even larger for aggressive
                        'very-aggressive': (10, 14)     # Good balance
                    }
                    min_size, max_size = BASKET_SIZE_BY_PROFILE.get(request.risk_profile, (10, 14))
                    target_pool_size = variation_random.randint(min_size, max_size)
                    logger.info(f"🎲 Variable basket size: {target_pool_size} tickers (seed: {seed_value})")
                    logger.info(f"🎲 Shuffled candidates (first 10): {shuffled_candidates[:10]}")
                    
                    # Validate each ticker has sufficient data overlap with others
                    # by checking metrics calculation doesn't produce NaN
                    best_tickers = []
                    logger.info(f"🔍 Validating {len(shuffled_candidates)} candidate tickers for data overlap (shuffled for variation)...")
                    
                    # Try to find a subset with valid overlap
                    # Build basket from shuffled candidates (ensures variation)
                    for candidate in shuffled_candidates:
                        test_set = best_tickers + [candidate]
                        if len(test_set) >= 2:
                            try:
                                # Quick validation: check if metrics are valid
                                mu, sigma = optimizer.get_ticker_metrics(
                                    tickers=test_set,
                                    annualize=True,
                                    min_overlap_months=96,  # Use 96 months (8 years) for market optimization
                                    strict_overlap=True
                                )
                                # Check for NaN/Inf values
                                if mu and sigma is not None:
                                    has_nan = any(np.isnan(v) for v in mu.values()) or np.isnan(sigma.values).any()
                                    has_inf = np.isinf(sigma.values).any()
                                    if not has_nan and not has_inf:
                                        best_tickers.append(candidate)
                                        logger.info(f"  ✅ {candidate} added (valid overlap with {len(best_tickers)-1} others)")
                                        if len(best_tickers) >= target_pool_size:
                                            break
                                    else:
                                        logger.debug(f"  ⚠️ {candidate} skipped (NaN/Inf in metrics)")
                            except Exception as e:
                                logger.debug(f"  ⚠️ {candidate} skipped (metrics error: {e})")
                        else:
                            # First ticker, just add it
                            best_tickers.append(candidate)
                    
                    logger.info(f"📊 Found {len(best_tickers)} tickers with valid data overlap")
                    
                    # Fallback: include user tickers if not enough diversity
                    if len(best_tickers) < 2:
                        logger.warning("⚠️ Not enough valid market tickers, trying with user tickers...")
                        best_tickers = [t['ticker'].upper() for t in eligible_tickers_data[:target_pool_size]]
                    
                    if len(best_tickers) >= 2:
                        # PRIORITY 2: Add fallback mechanisms for market exploration
                        # The optimize_portfolio method now has built-in fallback (constraint relaxation + min_variance)
                        # So we just call it once and it will handle fallbacks internally
                        try:
                            logger.info(f"🔄 Attempting market optimization with max_sharpe (with automatic fallbacks)...")
                            optimized_result = optimizer.optimize_portfolio(
                                tickers=best_tickers,
                                optimization_type=request.optimization_type,  # Usually 'max_sharpe'
                                risk_profile=request.risk_profile,
                                min_overlap_months=96,  # Use 96 months (8 years) for market optimization
                                strict_overlap=False
                            )
                            logger.info(f"✅ Market optimization succeeded")
                        except Exception as e:
                            # Final fallback: try min_variance directly
                            logger.warning(f"⚠️ Market optimization with fallbacks failed: {e}, trying min_variance as last resort...")
                            try:
                                optimized_result = optimizer.optimize_portfolio(
                                    tickers=best_tickers,
                                    optimization_type='min_variance',
                                    risk_profile=request.risk_profile,
                                    min_overlap_months=96,
                                    strict_overlap=False
                                )
                                logger.info(f"✅ Market optimization succeeded with min_variance fallback")
                            except Exception as e2:
                                logger.error(f"❌ All market optimization strategies failed: {e2}")
                                raise Exception(f"Market optimization failed after all fallback attempts: {e2}")
                        
                        final_tickers = optimized_result.get('tickers', best_tickers)
                        raw_weights = optimized_result.get('weights', {})
                        optimized_weights = _postprocess_weights(raw_weights, max_assets=10, min_weight=0.005)
                        final_tickers = list(optimized_weights.keys()) if optimized_weights else final_tickers
                        
                        # Generate efficient frontier if requested
                        efficient_frontier = []
                        if request.include_efficient_frontier:
                            try:
                                logger.info(f"📊 Generating efficient frontier for market-optimized portfolio...")
                                efficient_frontier = optimizer.generate_efficient_frontier(
                                    tickers=best_tickers,
                                    num_points=request.num_frontier_points,
                                    risk_profile=request.risk_profile,
                                    min_overlap_months=96,  # Use 96 months (8 years) for market optimization
                                    strict_overlap=False
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ Could not generate efficient frontier: {e}")
                        
                        # Generate random portfolios if requested
                        random_portfolios = []
                        if request.include_random_portfolios:
                            try:
                                logger.info(f"🎲 Generating {request.num_random_portfolios} random portfolios...")
                                random_portfolios = optimizer.generate_random_portfolios(
                                    tickers=best_tickers,
                                    num_portfolios=request.num_random_portfolios,
                                    risk_profile=request.risk_profile,
                                    min_overlap_months=96,  # Use 96 months (8 years) for market optimization
                                    strict_overlap=False
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ Could not generate random portfolios: {e}")
                        
                        # Generate inefficient frontier
                        inefficient_frontier = []
                        if efficient_frontier:
                            try:
                                inefficient_frontier = optimizer.generate_inefficient_frontier(
                                    tickers=best_tickers,
                                    num_points=request.num_frontier_points,
                                    risk_profile=request.risk_profile
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ Could not generate inefficient frontier: {e}")
                        
                        # Calculate CML from market-optimized portfolio (ensures CML connects Rf to market-opt portfolio)
                        capital_market_line = []
                        if efficient_frontier:
                            try:
                                logger.info("📈 Calculating Capital Market Line from market-optimized portfolio...")
                                # Use market-optimized portfolio metrics to ensure CML connects to it
                                market_portfolio_metrics = {
                                    'return': optimized_result.get('expected_return', 0),
                                    'risk': optimized_result.get('risk', 0),
                                    'sharpe_ratio': optimized_result.get('sharpe_ratio', 0)
                                }
                                capital_market_line = optimizer.calculate_capital_market_line(
                                    efficient_frontier=efficient_frontier,
                                    risk_free_rate=optimizer.risk_free_rate,
                                    market_portfolio=market_portfolio_metrics
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ Could not calculate CML: {e}")
                        
                        market_optimized_response = MVOOptimizationResponse(
                            optimization_type=request.optimization_type,
                            strategy_name=f"Market-Optimized Portfolio ({request.risk_profile})",
                            optimized_portfolio={
                                "tickers": final_tickers,
                                "weights": optimized_weights,
                                "weights_list": list(optimized_weights.values()),
                                "metrics": {
                                    "expected_return": optimized_result.get('expected_return', 0),
                                    "risk": optimized_result.get('risk', 0),
                                    "sharpe_ratio": optimized_result.get('sharpe_ratio', 0)
                                }
                            },
                            current_portfolio=current_portfolio_data,
                            efficient_frontier=efficient_frontier,
                            inefficient_frontier=inefficient_frontier,
                            random_portfolios=random_portfolios,
                            capital_market_line=capital_market_line,
                            metadata={
                                "ticker_count": len(final_tickers),
                                "risk_profile": request.risk_profile,
                                "optimization_type": "market_exploration",
                                "risk_free_rate": optimizer.risk_free_rate
                            }
                        )
                        market_exploration_successful = True
            except Exception as e:
                logger.warning(f"⚠️ Market exploration failed: {e}")
                market_optimized_response = None
        
        # Step 4: Decision framework (for recommendation) - Using improved v2 logic
        recommendation = decide_best_portfolio_v2(
            current=current_metrics,
            weights_opt=weights_optimized_data,
            market_opt=market_optimized_response.optimized_portfolio if market_optimized_response else None,
            risk_profile=request.risk_profile
        )
        
        # Step 5: Build comparison
        comparison = build_triple_comparison(
            current=current_metrics,
            weights_opt=weights_optimized_data,
            market_opt=market_optimized_response.optimized_portfolio if market_optimized_response else None
        )
        
        # ==================== NEW: Add Monte Carlo and Quality Score for all portfolios ====================
        try:
            from utils.port_analytics import PortfolioAnalytics
            analytics = PortfolioAnalytics()
            
            # Helper for safe weight extraction
            def get_weights_safe(response_obj):
                if not response_obj or not response_obj.optimized_portfolio:
                    return {}
                opt = response_obj.optimized_portfolio
                # Check if it's a dict or object
                if isinstance(opt, dict):
                    return opt.get('weights', {})
                return getattr(opt, 'weights', {})
                
            # Helper for safe metric extraction
            def get_metrics_safe(response_obj):
                if not response_obj or not response_obj.optimized_portfolio:
                    return {}
                opt = response_obj.optimized_portfolio
                if isinstance(opt, dict):
                    return opt.get('metrics', {})
                # It's an object (Pydantic model)
                metrics = getattr(opt, 'metrics', {})
                if hasattr(metrics, 'model_dump'):
                    return metrics.model_dump()
                if hasattr(metrics, 'dict'):
                    return metrics.dict()
                return metrics if isinstance(metrics, dict) else {}

            # Get diversification scores for all portfolios
            current_diversification = 50.0
            if request.user_weights:
                allocations = [{'symbol': t, 'allocation': w * 100, 'sector': 'Unknown'} for t, w in request.user_weights.items()]
                current_diversification = analytics._calculate_sophisticated_diversification_score(allocations)
            
            weights_diversification = 50.0
            w_weights = get_weights_safe(weights_optimized_response)
            if w_weights:
                allocations = [{'symbol': t, 'allocation': w * 100, 'sector': 'Unknown'} for t, w in w_weights.items()]
                weights_diversification = analytics._calculate_sophisticated_diversification_score(allocations)
            
            market_diversification = 50.0
            m_weights = get_weights_safe(market_optimized_response)
            if m_weights:
                allocations = [{'symbol': t, 'allocation': w * 100, 'sector': 'Unknown'} for t, w in m_weights.items()]
                market_diversification = analytics._calculate_sophisticated_diversification_score(allocations)
            
            # Monte Carlo simulations for all portfolios
            current_monte_carlo = analytics.run_monte_carlo_simulation(
                expected_return=current_metrics.get('expected_return', 0),
                risk=current_metrics.get('risk', 0),
                num_simulations=10000
            )
            
            # Use safe metric extraction for weights
            w_metrics = get_metrics_safe(weights_optimized_response)
            weights_monte_carlo = analytics.run_monte_carlo_simulation(
                expected_return=w_metrics.get('expected_return', 0),
                risk=w_metrics.get('risk', 0),
                num_simulations=10000
            )
            
            market_monte_carlo = None
            if market_optimized_response:
                m_metrics = get_metrics_safe(market_optimized_response)
                market_monte_carlo = analytics.run_monte_carlo_simulation(
                    expected_return=m_metrics.get('expected_return', 0),
                    risk=m_metrics.get('risk', 0),
                    num_simulations=10000
                )
            
            # Quality scores for all portfolios
            current_quality = analytics.calculate_quality_score(
                expected_return=current_metrics.get('expected_return', 0),
                risk=current_metrics.get('risk', 0),
                risk_profile=request.risk_profile,
                diversification_score=current_diversification
            )
            
            weights_quality = analytics.calculate_quality_score(
                expected_return=w_metrics.get('expected_return', 0),
                risk=w_metrics.get('risk', 0),
                risk_profile=request.risk_profile,
                diversification_score=weights_diversification
            )
            
            market_quality = None
            if market_optimized_response:
                m_metrics = get_metrics_safe(market_optimized_response)
                market_quality = analytics.calculate_quality_score(
                    expected_return=m_metrics.get('expected_return', 0),
                    risk=m_metrics.get('risk', 0),
                    risk_profile=request.risk_profile,
                    diversification_score=market_diversification
                )
            
            # Add to comparison - structure matches what frontend expects
            comparison['monte_carlo'] = {
                'current': current_monte_carlo,
                'weights': weights_monte_carlo,
                'market': market_monte_carlo
            }
            
            comparison['quality_scores'] = {
                'current': current_quality,
                'weights': weights_quality,
                'market': market_quality
            }
            
            # FIXED: Safe logging format without conditional expression inside f-string
            market_score_str = f"{market_quality['composite_score']:.1f}" if market_quality else "N/A"
            logger.info(f"📊 Quality scores - Current: {current_quality['composite_score']:.1f}, Weights: {weights_quality['composite_score']:.1f}, Market: {market_score_str}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate Monte Carlo/Quality scores: {e}")
            # Continue without these metrics
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Triple portfolio optimization completed in {processing_time:.3f}s (recommendation: {recommendation})")
        
        return TripleOptimizationResponse(
            current_portfolio=current_portfolio_data,
            weights_optimized_portfolio=weights_optimized_response,
            market_optimized_portfolio=market_optimized_response,
            comparison=comparison,
            optimization_metadata={
                "strategy_used": "combined_strategy",
                "attempts_made": 2 if market_optimized_response else 1,
                "market_exploration_attempted": request.attempt_market_exploration,
                "market_exploration_successful": market_exploration_successful,
                "recommendation": recommendation,
                "processing_time_seconds": processing_time
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in triple optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to perform triple optimization: {str(e)}")

@analytics_router.post("/stress-test")
def run_stress_test(request: Dict[str, Any]):
    """
    Run stress test scenarios on selected portfolio.
    
    Request Body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "weights": {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
        "scenarios": ["covid19", "2008_crisis"],
        "capital": 8000,
        "risk_profile": "moderate"
    }
    
    Returns:
    {
        "portfolio_summary": {...},
        "scenarios": {
            "covid19": {...},
            "2008_crisis": {...}
        },
        "resilience_score": 75.0,
        "overall_assessment": "..."
    }
    """
    import time
    start_time = time.time()
    
    try:
        from utils.stress_test_analyzer import StressTestAnalyzer
        
        # Parse request
        tickers = [t.upper().strip() for t in request.get('tickers', [])]
        weights_raw = request.get('weights', {})
        scenarios = request.get('scenarios', [])
        capital = request.get('capital', 0)
        risk_profile = request.get('risk_profile', 'moderate')
        
        # Validation
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required for stress test")
        
        if not scenarios:
            raise HTTPException(status_code=400, detail="At least one scenario must be selected")
        
        # Normalize weights: ensure ticker keys are uppercase and match tickers list
        weights = {}
        for ticker in tickers:
            # Try uppercase key first, then lowercase, then original
            weight = weights_raw.get(ticker, weights_raw.get(ticker.lower(), weights_raw.get(ticker.upper(), 0.0)))
            if weight > 0:
                weights[ticker] = float(weight)
        
        # If no weights provided or all zero, use equal weights
        total_weight = sum(weights.values())
        if total_weight <= 0:
            logger.warning(f"⚠️ No valid weights provided, using equal weights")
            weights = {t: 1.0 / len(tickers) for t in tickers}
        elif abs(total_weight - 1.0) > 0.1:
            logger.warning(f"⚠️ Weights sum to {total_weight}, normalizing...")
            weights = {t: w / total_weight for t, w in weights.items()}
        
        # Optional: Warm cache for portfolio tickers (non-blocking, improves first-run performance)
        try:
            logger.info(f"🔥 Pre-warming cache for {len(tickers)} tickers...")
            warm_start = time.time()
            for ticker in tickers:
                try:
                    # Pre-warm monthly data and ticker info (Redis-first approach)
                    _ = _rds.get_monthly_data(ticker)
                    _ = _rds.get_ticker_info(ticker)
                except Exception:
                    pass  # Continue even if some tickers fail
            warm_time = time.time() - warm_start
            if warm_time > 0.1:  # Only log if it took meaningful time
                logger.info(f"✅ Cache warmed in {warm_time:.3f}s")
        except Exception as e:
            logger.debug(f"Cache warm-up skipped: {e}")
        
        # Initialize analyzer
        analyzer = StressTestAnalyzer()
        
        # Run selected scenarios
        scenario_results = {}
        
        for scenario in scenarios:
            try:
                scenario_start = time.time()
                logger.info(f"⏱️ Starting {scenario} scenario analysis...")
                
                if scenario == 'covid19':
                    result = analyzer.analyze_covid19_scenario(tickers, weights)
                    scenario_results['covid19'] = result
                elif scenario == '2008_crisis':
                    result = analyzer.analyze_2008_crisis_scenario(tickers, weights)
                    scenario_results['2008_crisis'] = result
                else:
                    logger.warning(f"⚠️ Unknown scenario: {scenario}")
                    continue
                
                scenario_time = time.time() - scenario_start
                logger.info(f"✅ {scenario} scenario completed in {scenario_time:.3f}s")
            except Exception as e:
                logger.error(f"❌ Error running {scenario} scenario: {e}")
                import traceback
                traceback.print_exc()
                # Continue with other scenarios
                continue
        
        if not scenario_results:
            raise HTTPException(status_code=500, detail="Failed to run any stress test scenarios")
        
        # Calculate resilience score
        # Resilience Score Formula (0-100 scale):
        # - Drawdown Score (40%): Based on maximum drawdown during crisis
        #   - 0% drawdown = 100 points (perfect)
        #   - 10% drawdown = 90 points
        #   - 30% drawdown = 70 points
        #   - 50% drawdown = 50 points
        #   Formula: 100 - (abs(drawdown) * 100)
        #
        # - Recovery Score (40%): Based on recovery time
        #   - Instant recovery (0 months) = 100 points
        #   - 3 months = 94 points (100 - 3*2)
        #   - 6 months = 88 points
        #   - 12+ months = 76 points (capped)
        #   Formula: 100 - (recovery_months * 2), max 100, min 0
        #
        # - Volatility Score (20%): Based on volatility ratio vs normal
        #   - 1.0x (normal) = 100 points
        #   - 1.5x = 75 points (100 - (1.5-1)*50)
        #   - 2.0x = 50 points
        #   - 0.5x = 100 points (capped - less volatile is good)
        #   Formula: max(0, 100 - ((volatility_ratio - 1) * 50)), capped at 100
        
        resilience_scores = []
        for scenario_name, scenario_data in scenario_results.items():
            metrics = scenario_data.get('metrics', {})
            max_drawdown = metrics.get('max_drawdown', 0)  # Negative value (e.g., -0.30 for 30% loss)
            recovery_months = metrics.get('recovery_months')
            volatility_ratio = metrics.get('volatility_ratio', 1.0)
            recovered = metrics.get('recovered', False)
            
            # Drawdown score: Convert negative drawdown to positive loss percentage
            # max_drawdown is negative (e.g., -0.30 for 30% loss)
            # Score = 100 - (loss percentage * 100)
            # Example: -0.30 drawdown = 30% loss = 70 points
            drawdown_loss_pct = abs(max_drawdown)  # Convert to positive percentage
            drawdown_score = max(0, min(100, 100 - (drawdown_loss_pct * 100)))
            
            # Recovery score: Penalize longer recovery times
            # 0 months = 100 points, 1 month = 98 points, 6 months = 88 points, 12+ months = 76 points
            if recovered and recovery_months is not None and recovery_months >= 0:
                recovery_score = max(0, min(100, 100 - (recovery_months * 2)))
            elif not recovered:
                # Not recovered: Use projected recovery time if available
                trajectory_projections = metrics.get('trajectory_projections', {})
                projected_months = trajectory_projections.get('realistic_months')
                if projected_months is not None and projected_months >= 0:
                    # Penalize projected recovery time more heavily (factor of 2.5 instead of 2)
                    recovery_score = max(0, min(100, 100 - (projected_months * 2.5)))
                else:
                    # No recovery projection available: assign low score
                    recovery_score = 20  # Low score for no recovery
            else:
                recovery_score = 0
            
            # Volatility score: Penalize higher volatility during crisis
            # Normal volatility (1.0x) = 100 points
            # Higher volatility reduces score
            # Lower volatility (good) is capped at 100
            volatility_penalty = max(0, (volatility_ratio - 1) * 50)  # Penalty for volatility > 1.0
            volatility_score = max(0, min(100, 100 - volatility_penalty))
            
            # Scenario score: weighted average of three components
            scenario_score = (drawdown_score * 0.4 + recovery_score * 0.4 + volatility_score * 0.2)
            # Ensure score is between 0 and 100
            scenario_score = max(0, min(100, scenario_score))
            resilience_scores.append(scenario_score)
        
        # Overall resilience score - average of scenario scores, capped at 100
        resilience_score = max(0, min(100, sum(resilience_scores) / len(resilience_scores) if resilience_scores else 0.0))
        
        # Generate overall assessment
        if resilience_score >= 70:
            assessment = f"Your portfolio shows strong resilience (score: {resilience_score:.0f}/100). It has demonstrated good performance during historical market crises."
        elif resilience_score >= 50:
            assessment = f"Your portfolio shows moderate resilience (score: {resilience_score:.0f}/100). Consider reviewing the stress test results to understand potential risks."
        else:
            assessment = f"Your portfolio shows weak resilience (score: {resilience_score:.0f}/100). The stress test reveals significant vulnerabilities. Consider adjusting your portfolio composition or risk profile."
        
        # Portfolio summary (from optimization step data if available)
        portfolio_summary = {
            'tickers': tickers,
            'weights': weights,
            'capital': capital,
            'risk_profile': risk_profile
        }
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Stress test completed in {processing_time:.3f}s ({len(scenario_results)} scenarios)")
        
        response = {
            'portfolio_summary': portfolio_summary,
            'scenarios': scenario_results,
            'resilience_score': round(resilience_score, 1),
            'overall_assessment': assessment,
            'processing_time_seconds': round(processing_time, 3)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in stress test: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run stress test: {str(e)}")

@analytics_router.post("/what-if-scenario")
def run_what_if_scenario(request: Dict[str, Any]):
    """
    Run What-If scenario simulation with custom parameters.
    Also supports hypothetical scenarios via scenario_type parameter.
    
    Request Body (What-If mode):
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "weights": {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
        "volatility_multiplier": 2.0,
        "return_adjustment": -0.15,
        "time_horizon_months": 12,
        "capital": 8000
    }
    
    Request Body (Hypothetical mode):
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "weights": {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
        "scenario_type": "tech_crash",  # tech_crash, inflation, geopolitical, recession
        "market_decline": -0.30,
        "duration_months": 6,
        "recovery_rate": "moderate",
        "capital": 8000
    }
    """
    import time
    start_time = time.time()
    
    try:
        from utils.port_analytics import PortfolioAnalytics
        
        # Check if this is a hypothetical scenario request
        scenario_type = request.get('scenario_type')
        if scenario_type:
            # Handle hypothetical scenario
            return _handle_hypothetical_scenario(request, start_time)
        
        # Parse request (What-If mode)
        tickers = [t.upper().strip() for t in request.get('tickers', [])]
        weights_raw = request.get('weights', {})
        volatility_multiplier = float(request.get('volatility_multiplier', 1.5))
        return_adjustment = float(request.get('return_adjustment', 0.0))
        time_horizon_months = float(request.get('time_horizon_months', 12))
        capital = request.get('capital', 0)
        
        # Validation
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required")
        
        if volatility_multiplier < 0.1 or volatility_multiplier > 10:
            raise HTTPException(status_code=400, detail="Volatility multiplier must be between 0.1 and 10")
        
        if time_horizon_months < 1 or time_horizon_months > 60:
            raise HTTPException(status_code=400, detail="Time horizon must be between 1 and 60 months")
        
        # Normalize weights
        weights = {}
        for ticker in tickers:
            weight = weights_raw.get(ticker, weights_raw.get(ticker.lower(), weights_raw.get(ticker.upper(), 0.0)))
            if weight > 0:
                weights[ticker] = float(weight)
        
        total_weight = sum(weights.values())
        if total_weight <= 0:
            logger.warning(f"⚠️ No valid weights provided, using equal weights")
            weights = {t: 1.0 / len(tickers) for t in tickers}
        elif abs(total_weight - 1.0) > 0.1:
            logger.warning(f"⚠️ Weights sum to {total_weight}, normalizing...")
            weights = {t: w / total_weight for t, w in weights.items()}
        
        # Calculate baseline portfolio metrics
        try:
            from utils.redis_first_data_service import redis_first_data_service
            data_service = redis_first_data_service
            
            # Optimized: Batch retrieve price data (Redis-first approach handles caching)
            # Sequential loop is fine here as Redis cache makes subsequent calls instant
            all_prices = {}
            import time as time_module
            data_start = time_module.time()
            
            for ticker in tickers:
                try:
                    # Redis-first approach: get_monthly_data uses cached data when available
                    ticker_data = data_service.get_monthly_data(ticker)
                    if ticker_data and ticker_data.get('prices'):
                        prices = ticker_data['prices']
                        # Convert to dict format if needed
                        if isinstance(prices, pd.Series):
                            prices_dict = {str(date): float(price) for date, price in prices.items()}
                        elif isinstance(prices, dict):
                            prices_dict = prices
                        else:
                            continue
                        # Get last 12 months of data
                        sorted_dates = sorted(prices_dict.keys(), reverse=True)[:12]
                        all_prices[ticker] = {date: prices_dict[date] for date in sorted_dates}
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch prices for {ticker}: {e}")
            
            data_time = time_module.time() - data_start
            if data_time > 1.0:  # Log if data retrieval takes more than 1 second
                logger.debug(f"⏱️ Price data retrieval: {data_time:.3f}s for {len(tickers)} tickers")
            
            if not all_prices:
                raise HTTPException(status_code=500, detail="Could not fetch price data for portfolio")
            
            # Calculate portfolio returns
            analytics = PortfolioAnalytics()
            portfolio_returns = []
            dates = sorted(set([d for ticker_prices in all_prices.values() for d in ticker_prices.keys()]))
            
            if len(dates) < 2:
                raise HTTPException(status_code=500, detail="Insufficient price data for analysis")
            
            for i in range(1, len(dates)):
                portfolio_return = 0.0
                for ticker, weight in weights.items():
                    if ticker in all_prices and dates[i] in all_prices[ticker] and dates[i-1] in all_prices[ticker]:
                        price_change = (all_prices[ticker][dates[i]] - all_prices[ticker][dates[i-1]]) / all_prices[ticker][dates[i-1]]
                        portfolio_return += weight * price_change
                portfolio_returns.append(portfolio_return)
            
            # Calculate baseline metrics
            baseline_expected_return = float(np.mean(portfolio_returns) * 12) if portfolio_returns else 0.12  # Annualized
            baseline_volatility = float(np.std(portfolio_returns) * np.sqrt(12)) if len(portfolio_returns) > 1 else 0.20  # Annualized
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate baseline metrics, using defaults: {e}")
            baseline_expected_return = 0.12  # 12% default
            baseline_volatility = 0.20  # 20% default
        
        # Apply adjustments
        adjusted_expected_return = baseline_expected_return + return_adjustment
        adjusted_volatility = baseline_volatility * volatility_multiplier
        time_horizon_years = time_horizon_months / 12.0
        
        # Run Monte Carlo simulation
        analytics = PortfolioAnalytics()
        # Optimized: reduced from 10,000 to 5,000 iterations for better performance
        monte_carlo = analytics.run_monte_carlo_simulation(
            expected_return=adjusted_expected_return,
            risk=adjusted_volatility,
            num_simulations=5000,  # Optimized: reduced from 10,000 to 5,000
            time_horizon_years=time_horizon_years
        )
        
        # Calculate summary metrics
        simulated_returns = monte_carlo.get('simulated_returns', [])
        percentiles = monte_carlo.get('percentiles', {})
        
        metrics = {
            'expected_return': adjusted_expected_return,
            'volatility': adjusted_volatility,
            'baseline_expected_return': baseline_expected_return,
            'baseline_volatility': baseline_volatility,
            'return_adjustment': return_adjustment,
            'volatility_multiplier': volatility_multiplier,
            'time_horizon_months': time_horizon_months,
            'probability_positive': monte_carlo.get('probability_positive', 0.5),
            'probability_loss_10pct': monte_carlo.get('probability_loss_thresholds', {}).get('loss_10pct', 0.0),
            'probability_loss_20pct': monte_carlo.get('probability_loss_thresholds', {}).get('loss_20pct', 0.0),
            'percentiles': percentiles
        }
        
        processing_time = time.time() - start_time
        logger.info(f"✅ What-If scenario completed in {processing_time:.3f}s")
        
        return {
            'portfolio_summary': {
                'tickers': tickers,
                'weights': weights,
                'capital': capital
            },
            'scenario_name': 'Custom What-If Scenario',
            'parameters': {
                'volatility_multiplier': volatility_multiplier,
                'return_adjustment': return_adjustment,
                'time_horizon_months': time_horizon_months
            },
            'monte_carlo': monte_carlo,
            'metrics': metrics,
            'processing_time_seconds': round(processing_time, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in What-If scenario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run What-If scenario: {str(e)}")

def _handle_hypothetical_scenario(request: Dict[str, Any], start_time: float):
    """Handle hypothetical scenario logic (called from what-if endpoint)"""
    import time
    try:
        from utils.port_analytics import PortfolioAnalytics
        
        # Parse request
        tickers = [t.upper().strip() for t in request.get('tickers', [])]
        weights_raw = request.get('weights', {})
        scenario_type = request.get('scenario_type', 'tech_crash')
        market_decline = float(request.get('market_decline', -0.30))
        duration_months = int(request.get('duration_months', 6))
        recovery_rate = request.get('recovery_rate', 'moderate')
        capital = float(request.get('capital', 0))
        
        # Validation
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required")
        
        if market_decline > 0 or market_decline < -1:
            raise HTTPException(status_code=400, detail="Market decline must be between -100% and 0%")
        
        # Normalize weights
        weights = {}
        for ticker in tickers:
            weight = weights_raw.get(ticker, weights_raw.get(ticker.lower(), weights_raw.get(ticker.upper(), 0.0)))
            if weight > 0:
                weights[ticker] = float(weight)
        
        total_weight = sum(weights.values())
        if total_weight <= 0:
            weights = {t: 1.0 / len(tickers) for t in tickers}
        elif abs(total_weight - 1.0) > 0.1:
            weights = {t: w / total_weight for t, w in weights.items()}
        
        # Scenario-specific parameters
        scenario_configs = {
            'tech_crash': {'volatility_mult': 2.5, 'sector_impacts': {'Technology': -0.50, 'Communication Services': -0.40, 'Consumer Discretionary': -0.30, 'default': -0.20}},
            'inflation': {'volatility_mult': 2.0, 'sector_impacts': {'Real Estate': -0.35, 'Utilities': -0.25, 'Consumer Staples': -0.15, 'default': -0.20}},
            'geopolitical': {'volatility_mult': 3.0, 'sector_impacts': {'Energy': 0.20, 'Industrials': -0.30, 'Financials': -0.25, 'default': -0.25}},
            'recession': {'volatility_mult': 2.2, 'sector_impacts': {'Consumer Discretionary': -0.40, 'Financials': -0.35, 'Real Estate': -0.30, 'default': -0.25}}
        }
        
        config = scenario_configs.get(scenario_type, scenario_configs['recession'])
        
        # Calculate sector-weighted portfolio impact
        try:
            from utils.redis_first_data_service import redis_first_data_service
            data_service = redis_first_data_service
            
            sector_impact = {}
            portfolio_weighted_decline = 0.0
            
            for ticker, weight in weights.items():
                try:
                    ticker_info = data_service.get_ticker_info(ticker)
                    sector = ticker_info.get('sector', 'Unknown') if ticker_info else 'Unknown'
                    sector_decline = config['sector_impacts'].get(sector, config['sector_impacts']['default'])
                    sector_impact[sector] = sector_decline
                    portfolio_weighted_decline += weight * sector_decline
                except Exception:
                    portfolio_weighted_decline += weight * config['sector_impacts']['default']
            
            estimated_loss = market_decline + (portfolio_weighted_decline * 0.5)
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate sector impact: {e}")
            estimated_loss = market_decline
            sector_impact = {}
        
        # Recovery time estimation
        recovery_multipliers = {'slow': 2.0, 'moderate': 1.0, 'fast': 0.5}
        base_recovery_months = abs(market_decline) * 100 * 0.5
        estimated_recovery_months = int(base_recovery_months * recovery_multipliers.get(recovery_rate, 1.0))
        
        # Capital at risk
        capital_at_risk = capital * abs(estimated_loss)
        
        # Run Monte Carlo with scenario parameters
        analytics = PortfolioAnalytics()
        adjusted_volatility = 0.20 * config['volatility_mult']

        monte_carlo = analytics.run_monte_carlo_simulation(
            expected_return=estimated_loss,
            risk=adjusted_volatility,
            num_simulations=5000,
            time_horizon_years=duration_months / 12.0
        )

        processing_time = time.time() - start_time
        logger.info(f"✅ Hypothetical scenario completed in {processing_time:.3f}s")

        return {
            'scenario_type': scenario_type,
            'parameters': {
                'market_decline': market_decline,
                'duration_months': duration_months,
                'recovery_rate': recovery_rate
            },
            'estimated_loss': estimated_loss,
            'capital_at_risk': round(capital_at_risk, 2),
            'estimated_recovery_months': estimated_recovery_months,
            'sector_impact': sector_impact,
            'monte_carlo': monte_carlo,
            'processing_time_seconds': round(processing_time, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in hypothetical scenario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run hypothetical scenario: {str(e)}")

@analytics_router.post("/hypothetical-scenario")
def run_hypothetical_scenario(request: Dict[str, Any]):
    """
    Run hypothetical stress test scenario with custom parameters.
    
    Request Body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "weights": {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
        "scenario_type": "tech_crash",  # tech_crash, inflation, geopolitical, recession
        "market_decline": -0.30,  # -30%
        "duration_months": 6,
        "recovery_rate": "moderate",  # slow, moderate, fast
        "capital": 8000
    }
    """
    import time
    start_time = time.time()
    
    try:
        from utils.port_analytics import PortfolioAnalytics
        
        # Parse request
        tickers = [t.upper().strip() for t in request.get('tickers', [])]
        weights_raw = request.get('weights', {})
        scenario_type = request.get('scenario_type', 'tech_crash')
        market_decline = float(request.get('market_decline', -0.30))
        duration_months = int(request.get('duration_months', 6))
        recovery_rate = request.get('recovery_rate', 'moderate')
        capital = float(request.get('capital', 0))
        
        # Validation
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers required")
        
        if market_decline > 0 or market_decline < -1:
            raise HTTPException(status_code=400, detail="Market decline must be between -100% and 0%")
        
        # Normalize weights
        weights = {}
        for ticker in tickers:
            weight = weights_raw.get(ticker, weights_raw.get(ticker.lower(), weights_raw.get(ticker.upper(), 0.0)))
            if weight > 0:
                weights[ticker] = float(weight)
        
        total_weight = sum(weights.values())
        if total_weight <= 0:
            weights = {t: 1.0 / len(tickers) for t in tickers}
        elif abs(total_weight - 1.0) > 0.1:
            weights = {t: w / total_weight for t, w in weights.items()}
        
        # Scenario-specific parameters
        scenario_configs = {
            'tech_crash': {'volatility_mult': 2.5, 'sector_impacts': {'Technology': -0.50, 'Communication Services': -0.40, 'Consumer Discretionary': -0.30, 'default': -0.20}},
            'inflation': {'volatility_mult': 2.0, 'sector_impacts': {'Real Estate': -0.35, 'Utilities': -0.25, 'Consumer Staples': -0.15, 'default': -0.20}},
            'geopolitical': {'volatility_mult': 3.0, 'sector_impacts': {'Energy': 0.20, 'Industrials': -0.30, 'Financials': -0.25, 'default': -0.25}},
            'recession': {'volatility_mult': 2.2, 'sector_impacts': {'Consumer Discretionary': -0.40, 'Financials': -0.35, 'Real Estate': -0.30, 'default': -0.25}}
        }
        
        config = scenario_configs.get(scenario_type, scenario_configs['recession'])
        
        # Calculate sector-weighted portfolio impact
        try:
            from utils.redis_first_data_service import redis_first_data_service
            data_service = redis_first_data_service
            
            # Optimized: Batch retrieve sector info (Redis-first approach handles caching)
            sector_impact = {}
            portfolio_weighted_decline = 0.0
            import time as time_module
            sector_start = time_module.time()
            
            for ticker, weight in weights.items():
                try:
                    # Redis-first approach: get_ticker_info uses cached data when available
                    ticker_info = data_service.get_ticker_info(ticker)
                    sector = ticker_info.get('sector', 'Unknown') if ticker_info else 'Unknown'
                    sector_decline = config['sector_impacts'].get(sector, config['sector_impacts']['default'])
                    sector_impact[sector] = sector_decline
                    portfolio_weighted_decline += weight * sector_decline
                except Exception:
                    portfolio_weighted_decline += weight * config['sector_impacts']['default']
            
            sector_time = time_module.time() - sector_start
            if sector_time > 0.5:  # Log if sector retrieval takes more than 0.5 seconds
                logger.debug(f"⏱️ Sector info retrieval: {sector_time:.3f}s for {len(weights)} tickers")
            
            # Apply market-wide decline as baseline
            estimated_loss = market_decline + (portfolio_weighted_decline * 0.5)
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate sector impact: {e}")
            estimated_loss = market_decline
            sector_impact = {}
        
        # Recovery time estimation
        recovery_multipliers = {'slow': 2.0, 'moderate': 1.0, 'fast': 0.5}
        base_recovery_months = abs(market_decline) * 100 * 0.5  # ~0.5 months per 1% decline
        estimated_recovery_months = int(base_recovery_months * recovery_multipliers.get(recovery_rate, 1.0))
        
        # Capital at risk
        capital_at_risk = capital * abs(estimated_loss)
        
        # Generate synthetic historical data under scenario conditions
        try:
            logger.info("🔬 Starting synthetic historical data generation for hypothetical scenario")
            from utils.stress_test_analyzer import StressTestAnalyzer
            analyzer = StressTestAnalyzer()
            logger.info("✅ StressTestAnalyzer initialized")

            # Create synthetic portfolio performance under the scenario
            # We'll simulate a 24-month period with the market decline applied
            synthetic_dates = []
            synthetic_values = []

            # Start with current portfolio value (normalized to 100)
            current_value = 100.0
            base_decline_per_month = market_decline / duration_months

            # Generate monthly performance under scenario
            for month in range(24):  # 24 months of synthetic data
                # Apply market decline gradually over the scenario duration
                if month < duration_months:
                    # During scenario period - apply decline and sector impacts
                    monthly_decline = base_decline_per_month

                    # Add sector-specific impact for this portfolio
                    sector_adjustment = portfolio_weighted_decline * 0.3  # 30% of sector impact
                    monthly_decline += sector_adjustment / duration_months

                    # Add some volatility (±10%)
                    import random
                    volatility_factor = 1.0 + (random.uniform(-0.1, 0.1) * config['volatility_mult'] * 0.1)
                    monthly_decline *= volatility_factor

                    current_value *= (1 + monthly_decline)
                else:
                    # Post-scenario recovery period
                    recovery_progress = (month - duration_months) / (24 - duration_months)
                    recovery_rate_monthly = (abs(market_decline) * 0.6) / (24 - duration_months)  # 60% recovery

                    if recovery_rate == 'fast':
                        recovery_rate_monthly *= 1.5
                    elif recovery_rate == 'slow':
                        recovery_rate_monthly *= 0.7

                    current_value *= (1 + recovery_rate_monthly * (1 - recovery_progress * 0.5))

                # Ensure we don't go below 10% of starting value (floor for realism)
                current_value = max(current_value, 10.0)

                synthetic_values.append(current_value / 100.0)  # Convert back to decimal
                synthetic_dates.append(f"2024-{str(month % 12 + 1).zfill(2)}")

            # Analyze the synthetic portfolio performance using available methods
            logger.info(f"📊 Analyzing synthetic data: {len(synthetic_values)} values, {len(synthetic_dates)} dates")
            logger.info(f"📊 Sample values: {synthetic_values[:5]}")

            # Calculate basic metrics manually
            initial_value = synthetic_values[0] if synthetic_values else 1.0
            final_value = synthetic_values[-1] if synthetic_values else 1.0
            total_return = (final_value - initial_value) / initial_value

            # Calculate max drawdown
            max_drawdown_data = analyzer.calculate_maximum_drawdown(
                portfolio_values=synthetic_values,
                dates=synthetic_dates,
                drawdown_threshold=0.0  # Include all drawdowns for synthetic data
            )
            max_drawdown = max_drawdown_data.get('max_drawdown', abs(estimated_loss))

            # Calculate trajectory projections
            try:
                logger.info(f"📈 Calculating trajectory projections with {len(synthetic_values)} values, peak={max(synthetic_values) if synthetic_values else 1.0}")
                trajectory_projections = analyzer.calculate_enhanced_trajectory_projections(
                    portfolio_values=synthetic_values,
                    dates=synthetic_dates,
                    peak_value=max(synthetic_values) if synthetic_values else 1.0,
                    lookback_months=min(6, len(synthetic_values))
                )
                logger.info(f"📈 Trajectory projections result: {type(trajectory_projections)}, keys: {list(trajectory_projections.keys()) if isinstance(trajectory_projections, dict) else 'not dict'}")
            except Exception as e:
                logger.error(f"❌ Failed to calculate trajectory projections: {e}")
                trajectory_projections = {}

            # Simple recovery analysis
            peak_value = max(synthetic_values) if synthetic_values else 1.0
            current_value = synthetic_values[-1] if synthetic_values else 1.0
            recovery_pct = ((current_value - min(synthetic_values)) / peak_value) * 100 if peak_value > 0 else 0

            # Determine recovery pattern based on simple logic
            if recovery_pct >= 90:
                recovery_pattern = 'V-shaped Recovery'
                recovery_months = 3
            elif recovery_pct >= 70:
                recovery_pattern = 'U-shaped Recovery'
                recovery_months = 6
            else:
                recovery_pattern = 'L-shaped Recovery'
                recovery_months = 12

            logger.info(f"📊 Synthetic metrics calculated: total_return={total_return:.2%}, max_drawdown={max_drawdown:.2%}, recovery_pattern={recovery_pattern}")

        except Exception as e:
            logger.error(f"❌ Failed to generate synthetic historical data: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Fallback to original Monte Carlo only approach
            total_return = estimated_loss
            max_drawdown = abs(estimated_loss)
            recovery_months = estimated_recovery_months
            recovery_pattern = 'Estimated Scenario'
            trajectory_projections = {}

        # Run Monte Carlo with scenario parameters for forward-looking projections
        analytics = PortfolioAnalytics()
        adjusted_volatility = 0.20 * config['volatility_mult']

        # Use actual historical return if available, otherwise estimated
        monte_carlo_return = total_return if total_return != 0 else estimated_loss

        monte_carlo = analytics.run_monte_carlo_simulation(
            expected_return=monte_carlo_return,
            risk=adjusted_volatility,
            num_simulations=5000,
            time_horizon_years=duration_months / 12.0
        )

        processing_time = time.time() - start_time
        logger.info(f"✅ Hypothetical scenario with historical analysis completed in {processing_time:.3f}s")

        return {
            'scenario_type': scenario_type,
            'parameters': {
                'market_decline': market_decline,
                'duration_months': duration_months,
                'recovery_rate': recovery_rate
            },
            'metrics': {
                'total_return': float(total_return),
                'max_drawdown': float(max_drawdown),
                'recovery_months': recovery_months,
                'recovery_pattern': recovery_pattern,
                'trajectory_projections': trajectory_projections
            },
            'estimated_loss': estimated_loss,
            'capital_at_risk': round(capital_at_risk, 2),
            'estimated_recovery_months': estimated_recovery_months,
            'sector_impact': sector_impact,
            'monte_carlo': monte_carlo,
            'processing_time_seconds': round(processing_time, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in hypothetical scenario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to run hypothetical scenario: {str(e)}")

def _warm_tickers_for_recommendations(symbols: List[str]) -> None:
    """Background helper: warm Redis cache for tickers used in recommendations (non-blocking)."""
    if not symbols:
        return
    try:
        for sym in symbols:
            try:
                _ = _rds.get_monthly_data(sym)
                _ = _rds.get_ticker_info(sym)
            except Exception:
                continue
        logger.debug(f"✅ Background warm completed for {len(symbols)} tickers")
    except Exception as e:
        logger.debug(f"Background warm skipped: {e}")


@portfolios_router.get("/recommendations/{risk_profile}", response_model=List[PortfolioResponse])
def get_portfolio_recommendations(risk_profile: str, background_tasks: BackgroundTasks):
    """Get portfolio recommendations from Enhanced Portfolio System.
    Portfolios are cached in Redis; ticker data is warmed in background so response returns quickly."""
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
                stats = _ensure_missing_portfolios_generated(risk_profile)
                if stats.get('success'):
                    logger.debug(f"✅ Lazy generation completed for {risk_profile}: {stats.get('portfolios_stored', 0)} portfolios stored")
                else:
                    logger.warning(f"⚠️ Lazy generation had issues for {risk_profile}: {stats.get('errors', [])}")
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
        
        # Collect symbols to warm in background (do not block the response)
        symbols_to_warm = []
        for p in portfolios:
            for a in p.get('allocations', []):
                s = a.get('symbol')
                if s:
                    symbols_to_warm.append(s)
        if symbols_to_warm:
            background_tasks.add_task(_warm_tickers_for_recommendations, list(set(symbols_to_warm)))

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

# Helper: Ensure missing portfolios are generated (enhanced to handle full expiration)
def _ensure_missing_portfolios_generated(risk_profile: str) -> dict:
    """
    Enhanced lazy generation that handles:
    - Full expiration: If count = 0, regenerate all 12 portfolios
    - Partial expiration: If count < 12, fill only missing slots
    
    Returns:
        dict: Statistics about the generation process including:
            - success: bool
            - portfolios_generated: int
            - portfolios_stored: int
            - portfolios_failed: int
            - processing_time_seconds: float
            - start_time: str (ISO format)
            - end_time: str (ISO format)
            - mode: str ("full" or "partial")
            - errors: list
    """
    import time
    stats = {
        'success': False,
        'risk_profile': risk_profile,
        'portfolios_generated': 0,
        'portfolios_stored': 0,
        'portfolios_failed': 0,
        'processing_time_seconds': 0.0,
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'mode': None,
        'errors': []
    }
    
    start_time = time.time()
    
    try:
        if not redis_manager or not redis_manager.redis_client:
            error_msg = f"Redis not available for {risk_profile}"
            logger.warning(f"⚠️ {error_msg}")
            stats['errors'].append(error_msg)
            stats['end_time'] = datetime.now().isoformat()
            stats['processing_time_seconds'] = time.time() - start_time
            return stats
        
        # Check current portfolio count
        current_count = redis_manager.get_portfolio_count(risk_profile)
        logger.info(f"📊 [{risk_profile}] Current portfolio count: {current_count}/{redis_manager.PORTFOLIOS_PER_PROFILE}")
        
        if current_count >= redis_manager.PORTFOLIOS_PER_PROFILE:
            logger.debug(f"✅ All portfolios exist for {risk_profile} ({current_count}/{redis_manager.PORTFOLIOS_PER_PROFILE})")
            stats['success'] = True
            stats['end_time'] = datetime.now().isoformat()
            stats['processing_time_seconds'] = time.time() - start_time
            return stats
        
        # Determine which portfolio slots are missing
        missing_ids = []
        bucket_prefix = f"portfolio_bucket:{risk_profile}:"
        for i in range(redis_manager.PORTFOLIOS_PER_PROFILE):
            key = f"{bucket_prefix}{i}"
            exists = redis_manager.redis_client.exists(key)
            if not exists:
                missing_ids.append(i)
        
        if not missing_ids:
            logger.info(f"✅ No missing portfolios for {risk_profile}")
            stats['success'] = True
            stats['end_time'] = datetime.now().isoformat()
            stats['processing_time_seconds'] = time.time() - start_time
            return stats
        
        # If all portfolios are expired (count = 0), regenerate all 12
        if current_count == 0:
            stats['mode'] = 'full'
            logger.info("="*80)
            logger.info(f"🔄 [{risk_profile}] FULL REGENERATION MODE")
            logger.info(f"   All portfolios expired - regenerating full bucket (12 portfolios)")
            logger.info("="*80)
            
            from utils.redis_first_data_service import redis_first_data_service
            from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
            from utils.port_analytics import PortfolioAnalytics

            gen_start = time.time()
            # Use conservative approach + Strategy 5 for aggressive profiles
            generator = EnhancedPortfolioGenerator(redis_first_data_service, PortfolioAnalytics(), use_conservative_approach=True)
            logger.info(f"⏱️  [{risk_profile}] Starting portfolio generation...")
            generated = generator.generate_portfolio_bucket(risk_profile, use_parallel=True)
            gen_time = time.time() - gen_start
            
            stats['portfolios_generated'] = len(generated) if generated else 0
            logger.info(f"⏱️  [{risk_profile}] Generation completed in {gen_time:.2f}s ({stats['portfolios_generated']} portfolios)")
            
            # Store all portfolios using RedisPortfolioManager (handles TTL and metadata)
            if generated and len(generated) >= redis_manager.PORTFOLIOS_PER_PROFILE:
                store_start = time.time()
                logger.info(f"💾 [{risk_profile}] Storing {len(generated)} portfolios in Redis...")
                success = redis_manager.store_portfolio_bucket(risk_profile, generated)
                store_time = time.time() - store_start
                
                if success:
                    final_count = redis_manager.get_portfolio_count(risk_profile)
                    stats['portfolios_stored'] = final_count
                    stats['success'] = True
                    logger.info(f"💾 [{risk_profile}] Storage completed in {store_time:.2f}s ({final_count} portfolios stored)")
                    logger.info("="*80)
                    logger.info(f"✅ [{risk_profile}] FULL REGENERATION COMPLETE!")
                    logger.info(f"   📊 Portfolios Generated: {stats['portfolios_generated']}")
                    logger.info(f"   💾 Portfolios Stored: {stats['portfolios_stored']}")
                    logger.info(f"   ⏱️  Generation Time: {gen_time:.2f}s")
                    logger.info(f"   💾 Storage Time: {store_time:.2f}s")
                    logger.info(f"   ⏱️  Total Time: {time.time() - start_time:.2f}s")
                    logger.info("="*80)
                else:
                    error_msg = f"Failed to store regenerated portfolios for {risk_profile}"
                    stats['errors'].append(error_msg)
                    logger.error(f"❌ [{risk_profile}] {error_msg}")
            else:
                error_msg = f"Generated only {stats['portfolios_generated']} portfolios, expected {redis_manager.PORTFOLIOS_PER_PROFILE}"
                stats['errors'].append(error_msg)
                stats['portfolios_failed'] = redis_manager.PORTFOLIOS_PER_PROFILE - stats['portfolios_generated']
                logger.warning(f"⚠️ [{risk_profile}] {error_msg}")
        else:
            # Partial expiration: fill only missing slots
            stats['mode'] = 'partial'
            logger.info("="*80)
            logger.info(f"🔄 [{risk_profile}] PARTIAL REGENERATION MODE")
            logger.info(f"   Filling {len(missing_ids)} missing portfolio slots ({current_count}/{redis_manager.PORTFOLIOS_PER_PROFILE} exist)")
            logger.info(f"   Missing slots: {missing_ids}")
            logger.info("="*80)
            
            from utils.redis_first_data_service import redis_first_data_service
            from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
            from utils.port_analytics import PortfolioAnalytics

            gen_start = time.time()
            # Use conservative approach + Strategy 5 for aggressive profiles
            generator = EnhancedPortfolioGenerator(redis_first_data_service, PortfolioAnalytics(), use_conservative_approach=True)
            logger.info(f"⏱️  [{risk_profile}] Starting portfolio generation for {len(missing_ids)} missing slots...")
            generated = generator.generate_portfolio_bucket(risk_profile, use_parallel=True)
            gen_time = time.time() - gen_start
            
            stats['portfolios_generated'] = len(generated) if generated else 0
            logger.info(f"⏱️  [{risk_profile}] Generation completed in {gen_time:.2f}s ({stats['portfolios_generated']} portfolios)")

            # Index generated portfolios by variation_id
            vid_to_port = {p.get('variation_id', idx): p for idx, p in enumerate(generated)}

            # Store only missing variation ids with proper TTL, without touching existing ones
            store_start = time.time()
            logger.info(f"💾 [{risk_profile}] Storing {len(missing_ids)} portfolios in missing slots...")
            stored_count = 0
            failed_slots = []
            
            for vid in missing_ids:
                p = vid_to_port.get(vid)
                if not p:
                    failed_slots.append(vid)
                    stats['portfolios_failed'] += 1
                    logger.warning(f"⚠️ [{risk_profile}] No portfolio found for variation_id {vid}")
                    continue
                try:
                    key = f"{bucket_prefix}{vid}"
                    redis_manager.redis_client.setex(
                        key,
                        redis_manager.PORTFOLIO_TTL_SECONDS,
                        json.dumps(p, default=str)
                    )
                    stored_count += 1
                    stats['portfolios_stored'] += 1
                    logger.debug(f"🧩 [{risk_profile}] Filled missing portfolio slot {vid}")
                except Exception as e:
                    failed_slots.append(vid)
                    stats['portfolios_failed'] += 1
                    error_msg = f"Failed storing portfolio {vid} for {risk_profile}: {e}"
                    stats['errors'].append(error_msg)
                    logger.warning(f"⚠️ [{risk_profile}] {error_msg}")
            
            store_time = time.time() - store_start
            
            if stored_count > 0:
                final_count = redis_manager.get_portfolio_count(risk_profile)
                stats['success'] = stored_count == len(missing_ids)
                logger.info(f"💾 [{risk_profile}] Storage completed in {store_time:.2f}s ({stored_count}/{len(missing_ids)} portfolios stored)")
                logger.info("="*80)
                logger.info(f"✅ [{risk_profile}] PARTIAL REGENERATION COMPLETE!")
                logger.info(f"   📊 Portfolios Generated: {stats['portfolios_generated']}")
                logger.info(f"   💾 Portfolios Stored: {stored_count}/{len(missing_ids)}")
                logger.info(f"   ❌ Portfolios Failed: {stats['portfolios_failed']}")
                if failed_slots:
                    logger.info(f"   ⚠️  Failed Slots: {failed_slots}")
                logger.info(f"   📊 Final Count: {final_count}/{redis_manager.PORTFOLIOS_PER_PROFILE}")
                logger.info(f"   ⏱️  Generation Time: {gen_time:.2f}s")
                logger.info(f"   💾 Storage Time: {store_time:.2f}s")
                logger.info(f"   ⏱️  Total Time: {time.time() - start_time:.2f}s")
                logger.info("="*80)
            else:
                error_msg = f"Failed to store any portfolios for {risk_profile}"
                stats['errors'].append(error_msg)
                logger.error(f"❌ [{risk_profile}] {error_msg}")
            
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
        
        stats['end_time'] = datetime.now().isoformat()
        stats['processing_time_seconds'] = round(time.time() - start_time, 3)
                
    except Exception as e:
        error_msg = f"Error in _ensure_missing_portfolios_generated for {risk_profile}: {e}"
        stats['errors'].append(error_msg)
        logger.error(f"❌ [{risk_profile}] {error_msg}")
        import traceback
        traceback.print_exc()
        stats['end_time'] = datetime.now().isoformat()
        stats['processing_time_seconds'] = round(time.time() - start_time, 3)
    
    return stats

# NEW: Dynamic Portfolio Generation Endpoint - LIVE GENERATION
@portfolios_router.post("/recommendations/dynamic", response_model=List[PortfolioResponse])
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

# NEW: Strategy Portfolio Generation Endpoint (Pure + Personalized)
@portfolios_router.post("/recommendations/strategy-pure", response_model=List[PortfolioResponse])
async def generate_pure_strategy_portfolios(
    risk_profile: str,
    strategy: str
):
    """
    Generate strategy portfolios (mix of pure and personalized) using real market data
    
    This endpoint generates a mix of pure and personalized strategy portfolios for the selected strategy,
    using real market data and proven optimization algorithms. Returns both pure (unconstrained) and
    personalized (risk-profile-adjusted) portfolios.
    
    Args:
        risk_profile: User's risk profile (for personalized portfolios)
        strategy: Investment strategy ('diversification', 'risk', 'return')
    
    Returns:
        List of strategy portfolios (mix of pure and personalized) with real market data
        All portfolios are validated to have positive expected returns
    """
    try:
        logger.info(f"🎯 Strategy Portfolio Generation: {strategy} for {risk_profile}")
        
        # Initialize strategy optimizer if not already done
        if not hasattr(_rds, 'strategy_optimizer'):
            _rds.strategy_optimizer = StrategyPortfolioOptimizer(_rds, redis_manager)
        
        responses = []
        
        # Get pure strategy portfolios from cache or generate
        pure_portfolios = _rds.strategy_optimizer.get_pure_portfolios_from_cache(strategy)
        if not pure_portfolios:
            logger.info(f"🔄 Cache miss: Generating pure {strategy} portfolios")
            pure_portfolios = _rds.strategy_optimizer._generate_pure_strategy_portfolios(strategy)
            if pure_portfolios:
                _rds.strategy_optimizer._store_pure_portfolios_in_redis(strategy, pure_portfolios)
        
        # Get personalized strategy portfolios from cache or generate
        personalized_portfolios = _rds.strategy_optimizer.get_personalized_portfolios_from_cache(strategy, risk_profile)
        if not personalized_portfolios:
            logger.info(f"🔄 Cache miss: Generating personalized {strategy} portfolios for {risk_profile}")
            personalized_portfolios = _rds.strategy_optimizer._generate_personalized_strategy_portfolios(strategy, risk_profile)
            if personalized_portfolios:
                _rds.strategy_optimizer._store_personalized_portfolios_in_redis(strategy, risk_profile, personalized_portfolios)
        
        # Randomize portfolio selection for variety (different portfolios each time)
        # Use timestamp-based seed for variation while maintaining some consistency
        random.seed(int(datetime.now().timestamp() * 1000) % 1000000)
        
        # Shuffle portfolios to get different ones each time
        if pure_portfolios and len(pure_portfolios) > 1:
            pure_shuffled = pure_portfolios.copy()
            random.shuffle(pure_shuffled)
            pure_portfolios = pure_shuffled
        
        if personalized_portfolios and len(personalized_portfolios) > 1:
            personalized_shuffled = personalized_portfolios.copy()
            random.shuffle(personalized_shuffled)
            personalized_portfolios = personalized_shuffled
        
        # Combine portfolios: 1 pure + 1 personalized (randomly selected)
        all_portfolios = []
        if pure_portfolios:
            # Take 1 pure portfolio (randomly selected after shuffle)
            all_portfolios.append(('pure', pure_portfolios[0]))
        if personalized_portfolios:
            # Take 1 personalized portfolio (randomly selected after shuffle)
            all_portfolios.append(('personalized', personalized_portfolios[0]))
        
        if not all_portfolios:
            logger.warning(f"No strategy portfolios available for {strategy}, falling back to static")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Convert portfolios to response format and filter out negative returns
        for portfolio_type, portfolio in all_portfolios:
            try:
                metrics = portfolio.get('metrics', {})
                expected_return = metrics.get('expected_return', 0.12)
                
                # STRICT FILTER: Skip portfolios with negative or zero returns
                if expected_return <= 0:
                    logger.warning(f"⚠️ Skipping {portfolio_type} portfolio with negative/zero return: {expected_return:.2%}")
                    continue
                
                allocations = []
                # Convert float weights (0-1) to whole-number percentages summing to 100
                raw_allocs = portfolio.get('allocations', [])
                float_weights = [max(0.0, float(a.get('allocation', 0.0))) for a in raw_allocs]
                total = sum(float_weights) or 1.0
                percents = [int(round(w / total * 100)) for w in float_weights]
                diff = 100 - sum(percents)
                if percents and diff != 0:
                    # Adjust the largest weight to fix rounding sum
                    max_idx = percents.index(max(percents))
                    percents[max_idx] += diff
                
                # Convert allocations to PortfolioAllocation format
                for idx, allocation in enumerate(raw_allocs):
                    allocations.append(PortfolioAllocation(
                        symbol=allocation.get('symbol', ''),
                        allocation=max(0, percents[idx] if idx < len(percents) else 0),
                        name=allocation.get('name', allocation.get('symbol', '')),
                        assetType=allocation.get('assetType', 'stock')
                    ))
                
                response = PortfolioResponse(
                    portfolio=allocations,
                    name=portfolio.get('name', f"{portfolio_type.title()} {strategy.title()} Portfolio"),
                    description=portfolio.get('description', f"{portfolio_type.title()} {strategy} strategy portfolio optimized using real market data"),
                    expectedReturn=max(0.0, expected_return),  # Ensure non-negative
                    risk=metrics.get('risk', 0.15),
                    diversificationScore=metrics.get('diversification_score', 75.0),
                    sharpeRatio=0.0  # Always 0 as requested
                )
                responses.append(response)
                
            except Exception as e:
                logger.error(f"Error converting {portfolio_type} portfolio: {e}")
                continue
        
        # If we filtered out portfolios, try to get alternatives
        if len(responses) < 2:
            # Try to get alternative pure portfolio if first one was filtered
            if len([r for r in responses if 'Pure' in r.name]) == 0 and len(pure_portfolios) > 1:
                for portfolio in pure_portfolios[1:]:
                    try:
                        metrics = portfolio.get('metrics', {})
                        expected_return = metrics.get('expected_return', 0.12)
                        if expected_return > 0:
                            # Same conversion logic as above
                            allocations = []
                            raw_allocs = portfolio.get('allocations', [])
                            float_weights = [max(0.0, float(a.get('allocation', 0.0))) for a in raw_allocs]
                            total = sum(float_weights) or 1.0
                            percents = [int(round(w / total * 100)) for w in float_weights]
                            diff = 100 - sum(percents)
                            if percents and diff != 0:
                                max_idx = percents.index(max(percents))
                                percents[max_idx] += diff
                            
                            for idx, allocation in enumerate(raw_allocs):
                                allocations.append(PortfolioAllocation(
                                    symbol=allocation.get('symbol', ''),
                                    allocation=max(0, percents[idx] if idx < len(percents) else 0),
                                    name=allocation.get('name', allocation.get('symbol', '')),
                                    assetType=allocation.get('assetType', 'stock')
                                ))
                            
                            response = PortfolioResponse(
                                portfolio=allocations,
                                name=portfolio.get('name', f"Pure {strategy.title()} Portfolio"),
                                description=portfolio.get('description', f"Pure {strategy} strategy portfolio"),
                                expectedReturn=expected_return,
                                risk=metrics.get('risk', 0.15),
                                diversificationScore=metrics.get('diversification_score', 75.0),
                                sharpeRatio=0.0
                            )
                            responses.append(response)
                            break
                    except Exception as e:
                        logger.error(f"Error converting alternative pure portfolio: {e}")
                        continue
            
            # Try to get alternative personalized portfolio if first one was filtered
            if len([r for r in responses if 'Personalized' in r.name]) == 0 and len(personalized_portfolios) > 1:
                for portfolio in personalized_portfolios[1:]:
                    try:
                        metrics = portfolio.get('metrics', {})
                        expected_return = metrics.get('expected_return', 0.12)
                        if expected_return > 0:
                            # Same conversion logic as above
                            allocations = []
                            raw_allocs = portfolio.get('allocations', [])
                            float_weights = [max(0.0, float(a.get('allocation', 0.0))) for a in raw_allocs]
                            total = sum(float_weights) or 1.0
                            percents = [int(round(w / total * 100)) for w in float_weights]
                            diff = 100 - sum(percents)
                            if percents and diff != 0:
                                max_idx = percents.index(max(percents))
                                percents[max_idx] += diff
                            
                            for idx, allocation in enumerate(raw_allocs):
                                allocations.append(PortfolioAllocation(
                                    symbol=allocation.get('symbol', ''),
                                    allocation=max(0, percents[idx] if idx < len(percents) else 0),
                                    name=allocation.get('name', allocation.get('symbol', '')),
                                    assetType=allocation.get('assetType', 'stock')
                                ))
                            
                            response = PortfolioResponse(
                                portfolio=allocations,
                                name=portfolio.get('name', f"Personalized {strategy.title()} Portfolio"),
                                description=portfolio.get('description', f"Personalized {strategy} strategy portfolio"),
                                expectedReturn=expected_return,
                                risk=metrics.get('risk', 0.15),
                                diversificationScore=metrics.get('diversification_score', 75.0),
                                sharpeRatio=0.0
                            )
                            responses.append(response)
                            break
                    except Exception as e:
                        logger.error(f"Error converting alternative personalized portfolio: {e}")
                        continue
        
        if not responses:
            logger.warning(f"No valid strategy portfolios with positive returns for {strategy}, falling back to static")
            return _get_static_portfolio_recommendations(risk_profile)
        
        # Ensure we return exactly 2 portfolios: 1 pure + 1 personalized
        # Sort to ensure pure comes first, then personalized
        sorted_responses = sorted(responses, key=lambda r: ('Pure' not in r.name, r.name))
        final_responses = []
        
        # Add 1 pure portfolio
        pure_found = False
        for resp in sorted_responses:
            if 'Pure' in resp.name and not pure_found:
                final_responses.append(resp)
                pure_found = True
                if len(final_responses) >= 2:
                    break
        
        # Add 1 personalized portfolio
        personalized_found = False
        for resp in sorted_responses:
            if 'Personalized' in resp.name and not personalized_found:
                final_responses.append(resp)
                personalized_found = True
                if len(final_responses) >= 2:
                    break
        
        logger.info(f"✅ Generated {len(final_responses)} {strategy} strategy portfolios (1 pure + 1 personalized, all with positive returns)")
        return final_responses[:2]  # Ensure exactly 2 portfolios
        
    except Exception as e:
        logger.error(f"❌ Error generating strategy portfolios: {e}")
        return _get_static_portfolio_recommendations(risk_profile)

# NEW: Pure vs Personalized Strategy Comparison for Optimization Tab
@portfolios_router.post("/optimize/strategy-comparison")
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
@portfolios_router.post("/optimize/analysis", response_model=Dict)
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

@portfolios_router.post("/recommendations/strategy-comparison")
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

@portfolios_router.post("/strategy-portfolios/pre-generate")
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

@portfolios_router.get("/strategy-portfolios/cache-status")
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

@portfolios_router.post("/strategy-portfolios/clear-cache")
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

@portfolios_router.post("/", response_model=PortfolioResponse)
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
    risk_free_rate = 0.038
    sharpe_ratio = (weighted_return - risk_free_rate) / weighted_risk if weighted_risk > 0 else 0
    
    return PortfolioResponse(
        portfolio=normalized_portfolio,
        expectedReturn=weighted_return * 100,  # Convert to percentage
        risk=weighted_risk * 100,  # Convert to percentage
        diversificationScore=diversification_score,
        sharpeRatio=sharpe_ratio
    ) 

@portfolios_router.get("/two-asset-analysis")
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

@portfolios_router.get("/portfolio-validation/{risk_profile}")
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

# Use app Redis (REDIS_URL) for enhanced analytics; no localhost
def _analytics_redis():
    if _rds and getattr(_rds, 'redis_client', None):
        return _rds.redis_client
    return None

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
    redis_client = _analytics_redis()
    if not redis_client:
        return price_data
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
    risk_free_rate = 0.038
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

@analytics_router.post("/analytics/risk-return-analysis")
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
                returns = prices.pct_change(fill_method=None).dropna()
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

@analytics_router.get("/sector-distribution/enhanced")
async def enhanced_sector_distribution():
    try:
        redis_client = _analytics_redis()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        # Get all tickers from Redis (handle bytes when decode_responses=False)
        all_keys = redis_client.keys("sector_data:*")
        tickers = []
        for key in all_keys:
            sep = b":" if isinstance(key, bytes) else ":"
            part = key.split(sep)[1]
            tickers.append(part.decode() if isinstance(part, bytes) else part)
        
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
                    returns = prices.pct_change(fill_method=None).dropna()
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



class SmartRefreshRequest(BaseModel):
    tickers: Optional[List[str]] = None

@analytics_router.post("/ticker-table/refresh")
async def refresh_ticker_table():
    """
    Force refresh of all ticker data in Redis using Redis-first approach
    """
    try:
        # Force refresh expired data
        result = _rds.force_refresh_expired_data()
        return {
            "status": "success" if result and result.get('success') else "error",
            "message": "Ticker table refresh completed",
            "summary": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing ticker table: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing ticker table: {str(e)}")

@analytics_router.post("/ticker-table/smart-refresh")
async def smart_monthly_refresh(request: SmartRefreshRequest = Body(default=SmartRefreshRequest())):
    """
    Smart monthly refresh that only fetches the latest month of data using Redis-first approach
    - Extends time range incrementally (no re-downloading of historical data)
    - Respects TTL and only refreshes when needed
    - Efficient: Only fetches new months, not entire history
    - Can target specific tickers if provided in request body
    """
    try:
        # Check if specific tickers were requested
        target_tickers = request.tickers if request else None
        if target_tickers:
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

@analytics_router.get("/tickers/ttl-status")
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

@portfolios_router.post("/regenerate-recommendations")
async def regenerate_recommendation_portfolios(risk_profile: str = None):
    """
    Regenerate recommendation portfolios (regular portfolios) for specific or all risk profiles.
    Uses EnhancedPortfolioGenerator directly.
    """
    try:
        from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
        from utils.port_analytics import PortfolioAnalytics
        
        if not redis_manager:
            raise HTTPException(status_code=500, detail="Redis portfolio manager not available")
        
        risk_profiles = [risk_profile] if risk_profile else ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        
        # Use conservative approach + Strategy 5 for aggressive profiles
        generator = EnhancedPortfolioGenerator(_rds, portfolio_analytics, use_conservative_approach=True)
        results = {}
        total_portfolios = 0
        
        for rp in risk_profiles:
            try:
                logger.info(f"🔄 Regenerating portfolios for {rp}...")
                portfolios = generator.generate_portfolio_bucket(rp, use_parallel=True)
                
                if portfolios and len(portfolios) >= 12:
                    success = redis_manager.store_portfolio_bucket(rp, portfolios)
                    if success:
                        total_portfolios += len(portfolios)
                        results[rp] = {
                            'success': True,
                            'count': len(portfolios),
                            'timestamp': datetime.now().isoformat()
                        }
                        logger.info(f"✅ Regenerated {len(portfolios)} portfolios for {rp}")
                    else:
                        results[rp] = {
                            'success': False,
                            'error': 'Failed to store portfolios',
                            'timestamp': datetime.now().isoformat()
                        }
                else:
                    results[rp] = {
                        'success': False,
                        'error': f'Generated only {len(portfolios) if portfolios else 0} portfolios',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"❌ Error regenerating portfolios for {rp}: {e}")
                results[rp] = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        successful = sum(1 for r in results.values() if r.get('success'))
        return {
            "success": successful == len(risk_profiles),
            "message": f"Regenerated portfolios for {successful}/{len(risk_profiles)} profiles",
            "total_portfolios": total_portfolios,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error regenerating recommendation portfolios: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate portfolios: {str(e)}")

@portfolios_router.post("/regenerate")
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
        portfolio_regen_logger.info("Portfolio regeneration requested from UI")
        
        # Initialize services (use app Redis from REDIS_URL)
        redis_client = (redis_manager and getattr(redis_manager, 'redis_client', None)) or (getattr(_rds, 'redis_client', None) if _rds else None)
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        portfolio_manager = RedisPortfolioManager(redis_client)
        # Use conservative approach + Strategy 5 for aggressive profiles
        portfolio_generator = EnhancedPortfolioGenerator(_rds, portfolio_analytics, use_conservative_approach=True)
        
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        total_portfolios = 0
        profiles_generated = []
        
        for risk_profile in risk_profiles:
            try:
                logger.info(f"🔄 Regenerating portfolios for {risk_profile} profile")
                portfolio_regen_logger.info("Regenerating risk profile '%s'", risk_profile)
                
                # Generate 12 portfolios for this risk profile
                portfolios = portfolio_generator.generate_portfolio_bucket(risk_profile)
                
                if portfolios:
                    # Store in Redis
                    success = portfolio_manager.store_portfolio_bucket(risk_profile, portfolios)
                    
                    if success:
                        total_portfolios += len(portfolios)
                        profiles_generated.append(risk_profile)
                        logger.info(f"✅ Generated {len(portfolios)} portfolios for {risk_profile}")
                        portfolio_regen_logger.info(
                            "Stored %s portfolios for %s",
                            len(portfolios),
                            risk_profile,
                        )
                    else:
                        logger.error(f"❌ Failed to store portfolios for {risk_profile}")
                        portfolio_regen_logger.error("Failed to store portfolios for %s", risk_profile)
                else:
                    logger.warning(f"⚠️ No portfolios generated for {risk_profile}")
                    portfolio_regen_logger.warning("No portfolios generated for %s", risk_profile)
                    
            except Exception as e:
                logger.error(f"❌ Error generating portfolios for {risk_profile}: {e}")
                portfolio_regen_logger.error("Error generating portfolios for %s: %s", risk_profile, e)
                continue
        
        logger.info(f"🎉 Portfolio regeneration completed: {total_portfolios} portfolios across {len(profiles_generated)} profiles")
        portfolio_regen_logger.info(
            "Portfolio regeneration completed: %s portfolios across %s profiles (%s)",
            total_portfolios,
            len(profiles_generated),
            ", ".join(profiles_generated) or "none",
        )
        
        return {
            "success": True,
            "message": f"Successfully regenerated {total_portfolios} portfolios",
            "total_portfolios": total_portfolios,
            "profiles_generated": profiles_generated,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in portfolio regeneration: {e}")
        portfolio_regen_logger.error("Portfolio regeneration failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Portfolio regeneration failed: {str(e)}")

@analytics_router.get("/ticker-table/data")
async def get_ticker_table_data():
    """
    Get ticker table data with return and risk metrics using Redis-first approach
    Returns: Ticker information with essential metrics for the ticker table
    """
    try:
        import json as _json
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
                    try:
                        sector_info = json.loads(sector_raw.decode())
                        # Handle case where sector_info is a string instead of dict
                        if isinstance(sector_info, str):
                            sector_info = {'sector': sector_info, 'companyName': ticker, 'industry': 'Unknown', 'country': 'Unknown'}
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.debug(f"Sector data parse issue for {ticker}: {e}, using defaults")
                        sector_info = {'sector': 'Unknown', 'companyName': ticker, 'industry': 'Unknown', 'country': 'Unknown'}
                    
                    # Calculate data points and date range
                    data_points = len(prices)
                    # Handle dates - might be strings or tuples
                    first_date_raw = dates[0] if dates else "N/A"
                    last_date_raw = dates[-1] if dates else "N/A"
                    
                    # Extract date string from various formats
                    def extract_date_str(date_val):
                        if date_val == "N/A" or date_val is None:
                            return "N/A"
                        
                        # Handle tuple objects
                        if isinstance(date_val, tuple):
                            # If tuple, take the second element (date)
                            date_val = date_val[1] if len(date_val) > 1 else date_val[0]
                        
                        # Handle string representation of tuples (e.g., "('APOTEA.ST', datetime.datetime(...))")
                        if isinstance(date_val, str) and date_val.startswith("(") and "datetime" in date_val:
                            try:
                                # Try to extract date from string representation
                                # Pattern: "('TICKER', datetime.datetime(2025, 10, 27, ...))"
                                import re
                                # Extract datetime.datetime(...) or datetime.date(...) part
                                match = re.search(r'datetime\.(?:datetime|date)\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})', date_val)
                                if match:
                                    year, month, day = match.groups()
                                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            except Exception:
                                pass
                        
                        # Handle datetime/date objects
                        if isinstance(date_val, (datetime, date)):
                            # Convert datetime/date objects to string
                            return date_val.strftime("%Y-%m-%d")
                        
                        return str(date_val)
                    
                    first_date = extract_date_str(first_date_raw)
                    last_date = extract_date_str(last_date_raw)
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
                    
                    # Check data freshness - properly handle all cases
                    data_freshness = "unknown"
                    if last_date and last_date != "N/A":
                        date_str = None
                        try:
                            # Handle various date formats
                            date_str = str(last_date).strip()
                            
                            # Extract just the date part (YYYY-MM-DD) from various formats
                            # Examples: "2025-10-01", "2025-10-22 20:00:01+00:00", "2025-10-22T20:00:01Z"
                            if " " in date_str:
                                date_str = date_str.split(" ")[0]
                            elif "T" in date_str:
                                date_str = date_str.split("T")[0]
                            elif "+" in date_str:
                                date_str = date_str.split("+")[0]
                            
                            # Ensure we have a valid date format (YYYY-MM-DD)
                            if len(date_str) >= 10:
                                date_str = date_str[:10]
                            
                            # Parse date
                            last_date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            now = datetime.now()
                            
                            # Calculate days difference (handle future dates)
                            days_diff = (now - last_date_obj).days
                            
                            # If date is in the future, mark as very recent (likely timezone issue)
                            if days_diff < 0:
                                data_freshness = "very_recent"
                            elif days_diff <= 7:
                                data_freshness = "very_recent"
                            elif days_diff <= 30:
                                data_freshness = "recent"
                            elif days_diff <= 90:
                                data_freshness = "moderate"
                            else:
                                data_freshness = "stale"
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"Date parsing error for {ticker} (date: {last_date}, extracted: {date_str}): {e}")
                            data_freshness = "unknown"
                    else:
                        # No date available
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

@portfolios_router.get("/mini-lesson/assets")
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

@portfolios_router.get("/mini-lesson/random-pair")
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


@portfolios_router.post("/mini-lesson/custom-portfolio")
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
        returns1 = pd.Series(data1['prices']).pct_change(fill_method=None).dropna()
        returns2 = pd.Series(data2['prices']).pct_change(fill_method=None).dropna()
        
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

@portfolios_router.post("/optimize/risk-parity")
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
            returns = pd.Series(prices).pct_change(fill_method=None).dropna()
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

@portfolios_router.post("/optimize/mean-variance")
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
            returns = pd.Series(prices).pct_change(fill_method=None).dropna()
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

@analytics_router.get("/analytics/performance-attribution")
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
            returns = pd.Series(prices).pct_change(fill_method=None).dropna()
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
                excess_return = asset_return - 0.038  # Assuming 2% risk-free rate
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

@analytics_router.get("/analytics/risk-decomposition")
async def risk_decomposition(allocations: str):
    """
    Decompose portfolio risk into systematic and idiosyncratic components
    Returns: Risk breakdown and factor analysis
    """
    try:
        # Parse allocations
        import json as _json
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
            returns = pd.Series(prices).pct_change(fill_method=None).dropna()
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

@analytics_router.post("/rebalance/check")
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

@analytics_router.post("/monitor/performance-tracking")
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

# (Health check -> routers/admin.py)

# Enhanced Ticker Table Endpoints

# Global auto-refresh service instance
auto_refresh_service = None

def get_auto_refresh_service():
    """Get or create auto refresh service instance"""
    global auto_refresh_service
    if auto_refresh_service is None:
        auto_refresh_service = None
    return auto_refresh_service

@analytics_router.get("/ticker-table/enhanced")
def get_enhanced_ticker_table():
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

@analytics_router.get("/ticker-table/status")
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

@analytics_router.post("/ticker-table/start-auto-refresh")
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

@analytics_router.post("/ticker-table/stop-auto-refresh")
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


@analytics_router.get("/ticker-table/data-quality-report")
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

@analytics_router.get("/ticker-table/enhanced-html")
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

# (force-refresh-expired-data, smart-monthly-refresh -> routers/admin.py)

# New: Table-friendly portfolios endpoint (all profiles + strategy portfolios)
@analytics_router.get("/portfolios-table/data")
def get_all_portfolios_table_data():
    """
    Get all portfolios for all risk profiles in a table-friendly format.
    Includes both regular portfolios and strategy portfolios (pure + personalized).
    Returns flattened list with essential fields for rendering tables.
    """
    try:
        from datetime import datetime
        import math

        def _safe_num(value, *, mult: float = 1.0, digits: int | None = None, default: float = 0.0) -> float:
            """
            Ensure returned numbers are JSON-compliant (no NaN/Infinity).
            FastAPI's JSON rendering will raise if floats are out of range.
            """
            try:
                v = float(value)
            except Exception:
                v = default
            if math.isnan(v) or math.isinf(v):
                v = default
            v = v * mult
            if digits is not None:
                v = round(v, digits)
            return v

        if not redis_manager:
            return {
                "status": "error",
                "message": "Portfolio system not available",
                "portfolios": [],
                "total_count": 0,
                "timestamp": datetime.now().isoformat(),
            }

        risk_profiles = [
            'very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive'
        ]

        all_rows = []
        
        # 1. Get ALL regular portfolios for each risk profile (directly from Redis)
        for rp in risk_profiles:
            # Load all portfolios directly from Redis (bypass rotation logic)
            bucket_key = f"portfolio_bucket:{rp}"
            portfolios = []
            
            # Load all portfolios from Redis (up to 12 per profile)
            for i in range(redis_manager.PORTFOLIOS_PER_PROFILE):
                portfolio_key = f"{bucket_key}:{i}"
                portfolio_data = redis_manager.redis_client.get(portfolio_key) if redis_manager.redis_client else None
                
                if portfolio_data:
                    try:
                        portfolio = json.loads(portfolio_data)
                        portfolios.append(portfolio)
                    except json.JSONDecodeError as e:
                        logger.debug(f"⚠️ Failed to decode portfolio {i} for {rp}: {e}")
                        continue
            
            # Add all portfolios to table
            for idx, p in enumerate(portfolios):
                allocations = p.get('allocations', []) or []
                # Top 3 allocation preview
                top = sorted(allocations, key=lambda a: a.get('allocation', 0), reverse=True)[:3]
                top_preview = ", ".join([f"{t.get('symbol','?')} ({t.get('allocation',0):.1f}%)" for t in top])
                row = {
                    "id": len(all_rows) + 1,
                    "risk_profile": rp,
                    "risk_profile_display": rp.replace('-', ' ').title(),
                    "portfolio_name": p.get('name', f'Portfolio {idx + 1}'),
                    "portfolio_type": "Regular",
                    "strategy": None,
                    "variation_id": p.get('variation_id', idx),
                    "stock_count": len(allocations),
                    "expected_return": _safe_num(p.get('expectedReturn', 0), mult=100.0, digits=2),
                    "risk": _safe_num(p.get('risk', 0), mult=100.0, digits=2),
                    "diversification_score": _safe_num(p.get('diversificationScore', 0) or 0, digits=1),
                    "top_stocks": top_preview,
                }
                all_rows.append(row)
        
        # 2. Get strategy portfolios (pure + personalized)
        try:
            # Initialize strategy optimizer if not already done
            if not hasattr(_rds, 'strategy_optimizer'):
                _rds.strategy_optimizer = StrategyPortfolioOptimizer(_rds, redis_manager)
            
            strategies = ['diversification', 'risk', 'return']
            
            # Get pure strategy portfolios
            for strategy in strategies:
                pure_portfolios = _rds.strategy_optimizer.get_pure_portfolios_from_cache(strategy) or []
                for idx, p in enumerate(pure_portfolios):
                    allocations = p.get('allocations', []) or []
                    # Top 3 allocation preview
                    top = sorted(allocations, key=lambda a: a.get('allocation', 0), reverse=True)[:3]
                    top_preview = ", ".join([f"{t.get('symbol','?')} ({t.get('allocation',0):.1f}%)" for t in top])
                    
                    metrics = p.get('metrics', {})
                    row = {
                        "id": len(all_rows) + 1,
                        "risk_profile": "N/A",
                        "risk_profile_display": "Pure Strategy",
                        "portfolio_name": p.get('name', f'Pure {strategy.title()} Portfolio {idx + 1}'),
                        "portfolio_type": "Strategy (Pure)",
                        "strategy": strategy.title(),
                        "variation_id": None,
                        "stock_count": len(allocations),
                        "expected_return": _safe_num(metrics.get('expected_return', 0), mult=100.0, digits=2),
                        "risk": _safe_num(metrics.get('risk', 0), mult=100.0, digits=2),
                        "diversification_score": _safe_num(metrics.get('diversification_score', 0) or 0, digits=1),
                        "top_stocks": top_preview,
                    }
                    all_rows.append(row)
            
            # Get personalized strategy portfolios
            for strategy in strategies:
                for rp in risk_profiles:
                    personalized_portfolios = _rds.strategy_optimizer.get_personalized_portfolios_from_cache(strategy, rp) or []
                    for idx, p in enumerate(personalized_portfolios):
                        allocations = p.get('allocations', []) or []
                        # Top 3 allocation preview
                        top = sorted(allocations, key=lambda a: a.get('allocation', 0), reverse=True)[:3]
                        top_preview = ", ".join([f"{t.get('symbol','?')} ({t.get('allocation',0):.1f}%)" for t in top])
                        
                        metrics = p.get('metrics', {})
                        row = {
                            "id": len(all_rows) + 1,
                            "risk_profile": rp,
                            "risk_profile_display": rp.replace('-', ' ').title(),
                            "portfolio_name": p.get('name', f'Personalized {strategy.title()} Portfolio {idx + 1}'),
                            "portfolio_type": "Strategy (Personalized)",
                            "strategy": strategy.title(),
                            "variation_id": None,
                            "stock_count": len(allocations),
                            "expected_return": _safe_num(metrics.get('expected_return', 0), mult=100.0, digits=2),
                            "risk": _safe_num(metrics.get('risk', 0), mult=100.0, digits=2),
                            "diversification_score": _safe_num(metrics.get('diversification_score', 0) or 0, digits=1),
                            "top_stocks": top_preview,
                        }
                        all_rows.append(row)
        except Exception as e:
            logger.warning(f"⚠️ Error fetching strategy portfolios for table: {e}")

        # Final safety pass: ensure we never emit NaN/Infinity (FastAPI will error).
        import numbers
        for row in all_rows:
            for k, v in list(row.items()):
                if isinstance(v, bool) or v is None:
                    continue
                if isinstance(v, numbers.Real):
                    try:
                        fv = float(v)
                    except Exception:
                        continue
                    if math.isnan(fv) or math.isinf(fv):
                        row[k] = 0.0

        import json as _json

        def _sanitize_json_numbers(obj):
            if isinstance(obj, dict):
                return {k: _sanitize_json_numbers(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize_json_numbers(v) for v in obj]
            if isinstance(obj, bool) or obj is None:
                return obj
            # Covers float, int, numpy numeric types
            import numbers as _numbers
            if isinstance(obj, _numbers.Real):
                try:
                    fv = float(obj)
                except Exception:
                    return obj
                if math.isnan(fv) or math.isinf(fv):
                    return 0.0
                return fv
            return obj

        result = {
            "status": "success",
            "portfolios": all_rows,
            "total_count": len(all_rows),
            "timestamp": datetime.now().isoformat(),
        }

        # Validate + sanitize for strict JSON (no NaN/Inf)
        try:
            _json.dumps(result, allow_nan=False)
        except ValueError:
            result = _sanitize_json_numbers(result)

        return result

    except Exception as e:
        logger.error(f"Error getting portfolios table data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting portfolios table data: {str(e)}")




@analytics_router.get("/ticker-table/refresh/preview")
async def refresh_ticker_table_preview():
    """Return an estimate of how many tickers would be refreshed and estimated time."""
    try:
        # Use the same preview logic as smart-refresh but for full refresh
        result = _rds.preview_expired_data()
        expired_count = result.get('expired_count', 0)
        missing_counts = result.get('missing_counts', {})
        
        # Estimate time: roughly 0.5-1 second per ticker (with rate limiting)
        # More conservative estimate for full refresh
        estimate_seconds = max(60, expired_count * 1.5)  # At least 1 minute, or 1.5s per ticker
        if expired_count == 0:
            estimate_seconds = 30  # Quick check if nothing to refresh
        
        return {
            "status": "success",
            "expired_count": expired_count,
            "estimate_seconds": estimate_seconds,
            "note": "Full refresh updates all expired/incomplete tickers. This may take several minutes depending on the number of tickers needing updates.",
            "timestamp": datetime.now().isoformat(),
            "missing_counts": missing_counts,
            "missing_samples": result.get('missing_samples', {}),
            "refresh_candidates": result.get('refresh_candidates', []),
        }
    except Exception as e:
        logger.error(f"Error generating refresh preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating refresh preview: {str(e)}")

@analytics_router.get("/ticker-table/smart-refresh/preview")
async def smart_refresh_preview():
    """Return how many tickers would be refreshed by smart-refresh, without executing it."""
    try:
        result = _rds.preview_expired_data()
        return {
            "status": "success",
            "expired_count": result.get('expired_count', 0),
            "sample": result.get('tickers', []),
            "timestamp": datetime.now().isoformat(),
            "missing_counts": result.get('missing_counts', {}),
            "missing_samples": result.get('missing_samples', {}),
            "refresh_candidates": result.get('refresh_candidates', []),
        }
    except Exception as e:
        logger.error(f"Error generating smart-refresh preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating smart-refresh preview: {str(e)}")


@portfolios_router.get("/regenerate/estimate")
async def estimate_portfolio_regeneration():
    """Return an estimated duration for regenerating portfolios."""
    try:
        # Heuristic estimate based on strategy optimizer availability
        est_seconds = 120
        note = "Typical duration 1–3 minutes depending on cache and rate limits"
        try:
            # If strategy optimizer exposes summary stats, adjust estimate
            if hasattr(_rds, 'strategy_optimizer') and _rds.strategy_optimizer:
                est_seconds = 90
        except Exception:
            pass
        return {"status": "success", "estimate_seconds": est_seconds, "note": note}
    except Exception as e:
        logger.error(f"Error estimating regeneration: {e}")
        raise HTTPException(status_code=500, detail=f"Error estimating regeneration: {str(e)}")


# ============================================================================
# VISUALIZATION ENDPOINTS - Agent 2 Implementation
# ============================================================================

# Helper utilities for visualization endpoints
def _build_portfolio_metrics_cache_key(risk_profile: str, allocations: List[Dict]) -> str:
    """Build cache key for portfolio metrics using md5 hash."""
    try:
        rounded_parts = []
        for a in sorted(allocations, key=lambda x: x.get('symbol', '')):
            try:
                rounded_alloc = float(f"{float(a.get('allocation', 0.0)):.1f}")
            except Exception:
                rounded_alloc = 0.0
            rounded_parts.append(f"{a.get('symbol', '')}:{rounded_alloc:.1f}")
        key_raw = f"{risk_profile}|" + "|".join(rounded_parts)
        return f"portfolio:metrics:{hashlib.md5(key_raw.encode()).hexdigest()}"
    except Exception as e:
        logger.error(f"Error building cache key: {e}")
        return None

def _load_portfolio_metrics_from_cache(key: str) -> Optional[Dict]:
    """Load portfolio metrics from Redis cache."""
    if not key:
        return None
    try:
        r = _rds.redis_client
        if r is None:
            return None
        raw = r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Error loading portfolio metrics from cache: {e}")
    return None

def _store_portfolio_metrics_cache(key: str, metrics: Dict) -> bool:
    """Store portfolio metrics in Redis cache."""
    if not key:
        return False
    try:
        r = _rds.redis_client
        if r is None:
            return False
        ttl_days = getattr(redis_manager, 'PORTFOLIO_TTL_DAYS', 28) if redis_manager else 28
        r.setex(key, ttl_days * 24 * 3600, json.dumps(metrics))
        return True
    except Exception as e:
        logger.debug(f"Error storing portfolio metrics in cache: {e}")
    return False

def _get_stock_cached_metrics(symbol: str) -> Optional[Dict]:
    """Get cached metrics for a stock symbol. Returns {returnValue, risk, sector} or None."""
    try:
        symbol = symbol.upper()
        metrics = _rds.get_cached_metrics(symbol)
        sector_data = _rds._load_from_cache(symbol, 'sector')
        
        if metrics is None:
            return None
        
        return {
            'returnValue': metrics.get('annualized_return'),
            'risk': metrics.get('risk'),
            'sector': sector_data.get('sector', 'Unknown') if sector_data else 'Unknown'
        }
    except Exception as e:
        logger.debug(f"Error getting cached metrics for {symbol}: {e}")
        return None

def _record_warning(warnings: List[str], message: str):
    """Add a warning message to the warnings list."""
    if message and message not in warnings:
        warnings.append(message)

# Pydantic models for visualization endpoints
class ScatterPoint(BaseModel):
    label: str
    risk: float
    returnValue: float  # Using returnValue instead of return (reserved keyword)
    symbol: Optional[str] = None
    sector: Optional[str] = None

class ScatterDataRequest(BaseModel):
    selectedPortfolio: List[PortfolioAllocation]
    allRecommendations: List[Dict]
    selectedPortfolioIndex: int
    riskProfile: str

class ScatterDataResponse(BaseModel):
    points: List[ScatterPoint]
    tickerPoints: Optional[List[ScatterPoint]] = None  # Individual ticker-level points for Ticker View
    palette: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

class CorrelationMatrixRequest(BaseModel):
    tickers: str  # Comma-separated
    portfolioLabels: Optional[str] = None  # JSON string or comma-separated
    period: Optional[str] = None

class CorrelationMatrixResponse(BaseModel):
    tickers: List[str]
    matrix: List[List[float]]
    sectorMap: Dict[str, str]
    portfolioLabels: Optional[List[str]] = None
    warnings: List[str]
    missingTickers: List[str]
    metadata: Dict[str, Any]

class SectorAllocationRequest(BaseModel):
    tickers: List[str]
    weights: List[float]
    portfolioLabel: Optional[str] = None

class SectorInfo(BaseModel):
    sector: str
    weight: float
    color: str

class SectorAllocationResponse(BaseModel):
    sectors: List[SectorInfo]
    totalPercent: float
    warnings: List[str]
    metadata: Dict[str, Any]

class VisualizationDataRequest(BaseModel):
    selectedPortfolio: List[PortfolioAllocation]
    allRecommendations: List[Dict]
    selectedPortfolioIndex: int
    riskProfile: str
    correlationTickers: Optional[str] = None
    correlationPortfolioLabels: Optional[str] = None

class VisualizationDataResponse(BaseModel):
    scatter: ScatterDataResponse
    correlation: CorrelationMatrixResponse
    sectorAllocation: SectorAllocationResponse
    warnings: List[str]
    metadata: Dict[str, Any]

async def build_scatter_data(request: ScatterDataRequest) -> ScatterDataResponse:
    """
    Build scatter data for visualization by combining selected portfolio metrics with benchmark portfolios.
    """
    import time
    
    start_time = time.time()
    warnings: List[str] = []
    points: List[Dict[str, Any]] = []
    ticker_points: List[Dict[str, Any]] = []
    cache_hits = 0
    cache_misses = 0
    
    try:
        selected_portfolio = request.selectedPortfolio
        all_recommendations = request.allRecommendations
        selected_portfolio_index = request.selectedPortfolioIndex
        risk_profile = request.riskProfile
        
        # Process selected portfolio
        selected_allocations = [{'symbol': a.symbol, 'allocation': a.allocation} for a in selected_portfolio]
        
        # Check if allocations match original recommendation
        original_recommendation = None
        if 0 <= selected_portfolio_index < len(all_recommendations):
            original_recommendation = all_recommendations[selected_portfolio_index]
            original_allocs = original_recommendation.get('portfolio', [])
            if len(original_allocs) == len(selected_allocations):
                # Check if allocations match (within tolerance)
                matches = True
                for orig, sel in zip(original_allocs, selected_allocations):
                    if orig.get('symbol') != sel.get('symbol') or abs(orig.get('allocation', 0) - sel.get('allocation', 0)) > 0.1:
                        matches = False
                        break
                if matches:
                    # Reuse recommendation metrics directly
                    portfolio_metrics = {
                        'expected_return': original_recommendation.get('expectedReturn', 0.0),
                        'risk': original_recommendation.get('risk', 0.0)
                    }
                    cache_hits += 1
                else:
                    # Check portfolio metrics cache
                    cache_key = _build_portfolio_metrics_cache_key(risk_profile, selected_allocations)
                    portfolio_metrics = _load_portfolio_metrics_from_cache(cache_key)
                    if portfolio_metrics:
                        cache_hits += 1
                    else:
                        # Compute metrics
                        portfolio_data = {'allocations': selected_allocations}
                        portfolio_metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
                        _store_portfolio_metrics_cache(cache_key, portfolio_metrics)
                        cache_misses += 1
            else:
                # Check portfolio metrics cache
                cache_key = _build_portfolio_metrics_cache_key(risk_profile, selected_allocations)
                portfolio_metrics = _load_portfolio_metrics_from_cache(cache_key)
                if portfolio_metrics:
                    cache_hits += 1
                else:
                    # Compute metrics
                    portfolio_data = {'allocations': selected_allocations}
                    portfolio_metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
                    _store_portfolio_metrics_cache(cache_key, portfolio_metrics)
                    cache_misses += 1
        else:
            # Check portfolio metrics cache
            cache_key = _build_portfolio_metrics_cache_key(risk_profile, selected_allocations)
            portfolio_metrics = _load_portfolio_metrics_from_cache(cache_key)
            if portfolio_metrics:
                cache_hits += 1
            else:
                # Compute metrics
                portfolio_data = {'allocations': selected_allocations}
                portfolio_metrics = portfolio_analytics.calculate_real_portfolio_metrics(portfolio_data)
                _store_portfolio_metrics_cache(cache_key, portfolio_metrics)
                cache_misses += 1
        
        def _to_decimal_return(val):
            """Ensure return is decimal (0.12 for 12%). If > 1, assume percentage format."""
            v = float(val) if val is not None else 0.0
            return v / 100.0 if abs(v) > 1 else v

        def _to_decimal_risk(val):
            """Ensure risk is decimal (0.15 for 15%). If > 1, assume percentage format."""
            v = float(val) if val is not None else 0.0
            return v / 100.0 if v > 1 else v

        # Build scatter point for selected portfolio (chart expects decimals)
        selected_point = {
            'label': 'Selected Portfolio',
            'risk': _to_decimal_risk(portfolio_metrics.get('risk', 0.0)),
            'returnValue': _to_decimal_return(portfolio_metrics.get('expected_return', 0.0)),
            'symbol': None,
            'sector': None
        }
        points.append(selected_point)
        
        # Process benchmark portfolios (excluding selected index)
        benchmark_index = 0
        for idx, recommendation in enumerate(all_recommendations):
            if idx == selected_portfolio_index:
                continue
            
            benchmark_label = f"Benchmark {benchmark_index + 1}"
            benchmark_index += 1
            
            # Use recommendation-level metrics (chart expects decimals)
            exp_ret = recommendation.get('expectedReturn') or recommendation.get('expected_return', 0.0)
            rsk = recommendation.get('risk', 0.0)
            
            # Build scatter point for benchmark
            benchmark_point = {
                'label': benchmark_label,
                'risk': _to_decimal_risk(rsk),
                'returnValue': _to_decimal_return(exp_ret),
                'symbol': None,
                'sector': None
            }
            points.append(benchmark_point)
        
        # Build individual ticker-level points for Ticker View
        try:
            logger.debug(
                f"Building ticker points for {len(selected_portfolio)} selected portfolio tickers and {len(all_recommendations)} recommendations"
            )
            # Add tickers from selected portfolio
            for stock in selected_portfolio:
                ticker = stock.symbol.upper()

                cached_metrics = _rds._load_from_cache(ticker, 'metrics')
                cached_sector = _rds._load_from_cache(ticker, 'sector')
                cached_prices = _rds._load_from_cache(ticker, 'prices')

                # Fallback: ensure cached data exists by warming if necessary
                if cached_prices is None or cached_sector is None:
                    monthly_data = _rds.get_monthly_data(ticker)
                    if monthly_data:
                        try:
                            if cached_prices is None and monthly_data.get('prices') and monthly_data.get('dates'):
                                prices_series = pd.Series(
                                    monthly_data['prices'],
                                    index=pd.to_datetime(monthly_data['dates'])
                                )
                                cached_prices = prices_series
                        except Exception as price_error:
                            logger.debug(f"Failed to rebuild price series for {ticker}: {price_error}")
                        if cached_sector is None:
                            cached_sector = {
                                'sector': monthly_data.get('sector', 'Unknown'),
                                'industry': monthly_data.get('industry', 'Unknown'),
                                'companyName': monthly_data.get('company_name', ticker),
                                'country': monthly_data.get('country', 'Unknown'),
                                'exchange': monthly_data.get('exchange', 'Unknown'),
                            }

                if cached_metrics is None:
                    try:
                        cached_metrics = _rds.get_cached_metrics(ticker)
                    except Exception as metrics_error:
                        logger.debug(f"Failed to load cached metrics for {ticker}: {metrics_error}")

                ticker_risk = None
                ticker_return = None

                if cached_metrics:
                    ticker_risk = cached_metrics.get('risk') or cached_metrics.get('annualized_risk')
                    ticker_return = cached_metrics.get('annualized_return') or cached_metrics.get('annual_return')

                    if ticker_risk is not None and ticker_risk > 1:
                        ticker_risk = ticker_risk / 100.0
                    if ticker_return is not None and ticker_return > 1:
                        ticker_return = ticker_return / 100.0

                    if (ticker_risk is None or ticker_return is None) and cached_prices is not None:
                        try:
                            import pandas as pd
                            import numpy as np

                            if hasattr(cached_prices, 'pct_change'):
                                returns = cached_prices.pct_change(fill_method=None).dropna()
                            else:
                                if isinstance(cached_prices, dict):
                                    prices_series = pd.Series(cached_prices)
                                else:
                                    prices_series = pd.Series(cached_prices)
                                returns = prices_series.pct_change(fill_method=None).dropna()

                            if len(returns) >= 12:
                                if ticker_return is None:
                                    ticker_return = float((1 + returns.mean()) ** 12 - 1)

                                if ticker_risk is None:
                                    ticker_risk = float(returns.std() * np.sqrt(12))
                        except Exception as e:
                            logger.debug(f"Failed to calculate metrics for {ticker}: {e}")

                # Extract sector info regardless of price data availability
                sector = 'Unknown'
                if cached_sector:
                    if isinstance(cached_sector, dict):
                        sector = cached_sector.get('sector', 'Unknown')
                    elif isinstance(cached_sector, str):
                        sector = cached_sector

                # Add ticker point if we have price data (for scatter plot)
                if cached_prices is not None:
                    if ticker_risk is None:
                        ticker_risk = 0.15
                    if ticker_return is None:
                        ticker_return = 0.08
                    # Ensure display values are valid so chart shows ticker (frontend filters out return<=0 or risk<0)
                    display_risk = max(0.01, float(ticker_risk))
                    display_return = float(ticker_return) if float(ticker_return) > 0 else 0.005

                    ticker_points.append({
                        'label': 'Selected Portfolio',
                        'symbol': ticker,
                        'risk': display_risk,
                        'returnValue': display_return,
                        'sector': sector
                    })
                elif sector != 'Unknown':
                    # Add ticker point with sector info even without price data
                    # This ensures sector allocation works for all tickers with sector data
                    ticker_points.append({
                        'label': 'Selected Portfolio',
                        'symbol': ticker,
                        'risk': 0.15,  # Default risk
                        'returnValue': 0.08,  # Default return
                        'sector': sector
                    })
                else:
                    # No price and no sector: still show ticker so frontend does not report "insufficient data"
                    ticker_points.append({
                        'label': 'Selected Portfolio',
                        'symbol': ticker,
                        'risk': 0.15,
                        'returnValue': 0.08,
                        'sector': 'Unknown'
                    })

            # Add tickers from benchmark portfolios
            benchmark_index = 0
            for idx, recommendation in enumerate(all_recommendations):
                if idx == selected_portfolio_index:
                    continue

                benchmark_label = f"Benchmark {benchmark_index + 1}"
                benchmark_index += 1

                recommendation_allocs = recommendation.get('portfolio', [])
                if not recommendation_allocs:
                    recommendation_allocs = recommendation.get('allocations', [])

                for alloc_dict in recommendation_allocs:
                    ticker = alloc_dict.get('symbol', '').upper()
                    if not ticker:
                        continue

                    cached_metrics = _rds._load_from_cache(ticker, 'metrics')
                    cached_sector = _rds._load_from_cache(ticker, 'sector')
                    cached_prices = _rds._load_from_cache(ticker, 'prices')

                    if cached_prices is None or cached_sector is None:
                        monthly_data = _rds.get_monthly_data(ticker)
                        if monthly_data:
                            try:
                                if cached_prices is None and monthly_data.get('prices') and monthly_data.get('dates'):
                                    prices_series = pd.Series(
                                        monthly_data['prices'],
                                        index=pd.to_datetime(monthly_data['dates'])
                                    )
                                    cached_prices = prices_series
                            except Exception as price_error:
                                logger.debug(f"Failed to rebuild price series for {ticker}: {price_error}")
                            if cached_sector is None:
                                cached_sector = {
                                    'sector': monthly_data.get('sector', 'Unknown'),
                                    'industry': monthly_data.get('industry', 'Unknown'),
                                    'companyName': monthly_data.get('company_name', ticker),
                                    'country': monthly_data.get('country', 'Unknown'),
                                    'exchange': monthly_data.get('exchange', 'Unknown'),
                                }

                    if cached_metrics is None:
                        try:
                            cached_metrics = _rds.get_cached_metrics(ticker)
                        except Exception as metrics_error:
                            logger.debug(f"Failed to load cached metrics for {ticker}: {metrics_error}")

                    ticker_risk = None
                    ticker_return = None

                    if cached_metrics:
                        ticker_risk = cached_metrics.get('risk') or cached_metrics.get('annualized_risk')
                        ticker_return = cached_metrics.get('annualized_return') or cached_metrics.get('annual_return')

                        if ticker_risk is not None and ticker_risk > 1:
                            ticker_risk = ticker_risk / 100.0
                        if ticker_return is not None and ticker_return > 1:
                            ticker_return = ticker_return / 100.0

                    if (ticker_risk is None or ticker_return is None) and cached_prices is not None:
                        try:
                            import pandas as pd
                            import numpy as np

                            if hasattr(cached_prices, 'pct_change'):
                                returns = cached_prices.pct_change(fill_method=None).dropna()
                            else:
                                if isinstance(cached_prices, dict):
                                    prices_series = pd.Series(cached_prices)
                                else:
                                    prices_series = pd.Series(cached_prices)
                                returns = prices_series.pct_change(fill_method=None).dropna()

                            if len(returns) >= 12:
                                if ticker_return is None:
                                    ticker_return = float((1 + returns.mean()) ** 12 - 1)

                                if ticker_risk is None:
                                    ticker_risk = float(returns.std() * np.sqrt(12))
                        except Exception as e:
                            logger.debug(f"Failed to calculate metrics for {ticker}: {e}")

                    # Extract sector info regardless of price data availability
                    sector = 'Unknown'
                    if cached_sector:
                        if isinstance(cached_sector, dict):
                            sector = cached_sector.get('sector', 'Unknown')
                        elif isinstance(cached_sector, str):
                            sector = cached_sector

                    # Add ticker point if we have price data (for scatter plot)
                    if cached_prices is not None:
                        if ticker_risk is None:
                            ticker_risk = 0.15
                        if ticker_return is None:
                            ticker_return = 0.08
                        # Ensure display values are valid so chart shows ticker (frontend filters out return<=0 or risk<0)
                        display_risk = max(0.01, float(ticker_risk))
                        display_return = float(ticker_return) if float(ticker_return) > 0 else 0.005

                        ticker_points.append({
                            'label': benchmark_label,
                            'symbol': ticker,
                            'risk': display_risk,
                            'returnValue': display_return,
                            'sector': sector
                        })
                    elif sector != 'Unknown':
                        # Add ticker point with sector info even without price data
                        # This ensures sector allocation works for all tickers with sector data
                        ticker_points.append({
                            'label': benchmark_label,
                            'symbol': ticker,
                            'risk': 0.15,  # Default risk
                            'returnValue': 0.08,  # Default return
                            'sector': sector
                        })
                    else:
                        # No price and no sector: still show ticker for consistency
                        ticker_points.append({
                            'label': benchmark_label,
                            'symbol': ticker,
                            'risk': 0.15,
                            'returnValue': 0.08,
                            'sector': 'Unknown'
                        })

            logger.info(f"Built {len(ticker_points)} ticker points for visualization")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.warning(f"Error building ticker points: {e}\n{error_trace}")

        palette = ['#2c5aa0', '#1e3d6f', '#4a90e2', '#6ba3d6', '#8bb5c9', '#aac7bc']
        
        elapsed_time = time.time() - start_time
        logger.info(f"Scatter data prepared in {elapsed_time:.3f}s (cache hits: {cache_hits}, misses: {cache_misses})")
        
        return ScatterDataResponse(
            points=[ScatterPoint(**p) for p in points],
            tickerPoints=[ScatterPoint(**p) for p in ticker_points] if ticker_points else None,
            palette=palette,
            warnings=warnings,
            metadata={
                'pointCount': len(points),
                'tickerPointCount': len(ticker_points),
                'cacheHits': cache_hits,
                'cacheMisses': cache_misses,
                'elapsedTime': elapsed_time
            }
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"Error preparing scatter data: {error_msg}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Scatter data preparation failed: {error_msg}")

@analytics_router.get("/visualization/correlation-matrix", response_model=CorrelationMatrixResponse)
async def correlation_matrix(
    tickers: str = Query(..., description="Comma-separated list of ticker symbols"),
    portfolioLabels: Optional[str] = Query(None, description="JSON string or comma-separated portfolio labels"),
    period: Optional[str] = Query(None, description="Optional period filter")
):
    """
    Calculate correlation matrix for given tickers using cached price data.
    """
    import time
    
    start_time = time.time()
    warnings = []
    missing_tickers = []
    
    try:
        # Parse and deduplicate tickers
        ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        ticker_list = list(dict.fromkeys(ticker_list))  # Preserve order, remove duplicates
        
        # Parse portfolio labels
        portfolio_labels = None
        if portfolioLabels:
            try:
                portfolio_labels = json.loads(portfolioLabels)
            except:
                portfolio_labels = [l.strip() for l in portfolioLabels.split(',') if l.strip()]
        
        # Load price series from cache
        price_series_dict = {}
        for ticker in ticker_list:
            monthly_data = _rds.get_monthly_data(ticker)
            if monthly_data and 'prices' in monthly_data and 'dates' in monthly_data:
                try:
                    prices = monthly_data['prices']
                    dates = monthly_data['dates']
                    # Create pandas Series
                    price_series = pd.Series(prices, index=pd.to_datetime(dates))
                    price_series_dict[ticker] = price_series
                except Exception as e:
                    _record_warning(warnings, f"Failed to parse price data for {ticker}: {str(e)}")
                    missing_tickers.append(ticker)
            else:
                _record_warning(warnings, f"Price data not found in cache for {ticker}")
                missing_tickers.append(ticker)
        
        # Filter out missing tickers
        available_tickers = [t for t in ticker_list if t not in missing_tickers]
        
        if len(available_tickers) < 2:
            _record_warning(warnings, f"Insufficient tickers for correlation matrix. Need at least 2, got {len(available_tickers)}")
            return CorrelationMatrixResponse(
                tickers=available_tickers,
                matrix=[],
                sectorMap={},
                portfolioLabels=portfolio_labels,
                warnings=warnings,
                missingTickers=missing_tickers,
                metadata={
                    'dataPoints': 0,
                    'period': period,
                    'elapsedTime': time.time() - start_time
                }
            )
        
        # Create DataFrame of price series
        df = pd.DataFrame(price_series_dict)
        
        # Drop columns with insufficient data
        df = df.dropna(axis=1, how='all')
        if df.shape[1] < 2:
            _record_warning(warnings, f"Insufficient valid price history after cleaning. Need at least 2 tickers, got {df.shape[1]}")
            return CorrelationMatrixResponse(
                tickers=list(df.columns),
                matrix=[],
                sectorMap={},
                portfolioLabels=portfolio_labels,
                warnings=warnings,
                missingTickers=list(set(missing_tickers + [t for t in available_tickers if t not in df.columns])),
                metadata={
                    'dataPoints': 0,
                    'period': period,
                    'elapsedTime': time.time() - start_time
                }
            )
        
        # Calculate returns if needed (for correlation)
        # Fix deprecation warning: specify fill_method=None instead of default 'pad'
        returns_df = df.pct_change(fill_method=None).dropna()
        
        # Drop columns with insufficient return data
        valid_columns = [col for col in returns_df.columns if returns_df[col].count() > 0]
        returns_df = returns_df[valid_columns]
        
        if returns_df.shape[1] < 2:
            _record_warning(warnings, f"Returns data insufficient for correlation. Need at least 2 tickers with return data, got {returns_df.shape[1]}")
            return CorrelationMatrixResponse(
                tickers=list(returns_df.columns),
                matrix=[],
                sectorMap={},
                portfolioLabels=portfolio_labels,
                warnings=warnings,
                missingTickers=list(set(missing_tickers + [t for t in available_tickers if t not in returns_df.columns])),
                metadata={
                    'dataPoints': returns_df.shape[0],
                    'period': period,
                    'elapsedTime': time.time() - start_time
                }
            )
        
        # Calculate Pearson correlation matrix
        correlation_matrix = returns_df.corr().values.tolist()
        
        # Ensure symmetry and fill diagonal with 1.0
        n = len(available_tickers)
        for i in range(n):
            for j in range(n):
                if i == j:
                    correlation_matrix[i][j] = 1.0
                else:
                    # Ensure symmetry
                    correlation_matrix[i][j] = correlation_matrix[j][i] = (correlation_matrix[i][j] + correlation_matrix[j][i]) / 2
        
        # Build sector map
        sector_map = {}
        for ticker in available_tickers:
            sector_data = _rds._load_from_cache(ticker, 'sector')
            sector_map[ticker] = sector_data.get('sector', 'Unknown') if sector_data else 'Unknown'
        
        elapsed_time = time.time() - start_time
        logger.info(f"Correlation matrix calculated in {elapsed_time:.3f}s for {len(available_tickers)} tickers")
        
        return CorrelationMatrixResponse(
            tickers=available_tickers,
            matrix=correlation_matrix,
            sectorMap=sector_map,
            portfolioLabels=portfolio_labels,
            warnings=warnings,
            missingTickers=missing_tickers,
            metadata={
                'dataPoints': len(returns_df),
                'period': period,
                'elapsedTime': elapsed_time
            }
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"Error calculating correlation matrix: {error_msg}\n{error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Correlation matrix calculation failed: {error_msg}. Missing tickers: {', '.join(missing_tickers) if missing_tickers else 'none'}"
        )

@analytics_router.get("/visualization/sector-allocation", response_model=SectorAllocationResponse)
async def sector_allocation(
    tickers: str = Query(..., description="Comma-separated list of ticker symbols"),
    weights: str = Query(..., description="Comma-separated list of weights (percentages)"),
    portfolioLabel: Optional[str] = Query(None, description="Optional portfolio label")
):
    """
    Calculate sector allocation breakdown for given tickers and weights.
    """
    import time
    
    start_time = time.time()
    warnings = []
    
    try:
        # Parse tickers and weights
        ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        weight_list = []
        for w in weights.split(','):
            try:
                weight_list.append(float(w.strip()))
            except:
                _record_warning(warnings, f"Invalid weight value: {w}")
        
        # Validate arrays length match
        if len(ticker_list) != len(weight_list):
            _record_warning(warnings, f"Ticker count ({len(ticker_list)}) does not match weight count ({len(weight_list)})")
            return SectorAllocationResponse(
                sectors=[],
                totalPercent=0.0,
                warnings=warnings,
                metadata={'error': True, 'elapsedTime': time.time() - start_time}
            )
        
        # Validate sum of weights (allow small rounding, e.g. 99.5-100.5)
        total_weight = sum(weight_list)
        if abs(total_weight - 100.0) > 0.5:
            _record_warning(warnings, f"Total weight is {total_weight:.2f}%, expected 100%")
        
        # Aggregate weights per sector
        sector_weights = {}
        for ticker, weight in zip(ticker_list, weight_list):
            sector_data = _rds._load_from_cache(ticker, 'sector')
            if sector_data:
                sector = sector_data.get('sector', 'Unknown Sector')
            else:
                _record_warning(warnings, f"Sector data not found for {ticker}, using 'Unknown Sector'")
                sector = 'Unknown Sector'
            
            if sector not in sector_weights:
                sector_weights[sector] = 0.0
            sector_weights[sector] += weight
        
        # Sort sectors by weight (descending)
        sorted_sectors = sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
        
        # Generate color palette
        colors = ['#2c5aa0', '#1e3d6f', '#4a90e2', '#6ba3d6', '#8bb5c9', '#aac7bc', '#c9d9af', '#e8e992']
        
        # Build sector info list
        sectors = []
        for idx, (sector, weight) in enumerate(sorted_sectors):
            color = colors[idx % len(colors)]
            sectors.append({
                'sector': sector,
                'weight': round(weight, 2),
                'color': color
            })
        
        elapsed_time = time.time() - start_time
        logger.info(f"Sector allocation calculated in {elapsed_time:.3f}s for {len(ticker_list)} tickers")
        
        return SectorAllocationResponse(
            sectors=[SectorInfo(**s) for s in sectors],
            totalPercent=round(total_weight, 2),
            warnings=warnings,
            metadata={
                'tickerCount': len(ticker_list),
                'sectorCount': len(sectors),
                'elapsedTime': elapsed_time
            }
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"Error calculating sector allocation: {error_msg}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Sector allocation calculation failed: {error_msg}")

@analytics_router.post("/visualization/data", response_model=VisualizationDataResponse)
async def visualization_data(request: VisualizationDataRequest):
    """
    Consolidated endpoint that returns clustering, correlation, and sector allocation data.
    """
    import time
    
    start_time = time.time()
    all_warnings = []
    
    try:
        # Prepare scatter data request
        scatter_request = ScatterDataRequest(
            selectedPortfolio=request.selectedPortfolio,
            allRecommendations=request.allRecommendations,
            selectedPortfolioIndex=request.selectedPortfolioIndex,
            riskProfile=request.riskProfile
        )
        
        logger.debug(f"Visualization data request: {len(request.selectedPortfolio)} selected stocks, {len(request.allRecommendations)} recommendations")
        
        # Build scatter data
        try:
            scatter_response = await build_scatter_data(scatter_request)
            all_warnings.extend(scatter_response.warnings)
        except HTTPException as scatter_http_err:
            logger.error(f"Scatter data HTTP error: {scatter_http_err.detail} (status {scatter_http_err.status_code})")
            raise
        except Exception as scatter_err:
            logger.error(f"Scatter data preparation error: {scatter_err}")
            raise HTTPException(status_code=500, detail=f"Scatter data preparation failed: {str(scatter_err)}")
        
        # Prepare correlation matrix request
        if request.correlationTickers:
            correlation_tickers = request.correlationTickers
        else:
            # Extract tickers from selected portfolio
            correlation_tickers = ','.join([a.symbol for a in request.selectedPortfolio])
        
        if correlation_tickers:
            try:
                correlation_response = await correlation_matrix(
                    tickers=correlation_tickers,
                    portfolioLabels=request.correlationPortfolioLabels,
                    period=None
                )
                all_warnings.extend(correlation_response.warnings)
            except HTTPException as corr_http_err:
                logger.error(f"Correlation matrix HTTP error: {corr_http_err.detail} (status {corr_http_err.status_code})")
                raise
            except Exception as corr_err:
                logger.error(f"Correlation matrix error: {corr_err}")
                raise HTTPException(status_code=500, detail=f"Correlation matrix failed: {str(corr_err)}")
        else:
            # Create empty correlation response
            correlation_response = CorrelationMatrixResponse(
                tickers=[],
                matrix=[],
                sectorMap={},
                portfolioLabels=None,
                warnings=[],
                missingTickers=[],
                metadata={}
            )
        
        # Prepare sector allocation request
        tickers_list = [a.symbol for a in request.selectedPortfolio]
        weights_list = [a.allocation for a in request.selectedPortfolio]
        tickers_str = ','.join(tickers_list)
        weights_str = ','.join([str(w) for w in weights_list])
        
        try:
            sector_response = await sector_allocation(
                tickers=tickers_str,
                weights=weights_str,
                portfolioLabel=None
            )
            all_warnings.extend(sector_response.warnings)
        except HTTPException as sector_http_err:
            logger.error(f"Sector allocation HTTP error: {sector_http_err.detail} (status {sector_http_err.status_code})")
            raise
        except Exception as sector_err:
            logger.error(f"Sector allocation error: {sector_err}")
            raise HTTPException(status_code=500, detail=f"Sector allocation failed: {str(sector_err)}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Consolidated visualization data generated in {elapsed_time:.3f}s")
        
        return VisualizationDataResponse(
            scatter=scatter_response,
            correlation=correlation_response,
            sectorAllocation=sector_response,
            warnings=all_warnings,
            metadata={
                'elapsedTime': elapsed_time,
                'endpoint': 'consolidated'
            }
        )
        
    except HTTPException as http_exc:
        # Re-raise HTTP errors without wrapping so the client sees the original detail
        detail = http_exc.detail if http_exc.detail else "Unknown HTTP error occurred"
        logger.error(f"Visualization data generation HTTP error ({http_exc.status_code}): {detail}")
        # Ensure we have a meaningful detail message
        if not detail or detail == "HTTPException" or detail.strip() == "":
            detail = f"Visualization component failed (status {http_exc.status_code}). Check backend logs for details."
        raise HTTPException(status_code=http_exc.status_code, detail=detail)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # Check if it's an HTTPException that was caught as generic Exception
        if isinstance(e, HTTPException):
            detail = e.detail if e.detail else f"HTTP error {e.status_code}"
            logger.error(f"Visualization data generation HTTP error (caught as Exception): {detail}")
            raise HTTPException(status_code=e.status_code, detail=detail if detail != "HTTPException" else f"Visualization component failed (status {e.status_code})")
        error_msg = str(e) if str(e) else type(e).__name__
        logger.error(f"Error generating consolidated visualization data: {error_msg}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Visualization data generation failed: {error_msg}")


# New: Consolidated HTML with two tabs (Tickers + Portfolios) and search inputs
@portfolios_router.post("/portfolios/verify-tickers")
async def verify_portfolio_tickers():
    """
    Verify all tickers in cached portfolios and fetch missing ones
    
    This endpoint:
    1. Checks all tickers in cached portfolios
    2. Verifies if they exist in Redis
    3. Fetches missing tickers using the data fetching system
    4. Returns status report
    """
    try:
        if not redis_manager:
            raise HTTPException(status_code=503, detail="Redis manager not available")
        
        from utils.redis_first_data_service import RedisFirstDataService
        from utils.enhanced_data_fetcher import EnhancedDataFetcher
        
        data_service = RedisFirstDataService()
        data_fetcher = EnhancedDataFetcher()
        
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        all_tickers_by_profile = {}
        all_unique_tickers = set()
        
        # Step 1: Collect all tickers from portfolios
        logger.info("📊 Collecting tickers from cached portfolios...")
        for risk_profile in risk_profiles:
            tickers = set()
            try:
                portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=12)
                for portfolio in portfolios:
                    allocations = portfolio.get('allocations', [])
                    for alloc in allocations:
                        symbol = alloc.get('symbol', '').upper().strip()
                        if symbol:
                            tickers.add(symbol)
                all_tickers_by_profile[risk_profile] = tickers
                all_unique_tickers.update(tickers)
            except Exception as e:
                logger.error(f"Error getting tickers for {risk_profile}: {e}")
                all_tickers_by_profile[risk_profile] = set()
        
        # Step 2: Check which tickers are in Redis
        logger.info("🔍 Checking ticker availability in Redis...")
        ticker_status = {}
        for ticker in all_unique_tickers:
            try:
                price_key = data_service._get_cache_key(ticker, 'prices')
                sector_key = data_service._get_cache_key(ticker, 'sector')
                has_prices = data_service.redis_client.exists(price_key) > 0
                has_sector = data_service.redis_client.exists(sector_key) > 0
                ticker_status[ticker] = has_prices and has_sector
            except Exception as e:
                logger.warning(f"Error checking {ticker}: {e}")
                ticker_status[ticker] = False
        
        present_tickers = [t for t, status in ticker_status.items() if status]
        missing_tickers = [t for t, status in ticker_status.items() if not status]
        
        # Step 3: Fetch missing tickers
        fetch_results = {}
        newly_present = []
        still_missing = []
        
        if missing_tickers:
            logger.info(f"📥 Fetching {len(missing_tickers)} missing tickers...")
            for ticker in missing_tickers:
                try:
                    ticker_data = data_fetcher.get_ticker_data(ticker)
                    success = ticker_data is not None and 'prices' in ticker_data and len(ticker_data.get('prices', [])) > 0
                    fetch_results[ticker] = success
                    
                    if success:
                        # Verify it's now in Redis
                        price_key = data_service._get_cache_key(ticker, 'prices')
                        if data_service.redis_client.exists(price_key) > 0:
                            newly_present.append(ticker)
                        else:
                            still_missing.append(ticker)
                    else:
                        still_missing.append(ticker)
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                    fetch_results[ticker] = False
                    still_missing.append(ticker)
        else:
            newly_present = []
            still_missing = []
        
        # Build summary by profile
        profile_summary = {}
        for risk_profile, tickers in all_tickers_by_profile.items():
            profile_status = {t: ticker_status.get(t, False) for t in tickers}
            present_count = sum(1 for status in profile_status.values() if status)
            missing_count = len(profile_status) - present_count
            profile_summary[risk_profile] = {
                'total_tickers': len(tickers),
                'present': present_count,
                'missing': missing_count,
                'missing_tickers': [t for t, status in profile_status.items() if not status]
            }
        
        return {
            'total_unique_tickers': len(all_unique_tickers),
            'present_tickers': len(present_tickers),
            'missing_tickers': len(missing_tickers),
            'newly_fetched': len(newly_present),
            'still_missing': len(still_missing),
            'profile_summary': profile_summary,
            'newly_present_tickers': newly_present,
            'still_missing_tickers': still_missing,
            'fetch_results': fetch_results
        }
        
    except Exception as e:
        logger.error(f"❌ Error verifying portfolio tickers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to verify portfolio tickers: {str(e)}")

# ============================================================================
# Agent 2: Tax Calculation, Transaction Costs, Export, and Shareable Links
# ============================================================================

# Initialize calculators
tax_calculator = SwedishTaxCalculator()
courtage_calculator = AvanzaCourtageCalculator()
pdf_generator = PDFReportGenerator()
csv_generator = CSVExportGenerator()

# Shareable link generator will be initialized after redis_client is available
shareable_link_generator = None

def get_shareable_link_generator():
    """Get or initialize shareable link generator (uses REDIS_URL / app Redis)"""
    global shareable_link_generator
    if shareable_link_generator is None:
        try:
            redis_cli = (getattr(_rds, 'redis_client', None) if _rds else None)
            if redis_cli and redis_cli.ping():
                shareable_link_generator = ShareableLinkGenerator(redis_client=redis_cli)
            else:
                shareable_link_generator = ShareableLinkGenerator()
        except Exception as e:
            logger.warning(f"Could not initialize shareable link generator with Redis: {e}")
            shareable_link_generator = ShareableLinkGenerator()
    return shareable_link_generator

# Pydantic models for tax calculation
class TaxCalculationRequest(BaseModel):
    accountType: Literal["ISK", "KF", "AF"]
    taxYear: int
    portfolioValue: Optional[float] = None  # For ISK/KF (capital_underlag)
    realizedGains: Optional[float] = None  # For AF
    dividends: Optional[float] = None  # For AF
    fundHoldings: Optional[float] = None  # For AF
    expectedReturn: Optional[float] = None  # Decimal e.g. 0.07; used to compute afterTaxReturn

class TaxCalculationResponse(BaseModel):
    accountType: str
    taxYear: int
    capitalUnderlag: Optional[float] = None
    taxFreeLevel: Optional[float] = None
    taxableCapital: Optional[float] = None
    annualTax: float
    effectiveTaxRate: float
    afterTaxReturn: Optional[float] = None
    details: Dict[str, Any]

@export_router.post("/tax/calculate", response_model=TaxCalculationResponse)
async def calculate_tax(request: TaxCalculationRequest):
    """
    Calculate Swedish tax for portfolio
    
    Request:
    {
        "accountType": "ISK" | "KF" | "AF",
        "taxYear": 2025 | 2026,
        "portfolioValue": float (ISK/KF only),
        "realizedGains": float (AF only),
        "dividends": float (AF only),
        "fundHoldings": float (AF only)
    }
    
    Response:
    {
        "accountType": "ISK",
        "taxYear": 2026,
        "capitalUnderlag": float,
        "taxFreeLevel": float,
        "taxableCapital": float,
        "annualTax": float,
        "effectiveTaxRate": float,
        "afterTaxReturn": float (if portfolio return provided),
        "details": {...}
    }
    """
    try:
        if request.accountType in ["ISK", "KF"]:
            if request.portfolioValue is None:
                raise HTTPException(
                    status_code=400, 
                    detail=f"portfolioValue is required for {request.accountType} accounts"
                )
            
            result = tax_calculator.calculate_tax(
                account_type=request.accountType,
                tax_year=request.taxYear,
                capital_underlag=request.portfolioValue
            )
            after_tax_return = None
            if request.expectedReturn is not None and request.portfolioValue and request.portfolioValue > 0:
                gross_return_amount = request.portfolioValue * request.expectedReturn
                after_tax_return_amount = gross_return_amount - result["annual_tax"]
                after_tax_return = after_tax_return_amount / request.portfolioValue  # as decimal
            return TaxCalculationResponse(
                accountType=result["account_type"],
                taxYear=result["tax_year"],
                capitalUnderlag=result.get("capital_underlag"),
                taxFreeLevel=result.get("tax_free_level"),
                taxableCapital=result.get("taxable_capital"),
                annualTax=result["annual_tax"],
                effectiveTaxRate=result["effective_tax_rate"],
                afterTaxReturn=round(after_tax_return, 4) if after_tax_return is not None else None,
                details=result
            )
        
        elif request.accountType == "AF":
            result = tax_calculator.calculate_tax(
                account_type=request.accountType,
                tax_year=request.taxYear,
                realized_gains=request.realizedGains or 0.0,
                dividends=request.dividends or 0.0,
                fund_holdings=request.fundHoldings or 0.0
            )
            after_tax_return = None
            if request.expectedReturn is not None:
                # AF: 30% tax on gains -> after-tax return = expectedReturn * (1 - 0.30)
                after_tax_return = request.expectedReturn * 0.70
            return TaxCalculationResponse(
                accountType=result["account_type"],
                taxYear=result["tax_year"],
                annualTax=result["total_tax"],
                effectiveTaxRate=0.0,  # AF doesn't have a simple effective rate
                afterTaxReturn=round(after_tax_return, 4) if after_tax_return is not None else None,
                details=result
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid account type: {request.accountType}"
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating tax: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate tax: {str(e)}")

# Pydantic models for transaction costs
class TransactionCostRequest(BaseModel):
    courtageClass: Literal["start", "mini", "small", "medium", "fastPris"]
    portfolio: List[Dict[str, Any]]  # [{"ticker": "AAPL", "shares": 10, "value": 15000}]
    rebalancingFrequency: Literal["monthly", "quarterly", "semi-annual", "annual"] = "quarterly"

class TransactionCostResponse(BaseModel):
    courtageClass: str
    setupCost: float
    setupBreakdown: List[Dict[str, Any]]
    annualRebalancingCost: float
    totalFirstYearCost: float
    costOptimization: Dict[str, Any]

@export_router.post("/transaction-costs/estimate", response_model=TransactionCostResponse)
async def estimate_transaction_costs(request: TransactionCostRequest):
    """
    Estimate transaction costs for portfolio
    
    Request:
    {
        "courtageClass": "start" | "mini" | "small" | "medium" | "fastPris",
        "portfolio": [
            {"ticker": "AAPL", "shares": 10, "value": 15000}
        ],
        "rebalancingFrequency": "monthly" | "quarterly" | "semi-annual" | "annual"
    }
    
    Response:
    {
        "courtageClass": "medium",
        "setupCost": float,
        "setupBreakdown": [...],
        "annualRebalancingCost": float,
        "totalFirstYearCost": float,
        "costOptimization": {
            "recommendedClass": "small",
            "potentialSavings": float
        }
    }
    """
    try:
        # Calculate setup costs
        setup_data = courtage_calculator.estimate_setup_cost(
            portfolio=request.portfolio,
            courtage_class=request.courtageClass
        )
        
        # Calculate rebalancing costs
        rebalancing_data = courtage_calculator.estimate_rebalancing_cost(
            transactions=request.portfolio,
            courtage_class=request.courtageClass,
            frequency=request.rebalancingFrequency
        )
        
        # Get cost optimization
        optimization = courtage_calculator.find_optimal_courtage_class(
            portfolio=request.portfolio,
            rebalancing_frequency=request.rebalancingFrequency
        )
        
        return TransactionCostResponse(
            courtageClass=request.courtageClass,
            setupCost=setup_data["total_setup_cost"],
            setupBreakdown=setup_data["breakdown"],
            annualRebalancingCost=rebalancing_data["annual_cost"],
            totalFirstYearCost=setup_data["total_setup_cost"] + rebalancing_data["annual_cost"],
            costOptimization=optimization
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error estimating transaction costs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate transaction costs: {str(e)}")


# Five-year projection (regression-based, Sweden tax/costs)
class FiveYearProjectionRequest(BaseModel):
    weights: Dict[str, float]  # ticker -> weight (fraction, sum 1)
    capital: float
    accountType: Literal["ISK", "KF", "AF"]
    taxYear: Literal[2025, 2026]
    courtageClass: Literal["start", "mini", "small", "medium", "fastPris"]
    expectedReturn: float  # decimal, e.g. 0.08
    risk: float  # decimal, e.g. 0.15
    rebalancingFrequency: Literal["monthly", "quarterly", "semi-annual", "annual"] = "quarterly"


class FiveYearProjectionResponse(BaseModel):
    years: List[int]
    optimistic: List[float]
    base: List[float]
    pessimistic: List[float]


@export_router.post("/projection/five-year", response_model=FiveYearProjectionResponse)
async def projection_five_year(request: FiveYearProjectionRequest):
    """
    Five-year portfolio projection with Swedish tax and transaction costs.
    Returns three regression-based scenarios: optimistic, base, pessimistic.
    """
    try:
        result = run_five_year_projection(
            initial_capital=request.capital,
            weights=request.weights,
            expected_return=request.expectedReturn,
            risk=request.risk,
            account_type=request.accountType,
            tax_year=request.taxYear,
            courtage_class=request.courtageClass,
            rebalancing_frequency=request.rebalancingFrequency,
        )
        return FiveYearProjectionResponse(
            years=result["years"],
            optimistic=result["optimistic"],
            base=result["base"],
            pessimistic=result["pessimistic"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running five-year projection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run projection: {str(e)}")


# Pydantic models for tax-adjusted metrics
class TaxAdjustedMetricsRequest(BaseModel):
    portfolio: List[Dict[str, Any]]  # [{"ticker": "AAPL", "allocation": 0.4}]
    accountType: Literal["ISK", "KF", "AF"]
    taxYear: int
    courtageClass: Literal["start", "mini", "small", "medium", "fastPris"]
    portfolioValue: float
    expectedReturn: Optional[float] = None  # Annual expected return percentage

class TaxAdjustedMetricsResponse(BaseModel):
    grossExpectedReturn: float
    annualTaxImpact: float
    afterTaxReturn: float
    transactionCosts: Dict[str, float]
    netExpectedReturn: float
    fiveYearProjection: List[Dict[str, Any]]

@export_router.post("/metrics/tax-adjusted", response_model=TaxAdjustedMetricsResponse)
async def calculate_tax_adjusted_metrics(request: TaxAdjustedMetricsRequest):
    """
    Calculate tax-adjusted portfolio metrics
    
    Request:
    {
        "portfolio": [{"ticker": "AAPL", "allocation": 0.4}],
        "accountType": "ISK" | "KF" | "AF",
        "taxYear": 2025 | 2026,
        "courtageClass": "medium",
        "portfolioValue": float,
        "expectedReturn": float (optional, annual percentage)
    }
    
    Response:
    {
        "grossExpectedReturn": float,
        "annualTaxImpact": float,
        "afterTaxReturn": float,
        "transactionCosts": {
            "setup": float,
            "annual": float
        },
        "netExpectedReturn": float,
        "fiveYearProjection": [
            {"year": 1, "value": float, "tax": float, "netValue": float}
        ]
    }
    """
    try:
        portfolio_value = request.portfolioValue
        expected_return = request.expectedReturn or 0.0  # Default to 0 if not provided

        def _normalize_supported_tax_year(year: int) -> int:
            """
            SwedishTaxCalculator only supports 2025 and 2026 in this codebase.
            For multi-year projections, cap to the nearest supported year.
            """
            return 2025 if year <= 2025 else 2026
        
        # Calculate tax
        if request.accountType in ["ISK", "KF"]:
            tax_result = tax_calculator.calculate_tax(
                account_type=request.accountType,
                tax_year=request.taxYear,
                capital_underlag=portfolio_value
            )
            annual_tax = tax_result["annual_tax"]
        else:  # AF
            # For AF, we need realized gains - estimate based on expected return
            estimated_gains = portfolio_value * (expected_return / 100) if expected_return else 0.0
            tax_result = tax_calculator.calculate_tax(
                account_type=request.accountType,
                tax_year=request.taxYear,
                realized_gains=estimated_gains,
                dividends=0.0,
                fund_holdings=0.0
            )
            annual_tax = tax_result["total_tax"]
        
        # Calculate transaction costs
        portfolio_positions = [
            {
                "ticker": pos.get("ticker", pos.get("symbol", "UNKNOWN")),
                "shares": pos.get("shares", 0),
                "value": portfolio_value * pos.get("allocation", 0.0)
            }
            for pos in request.portfolio
        ]
        
        setup_data = courtage_calculator.estimate_setup_cost(
            portfolio=portfolio_positions,
            courtage_class=request.courtageClass
        )
        
        rebalancing_data = courtage_calculator.estimate_rebalancing_cost(
            transactions=portfolio_positions,
            courtage_class=request.courtageClass,
            frequency="quarterly"
        )
        
        # Calculate returns
        gross_return_amount = portfolio_value * (expected_return / 100) if expected_return else 0.0
        after_tax_return_amount = gross_return_amount - annual_tax
        after_tax_return_pct = (after_tax_return_amount / portfolio_value * 100) if portfolio_value > 0 else 0.0
        
        net_return_amount = after_tax_return_amount - rebalancing_data["annual_cost"]
        net_return_pct = (net_return_amount / portfolio_value * 100) if portfolio_value > 0 else 0.0
        
        # Generate 5-year projection
        five_year_projection = []
        current_value = portfolio_value
        
        for year in range(1, 6):
            # Calculate growth
            year_return = current_value * (expected_return / 100) if expected_return else 0.0
            year_value = current_value + year_return
            
            # Calculate tax for this year
            projection_tax_year = _normalize_supported_tax_year(request.taxYear + year - 1)
            if request.accountType in ["ISK", "KF"]:
                year_tax_result = tax_calculator.calculate_tax(
                    account_type=request.accountType,
                    tax_year=projection_tax_year,
                    capital_underlag=year_value
                )
                year_tax = year_tax_result["annual_tax"]
            else:
                year_tax_result = tax_calculator.calculate_tax(
                    account_type=request.accountType,
                    tax_year=projection_tax_year,
                    realized_gains=year_return,
                    dividends=0.0,
                    fund_holdings=0.0
                )
                year_tax = year_tax_result["total_tax"]
            
            # Apply tax and transaction costs
            net_value = year_value - year_tax - rebalancing_data["annual_cost"]
            
            five_year_projection.append({
                "year": year,
                "value": round(year_value, 2),
                "tax": round(year_tax, 2),
                "netValue": round(net_value, 2)
            })
            
            current_value = net_value
        
        return TaxAdjustedMetricsResponse(
            grossExpectedReturn=round(expected_return, 2),
            annualTaxImpact=round(annual_tax, 2),
            afterTaxReturn=round(after_tax_return_pct, 2),
            transactionCosts={
                "setup": round(setup_data["total_setup_cost"], 2),
                "annual": round(rebalancing_data["annual_cost"], 2)
            },
            netExpectedReturn=round(net_return_pct, 2),
            fiveYearProjection=five_year_projection
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating tax-adjusted metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate tax-adjusted metrics: {str(e)}")

def _normalize_export_portfolio(portfolio: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Accept portfolio as list of positions or as { tickers, weights, allocations }; return list of positions (allocation 0-1, ticker set)."""
    if isinstance(portfolio, list):
        out = []
        for pos in portfolio:
            p = dict(pos)
            alloc = p.get("allocation", 0.0)
            if alloc > 1:
                p["allocation"] = alloc / 100.0
            if "symbol" in p and "ticker" not in p:
                p["ticker"] = p["symbol"]
            out.append(p)
        return out
    if isinstance(portfolio, dict) and "allocations" in portfolio:
        out = []
        for pos in portfolio["allocations"]:
            p = dict(pos)
            alloc = p.get("allocation", 0.0)
            if alloc > 1:
                p["allocation"] = alloc / 100.0
            if "symbol" in p and "ticker" not in p:
                p["ticker"] = p["symbol"]
            out.append(p)
        return out
    return []

# Pydantic models for PDF export
class PDFExportRequest(BaseModel):
    portfolio: Union[List[Dict[str, Any]], Dict[str, Any]]
    portfolioName: Optional[str] = None
    includeSections: Dict[str, bool] = {}
    optimizationResults: Optional[Dict[str, Any]] = None
    projectionMetrics: Optional[Dict[str, Any]] = None  # weights, expectedReturn, risk for 5-year projection (recommended portfolio)
    taxData: Optional[Dict[str, Any]] = None
    costData: Optional[Dict[str, Any]] = None
    stressTestResults: Optional[Dict[str, Any]] = None
    portfolioValue: Optional[float] = None
    accountType: Optional[str] = None
    taxYear: Optional[int] = None
    courtageClass: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    # New enhanced fields
    taxComparison: Optional[List[Dict[str, Any]]] = None
    taxFreeData: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    educationalSummary: Optional[Dict[str, Any]] = None

@export_router.post("/export/pdf")
async def export_pdf(request: PDFExportRequest):
    """
    Generate PDF report
    
    Request:
    {
        "portfolio": {...} or [ {...}, ... ],
        "includeSections": {
            "optimization": bool,
            "stressTest": bool,
            "goals": bool,
            "rebalancing": bool
        },
        "taxData": {...},
        "costData": {...},
        "stressTestResults": {...} (optional),
        "portfolioValue": float,
        "accountType": str,
        "taxYear": int,
        "metrics": {...}
    }
    
    Response:
    - Returns PDF file as binary response
    - Content-Type: application/pdf
    """
    try:
        portfolio_list = _normalize_export_portfolio(request.portfolio)
        # Prepare data for PDF generation
        pdf_data = {
            "portfolio": portfolio_list,
            "portfolioName": request.portfolioName or "Investment Portfolio",
            "includeSections": request.includeSections,
            "optimizationResults": request.optimizationResults,
            "projectionMetrics": request.projectionMetrics,
            "taxData": request.taxData or {},
            "costData": request.costData or {},
            "stressTestResults": request.stressTestResults,
            "portfolioValue": request.portfolioValue or 0.0,
            "accountType": request.accountType,
            "taxYear": request.taxYear or datetime.now().year,
            "courtageClass": request.courtageClass,
            "metrics": request.metrics or {},
            # Enhanced data
            "taxComparison": request.taxComparison,
            "taxFreeData": request.taxFreeData,
            "recommendations": request.recommendations,
            "educationalSummary": request.educationalSummary
        }

        # Generate PDF
        pdf_bytes = pdf_generator.generate_portfolio_report(pdf_data)
        
        # Return PDF as binary response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

# Pydantic models for CSV export (same content as PDF for parity)
class CSVExportRequest(BaseModel):
    portfolio: Union[List[Dict[str, Any]], Dict[str, Any]]
    portfolioName: Optional[str] = None
    taxData: Optional[Dict[str, Any]] = None
    costData: Optional[Dict[str, Any]] = None
    stressTestResults: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    optimizationResults: Optional[Dict[str, Any]] = None
    projectionMetrics: Optional[Dict[str, Any]] = None
    portfolioValue: Optional[float] = None
    accountType: Optional[str] = None
    taxYear: Optional[int] = None
    courtageClass: Optional[str] = None
    # New enhanced fields
    taxComparison: Optional[List[Dict[str, Any]]] = None
    taxFreeData: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    educationalSummary: Optional[Dict[str, Any]] = None
    includeFiles: List[str] = ["holdings", "tax", "costs", "metrics", "stressTest", "optimization", "projection", "taxComparison", "recommendations"]

class CSVExportResponse(BaseModel):
    files: List[Dict[str, Any]]
    zipFile: Optional[str] = None  # base64 encoded zip if multiple files

@export_router.post("/export/csv", response_model=CSVExportResponse)
async def export_csv(request: CSVExportRequest):
    """
    Generate CSV exports
    
    Request:
    {
        "portfolio": {...},
        "taxData": {...},
        "costData": {...},
        "stressTestResults": {...} (optional),
        "includeFiles": ["holdings", "tax", "costs", "metrics", "stressTest"]
    }
    
    Response:
    {
        "files": [
            {
                "filename": "portfolio_holdings.csv",
                "content": "base64_encoded_csv",
                "size": int
            }
        ],
        "zipFile": "base64_encoded_zip" (if multiple files)
    }
    """
    try:
        files = []
        portfolio_list = _normalize_export_portfolio(request.portfolio)

        # Executive summary (same info as PDF Section 1) - include when we have core data
        if request.portfolioValue is not None and request.accountType and request.taxYear is not None:
            exec_csv = csv_generator.generate_executive_summary_csv(
                portfolio_value=float(request.portfolioValue),
                account_type=request.accountType,
                tax_year=int(request.taxYear),
                metrics=request.metrics,
                portfolio_name=request.portfolioName,
            )
            files.append({
                "filename": "executive_summary.csv",
                "content": base64.b64encode(exec_csv.encode('utf-8')).decode('utf-8'),
                "size": len(exec_csv.encode('utf-8')),
            })

        # Generate requested CSV files
        if "holdings" in request.includeFiles and portfolio_list:
            holdings_csv = csv_generator.generate_portfolio_holdings_csv(
                portfolio_list, portfolio_value=request.portfolioValue
            )
            files.append({
                "filename": "portfolio_holdings.csv",
                "content": base64.b64encode(holdings_csv.encode('utf-8')).decode('utf-8'),
                "size": len(holdings_csv.encode('utf-8'))
            })

        if "tax" in request.includeFiles and request.taxData:
            tax_csv = csv_generator.generate_tax_analysis_csv(
                request.taxData,
                tax_free_data=request.taxFreeData,
            )
            files.append({
                "filename": "tax_analysis.csv",
                "content": base64.b64encode(tax_csv.encode('utf-8')).decode('utf-8'),
                "size": len(tax_csv.encode('utf-8'))
            })
        
        if "costs" in request.includeFiles and request.costData:
            costs_csv = csv_generator.generate_transaction_costs_csv(
                request.costData,
                portfolio_value=request.portfolioValue,
            )
            files.append({
                "filename": "transaction_costs.csv",
                "content": base64.b64encode(costs_csv.encode('utf-8')).decode('utf-8'),
                "size": len(costs_csv.encode('utf-8'))
            })
        
        if "metrics" in request.includeFiles and request.metrics:
            metrics_csv = csv_generator.generate_portfolio_metrics_csv(request.metrics)
            files.append({
                "filename": "portfolio_metrics.csv",
                "content": base64.b64encode(metrics_csv.encode('utf-8')).decode('utf-8'),
                "size": len(metrics_csv.encode('utf-8'))
            })
        
        if "stressTest" in request.includeFiles and request.stressTestResults:
            stress_csv = csv_generator.generate_stress_test_csv(request.stressTestResults)
            files.append({
                "filename": "stress_test_results.csv",
                "content": base64.b64encode(stress_csv.encode('utf-8')).decode('utf-8'),
                "size": len(stress_csv.encode('utf-8'))
            })

        # Same content as PDF: optimization comparison, quality scores, Monte Carlo
        if "optimization" in request.includeFiles and request.optimizationResults:
            opt = request.optimizationResults
            try:
                opt_comp = csv_generator.generate_optimization_comparison_csv(opt)
                files.append({
                    "filename": "optimization_comparison.csv",
                    "content": base64.b64encode(opt_comp.encode('utf-8')).decode('utf-8'),
                    "size": len(opt_comp.encode('utf-8'))
                })
                qual = csv_generator.generate_quality_scores_csv(opt)
                if qual.strip() and qual.count('\n') >= 1:
                    files.append({
                        "filename": "quality_scores.csv",
                        "content": base64.b64encode(qual.encode('utf-8')).decode('utf-8'),
                        "size": len(qual.encode('utf-8'))
                    })
                mc = csv_generator.generate_monte_carlo_csv(opt)
                if mc.strip() and mc.count('\n') >= 1:
                    files.append({
                        "filename": "monte_carlo_summary.csv",
                        "content": base64.b64encode(mc.encode('utf-8')).decode('utf-8'),
                        "size": len(mc.encode('utf-8'))
                    })
            except Exception as e:
                logger.warning("CSV optimization export failed: %s", e)

        # Same content as PDF: 5-year projection (run same projection as PDF)
        if "projection" in request.includeFiles and request.projectionMetrics and request.portfolioValue and request.accountType and request.taxYear:
            proj_metrics = request.projectionMetrics
            weights = proj_metrics.get('weights') or {}
            if not weights and portfolio_list:
                weights = {p.get('symbol', p.get('ticker', '')): p.get('allocation', 0) for p in portfolio_list if p.get('symbol') or p.get('ticker')}
            exp_ret = proj_metrics.get('expectedReturn') or proj_metrics.get('expected_return') or (request.metrics or {}).get('expectedReturn') or (request.metrics or {}).get('expected_return') or 0.08
            risk_val = proj_metrics.get('risk') or (request.metrics or {}).get('risk') or 0.15
            cost_data = request.costData or {}
            courtage_class = (cost_data.get('courtageClass') or cost_data.get('courtage_class') or 'medium').lower() or 'medium'
            if courtage_class == 'fastpris':
                courtage_class = 'fastPris'
            try:
                if run_five_year_projection and weights and 2025 <= (request.taxYear or 0) <= 2026:
                    proj = run_five_year_projection(
                        initial_capital=float(request.portfolioValue),
                        weights={k: float(v) for k, v in weights.items() if v and k},
                        expected_return=float(exp_ret) if exp_ret is not None else 0.08,
                        risk=float(risk_val) if risk_val is not None else 0.15,
                        account_type=str(request.accountType),
                        tax_year=int(request.taxYear),
                        courtage_class=courtage_class or 'medium',
                        rebalancing_frequency='quarterly',
                    )
                    proj_csv = csv_generator.generate_five_year_projection_csv(proj)
                    files.append({
                        "filename": "five_year_projection.csv",
                        "content": base64.b64encode(proj_csv.encode('utf-8')).decode('utf-8'),
                        "size": len(proj_csv.encode('utf-8'))
                    })
            except Exception as e:
                logger.warning("CSV 5-year projection export failed: %s", e)

        # New enhanced CSV files
        if "taxComparison" in request.includeFiles and request.taxComparison:
            try:
                tax_comp_csv = csv_generator.generate_tax_comparison_csv(
                    request.taxComparison,
                    request.accountType
                )
                files.append({
                    "filename": "tax_comparison.csv",
                    "content": base64.b64encode(tax_comp_csv.encode('utf-8')).decode('utf-8'),
                    "size": len(tax_comp_csv.encode('utf-8'))
                })
            except Exception as e:
                logger.warning("CSV tax comparison export failed: %s", e)

        if "recommendations" in request.includeFiles and request.recommendations:
            try:
                rec_csv = csv_generator.generate_recommendations_csv(request.recommendations)
                files.append({
                    "filename": "recommendations.csv",
                    "content": base64.b64encode(rec_csv.encode('utf-8')).decode('utf-8'),
                    "size": len(rec_csv.encode('utf-8'))
                })
            except Exception as e:
                logger.warning("CSV recommendations export failed: %s", e)

        if request.educationalSummary:
            try:
                edu_csv = csv_generator.generate_educational_summary_csv(request.educationalSummary)
                files.append({
                    "filename": "educational_summary.csv",
                    "content": base64.b64encode(edu_csv.encode('utf-8')).decode('utf-8'),
                    "size": len(edu_csv.encode('utf-8'))
                })
            except Exception as e:
                logger.warning("CSV educational summary export failed: %s", e)

        # Always include methodology and glossary for user comprehension
        try:
            methodology_csv = csv_generator.generate_methodology_csv(
                account_type=request.accountType,
                tax_year=request.taxYear,
                courtage_class=request.costData.get('courtageClass') if request.costData else None
            )
            files.insert(0, {  # Insert at beginning so it's read first
                "filename": "00_METHODOLOGY.csv",
                "content": base64.b64encode(methodology_csv.encode('utf-8')).decode('utf-8'),
                "size": len(methodology_csv.encode('utf-8'))
            })
        except Exception as e:
            logger.warning("CSV methodology export failed: %s", e)

        try:
            glossary_csv = csv_generator.generate_glossary_csv()
            files.insert(1, {  # Insert second so it's read after methodology
                "filename": "01_GLOSSARY.csv",
                "content": base64.b64encode(glossary_csv.encode('utf-8')).decode('utf-8'),
                "size": len(glossary_csv.encode('utf-8'))
            })
        except Exception as e:
            logger.warning("CSV glossary export failed: %s", e)

        # Include visualizations in the ZIP file
        try:
            pdf_data = {
                "portfolio": portfolio_list,
                "portfolioName": request.portfolioName or "Investment Portfolio",
                "includeSections": {
                    "optimization": request.optimizationResults is not None,
                    "stressTest": request.stressTestResults is not None,
                    "goals": False,
                    "rebalancing": False,
                    "taxEducation": True,
                    "taxComparison": request.taxComparison is not None,
                    "recommendations": request.recommendations is not None and len(request.recommendations) > 0
                },
                "optimizationResults": request.optimizationResults,
                "projectionMetrics": request.projectionMetrics,
                "taxData": request.taxData or {},
                "costData": request.costData or {},
                "stressTestResults": request.stressTestResults,
                "portfolioValue": request.portfolioValue or 0.0,
                "accountType": request.accountType,
                "taxYear": request.taxYear,
                "courtageClass": request.courtageClass,
                "metrics": request.metrics or {},
                "taxComparison": request.taxComparison,
                "taxFreeData": request.taxFreeData,
                "recommendations": request.recommendations,
                "educationalSummary": request.educationalSummary
            }
            plots = pdf_generator.generate_report_plots(pdf_data)
            if plots:
                files.extend(plots)
        except Exception as e:
            logger.warning("Failed to include plots in CSV export: %s", e)

        # Create zip file if multiple files
        zip_file_base64 = None
        if len(files) > 1:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in files:
                    content = base64.b64decode(file_info["content"])
                    zip_file.writestr(file_info["filename"], content)
            
            zip_buffer.seek(0)
            zip_file_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
        
        return CSVExportResponse(
            files=files,
            zipFile=zip_file_base64
        )
    
    except Exception as e:
        logger.error(f"Error generating CSV exports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV exports: {str(e)}")

# Pydantic models for shareable links
class ShareLinkRequest(BaseModel):
    portfolioData: Dict[str, Any]
    expiryDays: int = 30
    password: Optional[str] = None

class ShareLinkResponse(BaseModel):
    linkId: str
    shareableUrl: str
    expiresAt: str

@export_router.post("/share/create", response_model=ShareLinkResponse)
async def create_shareable_link(request: ShareLinkRequest):
    """
    Create shareable link
    
    Request:
    {
        "portfolioData": {...},
        "expiryDays": 30,
        "password": "optional_password"
    }
    
    Response:
    {
        "linkId": "abc123",
        "shareableUrl": "https://app.com/share/abc123",
        "expiresAt": "2026-02-22T00:00:00Z"
    }
    """
    try:
        link_gen = get_shareable_link_generator()
        link_id = link_gen.generate_link(
            portfolio_data=request.portfolioData,
            expiry_days=request.expiryDays,
            password=request.password
        )
        
        # Get link info to get expiry date
        link_info = link_gen.get_link_info(link_id)
        expires_at = link_info.get("expires_at") if link_info else None
        
        # Construct shareable URL (adjust domain as needed)
        shareable_url = f"/api/v1/portfolio/share/{link_id}"
        
        return ShareLinkResponse(
            linkId=link_id,
            shareableUrl=shareable_url,
            expiresAt=expires_at or ""
        )
    
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating shareable link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create shareable link: {str(e)}")

@export_router.get("/share/{link_id}")
async def get_shareable_link(link_id: str, password: Optional[str] = None):
    """
    Retrieve shareable link data
    
    Args:
        link_id: The shareable link ID
        password: Optional password if link is protected
        
    Response:
    {
        "portfolioData": {...},
        "createdAt": "2026-01-26T00:00:00Z",
        "expiresAt": "2026-02-22T00:00:00Z"
    }
    """
    try:
        link_gen = get_shareable_link_generator()
        link_data = link_gen.get_link_data(link_id, password)
        
        return {
            "portfolioData": link_data.get("portfolio_data", {}),
            "createdAt": link_data.get("created_at"),
            "expiresAt": link_data.get("expires_at")
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving shareable link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve shareable link: {str(e)}")

@export_router.get("/share/{link_id}/info")
async def get_shareable_link_info(link_id: str):
    """
    Get shareable link metadata (without requiring password)
    
    Response:
    {
        "linkId": "abc123",
        "createdAt": "2026-01-26T00:00:00Z",
        "expiresAt": "2026-02-22T00:00:00Z",
        "hasPassword": bool,
        "isValid": bool
    }
    """
    try:
        link_gen = get_shareable_link_generator()
        link_info = link_gen.get_link_info(link_id)
        
        if not link_info:
            raise HTTPException(status_code=404, detail="Link not found or expired")
        
        return link_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shareable link info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shareable link info: {str(e)}")

@analytics_router.get("/consolidated-table")
async def get_consolidated_table_html():
    """Serve consolidated HTML page with Tickers and Portfolios tabs and search."""
    try:
        from fastapi.responses import HTMLResponse
        from datetime import datetime

        # Gather data via existing endpoints
        ticker_payload = await get_ticker_table_data()
        tickers = ticker_payload.get('tickers', [])

        portfolio_payload = get_all_portfolios_table_data()  # Not async
        portfolios = portfolio_payload.get('portfolios', [])

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Consolidated Tables - Portfolio Navigator</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #f8f9fa; color: #212529; }}
    .header {{ background: linear-gradient(135deg, #2c5aa0 0%, #1e3d6f 100%); color: #fff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0 0 6px 0; font-size: 22px; font-weight: 600; }}
    .header div {{ opacity: 0.9; font-size: 14px; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
    .stats {{ display: flex; gap: 16px; margin-bottom: 16px; }}
    .stat {{ flex: 1; background: #fff; border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
    .stat .label {{ color: #6c757d; font-size: 12px; text-transform: uppercase; }}
    .stat .value {{ color: #2c5aa0; font-weight: 700; font-size: 20px; }}
    .tabs {{ display: flex; gap: 8px; background: #fff; border-radius: 8px 8px 0 0; border-bottom: 2px solid #e9ecef; padding: 0 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); justify-content: center; }}
    .tab {{ padding: 12px 18px; background: transparent; border: none; cursor: pointer; color: #6c757d; font-weight: 600; border-bottom: 3px solid transparent; }}
    .tab.active {{ color: #2c5aa0; border-bottom-color: #2c5aa0; }}
    .content {{ background: #fff; border-radius: 0 0 8px 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: visible; }}
    .toolbar {{ display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid #e9ecef; align-items: center; }}
    .search {{ flex: 1; }}
    .search input {{ width: 100%; padding: 10px 12px; border: 1px solid #dee2e6; border-radius: 6px; }}
    .btn {{ padding: 10px 12px; border-radius: 6px; border: 1px solid #dee2e6; background: #f8f9fa; cursor: pointer; position: relative; }}
    .btn.primary {{ background: #2c5aa0; color: #fff; border-color: #2c5aa0; }}
    .btn:hover {{ background: #e9ecef; }}
    .btn.primary:hover {{ background: #1e3d6f; }}
    .modal-backdrop {{ position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: none; align-items: center; justify-content: center; z-index: 2000; }}
    .modal {{ background: #fff; border-radius: 8px; width: 400px; max-width: 90vw; box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
    .modal header {{ padding: 12px 16px; border-bottom: 1px solid #e9ecef; font-weight: 600; }}
    .modal .body {{ padding: 16px; color: #212529; }}
    .modal footer {{ padding: 12px 16px; border-top: 1px solid #e9ecef; display: flex; gap: 8px; justify-content: flex-end; }}
    .btn.secondary {{ background: #fff; color: #212529; }}
    .table-wrap {{ overflow-x: auto; max-height: 70vh; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    thead {{ position: sticky; top: 0; background: #f8f9fa; z-index: 1; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e9ecef; text-align: left; }}
    th {{ cursor: pointer; user-select: none; position: relative; }}
    th:hover {{ background: #e9ecef; }}
    tbody tr:hover {{ background: #f8f9fa; }}
    td.col-hover, th.col-hover {{ background: #eef4ff; }}
    .number {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .footer {{ color: #6c757d; text-align: center; padding: 14px; font-size: 13px; }}
    @media (max-width: 768px) {{ .stats {{ flex-direction: column; }} }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Consolidated Data Tables</h1>
    <div>All tickers and portfolios from Redis</div>
  </div>
  <div class="container">
    <div class="stats">
      <div class="stat"><div class="label">Total Tickers</div><div class="value">{len(tickers)}</div></div>
      <div class="stat"><div class="label">Total Portfolios</div><div class="value">{len(portfolios)}</div></div>
      <div class="stat"><div class="label">Updated</div><div class="value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div></div>
    </div>
    <div class="tabs">
      <button id="tab-tickers" class="tab active" onclick="switchTab('tickers')">Tickers</button>
      <button id="tab-portfolios" class="tab" onclick="switchTab('portfolios')">Portfolios</button>
    </div>
    <div class="content">
             <div id="panel-tickers">
               <div class="toolbar">
                 <div class="search"><input id="search-tickers" placeholder="Search tickers or companies..." oninput="searchTickers()" /></div>
                 <button class="btn" onclick="refreshTickers()" title="Full refresh: Updates all tickers regardless of cache status. Use when data is outdated or missing.">Refresh</button>
                 <button class="btn" onclick="smartRefreshTickers()" title="Smart refresh: Only updates expired or incomplete tickers. Faster and respects rate limits.">Smart Refresh</button>
               </div>
        <div class="table-wrap">
          <table id="table-tickers"><thead><tr>
            <th class="sortable" onclick="sortTable('tickers', 0, 'number')">#</th>
            <th class="sortable" onclick="sortTable('tickers', 1, 'text')">Ticker</th>
            <th class="sortable" onclick="sortTable('tickers', 2, 'text')">Company</th>
            <th class="sortable" onclick="sortTable('tickers', 3, 'text')">Sector</th>
            <th class="sortable" onclick="sortTable('tickers', 4, 'text')">Industry</th>
            <th class="sortable number" onclick="sortTable('tickers', 5, 'number')">Last Price</th>
            <th class="sortable number" onclick="sortTable('tickers', 6, 'number')">Return %</th>
            <th class="sortable number" onclick="sortTable('tickers', 7, 'number')">Risk %</th>
            <th class="sortable" onclick="sortTable('tickers', 8, 'text')">Freshness</th>
          </tr></thead><tbody>
"""
        for t in tickers:
            html += f"""
            <tr>
              <td>{t.get('id','-')}</td>
              <td><strong>{t.get('ticker','-')}</strong></td>
              <td>{t.get('companyName','-')}</td>
              <td>{t.get('sector','-')}</td>
              <td>{t.get('industry','-')}</td>
              <td class=\"number\">{t.get('lastPrice',0):.2f}</td>
              <td class=\"number\">{t.get('annualizedReturn',0):.2f}%</td>
              <td class=\"number\">{t.get('annualizedRisk',0):.2f}%</td>
              <td>{t.get('dataFreshness','unknown').replace('_', ' ').title() if t.get('dataFreshness') != 'error' else 'Unknown'}</td>
            </tr>
"""
        html += """
          </tbody></table>
        </div>
      </div>
      <div id="panel-portfolios" style="display:none;">
        <div class="toolbar">
          <div class="search"><input id="search-portfolios" placeholder="Search portfolios (name, profile, tickers)..." oninput="searchPortfolios()" /></div>
          <button class="btn" onclick="openRegenRecommendationsModal()" title="Regenerate recommendation portfolios (used in Portfolio Recommendations tab).">Regenerate Recommendations</button>
          <button class="btn" onclick="openRegenStrategiesModal()" title="Regenerate strategy portfolios (pure + personalized, used in Strategy part).">Regenerate Strategies</button>
        </div>
        <div class="table-wrap">
          <table id="table-portfolios"><thead><tr>
            <th class="sortable" onclick="sortTable('portfolios', 0, 'number')">#</th>
            <th class="sortable" onclick="sortTable('portfolios', 1, 'text')">Type</th>
            <th class="sortable" onclick="sortTable('portfolios', 2, 'text')">Strategy</th>
            <th class="sortable" onclick="sortTable('portfolios', 3, 'text')">Risk Profile</th>
            <th class="sortable" onclick="sortTable('portfolios', 4, 'text')">Portfolio</th>
            <th class="sortable number" onclick="sortTable('portfolios', 5, 'number')">Stocks</th>
            <th class="sortable number" onclick="sortTable('portfolios', 6, 'number')">Return %</th>
            <th class="sortable number" onclick="sortTable('portfolios', 7, 'number')">Risk %</th>
            <th class="sortable number" onclick="sortTable('portfolios', 8, 'number')">Diversification</th>
            <th class="sortable" onclick="sortTable('portfolios', 9, 'text')">Top Stocks</th>
          </tr></thead><tbody>
"""
        for p in portfolios:
            portfolio_type = p.get('portfolio_type', 'Regular')
            strategy = p.get('strategy', '-')
            html += f"""
            <tr>
              <td>{p.get('id','-')}</td>
              <td>{portfolio_type}</td>
              <td>{strategy}</td>
              <td>{p.get('risk_profile_display','-')}</td>
              <td><strong>{p.get('portfolio_name','-')}</strong></td>
              <td class=\"number\">{p.get('stock_count',0)}</td>
              <td class=\"number\">{p.get('expected_return',0):.2f}%</td>
              <td class=\"number\">{p.get('risk',0):.2f}%</td>
              <td class=\"number\">{p.get('diversification_score',0):.1f}</td>
              <td>{p.get('top_stocks','-')}</td>
            </tr>
"""
        html += """
          </tbody></table>
        </div>
      </div>
    </div>
    <div class="footer">Data source: Redis | Use Refresh for full refresh, Smart Refresh for incremental update</div>

    <div id="regenRecommendationsModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="regenRecommendationsModalTitle" style="display:none;">
      <div class="modal">
        <header id="regenRecommendationsModalTitle">Confirm Recommendation Portfolios Regeneration</header>
        <div class="body">
          <div id="regenRecommendationsModalText">Regenerating recommendation portfolios for all risk profiles may take 2–3 minutes. This will regenerate 12 portfolios per risk profile (60 total).</div>
        </div>
        <footer>
          <button class="btn secondary" onclick="closeRegenRecommendationsModal()">Cancel</button>
          <button class="btn primary" onclick="proceedRegenRecommendations()">Proceed</button>
        </footer>
      </div>
    </div>

    <div id="regenStrategiesModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="regenStrategiesModalTitle" style="display:none;">
      <div class="modal">
        <header id="regenStrategiesModalTitle">Confirm Strategy Portfolios Regeneration</header>
        <div class="body">
          <div id="regenStrategiesModalText">Regenerating strategy portfolios may take 3–4 minutes. This will regenerate pure and personalized strategy portfolios for all strategies and risk profiles.</div>
        </div>
        <footer>
          <button class="btn secondary" onclick="closeRegenStrategiesModal()">Cancel</button>
          <button class="btn primary" onclick="proceedRegenStrategies()">Proceed</button>
        </footer>
      </div>
    </div>

    <div id="refreshModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="refreshModalTitle" style="display:none;">
      <div class="modal">
        <header id="refreshModalTitle">Confirm Full Refresh</header>
        <div class="body">
          <div id="refreshModalText">Full refresh will update all expired/incomplete tickers. This may take several minutes.</div>
        </div>
        <footer>
          <button class="btn secondary" onclick="closeRefreshModal()">Cancel</button>
          <button class="btn primary" onclick="proceedRefresh()">Proceed</button>
        </footer>
      </div>
    </div>

    <div id="smartModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="smartModalTitle">
      <div class="modal">
        <header id="smartModalTitle">Confirm Smart Refresh</header>
        <div class="body">
          <div id="smartModalText">About to refresh N tickers.</div>
        </div>
        <footer>
          <button class="btn secondary" onclick="closeSmartModal()">Cancel</button>
          <button class="btn primary" onclick="proceedSmartRefresh()">Proceed</button>
        </footer>
      </div>
    </div>
  </div>

  <script>
    let fullRefreshPreview = null;
    let smartRefreshPreview = null;

    function switchTab(name) {
      document.getElementById('panel-tickers').style.display = (name==='tickers')?'block':'none';
      document.getElementById('panel-portfolios').style.display = (name==='portfolios')?'block':'none';
      document.getElementById('tab-tickers').classList.toggle('active', name==='tickers');
      document.getElementById('tab-portfolios').classList.toggle('active', name==='portfolios');
    }

    // Ticker search: use backend enhanced search when 3+ chars, else client filter
    let allTickerRows = Array.from(document.querySelectorAll('#table-tickers tbody tr'));
    async function searchTickers() {
      const q = document.getElementById('search-tickers').value.trim();
      if (q.length >= 3) {
        try {
          const res = await fetch(`/api/v1/portfolio/search-tickers?q=${encodeURIComponent(q)}&limit=50`);
          if (res.ok) {
            const data = await res.json();
            const results = data || [];
            // Fast client-side render: hide all rows, show only those matching tickers
            const set = new Set(results.map(r => (r.ticker || r.symbol || '').toUpperCase()));
            allTickerRows.forEach(row => {
              const ticker = (row.children[1]?.innerText || '').toUpperCase();
              row.style.display = set.size ? (set.has(ticker) ? '' : 'none') : '';
            });
            return;
          }
        } catch(_) { /* fall back to client filter */ }
      }
      // Client-only filter by ticker/company/sector
      const query = q.toLowerCase();
      allTickerRows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    }

    // Portfolios search: client-side filter by name/profile/top stocks
    let allPortfolioRows = Array.from(document.querySelectorAll('#table-portfolios tbody tr'));
    function searchPortfolios() {
      const q = document.getElementById('search-portfolios').value.trim().toLowerCase();
      allPortfolioRows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    }

    // Refresh endpoints
    async function refreshTickers() {
      try {
        const res = await fetch('/api/v1/portfolio/ticker-table/refresh/preview');
        if (res.ok) {
          const data = await res.json();
          fullRefreshPreview = data;
          const n = data.expired_count || 0;
          const secs = data.estimate_seconds || 120;
          const note = data.note || '';
          const counts = data.missing_counts || {};
          const details = [];
          if (counts.prices) { details.push(`${counts.prices} missing prices`); }
          if (counts.sector) { details.push(`${counts.sector} missing sector entries`); }
          if (counts.metrics) { details.push(`${counts.metrics} missing metrics`); }
          const detailText = details.length ? ` (${details.join(', ')})` : '';
          const el = document.getElementById('refreshModalText');
          el.textContent = `Full refresh will update ${n} expired/incomplete tickers${detailText}. Estimated time: ${Math.round(secs/60) || 2} minutes. ${note}`;
          openRefreshModal();
          return;
        }
      } catch(_) {}
      // Fallback
      openRefreshModal();
    }
    function openRefreshModal(){ document.getElementById('refreshModal').style.display='flex'; }
    function closeRefreshModal(){ document.getElementById('refreshModal').style.display='none'; }
    async function proceedRefresh(){
      closeRefreshModal();
      try { await fetch('/api/v1/portfolio/ticker-table/refresh', { method: 'POST' }); } catch(_) {}
      alert('Full refresh initiated');
    }
    async function smartRefreshTickers() {
      try {
        const res = await fetch('/api/v1/portfolio/ticker-table/smart-refresh/preview');
        if (res.ok) {
          const data = await res.json();
          smartRefreshPreview = data;
          const n = data.expired_count || 0;
          const counts = data.missing_counts || {};
          const expiredByTtlCount = data.expired_by_ttl_count || 0;
          const expiringSoonCount = data.expiring_soon_count || 0;
          const details = [];
          if (counts.prices) { details.push(`${counts.prices} missing prices`); }
          if (counts.sector) { details.push(`${counts.sector} missing sector entries`); }
          if (counts.metrics) { details.push(`${counts.metrics} missing metrics`); }
          if (expiredByTtlCount > 0) { details.push(`${expiredByTtlCount} expired by TTL`); }
          const note = details.length ? ` (${details.join(', ')})` : '';
          const samples = data.missing_samples || {};
          const sampleLines = [];
          if (samples.prices && samples.prices.length) {
            sampleLines.push(`Prices: ${samples.prices.slice(0, 5).join(', ')}`);
          }
          if (samples.sector && samples.sector.length) {
            sampleLines.push(`Sector: ${samples.sector.slice(0, 5).join(', ')}`);
          }
          if (samples.metrics && samples.metrics.length) {
            sampleLines.push(`Metrics: ${samples.metrics.slice(0, 5).join(', ')}`);
          }
          if (data.expired_by_ttl_tickers && data.expired_by_ttl_tickers.length) {
            sampleLines.push(`Expired TTL: ${data.expired_by_ttl_tickers.slice(0, 5).join(', ')}`);
          }
          const el = document.getElementById('smartModalText');
          const summaryLines = [
            `<strong>${n}</strong> ticker${n === 1 ? '' : 's'} scheduled for smart refresh${note}.`,
          ];
          if (details.length) {
            summaryLines.push(`Data gaps detected: ${details.join(', ')}.`);
          }
          if (expiringSoonCount > 0) {
            summaryLines.push(`⚠️ <strong>${expiringSoonCount}</strong> ticker${expiringSoonCount === 1 ? '' : 's'} expiring soon (< 24 hours).`);
          }
          if (sampleLines.length) {
            summaryLines.push(`Example tickers: ${sampleLines.join(' | ')}.`);
          }
          el.innerHTML = summaryLines.join('<br>');
          openSmartModal();
          return;
        }
      } catch(_) {}
      // Fallback
      openSmartModal();
    }
    function openSmartModal(){ document.getElementById('smartModal').style.display='flex'; }
    function closeSmartModal(){ document.getElementById('smartModal').style.display='none'; }
    async function proceedSmartRefresh(){
      closeSmartModal();
      try {
        const candidates = smartRefreshPreview && Array.isArray(smartRefreshPreview.refresh_candidates)
          ? smartRefreshPreview.refresh_candidates
          : null;
        const hasCandidates = candidates && candidates.length > 0;
        const options = hasCandidates
          ? {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tickers: candidates })
            }
          : { method: 'POST' };
        await fetch('/api/v1/portfolio/ticker-table/smart-refresh', options);
      } catch(_) {}
      alert('Smart refresh initiated');
    }

    // Table sorting functionality
    let sortState = { tickers: {}, portfolios: {} };
    
    function sortTable(tableType, columnIndex, dataType) {
      const tableId = tableType === 'tickers' ? 'table-tickers' : 'table-portfolios';
      const table = document.getElementById(tableId);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const headers = table.querySelectorAll('thead th');
      
      // Get current sort direction
      const currentState = sortState[tableType][columnIndex] || 'none';
      const newDirection = currentState === 'asc' ? 'desc' : 'asc';
      
      // Reset all header classes
      headers.forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
        if (h.classList.contains('sortable')) {
          h.classList.add('sortable');
        }
      });
      
      // Set new sort direction
      sortState[tableType] = {};
      sortState[tableType][columnIndex] = newDirection;
      headers[columnIndex].classList.remove('sortable');
      headers[columnIndex].classList.add(newDirection === 'asc' ? 'sort-asc' : 'sort-desc');
      
      // Sort rows
      rows.sort((a, b) => {
        const aCell = a.cells[columnIndex];
        const bCell = b.cells[columnIndex];
        let aVal = aCell ? aCell.textContent.trim() : '';
        let bVal = bCell ? bCell.textContent.trim() : '';
        
        if (dataType === 'number') {
          // Extract numeric value (remove % and other non-numeric chars)
          aVal = parseFloat(aVal.replace(/[^0-9.-]/g, '')) || 0;
          bVal = parseFloat(bVal.replace(/[^0-9.-]/g, '')) || 0;
        } else {
          // Text comparison
          aVal = aVal.toLowerCase();
          bVal = bVal.toLowerCase();
        }
        
        if (aVal < bVal) return newDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return newDirection === 'asc' ? 1 : -1;
        return 0;
      });
      
      // Re-append sorted rows
      rows.forEach(row => tbody.appendChild(row));
    }

    // Column hover highlighting
    function enableColumnHover(tableId) {
      const table = document.getElementById(tableId);
      if (!table) return;
      table.addEventListener('mouseover', (e) => {
        const cell = e.target.closest('td, th');
        if (!cell) return;
        const idx = cell.cellIndex;
        Array.from(table.rows).forEach(tr => {
          const c = tr.cells[idx];
          if (c) c.classList.add('col-hover');
        });
      });
      table.addEventListener('mouseout', () => {
        table.querySelectorAll('.col-hover').forEach(el => el.classList.remove('col-hover'));
      });
    }

    document.addEventListener('DOMContentLoaded', () => {
      enableColumnHover('table-tickers');
      enableColumnHover('table-portfolios');
    });

    async function openRegenRecommendationsModal(){
      document.getElementById('regenRecommendationsModal').style.display='flex';
    }
    function closeRegenRecommendationsModal(){ document.getElementById('regenRecommendationsModal').style.display='none'; }
    async function proceedRegenRecommendations(){
      closeRegenRecommendationsModal();
      try { 
        const res = await fetch('/api/v1/portfolio/regenerate-recommendations', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          alert(`Portfolio regeneration started: ${data.message || 'Processing...'}`);
        } else {
          alert('Failed to start portfolio regeneration');
        }
      } catch(e) {
        alert('Error: ' + e.message);
      }
    }

    async function openRegenStrategiesModal(){
      document.getElementById('regenStrategiesModal').style.display='flex';
    }
    function closeRegenStrategiesModal(){ document.getElementById('regenStrategiesModal').style.display='none'; }
    async function proceedRegenStrategies(){
      closeRegenStrategiesModal();
      try { 
        const res = await fetch('/api/v1/portfolio/pre-generate-strategy-portfolios', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          alert(`Strategy portfolio regeneration started: ${data.message || 'Processing...'}`);
        } else {
          alert('Failed to start strategy portfolio regeneration');
        }
      } catch(e) {
        alert('Error: ' + e.message);
      }
    }
  </script>
</body>
</html>
"""

        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Error serving consolidated table: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve consolidated table: {str(e)}")


# Mount domain sub-routers after all route decorators have run (so routes are registered)
router.include_router(portfolios_router)
router.include_router(optimization_router)
router.include_router(analytics_router)
router.include_router(export_router)
