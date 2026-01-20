# WSL2 and Redis Setup Guide
**Portfolio Navigator Wizard - Windows Migration**

## Current Status
✅ Node.js v24.13.0 installed
✅ npm 11.6.2 installed  
✅ Python 3.9.0 installed
✅ Backend virtual environment created
✅ Backend dependencies installed (all packages)
✅ Frontend dependencies installed (503 packages)
✅ Makefile updated for cross-platform compatibility
⏳ WSL2 - Requires installation and restart
⏳ Redis - Requires WSL2 to be installed first

---

## Step 1: Complete WSL2 Installation

WSL2 installation was initiated but requires a system restart to complete.

### After Restart:

1. **Open PowerShell as Administrator** (Right-click → Run as Administrator)

2. **Verify WSL2 is installed:**
   ```powershell
   wsl --status
   ```
   Expected output: Should show WSL version 2

3. **Install Ubuntu distribution:**
   ```powershell
   wsl --install -d Ubuntu
   ```
   OR if Ubuntu is already listed:
   ```powershell
   wsl --list --online
   wsl --install -d Ubuntu-22.04
   ```

4. **First-time Ubuntu setup:**
   - When Ubuntu opens, it will prompt for username and password
   - Create a username (e.g., `portfoliouser`)
   - Set a password (remember this for sudo commands)

---

## Step 2: Install Redis in WSL

1. **Open WSL (Ubuntu):**
   ```powershell
   wsl
   ```

2. **Update package list:**
   ```bash
   sudo apt update
   ```

3. **Install Redis server:**
   ```bash
   sudo apt install redis-server -y
   ```

4. **Start Redis service:**
   ```bash
   sudo service redis-server start
   ```

5. **Verify Redis is running:**
   ```bash
   redis-cli ping
   ```
   Expected output: `PONG`

6. **Configure Redis to start automatically:**
   ```bash
   sudo systemctl enable redis-server
   ```

7. **Exit WSL:**
   ```bash
   exit
   ```

---

## Step 3: Import Redis Backup Data

If you have the Redis backup file `redis-backup-20260117-181330.rdb`:

1. **Locate the backup file** (should be in Desktop or project directory)

2. **Copy backup to WSL:**
   ```powershell
   # From PowerShell, copy file to WSL home directory
   wsl mkdir -p ~/redis-backup
   # Copy the file (adjust path as needed)
   wsl cp /mnt/c/Users/Mustafa\ Ibrahim/Desktop/redis-backup-20260117-181330.rdb ~/redis-backup/
   ```

3. **Stop Redis in WSL:**
   ```powershell
   wsl sudo service redis-server stop
   ```

4. **Backup existing dump.rdb (if exists):**
   ```powershell
   wsl sudo cp /var/lib/redis/dump.rdb /var/lib/redis/dump.rdb.backup 2>/dev/null || echo "No existing dump.rdb"
   ```

5. **Copy backup to Redis data directory:**
   ```powershell
   wsl sudo cp ~/redis-backup/redis-backup-20260117-181330.rdb /var/lib/redis/dump.rdb
   ```

6. **Set correct permissions:**
   ```powershell
   wsl sudo chown redis:redis /var/lib/redis/dump.rdb
   wsl sudo chmod 660 /var/lib/redis/dump.rdb
   ```

7. **Start Redis:**
   ```powershell
   wsl sudo service redis-server start
   ```

8. **Verify data was imported:**
   ```powershell
   wsl redis-cli DBSIZE
   ```
   Expected: Should show number of keys (not 0 if backup had data)

9. **Test connection from Windows:**
   ```powershell
   # From PowerShell
   cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard\backend"
   .\venv\Scripts\Activate.ps1
   python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis connected:', r.ping())"
   ```

---

## Step 4: Verify Complete System

### Test Backend:
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard\backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, test:
```powershell
curl http://localhost:8000/health
```

### Test Frontend:
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard\frontend"
npm run dev
```

Open browser: http://localhost:8080

### Test Redis Connection:
```powershell
wsl redis-cli ping
```

---

## Troubleshooting

### WSL2 not starting after restart:
- Check BIOS: Virtualization must be enabled
- Run: `wsl --update` in PowerShell (as admin)
- Check Windows Features: "Virtual Machine Platform" and "Windows Subsystem for Linux" must be enabled

### Redis connection refused:
- Ensure Redis is running: `wsl sudo service redis-server status`
- Check Redis is listening: `wsl redis-cli ping`
- Verify port 6379 is accessible from Windows

### Cannot connect to Redis from Python:
- Redis in WSL listens on localhost, which should be accessible from Windows
- Test: `wsl redis-cli -h localhost ping`
- If still failing, check WSL network settings

---

## Daily Workflow Commands

### Morning Startup:

**Terminal 1 - Start Redis:**
```powershell
wsl sudo service redis-server start
```

**Terminal 2 - Start Backend:**
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard\backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 3 - Start Frontend:**
```powershell
cd "C:\Users\Mustafa Ibrahim\Desktop\portfolio-navigator-wizard\portfolio-navigator-wizard\frontend"
npm run dev
```

### Access URLs:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Evening Shutdown:
- Press `Ctrl+C` in each terminal
- Redis will continue running (or stop with: `wsl sudo service redis-server stop`)

---

## Quick Verification Script

Run this after completing WSL2 setup:

```powershell
Write-Host "=== System Verification ===" -ForegroundColor Green
Write-Host "Node.js:" -NoNewline; node --version
Write-Host "npm:" -NoNewline; npm --version
Write-Host "Python:" -NoNewline; python --version
Write-Host "WSL2:" -NoNewline; wsl --version
Write-Host "Redis:" -NoNewline; wsl redis-cli ping
Write-Host "Backend venv:" -NoNewline; Test-Path "backend\venv"
Write-Host "Frontend deps:" -NoNewline; Test-Path "frontend\node_modules"
```

---

**Next Steps:** Complete WSL2 installation, then follow this guide to set up Redis and import your backup data.
