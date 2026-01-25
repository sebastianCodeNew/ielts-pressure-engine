from typing import List, Literal, Optional
from pydantic import BaseModel
from app.schemas import UserAttempt, SignalMetrics

# --- State Definitions ---

class AttemptResult(BaseModel):
    """Snapshot of a single interaction"""
    attempt_id: str
    prompt: str
    transcript: str
    metrics: SignalMetrics
    outcome: Literal['PASS', 'FAIL', 'RETRY']

class AgentState(BaseModel):
    """The 'Short-term Memory' of the session"""
    session_id: str
    history: List[AttemptResult] = []
    
    # Context (Where are we?)
    current_difficulty: int = 1 # 1-10 scale
    consecutive_failures: int = 0
    
    # Psychological Mode (The Vitals)
    # Calculated from history
    stress_level: float = 0.0 # 0.0 (Bored) -> 1.0 (Panic)
    fluency_trend: Literal['improving', 'stable', 'degrading'] = 'stable'
    
    # User Context (Deep Adaptation)
    target_band: str = "7.5"
    weakness: str = "General"

# --- Logic / Reducers ---

def calculate_stress(history: List[AttemptResult]) -> float:
    """
    Heuristic: Stress increases with hesitancy and failures.
    """
    if not history:
        return 0.0
    
    last = history[-1]
    
    # Base stress from last performance
    stress = last.metrics.hesitation_ratio * 1.0 
    
    # compound with failures
    if last.outcome == 'FAIL':
        stress += 0.3
        
    return min(max(stress, 0.0), 1.0)

def determine_trend(history: List[AttemptResult]) -> str:
    if len(history) < 2:
        return 'stable'
        
    current_wpm = history[-1].metrics.fluency_wpm
    prev_wpm = history[-2].metrics.fluency_wpm
    
    delta = current_wpm - prev_wpm
    if delta > 5: return 'improving'
    if delta < -5: return 'degrading'
    return 'stable'

def update_state(state: AgentState, attempt: UserAttempt, metrics: SignalMetrics, outcome: str, current_prompt: str) -> AgentState:
    """
    State Transition Function: S' = f(S, A)
    """
    # 1. Archive the result
    result = AttemptResult(
        attempt_id=attempt.task_id,
        prompt=current_prompt,
        transcript=attempt.transcript or "",
        metrics=metrics,
        outcome=outcome # type: ignore
    )
    
    # 2. Update History (Limit to last 10 for context window)
    new_history = state.history + [result]
    if len(new_history) > 10:
        new_history = new_history[-10:]
        
    # 3. Calculate Derived Metrics
    new_stress = calculate_stress(new_history)
    new_trend = determine_trend(new_history)
    
    # 4. Update Counters
    new_failures = state.consecutive_failures + 1 if outcome == 'FAIL' else 0
    
    return state.model_copy(update={
        "history": new_history,
        "stress_level": new_stress,
        "fluency_trend": new_trend,
        "consecutive_failures": new_failures
    })
