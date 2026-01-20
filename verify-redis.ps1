$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Redis Verification (Windows) - localhost:6379" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$repoRoot = Get-Location | Select-Object -ExpandProperty Path
$venvPython = Join-Path $repoRoot "backend\venv\Scripts\python.exe"

Write-Host "Repo: $repoRoot" -ForegroundColor Gray
Write-Host "Python: $venvPython" -ForegroundColor Gray

if (-not (Test-Path $venvPython)) {
    Write-Host "❌ backend venv python not found. Run: make install" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Checking TCP port 6379..." -ForegroundColor Yellow
$tcpOk = $false
try { $tcpOk = Test-NetConnection -ComputerName 127.0.0.1 -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue } catch { $tcpOk = $false }
if (-not $tcpOk) {
    Write-Host "❌ Nothing listening on 127.0.0.1:6379" -ForegroundColor Red
    Write-Host "Run: .\\start-redis.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Port open: 127.0.0.1:6379" -ForegroundColor Green

Write-Host ""
Write-Host "Pinging Redis via python..." -ForegroundColor Yellow
& $venvPython -X utf8 -c "import redis; r=redis.Redis(host='127.0.0.1',port=6379,socket_connect_timeout=2); print('PING:', r.ping()); print('DBSIZE:', r.dbsize())"

Write-Host ""
Write-Host "✅ Redis OK" -ForegroundColor Green

