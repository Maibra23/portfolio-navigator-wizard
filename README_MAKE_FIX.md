# Fix for "make command not found" Error

## ✅ SOLUTION - Run This Command

**Every time you open a NEW PowerShell terminal, run this FIRST:**

```powershell
$env:Path += ";C:\Program Files (x86)\GnuWin32\bin"
```

Then `make` commands will work!

## Quick Test

After running the command above, test it:
```powershell
make --version
```

You should see: `GNU Make 3.81`

## Available Commands

Once Make is enabled, you can use:

```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard"

make status              # Check server status
make check-redis         # Check Redis connection  
make consolidated-view   # Start consolidated view (backend + monitoring)
make full-dev            # Start full dev environment
make stop                # Stop all servers
```

## Permanent Fix (Optional)

**Option 1: Add to PowerShell Profile (Recommended)**

1. Check if profile exists:
   ```powershell
   Test-Path $PROFILE
   ```

2. Create/edit profile:
   ```powershell
   notepad $PROFILE
   ```

3. Add this line:
   ```powershell
   $env:Path += ";C:\Program Files (x86)\GnuWin32\bin"
   ```

4. Save and restart PowerShell

**Option 2: Run Setup Script Once**
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard"
.\setup-make-path.ps1
```
Then restart PowerShell.

**Option 3: Use Helper Script**
```powershell
.\ENABLE_MAKE.ps1
make status
```

## Why This Happens

- Make is installed at: `C:\Program Files (x86)\GnuWin32\bin\make.exe`
- But it's not automatically added to PATH in PowerShell
- You need to add it manually (either per session or permanently)

## Summary

**Quick Fix (for this session):**
```powershell
$env:Path += ";C:\Program Files (x86)\GnuWin32\bin"
```

**Then use make commands:**
```powershell
make consolidated-view
make status
make full-dev
```

That's it! 🎉
