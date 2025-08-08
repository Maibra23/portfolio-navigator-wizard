#!/usr/bin/env python3
"""
Ticker Table Server
A FastAPI server to serve the ticker table with proper CORS and integration
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from pathlib import Path

import httpx

app = FastAPI(
    title="Ticker Table Server",
    description="Serves the ticker table with proxy to main backend API",
    version="1.0.0"
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main backend server URL
MAIN_BACKEND_URL = "http://127.0.0.1:8000"

@app.get("/api/portfolio/ticker-table/data")
async def proxy_ticker_data():
    """Proxy ticker data from main backend"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{MAIN_BACKEND_URL}/api/portfolio/ticker-table/data")
            return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch data from main backend: {str(e)}"}

@app.post("/api/portfolio/ticker-table/refresh")
async def proxy_refresh():
    """Proxy refresh request to main backend"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{MAIN_BACKEND_URL}/api/portfolio/ticker-table/refresh")
            return response.json()
        except Exception as e:
            return {"error": f"Failed to refresh data: {str(e)}"}

# Get the path to the HTML file
current_dir = Path(__file__).parent
html_file_path = current_dir.parent / "frontend" / "public" / "ticker-table.html"

@app.get("/", response_class=HTMLResponse)
async def serve_ticker_table():
    """Serve the ticker table HTML"""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Error</title></head>
                <body>
                    <h1>Error: Ticker table HTML file not found</h1>
                    <p>The ticker-table.html file could not be found at: {}</p>
                </body>
            </html>
            """.format(html_file_path),
            status_code=404
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ticker-table-server",
        "html_file": str(html_file_path),
        "html_exists": html_file_path.exists()
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "running",
        "endpoints": {
            "ticker_table": "/",
            "api_data": "/api/portfolio/ticker-table/data",
            "api_refresh": "/api/portfolio/ticker-table/refresh",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Ticker Table Server...")
    print(f"📁 HTML file path: {html_file_path}")
    print(f"✅ HTML file exists: {html_file_path.exists()}")
    print("🌐 Server will be available at: http://localhost:8081")
    print("📊 API endpoints available at: http://localhost:8081/api/portfolio/")
    
    uvicorn.run(
        "ticker_table_server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )
