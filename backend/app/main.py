
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
            
        # Optional: Periodic cleanup of all inactive clients to prevent memory leak
        if len(self.requests) > 1000: # Simple threshold
            self.cleanup()
            
        return False
        
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
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
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
            "error_en": "Internal Server Error. Please contact support if this persists.",
            "error_type": exc.__class__.__name__
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

@app.post("/api/submit-audio")
def process_audio_attempt(
    file: UploadFile = File(...), 
    task_id: str = Form(...), 
    is_retry: bool = Form(False),
    db: Session = Depends(get_db)
):
    # Use UUID to prevent collision if multiple users (or sessions) upload simultaneously
    # Security: File Extension Validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid audio format. Use {', '.join(settings.ALLOWED_EXTENSIONS)}")
        
    temp_filename = f"temp_{uuid.uuid4().hex}{ext}"
    
    # Security: File Size Limit
    MAX_SIZE = settings.MAX_AUDIO_SIZE_BYTES
    file.file.seek(0, 2) # Seek to end
    file_size = file.file.tell()
    file.file.seek(0) # Reset
    
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_SIZE // (1024*1024)}MB.")

    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Check if task_id is a valid UUID (Exam Mode)
        is_exam = False
        try:
            uuid.UUID(task_id)
            is_exam = True
        except ValueError:
            pass

        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=task_id,
            db=db,
            session_id=task_id, # Use correct session ID
            is_exam_mode=is_exam, # Enable exam logic if UUID
            is_retry=is_retry
        )
        return intervention
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"Cleanup Error: {e}")