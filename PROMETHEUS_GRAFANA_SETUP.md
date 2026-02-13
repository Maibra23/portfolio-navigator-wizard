# Prometheus + Grafana Setup Guide
## Comprehensive Monitoring for Portfolio Navigator Wizard

**Last Updated:** February 12, 2026
**Target Environment:** Railway / Cloud Infrastructure
**Prometheus Version:** 2.45+
**Grafana Version:** 10.0+

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prometheus Setup](#prometheus-setup)
4. [Grafana Setup](#grafana-setup)
5. [Dashboard Configuration](#dashboard-configuration)
6. [Alert Rules](#alert-rules)
7. [How to Use](#how-to-use)
8. [Demo Walkthrough](#demo-walkthrough)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### What This Setup Provides

**Metrics Collection:**
- ✅ API request latency (P50, P95, P99)
- ✅ Request count by endpoint
- ✅ Error rates
- ✅ Redis memory usage
- ✅ Redis cache hit rate
- ✅ Redis connection pool usage
- ✅ Background job status

**Visualizations:**
- ✅ Real-time dashboards
- ✅ Historical trends
- ✅ Performance heatmaps
- ✅ System health overview

**Alerting:**
- ✅ High error rates
- ✅ Slow responses
- ✅ Redis memory pressure
- ✅ Low cache hit rates

### Current Implementation Status

✅ **Already Implemented:**
```python
# backend/main.py (lines 575-594)
- PrometheusMiddleware (request tracking)
- REQUEST_COUNT metric
- REQUEST_LATENCY metric
- /metrics endpoint exposed
```

⏭️ **To Be Added:**
- Redis-specific metrics
- Custom business metrics
- Grafana dashboards
- Alert rules

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│  (React App)    │
└────────┬────────┘
         │ HTTP requests
         ▼
┌─────────────────┐
│  FastAPI        │◄──── PrometheusMiddleware
│  Backend        │      (tracks requests)
└────────┬────────┘
         │
         ├─────► Redis ──────┐
         │                   │
         │                   ▼
         │            Metrics Collection
         │                   │
         ▼                   │
  ┌──────────────┐          │
  │  /metrics    │◄─────────┘
  │  endpoint    │
  └──────┬───────┘
         │ Scrape every 15s
         ▼
  ┌──────────────┐
  │  Prometheus  │
  │  (Storage &  │
  │   Queries)   │
  └──────┬───────┘
         │ Query
         ▼
  ┌──────────────┐
  │   Grafana    │
  │ (Dashboards) │
  └──────────────┘
```

---

## 📊 Prometheus Setup

### Option 1: Railway Deployment (Recommended)

**Step 1: Create Prometheus Service**

```bash
# Clone Prometheus Railway template
railway init

# Or manually create docker service
# See docker-compose.yml below
```

**Step 2: Create Configuration**

Create `prometheus.yml` in your project:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s  # Scrape metrics every 15 seconds
  evaluation_interval: 15s  # Evaluate alert rules every 15 seconds

# Alert manager configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets: []
          # - alertmanager:9093

# Load alert rules
rule_files:
  - "alert_rules.yml"

# Scrape configurations
scrape_configs:
  # Portfolio Navigator Backend
  - job_name: 'portfolio-backend'
    static_configs:
      - targets: ['backend:8000']  # Railway internal DNS
    metrics_path: '/metrics'
    scrape_interval: 15s

  # Redis Exporter (optional - for detailed Redis metrics)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

**Step 3: Create Alert Rules**

Create `alert_rules.yml`:

```yaml
# alert_rules.yml
groups:
  - name: portfolio_backend_alerts
    interval: 30s
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 2m
        labels:
          severity: critical
          component: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # Slow API Responses
      - alert: SlowAPIResponses
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: warning
          component: backend
        annotations:
          summary: "API responses are slow"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"

      # Redis Memory High
      - alert: RedisMemoryHigh
        expr: |
          redis_memory_used_bytes / redis_maxmemory_bytes > 0.80
        for: 5m
        labels:
          severity: warning
          component: redis
        annotations:
          summary: "Redis memory usage > 80%"
          description: "Current usage: {{ $value | humanizePercentage }}"

      # Redis Memory Critical
      - alert: RedisMemoryCritical
        expr: |
          redis_memory_used_bytes / redis_maxmemory_bytes > 0.90
        for: 2m
        labels:
          severity: critical
          component: redis
        annotations:
          summary: "Redis memory usage > 90%"
          description: "URGENT: Current usage: {{ $value | humanizePercentage }}"

      # Low Cache Hit Rate
      - alert: LowCacheHitRate
        expr: |
          redis_cache_hit_rate_percent < 90
        for: 10m
        labels:
          severity: warning
          component: redis
        annotations:
          summary: "Cache hit rate below 90%"
          description: "Current hit rate: {{ $value }}% (target: >95%)"

      # Redis Evicting Keys
      - alert: RedisEvictingKeys
        expr: |
          rate(redis_evicted_keys_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
          component: redis
        annotations:
          summary: "Redis is evicting keys!"
          description: "Memory limit too low. Increase maxmemory immediately."

      # Backend Service Down
      - alert: BackendDown
        expr: |
          up{job="portfolio-backend"} == 0
        for: 1m
        labels:
          severity: critical
          component: backend
        annotations:
          summary: "Backend service is down"
          description: "Portfolio Navigator backend is unreachable"
```

**Step 4: Deploy to Railway**

```bash
# Create Dockerfile for Prometheus
cat > Dockerfile.prometheus <<'EOF'
FROM prom/prometheus:v2.45.0

COPY prometheus.yml /etc/prometheus/
COPY alert_rules.yml /etc/prometheus/

EXPOSE 9090

CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles"]
EOF

# Deploy via Railway
railway up
```

---

### Option 2: Docker Compose (Local Development)

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.0.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis:6379
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

**Start locally:**
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## 📈 Grafana Setup

### Step 1: Deploy Grafana (Railway)

```bash
# Add Grafana service to Railway project
railway add

# Or use Docker
cat > Dockerfile.grafana <<'EOF'
FROM grafana/grafana:10.0.0

# Copy provisioning files
COPY grafana/dashboards /etc/grafana/provisioning/dashboards
COPY grafana/datasources /etc/grafana/provisioning/datasources

EXPOSE 3000
EOF
```

### Step 2: Configure Prometheus Data Source

Create `grafana/datasources/prometheus.yml`:

```yaml
# grafana/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      httpMethod: POST
      timeInterval: 15s
```

### Step 3: Create Dashboard Provisioning

Create `grafana/dashboards/dashboard.yml`:

```yaml
# grafana/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'Portfolio Navigator'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## 📊 Dashboard Configuration

### Main Dashboard: Portfolio Navigator Overview

Create `grafana/dashboards/portfolio-overview.json`:

```json
{
  "dashboard": {
    "title": "Portfolio Navigator - System Overview",
    "tags": ["portfolio", "backend", "redis"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (path)",
            "legendFormat": "{{path}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "P95 Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))",
            "legendFormat": "Error Rate"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Redis Memory Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "redis_memory_used_bytes / redis_maxmemory_bytes * 100",
            "legendFormat": "Memory %"
          }
        ],
        "thresholds": [
          {"value": 0, "color": "green"},
          {"value": 80, "color": "yellow"},
          {"value": 90, "color": "red"}
        ],
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 16}
      },
      {
        "id": 5,
        "title": "Cache Hit Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "redis_cache_hit_rate_percent",
            "legendFormat": "Hit Rate"
          }
        ],
        "thresholds": [
          {"value": 0, "color": "red"},
          {"value": 90, "color": "yellow"},
          {"value": 95, "color": "green"}
        ],
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 16}
      },
      {
        "id": 6,
        "title": "Redis Keys by Type",
        "type": "piechart",
        "targets": [
          {
            "expr": "redis_keys_by_type",
            "legendFormat": "{{key_type}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      }
    ]
  }
}
```

### Detailed Metrics List

**Panel 1: Request Rate**
- **Metric:** `sum(rate(http_requests_total[5m])) by (path)`
- **Description:** Requests per second by endpoint
- **Type:** Time series graph
- **Y-axis:** Requests/sec

**Panel 2: Response Latency**
- **Metrics:**
  - P95: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
  - P99: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
  - P50: `histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))`
- **Description:** API response time percentiles
- **Type:** Time series graph
- **Y-axis:** Seconds
- **Thresholds:** P95 > 1s (warning), P95 > 2s (critical)

**Panel 3: Error Rate**
- **Metric:** `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100`
- **Description:** Percentage of 5xx errors
- **Type:** Time series graph
- **Y-axis:** Percentage
- **Target:** < 1% (green), 1-5% (yellow), >5% (red)

**Panel 4: Redis Memory Usage**
- **Metric:** `redis_memory_used_bytes / redis_maxmemory_bytes * 100`
- **Description:** Redis memory utilization
- **Type:** Gauge
- **Unit:** Percentage
- **Thresholds:** <80% (green), 80-90% (yellow), >90% (red)

**Panel 5: Cache Hit Rate**
- **Metric:** `redis_cache_hit_rate_percent`
- **Description:** Percentage of cache hits
- **Type:** Gauge
- **Unit:** Percentage
- **Target:** >95% (green), 90-95% (yellow), <90% (red)

**Panel 6: Redis Keys by Type**
- **Metric:** `redis_keys_by_type`
- **Description:** Distribution of keys
- **Type:** Pie chart
- **Labels:** prices, sectors, metrics, portfolios, strategies, other

**Panel 7: Top Endpoints by Latency**
- **Metric:** `topk(10, avg(rate(http_request_duration_seconds_sum[5m])) by (path) / avg(rate(http_request_duration_seconds_count[5m])) by (path))`
- **Description:** Slowest endpoints
- **Type:** Table
- **Columns:** Endpoint, Avg Latency

**Panel 8: Request Status Codes**
- **Metric:** `sum(rate(http_requests_total[5m])) by (status)`
- **Description:** HTTP status code distribution
- **Type:** Stacked area chart
- **Labels:** 2xx (green), 4xx (yellow), 5xx (red)

**Panel 9: Redis Connection Pool**
- **Metric:** `redis_connected_clients`
- **Description:** Active Redis connections
- **Type:** Time series graph
- **Y-axis:** Connection count
- **Max:** 200 (4 workers × 50 per worker)

**Panel 10: Background Jobs Status**
- **Metric:** Custom (implement job_status metric)
- **Description:** TTL monitoring, portfolio generation status
- **Type:** Status list
- **States:** Running, Completed, Failed

---

## 🚨 Alert Rules

### Alert Configuration

Create `grafana/alerts/alert-rules.yml`:

```yaml
# grafana/alerts/alert-rules.yml
groups:
  - name: api_performance
    interval: 30s
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API latency is high"
          description: "P95 latency is {{ $value }}s (threshold: 1s)"
          runbook_url: "https://wiki.example.com/runbooks/high-latency"

      - alert: VeryHighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API latency is very high"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"
          runbook_url: "https://wiki.example.com/runbooks/high-latency"

  - name: redis_health
    interval: 30s
    rules:
      - alert: RedisMemoryWarning
        expr: (redis_memory_used_bytes / redis_maxmemory_bytes) > 0.80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage > 80%"
          description: "{{ $value | humanizePercentage }} memory used"

      - alert: RedisCacheHitRateLow
        expr: redis_cache_hit_rate_percent < 90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 90%"
          description: "Current: {{ $value }}%, Target: >95%"
```

### Notification Channels

**Slack Integration:**

1. Create Slack webhook:
   - Go to https://api.slack.com/messaging/webhooks
   - Create new webhook for your workspace
   - Copy webhook URL

2. Configure in Grafana:
   - Go to Alerting → Notification channels
   - Click "New channel"
   - Type: Slack
   - Webhook URL: Paste your webhook
   - Channel: #alerts or #redis-alerts

**Email Integration:**

```yaml
# grafana.ini (or environment variables)
[smtp]
enabled = true
host = smtp.gmail.com:587
user = your-email@gmail.com
password = your-app-password
from_address = grafana@yourdomain.com
from_name = Grafana Alerts

[alerting]
enabled = true
execute_alerts = true
```

---

## 🎮 How to Use

### Accessing Dashboards

**Railway Deployment:**
```
1. Go to Railway Dashboard → Grafana service
2. Click "Open" or copy URL
3. Login with admin credentials
4. Navigate to Dashboards → Portfolio Navigator
```

**Local Development:**
```
1. Open http://localhost:3000
2. Login: admin / admin
3. Dashboards → Portfolio Navigator → System Overview
```

### Common Workflows

#### Check API Performance

1. Open "Portfolio Navigator - System Overview" dashboard
2. Look at "Request Rate" panel → See traffic patterns
3. Check "P95 Latency" panel → Identify slow endpoints
4. Review "Error Rate" panel → Spot issues

#### Monitor Redis Health

1. Go to "Redis Metrics" dashboard
2. Check "Memory Usage" gauge → Should be <80%
3. Review "Cache Hit Rate" gauge → Should be >95%
4. Look at "Keys by Type" pie chart → Understand data distribution

#### Investigate Slow Responses

1. Open "API Performance" dashboard
2. Find "Top Endpoints by Latency" table
3. Identify slow endpoint (e.g., /optimization/triple)
4. Click endpoint name → Drill down to specific metrics
5. Check "Command Latency" heatmap → See Redis impact

#### Respond to Alerts

1. Receive Slack notification: "High Error Rate"
2. Click alert link → Opens Grafana
3. Review dashboard at alert time
4. Check logs via Railway Dashboard
5. Follow runbook (if configured)

---

## 🎬 Demo Walkthrough

### Demo 1: Real-Time Monitoring

**Scenario:** Monitor system during portfolio generation spike

**Steps:**

1. **Start monitoring:**
   ```bash
   # Open Grafana
   open http://localhost:3000

   # Navigate to System Overview dashboard
   ```

2. **Generate load:**
   ```bash
   # Trigger 100 portfolio optimizations
   for i in {1..100}; do
     curl -X POST http://localhost:8000/api/v1/portfolio/optimization/triple \
       -H "Content-Type: application/json" \
       -d '{"tickers":["AAPL","GOOGL"],"weights":{"AAPL":0.5,"GOOGL":0.5}}'
   done
   ```

3. **Observe metrics:**
   - Request Rate spikes to ~100 req/min
   - P95 Latency increases to ~1.5s
   - Redis Memory usage rises by ~5 MB
   - Cache Hit Rate remains >95%

4. **Screenshot opportunity:** Capture dashboard showing spike

---

### Demo 2: Alert Testing

**Scenario:** Trigger and resolve a memory alert

**Steps:**

1. **Simulate memory pressure:**
   ```bash
   # Fill Redis with test data
   for i in {1..10000}; do
     redis-cli SET "test_key_$i" "$(dd if=/dev/urandom bs=1024 count=10 2>/dev/null)"
   done
   ```

2. **Watch alert fire:**
   - Grafana shows "RedisMemoryWarning" alert
   - Slack channel receives notification
   - Dashboard panel turns yellow/red

3. **Resolve issue:**
   ```bash
   # Clear test data
   redis-cli --scan --pattern "test_key_*" | xargs redis-cli DEL
   ```

4. **Verify resolution:**
   - Memory usage drops below 80%
   - Alert resolves automatically
   - Slack receives "resolved" notification

---

### Demo 3: Performance Investigation

**Scenario:** Identify slow API endpoint

**Steps:**

1. **Detect slowness:**
   - Dashboard shows P95 latency > 2s
   - Alert fires: "VeryHighLatency"

2. **Drill down:**
   - Click "Top Endpoints by Latency" table
   - Identify culprit: `/api/v1/portfolio/optimization/triple` (3.5s avg)

3. **Analyze:**
   - Check Redis hit rate for this endpoint → 45% (low!)
   - Review Redis "Command Latency" → Many cache misses
   - Check backend logs → Yahoo Finance API timeouts

4. **Fix:**
   - Increase cache TTL for price data
   - Pre-warm cache for popular tickers
   - Verify: Latency drops to <1s, hit rate >95%

---

## 🔧 Troubleshooting

### Issue 1: Prometheus Not Scraping Metrics

**Symptoms:**
- Dashboards show "No data"
- Prometheus targets page shows backend as "DOWN"

**Solution:**
```bash
# Check /metrics endpoint is accessible
curl http://localhost:8000/metrics

# Expected output:
# http_requests_total{method="GET",path="/api/v1/portfolio"} 123
# http_request_duration_seconds_bucket{...} 0.045

# If not working, verify PrometheusMiddleware is enabled in main.py

# Check Prometheus config
docker exec prometheus cat /etc/prometheus/prometheus.yml

# Restart Prometheus
docker restart prometheus
```

---

### Issue 2: Grafana Can't Connect to Prometheus

**Symptoms:**
- Datasource test fails
- Error: "Bad Gateway" or "Connection refused"

**Solution:**
```bash
# Check Prometheus is running
docker ps | grep prometheus

# Check Prometheus URL in Grafana
# Should be: http://prometheus:9090 (Docker network)
# NOT: http://localhost:9090

# Test connectivity from Grafana container
docker exec grafana wget -O- http://prometheus:9090/api/v1/status/config

# Fix datasource URL in Grafana UI:
# Configuration → Data Sources → Prometheus → URL
```

---

### Issue 3: Alerts Not Firing

**Symptoms:**
- Memory >90% but no alert
- Grafana Alerting page shows "No alerts"

**Solution:**
```bash
# Verify alert rules loaded in Prometheus
open http://localhost:9090/alerts

# Check alert evaluation
# Should see rules listed with state: pending/firing/inactive

# Verify Grafana notification channel configured
# Alerting → Notification channels → Test

# Check Grafana logs
docker logs grafana | grep -i alert
```

---

### Issue 4: Missing Redis Metrics

**Symptoms:**
- Redis panels show "No data"
- `redis_memory_used_bytes` metric not found

**Solution:**
```bash
# Verify redis_metrics.py is collecting
# Check backend logs for "Redis metrics collection started"

# Manually trigger collection
curl http://localhost:8000/api/v1/admin/collect-metrics

# Verify metrics appear in /metrics endpoint
curl http://localhost:8000/metrics | grep redis

# If missing, ensure redis_metrics_task started in main.py lifespan
```

---

## ✅ Setup Checklist

**Before Production:**

### Prometheus
- [ ] Prometheus deployed (Railway or Docker)
- [ ] `prometheus.yml` configured
- [ ] `alert_rules.yml` created
- [ ] Backend `/metrics` endpoint accessible
- [ ] Scraping working (Prometheus UI shows target UP)

### Grafana
- [ ] Grafana deployed
- [ ] Prometheus datasource configured
- [ ] Dashboards imported
- [ ] Notification channels configured (Slack/Email)
- [ ] Test alerts sent successfully

### Backend
- [ ] PrometheusMiddleware enabled (✅ done)
- [ ] Redis metrics collection started
- [ ] Custom business metrics added (optional)
- [ ] `/metrics` endpoint exposed (✅ done)

### Alerts
- [ ] Alert rules validated
- [ ] Notification channels tested
- [ ] Runbooks created (optional)
- [ ] Team trained on alert response

---

## 📚 Quick Reference

### Prometheus Queries (PromQL)

```promql
# Request rate (last 5 min)
sum(rate(http_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate (%)
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Redis memory usage (%)
redis_memory_used_bytes / redis_maxmemory_bytes * 100

# Cache hit rate (%)
(
  sum(rate(redis_cache_hits_total[5m])) /
  (sum(rate(redis_cache_hits_total[5m])) + sum(rate(redis_cache_misses_total[5m])))
) * 100

# Top 10 slowest endpoints
topk(10, avg(rate(http_request_duration_seconds_sum[5m])) by (path))
```

### Grafana Shortcuts

- `Ctrl+K` → Open search
- `Ctrl+S` → Save dashboard
- `Ctrl+H` → Hide/show controls
- `v` → Toggle variable dropdown
- `d` → Open dashboard settings
- `e` → Edit panel
- `Escape` → Exit edit mode

### Useful Links

- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000
- Backend metrics: http://localhost:8000/metrics

---

## 🚀 Next Steps

1. ✅ Set up Prometheus (this guide)
2. ✅ Set up Grafana (this guide)
3. ⏭️ Import dashboards
4. ⏭️ Configure alerts
5. ⏭️ Test monitoring
6. ⏭️ Train team on usage
7. ⏭️ Deploy to production

**Related Docs:**
- [Redis Configuration Guide](./REDIS_CONFIGURATION_GUIDE.md)
- [Supabase Integration](./SUPABASE_INTEGRATION_PLAN.md)

---

**Questions?** Review [Troubleshooting](#troubleshooting) or check Prometheus/Grafana docs.
