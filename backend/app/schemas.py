from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List, Optional
from datetime import datetime

# --- INPUT ---
class UserAttempt(BaseModel):
    task_id: str
    transcript: Optional[str] = None
    audio_duration: float = 0.0

# --- ANALYSIS & SCORES ---
class DetailedScores(BaseModel):
    fluency: float = Field(..., description="0-9 IELTS scale")
    coherence: float = Field(..., description="0-9 IELTS scale")
    lexical_resource: float = Field(..., description="0-9 IELTS scale")
    grammatical_range: float = Field(..., description="0-9 IELTS scale")
    pronunciation: float = Field(..., description="0-9 IELTS scale")

class SignalMetrics(BaseModel):
    fluency_wpm: float
    hesitation_ratio: float
    grammar_error_count: int
    filler_count: int = 0
    coherence_score: float = 0.0 
    is_complete: bool
    
    # Detailed AI feedback
    detailed_scores: Optional[DetailedScores] = None

# --- OUTPUT / INTERVENTION ---
class Intervention(BaseModel):
    action_id: Literal['MAINTAIN', 'ESCALATE_PRESSURE', 'DEESCALATE_PRESSURE', 'FORCE_RETRY', 'DRILL_SPECIFIC', 'FAIL']
    next_task_prompt: str
    topic_core: Optional[str] = None 
    constraints: Dict[str, Any]
    
    ideal_response: Optional[str] = None
    feedback_markdown: Optional[str] = None
    keywords: Optional[List[str]] = None
    
    # Specific feedback fields
    grammar_advice: Optional[str] = None
    vocabulary_advice: Optional[str] = None
    pronunciation_advice: Optional[str] = None

# --- EXAM FLOW ---
class ExamStartRequest(BaseModel):
    exam_type: str = "FULL_MOCK" # FULL_MOCK, PART_1_ONLY, etc.
    user_id: str = "default_user"

class ExamSessionSchema(BaseModel):
    id: str
    user_id: str
    current_part: str
    status: str
    start_time: datetime
    overall_band_score: Optional[float] = None

class ExamSummary(BaseModel):
    session_id: str
    overall_score: float
    breakdown: DetailedScores
    feedback: str
    recommendations: List[str]