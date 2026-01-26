#!/usr/bin/env python3
"""
Redis Portfolio Manager
Handles storage and retrieval of enhanced portfolios in Redis
Manages TTL and portfolio metadata
"""

import json
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional
import redis

logger = logging.getLogger(__name__)

class RedisPortfolioManager:
    """
    Manages portfolio storage and retrieval in Redis
    Handles TTL management and portfolio metadata
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.PORTFOLIO_TTL_DAYS = 7  # Shorter than data TTL (28 days)
        self.PORTFOLIO_TTL_SECONDS = self.PORTFOLIO_TTL_DAYS * 24 * 3600
        self.PORTFOLIOS_PER_PROFILE = 12  # Backend expects 12 portfolios per risk profile
        
        if not self.redis_client:
            logger.warning("⚠️ Redis client not available, portfolio caching disabled")
    
    def _validate_portfolio_compliance(self, portfolio: Dict, risk_profile: str) -> bool:
        """
        Final compliance check using three-tier system.
        Accepts portfolios with violations ≤2% (COMPLIANT or ACCEPTABLE).
        """
        try:
            from .risk_profile_config import UNIFIED_RISK_PROFILE_CONFIG
            
            config = UNIFIED_RISK_PROFILE_CONFIG.get(risk_profile)
            if not config:
                logger.warning(f"No config found for {risk_profile}")
                return False
            
            # Get metrics (handle both decimal and percentage formats)
            ret = portfolio.get('expectedReturn', 0)
            risk = portfolio.get('risk', 0)
            
            # Convert to decimal if in percentage format
            if ret > 1.0:  # Assume percentage if > 1
                ret = ret / 100
            if risk > 1.0:  # Assume percentage if > 1
                risk = risk / 100
            
            # CRITICAL: Reject portfolios with non-positive returns
            if ret <= 0:
                logger.error(
                    f"🔴 Storage REJECTED portfolio: Non-positive return {ret*100:.2f}% "
                    f"for {risk_profile}. Stocks: {[a.get('symbol') for a in portfolio.get('allocations', [])[:3]]}"
                )
                return False
            
            # Get valid ranges (these are in decimals)
            min_ret, max_ret = config['return_range']
            min_risk, max_risk = config['quality_risk_range']
            max_risk_variance = config.get('max_risk_variance', 0.05)
            risk_max = max_risk + max_risk_variance
            
            # Calculate violations (in percentage points)
            return_violation_pct = 0
            if ret < min_ret:
                return_violation_pct = (min_ret - ret) * 100
            elif ret > max_ret:
                return_violation_pct = (ret - max_ret) * 100
            
            risk_violation_pct = 0
            if risk < min_risk:
                risk_violation_pct = (min_risk - risk) * 100
            elif risk > risk_max:
                risk_violation_pct = (risk - risk_max) * 100
            
            max_violation_pct = max(return_violation_pct, risk_violation_pct)
            
            # Accept if violation ≤ 2% (COMPLIANT or ACCEPTABLE)
            if max_violation_pct <= 2.0:
                return True
            
            # Reject if violation > 2%
            logger.warning(
                f"Storage rejected portfolio: max_violation={max_violation_pct:.2f}%, "
                f"return={ret*100:.2f}%, risk={risk*100:.2f}%"
            )
            return False
            
        except Exception as e:
            logger.error(f"Error validating portfolio: {e}")
            return False

    def _filter_valid_portfolios(self, portfolios: List[Dict], risk_profile: str) -> List[Dict]:
        """Filter portfolios to only include compliant ones"""
        validated = []
        rejected = 0
        
        for portfolio in portfolios:
            if self._validate_portfolio_compliance(portfolio, risk_profile):
                validated.append(portfolio)
            else:
                rejected += 1
        
        if rejected > 0:
            logger.warning(f"Rejected {rejected} non-compliant portfolios before storage for {risk_profile}")
        
        return validated

    def store_portfolio_bucket(self, risk_profile: str, portfolios: List[Dict]) -> bool:
        """Store 12 portfolios for a risk profile in Redis"""
        if not self.redis_client:
            logger.warning("⚠️ Redis not available, cannot store portfolios")
            return False
        
        try:
            # CRITICAL: First pass - reject any portfolio with non-positive returns
            # These should have been filtered during generation, but double-check here
            clean_portfolios = []
            rejected_count = 0
            for p in portfolios:
                ret = p.get('expectedReturn', 0)
                if ret > 1.0:
                    ret = ret / 100
                
                if ret > 0:
                    clean_portfolios.append(p)
                else:
                    rejected_count += 1
                    logger.error(
                        f"🔴 PRE-STORAGE REJECTION: Portfolio with return {ret*100:.2f}% "
                        f"for {risk_profile}. Stocks: {[a.get('symbol') for a in p.get('allocations', [])[:3]]}"
                    )
            
            if rejected_count > 0:
                logger.error(
                    f"🔴 {rejected_count} portfolios rejected for non-positive returns in {risk_profile}"
                )
            
            # Second pass - validate against profile constraints
            validated_portfolios = self._filter_valid_portfolios(clean_portfolios, risk_profile)
            
            if len(validated_portfolios) < 8:  # Require at least 8 valid portfolios
                logger.error(
                    f"Insufficient valid portfolios for {risk_profile}: "
                    f"{len(validated_portfolios)}/12 passed validation (rejected {rejected_count} for negative returns)"
                )
                return False
            
            if len(validated_portfolios) < len(portfolios):
                logger.warning(
                    f"Using {len(validated_portfolios)}/{len(portfolios)} portfolios "
                    f"after validation for {risk_profile}"
                )
            
            # Use validated portfolios instead of original
            portfolios = validated_portfolios

            bucket_key = f"portfolio_bucket:{risk_profile}"
            
            # Store each portfolio with FINAL validation
            stored_count = 0
            for i, portfolio in enumerate(portfolios):
                # FINAL CHECK: Absolutely no negative returns allowed
                final_ret = portfolio.get('expectedReturn', 0)
                if final_ret > 1.0:
                    final_ret = final_ret / 100
                
                if final_ret <= 0:
                    logger.error(
                        f"🔴 FINAL STORAGE BLOCK: Portfolio {i+1} has non-positive return "
                        f"{final_ret*100:.2f}%. NOT storing this portfolio."
                    )
                    continue  # Skip this portfolio
                
                portfolio_key = f"{bucket_key}:{stored_count}"
                portfolio_json = json.dumps(portfolio, default=str)
                
                self.redis_client.setex(
                    portfolio_key,
                    self.PORTFOLIO_TTL_SECONDS,
                    portfolio_json
                )
                
                stored_count += 1
                logger.debug(f"✅ Stored portfolio {stored_count} for {risk_profile}")
            
            # Check if we stored enough portfolios
            if stored_count < 8:
                logger.error(
                    f"🔴 Only stored {stored_count} portfolios for {risk_profile} (need at least 8)"
                )
                return False
            
            # Store metadata
            metadata = {
                'risk_profile': risk_profile,
                'portfolio_count': stored_count,
                'generated_at': datetime.now().isoformat(),
                'data_dependency_hash': portfolios[0].get('data_dependency_hash', 'unknown') if portfolios else 'unknown',
                'ttl_days': self.PORTFOLIO_TTL_DAYS,
                'last_updated': datetime.now().isoformat()
            }
            
            self.redis_client.setex(
                f"{bucket_key}:metadata",
                self.PORTFOLIO_TTL_SECONDS,
                json.dumps(metadata, default=str)
            )
            
            logger.info(f"✅ Successfully stored {stored_count} portfolios for {risk_profile} in Redis")
            
            # Auto-update PORTFOLIOS_IN_REDIS.md
            try:
                self._update_portfolios_markdown()
            except Exception as e:
                logger.debug(f"Auto-update markdown failed: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store portfolios for {risk_profile}: {e}")
            return False
    
    def get_portfolio_recommendations(self, risk_profile: str, count: int = 3) -> List[Dict]:
        """Get portfolio recommendations from Redis with Top Pick as highest return"""
        if not self.redis_client:
            logger.warning("⚠️ Redis not available, cannot retrieve portfolios")
            return []
        
        try:
            # Use correct key format for recommendation portfolios
            bucket_key = f"portfolio_bucket:{risk_profile}"
            available_portfolios = []
            
            # Load portfolios from Redis
            for i in range(self.PORTFOLIOS_PER_PROFILE):
                portfolio_key = f"{bucket_key}:{i}"
                portfolio_data = self.redis_client.get(portfolio_key)
                
                if portfolio_data:
                    try:
                        portfolio = json.loads(portfolio_data)
                        available_portfolios.append(portfolio)
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Failed to decode portfolio {i} for {risk_profile}: {e}")
                        continue
                else:
                    logger.debug(f"Portfolio {i} not found in Redis for {risk_profile}")
            
            if len(available_portfolios) < count:
                logger.warning(f"⚠️ Only {len(available_portfolios)} portfolios available for {risk_profile}, need {count}")
                return available_portfolios
            
            # Deduplicate portfolios by composition or identifiers (variation_id/data_dependency_hash)
            def _make_signature(portfolio: Dict):
                vid = portfolio.get('variation_id')
                ddh = portfolio.get('data_dependency_hash')
                if vid:
                    return ('vid', str(vid))
                if ddh:
                    return ('ddh', str(ddh))
                allocs = portfolio.get('allocations') or portfolio.get('portfolio') or []
                pairs = []
                for a in allocs:
                    sym = a.get('symbol') or a.get('ticker') or ''
                    alloc = float(a.get('allocation', 0.0))
                    pairs.append((sym, round(alloc, 4)))
                return ('comp', tuple(sorted(pairs, key=lambda x: (x[0], x[1]))))

            unique_portfolios = []
            seen = set()
            for p in available_portfolios:
                sig = _make_signature(p)
                if sig in seen:
                    logger.debug("Duplicate portfolio skipped in recommendations (signature matched)")
                    continue
                seen.add(sig)
                unique_portfolios.append(p)

            available_portfolios = unique_portfolios
            
            # Add rotation logic: use time-based seed for consistent rotation
            import time
            rotation_seed = int(time.time() // 300) % len(available_portfolios)  # Rotate every 5 minutes
            
            # Sort portfolios by expected return (highest first) for Top Pick selection
            available_portfolios.sort(key=lambda p: p.get('expectedReturn', 0), reverse=True)
            
            # Rotate the portfolio selection
            rotated_portfolios = available_portfolios[rotation_seed:] + available_portfolios[:rotation_seed]
            
            # Return top portfolios with Top Pick being the highest return
            selected_portfolios = rotated_portfolios[:count]
            
            # Mark the first portfolio (highest return) as Top Pick
            if selected_portfolios:
                selected_portfolios[0]['isTopPick'] = True
                # Clean up any existing "Top Pick -" prefix from the name
                portfolio_name = selected_portfolios[0].get('name', 'Portfolio')
                if portfolio_name.startswith('Top Pick - '):
                    selected_portfolios[0]['name'] = portfolio_name.replace('Top Pick - ', '')
            
            logger.info(f"✅ Retrieved {len(selected_portfolios)} portfolio recommendations for {risk_profile}")
            return selected_portfolios
                
        except Exception as e:
            logger.error(f"❌ Error retrieving portfolios for {risk_profile}: {e}")
            return []
    
    def _select_random_portfolios(self, portfolios: List[Dict], count: int) -> List[Dict]:
        """Select random portfolios deterministically based on current time"""
        if len(portfolios) <= count:
            return portfolios
        
        # Use current hour as seed for daily variation
        current_hour = datetime.now().hour
        random.seed(current_hour)
        
        return random.sample(portfolios, count)
    
    def get_portfolio_metadata(self, risk_profile: str) -> Optional[Dict]:
        """Get metadata for a specific risk profile"""
        if not self.redis_client:
            return None
        
        try:
            metadata_key = f"portfolio_bucket:{risk_profile}:metadata"
            metadata_data = self.redis_client.get(metadata_key)
            
            if metadata_data:
                return json.loads(metadata_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting metadata for {risk_profile}: {e}")
            return None
    
    def is_portfolio_bucket_available(self, risk_profile: str) -> bool:
        """Check if portfolio bucket is available in Redis"""
        if not self.redis_client:
            return False
        
        try:
            # Check if at least one portfolio exists
            bucket_key = f"portfolio_bucket:{risk_profile}:0"
            return self.redis_client.exists(bucket_key) > 0
            
        except Exception as e:
            logger.error(f"Error checking portfolio availability for {risk_profile}: {e}")
            return False
    
    def get_portfolio_count(self, risk_profile: str) -> int:
        """Get the number of portfolios available for a risk profile"""
        if not self.redis_client:
            return 0
        
        try:
            count = 0
            # Check for actual portfolio recommendation keys (not metrics keys)
            bucket_key = f"portfolio_bucket:{risk_profile}"
            
            for i in range(self.PORTFOLIOS_PER_PROFILE):
                portfolio_key = f"{bucket_key}:{i}"
                if self.redis_client.exists(portfolio_key):
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting portfolios for {risk_profile}: {e}")
            return 0
    
    def get_valid_portfolio_count(self, risk_profile: str) -> int:
        """Get the number of VALID portfolios (with stocks) available for a risk profile"""
        if not self.redis_client:
            return 0
        
        try:
            count = 0
            bucket_key = f"portfolio_bucket:{risk_profile}"
            
            for i in range(self.PORTFOLIOS_PER_PROFILE):
                portfolio_key = f"{bucket_key}:{i}"
                portfolio_data = self.redis_client.get(portfolio_key)
                
                if portfolio_data:
                    try:
                        portfolio = json.loads(portfolio_data)
                        allocations = portfolio.get('allocations', [])
                        # Count stocks (assetType='stock' or no assetType specified)
                        stock_count = len([a for a in allocations if a.get('assetType') == 'stock' or not a.get('assetType')])
                        if stock_count > 0:
                            count += 1
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Invalid portfolio data
                        continue
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting valid portfolios for {risk_profile}: {e}")
            return 0
    
    def clear_portfolio_bucket(self, risk_profile: str) -> bool:
        """Clear all portfolios for a specific risk profile"""
        if not self.redis_client:
            return False
        
        try:
            bucket_key = f"portfolio_bucket:{risk_profile}"
            
            # Delete all portfolios
            for i in range(self.PORTFOLIOS_PER_PROFILE):
                portfolio_key = f"{bucket_key}:{i}"
                self.redis_client.delete(portfolio_key)
            
            # Delete metadata
            metadata_key = f"{bucket_key}:metadata"
            self.redis_client.delete(metadata_key)
            
            logger.info(f"✅ Cleared portfolio bucket for {risk_profile}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear portfolio bucket for {risk_profile}: {e}")
            return False
    
    def get_all_portfolio_buckets_status(self) -> Dict[str, Dict]:
        """Get status of all portfolio buckets"""
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        status = {}
        
        for risk_profile in risk_profiles:
            try:
                metadata = self.get_portfolio_metadata(risk_profile)
                portfolio_count = self.get_portfolio_count(risk_profile)
                
                status[risk_profile] = {
                    'available': portfolio_count > 0,
                    'portfolio_count': portfolio_count,
                    'expected_count': self.PORTFOLIOS_PER_PROFILE,
                    'metadata': metadata,
                    'last_updated': metadata.get('last_updated') if metadata else None
                }
                
            except Exception as e:
                logger.error(f"Error getting status for {risk_profile}: {e}")
                status[risk_profile] = {
                    'available': False,
                    'portfolio_count': 0,
                    'expected_count': self.PORTFOLIOS_PER_PROFILE,
                    'metadata': None,
                    'last_updated': None,
                    'error': str(e)
                }
        
        return status
    
    def get_portfolio_ttl_info(self, risk_profile: str) -> Optional[Dict]:
        """Get TTL information for portfolio bucket"""
        if not self.redis_client:
            return None
        
        try:
            bucket_key = f"portfolio_bucket:{risk_profile}:0"
            ttl_seconds = self.redis_client.ttl(bucket_key)
            
            if ttl_seconds > 0:
                ttl_days = ttl_seconds // 86400
                ttl_hours = (ttl_seconds % 86400) // 3600
                
                return {
                    'ttl_seconds': ttl_seconds,
                    'ttl_days': ttl_days,
                    'ttl_hours': ttl_hours,
                    'expires_in': f"{ttl_days}d {ttl_hours}h",
                    'expires_at': datetime.now().timestamp() + ttl_seconds
                }
            elif ttl_seconds == -1:
                return {'status': 'no_expiry', 'ttl_seconds': -1}
            else:
                return {'status': 'expired', 'ttl_seconds': 0}
                
        except Exception as e:
            logger.error(f"Error getting TTL info for {risk_profile}: {e}")
            return None
    
    def _update_portfolios_markdown(self):
        """Auto-update PORTFOLIOS_IN_REDIS.md with current portfolio data"""
        try:
            from datetime import datetime
            
            lines = [
                "# Portfolios in Redis",
                f"Generated: {datetime.now().isoformat()}",
                ""
            ]
            
            risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
            
            # Return caps for highlighting
            caps = {
                'very-conservative': 0.12,
                'conservative': 0.15,
                'moderate': 0.25,
                'aggressive': 0.35,
                'very-aggressive': 0.45
            }
            
            total_portfolios = 0
            
            for rp in risk_profiles:
                try:
                    portfolios = self.get_portfolio_recommendations(rp, count=12)
                    lines.append(f"## {rp} ({len(portfolios)} portfolios)")
                    lines.append("")
                    
                    if not portfolios:
                        lines.append("*No portfolios found in Redis*")
                        lines.append("")
                        continue
                    
                    cap = caps.get(rp)
                    for idx, p in enumerate(portfolios):
                        total_portfolios += 1
                        name = p.get('name', f'Portfolio {idx+1}')
                        exp = p.get('expectedReturn')
                        risk = p.get('risk')
                        div = p.get('diversificationScore')
                        
                        # Check if above cap
                        is_above_cap = False
                        if cap is not None and isinstance(exp, (int, float)) and exp > cap:
                            is_above_cap = True
                        
                        # Format expected return
                        if isinstance(exp, (int, float)):
                            exp_disp = f"{exp:.2f}"
                        else:
                            exp_disp = f"{exp}"
                        
                        # Add header with cap warning if needed
                        if is_above_cap:
                            lines.append(f"### {idx+1}. {name} ⚠️ Above cap ({cap*100:.0f}%)")
                        else:
                            lines.append(f"### {idx+1}. {name}")
                        
                        lines.append(f"- expectedReturn: {exp_disp}")
                        lines.append(f"- risk: {risk}")
                        lines.append(f"- diversificationScore: {div}")
                        lines.append(f"- variation_id: {p.get('variation_id')}")
                        lines.append(f"- data_dependency_hash: {p.get('data_dependency_hash')}")
                        lines.append(f"- generated_at: {p.get('generated_at')}")
                        lines.append(f"- risk_profile: {rp}")
                        lines.append("")
                        lines.append("Allocations:")
                        lines.append("")
                        lines.append("| Symbol | Allocation | Sector | Name |")
                        lines.append("|---|---:|---|---|")
                        
                        allocs = p.get('allocations', [])
                        for alloc in allocs:
                            symbol = alloc.get('symbol', '')
                            allocation = alloc.get('allocation', 0)
                            sector = alloc.get('sector', '')
                            name_col = alloc.get('name', '')
                            lines.append(f"| {symbol} | {allocation:.1f}% | {sector} | {name_col} |")
                        
                        lines.append("")
                        
                except Exception as e:
                    lines.append(f"## {rp} (Error)")
                    lines.append("")
                    lines.append(f"*Error loading portfolios: {e}*")
                    lines.append("")
            
            lines.append("")
            lines.append(f"Total portfolios exported: {total_portfolios}")
            lines.append("")
            
            # Write to file (relative to project root)
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            markdown_path = os.path.join(project_root, "PORTFOLIOS_IN_REDIS.md")
            
            with open(markdown_path, 'w') as f:
                f.write('\n'.join(lines))
            
            logger.debug("✅ Auto-updated PORTFOLIOS_IN_REDIS.md")
            
        except Exception as e:
            logger.debug(f"Failed to auto-update markdown: {e}")
