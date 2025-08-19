#!/usr/bin/env python3
"""
Data Change Detector
Monitors changes in underlying stock data and triggers portfolio regeneration
Integrates with Enhanced Data Fetcher to detect data updates
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import redis

logger = logging.getLogger(__name__)

class DataChangeDetector:
    """
    Detects changes in underlying stock data that require portfolio regeneration
    Monitors key stocks and calculates data dependency hashes
    """
    
    def __init__(self, data_service):
        """
        Initialize Data Change Detector
        Args:
            data_service: RedisFirstDataService or EnhancedDataFetcher instance
        """
        self.data_service = data_service
        
        # Handle both RedisFirstDataService and EnhancedDataFetcher
        if hasattr(data_service, 'redis_client'):
            self.redis_client = data_service.redis_client
        else:
            self.redis_client = data_service.r
        self.last_data_state = {}
        
        # Key stocks to monitor for data changes (representative of each sector)
        self.MONITORING_STOCKS = {
            'technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'],
            'healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO'],
            'financial': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            'consumer': ['PG', 'KO', 'PEP', 'WMT', 'HD'],
            'energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB'],
            'industrial': ['CAT', 'BA', 'MMM', 'GE', 'HON'],
            'communication': ['VZ', 'T', 'CMCSA', 'DIS', 'NFLX']
        }
        
        # Flatten the monitoring stocks list
        self.KEY_STOCKS = [stock for sector_stocks in self.MONITORING_STOCKS.values() for stock in sector_stocks]
        
        logger.info(f"🔍 Data Change Detector initialized with {len(self.KEY_STOCKS)} monitoring stocks")
    
    def calculate_data_dependency_hash(self) -> str:
        """Calculate hash based on Redis cache state and portfolio metadata - NOT live API calls"""
        try:
            # Instead of calling live APIs, check Redis cache state
            # This should only change when Redis data actually changes
            
            # Get portfolio metadata from Redis to check last update times
            portfolio_metadata = self._get_portfolio_metadata_state()
            
            # Get Redis cache status for key stocks
            cache_state = self._get_redis_cache_state()
            
            # Combine portfolio metadata and cache state for hash
            state_data = {
                'portfolio_metadata': portfolio_metadata,
                'cache_state': cache_state,
                'timestamp': datetime.now().isoformat()
            }
            
            # Create hash from Redis state, not live data
            state_json = json.dumps(state_data, sort_keys=True)
            return hashlib.md5(state_json.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating Redis-based data dependency hash: {e}")
            return "error_hash"
    
    def _get_portfolio_metadata_state(self) -> Dict:
        """Get portfolio metadata state from Redis"""
        metadata_state = {}
        
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        
        for risk_profile in risk_profiles:
            try:
                metadata_key = f"portfolio_bucket:{risk_profile}:metadata"
                metadata = self.redis_client.get(metadata_key) if self.redis_client else None
                
                if metadata:
                    metadata_data = json.loads(metadata)
                    metadata_state[risk_profile] = {
                        'last_updated': metadata_data.get('last_updated'),
                        'generated_at': metadata_data.get('generated_at'),
                        'portfolio_count': metadata_data.get('portfolio_count')
                    }
                else:
                    metadata_state[risk_profile] = {'status': 'missing'}
                    
            except Exception as e:
                metadata_state[risk_profile] = {'error': str(e)}
        
        return metadata_state
    
    def _get_redis_cache_state(self) -> Dict:
        """Get Redis cache state for key stocks"""
        cache_state = {}
        
        # Check Redis cache status for a few key stocks
        key_stocks = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'JNJ']
        
        for stock in key_stocks:
            try:
                # Check if data exists in Redis and get TTL
                price_key = f"ticker:{stock}:prices"
                sector_key = f"ticker:{stock}:sector"
                
                price_exists = self.redis_client.exists(price_key) if self.redis_client else False
                sector_exists = self.redis_client.exists(sector_key) if self.redis_client else False
                
                if price_exists and sector_exists:
                    price_ttl = self.redis_client.ttl(price_key) if self.redis_client else -1
                    sector_ttl = self.redis_client.ttl(sector_key) if self.redis_client else -1
                    
                    cache_state[stock] = {
                        'price_ttl': price_ttl,
                        'sector_ttl': sector_ttl,
                        'price_days_left': price_ttl // 86400 if price_ttl > 0 else 0,
                        'sector_days_left': sector_ttl // 86400 if sector_ttl > 0 else 0
                    }
                else:
                    cache_state[stock] = {'status': 'missing'}
                    
            except Exception as e:
                cache_state[stock] = {'error': str(e)}
        
        return cache_state
    
    def has_data_changed(self, risk_profile: str) -> bool:
        """Check if data has changed for a specific risk profile - Redis-based detection"""
        try:
            # Get current Redis state hash
            current_hash = self.calculate_data_dependency_hash()
            
            if current_hash in ['error_hash']:
                logger.warning(f"⚠️ Invalid data hash for {risk_profile}: {current_hash}")
                return False  # Don't trigger regeneration on hash errors
            
            # Get stored data state from portfolio metadata
            metadata_key = f"portfolio_bucket:{risk_profile}:metadata"
            metadata = self.redis_client.get(metadata_key) if self.redis_client else None
            
            if not metadata:
                logger.info(f"ℹ️ No metadata found for {risk_profile}, data considered unchanged")
                return False  # Don't regenerate if no metadata exists
            
            try:
                stored_metadata = json.loads(metadata)
                stored_hash = stored_metadata.get('data_dependency_hash')
                
                if not stored_hash:
                    logger.info(f"ℹ️ No data dependency hash in metadata for {risk_profile}")
                    return False  # Don't regenerate if no hash exists
                
                # Check if data state changed
                if stored_hash != current_hash:
                    logger.info(f"🔄 Data state changed for {risk_profile}")
                    logger.info(f"   Old hash: {stored_hash[:8]}...")
                    logger.info(f"   New hash: {current_hash[:8]}...")
                    
                    # Additional check: Only regenerate if significant time has passed
                    # Since we're dealing with monthly data, don't regenerate too frequently
                    last_updated = stored_metadata.get('last_updated')
                    if last_updated:
                        try:
                            last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            time_since_update = datetime.now() - last_update_time.replace(tzinfo=None)
                            
                            # Only regenerate if at least 7 days have passed (since portfolios have 7-day TTL)
                            if time_since_update.days < 7:
                                logger.info(f"ℹ️ Portfolios for {risk_profile} updated recently ({time_since_update.days} days ago), skipping regeneration")
                                return False
                        except Exception as e:
                            logger.debug(f"Could not parse last update time: {e}")
                    
                    return True
                
                logger.debug(f"✅ Data state unchanged for {risk_profile}")
                return False
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to decode metadata for {risk_profile}: {e}")
                return False  # Don't regenerate on decode error
            
        except Exception as e:
            logger.error(f"❌ Error checking data change for {risk_profile}: {e}")
            return False  # Don't regenerate on error
    
    def get_data_change_summary(self) -> Dict[str, any]:
        """Get summary of data changes across all risk profiles"""
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        current_hash = self.calculate_data_dependency_hash()
        
        summary = {
            'current_data_hash': current_hash,
            'hash_timestamp': datetime.now().isoformat(),
            'risk_profiles': {},
            'overall_status': 'unknown'
        }
        
        changed_profiles = []
        unchanged_profiles = []
        
        for risk_profile in risk_profiles:
            try:
                has_changed = self.has_data_changed(risk_profile)
                
                profile_summary = {
                    'risk_profile': risk_profile,
                    'data_changed': has_changed,
                    'last_check': datetime.now().isoformat()
                }
                
                # Get additional metadata if available
                if self.redis_client:
                    metadata_key = f"portfolio_bucket:{risk_profile}:metadata"
                    metadata = self.redis_client.get(metadata_key)
                    if metadata:
                        try:
                            stored_metadata = json.loads(metadata)
                            profile_summary['stored_hash'] = stored_metadata.get('data_dependency_hash', 'unknown')
                            profile_summary['last_updated'] = stored_metadata.get('last_updated', 'unknown')
                            profile_summary['portfolio_count'] = stored_metadata.get('portfolio_count', 0)
                        except json.JSONDecodeError:
                            profile_summary['metadata_error'] = 'Failed to decode metadata'
                
                summary['risk_profiles'][risk_profile] = profile_summary
                
                if has_changed:
                    changed_profiles.append(risk_profile)
                else:
                    unchanged_profiles.append(risk_profile)
                    
            except Exception as e:
                logger.error(f"Error checking data change for {risk_profile}: {e}")
                summary['risk_profiles'][risk_profile] = {
                    'risk_profile': risk_profile,
                    'error': str(e),
                    'data_changed': True  # Consider changed on error
                }
                changed_profiles.append(risk_profile)
        
        # Determine overall status
        if changed_profiles:
            summary['overall_status'] = 'data_changed'
            summary['changed_profiles'] = changed_profiles
            summary['unchanged_profiles'] = unchanged_profiles
            summary['change_percentage'] = (len(changed_profiles) / len(risk_profiles)) * 100
        else:
            summary['overall_status'] = 'no_changes'
            summary['unchanged_profiles'] = unchanged_profiles
            summary['change_percentage'] = 0.0
        
        return summary
    
    def get_monitoring_stocks_status(self) -> Dict[str, Dict]:
        """Get status of all monitoring stocks"""
        status = {}
        
        for stock in self.KEY_STOCKS:
            try:
                price_data = self.data_service.get_monthly_data(stock)
                
                if price_data and 'prices' in price_data:
                    prices = price_data['prices']
                    
                    status[stock] = {
                        'available': True,
                        'data_points': len(prices),
                        'last_price': prices[-1] if prices else None,
                        'last_updated': price_data.get('last_updated', 'unknown'),
                        'data_quality': 'good' if len(prices) >= 12 else 'insufficient'
                    }
                else:
                    status[stock] = {
                        'available': False,
                        'data_points': 0,
                        'last_price': None,
                        'last_updated': None,
                        'data_quality': 'missing'
                    }
                    
            except Exception as e:
                status[stock] = {
                    'available': False,
                    'error': str(e),
                    'data_quality': 'error'
                }
        
        return status
    
    def force_data_refresh_check(self) -> Dict[str, any]:
        """Force a complete data refresh check and return detailed results"""
        logger.info("🔄 Forcing complete data refresh check...")
        
        # Calculate current hash
        current_hash = self.calculate_data_dependency_hash()
        
        # Check all risk profiles
        change_summary = self.get_data_change_summary()
        
        # Get monitoring stocks status
        stocks_status = self.get_monitoring_stocks_status()
        
        # Compile comprehensive report
        report = {
            'timestamp': datetime.now().isoformat(),
            'current_data_hash': current_hash,
            'change_summary': change_summary,
            'monitoring_stocks': stocks_status,
            'recommendations': []
        }
        
        # Generate recommendations based on findings
        if change_summary['overall_status'] == 'data_changed':
            changed_count = len(change_summary.get('changed_profiles', []))
            report['recommendations'].append(f"Regenerate portfolios for {changed_count} risk profiles")
            
            if changed_count == len(risk_profiles):
                report['recommendations'].append("All portfolios need regeneration - consider system-wide refresh")
        
        # Check data quality issues
        poor_quality_stocks = [stock for stock, status in stocks_status.items() 
                             if status.get('data_quality') in ['insufficient', 'missing', 'error']]
        
        if poor_quality_stocks:
            report['recommendations'].append(f"Address data quality issues for {len(poor_quality_stocks)} stocks")
        
        logger.info(f"✅ Data refresh check completed. Status: {change_summary['overall_status']}")
        return report
    
    def get_data_health_score(self) -> float:
        """Calculate overall data health score (0-100)"""
        try:
            stocks_status = self.get_monitoring_stocks_status()
            
            if not stocks_status:
                return 0.0
            
            healthy_stocks = 0
            total_stocks = len(stocks_status)
            
            for stock, status in stocks_status.items():
                if status.get('available') and status.get('data_quality') == 'good':
                    healthy_stocks += 1
            
            health_score = (healthy_stocks / total_stocks) * 100
            return round(health_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating data health score: {e}")
            return 0.0
