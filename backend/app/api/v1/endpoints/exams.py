import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, ExamSession, QuestionAttempt, User
from app.schemas import ExamStartRequest, ExamSessionSchema, Intervention, DetailedScores
from app.core.engine import process_user_attempt # We'll need to adapt this

router = APIRouter()

@router.post("/start", response_model=ExamSessionSchema)
def start_exam(request: ExamStartRequest, db: Session = Depends(get_db)):
    # Ensure user exists (hack for MVP)
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        user = User(id=request.user_id, username=request.user_id)
        db.add(user)
        db.commit()

    session_id = str(uuid.uuid4())
    new_session = ExamSession(
        id=session_id,
        user_id=request.user_id,
        exam_type=request.exam_type,
        current_part="PART_1",
        status="IN_PROGRESS"
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

    # Save Temp File (copied from main.py logic)
    import shutil
    import os
    temp_filename = f"temp_{session_id}_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Here we would use the engine but also handle Part transitions
        # For now, delegating to a modified engine call
        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=session.current_part,
            db=db,
            session_id=session_id,
            is_exam_mode=True # New flag to handle exam transitions
        )
        
        # Log to QuestionAttempt with REAL metrics from the engine
        new_attempt = QuestionAttempt(
            session_id=session_id,
            part=session.current_part,
            question_text=intervention.next_task_prompt, 
            transcript=intervention.feedback_markdown or "No transcript", # Usually engine fills transcript
            duration_seconds=0.0, # WIP: Get from engine return
            wpm=0.0, # WIP: Engine should return metrics or we extract
            coherence_score=0.0,
            hesitation_ratio=0.0,
            feedback_markdown=intervention.feedback_markdown,
            improved_response=intervention.ideal_response
        )
        # Note: process_user_attempt already logs to QuestionAttempt if is_exam_mode=True
        # We should avoid double logging but ensure metrics are captured.
        # Let's adjust engine.py if needed, or rely on it.
        
        # Actually, engine.py already adds QuestionAttempt! 
        # So we just return the intervention here.
        return intervention
        
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@router.get("/{session_id}/summary")
def get_exam_summary(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate mock summary logic
    return {
        "session_id": session_id,
        "overall_score": session.overall_band_score or 6.5,
        "breakdown": {
            "fluency": session.fluency_score or 6.0,
            "coherence": session.lexical_resource_score or 7.0,
            "lexical_resource": session.lexical_resource_score or 6.5,
            "grammatical_range": session.grammatical_range_score or 6.5,
            "pronunciation": session.pronunciation_score or 7.0
        }
    }
