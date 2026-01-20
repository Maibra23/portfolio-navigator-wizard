#!/usr/bin/env pwsh
# Comprehensive verification before starting data fetching

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Pre-Fetch Verification Report" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Test 1: Redis (Memurai) Service
Write-Host "1. Redis (Memurai) Service..." -ForegroundColor Yellow
$memuraiService = Get-Service -Name "Memurai" -ErrorAction SilentlyContinue
if ($memuraiService) {
    if ($memuraiService.Status -eq "Running") {
        Write-Host "   [PASS] Memurai service is running" -ForegroundColor Green
        try {
            $redisTest = python -c "import redis; r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2); print('PING:', r.ping()); print('KEYS:', r.dbsize())" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   [PASS] Redis connection successful" -ForegroundColor Green
                Write-Host "   $redisTest" -ForegroundColor Gray
            } else {
                Write-Host "   [FAIL] Redis connection failed" -ForegroundColor Red
                $allPassed = $false
            }
        } catch {
            Write-Host "   [FAIL] Redis test error: $_" -ForegroundColor Red
            $allPassed = $false
        }
    } else {
        Write-Host "   [FAIL] Memurai service is stopped" -ForegroundColor Red
        Write-Host "   [ACTION] Start Memurai with: Start-Service -Name 'Memurai' (requires admin)" -ForegroundColor Yellow
        $allPassed = $false
    }
} else {
    Write-Host "   [FAIL] Memurai service not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Test 2: Python Environment
Write-Host "2. Python Environment..." -ForegroundColor Yellow
if (Test-Path "backend\venv\Scripts\python.exe") {
    $venvPython = "backend\venv\Scripts\python.exe"
    $venvVersion = & $venvPython --version 2>&1
    Write-Host "   [PASS] Virtual environment exists: $venvVersion" -ForegroundColor Green
    
    # Test key imports
    $testImports = & $venvPython -c "import fastapi, redis, pandas, yfinance, uvicorn" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [PASS] All key dependencies available" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Missing dependencies" -ForegroundColor Red
        Write-Host "   $testImports" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "   [FAIL] Virtual environment not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Test 3: Node.js and Frontend
Write-Host "3. Node.js and Frontend..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "   [PASS] Node.js: $nodeVersion" -ForegroundColor Green
    Write-Host "   [PASS] npm: $npmVersion" -ForegroundColor Green
    
    if (Test-Path "frontend\node_modules") {
        Write-Host "   [PASS] Frontend dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Frontend node_modules not found" -ForegroundColor Red
        Write-Host "   [ACTION] Run: cd frontend && npm install" -ForegroundColor Yellow
        $allPassed = $false
    }
} catch {
    Write-Host "   [FAIL] Node.js or npm not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Test 4: Make Command
Write-Host "4. Make Command..." -ForegroundColor Yellow
$makePaths = @(
    "C:\Program Files (x86)\GnuWin32\bin\make.exe",
    "C:\Program Files\GnuWin32\bin\make.exe",
    "$env:ProgramFiles\GnuWin32\bin\make.exe"
)
$makeFound = $false
foreach ($path in $makePaths) {
    if (Test-Path $path) {
        Write-Host "   [PASS] Make found at: $path" -ForegroundColor Green
        $makeFound = $true
        break
    }
}
if (-not $makeFound) {
    Write-Host "   [WARN] Make not found in standard locations" -ForegroundColor Yellow
    Write-Host "   [INFO] You can use start-dev.ps1 instead of make full-dev" -ForegroundColor Gray
}
Write-Host ""

# Test 5: Backend Server (if running)
Write-Host "5. Backend Server Status..." -ForegroundColor Yellow
try {
    $backendHealth = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [PASS] Backend is running (Status: $($backendHealth.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   [INFO] Backend not running (will start with make full-dev)" -ForegroundColor Gray
}
Write-Host ""

# Test 6: Frontend Server (if running)
Write-Host "6. Frontend Server Status..." -ForegroundColor Yellow
try {
    $frontendCheck = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   [PASS] Frontend is running (Status: $($frontendCheck.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   [INFO] Frontend not running (will start with make full-dev)" -ForegroundColor Gray
}
Write-Host ""

# Test 7: Consolidated View Endpoint (if backend running)
Write-Host "7. Consolidated View Endpoint..." -ForegroundColor Yellow
try {
    $consolidatedView = Invoke-WebRequest -Uri "http://localhost:8000/api/portfolio/consolidated-table" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    if ($consolidatedView.StatusCode -eq 200) {
        Write-Host "   [PASS] Consolidated view endpoint accessible" -ForegroundColor Green
        Write-Host "   [INFO] URL: http://localhost:8080/api/portfolio/consolidated-table" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [INFO] Consolidated view not accessible (backend not running)" -ForegroundColor Gray
}
Write-Host ""

# Test 8: RDB Backup File
Write-Host "8. RDB Backup File..." -ForegroundColor Yellow
$rdbBackup = "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\redis-backup-20260117-181330.rdb"
$memuraiRdb = "C:\Program Files\Memurai\dump.rdb"
if (Test-Path $rdbBackup) {
    $sizeMB = [math]::Round((Get-Item $rdbBackup).Length / 1MB, 2)
    Write-Host "   [PASS] Backup file found: $sizeMB MB" -ForegroundColor Green
} else {
    Write-Host "   [WARN] Backup file not found at expected location" -ForegroundColor Yellow
}
if (Test-Path $memuraiRdb) {
    $sizeMB = [math]::Round((Get-Item $memuraiRdb).Length / 1MB, 2)
    Write-Host "   [INFO] Memurai RDB file exists: $sizeMB MB" -ForegroundColor Gray
}
Write-Host ""

# Final Summary
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Verification Summary" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

if ($allPassed) {
    Write-Host "[READY] All critical components are ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Ensure Redis (Memurai) is running:" -ForegroundColor White
    Write-Host "   Start-Service -Name 'Memurai' (requires admin)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Start the application:" -ForegroundColor White
    Write-Host "   make full-dev" -ForegroundColor Gray
    Write-Host "   OR" -ForegroundColor Gray
    Write-Host "   .\start-dev.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Access consolidated view:" -ForegroundColor White
    Write-Host "   http://localhost:8080/api/portfolio/consolidated-table" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Click 'Refresh' button to repopulate Redis data" -ForegroundColor White
} else {
    Write-Host "[NOT READY] Some components need attention" -ForegroundColor Red
    Write-Host ""
    Write-Host "Required Actions:" -ForegroundColor Yellow
    if (-not ($memuraiService -and $memuraiService.Status -eq "Running")) {
        Write-Host "- Start Memurai service (requires admin privileges)" -ForegroundColor Red
    }
    if (-not (Test-Path "backend\venv\Scripts\python.exe")) {
        Write-Host "- Set up Python virtual environment" -ForegroundColor Red
    }
    if (-not (Test-Path "frontend\node_modules")) {
        Write-Host "- Install frontend dependencies: cd frontend && npm install" -ForegroundColor Red
    }
}
Write-Host ""
