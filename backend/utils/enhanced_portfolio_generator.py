#!/usr/bin/env python3
"""
Enhanced Portfolio Generator System
Generates 12 unique portfolios per risk profile using deterministic algorithms
Automatically stores portfolios in Redis with smart regeneration
"""

import random
import hashlib
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .portfolio_stock_selector import PortfolioStockSelector
from .port_analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)

class EnhancedPortfolioGenerator:
    """
    Enhanced Portfolio Generator that creates 12 unique portfolios per risk profile
    Uses deterministic algorithms for consistent generation and smart Redis storage
    """
    
    def __init__(self, data_service, portfolio_analytics: PortfolioAnalytics):
        self.data_service = data_service  # Can be RedisFirstDataService or EnhancedDataFetcher
        self.portfolio_analytics = portfolio_analytics
        self.PORTFOLIOS_PER_PROFILE = 12
        self.PORTFOLIO_TTL_DAYS = 7  # Shorter than data TTL (28 days)
        self.redis_client = data_service.redis_client if hasattr(data_service, 'redis_client') else data_service.r
        
        # Portfolio names for each risk profile
        self.PORTFOLIO_NAMES = {
            'very-conservative': [
                'Capital Preservation Portfolio',
                'Defensive Income Portfolio',
                'Stable Growth Portfolio',
                'Conservative Dividend Portfolio',
                'Low-Risk Income Portfolio',
                'Defensive Growth Portfolio',
                'Stable Value Portfolio',
                'Conservative Blend Portfolio',
                'Income Preservation Portfolio',
                'Defensive Core Portfolio',
                'Stable Income Portfolio',
                'Conservative Growth Portfolio'
            ],
            'conservative': [
                'Income & Stability Portfolio',
                'Balanced Conservative Portfolio',
                'Moderate Growth Portfolio',
                'Conservative Growth Portfolio',
                'Stable Income Portfolio',
                'Balanced Income Portfolio',
                'Conservative Blend Portfolio',
                'Income Growth Portfolio',
                'Stable Core Portfolio',
                'Conservative Core Portfolio',
                'Balanced Stability Portfolio',
                'Growth Income Portfolio'
            ],
            'moderate': [
                'Core Diversified Portfolio',
                'Balanced Growth Portfolio',
                'Moderate Growth Portfolio',
                'Diversified Core Portfolio',
                'Balanced Core Portfolio',
                'Growth Diversified Portfolio',
                'Core Growth Portfolio',
                'Balanced Diversified Portfolio',
                'Moderate Core Portfolio',
                'Diversified Growth Portfolio',
                'Core Balanced Portfolio',
                'Growth Core Portfolio'
            ],
            'aggressive': [
                'Growth Focused Portfolio',
                'High Growth Portfolio',
                'Aggressive Growth Portfolio',
                'Growth Maximizer Portfolio',
                'High Return Portfolio',
                'Aggressive Core Portfolio',
                'Growth Core Portfolio',
                'High Growth Core Portfolio',
                'Aggressive Diversified Portfolio',
                'Growth Diversified Portfolio',
                'High Return Core Portfolio',
                'Aggressive Focus Portfolio'
            ],
            'very-aggressive': [
                'Maximum Growth Portfolio',
                'Ultra Aggressive Portfolio',
                'High Risk Growth Portfolio',
                'Maximum Return Portfolio',
                'Ultra Growth Portfolio',
                'High Risk Core Portfolio',
                'Maximum Core Portfolio',
                'Ultra Return Portfolio',
                'High Risk Diversified Portfolio',
                'Maximum Diversified Portfolio',
                'Ultra Growth Core Portfolio',
                'High Risk Focus Portfolio'
            ]
        }
        
        # Portfolio descriptions for each risk profile
        self.PORTFOLIO_DESCRIPTIONS = {
            'very-conservative': [
                'Defensive strategy focused on stable dividend stocks and capital preservation. Ideal for investors who prioritize safety over growth.',
                'Conservative approach emphasizing income generation with minimal risk exposure. Suitable for retirees and conservative investors.',
                'Balanced conservative strategy offering modest growth potential while maintaining capital stability.',
                'Income-focused portfolio with emphasis on dividend-paying stocks from stable sectors.',
                'Ultra-conservative approach minimizing volatility while providing steady income streams.',
                'Defensive growth strategy with focus on companies with stable earnings and low volatility.',
                'Value-oriented portfolio emphasizing companies with strong fundamentals and stable performance.',
                'Conservative blend of income and growth stocks with emphasis on stability.',
                'Income preservation strategy protecting capital while generating consistent returns.',
                'Core conservative holdings providing foundation for long-term wealth preservation.',
                'Stable income generation with focus on essential service companies.',
                'Conservative growth approach with emphasis on established, stable companies.'
            ],
            'conservative': [
                'Balanced conservative strategy offering growth potential with moderate risk exposure.',
                'Conservative approach with focus on stable growth and income generation.',
                'Moderate growth strategy within conservative risk parameters.',
                'Conservative growth portfolio emphasizing established companies with growth potential.',
                'Stable income strategy with focus on reliable dividend-paying stocks.',
                'Balanced income approach combining growth and income generation.',
                'Conservative blend strategy with emphasis on stability and modest growth.',
                'Income growth strategy focusing on companies with growing dividend payments.',
                'Stable core holdings providing foundation for conservative growth.',
                'Conservative core strategy emphasizing quality and stability.',
                'Balanced stability approach with focus on risk management.',
                'Growth income strategy combining conservative growth with income generation.'
            ],
            'moderate': [
                'Core diversified strategy offering balanced growth and risk exposure.',
                'Balanced growth approach with emphasis on diversification across sectors.',
                'Moderate growth strategy with balanced risk-return profile.',
                'Diversified core holdings providing foundation for balanced growth.',
                'Balanced core strategy emphasizing stability and growth potential.',
                'Growth diversification approach with focus on sector balance.',
                'Core growth strategy with emphasis on established growth companies.',
                'Balanced diversification strategy combining growth and stability.',
                'Moderate core approach with focus on balanced risk exposure.',
                'Diversified growth strategy emphasizing sector diversification.',
                'Core balanced strategy with focus on risk-return optimization.',
                'Growth core approach emphasizing growth within moderate risk parameters.'
            ],
            'aggressive': [
                'Growth-focused strategy emphasizing high-growth potential companies.',
                'High growth approach with focus on emerging growth opportunities.',
                'Aggressive growth strategy maximizing growth potential with higher risk.',
                'Growth maximizer strategy focusing on highest growth potential stocks.',
                'High return strategy emphasizing companies with strong growth prospects.',
                'Aggressive core strategy with focus on growth-oriented holdings.',
                'Growth core approach emphasizing growth within aggressive parameters.',
                'High growth core strategy focusing on emerging growth companies.',
                'Aggressive diversification strategy combining growth and sector balance.',
                'Growth diversification approach emphasizing growth across sectors.',
                'High return core strategy focusing on strong growth prospects.',
                'Aggressive focus strategy emphasizing concentrated growth positions.'
            ],
            'very-aggressive': [
                'Maximum growth strategy targeting highest growth potential with maximum risk.',
                'Ultra aggressive approach emphasizing maximum growth opportunities.',
                'High risk growth strategy focusing on emerging and disruptive companies.',
                'Maximum return strategy targeting highest potential returns.',
                'Ultra growth approach emphasizing fastest growing companies.',
                'High risk core strategy with focus on maximum growth potential.',
                'Maximum core strategy emphasizing highest growth prospects.',
                'Ultra return strategy targeting maximum return potential.',
                'High risk diversification strategy combining maximum growth with sector balance.',
                'Maximum diversification strategy emphasizing growth across all sectors.',
                'Ultra growth core strategy focusing on fastest growing companies.',
                'High risk focus strategy emphasizing concentrated maximum growth positions.'
            ]
        }
    
    def generate_portfolio_bucket(self, risk_profile: str) -> List[Dict]:
        """Generate 12 unique portfolios for a specific risk profile efficiently with shared stock data"""
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Generating {self.PORTFOLIOS_PER_PROFILE} portfolios for {risk_profile} risk profile...")
        
        # Initialize stock selector ONCE for all portfolios
        stock_selector = PortfolioStockSelector(self.data_service)
        
        # Get stock data ONCE for all portfolios (will use cache after first call)
        logger.info(f"📊 Fetching stock data for {risk_profile} (shared across all portfolios)...")
        stock_fetch_start = time.time()
        _ = stock_selector._get_available_stocks_with_metrics()  # Prime the cache
        stock_fetch_time = time.time() - stock_fetch_start
        logger.info(f"⚡ Stock data fetched in {stock_fetch_time:.2f}s")
        
        portfolios = []
        
        for variation_id in range(self.PORTFOLIOS_PER_PROFILE):
            try:
                # Generate deterministic seed
                variation_seed = self._generate_variation_seed(risk_profile, variation_id)
                
                # Generate single portfolio using shared stock selector
                portfolio = self._generate_single_portfolio_deterministic(
                    risk_profile=risk_profile,
                    variation_seed=variation_seed,
                    variation_id=variation_id,
                    stock_selector=stock_selector  # Pass the shared selector
                )
                
                portfolios.append(portfolio)
                logger.debug(f"✅ Generated portfolio {variation_id + 1} for {risk_profile}")
                
            except Exception as e:
                logger.error(f"❌ Failed to generate portfolio {variation_id + 1} for {risk_profile}: {e}")
                # Generate fallback portfolio
                fallback = self._generate_fallback_portfolio(risk_profile, variation_id)
                portfolios.append(fallback)
        
        total_time = time.time() - start_time
        # Validate portfolio uniqueness
        unique_portfolios = self._ensure_portfolio_uniqueness(portfolios)
        if len(unique_portfolios) < len(portfolios):
            logger.warning(f"⚠️ Generated {len(portfolios)} portfolios but only {len(unique_portfolios)} are unique")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Successfully generated {len(unique_portfolios)} unique portfolios for {risk_profile} in {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/len(unique_portfolios):.3f}s per portfolio (with shared stock data)")
        return unique_portfolios
    
    async def generate_portfolio_bucket_async(self, risk_profile: str) -> List[Dict]:
        """Generate 12 unique portfolios for a specific risk profile (async version for parallel processing)"""
        logger.info(f"🚀 Generating {self.PORTFOLIOS_PER_PROFILE} portfolios for {risk_profile} risk profile (async)...")
        
        portfolios = []
        
        for variation_id in range(self.PORTFOLIOS_PER_PROFILE):
            try:
                # Generate deterministic seed
                variation_seed = self._generate_variation_seed(risk_profile, variation_id)
                
                # Generate single portfolio
                portfolio = self._generate_single_portfolio_deterministic(
                    risk_profile=risk_profile,
                    variation_seed=variation_seed,
                    variation_id=variation_id
                )
                
                portfolios.append(portfolio)
                logger.debug(f"✅ Generated portfolio {variation_id + 1} for {risk_profile}")
                
            except Exception as e:
                logger.error(f"❌ Failed to generate portfolio {variation_id + 1} for {risk_profile}: {e}")
                # Generate fallback portfolio
                fallback = self._generate_fallback_portfolio(risk_profile, variation_id)
                portfolios.append(fallback)
        
        logger.info(f"✅ Successfully generated {len(portfolios)} portfolios for {risk_profile} (async)")
        return portfolios
    
    def _generate_variation_seed(self, risk_profile: str, variation_id: int) -> int:
        """Generate deterministic seed for portfolio variation"""
        # Use a more robust seed generation to ensure uniqueness
        import hashlib
        
        # Create a unique seed string with more variation
        seed_string = f"{risk_profile}_{variation_id}_{variation_id * 7 + 13}"
        
        # Use SHA-256 hash for better distribution and convert to integer
        hash_object = hashlib.sha256(seed_string.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert first 8 characters of hash to integer
        seed_int = int(hash_hex[:8], 16)
        
        # Ensure positive and within reasonable range
        return abs(seed_int) % 1000000
    
    def _generate_single_portfolio_deterministic(self, risk_profile: str, variation_seed: int, variation_id: int, stock_selector=None) -> Dict:
        """Generate single portfolio using deterministic algorithm"""
        random.seed(variation_seed)
        
        # Get portfolio name and description
        name = self._get_portfolio_name(risk_profile, variation_id)
        description = self._get_portfolio_description(risk_profile, variation_id)
        
        # Use shared stock selector if provided, otherwise create new one
        if stock_selector is None:
            stock_selector = PortfolioStockSelector(self.data_service)
        
        allocations = stock_selector.select_stocks_for_risk_profile_deterministic(
            risk_profile, variation_seed
        )
        
        # Calculate portfolio metrics
        try:
            metrics = self.portfolio_analytics.calculate_real_portfolio_metrics({
                'allocations': allocations
            })
        except Exception as e:
            logger.warning(f"Failed to calculate metrics for {risk_profile}-{variation_id}: {e}")
            metrics = self._get_fallback_metrics(risk_profile)
        
        # Calculate data dependency hash
        data_dependency_hash = self._calculate_data_dependency_hash()
        
        return {
            'name': name,
            'description': description,
            'allocations': allocations,
            'expectedReturn': metrics.get('expected_return', 0.10),
            'risk': metrics.get('risk', 0.15),
            'diversificationScore': metrics.get('diversification_score', 75.0),
            'sectorBreakdown': metrics.get('sector_breakdown', {}),
            'variation_id': variation_id,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'data_dependency_hash': data_dependency_hash
        }
    
    def _get_portfolio_name(self, risk_profile: str, variation_id: int) -> str:
        """Get portfolio name for specific risk profile and variation"""
        names = self.PORTFOLIO_NAMES.get(risk_profile, [])
        if variation_id < len(names):
            return names[variation_id]
        return f"Portfolio {variation_id + 1}"
    
    def _get_portfolio_description(self, risk_profile: str, variation_id: int) -> str:
        """Get portfolio description for specific risk profile and variation"""
        descriptions = self.PORTFOLIO_DESCRIPTIONS.get(risk_profile, [])
        if variation_id < len(descriptions):
            return descriptions[variation_id]
        return f"Diversified portfolio based on {risk_profile} risk profile"
    
    def _ensure_portfolio_uniqueness(self, portfolios: List[Dict]) -> List[Dict]:
        """Ensure all portfolios have unique stock allocations"""
        unique_portfolios = []
        seen_allocations = set()
        
        for portfolio in portfolios:
            # Create a unique key for the portfolio based on stock symbols and allocations
            allocation_key = self._create_allocation_key(portfolio['allocations'])
            
            if allocation_key not in seen_allocations:
                seen_allocations.add(allocation_key)
                unique_portfolios.append(portfolio)
            else:
                logger.warning(f"⚠️ Duplicate portfolio detected: {portfolio['name']}")
        
        return unique_portfolios
    
    def _create_allocation_key(self, allocations: List[Dict]) -> str:
        """Create a unique key for portfolio allocations"""
        # Sort allocations by symbol for consistent key generation
        sorted_allocations = sorted(allocations, key=lambda x: x['symbol'])
        
        # Create key from symbols and allocations
        key_parts = [f"{alloc['symbol']}:{alloc['allocation']}" for alloc in sorted_allocations]
        return "|".join(key_parts)
    
    def _calculate_data_dependency_hash(self) -> str:
        """Calculate hash of current stock data state"""
        try:
            # Sample key stocks from each sector for state monitoring
            key_stocks = [
                'AAPL', 'MSFT', 'GOOGL', 'JPM', 'JNJ',  # Tech, Financial, Healthcare
                'PG', 'KO', 'VZ', 'XOM', 'CVX'           # Consumer, Energy
            ]
            
            state_data = {}
            for stock in key_stocks:
                try:
                    price_data = self.data_service.get_monthly_data(stock)
                    if price_data and 'prices' in price_data:
                        # Hash recent price data and volatility
                        recent_prices = price_data['prices'][-12:]  # Last 12 months
                        if len(recent_prices) >= 12:
                            # Calculate simple volatility
                            returns = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] 
                                     for i in range(1, len(recent_prices))]
                            volatility = sum(abs(r) for r in returns) / len(returns) if returns else 0
                            
                            state_data[stock] = {
                                'recent_prices': recent_prices[-3:],  # Last 3 months
                                'volatility': volatility,
                                'last_price': recent_prices[-1]
                            }
                except Exception as e:
                    logger.debug(f"Error processing {stock} for data hash: {e}")
                    continue
            
            # Create hash of state data
            state_json = json.dumps(state_data, sort_keys=True)
            return hashlib.md5(state_json.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating data dependency hash: {e}")
            return "error_hash"
    
    def _get_fallback_metrics(self, risk_profile: str) -> Dict:
        """Get fallback metrics when calculation fails"""
        fallback_metrics = {
            'very-conservative': {'expected_return': 0.06, 'risk': 0.12, 'diversification_score': 85.0},
            'conservative': {'expected_return': 0.08, 'risk': 0.18, 'diversification_score': 80.0},
            'moderate': {'expected_return': 0.12, 'risk': 0.25, 'diversification_score': 75.0},
            'aggressive': {'expected_return': 0.16, 'risk': 0.35, 'diversification_score': 70.0},
            'very-aggressive': {'expected_return': 0.20, 'risk': 0.45, 'diversification_score': 65.0}
        }
        return fallback_metrics.get(risk_profile, {'expected_return': 0.10, 'risk': 0.20, 'diversification_score': 75.0})
    
    def _generate_fallback_portfolio(self, risk_profile: str, variation_id: int) -> Dict:
        """Generate fallback portfolio when main generation fails"""
        logger.warning(f"Generating fallback portfolio for {risk_profile}-{variation_id}")
        
        return {
            'name': f"Fallback Portfolio {variation_id + 1}",
            'description': f"Fallback portfolio for {risk_profile} risk profile",
            'allocations': [
                {'symbol': 'AAPL', 'allocation': 40, 'name': 'Apple Inc.', 'assetType': 'stock'},
                {'symbol': 'MSFT', 'allocation': 35, 'name': 'Microsoft Corp.', 'assetType': 'stock'},
                {'symbol': 'JPM', 'allocation': 25, 'name': 'JPMorgan Chase & Co.', 'assetType': 'stock'}
            ],
            'expectedReturn': 0.10,
            'risk': 0.20,
            'diversificationScore': 75.0,
            'sectorBreakdown': {},
            'variation_id': variation_id,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'data_dependency_hash': 'fallback_hash'
        }
