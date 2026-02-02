import uuid
import shutil
import os
import re
import random
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, ExamSession, QuestionAttempt, User
from app.schemas import ExamStartRequest, ExamSessionSchema, Intervention
from app.core.engine import process_user_attempt 

router = APIRouter()

PART_1_TOPICS = [
    "Tell me about your hometown.",
    "Tell me about your job or studies.",
    "Do you prefer living in a house or an apartment?",
    "How do you usually spend your weekends?",
    "Tell me about your family.",
    "Do you like traveling?",
    "What kind of music do you like?"
]

@router.get("/warmup")
def get_exam_warmup(user_id: str = "default_user", db: Session = Depends(get_db)):
    """Fetches due vocabulary for the pre-flight warm-up."""
    from app.core.spaced_repetition import get_due_vocabulary
    due_words = get_due_vocabulary(db, user_id, limit=3)
    
    return [
        {
            "word": w.word,
            "definition": w.definition or "No definition available."
        } for w in due_words
    ]

@router.post("/start", response_model=ExamSessionSchema)
def start_exam(request: ExamStartRequest, db: Session = Depends(get_db)):
    # Ensure user exists (hack for MVP)
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        user = User(id=request.user_id, username=request.user_id)
        db.add(user)
        db.commit()

    session_id = str(uuid.uuid4())
    
    # Randomize Topic
    initial_prompt = random.choice(PART_1_TOPICS)
    
    # Map topics to initial Band 8+ keywords
    TOPIC_KEYWORDS = {
        "Tell me about your hometown.": ["picturesque", "bustling", "quaint"],
        "Tell me about your job or studies.": ["meticulous", "demanding", "rewarding"],
        "Do you prefer living in a house or an apartment?": ["contemporary", "spacious", "minimalist"],
        "How do you usually spend your weekends?": ["leisurely", "rejuvenating", "unwind"],
        "Tell me about your family.": ["tight-knit", "resemblance", "upbringing"],
        "Do you like traveling?": ["wanderlust", "exotic", "itinerary"],
        "What kind of music do you like?": ["melodic", "rhythmic", "eclectic"]
    }
    initial_keywords = TOPIC_KEYWORDS.get(initial_prompt, ["interesting", "significant", "diverse"])
    
    # 3. Seed Due Words from Spaced Repetition Engine
    from app.core.spaced_repetition import get_due_vocabulary
    due_words = get_due_vocabulary(db, request.user_id, limit=2)
    
    final_keywords = initial_keywords
    if due_words:
        # Mix in due words, ensuring no duplicates
        vault_words = [w.word for w in due_words]
        final_keywords = list(set(initial_keywords + vault_words))[:5] # Max 5 for HUD space
    
    # 4. Generate Pre-Exam Briefing (Phase 11)
    briefing = f"Welcome back. Your target is Band {user.target_band}. "
    
    # Fetch chronic issues
    from app.core.database import ErrorLog
    error_logs = db.query(ErrorLog).filter(
        ErrorLog.user_id == request.user_id
    ).order_by(ErrorLog.count.desc()).limit(2).all()
    
    if error_logs:
        issues = [e.error_type for e in error_logs]
        briefing += f"Last time, you struggled with {', '.join(issues)}. Focus on avoiding these today. "
    else:
        briefing += "Consistent practice is key. Focus on fluency today. "

    if user.weakness and user.weakness != "General":
       briefing += f"Remember to work on your {user.weakness}."

    new_session = ExamSession(
        id=session_id,
        user_id=request.user_id,
        exam_type=request.exam_type,
        current_part="PART_1",
        current_prompt=initial_prompt,
        initial_keywords=final_keywords,
        status="IN_PROGRESS",
        start_time=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return ExamSessionSchema(
        id=new_session.id, 
        user_id=new_session.user_id,
        current_part=new_session.current_part,
        status=new_session.status,
        start_time=new_session.start_time,
        current_prompt=new_session.current_prompt,
        initial_keywords=new_session.initial_keywords,
        briefing_text=briefing
    )

@router.post("/{session_id}/submit-audio", response_model=Intervention)
def submit_exam_audio(
    session_id: str, 
    file: UploadFile = File(...), 
    is_retry: bool = False,
    db: Session = Depends(get_db)
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Use unique UUID for temp file
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_filename = f"temp_exam_{session_id}_{uuid.uuid4()}{ext}"
    
    # Persistent audio storage path
    AUDIO_DIR = "audio_storage"
    os.makedirs(AUDIO_DIR, exist_ok=True)
    persistent_filename = f"{AUDIO_DIR}/{session_id}_{uuid.uuid4()}{ext}"
    
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Copy to persistent storage for Audio Mirror
        shutil.copy(temp_filename, persistent_filename)

        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=session.current_part,
            db=db,
            session_id=session_id,
            is_exam_mode=True,
            is_retry=is_retry
        )
        
        # Attach audio URL for Audio Mirror feature
        intervention.user_audio_url = f"/audio/{session_id}_{attempt_count}{ext}"
        
        return intervention
    except Exception as e:
        print(f"Error processing exam audio: {e}")
        raise HTTPException(status_code=500, detail="Error processing audio submission")
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"Failed to delete temp file {temp_filename}: {e}")

@router.get("/{session_id}/summary")
def get_exam_summary(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "overall_score": session.overall_band_score or 0.0,
        "breakdown": {
            "fluency": session.fluency_score or 0.0,
            "coherence": session.coherence_score or 0.0,
            "lexical_resource": session.lexical_resource_score or 0.0,
            "grammatical_range": session.grammatical_range_score or 0.0,
            "pronunciation": session.pronunciation_score or 0.0
        },
        "feedback": "Great job completing the exam! Focus on your grammatical range to reach a higher band.",
        "recommendations": ["Practice complex sentences", "Review vocabulary in the Lab"]
    }

@router.post("/analyze-shadowing")
def analyze_shadowing(
    target_text: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyzes a specific sentence shadow attempt.
    """
    temp_filename = f"shadow_{uuid.uuid4()}.webm"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. Transcribe the shadow attempt
        from app.core.transcriber import transcribe_audio
        result = transcribe_audio(temp_filename)
        transcript = result.get("text", "").lower()
        
        # 2. Analyze Pronunciation
        from app.core.pronunciation import analyze_pronunciation
        metrics = analyze_pronunciation(temp_filename)
        
        # 3. Calculate Similarity Score (Robust word-level overlap)
        # Using [^\w\s] to strip punctuation from target_text as well
        clean_target = re.sub(r'[^\w\s]', '', target_text.lower())
        target_words = [w for w in clean_target.split() if w]
        
        clean_shadow = re.sub(r'[^\w\s]', '', transcript.lower())
        shadow_words = set(clean_shadow.split())
        
        if not target_words:
            similarity = 1.0
        else:
            overlap = sum(1 for w in target_words if w in shadow_words)
            similarity = overlap / len(target_words)
            
        # 4. Combine into a "Mastery Score"
        # 50% Similarity, 50% Pronunciation Clarity
        clarity = metrics.get("pronunciation_score", 0.0)
        mastery_score = (similarity * 0.5 + clarity * 0.5)
        
        return {
            "transcript": transcript,
            "mastery_score": round(mastery_score, 2),
            "similarity": round(similarity, 2),
            "clarity": clarity,
            "is_passed": mastery_score > 0.7
        }
        
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@router.get("/{session_id}/status")
def get_exam_status(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": session.status, "current_part": session.current_part}
