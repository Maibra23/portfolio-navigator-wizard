#!/usr/bin/env python3
"""
Portfolio Navigator Wizard - Enhanced Backend
FastAPI application with Enhanced Portfolio Generator System
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Import existing routers
from routers import portfolio, strategy_buckets

# Import enhanced portfolio system (avoid hard import of generator at module load)
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
# Import will be done locally in lifespan function
from utils.port_analytics import PortfolioAnalytics

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        # Fast fail: Check Redis availability first (early health check)
        try:
            import redis
            r_test = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2, socket_timeout=2)
            r_test.ping()
            logger.info("✅ Early Redis health check: connected")
        except Exception as e:
            logger.warning(f"⚠️ Early Redis health check failed: {e}")
            logger.warning("⚠️ Continuing with degraded mode - some features may be unavailable")
        
        # Initialize Redis-first data service (fast, no external API calls)
        global redis_first_data_service
        from utils.redis_first_data_service import RedisFirstDataService
        redis_first_data_service = RedisFirstDataService()
        
        # No waiting needed - Redis-first service is instant
        logger.info("✅ Redis-first data service initialized")
        
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
            
            # Schedule background generation for missing portfolios (non-blocking)
            if profiles_needing_generation:
                logger.warning(f"⚠️ Missing portfolios detected for {len(profiles_needing_generation)} profiles")
                logger.info("⏱️  Background generation will take ~2-3 minutes; API stays responsive")
                
                async def background_generate_missing_portfolios():
                    try:
                        logger.info("🚀 Background portfolio generation started...")
                        from routers.portfolio import _ensure_missing_portfolios_generated
                        import time
                        
                        start_time = time.time()
                        generated_count = 0
                        
                        for risk_profile in profiles_needing_generation:
                            try:
                                logger.info(f"🔄 Generating portfolios for {risk_profile}...")
                                await asyncio.to_thread(_ensure_missing_portfolios_generated, risk_profile)
                                
                                # Verify generation
                                count = redis_manager.get_portfolio_count(risk_profile)
                                if count >= 12:
                                    generated_count += 1
                                    logger.info(f"✅ {risk_profile}: {count}/12 portfolios generated")
                                else:
                                    logger.warning(f"⚠️ {risk_profile}: Only {count}/12 portfolios generated")
                            except Exception as e:
                                logger.error(f"❌ Error generating portfolios for {risk_profile}: {e}")
                                continue
                        
                        elapsed = time.time() - start_time
                        logger.info("="*80)
                        logger.info("✅ PORTFOLIO GENERATION COMPLETED!")
                        logger.info(f"   ⏱️  Processing Time: {elapsed:.2f}s")
                        logger.info(f"   📊 Profiles Generated: {generated_count}/{len(profiles_needing_generation)}")
                        logger.info("="*80)
                        logger.info("✅ Portfolio recommendations are now ready!")
                        
                    except Exception as e:
                        logger.error(f"❌ Background portfolio generation failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                asyncio.create_task(background_generate_missing_portfolios())
                logger.info("✅ API will serve using lazy generation until portfolios are ready")
            else:
                logger.info("✅ All portfolios available - no generation needed")
                
        except Exception as e:
            logger.error(f"❌ Portfolio cache check failed: {e}")
            logger.info("💡 Portfolios will be generated on-demand via lazy generation")
        
        # Using Redis TTL for automatic expiration (7 days for portfolios)
        logger.info("✅ Using Redis TTL for automatic portfolio expiration (7 days)")
        
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
            
            if not cache_exists:
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
                                604800,  # 1 week TTL (604800 seconds)
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
        
        logger.info("✅ Enhanced portfolio system initialized successfully")
        
        # Set Redis manager in portfolio router
        from routers.portfolio import set_redis_manager
        set_redis_manager(redis_manager)
        logger.info("✅ Redis manager set in portfolio router")
        
        # Search functionality ready (no index warming needed for basic search)
        logger.info("✅ Search functionality ready for all cached tickers")
        
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers
app.include_router(portfolio.router, tags=["portfolio"])
app.include_router(strategy_buckets.router, prefix="/api/strategy-buckets", tags=["strategy-buckets"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if enhanced portfolio system is available
        if redis_manager:
            portfolio_status = redis_manager.get_all_portfolio_buckets_status()
            available_buckets = sum(1 for status in portfolio_status.values() if status.get('available'))
            
            return {
                "status": "healthy",
                "enhanced_portfolio_system": True,
                "available_portfolio_buckets": available_buckets,
                "total_risk_profiles": 5,
                "lazy_generation": True
            }
        else:
            return {
                "status": "degraded",
                "enhanced_portfolio_system": False,
                "message": "Enhanced portfolio system not initialized"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Portfolio bucket status endpoint
@app.get("/api/enhanced-portfolio/buckets")
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

# Portfolio bucket status endpoint
@app.get("/api/enhanced-portfolio/buckets")
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

# Error handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "timestamp": str(datetime.now())
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 