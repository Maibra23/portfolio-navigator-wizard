#!/usr/bin/env python3
"""
Test script to start the backend server and test Redis implementation
"""
import subprocess
import sys
import os
import time
import requests
import json

def start_backend():
    """Start the backend server"""
    print("🚀 Starting Portfolio Navigator Wizard Backend...")
    print("=" * 50)
    
    # Change to backend directory
    os.chdir('backend')
    
    # Start the server
    try:
        # Activate virtual environment and start server
        cmd = "source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        print("✅ Backend server started successfully!")
        print("📊 Server running on: http://localhost:8000")
        print("📚 API Documentation: http://localhost:8000/docs")
        print("=" * 50)
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None

def test_api_endpoints():
    """Test the API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Root endpoint
    print("\n2. Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Root endpoint: {data['message']} v{data['version']}")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
    
    # Test 3: Ticker search
    print("\n3. Testing ticker search...")
    test_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog"]
    
    for query in test_queries:
        try:
            response = requests.get(f"{base_url}/api/portfolio/ticker/search?q={query}&limit=5", timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"   ✅ Search '{query}': Found {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"      Tickers: {tickers}")
            else:
                print(f"   ❌ Search '{query}' failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Search '{query}' error: {e}")
    
    # Test 4: Cache status
    print("\n4. Testing cache status...")
    try:
        response = requests.get(f"{base_url}/api/portfolio/cache/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('system_status', {})
            print(f"   ✅ Cache status: {status.get('master_count', 0)} master tickers, {status.get('cached_count', 0)} cached")
            print(f"      Redis status: {status.get('redis_status', 'unknown')}")
        else:
            print(f"   ❌ Cache status failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache status error: {e}")

def main():
    """Main function"""
    print("🧪 Portfolio Navigator Wizard - Backend Test")
    print("=" * 50)
    
    # Start backend
    process = start_backend()
    
    if process:
        try:
            # Wait a bit more for server to fully start
            time.sleep(5)
            
            # Test endpoints
            test_api_endpoints()
            
            print("\n" + "=" * 50)
            print("✅ Backend testing completed!")
            print("🌐 Server is running on http://localhost:8000")
            print("📚 API docs available at http://localhost:8000/docs")
            print("🛑 Press Ctrl+C to stop the server")
            
            # Keep the server running
            process.wait()
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            process.terminate()
            process.wait()
            print("✅ Server stopped")
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            process.terminate()
    else:
        print("❌ Failed to start backend server")
        sys.exit(1)

if __name__ == "__main__":
    main() 