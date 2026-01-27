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
    # 3. Seed Retention Words from Vault
    from app.core.database import VocabularyItem
    retention_words = db.query(VocabularyItem).filter(
        VocabularyItem.user_id == request.user_id,
        VocabularyItem.mastery_level < 80
    ).order_by(VocabularyItem.last_reviewed_at.asc()).limit(2).all()
    
    final_keywords = initial_keywords
    if retention_words:
        # Mix in retention words, ensuring no duplicates
        vault_words = [r.word for r in retention_words]
        final_keywords = list(set(initial_keywords + vault_words))[:5] # Max 5 for hud space

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
    
    return new_session

@router.post("/{session_id}/submit-audio", response_model=Intervention)
def submit_exam_audio(
    session_id: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Use unique UUID for temp file
    # Use unique UUID for temp file
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_filename = f"temp_exam_{session_id}_{uuid.uuid4()}{ext}"
    
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=session.current_part,
            db=db,
            session_id=session_id,
            is_exam_mode=True
        )
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
