#!/usr/bin/env python3
"""
Strategy Buckets Router - Simple, focused router for strategy bucket operations
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create a simple router without prefix for now
router = APIRouter(tags=["strategy-buckets"])

# Global variable for Redis service (will be set by main.py)
redis_service = None

def set_redis_service(service):
    """Set Redis service from main application"""
    global redis_service
    redis_service = service

@router.get("/test")
def test_strategy_router():
    """Test endpoint to verify strategy router is working"""
    return {
        "message": "Strategy Buckets Router is working!",
        "timestamp": datetime.now().isoformat(),
        "redis_service_available": redis_service is not None
    }

@router.post("/clear")
def clear_strategy_buckets():
    """Clear all existing strategy portfolio buckets from Redis"""
    try:
        if not redis_service:
            raise HTTPException(status_code=503, detail="Redis service not available")
        
        logger.info("🧹 Clearing all strategy portfolio buckets...")
        
        # Get all strategy bucket keys
        strategy_keys = redis_service.redis_client.keys("strategy_bucket:*")
        cleared_count = 0
        
        for key in strategy_keys:
            try:
                redis_service.redis_client.delete(key)
                cleared_count += 1
                logger.debug(f"✅ Cleared key: {key}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clear key {key}: {e}")
        
        logger.info(f"✅ Successfully cleared {cleared_count}/{len(strategy_keys)} strategy bucket keys")
        
        return {
            "message": "Strategy buckets cleared successfully",
            "cleared_keys": cleared_count,
            "total_keys": len(strategy_keys),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing strategy buckets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear strategy buckets: {str(e)}")

@router.get("/status")
def get_strategy_buckets_status():
    """Get status of strategy buckets in Redis"""
    try:
        if not redis_service:
            raise HTTPException(status_code=503, detail="Redis service not available")
        
        # Get all strategy bucket keys
        strategy_keys = redis_service.redis_client.keys("strategy_bucket:*")
        
        # Count by type
        personalized_count = len([k for k in strategy_keys if 'personalized' in k])
        pure_count = len([k for k in strategy_keys if 'pure' in k])
        
        return {
            "total_strategy_buckets": len(strategy_keys),
            "personalized_buckets": personalized_count,
            "pure_buckets": pure_count,
            "keys": strategy_keys[:10],  # Show first 10 keys
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting strategy buckets status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy buckets status: {str(e)}")
