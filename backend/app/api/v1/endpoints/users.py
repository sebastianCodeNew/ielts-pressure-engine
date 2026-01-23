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
    
    # Calculate Skill Breakdown (Average of all completed sessions)
    completed_sessions = [s for s in sessions if s.status == "COMPLETED"]
    
    skill_breakdown = [
        {"subject": 'Fluency', "A": sum(s.fluency_score or 0 for s in completed_sessions) / len(completed_sessions) if completed_sessions else 0, "fullMark": 9},
        {"subject": 'Coherence', "A": sum(s.lexical_resource_score or 0 for s in completed_sessions) / len(completed_sessions) if completed_sessions else 0, "fullMark": 9},
        {"subject": 'Lexical', "A": sum(s.lexical_resource_score or 0 for s in completed_sessions) / len(completed_sessions) if completed_sessions else 0, "fullMark": 9},
        {"subject": 'Grammar', "A": sum(s.grammatical_range_score or 0 for s in completed_sessions) / len(completed_sessions) if completed_sessions else 0, "fullMark": 9},
        {"subject": 'Pronunciation', "A": sum(s.pronunciation_score or 0 for s in completed_sessions) / len(completed_sessions) if completed_sessions else 0, "fullMark": 9},
    ]

    return {
        "total_exams": len(sessions),
        "average_score": user.average_band_score,
        "recent_scores": [
            {"name": f"Attempt {i+1}", "score": s.overall_band_score} 
            for i, s in enumerate(sessions[-6:]) if s.overall_band_score
        ],
        "skill_breakdown": skill_breakdown
    }

@router.get("/me/history")
def get_user_history(user_id: str = "default_user", db: Session = Depends(get_db)):
    sessions = db.query(ExamSession).filter(ExamSession.user_id == user_id).order_by(ExamSession.start_time.desc()).all()
    return [
        {
            "date": s.start_time.strftime("%b %d, %Y"),
            "topic": s.exam_type, # Or get the actual first question topic
            "duration": "14m", # Placeholder until duration is tracked in ExamSession
            "score": s.overall_band_score or 0,
            "status": s.status
        } for s in sessions
    ]
