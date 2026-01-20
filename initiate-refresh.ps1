# One-Time Script to Initiate Ticker Data Refresh
# This script triggers the refresh endpoint to repopulate Redis with ticker data

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Initiating Ticker Data Refresh" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard"
$backendUrl = "http://localhost:8000"

# Step 1: Check if Redis is running
Write-Host "STEP 1: Checking Redis..." -ForegroundColor Yellow
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($redisTest) {
        Write-Host "✅ Redis is running on port 6379" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis is not running. Starting Redis..." -ForegroundColor Red
        $startRedisScript = Join-Path $rootDir "start-redis.ps1"
        if (Test-Path $startRedisScript) {
            & $startRedisScript
            Start-Sleep -Seconds 3
            $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue
            if (-not $redisTest) {
                Write-Host "❌ Failed to start Redis. Please start it manually." -ForegroundColor Red
                exit 1
            }
            Write-Host "✅ Redis started successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ start-redis.ps1 not found. Please start Redis manually." -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "❌ Error checking Redis: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Check if backend is running
Write-Host "STEP 2: Checking Backend..." -ForegroundColor Yellow
try {
    $backendTest = Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($backendTest) {
        Write-Host "✅ Backend is running on port 8000" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend is not running. Please start it first:" -ForegroundColor Red
        Write-Host "   Run: make consolidated-view" -ForegroundColor Yellow
        Write-Host "   OR: make full-dev" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Error checking backend: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Get preview of refresh
Write-Host "STEP 3: Getting Refresh Preview..." -ForegroundColor Yellow
try {
    $previewUrl = "$backendUrl/api/portfolio/ticker-table/refresh/preview"
    $previewResponse = Invoke-RestMethod -Uri $previewUrl -Method GET -ErrorAction Stop
    
    $expiredCount = $previewResponse.expired_count
    $estimateSeconds = $previewResponse.estimate_seconds
    $estimateMinutes = [math]::Round($estimateSeconds / 60, 1)
    $missingCounts = $previewResponse.missing_counts
    
    Write-Host "✅ Preview retrieved:" -ForegroundColor Green
    Write-Host "   Tickers needing refresh: $expiredCount" -ForegroundColor White
    Write-Host "   Estimated time: ~$estimateMinutes minutes" -ForegroundColor White
    
    if ($missingCounts) {
        $details = @()
        if ($missingCounts.prices) { $details += "$($missingCounts.prices) missing prices" }
        if ($missingCounts.sector) { $details += "$($missingCounts.sector) missing sector entries" }
        if ($missingCounts.metrics) { $details += "$($missingCounts.metrics) missing metrics" }
        if ($details.Count -gt 0) {
            Write-Host "   Missing data: $($details -join ', ')" -ForegroundColor White
        }
    }
    Write-Host ""
} catch {
    Write-Host "⚠️ Could not get preview (continuing anyway): $_" -ForegroundColor Yellow
    Write-Host ""
}

# Step 4: Confirm before proceeding
Write-Host "STEP 4: Confirmation" -ForegroundColor Yellow
Write-Host "This will start fetching data for all tickers from master_ticker_list.txt" -ForegroundColor White
Write-Host "Estimated time: ~$estimateMinutes minutes" -ForegroundColor White
Write-Host ""
$confirmation = Read-Host "Do you want to proceed? (Y/N)"
if ($confirmation -ne "Y" -and $confirmation -ne "y") {
    Write-Host "Refresh cancelled." -ForegroundColor Yellow
    exit 0
}
Write-Host ""

# Step 5: Initiate refresh
Write-Host "STEP 5: Initiating Refresh..." -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Refresh started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 The refresh process is running in the background." -ForegroundColor Cyan
Write-Host "📝 Monitor progress in:" -ForegroundColor Cyan
Write-Host "   - Terminal/console logs (backend output)" -ForegroundColor White
Write-Host "   - Log file: backend\logs\full_refresh.log" -ForegroundColor White
Write-Host ""
Write-Host "To watch the log file in real-time, run:" -ForegroundColor Yellow
Write-Host "   Get-Content backend\logs\full_refresh.log -Wait -Tail 50" -ForegroundColor White
Write-Host ""

try {
    $refreshUrl = "$backendUrl/api/portfolio/ticker-table/refresh"
    $response = Invoke-RestMethod -Uri $refreshUrl -Method POST -ErrorAction Stop
    
    Write-Host "✅ Refresh initiated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Message: $($response.message)" -ForegroundColor White
    
    if ($response.summary) {
        $summary = $response.summary
        Write-Host ""
        Write-Host "Summary:" -ForegroundColor Cyan
        Write-Host "  Expired before: $($summary.expired_before)" -ForegroundColor White
        Write-Host "  Expired after: $($summary.expired_after)" -ForegroundColor White
        Write-Host "  Refreshed count: $($summary.refreshed_count)" -ForegroundColor White
        Write-Host "  Success: $($summary.success)" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "Refresh Process Started" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The system is now fetching data for all tickers." -ForegroundColor White
    Write-Host "This will take approximately $estimateMinutes minutes." -ForegroundColor White
    Write-Host ""
    Write-Host "You can:" -ForegroundColor Yellow
    Write-Host "  1. Monitor logs: Get-Content backend\logs\full_refresh.log -Wait -Tail 50" -ForegroundColor White
    Write-Host "  2. Check Redis keys: make check-redis" -ForegroundColor White
    Write-Host "  3. View consolidated table: http://localhost:8000/api/portfolio/consolidated-table" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ Error initiating refresh: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response: $responseBody" -ForegroundColor Red
        } catch {}
    }
    exit 1
}
