# Portfolio Navigator Wizard - Backend
FROM python:3.11-slim

WORKDIR /app

# Install system deps if needed (e.g. for reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
ENV PORT=8000

# Health check via HTTP (uses PORT so Railway can probe correctly)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz')" || exit 1

# Use PORT so Railway (and any host that injects PORT) works when using this Dockerfile
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
