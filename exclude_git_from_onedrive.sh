#!/bin/bash

# Script to exclude .git folder from OneDrive sync
# This prevents OneDrive from locking git files

echo "=== Excluding .git folder from OneDrive Sync ==="
echo ""

PROJECT_DIR="/Users/Brook/Library/CloudStorage/OneDrive-Linnéuniversitetet/portfolio-navigator-wizard"
GIT_DIR="$PROJECT_DIR/.git"

# Check if .git exists
if [ ! -d "$GIT_DIR" ]; then
    echo "❌ Error: .git directory not found at $GIT_DIR"
    exit 1
fi

# Method 1: Set macOS extended attribute to prevent OneDrive sync
echo "1. Setting extended attribute to prevent OneDrive sync..."
xattr -w com.microsoft.OneDrive.SyncSkip 1 "$GIT_DIR"

if [ $? -eq 0 ]; then
    echo "   ✅ Successfully marked .git folder to skip OneDrive sync"
else
    echo "   ⚠️  Failed to set attribute (this is normal on some macOS versions)"
fi

# Method 2: Add .git to OneDrive ignore list (if OneDrive CLI is available)
echo ""
echo "2. Checking for OneDrive configuration..."

ONEDRIVE_CONFIG="$HOME/Library/Application Support/OneDrive/settings/Personal/global.ini"
if [ -f "$ONEDRIVE_CONFIG" ]; then
    echo "   ℹ️  OneDrive config found"
    echo "   → You may need to manually add .git to OneDrive exclusions"
else
    echo "   ℹ️  OneDrive config not found (this is normal)"
fi

# Method 3: Check current OneDrive sync status
echo ""
echo "3. Checking .git folder attributes..."
xattr -l "$GIT_DIR" | head -5

echo ""
echo "=== Additional Steps (Manual) ==="
echo ""
echo "To fully exclude .git from OneDrive:"
echo ""
echo "1. Right-click on the .git folder in Finder"
echo "2. Select 'Always keep on this device' to prevent cloud-only status"
echo "3. Or use OneDrive settings to exclude the folder:"
echo "   - Open OneDrive preferences"
echo "   - Go to 'Backup' tab"
echo "   - Click 'Manage backup'"
echo "   - Uncheck folders or add .git to exclusions"
echo ""
echo "=== Current .git Folder Size ==="
du -sh "$GIT_DIR"

echo ""
echo "✅ Script complete!"
echo ""
echo "NEXT STEPS:"
echo "1. Restart OneDrive: killall OneDrive && open /Applications/OneDrive.app"
echo "2. Test git operations: cd '$PROJECT_DIR' && git status"

