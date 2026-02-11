# Railway Deployment Guide
## Portfolio Navigator Wizard - Complete Pre-Deployment & Deployment

**Platform:** Railway.app
**Date:** 2026-02-05
**Estimated Deployment Time:** 2-3 hours (including setup and cache warming)

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Code Changes Required](#code-changes-required)
3. [Railway Account Setup](#railway-account-setup)
4. [Redis Configuration](#redis-configuration)
5. [Backend Deployment](#backend-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [TTL Monitoring Setup](#ttl-monitoring-setup)
8. [Security Configuration](#security-configuration)
9. [Cache Warming](#cache-warming)
10. [Post-Deployment Verification](#post-deployment-verification)
11. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Pre-Deployment Checklist

### ✅ Phase 1: Code Preparation (Do This First!)

Before deploying to Railway, you **must** make these code changes:

- [ ] Update CORS configuration for production
- [ ] Add rate limiting to protect endpoints
- [ ] Update Redis connection to support TLS
- [ ] Add TTL monitoring API endpoints
- [ ] Create environment variable configuration
- [ ] Test changes locally

**Estimated Time:** 4-6 hours

### ✅ Phase 2: Railway Account Setup

- [ ] Create Railway account
- [ ] Add payment method (required even for free $5 credit)
- [ ] Verify email address
- [ ] Connect GitHub account

**Estimated Time:** 15 minutes

### ✅ Phase 3: Deployment

- [ ] Deploy Redis service
- [ ] Deploy backend service
- [ ] Deploy frontend service
- [ ] Configure environment variables
- [ ] Set up custom domains (optional)

**Estimated Time:** 1-2 hours

### ✅ Phase 4: Post-Deployment

- [ ] Warm Redis cache
- [ ] Set up TTL monitoring
- [ ] Configure alerting
- [ ] Test all endpoints
- [ ] Monitor for 24 hours

**Estimated Time:** 2-3 hours

---

## Code Changes Required

### 1. Update CORS Configuration

**File:** `backend/main.py`

**Current Code (Lines 550-563):**
```python
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
```

**Replace With:**
```python
import os

# Get allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Update Redis Connection for TLS

**File:** `backend/utils/redis_first_data_service.py`

**Current Code (Lines 28-29):**
```python
def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
    self.redis_client = self._init_redis(redis_host, redis_port)
```

**Replace With:**
```python
def __init__(self, redis_url: str = None):
    """
    Initialize Redis-First Data Service

    Args:
        redis_url: Redis connection URL (redis://host:port or rediss://host:port for TLS)
                  If not provided, uses REDIS_URL env var or defaults to localhost
    """
    import os

    # Get Redis URL from parameter or environment
    if redis_url is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

    self.redis_client = self._init_redis_from_url(redis_url)
    self._enhanced_data_fetcher = None
    self._ticker_list = None

    # Cache configuration
    self.CACHE_TTL_DAYS = 28
    self.CACHE_TTL_HOURS = self.CACHE_TTL_DAYS * 24

    logger.info("✅ Redis-First Data Service initialized")

def _init_redis_from_url(self, redis_url: str) -> Optional[redis.Redis]:
    """Initialize Redis connection from URL (supports TLS)"""
    try:
        import ssl
        from urllib.parse import urlparse

        # Parse the URL
        parsed = urlparse(redis_url)

        # Check if TLS is required (rediss:// scheme)
        use_ssl = parsed.scheme == 'rediss'

        # Railway provides REDIS_URL in format: redis://default:password@host:port
        if use_ssl:
            # Use TLS connection for production
            r = redis.from_url(
                redis_url,
                decode_responses=False,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        else:
            # Standard connection for local development
            r = redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5
            )

        # Test connection
        r.ping()
        logger.info(f"✅ Redis connection established ({'TLS' if use_ssl else 'non-TLS'})")
        return r

    except redis.ConnectionError as e:
        logger.warning(f"❌ Redis connection failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Redis unavailable: {e}")
        return None
```

**Also Update Line 44 (old _init_redis method):**

Remove or rename the old `_init_redis` method since we're now using `_init_redis_from_url`.

### 3. Add Rate Limiting

**Install dependency:**
```bash
cd backend
pip install slowapi
pip freeze > requirements.txt
```

**File:** `backend/main.py`

**Add at the top (after other imports):**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
```

**Add before `app = FastAPI(...)` (around line 540):**
```python
# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
```

**Add after `app = FastAPI(...)` (around line 548):**
```python
# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**File:** `backend/routers/portfolio.py`

**Add at the top:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)
```

**Add rate limits to critical endpoints:**
```python
# Example: Search endpoint (around line 200)
@router.get("/search-tickers")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def search_tickers(request: Request, q: str = Query(...), limit: int = Query(10)):
    # ... existing code ...

# Example: Optimization endpoint
@router.post("/optimize/mean-variance")
@limiter.limit("5/minute")  # 5 requests per minute (expensive operation)
async def optimize_mean_variance(request: Request, portfolio_request: PortfolioRequest):
    # ... existing code ...

# Example: Cache warming (prevent abuse)
@router.post("/warm-cache")
@limiter.limit("1/hour")  # Only once per hour
async def warm_cache(request: Request):
    # ... existing code ...
```

### 4. Add TTL Monitoring Endpoints

**File:** `backend/routers/portfolio.py`

**Add import at the top:**
```python
from utils.redis_ttl_monitor import RedisTTLMonitor
```

**Add these new endpoints (after existing cache endpoints, around line 670):**
```python
@router.get("/cache/ttl-status")
@limiter.limit("10/minute")
async def get_cache_ttl_status(request: Request):
    """
    Get TTL (Time-To-Live) status for all cached tickers

    Returns categorization by expiration urgency:
    - Expired: Already expired
    - Critical: < 1 day left
    - Warning: < 7 days left
    - Info: < 14 days left
    - Healthy: >= 14 days left
    """
    try:
        if not _rds.redis_client:
            return {
                "error": "Redis not available",
                "message": "TTL monitoring requires Redis connection"
            }

        monitor = RedisTTLMonitor(_rds.redis_client)
        status = monitor.check_ttl_status()

        return {
            "success": True,
            "status": status,
            "message": "TTL status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"TTL status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TTL status: {str(e)}"
        )


@router.get("/cache/ttl-report")
@limiter.limit("10/minute")
async def get_cache_ttl_report(request: Request):
    """
    Get human-readable TTL report

    Returns a formatted text report showing:
    - Total tickers cached
    - Breakdown by expiration category
    - Sample of expiring tickers
    - Recommended actions
    """
    try:
        if not _rds.redis_client:
            return {
                "error": "Redis not available",
                "report": "TTL monitoring requires Redis connection"
            }

        monitor = RedisTTLMonitor(_rds.redis_client)
        report = monitor.generate_ttl_report()

        return {
            "success": True,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"TTL report error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate TTL report: {str(e)}"
        )


@router.post("/cache/refresh-expiring")
@limiter.limit("2/hour")  # Expensive operation, limit to 2 per hour
async def refresh_expiring_tickers(
    request: Request,
    days_threshold: int = Query(7, description="Refresh tickers expiring within this many days")
):
    """
    Automatically refresh tickers that are expiring soon

    Args:
        days_threshold: Refresh tickers expiring within this many days (default: 7)

    Returns:
        Statistics about the refresh operation
    """
    try:
        if not _rds.redis_client:
            raise HTTPException(
                status_code=503,
                detail="Redis not available"
            )

        if days_threshold < 1 or days_threshold > 30:
            raise HTTPException(
                status_code=400,
                detail="days_threshold must be between 1 and 30"
            )

        monitor = RedisTTLMonitor(_rds.redis_client)

        # Get list of expiring tickers first
        expiring_tickers = monitor.get_expiring_tickers(days_threshold)

        if not expiring_tickers:
            return {
                "success": True,
                "message": "No tickers need refreshing",
                "total_expiring": 0,
                "refreshed": 0,
                "failed": 0
            }

        logger.info(f"🔄 Starting refresh of {len(expiring_tickers)} expiring tickers...")

        # Perform refresh
        result = monitor.refresh_expiring_tickers(
            days_threshold=days_threshold,
            data_service=_rds
        )

        return {
            "success": True,
            "message": f"Refreshed {result['refreshed']} out of {result['total_expiring']} tickers",
            **result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh expiring tickers error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh expiring tickers: {str(e)}"
        )


@router.get("/cache/expiring-list")
@limiter.limit("20/minute")
async def get_expiring_tickers_list(
    request: Request,
    days_threshold: int = Query(7, description="Get tickers expiring within this many days")
):
    """
    Get list of tickers expiring within threshold

    Args:
        days_threshold: Number of days threshold (default: 7)

    Returns:
        List of ticker symbols that need refreshing
    """
    try:
        if not _rds.redis_client:
            return {
                "error": "Redis not available",
                "tickers": []
            }

        monitor = RedisTTLMonitor(_rds.redis_client)
        expiring_tickers = monitor.get_expiring_tickers(days_threshold)

        return {
            "success": True,
            "days_threshold": days_threshold,
            "count": len(expiring_tickers),
            "tickers": expiring_tickers,
            "message": f"Found {len(expiring_tickers)} tickers expiring within {days_threshold} days"
        }

    except Exception as e:
        logger.error(f"Get expiring list error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get expiring tickers: {str(e)}"
        )
```

### 5. Update Frontend API Configuration

**File:** `frontend/src/config/api.ts`

**Current Code (Line 2):**
```typescript
const API_BASE_URL = '';
```

**Replace With:**
```typescript
// Use environment variable for production, empty string for development (uses proxy)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
```

### 6. Create Environment Variable Template

**Create File:** `backend/.env.example`

```bash
# =============================================================================
# Portfolio Navigator Wizard - Environment Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Required Variables
# -----------------------------------------------------------------------------

# Alpha Vantage API Key (Required)
# Get free key at: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Redis Connection URL (Required for production)
# Railway format: redis://default:password@host:port
# Local development: redis://localhost:6379
REDIS_URL=redis://localhost:6379

# Allowed CORS Origins (Required for production)
# Comma-separated list of allowed frontend URLs
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173

# -----------------------------------------------------------------------------
# Optional Variables
# -----------------------------------------------------------------------------

# Environment (development, staging, production)
ENVIRONMENT=development

# Use live market data (true/false)
USE_LIVE_DATA=false

# Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# -----------------------------------------------------------------------------
# TTL Monitoring & Notifications (Optional)
# -----------------------------------------------------------------------------

# Enable email notifications for TTL alerts
TTL_EMAIL_NOTIFICATIONS=false

# Email address for TTL notifications
TTL_NOTIFICATION_EMAIL=admin@example.com

# Webhook URL for notifications (Slack, Discord, etc.)
TTL_WEBHOOK_URL=

# -----------------------------------------------------------------------------
# Redis Configuration (Optional - uses defaults if not set)
# -----------------------------------------------------------------------------

# Maximum Redis connections
REDIS_MAX_CONNECTIONS=50

# Redis socket timeout (seconds)
REDIS_SOCKET_TIMEOUT=5

# -----------------------------------------------------------------------------
# API Rate Limits (Optional - only if using custom limits)
# -----------------------------------------------------------------------------

# Alpha Vantage daily rate limit
ALPHA_VANTAGE_RATE_LIMIT=500

# Yahoo Finance retry attempts
YAHOO_FINANCE_RETRY_ATTEMPTS=3

# Cache duration in hours
CACHE_DURATION_HOURS=24

# -----------------------------------------------------------------------------
# Error Monitoring (Optional)
# -----------------------------------------------------------------------------

# Sentry DSN for error tracking
SENTRY_DSN=

# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------
# 1. Copy this file to .env and fill in actual values
# 2. Never commit .env to git (already in .gitignore)
# 3. Use different values for development, staging, and production
# 4. Railway will provide REDIS_URL automatically when you add Redis service
```

**Create File:** `frontend/.env.example`

```bash
# Portfolio Navigator Wizard - Frontend Environment Variables

# Backend API URL (Required for production)
# Leave empty for development (uses Vite proxy)
# Production example: https://your-backend.railway.app
VITE_API_BASE_URL=
```

### 7. Update requirements.txt

**File:** `backend/requirements.txt`

Add slowapi for rate limiting:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
yfinance==0.2.66
yahooquery>=2.4.1
numpy>=1.26.0
pandas>=2.0.3
requests==2.31.0
python-dotenv==1.0.0
python-dateutil==2.8.2
alpha-vantage==3.0.0
redis==5.0.1
pathlib2==2.3.7
beautifulsoup4==4.12.2
httpx==0.25.2
quantstats==0.0.62
PyPortfolioOpt==1.5.6
scipy>=1.11.0
scikit-learn>=1.3.0
reportlab>=4.0.0
matplotlib>=3.8.0
pytest>=7.0.0
pytest-cov>=4.0.0
slowapi>=0.1.9
```

### 8. Test Changes Locally

**Before deploying, test all changes locally:**

```bash
# 1. Update dependencies
cd backend
pip install -r requirements.txt

# 2. Set environment variables
export ALLOWED_ORIGINS="http://localhost:8080,http://localhost:5173"
export REDIS_URL="redis://localhost:6379"
export ALPHA_VANTAGE_API_KEY="your_key"

# 3. Start backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/portfolio/cache/ttl-status

# 5. Test rate limiting (should block after limit)
for i in {1..35}; do curl http://localhost:8000/api/v1/portfolio/search-tickers?q=AAPL; done
```

---

## Railway Account Setup

### Step 1: Create Account

1. Go to https://railway.app
2. Click "Login" → "Login with GitHub"
3. Authorize Railway to access your GitHub account
4. Complete email verification

### Step 2: Add Payment Method

**Important:** Railway requires a payment method even for the free $5 credit.

1. Go to Account Settings → Billing
2. Click "Add Payment Method"
3. Enter credit card details
4. Verify payment method

**You won't be charged immediately.** Railway gives you $5 free credit monthly.

### Step 3: Understand Pricing

**Free Tier:**
- $5 credit per month
- No credit card charged unless you exceed $5
- Typical usage for your app: $3-5/month

**What uses credits:**
- Backend service: ~$2-3/month (always-on)
- Redis: ~$1-2/month
- Frontend: Usually free (static hosting)
- Egress (bandwidth): Usually under $1/month

**Monitoring your usage:**
- Dashboard shows real-time usage
- Set usage alerts at $3, $4, $5
- Can set hard cap to prevent charges

---

## Redis Configuration

### Step 1: Deploy Redis Service

1. **In Railway Dashboard:**
   - Click "New Project"
   - Name it: `portfolio-navigator-wizard`
   - Click "New" → "Database" → "Add Redis"

2. **Redis Configuration:**
   - Railway automatically provisions Redis
   - Default memory: 512MB (more than enough)
   - Automatically enables persistence
   - Provides `REDIS_URL` environment variable

3. **Important Settings:**

   Railway automatically sets:
   - **Memory:** 512MB (can cache ~75,000+ tickers)
   - **Persistence:** Enabled (data survives restarts)
   - **TLS:** Enabled automatically
   - **Network:** Private network (secure)

### Step 2: Get Redis Connection Details

After Redis is deployed:

1. Click on Redis service
2. Go to "Variables" tab
3. Copy `REDIS_URL` value

It will look like:
```
redis://default:xxxpasswordxxx@red-xxxxxxxxxxxx.railway.app:6379
```

**Security Note:** Railway Redis uses TLS by default, but the URL shows `redis://` not `rediss://`. The connection is still encrypted on Railway's private network.

### Step 3: Configure Redis for Production

Railway Redis comes pre-configured with:
- ✅ Automatic backups
- ✅ High availability
- ✅ SSL/TLS encryption
- ✅ Private networking
- ✅ Monitoring

**No additional configuration needed!**

---

## Backend Deployment

### Step 1: Prepare Backend for Deployment

1. **Create `backend/railway.json`** (optional but recommended):

```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. **Create `Procfile`** (alternative to railway.json):

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Step 2: Deploy Backend to Railway

1. **In Railway Dashboard:**
   - Click "New" → "GitHub Repo"
   - Select your repository
   - Railway will auto-detect it's a Python app

2. **Configure Build Settings:**
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables:**

   Go to backend service → "Variables" tab → Add variables:

   ```bash
   ALPHA_VANTAGE_API_KEY=your_actual_api_key
   ENVIRONMENT=production
   USE_LIVE_DATA=true
   LOG_LEVEL=INFO
   ALLOWED_ORIGINS=  # Will add after frontend deployment
   ```

4. **Connect Redis:**
   - In "Variables" tab, click "Reference" → Select Redis service
   - This automatically adds `REDIS_URL` pointing to your Redis instance

5. **Deploy:**
   - Click "Deploy"
   - Watch build logs for any errors
   - First deployment takes ~5-10 minutes

### Step 3: Get Backend URL

After deployment:
1. Go to backend service
2. Click "Settings" → "Networking"
3. Click "Generate Domain"
4. Copy the URL (e.g., `portfolio-backend-production.up.railway.app`)

**Save this URL** - you'll need it for frontend configuration.

### Step 4: Test Backend

```bash
# Replace with your actual Railway domain
BACKEND_URL="https://portfolio-backend-production.up.railway.app"

# Test health endpoint
curl $BACKEND_URL/health

# Test cache status
curl $BACKEND_URL/api/v1/portfolio/cache-status

# Test TTL monitoring
curl $BACKEND_URL/api/v1/portfolio/cache/ttl-status
```

---

## Frontend Deployment

### Step 1: Deploy Frontend Service

1. **In Railway Dashboard:**
   - Click "New" → "GitHub Repo" (same repository)
   - Name it differently (e.g., "frontend")

2. **Configure Build Settings:**
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npm run preview` (or use static server)

   **Alternative (recommended): Use static file server**
   - **Install Command:** `npm install && npm install -g serve`
   - **Build Command:** `npm run build`
   - **Start Command:** `serve -s dist -p $PORT`

3. **Set Environment Variables:**

   ```bash
   VITE_API_BASE_URL=https://your-backend-url.railway.app
   NODE_ENV=production
   ```

   Replace `your-backend-url.railway.app` with the actual backend URL from Step 3.

4. **Deploy:**
   - Click "Deploy"
   - Wait for build to complete (~3-5 minutes)

### Step 2: Get Frontend URL

1. Go to frontend service
2. Settings → Networking → Generate Domain
3. Copy URL (e.g., `portfolio-frontend-production.up.railway.app`)

### Step 3: Update Backend CORS

Now that you have the frontend URL:

1. **Go to backend service → Variables**
2. **Update `ALLOWED_ORIGINS`:**
   ```
   https://portfolio-frontend-production.up.railway.app,http://localhost:8080
   ```
3. **Redeploy backend** (it will auto-redeploy when variables change)

### Step 4: Test Frontend

1. Open frontend URL in browser
2. Test ticker search
3. Test portfolio building
4. Check browser console for errors (F12)

---

## TTL Monitoring Setup

### Option 1: Railway Cron Job (Recommended)

Railway doesn't have native cron jobs, but you can use GitHub Actions or an external service.

**Using GitHub Actions (Free):**

**Create File:** `.github/workflows/ttl-monitor.yml`

```yaml
name: Redis TTL Monitoring

on:
  schedule:
    # Run daily at 6 AM UTC
    - cron: '0 6 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  monitor-ttl:
    runs-on: ubuntu-latest
    steps:
      - name: Call TTL Status Endpoint
        run: |
          echo "Checking TTL status..."
          curl -X GET "${{ secrets.BACKEND_URL }}/api/v1/portfolio/cache/ttl-report"

      - name: Refresh Expiring Tickers
        run: |
          echo "Refreshing expiring tickers..."
          curl -X POST "${{ secrets.BACKEND_URL }}/api/v1/portfolio/cache/refresh-expiring?days_threshold=7"
```

**Setup:**
1. Go to your GitHub repo → Settings → Secrets
2. Add secret: `BACKEND_URL` = `https://your-backend.railway.app`
3. Commit the workflow file
4. GitHub Actions will run daily

### Option 2: Background Task in Backend

**File:** `backend/main.py`

Add this in the lifespan function:

```python
import asyncio
from utils.redis_ttl_monitor import RedisTTLMonitor

async def ttl_monitoring_task():
    """Background task to monitor TTL and refresh expiring cache"""
    await asyncio.sleep(60)  # Wait 1 minute after startup

    monitor = RedisTTLMonitor(redis_first_data_service.redis_client)

    while True:
        try:
            logger.info("🔍 Running TTL monitoring check...")

            # Check TTL status
            status = monitor.check_ttl_status()

            # Log status
            categories = status.get('categories', {})
            logger.info(
                f"TTL Status - "
                f"Expired: {categories.get('expired', 0)}, "
                f"Critical: {categories.get('critical', 0)}, "
                f"Warning: {categories.get('warning', 0)}"
            )

            # Auto-refresh if critical or warning
            if categories.get('critical', 0) > 0 or categories.get('warning', 0) > 5:
                logger.warning("🔄 Auto-refreshing expiring tickers...")
                result = monitor.refresh_expiring_tickers(
                    days_threshold=7,
                    data_service=redis_first_data_service
                )
                logger.info(
                    f"✅ Refreshed {result['refreshed']}/{result['total_expiring']} tickers"
                )

            # Wait 24 hours before next check
            await asyncio.sleep(86400)  # 24 hours

        except Exception as e:
            logger.error(f"❌ TTL monitoring error: {e}")
            # Wait 1 hour before retry on error
            await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Portfolio Navigator Wizard Backend...")

    # ... existing startup code ...

    # Start TTL monitoring task
    logger.info("🔍 Starting TTL monitoring background task...")
    asyncio.create_task(ttl_monitoring_task())

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
```

### Option 3: External Monitoring Service

Use **EasyCron** or **Cron-job.org** (both have free tiers):

1. Sign up at https://www.easycron.com
2. Create new cron job:
   - **URL:** `https://your-backend.railway.app/api/v1/portfolio/cache/ttl-status`
   - **Schedule:** Daily at 6 AM
3. Add another for auto-refresh:
   - **URL:** `https://your-backend.railway.app/api/v1/portfolio/cache/refresh-expiring?days_threshold=7`
   - **Schedule:** Daily at 6:30 AM

---

## Security Configuration

### 1. Environment Variable Security

**Railway Best Practices:**

✅ **Use Railway's variable references:**
```bash
# Instead of hardcoding URLs, reference other services
REDIS_URL=${{Redis.REDIS_URL}}
BACKEND_URL=${{backend.RAILWAY_PUBLIC_DOMAIN}}
```

✅ **Use different values per environment:**
- Create "staging" and "production" environments
- Each environment has its own variables

✅ **Rotate secrets regularly:**
- Change `ALPHA_VANTAGE_API_KEY` every 90 days
- Update Railway variables when rotated

### 2. Network Security

Railway provides:
- ✅ **Private networking** between services
- ✅ **Automatic HTTPS** for all public endpoints
- ✅ **DDoS protection**
- ✅ **SSL/TLS certificates** (auto-renewed)

**No additional configuration needed.**

### 3. Rate Limiting Configuration

Already implemented in code changes above.

**Monitor rate limiting:**
```bash
# Check logs for rate limit violations
# In Railway dashboard → Service → Logs
# Search for "429" or "Rate limit"
```

**Adjust limits if needed:**
Edit `backend/routers/portfolio.py` rate limit decorators.

### 4. Logging & Monitoring

**Railway provides:**
- ✅ Real-time logs (last 7 days on free tier)
- ✅ Resource usage metrics
- ✅ Deployment history
- ✅ Health checks

**Set up alerts:**
1. Go to Service → Metrics
2. Set up alerts for:
   - High CPU usage (>80%)
   - High memory usage (>80%)
   - Error rate increase
   - Deployment failures

### 5. Additional Security Measures

**Enable these in Railway:**

1. **Deploy Protection:**
   - Settings → "Require confirmation for deployments"
   - Prevents accidental deploys

2. **Access Control:**
   - Only invite necessary team members
   - Use GitHub teams for access control

3. **Environment Separation:**
   - Create separate projects for staging/production
   - Test in staging before production deploy

---

## Cache Warming

### Immediately After Deployment

**Step 1: Verify Redis Connection**
```bash
curl https://your-backend.railway.app/api/v1/portfolio/cache-status
```

**Expected response:**
```json
{
  "total_tickers": 0,
  "cached_tickers": 0,
  "message": "Cache is empty - ready for warming"
}
```

**Step 2: Warm Cache with All Tickers**

**Option A: Use warm-cache endpoint** (Automatic)
```bash
curl -X POST https://your-backend.railway.app/api/v1/portfolio/warm-cache
```

This will take ~90 minutes to fetch all 1,432 tickers.

**Option B: Warm specific tickers** (Faster initial deployment)
```bash
# Warm top 100 popular tickers first (5-10 minutes)
curl -X POST https://your-backend.railway.app/api/v1/portfolio/warm-tickers \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": [
      "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK.B",
      "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "NFLX",
      "VZ", "ADBE", "CMCSA", "PFE", "INTC", "CSCO", "PEP", "KO", "T",
      "NKE", "MRK", "XOM", "ABT", "CVX", "WMT", "CRM", "TMO", "AVGO",
      "COST", "ACN", "ORCL", "DHR", "NEE", "LLY", "TXN", "MDT", "UNP",
      "BMY", "QCOM", "PM", "LOW", "UPS", "HON", "LIN", "RTX", "IBM",
      "CAT", "AMGN", "SBUX", "GS", "BA", "MMM", "GE", "SPGI", "BLK",
      "AXP", "DE", "ISRG", "AMD", "NOW", "TGT", "INTU", "GILD", "CVS",
      "ZTS", "SYK", "BKNG", "MO", "CI", "MDLZ", "VRTX", "ADP", "REGN",
      "DUK", "PLD", "CCI", "SO", "TJX", "CME", "USB", "MS", "PNC",
      "BDX", "AON", "CL", "MMC", "EOG", "WM", "ITW", "NSC"
    ]
  }'
```

Then schedule full warming overnight:
```bash
# Later, warm remaining tickers
curl -X POST https://your-backend.railway.app/api/v1/portfolio/warm-cache
```

**Step 3: Monitor Cache Warming Progress**

```bash
# Check progress every few minutes
watch -n 300 'curl https://your-backend.railway.app/api/v1/portfolio/cache-status'
```

**Step 4: Verify Cache is Populated**

```bash
# Should show ~1,432 tickers after full warming
curl https://your-backend.railway.app/api/v1/portfolio/cache-status

# Check TTL status
curl https://your-backend.railway.app/api/v1/portfolio/cache/ttl-status
```

**Expected after warming:**
```json
{
  "total_tickers": 1432,
  "categories": {
    "expired": 0,
    "critical": 0,
    "warning": 0,
    "info": 0,
    "healthy": 1432
  },
  "needs_action": false
}
```

---

## Post-Deployment Verification

### Comprehensive Testing Checklist

**1. Health Checks**
```bash
# Backend health
curl https://your-backend.railway.app/health
# Expected: {"status": "healthy"}

# Redis connection
curl https://your-backend.railway.app/api/v1/portfolio/cache-status
# Expected: Shows ticker count
```

**2. API Endpoints**
```bash
# Search
curl "https://your-backend.railway.app/api/v1/portfolio/search-tickers?q=AAPL"

# Ticker info
curl "https://your-backend.railway.app/api/v1/portfolio/tickers"

# TTL status
curl "https://your-backend.railway.app/api/v1/portfolio/cache/ttl-status"
```

**3. Frontend**
- Open frontend URL in browser
- Test search functionality
- Build a test portfolio
- Complete risk profiling
- Generate PDF report
- Check all tabs work

**4. Security**
```bash
# Test CORS (from different origin - should be blocked)
curl -H "Origin: https://evil.com" https://your-backend.railway.app/health

# Test rate limiting (should block after limit)
for i in {1..35}; do
  curl "https://your-backend.railway.app/api/v1/portfolio/search-tickers?q=AAPL"
done
# Should see "Rate limit exceeded" after ~30 requests
```

**5. Monitoring**
- Check Railway logs for errors
- Verify no 500 errors
- Check Redis memory usage (should be ~7-8 MB after warming)
- Verify TTL monitoring is running

---

## Monitoring & Maintenance

### Daily Monitoring

**Automated:**
- GitHub Actions runs TTL check daily
- Or backend background task checks automatically
- Alerts sent if issues detected

**Manual (Optional):**
```bash
# Quick health check
curl https://your-backend.railway.app/api/v1/portfolio/cache/ttl-report
```

### Weekly Review

1. **Check Railway Dashboard:**
   - Total usage ($X of $5 credit)
   - Any deployment failures
   - Error rate trends

2. **Review Logs:**
   - Search for errors or warnings
   - Check for unusual patterns
   - Verify TTL refresh ran successfully

3. **Cache Health:**
   ```bash
   # Check cache status
   curl https://your-backend.railway.app/api/v1/portfolio/cache-status

   # Check TTL status
   curl https://your-backend.railway.app/api/v1/portfolio/cache/ttl-status
   ```

### Monthly Maintenance

1. **Dependency Updates:**
   ```bash
   # Check for security updates
   pip list --outdated

   # Update requirements.txt
   pip install --upgrade package-name
   pip freeze > requirements.txt

   # Commit and push (triggers auto-deploy)
   git add requirements.txt
   git commit -m "Update dependencies"
   git push
   ```

2. **API Key Rotation:**
   - Generate new Alpha Vantage key
   - Update in Railway variables
   - Delete old key

3. **Cache Cleanup:**
   ```bash
   # Clear old cache (if needed)
   curl -X POST https://your-backend.railway.app/api/v1/portfolio/cache/clear

   # Re-warm cache
   curl -X POST https://your-backend.railway.app/api/v1/portfolio/warm-cache
   ```

### Scaling Considerations

**When to upgrade from free tier ($5/month):**

- **Usage consistently >$5/month** for 2-3 months
- **Backend sleep is affecting users** (upgrade to Pro Plan $7/month)
- **Redis memory >80%** (upgrade Redis to 2GB for $10/month)
- **Multiple concurrent users** experiencing slowness

**Current free tier capacity:**
- ~500-1,000 requests/day
- 1-5 concurrent users
- 1,432 tickers cached
- Response times <500ms (when warm)

---

## Cost Monitoring

### Setting Up Budget Alerts

1. **In Railway Dashboard:**
   - Go to Account → Usage
   - Click "Set Usage Limit"
   - Set limit to $5 (or $10 with buffer)

2. **Set Email Alerts:**
   - Alert at $3 (60% of free tier)
   - Alert at $4 (80% of free tier)
   - Alert at $5 (100% of free tier)

### Typical Monthly Costs

**Free Tier Usage:**
```
Backend service:    $2-3
Redis:              $1-2
Frontend:           $0 (static)
Bandwidth:          $0-1
────────────────────────
Total:              $3-6/month
```

**If you exceed $5:**
You'll be charged the difference (e.g., $1 if usage is $6).

### Cost Optimization Tips

1. **Reduce Redis memory:**
   - Keep only popular tickers cached
   - Use shorter TTL (14 days instead of 28)

2. **Optimize API calls:**
   - Cache warming during off-peak hours
   - Reduce unnecessary refreshes

3. **Use Railway's free static hosting:**
   - Frontend is free on Railway
   - Or use Vercel (also free) for frontend

---

## Troubleshooting

### Common Issues

**Issue 1: Backend won't start**
- **Error:** "Port $PORT not found"
- **Fix:** Ensure start command uses `--port $PORT`
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

**Issue 2: Redis connection failed**
- **Error:** "Redis connection failed"
- **Fix:** Verify `REDIS_URL` is set correctly in variables

**Issue 3: CORS errors in frontend**
- **Error:** "CORS policy: No 'Access-Control-Allow-Origin'"
- **Fix:** Update `ALLOWED_ORIGINS` to include frontend URL

**Issue 4: Rate limiting too aggressive**
- **Error:** "429 Too Many Requests"
- **Fix:** Adjust rate limits in code or wait for reset

**Issue 5: Cache warming times out**
- **Error:** "Request timeout during cache warming"
- **Fix:** Warm cache in batches instead of all at once

---

## Summary Checklist

Before deployment, ensure:

- [ ] All code changes committed and pushed
- [ ] `slowapi` added to requirements.txt
- [ ] `.env.example` files created
- [ ] Local testing completed successfully
- [ ] Railway account created with payment method
- [ ] GitHub repository connected to Railway

During deployment:
- [ ] Redis service deployed and URL copied
- [ ] Backend deployed with all environment variables
- [ ] Frontend deployed with backend URL
- [ ] CORS updated with frontend URL
- [ ] All services have generated domains
- [ ] Health checks passing

After deployment:
- [ ] Cache warmed with all tickers
- [ ] TTL monitoring configured
- [ ] Alerts set up (GitHub Actions or background task)
- [ ] Frontend tested in browser
- [ ] Security verified (CORS, rate limiting)
- [ ] Usage alerts configured

---

## Next Steps

You're now ready to deploy to Railway!

**What would you like me to help with?**

1. **Implement the code changes** (CORS, rate limiting, Redis TLS, TTL endpoints)
2. **Create the deployment scripts** (automated deployment commands)
3. **Set up the monitoring system** (choose which option: GitHub Actions, background task, or external)
4. **Walk through the deployment** step-by-step
5. **Something else**

The complete deployment will take approximately:
- **Code changes & testing:** 4-6 hours
- **Railway deployment:** 1-2 hours
- **Cache warming:** 1-2 hours
- **Monitoring setup:** 1 hour
- **Total:** 7-11 hours (can be spread over 2-3 days)

Let me know what you'd like to tackle first!
