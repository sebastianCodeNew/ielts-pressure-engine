from pydantic import BaseModel
from typing import Literal, Dict, Any, List, Optional

# The Input
class UserAttempt(BaseModel):
    task_id: str
    transcript: Optional[str] = None
    audio_duration: float = 0.0

# The Analysis (UPDATED)
# The Analysis (UPDATED)
class SignalMetrics(BaseModel):
    fluency_wpm: float
    hesitation_ratio: float
    grammar_error_count: int
    filler_count: int = 0 # <--- NEW: Logic to count 'um', 'ah'
    coherence_score: float = 0.0 
    is_complete: bool

# The Output
class Intervention(BaseModel):
    action_id: Literal['MAINTAIN', 'ESCALATE_PRESSURE', 'DEESCALATE_PRESSURE', 'FORCE_RETRY', 'DRILL_SPECIFIC', 'FAIL']
    next_task_prompt: str
    topic_core: Optional[str] = None 
    constraints: Dict[str, Any]
    
    # --- NEW EDUCATIONAL FIELDS ---
    ideal_response: Optional[str] = None # Band 7.0 Example
    feedback_markdown: Optional[str] = None # Specific grammar tips
    keywords: Optional[List[str]] = None # For next task priming