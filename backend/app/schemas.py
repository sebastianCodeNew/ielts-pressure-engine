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
    lexical_diversity: float = 0.0 
    grammar_complexity: float = 0.0 
    pronunciation_score: float = 0.0
    prosody_score: float = 0.0 # v3.0
    confidence_score: float = 0.0 # v3.0
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
    correction_drill: Optional[str] = Field(None, description="A single, specific corrective micro-task based on the turn's biggest error")
    keywords: Optional[List[str]] = None
    target_keywords: Optional[List[str]] = Field(default_factory=list, description="Target Band 8+ words for the user to use in the NEXT turn")
    user_transcript: Optional[str] = None
    reasoning: Optional[str] = Field(None, description="Explains WHY the correction matters for hitting higher bands")
    keywords_hit: List[str] = Field(default_factory=list, description="Keywords from the current mission that were successfully used")
    
    # Specific feedback fields
    grammar_advice: Optional[str] = None
    vocabulary_advice: Optional[str] = None
    pronunciation_advice: Optional[str] = None
    
    # Audio Mirror
    user_audio_url: Optional[str] = Field(None, description="URL to the user's original audio recording")
    
    # NEW: Learning v2.0 Fields
    is_probing: bool = Field(False, description="True if the examiner is asking a Socratic follow-up instead of a new topic")
    refactor_mission: Optional[str] = Field(None, description="Specific instruction for an immediate retry (e.g., 'Say that again but use the word nonetheless')")
    interjection_type: Optional[Literal['ELABORATION', 'CONTRAST', 'CAUSE_EFFECT', 'NONE']] = Field('NONE', description="The cognitive strategy used for probing")

    # NEW: Learning v3.0 Fields
    realtime_word_bank: List[str] = Field(default_factory=list, description="Top 5 Band 8+ words for the user to use in the NEXT turn (HUD display)")
    confidence_score: float = 0.0 # 0.0 (Uncertain) -> 1.0 (Confident)

    # NEW: Learning v4.0 - Active Recall Quiz
    quiz_question: Optional[str] = Field(None, description="A single-question quiz to reinforce the correction (e.g., 'Which is correct?')")
    quiz_options: Optional[List[str]] = Field(None, description="4 multiple-choice options, first one is correct")
    quiz_correct_index: int = Field(0, description="Index of the correct answer (0-3)")
    
    # NEW: Learning v4.0 - Radar Chart Metrics
    radar_metrics: Optional[Dict[str, float]] = Field(None, description="Granular scores for the turn (0-9 band scale)")

    # Real-time Engine State
    stress_level: float = 0.0

# --- EXAM FLOW ---
class ExamStartRequest(BaseModel):
    exam_type: str = "FULL_MOCK" # FULL_MOCK, PART_1_ONLY, etc.
    user_id: str = "default_user"
    topic_override: Optional[str] = None # v3.0 Mastery Drill

class ExamSessionSchema(BaseModel):
    id: str
    user_id: str
    current_part: str
    status: str
    start_time: datetime
    current_prompt: Optional[str] = None
    initial_keywords: Optional[List[str]] = None
    overall_band_score: Optional[float] = None
    briefing_text: Optional[str] = None

class ExamSummary(BaseModel):
    session_id: str
    overall_score: float
    topic_prompt: Optional[str] = None
    initial_keywords: Optional[List[str]] = None
    breakdown: DetailedScores
    feedback: str
    recommendations: List[str]

# --- VOCABULARY ---
class VocabularyCreate(BaseModel):
    word: str
    definition: str
    context_sentence: Optional[str] = None

class VocabularyItemSchema(BaseModel):
    id: int
    word: str
    definition: str
    context_sentence: Optional[str] = None
    mastery_level: int
    last_reviewed_at: datetime

    class Config:
        from_attributes = True

# --- STUDY PLAN ---
class StudyPlanItem(BaseModel):
    day: str
    focus: str
    tasks: List[str]

class StudyPlan(BaseModel):
    user_id: str
    created_at: datetime
    plan: List[StudyPlanItem]