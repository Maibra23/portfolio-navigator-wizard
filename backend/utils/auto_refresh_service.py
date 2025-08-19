#!/usr/bin/env python3
"""
Integrated Auto Refresh Service for Original Ticker Table
Provides automatic TTL-based refresh with tracking and notifications
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import redis
import json

logger = logging.getLogger(__name__)

class AutoRefreshService:
    """
    Automatic refresh service that monitors TTL and refreshes data automatically
    """
    
    def __init__(self, data_service, notification_callback: Optional[Callable] = None):
        """
        Initialize Auto Refresh Service
        Args:
            data_service: RedisFirstDataService or EnhancedDataFetcher instance
            notification_callback: Optional callback for notifications
        """
        self.data_service = data_service
        self.notification_callback = notification_callback
        
        # Handle both RedisFirstDataService and EnhancedDataFetcher
        if hasattr(data_service, 'redis_client'):
            self.r = data_service.redis_client
        else:
            self.r = data_service.r
            
        self.is_running = False
        self.refresh_thread = None
        self.tracking_data = {}
        
        # Configuration
        self.CACHE_TTL_DAYS = 28
        self.WARNING_DAYS_BEFORE = 2  # Warning 2 days before refresh
        self.CHECK_INTERVAL_HOURS = 6  # Check every 6 hours
        self.REFRESH_BUFFER_DAYS = 1  # Refresh 1 day before TTL expires
        
        # Initialize tracking
        self._initialize_tracking()
    
    def _initialize_tracking(self):
        """Initialize tracking data for all tickers"""
        if not self.r:
            return
        
        try:
            for ticker in self.data_service.all_tickers:
                self._update_ticker_tracking(ticker)
        except Exception as e:
            logger.error(f"Error initializing tracking: {e}")
    
    def _update_ticker_tracking(self, ticker: str):
        """Update tracking information for a specific ticker"""
        try:
            # Get TTL for prices and sector data
            price_key = self.data_service._get_cache_key(ticker, 'prices')
            sector_key = self.data_service._get_cache_key(ticker, 'sector')
            
            price_ttl = self.r.ttl(price_key) if self.r.exists(price_key) else -1
            sector_ttl = self.r.ttl(sector_key) if self.r.exists(sector_key) else -1
            
            # Calculate days remaining
            price_days_left = price_ttl // 86400 if price_ttl > 0 else 0
            sector_days_left = sector_ttl // 86400 if sector_ttl > 0 else 0
            
            # Determine next refresh date
            if price_ttl > 0:
                next_refresh = datetime.now() + timedelta(seconds=price_ttl)
            else:
                next_refresh = datetime.now()
            
            # Check data quality
            data_quality = self._check_ticker_data_quality(ticker)
            
            self.tracking_data[ticker] = {
                'price_ttl_seconds': price_ttl,
                'sector_ttl_seconds': sector_ttl,
                'price_days_left': price_days_left,
                'sector_days_left': sector_days_left,
                'next_refresh': next_refresh.isoformat(),
                'data_quality': data_quality,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating tracking for {ticker}: {e}")
    
    def _check_ticker_data_quality(self, ticker: str) -> Dict:
        """Check data quality for a ticker"""
        try:
            ticker_info = self.data_service.get_ticker_info(ticker)
            if not ticker_info:
                return {'status': 'missing', 'issues': ['No data available']}
            
            issues = []
            
            # Check sector information
            if ticker_info.get('sector') in ['Unknown', 'N/A', None]:
                issues.append('Unknown sector')
            if ticker_info.get('industry') in ['Unknown', 'N/A', None]:
                issues.append('Unknown industry')
            
            # Check price data
            if ticker_info.get('data_points', 0) < 12:
                issues.append('Insufficient price data')
            
            # Check current price
            if ticker_info.get('current_price', 0) <= 0:
                issues.append('Invalid current price')
            
            status = 'good' if not issues else 'warning' if len(issues) <= 2 else 'critical'
            
            return {
                'status': status,
                'issues': issues,
                'data_points': ticker_info.get('data_points', 0),
                'sector': ticker_info.get('sector', 'Unknown'),
                'industry': ticker_info.get('industry', 'Unknown')
            }
            
        except Exception as e:
            return {'status': 'error', 'issues': [f'Error checking data: {str(e)}']}
    
    def start_auto_refresh_service(self):
        """Start the automatic refresh service"""
        if self.is_running:
            logger.warning("Auto refresh service is already running")
            return
        
        self.is_running = True
        self.refresh_thread = threading.Thread(target=self._refresh_service_loop, daemon=True)
        self.refresh_thread.start()
        logger.info("🚀 Automatic refresh service started")
    
    def stop_auto_refresh_service(self):
        """Stop the automatic refresh service"""
        self.is_running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        logger.info("🛑 Automatic refresh service stopped")
    
    def _refresh_service_loop(self):
        """Main loop for the refresh service"""
        while self.is_running:
            try:
                self._check_and_refresh()
                time.sleep(self.CHECK_INTERVAL_HOURS * 3600)  # Sleep for configured interval
            except Exception as e:
                logger.error(f"Error in refresh service loop: {e}")
                time.sleep(3600)  # Sleep for 1 hour on error
    
    def _check_and_refresh(self):
        """Check which tickers need refresh and handle notifications"""
        logger.info("🔄 Auto refresh service checking tickers...")
        
        refresh_needed = []
        warnings_needed = []
        
        for ticker in self.data_service.all_tickers:
            self._update_ticker_tracking(ticker)
            tracking = self.tracking_data.get(ticker, {})
            
            days_left = min(tracking.get('price_days_left', 0), tracking.get('sector_days_left', 0))
            
            # Check if refresh is needed
            if days_left <= self.REFRESH_BUFFER_DAYS:
                refresh_needed.append(ticker)
            
            # Check if warning should be sent
            elif days_left <= self.WARNING_DAYS_BEFORE:
                warnings_needed.append(ticker)
        
        # Send warnings
        if warnings_needed:
            self._send_warning_notification(warnings_needed)
        
        # Perform refresh if needed
        if refresh_needed:
            self._perform_automatic_refresh(refresh_needed)
    
    def _send_warning_notification(self, tickers: List[str]):
        """Send warning notification for tickers approaching TTL"""
        warning_msg = {
            'type': 'ttl_warning',
            'message': f'⚠️ {len(tickers)} tickers will refresh in {self.WARNING_DAYS_BEFORE} days',
            'tickers': tickers,
            'timestamp': datetime.now().isoformat(),
            'days_until_refresh': self.WARNING_DAYS_BEFORE
        }
        
        logger.info(f"⚠️ TTL Warning: {len(tickers)} tickers approaching refresh")
        
        if self.notification_callback:
            self.notification_callback(warning_msg)
    
    def _perform_automatic_refresh(self, tickers: List[str]):
        """Perform automatic refresh for tickers"""
        logger.info(f"🔄 Performing automatic refresh for {len(tickers)} tickers")
        
        try:
            # Use the enhanced data fetcher's smart monthly refresh
            self.data_service.smart_monthly_refresh()
            
            # Update tracking after refresh
            for ticker in tickers:
                self._update_ticker_tracking(ticker)
            
            # Send refresh completion notification
            completion_msg = {
                'type': 'refresh_completed',
                'message': f'✅ Automatic refresh completed for {len(tickers)} tickers',
                'tickers': tickers,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.notification_callback:
                self.notification_callback(completion_msg)
                
        except Exception as e:
            logger.error(f"Error during automatic refresh: {e}")
    
    def get_tracking_summary(self) -> Dict:
        """Get summary of tracking information"""
        if not self.tracking_data:
            return {}
        
        total_tickers = len(self.tracking_data)
        critical_count = 0
        warning_count = 0
        good_count = 0
        
        for tracking in self.tracking_data.values():
            quality = tracking.get('data_quality', {})
            status = quality.get('status', 'unknown')
            
            if status == 'critical':
                critical_count += 1
            elif status == 'warning':
                warning_count += 1
            elif status == 'good':
                good_count += 1
        
        # Find tickers needing immediate attention
        immediate_refresh = []
        warnings = []
        
        for ticker, tracking in self.tracking_data.items():
            days_left = min(tracking.get('price_days_left', 0), tracking.get('sector_days_left', 0))
            
            if days_left <= self.REFRESH_BUFFER_DAYS:
                immediate_refresh.append(ticker)
            elif days_left <= self.WARNING_DAYS_BEFORE:
                warnings.append(ticker)
        
        return {
            'total_tickers': total_tickers,
            'data_quality': {
                'critical': critical_count,
                'warning': warning_count,
                'good': good_count
            },
            'refresh_status': {
                'immediate_refresh_needed': len(immediate_refresh),
                'warnings': len(warnings),
                'immediate_tickers': immediate_refresh,
                'warning_tickers': warnings
            },
            'next_check': (datetime.now() + timedelta(hours=self.CHECK_INTERVAL_HOURS)).isoformat(),
            'service_status': 'running' if self.is_running else 'stopped'
        }
    
    def get_ticker_tracking(self, ticker: str) -> Optional[Dict]:
        """Get tracking information for a specific ticker"""
        return self.tracking_data.get(ticker)
    
    def force_refresh_ticker(self, ticker: str) -> bool:
        """Force refresh a specific ticker"""
        try:
            logger.info(f"🔄 Force refreshing {ticker}")
            
            # Use the enhanced data fetcher to refresh
            data = self.data_service._fetch_single_ticker_with_retry(ticker)
            
            if data:
                self._update_ticker_tracking(ticker)
                logger.info(f"✅ {ticker} force refresh successful")
                return True
            else:
                logger.error(f"❌ {ticker} force refresh failed")
                return False
                
        except Exception as e:
            logger.error(f"Error force refreshing {ticker}: {e}")
            return False
