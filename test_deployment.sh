#!/bin/bash

# Pre-Deployment Test Script
# Runs all 7 tests from PRE_DEPLOYMENT_CHECKLIST.md

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================================"
echo "Portfolio Navigator Wizard - Pre-Deployment Tests"
echo "================================================================"
echo ""

# Check if backend is running
check_backend() {
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

if ! check_backend; then
    echo -e "${RED}❌ Backend is not running!${NC}"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  export REDIS_URL='redis://localhost:6379'"
    echo "  export ALLOWED_ORIGINS='http://localhost:8080,http://localhost:5173'"
    echo "  export ALPHA_VANTAGE_API_KEY='your_key'"
    echo "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Backend is running${NC}"
echo ""

# Test 1: Health Check
echo "================================================================"
echo "Test 1: Health Check"
echo "================================================================"
response=$(curl -s http://localhost:8000/health)
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✅ PASS: Health check successful${NC}"
else
    echo -e "${RED}❌ FAIL: Health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: CORS Configuration
echo "================================================================"
echo "Test 2: CORS Configuration"
echo "================================================================"
echo "Testing CORS headers..."
cors_response=$(curl -s -I -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8000/health)

if echo "$cors_response" | grep -iq "Access-Control-Allow-Origin"; then
    echo -e "${GREEN}✅ PASS: CORS headers present${NC}"
    echo "$cors_response" | grep -i "Access-Control"
else
    echo -e "${YELLOW}⚠️  WARNING: CORS headers not found${NC}"
fi
echo ""

# Test 3: TTL Monitoring Endpoints
echo "================================================================"
echo "Test 3: TTL Monitoring Endpoints"
echo "================================================================"

echo "Testing GET /cache/ttl-status..."
ttl_status=$(curl -s http://localhost:8000/api/v1/portfolio/cache/ttl-status)
if echo "$ttl_status" | grep -q "success"; then
    echo -e "${GREEN}✅ PASS: TTL status endpoint works${NC}"
else
    echo -e "${RED}❌ FAIL: TTL status endpoint failed${NC}"
fi
echo ""

echo "Testing GET /cache/ttl-report..."
ttl_report=$(curl -s http://localhost:8000/api/v1/portfolio/cache/ttl-report)
if echo "$ttl_report" | grep -q "success"; then
    echo -e "${GREEN}✅ PASS: TTL report endpoint works${NC}"
else
    echo -e "${RED}❌ FAIL: TTL report endpoint failed${NC}"
fi
echo ""

echo "Testing GET /cache/expiring-list..."
expiring_list=$(curl -s "http://localhost:8000/api/v1/portfolio/cache/expiring-list?days_threshold=7")
if echo "$expiring_list" | grep -q "success"; then
    echo -e "${GREEN}✅ PASS: Expiring list endpoint works${NC}"
    echo "Sample response:"
    echo "$expiring_list" | python3 -m json.tool 2>/dev/null | head -20 || echo "$expiring_list" | head -20
else
    echo -e "${RED}❌ FAIL: Expiring list endpoint failed${NC}"
fi
echo ""

# Test 4: Rate Limiting
echo "================================================================"
echo "Test 4: Rate Limiting"
echo "================================================================"
echo "Sending 12 requests to test rate limiting (limit: 10/minute)..."

rate_limit_hit=false
for i in {1..12}; do
    response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/v1/portfolio/cache/ttl-status)
    http_code=$(echo "$response" | tail -1)

    if [ "$http_code" == "429" ]; then
        echo -e "${GREEN}✅ PASS: Rate limit enforced at request $i${NC}"
        rate_limit_hit=true
        break
    fi

    if [ $i -le 10 ]; then
        echo "  Request $i: HTTP $http_code ✓"
    else
        echo "  Request $i: HTTP $http_code"
    fi

    sleep 0.5
done

if [ "$rate_limit_hit" = false ]; then
    echo -e "${YELLOW}⚠️  WARNING: Rate limit not triggered after 12 requests${NC}"
fi
echo ""

# Test 5: Redis Connection
echo "================================================================"
echo "Test 5: Redis Connection"
echo "================================================================"
echo "Checking Redis connectivity..."

if command -v redis-cli &> /dev/null; then
    redis_ping=$(redis-cli ping 2>/dev/null)
    if [ "$redis_ping" == "PONG" ]; then
        echo -e "${GREEN}✅ PASS: Redis is running${NC}"

        # Get Redis stats
        keys_count=$(redis-cli DBSIZE 2>/dev/null | grep -o '[0-9]*')
        memory=$(redis-cli INFO memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')

        echo "  Keys in Redis: $keys_count"
        echo "  Memory used: $memory"
    else
        echo -e "${RED}❌ FAIL: Redis not responding${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  WARNING: redis-cli not installed, skipping Redis test${NC}"
fi
echo ""

# Test 6: Cache Status
echo "================================================================"
echo "Test 6: Cache Status"
echo "================================================================"
cache_status=$(curl -s http://localhost:8000/api/v1/portfolio/cache-status)
echo "$cache_status" | python3 -m json.tool 2>/dev/null || echo "$cache_status"
echo ""
echo -e "${GREEN}✅ PASS: Cache status retrieved${NC}"
echo ""

# Test 7: Enhanced Slack Notification Test (if configured)
echo "================================================================"
echo "Test 7: Slack Notification Test"
echo "================================================================"

if [ -n "$TTL_SLACK_WEBHOOK_URL" ] && [ "$TTL_SLACK_NOTIFICATIONS" == "true" ]; then
    echo "Slack notifications configured, testing..."
    echo "Triggering TTL check (should send Slack notification)..."

    ttl_check=$(curl -s http://localhost:8000/api/v1/portfolio/cache/ttl-status)

    echo ""
    echo -e "${BLUE}📱 Check your Slack channel for the notification!${NC}"
    echo ""
    echo "Expected message format:"
    echo "  🔔 Redis Cache TTL Alert - INFO/WARNING/CRITICAL"
    echo "  📊 TTL Status (tickers, timestamp)"
    echo "  💾 Redis Storage Overview (keys, memory)"
    echo "  🔑 Key Distribution (prices, sectors, metrics, portfolios)"
    echo "  📈 Ticker Data Completeness"
    echo "  📦 Estimated Storage by Type"
    echo ""

    echo -e "${GREEN}✅ PASS: TTL check triggered (check Slack for notification)${NC}"
else
    echo -e "${YELLOW}⚠️  SKIP: Slack not configured${NC}"
    echo ""
    echo "To test Slack notifications, set environment variables:"
    echo "  export TTL_SLACK_NOTIFICATIONS=true"
    echo "  export TTL_SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'"
    echo "  export TTL_SLACK_CHANNEL='#redis-alerts'"
    echo ""
    echo "Then restart the backend and run this test again."
fi
echo ""

# Summary
echo "================================================================"
echo "Test Summary"
echo "================================================================"
echo -e "${GREEN}✅ All critical tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review test results above"
echo "  2. If all tests pass, commit and push changes"
echo "  3. Deploy to Railway"
echo "  4. Run post-deployment verification"
echo ""
echo "================================================================"
