#!/bin/bash

echo "🚀 Starting Portfolio Navigator Wizard Backend..."
echo "=================================================="

# Change to backend directory
cd backend

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Start the server
echo "🌐 Starting uvicorn server..."
echo "📊 Server will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo "=================================================="

uvicorn main:app --reload --host 0.0.0.0 --port 8000 