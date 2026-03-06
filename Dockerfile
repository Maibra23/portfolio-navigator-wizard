# Portfolio Navigator Wizard — Fly.io Deployment with External Redis (Upstash)
# Connects to Upstash Redis for persistent data storage.
#
# Usage:
#   fly deploy --remote-only       (no local Docker required)
#   docker build -t portfolio-wizard .   (local build)
#
# Environment variables required at runtime:
#   REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379  (set via fly secrets)
#   ALLOWED_ORIGINS=https://yourdomain.com
#   ADMIN_API_KEY=<strong-random-key>
#   For email alerts: TTL_EMAIL_NOTIFICATIONS, TTL_NOTIFICATION_EMAIL, SMTP_USER, SMTP_PASSWORD
#   See backend/.env.example for full list
#
# Migration from bundled Redis:
#   1. Create Upstash database at https://console.upstash.com (choose eu-central-1)
#   2. Set secret: fly secrets set REDIS_URL="rediss://default:xxx@xxx.upstash.io:6379"
#   3. Deploy: fly deploy --remote-only

FROM python:3.11-slim

# Install only build dependencies (no Redis server needed with Upstash)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying code (layer-cache friendly)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# REDIS_URL is now provided via fly secrets (Upstash connection string)
# Fallback for local development only
ENV REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# Fly.io injects PORT — fall back to 8080 for local runs (aligned with fly.toml)
ENV PORT=8080

# Health check (Fly.io uses this to decide if the instance is healthy)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/healthz')" || exit 1

EXPOSE 8080

# Start uvicorn with 2 workers for better concurrency
# If one worker is blocked by heavy operations, the other handles health checks
CMD exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 2
