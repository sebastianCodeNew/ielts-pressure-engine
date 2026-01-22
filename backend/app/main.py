import shutil
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Core Logic Imports
# Core Logic Imports
from app.schemas import UserAttempt, Intervention, SignalMetrics
from app.core.transcriber import transcribe_audio
from app.core.evaluator import extract_signals
from app.core.agent import formulate_strategy
from app.core.translator import translate_to_english
from app.core.cache import init_db as init_cache_db, get_cached_translation, save_translation_to_cache
from app.core.state import AgentState, update_state
from app.core.database import init_db, get_db, SessionModel
from app.core.engine import process_user_attempt # <--- NEW SERVICE

# --- LIFESPAN MANAGER (Database Startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create DBs
    init_cache_db()
    init_db() # SQLite
    print("--- Databases Loaded ---")
    yield

app = FastAPI(title="IELTS Pressure Engine", lifespan=lifespan)

class TranslationRequest(BaseModel):
    text: str

@app.get("/")
def health_check():
    return {"status": "system_active", "mode": "adaptive"}

# --- AUDIO ENDPOINT (Refactored) ---
@app.post("/api/submit-audio", response_model=Intervention)
def process_audio_attempt(file: UploadFile = File(...), task_id: str = "default", db: Session = Depends(get_db)):
    
    # SECURITY: Validate file size (Max 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="File too large. Max size is 10MB.")
    
    # 1. Save Temp File
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 2. Delegate to Engine
        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=task_id,
            db=db,
            session_id="default_user" # Hardcoded for single-user MVP
        )
        return intervention
        
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# --- TRANSLATION ENDPOINT (With Caching) ---
@app.post("/api/translate")
def quick_translate(request: TranslationRequest):
    # 1. CHECK CACHE (Fast Layer)
    cached_result = get_cached_translation(request.text)
    
    if cached_result:
        print(f"DEBUG: Cache Hit for '{request.text}'")
        return {"original": request.text, "translated": cached_result}

    # 2. CALL AI (Slow Layer)
    print(f"DEBUG: Cache Miss. Asking Llama-3.2...")
    english_text = translate_to_english(request.text)
    
    # 3. SAVE TO CACHE (Future Investment)
    if english_text and "Error" not in english_text:
        save_translation_to_cache(request.text, english_text)
    
    return {"original": request.text, "translated": english_text}