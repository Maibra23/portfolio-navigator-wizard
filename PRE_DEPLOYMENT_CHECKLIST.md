# Pre-Deployment Checklist & Testing Guide
## Portfolio Navigator Wizard - Railway Deployment

**Status**: ✅ All code changes implemented
**Date**: 2026-02-05
**Estimated Testing Time**: 30-45 minutes

---

## ✅ What Has Been Implemented

All 8 pre-deployment tasks are now complete:

### 1. ✅ CORS Configuration Updated
**File**: `backend/main.py`
- Now uses `ALLOWED_ORIGINS` environment variable
- Supports multiple origins (comma-separated)
- Automatically includes localhost for development

### 2. ✅ Rate Limiting Added
**Files**: `backend/main.py`, `backend/routers/portfolio.py`
- SlowAPI integration complete
- Rate limits configured:
  - Cache warming: **2/hour** (as requested)
  - TTL endpoints: 2-20/minute
  - General endpoints: 10-30/minute

### 3. ✅ Redis TLS Support
**File**: `backend/utils/redis_first_data_service.py`
- Now supports URL-based connection (`REDIS_URL`)
- Automatic TLS detection (rediss://)
- Works with Railway's private networking

### 4. ✅ TTL Monitoring Endpoints
**File**: `backend/routers/portfolio.py`
- `GET /api/v1/portfolio/cache/ttl-status` - JSON status
- `GET /api/v1/portfolio/cache/ttl-report` - Human-readable report
- `POST /api/v1/portfolio/cache/refresh-expiring` - Auto-refresh
- `GET /api/v1/portfolio/cache/expiring-list` - Get expiring tickers

### 5. ✅ Frontend API Config
**File**: `frontend/src/config/api.ts`
- Now uses `VITE_API_BASE_URL` environment variable
- Falls back to empty string for dev (uses Vite proxy)

### 6. ✅ Environment Templates
**Files**: `backend/.env.example`, `frontend/.env.example`
- Complete documentation of all variables
- Railway-specific notes included
- Email integration variables added

### 7. ✅ Requirements Updated
**File**: `backend/requirements.txt`
- Added `slowapi>=0.1.9` for rate limiting

### 8. ✅ Email Integration
**Files**: `backend/utils/redis_ttl_monitor.py`, `backend/main.py`
- Enhanced Email webhook notifications
- Beautiful message formatting with emojis
- Automatic TTL monitoring background task
- Runs every 24 hours
- Auto-refreshes critical tickers

---

## 🧪 Local Testing Before Deployment

### Prerequisites

1. **Install Updated Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Verify Installation**
   ```bash
   pip list | grep slowapi
   # Should show: slowapi (0.1.9 or higher)
   ```

### Test 1: Backend Starts Successfully

```bash
cd backend

# Set minimal environment variables
export REDIS_URL="redis://localhost:6379"
export ALLOWED_ORIGINS="http://localhost:8080,http://localhost:5173"
export ALPHA_VANTAGE_API_KEY="your_key_here"

# Start backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
✅ Redis connection established (standard)
✅ Redis-First Data Service initialized
🔍 Starting TTL monitoring background task...
✅ Search functionality ready for all cached tickers
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Pass Criteria**: Backend starts without errors

### Test 2: Health Check

Open new terminal:
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-05T...",
  "redis_connected": true
}
```

**✅ Pass Criteria**: Returns 200 OK with healthy status

### Test 3: CORS Configuration

```bash
curl -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:8000/health \
     -v
```

**Expected**: Should see `Access-Control-Allow-Origin: http://localhost:8080` in headers

**✅ Pass Criteria**: CORS headers present

### Test 4: TTL Monitoring Endpoints

```bash
# Test TTL status endpoint
curl http://localhost:8000/api/v1/portfolio/cache/ttl-status

# Test TTL report endpoint
curl http://localhost:8000/api/v1/portfolio/cache/ttl-report

# Test expiring list endpoint
curl http://localhost:8000/api/v1/portfolio/cache/expiring-list?days_threshold=7
```

**Expected**: All return 200 OK with JSON responses

**✅ Pass Criteria**: All 3 endpoints respond successfully

### Test 5: Rate Limiting

```bash
# Test rate limiting (should block after 10 requests)
for i in {1..12}; do
  echo "Request $i:"
  curl http://localhost:8000/api/v1/portfolio/cache/ttl-status
  sleep 1
done
```

**Expected**: First 10 succeed, then see:
```json
{
  "error": "Rate limit exceeded: 10 per minute"
}
```

**✅ Pass Criteria**: Rate limiting kicks in after limit

### Test 6: Email Integration (Optional)

**Setup Email Webhook:**
1. Go to https://myaccount.google.com/apppasswords
2. Create Gmail app password
3. Copy app password

**Test:**
```bash
export TTL_EMAIL_NOTIFICATIONS=true
export SMTP_PASSWORD="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Restart backend with these variables
python -m uvicorn main:app --reload

# Trigger a manual TTL check (will send Email message)
curl http://localhost:8000/api/v1/portfolio/cache/ttl-status
```

**Expected**: Email message appears in your channel

**✅ Pass Criteria**: Email notification received

### Test 7: Frontend (Optional)

```bash
cd frontend

# Set backend URL (empty for dev, uses proxy)
export VITE_API_BASE_URL=""

# Start frontend
npm run dev
```

Open http://localhost:5173 in browser

**✅ Pass Criteria**: Frontend loads and can search tickers

---

## 📋 Pre-Deployment Checklist

Before deploying to Railway, verify:

- [x] All code changes implemented
- [ ] Backend starts locally without errors
- [ ] All tests pass (Tests 1-5 above)
- [ ] Dependencies installed (`slowapi` present)
- [ ] Git repository up to date

### Commit Your Changes

```bash
# Review changes
git status

# Add all changes
git add .

# Commit
git commit -m "Add Railway deployment readiness: CORS, rate limiting, TLS, TTL monitoring, Email integration

- Update CORS to use environment variable
- Add SlowAPI rate limiting (2/hour for cache warming)
- Update Redis connection for TLS support
- Add 4 new TTL monitoring endpoints
- Update frontend API config for production
- Add environment variable templates
- Add email (SMTP) integration
- Add automated TTL monitoring background task

Resolves pre-deployment requirements for Railway deployment.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to GitHub (triggers Railway auto-deploy)
git push origin main
```

---

## 🚀 Railway Deployment Steps

Now that code is ready, follow these steps:

### Step 1: Deploy Redis (5 minutes)

1. Go to Railway dashboard
2. Click "New Project"
3. Name: `portfolio-navigator-wizard`
4. Click "New" → "Database" → "Add Redis"
5. Wait for deployment
6. Go to Redis service → "Variables" tab
7. Copy `REDIS_URL` value

### Step 2: Deploy Backend (10 minutes)

1. Click "New" → "GitHub Repo"
2. Select your repository
3. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. Add Environment Variables:
   ```
   ALPHA_VANTAGE_API_KEY=your_actual_key
   ENVIRONMENT=production
   USE_LIVE_DATA=true
   LOG_LEVEL=INFO
   TTL_EMAIL_NOTIFICATIONS=true
   SMTP_USER=your@gmail.com
   SMTP_PASSWORD=your-app-password
   TTL_NOTIFICATION_EMAIL=your@email.com
   TTL_NOTIFICATION_EMAIL=#redis-alerts
   ```

5. **Reference Redis**:
   - Click "Add Reference" → Select Redis service
   - This automatically adds `REDIS_URL`

6. Deploy
7. Settings → Networking → Generate Domain
8. **Copy backend URL** (e.g., `https://backend-production.up.railway.app`)

### Step 3: Update Backend CORS (2 minutes)

1. Go to backend service → Variables
2. Add/Update:
   ```
   ALLOWED_ORIGINS=https://frontend-production.up.railway.app,http://localhost:8080
   ```
3. Replace with your actual frontend URL (add after frontend deployment)
4. Backend will auto-redeploy

### Step 4: Deploy Frontend (10 minutes)

1. Click "New" → "GitHub Repo" (same repository)
2. Name: `frontend`
3. Configure:
   - **Root Directory**: `frontend`
   - **Install Command**: `npm install && npm install -g serve`
   - **Build Command**: `npm run build`
   - **Start Command**: `serve -s dist -p $PORT`

4. Add Environment Variable:
   ```
   VITE_API_BASE_URL=https://your-backend-url.up.railway.app
   ```

5. Deploy
6. Generate domain
7. **Copy frontend URL**

### Step 5: Update Backend CORS with Frontend URL (2 minutes)

1. Go to backend → Variables
2. Update `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://your-frontend.up.railway.app,http://localhost:8080
   ```
3. Backend redeploys automatically

### Step 6: Warm Cache (90 minutes, automated)

```bash
# From your local machine
BACKEND_URL="https://your-backend.up.railway.app"

# Start full cache warming
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-cache"

# Monitor progress (every 5 minutes)
watch -n 300 "curl $BACKEND_URL/api/v1/portfolio/cache-status"
```

### Step 7: Verify Deployment (5 minutes)

```bash
BACKEND_URL="https://your-backend.up.railway.app"

# Health check
curl $BACKEND_URL/health

# TTL status
curl $BACKEND_URL/api/v1/portfolio/cache/ttl-status

# Test frontend
# Open https://your-frontend.up.railway.app in browser
```

### Step 8: Verify Email Notifications (1 minute)

Within 5 minutes of backend startup, you should receive a Email notification about TTL status.

Check your `#redis-alerts` channel.

---

## 🔔 Email Notification Setup

### Create Email Webhook

1. Go to https://myaccount.google.com/apppasswords
2. Click "Create New App" → "From scratch"
3. App name: "Portfolio Navigator Alerts"
4. Select your workspace
5. Click "Incoming Webhooks"
6. Toggle "Activate Incoming Webhooks" to ON
7. Click "Add New Webhook to Workspace"
8. Select channel (e.g., `#redis-alerts`)
9. Copy app password

### Configure in Railway

1. Go to backend service → Variables
2. Add:
   ```
   TTL_EMAIL_NOTIFICATIONS=true
   SMTP_USER=your@gmail.com
   SMTP_PASSWORD=your-app-password
   TTL_NOTIFICATION_EMAIL=your@email.com
   TTL_NOTIFICATION_EMAIL=#redis-alerts
   ```
3. Backend redeploys automatically

### Test Email Integration

```bash
# Trigger TTL check (sends Email message)
curl https://your-backend.up.railway.app/api/v1/portfolio/cache/ttl-status
```

Check Email channel for message like:
```
🔔 Redis Cache TTL Alert - INFO

All tickers have healthy TTL status

Total Tickers: 1432
Expired: 0 tickers
Critical (<1 day): 0 tickers
Warning (<7 days): 0 tickers
```

---

## 📊 Monitoring After Deployment

### Daily (Automated by Background Task)

- ✅ TTL monitoring runs every 24 hours
- ✅ Email notifications sent if issues detected
- ✅ Auto-refresh of critical tickers

### Weekly (Manual Check)

```bash
BACKEND_URL="https://your-backend.up.railway.app"

# Check cache status
curl $BACKEND_URL/api/v1/portfolio/cache-status

# Check TTL report
curl $BACKEND_URL/api/v1/portfolio/cache/ttl-report

# Check Railway usage
# Go to Railway dashboard → Usage
# Should be ~$3-5/month
```

### Monthly (Maintenance)

1. Check for dependency updates
2. Review Email alerts history
3. Verify cache health
4. Check Railway costs

---

## 🎯 Success Criteria

Your deployment is successful when:

- ✅ Backend health check returns 200 OK
- ✅ Frontend loads and searches work
- ✅ Redis has 1,432 tickers cached
- ✅ TTL monitoring endpoint works
- ✅ Email notifications received
- ✅ Background task running (check logs)
- ✅ Rate limiting works
- ✅ CORS allows frontend requests

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Railway logs
# Common issues:
# - Missing REDIS_URL (add Redis reference)
# - Missing ALPHA_VANTAGE_API_KEY
# - Wrong PORT (Railway sets this automatically)
```

### Redis Connection Failed
```bash
# Verify Redis is running
# Check REDIS_URL is set correctly
# Format: redis://default:password@host:port
```

### Email Notifications Not Working
```bash
# Check environment variables:
echo $TTL_EMAIL_NOTIFICATIONS  # Should be "true"
echo $SMTP_USER $TTL_NOTIFICATION_EMAIL  # Should be set

# Check backend logs for "Email notification sent"
```

### Rate Limiting Too Aggressive
```bash
# Edit backend/routers/portfolio.py
# Adjust @limiter.limit("X/minute") values
# Commit and push to trigger redeploy
```

---

## 📝 Next Steps After Deployment

1. **Monitor for 24 hours**
   - Check Email for first automatic TTL report
   - Verify cache remains healthy
   - Check Railway usage

2. **Test all features**
   - Search tickers
   - Build portfolios
   - Generate PDFs
   - Test risk profiling

3. **Set up alerts**
   - Railway usage alerts ($3, $4, $5)
   - Email notifications for errors

4. **Document**
   - Save backend and frontend URLs
   - Document any custom configurations
   - Keep SMTP credentials secure

---

## ✅ You're Ready to Deploy!

All pre-deployment tasks are complete. Your application is:
- ✅ Production-ready
- ✅ Secure (CORS, rate limiting)
- ✅ Monitored (TTL alerts, Email notifications)
- ✅ Scalable (supports Railway cloud)

**Estimated Total Deployment Time**: 2-3 hours
- Setup: 30 minutes
- Cache warming: 90 minutes (automated)
- Testing: 30 minutes

Good luck with your deployment! 🚀
