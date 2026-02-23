"""
Admin router: cache management, TTL monitoring, ticker refresh, health.
Protected by ADMIN_API_KEY (X-Admin-Key header or Authorization: Bearer <key>).
Fail-closed: requests are rejected when ADMIN_API_KEY is not configured.
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from datetime import datetime

from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.redis_ttl_monitor import RedisTTLMonitor
from .portfolio_shared import WarmTickersRequest, limiter, logger, redis_manager, portfolio_analytics, require_admin_key

router = APIRouter(tags=["admin"])


@router.post("/warm-cache")
@limiter.limit("2/hour")
async def warm_cache(request: Request, _: None = Depends(require_admin_key)):
    """Warm up the Redis cache with Redis-first approach."""
    try:
        results = _rds.warm_cache()
        return {"message": "Cache warming completed", "results": results}
    except Exception as e:
        logger.error("Cache warming error: %s", e)
        raise HTTPException(status_code=500, detail="Cache warming failed: %s" % str(e))


@router.post("/warm-tickers")
def warm_tickers(body: WarmTickersRequest, _: None = Depends(require_admin_key)):
    """Warm up ticker data for a list of tickers."""
    try:
        tickers = body.tickers
        if not tickers:
            raise HTTPException(status_code=400, detail="Invalid tickers list")

        warmed = 0
        failed = []
        unique_tickers = list(set([str(t).upper().strip() for t in tickers if t and str(t).strip()]))
        logger.info("Warming %d tickers", len(unique_tickers))

        for ticker in unique_tickers:
            try:
                _ = _rds.get_monthly_data(ticker)
                _ = _rds.get_ticker_info(ticker)
                try:
                    _ = _rds.get_cached_metrics(ticker)
                except Exception:
                    pass
                warmed += 1
            except Exception as e:
                failed.append(ticker)
                logger.debug("Failed to warm %s: %s", ticker, e)

        logger.info("Warmed %d/%d tickers", warmed, len(unique_tickers))
        return {
            "status": "success",
            "warmed": warmed,
            "total": len(unique_tickers),
            "failed": failed[:10],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ticker warming error: %s", e)
        raise HTTPException(status_code=500, detail="Ticker warming failed: %s" % str(e))


@router.get("/cache-status")
async def get_cache_status(_: None = Depends(require_admin_key)):
    """Get cache status with Redis-first approach (async Redis when available)."""
    try:
        status = await _rds.get_cache_status_async()
        if status is not None:
            return status
        return _rds.get_cache_status()
    except Exception as e:
        logger.error("Cache status error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get cache status: %s" % str(e))


@router.post("/clear-cache")
def clear_cache(_: None = Depends(require_admin_key)):
    """Clear all cached data with Redis-first approach."""
    try:
        results = _rds.clear_cache()
        return {"message": "Cache cleared successfully", "results": results}
    except Exception as e:
        logger.error("Cache clearing error: %s", e)
        raise HTTPException(status_code=500, detail="Cache clearing failed: %s" % str(e))


@router.get("/cache/ttl-status")
@limiter.limit("10/minute")
async def get_cache_ttl_status(request: Request, _: None = Depends(require_admin_key)):
    """Get TTL status for all cached tickers."""
    try:
        if not _rds.redis_client:
            return {"error": "Redis not available", "message": "TTL monitoring requires Redis connection"}
        monitor = RedisTTLMonitor(_rds.redis_client)
        status = monitor.check_ttl_status()
        return {"success": True, "status": status, "message": "TTL status retrieved successfully"}
    except Exception as e:
        logger.error("TTL status error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get TTL status: %s" % str(e))


@router.get("/cache/ttl-report")
@limiter.limit("10/minute")
async def get_cache_ttl_report(request: Request, _: None = Depends(require_admin_key)):
    """Get human-readable TTL report."""
    try:
        if not _rds.redis_client:
            return {"error": "Redis not available", "report": "TTL monitoring requires Redis connection"}
        monitor = RedisTTLMonitor(_rds.redis_client)
        report = monitor.generate_ttl_report()
        return {"success": True, "report": report, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error("TTL report error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate TTL report: %s" % str(e))


@router.post("/cache/refresh-expiring")
@limiter.limit("2/hour")
async def refresh_expiring_tickers(
    request: Request,
    days_threshold: int = Query(7, description="Refresh tickers expiring within this many days"),
    _: None = Depends(require_admin_key),
):
    """Refresh tickers that are expiring soon."""
    try:
        if not _rds.redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        if days_threshold < 1 or days_threshold > 30:
            raise HTTPException(status_code=400, detail="days_threshold must be between 1 and 30")
        monitor = RedisTTLMonitor(_rds.redis_client)
        expiring_tickers = monitor.get_expiring_tickers(days_threshold)
        if not expiring_tickers:
            return {
                "success": True,
                "message": "No tickers need refreshing",
                "total_expiring": 0,
                "refreshed": 0,
                "failed": 0,
            }
        logger.info("Starting refresh of %d expiring tickers", len(expiring_tickers))
        result = monitor.refresh_expiring_tickers(days_threshold=days_threshold, data_service=_rds)
        return {"success": True, "message": "Refreshed %d out of %d tickers" % (result["refreshed"], result["total_expiring"]), **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Refresh expiring tickers error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to refresh expiring tickers: %s" % str(e))


@router.get("/cache/expiring-list")
@limiter.limit("20/minute")
async def get_expiring_tickers_list(
    request: Request,
    days_threshold: int = Query(7, description="Get tickers expiring within this many days"),
    _: None = Depends(require_admin_key),
):
    """Get list of tickers expiring within threshold."""
    try:
        if not _rds.redis_client:
            return {"error": "Redis not available", "tickers": []}
        monitor = RedisTTLMonitor(_rds.redis_client)
        expiring_tickers = monitor.get_expiring_tickers(days_threshold)
        return {
            "success": True,
            "days_threshold": days_threshold,
            "count": len(expiring_tickers),
            "tickers": expiring_tickers,
            "message": "Found %d tickers expiring within %d days" % (len(expiring_tickers), days_threshold),
        }
    except Exception as e:
        logger.error("Get expiring list error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get expiring tickers: %s" % str(e))


@router.post("/force-refresh-expired-data")
def force_refresh_expired_data(_: None = Depends(require_admin_key)):
    """Force refresh of expired data using Redis-first approach."""
    try:
        _rds.force_refresh_expired_data()
        return {"message": "Force refresh completed successfully"}
    except Exception as e:
        logger.error("Force refresh error: %s", e)
        raise HTTPException(status_code=500, detail="Force refresh failed: %s" % str(e))


@router.post("/smart-monthly-refresh")
def smart_monthly_refresh(_: None = Depends(require_admin_key)):
    """Smart monthly refresh using Redis-first approach."""
    try:
        result = _rds.smart_monthly_refresh()
        return {"message": "Smart monthly refresh completed", "result": result}
    except Exception as e:
        logger.error("Smart monthly refresh error: %s", e)
        raise HTTPException(status_code=500, detail="Smart monthly refresh failed: %s" % str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for portfolio service."""
    try:
        redis_status = "healthy"
        try:
            if _rds._async_client:
                ok = await _rds.ping_async()
                if not ok:
                    redis_status = "unhealthy: ping failed"
            elif _rds.redis_client:
                _rds.redis_client.ping()
            else:
                redis_status = "unhealthy: Redis not configured"
        except Exception as e:
            redis_status = "unhealthy: %s" % str(e)

        data_fetcher_status = "healthy"
        try:
            cache_status = _rds.get_cache_status()
            data_fetcher_status = "healthy" if cache_status else "unhealthy"
        except Exception as e:
            data_fetcher_status = "unhealthy: %s" % str(e)

        analytics_status = "healthy"
        try:
            test_data = {"allocations": [{"symbol": "AAPL", "allocation": 100}]}
            test_result = portfolio_analytics.calculate_real_portfolio_metrics(test_data)
            analytics_status = "healthy" if test_result else "unhealthy"
        except Exception as e:
            analytics_status = "unhealthy: %s" % str(e)

        return {
            "service": "portfolio-service",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "redis": redis_status,
                "data_fetcher": data_fetcher_status,
                "portfolio_analytics": analytics_status,
            },
            "version": "1.0.0",
        }
    except Exception as e:
        logger.error("Health check failed: %s", e)
        out = {
            "service": "portfolio-service",
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
        }
        if not os.getenv("ENVIRONMENT", "").lower() == "production":
            out["error"] = str(e)
        return out
