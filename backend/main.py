#!/usr/bin/env python3
"""
Portfolio Navigator Wizard - Enhanced Backend
FastAPI application with Enhanced Portfolio Generator System
"""

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import make_asgi_app
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Load backend/.env before any router imports (so ADMIN_API_KEY etc. are available)
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from shared.errors import error_response, is_production
from shared.structured_logging import set_request_id, configure_structured_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY

# Import security middleware
from middleware.rate_limiting import limiter as rate_limiter, rate_limit_exceeded_handler
from starlette.middleware.trustedhost import TrustedHostMiddleware
from middleware.security import SecurityHeadersMiddleware, HTTPSRedirectMiddleware
from middleware.validation import ValidationError

# Import existing routers
from routers import portfolio, strategy_buckets

# Import enhanced portfolio system (avoid hard import of generator at module load)
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
# Import will be done locally in lifespan function
from utils.port_analytics import PortfolioAnalytics

# Configure logging (structured JSON in production, plain in development)
logging.basicConfig(level=logging.INFO)
configure_structured_logging()
logger = logging.getLogger(__name__)

# Global variables for enhanced portfolio system
redis_first_data_service = None
enhanced_generator = None
redis_manager = None
strategy_optimizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Portfolio Navigator Wizard Backend...")
    
    try:
        # Centralized email notifier (single recipient via SMTP)
        from utils.email_notifier import NotificationMessage, send_notification as _send_notification

        def send_notification(title: str, message: str, severity: str = "INFO", fields: dict | None = None,
                              throttle_key: str | None = None, min_interval_seconds: int = 0):
            _send_notification(
                NotificationMessage(title=title, message=message, severity=severity, fields=fields),
                throttle_key=throttle_key,
                min_interval_seconds=min_interval_seconds,
            )

        # Initialize Redis-first data service (fast, no external API calls)
        global redis_first_data_service
        from utils.redis_first_data_service import RedisFirstDataService
        redis_first_data_service = RedisFirstDataService()

        # No waiting needed - Redis-first service is instant
        logger.info("✅ Redis-first data service initialized")

        # Initialize Redis metrics collector for Prometheus
        if redis_first_data_service.redis_client:
            from utils.redis_metrics import init_redis_metrics_collector
            redis_metrics = init_redis_metrics_collector(redis_first_data_service.redis_client)
            logger.info("✅ Redis metrics collector initialized")

        # Initialize backend metrics (Prometheus)
        from utils.anonymous_analytics import init_backend_metrics
        backend_metrics = init_backend_metrics(redis_client=redis_first_data_service.redis_client)
        app.state.backend_metrics = backend_metrics
        logger.info("✅ Backend metrics initialized (Prometheus)")

        # -----------------------------------------------------------------
        # Cold-start detection: container restart with empty Redis
        # -----------------------------------------------------------------
        is_cold_start = False
        if redis_first_data_service.redis_client:
            try:
                db_size = redis_first_data_service.redis_client.dbsize()
                price_key_count = len(redis_first_data_service.redis_client.keys("ticker_data:prices:*"))
                portfolio_key_count = len(redis_first_data_service.redis_client.keys("portfolio_bucket:*"))

                if db_size == 0 or (price_key_count == 0 and portfolio_key_count == 0):
                    is_cold_start = True
                    logger.warning("=" * 80)
                    logger.warning("🧊 COLD START DETECTED - Redis is empty")
                    logger.warning(f"   db_size={db_size}, price_keys={price_key_count}, portfolio_keys={portfolio_key_count}")
                    logger.warning("   This typically happens after a container restart without Redis persistence.")
                    logger.warning("   All caches will be regenerated automatically in the background.")
                    logger.warning("=" * 80)

                    send_notification(
                        title="Cold start detected - Redis empty",
                        severity="CRITICAL",
                        message=(
                            "Container restarted and Redis has no data. "
                            "Full cache warm-up is starting automatically. "
                            "Users may experience slower responses for the next 5-15 minutes "
                            "while portfolios and ticker data are regenerated."
                        ),
                        fields={
                            "db_size": str(db_size),
                            "price_keys": str(price_key_count),
                            "portfolio_keys": str(portfolio_key_count),
                        },
                        throttle_key="cold_start",
                        min_interval_seconds=60,
                    )
                else:
                    logger.info(f"✅ Warm start - Redis has {db_size} keys ({price_key_count} prices, {portfolio_key_count} portfolios)")
            except Exception as e:
                logger.warning(f"⚠️ Could not check Redis state for cold-start detection: {e}")

        # Check ticker status and show warnings (NO automatic fetching)
        logger.info("🔍 Checking ticker data status in Redis...")
        try:
            ticker_status = redis_first_data_service.check_ticker_status()
            if ticker_status:
                total_in_redis = ticker_status.get('total_tickers_in_redis', 0)
                total_in_master = ticker_status.get('total_tickers_in_master', 0)
                missing_from_master = ticker_status.get('missing_from_master_count', 0)
                expired = ticker_status.get('expired_count', 0)
                expiring_soon = ticker_status.get('expiring_soon_count', 0)
                missing_data = ticker_status.get('missing_data_count', 0)
                needs_fetch = ticker_status.get('needs_fetch_count', 0)
                
                if needs_fetch > 0:
                    logger.warning("="*80)
                    logger.warning("⚠️  TICKER DATA STATUS WARNING")
                    logger.warning("="*80)
                    logger.warning(f"   Master Ticker List:          {total_in_master} tickers")
                    logger.warning(f"   Tickers in Redis:            {total_in_redis} tickers")
                    logger.warning(f"   Tickers Needing Fetch:       {needs_fetch}")
                    logger.warning(f"     - Missing from Master:     {missing_from_master}")
                    logger.warning(f"     - Expired TTL:             {expired}")
                    logger.warning(f"     - Missing Data:            {missing_data}")
                    logger.warning(f"   Tickers Expiring Soon (<24h): {expiring_soon}")
                    logger.warning("="*80)
                    logger.warning("⚠️  NO AUTOMATIC FETCHING - Use manual refresh buttons if needed")
                    logger.warning("="*80)
                elif expiring_soon > 0:
                    logger.info(f"ℹ️  {expiring_soon} tickers expiring soon (< 24 hours)")
                else:
                    logger.info(f"✅ Ticker data status: {total_in_redis}/{total_in_master} tickers, all healthy")
        except Exception as e:
            logger.debug(f"Could not check ticker status: {e}")
        
        # Initialize portfolio analytics
        portfolio_analytics = PortfolioAnalytics()
        
        # Initialize enhanced portfolio generator with Redis-first service (best-effort)
        global enhanced_generator
        try:
            from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
            enhanced_generator = EnhancedPortfolioGenerator(redis_first_data_service, portfolio_analytics)
        except Exception as e:
            enhanced_generator = None
            logger.warning(f"⚠️ Skipping EnhancedPortfolioGenerator init due to error: {e}")
        
        # Initialize Redis portfolio manager with Redis connection
        global redis_manager
        redis_manager = RedisPortfolioManager(redis_first_data_service.redis_client)
        
        # Initialize strategy portfolio optimizer
        global strategy_optimizer
        strategy_optimizer = StrategyPortfolioOptimizer(redis_first_data_service, redis_manager)
        logger.info("✅ Strategy portfolio optimizer initialized")
        
        # Strategy Portfolio Management (Option 4: Hybrid Approach)
        # Check cache and generate/refresh as needed
        logger.info("🚀 Checking strategy portfolio cache...")
        try:
            cache_status = strategy_optimizer.get_cache_status_detailed()
            
            if cache_status.get('success'):
                strategy_optimizer.display_cache_status()
                
                if cache_status['needs_generation']:
                    # No cache - schedule initial generation in the background to avoid blocking startup
                    logger.warning("⚠️  No cached strategy portfolios - scheduling initial background generation")
                    logger.info("⏱️  Background setup will take ~3-4 minutes; API stays responsive")
                    async def background_initial_generation():
                        try:
                            logger.info("🚀 Background initial strategy pre-generation started...")
                            await asyncio.to_thread(strategy_optimizer.pre_generate_all_strategy_portfolios)
                            logger.info("✅ Background initial generation completed")
                            await asyncio.to_thread(strategy_optimizer.display_cache_status)
                        except Exception as e:
                            logger.error(f"❌ Background initial generation failed: {e}")
                    asyncio.create_task(background_initial_generation())
                    logger.info("✅ API will serve using on-demand generation and fallbacks until cache is ready")
                    
                elif cache_status['needs_refresh']:
                    # Cache expiring soon - schedule background refresh
                    logger.info("🔄 Cache TTL < 24 hours - scheduling background refresh")
                    async def background_refresh():
                        try:
                            logger.info("🔄 Background refresh started...")
                            await asyncio.to_thread(strategy_optimizer.pre_generate_all_strategy_portfolios)
                            logger.info("✅ Background refresh completed")
                        except Exception as e:
                            logger.error(f"❌ Background refresh failed: {e}")
                    
                    asyncio.create_task(background_refresh())
                    logger.info("✅ Strategy portfolios available (background refresh scheduled)")
                else:
                    # Good cache - no action needed
                    logger.info("✅ Strategy portfolios cached and fresh (no refresh needed)")
            else:
                logger.warning(f"⚠️  Could not check strategy cache: {cache_status.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Strategy portfolio cache check failed: {e}")
            logger.info("💡 Portfolios will be generated on-demand if needed")
        
        # Pre-compute eligible tickers cache in background (for full-dev mode)
        logger.info("🚀 Checking eligible tickers cache...")
        try:
            # Check if cache exists for default parameters
            default_cache_params = {
                'min_data_points': 30,
                'filter_negative_returns': True,
                'min_volatility': None,
                'max_volatility': 5.0,
                'min_return': None,
                'max_return': 10.0,
                'sectors': None
            }
            
            import json
            import hashlib
            cache_key_str = json.dumps(default_cache_params, sort_keys=True)
            cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
            cache_key = f"optimization:eligible_tickers:{cache_hash}"
            
            # Check if cache exists
            cache_exists = False
            if redis_first_data_service.redis_client:
                existing_cache = redis_first_data_service.redis_client.get(cache_key)
                if existing_cache:
                    cache_exists = True
                    logger.info("✅ Eligible tickers cache already exists")
            
            if not cache_exists or is_cold_start:
                # Schedule background pre-computation
                logger.warning("⚠️  No eligible tickers cache - scheduling background pre-computation")
                logger.info("⏱️  Background pre-computation will take ~3-4 minutes; API stays responsive")
                
                async def background_precompute_eligible_tickers():
                    try:
                        logger.info("🚀 Background eligible tickers pre-computation started...")
                        from routers.portfolio import _compute_eligible_tickers_internal
                        from utils.redis_first_data_service import redis_first_data_service as _rds
                        import time
                        
                        start_time = time.time()
                        
                        # Get all tickers
                        all_tickers = _rds.all_tickers or _rds.list_cached_tickers()
                        if not all_tickers:
                            logger.warning("⚠️  No tickers available for pre-computation")
                            return
                        
                        logger.info(f"📋 Processing {len(all_tickers)} tickers with optimized parallel processing (8 workers, 4 batches)...")
        
                        # Compute with optimized parallel processing (8 workers, 4 batches)
                        eligible_tickers, filtered_stats = await asyncio.to_thread(
                            _compute_eligible_tickers_internal,
                            all_tickers,
                            min_data_points=30,
                            filter_negative_returns=True,
                            min_volatility=None,
                            max_volatility=5.0,
                            min_return=None,
                            max_return=10.0,
                            sectors_list=None,
                            exclude_list=None,
                            sort_by='ticker',
                            max_workers=8,  # Optimized: 8 workers
                            batch_workers=4,  # Optimized: 4 batches
                            batch_size=100
                        )
                        
                        # Calculate statistics
                        total_eligible = len(eligible_tickers)
                        overlap_groups = {'full': 0, 'partial': 0}
                        data_quality_dist = {'Good': 0, 'Fair': 0, 'Limited': 0}
                        
                        for ticker_info in eligible_tickers:
                            overlap_groups[ticker_info.get('overlap_group', 'partial')] += 1
                            data_quality_dist[ticker_info.get('data_quality', 'Unknown')] += 1
                        
                        summary = {
                            "total_eligible": total_eligible,
                            "filtered_by_negative_returns": filtered_stats['negative_returns'],
                            "filtered_by_insufficient_data": filtered_stats['insufficient_data'],
                            "filtered_by_data_quality": filtered_stats['data_quality'],
                            "filtered_by_missing_metrics": filtered_stats['missing_metrics'],
                            "filtered_by_volatility": filtered_stats['volatility'],
                            "filtered_by_return": filtered_stats['return'],
                            "filtered_by_sector": filtered_stats['sector'],
                            "filtered_by_exclude": filtered_stats['exclude'],
                            "overlap_groups": overlap_groups,
                            "data_quality_distribution": data_quality_dist
                        }
                        
                        # Cache the result
                        result_to_cache = {
                            "eligible_tickers": eligible_tickers,
                            "summary": summary
                        }
                        
                        if _rds.redis_client:
                            _rds.redis_client.setex(
                                cache_key,
                                604800,  # 7 days TTL - background regeneration handles refresh before expiry
                                json.dumps(result_to_cache)
                            )
                        
                        elapsed = time.time() - start_time
                        logger.info("="*80)
                        logger.info("✅ ELIGIBLE TICKERS CACHE PRE-COMPUTATION COMPLETED!")
                        logger.info(f"   ⏱️  Processing Time: {elapsed:.2f}s")
                        logger.info(f"   📊 Total Eligible: {total_eligible} tickers")
                        logger.info(f"   🔗 Full Overlap: {overlap_groups['full']} tickers")
                        logger.info(f"   🔗 Partial Overlap: {overlap_groups['partial']} tickers")
                        logger.info(f"   ⚡ Performance: {len(all_tickers)/elapsed:.2f} tickers/sec")
                        logger.info("="*80)
                        logger.info("✅ Eligible tickers endpoint is now ready for instant responses!")

                        send_notification(
                            title="Eligible tickers cache ready",
                            severity="SUCCESS",
                            message=(
                                f"Pre-computation finished in {elapsed:.1f}s. "
                                f"{total_eligible} eligible tickers cached (7-day TTL)."
                            ),
                            fields={
                                "total_eligible": str(total_eligible),
                                "full_overlap": str(overlap_groups['full']),
                                "partial_overlap": str(overlap_groups['partial']),
                            },
                            throttle_key="eligible_tickers:ready",
                            min_interval_seconds=120,
                        )

                    except Exception as e:
                        logger.error(f"❌ Background eligible tickers pre-computation failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                asyncio.create_task(background_precompute_eligible_tickers())
                logger.info("✅ API will serve using on-demand computation until cache is ready")
            else:
                logger.info("✅ Eligible tickers cache exists and fresh")
                
        except Exception as e:
            logger.error(f"❌ Eligible tickers cache check failed: {e}")
            logger.info("💡 Eligible tickers will be computed on-demand if needed")
        
        # Check and generate missing portfolios on startup (lazy generation integration)
        logger.info("🚀 Checking portfolio recommendations cache...")
        try:
            risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
            total_portfolios = 0
            profiles_needing_generation = []
            
            for risk_profile in risk_profiles:
                portfolio_count = redis_manager.get_portfolio_count(risk_profile)
                total_portfolios += portfolio_count
                
                if portfolio_count < 12:  # Need at least 12 portfolios per profile
                    profiles_needing_generation.append(risk_profile)
                    logger.info(f"📊 {risk_profile}: {portfolio_count}/12 portfolios - needs generation")
                else:
                    logger.debug(f"✅ {risk_profile}: {portfolio_count}/12 portfolios - sufficient")
            
            logger.info(f"📊 Total portfolios in Redis: {total_portfolios}/60")
        
            # On cold start, force ALL profiles into generation queue
            if is_cold_start and not profiles_needing_generation:
                profiles_needing_generation = list(risk_profiles)
                logger.warning("🧊 Cold start: forcing regeneration of all risk profile portfolios")

            # Schedule background generation for missing portfolios (non-blocking)
            if profiles_needing_generation:
                logger.warning(f"⚠️ Missing portfolios detected for {len(profiles_needing_generation)} profiles")
                logger.info("⏱️  Background generation will take ~2-3 minutes; API stays responsive")
                
                async def background_generate_missing_portfolios():
                    """Background portfolio generation with comprehensive monitoring and statistics"""
                    import time
                    overall_start = time.time()
                    
                    # Overall statistics
                    overall_stats = {
                        'start_time': datetime.now().isoformat(),
                        'end_time': None,
                        'total_processing_time_seconds': 0.0,
                        'profiles_processed': 0,
                        'profiles_successful': 0,
                        'profiles_failed': 0,
                        'total_portfolios_generated': 0,
                        'total_portfolios_stored': 0,
                        'total_portfolios_failed': 0,
                        'profile_stats': {},
                        'errors': []
                    }
                    
                    try:
                        logger.info("="*80)
                        logger.info("🚀 BACKGROUND PORTFOLIO GENERATION STARTED")
                        logger.info("="*80)
                        logger.info(f"📊 Profiles to process: {len(profiles_needing_generation)}")
                        logger.info(f"   {', '.join(profiles_needing_generation)}")
                        logger.info("="*80)
                        
                        from routers.portfolio import _ensure_missing_portfolios_generated
                        
                        # Process each risk profile
                        for idx, risk_profile in enumerate(profiles_needing_generation, 1):
                            try:
                                logger.info("")
                                logger.info(f"[{idx}/{len(profiles_needing_generation)}] Processing {risk_profile}...")
                                
                                # Call lazy generation (now returns statistics)
                                profile_stats = await asyncio.to_thread(_ensure_missing_portfolios_generated, risk_profile)
                                
                                # Update overall statistics
                                overall_stats['profiles_processed'] += 1
                                overall_stats['profile_stats'][risk_profile] = profile_stats
                                
                                if profile_stats.get('success', False):
                                    overall_stats['profiles_successful'] += 1
                                else:
                                    overall_stats['profiles_failed'] += 1
                                    if profile_stats.get('errors'):
                                        overall_stats['errors'].extend(profile_stats['errors'])
                                
                                overall_stats['total_portfolios_generated'] += profile_stats.get('portfolios_generated', 0)
                                overall_stats['total_portfolios_stored'] += profile_stats.get('portfolios_stored', 0)
                                overall_stats['total_portfolios_failed'] += profile_stats.get('portfolios_failed', 0)
                                
                                # Log profile summary
                                if profile_stats.get('success'):
                                    logger.info(f"✅ [{risk_profile}] Completed successfully")
                                    logger.info(f"   📊 Generated: {profile_stats.get('portfolios_generated', 0)}")
                                    logger.info(f"   💾 Stored: {profile_stats.get('portfolios_stored', 0)}")
                                    logger.info(f"   ⏱️  Time: {profile_stats.get('processing_time_seconds', 0):.2f}s")
                                else:
                                    logger.warning(f"⚠️ [{risk_profile}] Completed with errors")
                                    logger.warning(f"   📊 Generated: {profile_stats.get('portfolios_generated', 0)}")
                                    logger.warning(f"   💾 Stored: {profile_stats.get('portfolios_stored', 0)}")
                                    logger.warning(f"   ❌ Failed: {profile_stats.get('portfolios_failed', 0)}")
                                    logger.warning(f"   ⏱️  Time: {profile_stats.get('processing_time_seconds', 0):.2f}s")
                                
                            except Exception as e:
                                overall_stats['profiles_failed'] += 1
                                error_msg = f"Error processing {risk_profile}: {e}"
                                overall_stats['errors'].append(error_msg)
                                logger.error(f"❌ [{risk_profile}] {error_msg}")
                                import traceback
                                traceback.print_exc()
                                continue
                        
                        # Calculate final statistics
                        overall_elapsed = time.time() - overall_start
                        overall_stats['end_time'] = datetime.now().isoformat()
                        overall_stats['total_processing_time_seconds'] = round(overall_elapsed, 3)
            
                        # Final summary
                        logger.info("")
                        logger.info("="*80)
                        logger.info("✅ BACKGROUND PORTFOLIO GENERATION COMPLETED!")
                        logger.info("="*80)
                        logger.info(f"📊 OVERALL STATISTICS:")
                        logger.info(f"   ⏱️  Total Processing Time: {overall_elapsed:.2f}s ({overall_elapsed/60:.2f} minutes)")
                        logger.info(f"   📋 Profiles Processed: {overall_stats['profiles_processed']}/{len(profiles_needing_generation)}")
                        logger.info(f"   ✅ Profiles Successful: {overall_stats['profiles_successful']}")
                        logger.info(f"   ❌ Profiles Failed: {overall_stats['profiles_failed']}")
                        logger.info(f"   📊 Total Portfolios Generated: {overall_stats['total_portfolios_generated']}")
                        logger.info(f"   💾 Total Portfolios Stored: {overall_stats['total_portfolios_stored']}")
                        logger.info(f"   ❌ Total Portfolios Failed: {overall_stats['total_portfolios_failed']}")
                        
                        if overall_stats['profiles_processed'] > 0:
                            avg_time_per_profile = overall_elapsed / overall_stats['profiles_processed']
                            logger.info(f"   ⏱️  Average Time per Profile: {avg_time_per_profile:.2f}s")
                        
                        if overall_stats['total_portfolios_generated'] > 0:
                            avg_time_per_portfolio = overall_elapsed / overall_stats['total_portfolios_generated']
                            logger.info(f"   ⏱️  Average Time per Portfolio: {avg_time_per_portfolio:.2f}s")
                        
                        if overall_stats['errors']:
                            logger.warning(f"   ⚠️  Total Errors: {len(overall_stats['errors'])}")
                            for error in overall_stats['errors'][:5]:  # Show first 5 errors
                                logger.warning(f"      - {error}")
                            if len(overall_stats['errors']) > 5:
                                logger.warning(f"      ... and {len(overall_stats['errors']) - 5} more errors")
                        
                        logger.info("="*80)
                        logger.info("✅ Portfolio recommendations are now ready!")
                        logger.info("="*80)

                        # Email notification on completion (especially useful after cold start)
                        send_notification(
                            title="Portfolio generation completed",
                            severity="SUCCESS",
                            message=(
                                f"Background generation finished in {overall_elapsed:.1f}s. "
                                f"Generated {overall_stats['total_portfolios_generated']} portfolios "
                                f"for {overall_stats['profiles_successful']}/{overall_stats['profiles_processed']} profiles."
                            ),
                            fields={
                                "profiles_processed": str(overall_stats['profiles_processed']),
                                "portfolios_stored": str(overall_stats['total_portfolios_stored']),
                                "errors": str(len(overall_stats['errors'])),
                                "duration_seconds": f"{overall_elapsed:.1f}",
                            },
                            throttle_key="portfolio_gen:complete",
                            min_interval_seconds=120,
                        )

                    except Exception as e:
                        overall_stats['end_time'] = datetime.now().isoformat()
                        overall_stats['total_processing_time_seconds'] = round(time.time() - overall_start, 3)
                        error_msg = f"Background portfolio generation failed: {e}"
                        overall_stats['errors'].append(error_msg)
                        logger.error(f"❌ {error_msg}")
                        import traceback
                        traceback.print_exc()
                
                asyncio.create_task(background_generate_missing_portfolios())
                logger.info("✅ API will serve using lazy generation until portfolios are ready")
            else:
                logger.info("✅ All portfolios available - no generation needed")
            
            # Verify Redis health
            try:
                redis_status = redis_manager.redis_client.ping() if redis_manager.redis_client else False
                if redis_status:
                    logger.info("✅ Redis health check: connected and responsive")
                else:
                    logger.warning("⚠️ Redis health check: not responsive")
            except Exception as e:
                logger.warning(f"⚠️ Redis health check failed: {e}")
        
        except Exception as e:
            logger.error(f"❌ Portfolio cache check failed: {e}")
            logger.info("💡 Portfolios will be generated on-demand via lazy generation")
        
        logger.info("✅ Enhanced portfolio system initialized successfully")
        
        # Set Redis manager in portfolio router
        from routers.portfolio import set_redis_manager
        set_redis_manager(redis_manager)
        logger.info("✅ Redis manager set in portfolio router")
        
        # Search functionality ready (no index warming needed for basic search)
        logger.info("✅ Search functionality ready for all cached tickers")

        # Start TTL monitoring background task
        async def ttl_monitoring_task():
            """Background task to monitor TTL and send email notifications"""
            from utils.redis_ttl_monitor import RedisTTLMonitor, email_notification_callback

            # Wait 5 minutes after startup before first check
            await asyncio.sleep(300)

            if not redis_first_data_service or not redis_first_data_service.redis_client:
                logger.warning("⚠️ Redis not available, TTL monitoring disabled")
                return

            monitor = RedisTTLMonitor(
                redis_first_data_service.redis_client,
                notification_callback=email_notification_callback
            )

            logger.info("🔍 TTL monitoring background task started")

            while True:
                try:
                    logger.info("🔍 Running TTL monitoring check...")

                    # Check TTL status (this will trigger notifications if needed)
                    status = monitor.check_ttl_status()

                    # Log status
                    categories = status.get('categories', {})
                    logger.info(
                        f"TTL Status - "
                        f"Total: {status.get('total_tickers', 0)}, "
                        f"Expired: {categories.get('expired', 0)}, "
                        f"Critical: {categories.get('critical', 0)}, "
                        f"Warning: {categories.get('warning', 0)}, "
                        f"Healthy: {categories.get('healthy', 0)}"
                    )

                    # Auto-refresh if critical or expired
                    if categories.get('critical', 0) > 0 or categories.get('expired', 0) > 0:
                        pre_notice_seconds = int(os.getenv("CACHE_REGEN_PRENOTICE_SECONDS", "7200"))

                        # If anything is already expired, refresh immediately (cannot pre-notify 2 hours ahead).
                        if categories.get("expired", 0) > 0:
                            send_notification(
                                title="Ticker cache auto-refresh starting (expired)",
                                severity="CRITICAL",
                                message=(
                                    "Expired ticker cache detected. Starting auto-refresh immediately "
                                    "(2-hour pre-notice not possible when already expired)."
                                ),
                                fields={
                                    "expired": str(categories.get("expired", 0)),
                                    "critical": str(categories.get("critical", 0)),
                                    "warning": str(categories.get("warning", 0)),
                                    "healthy": str(categories.get("healthy", 0)),
                                },
                                throttle_key="ticker_refresh:expired_start",
                                min_interval_seconds=600,
                            )
                        else:
                            # Only critical (not expired): schedule with 2-hour pre-notice
                            send_notification(
                                title="Ticker cache auto-refresh scheduled",
                                severity="WARNING",
                                message=(
                                    f"Critical ticker cache detected. Auto-refresh will run in ~{pre_notice_seconds//3600}h "
                                    f"to keep users from hitting cache gaps."
                                ),
                                fields={
                                    "expired": str(categories.get("expired", 0)),
                                    "critical": str(categories.get("critical", 0)),
                                    "warning": str(categories.get("warning", 0)),
                                    "healthy": str(categories.get("healthy", 0)),
                                },
                                throttle_key="ticker_refresh:scheduled",
                                min_interval_seconds=600,
                            )
                            await asyncio.sleep(pre_notice_seconds)

                        logger.warning("🔄 Auto-refreshing critical/expired tickers...")
                        try:
                            result = monitor.refresh_expiring_tickers(
                                days_threshold=1,  # Refresh tickers expiring within 1 day
                                data_service=redis_first_data_service
                            )
                            logger.info(
                                f"✅ Auto-refresh complete: {result['refreshed']}/{result['total_expiring']} tickers"
                            )
                            send_notification(
                                title="Ticker cache auto-refresh completed",
                                severity="SUCCESS",
                                message=f"Refreshed {result['refreshed']}/{result['total_expiring']} tickers.",
                                throttle_key="ticker_refresh:completed",
                                min_interval_seconds=300,
                            )
                        except Exception as e:
                            logger.error(f"❌ Auto-refresh failed: {e}")
                            send_notification(
                                title="Ticker cache auto-refresh failed",
                                severity="CRITICAL",
                                message=f"Auto-refresh failed: {e}",
                                throttle_key="ticker_refresh:failed",
                                min_interval_seconds=300,
                            )

                    # Wait 6 hours before next check (enables 2h pre-notice scheduling)
                    logger.info("⏰ Next TTL check in 6 hours")
                    await asyncio.sleep(21600)  # 6 hours

                except Exception as e:
                    logger.error(f"❌ TTL monitoring error: {e}")
                    # Wait 1 hour before retry on error
                    await asyncio.sleep(3600)

        # Start TTL monitoring task
        logger.info("🔍 Starting TTL monitoring background task...")
        asyncio.create_task(ttl_monitoring_task())

        # ---------------------------------------------------------------------
        # Proactive cache regeneration supervisor (app-level caches)
        # - Schedules regeneration 2 hours in advance (email pre-notify)
        # - Regenerates in background while old cache is still valid
        # ---------------------------------------------------------------------
        async def cache_regeneration_supervisor():
            """
            Proactively refresh critical app caches so users never wait:
              - portfolio_bucket:* (recommendations)
              - strategy_portfolios:* (strategy comparisons)
              - optimization:eligible_tickers:* (default eligible-tickers cache)

            Behavior:
              - If missing/expired: regenerate immediately (background) + email alert
              - If expiring within SCHEDULE_THRESHOLD: notify now, regenerate after PRENOTICE_SECONDS
              - Deduplicates schedules to avoid repeated regenerations
            """
            # Delay start slightly to avoid competing with initial startup warmups
            await asyncio.sleep(600)

            prenotice_seconds = int(os.getenv("CACHE_REGEN_PRENOTICE_SECONDS", "7200"))  # default 2h
            schedule_threshold_seconds = int(os.getenv("CACHE_REGEN_SCHEDULE_THRESHOLD_SECONDS", "28800"))  # default 8h
            loop_seconds = int(os.getenv("CACHE_REGEN_LOOP_SECONDS", "1800"))  # default 30m

            scheduled: dict[str, float] = {}  # job_name -> unix timestamp when job will run

            def _now_ts() -> float:
                return time.time()

            def _fmt_seconds(s: int | None) -> str:
                if s is None:
                    return "unknown"
                if s <= 0:
                    return "expired/missing"
                h = s // 3600
                m = (s % 3600) // 60
                return f"{h}h {m}m"

            async def _schedule(job_name: str, run_coro_factory, ttl_seconds: int | None):
                now = _now_ts()
                already = scheduled.get(job_name)
                if already and already > now:
                    return

                run_at = now + prenotice_seconds
                scheduled[job_name] = run_at

                send_notification(
                    title="Cache regeneration scheduled",
                    severity="WARNING",
                    message=f"{job_name} will regenerate in ~{prenotice_seconds//3600} hours (proactive refresh).",
                    fields={"current_ttl": _fmt_seconds(ttl_seconds), "run_at": datetime.fromtimestamp(run_at).isoformat(timespec="seconds")},
                )

                async def _runner():
                    try:
                        await asyncio.sleep(max(0, run_at - _now_ts()))
                        send_notification(
                            title="Cache regeneration starting",
                            severity="INFO",
                            message=f"Starting regeneration for {job_name}.",
                        )
                        await run_coro_factory()
                        send_notification(
                            title="Cache regeneration completed",
                            severity="SUCCESS",
                            message=f"Regeneration completed for {job_name}.",
                        )
                    except Exception as e:
                        send_notification(
                            title="Cache regeneration failed",
                            severity="CRITICAL",
                            message=f"{job_name} regeneration failed: {e}",
                        )
                    finally:
                        # Clear schedule once attempted
                        scheduled.pop(job_name, None)

                asyncio.create_task(_runner())

            logger.info("🧠 Cache regeneration supervisor started")

            while True:
                try:
                    if not redis_first_data_service or not redis_first_data_service.redis_client:
                        await asyncio.sleep(loop_seconds)
                        continue

                    r = redis_first_data_service.redis_client

                    # 1) Portfolio buckets (recommendations)
                    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
                    for rp in risk_profiles:
                        ttl_info = redis_manager.get_portfolio_ttl_info(rp) if redis_manager else None
                        ttl_s = int(ttl_info.get("ttl_seconds")) if ttl_info and ttl_info.get("ttl_seconds") else None
                        job_name = f"portfolio recommendations ({rp})"

                        async def _regen_portfolios_for(risk_profile=rp):
                            from routers.portfolio import _ensure_missing_portfolios_generated
                            await asyncio.to_thread(_ensure_missing_portfolios_generated, risk_profile)

                        if ttl_s is None or ttl_s <= 0:
                            send_notification(
                                title="Portfolio cache missing/expired",
                                severity="WARNING",
                                message=f"{job_name} missing/expired. Regenerating immediately in background.",
                                fields={"current_ttl": _fmt_seconds(ttl_s)},
                            )
                            asyncio.create_task(_regen_portfolios_for())
                        elif ttl_s <= prenotice_seconds:
                            # Too close to expiry to wait 2h; refresh now
                            send_notification(
                                title="Portfolio cache expiring soon",
                                severity="WARNING",
                                message=f"{job_name} expires in {_fmt_seconds(ttl_s)}. Regenerating immediately (cannot wait 2h).",
                                fields={"current_ttl": _fmt_seconds(ttl_s)},
                            )
                            asyncio.create_task(_regen_portfolios_for())
                        elif ttl_s <= schedule_threshold_seconds:
                            await _schedule(job_name, lambda: _regen_portfolios_for(), ttl_s)

                    # 2) Strategy portfolios (pure + personalized)
                    if strategy_optimizer:
                        status = await asyncio.to_thread(strategy_optimizer.get_cache_status_detailed)
                        min_ttl_hours = status.get("min_ttl_hours", 0) if isinstance(status, dict) else 0
                        min_ttl_s = int(float(min_ttl_hours) * 3600) if min_ttl_hours else 0
                        job_name = "strategy portfolios (all)"

                        async def _regen_strategies():
                            await asyncio.to_thread(strategy_optimizer.pre_generate_all_strategy_portfolios)

                        needs_generation = bool(status.get("needs_generation")) if isinstance(status, dict) else False

                        if needs_generation or min_ttl_s <= 0:
                            send_notification(
                                title="Strategy cache missing/expired",
                                severity="WARNING",
                                message=f"{job_name} missing/expired. Regenerating immediately in background.",
                                fields={"current_ttl": _fmt_seconds(min_ttl_s)},
                            )
                            asyncio.create_task(_regen_strategies())
                        elif min_ttl_s <= prenotice_seconds:
                            send_notification(
                                title="Strategy cache expiring soon",
                                severity="WARNING",
                                message=f"{job_name} expires in {_fmt_seconds(min_ttl_s)}. Regenerating immediately (cannot wait 2h).",
                                fields={"current_ttl": _fmt_seconds(min_ttl_s)},
                            )
                            asyncio.create_task(_regen_strategies())
                        elif min_ttl_s <= schedule_threshold_seconds:
                            await _schedule(job_name, lambda: _regen_strategies(), min_ttl_s)

                    # 3) Default eligible tickers cache (optimization:eligible_tickers:{hash})
                    try:
                        default_cache_params = {
                            'min_data_points': 30,
                            'filter_negative_returns': True,
                            'min_volatility': None,
                            'max_volatility': 5.0,
                            'min_return': None,
                            'max_return': 10.0,
                            'sectors': None
                        }
                        import json
                        import hashlib
                        cache_key_str = json.dumps(default_cache_params, sort_keys=True)
                        cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
                        cache_key = f"optimization:eligible_tickers:{cache_hash}"

                        ttl_s = r.ttl(cache_key) if r.exists(cache_key) else 0
                        job_name = "eligible tickers cache (default)"

                        async def _regen_eligible():
                            from routers.portfolio import _compute_eligible_tickers_internal
                            from utils.redis_first_data_service import redis_first_data_service as _rds
                            start_time = time.time()
                            all_tickers = _rds.all_tickers or _rds.list_cached_tickers()
                            if not all_tickers:
                                raise RuntimeError("No tickers available for eligible-tickers regeneration")
                            eligible_tickers, filtered_stats = await asyncio.to_thread(
                                _compute_eligible_tickers_internal,
                                all_tickers,
                                min_data_points=30,
                                filter_negative_returns=True,
                                min_volatility=None,
                                max_volatility=5.0,
                                min_return=None,
                                max_return=10.0,
                                sectors_list=None
                            )
                            # Store full result (same key, 7d TTL)
                            result_to_cache = {
                                "eligible_tickers": eligible_tickers,
                                "summary": filtered_stats
                            }
                            _rds.redis_client.setex(cache_key, 604800, json.dumps(result_to_cache))
                            logger.info(f"✅ Eligible tickers cache regenerated in {time.time()-start_time:.1f}s")

                        if ttl_s <= 0:
                            send_notification(
                                title="Eligible tickers cache missing/expired",
                                severity="WARNING",
                                message=f"{job_name} missing/expired. Regenerating immediately in background.",
                                fields={"current_ttl": _fmt_seconds(ttl_s)},
                            )
                            asyncio.create_task(_regen_eligible())
                        elif ttl_s <= prenotice_seconds:
                            send_notification(
                                title="Eligible tickers cache expiring soon",
                                severity="WARNING",
                                message=f"{job_name} expires in {_fmt_seconds(ttl_s)}. Regenerating immediately (cannot wait 2h).",
                                fields={"current_ttl": _fmt_seconds(ttl_s)},
                            )
                            asyncio.create_task(_regen_eligible())
                        elif ttl_s <= schedule_threshold_seconds:
                            await _schedule(job_name, lambda: _regen_eligible(), int(ttl_s))
                    except Exception as e:
                        logger.debug(f"Eligible tickers supervisor check failed: {e}")

                except Exception as e:
                    logger.error(f"❌ Cache regeneration supervisor error: {e}")

                await asyncio.sleep(loop_seconds)

        logger.info("🧠 Starting cache regeneration supervisor...")
        asyncio.create_task(cache_regeneration_supervisor())

        # ---------------------------------------------------------------------
        # Redis connectivity watchdog (email notification, single recipient)
        # ---------------------------------------------------------------------
        async def redis_health_watchdog():
            await asyncio.sleep(120)
            if not redis_first_data_service or not redis_first_data_service.redis_client:
                send_notification(
                    title="Redis not connected at startup",
                    severity="CRITICAL",
                    message="Redis client is not available. Cache regeneration and TTL monitoring may not function.",
                    throttle_key="redis_watchdog:startup_missing",
                    min_interval_seconds=1800,
                )
                return

            r = redis_first_data_service.redis_client
            was_up = True
            consecutive_failures = 0

            while True:
                try:
                    ok = bool(r.ping())
                except Exception:
                    ok = False

                if ok:
                    consecutive_failures = 0
                    if not was_up:
                        was_up = True
                        send_notification(
                            title="Redis connectivity restored",
                            severity="SUCCESS",
                            message="Redis ping succeeded again. Cache operations should be healthy.",
                            throttle_key="redis_watchdog:restored",
                            min_interval_seconds=300,
                        )
                else:
                    consecutive_failures += 1
                    # only alert if it's not a transient blip
                    if was_up and consecutive_failures >= 3:
                        was_up = False
                        send_notification(
                            title="Redis connectivity lost",
                            severity="CRITICAL",
                            message="Redis ping has failed 3 consecutive checks. Users may see degraded performance or cache misses.",
                            throttle_key="redis_watchdog:lost",
                            min_interval_seconds=600,
                        )

                await asyncio.sleep(60)

        logger.info("🩺 Starting Redis health watchdog...")
        asyncio.create_task(redis_health_watchdog())

        # ---------------------------------------------------------------------
        # Redis metrics updater for Prometheus
        # ---------------------------------------------------------------------
        async def redis_metrics_updater():
            """Update Redis metrics for Prometheus every 30 seconds"""
            await asyncio.sleep(30)  # Wait for initialization

            from utils.redis_metrics import update_redis_metrics

            while True:
                try:
                    update_redis_metrics()
                except Exception as e:
                    logger.error(f"❌ Redis metrics update error: {e}")

                await asyncio.sleep(30)  # Update every 30 seconds

        logger.info("📊 Starting Redis metrics updater...")
        asyncio.create_task(redis_metrics_updater())

        # Yield control back to FastAPI
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize enhanced portfolio system: {e}")
        yield
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Portfolio Navigator Wizard Backend...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Portfolio Navigator Wizard - Enhanced Backend",
    description="Enhanced portfolio generation system with automatic regeneration",
    version="2.0.0",
    lifespan=lifespan
)

# Add rate limiter to app (using imported rate_limiter from middleware)
app.state.limiter = rate_limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add validation error handler
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors with proper error response"""
    return JSONResponse(
        status_code=400,
        content=error_response(
            code="VALIDATION_ERROR",
            message=str(exc),
            request_id=getattr(request.state, "request_id", "unknown")
        )
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Set a unique request_id on each request for tracing and structured logging."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


class Email5xxMiddleware(BaseHTTPMiddleware):
    """
    Email notification for 5xx responses (rate limited).
    Uses the same SMTP/recipient configured for TTL notifications.
    """

    async def dispatch(self, request: Request, call_next):
        from utils.email_notifier import NotificationMessage, send_notification

        path = request.url.path
        # Avoid spamming for health/metrics endpoints
        if path in ("/healthz", "/health", "/metrics"):
            return await call_next(request)

        try:
            response = await call_next(request)
            if response.status_code >= 500:
                rid = getattr(request.state, "request_id", "unknown")
                send_notification(
                    NotificationMessage(
                        title="HTTP 5xx detected",
                        severity="CRITICAL",
                        message=f"Request returned {response.status_code}.",
                        fields={
                            "method": request.method,
                            "path": path,
                            "request_id": rid,
                        },
                    ),
                    throttle_key=f"http5xx:{request.method}:{path}:{response.status_code}",
                    min_interval_seconds=300,
                )
            return response
        except Exception as e:
            rid = getattr(request.state, "request_id", "unknown")
            send_notification(
                NotificationMessage(
                    title="Unhandled exception in request",
                    severity="CRITICAL",
                    message=f"Unhandled exception while processing request: {e}",
                    fields={
                        "method": request.method,
                        "path": path,
                        "request_id": rid,
                    },
                ),
                throttle_key=f"httpex:{request.method}:{path}:{type(e).__name__}",
                min_interval_seconds=300,
            )
            raise


app.add_middleware(RequestIDMiddleware)
app.add_middleware(Email5xxMiddleware)

# Add security middleware
# Note: HTTPS redirect disabled in development, enabled via environment variable
enable_https_redirect = os.getenv("ENABLE_HTTPS_REDIRECT", "false").lower() == "true"
if enable_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)
    logger.info("🔒 HTTPS redirect middleware enabled")

# Security headers middleware (always enabled; X-Frame-Options is always set in the middleware)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=enable_https_redirect,  # Only enable HSTS if HTTPS is enforced
    enable_csp=True,
)
logger.info("🔒 Security headers middleware enabled")

# TrustedHostMiddleware in production (fly.io, Railway, etc.)
# Custom wrapper to bypass host validation for health check paths (Fly.io probes may use internal IPs)
class HealthCheckAwareTrustedHostMiddleware(TrustedHostMiddleware):
    """TrustedHostMiddleware that bypasses validation for /health and /healthz paths."""
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path in ("/health", "/healthz", "/metrics"):
                # Bypass host validation for health/metrics endpoints
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)

if is_production():
    _allowed_hosts_env = os.getenv(
        "ALLOWED_HOSTS",
        "portfolio-navigator-wizard.fly.dev,localhost,127.0.0.1",
    )
    _allowed_hosts = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
    app.add_middleware(HealthCheckAwareTrustedHostMiddleware, allowed_hosts=_allowed_hosts)
    logger.info("🔒 TrustedHostMiddleware enabled (health paths bypassed): %s", _allowed_hosts)


# Paths to exclude from request metrics and logging (health checks, metrics endpoint)
_HEALTH_AND_METRICS_PATHS = frozenset({"/healthz", "/health", "/metrics"})


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record request count and latency for Prometheus. Skip health and metrics paths."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        path = request.scope.get("path", "").split("?")[0] or "unknown"
        method = request.method
        response = await call_next(request)
        duration = time.perf_counter() - start
        status = response.status_code
        if path not in _HEALTH_AND_METRICS_PATHS:
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        return response


app.add_middleware(PrometheusMiddleware)

# Mount Prometheus metrics endpoint (optional METRICS_SECRET restricts access in production)
metrics_app = make_asgi_app()

class _MetricsGuardMiddleware(BaseHTTPMiddleware):
    """Require X-Metrics-Secret header when METRICS_SECRET env is set."""
    async def dispatch(self, request: Request, call_next):
        import hmac
        path = request.scope.get("path", "").split("?")[0] or ""
        secret = os.getenv("METRICS_SECRET")
        if path == "/metrics" and secret:
            provided = request.headers.get("X-Metrics-Secret", "").strip()
            # Use constant-time comparison to prevent timing attacks
            if not provided or not hmac.compare_digest(provided, secret):
                return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        return await call_next(request)

app.add_middleware(_MetricsGuardMiddleware)
app.mount("/metrics", metrics_app)

# Add CORS middleware with environment-based configuration
# Get allowed origins from environment variable
# Default includes localhost for development
ALLOWED_ORIGINS_ENV = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://localhost:5173,http://localhost:3000,http://127.0.0.1:8080,http://127.0.0.1:5173,http://127.0.0.1:3000"
)

# Clean up origins (remove whitespace)
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]

logger.info(f"🔒 CORS configured for origins: {ALLOWED_ORIGINS}")

# Restrict methods and headers in production for security
ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Request-ID", "Accept"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include existing routers
# Mount the portfolio router under both the versioned prefix and the legacy prefix
# so existing clients that call /api/portfolio/... keep working while new clients
# use /api/v1/portfolio/ for versioning.
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio", "legacy"])
app.include_router(strategy_buckets.router, prefix="/api/v1/strategy-buckets", tags=["strategy-buckets"])

# Health check endpoints (/health and /healthz for load balancers and Kubernetes)
# Lightweight: ping-only for fast load balancer checks (no portfolio enumeration)
@app.get("/healthz")
async def healthz():
    """Lightweight health check for load balancers (Redis ping only)."""
    try:
        if redis_first_data_service and redis_first_data_service._async_client:
            ok = await redis_first_data_service.ping_async()
            if ok:
                return {"status": "healthy"}
            return {"status": "unhealthy", "reason": "redis_ping_failed"}
        return {"status": "degraded", "reason": "redis_unavailable"}
    except Exception as e:
        if is_production():
            return {"status": "unhealthy"}
        return {"status": "unhealthy", "error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint (same lightweight check as /healthz)."""
    return await healthz()


async def _health_response():
    """Detailed health with portfolio bucket status (for diagnostics only)."""
    try:
        if redis_manager:
            portfolio_status = redis_manager.get_all_portfolio_buckets_status()
            available_buckets = sum(1 for status in portfolio_status.values() if status.get("available"))
            return {
                "status": "healthy",
                "enhanced_portfolio_system": True,
                "available_portfolio_buckets": available_buckets,
                "total_risk_profiles": 5,
                "lazy_generation": True,
            }
        return {
            "status": "degraded",
            "enhanced_portfolio_system": False,
            "message": "Enhanced portfolio system not initialized",
        }
    except Exception as e:
        logger.error("Health check failed: %s", e)
        if is_production():
            return {"status": "unhealthy"}
        return {"status": "unhealthy", "error": str(e)}


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with portfolio status (for diagnostics)."""
    return await _health_response()

# Portfolio bucket status endpoint
@app.get("/api/v1/enhanced-portfolio/buckets")
async def get_portfolio_buckets_status():
    """Get status of all portfolio buckets"""
    try:
        if not redis_manager:
            raise HTTPException(status_code=503, detail="Redis portfolio manager not available")
        
        status = redis_manager.get_all_portfolio_buckets_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get portfolio buckets status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Standardized error handlers
def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or ""


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return HTTPException as standard error response schema. Hide 5xx detail in production."""
    request_id = _request_id(request)
    if exc.status_code >= 500 and is_production():
        logger.error("HTTP 5xx (detail hidden in production): %s", exc.detail)
        message = "An error occurred. Please try again later."
        details = None
    elif isinstance(exc.detail, str):
        message = exc.detail
        details = None
    elif isinstance(exc.detail, list):
        message = "Validation error"
        details = {"errors": exc.detail}
    else:
        message = "Request failed"
        details = {"detail": exc.detail}
    body = error_response(
        code=f"HTTP_{exc.status_code}",
        message=message,
        details=details,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler; do not expose internal errors in production."""
    request_id = _request_id(request)
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    message = "Internal server error"
    details = None
    if not is_production():
        details = {"error": str(exc)}
    body = error_response(
        code="INTERNAL_ERROR",
        message=message,
        details=details,
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=body)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 