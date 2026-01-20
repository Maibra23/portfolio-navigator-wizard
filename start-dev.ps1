# Daily Development Startup Script
# Portfolio Navigator Wizard - Windows

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portfolio Navigator Wizard" -ForegroundColor Cyan
Write-Host "Starting Development Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Host "ERROR: Must run from project root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "Expected: portfolio-navigator-wizard" -ForegroundColor Yellow
    exit 1
}

# Step 1: Start Redis (Memurai)
Write-Host "[1/3] Starting Redis (Memurai)..." -ForegroundColor Yellow
try {
    $memuraiService = Get-Service -Name "Memurai" -ErrorAction SilentlyContinue
    if ($memuraiService -and $memuraiService.Status -eq "Running") {
        Write-Host "  Memurai already running" -ForegroundColor Green
        # Test connection
        try {
            python -c "import redis; r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2); r.ping()" 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Redis connection verified" -ForegroundColor Green
            }
        } catch {
            Write-Host "  WARNING: Redis connection test failed" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Starting Memurai service..." -ForegroundColor Yellow
        try {
            Start-Service -Name "Memurai" -ErrorAction Stop
            Start-Sleep -Seconds 3
            $memuraiService = Get-Service -Name "Memurai"
            if ($memuraiService.Status -eq "Running") {
                Write-Host "  Memurai started successfully" -ForegroundColor Green
            } else {
                Write-Host "  WARNING: Memurai service may need administrator privileges" -ForegroundColor Yellow
                Write-Host "  Please run: Start-Service -Name 'Memurai' (as administrator)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  WARNING: Could not start Memurai (may need admin privileges)" -ForegroundColor Yellow
            Write-Host "  Please start manually: Start-Service -Name 'Memurai' (as administrator)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  WARNING: Memurai service not found or not accessible" -ForegroundColor Yellow
    Write-Host "  Application will work with lazy loading if Redis is unavailable" -ForegroundColor Gray
}

# Step 2: Start Backend
Write-Host "[2/3] Starting Backend Server..." -ForegroundColor Yellow
if (-not (Test-Path "backend\venv\Scripts\python.exe")) {
    Write-Host "  ERROR: Backend virtual environment not found" -ForegroundColor Red
    Write-Host "  Run: cd backend && python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "  Backend will start on: http://localhost:8000" -ForegroundColor Gray
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  Starting in new window..." -ForegroundColor Gray

# Start backend in new PowerShell window
$backendScript = @"
cd '$PWD\backend'
.\venv\Scripts\Activate.ps1
Write-Host 'Backend Server Starting...' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

# Step 3: Start Frontend
Write-Host "[3/3] Starting Frontend Server..." -ForegroundColor Yellow
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "  ERROR: Frontend dependencies not installed" -ForegroundColor Red
    Write-Host "  Run: cd frontend && npm install" -ForegroundColor Yellow
    exit 1
}

Write-Host "  Frontend will start on: http://localhost:8080" -ForegroundColor Gray
Write-Host "  Starting in new window..." -ForegroundColor Gray

# Start frontend in new PowerShell window
$frontendScript = @"
cd '$PWD\frontend'
Write-Host 'Frontend Server Starting...' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Development Environment Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  Frontend:  http://localhost:8080" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health:    http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Two new PowerShell windows have opened:" -ForegroundColor Yellow
Write-Host "  - Backend server (port 8000)" -ForegroundColor Gray
Write-Host "  - Frontend server (port 8080)" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop servers:" -ForegroundColor Yellow
Write-Host "  - Press Ctrl+C in each window, OR" -ForegroundColor Gray
Write-Host "  - Run: .\stop-dev.ps1" -ForegroundColor Gray
Write-Host ""
