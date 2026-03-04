# Upstash Console and Population Reference

This document is a reference for Upstash console usage, pipeline verification, and how the Redis population system works. It also covers the choice between standalone Upstash and Fly.io-integrated Redis.

---

## Pipeline Verification Results

After deployment or when verifying that the backend writes to Upstash correctly, you can confirm the pipeline with a small test. Example results:

| Test | Result |
|------|--------|
| Upstash connection | Working |
| Fetch 3 test tickers | 3/3 success |
| Data stored in Upstash | 76 keys |
| Cache status shows data | 16 tickers cached |

The pipeline is working correctly when these checks pass. You can then proceed with full population.

Note: The numbers above (76 keys, 16 tickers cached) are from a small verification run. A full population of all ~1432 tickers yields thousands of keys (e.g. 5700+) and 100% price/sector/metrics coverage.

---

## How the Population System Works

The system has three fetch modes: full fetch, cache-aware fetch, and incremental fetch. Understanding these prevents unnecessary API calls and explains why subsequent runs are faster.

### 1. First-Time Population

- Fetches all ~1432 tickers from Yahoo Finance.
- Takes about 1.5–2 hours (rate limits: 1.3–4 sec delay per ticker).
- Each ticker gets a 90-day TTL with ±15% jitter to prevent stampede.

### 2. Subsequent Warm-Cache Calls (Smart Refresh)

Code reference: `backend/utils/enhanced_data_fetcher.py` (e.g. lines 888–912).

The system checks cache first before fetching (unless `force_fetch` is requested):

```python
if not force_fetch:
    cached_prices = self._load_from_cache(ticker, 'prices')
    cached_sector = self._load_from_cache(ticker, 'sector')
    if cached_prices is not None and cached_sector is not None:
        self.stats['cached'] += 1
        return {'prices': cached_prices, 'sector': cached_sector}  # SKIP fetch
```

| Scenario | What Happens |
|----------|--------------|
| Ticker has valid cache | Skip fetch, use cached data |
| Ticker TTL expired (90 days) | Fetch fresh data |
| Ticker missing from cache | Fetch fresh data |
| force_fetch=True | Force fetch regardless of cache |

### 3. Incremental Updates (Proactive Refresh)

Code reference: `backend/utils/enhanced_data_fetcher.py` (e.g. lines 792–826).

When TTL is approaching expiration, the system can fetch only new months since the last cached date:

```python
def _fetch_incremental(self, ticker: str):
    # Only fetch NEW months since last cached date
    last_cached_date = cached_prices.index[-1]
    incremental_start = last_cached_date + 1 month
    # Merge new data with existing
    merged = pd.concat([cached_prices, new_prices])
```

- After initial population, subsequent refreshes only fetch 1–2 months of new data.
- The system does not re-fetch 20 years of history every time.

---

## Upstash: Standalone vs Fly.io Integrated

| Feature | Standalone Upstash (Current) | Fly.io Integrated Upstash |
|---------|------------------------------|----------------------------|
| Dashboard | console.upstash.com | fly.io dashboard + Upstash console |
| Connection URL | Set manually via `fly secrets set REDIS_URL=...` | Auto-injected by Fly |
| Billing | Separate Upstash account | Consolidated in Fly billing |
| Region selection | Manual (you choose) | Auto-selects closest to Fly app |
| Setup | Manual database creation | `fly redis create` command |
| SSL/TLS | You must use `rediss://` | Auto-configured |
| Secret management | Manual | Auto-managed by Fly |
| Data browser | Upstash console only | Upstash console (linked from Fly) |

### Current Setup (Standalone)

- You create the database at [console.upstash.com](https://console.upstash.com).
- You set the secret manually:

  ```bash
  fly secrets set REDIS_URL="rediss://...@noted-bream-63128.upstash.io:6379"
  ```

### Fly.io Integrated Alternative

- Creates Upstash Redis linked to your Fly account:

  ```bash
  fly redis create --name portfolio-redis --region ams
  ```

- Auto-injects `REDIS_URL` into your app.
- Billing appears on the Fly invoice.
- Database is visible via `fly redis list`.

---

## Which to Use

| Use Standalone When | Use Fly-Integrated When |
|---------------------|--------------------------|
| Need REST API access | Want simpler management |
| Use multiple Fly orgs | Want consolidated billing |
| Already have Upstash account | Setting up a new project |
| Need Upstash-specific features (Vector, QStash) | Want auto-region selection |

Your current standalone setup is fine. The main disadvantage is manual secret management; functionally there is no difference.

---

## Ready to Populate

After verifying the pipeline:

**Start full population (ticker cache only):**

```bash
curl -X POST "https://portfolio-navigator-wizard.fly.dev/api/v1/portfolio/warm-cache" \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY"
```

**Monitor in another terminal:**

```bash
fly logs -a portfolio-navigator-wizard
```

For full population including portfolio buckets (60 portfolios), use the manual population script via SSH as described in [DEPLOYMENT_OPERATIONS.md](DEPLOYMENT_OPERATIONS.md).

---

## Notification System (Deployed Webapp)

Notifications are **email-only** and **opt-in**. They are sent by the backend via SMTP; the webapp UI has no notification settings or status for these alerts.

### How It Works

- **Opt-in:** Email sending is gated by `TTL_EMAIL_NOTIFICATIONS=true`. If this is false or unset, no email is sent.
- **Recipient and SMTP:** The backend uses `TTL_NOTIFICATION_EMAIL` (valid email address), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` (or `GMAIL_APP_PASSWORD`). If any of these are missing, the notification is skipped and the failure is logged at debug level only.
- **Triggers (all from `backend/main.py`):**
  - **Cold start:** Redis empty at startup — one throttled notification.
  - **TTL monitoring:** Started about 5 minutes after startup, then every 6 hours. Uses `backend/utils/redis_ttl_monitor.py` and the email callback for CRITICAL, WARNING, and EXPIRED TTL alerts.
  - **Redis watchdog:** Redis connectivity lost or restored — throttled notifications.
  - **HTTP 5xx:** Rate-limited email on 5xx responses.
  - **Regeneration:** Notifications for scheduled refresh (expired/critical), refresh completed, and similar events (throttled).

### Verifying on the Deployed Webapp

1. **Secrets on Fly:** Ensure the app has `TTL_EMAIL_NOTIFICATIONS=true`, `TTL_NOTIFICATION_EMAIL`, `SMTP_USER`, and `SMTP_PASSWORD` (and optionally `SMTP_HOST`, `SMTP_PORT`) set via `fly secrets set`. If any are missing, no email is sent and no error is shown in the UI.
2. **Logs:** Run `fly logs -a portfolio-navigator-wizard` and look for:
   - "TTL monitoring background task started"
   - "Running TTL monitoring check..."
   - TTL status lines (total tickers, expired, critical, warning, healthy).
   - At DEBUG level: "Email notification sent" on success, or "Email send failed (non-fatal)" on failure.
3. **Inbox:** After a deploy with cold start (e.g. empty Redis) or about 5+ minutes after startup (first TTL run), check the inbox for `TTL_NOTIFICATION_EMAIL`. With notifications enabled and SMTP correctly set, cold start or TTL alerts should produce an email.
4. **Working as intended:** The app runs normally even when email is not configured or disabled; it simply does not send. There are no in-app toggles or status. Verification is via environment (secrets), logs, and inbox.
