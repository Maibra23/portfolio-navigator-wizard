#!/usr/bin/env python3
"""
Ticker Table Launcher
Simple script to launch the ticker table server
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Change to the backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("🚀 Launching Ticker Table Server...")
    print("📁 Working directory:", backend_dir)
    print("🌐 Server will be available at: http://localhost:8080")
    print("📊 API endpoints: http://localhost:8080/api/portfolio/")
    print("🔗 Direct table access: http://localhost:8080/")
    print("\n" + "="*50)
    
    try:
        # Run the ticker table server
        subprocess.run([
            sys.executable, 
            "ticker_table_server.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
