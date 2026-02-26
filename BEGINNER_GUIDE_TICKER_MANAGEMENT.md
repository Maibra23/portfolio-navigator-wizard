# Beginner's Guide: Managing Tickers After Deployment
## Portfolio Navigator Wizard

**For users new to web deployment and API management**

---

## 📚 What You Need to Know First

### What is a "Ticker"?
A **ticker** is a stock symbol (like `AAPL` for Apple, `MSFT` for Microsoft). Your app tracks 1,432 different tickers with their:
- **Price history**: 15 years of daily prices
- **Sector info**: What industry they're in
- **Metrics**: Risk, return, volatility calculations

### What is "Redis"?
**Redis** is like a super-fast storage box where your app keeps ticker data so it doesn't have to fetch it from the internet every time. Think of it as a cache (temporary storage).

### What is "TTL"?
**TTL** (Time To Live) is how long data stays fresh in Redis before it expires. Your app uses **28 days** as the TTL. After 28 days, the data is considered "stale" and needs refreshing.

---

## 🚀 After You Deploy: What Happens?

### Day 1: Deployment Day

**What you did:**
```
1. Created Railway account ✓
2. Deployed Redis database ✓
3. Deployed Backend (Python/FastAPI) ✓
4. Deployed Frontend (React) ✓
5. Connected email notifications ✓
```

**Current state:**
- ✅ Your app is live online
- ⚠️ Redis cache is **empty** (0 tickers)
- ⚠️ App works but will be **slow** (fetching from Yahoo Finance every time)

**What to do next:** Fill the cache (called "warming")

---

## 🔥 Step 1: Warm the Cache (First Time)

### What is "Cache Warming"?
**Cache warming** = Downloading all ticker data and storing it in Redis so your app is fast.

### How to do it:

**Option A: Using your web browser** (Easiest)
1. Open this URL in your browser:
   ```
   https://your-backend-url.railway.app/api/v1/portfolio/warm-cache
   ```
2. You'll see a loading screen
3. Wait ~90 minutes (yes, it takes a while!)
4. You'll see: `{"message": "Cache warming completed"}`

**Option B: Using Terminal/Command Line**
```bash
# Open Terminal (Mac) or Command Prompt (Windows)

# Copy this command (replace YOUR-URL with your actual backend URL)
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-cache

# Press Enter and wait ~90 minutes
```

**What's happening behind the scenes:**
1. Your backend contacts Yahoo Finance
2. Downloads 15 years of price data for each of 1,432 tickers
3. Stores everything in Redis
4. Takes ~90 minutes because that's a LOT of data!

**How to know it's done:**
- You'll receive a email notification (if configured)
- Or check status: `https://your-backend-url.railway.app/api/v1/portfolio/cache-status`

---

## 📊 Step 2: Understanding Your Cache Status

### Check Cache Status Anytime

**Using Browser:**
```
https://your-backend-url.railway.app/api/v1/portfolio/cache-status
```

**What you'll see:**
```json
{
  "total_tickers": 1432,
  "cached_tickers": 1432,
  "memory_used": "7.4 MB",
  "status": "healthy"
}
```

**What it means:**
- `total_tickers: 1432` = All tickers are cached ✅
- `total_tickers: 0` = Cache is empty, need to warm ❌
- `total_tickers: 500` = Only half cached, keep warming ⚠️

---

## 🔔 Step 3: Email Notifications (Set It and Forget It)

### What You'll Receive

**Every 24 hours,** Slack sends you a health report:

```
🔔 Redis Cache TTL Alert - INFO

All tickers have healthy TTL status

📊 TTL Status
Total Tickers: 1,432
Expired: 0
Warning: 120 (will expire in 7 days)
Healthy: 1,312

💾 Redis Storage
Memory Used: 7.37 MB
Total Keys: 4,991

📈 Ticker Data
Complete Data: 1,432
Missing Metrics: 19
```

### What to Do When You Get Alerts

**🔔 INFO (Green) - "Everything is fine"**
- **Action:** Nothing! Just ignore it
- **Meaning:** All data is fresh and healthy

**⚠️ WARNING (Orange) - "Some data expiring soon"**
- **Action:** Optional - You can refresh early (see Step 4)
- **Meaning:** Some tickers expire in 7 days
- **Auto-fix:** System will auto-refresh when critical

**🚨 CRITICAL (Red) - "Data expiring within 1 day"**
- **Action:** System auto-refreshes, but check email
- **Meaning:** Some tickers need immediate refresh
- **Auto-fix:** Already triggered automatically!

**❌ EXPIRED (Red) - "Some data already expired"**
- **Action:** System auto-refreshes, verify it worked
- **Meaning:** Cache missed the auto-refresh window
- **Fix:** Check if auto-refresh succeeded in logs

---

## 🔄 Step 4: Refreshing Ticker Data (Keeping It Fresh)

### Automatic Refresh (Recommended - Zero Work!)

**You don't need to do anything!**

Your app automatically:
- ✅ Checks TTL status every 24 hours
- ✅ Refreshes tickers when they expire within 1 day
- ✅ Sends email notifications to keep you informed
- ✅ Logs everything for troubleshooting

**This is already running!** It started the moment you deployed.

---

### Manual Refresh (Optional)

**When you might want to manually refresh:**
- You added new tickers to the master list
- You want the latest month's data immediately
- Email alerted you to issues and auto-refresh failed

**How to manually refresh:**

#### Option 1: Refresh All Expiring Tickers (Recommended)

**What it does:** Refreshes only tickers expiring within 7 days

**Browser:**
```
https://your-backend-url.railway.app/api/v1/portfolio/cache/refresh-expiring?days_threshold=7
```

**Terminal:**
```bash
curl -X POST "https://your-backend-url.railway.app/api/v1/portfolio/cache/refresh-expiring?days_threshold=7"
```

**Time:** ~5-20 minutes (only refreshes what's needed)

---

#### Option 2: Smart Monthly Refresh (Most Efficient)

**What it does:** Only downloads the latest month's data (not the full 15 years!)

**Browser:**
```
https://your-backend-url.railway.app/api/v1/portfolio/ticker-table/smart-refresh
```

**Terminal:**
```bash
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/ticker-table/smart-refresh
```

**Time:** ~10-20 minutes
**Best for:** Monthly maintenance

---

#### Option 3: Refresh Specific Tickers (Targeted)

**What it does:** Refreshes only the tickers you specify

**Terminal only** (requires JSON):
```bash
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-tickers \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA"]
  }'
```

**Time:** ~1 second per ticker

---

#### Option 4: Full Re-Warm (Nuclear Option)

**What it does:** Re-downloads ALL 1,432 tickers completely

**⚠️ WARNING:** Only use if cache is corrupted or completely stale

**Browser:**
```
https://your-backend-url.railway.app/api/v1/portfolio/warm-cache
```

**Time:** ~90 minutes
**Cost:** ~1,432 Yahoo Finance API calls

---

## 📅 Recommended Maintenance Schedule

### Daily: Do Nothing! 🎉
- Automatic TTL monitoring runs at 6 AM (or 5 min after deploy)
- Auto-refreshes critical tickers
- Sends email notifications

### Weekly: Quick Check (2 minutes)
```bash
# Check email for any WARNING or CRITICAL alerts
# If all INFO alerts, you're good! ✅
```

### Monthly: Optional Smart Refresh (10 minutes)
```bash
# First day of month (optional):
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/ticker-table/smart-refresh

# This gets the latest month's data
# Not required if auto-refresh is working
```

### Quarterly: Review (5 minutes)
- Check Railway usage ($3-5/month expected)
- Review Slack alert history
- Verify cache health

---

## 🆘 Common Scenarios: What to Do When...

### Scenario 1: "I just deployed, cache is empty"

**What to do:**
```bash
# Warm the cache (takes 90 minutes)
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-cache

# Go grab coffee ☕
# Come back in 90 minutes

# Check it worked:
curl https://your-backend-url.railway.app/api/v1/portfolio/cache-status
# Should show: "total_tickers": 1432
```

---

### Scenario 2: "email says WARNING - 120 tickers expiring"

**What it means:** Some tickers will expire in 7 days

**What to do:**
```
Option A: Do nothing
  - System will auto-refresh when they hit critical (< 1 day)
  - Zero work for you

Option B: Refresh early (proactive)
  curl -X POST "https://your-backend-url.railway.app/api/v1/portfolio/cache/refresh-expiring?days_threshold=7"
  - Takes 10-15 minutes
  - Prevents future critical alerts
```

**Recommendation:** Do nothing unless you want to be proactive

---

### Scenario 3: "email says CRITICAL - 45 tickers expiring within 1 day"

**What it means:** Auto-refresh should have already triggered

**What to do:**
1. **Check if auto-refresh worked:**
   ```bash
   curl https://your-backend-url.railway.app/api/v1/portfolio/cache/ttl-status
   ```

2. **If still critical, manually trigger:**
   ```bash
   curl -X POST "https://your-backend-url.railway.app/api/v1/portfolio/cache/refresh-expiring?days_threshold=1"
   ```

3. **Verify it worked:**
   ```bash
   # Wait 5-10 minutes, then check again
   curl https://your-backend-url.railway.app/api/v1/portfolio/cache/ttl-status
   # Critical count should be 0
   ```

---

### Scenario 4: "Some tickers showing old data on the website"

**What it means:** Those specific tickers expired or failed to refresh

**What to do:**
```bash
# Example: AAPL and MSFT showing old data

curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-tickers \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT"]}'

# Takes ~2 seconds
# Refresh the website to see updated data
```

---

### Scenario 5: "I want to add 10 new tickers to the app"

**What to do:**
```bash
# First, add them to your master ticker list (backend code)
# Then warm just those new tickers:

curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-tickers \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["NVDA", "AMD", "INTC", "QCOM", "MU", "TSM", "ASML", "AVGO", "TXN", "ADI"]
  }'

# Takes ~10 seconds
# New tickers now available in your app!
```

---

### Scenario 6: "Redis crashed or Railway restarted"

**What it means:** All cache is lost (empty Redis)

**What to do:**
```bash
# Re-warm the entire cache
curl -X POST https://your-backend-url.railway.app/api/v1/portfolio/warm-cache

# Wait 90 minutes
# Cache will be fully populated again
```

**Prevention:** Railway Redis has automatic backups (paid tier)

---

## 🎓 Understanding the Different Refresh Commands

### Quick Reference Chart

| Command | When to Use | Time | API Calls | Best For |
|---------|-------------|------|-----------|----------|
| **warm-cache** | First deploy, empty cache | 90 min | 1,432 | Initial setup |
| **warm-tickers** | Add specific tickers | ~1 sec/ticker | Number of tickers | Adding new tickers |
| **refresh-expiring** | Refresh expiring data | 5-20 min | 50-200 | Maintenance |
| **smart-refresh** | Monthly update | 10-20 min | ~120 | Monthly maintenance |
| **ticker-table/refresh** | Force refresh expired | Varies | Varies | Emergency fix |

---

## 💡 Tips and Best Practices

### DO ✅
- **Trust the automatic system** - It handles 99% of maintenance
- **Monitor Slack** - Set up #redis-alerts channel
- **Use smart-refresh monthly** - Gets latest data efficiently
- **Check cache-status** - Quick health check anytime
- **Keep backend URL handy** - Save it in a notes app

### DON'T ❌
- **Don't manually refresh daily** - Auto-refresh handles it
- **Don't use warm-cache repeatedly** - Only for initial setup
- **Don't ignore CRITICAL alerts** - Verify auto-refresh worked
- **Don't refresh without checking status first** - Avoid unnecessary API calls
- **Don't panic if one ticker fails** - Just refresh that specific ticker

---

## 🔍 How to Check Stuff

### Check Current Cache Status
```bash
# How many tickers are cached?
curl https://your-backend-url.railway.app/api/v1/portfolio/cache-status

# Example output:
{
  "total_tickers": 1432,  ← All tickers cached ✅
  "memory_used": "7.4 MB",
  "status": "healthy"
}
```

### Check TTL (Time Until Expiration)
```bash
# Which tickers are expiring soon?
curl "https://your-backend-url.railway.app/api/v1/portfolio/cache/expiring-list?days_threshold=7"

# Example output:
{
  "count": 120,
  "tickers": ["AAPL", "MSFT", ...],
  "message": "Found 120 tickers expiring within 7 days"
}
```

### Check TTL Report (Human Readable)
```bash
# Get a detailed text report
curl https://your-backend-url.railway.app/api/v1/portfolio/cache/ttl-report

# Example output:
REDIS TTL MONITORING REPORT
===========================
Total Tickers: 1,432
Expired: 0
Critical (< 1 day): 0
Warning (< 7 days): 120
Healthy (>= 14 days): 1,312
```

---

## 📱 Setting Up Your Slack Workspace

### Step 1: Create Slack Workspace (Free)
1. Go to https://slack.com/create
2. Sign up with email (completely free)
3. Create workspace name: "Portfolio Monitor"
4. Create channel: `#redis-alerts`

### Step 2: Create Incoming Webhook
1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create New App" → "From scratch"
3. App name: "Portfolio Navigator Alerts"
4. Select your workspace
5. Click "Incoming Webhooks"
6. Toggle "Activate Incoming Webhooks" to ON
7. Click "Add New Webhook to Workspace"
8. Select channel: `#redis-alerts`
9. Click "Allow"
10. **Copy the Webhook URL** (starts with `https://hooks.slack.com/services/...`)

### Step 3: Configure in Railway
1. Go to Railway dashboard
2. Click on your backend service
3. Go to "Variables" tab
4. Add these variables:
   ```
   TTL_EMAIL_NOTIFICATIONS=true
   TTL_NOTIFICATION_EMAIL=your@email.com, SMTP_USER, SMTP_PASSWORD (see .env.example)
   TTL_NOTIFICATION_EMAIL=#redis-alerts
   ```
5. Backend automatically redeploys
6. Wait 5 minutes - you'll get your first notification!

---

## 🎯 Summary: Your Post-Deployment Workflow

### Day 1 (Deployment Day):
```
1. Deploy to Railway ✓
2. Warm cache (90 minutes)
3. Verify via email notification
4. Done! ✅
```

### Day 2-30 (Automated):
```
- Automatic TTL monitoring running
- email notifications every 24 hours
- Auto-refresh of critical tickers
- You do: Nothing! 🎉
```

### Monthly (Optional):
```
- Review email alerts
- Optional: Run smart-refresh
- Check Railway costs
```

### When Issues Arise (Rare):
```
- Check email alert
- Check cache-status
- Manually refresh if needed
- 99% of the time: Auto-refresh already fixed it
```

---

## ❓ Frequently Asked Questions

### Q: How often should I manually refresh?
**A:** Never! The automatic system handles it. Only refresh manually if:
- Initial deployment (warm-cache once)
- email alerts you to a CRITICAL issue
- You're adding new tickers

### Q: What if I forget to refresh?
**A:** Nothing bad happens! The app still works, just fetches from Yahoo Finance directly (slightly slower). Auto-refresh will fix it within 24 hours.

### Q: How much does this cost?
**A:** Yahoo Finance: Free, unlimited (be reasonable)
Alpha Vantage: Rarely used (500/day free limit)
Railway: $3-5/month total
Slack: $0 (free forever)

### Q: Can I break anything by refreshing?
**A:** No! Refreshing just updates the cache. Worst case: You waste some API calls. The app keeps working normally.

### Q: What's the difference between warm-cache and smart-refresh?
**A:**
- **warm-cache**: Downloads all 15 years for all tickers (~90 mins)
- **smart-refresh**: Only downloads last month for affected tickers (~10-20 mins)

Use warm-cache once (initial deploy), use smart-refresh for monthly updates.

### Q: Do I need to understand Redis to use this?
**A:** No! Think of it as a temporary storage that automatically cleans itself. The automatic system manages it for you.

---

## 🚨 Emergency Contact Commands

**Copy these to your notes for quick reference:**

```bash
# Replace YOUR-BACKEND-URL with your actual URL
BACKEND_URL="https://your-backend-url.railway.app"

# Check if everything is healthy
curl "$BACKEND_URL/health"

# Check cache status
curl "$BACKEND_URL/api/v1/portfolio/cache-status"

# Check what's expiring soon
curl "$BACKEND_URL/api/v1/portfolio/cache/expiring-list?days_threshold=7"

# Emergency: Refresh critical tickers
curl -X POST "$BACKEND_URL/api/v1/portfolio/cache/refresh-expiring?days_threshold=1"

# Emergency: Full re-warm (takes 90 mins)
curl -X POST "$BACKEND_URL/api/v1/portfolio/warm-cache"
```

---

## 📚 Additional Resources

- **Full Technical Guide:** [TICKER_UPDATE_WORKFLOW.md](TICKER_UPDATE_WORKFLOW.md)
- **Deployment Guide:** [RAILWAY_DEPLOYMENT_GUIDE.md](RAILWAY_DEPLOYMENT_GUIDE.md)
- **Security Assessment:** [REDIS_SECURITY_ASSESSMENT.md](REDIS_SECURITY_ASSESSMENT.md)
- **Pre-Deployment Checklist:** [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md)

---

**You're all set!** 🎉

Remember: The system is designed to run itself. You just monitor Slack and enjoy your deployment! ☕

Questions? Check the guides above or review email notifications for system status.
