from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, User, ExamSession
from typing import List

router = APIRouter()

@router.get("/me")
def get_user_profile(user_id: str = "default_user", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/me/stats")
def get_user_stats(user_id: str = "default_user", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    sessions = db.query(ExamSession).filter(ExamSession.user_id == user_id).all()
    
    return {
        "total_exams": len(sessions),
        "average_score": user.average_band_score,
        "recent_scores": [s.overall_band_score for s in sessions[-5:] if s.overall_band_score]
    }
