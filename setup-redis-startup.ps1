$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Setup Redis Auto-Start (Windows) - Scheduled Task" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$repoRoot = Get-Location | Select-Object -ExpandProperty Path
$scriptPath = Join-Path $repoRoot "start-redis.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ start-redis.ps1 not found in repo root: $scriptPath" -ForegroundColor Red
    exit 1
}

$taskName = "PortfolioNavigatorWizard-StartRedis"

# Create a per-user logon task (does NOT require admin)
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

Write-Host "Creating/Updating scheduled task: $taskName" -ForegroundColor Yellow
Write-Host "Action: $action" -ForegroundColor Gray

schtasks.exe /Create /F /SC ONLOGON /TN $taskName /TR $action | Out-Null

Write-Host "✅ Scheduled task created/updated." -ForegroundColor Green
Write-Host "It will run at next logon and ensure Redis is listening on localhost:6379." -ForegroundColor Green

Write-Host ""
Write-Host "Test now:" -ForegroundColor Yellow
Write-Host "  .\\start-redis.ps1" -ForegroundColor White
Write-Host "  .\\verify-redis.ps1" -ForegroundColor White

