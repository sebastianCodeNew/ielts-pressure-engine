import uuid
import shutil
import asyncio
from app.core.logger import logger
import os
import re
import random
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, ExamSession, QuestionAttempt, User, VocabularyItem
from app.schemas import ExamStartRequest, ExamSessionSchema, Intervention, ExamSummary
from app.core.engine import process_user_attempt 
from app.core.translator import translate_to_indonesian_async, translate_checkpoint_words_async
from app.core.config import settings

router = APIRouter()

PART_1_TOPICS = settings.PART_1_TOPICS

@router.get("/warmup")
async def get_exam_warmup(db: Session = Depends(get_db)):
    """Fetches due vocabulary for the pre-flight warm-up."""
    user_id = settings.DEFAULT_USER_ID
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
    user_id = settings.DEFAULT_USER_ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username=user_id)
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
        logger.error(f"Start Exam translation error: {e}", exc_info=True)
        tr_list, mn_list = [], []
        prompt_tr = initial_prompt

    new_session = ExamSession(
        id=session_id,
        user_id=user_id,
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
        briefing_text="Welcome. We have set your target to Band 9.0 per your request to maximize performance."
    )

@router.get("/history")
async def get_detailed_history(db: Session = Depends(get_db)):
    user_id = settings.DEFAULT_USER_ID
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

    # 1. File Validation
    filename = file.filename or "response.webm"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
    
    # Read content to check size
    content = await file.read()
    if len(content) > settings.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
    if len(content) < 100:
        # Return graceful intervention instead of crashing/400
        return Intervention(
            action_id="MAINTAIN",
            next_task_prompt="Please try again with a longer recording.",
            feedback_markdown="⚠️ **Audio too short**. Please record for at least 3 seconds.",
            constraints={"timer": 45}
        )

    temp_filename = os.path.abspath(f"temp_exam_{session_id}_{uuid.uuid4().hex}{ext}")
    
    AUDIO_DIR = settings.AUDIO_STORAGE_DIR
    os.makedirs(AUDIO_DIR, exist_ok=True)
    persistent_filename = f"{AUDIO_DIR}/{session_id}_{uuid.uuid4()}{ext}"
    
    try:
        with open(temp_filename, "wb") as buffer:
            buffer.write(content)
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
        logger.error(f"Error processing exam audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing audio submission")
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"CRITICAL: Failed to delete temp file {temp_filename}. Error: {e}")

@router.get("/{session_id}/summary", response_model=ExamSummary)
def get_exam_summary(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Simple dynamic analytics
    metrics = {
        "Fluency": session.fluency_score or 0.0,
        "Coherence": session.coherence_score or 0.0,
        "Lexical": session.lexical_resource_score or 0.0,
        "Grammar": session.grammatical_range_score or 0.0,
        "Pronunciation": session.pronunciation_score or 0.0
    }
    lowest_area = min(metrics, key=metrics.get)
    
    advice_map = {
        "Fluency": "Fokus pada kecepatan bicara (WPM) dan kurangi pause panjang untuk skor lebih tinggi.",
        "Coherence": "Gunakan kata hubung seperti 'However' atau 'Additionally' agar jawaban lebih logis.",
        "Lexical": "Coba gunakan kosakata yang lebih spesifik. Cek 'Vocabulary Lab' untuk referensi.",
        "Grammar": "Perhatikan struktur kalimat kompleks dan kesesuaian subjek-kata kerja.",
        "Pronunciation": "Latih intonasi dan kejelasan pengucapan kata kunci."
    }
    
    return {
        "session_id": session_id,
        "overall_score": session.overall_band_score or 0.0,
        "topic_prompt": session.current_prompt,
        "initial_keywords": session.initial_keywords,
        "breakdown": {
            "fluency": metrics["Fluency"],
            "coherence": metrics["Coherence"],
            "lexical_resource": metrics["Lexical"],
            "grammatical_range": metrics["Grammar"],
            "pronunciation": metrics["Pronunciation"]
        },
        "feedback": f"Sesi selesai! Area yang paling butuh perhatian adalah {lowest_area}. {advice_map[lowest_area]}",
        "recommendations": [
            f"Latih micro-skill {lowest_area}",
            "Review hasil rekaman di history",
            "Gunakan Vocabulary Lab untuk kata baru"
        ]
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
    
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        loop = asyncio.get_running_loop()
        # 1. Transcribe the shadow attempt (CPU-bound → run in thread)
        from app.core.transcriber import transcribe_audio
        from app.core.transcript_processor import post_process_transcript
        result = await loop.run_in_executor(None, transcribe_audio, temp_filename)
        transcript = result.get("text", "")
        
        # 1b. Clean transcript (v15.0 - apply same pipeline as exam mode)
        transcript = post_process_transcript(transcript)
        transcript = transcript.lower() if transcript else ""
        
        # 2. Analyze Pronunciation (CPU-bound → run in thread)
        from app.core.pronunciation import analyze_pronunciation
        metrics = await loop.run_in_executor(None, analyze_pronunciation, temp_filename)
        
        # 3. Calculate Similarity Score (Frequency-aware, punctuation-insensitive word overlap)
        from collections import Counter
        target_words = re.findall(r'\b\w+\b', target_text.lower())
        target_counts = Counter(target_words)
        
        shadow_words = re.findall(r'\b\w+\b', transcript.lower())
        shadow_counts = Counter(shadow_words)
        
        if not target_words:
            similarity = 1.0
        else:
            # Count matches based on minimum frequency in target vs shadow
            overlap = 0
            for word, count in target_counts.items():
                overlap += min(count, shadow_counts.get(word, 0))
            similarity = overlap / len(target_words)
            
        # 4. Combine into a "Mastery Score"
        clarity = metrics.get("pronunciation_score", 0.0)
        mastery_score = (similarity * 0.5 + clarity * 0.5)
        
        # 5. Indonesian Translations (v15.0)
        transcript_tr = ""
        target_tr = ""
        try:
            transcript_tr = await translate_to_indonesian_async(transcript) if transcript else ""
            target_tr = await translate_to_indonesian_async(target_text)
        except Exception as e:
            logger.error(f"Shadowing translation error: {e}", exc_info=True)
        
        return {
            "transcript": transcript,
            "transcript_translated": transcript_tr,
            "target_text_translated": target_tr,
            "mastery_score": round(mastery_score, 2),
            "similarity": round(similarity, 2),
            "clarity": clarity,
            "is_passed": mastery_score > 0.7
        }
        
    finally:
        # v16.0: Hardened cleanup for Windows file-locking resilience
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                logger.debug(f"Shadowing temp file {temp_filename} removed.")
            except PermissionError:
                # On Windows, sometimes FFmpeg or the engine still holds the handle for a split second
                logger.warning(f"File {temp_filename} is locked. Retrying cleanup in 1s...")
                import time
                try: 
                    time.sleep(1)
                    os.remove(temp_filename)
                except Exception:
                    logger.error(f"Failed to remove locked shadowing file {temp_filename}. Manual cleanup required.")
            except Exception as e:
                logger.error(f"Shadowing cleanup error: {e}")

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
            logger.error(f"Checkpoint translation error (status): {e}", exc_info=True)

    return {
        "status": session.status, 
        "current_part": session.current_part,
        "current_prompt": session.current_prompt,
        "current_prompt_translated": session.current_prompt_translated,
        "checkpoint_words": checkpoint_words,
        "checkpoint_words_translated": checkpoint_words_translated,
        "checkpoint_words_meanings": checkpoint_words_meanings,
    }

@router.get("/error-gym")
async def get_error_gym(db: Session = Depends(get_db)):
    """
    Fetches targeted remediation drills for the user's most frequent error.
    """
    user_id = settings.DEFAULT_USER_ID
    from app.core.error_gym import get_top_errors_for_user, generate_error_gym_drills
    
    top_errors = get_top_errors_for_user(db, user_id, limit=1)
    if not top_errors:
        return {"message": "No chronic errors identified yet. Keep practicing!", "drills": []}
    
    error_type = top_errors[0]["error_type"]
    session = await generate_error_gym_drills(error_type)
    return session
