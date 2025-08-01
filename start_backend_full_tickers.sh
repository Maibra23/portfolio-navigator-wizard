#!/bin/bash

echo "🚀 Starting Portfolio Navigator Wizard Backend (Full Ticker Mode)..."
echo "=================================================="
echo "📊 This will fetch ALL tickers from Wikipedia (600+ tickers)"
echo "⏱️  Startup may take longer but you'll get the complete ticker list"
echo "🔍 Search functionality will work with all available stocks"
echo "=================================================="

# Change to backend directory
cd backend

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Start the server with full ticker list (FAST_STARTUP=false)
echo "🌐 Starting uvicorn server with FAST_STARTUP=false..."
echo "📊 Server will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo "=================================================="

FAST_STARTUP=false uvicorn main:app --reload --host 0.0.0.0 --port 8000 