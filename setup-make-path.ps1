# Setup Make PATH for Portfolio Navigator Wizard
# This script adds GnuWin32 Make to your PATH permanently

$makePath = "C:\Program Files (x86)\GnuWin32\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -notlike "*$makePath*") {
    Write-Host "Adding Make to user PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$makePath", "User")
    Write-Host "✅ Make added to PATH permanently" -ForegroundColor Green
    Write-Host "Please restart your PowerShell terminal for changes to take effect" -ForegroundColor Yellow
} else {
    Write-Host "✅ Make is already in PATH" -ForegroundColor Green
}

# Add to current session
$env:Path += ";$makePath"
Write-Host "✅ Make added to current session PATH" -ForegroundColor Green

# Test make
Write-Host "`nTesting make command..." -ForegroundColor Cyan
try {
    $makeVersion = make --version 2>&1 | Select-Object -First 1
    Write-Host "✅ Make is working: $makeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Make test failed: $_" -ForegroundColor Red
}
