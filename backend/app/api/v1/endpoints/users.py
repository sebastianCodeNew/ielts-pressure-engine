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
        "skill_breakdown": skill_breakdown,
        "target_band": user.target_band,
        "weakness": user.weakness
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

from pydantic import BaseModel

class UserProfileUpdate(BaseModel):
    target_band: str
    weakness: str

@router.put("/me")
def update_user_profile(profile: UserProfileUpdate, user_id: str = "default_user", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.target_band = profile.target_band
    user.weakness = profile.weakness
    db.commit()
    return {"status": "updated", "target_band": user.target_band, "weakness": user.weakness}

@router.get("/me/weakness-report")
def get_weakness_report(user_id: str = "default_user", db: Session = Depends(get_db)):
    """Comprehensive weakness analysis across all sessions."""
    from app.core.database import QuestionAttempt
    from collections import Counter
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all attempts for this user
    sessions = db.query(ExamSession).filter(ExamSession.user_id == user_id).all()
    
    # Early return if no sessions (prevents empty IN clause error)
    if not sessions:
        return {
            "skill_averages": {"Fluency": 5, "Coherence": 5, "Lexical": 5, "Grammar": 5, "Pronunciation": 5},
            "lowest_area": "General",
            "trend_data": [],
            "recurring_errors": [],
            "total_attempts": 0
        }
    
    session_ids = [s.id for s in sessions]
    
    all_attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id.in_(session_ids)
    ).all()
    
    if not all_attempts:
        return {
            "skill_averages": {"Fluency": 5, "Coherence": 5, "Lexical": 5, "Grammar": 5, "Pronunciation": 5},
            "lowest_area": "General",
            "trend_data": [],
            "recurring_errors": [],
            "total_attempts": 0
        }
    
    # Calculate averages (normalized to 0-9 scale)
    avg_fluency = sum((a.wpm or 0) / 15 for a in all_attempts) / len(all_attempts)
    avg_coherence = sum((a.coherence_score or 0) * 9 for a in all_attempts) / len(all_attempts)
    avg_lexical = sum((a.lexical_diversity or 0) * 15 for a in all_attempts) / len(all_attempts)
    avg_grammar = sum((a.grammar_complexity or 0) * 40 for a in all_attempts) / len(all_attempts)
    avg_pronunciation = sum((a.pronunciation_score or 0) * 9 for a in all_attempts) / len(all_attempts)
    
    skill_averages = {
        "Fluency": min(9, avg_fluency),
        "Coherence": min(9, avg_coherence),
        "Lexical": min(9, avg_lexical),
        "Grammar": min(9, avg_grammar),
        "Pronunciation": min(9, avg_pronunciation)
    }
    
    lowest_area = min(skill_averages, key=skill_averages.get)
    
    # Extract recurring error patterns from feedback
    error_keywords = []
    for a in all_attempts:
        if a.feedback_markdown:
            fb = a.feedback_markdown.lower()
            if "grammar" in fb or "tense" in fb or "agreement" in fb:
                error_keywords.append("Grammar Errors")
            if "vocabulary" in fb or "lexical" in fb or "word choice" in fb:
                error_keywords.append("Vocabulary Range")
            if "coherence" in fb or "linking" in fb or "connector" in fb:
                error_keywords.append("Coherence Issues")
            if "hesitation" in fb or "filler" in fb or "pause" in fb:
                error_keywords.append("Fluency Gaps")
    
    # Now use micro-skill ErrorLog for granular breakdown
    from app.core.database import ErrorLog
    error_logs = db.query(ErrorLog).filter(
        ErrorLog.user_id == user_id
    ).order_by(ErrorLog.count.desc()).limit(5).all()
    
    micro_skill_errors = [{"error": e.error_type, "count": e.count} for e in error_logs]
    
    # Trend data (last 10 sessions)
    completed = [s for s in sessions if s.status == "COMPLETED"][-10:]
    trend_data = [
        {"session": i+1, "score": s.overall_band_score or 0} 
        for i, s in enumerate(completed)
    ]
    
    return {
        "skill_averages": skill_averages,
        "lowest_area": lowest_area,
        "trend_data": trend_data,
        "recurring_errors": micro_skill_errors,  # Now uses micro-skill tracking
        "total_attempts": len(all_attempts)
    }
