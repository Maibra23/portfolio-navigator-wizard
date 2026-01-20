# Quick Fix for Make Command
# Run this script in any PowerShell session to enable make command

$makePath = "C:\Program Files (x86)\GnuWin32\bin"

# Check if Make exists
if (-not (Test-Path "$makePath\make.exe")) {
    Write-Host "ERROR: Make not found at $makePath" -ForegroundColor Red
    Write-Host "Please install Make first: winget install --id GnuWin32.Make" -ForegroundColor Yellow
    exit 1
}

# Add to current session PATH
if ($env:Path -notlike "*$makePath*") {
    $env:Path += ";$makePath"
    Write-Host "✅ Added Make to current session PATH" -ForegroundColor Green
} else {
    Write-Host "✅ Make is already in PATH" -ForegroundColor Green
}

# Test make
Write-Host "`nTesting make command..." -ForegroundColor Cyan
try {
    $result = & make --version 2>&1 | Select-Object -First 1
    Write-Host "✅ Make is working: $result" -ForegroundColor Green
    Write-Host "`nYou can now use make commands!" -ForegroundColor Green
    Write-Host "Example: make status" -ForegroundColor Gray
} catch {
    Write-Host "❌ Make test failed: $_" -ForegroundColor Red
    exit 1
}
