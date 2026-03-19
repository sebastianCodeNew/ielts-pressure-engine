import uuid
import shutil
import os
import re
import random
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, ExamSession, QuestionAttempt, User, VocabularyItem
from app.schemas import ExamStartRequest, ExamSessionSchema, Intervention
from app.core.engine import process_user_attempt 
from app.core.translator import translate_to_indonesian_async, translate_checkpoint_words_async
from app.core.config import settings

router = APIRouter()

PART_1_TOPICS = settings.PART_1_TOPICS

@router.get("/warmup")
async def get_exam_warmup(user_id: str = settings.DEFAULT_USER_ID, db: Session = Depends(get_db)):
    """Fetches due vocabulary for the pre-flight warm-up."""
    from app.core.spaced_repetition import get_due_vocabulary
    # Note: DB operations are sync, but we can call them in async routes normally in FastAPI.
    due_words = get_due_vocabulary(db, user_id, limit=3)
    
    return [
        {
            "word": w.word,
            "definition": w.definition or "No definition available."
        } for w in due_words
    ]

@router.post("/start", response_model=ExamSessionSchema)
async def start_exam(request: ExamStartRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        user = User(id=request.user_id, username=request.user_id)
        db.add(user)
        db.commit()

    session_id = str(uuid.uuid4())
    initial_prompt = request.topic_override or random.choice(PART_1_TOPICS)
    
    TOPIC_KEYWORDS = {
        "Tell me about your hometown.": [
            "picturesque", "bustling", "quaint", "lively", "suburban", "cosmopolitan", "landmark", "heritage"
        ],
        "Tell me about your job or studies.": [
            "meticulous", "demanding", "rewarding", "hands-on", "rigorous", "deadline", "curriculum", "specialize"
        ],
        "Do you prefer living in a house or an apartment?": [
            "contemporary", "spacious", "minimalist", "privacy", "maintenance", "commute", "amenities", "neighbors"
        ],
        "How do you usually spend your weekends?": [
            "leisurely", "rejuvenating", "unwind", "recharge", "hang out", "run errands", "catch up", "productive"
        ],
        "Tell me about your family.": [
            "tight-knit", "resemblance", "upbringing", "supportive", "close bond", "generation", "household", "values"
        ],
        "Do you like traveling?": [
            "wanderlust", "exotic", "itinerary", "sightseeing", "budget", "local cuisine", "culture shock", "souvenir"
        ],
        "What kind of music do you like?": [
            "melodic", "rhythmic", "eclectic", "lyrics", "upbeat", "genre", "instrumental", "catchy"
        ]
    }
    topic_pool = TOPIC_KEYWORDS.get(initial_prompt, ["interesting", "significant", "diverse"])

    missing_words = [w for w in topic_pool] # Simplified logic for speed
    
    # Batch Translate Initial Keywords if needed
    from app.core.translator import translate_to_indonesian_async, translate_checkpoint_words_async
    
    try:
        tr_list, mn_list = await translate_checkpoint_words_async(topic_pool[:5])
        prompt_tr = await translate_to_indonesian_async(initial_prompt)
    except Exception as e:
        print(f"Start Exam translation error: {e}")
        tr_list, mn_list = [], []
        prompt_tr = initial_prompt

    new_session = ExamSession(
        id=session_id,
        user_id=request.user_id,
        exam_type=request.exam_type,
        current_part="PART_3" if request.exam_type == "PART_3_ONLY" else "PART_2" if request.exam_type == "PART_2_ONLY" else "PART_1",
        current_prompt=initial_prompt,
        current_prompt_translated=prompt_tr,
        initial_keywords=topic_pool[:5],
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
        current_prompt_translated=new_session.current_prompt_translated,
        initial_keywords=new_session.initial_keywords,
        initial_keywords_translated=tr_list,
        initial_keywords_meanings=mn_list,
        checkpoint_words=new_session.initial_keywords,
        checkpoint_words_translated=tr_list,
        checkpoint_words_meanings=mn_list,
        briefing_text=f"Welcome. Focus on Band {user.target_band} today."
    )

@router.get("/history/{user_id}")
async def get_detailed_history(user_id: str, db: Session = Depends(get_db)):
    attempts = db.query(QuestionAttempt).join(ExamSession).filter(
        ExamSession.user_id == user_id
    ).order_by(QuestionAttempt.created_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "part": a.part,
            "question": a.question_text,
            "question_translated": a.question_translated,
            "your_answer": a.transcript,
            "your_answer_translated": a.transcript_translated,
            "improved_answer": a.improved_response,
            "improved_answer_translated": a.improved_response_translated,
            "feedback": a.feedback_markdown,
            "feedback_translated": a.feedback_translated,
            "audio_url": f"/audio/{os.path.basename(a.audio_path)}" if a.audio_path else None,
            "keywords_hit": a.keywords_hit or [],
            "score": round((a.wpm or 0) / 15.0, 1) if a.wpm else 0.0,
            "date": a.created_at.strftime("%b %d, %Y")
        } for a in attempts
    ]

@router.post("/{session_id}/submit-audio", response_model=Intervention)
async def submit_exam_audio(
    session_id: str, 
    file: UploadFile = File(...), 
    is_retry: bool = False,
    is_refactor: bool = False,
    db: Session = Depends(get_db)
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".webm"
    temp_filename = os.path.abspath(f"temp_exam_{session_id}_{uuid.uuid4().hex}{ext}")
    
    AUDIO_DIR = "audio_storage"
    os.makedirs(AUDIO_DIR, exist_ok=True)
    persistent_filename = f"{AUDIO_DIR}/{session_id}_{uuid.uuid4()}{ext}"
    
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        shutil.copy(temp_filename, persistent_filename)

        intervention = await process_user_attempt(
            file_path=temp_filename,
            task_id=session.current_part,
            db=db,
            session_id=session_id,
            is_exam_mode=True,
            is_retry=is_retry,
            is_refactor=is_refactor
        )
        
        latest_qa = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id
        ).order_by(QuestionAttempt.id.desc()).first()
        
        if latest_qa:
            latest_qa.audio_path = persistent_filename
            db.commit()

        audio_name = os.path.basename(persistent_filename)
        intervention.user_audio_url = f"/audio/{audio_name}"
        return intervention
    except Exception as e:
        print(f"Error processing exam audio: {e}")
        raise HTTPException(status_code=500, detail="Error processing audio submission")
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"CRITICAL: Failed to delete temp file {temp_filename}. Error: {e}")

@router.get("/{session_id}/summary")
def get_exam_summary(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "overall_score": session.overall_band_score or 0.0,
        "topic_prompt": session.current_prompt,
        "initial_keywords": session.initial_keywords,
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
async def analyze_shadowing(
    target_text: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyzes a specific sentence shadow attempt.
    """
    import asyncio
    temp_filename = f"shadow_{uuid.uuid4()}.webm"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        loop = asyncio.get_running_loop()
        # 1. Transcribe the shadow attempt (CPU-bound → run in thread)
        from app.core.transcriber import transcribe_audio
        result = await loop.run_in_executor(None, transcribe_audio, temp_filename)
        transcript = result.get("text", "").lower()
        
        # 2. Analyze Pronunciation (CPU-bound → run in thread)
        from app.core.pronunciation import analyze_pronunciation
        metrics = await loop.run_in_executor(None, analyze_pronunciation, temp_filename)
        
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
async def get_exam_status(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    checkpoint_words: list[str] = []
    checkpoint_words_translated: list[str] = []
    checkpoint_words_meanings: list[str] = []

    # Prefer the latest saved NEXT-turn checkpoint requirements.
    from app.core.database import QuestionAttempt
    from app.core.translator import translate_checkpoint_words_async

    latest_qa = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).order_by(QuestionAttempt.id.desc()).first()

    if latest_qa and latest_qa.checkpoint_words_required:
        checkpoint_words = latest_qa.checkpoint_words_required or []
        checkpoint_words_translated = latest_qa.checkpoint_words_translated or []
        checkpoint_words_meanings = latest_qa.checkpoint_words_meanings or []
    elif session.initial_keywords:
        checkpoint_words = session.initial_keywords or []
        try:
            checkpoint_words_translated, checkpoint_words_meanings = await translate_checkpoint_words_async(checkpoint_words)
        except Exception as e:
            print(f"Checkpoint translation error (status): {e}")

    return {
        "status": session.status, 
        "current_part": session.current_part,
        "current_prompt": session.current_prompt,
        "current_prompt_translated": session.current_prompt_translated,
        "checkpoint_words": checkpoint_words,
        "checkpoint_words_translated": checkpoint_words_translated,
        "checkpoint_words_meanings": checkpoint_words_meanings,
    }

@router.get("/error-gym/{user_id}")
def get_error_gym(user_id: str, db: Session = Depends(get_db)):
    """
    Fetches targeted remediation drills for the user's most frequent error.
    """
    from app.core.error_gym import get_top_errors_for_user, generate_error_gym_drills
    
    top_errors = get_top_errors_for_user(db, user_id, limit=1)
    if not top_errors:
        return {"message": "No chronic errors identified yet. Keep practicing!", "drills": []}
    
    error_type = top_errors[0]["error_type"]
    session = generate_error_gym_drills(error_type)
    return session
