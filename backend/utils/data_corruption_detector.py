#!/usr/bin/env python3
"""
Comprehensive Data Corruption Detection System
Integrates with cache warming to detect and warn about corrupted data
"""

import logging
import pandas as pd
import numpy as np
import json
import gzip
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class DataCorruptionDetector:
    """
    Advanced data corruption detection system that:
    1. Scans all cached data for corruption
    2. Provides detailed corruption reports
    3. Integrates with cache warming process
    4. Offers automatic corruption repair options
    """
    
    def __init__(self, data_service):
        """
        Initialize Data Corruption Detector
        Args:
            data_service: RedisFirstDataService or EnhancedDataFetcher instance
        """
        self.data_service = data_service
        
        # Handle both RedisFirstDataService and EnhancedDataFetcher
        if hasattr(data_service, 'redis_client'):
            self.redis_client = data_service.redis_client
        else:
            self.redis_client = data_service.r
        self.corruption_report = {
            'scan_timestamp': None,
            'total_tickers_scanned': 0,
            'corruption_summary': {
                'critical': 0,
                'warning': 0,
                'good': 0,
                'missing': 0
            },
            'corrupted_tickers': [],
            'corruption_details': {},
            'recommendations': []
        }
        
        # Corruption severity thresholds
        self.CORRUPTION_THRESHOLDS = {
            'critical': {
                'max_missing_ratio': 0.5,      # >50% missing data
                'max_zero_ratio': 0.3,         # >30% zero prices
                'min_data_points': 6,          # <6 months of data
                'max_price_anomaly': 100000    # >$100k price
            },
            'warning': {
                'max_missing_ratio': 0.2,      # >20% missing data
                'max_zero_ratio': 0.1,         # >10% zero prices
                'min_data_points': 12,         # <12 months of data
                'max_price_anomaly': 10000     # >$10k price
            }
        }
    
    def scan_all_data_for_corruption(self) -> Dict[str, Any]:
        """
        Comprehensive scan of all cached data for corruption
        Returns: Detailed corruption report
        """
        logger.info("🔍 Starting comprehensive data corruption scan...")
        
        if not self.redis_client:
            logger.error("❌ Redis unavailable - cannot scan for corruption")
            return self._create_error_report("Redis unavailable")
        
        # Reset report
        self.corruption_report = {
            'scan_timestamp': datetime.now().isoformat(),
            'total_tickers_scanned': 0,
            'corruption_summary': {'critical': 0, 'warning': 0, 'good': 0, 'missing': 0},
            'corrupted_tickers': [],
            'corruption_details': {},
            'recommendations': []
        }
        
        total_tickers = len(self.data_service.all_tickers)
        logger.info(f"📊 Scanning {total_tickers} tickers for corruption...")
        
        for i, ticker in enumerate(self.data_service.all_tickers):
            if i % 100 == 0:
                logger.info(f"🔍 Progress: {i}/{total_tickers} tickers scanned...")
            
            corruption_status = self._analyze_ticker_corruption(ticker)
            self.corruption_report['total_tickers_scanned'] += 1
            
            # Categorize corruption
            if corruption_status['severity'] == 'critical':
                self.corruption_report['corruption_summary']['critical'] += 1
                self.corruption_report['corrupted_tickers'].append(ticker)
            elif corruption_status['severity'] == 'warning':
                self.corruption_report['corruption_summary']['warning'] += 1
                self.corruption_report['corrupted_tickers'].append(ticker)
            elif corruption_status['severity'] == 'missing':
                self.corruption_report['corruption_summary']['missing'] += 1
            else:
                self.corruption_report['corruption_summary']['good'] += 1
            
            # Store detailed corruption info
            if corruption_status['severity'] != 'good':
                self.corruption_report['corruption_details'][ticker] = corruption_status
        
        # Generate recommendations
        self._generate_corruption_recommendations()
        
        # Log summary
        logger.info("✅ Data corruption scan completed!")
        logger.info(f"📊 Results: {self.corruption_report['corruption_summary']}")
        
        return self.corruption_report
    
    def _analyze_ticker_corruption(self, ticker: str) -> Dict[str, Any]:
        """
        Analyze corruption level for a specific ticker
        Returns: Corruption status with severity and details
        """
        try:
            # Check if ticker exists in cache
            price_key = self.data_service._get_cache_key(ticker, 'prices')
            sector_key = self.data_service._get_cache_key(ticker, 'sector')
            
            if not self.redis_client.exists(price_key):
                return {
                    'severity': 'missing',
                    'issues': ['No price data in cache'],
                    'data_points': 0,
                    'missing_ratio': 1.0,
                    'zero_ratio': 0.0,
                    'price_range': None,
                    'recommendation': 'Fetch data from yfinance'
                }
            
            # Load and analyze price data
            cached_prices = self.data_service._load_from_cache(ticker, 'prices')
            if cached_prices is None or not isinstance(cached_prices, pd.Series):
                return {
                    'severity': 'critical',
                    'issues': ['Invalid price data format'],
                    'data_points': 0,
                    'missing_ratio': 1.0,
                    'zero_ratio': 0.0,
                    'price_range': None,
                    'recommendation': 'Clear cache and re-fetch'
                }
            
            # Analyze data quality
            data_points = len(cached_prices)
            missing_ratio = cached_prices.isna().sum() / data_points if data_points > 0 else 1.0
            zero_ratio = (cached_prices == 0).sum() / data_points if data_points > 0 else 0.0
            price_range = (cached_prices.min(), cached_prices.max()) if data_points > 0 else (None, None)
            
            # Check for anomalies
            issues = []
            if data_points < self.CORRUPTION_THRESHOLDS['critical']['min_data_points']:
                issues.append(f'Insufficient data points: {data_points}')
            if missing_ratio > self.CORRUPTION_THRESHOLDS['critical']['max_missing_ratio']:
                issues.append(f'High missing data: {missing_ratio:.1%}')
            if zero_ratio > self.CORRUPTION_THRESHOLDS['critical']['max_zero_ratio']:
                issues.append(f'High zero prices: {zero_ratio:.1%}')
            if price_range[1] and price_range[1] > self.CORRUPTION_THRESHOLDS['critical']['max_price_anomaly']:
                issues.append(f'Suspicious high price: ${price_range[1]:,.2f}')
            
            # Determine severity
            if issues:
                if any([
                    data_points < self.CORRUPTION_THRESHOLDS['critical']['min_data_points'],
                    missing_ratio > self.CORRUPTION_THRESHOLDS['critical']['max_missing_ratio'],
                    zero_ratio > self.CORRUPTION_THRESHOLDS['critical']['max_zero_ratio']
                ]):
                    severity = 'critical'
                else:
                    severity = 'warning'
            else:
                severity = 'good'
            
            # Generate recommendation
            recommendation = self._generate_ticker_recommendation(severity, issues, data_points)
            
            return {
                'severity': severity,
                'issues': issues,
                'data_points': data_points,
                'missing_ratio': missing_ratio,
                'zero_ratio': zero_ratio,
                'price_range': price_range,
                'recommendation': recommendation
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing corruption for {ticker}: {e}")
            return {
                'severity': 'critical',
                'issues': [f'Analysis error: {str(e)}'],
                'data_points': 0,
                'missing_ratio': 1.0,
                'zero_ratio': 0.0,
                'price_range': None,
                'recommendation': 'Investigate and repair'
            }
    
    def _generate_ticker_recommendation(self, severity: str, issues: List[str], data_points: int) -> str:
        """Generate specific recommendation for ticker based on corruption level"""
        if severity == 'good':
            return 'Data is healthy'
        elif severity == 'missing':
            return 'Fetch data from yfinance'
        elif severity == 'critical':
            if data_points == 0:
                return 'Clear cache and re-fetch from yfinance'
            elif data_points < 6:
                return 'Re-fetch with extended time range'
            else:
                return 'Clear cache and re-fetch from yfinance'
        else:  # warning
            return 'Monitor and consider refresh if issues persist'
    
    def _generate_corruption_recommendations(self):
        """Generate system-wide recommendations based on corruption scan"""
        critical_count = self.corruption_report['corruption_summary']['critical']
        warning_count = self.corruption_report['corruption_summary']['warning']
        missing_count = self.corruption_report['corruption_summary']['missing']
        
        recommendations = []
        
        if critical_count > 0:
            recommendations.append({
                'priority': 'high',
                'action': 'Immediate cache refresh required',
                'description': f'{critical_count} tickers have critical corruption issues',
                'command': 'make warm-cache'
            })
        
        if warning_count > 0:
            recommendations.append({
                'priority': 'medium',
                'action': 'Monitor and consider refresh',
                'description': f'{warning_count} tickers have minor data quality issues',
                'command': 'Check individual ticker details'
            })
        
        if missing_count > 0:
            recommendations.append({
                'priority': 'medium',
                'action': 'Fetch missing data',
                'description': f'{missing_count} tickers are missing from cache',
                'command': 'make warm-cache'
            })
        
        if critical_count == 0 and warning_count == 0 and missing_count == 0:
            recommendations.append({
                'priority': 'low',
                'action': 'System is healthy',
                'description': 'All data is valid and up-to-date',
                'command': 'Continue normal operation'
            })
        
        self.corruption_report['recommendations'] = recommendations
    
    def get_corruption_summary(self) -> Dict[str, Any]:
        """Get a summary of corruption status"""
        if not self.corruption_report['scan_timestamp']:
            return {'status': 'not_scanned', 'message': 'Run scan_all_data_for_corruption() first'}
        
        return {
            'status': 'scanned',
            'timestamp': self.corruption_report['scan_timestamp'],
            'summary': self.corruption_report['corruption_summary'],
            'total_corrupted': len(self.corruption_report['corrupted_tickers']),
            'recommendations': self.corruption_report['recommendations']
        }
    
    def get_corrupted_tickers_list(self) -> List[str]:
        """Get list of all corrupted tickers"""
        return self.corruption_report['corrupted_tickers'].copy()
    
    def get_ticker_corruption_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get detailed corruption information for a specific ticker"""
        return self.corruption_report['corruption_details'].get(ticker)
    
    def is_system_healthy(self) -> bool:
        """Check if the system has any critical corruption issues"""
        if not self.corruption_report['scan_timestamp']:
            return False  # Not scanned yet
        
        return self.corruption_report['corruption_summary']['critical'] == 0
    
    def get_health_status(self) -> str:
        """Get human-readable health status"""
        if not self.corruption_report['scan_timestamp']:
            return 'Not Scanned'
        
        critical = self.corruption_report['corruption_summary']['critical']
        warning = self.corruption_report['corruption_summary']['warning']
        
        if critical > 0:
            return f'🚨 CRITICAL ({critical} tickers)'
        elif warning > 0:
            return f'⚠️ WARNING ({warning} tickers)'
        else:
            return '✅ HEALTHY'
    
    def _create_error_report(self, error_message: str) -> Dict[str, Any]:
        """Create error report when scan fails"""
        return {
            'scan_timestamp': datetime.now().isoformat(),
            'error': error_message,
            'corruption_summary': {'critical': 0, 'warning': 0, 'good': 0, 'missing': 0},
            'corrupted_tickers': [],
            'corruption_details': {},
            'recommendations': [{
                'priority': 'high',
                'action': 'Fix system issue',
                'description': error_message,
                'command': 'Check Redis connection and system status'
            }]
        }
    
    def print_corruption_report(self):
        """Print a formatted corruption report to console"""
        if not self.corruption_report['scan_timestamp']:
            print("❌ No corruption scan has been performed yet")
            return
        
        print("\n" + "=" * 80)
        print("🔍 DATA CORRUPTION SCAN REPORT")
        print("=" * 80)
        print(f"📅 Scan Time: {self.corruption_report['scan_timestamp']}")
        print(f"📊 Total Tickers Scanned: {self.corruption_report['total_tickers_scanned']}")
        print()
        
        # Summary
        summary = self.corruption_report['corruption_summary']
        print("📈 CORRUPTION SUMMARY:")
        print(f"   🚨 Critical Issues: {summary['critical']}")
        print(f"   ⚠️  Warning Issues: {summary['warning']}")
        print(f"   ✅ Good Data: {summary['good']}")
        print(f"   ❓ Missing Data: {summary['missing']}")
        print()
        
        # Health Status
        health = self.get_health_status()
        print(f"🏥 SYSTEM HEALTH: {health}")
        print()
        
        # Recommendations
        if self.corruption_report['recommendations']:
            print("💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.corruption_report['recommendations'], 1):
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                print(f"   {i}. {priority_icon} {rec['action']}")
                print(f"      📝 {rec['description']}")
                print(f"      💻 Command: {rec['command']}")
                print()
        
        # Critical Issues Detail
        if summary['critical'] > 0:
            print("🚨 CRITICAL ISSUES DETAIL:")
            critical_tickers = [t for t, details in self.corruption_report['corruption_details'].items() 
                              if details['severity'] == 'critical']
            for ticker in critical_tickers[:10]:  # Show first 10
                details = self.corruption_report['corruption_details'][ticker]
                print(f"   • {ticker}: {', '.join(details['issues'])}")
            if len(critical_tickers) > 10:
                print(f"   ... and {len(critical_tickers) - 10} more critical tickers")
            print()
        
        print("=" * 80)
