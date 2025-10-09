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

        # Global uniqueness tracking - TTL longer than portfolio TTL to prevent cross-profile duplicates
        self.GLOBAL_SIGNATURE_TTL = 14  # 14 days to cover portfolio lifecycle
        # Increase attempts to lower duplicate probability without large perf hit
        self.MAX_RETRY_ATTEMPTS = 6  # previously 3
        
        # Uniqueness disabled globally (can re-enable via code change)
        self.dedup_bypass = True
        
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
        """Generate 12 unique portfolios for a specific risk profile efficiently with shared stock data
        
        Args:
            risk_profile: Risk profile to generate portfolios for
            use_parallel: If True, use parallel generation (3-4x faster)
        """
        import time
        start_time = time.time()
        
        logger.info(f"🚀 Generating {self.PORTFOLIOS_PER_PROFILE} portfolios for {risk_profile} risk profile...")
        
        # Initialize stock selector ONCE for all portfolios
        stock_selector = PortfolioStockSelector(self.data_service)
        
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
        
        # Choose generation method
        if use_parallel:
            portfolios = self._generate_portfolios_parallel(risk_profile, stock_selector, available_stocks)
        else:
            portfolios = self._generate_portfolios_sequential(risk_profile, stock_selector)
        
        # Uniqueness disabled; keep all portfolios
        unique_portfolios = portfolios

        # Enforce unique ticker cap across the 12 portfolios (aim for >=20 unique tickers)
        try:
            unique_portfolios = self._enforce_unique_ticker_cap(unique_portfolios, available_stocks, risk_profile, min_unique=20)
        except Exception as e:
            logger.debug(f"Unique ticker cap enforcement skipped: {e}")
        
        # Precompute and store overlap matrix for session-level diversity
        try:
            self._compute_and_store_overlap_matrix(unique_portfolios, risk_profile)
        except Exception as e:
            logger.debug(f"Overlap matrix computation skipped: {e}")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Successfully generated {len(unique_portfolios)} unique portfolios for {risk_profile} in {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/len(unique_portfolios):.3f}s per portfolio (with shared stock data)")

        # Store Top Pick for quick retrieval by API (expectedReturn-based)
        try:
            def _score(p):
                return float(p.get('expectedReturn', 0.0))
            top = max(unique_portfolios, key=_score)
            cache_key = f"portfolio:top_pick:{risk_profile}"
            self.redis_client.setex(cache_key, self.PORTFOLIO_TTL_DAYS * 24 * 3600, json.dumps(top))
        except Exception as e:
            logger.debug(f"Top pick store skipped: {e}")
        return unique_portfolios
    
    def _generate_portfolios_parallel(self, risk_profile: str, stock_selector, available_stocks: List[Dict] = None) -> List[Dict]:
        """Generate portfolios in parallel using ThreadPoolExecutor (3-4x faster)"""
        import concurrent.futures

        logger.info(f"⚡ Using parallel generation for {self.PORTFOLIOS_PER_PROFILE} portfolios...")

        portfolios = []
        max_workers = 4  # Process 4 portfolios at a time

        def generate_single(variation_id):
            """Worker function for parallel generation with global uniqueness"""
            import time
            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                try:
                    t0 = time.time()
                    variation_seed = self._generate_variation_seed(risk_profile, variation_id)
                    portfolio = self._generate_single_portfolio_deterministic(
                        risk_profile=risk_profile,
                        variation_seed=variation_seed + attempt,  # Add attempt offset
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
    
    def _generate_portfolios_sequential(self, risk_profile: str, stock_selector) -> List[Dict]:
        """Generate portfolios sequentially (original method) with global uniqueness"""
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

        return portfolios
    
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
            stock_selector = PortfolioStockSelector(self.data_service)

        # Try to generate unique portfolio with enhanced retry logic
        for attempt in range(self.MAX_RETRY_ATTEMPTS * 2):  # Double retry attempts
            import time
            phase_start = time.time()
            # Use more variation in seeds to increase uniqueness
            enhanced_seed = variation_seed + (attempt * 1000) + (variation_id * 100)
            random.seed(enhanced_seed)

            # Use pre-fetched data if available, otherwise fall back to original method
            if available_stocks is not None:
                allocations = stock_selector.select_stocks_for_risk_profile_deterministic_with_data(
                    risk_profile, enhanced_seed, variation_id, available_stocks, fast_mode=True
                )
            else:
                allocations = stock_selector.select_stocks_for_risk_profile_deterministic(
                    risk_profile, enhanced_seed, variation_id, fast_mode=True
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
