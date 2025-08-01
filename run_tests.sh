#!/bin/bash

echo "🧪 Portfolio Navigator Wizard - Step 5 Implementation"
echo "======================================================"

# Make scripts executable
chmod +x test_redis.py
chmod +x start_backend.sh

# Test Redis and data fetcher
echo "Step 1: Testing Redis connection and data fetcher..."
python3 test_redis.py

echo ""
echo "Step 2: Starting backend server..."
echo "======================================================"

# Start the backend server
./start_backend.sh 