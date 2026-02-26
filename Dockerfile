# Portfolio Navigator Wizard — Fly.io Single-Container Deployment
# Bundles Redis + FastAPI backend in one image (no external Redis service needed).
#
# Usage:
#   fly deploy --remote-only       (no local Docker required)
#   docker build -t portfolio-wizard .   (local build)
#
# Environment variables required at runtime (set in fly.toml [env] or Fly secrets):
#   REDIS_URL=redis://localhost:6379   (already set below — matches bundled Redis)
#   ALLOWED_ORIGINS=https://yourdomain.com
#   ADMIN_API_KEY=<strong-random-key>
#   For email alerts: TTL_EMAIL_NOTIFICATIONS, TTL_NOTIFICATION_EMAIL, SMTP_USER, SMTP_PASSWORD
#   See backend/.env.example for full list

FROM python:3.11-slim

# Install Redis server (lightweight Alpine Redis on slim Debian base)
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
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

# Tell the app to connect to the bundled Redis on localhost
ENV REDIS_URL=redis://localhost:6379

# Fly.io injects PORT — fall back to 8000 for local runs
ENV PORT=8000

# Health check (Fly.io uses this to decide if the instance is healthy)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz')" || exit 1

EXPOSE 8000

# Start Redis as a background daemon, then hand PID 1 to uvicorn via exec.
# redis-server --daemonize yes returns only after Redis is accepting connections,
# so there is no race condition.
CMD redis-server --daemonize yes \
        --save "" \
        --appendonly no \
        --maxmemory 128mb \
        --maxmemory-policy allkeys-lru \
        --loglevel warning \
    && exec uvicorn main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8000}" \
        --workers 1
