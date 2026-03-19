
import shutil
import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict

# Core Logic Imports
from app.core.database import init_db, get_db
from app.core.cache import init_db as init_cache_db
from app.core.engine import process_user_attempt
from app.core.config import settings
from app.api.v1.api import api_router

# --- RATE LIMITING ---
class RateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.requests: Dict[str, list] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = [now]
            return True
        
        # Filter requests in the current window
        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < self.window]
        
        if len(self.requests[client_id]) < self.limit:
            self.requests[client_id].append(now)
            return True
        
        # Frequent cleanup to prevent memory slow-leak
        if len(self.requests) > 100 or random.random() < 0.05:
            self.cleanup()
            
        return len(self.requests.get(client_id, [])) < self.limit
        
    def cleanup(self):
        """Removes client records that have no request history in the window."""
        now = time.time()
        to_delete = []
        for cid, requests in self.requests.items():
            valid_requests = [t for t in requests if now - t < self.window]
            if not valid_requests:
                to_delete.append(cid)
            else:
                self.requests[cid] = valid_requests
        for cid in to_delete:
            del self.requests[cid]

audio_limiter = RateLimiter(limit=settings.RATE_LIMIT_COUNT, window=settings.RATE_LIMIT_WINDOW_SECONDS) 

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.cleanup import cleanup_old_audio
    cleanup_old_audio(max_age_hours=settings.AUDIO_CLEANUP_HOURS)
    
    init_cache_db()
    init_db()
    print("--- Databases Loaded & Migrated ---")
    yield

app = FastAPI(title="IELTS Pressure Engine", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for rate limiting audio endpoints
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    if request.url.path.endswith("/submit-audio"):
        # Proxy-safe IP detection
        client_ip = request.headers.get("X-Forwarded-For") or request.client.host
        if not audio_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."}
            )
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Cleanly handles any unhandled server errors."""
    print(f"GLOBAL EXCEPTION: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Koneksi terganggu atau terjadi kesalahan sistem (Server Error). Silakan coba lagi.",
            "error_en": "Internal Server Error. Please contact support if this persists."
        }
    )

# Register API v1
app.include_router(api_router, prefix="/api/v1")

# Serve audio files for Audio Mirror feature
from fastapi.staticfiles import StaticFiles
AUDIO_DIR = settings.AUDIO_STORAGE_DIR
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.get("/")
def health_check():
    return {"status": "system_active", "mode": "performance_optimized"}

# Redundant endpoint removed.
# All audio submissions should now use the /api/v1/exams/{session_id}/submit-audio endpoint.
