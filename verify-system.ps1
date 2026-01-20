# System Verification Script
# Portfolio Navigator Wizard - Windows Setup Verification

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portfolio Navigator Wizard" -ForegroundColor Cyan
Write-Host "System Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Check Node.js
Write-Host "Checking Node.js..." -NoNewline
try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  Version: $nodeVersion" -ForegroundColor Gray
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL (not found)" -ForegroundColor Red
    $allPassed = $false
}

# Check npm
Write-Host "Checking npm..." -NoNewline
try {
    $npmVersion = npm --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  Version: $npmVersion" -ForegroundColor Gray
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL (not found)" -ForegroundColor Red
    $allPassed = $false
}

# Check Python
Write-Host "Checking Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  Version: $pythonVersion" -ForegroundColor Gray
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL (not found)" -ForegroundColor Red
    $allPassed = $false
}

# Check Git
Write-Host "Checking Git..." -NoNewline
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  Version: $gitVersion" -ForegroundColor Gray
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL (not found)" -ForegroundColor Red
    $allPassed = $false
}

# Check WSL2
Write-Host "Checking WSL2..." -NoNewline
try {
    $wslStatus = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0 -and $wslStatus -match "Default Version: 2") {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " NOT READY" -ForegroundColor Yellow
        Write-Host "  WSL2 requires installation and restart" -ForegroundColor Gray
    }
} catch {
    Write-Host " NOT INSTALLED" -ForegroundColor Yellow
}

# Check Redis
Write-Host "Checking Redis..." -NoNewline
try {
    $redisPing = wsl redis-cli ping 2>&1
    if ($redisPing -match "PONG") {
        Write-Host " PASS" -ForegroundColor Green
        $dbSize = wsl redis-cli DBSIZE 2>&1
        Write-Host "  Keys in database: $dbSize" -ForegroundColor Gray
    } else {
        Write-Host " NOT RUNNING" -ForegroundColor Yellow
        Write-Host "  Start with: wsl sudo service redis-server start" -ForegroundColor Gray
    }
} catch {
    Write-Host " NOT AVAILABLE" -ForegroundColor Yellow
    Write-Host "  Requires WSL2 and Redis installation" -ForegroundColor Gray
}

# Check Backend Virtual Environment
Write-Host "Checking Backend venv..." -NoNewline
if (Test-Path "backend\venv") {
    Write-Host " PASS" -ForegroundColor Green
    if (Test-Path "backend\venv\Scripts\python.exe") {
        Write-Host "  Virtual environment exists" -ForegroundColor Gray
    }
} else {
    Write-Host " NOT FOUND" -ForegroundColor Red
    $allPassed = $false
}

# Check Frontend Dependencies
Write-Host "Checking Frontend dependencies..." -NoNewline
if (Test-Path "frontend\node_modules") {
    Write-Host " PASS" -ForegroundColor Green
    $packageCount = (Get-ChildItem "frontend\node_modules" -Directory).Count
    Write-Host "  Installed packages: $packageCount" -ForegroundColor Gray
} else {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host "  Run: cd frontend && npm install" -ForegroundColor Gray
    $allPassed = $false
}

# Check Backend Dependencies
Write-Host "Checking Backend dependencies..." -NoNewline
if (Test-Path "backend\venv\Scripts\python.exe") {
    $backendPython = "backend\venv\Scripts\python.exe"
    $fastapiCheck = & $backendPython -c "import fastapi; print('OK')" 2>&1
    if ($fastapiCheck -match "OK") {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " INCOMPLETE" -ForegroundColor Yellow
        Write-Host "  Run: cd backend && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt" -ForegroundColor Gray
    }
} else {
    Write-Host " CANNOT CHECK" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "Core System: READY" -ForegroundColor Green
} else {
    Write-Host "Core System: NOT READY" -ForegroundColor Red
    Write-Host "  Fix issues above before proceeding" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
