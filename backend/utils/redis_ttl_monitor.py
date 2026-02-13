#!/usr/bin/env python3
"""
Redis TTL Monitor and Notification System
Monitors Redis cache expiration and sends notifications when TTL is low
"""

import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RedisTTLMonitor:
    """
    Monitors Redis TTL for cached ticker data and sends notifications
    when data is close to expiration
    """

    # Thresholds for notifications (in days)
    CRITICAL_THRESHOLD = 1   # < 1 day left
    WARNING_THRESHOLD = 7    # < 7 days left
    INFO_THRESHOLD = 14      # < 14 days left

    def __init__(self, redis_client: redis.Redis, notification_callback=None):
        """
        Initialize TTL Monitor

        Args:
            redis_client: Redis client instance
            notification_callback: Optional callback function for notifications
                                 Signature: callback(level: str, message: str, data: dict)
        """
        self.redis_client = redis_client
        self.notification_callback = notification_callback
        self.last_check_time = None

        logger.info("✅ Redis TTL Monitor initialized")

    def check_ttl_status(self) -> Dict:
        """
        Check TTL status for all cached ticker data

        Returns:
            Dict with TTL status and statistics
        """
        try:
            self.last_check_time = datetime.now()

            # Get all ticker data keys
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            metrics_keys = self.redis_client.keys("ticker_data:metrics:*")

            # Extract tickers with both prices and sector (complete cache)
            tickers_with_prices = {self._extract_ticker(k, "ticker_data:prices:")
                                  for k in price_keys}
            tickers_with_sector = {self._extract_ticker(k, "ticker_data:sector:")
                                  for k in sector_keys}

            complete_tickers = tickers_with_prices & tickers_with_sector

            # Categorize by TTL
            ttl_categories = {
                'critical': [],    # < 1 day
                'warning': [],     # < 7 days
                'info': [],        # < 14 days
                'healthy': [],     # >= 14 days
                'expired': []      # Already expired
            }

            total_tickers = len(complete_tickers)

            for ticker in sorted(complete_tickers):
                ttl_info = self._get_ticker_ttl(ticker)

                if ttl_info['days_left'] < 0:
                    ttl_categories['expired'].append((ticker, ttl_info))
                elif ttl_info['days_left'] < self.CRITICAL_THRESHOLD:
                    ttl_categories['critical'].append((ticker, ttl_info))
                elif ttl_info['days_left'] < self.WARNING_THRESHOLD:
                    ttl_categories['warning'].append((ticker, ttl_info))
                elif ttl_info['days_left'] < self.INFO_THRESHOLD:
                    ttl_categories['info'].append((ticker, ttl_info))
                else:
                    ttl_categories['healthy'].append((ticker, ttl_info))

            # Get detailed Redis stats
            redis_stats = self.get_detailed_redis_stats()

            status = {
                'timestamp': self.last_check_time.isoformat(),
                'total_tickers': total_tickers,
                'categories': {
                    'expired': len(ttl_categories['expired']),
                    'critical': len(ttl_categories['critical']),
                    'warning': len(ttl_categories['warning']),
                    'info': len(ttl_categories['info']),
                    'healthy': len(ttl_categories['healthy'])
                },
                'details': ttl_categories,
                'redis_stats': redis_stats,
                'needs_action': len(ttl_categories['expired']) > 0 or
                               len(ttl_categories['critical']) > 0
            }

            # Send notifications if needed
            self._send_notifications(status)

            return status

        except Exception as e:
            logger.error(f"Error checking TTL status: {e}")
            return {'error': str(e)}

    def _get_ticker_ttl(self, ticker: str) -> Dict:
        """Get TTL information for a specific ticker"""
        price_key = f"ticker_data:prices:{ticker}"
        sector_key = f"ticker_data:sector:{ticker}"
        metrics_key = f"ticker_data:metrics:{ticker}"

        # Get TTL for each key type
        ttl_price = self.redis_client.ttl(price_key) if self.redis_client.exists(price_key) else -2
        ttl_sector = self.redis_client.ttl(sector_key) if self.redis_client.exists(sector_key) else -2
        ttl_metrics = self.redis_client.ttl(metrics_key) if self.redis_client.exists(metrics_key) else -2

        # Effective TTL is the minimum (most urgent)
        effective_ttl = min([t for t in [ttl_price, ttl_sector] if t >= 0], default=-2)

        days_left = effective_ttl / 86400.0 if effective_ttl > 0 else -1

        return {
            'ticker': ticker,
            'ttl_seconds': effective_ttl,
            'days_left': days_left,
            'ttl_price': ttl_price,
            'ttl_sector': ttl_sector,
            'ttl_metrics': ttl_metrics,
            'expires_at': (datetime.now() + timedelta(seconds=effective_ttl)).isoformat()
                         if effective_ttl > 0 else 'expired'
        }

    def _extract_ticker(self, key: bytes, prefix: str) -> str:
        """Extract ticker symbol from Redis key"""
        key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
        return key_str.replace(prefix, '').strip()

    def _send_notifications(self, status: Dict):
        """Send notifications based on TTL status"""
        categories = status.get('categories', {})

        # Critical: Immediate action needed
        if categories.get('critical', 0) > 0:
            message = (f"🚨 CRITICAL: {categories['critical']} tickers expiring within "
                      f"{self.CRITICAL_THRESHOLD} day(s)")
            self._notify('CRITICAL', message, status)
            logger.error(message)

        # Warning: Action needed soon
        if categories.get('warning', 0) > 0:
            message = (f"⚠️  WARNING: {categories['warning']} tickers expiring within "
                      f"{self.WARNING_THRESHOLD} days")
            self._notify('WARNING', message, status)
            logger.warning(message)

        # Info: Monitor situation
        if categories.get('info', 0) > 0:
            message = (f"ℹ️  INFO: {categories['info']} tickers expiring within "
                      f"{self.INFO_THRESHOLD} days")
            self._notify('INFO', message, status)
            logger.info(message)

        # Expired: Data already expired
        if categories.get('expired', 0) > 0:
            message = f"❌ EXPIRED: {categories['expired']} tickers have expired cache"
            self._notify('EXPIRED', message, status)
            logger.error(message)

    def _notify(self, level: str, message: str, data: Dict):
        """Send notification via callback or log"""
        if self.notification_callback:
            try:
                self.notification_callback(level, message, data)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

        # Also log to file
        self._log_to_file(level, message, data)

    def _log_to_file(self, level: str, message: str, data: Dict):
        """Log notification to file"""
        try:
            log_dir = Path("backend/logs")
            log_dir.mkdir(exist_ok=True)

            log_file = log_dir / "redis_ttl_notifications.log"

            with open(log_file, 'a') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"\n{'='*80}\n")
                f.write(f"[{timestamp}] {level}: {message}\n")
                f.write(f"Total Tickers: {data.get('total_tickers', 0)}\n")
                f.write(f"Categories: {data.get('categories', {})}\n")
                f.write(f"{'='*80}\n")

        except Exception as e:
            logger.debug(f"Could not write to log file: {e}")

    def get_detailed_redis_stats(self) -> Dict:
        """
        Get detailed Redis storage statistics

        Returns:
            Dict with comprehensive Redis statistics
        """
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'keys': {},
                'memory': {},
                'data_types': {}
            }

            # Get all key patterns
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            metrics_keys = self.redis_client.keys("ticker_data:metrics:*")
            portfolio_keys = self.redis_client.keys("portfolio:*")
            strategy_keys = self.redis_client.keys("strategy_portfolio:*")
            master_keys = self.redis_client.keys("master_ticker_list*")

            # Count keys
            stats['keys'] = {
                'total': self.redis_client.dbsize(),
                'prices': len(price_keys),
                'sectors': len(sector_keys),
                'metrics': len(metrics_keys),
                'portfolios': len(portfolio_keys),
                'strategy_portfolios': len(strategy_keys),
                'master_lists': len(master_keys),
                'other': self.redis_client.dbsize() - (len(price_keys) + len(sector_keys) +
                                                       len(metrics_keys) + len(portfolio_keys) +
                                                       len(strategy_keys) + len(master_keys))
            }

            # Get memory info
            memory_info = self.redis_client.info('memory')
            stats['memory'] = {
                'used_memory_human': memory_info.get('used_memory_human', 'N/A'),
                'used_memory_peak_human': memory_info.get('used_memory_peak_human', 'N/A'),
                'used_memory_bytes': memory_info.get('used_memory', 0),
                'maxmemory_human': memory_info.get('maxmemory_human', 'unlimited'),
                'mem_fragmentation_ratio': memory_info.get('mem_fragmentation_ratio', 0)
            }

            # Calculate storage by type (sample-based estimation)
            def estimate_size(keys, sample_size=10):
                if not keys:
                    return 0
                sample = keys[:min(sample_size, len(keys))]
                total_size = 0
                for key in sample:
                    try:
                        total_size += self.redis_client.memory_usage(key) or 0
                    except:
                        pass
                avg_size = total_size / len(sample) if sample else 0
                return avg_size * len(keys)

            stats['data_types'] = {
                'prices_estimated_mb': estimate_size(price_keys) / (1024 * 1024),
                'sectors_estimated_mb': estimate_size(sector_keys) / (1024 * 1024),
                'metrics_estimated_mb': estimate_size(metrics_keys) / (1024 * 1024),
                'portfolios_estimated_mb': estimate_size(portfolio_keys) / (1024 * 1024),
                'strategy_portfolios_estimated_mb': estimate_size(strategy_keys) / (1024 * 1024)
            }

            # Get unique tickers
            tickers_with_prices = {self._extract_ticker(k, "ticker_data:prices:") for k in price_keys}
            tickers_with_sector = {self._extract_ticker(k, "ticker_data:sector:") for k in sector_keys}
            tickers_with_metrics = {self._extract_ticker(k, "ticker_data:metrics:") for k in metrics_keys}

            stats['tickers'] = {
                'total_unique': len(tickers_with_prices | tickers_with_sector | tickers_with_metrics),
                'with_prices': len(tickers_with_prices),
                'with_sectors': len(tickers_with_sector),
                'with_metrics': len(tickers_with_metrics),
                'complete_data': len(tickers_with_prices & tickers_with_sector),
                'missing_metrics': len((tickers_with_prices & tickers_with_sector) - tickers_with_metrics)
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting detailed Redis stats: {e}")
            return {'error': str(e)}

    def get_expiring_tickers(self, days_threshold: int = 7) -> List[str]:
        """
        Get list of tickers expiring within threshold

        Args:
            days_threshold: Number of days threshold

        Returns:
            List of ticker symbols
        """
        status = self.check_ttl_status()
        expiring = []

        for category in ['expired', 'critical', 'warning']:
            if category in status.get('details', {}):
                for ticker, info in status['details'][category]:
                    if info['days_left'] < days_threshold:
                        expiring.append(ticker)

        return expiring

    def generate_ttl_report(self) -> str:
        """
        Generate a human-readable TTL report

        Returns:
            Formatted report string
        """
        status = self.check_ttl_status()

        if 'error' in status:
            return f"Error generating report: {status['error']}"

        report = []
        report.append("=" * 80)
        report.append("REDIS TTL MONITORING REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {status['timestamp']}")
        report.append(f"Total Tickers Cached: {status['total_tickers']}")
        report.append("")

        categories = status['categories']
        report.append("TTL STATUS BREAKDOWN:")
        report.append(f"  ❌ Expired (already expired):     {categories['expired']:4d} tickers")
        report.append(f"  🚨 Critical (< {self.CRITICAL_THRESHOLD} day):          {categories['critical']:4d} tickers")
        report.append(f"  ⚠️  Warning (< {self.WARNING_THRESHOLD} days):         {categories['warning']:4d} tickers")
        report.append(f"  ℹ️  Info (< {self.INFO_THRESHOLD} days):            {categories['info']:4d} tickers")
        report.append(f"  ✅ Healthy (>= {self.INFO_THRESHOLD} days):        {categories['healthy']:4d} tickers")
        report.append("")

        if status['needs_action']:
            report.append("⚠️  ACTION REQUIRED:")
            if categories['expired'] > 0:
                report.append(f"   - {categories['expired']} tickers need immediate refresh (expired)")
            if categories['critical'] > 0:
                report.append(f"   - {categories['critical']} tickers need urgent refresh (< 1 day)")
        else:
            report.append("✅ No immediate action required")

        report.append("")

        # Show sample expired/critical tickers
        if categories['expired'] > 0 or categories['critical'] > 0:
            report.append("SAMPLE EXPIRING TICKERS:")
            details = status['details']

            if details['expired']:
                report.append("  Expired:")
                for ticker, info in details['expired'][:10]:
                    report.append(f"    - {ticker}: {info['expires_at']}")

            if details['critical']:
                report.append("  Critical:")
                for ticker, info in details['critical'][:10]:
                    report.append(f"    - {ticker}: {info['days_left']:.1f} days left")

        report.append("=" * 80)

        return "\n".join(report)

    def refresh_expiring_tickers(self, days_threshold: int = 7,
                                 data_service=None) -> Dict:
        """
        Automatically refresh tickers that are expiring soon

        Args:
            days_threshold: Refresh tickers expiring within this many days
            data_service: RedisFirstDataService instance for fetching data

        Returns:
            Dict with refresh results
        """
        if not data_service:
            return {'error': 'data_service required for refresh'}

        expiring_tickers = self.get_expiring_tickers(days_threshold)

        logger.info(f"🔄 Refreshing {len(expiring_tickers)} expiring tickers...")

        refreshed = 0
        failed = []

        for ticker in expiring_tickers:
            try:
                # Refresh price data
                data_service.get_monthly_data(ticker, force_refresh=True)
                # Refresh ticker info
                data_service.get_ticker_info(ticker, force_refresh=True)
                refreshed += 1
                logger.debug(f"✅ Refreshed {ticker}")
            except Exception as e:
                failed.append((ticker, str(e)))
                logger.warning(f"❌ Failed to refresh {ticker}: {e}")

        result = {
            'total_expiring': len(expiring_tickers),
            'refreshed': refreshed,
            'failed': len(failed),
            'failed_tickers': failed,
            'success_rate': f"{(refreshed/len(expiring_tickers)*100):.1f}%"
                           if expiring_tickers else "N/A"
        }

        logger.info(f"✅ Refresh complete: {refreshed}/{len(expiring_tickers)} successful")

        return result


# Email notification callback example
def email_notification_callback(level: str, message: str, data: Dict):
    """
    Example callback for email notifications

    To use:
        monitor = RedisTTLMonitor(redis_client, notification_callback=email_notification_callback)

    Requirements:
        pip install sendgrid  # or use smtplib
    """
    # Only send for critical/warning
    if level not in ['CRITICAL', 'WARNING', 'EXPIRED']:
        return

    try:
        # Example using environment variables
        email_enabled = os.getenv('TTL_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
        if not email_enabled:
            return

        # Email configuration from environment
        to_email = os.getenv('TTL_NOTIFICATION_EMAIL')

        if not to_email:
            logger.debug("TTL_NOTIFICATION_EMAIL not configured")
            return

        # Format email content
        subject = f"[{level}] Redis Cache Expiration Alert"
        body = f"""
        {message}

        Total Tickers: {data.get('total_tickers', 0)}

        Status Breakdown:
        - Expired: {data.get('categories', {}).get('expired', 0)}
        - Critical: {data.get('categories', {}).get('critical', 0)}
        - Warning: {data.get('categories', {}).get('warning', 0)}

        Timestamp: {data.get('timestamp', 'N/A')}

        Please refresh the cache using:
        POST /api/v1/portfolio/cache/warm
        """

        # Send email (implement your email service here)
        logger.info(f"Would send email to {to_email}: {subject}")
        # send_email(to_email, subject, body)  # Implement this

    except Exception as e:
        logger.error(f"Email notification failed: {e}")


# Slack webhook notification callback
def slack_notification_callback(level: str, message: str, data: Dict):
    """
    Slack webhook notification callback for TTL monitoring

    To use:
        monitor = RedisTTLMonitor(redis_client, notification_callback=slack_notification_callback)

    Environment variables required:
        TTL_SLACK_NOTIFICATIONS=true
        TTL_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
        TTL_SLACK_CHANNEL=#redis-alerts (optional)
    """
    try:
        # Only send for important levels
        if level not in ['CRITICAL', 'WARNING', 'EXPIRED']:
            return

        # Determine color based on level
        color_map = {
            'CRITICAL': '#FF0000',  # Red
            'EXPIRED': '#FF0000',   # Red
            'WARNING': '#FFA500',   # Orange
            'INFO': '#0000FF'       # Blue
        }
        color = color_map.get(level, '#808080')

        # Determine emoji based on level
        emoji_map = {
            'CRITICAL': ':rotating_light:',
            'EXPIRED': ':x:',
            'WARNING': ':warning:',
            'INFO': ':information_source:'
        }
        emoji = emoji_map.get(level, ':bell:')

        # Get categories
        categories = data.get('categories', {})
        total = data.get('total_tickers', 0)

        # Get detailed Redis stats (passed in data or fetch if needed)
        redis_stats = data.get('redis_stats')

        # Build Slack message with blocks for better formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Redis Cache TTL Alert - {level}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{message}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📊 TTL Status*"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Tickers:*\n{total}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{data.get('timestamp', 'N/A')[:19]}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expired:*\n{categories.get('expired', 0)} tickers"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Critical (<1 day):*\n{categories.get('critical', 0)} tickers"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Warning (<7 days):*\n{categories.get('warning', 0)} tickers"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Healthy:*\n{categories.get('healthy', 0)} tickers"
                    }
                ]
            }
        ]

        # Add detailed Redis storage statistics if available
        if redis_stats and 'error' not in redis_stats:
            keys = redis_stats.get('keys', {})
            memory = redis_stats.get('memory', {})
            tickers = redis_stats.get('tickers', {})
            data_types = redis_stats.get('data_types', {})

            # Storage Overview
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*💾 Redis Storage Overview*"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Keys:*\n{keys.get('total', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Memory Used:*\n{memory.get('used_memory_human', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Peak Memory:*\n{memory.get('used_memory_peak_human', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Memory Limit:*\n{memory.get('maxmemory_human', 'unlimited')}"
                    }
                ]
            })

            # Key Distribution
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔑 Key Distribution*"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Price Data:*\n{keys.get('prices', 0):,} keys"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sector Data:*\n{keys.get('sectors', 0):,} keys"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Metrics:*\n{keys.get('metrics', 0):,} keys"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Portfolios:*\n{keys.get('portfolios', 0):,} keys"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Strategy Portfolios:*\n{keys.get('strategy_portfolios', 0):,} keys"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Other:*\n{keys.get('other', 0):,} keys"
                    }
                ]
            })

            # Ticker Data Completeness
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📈 Ticker Data Completeness*"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Unique Tickers:*\n{tickers.get('total_unique', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*With Prices:*\n{tickers.get('with_prices', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*With Sectors:*\n{tickers.get('with_sectors', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*With Metrics:*\n{tickers.get('with_metrics', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Complete Data:*\n{tickers.get('complete_data', 0):,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Missing Metrics:*\n{tickers.get('missing_metrics', 0):,}"
                    }
                ]
            })

            # Storage Size Estimation
            total_estimated_mb = sum([
                data_types.get('prices_estimated_mb', 0),
                data_types.get('sectors_estimated_mb', 0),
                data_types.get('metrics_estimated_mb', 0),
                data_types.get('portfolios_estimated_mb', 0),
                data_types.get('strategy_portfolios_estimated_mb', 0)
            ])

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📦 Estimated Storage by Type* (Total: ~{total_estimated_mb:.2f} MB)"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Prices:*\n~{data_types.get('prices_estimated_mb', 0):.2f} MB"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sectors:*\n~{data_types.get('sectors_estimated_mb', 0):.2f} MB"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Metrics:*\n~{data_types.get('metrics_estimated_mb', 0):.2f} MB"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Portfolios:*\n~{data_types.get('portfolios_estimated_mb', 0):.2f} MB"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Strategy:*\n~{data_types.get('strategy_portfolios_estimated_mb', 0):.2f} MB"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Fragmentation:*\n{memory.get('mem_fragmentation_ratio', 0):.2f}"
                    }
                ]
            })

        # Add action buttons for critical/expired
        if level in ['CRITICAL', 'EXPIRED'] and categories.get(level.lower(), 0) > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Recommended Action:*\nRefresh expiring tickers immediately to maintain cache health."
                }
            })

        # Add divider
        blocks.append({"type": "divider"})

        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Portfolio Navigator Wizard | Redis TTL Monitoring System"
                }
            ]
        })

        # Optional: Override channel
        channel = os.getenv('TTL_SLACK_CHANNEL')

        # Build Slack payload
        # IMPORTANT: We send via a single-destination webhook. No per-message channel overrides.
        from utils.slack_notifier import SlackMessage, send_slack
        send_slack(
            SlackMessage(
                title=f"Redis Cache TTL Alert - {level}",
                message=f"*{message}*",
                severity=level,
                blocks=blocks,
            ),
            throttle_key=f"ttl_monitor:{level}",
            min_interval_seconds=60,  # prevent bursts when check runs frequently
        )
        logger.info(f"✅ Slack notification queued/sent: {level}")

    except Exception as e:
        logger.error(f"❌ Slack notification failed: {e}")


# Alias for backward compatibility
webhook_notification_callback = slack_notification_callback


if __name__ == "__main__":
    # Test the monitor
    import redis

    r = redis.Redis(host='localhost', port=6379, decode_responses=False)
    monitor = RedisTTLMonitor(r)

    print(monitor.generate_ttl_report())
