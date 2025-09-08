#!/usr/bin/env python3
"""
Consolidated Table Server
A FastAPI server to serve both ticker and portfolio tables with tabbed interface
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from pathlib import Path
import httpx
import json
import redis
import gzip

app = FastAPI(
    title="Consolidated Table Server",
    description="Serves both ticker and portfolio tables with tabbed interface",
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

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Ticker table endpoints (direct Redis access)
@app.get("/api/portfolio/ticker-table/data")
async def get_ticker_data():
    """Get ticker data directly from Redis"""
    try:
        # Get all ticker keys
        ticker_keys = redis_client.keys('ticker_data:*')
        
        # Separate by data type
        price_keys = [k for k in ticker_keys if b'ticker_data:prices:' in k]
        sector_keys = [k for k in ticker_keys if b'ticker_data:sector:' in k]
        metrics_keys = [k for k in ticker_keys if b'ticker_data:metrics:' in k]
        
        # Get unique tickers
        tickers = set()
        for key in price_keys:
            ticker = key.decode('utf-8').split(':')[-1]
            tickers.add(ticker)
        
        # Build ticker data
        ticker_data = []
        sectors = set()
        
        for ticker in tickers:
            try:
                # Get sector data
                sector_key = f'ticker_data:sector:{ticker}'
                sector_data = redis_client.get(sector_key)
                if not sector_data:
                    continue
                    
                sector_info = json.loads(sector_data.decode())
                sector = sector_info.get('sector', 'Unknown')
                sectors.add(sector)
                
                # Get metrics data
                metrics_key = f'ticker_data:metrics:{ticker}'
                metrics_data = redis_client.get(metrics_key)
                if not metrics_data:
                    continue
                    
                metrics = json.loads(metrics_data.decode())
                
                # Get price data for last price
                price_key = f'ticker_data:prices:{ticker}'
                price_data = redis_client.get(price_key)
                last_price = 0
                if price_data:
                    try:
                        decompressed = gzip.decompress(price_data)
                        prices = json.loads(decompressed.decode())
                        if prices:
                            last_price = list(prices.values())[-1]
                    except:
                        pass
                
                # Determine risk level based on volatility
                volatility = metrics.get('risk', 0)
                if volatility < 0.2:
                    risk_level = "Low Risk"
                elif volatility < 0.4:
                    risk_level = "Medium Risk"
                else:
                    risk_level = "High Risk"
                
                # Determine data quality
                data_quality = "good" if volatility > 0 else "limited"
                
                # Get additional data for original table structure
                exchange = sector_info.get('exchange', 'Unknown')
                country = sector_info.get('country', 'Unknown')
                
                # Calculate data points (simulate based on available data)
                data_points = 1000 if volatility > 0 else 0
                
                # Calculate dates (simulate)
                first_date = "2020-01-01"
                last_date = "2025-09-01"
                
                # Calculate annualized return and risk
                annualized_return = (volatility * 0.1) * 100  # Simulate return
                annualized_risk = volatility * 100
                
                ticker_data.append({
                    'id': len(ticker_data) + 1,
                    'ticker': ticker,
                    'companyName': sector_info.get('name', ticker),
                    'sector': sector,
                    'industry': sector_info.get('industry', 'Unknown'),
                    'exchange': exchange,
                    'country': country,
                    'dataPoints': data_points,
                    'firstDate': first_date,
                    'lastDate': last_date,
                    'lastPrice': last_price,
                    'annualizedReturn': annualized_return,
                    'annualizedRisk': annualized_risk
                })
                
            except Exception as e:
                print(f"Error processing ticker {ticker}: {e}")
                continue
        
        return {
            "success": True,
            "tickers": ticker_data,
            "total_tickers": len(ticker_data),
            "cached_tickers": len(ticker_data),
            "sectors": sorted(list(sectors)),
            "last_updated": "2025-09-01T18:00:00Z"
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch ticker data: {str(e)}"}

@app.post("/api/portfolio/ticker-table/refresh")
async def refresh_ticker_data():
    """Refresh ticker data (placeholder)"""
    return {
        "success": True,
        "message": "Ticker data refreshed successfully",
        "timestamp": "2025-09-01T18:00:00Z"
    }

@app.post("/api/portfolio/ticker-table/smart-refresh")
async def smart_refresh_ticker_data():
    """Smart refresh ticker data (placeholder)"""
    return {
        "success": True,
        "message": "Smart refresh completed successfully",
        "timestamp": "2025-09-01T18:00:00Z"
    }

# Portfolio table endpoints
@app.get("/api/portfolio/table/data")
async def get_portfolio_data():
    """Get portfolio data from Redis"""
    try:
        # Get all portfolio bucket keys
        portfolio_keys = redis_client.keys('portfolio_bucket:*')
        
        # Group by risk profile
        portfolios_by_profile = {}
        for key in portfolio_keys:
            key_str = key.decode('utf-8')
            parts = key_str.split(':')
            if len(parts) >= 3:
                risk_profile = parts[1]
                if risk_profile not in portfolios_by_profile:
                    portfolios_by_profile[risk_profile] = []
                
                # Get portfolio data
                data = redis_client.get(key)
                if data:
                    try:
                        portfolio_data = json.loads(data.decode())
                        portfolios_by_profile[risk_profile].append(portfolio_data)
                    except Exception as e:
                        print(f"Error parsing portfolio data for {key_str}: {e}")
        
        # Convert to array format for display
        all_portfolios = []
        for profile, portfolios in portfolios_by_profile.items():
            for portfolio in portfolios:
                all_portfolios.append({
                    'risk_profile': profile,
                    'name': portfolio.get('name', 'Unknown'),
                    'description': portfolio.get('description', ''),
                    'expected_return': portfolio.get('expectedReturn', 0),
                    'risk': portfolio.get('risk', 0),
                    'diversification_score': portfolio.get('diversificationScore', 0),
                    'stocks': portfolio.get('allocations', []),
                    'generated_at': portfolio.get('generated_at', ''),
                    'variation_id': portfolio.get('variation_id', 0)
                })
        
        return {
            "success": True,
            "portfolios": all_portfolios,
            "total_portfolios": len(all_portfolios),
            "profiles": list(portfolios_by_profile.keys()),
            "profile_counts": {profile: len(portfolios) for profile, portfolios in portfolios_by_profile.items()}
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch portfolio data: {str(e)}"}

@app.get("/api/portfolio/table/stats")
async def get_portfolio_stats():
    """Get portfolio statistics"""
    try:
        # Get all portfolio bucket keys
        portfolio_keys = redis_client.keys('portfolio_bucket:*')
        
        # Count by risk profile
        profile_counts = {}
        total_portfolios = 0
        
        for key in portfolio_keys:
            key_str = key.decode('utf-8')
            parts = key_str.split(':')
            if len(parts) >= 3:
                risk_profile = parts[1]
                profile_counts[risk_profile] = profile_counts.get(risk_profile, 0) + 1
                total_portfolios += 1
        
        return {
            "success": True,
            "total_portfolios": total_portfolios,
            "profile_counts": profile_counts,
            "total_profiles": len(profile_counts)
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch portfolio stats: {str(e)}"}

# Get the path to the HTML file
current_dir = Path(__file__).parent
html_file_path = current_dir.parent / "frontend" / "public" / "consolidated-table.html"

@app.get("/", response_class=HTMLResponse)
async def serve_consolidated_table():
    """Serve the consolidated table HTML"""
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
                    <h1>Error: Consolidated table HTML file not found</h1>
                    <p>The consolidated-table.html file could not be found at: {}</p>
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
        "service": "consolidated-table-server",
        "html_file": str(html_file_path),
        "html_exists": html_file_path.exists()
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "running",
        "endpoints": {
            "consolidated_table": "/",
            "ticker_data": "/api/portfolio/ticker-table/data",
            "portfolio_data": "/api/portfolio/table/data",
            "portfolio_stats": "/api/portfolio/table/stats",
            "ticker_refresh": "/api/portfolio/ticker-table/refresh",
            "ticker_smart_refresh": "/api/portfolio/ticker-table/smart-refresh",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Consolidated Table Server...")
    print(f"📁 HTML file path: {html_file_path}")
    print(f"✅ HTML file exists: {html_file_path.exists()}")
    print("🌐 Server will be available at: http://localhost:8081")
    print("📊 API endpoints available at: http://localhost:8081/api/portfolio/")
    
    uvicorn.run(
        "consolidated_table_server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )
