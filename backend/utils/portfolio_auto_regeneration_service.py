#!/usr/bin/env python3
"""
Portfolio Auto-Regeneration Service
Regenerates portfolios every 4 days to increase stochastic variation
Automatically replaces previous portfolios with new ones
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .redis_portfolio_manager import RedisPortfolioManager
from .volatility_weighted_sector import invalidate_volatility_sector_weights_cache

logger = logging.getLogger(__name__)

class PortfolioAutoRegenerationService:
    """
    Portfolio regeneration service that runs every 4 days
    Replaces previous portfolios with new ones for better stochastic variation
    """
    
    def __init__(self, data_service, enhanced_generator: Any,
                 redis_manager: RedisPortfolioManager):
        """
        Initialize Portfolio Auto Regeneration Service
        Args:
            data_service: RedisFirstDataService or EnhancedDataFetcher instance
            enhanced_generator: Enhanced portfolio generator
            redis_manager: Redis portfolio manager
        """
        self.data_service = data_service
        self.enhanced_generator = enhanced_generator
        self.redis_manager = redis_manager
        
        # Data change detector removed - using time-based regeneration only
        
        # Service state
        self.is_running = False
        self.regeneration_thread = None
        self.last_regeneration = {}
        self.regeneration_stats = {
            'total_regenerations': 0,
            'successful_regenerations': 0,
            'failed_regenerations': 0,
            'last_regeneration_time': None,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time': 0,
            'average_processing_time': 0
        }
        
        # Configuration - Weekly regeneration
        self.REGENERATION_INTERVAL_DAYS = 7  # Regenerate every 7 days (1 week)
        self.REGENERATION_INTERVAL_SECONDS = self.REGENERATION_INTERVAL_DAYS * 24 * 3600
        self.CHECK_INTERVAL_HOURS = 24  # Check every 24 hours
        self.MAX_RETRY_ATTEMPTS = 3
        self.RETRY_DELAY_HOURS = 6
        
        # Risk profiles to monitor
        self.RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        
        logger.info("🚀 Portfolio Auto-Regeneration Service initialized")
        logger.info(f"📅 Regeneration interval: {self.REGENERATION_INTERVAL_DAYS} days (weekly)")
        logger.info(f"⏰ Check interval: {self.CHECK_INTERVAL_HOURS} hours (daily)")
    
    def trigger_regeneration(self, risk_profile: str = None) -> Dict[str, Any]:
        """Trigger manual portfolio regeneration for specific risk profile or all profiles"""
        try:
            if risk_profile:
                # Regenerate specific risk profile
                logger.info(f"🔄 Manual regeneration triggered for {risk_profile}")
                success = self._regenerate_portfolios(risk_profile)
                return {
                    'success': success,
                    'risk_profile': risk_profile,
                    'timestamp': datetime.now().isoformat(),
                    'message': f"Regeneration {'successful' if success else 'failed'} for {risk_profile}"
                }
            else:
                # Regenerate all risk profiles
                logger.info("🔄 Manual regeneration triggered for all risk profiles")
                results = {}
                for profile in self.RISK_PROFILES:
                    success = self._regenerate_portfolios(profile)
                    results[profile] = success
                    self.last_regeneration[profile] = datetime.now()
                
                successful_count = sum(1 for success in results.values() if success)
                return {
                    'success': successful_count == len(self.RISK_PROFILES),
                    'results': results,
                    'successful_count': successful_count,
                    'total_count': len(self.RISK_PROFILES),
                    'timestamp': datetime.now().isoformat(),
                    'message': f"Regenerated {successful_count}/{len(self.RISK_PROFILES)} risk profiles"
                }
        except Exception as e:
            logger.error(f"❌ Error during manual regeneration: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'message': f"Regeneration failed: {str(e)}"
            }
    
    def stop_monitoring(self):
        """Stop portfolio regeneration monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.regeneration_thread:
            self.regeneration_thread.join(timeout=5)
        logger.info("🛑 Portfolio auto-regeneration service stopped")
    
    # Monitoring loop removed - using manual trigger only
    
    # Check and regenerate function removed - using manual trigger only
    
    # Time-based regeneration check removed - using manual trigger only
    
    def _regenerate_portfolios(self, risk_profile: str, retry_count: int = 0) -> bool:
        """Regenerate portfolios for a specific risk profile with retry logic"""
        try:
            logger.info(f"🔄 Regenerating portfolios for {risk_profile}...")
            
            # Generate new portfolios with stochastic variation
            new_portfolios = self.enhanced_generator.generate_portfolio_bucket(risk_profile)
            
            if not new_portfolios or len(new_portfolios) < 12:
                raise Exception(f"Generated only {len(new_portfolios) if new_portfolios else 0} portfolios, expected 12")
            
            # Validate portfolio uniqueness
            unique_portfolios = [p for p in new_portfolios if p]  # Remove any None portfolios
            if len(unique_portfolios) < 12:
                logger.warning(f"⚠️ Only {len(unique_portfolios)} unique portfolios generated for {risk_profile}, regenerating...")
                # Try one more time to get unique portfolios
                retry_portfolios = self.enhanced_generator.generate_portfolio_bucket(risk_profile)
                unique_portfolios = [p for p in retry_portfolios if p]
                
                if len(unique_portfolios) < 12:
                    raise Exception(f"Failed to generate 12 unique portfolios after retry. Got {len(unique_portfolios)}")
            
            logger.info(f"✅ Generated {len(unique_portfolios)} unique portfolios for {risk_profile}")
            
            # Clear old portfolios first (for clean replacement)
            logger.info(f"🧹 Clearing old portfolios for {risk_profile}")
            self.redis_manager.clear_portfolio_bucket(risk_profile)
            
            # Store new portfolios (replaces the old ones)
            storage_success = self.redis_manager.store_portfolio_bucket(risk_profile, unique_portfolios)
            
            if not storage_success:
                raise Exception("Failed to store new portfolios in Redis")
            
            # Invalidate sector weights cache so next access recomputes with fresh data
            try:
                redis_client = getattr(self.data_service, 'redis_client', None) or getattr(self.data_service, 'r', None)
                if redis_client:
                    invalidate_volatility_sector_weights_cache(redis_client, risk_profile)
            except Exception as e:
                logger.debug(f"Sector weights cache invalidation skipped: {e}")
            
            # Update statistics
            self.regeneration_stats['total_regenerations'] += 1
            self.regeneration_stats['successful_regenerations'] += 1
            self.regeneration_stats['last_regeneration_time'] = datetime.now().isoformat()
            
            logger.info(f"✅ Successfully regenerated and replaced {len(unique_portfolios)} portfolios for {risk_profile}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to regenerate portfolios for {risk_profile}: {e}")
            
            # Update statistics
            self.regeneration_stats['total_regenerations'] += 1
            self.regeneration_stats['failed_regenerations'] += 1
            
            # Retry logic
            if retry_count < self.MAX_RETRY_ATTEMPTS:
                logger.info(f"🔄 Retrying regeneration for {risk_profile} (attempt {retry_count + 1}/{self.MAX_RETRY_ATTEMPTS})")
                time.sleep(self.RETRY_DELAY_HOURS * 3600)
                return self._regenerate_portfolios(risk_profile, retry_count + 1)
            
            return False
    
    def force_regeneration(self, risk_profile: str = None) -> Dict[str, any]:
        """Force regeneration of portfolios for specific or all risk profiles"""
        try:
            if risk_profile:
                risk_profiles = [risk_profile]
                logger.info(f"🔄 Forcing portfolio regeneration for {risk_profile}")
            else:
                risk_profiles = self.RISK_PROFILES
                logger.info("🔄 Forcing portfolio regeneration for all risk profiles")
            
            results = {}
            
            for profile in risk_profiles:
                try:
                    start_time = time.time()
                    success = self._regenerate_portfolios(profile)
                    duration = time.time() - start_time
                    
                    results[profile] = {
                        'success': success,
                        'duration_seconds': round(duration, 2),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if success:
                        logger.info(f"✅ Forced regeneration successful for {profile}")
                    else:
                        logger.error(f"❌ Forced regeneration failed for {profile}")
                        
                except Exception as e:
                    logger.error(f"❌ Error during forced regeneration for {profile}: {e}")
                    results[profile] = {
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {
                'forced_regeneration': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error during forced regeneration: {e}")
            return {
                'forced_regeneration': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_service_status(self) -> Dict[str, any]:
        """Get current service status and statistics"""
        return {
            'service_running': self.is_running,
            'last_check': datetime.now().isoformat(),
            'regeneration_interval_days': self.REGENERATION_INTERVAL_DAYS,
            'check_interval_hours': self.CHECK_INTERVAL_HOURS,
            'regeneration_stats': self.regeneration_stats,
            'last_regeneration': self.last_regeneration,
            'data_health_score': 'N/A (data change detection removed)',
            'portfolio_buckets_status': self.redis_manager.get_all_portfolio_buckets_status(),
            'optimization_features': {
                'stock_cache_enabled': True,
                'shared_stock_data': True,
                'batch_portfolio_generation': True,
                'smart_regeneration_scheduling': True
            }
        }
    
    def get_regeneration_history(self) -> Dict[str, List]:
        """Get regeneration history for all risk profiles"""
        history = {}
        
        for risk_profile in self.RISK_PROFILES:
            try:
                metadata = self.redis_manager.get_portfolio_metadata(risk_profile)
                if metadata:
                    history[risk_profile] = {
                        'last_generated': metadata.get('generated_at'),
                        'last_updated': metadata.get('last_updated'),
                        'portfolio_count': metadata.get('portfolio_count'),
                        'data_dependency_hash': metadata.get('data_dependency_hash', 'unknown')[:8] + '...'
                    }
                else:
                    history[risk_profile] = {
                        'status': 'no_metadata',
                        'last_generated': None,
                        'last_updated': None
                    }
                    
            except Exception as e:
                history[risk_profile] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return history
    
    def emergency_regeneration(self) -> Dict[str, any]:
        """Emergency regeneration when system detects critical issues"""
        logger.critical("🚨 EMERGENCY: Starting emergency portfolio regeneration")
        
        try:
            # Force regeneration for all profiles
            results = self.force_regeneration()
            
            # Clear any corrupted data
            for risk_profile in self.RISK_PROFILES:
                try:
                    self.redis_manager.clear_portfolio_bucket(risk_profile)
                    logger.info(f"🧹 Cleared portfolio bucket for {risk_profile}")
                except Exception as e:
                    logger.error(f"❌ Failed to clear portfolio bucket for {risk_profile}: {e}")
            
            # Regenerate all portfolios
            regeneration_results = {}
            for risk_profile in self.RISK_PROFILES:
                try:
                    success = self._regenerate_portfolios(risk_profile)
                    regeneration_results[risk_profile] = {
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    regeneration_results[risk_profile] = {
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
            
            emergency_report = {
                'emergency_regeneration': True,
                'timestamp': datetime.now().isoformat(),
                'clear_results': results,
                'regeneration_results': regeneration_results,
                'data_health_after': 'N/A (data change detection removed)'
            }
            
            logger.critical(f"🚨 Emergency regeneration completed. Results: {emergency_report}")
            return emergency_report
            
        except Exception as e:
            logger.critical(f"🚨 Emergency regeneration failed: {e}")
            return {
                'emergency_regeneration': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def update_configuration(self, regeneration_interval_days: int = None):
        """Update service configuration"""
        if regeneration_interval_days is not None:
            self.REGENERATION_INTERVAL_DAYS = regeneration_interval_days
            self.REGENERATION_INTERVAL_SECONDS = self.REGENERATION_INTERVAL_DAYS * 24 * 3600
            logger.info(f"📝 Updated regeneration interval to {regeneration_interval_days} days")
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get performance metrics for the service"""
        try:
            # Calculate success rate
            total = self.regeneration_stats['total_regenerations']
            successful = self.regeneration_stats['successful_regenerations']
            failed = self.regeneration_stats['failed_regenerations']
            
            success_rate = (successful / total * 100) if total > 0 else 0
            
            # Data health metrics removed (data change detection removed)
            data_health = 'N/A'
            
            # Get portfolio availability
            portfolio_status = self.redis_manager.get_all_portfolio_buckets_status()
            available_buckets = sum(1 for status in portfolio_status.values() if status.get('available'))
            
            return {
                'total_regenerations': total,
                'successful_regenerations': successful,
                'failed_regenerations': failed,
                'success_rate_percent': round(success_rate, 1),
                'data_health_score': data_health,
                'available_portfolio_buckets': available_buckets,
                'total_portfolio_buckets': len(self.RISK_PROFILES),
                'last_regeneration_time': self.regeneration_stats.get('last_regeneration_time'),
                'service_uptime': self.is_running,
                'regeneration_interval_days': self.REGENERATION_INTERVAL_DAYS
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
