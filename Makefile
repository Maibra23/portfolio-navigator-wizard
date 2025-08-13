# Makefile for Portfolio Navigator Wizard

.PHONY: help dev dev-ticker backend frontend ticker-table prod-build prod-copy test-backend test-frontend full-dev status stop clean install fix-health open-ticker warm-cache activate-ticker-table start-ticker-table check-redis quick-ticker-table enhanced enhanced-quick backend-enhanced enhanced-table test-enhanced demo-enhanced start-auto-refresh stop-auto-refresh enhanced-status

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
	@echo "  make ticker-table - Start ticker table server on http://localhost:8081 (requires backend)"
	@echo "  make full-dev     - Start with full ticker list (slower startup)"
	@echo "  make fix-health   - Fix health endpoint error (restart backend)"
	@echo "  make open-ticker  - Open ticker table in browser"
	@echo "  make warm-cache   - Pre-warm Redis cache with all required data"
	@echo "  make check-redis  - 🆕 Check Redis status and provide startup instructions"
	@echo "  make quick-ticker-table - 🆕 QUICK: Check Redis + start essential ticker table system"
	@echo "  make start-ticker-table - 🆕 ESSENTIAL: Warm cache + start backend + ticker table server"
	@echo "  make activate-ticker-table - 🆕 COMPLETE: Warm cache + start all servers for ticker table"
	@echo ""
	@echo "🚀 Enhanced Ticker Table Commands:"
	@echo "  make enhanced          - Start enhanced ticker table system"
	@echo "  make enhanced-quick    - 🚀 QUICK: Start enhanced system (no waiting)"
	@echo "  make backend-enhanced  - Start enhanced backend only (fastest)"
	@echo "  make enhanced-table    - Start enhanced table only"
	@echo "  make test-enhanced     - Test enhanced features"
	@echo "  make demo-enhanced     - Run enhanced features demo"
	@echo "  make start-auto-refresh- Start auto-refresh service"
	@echo "  make stop-auto-refresh - Stop auto-refresh service"
	@echo "  make enhanced-status   - Check enhanced system status"
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
	@echo "  Ticker Table: http://localhost:8081"
	@echo "  Enhanced Table: http://localhost:8000/api/portfolio/ticker-table/enhanced"

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
dev-ticker: warm-cache
	@echo "🚀 Starting Portfolio Navigator Wizard (Ticker Table Mode)..."
	@echo "📊 Backend: http://localhost:8000"
	@echo "📊 Ticker Table: http://localhost:8081"
	@echo "=================================================="
	@echo "🔄 Starting servers in background..."
	cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 & \
	echo "✅ Backend server started (PID: $$!)" && \
	sleep 3 && \
	cd backend && /usr/local/bin/python3.11 ticker_table_server.py > /dev/null 2>&1 & \
	echo "✅ Ticker table server started (PID: $$!)" && \
	echo "" && \
	echo "🎉 Both servers are now running in background!" && \
	echo "📊 Backend: http://localhost:8000" && \
	echo "📊 Ticker Table: http://localhost:8081" && \
	echo "💡 To stop: make stop" && \
	echo "💡 To check status: make status"

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

# Backend only (with cache warming)
backend: warm-cache
	@echo "🚀 Starting Backend Server..."
	@echo "📊 Server: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Backend with full ticker list (with cache warming)
backend-full: warm-cache
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
	@echo "📊 Server: http://localhost:8081"
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
	@echo "Ticker Table (port 8081):"
	@if curl -s http://localhost:8081/health > /dev/null 2>&1; then \
		echo "  ✅ Running - $(curl -s http://localhost:8081/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "healthy")"; \
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
	@if curl -s http://localhost:8081/health > /dev/null 2>&1; then \
		open "http://localhost:8081"; \
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

# 🆕 COMPLETE: Activate ticker table with cache warming and all necessary servers
activate-ticker-table:
	@echo "🚀 ACTIVATING COMPLETE TICKER TABLE SYSTEM..."
	@echo "=================================================="
	@echo "📋 This command will:"
	@echo "  1. 🔥 Warm up Redis cache with all required data"
	@echo "  2. 🖥️  Start main backend server (port 8000)"
	@echo "  3. 📊 Start ticker table server (port 8081)"
	@echo "  4. 🌐 Start frontend development server (port 8080)"
	@echo "  5. 🔍 Open ticker table in browser"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 1: Warming up Redis cache..."
	@make warm-cache
	@echo ""
	@echo "🔄 Step 2: Starting all servers in background..."
	@echo "📊 Starting main backend server on port 8000..."
	@cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
	@echo "✅ Backend server started (PID: $$!)"
	@sleep 3
	@echo "📊 Starting ticker table server on port 8081..."
	@cd backend && /usr/local/bin/python3.11 ticker_table_server.py > /dev/null 2>&1 &
	@echo "✅ Ticker table server started (PID: $$!)"
	@sleep 2
	@echo "🌐 Starting frontend development server on port 8080..."
	@cd frontend && npm run dev > /dev/null 2>&1 &
	@echo "✅ Frontend server started (PID: $$!)"
	@echo ""
	@echo "🔄 Step 3: Waiting for servers to be ready..."
	@echo "⏳ Waiting for backend server..."
	@until curl -s http://localhost:8000/health > /dev/null 2>&1; do sleep 1; done
	@echo "✅ Backend server ready!"
	@echo "⏳ Waiting for ticker table server..."
	@until curl -s http://localhost:8081/health > /dev/null 2>&1; do sleep 1; done
	@echo "✅ Ticker table server ready!"
	@echo "⏳ Waiting for frontend server..."
	@until curl -s http://localhost:8080 > /dev/null 2>&1; do sleep 1; done
	@echo "✅ Frontend server ready!"
	@echo ""
	@echo "🎉 ALL SERVERS ARE NOW RUNNING!"
	@echo "=================================================="
	@echo "📊 Main Backend: http://localhost:8000"
	@echo "📊 Ticker Table: http://localhost:8081"
	@echo "🌐 Frontend: http://localhost:8080"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 4: Opening ticker table in browser..."
	@sleep 2
	@open "http://localhost:8081"
	@echo "✅ Ticker table opened in browser!"
	@echo ""
	@echo "🎯 TICKER TABLE SYSTEM FULLY ACTIVATED!"
	@echo "=================================================="
	@echo "💡 To stop all servers: make stop"
	@echo "💡 To check status: make status"
	@echo "💡 To view logs: Check terminal output above"
	@echo "==================================================" 

# 🆕 ESSENTIAL: Start ticker table with cache warming and essential servers only
start-ticker-table:
	@echo "🚀 STARTING ESSENTIAL TICKER TABLE SYSTEM..."
	@echo "=================================================="
	@echo "📋 This command will:"
	@echo "  1. 🔥 Warm up Redis cache with all required data"
	@echo "  2. 🖥️  Start main backend server (port 8000)"
	@echo "  3. 📊 Start ticker table server (port 8081)"
	@echo "  4. 🔍 Open ticker table in browser"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 1: Warming up Redis cache..."
	@make warm-cache
	@echo ""
	@echo "🔄 Step 2: Starting essential servers in background..."
	@echo "📊 Starting main backend server on port 8000..."
	@cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
	@echo "✅ Backend server started (PID: $$!)"
	@sleep 3
	@echo "📊 Starting ticker table server on port 8081..."
	@cd backend && /usr/local/bin/python3.11 ticker_table_server.py > /dev/null 2>&1 &
	@echo "✅ Ticker table server started (PID: $$!)"
	@echo ""
	@echo "🔄 Step 3: Waiting for servers to be ready..."
	@echo "⏳ Waiting for backend server..."
	@until curl -s http://localhost:8000/health > /dev/null 2>&1; do sleep 1; done
	@echo "✅ Backend server ready!"
	@echo "⏳ Waiting for ticker table server..."
	@until curl -s http://localhost:8081/health > /dev/null 2>&1; do sleep 1; done
	@echo "✅ Ticker table server ready!"
	@echo ""
	@echo "🎉 ESSENTIAL SERVERS ARE NOW RUNNING!"
	@echo "=================================================="
	@echo "📊 Main Backend: http://localhost:8000"
	@echo "📊 Ticker Table: http://localhost:8081"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 4: Opening ticker table in browser..."
	@sleep 2
	@open "http://localhost:8081"
	@echo "✅ Ticker table opened in browser!"
	@echo ""
	@echo "🎯 TICKER TABLE SYSTEM READY!"
	@echo "=================================================="
	@echo "💡 To stop all servers: make stop"
	@echo "💡 To check status: make status"
	@echo "💡 To start frontend later: make frontend"
	@echo "==================================================" 

# 🆕 Check Redis status and provide startup instructions
check-redis:
	@echo "🔍 Checking Redis status..."
	@echo "=================================================="
	@if redis-cli ping > /dev/null 2>&1; then \
		echo "✅ Redis is running and accessible"; \
		echo "📊 Redis Info:"; \
		redis-cli info server | grep -E "(redis_version|uptime_in_seconds|connected_clients)" | sed 's/^/  /'; \
		echo ""; \
		echo "💡 Redis is ready for cache operations!"; \
	else \
		echo "❌ Redis is not running or not accessible"; \
		echo ""; \
		echo "🚀 To start Redis:"; \
		echo "  macOS (Homebrew): brew services start redis"; \
		echo "  macOS (Manual): redis-server /usr/local/etc/redis.conf"; \
		echo "  Linux: sudo systemctl start redis"; \
		echo "  Docker: docker run -d -p 6379:6379 redis:alpine"; \
		echo ""; \
		echo "💡 After starting Redis, run: make check-redis"; \
	fi
	@echo "==================================================" 

# 🆕 QUICK: Check Redis and start essential ticker table system
quick-ticker-table: check-redis
	@echo ""
	@echo "🚀 Starting ticker table system..."
	@make start-ticker-table

# 🚀 Enhanced Ticker Table Commands

# Start enhanced ticker table system (backend + enhanced table)
enhanced: warm-cache
	@echo "🚀 Starting Enhanced Ticker Table System..."
	@echo "=================================================="
	@echo "📋 This command will:"
	@echo "  1. 🔥 Warm up Redis cache with all required data"
	@echo "  2. 🖥️  Start main backend server (port 8000)"
	@echo "  3. 📊 Access enhanced ticker table via API"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 1: Warming up Redis cache..."
	@make warm-cache
	@echo ""
	@echo "🔄 Step 2: Starting backend server..."
	@echo "📊 Starting main backend server on port 8000..."
	@cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
	@echo "✅ Backend server started (PID: $$!)"
	@echo ""
	@echo "🔄 Step 3: Starting server (this may take a few seconds)..."
	@echo "⏳ Waiting for backend server to start..."
	@for i in {1..10}; do \
		if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend server ready!"; \
			break; \
		fi; \
		echo "  Attempt $$i/10..."; \
		sleep 2; \
	done
	@echo ""
	@echo "🎉 ENHANCED TICKER TABLE SYSTEM IS NOW RUNNING!"
	@echo "=================================================="
	@echo "📊 Main Backend: http://localhost:8000"
	@echo "📊 Enhanced Table: http://localhost:8000/api/portfolio/ticker-table/enhanced"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 4: Opening enhanced table in browser..."
	@sleep 2
	@open "http://localhost:8000/api/portfolio/ticker-table/enhanced"
	@echo "✅ Enhanced table opened in browser!"
	@echo ""
	@echo "🎯 ENHANCED SYSTEM READY!"
	@echo "=================================================="
	@echo "💡 To stop server: make stop"
	@echo "💡 To check status: make status"
	@echo "💡 To start auto-refresh: make start-auto-refresh"
	@echo "=================================================="

# Quick start enhanced system (no waiting)
enhanced-quick: warm-cache
	@echo "🚀 Quick Starting Enhanced Ticker Table System..."
	@echo "=================================================="
	@echo "📋 This command will:"
	@echo "  1. 🔥 Warm up Redis cache with all required data"
	@echo "  2. 🖥️  Start main backend server (port 8000)"
	@echo "  3. 📊 Open enhanced ticker table in browser"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Step 1: Warming up Redis cache..."
	@make warm-cache
	@echo ""
	@echo "🔄 Step 2: Starting backend server..."
	@echo "📊 Starting main backend server on port 8000..."
	@cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
	@echo "✅ Backend server started (PID: $$!)"
	@echo ""
	@echo "🔄 Step 3: Opening enhanced table in browser..."
	@echo "⏳ Waiting 5 seconds for server to initialize..."
	@sleep 5
	@open "http://localhost:8000/api/portfolio/ticker-table/enhanced"
	@echo "✅ Enhanced table opened in browser!"
	@echo ""
	@echo "🎯 ENHANCED SYSTEM STARTING!"
	@echo "=================================================="
	@echo "📊 Main Backend: http://localhost:8000"
	@echo "📊 Enhanced Table: http://localhost:8000/api/portfolio/ticker-table/enhanced"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	@echo "💡 To stop server: make stop"
	@echo "💡 To check status: make status"
	@echo "💡 To start auto-refresh: make start-auto-refresh"
	@echo "=================================================="

# Start enhanced table only (requires backend to be running)
enhanced-table:
	@echo "📊 Opening Enhanced Ticker Table..."
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		open "http://localhost:8000/api/portfolio/ticker-table/enhanced"; \
		echo "✅ Enhanced table opened in browser"; \
	else \
		echo "❌ Backend server not running. Start it with: make enhanced"; \
	fi

# Test enhanced features
test-enhanced:
	@echo "🧪 Testing Enhanced Features..."
	@echo "=================================================="
	@echo "Running auto-refresh service test..."
	@cd backend && /usr/local/bin/python3.11 -c "from utils.auto_refresh_service import AutoRefreshService; from utils.enhanced_data_fetcher import enhanced_data_fetcher; service = AutoRefreshService(enhanced_data_fetcher); print('✅ Auto-refresh service initialized successfully'); summary = service.get_tracking_summary(); print(f'📊 Tracking summary: {summary.get(\"total_tickers\", 0)} tickers'); print('✅ Enhanced features test completed!')"
	@echo "=================================================="
	@echo "✅ Enhanced features test completed!"

# Start auto-refresh service
start-auto-refresh:
	@echo "🔄 Starting Auto-Refresh Service..."
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		curl -X POST http://localhost:8000/api/portfolio/ticker-table/start-auto-refresh; \
		echo ""; \
		echo "✅ Auto-refresh service started!"; \
		echo "💡 Service will now monitor TTL and refresh data automatically"; \
	else \
		echo "❌ Backend server not running. Start it with: make enhanced"; \
	fi

# Stop auto-refresh service
stop-auto-refresh:
	@echo "🛑 Stopping Auto-Refresh Service..."
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		curl -X POST http://localhost:8000/api/portfolio/ticker-table/stop-auto-refresh; \
		echo ""; \
		echo "✅ Auto-refresh service stopped!"; \
	else \
		echo "❌ Backend server not running."; \
	fi

# Start backend only (for development)
backend-enhanced:
	@echo "🚀 Starting Enhanced Backend Server Only..."
	@echo "=================================================="
	@echo "📋 This command will:"
	@echo "  1. 🖥️  Start main backend server (port 8000)"
	@echo "  2. 📊 Ready for enhanced ticker table access"
	@echo "=================================================="
	@echo ""
	@echo "🔄 Starting backend server..."
	@echo "📊 Starting main backend server on port 8000..."
	@cd backend && /usr/local/bin/python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
	@echo "✅ Backend server started (PID: $$!)"
	@echo ""
	@echo "🎯 BACKEND SERVER STARTING!"
	@echo "=================================================="
	@echo "📊 Main Backend: http://localhost:8000"
	@echo "📊 Enhanced Table: http://localhost:8000/api/portfolio/ticker-table/enhanced"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	@echo "💡 To stop server: make stop"
	@echo "💡 To check status: make status"
	@echo "💡 To open enhanced table: make enhanced-table"
	@echo "=================================================="

# Check enhanced system status
enhanced-status:
	@echo "📊 Enhanced System Status..."
	@echo "=================================================="
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "✅ Backend server is running"; \
		echo ""; \
		echo "🔄 Auto-Refresh Service Status:"; \
		curl -s http://localhost:8000/api/portfolio/ticker-table/status | python3 -m json.tool 2>/dev/null || echo "  Service status unavailable"; \
		echo ""; \
		echo "📊 Data Quality Report:"; \
		curl -s http://localhost:8000/api/portfolio/ticker-table/data-quality-report | python3 -m json.tool 2>/dev/null || echo "  Quality report unavailable"; \
	else \
		echo "❌ Backend server not running"; \
		echo "💡 Start it with: make enhanced"; \
	fi
	@echo "==================================================" 