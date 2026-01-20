$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Redis Startup (Windows) - Memurai" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

function Test-RedisPort {
    try {
        return (Test-NetConnection -ComputerName 127.0.0.1 -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue)
    } catch {
        return $false
    }
}

if (Test-RedisPort) {
    Write-Host "✅ Redis already listening on 127.0.0.1:6379" -ForegroundColor Green
    exit 0
}

Write-Host "Redis not listening on 127.0.0.1:6379. Attempting to start Memurai..." -ForegroundColor Yellow

# 1) Try to start Memurai service (requires admin in many setups)
try {
    $svc = Get-Service -Name "Memurai" -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -ne "Running") {
            Write-Host "Trying Start-Service Memurai (may require Admin)..." -ForegroundColor Yellow
            Start-Service -Name "Memurai" -ErrorAction Stop
            Start-Sleep -Seconds 2
        }
    }
} catch {
    Write-Host "Start-Service failed (likely needs Admin). Falling back to starting Memurai as a user process..." -ForegroundColor Yellow
}

if (-not (Test-RedisPort)) {
    # 2) Fallback: start Memurai as a user process using its config file
    $exe  = "C:\Program Files\Memurai\memurai.exe"
    $conf = "C:\Program Files\Memurai\memurai.conf"

    if (-not (Test-Path $exe)) {
        Write-Host "❌ Memurai executable not found: $exe" -ForegroundColor Red
        Write-Host "Install Memurai Developer via: winget install --id Memurai.MemuraiDeveloper" -ForegroundColor Yellow
        exit 1
    }
    if (-not (Test-Path $conf)) {
        Write-Host "❌ Memurai config not found: $conf" -ForegroundColor Red
        exit 1
    }

    # Important: memurai needs the config path quoted because it contains spaces
    $arg = '"' + $conf + '"'
    Start-Process -FilePath $exe -ArgumentList $arg -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
}

# Wait for port
$ready = $false
for ($i = 1; $i -le 15; $i++) {
    if (Test-RedisPort) { $ready = $true; break }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host "❌ Redis still not reachable on 127.0.0.1:6379" -ForegroundColor Red
    Write-Host "Next checks:" -ForegroundColor Yellow
    Write-Host "  - Is port 6379 blocked by firewall?" -ForegroundColor Yellow
    Write-Host "  - Is another process using 6379?" -ForegroundColor Yellow
    Write-Host "  - Try running PowerShell as Admin and: Start-Service Memurai" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Redis is now listening on 127.0.0.1:6379" -ForegroundColor Green

# Optional: disable RDB snapshots and use AOF (avoids relying on any dump.rdb file)
# If this fails due to permissions, Redis will still work; it just won't change persistence mode.
try {
    $repoRoot = Get-Location | Select-Object -ExpandProperty Path
    $venvPython = Join-Path $repoRoot "backend\venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        & $venvPython -c "import redis; r=redis.Redis(host='127.0.0.1',port=6379); r.config_set('save',''); r.config_set('appendonly','yes'); r.config_set('appendfsync','everysec'); print('✅ Redis persistence set: AOF enabled, RDB snapshots disabled')" 2>$null | Out-Null
    }
} catch {
    # ignore; connectivity is the main goal
}

exit 0

