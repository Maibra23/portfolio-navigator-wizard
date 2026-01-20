# Stop Development Environment Script
# Portfolio Navigator Wizard - Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping Development Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop Python processes (Backend)
Write-Host "Stopping Backend Server..." -ForegroundColor Yellow
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*uvicorn*" -or $_.CommandLine -like "*uvicorn*" }
if ($pythonProcs) {
    $pythonProcs | Stop-Process -Force
    Write-Host "  Backend stopped" -ForegroundColor Green
} else {
    # Fallback: stop all Python processes (be careful!)
    $allPython = Get-Process python -ErrorAction SilentlyContinue
    if ($allPython) {
        Write-Host "  Stopping Python processes..." -ForegroundColor Yellow
        $allPython | Stop-Process -Force
        Write-Host "  Python processes stopped" -ForegroundColor Green
    } else {
        Write-Host "  No Python processes found" -ForegroundColor Gray
    }
}

# Stop Node processes (Frontend)
Write-Host "Stopping Frontend Server..." -ForegroundColor Yellow
$nodeProcs = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcs) {
    $nodeProcs | Stop-Process -Force
    Write-Host "  Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "  No Node processes found" -ForegroundColor Gray
}

# Optionally stop Redis (commented out - usually keep running)
# Write-Host "Stopping Redis..." -ForegroundColor Yellow
# wsl sudo service redis-server stop 2>&1 | Out-Null
# Write-Host "  Redis stopped (optional)" -ForegroundColor Gray

Write-Host ""
Write-Host "Development environment stopped!" -ForegroundColor Green
Write-Host ""
