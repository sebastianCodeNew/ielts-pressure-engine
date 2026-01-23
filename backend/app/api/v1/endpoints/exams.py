import uuid
import shutil
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, ExamSession, QuestionAttempt, User
from app.schemas import ExamStartRequest, ExamSessionSchema, Intervention
from app.core.engine import process_user_attempt 

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

    # Use unique UUID for temp file
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_filename = f"temp_exam_{session_id}_{uuid.uuid4()}{ext}"
    
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        intervention = process_user_attempt(
            file_path=temp_filename,
            task_id=session.current_part,
            db=db,
            session_id=session_id,
            is_exam_mode=True
        )
        return intervention
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass

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

@router.get("/{session_id}/status")
def get_exam_status(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": session.status, "current_part": session.current_part}
