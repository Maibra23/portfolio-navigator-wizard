# Makefile for Portfolio Navigator Wizard

.PHONY: help dev dev-ticker backend frontend ticker-table prod-build prod-copy test-backend test-frontend full-dev status stop clean install fix-health open-ticker warm-cache

# Default target - show help
help:
	@echo "🚀 Portfolio Navigator Wizard - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "📋 Development Commands:"
	@echo "  make dev          - Start both backend and frontend (recommended)"
	@echo "  make dev-ticker   - Start backend + ticker table server"
	@echo "  make backend      - Start backend only on http://localhost:8000"
	@echo "  make frontend     - Start frontend only on http://localhost:8080"
	@echo "  make ticker-table - Start ticker table server on http://localhost:8080 (requires backend)"
	@echo "  make full-dev     - Start with full ticker list (slower startup)"
	@echo "  make fix-health   - Fix health endpoint error (restart backend)"
	@echo "  make open-ticker  - Open ticker table in browser"
	@echo "  make warm-cache   - Pre-warm Redis cache with all required data"
	@echo ""
	@echo "🔧 Setup Commands:"
	@echo "  make install      - Install all dependencies (backend + frontend)"
	@echo "  make clean        - Stop all servers and clean up"
	@echo ""
	@echo "📊 Status Commands:"
	@echo "  make status       - Check if servers are running"
	@echo "  make stop         - Stop all running servers"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-frontend- Run frontend tests"
	@echo "  make test-search   - Test search functionality"
	@echo ""
	@echo "🚀 Production Commands:"
	@echo "  make prod-build   - Build frontend for production"
	@echo "  make prod-copy    - Build and copy to backend/static"
	@echo ""
	@echo "🌐 Access URLs:"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Health Check: http://localhost:8000/health"

# Warm up the Redis cache with all required data
warm-cache:
	@echo "🔥 Warming up Redis cache..."
	@echo "This may take a few minutes for the first run"
	@cd backend && /usr/local/bin/python3.11 -c "from utils.enhanced_data_fetcher import enhanced_data_fetcher; \
		print('\n📊 Pre-Warm Cache Status:'); \
		pre_status = enhanced_data_fetcher.get_health_metrics(); \
		print(f'Redis Status: {pre_status[\"redis\"][\"status\"]}'); \
		print(f'Memory Used: {pre_status[\"redis\"].get(\"memory_used_mb\", \"N/A\")}'); \
		print(f'Cache Coverage: {pre_status[\"data\"].get(\"cache_coverage\", 0):.1f}%\n'); \
		\
		print('🔄 Warming cache...'); \
		warm_result = enhanced_data_fetcher.warm_required_cache(); \
		print(f'\n✅ Warm-up completed with {warm_result[\"success_count\"]} tickers\n'); \
		\
		print('📊 Post-Warm Cache Status:'); \
		post_status = enhanced_data_fetcher.get_health_metrics(); \
		print(f'Redis Status: {post_status[\"redis\"][\"status\"]}'); \
		print(f'Memory Used: {post_status[\"redis\"].get(\"memory_used_mb\", \"N/A\")}'); \
		print(f'Cache Coverage: {post_status[\"data\"].get(\"cache_coverage\", 0):.1f}%'); \
		print(f'Data Quality: {post_status[\"data\"].get(\"error_rate\", 0):.1f}% error rate'); \
		print(f'Time Frame: {warm_result[\"time_frame\"][\"start\"]} to {warm_result[\"time_frame\"][\"end\"]} ({warm_result[\"time_frame\"][\"months\"]} months)'); \
		print(f'Cache TTL: {post_status[\"performance\"][\"cache_ttl_days\"]} days\n'); \
		"

# Development: run both backend and frontend (recommended)
dev: warm-cache
	@echo "🚀 Starting Portfolio Navigator Wizard..."
	@echo "📊 Backend: http://localhost:8000"
	@echo "🌐 Frontend: http://localhost:8080"
	@echo "=================================================="
	cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev

# Development with ticker table instead of frontend
dev-ticker:
	@echo "🚀 Starting Portfolio Navigator Wizard (Ticker Table Mode)..."
	@echo "📊 Backend: http://localhost:8000"
	@echo "📊 Ticker Table: http://localhost:8080"
	@echo "=================================================="
	cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd backend && /usr/local/bin/python3.11 ticker_table_server.py

# Full development: run with all tickers and complete cache
full-dev: warm-cache
	@echo "🚀 Starting Portfolio Navigator Wizard (Full Mode)..."
	@echo "📊 Backend: http://localhost:8000 (with all tickers)"
	@echo "🌐 Frontend: http://localhost:8080"
	@echo "=================================================="
	@echo "🔄 Checking Redis status..."
	@cd backend && /usr/local/bin/python3.11 -c "from utils.enhanced_data_fetcher import enhanced_data_fetcher; \
		status = enhanced_data_fetcher.get_health_metrics(); \
		print(f'\nRedis Status: {status[\"redis\"][\"status\"]}'); \
		print(f'Cache Coverage: {status[\"data\"].get(\"cache_coverage\", 0):.1f}%\n')"
	@echo "🚀 Starting servers with full data mode..."
	cd backend && PYTHONPATH=/Users/Brook/Library/CloudStorage/OneDrive-Linnéuniversitetet/portfolio-navigator-wizard FAST_STARTUP=false /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev

# Backend only
backend:
	@echo "🚀 Starting Backend Server..."
	@echo "📊 Server: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Backend with full ticker list
backend-full:
	@echo "🚀 Starting Backend Server (Full Mode)..."
	@echo "📊 Server: http://localhost:8000 (with all tickers)"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	cd backend && FAST_STARTUP=false /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend only
frontend:
	@echo "🌐 Starting Frontend Server..."
	@echo "🌐 Server: http://localhost:8080"
	@echo "=================================================="
	cd frontend && npm run dev

# Ticker table server only
ticker-table:
	@echo "📊 Starting Ticker Table Server..."
	@echo "📊 Server: http://localhost:8080"
	@echo "📊 Requires main backend on http://localhost:8000"
	@echo "=================================================="
	cd backend && /usr/local/bin/python3.11 ticker_table_server.py

# Install all dependencies
install:
	@echo "📦 Installing Backend Dependencies..."
	cd backend && /usr/local/bin/python3.11 -m pip install -r requirements.txt
	@echo "📦 Installing Frontend Dependencies..."
	cd frontend && npm install
	@echo "✅ All dependencies installed!"

# Check status of servers
status:
	@echo "📊 Checking Server Status..."
	@echo "=================================================="
	@echo "Python Version:"
	@python3 --version 2>/dev/null || echo "  ❌ Python3 not found - please install Python 3.9+"
	@echo ""
	@echo "Backend (port 8000):"
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "  ✅ Running - $(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "healthy")"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Frontend (port 8080):"
	@if curl -s http://localhost:8080 > /dev/null 2>&1; then \
		echo "  ✅ Running"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Ticker Table (port 8080):"
	@if curl -s http://localhost:8080/health > /dev/null 2>&1; then \
		echo "  ✅ Running - $(curl -s http://localhost:8080/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "healthy")"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "=================================================="

# Stop all running servers
stop:
	@echo "🛑 Stopping all servers..."
	pkill -f uvicorn || true
	pkill -f "npm run dev" || true
	pkill -f "ticker_table_server.py" || true
	@echo "✅ All servers stopped!"

# Clean up and stop servers
clean: stop
	@echo "🧹 Cleaning up..."
	@echo "✅ Cleanup complete!"

# Production build: build frontend and copy to backend/static
prod-build:
	@echo "🏗️ Building Frontend for Production..."
	cd frontend && npm install && npm run build
	@echo "✅ Production build complete!"

prod-copy:
	@echo "🏗️ Building and Copying to Backend..."
	cd frontend && npm run build && cp -r dist ../backend/static
	@echo "✅ Production files copied to backend/static!"

# Backend tests
test-backend:
	@echo "🧪 Running Backend Tests..."
	cd backend && /usr/local/bin/python3.11 -m pytest

# Fix health endpoint (temporary workaround)
fix-health:
	@echo "🔧 Fixing health endpoint error..."
	@echo "This will restart the backend to clear the cached_count error"
	make stop
	sleep 2
	make backend

# Open ticker table in browser
open-ticker:
	@echo "🌐 Opening ticker table in browser..."
	@if curl -s http://localhost:8080/health > /dev/null 2>&1; then \
		open "http://localhost:8080"; \
		echo "✅ Ticker table opened in browser"; \
	else \
		echo "❌ Ticker table server not running. Start it with: make ticker-table"; \
	fi

# Frontend tests
test-frontend:
	@echo "🧪 Running Frontend Tests..."
	cd frontend && npm test

# Test search functionality
test-search:
	@echo "🧪 Testing Search Functionality..."
	/usr/local/bin/python3.11 test_search_fix.py 