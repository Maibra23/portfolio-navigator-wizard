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
from utils.portfolio_auto_regeneration_service import PortfolioAutoRegenerationService
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
auto_regeneration_service = None
strategy_optimizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Portfolio Navigator Wizard Backend...")
    
    try:
        # Initialize Redis-first data service (fast, no external API calls)
        global redis_first_data_service
        from utils.redis_first_data_service import RedisFirstDataService
        redis_first_data_service = RedisFirstDataService()
        
        # No waiting needed - Redis-first service is instant
        logger.info("✅ Redis-first data service initialized")
        
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
                    import asyncio
                    async def background_initial_generation():
                        try:
                            logger.info("🚀 Background initial strategy pre-generation started...")
                            strategy_optimizer.pre_generate_all_strategy_portfolios()
                            logger.info("✅ Background initial generation completed")
                            strategy_optimizer.display_cache_status()
                        except Exception as e:
                            logger.error(f"❌ Background initial generation failed: {e}")
                    asyncio.create_task(background_initial_generation())
                    logger.info("✅ API will serve using on-demand generation and fallbacks until cache is ready")
                    
                elif cache_status['needs_refresh']:
                    # Cache expiring soon - schedule background refresh
                    logger.info("🔄 Cache TTL < 24 hours - scheduling background refresh")
                    import asyncio
                    async def background_refresh():
                        try:
                            logger.info("🔄 Background refresh started...")
                            strategy_optimizer.pre_generate_all_strategy_portfolios()
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
        
        # Initialize auto-regeneration service
        global auto_regeneration_service
        try:
            auto_regeneration_service = PortfolioAutoRegenerationService(
                redis_first_data_service, enhanced_generator, redis_manager
            )
        except Exception as e:
            auto_regeneration_service = None
            logger.warning(f"⚠️ Auto-regeneration service disabled: {e}")
        
        # Auto refresh service removed - using Redis TTL for automatic expiration
        logger.info("✅ Using Redis TTL for automatic data expiration (28 days)")
        
        # Smart portfolio availability check - only generate if truly needed
        logger.info("🚀 Checking portfolio availability in Redis...")
        
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
        
        # Quick check: count total portfolios in Redis
        total_portfolios = 0
        profiles_needing_generation = []
        
        for risk_profile in risk_profiles:
            portfolio_count = redis_manager.get_portfolio_count(risk_profile)
            total_portfolios += portfolio_count
            
            if portfolio_count < 12:  # Need at least 12 portfolios per profile
                profiles_needing_generation.append(risk_profile)
                logger.info(f"📊 {risk_profile}: {portfolio_count}/12 portfolios - needs generation")
            else:
                logger.info(f"✅ {risk_profile}: {portfolio_count}/12 portfolios - sufficient")
        
        logger.info(f"📊 Total portfolios in Redis: {total_portfolios}")
        
        # FIX #1: Temporarily disable portfolio generation to allow immediate server binding
        if total_portfolios < 60:
            logger.warning(f"⚠️ Insufficient portfolios in Redis ({total_portfolios}/60)")
            logger.info("💡 Portfolio generation temporarily disabled for fast startup")
            logger.info("💡 Use POST /api/portfolio/regenerate to generate portfolios manually")
            logger.info(f"📋 Profiles needing generation: {', '.join(profiles_needing_generation)}")
        else:
            logger.info("✅ Sufficient portfolios available in Redis - no generation needed")
            
            # Lazy Stock Selection - cache will be populated on-demand when needed
            logger.info("🔄 Stock selection cache will be populated on-demand when needed")
            logger.info("✅ Portfolio system ready for immediate use")
            
            # Verify Redis health
            try:
                # Use the correct method for Redis health check
                redis_status = redis_manager.redis_client.ping() if redis_manager.redis_client else False
                if redis_status:
                    logger.info("✅ Redis health check: connected and responsive")
                else:
                    logger.warning("⚠️ Redis health check: not responsive")
            except Exception as e:
                logger.warning(f"⚠️ Redis health check failed: {e}")
        
        # Auto-regeneration service ready for manual triggers (monitoring removed)
        logger.info("✅ Auto-regeneration service ready for manual triggers")
        
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
        
        if auto_regeneration_service:
            auto_regeneration_service.stop_monitoring()
            logger.info("✅ Auto-regeneration service stopped")

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
                "auto_regeneration_service": auto_regeneration_service.is_running if auto_regeneration_service else False
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

# Enhanced portfolio system status endpoint
@app.get("/api/enhanced-portfolio/status")
async def get_enhanced_portfolio_status():
    """Get status of enhanced portfolio system"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        status = auto_regeneration_service.get_service_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get enhanced portfolio status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced portfolio system performance endpoint
@app.get("/api/enhanced-portfolio/performance")
async def get_enhanced_portfolio_performance():
    """Get performance metrics of enhanced portfolio system"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        metrics = auto_regeneration_service.get_performance_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get enhanced portfolio performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Force portfolio regeneration endpoint
@app.post("/api/enhanced-portfolio/regenerate")
async def force_portfolio_regeneration(risk_profile: str = None):
    """Force portfolio regeneration for specific or all risk profiles"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        results = auto_regeneration_service.force_regeneration(risk_profile)
        return results
        
    except Exception as e:
        logger.error(f"Failed to force portfolio regeneration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Emergency portfolio regeneration endpoint
@app.post("/api/enhanced-portfolio/emergency-regenerate")
async def emergency_portfolio_regeneration():
    """Emergency portfolio regeneration when system detects critical issues"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        results = auto_regeneration_service.emergency_regeneration()
        return results
        
    except Exception as e:
        logger.error(f"Failed to perform emergency portfolio regeneration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data change detection endpoint
@app.get("/api/enhanced-portfolio/data-changes")
async def get_data_changes():
    """Get summary of data changes across all risk profiles"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        data_change_detector = auto_regeneration_service.data_change_detector
        summary = data_change_detector.get_data_change_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get data changes: {e}")
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

# Enhanced portfolio system cache status endpoint
@app.get("/api/enhanced-portfolio/cache-status")
async def get_cache_status():
    """Get cache status and performance metrics"""
    try:
        if not auto_regeneration_service:
            raise HTTPException(status_code=503, detail="Enhanced portfolio system not available")
        
        # Get cache status from stock selector
        from utils.portfolio_stock_selector import PortfolioStockSelector
        
        stock_selector = PortfolioStockSelector(redis_first_data_service)
        cache_status = {
            'cache_enabled': True,
            'cache_timestamp': stock_selector._cache_timestamp.isoformat() if stock_selector._cache_timestamp else None,
            'cache_ttl_hours': stock_selector._cache_ttl_hours,
            'cache_size': len(stock_selector._stock_cache),
            'cache_valid': (
                stock_selector._cache_timestamp and 
                (datetime.now() - stock_selector._cache_timestamp).total_seconds() < stock_selector._cache_ttl_hours * 3600
            ) if stock_selector._cache_timestamp else False
        }
        
        return {
            'cache_status': cache_status,
            'optimization_features': {
                'stock_cache_enabled': True,
                'shared_stock_data': True,
                'batch_portfolio_generation': True,
                'smart_regeneration_scheduling': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
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