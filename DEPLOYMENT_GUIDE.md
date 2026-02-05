# Deployment Guide - Portfolio Navigator Wizard

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture & Requirements](#architecture--requirements)
4. [Deployment Options](#deployment-options)
5. [Option 1: Render.com (Recommended)](#option-1-rendercom-recommended)
6. [Option 2: Railway.app](#option-2-railwayapp)
7. [Option 3: Vercel + Render](#option-3-vercel--render)
8. [Pre-Deployment Checklist](#pre-deployment-checklist)
9. [Post-Deployment](#post-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Your Portfolio Navigator Wizard has three components that need hosting:
- **Frontend**: React + Vite static app
- **Backend**: FastAPI Python server
- **Database**: Redis for caching

**Important**: GitHub Pages can only host static files, so it won't work for your backend or Redis. You need a platform that supports full-stack applications.

---

## Prerequisites

Before deploying, ensure you have:

- [ ] Git repository with your code
- [ ] GitHub account (if using GitHub integration)
- [ ] Alpha Vantage API key (get free at https://www.alphavantage.co/support/#api-key)
- [ ] Credit card (optional, for paid tiers, but NOT required for free tiers)

---

## Architecture & Requirements

### Backend Requirements
- Python 3.9+
- Dependencies: FastAPI, Redis, yfinance, pandas, numpy, etc. (see `backend/requirements.txt`)
- Environment variables:
  - `ALPHA_VANTAGE_API_KEY` (required)
  - `REDIS_URL` or `REDIS_HOST`/`REDIS_PORT`
  - `ENVIRONMENT` (optional, defaults to 'development')
  - `USE_LIVE_DATA` (optional, defaults to 'false')

### Frontend Requirements
- Node.js 18+
- Build command: `npm run build`
- Build output directory: `frontend/dist`

### Redis Requirements
- Redis 5.0+
- At least 100MB memory recommended
- Persistent storage optional but recommended

---

## Deployment Options

| Option | Best For | Cost | Complexity |
|--------|----------|------|------------|
| **Render.com** (Recommended) | Full-stack apps | Free tier available | Low |
| **Railway.app** | Quick deployment | Free $5/month credit | Very Low |
| **Vercel + Render** | Separate frontend/backend | Mostly free | Medium |

---

## Option 1: Render.com (Recommended)

Render provides free hosting for web services, databases, and static sites.

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (recommended for auto-deploy)
3. Authorize Render to access your repository

### Step 2: Deploy Redis
1. In Render dashboard, click "New +" → "Redis"
2. Name: `portfolio-wizard-redis`
3. Select free tier ($0/month) - **Note: Limited to 25MB**
4. Click "Create Redis"
5. **Save the Internal Redis URL** - looks like: `redis://red-xxxxx:6379`

### Step 3: Deploy Backend
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `portfolio-wizard-backend`
   - **Region**: Select closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Select **Free** tier ($0/month)
   - ⚠️ Free tier sleeps after 15 min of inactivity
   - First request after sleep takes ~30 seconds to wake up
5. Add Environment Variables:
   - `ALPHA_VANTAGE_API_KEY` = `your_api_key_here`
   - `REDIS_URL` = `redis://red-xxxxx:6379` (from Step 2)
   - `ENVIRONMENT` = `production`
   - `USE_LIVE_DATA` = `true` (if you want real-time data)
6. Click "Create Web Service"
7. Wait for deployment (5-10 minutes)
8. **Save the backend URL** - looks like: `https://portfolio-wizard-backend.onrender.com`

### Step 4: Deploy Frontend
1. Click "New +" → "Static Site"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `portfolio-wizard-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add Environment Variable:
   - `VITE_API_BASE_URL` = `https://portfolio-wizard-backend.onrender.com` (your backend URL)
5. Click "Create Static Site"
6. Wait for deployment (3-5 minutes)
7. Your app is live at: `https://portfolio-wizard-frontend.onrender.com`

### Step 5: Update CORS (Important!)
After frontend deployment, you need to update backend CORS settings:

1. Go to your backend code in `backend/main.py`
2. Find the CORS middleware section (around line 120-130)
3. Add your frontend URL to allowed origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://portfolio-wizard-frontend.onrender.com",  # Add this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
4. Commit and push changes - Render will auto-deploy

### Limitations of Free Tier
- **Backend**: Sleeps after 15 min inactivity (wakes on first request in ~30s)
- **Redis**: Only 25MB storage (should be enough for ~500-1000 tickers cached)
- **Static Site**: No limitations
- **Bandwidth**: 100GB/month across all services

---

## Option 2: Railway.app

Railway is simpler but uses a credit system.

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Get $5 free monthly credit (no credit card needed)

### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your repository

### Step 3: Add Redis
1. In project dashboard, click "+ New"
2. Select "Database" → "Redis"
3. Redis will be created automatically
4. Click on Redis service → "Variables" → Copy `REDIS_URL`

### Step 4: Add Backend Service
1. Click "+ New" → "GitHub Repo" → Select your repo
2. Railway auto-detects it's a Python app
3. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `ALPHA_VANTAGE_API_KEY` = `your_api_key_here`
   - `REDIS_URL` = Paste from Step 3
   - `ENVIRONMENT` = `production`
   - `PORT` = `8000`
5. Click "Deploy"
6. Go to "Settings" → "Networking" → "Generate Domain"
7. **Save the backend URL**

### Step 5: Add Frontend Service
1. Click "+ New" → "GitHub Repo" → Select your repo (add again)
2. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build && npm install -g serve`
   - **Start Command**: `serve -s dist -p $PORT`
3. Add Environment Variable:
   - `VITE_API_BASE_URL` = `your_backend_url_from_step_4`
4. Click "Deploy"
5. Generate domain in Settings → Networking
6. Your app is live!

### Cost Estimate
- Free $5/month credit
- Typical usage: $3-5/month (backend + Redis)
- No sleep mode - always on!
- After free credit: ~$5/month

---

## Option 3: Vercel + Render

Use Vercel (fastest) for frontend, Render for backend/Redis.

### Frontend on Vercel
1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "Add New..." → "Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
6. Add Environment Variable:
   - `VITE_API_BASE_URL` = (you'll add this after backend deployment)
7. Click "Deploy"

### Backend on Render
- Follow "Option 1" steps 2-3 for Redis and Backend deployment
- After backend is deployed, go back to Vercel:
  - Project Settings → Environment Variables
  - Add `VITE_API_BASE_URL` with your backend URL
  - Redeploy frontend

### Benefits
- Frontend on Vercel CDN (faster global performance)
- Backend on Render (easier Python deployment)
- Both have generous free tiers

---

## Pre-Deployment Checklist

Before deploying, you should update your code. Here are the issues:

### 1. ⚠️ Redis Configuration (Required Fix)

**Current issue**: Redis is hardcoded to `localhost:6379` in `backend/utils/redis_first_data_service.py:28`

**Fix needed**: Update to support environment variable:
```python
def __init__(self, redis_host: str = None, redis_port: int = None):
    # Support REDIS_URL (full URL) or separate host/port
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        # Parse redis://host:port format
        import urllib.parse
        parsed = urllib.parse.urlparse(redis_url)
        redis_host = parsed.hostname or 'localhost'
        redis_port = parsed.port or 6379
    else:
        redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        redis_port = redis_port or int(os.getenv('REDIS_PORT', '6379'))

    self.redis_client = self._init_redis(redis_host, redis_port)
```

### 2. ⚠️ Frontend API URL (Required Fix)

**Current issue**: `frontend/src/config/api.ts` has empty `API_BASE_URL`

**Fix needed**:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
```

Then create `frontend/.env.production`:
```
VITE_API_BASE_URL=https://your-backend-url.onrender.com
```

### 3. ⚠️ CORS Configuration (Critical)

**Current issue**: Backend may not allow requests from production frontend

**Fix needed**: In `backend/main.py`, update CORS to include your production frontend URL:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Keep for local dev
        "https://your-frontend-url.onrender.com",  # Add production URL
        "https://your-frontend-url.vercel.app",  # If using Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Create `.env.example` File

Create `backend/.env.example` for documentation:
```bash
# Alpha Vantage API Key (Required)
# Get free key at: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Redis Connection (Required for production)
REDIS_URL=redis://localhost:6379

# Or use separate host/port:
# REDIS_HOST=localhost
# REDIS_PORT=6379

# Environment (optional)
ENVIRONMENT=production

# Use live market data (optional, default: false)
USE_LIVE_DATA=true

# Logging (optional)
LOG_LEVEL=INFO
```

### 5. Test Production Build Locally

Before deploying, test the build locally:

```bash
# Build frontend
cd frontend
npm install
npm run build
npm run preview  # Test the build

# Run backend in production mode
cd ../backend
export ENVIRONMENT=production
export ALPHA_VANTAGE_API_KEY=your_key
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Post-Deployment

### 1. Warm Up Redis Cache
Your app uses Redis for caching ticker data. On first deployment, cache is empty.

**Options**:
- Let it populate naturally (slower first few uses)
- Use the cache warming endpoint: `GET /api/portfolio/cache/warm`
- Run the backend script: `python backend/scripts/review_redis_tickers.py`

### 2. Monitor Performance
- Check Render/Railway logs for errors
- Monitor Redis memory usage (free tier = 25MB limit)
- Watch for API rate limits (Alpha Vantage free = 500 calls/day)

### 3. Set Up Custom Domain (Optional)
Both Render and Railway support custom domains:
1. Buy domain (e.g., from Namecheap, Google Domains)
2. In platform settings, add custom domain
3. Update DNS records as instructed
4. Update CORS to include new domain

### 4. Enable HTTPS
Most platforms provide free SSL certificates automatically. Verify your site uses `https://`.

---

## Troubleshooting

### Frontend can't connect to backend
**Symptoms**: API calls fail, CORS errors in browser console

**Solutions**:
1. Check `VITE_API_BASE_URL` is set correctly
2. Verify backend URL is accessible (visit `https://your-backend.com/api/portfolio/health`)
3. Update CORS in `backend/main.py` to include frontend URL
4. Check backend logs for errors

### Backend crashes on startup
**Symptoms**: Backend service fails to start, shows error in logs

**Solutions**:
1. Check all environment variables are set correctly
2. Verify Redis connection (test `REDIS_URL` format)
3. Check `requirements.txt` is in `backend/` directory
4. Review startup logs for specific error messages

### Redis connection fails
**Symptoms**: Backend errors about Redis, cache not working

**Solutions**:
1. Verify `REDIS_URL` format: `redis://host:port`
2. Check Redis service is running (in platform dashboard)
3. Test connection from backend service (same network/region)
4. Ensure Redis accepts connections from backend

### Frontend shows blank page
**Symptoms**: Deployment succeeds but site is blank

**Solutions**:
1. Check browser console for errors (F12)
2. Verify build output directory is `dist` not `build`
3. Check routes work (SPA routing may need config)
4. Verify all environment variables are set during build

### Alpha Vantage API errors
**Symptoms**: Ticker search fails, market data errors

**Solutions**:
1. Verify `ALPHA_VANTAGE_API_KEY` is set correctly
2. Check API rate limits (500 calls/day free tier)
3. Your app primarily uses Yahoo Finance (free, unlimited)
4. Alpha Vantage is fallback - app works without it

### Free tier limitations hit
**Symptoms**: Backend slow, Redis evicting data, bandwidth warnings

**Solutions**:
1. **Backend sleep**: Upgrade to paid tier ($7/month on Render)
2. **Redis memory**: Reduce cache size, clear old data, or upgrade
3. **Bandwidth**: Optimize assets, use CDN for frontend
4. Consider upgrading to paid tier for production use

---

## Cost Summary

### Free Tier (Development/Testing)
| Service | Platform | Cost | Limitations |
|---------|----------|------|-------------|
| Frontend | Vercel/Render | $0 | 100GB bandwidth |
| Backend | Render | $0 | Sleeps after 15 min |
| Redis | Render | $0 | 25MB memory |
| **Total** | | **$0** | Good for demo/testing |

### Paid Tier (Production)
| Service | Platform | Cost | Benefits |
|---------|----------|------|----------|
| Frontend | Vercel | $0 | CDN, always on |
| Backend | Render | $7/mo | Always on, 512MB RAM |
| Redis | Render | $10/mo | 256MB, persistence |
| **Total** | | **$7-17/mo** | Production-ready |

### Railway Alternative
| Service | Cost | Benefits |
|---------|------|----------|
| All-in-one | $5/mo | Everything in one place, always on |

---

## Recommended Path

For your first deployment, I recommend:

1. **Start with Render free tier** - Test everything works
2. **Use Railway for $5/month** - If you want always-on without sleep
3. **Upgrade to Render paid** - When you need more Redis and no sleep

All platforms support:
- Auto-deploy from GitHub (push code → auto-deploy)
- Environment variables
- SSL certificates (HTTPS)
- Logs and monitoring
- Easy upgrades

---

## Next Steps

1. Choose your deployment platform
2. Fix the code issues listed in "Pre-Deployment Checklist"
3. Follow the step-by-step guide for your chosen platform
4. Test thoroughly after deployment
5. Monitor logs and performance

Need help with any specific step? Let me know!
