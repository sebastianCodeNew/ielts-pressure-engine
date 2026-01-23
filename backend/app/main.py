import shutil
import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict

# Core Logic Imports
from app.core.database import init_db, get_db
from app.core.cache import init_db as init_cache_db
from app.core.engine import process_user_attempt
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
        return False

audio_limiter = RateLimiter(limit=10, window=60) 

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
        client_ip = request.client.host
        if not audio_limiter.is_allowed(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
    return await call_next(request)

# Register API v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "system_active", "mode": "performance_optimized"}

@app.post("/api/submit-audio")
def process_audio_attempt(file: UploadFile = File(...), task_id: str = "default", db: Session = Depends(get_db)):
    # Use UUID to prevent collision if multiple users (or sessions) upload simultaneously
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_filename = f"temp_{uuid.uuid4()}{ext}"
    
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=task_id,
            db=db,
            session_id="default_user"
        )
        return intervention
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"Cleanup Error: {e}")