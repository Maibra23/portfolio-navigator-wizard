#!/bin/bash

echo "🚀 Portfolio Navigator Wizard - Full Implementation"
echo "=================================================="
echo "📊 This will implement the complete solution with:"
echo "   ✅ Full ticker list (600+ tickers)"
echo "   ✅ Enhanced search functionality"
echo "   ✅ Redis fallback support"
echo "   ✅ Case-insensitive search"
echo "=================================================="

# Make scripts executable
chmod +x test_full_implementation.py
chmod +x start_backend_full_tickers.sh

# Test the implementation
echo "Step 1: Testing the implementation..."
python3 test_full_implementation.py

echo ""
echo "Step 2: Starting backend with full ticker support..."
echo "=================================================="

# Start the backend server with full ticker support
./start_backend_full_tickers.sh 