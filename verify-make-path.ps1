# Verify Make PATH Configuration
# This script verifies that GnuWin32 Make is permanently added to PATH

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Verifying Make PATH Configuration" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if make.exe exists
$makePath = "C:\Program Files (x86)\GnuWin32\bin\make.exe"
if (Test-Path $makePath) {
    Write-Host "✅ make.exe found at: $makePath" -ForegroundColor Green
} else {
    Write-Host "❌ make.exe NOT found at: $makePath" -ForegroundColor Red
    exit 1
}

# Check User PATH
Write-Host ""
Write-Host "Checking User Environment PATH..." -ForegroundColor Yellow
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -match "GnuWin32") {
    $gnuWin32Path = ($userPath -split ';' | Select-String "GnuWin32").ToString()
    Write-Host "✅ PATH is PERMANENTLY set in User environment variables" -ForegroundColor Green
    Write-Host "   Location: User PATH" -ForegroundColor Cyan
    Write-Host "   Value: $gnuWin32Path" -ForegroundColor White
} else {
    Write-Host "❌ PATH NOT found in User environment variables" -ForegroundColor Red
    Write-Host "   Attempting to add it..." -ForegroundColor Yellow
    $newPath = $userPath + ";C:\Program Files (x86)\GnuWin32\bin"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "✅ PATH added to User environment variables" -ForegroundColor Green
    Write-Host "   ⚠️  Please restart PowerShell for changes to take effect" -ForegroundColor Yellow
}

# Check System PATH
Write-Host ""
Write-Host "Checking System Environment PATH..." -ForegroundColor Yellow
$systemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($systemPath -match "GnuWin32") {
    Write-Host "✅ PATH also found in System environment variables" -ForegroundColor Green
} else {
    Write-Host "ℹ️  PATH not in System environment (User PATH is sufficient)" -ForegroundColor Cyan
}

# Check current session PATH
Write-Host ""
Write-Host "Checking current PowerShell session PATH..." -ForegroundColor Yellow
if ($env:Path -match "GnuWin32") {
    Write-Host "✅ PATH is available in current session" -ForegroundColor Green
} else {
    Write-Host "⚠️  PATH NOT in current session (restart PowerShell to load it)" -ForegroundColor Yellow
    Write-Host "   Adding to current session temporarily..." -ForegroundColor Cyan
    $env:Path += ";C:\Program Files (x86)\GnuWin32\bin"
    Write-Host "✅ Added to current session" -ForegroundColor Green
}

# Test make command
Write-Host ""
Write-Host "Testing make command..." -ForegroundColor Yellow
try {
    $makeVersion = & make --version 2>&1 | Select-Object -First 1
    if ($makeVersion -match "GNU Make") {
        Write-Host "✅ make command works!" -ForegroundColor Green
        Write-Host "   $makeVersion" -ForegroundColor White
    } else {
        Write-Host "❌ make command failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ make command not found: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  ✅ make.exe exists" -ForegroundColor Green
Write-Host "  ✅ PATH is permanently set (User environment)" -ForegroundColor Green
if ($env:Path -match "GnuWin32") {
    Write-Host "  ✅ Current session has PATH loaded" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Restart PowerShell to load PATH in new sessions" -ForegroundColor Yellow
}
Write-Host "==================================================" -ForegroundColor Cyan
