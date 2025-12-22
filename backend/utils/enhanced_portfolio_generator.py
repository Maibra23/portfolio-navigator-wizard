#!/usr/bin/env python3
"""
Enhanced Portfolio Generator System
Generates 12 unique portfolios per risk profile using deterministic algorithms
Automatically stores portfolios in Redis with smart regeneration
"""

import random
import os
import hashlib
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .portfolio_stock_selector import PortfolioStockSelector
from .enhanced_stock_selector import EnhancedStockSelector
from .port_analytics import PortfolioAnalytics
from .enhanced_portfolio_config import EnhancedPortfolioConfig

logger = logging.getLogger(__name__)

class EnhancedPortfolioGenerator:
    """
    Enhanced Portfolio Generator that creates 12 unique portfolios per risk profile
    Uses deterministic algorithms for consistent generation and smart Redis storage
    """
    
    def __init__(self, data_service, portfolio_analytics: PortfolioAnalytics):
        self.data_service = data_service  # Can be RedisFirstDataService or EnhancedDataFetcher
        self.portfolio_analytics = portfolio_analytics
        self.PORTFOLIOS_PER_PROFILE = 12  # Backend expects 12 portfolios per risk profile
        self.PORTFOLIO_TTL_DAYS = 7  # Shorter than data TTL (28 days)
        self.redis_client = data_service.redis_client if hasattr(data_service, 'redis_client') else data_service.r

        # Global uniqueness tracking - TTL longer than portfolio TTL to prevent cross-profile duplicates
        self.GLOBAL_SIGNATURE_TTL = 14  # 14 days to cover portfolio lifecycle
        # Reduce attempts for faster generation
        self.MAX_RETRY_ATTEMPTS = 1  # Reduced from 6 to 1 for speed
        
        # Uniqueness disabled globally (can re-enable via code change)
        self.dedup_bypass = True
        
        # Quality control configuration - Increased retries to ensure realistic portfolios
        self.MAX_QUALITY_RETRIES = 10  # Increased to ensure we find realistic portfolios
        
        # Load realistic quality control ranges from enhanced config
        from .enhanced_portfolio_config import EnhancedPortfolioConfig
        config = EnhancedPortfolioConfig()
        self.TARGET_RANGES = config.ENHANCED_QUALITY_CONTROL
        
        # Load return target gradation from enhanced config
        self.RETURN_TARGET_GRADATION = config.RETURN_TARGET_GRADATION
        
        # Load diversification variation from enhanced config
        self.DIVERSIFICATION_VARIATION = config.DIVERSIFICATION_VARIATION
        
        # Load stock count ranges from enhanced config
        self.STOCK_COUNT_RANGES = config.STOCK_COUNT_RANGES
        
        # Portfolio names for each risk profile
        self.PORTFOLIO_NAMES = {
            'very-conservative': [
                'Capital Shield Portfolio',
                'Income Fortress Portfolio',
                'Stability First Portfolio',
                'Dividend Guardian Portfolio',
                'Wealth Preservation Portfolio',
                'Safety Net Portfolio',
                'Steady Income Portfolio',
                'Conservative Haven Portfolio',
                'Risk-Minimizer Portfolio',
                'Defensive Anchor Portfolio',
                'Secure Income Portfolio',
                'Low-Volatility Core Portfolio'
            ],
            'conservative': [
                'Income Plus Growth Portfolio',
                'Moderate Shield Portfolio',
                'Quality Dividend Portfolio',
                'Steady Builder Portfolio',
                'Conservative Accumulation Portfolio',
                'Balanced Safety Portfolio',
                'Income Stability Portfolio',
                'Cautious Growth Portfolio',
                'Defensive Opportunity Portfolio',
                'Reliable Returns Portfolio',
                'Conservative Advantage Portfolio',
                'Stable Appreciation Portfolio'
            ],
            'moderate': [
                'Balanced Horizon Portfolio',
                'Core Diversification Portfolio',
                'Growth & Income Portfolio',
                'Strategic Balance Portfolio',
                'Diversified Opportunity Portfolio',
                'All-Equity Balanced Portfolio',
                'All-Weather Equity Portfolio',
                'Moderate Accumulator Portfolio',
                'Equilibrium Portfolio',
                'Diversified Foundation Portfolio',
                'Long-Term Balance Portfolio',
                'Multi-Strategy Core Portfolio'
            ],
            'aggressive': [
                'Growth Accelerator Portfolio',
                'Equity-Focused Portfolio',
                'Capital Appreciation Portfolio',
                'High-Octane Growth Portfolio',
                'Growth Maximizer Portfolio',
                'Performance Seeker Portfolio',
                'Dynamic Growth Portfolio',
                'Aggressive Builder Portfolio',
                'Growth Opportunity Portfolio',
                'Equity Advantage Portfolio',
                'Expansion Portfolio',
                'Growth-Driven Portfolio'
            ],
            'very-aggressive': [
                'Maximum Velocity Portfolio',
                'Ultra-Growth Portfolio',
                'Peak Performance Portfolio',
                'Exponential Growth Portfolio',
                'High-Conviction Equity Portfolio',
                'Frontier Growth Portfolio',
                'Acceleration Portfolio',
                'Maximum Alpha Portfolio',
                'Elite Growth Portfolio',
                'Breakout Opportunity Portfolio',
                'Next-Generation Portfolio',
                'Momentum Maximizer Portfolio'
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
    
    def generate_portfolio_bucket(self, risk_profile: str, use_parallel: bool = True) -> List[Dict]:
        """Generate 9 unique portfolios for a specific risk profile with ticker exclusion
        
        Args:
            risk_profile: Risk profile to generate portfolios for
            use_parallel: If True, use parallel generation (3-4x faster)
        """
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Generating {self.PORTFOLIOS_PER_PROFILE} portfolios for {risk_profile} risk profile...")
        
        # Initialize enhanced stock selector ONCE for all portfolios
        stock_selector = EnhancedStockSelector(self.data_service)
        
        # Get stock data ONCE for all portfolios (will use cache after first call)
        logger.info(f"📊 Fetching stock data for {risk_profile} (shared across all portfolios)...")
        stock_fetch_start = time.time()
        available_stocks = stock_selector._get_available_stocks_with_metrics()  # Get actual data
        stock_fetch_time = time.time() - stock_fetch_start
        logger.info(f"⚡ Stock data fetched in {stock_fetch_time:.2f}s")

        # Validate stock pool sufficiency (pre-flight)
        try:
            pool_ok, pool_stats = self._validate_stock_pool_sufficiency(stock_selector, available_stocks, risk_profile)
            if not pool_ok:
                logger.warning(f"⚠️ Stock pool may be insufficient for uniqueness: {pool_stats}")
        except Exception as e:
            logger.debug(f"Pool validation skipped: {e}")
        
        # Generate portfolios with ticker exclusion
        portfolios = self._generate_portfolios_with_ticker_exclusion(risk_profile, stock_selector, available_stocks)
        
        # Precompute and store overlap matrix for session-level diversity
        try:
            self._compute_and_store_overlap_matrix(portfolios, risk_profile)
        except Exception as e:
            logger.debug(f"Overlap matrix computation skipped: {e}")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Successfully generated {len(portfolios)} unique portfolios for {risk_profile} in {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/len(portfolios):.3f}s per portfolio (with ticker exclusion)")

        # Store portfolios in Redis using the standard format
        try:
            from .redis_portfolio_manager import RedisPortfolioManager
            portfolio_manager = RedisPortfolioManager(self.redis_client)
            storage_success = portfolio_manager.store_portfolio_bucket(risk_profile, portfolios)
            if storage_success:
                logger.info(f"✅ Successfully stored {len(portfolios)} portfolios for {risk_profile} in Redis")
            else:
                logger.warning(f"⚠️ Failed to store portfolios for {risk_profile} in Redis")
        except Exception as e:
            logger.error(f"❌ Error storing portfolios for {risk_profile}: {e}")

        # Store Top Pick for quick retrieval by API (expectedReturn-based)
        try:
            def _score(p):
                return float(p.get('expectedReturn', 0.0))
            top = max(portfolios, key=_score)
            cache_key = f"portfolio:top_pick:{risk_profile}"
            self.redis_client.setex(cache_key, self.PORTFOLIO_TTL_DAYS * 24 * 3600, json.dumps(top))
        except Exception as e:
            logger.debug(f"Top pick store skipped: {e}")
        return portfolios
    
    def _generate_portfolios_with_ticker_exclusion(self, risk_profile: str, stock_selector, available_stocks: List[Dict]) -> List[Dict]:
        """Generate portfolios with ticker exclusion to prevent reuse across portfolios"""
        logger.info(f"🎯 Generating portfolios with ticker exclusion for {risk_profile}...")
        
        portfolios = []
        ticker_usage_count = {}  # Track ticker usage count across all portfolios (not just set)
        config = EnhancedPortfolioConfig()
        
        # NEW: Enforce composition uniqueness within this risk profile
        used_compositions = set()
        MAX_RETRIES_PER_PORTFOLIO = 5
        
        for portfolio_index in range(self.PORTFOLIOS_PER_PROFILE):
            logger.info(f"📊 Generating portfolio {portfolio_index + 1}/{self.PORTFOLIOS_PER_PROFILE}")
            
            try:
                # Get return target for this portfolio using adaptive targeting
                return_target = config.get_adaptive_return_target(risk_profile, available_stocks, portfolio_index)
                
                # Allow more ticker reuse for higher-risk profiles to explore more diverse combinations
                # This enables different portfolio compositions using same tickers with different weights
                reuse_map = {
                    'very-conservative': (1, 2),  # Keep strict for conservative
                    'conservative': (1, 2),       # Keep strict for conservative
                    'moderate': (2, 3),           # Allow more reuse for diversity
                    'aggressive': (2, 3),         # Allow more reuse for diversity
                    'very-aggressive': (2, 4)     # Allow even more reuse for maximum diversity
                }
                max_reuse_first, max_reuse_last = reuse_map.get(risk_profile, (1, 2))
                max_reuse = max_reuse_first if portfolio_index < 6 else max_reuse_last
                
                # Filter out heavily used tickers
                available_tickers = []
                for stock in available_stocks:
                    ticker = stock.get('symbol', stock.get('ticker'))
                    usage_count = ticker_usage_count.get(ticker, 0)
                    if usage_count < max_reuse:
                        available_tickers.append(stock)
                
                if len(available_tickers) < 3:  # Need at least 3 stocks per portfolio
                    logger.warning(f"⚠️ Insufficient available tickers for portfolio {portfolio_index + 1}, expanding pool")
                    # Expand to all stocks but prefer less used ones
                    available_tickers = sorted(available_stocks, 
                                             key=lambda s: ticker_usage_count.get(s.get('symbol', s.get('ticker')), 0))
                
                # Generate portfolio with retries to enforce unique composition
                retry = 0
                generated = False
                while retry < MAX_RETRIES_PER_PORTFOLIO and not generated:
                    # Slightly perturb return target on retries to promote variety
                    adj_return_target = return_target * (1.0 + (retry * 0.02)) if retry > 0 else return_target
                    
                    portfolio = self._generate_single_portfolio_with_exclusion(
                        risk_profile, portfolio_index, stock_selector, 
                        available_tickers, adj_return_target
                    )
                    
                    if not portfolio:
                        retry += 1
                        continue
                    
                    # Build composition signature (tickers only, sorted)
                    try:
                        comp = tuple(sorted([alloc['symbol'] for alloc in portfolio.get('allocations', [])]))
                    except Exception:
                        comp = None
                    
                    # Accept only if composition not seen before
                    if comp and comp not in used_compositions:
                        used_compositions.add(comp)
                        portfolios.append(portfolio)
                        
                        # Track used tickers and update usage counts
                        for ticker in comp:
                            ticker_usage_count[ticker] = ticker_usage_count.get(ticker, 0) + 1
                        
                        unique_tickers = len(ticker_usage_count)
                        logger.info(f"✅ Portfolio {portfolio_index + 1}: {len(comp)} stocks, composition unique, {unique_tickers} unique tickers used so far")
                        generated = True
                    else:
                        logger.warning(f"🔁 Duplicate composition detected on attempt {retry + 1} for portfolio {portfolio_index + 1}; retrying...")
                        retry += 1
                
                if not generated:
                    logger.error(f"❌ Failed to generate unique composition for portfolio {portfolio_index + 1} after {MAX_RETRIES_PER_PORTFOLIO} retries; accepting last generated portfolio but adjusting composition if possible")
                    if portfolio:
                        # Last resort: accept but try to mutate one symbol if pool allows
                        try:
                            current_allocs = portfolio.get('allocations', [])
                            current_symbols = set(a['symbol'] for a in current_allocs)
                            # Attempt to swap one symbol with a less-used alternative from same sector
                            by_sector = {}
                            for s in available_tickers:
                                by_sector.setdefault(s.get('sector', 'Unknown'), []).append(s)
                            mutated = False
                            new_allocs = []
                            for alloc in current_allocs:
                                sym = alloc['symbol']
                                if not mutated:
                                    sec = alloc.get('sector', 'Unknown')
                                    candidates = [c for c in by_sector.get(sec, []) if c.get('symbol') not in current_symbols]
                                    if candidates:
                                        repl = candidates.pop()
                                        alloc = {
                                            'symbol': repl.get('symbol'),
                                            'allocation': alloc['allocation'],
                                            'name': repl.get('name', repl.get('symbol')),
                                            'assetType': 'stock',
                                            'sector': repl.get('sector', 'Unknown'),
                                            'volatility': repl.get('volatility', alloc.get('volatility'))
                                        }
                                        mutated = True
                                new_allocs.append(alloc)
                            if mutated:
                                portfolio['allocations'] = new_allocs
                                comp = tuple(sorted([a['symbol'] for a in new_allocs]))
                                used_compositions.add(comp)
                        except Exception:
                            pass
                        portfolios.append(portfolio)
                    else:
                        logger.warning(f"⚠️ No portfolio generated for index {portfolio_index + 1}")
                    
            except Exception as e:
                logger.error(f"❌ Error generating portfolio {portfolio_index + 1}: {e}")
                continue
        
        unique_tickers = len(ticker_usage_count)
        max_reuse_actual = max(ticker_usage_count.values()) if ticker_usage_count else 0
        logger.info(f"🎯 Ticker exclusion summary: {unique_tickers} unique tickers used across {len(portfolios)} portfolios (max reuse: {max_reuse_actual})")
        return portfolios
    
    def _generate_single_portfolio_with_exclusion(self, risk_profile: str, portfolio_index: int, 
                                                stock_selector, available_stocks: List[Dict], 
                                                return_target: float) -> Optional[Dict]:
        """Generate a single portfolio with ticker exclusion"""
        try:
            # Get portfolio size range
            portfolio_size_range = EnhancedPortfolioConfig().STOCK_COUNT_RANGES.get(risk_profile, (3, 5))
            min_size, max_size = portfolio_size_range
            portfolio_size = min_size + (portfolio_index % (max_size - min_size + 1))
            
            # Select stocks for this portfolio (get raw stock data, not allocations)
            selected_stocks = stock_selector._select_stocks_with_targeting(
                stocks=available_stocks,
                risk_profile=risk_profile,
                portfolio_size=portfolio_size,
                return_target=return_target,  # Already in decimal format from config
                diversification_target=None
            )
            
            if not selected_stocks:
                logger.warning(f"⚠️ No stocks selected for portfolio {portfolio_index + 1}")
                return None
            
            # Create allocations using random weight generation
            allocations = stock_selector._create_simple_allocations(selected_stocks, portfolio_index)
            
            if not allocations:
                logger.warning(f"⚠️ No allocations created for portfolio {portfolio_index + 1}")
                return None
            
            # Calculate real-time metrics first
            temp_portfolio_data = {'allocations': allocations}
            metrics = self.portfolio_analytics.calculate_real_portfolio_metrics(temp_portfolio_data)
            
            # Create portfolio with proper naming using the enhanced method
            portfolio_data = self._create_portfolio_dict_enhanced(
                risk_profile=risk_profile,
                variation_id=portfolio_index,
                allocations=allocations,
                metrics=metrics
            )
            
            return portfolio_data
            
        except Exception as e:
            logger.error(f"❌ Error in single portfolio generation: {e}")
            return None
    
    def _generate_portfolios_parallel(self, risk_profile: str, stock_selector, available_stocks: List[Dict] = None) -> List[Dict]:
        """Generate portfolios in parallel using ThreadPoolExecutor with enhanced targeting"""
        import concurrent.futures

        logger.info(f"⚡ Using parallel generation for {self.PORTFOLIOS_PER_PROFILE} portfolios...")

        portfolios = []
        max_workers = 2  # Process 2 portfolios at a time for speed

        def generate_single(variation_id):
            """Worker function for parallel generation with enhanced targeting"""
            import time
            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                try:
                    t0 = time.time()
                    
                    # Generate portfolio using the enhanced method
                    portfolio = self._regenerate_portfolio_with_quality_control(
                        risk_profile=risk_profile,
                        variation_id=variation_id,
                        stock_selector=stock_selector,
                        available_stocks=available_stocks
                    )
                    logger.debug(f"⏱️ gen_single_t={(time.time()-t0):.3f}s var={variation_id} att={attempt}")
                    return portfolio
                except Exception as e:
                    logger.error(f"❌ Failed to generate portfolio {variation_id + 1}: {e}")
                    break

            # Return fallback if all attempts fail
            logger.warning(f"⚠️ Using fallback for portfolio {variation_id + 1}")
            fallback = self._generate_fallback_portfolio(risk_profile, variation_id)
            # Mark fallback allocation as used (scoped)
            self._mark_allocation_as_used_scoped(fallback['allocations'], risk_profile, variation_id)
            return fallback

        # Generate portfolios in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(generate_single, variation_id): variation_id
                for variation_id in range(self.PORTFOLIOS_PER_PROFILE)
            }

            for future in concurrent.futures.as_completed(future_to_id):
                variation_id = future_to_id[future]
                try:
                    portfolio = future.result()
                    portfolios.append(portfolio)
                    logger.debug(f"✅ Generated portfolio {variation_id + 1} for {risk_profile}")
                except Exception as e:
                    logger.error(f"❌ Worker failed for portfolio {variation_id + 1}: {e}")
                    portfolios.append(self._generate_fallback_portfolio(risk_profile, variation_id))

        # Sort by variation_id to maintain consistent ordering
        portfolios.sort(key=lambda p: p.get('variation_id', 0))

        logger.info(f"⚡ Parallel generation complete: {len(portfolios)} portfolios")
        return portfolios
    
    def get_return_target(self, risk_profile: str, portfolio_index: int) -> float:
        """Get flexible return target within the acceptable range"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile))
        
        # Flexible return target ranges (7% above base targets, but realistic)
        return_ranges = {
            'very-conservative': (0.07, 0.12),    # 7-12% (realistic for conservative stocks)
            'conservative': (0.08, 0.13),         # 8-13% (realistic for conservative stocks)
            'moderate': (0.10, 0.15),             # 10-15% (realistic for moderate stocks)
            'aggressive': (0.12, 0.18),           # 12-18% (realistic for aggressive stocks)
            'very-aggressive': (0.15, 0.22)       # 15-22% (realistic for very aggressive stocks)
        }
        
        target_range = return_ranges.get(risk_profile, (0.10, 0.20))
        target = random.uniform(target_range[0], target_range[1])
        
        return target
    
    def get_diversification_score(self, risk_profile: str, portfolio_index: int) -> float:
        """Get diversification score with variation within profile"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile))
        
        div_range = self.DIVERSIFICATION_VARIATION.get(risk_profile, (75.0, 100.0))
        score = random.uniform(div_range[0], div_range[1])
        
        # Round to 1 decimal place
        return round(score, 1)
    
    def get_stock_count(self, risk_profile: str, portfolio_index: int) -> int:
        """Get variable stock count within the range for this risk profile"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile) + 42)  # Different seed
        
        # Variable stock count ranges
        count_ranges = {
            'very-conservative': (3, 5),    # 3-5 stocks for diversification
            'conservative': (3, 5),         # 3-5 stocks for stability
            'moderate': (3, 5),             # 3-5 stocks for balanced approach
            'aggressive': (3, 4),           # 3-4 stocks for focused growth
            'very-aggressive': (3, 4)       # 3-4 stocks for concentrated growth
        }
        
        count_range = count_ranges.get(risk_profile, (3, 5))
        count = random.randint(count_range[0], count_range[1])
        
        return count
    
    def _generate_single_portfolio_enhanced(self, risk_profile: str, variation_id: int, 
                                         stock_selector: EnhancedStockSelector, 
                                         available_stocks: List[Dict] = None,
                                         return_target: float = None,
                                         diversification_target: float = None,
                                         stock_count: int = None) -> Dict:
        """Generate a single portfolio with enhanced targeting"""
        
        for attempt in range(self.MAX_QUALITY_RETRIES):
            try:
                # Generate stock allocations with enhanced targeting
                allocations = stock_selector.select_stocks_for_portfolio(
                    risk_profile=risk_profile,
                    portfolio_size=stock_count,
                    available_stocks=available_stocks,
                    diversification_target=diversification_target,
                    return_target=return_target
                )
                
                if not allocations:
                    logger.warning(f"    Attempt {attempt + 1}: No allocations generated")
                    continue
                
                # Calculate portfolio metrics
                metrics = self.portfolio_analytics.calculate_real_portfolio_metrics({
                    'allocations': allocations
                })
                
                # Check if portfolio meets enhanced quality criteria
                if self._meets_enhanced_quality_criteria(risk_profile, metrics, return_target):
                    portfolio = self._create_portfolio_dict_enhanced(
                        risk_profile, variation_id, allocations, metrics
                    )
                    return portfolio
                else:
                    logger.debug(f"    Attempt {attempt + 1}: Quality criteria not met")
                    
            except Exception as e:
                logger.error(f"    Attempt {attempt + 1} failed: {e}")
                continue
        
        # Fallback portfolio if all attempts fail
        logger.warning(f"  Using fallback portfolio for {risk_profile} #{variation_id + 1}")
        return self._generate_fallback_portfolio(risk_profile, variation_id)
    
    def _meets_enhanced_quality_criteria(self, risk_profile: str, metrics: Dict, return_target: float) -> bool:
        """Check if portfolio meets enhanced quality criteria with realistic bounds"""
        try:
            expected_return = metrics.get('expected_return', 0)
            risk = metrics.get('risk', 0)
            diversification = metrics.get('diversification_score', 0)
            
            # CRITICAL: Realistic absolute maximums (safety check)
            max_realistic_return = {
                'very-conservative': 0.15,  # 15% max
                'conservative': 0.25,       # 25% max
                'moderate': 0.35,           # 35% max
                'aggressive': 0.35,         # 35% max (expanded from ticker pool analysis)
                'very-aggressive': 0.42     # 42% max (expanded to match new return range)
            }.get(risk_profile, 0.30)
            
            max_realistic_risk = {
                'very-conservative': 0.25,  # 25% max
                'conservative': 0.30,       # 30% max
                'moderate': 0.40,           # 40% max
                'aggressive': 0.45,         # 45% max (expanded to match new risk range)
                'very-aggressive': 0.58     # 58% max (expanded to match new risk range)
            }.get(risk_profile, 0.40)
            
            # Reject if metrics exceed realistic bounds (CRITICAL SAFETY CHECK)
            if expected_return > max_realistic_return:
                logger.warning(f"⚠️ Portfolio rejected: Return {expected_return*100:.1f}% exceeds realistic max {max_realistic_return*100:.0f}%")
                return False
            
            if risk > max_realistic_risk:
                logger.warning(f"⚠️ Portfolio rejected: Risk {risk*100:.1f}% exceeds realistic max {max_realistic_risk*100:.0f}%")
                return False
            
            # Get enhanced targets for this risk profile
            targets = self.TARGET_RANGES.get(risk_profile, {})
            
            # Check return range
            return_range = targets.get('return_range', (0.05, 0.15))
            if not (return_range[0] <= expected_return <= return_range[1]):
                logger.debug(f"    Return {expected_return:.3f} outside range {return_range}")
                return False
            
            # Check if return is close to target (profile-specific tolerance for improved diversity)
            # Higher-risk profiles get more tolerance to allow greater portfolio diversity
            tolerance_map = {
                'very-conservative': 0.01,   # Keep tight for conservative (1%)
                'conservative': 0.015,       # Slightly relaxed (1.5%)
                'moderate': 0.025,           # Increased tolerance for diversity (2.5%)
                'aggressive': 0.025,         # Increased tolerance for diversity (2.5%)
                'very-aggressive': 0.03      # Most relaxed for maximum diversity (3%)
            }
            tolerance = tolerance_map.get(risk_profile, 0.02)
            
            if return_target and abs(expected_return - return_target) > tolerance:
                logger.debug(f"    Return {expected_return:.3f} too far from target {return_target:.3f} (tolerance: {tolerance})")
                return False
            
            # Check risk range (with tighter enforcement)
            risk_range = targets.get('risk_range', (0.10, 0.30))
            # Allow small variance but enforce strict upper bound
            risk_max = risk_range[1] + targets.get('max_risk_variance', 0.05)
            if not (risk_range[0] <= risk <= risk_max):
                logger.debug(f"    Risk {risk:.3f} outside range {risk_range[0]:.3f}-{risk_max:.3f}")
                return False
            
            # Additional strict check: risk should not exceed realistic max even with variance
            if risk > max_realistic_risk:
                logger.debug(f"    Risk {risk:.3f} exceeds realistic max {max_realistic_risk:.3f} even with variance")
                return False
            
            # Check diversification range
            div_range = (targets.get('min_diversification', 70), targets.get('max_diversification', 100))
            if not (div_range[0] <= diversification <= div_range[1]):
                logger.debug(f"    Diversification {diversification:.1f} outside range {div_range}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking quality criteria: {e}")
            return False
    
    def _create_portfolio_dict_enhanced(self, risk_profile: str, variation_id: int, 
                                     allocations: List[Dict], metrics: Dict) -> Dict:
        """Create portfolio dictionary with enhanced structure"""
        
        # Get portfolio name and description
        portfolio_names = self.PORTFOLIO_NAMES.get(risk_profile, [f"Portfolio {variation_id + 1}"])
        portfolio_descriptions = self.PORTFOLIO_DESCRIPTIONS.get(risk_profile, ["Balanced portfolio strategy."])
        
        name = portfolio_names[variation_id % len(portfolio_names)]
        description = portfolio_descriptions[variation_id % len(portfolio_descriptions)]
        
        # Ensure all metrics are JSON-compliant
        expected_return = self._sanitize_metric_value(metrics.get('expected_return', 0.10), 0.10)
        risk = self._sanitize_metric_value(metrics.get('risk', 0.15), 0.15)
        diversification_score = self._sanitize_metric_value(metrics.get('diversification_score', 75.0), 75.0)
        
        portfolio = {
            'allocations': allocations,
            'name': name,
            'description': description,
            'symbol_set': [a['symbol'] for a in allocations],
            'expectedReturn': expected_return,
            'risk': risk,
            'diversificationScore': diversification_score,
            'sectorBreakdown': metrics.get('sector_breakdown', {}),
            'variation_id': variation_id,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'version': 'enhanced_v2'
        }
        
        return portfolio
    
    def _sanitize_metric_value(self, value: float, default_value: float) -> float:
        """Ensure metric values are JSON-compliant"""
        import math
        
        # Check for NaN, inf, or -inf
        if math.isnan(value) or math.isinf(value):
            logger.warning(f"Invalid metric value detected: {value}, using default: {default_value}")
            return default_value
        
        # Ensure the value is a finite number
        if not isinstance(value, (int, float)):
            logger.warning(f"Non-numeric metric value detected: {type(value)}, using default: {default_value}")
            return default_value
            
        return float(value)
    
    def _generate_portfolios_sequential(self, risk_profile: str, stock_selector) -> List[Dict]:
        """Generate portfolios sequentially (original method) with global uniqueness and quality control"""
        portfolios = []

        for variation_id in range(self.PORTFOLIOS_PER_PROFILE):
            try:
                # Generate portfolio with quality control
                portfolio = self._regenerate_portfolio_with_quality_control(
                    risk_profile=risk_profile,
                    variation_id=variation_id,
                    stock_selector=stock_selector
                )

                portfolios.append(portfolio)
                logger.debug(f"✅ Generated portfolio {variation_id + 1} for {risk_profile}")

            except Exception as e:
                logger.error(f"❌ Failed to generate portfolio {variation_id + 1} for {risk_profile}: {e}")
                # Generate fallback portfolio
                fallback = self._generate_fallback_portfolio(risk_profile, variation_id)
                portfolios.append(fallback)

        # Verify overall portfolio set quality and regenerate if needed
        if not self._verify_portfolio_set_quality(portfolios, risk_profile):
            logger.warning(f"Portfolio set for {risk_profile} failed variance check, regenerating worst performers...")
            portfolios = self._regenerate_worst_portfolios(portfolios, risk_profile, stock_selector)

        return portfolios
    
    async def generate_portfolio_bucket_async(self, risk_profile: str) -> List[Dict]:
        """Generate 12 unique portfolios for a specific risk profile with quality control (async version)"""
        logger.info(f"🚀 Generating {self.PORTFOLIOS_PER_PROFILE} portfolios for {risk_profile} risk profile (async)...")
        
        portfolios = []
        
        for variation_id in range(self.PORTFOLIOS_PER_PROFILE):
            try:
                # Generate portfolio with quality control
                portfolio = self._regenerate_portfolio_with_quality_control(
                    risk_profile=risk_profile,
                    variation_id=variation_id,
                    stock_selector=None  # Will create new selector in the method
                )
                
                portfolios.append(portfolio)
                logger.debug(f"✅ Generated portfolio {variation_id + 1} for {risk_profile}")
                
            except Exception as e:
                logger.error(f"❌ Failed to generate portfolio {variation_id + 1} for {risk_profile}: {e}")
                # Generate fallback portfolio
                fallback = self._generate_fallback_portfolio(risk_profile, variation_id)
                portfolios.append(fallback)
        
        # Verify overall portfolio set quality and regenerate if needed
        if not self._verify_portfolio_set_quality(portfolios, risk_profile):
            logger.warning(f"Portfolio set for {risk_profile} failed variance check, regenerating worst performers...")
            # Create a stock selector for regeneration
            from utils.portfolio_stock_selector import PortfolioStockSelector
            stock_selector = PortfolioStockSelector(self.data_service)
            portfolios = self._regenerate_worst_portfolios(portfolios, risk_profile, stock_selector)
        
        logger.info(f"✅ Successfully generated {len(portfolios)} portfolios for {risk_profile} (async)")
        return portfolios
    
    def _generate_variation_seed(self, risk_profile: str, variation_id: int) -> int:
        """Generate deterministic seed for portfolio variation"""
        # Use a more robust seed generation to ensure uniqueness
        import hashlib
        
        # Create a unique seed string with more variation
        # Deterministic only on inputs (no time), but higher dispersion
        seed_string = f"{risk_profile}|vid:{variation_id}|mix:{variation_id * 7 + 13}|rot:{(variation_id * 17) % 97}"
        
        # Use SHA-256 hash for better distribution and convert to integer
        hash_object = hashlib.sha256(seed_string.encode())
        hash_hex = hash_object.hexdigest()
        
        # Use more of the hash for dispersion
        seed_int = int(hash_hex[:12], 16)
        
        # Ensure positive and within reasonable range
        return abs(seed_int) % 10000000
    
    def _generate_single_portfolio_deterministic(self, risk_profile: str, variation_seed: int, variation_id: int, stock_selector=None, available_stocks: List[Dict] = None) -> Dict:
        """Generate single portfolio using deterministic algorithm with global uniqueness enforcement"""

        # Get portfolio name and description
        name = self._get_portfolio_name(risk_profile, variation_id)
        description = self._get_portfolio_description(risk_profile, variation_id)

        # Use shared stock selector if provided, otherwise create new one
        if stock_selector is None:
            stock_selector = EnhancedStockSelector(self.data_service)

        # Try to generate unique portfolio with enhanced retry logic
        for attempt in range(self.MAX_RETRY_ATTEMPTS * 2):  # Double retry attempts
            import time
            phase_start = time.time()
            # Use more variation in seeds to increase uniqueness
            enhanced_seed = variation_seed + (attempt * 1000) + (variation_id * 100)
            random.seed(enhanced_seed)

            # Get targeting parameters from enhanced config
            from .enhanced_portfolio_config import EnhancedPortfolioConfig
            config = EnhancedPortfolioConfig()
            
            # Get specific targets for this portfolio using adaptive targeting
            return_target = config.get_adaptive_return_target(risk_profile, available_stocks, variation_id)
            diversification_target = config.get_diversification_score(risk_profile, variation_id)
            stock_count = config.get_stock_count(risk_profile, variation_id)
            
            # Use enhanced stock selection with targeting
            if available_stocks is not None:
                allocations = stock_selector.select_stocks_for_portfolio(
                    risk_profile=risk_profile,
                    portfolio_size=stock_count,
                    available_stocks=available_stocks,
                    diversification_target=diversification_target,
                    return_target=return_target
                )
            else:
                allocations = stock_selector.select_stocks_for_portfolio(
                    risk_profile=risk_profile,
                    portfolio_size=stock_count,
                    diversification_target=diversification_target,
                    return_target=return_target
                )
            sel_time = time.time() - phase_start

            logger.debug(f"⏱️ select_t={sel_time:.3f}s rp={risk_profile} var={variation_id} att={attempt}")
            break

        # Calculate portfolio metrics with caching
        metrics = self._get_cached_metrics(allocations, risk_profile)
        if not metrics:
            try:
                metrics = self.portfolio_analytics.calculate_real_portfolio_metrics({
                    'allocations': allocations
                })
                self._cache_metrics(allocations, risk_profile, metrics)
            except Exception as e:
                logger.warning(f"Failed to calculate metrics for {risk_profile}-{variation_id}: {e}")
                metrics = self._get_fallback_metrics(risk_profile)

        # Calculate data dependency hash
        data_dependency_hash = self._calculate_data_dependency_hash()

        return {
            'name': name,
            'description': description,
            'allocations': allocations,
            'symbol_set': [a['symbol'] for a in allocations],
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
        """Create a unique key for portfolio allocations with enhanced uniqueness"""
        # Sort allocations by symbol for consistent key generation
        sorted_allocations = sorted(allocations, key=lambda x: x['symbol'])

        # Create key from symbols and allocations (round to 3 decimals for more precision)
        # Also include sector information for better uniqueness
        key_parts = [f"{alloc['symbol']}:{round(alloc['allocation'], 3)}:{alloc.get('sector', 'Unknown')}" for alloc in sorted_allocations]
        return "|".join(key_parts)

    # NEW: Scoped uniqueness helpers with tolerance and optional variation
    def _create_allocation_key_scoped(self, allocations: List[Dict], risk_profile: str, tolerance_pct: float = 0.1) -> str:
        """Simplified uniqueness signature: symbol + allocation only for better diversity"""
        def bucket(v: float) -> float:
            return round(v / tolerance_pct) * tolerance_pct
        sorted_allocations = sorted(allocations, key=lambda x: x['symbol'])
        parts = [f"{a['symbol']}:{bucket(a['allocation']):.1f}" for a in sorted_allocations]
        return f"{risk_profile}|" + "|".join(parts)

    def _validate_stock_pool_sufficiency(self, stock_selector: PortfolioStockSelector, available_stocks: List[Dict], risk_profile: str) -> Tuple[bool, Dict]:
        """Validate stock pool size and sector diversity after volatility filtering."""
        if not available_stocks:
            return False, {'reason': 'no_stocks'}
        try:
            vr = stock_selector.RISK_PROFILE_VOLATILITY[risk_profile]
            filtered = stock_selector._filter_stocks_by_volatility(available_stocks, vr)
            sectors = {}
            for s in filtered:
                sec = s.get('sector', 'Unknown')
                if sec != 'Unknown':
                    sectors[sec] = sectors.get(sec, 0) + 1
            portfolio_size = stock_selector.PORTFOLIO_SIZE[risk_profile]
            min_stocks = portfolio_size * self.PORTFOLIOS_PER_PROFILE  # base
            ok = len(filtered) >= max(60, min_stocks) and len(sectors.keys()) >= 5
            return ok, {
                'filtered_count': len(filtered),
                'sectors': sectors,
                'min_required': max(60, min_stocks)
            }
        except Exception as e:
            return False, {'reason': f'error:{e}'}

    def _compute_and_store_overlap_matrix(self, portfolios: List[Dict], risk_profile: str) -> None:
        """Compute 12x12 symbol overlap counts and store in Redis for session selection."""
        if not portfolios:
            return
        try:
            symbols_list = []
            for p in portfolios:
                if 'symbol_set' in p and p['symbol_set']:
                    symbols_list.append(set(p['symbol_set']))
                else:
                    symbols_list.append(set(a['symbol'] for a in p.get('allocations', [])))
            n = len(symbols_list)
            matrix = [[0 for _ in range(n)] for _ in range(n)]
            for i in range(n):
                for j in range(i, n):
                    overlap = len(symbols_list[i] & symbols_list[j])
                    matrix[i][j] = overlap
                    matrix[j][i] = overlap
            data_hash = portfolios[0].get('data_dependency_hash', 'unknown')
            key = f"portfolio:overlap:{risk_profile}:{data_hash}"
            self.redis_client.setex(key, self.PORTFOLIO_TTL_DAYS * 24 * 3600, json.dumps({'matrix': matrix}))
            logger.debug(f"Stored overlap matrix {key}")
        except Exception as e:
            logger.debug(f"Failed storing overlap matrix: {e}")

    def _is_allocation_unique(self, allocations: List[Dict], risk_profile: str, variation_id: int) -> bool:
        """Uniqueness disabled: always accept."""
        return True

    def _mark_allocation_as_used_scoped(self, allocations: List[Dict], risk_profile: str, variation_id: int):
        """Uniqueness disabled: no-op."""
        return
    
    def _get_cached_metrics(self, allocations: List[Dict], risk_profile: str) -> Optional[Dict]:
        """Get cached metrics using a lightweight hash of allocations (no uniqueness signature)."""
        try:
            parts = [f"{a['symbol']}:{float(a['allocation']):.1f}" for a in sorted(allocations, key=lambda x: x['symbol'])]
            key_raw = f"{risk_profile}|" + "|".join(parts)
            cache_key = f"portfolio:metrics:{hashlib.md5(key_raw.encode()).hexdigest()}"
        except Exception:
            return None
        try:
            cached_metrics = self.redis_client.get(cache_key)
            if cached_metrics:
                return json.loads(cached_metrics)
        except Exception as e:
            logger.debug(f"Error getting cached metrics: {e}")
        return None
    
    def _cache_metrics(self, allocations: List[Dict], risk_profile: str, metrics: Dict):
        """Cache metrics using a lightweight hash of allocations (no uniqueness signature)."""
        try:
            parts = [f"{a['symbol']}:{float(a['allocation']):.1f}" for a in sorted(allocations, key=lambda x: x['symbol'])]
            key_raw = f"{risk_profile}|" + "|".join(parts)
            cache_key = f"portfolio:metrics:{hashlib.md5(key_raw.encode()).hexdigest()}"
        except Exception as e:
            logger.debug(f"Error building cache key: {e}")
            return
        try:
            self.redis_client.setex(cache_key, self.PORTFOLIO_TTL_DAYS * 24 * 3600, json.dumps(metrics))
        except Exception as e:
            logger.debug(f"Error caching metrics: {e}")

    def _enforce_unique_ticker_cap(self, portfolios: List[Dict], available_stocks: List[Dict], risk_profile: str, min_unique: int = 20) -> List[Dict]:
        """Ensure at least min_unique unique tickers across the 12 portfolios when possible.
        Light-touch: attempt to replace repeated symbols in later portfolios with alternatives.
        """
        try:
            if not portfolios:
                return portfolios
            # Build frequency map
            from collections import Counter
            freq = Counter()
            for p in portfolios:
                for s in p.get('symbol_set', []):
                    freq[s] += 1
            unique_symbols = set(freq.keys())
            if len(unique_symbols) >= min_unique or not available_stocks:
                return portfolios
            # Build quick lookup of alternatives by sector within volatility band
            selector = PortfolioStockSelector(self.data_service)
            lo, hi = selector.RISK_PROFILE_VOLATILITY.get(risk_profile, (0.15, 0.30))
            pool = [s for s in (available_stocks or []) if lo <= s.get('volatility', 0) <= hi]
            by_sector = {}
            for s in pool:
                sec = s.get('sector', 'Unknown')
                
                # ENHANCED: Apply sector inference if Unknown
                if sec == 'Unknown':
                    from .portfolio_stock_selector import PortfolioStockSelector
                    selector = PortfolioStockSelector()
                    sec = selector._infer_sector_from_ticker(s['symbol'])
                    s['sector'] = sec  # Update the stock data
                    logger.debug(f"✅ {s['symbol']}: Applied sector inference: {sec}")
                
                by_sector.setdefault(sec, []).append(s)
            # Iterate portfolios, try to swap the most frequent symbols first
            sorted_symbols = [sym for sym, _ in freq.most_common()]
            for p in portfolios:
                changed = False
                new_allocs = []
                for alloc in p.get('allocations', []):
                    sym = alloc['symbol']
                    if len(unique_symbols) >= min_unique:
                        new_allocs.append(alloc)
                        continue
                    # If symbol is overly frequent, try swap within same sector
                    if sym in sorted_symbols:
                        sec = alloc.get('sector', 'Unknown')
                        candidates = [c for c in by_sector.get(sec, []) if c.get('symbol') not in unique_symbols]
                        if candidates:
                            repl = candidates.pop()
                            # Build replacement alloc preserving weight
                            new_allocs.append({
                                'symbol': repl['symbol'],
                                'allocation': alloc['allocation'],
                                'name': repl.get('name', repl.get('symbol')),
                                'assetType': 'stock',
                                'sector': repl.get('sector', 'Unknown'),
                                'volatility': repl.get('volatility', alloc.get('volatility'))
                            })
                            unique_symbols.add(repl['symbol'])
                            changed = True
                        else:
                            new_allocs.append(alloc)
                    else:
                        new_allocs.append(alloc)
                if changed:
                    p['allocations'] = new_allocs
                    p['symbol_set'] = [a['symbol'] for a in new_allocs]
            return portfolios
        except Exception as e:
            logger.debug(f"Unique ticker cap enforcement error: {e}")
            return portfolios
    
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
        
        # Build base fallback allocations with required fields
        allocations = [
            {'symbol': 'AAPL', 'allocation': 40, 'name': 'Apple Inc.', 'assetType': 'stock', 'sector': 'Technology', 'volatility': 0.25},
            {'symbol': 'MSFT', 'allocation': 35, 'name': 'Microsoft Corp.', 'assetType': 'stock', 'sector': 'Technology', 'volatility': 0.22},
            {'symbol': 'JPM', 'allocation': 25, 'name': 'JPMorgan Chase & Co.', 'assetType': 'stock', 'sector': 'Financial Services', 'volatility': 0.28}
        ]
        # Attach metadata consistent with generated portfolios
        try:
            signature = self._create_allocation_key_scoped(allocations, risk_profile)
        except Exception:
            signature = "fallback_signature"
        
        return {
            'name': f"Fallback Portfolio {variation_id + 1}",
            'description': f"Fallback portfolio for {risk_profile} risk profile",
            'allocations': allocations,
            'allocation_signature': signature,
            'symbol_set': [a['symbol'] for a in allocations],
            'expectedReturn': 0.10,
            'risk': 0.20,
            'diversificationScore': 75.0,
            'sectorBreakdown': {},
            'variation_id': variation_id,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'data_dependency_hash': 'fallback_hash'
        }
    
    def _verify_portfolio_quality(self, portfolio: Dict, risk_profile: str, existing_portfolios: List[Dict] = None) -> bool:
        """Verify if a single portfolio meets quality criteria with graduated quality control"""
        try:
            expected_return = portfolio.get('expectedReturn', 0)
            risk = portfolio.get('risk', 0)
            diversification = portfolio.get('diversificationScore', 0)
            
            targets = self.TARGET_RANGES.get(risk_profile, {})
            if not targets:
                logger.warning(f"No target ranges defined for {risk_profile}")
                return True  # Skip verification if no targets defined
            
            # Graduated quality control - check if portfolio is within acceptable ranges
            quality_score = self._calculate_quality_score(portfolio, risk_profile, targets)
            
            # Accept portfolio if quality score is above threshold - OPTIMIZED for adaptive targeting
            if quality_score >= 0.4:  # 40% quality threshold (reduced from 60% for adaptive targeting)
                logger.debug(f"Portfolio quality score: {quality_score:.2f} - ACCEPTED")
                return True
            else:
                logger.debug(f"Portfolio quality score: {quality_score:.2f} - REJECTED")
                return False
            
        except Exception as e:
            logger.error(f"Error verifying portfolio quality: {e}")
            return True  # Allow portfolio if verification fails
    
    def _calculate_quality_score(self, portfolio: Dict, risk_profile: str, targets: Dict) -> float:
        """Calculate quality score using graduated quality control (0.0 to 1.0)"""
        try:
            expected_return = portfolio.get('expectedReturn', 0)
            risk = portfolio.get('risk', 0)
            diversification = portfolio.get('diversificationScore', 0)
            
            # Initialize score components
            return_score = 0.0
            risk_score = 0.0
            div_score = 0.0
            
            # Calculate return score (0.0 to 1.0) - OPTIMIZED with 22.75% threshold
            return_range = targets.get('return_range', (0, 1))
            return_min, return_max = return_range
            
            # Use 22.75% threshold based on dataset distribution analysis (1.5-sigma)
            ADAPTIVE_THRESHOLD = 0.2275  # 22.75% threshold
            
            # Calculate deviation from target range
            if expected_return < return_min:
                deviation = return_min - expected_return
                target_value = return_min
            elif expected_return > return_max:
                deviation = expected_return - return_max
                target_value = return_max
            else:
                # Within range - perfect score
                return_score = 1.0
                deviation = 0
            
            if deviation > 0:
                # Calculate penalty based on adaptive threshold
                penalty_ratio = deviation / (target_value * ADAPTIVE_THRESHOLD)
                return_score = max(0.0, 1.0 - penalty_ratio * 0.8)  # 80% penalty rate for adaptive threshold
            else:
                return_score = 1.0
            
            # Calculate risk score (0.0 to 1.0)
            risk_range = targets.get('risk_range', (0, 1))
            risk_min, risk_max = risk_range
            
            if risk_min <= risk <= risk_max:
                risk_score = 1.0
            else:
                if risk < risk_min:
                    penalty = (risk_min - risk) / max(0.1, risk_min)
                else:
                    penalty = (risk - risk_max) / max(0.1, risk_max)
                risk_score = max(0.0, 1.0 - penalty * 0.3)  # 30% penalty rate
            
            # NO DIVERSIFICATION SCORING - let diversification vary naturally
            div_score = 1.0  # Always give full score for diversification
            
            # Weighted average (return and risk only, no diversification limits)
            total_score = (return_score * 0.7 + risk_score * 0.3)
            
            return min(1.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5  # Default to 50% if calculation fails
    
    def _is_portfolio_unique(self, portfolio: Dict, existing_portfolios: List[Dict]) -> bool:
        """Check if a portfolio is unique compared to existing portfolios"""
        try:
            current_symbols = set(a['symbol'] for a in portfolio.get('allocations', []))
            current_return = round(portfolio.get('expectedReturn', 0), 3)
            current_risk = round(portfolio.get('risk', 0), 3)
            current_div = round(portfolio.get('diversificationScore', 0), 1)
            
            for existing in existing_portfolios:
                existing_symbols = set(a['symbol'] for a in existing.get('allocations', []))
                existing_return = round(existing.get('expectedReturn', 0), 3)
                existing_risk = round(existing.get('risk', 0), 3)
                existing_div = round(existing.get('diversificationScore', 0), 1)
                
                # Check if identical stock selection
                if current_symbols == existing_symbols:
                    logger.debug(f"Portfolio has identical stock selection: {current_symbols}")
                    return False
                
                # Check if identical metrics (very close values)
                if (abs(current_return - existing_return) < 0.001 and 
                    abs(current_risk - existing_risk) < 0.001 and 
                    abs(current_div - existing_div) < 0.1):
                    logger.debug(f"Portfolio has identical metrics: return={current_return}, risk={current_risk}, div={current_div}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking portfolio uniqueness: {e}")
            return True  # Allow portfolio if uniqueness check fails
    
    def _verify_portfolio_set_quality(self, portfolios: List[Dict], risk_profile: str) -> bool:
        """Verify if a set of portfolios meets variance criteria"""
        try:
            if len(portfolios) < 2:
                return True  # Single portfolio or empty set is always valid
            
            expected_returns = [p.get('expectedReturn', 0) for p in portfolios]
            risks = [p.get('risk', 0) for p in portfolios]
            
            # Calculate variance (standard deviation)
            import statistics
            return_variance = statistics.stdev(expected_returns) if len(expected_returns) > 1 else 0
            risk_variance = statistics.stdev(risks) if len(risks) > 1 else 0
            
            targets = self.TARGET_RANGES.get(risk_profile, {})
            max_return_variance = targets.get('max_return_variance', 0.02)
            max_risk_variance = targets.get('max_risk_variance', 0.03)
            
            # Check variance criteria
            return_variance_ok = return_variance <= max_return_variance
            risk_variance_ok = risk_variance <= max_risk_variance
            
            if not return_variance_ok:
                logger.debug(f"Return variance {return_variance:.3f} exceeds limit {max_return_variance:.3f} for {risk_profile}")
            if not risk_variance_ok:
                logger.debug(f"Risk variance {risk_variance:.3f} exceeds limit {max_risk_variance:.3f} for {risk_profile}")
            
            logger.info(f"Quality check for {risk_profile}: return_variance={return_variance:.3f} (limit={max_return_variance:.3f}), risk_variance={risk_variance:.3f} (limit={max_risk_variance:.3f})")
            
            return return_variance_ok and risk_variance_ok
            
        except Exception as e:
            logger.error(f"Error verifying portfolio set quality: {e}")
            return True  # Allow portfolios if verification fails
    
    def _regenerate_portfolio_with_quality_control(self, risk_profile: str, variation_id: int, stock_selector, available_stocks: List[Dict] = None) -> Dict:
        """Generate a single portfolio with quality control and retry logic"""
        for quality_attempt in range(self.MAX_QUALITY_RETRIES):
            try:
                # Generate deterministic seed with quality attempt variation
                variation_seed = self._generate_variation_seed(risk_profile, variation_id)
                enhanced_seed = variation_seed + (quality_attempt * 10000) + (variation_id * 1000)
                
                # Generate portfolio
                portfolio = self._generate_single_portfolio_deterministic(
                    risk_profile=risk_profile,
                    variation_seed=enhanced_seed,
                    variation_id=variation_id,
                    stock_selector=stock_selector,
                    available_stocks=available_stocks
                )
                
                # Verify quality (no existing portfolios for single portfolio generation)
                if self._verify_portfolio_quality(portfolio, risk_profile):
                    logger.debug(f"✅ Portfolio {variation_id + 1} passed quality check on attempt {quality_attempt + 1}")
                    return portfolio
                else:
                    logger.debug(f"🔄 Portfolio {variation_id + 1} failed quality check, retrying (attempt {quality_attempt + 1}/{self.MAX_QUALITY_RETRIES})")
                    
            except Exception as e:
                logger.warning(f"Error generating portfolio {variation_id + 1} on quality attempt {quality_attempt + 1}: {e}")
        
        # If all quality attempts fail, return fallback
        logger.warning(f"All quality attempts failed for portfolio {variation_id + 1}, using fallback")
        return self._generate_fallback_portfolio(risk_profile, variation_id)
    
    def _regenerate_worst_portfolios(self, portfolios: List[Dict], risk_profile: str, stock_selector) -> List[Dict]:
        """Regenerate portfolios that are outliers to improve variance"""
        try:
            if len(portfolios) < 3:
                return portfolios  # Not enough portfolios to identify outliers
            
            # Calculate metrics for all portfolios
            expected_returns = [p.get('expectedReturn', 0) for p in portfolios]
            risks = [p.get('risk', 0) for p in portfolios]
            
            # Calculate mean and standard deviation
            import statistics
            mean_return = statistics.mean(expected_returns)
            mean_risk = statistics.mean(risks)
            std_return = statistics.stdev(expected_returns) if len(expected_returns) > 1 else 0
            std_risk = statistics.stdev(risks) if len(risks) > 1 else 0
            
            # Identify outliers (portfolios more than 1.5 standard deviations from mean)
            outliers = []
            for i, (ret, risk) in enumerate(zip(expected_returns, risks)):
                return_outlier = abs(ret - mean_return) > 1.5 * std_return if std_return > 0 else False
                risk_outlier = abs(risk - mean_risk) > 1.5 * std_risk if std_risk > 0 else False
                
                if return_outlier or risk_outlier:
                    outliers.append((i, portfolios[i]))
            
            logger.info(f"Found {len(outliers)} outlier portfolios in {risk_profile}, regenerating...")
            
            # Regenerate outliers
            for original_index, original_portfolio in outliers:
                variation_id = original_portfolio.get('variation_id', original_index)
                
                # Try to regenerate with different seeds
                for attempt in range(3):  # 3 attempts per outlier
                    try:
                        new_portfolio = self._regenerate_portfolio_with_quality_control(
                            risk_profile=risk_profile,
                            variation_id=variation_id,
                            stock_selector=stock_selector
                        )
                        
                        # Check if new portfolio is better (closer to mean)
                        new_ret = new_portfolio.get('expectedReturn', 0)
                        new_risk = new_portfolio.get('risk', 0)
                        
                        new_return_distance = abs(new_ret - mean_return)
                        new_risk_distance = abs(new_risk - mean_risk)
                        
                        old_return_distance = abs(expected_returns[original_index] - mean_return)
                        old_risk_distance = abs(risks[original_index] - mean_risk)
                        
                        # Accept if significantly closer to mean
                        if (new_return_distance < old_return_distance * 0.8 or 
                            new_risk_distance < old_risk_distance * 0.8):
                            portfolios[original_index] = new_portfolio
                            logger.info(f"✅ Replaced outlier portfolio {original_index + 1} with better variant")
                            break
                        
                    except Exception as e:
                        logger.warning(f"Failed to regenerate outlier portfolio {original_index + 1}: {e}")
                        continue
            
            # Final variance check
            if self._verify_portfolio_set_quality(portfolios, risk_profile):
                logger.info(f"✅ Portfolio set for {risk_profile} now meets variance criteria after regeneration")
            else:
                logger.warning(f"⚠️ Portfolio set for {risk_profile} still has high variance after regeneration")
            
            return portfolios
            
        except Exception as e:
            logger.error(f"Error regenerating worst portfolios: {e}")
            return portfolios  # Return original portfolios if regeneration fails
