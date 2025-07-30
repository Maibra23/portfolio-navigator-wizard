from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from routers import portfolio, cookie_demo

load_dotenv()

app = FastAPI()

# Rate limiter
limiter = Limiter(key_func=lambda request: request.client.host)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend build) in production
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Routers
app.include_router(portfolio.router)
app.include_router(cookie_demo.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/")
def read_root():
    # If static/index.html exists, serve it (SPA fallback)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "FastAPI backend is running."}

# SPA fallback for all non-API routes
@app.middleware("http")
async def spa_fallback(request: Request, call_next):
    if request.url.path.startswith("/api") or request.url.path.startswith("/static"):
        return await call_next(request)
    if os.path.isdir(static_dir):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return await call_next(request) 