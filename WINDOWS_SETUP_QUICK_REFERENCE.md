# Windows Setup - Quick Reference Guide

**Portfolio Navigator Wizard - Windows Quick Start**

---

## Prerequisites Installation

### 1. Node.js (Required)
```powershell
# Install via winget (recommended)
winget install --id OpenJS.NodeJS.LTS

# Or download from: https://nodejs.org/
# Version required: 18.x or higher
```

### 2. Python (Required)
```powershell
# Install Python 3.9 or higher
winget install --id Python.Python.3.9

# Or download from: https://www.python.org/downloads/
# Make sure to check "Add Python to PATH" during installation
```

### 3. Git for Windows (Required)
```powershell
# Install via winget
winget install --id Git.Git

# Or download from: https://git-scm.com/download/win
```

### 4. GnuWin32 Make (Required for Makefile commands)
```powershell
# Download from: http://gnuwin32.sourceforge.net/packages/make.htm
# Or use Chocolatey:
choco install make

# After installation, add to PATH:
# C:\Program Files (x86)\GnuWin32\bin
```

### 5. Memurai (Redis for Windows)
```powershell
# Install via winget (recommended)
winget install --id Memurai.MemuraiDeveloper

# Or download from: https://www.memurai.com/
# Free Developer Edition includes all needed features
```

---

## First-Time Setup

### Step 1: Clone Repository
```powershell
cd "C:\Users\YourName\Desktop"
git clone <YOUR_REPO_URL> portfolio-navigator-wizard
cd portfolio-navigator-wizard
```

### Step 2: Install Backend Dependencies
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

### Step 3: Install Frontend Dependencies
```powershell
cd frontend
npm install
cd ..
```

### Step 4: Configure Environment (Optional)
```powershell
# Copy example environment file
copy backend\.env.example backend\.env

# Edit backend\.env with your settings (optional for basic usage)
# notepad backend\.env
```

### Step 5: Verify Installation
```powershell
.\verify-system.ps1
```

Expected output: All checks should show PASS (green)

---

## Daily Development Workflow

### Quick Start (Recommended)
```powershell
# Navigate to project directory
cd "C:\Users\YourName\Desktop\portfolio-navigator-wizard"

# Start everything (Redis + Backend + Frontend)
.\start-dev.ps1
```

This script will:
1. Start Memurai (Redis) service
2. Launch backend server in new window (port 8000)
3. Launch frontend server in new window (port 8080)
4. Display access URLs

**Access Points:**
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Using Makefile Commands
```powershell
# Show all available commands
make help

# Check server status
make status

# Start both backend and frontend
make dev

# Start only backend
make backend

# Start only frontend
make frontend

# Stop all servers
make stop
```

### Stop Development Servers
```powershell
# Option 1: Press Ctrl+C in each terminal window

# Option 2: Use stop script
.\stop-dev.ps1

# Option 3: Use Makefile
make stop
```

---

## Common Windows-Specific Tasks

### Start/Stop Redis (Memurai)
```powershell
# Start (automatic via start-dev.ps1)
.\start-redis.ps1

# Start service manually (requires admin)
Start-Service -Name 'Memurai'

# Check status
Get-Service -Name 'Memurai'

# Stop service (requires admin)
Stop-Service -Name 'Memurai'
```

### Check Redis Connection
```powershell
# Test from command line
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis:', r.ping())"
```

### View Backend Logs
```powershell
# Logs are in: backend/logs/
Get-Content -Path "backend\logs\smart_refresh.log" -Tail 50

# Or use tail-like functionality
Get-Content -Path "backend\logs\full_refresh.log" -Wait
```

### Check Running Processes
```powershell
# Check if backend is running
Get-Process python -ErrorAction SilentlyContinue

# Check if frontend is running
Get-Process node -ErrorAction SilentlyContinue

# Check ports in use
Get-NetTCPConnection -LocalPort 8000,8080,6379 -ErrorAction SilentlyContinue
```

---

## Troubleshooting

### Issue: "make: command not found"
**Solution:**
```powershell
# Check if Make is installed
Get-Command make

# If not found, reinstall and verify PATH
.\setup-make-path.ps1

# Restart PowerShell after adding to PATH
```

### Issue: "Python not found"
**Solution:**
```powershell
# Check Python installation
python --version

# If not found, verify PATH contains Python directory
$env:Path -split ';' | Select-String "Python"

# Add Python to PATH manually if needed
```

### Issue: "Cannot activate virtual environment"
**Solution:**
```powershell
# Enable script execution (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
cd backend
.\venv\Scripts\Activate.ps1
```

### Issue: "Redis connection refused"
**Solution:**
```powershell
# Check if Memurai is running
Get-Service -Name 'Memurai'

# If not running, start it
.\start-redis.ps1

# Or start service manually (requires admin)
Start-Service -Name 'Memurai'
```

### Issue: "Port already in use"
**Solution:**
```powershell
# Find what's using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess

# Kill the process (replace <PID> with actual process ID)
Stop-Process -Id <PID> -Force

# Or stop all development servers
.\stop-dev.ps1
```

### Issue: "Module not found" errors
**Solution:**
```powershell
# Backend dependencies
cd backend
.\venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

---

## Performance Tips for Windows

### 1. Windows Defender Exclusions (Optional)
Add these folders to Windows Defender exclusions to improve performance:
- Project directory: `C:\Users\YourName\Desktop\portfolio-navigator-wizard`
- Node modules: `...\portfolio-navigator-wizard\frontend\node_modules`
- Python venv: `...\portfolio-navigator-wizard\backend\venv`

**How to add exclusions:**
1. Open Windows Security
2. Go to Virus & threat protection
3. Manage settings
4. Add or remove exclusions
5. Add folder exclusions

### 2. OneDrive Considerations
If project is in OneDrive folder:
- File watching may be slower (polling is already enabled)
- Consider moving project outside OneDrive for best performance
- Or exclude `.git` folder from OneDrive sync

### 3. Windows Terminal (Recommended)
Install Windows Terminal for better PowerShell experience:
```powershell
winget install --id Microsoft.WindowsTerminal
```

Benefits:
- Multiple tabs
- Better color support
- Copy/paste improvements
- Split panes

---

## Keyboard Shortcuts

**In Development Servers:**
- `Ctrl + C` - Stop server
- `Ctrl + L` - Clear console (in some terminals)
- `↑` / `↓` - Navigate command history

**In Windows Terminal:**
- `Ctrl + Shift + T` - New tab
- `Ctrl + Shift + D` - Duplicate tab
- `Alt + Shift + +` - Split pane horizontally
- `Alt + Shift + -` - Split pane vertically

---

## Additional Resources

### Documentation
- Main README: `README.md`
- Full Windows Analysis: `WINDOWS_COMPATIBILITY_ANALYSIS.md`
- Migration Guide: `MIGRATION_COMPLETE.md`
- Makefile Help: `make help`

### Useful Scripts
- `start-dev.ps1` - Daily startup (recommended)
- `stop-dev.ps1` - Stop all servers
- `verify-system.ps1` - Check system requirements
- `start-redis.ps1` - Start Redis/Memurai
- `verify-make-path.ps1` - Verify Make installation

### Package Managers (Optional)
Consider using a Windows package manager for easier software installation:
- **winget** (built into Windows 11)
- **Chocolatey** (https://chocolatey.org/)
- **Scoop** (https://scoop.sh/)

---

## Quick Reference Card

**Daily Workflow:**
```powershell
cd portfolio-navigator-wizard
.\start-dev.ps1
# Work on your changes
# Ctrl+C in each window or .\stop-dev.ps1
```

**Access URLs:**
```
Frontend:  http://localhost:8080
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health
```

**Key Commands:**
```powershell
make help          # Show all commands
make status        # Check what's running
make dev           # Start development
make stop          # Stop servers
.\verify-system.ps1 # Check system
```

---

**Last Updated:** January 18, 2026  
**For Issues:** Check `WINDOWS_COMPATIBILITY_ANALYSIS.md` Appendix D (Troubleshooting)
