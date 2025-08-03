from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from routers import portfolio, cookie_demo
from utils.enhanced_data_fetcher import enhanced_data_fetcher
from utils.ticker_store import ticker_store

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Portfolio Navigator Wizard API",
    description="Enhanced portfolio construction and analysis API with Redis caching",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(portfolio.router)
app.include_router(cookie_demo.router)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting Portfolio Navigator Wizard API...")
    
    # Initialize ticker store
    logger.info(f"📊 Loaded {ticker_store.get_ticker_count()} master tickers")
    logger.info(f"   S&P 500: {len(ticker_store.sp500_tickers)} tickers")
    logger.info(f"   Nasdaq 100: {len(ticker_store.nasdaq100_tickers)} tickers")
    
    # Note: Cache warming is now optional and can be triggered via API
    logger.info("🚀 Application ready! Use /api/portfolio/cache/warm to preload data")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Portfolio Navigator Wizard API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Portfolio Navigator Wizard API",
        "version": "2.0.0",
        "features": [
            "Enhanced monthly data fetching with Redis caching",
            "S&P 500 + Nasdaq 100 ticker validation",
            "Instant cached lookups for monthly returns",
            "Simple and efficient data management"
        ],
        "endpoints": {
            "ticker_search": "/api/portfolio/ticker/search",
            "monthly_returns": "/api/portfolio/returns/monthly",
            "cache_warm": "/api/portfolio/cache/warm",
            "cache_status": "/api/portfolio/cache/status",
            "master_tickers": "/api/portfolio/tickers/master"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ticker_count = ticker_store.get_ticker_count()
    cache_status = enhanced_data_fetcher.get_cache_status()
    
    return {
        "status": "healthy",
        "ticker_count": ticker_count,
        "cached_tickers": cache_status['cached_count']
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    ) 