# Makefile for Portfolio Navigator Wizard

.PHONY: help dev backend frontend prod-build prod-copy test-backend test-frontend full-dev status stop clean install

# Default target - show help
help:
	@echo "🚀 Portfolio Navigator Wizard - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "📋 Development Commands:"
	@echo "  make dev          - Start both backend and frontend (recommended)"
	@echo "  make backend      - Start backend only on http://localhost:8000"
	@echo "  make frontend     - Start frontend only on http://localhost:8080"
	@echo "  make full-dev     - Start with full ticker list (slower startup)"
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

# Development: run both backend and frontend (recommended)
dev:
	@echo "🚀 Starting Portfolio Navigator Wizard..."
	@echo "📊 Backend: http://localhost:8000"
	@echo "🌐 Frontend: http://localhost:8080"
	@echo "=================================================="
	cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev

# Full development: run with all tickers (no fast startup)
full-dev:
	@echo "🚀 Starting Portfolio Navigator Wizard (Full Mode)..."
	@echo "📊 Backend: http://localhost:8000 (with all tickers)"
	@echo "🌐 Frontend: http://localhost:8080"
	@echo "=================================================="
	cd backend && FAST_STARTUP=false source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev

# Backend only
backend:
	@echo "🚀 Starting Backend Server..."
	@echo "📊 Server: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Backend with full ticker list
backend-full:
	@echo "🚀 Starting Backend Server (Full Mode)..."
	@echo "📊 Server: http://localhost:8000 (with all tickers)"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "=================================================="
	cd backend && FAST_STARTUP=false source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend only
frontend:
	@echo "🌐 Starting Frontend Server..."
	@echo "🌐 Server: http://localhost:8080"
	@echo "=================================================="
	cd frontend && npm run dev

# Install all dependencies
install:
	@echo "📦 Installing Backend Dependencies..."
	cd backend && source venv/bin/activate && pip install -r requirements.txt
	@echo "📦 Installing Frontend Dependencies..."
	cd frontend && npm install
	@echo "✅ All dependencies installed!"

# Check status of servers
status:
	@echo "📊 Checking Server Status..."
	@echo "=================================================="
	@echo "Backend (port 8000):"
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "  ✅ Running - $(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Frontend (port 8080):"
	@if curl -s http://localhost:8080 > /dev/null 2>&1; then \
		echo "  ✅ Running"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "=================================================="

# Stop all running servers
stop:
	@echo "🛑 Stopping all servers..."
	pkill -f uvicorn || true
	pkill -f "npm run dev" || true
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
	cd backend && source venv/bin/activate && pytest

# Frontend tests
test-frontend:
	@echo "🧪 Running Frontend Tests..."
	cd frontend && npm test

# Test search functionality
test-search:
	@echo "🧪 Testing Search Functionality..."
	python3 test_search_fix.py 