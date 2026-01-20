# ENABLE_MAKE.ps1
# Run this script at the start of EVERY PowerShell session to enable make command
# Or add this line to your PowerShell profile for automatic loading

$makePath = "C:\Program Files (x86)\GnuWin32\bin"

if (Test-Path "$makePath\make.exe") {
    if ($env:Path -notlike "*$makePath*") {
        $env:Path += ";$makePath"
        Write-Host "✅ Make command enabled" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Make not found. Install with: winget install --id GnuWin32.Make" -ForegroundColor Yellow
}
