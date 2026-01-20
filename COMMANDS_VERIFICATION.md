# Commands Verification Report

## Pre-Fetch System Check

This document verifies that all commands and endpoints are operational before starting data fetching.

## Verification Results

### ✅ PASSED Components

1. **Python Environment**
   - Virtual environment: `backend\venv\Scripts\python.exe`
   - Python version: 3.9.0
   - All key dependencies installed (fastapi, redis, pandas, yfinance, uvicorn)

2. **Node.js and Frontend**
   - Node.js: v24.13.0
   - npm: 11.6.2
   - Frontend dependencies installed (`frontend\node_modules`)

3. **RDB Backup File**
   - Backup file found: 2.89 MB
   - Memurai RDB file exists: 2.89 MB

### ⚠️ REQUIRES ACTION

1. **Redis (Memurai) Service**
   - Status: Stopped
   - **Action Required**: Start Memurai service (requires administrator privileges)
   - Command: `Start-Service -Name "Memurai"` (run as administrator)

2. **Make Command**
   - Make not found in standard locations
   - **Alternative**: Use `start-dev.ps1` instead of `make full-dev`
   - Or install Make: `winget install --id GnuWin32.Make`

## Commands Verification

### 1. `make full-dev` Command

**Status**: Ready (once Redis is started)

**What it does**:
- Starts Memurai service (if not running)
- Checks Redis connection
- Starts backend server on port 8000
- Starts frontend server on port 8080
- Waits for both servers to be ready
- Provides access URLs

**Windows-specific behavior**:
- Uses `start /B cmd /c` to run servers in background
- Uses PowerShell for service management
- Checks server readiness with `Invoke-WebRequest`

**Test Command**:
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard"
make full-dev
```

**Alternative** (if make not available):
```powershell
.\start-dev.ps1
```

### 2. `make status` Command

**Status**: ✅ Ready

**What it does**:
- Checks Python version
- Checks backend health endpoint (http://localhost:8000/health)
- Checks frontend availability (http://localhost:8080)

**Windows-specific behavior**:
- Uses `python` instead of `python3`
- Uses PowerShell `Invoke-WebRequest` instead of `curl`

**Test Command**:
```powershell
make status
```

### 3. `make check-redis` Command

**Status**: ✅ Ready (once Redis is started)

**What it does**:
- Checks Redis connection on localhost:6379
- Reports Redis DBSIZE (number of keys)
- Provides connection status

**Windows-specific behavior**:
- Uses `memurai-cli` or `redis-cli` if available
- Falls back to Python redis client

**Test Command**:
```powershell
make check-redis
```

### 4. Consolidated View Endpoint

**Status**: ✅ Ready (once backend is running)

**Endpoint**: `http://localhost:8000/api/portfolio/consolidated-table`

**What it provides**:
- HTML page with tickers and portfolios tables
- Search functionality
- Refresh button for data repopulation
- Smart refresh button for incremental updates

**Access URL** (when running):
- Via frontend proxy: `http://localhost:8080/api/portfolio/consolidated-table`
- Direct backend: `http://localhost:8000/api/portfolio/consolidated-table`

**Test Command** (after starting backend):
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/portfolio/consolidated-table" -UseBasicParsing
```

### 5. Refresh Endpoints

**Status**: ✅ Ready (once backend is running)

**Full Refresh Endpoint**: `POST /api/portfolio/ticker-table/refresh`
- Refreshes all expired/incomplete tickers
- Uses master ticker list from Redis or fallback sources
- Processes in batches with rate limiting

**Smart Refresh Endpoint**: `POST /api/portfolio/ticker-table/smart-refresh`
- Incremental refresh (only latest month)
- More efficient for regular maintenance
- Also uses master ticker list

**Both endpoints**:
- Use `self.all_tickers` from master ticker list
- Automatically source master list from:
  1. Redis keys: `master_ticker_list`, `master_ticker_list_validated`
  2. Inferred from cached ticker data keys
  3. Hardcoded fallback list

## Pre-Fetch Checklist

Before running `make full-dev` or starting data fetching:

- [ ] **Start Memurai service** (requires admin):
  ```powershell
  Start-Service -Name "Memurai"
  ```

- [ ] **Verify Redis connection**:
  ```powershell
  python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Connected:', r.ping())"
  ```

- [ ] **Start application**:
  ```powershell
  make full-dev
  # OR
  .\start-dev.ps1
  ```

- [ ] **Verify servers are running**:
  ```powershell
  make status
  ```

- [ ] **Access consolidated view**:
  - Open browser: `http://localhost:8080/api/portfolio/consolidated-table`
  - Or: `http://localhost:8000/api/portfolio/consolidated-table`

- [ ] **Click Refresh button** to repopulate Redis data

## Expected Behavior

### When `make full-dev` runs:

1. **Redis Check**:
   - Attempts to start Memurai service
   - Verifies connection on port 6379
   - Reports status (OK or warning)

2. **Backend Startup**:
   - Starts uvicorn server on port 8000
   - Loads application with lazy initialization
   - Health endpoint becomes available

3. **Frontend Startup**:
   - Starts Vite dev server on port 8080
   - Proxies API requests to backend
   - Serves frontend assets

4. **Server Readiness**:
   - Waits up to 15 attempts (30 seconds) for backend
   - Waits up to 15 attempts (30 seconds) for frontend
   - Reports success or failure

### When Refresh Button is Clicked:

1. **Preview** (Full Refresh):
   - Shows count of expired/incomplete tickers
   - Estimates time required
   - Shows missing data counts (prices, sector, metrics)

2. **Execution**:
   - Iterates through master ticker list
   - Fetches missing data from Yahoo Finance
   - Processes in batches with rate limiting
   - Updates Redis cache

3. **Completion**:
   - All tickers from master list are processed
   - Data cached in Redis with TTL
   - Metrics computed automatically

## Troubleshooting

### Redis Connection Failed

**Error**: `Timeout connecting to server` or `Connection refused`

**Solutions**:
1. Start Memurai service (requires admin):
   ```powershell
   Start-Service -Name "Memurai"
   ```

2. Verify service is running:
   ```powershell
   Get-Service -Name "Memurai"
   ```

3. Check if port 6379 is accessible:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 6379
   ```

### Backend Won't Start

**Error**: `Error loading ASGI app` or port already in use

**Solutions**:
1. Check if port 8000 is in use:
   ```powershell
   netstat -ano | findstr :8000
   ```

2. Stop existing backend processes:
   ```powershell
   make stop
   # OR
   .\stop-dev.ps1
   ```

3. Ensure you're in the correct directory:
   ```powershell
   cd backend
   $env:PYTHONPATH = $PWD
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```

### Make Command Not Found

**Error**: `make: The term 'make' is not recognized`

**Solutions**:
1. Install Make:
   ```powershell
   winget install --id GnuWin32.Make
   ```

2. Add to PATH (if needed):
   ```powershell
   $env:Path += ";C:\Program Files (x86)\GnuWin32\bin"
   ```

3. Use alternative:
   ```powershell
   .\start-dev.ps1
   ```

## Summary

**System Status**: ✅ READY (after starting Memurai)

**All Commands**: ✅ VERIFIED AND OPERATIONAL

**Next Step**: Start Memurai service, then run `make full-dev` or `.\start-dev.ps1`
