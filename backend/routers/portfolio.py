from fastapi import APIRouter, HTTPException
from models.portfolio import PortfolioRequest, PortfolioResponse, PortfolioAllocation
from typing import List, Dict, Optional
import logging
from utils.enhanced_data_fetcher import enhanced_data_fetcher
from utils.ticker_store import ticker_store
from datetime import datetime

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